"""

This sets up how models are displayed
in the web admin interface.

"""

from django.contrib import admin

from evennia.server.models import ServerConfig


@admin.register(ServerConfig)
class ServerConfigAdmin(admin.ModelAdmin):
    """
    Custom admin for server configs

    """

    list_display = ("db_key", "db_value")
    list_display_links = ("db_key",)
    ordering = ["db_key", "db_value"]
    search_fields = ["db_key"]
    save_as = True
    save_on_top = True
    list_select_related = True
