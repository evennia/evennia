#!/usr/bin/env python
"""
EVENNIA SERVER STARTUP SCRIPT

This is the start point for running Evennia.

Sets the appropriate environmental variables and launches the server
and portal through the runner. Run without arguments to get a
menu. Run the script with the -h flag to see usage information.

Usage:

    evennia init <path> - creates a new game location, sets up a custom
                          settings file and copies all templates to <path>
    evennia [settings][options] - handles server start/stop/restart if called
                                  from the game folder. Can be called outside
                                  the game folder if called with the path
                                  to the settings file.

"""
import os
import sys
import signal
import shutil
import importlib
import django
from argparse import ArgumentParser
from subprocess import Popen
from django.core import management

# Signal processing
SIG = signal.SIGINT

# Set up the main python paths to Evennia
EVENNIA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENNIA_BIN = os.path.join(EVENNIA_ROOT, "bin")
EVENNIA_LIB = os.path.join(EVENNIA_ROOT, "lib")
EVENNIA_RUNNER = os.path.join(EVENNIA_BIN, "runner.py")
EVENNIA_TEMPLATE = os.path.join(EVENNIA_ROOT, "game_template")

EVENNIA_VERSION = "Unknown"
TWISTED_BINARY = "twistd"

# Game directory structure
SETTINGFILE = "settings.py"
SERVERDIR = "server"
CONFDIR = os.path.join(SERVERDIR, "conf")
SETTINGS_PATH = os.path.join(CONFDIR, SETTINGFILE)
SETTINGS_DOTPATH = "server.conf.settings"
CURRENT_DIR = os.getcwd()
GAMEDIR = CURRENT_DIR

# Operational setup
SERVER_LOGFILE = None
PORTAL_LOGFILE = None
SERVER_PIDFILE = None
PORTAL_PIDFILE = None
SERVER_RESTART = None
PORTAL_RESTART = None
SERVER_PY_FILE = None
PORTAL_PY_FILE = None

# add Evennia root and bin dir to PYTHONPATH
sys.path.insert(0, EVENNIA_ROOT)


#------------------------------------------------------------
#
# Messages
#
#------------------------------------------------------------

WELCOME_MESSAGE = \
    """
    Welcome to Evennia!

    No previous setting file was found so we created a fresh
    settings.py file for you. No database was created.  You may edit
    the settings file now if you like, but you don't have to touch
    anything if you just want to quickly get started.

    Once you are ready to continue, run evennia.py again to
    initialize the database and a third time to start the server.

    The first time the server starts it will set things up for you.
    Make sure to create a superuser when asked. The superuser's
    email-address does not have to exist.
    """

WARNING_RUNSERVER = \
    """
    WARNING: There is no need to run the Django development
    webserver to test out Evennia web features (the web client
    will in fact not work since the Django test server knows
    nothing about MUDs).  Instead, just start Evennia with the
    webserver component active (this is the default).
    """

ERROR_SETTINGS = \
    """
    ERROR: Could not import the file {settingsfile} from {settingspath}.
    There are usually two reasons for this:
        1) The settings file is a normal Python module. It may contain a syntax error.
           Resolve the problem and try again.
        2) Django is not correctly installed. This usually shows by errors involving
           'DJANGO_SETTINGS_MODULE'. If you run a virtual machine, it might be worth to restart it
           to see if this resolves the issue.
    """.format(settingsfile=SETTINGFILE, settingspath=SETTINGS_PATH)

ERROR_DATABASE = \
    """
    Your database does not seem to be set up correctly.
    (error was '{traceback}')

    Try to run

       python evennia.py

    to initialize the database according to your settings.
    """

ERROR_WINDOWS_WIN32API = \
    """
    ERROR: Unable to import win32api, which Twisted requires to run.
    You may download it from:

    http://sourceforge.net/projects/pywin32
      or
    http://starship.python.net/crew/mhammond/win32/Downloads.html
    """

INFO_WINDOWS_BATFILE = \
    """
    INFO: Since you are running Windows, a file 'twistd.bat' was
    created for you. This is a simple batch file that tries to call
    the twisted executable. Evennia determined this to be:

       %(twistd_path)s

    If you run into errors at startup you might need to edit
    twistd.bat to point to the actual location of the Twisted
    executable (usually called twistd.py) on your machine.

    This procedure is only done once. Run evennia.py again when you
    are ready to start the server.
    """

