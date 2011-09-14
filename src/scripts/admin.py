#
# This sets up how models are displayed 
# in the web admin interface. 
#

from src.scripts.models import ScriptAttribute, ScriptDB
from django.contrib import admin

class ScriptAttributeInline(admin.TabularInline):
    model = ScriptAttribute
    fields = ('db_key', 'db_value')    
    max_num = 1

class ScriptDBAdmin(admin.ModelAdmin):
    inlines = [ScriptAttributeInline]
    list_display = ('id', 'db_key', 'db_typeclass_path', 'db_obj', 'db_interval', 'db_repeats', 'db_persistent')
    list_display_links = ('id', 'db_key')
    ordering = ['db_obj', 'db_typeclass_path']    
    search_fields = ['^db_key', 'db_typeclass_path']    
    save_as = True 
    save_on_top = True
    list_select_related = True 
admin.site.register(ScriptDB, ScriptDBAdmin)
