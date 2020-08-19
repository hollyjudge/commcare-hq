from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import TestCase, RequestFactory

from corehq.apps.api.resources.auth import LoginAuthentication, LoginAndDomainAuthentication
from corehq.apps.domain.models import Domain
from corehq.apps.users.models import WebUser, HQApiKey


class AuthenticationTestBase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = RequestFactory()
        cls.domain = Domain.get_or_create_with_name('api-test', is_active=True)
        cls.username = 'alice@example.com'
        cls.password = '***'
        cls.user = WebUser.create(cls.domain.name, cls.username, cls.password, None, None)
        cls.api_key, _ = HQApiKey.objects.get_or_create(user=WebUser.get_django_user(cls.user))

    @classmethod
    def tearDownClass(cls):
        cls.domain.delete()
        super().tearDownClass()

    def _get_request_with_api_key(self):
        return self._get_request(HTTP_AUTHORIZATION=f'ApiKey {self.username}:{self.api_key.key}')

    def _get_request(self, domain=None, **extras):
        path = self._get_domain_path() if domain else ''
        request = self.factory.get(path, **extras)
        request.user = AnonymousUser()  # this is required for HQ's permission classes to resolve
        request.domain = domain  # as is this for any domain-specific request
        return request

    def _get_domain_path(self):
        return f'/a/{self.domain.name}/'

    def assertAuthenticationSuccess(self, auth_instance, request):
        self.assertTrue(auth_instance.is_authenticated(request))

    def assertAuthenticationFail(self, auth_instance, request):
        result = auth_instance.is_authenticated(request)
        # currently auth classes return a 401/403 response in some scenarios
        # this should likely be changed to always return False
        # more discussion here: https://github.com/dimagi/commcare-hq/pull/28201#discussion_r461082885
        if isinstance(result, HttpResponse):
            self.assertTrue(result.status_code in (401, 403))
        else:
            self.assertFalse(result)


class LoginAuthenticationTest(AuthenticationTestBase):

    def test_login_no_auth(self):
        self.assertAuthenticationFail(LoginAuthentication(), self._get_request())

    def test_login_with_auth(self):
        self.assertAuthenticationSuccess(LoginAuthentication(), self._get_request_with_api_key())


class LoginAndDomainAuthenticationTest(AuthenticationTestBase):

    def test_login_with_domain(self):
        self.assertAuthenticationSuccess(LoginAndDomainAuthentication(), self._get_request(domain=self.domain))

    def test_login_with_wrong_domain(self):
        domain = Domain.get_or_create_with_name('api-test-fail', is_active=True)
        self.addCleanup(domain.delete)
        self.assertAuthenticationFail(LoginAndDomainAuthentication(), self._get_request(domain=domain))
