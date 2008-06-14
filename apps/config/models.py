from django.db import models

class CommandAlias(models.Model):
    """
    Command aliases. If the player enters the value equal to user_input, the
    command denoted by equiv_command is used instead.
    """
    user_input = models.CharField(max_length=50)
    equiv_command = models.CharField(max_length=50)
    
    class Admin:
        list_display = ('user_input', 'equiv_command',)
        
    class Meta:
        verbose_name_plural = "Command aliases"
        ordering = ['user_input']

class ConfigValue(models.Model):
    """
    Experimental new config model.
    """
    conf_key = models.CharField(max_length=100)
    conf_value = models.TextField()
    
    class Admin:
        list_display = ('conf_key', 'conf_value',)
        
class ConnectScreenManager(models.Manager):
    def get_random_connect_screen(self):
        """
        Returns a random active connect screen.
        """
        try:
            return self.filter(is_active=True).order_by('?')[0]
        except IndexError:
            new_screen = ConnectScreen(name='Default', 
                connect_screen_text='This is a placeholder connect screen. Remind your admin to edit it through the Admin interface.')
            new_screen.save()
            return new_screen
        
class ConnectScreen(models.Model):
    """
    Stores connect screens. The admins may have only one or multiple, which
    will cycle randomly.
    """
    name = models.CharField(max_length=255, help_text="An optional name for this screen (for organizational purposes).", blank=True)
    connect_screen_text = models.TextField(help_text="The text for the connect screen. Color codes and substitutions are evaluated.")
    is_active = models.BooleanField(default=1, help_text="Only active connect screens are placed in the rotation")
    
    # Custom manager
    objects = ConnectScreenManager()
    
    class Admin:
        list_display = ('id', 'name', 'is_active')
