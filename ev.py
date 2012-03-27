"""

Central API for the Evennia MUD/MUX/MU* creation system.

This basically a set of shortcuts to the main modules in src/. Import this 
from your code or explore it interactively from ./manage.py shell (or a normal 
python shell if you set DJANGO_SETTINGS_MODULE manually).

Notes: 

 1) You should import things explicitly from the root of this module - you can not use 
    dot-notation to import deeper. Hence, to access a default command, you can do the 
    following:

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
 3) You -have- to use the create_* functions (shortcuts to src.utils.create) to create new 
    Typeclassed game entities (Objects, Scripts or Players). Just initializing e.g. the Player class will 
    -not- set up Typeclasses correctly and will lead to errors. Other types of database objects 
    can be created normally, but there are conveniant create_* functions for those too, making
    some more error checking. 
 4) "settings" links to Evennia's game/settings file. "settings_full" shows all of django's available
    settings. Note that you cannot change settings from here in a meaningful way, you need to update 
    game/settings.py and restart the server.
 5) The API accesses all relevant and most-neeeded functions/classes from src/, but might not 
    always include all helper-functions referenced from each such entity. To get to those, access 
    the modules in src/ directly. You can always do this anyway, if you do not want to go through 
    this API. 

"""

import sys, os

# Stop erroneous direct run (would give a traceback since django is
#  not yet initialized)

if __name__ == "__main__":
    info = __doc__ + \
"""
  | This module gives access to Evennia's programming API.  It should
  | not be run on its own, but be imported and accessed as described
  | above.
  |
  | To start the Evennia server, see game/manage.py and game/evennia.py.  
  | More help can be found at http://www.evennia.com.
"""
    print info
    sys.exit()

# make sure settings is available, also if starting this API stand-alone
# make settings available, and also the full django settings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from django.core.management import setup_environ
from game import settings
setup_environ(settings)
del setup_environ
from django.conf import settings as settings_full

# set Evennia version in __version__ property

try:
    f = open(os.path.dirname(os.path.abspath(__file__)) + os.sep + "VERSION", 'r')
    __version__ = "Evennia %s-r%s" % (f.read().strip(), os.popen("hg id -i").read().strip())
    f.close()
    del f
except IOError:
    __version__ = "Evennia (unknown version)"
del sys, os

#
# Start Evennia API (easiest is to import this module interactively to explore it)
#

README = __doc__

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
db_serverconfigs = ServerConfig.objects
del ServerConfig

# utils

from src.utils.search import *
from src.utils.create import *
from src.utils import logger
from src.utils import utils
from src.utils import gametime
from src.utils import ansi
