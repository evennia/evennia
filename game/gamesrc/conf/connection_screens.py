"""
 This module holds textual connection screen definitions.  All global
 string variables (only) in this module are read by Evennia and
 assumed to define a Connection screen.  

 The names of the string variables doesn't matter (except they
 shouldn't start with _), but each should hold a string defining a
 connection screen - as seen when first connecting to the game
 (before having logged in).

 OBS - If there are more than one string variable viable in this
 module, a random one is picked!

 After adding new connection screens to this module you must either
 reboot or reload the server to make them available.

You can change which module is used with
settings.CONNECTION_SCREEN_MODULE.

"""

from src.utils import utils 
from src.commands.connection_screen import DEFAULT_SCREEN

#
# CUSTOM_SCREEN = \
# """{b=============================================================={n
# Welcome to {gEvennia{n, version %s! 
#
# If you have an existing account, connect to it by typing:
#      {wconnect <email> <password>{n
# If you need to create an account, type (without the <>'s):
#      {wcreate \"<username>\" <email> <password>{n
#
# Enter {whelp{n for more info. {wlook{n will re-load this screen.
#{b=============================================================={n""" % utils.get_evennia_version()

# # A suggested alternative screen for the Menu login system

# MENU_SCREEN = \
# """{b=============================================================={n
#  Welcome to {gEvennnia{n, version %s! 
# {b=============================================================={n""" % utils.get_evennia_version()
