#!/usr/bin/env python
"""

This runner is controlled by evennia.py and should normally not be
 launched directly.  It manages the two main Evennia processes (Server
 and Portal) and most importanly runs a passive, threaded loop that
 makes sure to restart Server whenever it shuts down.

Since twistd does not allow for returning an optional exit code we
need to handle the current reload state for server and portal with
flag-files instead. The files, one each for server and portal either
contains True or False indicating if the process should be restarted
upon returning, or not. A process returning != 0 will always stop, no
matter the value of this file.

"""
import os
import sys
from optparse import OptionParser
from subprocess import Popen
import Queue, thread

try:
    # check if launched with pypy
    import __pypy__ as is_pypy
except ImportError:
    is_pypy = False

#
# System Configuration
#

SERVER_PIDFILE = "server.pid"
PORTAL_PIDFILE = "portal.pid"

SERVER_RESTART = "server.restart"
PORTAL_RESTART = "portal.restart"

# Set the Python path up so we can get to settings.py from here.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DJANGO_SETTINGS_MODULE'] = 'game.settings'

if not os.path.exists('settings.py'):

    print "No settings.py file found. Run evennia.py to create it."
    sys.exit()

# Get the settings
from django.conf import settings

# Setup access of the evennia server itself
SERVER_PY_FILE = os.path.join(settings.SRC_DIR, 'server/server.py')
PORTAL_PY_FILE = os.path.join(settings.SRC_DIR, 'server/portal.py')

# Get logfile names
SERVER_LOGFILE = settings.SERVER_LOG_FILE
PORTAL_LOGFILE = settings.PORTAL_LOG_FILE

# Add this to the environmental variable for the 'twistd' command.
currpath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if 'PYTHONPATH' in os.environ:
    os.environ['PYTHONPATH'] += (":%s" % currpath)
else:
    os.environ['PYTHONPATH'] = currpath

TWISTED_BINARY = 'twistd'
if os.name == 'nt':
    TWISTED_BINARY = 'twistd.bat'
    err = False
    try:
        import win32api  # Test for for win32api
    except ImportError:
        err = True
    if not os.path.exists(TWISTED_BINARY):
        err = True
    if err:
        print "Twisted binary for Windows is not ready to use. Please run evennia.py."
        sys.exit()

# Functions

def set_restart_mode(restart_file, flag="reload"):
    """
    This sets a flag file for the restart mode.
    """
    with open(restart_file, 'w') as f:
        f.write(str(flag))

def get_restart_mode(restart_file):
    """
    Parse the server/portal restart status
    """
    if os.path.exists(restart_file):
        with open(restart_file, 'r') as f:
            return f.read()
    return "shutdown"

def get_pid(pidfile):
    """
    Get the PID (Process ID) by trying to access
    an PID file.
    """
    pid = None
    if os.path.exists(pidfile):
        with open(pidfile, 'r') as f:
            pid = f.read()
    return pid

def cycle_logfile(logfile):
    """
    Move the old log files to <filename>.old

    """
    logfile_old = logfile + '.old'
    if os.path.exists(logfile):
        # Cycle the old logfiles to *.old
        if os.path.exists(logfile_old):
            # E.g. Windows don't support rename-replace
            os.remove(logfile_old)
        os.rename(logfile, logfile_old)

    logfile = settings.HTTP_LOG_FILE.strip()
    logfile_old = logfile + '.old'
    if os.path.exists(logfile):
        # Cycle the old logfiles to *.old
        if os.path.exists(logfile_old):
            # E.g. Windows don't support rename-replace
            os.remove(logfile_old)
        os.rename(logfile, logfile_old)


# Start program management

SERVER = None
PORTAL = None

def start_services(server_argv, portal_argv):
    """
    This calls a threaded loop that launces the Portal and Server
    and then restarts them when they finish.
    """
    global SERVER, PORTAL

    processes = Queue.Queue()

    def server_waiter(queue):
        try:
            rc = Popen(server_argv).wait()
        except Exception, e:
            print "Server process error: %(e)s" % {'e': e}
            return
        queue.put(("server_stopped", rc)) # this signals the controller that the program finished

    def portal_waiter(queue):
        try:
            rc = Popen(portal_argv).wait()
        except Exception, e:
            print "Portal process error: %(e)s" % {'e': e}
            return
        queue.put(("portal_stopped", rc)) # this signals the controller that the program finished

    if portal_argv:
        try:
            if get_restart_mode(PORTAL_RESTART) == "True":
                # start portal as interactive, reloadable thread
                PORTAL = thread.start_new_thread(portal_waiter, (processes, ))
            else:
                # normal operation: start portal as a daemon; we don't care to monitor it for restart
                PORTAL = Popen(portal_argv)
        except IOError, e:
            print "Portal IOError: %s\nA possible explanation for this is that 'twistd' is not found." % e
            return

    try:
        if server_argv:
            # start server as a reloadable thread
            SERVER = thread.start_new_thread(server_waiter, (processes, ))
    except IOError, e:
        print "Server IOError: %s\nA possible explanation for this is that 'twistd' is not found." % e
        return

    # Reload loop
    while True:

        # this blocks until something is actually returned.
        message, rc = processes.get()

        # restart only if process stopped cleanly
        if message == "server_stopped" and int(rc) == 0 and get_restart_mode(SERVER_RESTART) in ("True", "reload", "reset"):
            print "Evennia Server stopped. Restarting ..."
            SERVER = thread.start_new_thread(server_waiter, (processes, ))
            continue

        # normally the portal is not reloaded since it's run as a daemon.
        if message == "portal_stopped" and int(rc) == 0 and get_restart_mode(PORTAL_RESTART) == "True":
            print "Evennia Portal stopped in interactive mode. Restarting ..."
            PORTAL = thread.start_new_thread(portal_waiter, (processes, ))
            continue
        break