CMDLINE_HELP = \
    """
    Main Evennia launcher. When starting in interactive (-i) mode, only
    the Server will do so since this is the most commonly useful setup. To
    activate interactive mode also for the Portal, use the menu or launch
    the two services one after the other as two separate calls to this
    program.
    """


VERSION_INFO = \
    """
    Evennia {version}
    {about}
    OS: {os}
    Python: {python}
    Twisted: {twisted}
    Django: {django}
    """

ABOUT_INFO= \
    """
    Evennia MUD/MUX/MU* development system

    Licence: BSD 3-Clause Licence
    Web: http://www.evennia.com
    Irc: #evennia on FreeNode
    Forum: http://www.evennia.com/discussions
    Maintainer (2010-):   Griatch (griatch AT gmail DOT com)
    Maintainer (2006-10): Greg Taylor
    """

HELP_ENTRY = \
"""
See python evennia.py -h for controlling Evennia directly from
the command line.

Evennia has two parts that both must run:

Portal - the connection to the outside world (via telnet, web, ssh
         etc). This is normally running as a daemon and don't need to
         be reloaded unless you are debugging a new connection
         protocol.
Server - the game server itself. This will often need to be reloaded
         as you develop your game. The Portal will auto-connect to the
         Server whenever the Server activates.

Use option (1) in a production environment.  During development (2) is
usually enough, portal debugging is usually only useful if you are
adding new protocols or are debugging an Evennia bug.

Reload with (5) to update the server with your changes without
disconnecting any players.

Reload and stop are sometimes poorly supported in Windows. If you have
issues, log into the game to stop or restart the server instead.
"""

MENU = \
"""
+----Evennia Launcher-------------------------------------------------------+
|                                                                           |
+--- Starting --------------------------------------------------------------+
|                                                                           |
|  1) (default):      All output to logfiles.                               |
|  2) (game debug):   Server outputs to terminal instead of to logfile.     |
|  3) (portal debug): Portal outputs to terminal instead of to logfile.     |
|  4) (full debug):   Both Server and Portal output to terminal             |
|                                                                           |
+--- Restarting ------------------------------------------------------------+
|                                                                           |
|  5) Reload the Server                                                     |
|  6) Reload the Portal (only works with portal/full debug)                 |
|                                                                           |
+--- Stopping --------------------------------------------------------------+
|                                                                           |
|  7) Stopping both Portal and Server.                                      |
|  8) Stopping only Server.                                                 |
|  9) Stopping only Portal.                                                 |
|                                                                           |
+---------------------------------------------------------------------------+
|  h) Help                     i) About info                      q) Abort  |
+---------------------------------------------------------------------------+
"""


#------------------------------------------------------------
#
# Functions
#
#------------------------------------------------------------

def evennia_version():
    """
    Get the Evennia version info from the main package.
    """
    version = "Unknown"
    with open(os.path.join(EVENNIA_ROOT, "VERSION.txt"), 'r') as f:
        version = f.read().strip()
    try:
        version = "%s(GIT %s)" % (version, os.popen("git rev-parse --short HEAD").read().strip())
    except IOError:
        pass
    return version


