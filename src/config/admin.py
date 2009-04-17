from src.config.models import CommandAlias, ConfigValue, ConnectScreen
from django.contrib import admin

class CommandAliasAdmin(admin.ModelAdmin):
    list_display = ('user_input', 'equiv_command')
admin.site.register(CommandAlias, CommandAliasAdmin)

class ConfigValueAdmin(admin.ModelAdmin):
    list_display = ('conf_key', 'conf_value')
admin.site.register(ConfigValue, ConfigValueAdmin)

class ConnectScreenAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active')
    list_display_links = ('id', 'name')
admin.site.register(ConnectScreen, ConnectScreenAdmin)