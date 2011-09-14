#
# This sets up how models are displayed 
# in the web admin interface. 
#

from src.objects.models import ObjAttribute, ObjectDB
from django.contrib import admin

class ObjAttributeInline(admin.TabularInline):
    model = ObjAttribute
    fields = ('db_key', 'db_value')
    max_num = 1

class ObjectDBAdmin(admin.ModelAdmin):
    inlines = [ObjAttributeInline]
    list_display = ('id', 'db_key', 'db_location', 'db_player', 'db_typeclass_path')
    list_display_links = ('id', 'db_key')
    ordering = ['db_player', 'db_typeclass_path', 'id']
    search_fields = ['^db_key', 'db_typeclass_path']
    save_as = True 
    save_on_top = True
    list_select_related = True 
admin.site.register(ObjectDB, ObjectDBAdmin)
