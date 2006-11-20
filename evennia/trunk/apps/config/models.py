from django.db import models

class CommandAlias(models.Model):
   """
   Command aliases.
   """
   user_input = models.CharField(maxlength=50)
   equiv_command = models.CharField(maxlength=50)
   
   class Admin:
      list_display = ('user_input', 'equiv_command',)

class Config(models.Model):
   """
   Although we technically have the ability to create more than one Config
   object via the admin interface, we only really need one. This also leaves
   the possibility for multiple games hosted on the same codebase or database
   in the future, although this is not a priority. In any case, this model
   contains most of the game-specific configuration.
   """
   site_name = models.CharField(maxlength=100)
   site_description = models.TextField(blank=True)
   site_website = models.URLField(blank=True)
   player_start_dbnum = models.IntegerField()

   class Admin:
      list_display = ('site_name', 'site_website',)
