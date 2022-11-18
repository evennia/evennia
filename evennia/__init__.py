"""
Evennia MUD/MUX/MU* creation system

This is the main top-level API for Evennia. You can explore the evennia library
by accessing evennia.<subpackage> directly. From inside the game you can read
docs of all object by viewing its `__doc__` string, such as through

    py evennia.ObjectDB.__doc__

For full functionality you should explore this module via a django-
aware shell. Go to your game directory and use the command

   evennia shell

to launch such a shell (using python or ipython depending on your install).
See www.evennia.com for full documentation.

"""

# docstring header

DOCSTRING = """
Evennia MU* creation system.

Online manual and API docs are found at http://www.evennia.com.

Flat-API shortcut names:
{}
"""

# Delayed loading of properties

# Typeclasses

DefaultAccount = None
DefaultGuest = None
DefaultObject = None
DefaultCharacter = None
DefaultRoom = None
DefaultExit = None
DefaultChannel = None
DefaultScript = None

# Database models
ObjectDB = None
AccountDB = None
ScriptDB = None
ChannelDB = None
Msg = None

# Properties
AttributeProperty = None
TagProperty = None

# commands
Command = None
CmdSet = None
default_cmds = None
syscmdkeys = None
InterruptCommand = None

# search functions
search_object = None
search_script = None
search_account = None
search_channel = None
search_message = None
search_help = None
search_tag = None

# create functions
create_object = None
create_script = None
create_account = None
create_channel = None
create_message = None
create_help_entry = None

# utilities
settings = None
lockfuncs = None
inputhandler = None
logger = None
gametime = None
ansi = None
spawn = None
managers = None
contrib = None
EvMenu = None
EvTable = None
EvForm = None
EvEditor = None
EvMore = None
ANSIString = None
signals = None

# Handlers
SESSION_HANDLER = None
TASK_HANDLER = None
TICKER_HANDLER = None
MONITOR_HANDLER = None

# Containers
GLOBAL_SCRIPTS = None
OPTION_CLASSES = None


def _create_version():
    """
    Helper function for building the version string
    """
    import os
    from subprocess import STDOUT, CalledProcessError, check_output

    version = "Unknown"
    root = os.path.dirname(os.path.abspath(__file__))
    try:
        with open(os.path.join(root, "VERSION.txt"), "r") as f:
            version = f.read().strip()
    except IOError as err:
        print(err)
    try:
        rev = (
            check_output("git rev-parse --short HEAD", shell=True, cwd=root, stderr=STDOUT)
            .strip()
            .decode()
        )
        version = "%s (rev %s)" % (version, rev)
    except (IOError, CalledProcessError, OSError):
        # ignore if we cannot get to git
        pass
    return version


__version__ = _create_version()
del _create_version


