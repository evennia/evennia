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
         ("builder", "Can build and modify objects"),
         ("chown_all", "Can @chown anything to anyone."),
         ("free_money", "Has infinite money"),
         ("long_fingers", "May get/look/examine etc. from a distance"),
         ("steal", "May give negative money"),
         ("set_hide", "May set themself invisible"),
         ("tel_anywhere", "May @teleport anywhere"),
         ("tel_anyone", "May @teleport anything"),
         ("see_session_data", "May see detailed player session data"),
         ("process_control", "May shutdown/restart/reload the game"),
         ("manage_players", "Can change passwords, siteban, etc."),
      )
