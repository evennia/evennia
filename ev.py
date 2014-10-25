"""
Central API for the Evennia MUD/MUX/MU* creation system.

This is a set of shortcuts for accessing common features in src/ with
less boiler-plate. Import this from your code, use it with @py from
in-game or explore it interactively from a python shell.

Notes:

 0) Use ev.help, ev.managers.help, ev.default_cmds.help and
    syscmdkeys.help to view the API structure and explore which
    variables/methods are available.
 1) This module holds variables, not modules in their own right. This
    means you cannot use import dot-notation to import nested things via
    this API.
 2) "managers" is a container object that contains shortcuts to
    initiated versions of Evennia's django database managers (e.g.
    managers.objects is an alias for ObjectDB.objects). These allow for
    exploring the database in various ways.
 3) "syscmdkeys" is a container object holding the names of system
    commands.  the syscmdkeys object.
 4) You -have- to use the create_* functions (shortcuts to
    src.utils.create) to create new typeclassed game entities (Objects,
    Scripts, Channels or Players).
 5) "settings" links to Evennia's game/settings file. "settings_full"
    shows all of django's available settings. Note that this is for
    viewing only - you cannot *change* settings from here in a meaningful
    way but have to update game/settings.py and restart the server.
"""

import sys
import os

######################################################################
# set Evennia version in __version__ property
######################################################################

try:
    __version__ = "Evennia"
    with open(os.path.dirname(os.path.abspath(__file__)) + os.sep + "VERSION.txt", 'r') as f:
        __version__ += " %s" % f.read().strip()
    rev = (os.popen("git rev-parse --short HEAD").read().strip())
    __version__ += "-%s" % (rev or "(unknown revision)")
except IOError:
    __version__ += " (unknown version)"

######################################################################
# Stop erroneous direct run (would give a traceback since django is
#  not yet initialized)
######################################################################

if __name__ == "__main__":
    print \
"""
   Evennia MU* creation system (%s)

   This module gives access to Evennia's API (Application Programming
   Interface). It should *not* be run on its own, but be imported and
   accessed from your code or explored interactively from a Python
   shell.

   For help configuring and starting the Evennia server, see the
   INSTALL file. More help can be found at http://www.evennia.com.
""" % __version__
    sys.exit()

######################################################################
# make sure settings is available, also if starting this API stand-alone
# make settings available, and also the full django settings
######################################################################

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)) + os.path.sep + "game")
os.environ["DJANGO_SETTINGS_MODULE"] = "game.settings"
del sys, os

from game import settings
from django.conf import settings as settings_full

try:
    # test this first import to make sure environment is set up correctly
    from src.help.models import HelpEntry
except AttributeError, e:
    err = e.message
    err += "\nError initializing ev.py: Maybe the correct environment variables were not set."
    err += "\nUse \"python game/manage.py shell\" to start an interpreter"
    err += " with everything configured correctly."
    raise AttributeError(err)


######################################################################
# Start Evennia API
# (easiest is to import this module interactively to explore it)
######################################################################

README = __doc__

# help entries
from src.help.models import HelpEntry

from src.typeclasses.models import Attribute
# players
from src.players.player import Player
from src.players.models import PlayerDB

# commands
from src.commands.command import Command
from src.commands.cmdset import CmdSet
# (default_cmds is created below)

# locks
from src.locks import lockfuncs

# scripts
from src.scripts.scripts import Script

# comms
from src.comms.models import Msg, ChannelDB
from src.comms.comms import Channel

# objects
from src.objects.objects import Object, Character, Room, Exit

# utils

from src.utils.search import *
from src.utils.create import *
from src.scripts.tickerhandler import TICKER_HANDLER as tickerhandler
from src.utils import logger
from src.utils import utils
from src.utils import gametime
from src.utils import ansi
from src.utils.spawner import spawn


######################################################################
# API containers and helper functions
######################################################################

