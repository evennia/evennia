"""
This sets up a few fields in the admin interface for connecting IRC channels
to evennia channels.
"""
from src.irc.models import IRCChannelMapping
from django.contrib import admin

class IRCChannelMappingAdmin(admin.ModelAdmin):
    list_display = ('channel', 'irc_server_name',
                    'irc_channel_name', 'is_enabled')
admin.site.register(IRCChannelMapping, IRCChannelMappingAdmin)