def init_game_directory(path):
    """
    Try to analyze the given path to find settings.py - this defines
    the game directory and also sets PYTHONPATH as well as the
    django path.
    """
    global GAMEDIR
    if os.path.exists(os.path.join(path, SETTINGFILE)):
        # path given to server/conf/
        GAMEDIR = os.path.dirname(os.path.dirname(os.path.dirname(path)))
    elif os.path.exists(SETTINGS_PATH):
        # path given to somewhere else in gamedir
        GAMEDIR = os.path.dirname(os.path.dirname(path))
    else:
        # Assume path given to root game dir
        GAMEDIR = path

    # set pythonpath to gamedir
    sys.path.insert(0, GAMEDIR)
    # set the settings location
    os.environ['DJANGO_SETTINGS_MODULE'] = SETTINGS_DOTPATH
    # required since django1.7.
    django.setup()

    # check all dependencies
    from evennia.utils.utils import check_evennia_dependencies
    if not check_evennia_



    # test existence of settings module
    try:
        settings = importlib.import_module(SETTINGS_DOTPATH)
    except Exception:
        import traceback
        print "\n" + traceback.format_exc()
        print ERROR_SETTINGS
        sys.exit()

    # set up the Evennia executables and log file locations
    global SERVER_PY_FILE, PORTAL_PY_FILE
    global SERVER_LOGFILE, PORTAL_LOGFILE
    global SERVER_PIDFILE, PORTAL_PIDFILE
    global SERVER_RESTART, PORTAL_RESTART
    global EVENNIA_VERSION

    SERVER_PY_FILE = os.path.join(settings.LIB_DIR, "server/server.py")
    PORTAL_PY_FILE = os.path.join(settings.LIB_DIR, "portal/server.py")

    SERVER_PIDFILE = os.path.join(GAMEDIR, SERVERDIR, "server.pid")
    PORTAL_PIDFILE = os.path.join(GAMEDIR, SERVERDIR, "portal.pid")

    SERVER_RESTART = os.path.join(GAMEDIR, SERVERDIR, "server.restart")
    PORTAL_RESTART = os.path.join(GAMEDIR, SERVERDIR, "portal.restart")

    SERVER_LOGFILE = settings.SERVER_LOG_FILE
    PORTAL_LOGFILE = settings.PORTAL_LOG_FILE

    # This also tests the library access
    from evennia.utils.utils import get_evennia_version
    EVENNIA_VERSION = get_evennia_version()

    # set up twisted
    if os.name == 'nt':
        # We need to handle Windows twisted separately. We create a
        # batchfile in game/server, linking to the actual binary

        global TWISTED_BINARY
        TWISTED_BINARY = "twistd.bat"

        # add path so system can find the batfile
        sys.path.insert(0, os.path.join(GAMEDIR, SERVERDIR))

        try:
            importlib.import_module("win32api")
        except ImportError:
            print ERROR_WINDOWS_WIN32API
            sys.exit()

        if not os.path.exists(os.path.join(EVENNIA_BIN, TWISTED_BINARY)):
            # Test for executable twisted batch file. This calls the
            # twistd.py executable that is usually not found on the
            # path in Windows.  It's not enough to locate
            # scripts.twistd, what we want is the executable script
            # C:\PythonXX/Scripts/twistd.py. Alas we cannot hardcode
            # this location since we don't know if user has Python in
            # a non-standard location. So we try to figure it out.
            twistd = importlib.import_module("twisted.scripts.twistd")
            twistd_dir = os.path.dirname(twistd.__file__)

            # note that we hope the twistd package won't change here, since we
            # try to get to the executable by relative path.
            twistd_path = os.path.abspath(os.path.join(twistd_dir,
                            os.pardir, os.pardir, os.pardir, os.pardir,
                            'scripts', 'twistd.py'))

            with open('twistd.bat', 'w') as bat_file:
                # build a custom bat file for windows
                bat_file.write("@\"%s\" \"%s\" %%*" % (sys.executable, twistd_path))

            print INFO_WINDOWS_BATFILE.format(twistd_path=twistd_path)


#
# Check/Create settings
#

def create_secret_key():
    """
    Randomly create the secret key for the settings file
    """
    import random
    import string
    secret_key = list((string.letters +
        string.digits + string.punctuation).replace("\\", "").replace("'", '"'))
    random.shuffle(secret_key)
    secret_key = "".join(secret_key[:40])
    return secret_key


def create_settings_file():
    """
    Uses the template settings file to build a working
    settings file.
    """
    settings_path = os.path.join(GAMEDIR, "server", "conf", "settings.py")
    with open(settings_path, 'r') as f:
        settings_string = f.read()

    # tweak the settings
    setting_dict = {"servername":"Evennia",
                    "secret_key":create_secret_key}

    # modify the settings
    settings_string.format(**setting_dict)

    with open(settings_path, 'w') as f:
        f.write(settingsj_string)


# Functions

def create_game_directory(dirname):
    """
    Initialize a new game directory named dirname
    at the current path. This means copying the
    template directory from evennia's root.
    """
    global GAMEDIR
    GAMEDIR = os.abspath(os.path.join(CURRENT_DIR, dirname))
    if os.path.exists(GAMEDIR):
        print "Cannot create new Evennia game dir: '%s' already exists." % dirname
        sys.exit()
    # copy template directory
    shutil.copytree(EVENNIA_TEMPLATE, GAMEDIR)
    # pre-build settings file in the new GAMEDIR
    create_settings_file()


