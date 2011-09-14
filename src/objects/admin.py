#
# This sets up how models are displayed 
# in the web admin interface. 
#

from src.objects.models import ObjAttribute, ObjectDB
from django.contrib import admin

class ObjAttributeAdmin(admin.ModelAdmin):
    list_display = ('id', 'db_key', 'db_value', 'db_lock_storage', 'db_obj')
    list_display_links = ("id", 'db_key')
    ordering = ["db_obj", 'db_key']
    search_fields = ['id', 'db_key', 'db_obj']
    save_as = True 
    save_on_top = True   
    list_select_related = True 
admin.site.register(ObjAttribute, ObjAttributeAdmin)

class ObjectDBAdmin(admin.ModelAdmin):
    list_display = ('id', 'db_key', 'db_typeclass_path', 'db_location', 'db_player')
    list_display_links = ('id', 'db_key')
    ordering = ['id', 'db_typeclass_path']
    readonly_fields = ['db_permissions', 'db_lock_storage']
    search_fields = ['^db_key', 'db_typeclass_path']
    save_as = True 
    save_on_top = True
    list_select_related = True 
admin.site.register(ObjectDB, ObjectDBAdmin)