def _init():
    """
    This function is called automatically by the launcher only after
    Evennia has fully initialized all its models. It sets up the API
    in a safe environment where all models are available already.
    """
    global DefaultAccount, DefaultObject, DefaultGuest, DefaultCharacter
    global DefaultRoom, DefaultExit, DefaultChannel, DefaultScript
    global ObjectDB, AccountDB, ScriptDB, ChannelDB, Msg
    global Command, CmdSet, default_cmds, syscmdkeys, InterruptCommand
    global search_object, search_script, search_account, search_channel
    global search_help, search_tag, search_message
    global create_object, create_script, create_account, create_channel
    global create_message, create_help_entry
    global signals
    global settings, lockfuncs, logger, utils, gametime, ansi, spawn, managers
    global contrib, TICKER_HANDLER, MONITOR_HANDLER, SESSION_HANDLER
    global TASK_HANDLER
    global GLOBAL_SCRIPTS, OPTION_CLASSES
    global EvMenu, EvTable, EvForm, EvMore, EvEditor
    global ANSIString
    global AttributeProperty, TagProperty

    # Parent typeclasses
    # utilities
    from django.conf import settings

    from . import contrib
    from .accounts.accounts import DefaultAccount, DefaultGuest
    from .accounts.models import AccountDB
    from .commands.cmdset import CmdSet
    from .commands.command import Command, InterruptCommand
    from .comms.comms import DefaultChannel
    from .comms.models import ChannelDB, Msg
    from .locks import lockfuncs
    from .objects.models import ObjectDB
    from .objects.objects import (
        DefaultCharacter,
        DefaultExit,
        DefaultObject,
        DefaultRoom,
    )
    from .prototypes.spawner import spawn
    from .scripts.models import ScriptDB
    from .scripts.monitorhandler import MONITOR_HANDLER
    from .scripts.scripts import DefaultScript
    from .scripts.taskhandler import TASK_HANDLER
    from .scripts.tickerhandler import TICKER_HANDLER
    from .server import signals
    from .server.sessionhandler import SESSION_HANDLER
    from .typeclasses.attributes import AttributeProperty
    from .typeclasses.tags import TagProperty
    from .utils import ansi, gametime, logger
    from .utils.ansi import ANSIString

    # containers
    from .utils.containers import GLOBAL_SCRIPTS, OPTION_CLASSES

    # create functions
    from .utils.create import (
        create_account,
        create_channel,
        create_help_entry,
        create_message,
        create_object,
        create_script,
    )
    from .utils.eveditor import EvEditor
    from .utils.evform import EvForm
    from .utils.evmenu import EvMenu
    from .utils.evmore import EvMore
    from .utils.evtable import EvTable

    # search functions
    from .utils.search import (
        search_account,
        search_channel,
        search_help,
        search_message,
        search_object,
        search_script,
        search_tag,
    )

    # API containers

    class _EvContainer(object):
        """
        Parent for other containers

        """

        def _help(self):
            "Returns list of contents"
            names = [name for name in self.__class__.__dict__ if not name.startswith("_")]
            names += [name for name in self.__dict__ if not name.startswith("_")]
            print(self.__doc__ + "-" * 60 + "\n" + ", ".join(names))

        help = property(_help)

    class DBmanagers(_EvContainer):
        """
        Links to instantiated Django database managers. These are used
        to perform more advanced custom database queries than the standard
        search functions allow.

        helpentries - HelpEntry.objects
        accounts - AccountDB.objects
        scripts - ScriptDB.objects
        msgs    - Msg.objects
        channels - Channel.objects
        objects - ObjectDB.objects
        serverconfigs - ServerConfig.objects
        tags - Tags.objects
        attributes - Attributes.objects

        """

        from .accounts.models import AccountDB
        from .comms.models import ChannelDB, Msg
        from .help.models import HelpEntry
        from .objects.models import ObjectDB
        from .scripts.models import ScriptDB
        from .server.models import ServerConfig
        from .typeclasses.attributes import Attribute
        from .typeclasses.tags import Tag

        # create container's properties
        helpentries = HelpEntry.objects
        accounts = AccountDB.objects
        scripts = ScriptDB.objects
        msgs = Msg.objects
        channels = ChannelDB.objects
        objects = ObjectDB.objects
        serverconfigs = ServerConfig.objects
        attributes = Attribute.objects
        tags = Tag.objects
        # remove these so they are not visible as properties
        del HelpEntry, AccountDB, ScriptDB, Msg, ChannelDB
        # del ExternalChannelConnection
        del ObjectDB, ServerConfig, Tag, Attribute

    managers = DBmanagers()
    del DBmanagers

    class DefaultCmds(_EvContainer):
        """
        This container holds direct shortcuts to all default commands in Evennia.

        To access in code, do 'from evennia import default_cmds' then
        access the properties on the imported default_cmds object.

        """

        from .commands.default.cmdset_account import AccountCmdSet
        from .commands.default.cmdset_character import CharacterCmdSet
        from .commands.default.cmdset_session import SessionCmdSet
        from .commands.default.cmdset_unloggedin import UnloggedinCmdSet
        from .commands.default.muxcommand import MuxAccountCommand, MuxCommand

        def __init__(self):
            "populate the object with commands"

            def add_cmds(module):
                "helper method for populating this object with cmds"
                from evennia.utils import utils

                cmdlist = utils.variable_from_module(module, module.__all__)
                self.__dict__.update(dict([(c.__name__, c) for c in cmdlist]))

            from .commands.default import (
                account,
                admin,
                batchprocess,
                building,
                comms,
                general,
                help,
                system,
                unloggedin,
            )

            add_cmds(admin)
            add_cmds(building)
            add_cmds(batchprocess)
            add_cmds(building)
            add_cmds(comms)
            add_cmds(general)
            add_cmds(account)
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
        CMD_LOGINSTART - this command will be called as the very
                         first command when an account connects to
                         the server.

        To access in code, do 'from evennia import syscmdkeys' then
        access the properties on the imported syscmdkeys object.

        """

        from .commands import cmdhandler

        CMD_NOINPUT = cmdhandler.CMD_NOINPUT
        CMD_NOMATCH = cmdhandler.CMD_NOMATCH
        CMD_MULTIMATCH = cmdhandler.CMD_MULTIMATCH
        CMD_LOGINSTART = cmdhandler.CMD_LOGINSTART
        del cmdhandler

    syscmdkeys = SystemCmds()
    del SystemCmds
    del _EvContainer

    # delayed starts - important so as to not back-access evennia before it has
    # finished initializing
    GLOBAL_SCRIPTS.start()


def set_trace(term_size=(140, 80), debugger="auto"):
    """
    Helper function for running a debugger inside the Evennia event loop.

    Args:
        term_size (tuple, optional): Only used for Pudb and defines the size of the terminal
            (width, height) in number of characters.
        debugger (str, optional): One of 'auto', 'pdb' or 'pudb'. Pdb is the standard debugger. Pudb
            is an external package with a different, more 'graphical', ncurses-based UI. With
            'auto', will use pudb if possible, otherwise fall back to pdb. Pudb is available through
            `pip install pudb`.

    Notes:
        To use:

        1) add this to a line to act as a breakpoint for entering the debugger:

            from evennia import set_trace; set_trace()

        2) restart evennia in interactive mode

            evennia istart

        3) debugger will appear in the interactive terminal when breakpoint is reached. Exit
           with 'q', remove the break line and restart server when finished.

    """
    import sys

    dbg = None

    if debugger in ("auto", "pudb"):
        try:
            from pudb import debugger

            dbg = debugger.Debugger(stdout=sys.__stdout__, term_size=term_size)
        except ImportError:
            if debugger == "pudb":
                raise
            pass

    if not dbg:
        import pdb

        dbg = pdb.Pdb(stdout=sys.__stdout__)

    try:
        # Start debugger, forcing it up one stack frame (otherwise `set_trace`
        # will start debugger this point, not the actual code location)
        dbg.set_trace(sys._getframe().f_back)
    except Exception:
        # Stopped at breakpoint. Press 'n' to continue into the code.
        dbg.set_trace()


# initialize the doc string
global __doc__
__doc__ = DOCSTRING.format(
    "\n- "
    + "\n- ".join(
        f"evennia.{key}"
        for key in sorted(globals())
        if not key.startswith("_") and key not in ("DOCSTRING",)
    )
)
