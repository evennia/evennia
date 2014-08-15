#!/usr/bin/env python
"""
EVENNIA SERVER STARTUP SCRIPT

This is the start point for running Evennia.

Sets the appropriate environmental variables and launches the server
and portal through the runner. Run without arguments to get a
menu. Run the script with the -h flag to see usage information.

"""
import os
import sys
import signal
from optparse import OptionParser
from subprocess import Popen

# Set the Python path up so we can get to settings.py from here.
from django.core import management

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DJANGO_SETTINGS_MODULE'] = 'game.settings'

if not os.path.exists('settings.py'):
    # make sure we have a settings.py file.
    print "    No settings.py file found. launching manage.py ..."

    # this triggers the settings file creation.
    import game.manage
    sys.exit()

# signal processing
SIG = signal.SIGINT


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
 {south}
"""

ABOUT_INFO= \
"""
 MUD/MUX/MU* development system

 Licence: BSD 3-Clause Licence
 Web: http://www.evennia.com
 Irc: #evennia on FreeNode
 Forum: http://www.evennia.com/discussions
 Maintainer (2010-):   Griatch (griatch AT gmail DOT com)
 Maintainer (2006-10): Greg Taylor
"""

HELP_ENTRY = \
"""
                                         (version %s)

All functionality of the launcher can also be accessed directly from
the command line. Use  "python evennia.py -h" for command line
options.

Evennia consists of two separate parts that both must be running
for the server to work as it should:

Portal - the connection to the outside world (via telnet, web, ssh
         etc). This is normally running as a daemon and don't need to
         be reloaded unless you are debugging a new connection
         protocol.
Server - the game server itself. This will often need to be reloaded
         as you develop your game. The Portal will auto-connect to the
         Server whenever the Server activates.

In a production environment you will want to run with the default
option (1), which runs as much as possible as a background process.
When developing your game it is however convenient to directly see
tracebacks on standard output, so starting with options 2-4 may be a
good bet. As you make changes to your code, reload the server (option
5) to make changes appear in the game.

Reload and stop is not well supported in Windows. If you have issues,
log into the game to stop or restart the server instead.
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
|  6) Reload the Portal (only works when portal outputs to terminal).       |
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


#
# System Configuration and setup
#

SERVER_PIDFILE = "server.pid"
PORTAL_PIDFILE = "portal.pid"

SERVER_RESTART = "server.restart"
PORTAL_RESTART = "portal.restart"

# Get the settings
from django.conf import settings

from src.utils.utils import get_evennia_version
EVENNIA_VERSION = get_evennia_version()

# Setup access of the evennia server itself
SERVER_PY_FILE = os.path.join(settings.SRC_DIR, 'server/server.py')
PORTAL_PY_FILE = os.path.join(settings.SRC_DIR, 'server/portal.py')

# Get logfile names
SERVER_LOGFILE = settings.SERVER_LOG_FILE
PORTAL_LOGFILE = settings.PORTAL_LOG_FILE

# Check so a database exists and is accessible
from django.db import DatabaseError
from src.players.models import PlayerDB
try:
    superuser = PlayerDB.objects.get(id=1)
except DatabaseError, e:
    print """
    Your database does not seem to be set up correctly.
    (error was '%s')

    Please run:

       python manage.py syncdb
       python manage.py migrate

    When you have a database set up, rerun evennia.py.
    """ % e
    sys.exit()
except PlayerDB.DoesNotExist:
    # no superuser yet. We need to create it.
    from django.core.management import call_command
    print "\nCreate a superuser below. The superuser is Player #1, the 'owner' account of the server.\n"
    call_command("createsuperuser", interactive=True)

# Add this to the environmental variable for the 'twistd' command.
currpath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if 'PYTHONPATH' in os.environ:
    os.environ['PYTHONPATH'] += (":%s" % currpath)
else:
    os.environ['PYTHONPATH'] = currpath

TWISTED_BINARY = 'twistd'
if os.name == 'nt':
    # Windows needs more work to get the correct binary
    try:
        # Test for for win32api
        import win32api
    except ImportError:
        print """
    ERROR: Unable to import win32api, which Twisted requires to run.
    You may download it from:

    http://sourceforge.net/projects/pywin32
      or
    http://starship.python.net/crew/mhammond/win32/Downloads.html"""
        sys.exit()

    if not os.path.exists('twistd.bat'):
        # Test for executable twisted batch file. This calls the twistd.py
        # executable that is usually not found on the path in Windows.
        # It's not enough to locate scripts.twistd, what we want is the
        # executable script C:\PythonXX/Scripts/twistd.py. Alas we cannot
        # hardcode this location since we don't know if user has Python
        # in a non-standard location, so we try to figure it out.
        from twisted.scripts import twistd
        twistd_path = os.path.abspath(
            os.path.join(os.path.dirname(twistd.__file__),
                         os.pardir, os.pardir, os.pardir, os.pardir,
                         'scripts', 'twistd.py'))
        bat_file = open('twistd.bat', 'w')
        bat_file.write("@\"%s\" \"%s\" %%*" % (sys.executable, twistd_path))
        bat_file.close()
        print """
    INFO: Since you are running Windows, a file 'twistd.bat' was
    created for you. This is a simple batch file that tries to call
    the twisted executable. Evennia determined this to be:

       %(twistd_path)s

    If you run into errors at startup you might need to edit
    twistd.bat to point to the actual location of the Twisted
    executable (usually called twistd.py) on your machine.

    This procedure is only done once. Run evennia.py again when you
    are ready to start the server.
    """ % {'twistd_path': twistd_path}
        sys.exit()

    TWISTED_BINARY = 'twistd.bat'


