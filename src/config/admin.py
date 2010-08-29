#
# This sets up how models are displayed 
# in the web admin interface. 
#

from src.config.models import ConfigValue, ConnectScreen
from django.contrib import admin

class ConfigValueAdmin(admin.ModelAdmin):
    list_display = ('id', 'db_key')
    list_display_links = ("id", 'db_key')
    ordering = ['id', 'db_key']
    search_fields = ['db_key']
    save_as = True 
    save_on_top = True   
    list_select_related = True 
admin.site.register(ConfigValue, ConfigValueAdmin)

class ConnectScreenAdmin(admin.ModelAdmin):
    list_display = ('id', 'db_key', 'db_text', 'db_is_active')
    list_display_links = ('id', 'db_key')
    ordering = ['id', 'db_key']
    search_fields = ['^db_key']
    save_as = True 
    save_on_top = True
    list_select_related = True 
admin.site.register(ConnectScreen, ConnectScreenAdmin)
