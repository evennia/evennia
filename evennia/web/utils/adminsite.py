"""
Custom Evennia admin-site, for better customization of the admin-site
as a whole.

This must be located outside of the admin/ folder because it must be imported
before any of the app-data (which in turn must be imported in the `__init__.py`
of that folder for Django to find them).

"""

from django.contrib import admin
from django.contrib.admin import apps


class EvenniaAdminApp(apps.AdminConfig):
    """
    This is imported in INSTALLED_APPS instead of django.contrib.admin.

    """

    default_site = "evennia.web.utils.adminsite.EvenniaAdminSite"


class EvenniaAdminSite(admin.AdminSite):
    """
    The main admin site root (replacing the default from Django). When doing
    admin.register in the admin/ folder, this is what is being registered to.

    """

    site_header = "Evennia web admin"

    app_order = [
        "accounts",
        "objects",
        "scripts",
        "comms",
        "help",
        "typeclasses",
        "server",
        "sites",
        "flatpages",
        "auth",
    ]

    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        app_mapping = {app["app_label"]: app for app in app_list}
        return [app_mapping.get(app_label) for app_label in self.app_order]