def get_pid(pidfile):
    """
    Get the PID (Process ID) by trying to access
    an PID file.
    """
    pid = None
    if os.path.exists(pidfile):
        f = open(pidfile, 'r')
        pid = f.read()
    return pid


def del_pid(pidfile):
    """
    The pidfile should normally be removed after a process has finished, but
    when sending certain signals they remain, so we need to clean them manually.
    """
    if os.path.exists(pidfile):
        os.remove(pidfile)


def kill(pidfile, signal=SIG, succmsg="", errmsg="", restart_file=SERVER_RESTART, restart="reload"):
    """
    Send a kill signal to a process based on PID. A customized success/error
    message will be returned. If clean=True, the system will attempt to manually
    remove the pid file.
    """
    pid = get_pid(pidfile)
    if pid:
        if os.name == 'nt':
            if sys.version < "2.7":
                print "Windows requires Python 2.7 or higher for this operation."
                return
            os.remove(pidfile)
        # set restart/norestart flag
        if restart == 'reload':
            management.call_command('collectstatic', interactive=False, verbosity=0)
        f = open(restart_file, 'w')
        f.write(str(restart))
        f.close()
        try:
            os.kill(int(pid), signal)
        except OSError:
            print "Process %(pid)s could not be signalled. The PID file '%(pidfile)s' seems stale. Try removing it." % {'pid': pid, 'pidfile': pidfile}
            return
        print "Evennia:", succmsg
        return
    print "Evennia:", errmsg

def show_version_info(about=False):
    """
    Display version info
    """
    import os, sys
    import twisted
    import django

    return VERSION_INFO.format(version=EVENNIA_VERSION,
                             about=ABOUT_INFO if about else "",
                             os=os.name, python=sys.version.split()[0],
                             twisted=twisted.version.short(),
                             django=django.get_version())

def run_menu():
    """
    This launches an interactive menu.
    """

    cmdstr = [sys.executable, EVENNIA_RUNNER]

    while True:
        # menu loop

        print MENU
        inp = raw_input(" option > ")

        # quitting and help
        if inp.lower() == 'q':
            sys.exit()
        elif inp.lower() == 'h':
            print HELP_ENTRY % EVENNIA_VERSION
            raw_input("press <return> to continue ...")
            continue
        elif inp.lower() in ('v', 'i', 'a'):
            print show_version_info(about=True)
            raw_input("press <return> to continue ...")
            continue

        # options
        try:
            inp = int(inp)
        except ValueError:
            print "Not a valid option."
            continue
        errmsg = "The %s does not seem to be running."
        if inp < 5:
            if inp == 1:
                pass  # default operation
            elif inp == 2:
                cmdstr.extend(['--iserver'])
            elif inp == 3:
                cmdstr.extend(['--iportal'])
            elif inp == 4:
                cmdstr.extend(['--iserver', '--iportal'])
            # start server
            cmdstr.append("start")
            Popen(cmdstr)
            return
        elif inp < 10:
            if inp == 5:
                if os.name == 'nt':
                    print "This operation is not supported under Windows. Log into the game to restart/reload the server."
                    return
                kill(SERVER_PIDFILE, SIG, "Server reloaded.", errmsg % "Server", restart="reload")
            elif inp == 6:
                if os.name == 'nt':
                    print "This operation is not supported under Windows."
                    return
                kill(PORTAL_PIDFILE, SIG, "Portal reloaded (or stopped if in daemon mode).", errmsg % "Portal", restart=True)
            elif inp == 7:
                kill(SERVER_PIDFILE, SIG, "Stopped Portal.", errmsg % "Portal", PORTAL_RESTART, restart=False)
                kill(PORTAL_PIDFILE, SIG, "Stopped Server.", errmsg % "Server", restart="shutdown")
            elif inp == 8:
                kill(PORTAL_PIDFILE, SIG, "Stopped Server.", errmsg % "Server", restart="shutdown")
            elif inp == 9:
                kill(SERVER_PIDFILE, SIG, "Stopped Portal.", errmsg % "Portal", PORTAL_RESTART, restart=False)
            return
        else:
            print "Not a valid option."