# Functions

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
    try:
        import south
        sversion = "South %s" % south.__version__
    except ImportError:
        sversion = "South <not installed>"

    return VERSION_INFO.format(version=EVENNIA_VERSION,
                             about=ABOUT_INFO if about else "",
                             os=os.name, python=sys.version.split()[0],
                             twisted=twisted.version.short(),
                             django=django.get_version(),
                             south=sversion)

def run_menu():
    """
    This launches an interactive menu.
    """

    cmdstr = [sys.executable, "runner.py"]

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
            return cmdstr
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
    return None


def handle_args(options, mode, service):
    """
    Handle argument options given on the command line.

    options - parsed object for command line
    mode - str; start/stop etc
    service - str; server, portal or all
    """

    inter = options.interactive
    cmdstr = [sys.executable, "runner.py"]
    errmsg = "The %s does not seem to be running."

    if mode == 'start':

        # launch the error checker. Best to catch the errors already here.
        error_check_python_modules()

        # starting one or many services
        if service == 'server':
            if inter:
                cmdstr.append('--iserver')
            cmdstr.append('--noportal')
        elif service == 'portal':
            if inter:
                cmdstr.append('--iportal')
            cmdstr.append('--noserver')
            management.call_command('collectstatic', verbosity=1, interactive=False)
        else:  # all
            # for convenience we don't start logging of
            # portal, only of server with this command.
            if inter:
                cmdstr.extend(['--iserver'])
            management.call_command('collectstatic', verbosity=1, interactive=False)
        return cmdstr

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
    return None


def error_check_python_modules():
    """
    Import settings modules in settings. This will raise exceptions on
    pure python-syntax issues which are hard to catch gracefully
    with exceptions in the engine (since they are formatting errors in
    the python source files themselves). Best they fail already here
    before we get any further.
    """
    def imp(path, split=True):
        mod, fromlist = path, "None"
        if split:
            mod, fromlist = path.rsplit('.', 1)
        __import__(mod, fromlist=[fromlist])

    # core modules
    imp(settings.COMMAND_PARSER)
    imp(settings.SEARCH_AT_RESULT)
    imp(settings.SEARCH_AT_MULTIMATCH_INPUT)
    imp(settings.CONNECTION_SCREEN_MODULE, split=False)
    #imp(settings.AT_INITIAL_SETUP_HOOK_MODULE, split=False)
    for path in settings.LOCK_FUNC_MODULES:
        imp(path, split=False)
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
    imp(settings.BASE_PLAYER_TYPECLASS)
    imp(settings.BASE_OBJECT_TYPECLASS)
    imp(settings.BASE_CHARACTER_TYPECLASS)
    imp(settings.BASE_ROOM_TYPECLASS)
    imp(settings.BASE_EXIT_TYPECLASS)
    imp(settings.BASE_SCRIPT_TYPECLASS)


def main():
    """
    This handles command line input.
    """

    parser = OptionParser(usage="%prog [-i] start|stop|reload|menu [server|portal]",
                          description=CMDLINE_HELP)
    parser.add_option('-i', '--interactive', action='store_true',
                      dest='interactive', default=False,
                      help="Start given processes in interactive mode.")
    parser.add_option('-v', '--version', action='store_true',
                      dest='show_version', default=False,
                      help="Show version info.")

    options, args = parser.parse_args()

    if not args:
        if options.show_version:
            print show_version_info()
            return
        mode = "menu"
        service = 'all'
    if args:
        mode = args[0]
        service = "all"
    if len(args) > 1:
        service = args[1]

    if mode not in ['menu', 'start', 'reload', 'stop']:
        print "mode should be none, 'menu', 'start', 'reload' or 'stop'."
        sys.exit()
    if service not in ['server', 'portal', 'all']:
        print "service should be none, 'server', 'portal' or 'all'."
        sys.exit()

    if mode == 'menu':
        # launch menu
        cmdstr = run_menu()
    else:
        # handle command-line arguments
        cmdstr = handle_args(options, mode, service)
    if cmdstr:
        # call the runner.
        cmdstr.append('start')
        Popen(cmdstr)

if __name__ == '__main__':
    # start Evennia
    from src.utils.utils import check_evennia_dependencies
    if check_evennia_dependencies():
        main()
