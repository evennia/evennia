"""

Central API for Evennia MUD/MUX/MU* system.

A simple way to explore Evennia's capabilities is to 
import it in a python interpreter where all environment
variables have been set. Easiest is to do the following: 

game/manage.py shell 
>>> import ev 

Using ipython is recommended since you will then have tab-completion
and the ability to view docstrings much easier than with the regular
python interpreter. 

In code, just import via ev.<item>

Philosophy is to keep the API as flat as possible, so as to not have
to remember which nested packages to traverse. Most of the important
stuff should be made visible from this module.

One can of course still import from src/ directly should one prefer!

"""

# Stop erroneous direct run (would give a traceback since django is
#  not yet initialized)

if __name__ == "__main__":
    print \
"""
    This module gives access to Evennia's programming API. 
    It should not be run on its own, but be imported and accessed as you develop your game.
    To start the server, see game/manage.py and game/evennia.py. 
    More help can be found at http://www.evennia.com. 
"""
    import sys
    sys.exit()


# Start Evennia API (easiest is to import this module interactively to explore it)

# help entries 
from src.help.models import HelpEntry
db_helpentries = HelpEntry.objects

# players 
from src.players.player import Player
from src.players.models import PlayerDB, PlayerAttribute, PlayerNick
db_players = PlayerDB.objects
db_playerattrs = PlayerAttribute.objects
db_playernicks = PlayerNick.objects
del PlayerDB, PlayerAttribute, PlayerNick

# commands
from src.commands.command import Command
from src.commands.cmdset import CmdSet
from src.commands import default as default_cmds

# locks
from src.locks import lockfuncs

# scripts 
from src.scripts.scripts import Script
from src.scripts.models import ScriptDB, ScriptAttribute
db_scripts = ScriptDB.objects
db_scriptattrs = ScriptAttribute.objects
del ScriptDB, ScriptAttribute

# comms
from src.comms.models import Msg, Channel, PlayerChannelConnection, ExternalChannelConnection
db_msgs = Msg.objects
db_channels = Channel.objects
db_connections = PlayerChannelConnection.objects
db_externalconnections = ExternalChannelConnection.objects

# objects
from src.objects.objects import Object, Character, Room, Exit
from src.objects.models import ObjAttribute, Alias, ObjectNick, ObjectDB
db_objects = ObjectDB.objects
db_aliases = Alias.objects
db_objnicks = ObjectNick.objects
db_objattrs = ObjAttribute.objects
del ObjAttribute, Alias, ObjectNick, ObjectDB

# server 
from src.server.models import ServerConfig
db_serverconfs = ServerConfig.objects
del ServerConfig

# utils
from src.utils import search
from src.utils import logger
from src.utils import create
from src.utils import utils