def server_operation(mode, service, interactive):
    """
    Handle argument options given on the command line.

    mode - str; start/stop etc
    service - str; server, portal or all
    interactive - bool; use interactive mode or daemon
    """

    cmdstr = [sys.executable, EVENNIA_RUNNER]
    errmsg = "The %s does not seem to be running."

    if mode == 'start':

        # launch the error checker. Best to catch the errors already here.
        error_check_python_modules()

        # starting one or many services
        if service == 'server':
            if interactive:
                cmdstr.append('--iserver')
            cmdstr.append('--noportal')
        elif service == 'portal':
            if interactive:
                cmdstr.append('--iportal')
            cmdstr.append('--noserver')
            management.call_command('collectstatic', verbosity=1, interactive=False)
        else:  # all
            # for convenience we don't start logging of
            # portal, only of server with this command.
            if interactive:
                cmdstr.extend(['--iserver'])
            management.call_command('collectstatic', verbosity=1, interactive=False)
        # start the server
        cmdstr.append("start")
        Popen(cmdstr)

    elif mode == 'reload':
        # restarting services
        if os.name == 'nt':
            print "Restarting from command line is not supported under Windows. Log into the game to restart."
            return
        if service == 'server':
            kill(SERVER_PIDFILE, SIG, "Server reloaded.", errmsg % 'Server', restart="reload")
        elif service == 'portal':
            print """
          Note: Portal usually don't need to be reloaded unless you are debugging in interactive mode.
          If Portal was running in default Daemon mode, it cannot be restarted. In that case you have
          to restart it manually with 'evennia.py start portal'
          """
            kill(PORTAL_PIDFILE, SIG, "Portal reloaded (or stopped, if it was in daemon mode).", errmsg % 'Portal', PORTAL_RESTART)
        else: # all
            # default mode, only restart server
            kill(SERVER_PIDFILE, SIG, "Server reload.", errmsg % 'Server', restart="reload")

    elif mode == 'stop':
        # stop processes, avoiding reload
        if service == 'server':
            kill(SERVER_PIDFILE, SIG, "Server stopped.", errmsg % 'Server', restart="shutdown")
        elif service == 'portal':
            kill(PORTAL_PIDFILE, SIG, "Portal stopped.", errmsg % 'Portal', PORTAL_RESTART, restart=False)
        else:
            kill(PORTAL_PIDFILE, SIG, "Portal stopped.", errmsg % 'Portal', PORTAL_RESTART, restart=False)
            kill(SERVER_PIDFILE, SIG, "Server stopped.", errmsg % 'Server', restart="shutdown")


