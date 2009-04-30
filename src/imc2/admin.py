from src.imc2.models import IMC2ChannelMapping
from django.contrib import admin

class IMC2ChannelMappingAdmin(admin.ModelAdmin):
    list_display = ('channel', 'imc2_server_name',
                    'imc2_channel_name', 'is_enabled')
admin.site.register(IMC2ChannelMapping, IMC2ChannelMappingAdmin)