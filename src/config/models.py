from django.db import models
from django.contrib import admin
from src.config.managers.commandalias import CommandAliasManager
from src.config.managers.configvalue import ConfigValueManager
from src.config.managers.connectscreen import ConnectScreenManager

class CommandAlias(models.Model):
    """
    Command aliases. If the player enters the value equal to user_input, the
    command denoted by equiv_command is used instead.
    """
    user_input = models.CharField(max_length=50)
    equiv_command = models.CharField(max_length=50)
    
    objects = CommandAliasManager()
    
    class Admin:
        list_display = ('user_input', 'equiv_command',)
        
    class Meta:
        verbose_name_plural = "Command aliases"
        ordering = ['user_input']
admin.site.register(CommandAlias)

class ConfigValue(models.Model):
    """
    Experimental new config model.
    """
    conf_key = models.CharField(max_length=100)
    conf_value = models.TextField()
    
    objects = ConfigValueManager()
    
    class Admin:
        list_display = ('conf_key', 'conf_value',)
        
    def __str__(self):
        return "%s" % self.conf_key
admin.site.register(ConfigValue)
        
class ConnectScreen(models.Model):
    """
    Stores connect screens. The admins may have only one or multiple, which
    will cycle randomly.
    """
    name = models.CharField(max_length=255, help_text="An optional name for this screen (for organizational purposes).", blank=True)
    connect_screen_text = models.TextField(help_text="The text for the connect screen. Color codes and substitutions are evaluated.")
    is_active = models.BooleanField(default=1, help_text="Only active connect screens are placed in the rotation")
    
    objects = ConnectScreenManager()
    
    class Admin:
        list_display = ('id', 'name', 'is_active')
admin.site.register(ConnectScreen)