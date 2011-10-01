from django.contrib import admin
from src.help.models import HelpEntry

class HelpEntryAdmin(admin.ModelAdmin):
     
    list_display = ('id', 'db_key', 'db_help_category', 'db_lock_storage')
    list_display_links = ('id', 'db_key')
    search_fields = ['^db_key', 'db_entrytext']
    ordering = ['db_help_category', 'db_key']
    save_as = True 
    save_on_top = True   
    list_select_related = True 
    fieldsets = (
        (None, {'fields':(('db_key', 'db_help_category'), 'db_entrytext', 'db_lock_storage'),
                'description':"Sets a Help entry. Set lock to <i>view:all()</I> unless you want to restrict it."}),)


admin.site.register(HelpEntry, HelpEntryAdmin)
