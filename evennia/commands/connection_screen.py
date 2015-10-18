#
# This is Evennia's default connection screen. It is imported
# and run from server/conf/connection_screens.py.
#

from django.conf import settings
from evennia.utils import utils

DEFAULT_SCREEN = \
"""{b=============================================================={n
 Welcome to {g%s{n, version %s!

 If you have an existing account, connect to it by typing:
      {wconnect <username> <password>{n
 If you need to create an account, type (without the <>'s):
      {wcreate <username> <password>{n

 If you have spaces in your username, enclose it in quotes.
 Enter {whelp{n for more info. {wlook{n will re-show this screen.
{b=============================================================={n""" \
% (settings.SERVERNAME, utils.get_evennia_version())
