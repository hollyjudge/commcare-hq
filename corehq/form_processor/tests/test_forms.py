import uuid

from django.conf import settings
from django.db import transaction
from django.test import TestCase

from corehq.form_processor.exceptions import XFormNotFound
from corehq.form_processor.models import XFormInstance
from corehq.form_processor.tests.utils import (
    FormProcessorTestUtils,
    create_form_for_test,
    sharded,
)

DOMAIN = 'test-forms-manager'


@sharded
class XFormInstanceManagerTest(TestCase):

    def tearDown(self):
        if settings.USE_PARTITIONED_DATABASE:
            FormProcessorTestUtils.delete_all_sql_forms(DOMAIN)
            FormProcessorTestUtils.delete_all_sql_cases(DOMAIN)
        super().tearDown()

    def test_get_form(self):
        form = create_form_for_test(DOMAIN)
        with self.assertNumQueries(1, using=form.db):
            form = XFormInstance.objects.get_form(form.form_id, DOMAIN)
        self._check_simple_form(form)

    def test_get_form_with_wrong_domain(self):
        form = create_form_for_test(DOMAIN)
        with self.assertRaises(XFormNotFound):
            XFormInstance.objects.get_form(form.form_id, "wrong-domain")

    def test_get_form_without_domain(self):
        # DEPRECATED domain should be supplied if available
        form = create_form_for_test(DOMAIN)
        with self.assertNumQueries(1, using=form.db):
            form = XFormInstance.objects.get_form(form.form_id)
        self._check_simple_form(form)

    def test_get_form_missing(self):
        with self.assertRaises(XFormNotFound):
            XFormInstance.objects.get_form('missing_form')

    def test_get_forms(self):
        form1 = create_form_for_test(DOMAIN)
        form2 = create_form_for_test(DOMAIN)

        forms = XFormInstance.objects.get_forms(['missing_form'])
        self.assertEqual(forms, [])

        forms = XFormInstance.objects.get_forms([form1.form_id])
        self.assertEqual([f.form_id for f in forms], [form1.form_id])

        forms = XFormInstance.objects.get_forms([form1.form_id, form2.form_id], ordered=True)
        self.assertEqual([f.form_id for f in forms], [form1.form_id, form2.form_id])

    def test_save_new_form_and_get_attachments(self):
        unsaved_form = create_form_for_test(DOMAIN, save=False)
        XFormInstance.objects.save_new_form(unsaved_form)
        self.assertTrue(unsaved_form.is_saved())
        self.assert_form_xml_attachment(unsaved_form)

    def test_save_new_form_db_error(self):
        form = create_form_for_test(DOMAIN)
        dup_form = create_form_for_test(DOMAIN, save=False)
        dup_form.form_id = form.form_id

        # use transaction to prevent rolling back the test's transaction
        with self.assertRaises(Exception), transaction.atomic(dup_form.db):
            XFormInstance.objects.save_new_form(dup_form)

        # save should succeed with unique form id
        dup_form.form_id = uuid.uuid4().hex
        XFormInstance.objects.save_new_form(dup_form)
        self.assert_form_xml_attachment(dup_form)

    def assert_form_xml_attachment(self, form):
        attachments = XFormInstance.objects.get_attachments(form.form_id)
        self.assertEqual([a.name for a in attachments], ["form.xml"])

    def _check_simple_form(self, form):
        self.assertIsInstance(form, XFormInstance)
        self.assertIsNotNone(form)
        self.assertEqual(DOMAIN, form.domain)
        self.assertEqual('user1', form.user_id)
        return form
