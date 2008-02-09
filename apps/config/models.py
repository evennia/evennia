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
