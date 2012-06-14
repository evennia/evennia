#
# This sets up how models are displayed
# in the web admin interface.
#

from django.contrib import admin
from src.comms.models import Channel, Msg, PlayerChannelConnection, ExternalChannelConnection

class MsgAdmin(admin.ModelAdmin):
    list_display = ('id', 'db_date_sent', 'db_sender', 'db_receivers', 'db_channels', 'db_message', 'db_lock_storage')
    list_display_links = ("id",)
    ordering = ["db_date_sent", 'db_sender', 'db_receivers', 'db_channels']
    #readonly_fields = ['db_message', 'db_sender', 'db_receivers', 'db_channels']
    search_fields = ['id', '^db_date_sent', '^db_message']
    save_as = True
    save_on_top = True
    list_select_related = True
#admin.site.register(Msg, MsgAdmin)

class PlayerChannelConnectionInline(admin.TabularInline):
    model = PlayerChannelConnection
    fieldsets = (
        (None, {
                'fields':(('db_player', 'db_channel')),
                'classes':('collapse',)}),)
    extra = 1

class ExternalChannelConnectionInline(admin.StackedInline):
    model = ExternalChannelConnection
    fieldsets = (
        (None, {
                'fields':(('db_is_enabled','db_external_key', 'db_channel'), 'db_external_send_code', 'db_external_config'),
                'classes':('collapse',)
                }),)
    extra = 1

class ChannelAdmin(admin.ModelAdmin):
    inlines = (PlayerChannelConnectionInline, ExternalChannelConnectionInline)

    list_display = ('id', 'db_key', 'db_desc', 'db_aliases', 'db_keep_log', 'db_lock_storage')
    list_display_links = ("id", 'db_key')
    ordering = ["db_key"]
    search_fields = ['id', 'db_key', 'db_aliases']
    save_as = True
    save_on_top = True
    list_select_related = True
    fieldsets = (
        (None, {'fields':(('db_key', 'db_aliases', 'db_desc'),'db_lock_storage', 'db_keep_log')}),
        )

admin.site.register(Channel, ChannelAdmin)

# class PlayerChannelConnectionAdmin(admin.ModelAdmin):
#     list_display = ('db_channel', 'db_player')
#     list_display_links = ("db_player", 'db_channel')
#     ordering = ["db_channel"]
#     search_fields = ['db_channel', 'db_player']
#     save_as = True
#     save_on_top = True
#     list_select_related = True
# admin.site.register(PlayerChannelConnection, PlayerChannelConnectionAdmin)

# class ExternalChannelConnectionAdmin(admin.ModelAdmin):
#     list_display = ('db_channel', 'db_external_key', 'db_external_config')
#     list_display_links = ("db_channel", 'db_external_key', 'db_external_config')
#     ordering = ["db_channel"]
#     search_fields = ['db_channel', 'db_external_key']
#     save_as = True
#     save_on_top = True
#     list_select_related = True
# admin.site.register(ExternalChannelConnection, ExternalChannelConnectionAdmin)

