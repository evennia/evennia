#!/usr/bin/env python
"""
EVENNIA SERVER STARTUP SCRIPT

This is the start point for running Evennia.

Sets the appropriate environmental variables and launches the server
and portal through the runner. Run without arguments to get a
menu. Run the script with the -h flag to see usage information.

"""
import os
import sys, signal
from optparse import OptionParser
from subprocess import Popen

# Set the Python path up so we can get to settings.py from here.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DJANGO_SETTINGS_MODULE'] = 'game.settings'

if not os.path.exists('settings.py'):
    # make sure we have a settings.py file.
    print "    No settings.py file found. launching manage.py ..."

    # this triggers the settings file creation.
    import game.manage

    print """
    ... A new settings file was created. Edit this file to configure
    Evennia as desired by copy&pasting options from
    src/settings_default.py.

    You should then also create/configure the database using

        python manage.py syncdb

    Make sure to create a new admin user when prompted -- this will be
    user #1 in-game.  If you use django-south, you'll see mentions of
    migrating things in the above run. You then also have to run

        python manage.py migrate

    If you use default sqlite3 database, you will find a file
    evennia.db appearing. This is the database file. Just delete this
    and repeat the above manage.py steps to start with a fresh
    database.

    When you are set up, run evennia.py again to start the server."""
    sys.exit()

# signal processing
SIG = signal.SIGINT

HELPENTRY = \
"""
                                                 (version %s)

This program launches Evennia with various options. You can access all
this functionality directly from the command line; for example option
five (restart server) would be "evennia.py restart server".  Use
"evennia.py -h" for command line options.

Evennia consists of two separate programs that both must be running
for the game to work as it should:

Portal - the connection to the outside world (via telnet, web, ssh
         etc). This is normally running as a daemon and don't need to
         be reloaded unless you are debugging a new connection
         protocol. As long as this is running, players won't loose
         their connection to your game. Only one instance of Portal
         will be started, more will be ignored.
Server - the game server itself. This will often need to be reloaded
         as you develop your game. The Portal will auto-connect to the
         Server whenever the Server activates. We will also make sure
         to automatically restart this whenever it is shut down (from
         here or from inside the game or via task manager etc). Only
         one instance of Server will be started, more will be ignored.

In a production environment you will want to run with the default
option (1), which runs as much as possible as a background
process. When developing your game it is however convenient to
directly see tracebacks on standard output, so starting with options
2-4 may be a good bet. As you make changes to your code, reload the
server (option 5) to make it available to users.

Reload and stop is not well supported in Windows. If you have issues, log
into the game to stop or restart the server instead.
"""

MENU = \
"""
+---------------------------------------------------------------------------+
|                                                                           |
|                    Welcome to the Evennia launcher!                       |
|                                                                           |
|                Pick an option below. Use 'h' to get help.                 |
|                                                                           |
+--- Starting (will not restart already running processes) -----------------+
|                                                                           |
|  1) (default):      Start Server and Portal. Portal starts in daemon mode.|
|                     All output is to logfiles.                            |
|  2) (game debug):   Start Server and Portal. Portal starts in daemon mode.|
|                     Server outputs to stdout instead of logfile.          |
|  3) (portal debug): Start Server and Portal. Portal starts in non-daemon  |
|                     mode (can be reloaded) and logs to stdout.            |
|  4) (full debug):   Start Server and Portal. Portal starts in non-daemon  |
|                     mode (can be reloaded). Both log to stdout.           |
|                                                                           |
+--- Restarting (must first be started) ------------------------------------+
|                                                                           |
|  5) Reload the Server                                                     |
|  6) Reload the Portal (only works in non-daemon mode. If running          |
|       in daemon mode, Portal needs to be restarted manually (option 1-4)) |
|                                                                           |
+--- Stopping (must first be started) --------------------------------------+
|                                                                           |
|  7) Stopping both Portal and Server. Server will not restart.             |
|  8) Stopping only Server. Server will not restart.                        |
|  9) Stopping only Portal.                                                 |
|                                                                           |
+---------------------------------------------------------------------------+
|  h) Help                                                                  |
|  q) Quit                                                                  |
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
from src.objects.models import ObjectDB
try:
    test = ObjectDB.objects.get(id=1)
except ObjectDB.DoesNotExist:
    pass # this is fine at this point
except DatabaseError:
    print """
    Your database does not seem to be set up correctly.

    Please run:

         python manage.py syncdb

    (make sure to create an admin user when prompted). If you use
    pyhon-south you will get mentions of migrating in the above
    run. You then need to also run

         python manage.py migrate

    When you have a database set up, rerun evennia.py.
    """
    sys.exit()

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
        bat_file = open('twistd.bat','w')
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
            print HELPENTRY % EVENNIA_VERSION
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
                pass # default operation
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
        else: # all
            # for convenience we don't start logging of portal, only of server with this command.
            if inter:
                cmdstr.extend(['--iserver'])
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
    from src.commands import cmdsethandler
    cmdsethandler.import_cmdset(settings.CMDSET_UNLOGGEDIN, None)
    cmdsethandler.import_cmdset(settings.CMDSET_DEFAULT, None)
    cmdsethandler.import_cmdset(settings.CMDSET_OOC, None)
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

    parser = OptionParser(usage="%prog [-i] [menu|start|reload|stop [server|portal|all]]",
                          description="""This is the main Evennia launcher. It handles the Portal and Server, the two services making up Evennia. Default is to operate on both services. Use --interactive together with start to launch services as 'interactive'. Note that when launching 'all' services with the --interactive flag, both services will be started, but only Server will actually be started in interactive mode. This is simply because this is the most commonly useful state. To activate interactive mode also for Portal, launch the two services explicitly as two separate calls to this program. You can also use the menu.""")

    parser.add_option('-i', '--interactive', action='store_true', dest='interactive', default=False, help="Start given processes in interactive mode (log to stdout, don't start as a daemon).")

    options, args = parser.parse_args()

    if not args:
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
    if  service not in ['server', 'portal', 'all']:
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