def help(header=False):
    """
    Main Evennia API.
       ev.help() views API contents
       ev.help(True) or ev.README shows module instructions

       See www.evennia.com for the full documentation.
    """
    if header:
        return __doc__
    else:
        import ev
        names = [str(var) for var in ev.__dict__ if not var.startswith('_')]
        return ", ".join(names)


class _EvContainer(object):
    """
    Parent for other containers

    """
    def _help(self):
        "Returns list of contents"
        names = [name for name in self.__class__.__dict__ if not name.startswith('_')]
        names += [name for name in self.__dict__ if not name.startswith('_')]
        print self.__doc__ + "-" * 60 + "\n" + ", ".join(names)
    help = property(_help)


class DBmanagers(_EvContainer):
    """
    Links to instantiated database managers.

    helpentry - HelpEntry.objects
    players - PlayerDB.objects
    scripts - ScriptDB.objects
    msgs    - Msg.objects
    channels - Channel.objects
    objects - ObjectDB.objects
    serverconfigs = ServerConfig.objects
    tags - Tags.objects
    attributes - Attributes.objects

    """
    from src.help.models import HelpEntry
    from src.players.models import PlayerDB
    from src.scripts.models import ScriptDB
    from src.comms.models import Msg, ChannelDB
    from src.objects.models import ObjectDB
    from src.server.models import ServerConfig
    from src.typeclasses.models import Tag, Attribute

    # create container's properties
    helpentries = HelpEntry.objects
    players = PlayerDB.objects
    scripts = ScriptDB.objects
    msgs = Msg.objects
    channels = ChannelDB.objects
    objects = ObjectDB.objects
    serverconfigs = ServerConfig.objects
    attributes = Attribute.objects
    tags = Tag.objects
    # remove these so they are not visible as properties
    del HelpEntry, PlayerDB, ScriptDB, Msg, ChannelDB
    #del ExternalChannelConnection
    del ObjectDB, ServerConfig, Tag, Attribute

managers = DBmanagers()
del DBmanagers


class DefaultCmds(_EvContainer):
    """
    This container holds direct shortcuts to all default commands in Evennia.

    To access in code, do 'from ev import default_cmds' then
    access the properties on the imported default_cmds object.

    """

    from src.commands.default.cmdset_character import CharacterCmdSet
    from src.commands.default.cmdset_player import PlayerCmdSet
    from src.commands.default.cmdset_unloggedin import UnloggedinCmdSet
    from src.commands.default.muxcommand import MuxCommand, MuxPlayerCommand

    def __init__(self):
        "populate the object with commands"

        def add_cmds(module):
            "helper method for populating this object with cmds"
            cmdlist = utils.variable_from_module(module, module.__all__)
            self.__dict__.update(dict([(c.__name__, c) for c in cmdlist]))

        from src.commands.default import (admin, batchprocess,
                                          building, comms, general,
                                          player, help, system, unloggedin)
        add_cmds(admin)
        add_cmds(building)
        add_cmds(batchprocess)
        add_cmds(building)
        add_cmds(comms)
        add_cmds(general)
        add_cmds(player)
        add_cmds(help)
        add_cmds(system)
        add_cmds(unloggedin)
default_cmds = DefaultCmds()
del DefaultCmds


class SystemCmds(_EvContainer):
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

    To access in code, do 'from ev import syscmdkeys' then
    access the properties on the imported syscmdkeys object.

    """
    from src.commands import cmdhandler
    CMD_NOINPUT = cmdhandler.CMD_NOINPUT
    CMD_NOMATCH = cmdhandler.CMD_NOMATCH
    CMD_MULTIMATCH = cmdhandler.CMD_MULTIMATCH
    CMD_CHANNEL = cmdhandler.CMD_CHANNEL
    CMD_LOGINSTART = cmdhandler.CMD_LOGINSTART
    del cmdhandler
syscmdkeys = SystemCmds()
del SystemCmds
del _EvContainer
