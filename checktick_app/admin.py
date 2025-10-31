from django.conf import settings
from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig


class CheckTickAdminSite(AdminSite):
    site_header = f"{getattr(settings, 'BRAND_TITLE', 'CheckTick')} Admin"
    site_title = f"{getattr(settings, 'BRAND_TITLE', 'CheckTick')} Admin"
    index_title = "Administration"

    def has_permission(self, request):  # type: ignore[override]
        # Restrict access strictly to active superusers
        return bool(
            request.user and request.user.is_active and request.user.is_superuser
        )


class CheckTickAdminConfig(AdminConfig):
    default_site = "checktick_app.admin.CheckTickAdminSite"
