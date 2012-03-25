"""

Central API for Evennia MUD/MUX/MU* system.

This basically a set of shortcuts to the main modules in src/. 
Import this from ./manage.py shell or set DJANGO_SETTINGS_MODULE manually for proper
functionality.

 1) You should import things explicitly from the root of this module - you can generally 
    not use dot-notation to import deeper. Hence, to access a default command, you can do
    the following: 

       import ev
       ev.default_cmds.CmdLook
    or 
       from ev import default_cmds
       default_cmds.CmdLook
   
    But trying to import CmdLook directly with "from ev.default_cmds import CmdLook" will 
    not work since default_cmds is a property on the "ev" module, not a module of its own. 
 2) db_* are shortcuts to initiated versions of Evennia's django database managers (e.g.
    db_objects is an alias for ObjectDB.objects). These allows for exploring the database in 
    various ways. Please note that the evennia-specific methods in the managers return 
    typeclasses (or lists of typeclasses), whereas the default django ones (filter etc) 
    return database objects. You can convert between the two easily via dbobj.typeclass and 
    typeclass.dbobj, but it's worth to remember this difference.  
 3) You -have- to use the methods of the "create" module to create new Typeclassed game
    entities (Objects, Scripts or Players). Just initializing e.g. the Player class will 
    -not- set up Typeclasses correctly and will lead to errors. Other types of database objects 
    can be created normally, but the "create" module offers convenient methods for those too. 
 4) The API accesses all relevant methods/classes, but might not always include all helper-methods
    referenced from each such entity. To get to those, access the modules in src/ directly. You
    can always do this anyway, if you do not want to go through this API. 

"""

import sys, os

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
    sys.exit()
try:
    f = open(os.path.dirname(os.path.abspath(__file__)) + os.sep + "VERSION", 'r')
    __version__ = "Evennia %s-r%s" % (f.read().strip(), os.popen("hg id -i").read().strip())
    f.close()
    del f
except IOError:
    __version__ = "Evennia (unknown version)"
del sys, os

# Start Evennia API (easiest is to import this module interactively to explore it)

README = "Evennia flat API. See the module header for usage information."

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

class SystemCmds(object):
    """
    Creating commands with keys set to these constants will make
    them system commands called as a replacement by the parser when 
    special situations occur. If not defined, the hard-coded 
    responses in the server are used.

    CMD_NOINPUT - no input was given on command line
    CMD_NOMATCH - no valid command key was found
    CMD_MULTIMATCH - multiple command matches were found
    CMD_CHANNEL - the command name is a channel name
    CMD_LOGINSTART - this command will be called as the very
                     first command when a player connects to
                     the server. 

    """
    from src.commands import cmdhandler
    CMD_NOINPUT = cmdhandler.CMD_NOINPUT
    CMD_NOMATCH = cmdhandler.CMD_NOMATCH
    CMD_MULTIMATCH = cmdhandler.CMD_MULTIMATCH
    CMD_CHANNEL = cmdhandler.CMD_CHANNEL
    CMD_LOGINSTART = cmdhandler.CMD_LOGINSTART
    del cmdhandler 
syscmdkeys = SystemCmds()

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

from src.utils.search import *
from src.utils.create import *
from src.utils import logger
from src.utils import utils
from src.utils import gametime
from src.utils import ansi
