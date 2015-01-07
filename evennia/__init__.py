"""
Evennia MUD/MUX/MU* creation system
"""

######################################################################
# set Evennia version in __version__ property
######################################################################
import os
try:
    __version__ = "Evennia"
    with os.path.join(open(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "VERSION.txt", 'r') as f:
        __version__ += " %s" % f.read().strip()
except IOError:
    __version__ += " (unknown version)"

del os

######################################################################
# Start Evennia API
# (easiest is to import this module interactively to explore it)
######################################################################

# help entries
from help.models import HelpEntry

# players
from players.player import DefaultPlayer
from players.models import PlayerDB

# commands
from commands.command import Command
from commands.cmdset import CmdSet
# (default_cmds is created below)

# locks
from locks import lockfuncs

# scripts
from scripts.scripts import Script

# comms
from comms.models import Msg, ChannelDB
from comms.comms import Channel

# objects
from objects.objects import DefaultObject, DefaultCharacter, DefaultRoom, DefaultExit

# utils

from utils.search import *
from utils.create import *
from scripts.tickerhandler import TICKER_HANDLER as tickerhandler
from utils import logger
from utils import utils
from utils import gametime
from utils import ansi
from utils.spawner import spawn

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
    from help.models import HelpEntry
    from players.models import PlayerDB
    from scripts.models import ScriptDB
    from comms.models import Msg, ChannelDB
    from objects.models import ObjectDB
    from server.models import ServerConfig
    from typeclasses.attributes import Attribute
    from typeclasses.tags import Tag

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

    from commands.default.cmdset_character import CharacterCmdSet
    from commands.default.cmdset_player import PlayerCmdSet
    from commands.default.cmdset_unloggedin import UnloggedinCmdSet
    from commands.default.muxcommand import MuxCommand, MuxPlayerCommand

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

