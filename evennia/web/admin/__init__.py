"""
Django-admin code for customizing the web admin for Evennia.

"""

# importing here are necessary for Django to find these, since it will only
# look for `admin` in the web/ folder.

from .accounts import AccountAdmin
from .comms import ChannelAdmin, MsgAdmin
from .help import HelpEntryAdmin
from .objects import ObjectAdmin
from .scripts import ScriptAdmin
from .server import ServerConfigAdmin
from .tags import TagAdmin
