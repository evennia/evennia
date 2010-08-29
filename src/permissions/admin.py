#
# This sets up how models are displayed 
# in the web admin interface. 
#

from src.permissions.models import PermissionGroup
from django.contrib import admin

class PermissionGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'db_key', 'db_group_permissions')
    list_display_links = ('id', "db_key")
    ordering = ['db_key', 'db_group_permissions']
    readonly_fields = ['db_key', 'db_group_permissions', 'db_permissions']
    search_fields = ['db_key']
    save_as = True 
    save_on_top = True   
    list_select_related = True 
admin.site.register(PermissionGroup, PermissionGroupAdmin)
