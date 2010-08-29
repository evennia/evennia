#
# This sets up how models are displayed 
# in the web admin interface. 
#

from django.contrib import admin
from src.comms.models import Channel, Msg, ChannelConnection

class MsgAdmin(admin.ModelAdmin):
    list_display = ('id', 'db_date_sent', 'db_sender', 'db_receivers', 'db_channels', 'db_message')    
    list_display_links = ("id",)
    ordering = ["db_date_sent", 'db_sender', 'db_receivers', 'db_channels']
    readonly_fields = ['db_permissions', 'db_message', 'db_sender', 'db_receivers', 'db_channels']
    search_fields = ['id', '^db_date_sent', '^db_message']
    save_as = True 
    save_on_top = True   
    list_select_related = True 
admin.site.register(Msg, MsgAdmin)

class ChannelAdmin(admin.ModelAdmin):
    list_display = ('id', 'db_key', 'db_desc', 'db_aliases', 'db_keep_log', 'db_permissions')
    list_display_links = ("id", 'db_key')
    ordering = ["db_key"]
    readonly_fields = ['db_permissions']
    search_fields = ['id', 'db_key', 'db_aliases']
    save_as = True 
    save_on_top = True   
    list_select_related = True 
admin.site.register(Channel, ChannelAdmin)

class ChannelConnectionAdmin(admin.ModelAdmin):
    list_display = ('db_channel', 'db_player')
    list_display_links = ("db_player", 'db_channel')
    ordering = ["db_channel"]
    search_fields = ['db_channel', 'db_player']
    save_as = True 
    save_on_top = True   
    list_select_related = True 
admin.site.register(ChannelConnection, ChannelConnectionAdmin)