def error_check_python_modules():
    """
    Import settings modules in settings. This will raise exceptions on
    pure python-syntax issues which are hard to catch gracefully
    with exceptions in the engine (since they are formatting errors in
    the python source files themselves). Best they fail already here
    before we get any further.
    """
    from django.conf import settings

    # core modules
    importlib.import_module(settings.COMMAND_PARSER)
    importlib.import_module(settings.SEARCH_AT_RESULT)
    importlib.import_module(settings.SEARCH_AT_MULTIMATCH_INPUT)
    importlib.import_module(settings.CONNECTION_SCREEN_MODULE, split=False)
    #imp(settings.AT_INITIAL_SETUP_HOOK_MODULE, split=False)
    for path in settings.LOCK_FUNC_MODULES:
        importlib.import_module(path, split=False)
    # cmdsets

    deprstring = "settings.%s should be renamed to %s. If defaults are used, " \
                 "their path/classname must be updated (see src/settings_default.py)."
    if hasattr(settings, "CMDSET_DEFAULT"):
        raise DeprecationWarning(deprstring % ("CMDSET_DEFAULT", "CMDSET_CHARACTER"))
    if hasattr(settings, "CMDSET_OOC"):
        raise DeprecationWarning(deprstring % ("CMDSET_OOC", "CMDSET_PLAYER"))
    if settings.WEBSERVER_ENABLED and not isinstance(settings.WEBSERVER_PORTS[0], tuple):
        raise DeprecationWarning("settings.WEBSERVER_PORTS must be on the form [(proxyport, serverport), ...]")
    if hasattr(settings, "BASE_COMM_TYPECLASS"):
        raise DeprecationWarning(deprstring % ("BASE_COMM_TYPECLASS", "BASE_CHANNEL_TYPECLASS"))
    if hasattr(settings, "COMM_TYPECLASS_PATHS"):
        raise DeprecationWarning(deprstring % ("COMM_TYPECLASS_PATHS", "CHANNEL_TYPECLASS_PATHS"))
    if hasattr(settings, "CHARACTER_DEFAULT_HOME"):
        raise DeprecationWarning("settings.CHARACTER_DEFAULT_HOME should be renamed to DEFAULT_HOME. " \
                "See also settings.START_LOCATION (see src/settings_default.py).")

    from src.commands import cmdsethandler
    if not cmdsethandler.import_cmdset(settings.CMDSET_UNLOGGEDIN, None): print "Warning: CMDSET_UNLOGGED failed to load!"
    if not cmdsethandler.import_cmdset(settings.CMDSET_CHARACTER, None): print "Warning: CMDSET_CHARACTER failed to load"
    if not cmdsethandler.import_cmdset(settings.CMDSET_PLAYER, None): print "Warning: CMDSET_PLAYER failed to load"
    # typeclasses
    importlib.import_module(settings.BASE_PLAYER_TYPECLASS)
    importlib.import_module(settings.BASE_OBJECT_TYPECLASS)
    importlib.import_module(settings.BASE_CHARACTER_TYPECLASS)
    importlib.import_module(settings.BASE_ROOM_TYPECLASS)
    importlib.import_module(settings.BASE_EXIT_TYPECLASS)
    importlib.import_module(settings.BASE_SCRIPT_TYPECLASS)


def create_database():
    from django.core.management import call_command
    print "\nCreating a database ...\n"
    call_command("migrate", interactive=False)
    print "\n ... database initialized.\n"


def create_superuser():
    from django.core.management import call_command
    print "\nCreate a superuser below. The superuser is Player #1, the 'owner' account of the server.\n"
    call_command("createsuperuser", interactive=True)


def check_database(automigrate=False):
    # Check so a database exists and is accessible
    from django.db import DatabaseError
    from src.players.models import PlayerDB
    try:
        PlayerDB.objects.get(id=1)
    except DatabaseError, e:
        if automigrate:
            create_database()
            create_superuser()
        else:
            print ERROR_DATABASE.format(traceback=e)
            sys.exit()
    except PlayerDB.DoesNotExist:
        # no superuser yet. We need to create it.
        create_superuser()

def main():
    """
    Run the evennia main program.
    """

    # set up argument parser

    parser = ArgumentParser(#usage="%prog [-i] start|stop|reload|menu [server|portal]|manager args",
                          description=CMDLINE_HELP)
    parser.add_argument('-i', '--interactive', action='store_true',
                      dest='interactive', default=False,
                      help="Start given processes in interactive mode.")
    parser.add_argument('-v', '--version', action='store_true',
                      dest='show_version', default=False,
                      help="Show version info.")
    parser.add_argument('--init', action='store', dest="init", metavar="dirname")
    parser.add_argument('-c', '--config', action='store', dest="config", default=None)
    parser.add_argument("mode", default="menu")
    parser.add_argument("service", choices=["all", "server", "portal"], default="all")

    args = parser.parse_args()

    # handle arguments

    if args.show_version:
        print show_version_info()

    mode, service = args.mode, args.service

    if args.init:
        create_game_directory(args.init)
        sys.exit()

    # this must be done first - it sets up all the global properties
    # and initializes django for the game directory
    init_game_directory(CURRENT_DIR)

    if mode == 'menu':
        # launch menu for operation
        check_database(True)
        run_menu()
    elif mode in ('start', 'reload', 'stop'):
        # operate the server directly
        if mode != "stop":
            check_database(False)
        server_operation(mode, service, args.interactive)
    else:
        # pass-through to django manager
        from django.core.management import call_command
        call_command(mode)


if __name__ == '__main__':
    # start Evennia from the command line

    if check_evennia_dependencies():
        if len(sys.argv) > 1 and sys.argv[1] in ('runserver', 'testserver'):
            print WARNING_RUNSERVER
        main()
