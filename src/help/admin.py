from django.contrib import admin
from src.help.models import HelpEntry

class HelpEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'db_key', 'db_help_category', 'db_permissions')
    list_display_links = ('id', 'db_key')
    search_fields = ['^db_key', 'db_entrytext']
    ordering = ['db_help_category', 'db_key']
    save_as = True 
    save_on_top = True   
    list_select_related = True 
admin.site.register(HelpEntry, HelpEntryAdmin)