# Setup signal handling

def main():
    """
    This handles the command line input of the runner (it's most often called by evennia.py)
    """

    parser = OptionParser(usage="%prog [options] start",
                          description="This runner should normally *not* be called directly - it is called automatically from the evennia.py main program. It manages the Evennia game server and portal processes an hosts a threaded loop to restart the Server whenever it is stopped (this constitues Evennia's reload mechanism).")
    parser.add_option('-s', '--noserver', action='store_true',
                      dest='noserver', default=False,
                      help='Do not start Server process')
    parser.add_option('-p', '--noportal', action='store_true',
                      dest='noportal', default=False,
                      help='Do not start Portal process')
    parser.add_option('-i', '--iserver', action='store_true',
                      dest='iserver', default=False,
                      help='output server log to stdout instead of logfile')
    parser.add_option('-d', '--iportal', action='store_true',
                      dest='iportal', default=False,
                      help='output portal log to stdout. Does not make portal a daemon.')
    parser.add_option('-S', '--profile-server', action='store_true',
                      dest='sprof', default=False,
                      help='run server under cProfile')
    parser.add_option('-P', '--profile-portal', action='store_true',
                      dest='pprof', default=False,
                      help='run portal under cProfile')

    options, args = parser.parse_args()

    if not args or args[0] != 'start':
        # this is so as to avoid runner.py be accidentally launched manually.
        parser.print_help()
        sys.exit()

    # set up default project calls
    server_argv = [TWISTED_BINARY,
                   '--nodaemon',
                   '--logfile=%s' % SERVER_LOGFILE,
                   '--pidfile=%s' % SERVER_PIDFILE,
                   '--python=%s' % SERVER_PY_FILE]
    portal_argv = [TWISTED_BINARY,
                   '--logfile=%s' % PORTAL_LOGFILE,
                   '--pidfile=%s' % PORTAL_PIDFILE,
                   '--python=%s' % PORTAL_PY_FILE]

    # Profiling settings (read file from python shell e.g with
    # p = pstats.Stats('server.prof')
    sprof_argv = ['--savestats',
                  '--profiler=cprofile',
                  '--profile=server.prof']
    pprof_argv = ['--savestats',
                  '--profiler=cprofile',
                  '--profile=portal.prof']

    # Server

    pid = get_pid(SERVER_PIDFILE)
    if pid and not options.noserver:
            print "\nEvennia Server is already running as process %(pid)s. Not restarted." % {'pid': pid}
            options.noserver = True
    if options.noserver:
        server_argv = None
    else:
        set_restart_mode(SERVER_RESTART, "shutdown")
        if options.iserver:
            # don't log to server logfile
            del server_argv[2]
            print "\nStarting Evennia Server (output to stdout)."
        else:
            cycle_logfile(SERVER_LOGFILE)
            print "\nStarting Evennia Server (output to server logfile)."
        if options.sprof:
            server_argv.extend(sprof_argv)
            print "\nRunning Evennia Server under cProfile."


    # Portal

    pid = get_pid(PORTAL_PIDFILE)
    if pid and not options.noportal:
        print "\nEvennia Portal is already running as process %(pid)s. Not restarted." % {'pid': pid}
        options.noportal = True
    if options.noportal:
        portal_argv = None
    else:
        if options.iportal:
            # make portal interactive
            portal_argv[1] = '--nodaemon'
            set_restart_mode(PORTAL_RESTART, True)
            print "\nStarting Evennia Portal in non-Daemon mode (output to stdout)."
        else:
            cycle_logfile(PORTAL_LOGFILE)
            set_restart_mode(PORTAL_RESTART, False)
            print "\nStarting Evennia Portal in Daemon mode (output to portal logfile)."
        if options.pprof:
            portal_argv.extend(pprof_argv)
            print "\nRunning Evennia Portal under cProfile."


    # Windows fixes (Windows don't support pidfiles natively)
    if os.name == 'nt':
        if server_argv:
            del server_argv[-2]
        if portal_argv:
            del portal_argv[-2]

    # Start processes
    start_services(server_argv, portal_argv)

if __name__ == '__main__':
    from src.utils.utils import check_evennia_dependencies
    if check_evennia_dependencies():
        main()
