"""
Evennia MUD/MUX/MU* creation system

This is the main top-level API for Evennia. You can also explore the
evennia library by accessing evennia.<subpackage> directly.

For full functionality you need to explore this module via a django-
aware shell. Go to your game directory and use the command 'evennia.py shell'
to launch such a shell (using python or ipython depending on your install).

See www.evennia.com for full documentation.

"""

# Delayed loading of properties

# Typeclasses

DefaultPlayer = None
DefaultGuest = None
DefaultObject = None
DefaultCharacter = None
DefaultRoom = None
DefaultExit = None
DefaultChannel = None
Script = None

# Database models
ObjectDB = None
PlayerDB = None
ScriptDB = None
ChannelDB = None
Msg = None

# commands
Command = None
CmdSet = None
default_cmds = None
syscmdkeys = None

# search functions
search_object = None
search_script = None
search_player = None
search_channel = None
search_help = None

# create functions
create_object = None
create_script = None
create_player = None
create_channel = None
create_message = None

# utilities
lockfuncs = None
tickerhandler = None
logger = None
gametime = None
ansi = None
spawn = None
managers = None

import os
from subprocess import check_output, CalledProcessError, STDOUT

__version__ = "Unknown"

root = os.path.dirname(os.path.abspath(__file__))
try:
    with open(os.path.join(root, "VERSION.txt"), 'r') as f:
        __version__ = f.read().strip()
except IOError as err:
    print err
try:
    __version__ = "%s" % (check_output("git rev-parse --short HEAD", shell=True, cwd=root, stderr=STDOUT).strip())
except (IOError, CalledProcessError):
    pass


def init():
    """
    This is called only after Evennia has fully initialized all its models.
    """
    def imp(path, variable=True):
        "Helper function"
        mod, fromlist = path, "None"
        if variable:
            mod, fromlist = path.rsplit('.', 1)
        return __import__(mod, fromlist=[fromlist])

    global DefaultPlayer, DefaultObject, DefaultGuest, DefaultCharacter, \
           DefaultRoom, DefaultExit, DefaultChannel, Script
    global ObjectDB, PlayerDB, ScriptDB, ChannelDB, Msg
    global Command, CmdSet, default_cmds, syscmdkeys
    global search_object, search_script, search_player, search_channel, search_help
    global create_object, create_script, create_player, create_channel, create_message
    global lockfuncs, tickerhandler, logger, utils, gametime, ansi, spawn, managers

    from players.players import DefaultPlayer
    from players.players import DefaultGuest
    from objects.objects import DefaultObject
    from objects.objects import DefaultCharacter
    from objects.objects import DefaultRoom
    from objects.objects import DefaultExit
    from comms.comms import DefaultChannel
    from scripts.scripts import Script

    # Database models
    from objects.models import ObjectDB
    from players.models import PlayerDB
    from scripts.models import ScriptDB
    from comms.models import ChannelDB
    from comms.models import Msg

    # commands
    from commands.command import Command
    from commands.cmdset import CmdSet

    # search functions
    from utils.search import search_object
    from utils.search import search_script
    from utils.search import search_player
    from utils.search import search_channel
    from utils.search import search_help

    # create functions
    from utils.create import create_object
    from utils.create import create_script
    from utils.create import create_player
    from utils.create import create_channel
    from utils.create import create_message

    # utilities
    from locks import lockfuncs
    from scripts.tickerhandler import TICKER_HANDLER as tickerhandler
    from utils import logger
    from utils import gametime
    from utils import ansi
    from utils.spawner import spawn

    # API containers

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

        To access in code, do 'from evennia import default_cmds' then
        access the properties on the imported default_cmds object.

        """

        from commands.default.cmdset_character import CharacterCmdSet
        from commands.default.cmdset_player import PlayerCmdSet
        from commands.default.cmdset_unloggedin import UnloggedinCmdSet
        from commands.default.cmdset_session import SessionCmdSet
        from commands.default.muxcommand import MuxCommand, MuxPlayerCommand

        def __init__(self):
            "populate the object with commands"

            def add_cmds(module):
                "helper method for populating this object with cmds"
                cmdlist = utils.variable_from_module(module, module.__all__)
                self.__dict__.update(dict([(c.__name__, c) for c in cmdlist]))

            from commands.default import (admin, batchprocess,
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

        To access in code, do 'from evennia import syscmdkeys' then
        access the properties on the imported syscmdkeys object.

        """
        from commands import cmdhandler
        CMD_NOINPUT = cmdhandler.CMD_NOINPUT
        CMD_NOMATCH = cmdhandler.CMD_NOMATCH
        CMD_MULTIMATCH = cmdhandler.CMD_MULTIMATCH
        CMD_CHANNEL = cmdhandler.CMD_CHANNEL
        CMD_LOGINSTART = cmdhandler.CMD_LOGINSTART
        del cmdhandler
    syscmdkeys = SystemCmds()
    del SystemCmds
    del _EvContainer
