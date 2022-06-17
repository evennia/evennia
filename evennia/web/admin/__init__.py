"""
Django-admin code for customizing the web admin for Evennia.

"""

# importing here are necessary for Django to find these, since it will only
# look for `admin` in the web/ folder.

from .accounts import AccountAdmin
from .objects import ObjectAdmin
from .scripts import ScriptAdmin
from .comms import ChannelAdmin, MsgAdmin
from .help import HelpEntryAdmin
from .tags import TagAdmin
from .server import ServerConfigAdmin
