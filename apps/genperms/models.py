from django.db import models

class GenericPerm(models.Model):
   """
   This is merely a container class for some generic permissions that don't
   fit under a particular module.
   """
   class Meta:
      permissions = (
         ("announce", "May use @wall to make announcements"),
         ("boot", "May use @boot to kick players"),
         ("builder", "May build"),
         ("chown_all", "Can @chown anything to anyone."),
         ("control_all", "May control everything"),
         ("examine_all", "Can examine any object"),
         ("extended_who", "May see extended WHO list"),
         ("free_money", "Has infinite money"),
         ("long_fingers", "May get/look/examine etc. from a distance"),
         ("steal", "May give negative money"),
         ("set_hide", "May set themself invisible"),
         ("shutdown", "May @shutdown the site"),
         ("tel_anywhere", "May @teleport anywhere"),
         ("tel_anyone", "May @teleport anything"),
      )
