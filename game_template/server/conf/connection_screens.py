# -*- coding: utf-8 -*-
"""
Connect screen module template

Copy this module one level up, to gamesrc/conf/, name it what
you want and modify it to your liking.

Then you set settings.CONNECTION_SCREEN_MODULE to point to your
new module.


 This module holds textual connection screen definitions. All global
 string variables (only) in this module are read by Evennia and
 assumed to define a Connection screen.

 The names of the string variables doesn't matter (but names starting
 with an underscore will be ignored), but each should hold a string
 defining a connection screen - as seen when first connecting to the
 game (before having logged in).

 OBS - If there are more than one global string variable in this
 module, a random one is picked!

 After adding new connection screens to this module you must either
 reboot or reload the server to make them available.

"""

# comment this out if wanting to completely remove the default screen
from src.commands.connection_screen import DEFAULT_SCREEN

## uncomment these for showing the name and version
# from django.conf import settings
# from src.utils import utils

## A copy of the default screen to modify

# CUSTOM_SCREEN = \
#"""{b=============================================================={n
# Welcome to {g%s{n, version %s!
#
# If you have an existing account, connect to it by typing:
#      {wconnect <username> <password>{n
# If you need to create an account, type (without the <>'s):
#      {wcreate <username> <password>{n
#
# If you have spaces in your username, enclose it in quotes.
# Enter {whelp{n for more info. {wlook{n will re-show this screen.
#{b=============================================================={n""" \
# % (settings.SERVERNAME, utils.get_evennia_version())

## Minimal header for use with contrib/menu_login.py

# MENU_SCREEN = \
# """{b=============================================================={n
#  Welcome to {g%s{n, version %s!
# {b=============================================================={n""" \
# % (settings.SERVERNAME, utils.get_evennia_version())
