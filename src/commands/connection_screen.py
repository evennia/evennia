#
# This is Evennia's default connection screen. It is imported
# and run from game/gamesrc/world/connection_screens.py.
#

from src.utils import utils

DEFAULT_SCREEN = \
"""{b=============================================================={n
 Welcome to {gEvennia{n, version %s!

 If you have an existing account, connect to it by typing:
      {wconnect <username> <password>{n
 If you need to create an account, type (without the <>'s):
      {wcreate <username> <password>{n

 If you have spaces in your username, enclose it in quotes.
 Enter {whelp{n for more info. {wlook{n will re-show this screen.
{b=============================================================={n""" % utils.get_evennia_version()
