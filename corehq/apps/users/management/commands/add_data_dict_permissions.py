from django.core.management.base import BaseCommand

from django.db.models import Q

from dimagi.utils.chunked import chunked
from corehq.apps.users.permissions import EXPORT_PERMISSIONS
from corehq.apps.users.models import RolePermission, HqPermissions
from corehq.apps.users.models_role import Permission, UserRole
from corehq.toggles import DATA_DICTIONARY, DATA_FILE_DOWNLOAD


class Command(BaseCommand):
    help = "Adds data dictionary permission to user role if not already present and edit tab is viewable."

    def handle(self, **options):
        num_roles_modified = 0
        view_data_dict_permission, created = Permission.objects.get_or_create(value='view_data_dict')
        edit_data_dict_permission, created = Permission.objects.get_or_create(value='edit_data_dict')

        user_role_ids_to_migrate = get_user_role_ids_to_migrate()

        for chunk in chunked(user_role_ids_to_migrate, 1000):
            for role in UserRole.objects.filter(id__in=chunk):
                role.rolepermission_set.get_or_create(
                    permission_fk=view_data_dict_permission,
                    defaults={"allow_all": True}
                )
                rp, created = role.rolepermission_set.get_or_create(
                    permission_fk=edit_data_dict_permission,
                    defaults={"allow_all": True}
                )
                num_roles_modified += 1
                if num_roles_modified % 5000 == 0:
                    print("Updated {} roles".format(num_roles_modified))


def get_user_role_ids_to_migrate():
    data_dict_domains = DATA_DICTIONARY.get_enabled_domains()

    return (UserRole.objects
        .filter(domain__in=data_dict_domains)
        .exclude(role_already_migrated())
        .filter(role_can_view_data_tab())
        .distinct()
        .values_list("id", flat=True))

def role_already_migrated() -> Q:
    edit_data_dict_permission = Permission.objects.get(value=HqPermissions.edit_data_dict.name)
    return Q(rolepermission__permission_fk_id=edit_data_dict_permission.id)

def role_can_view_data_tab() -> Q:
    can_edit_commcare_data = build_role_can_edit_commcare_data_q_object()
    can_export_data = build_role_can_export_data_q_object()
    can_download_data_files = build_role_can_download_data_files_q_object()

    return (can_edit_commcare_data | can_export_data | can_download_data_files)


def build_role_can_edit_commcare_data_q_object() -> Q:
    edit_data_permission, created = Permission.objects.get_or_create(value='edit_data')
    return Q(rolepermission__permission_fk_id=edit_data_permission.id)


def build_role_can_export_data_q_object() -> Q:
    can_view_commcare_export_reports = Q(allow_all=True)
    for export_permission in EXPORT_PERMISSIONS:
        can_view_commcare_export_reports.add(Q(allowed_items__contains=[export_permission]), Q.OR)
    queryset = (RolePermission.objects
                .filter(permission_fk__value=HqPermissions.view_reports.name)
                .filter(can_view_commcare_export_reports))

    return Q(rolepermission__in=queryset)


def build_role_can_download_data_files_q_object() -> Q:
    data_file_download_domains = DATA_FILE_DOWNLOAD.get_enabled_domains()
    view_file_dropzone_permission, created = Permission.objects.get_or_create(value='view_file_dropzone')
    edit_file_dropzone_permission, created = Permission.objects.get_or_create(value='edit_file_dropzone')

    data_file_download_feat_flag_on = Q(domain__in=data_file_download_domains)
    can_view_file_dropzone = Q(rolepermission__permission_fk_id=view_file_dropzone_permission.id)
    can_edit_file_dropzone = Q(rolepermission__permission_fk_id=edit_file_dropzone_permission.id)

    return (data_file_download_feat_flag_on & (can_view_file_dropzone | can_edit_file_dropzone))
