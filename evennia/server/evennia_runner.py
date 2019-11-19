#!/usr/bin/env python
"""

This runner is controlled by the evennia launcher and should normally
not be launched directly.  It manages the two main Evennia processes
(Server and Portal) and most importantly runs a passive, threaded loop
that makes sure to restart Server whenever it shuts down.

Since twistd does not allow for returning an optional exit code we
need to handle the current reload state for server and portal with
flag-files instead. The files, one each for server and portal either
contains True or False indicating if the process should be restarted
upon returning, or not. A process returning != 0 will always stop, no
matter the value of this file.

"""

import os
import sys
from argparse import ArgumentParser
from subprocess import Popen
import queue
import _thread
import evennia

try:
    # check if launched with pypy
    import __pypy__ as is_pypy
except ImportError:
    is_pypy = False

SERVER = None
PORTAL = None

EVENNIA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENNIA_BIN = os.path.join(EVENNIA_ROOT, "bin")
EVENNIA_LIB = os.path.dirname(evennia.__file__)

SERVER_PY_FILE = os.path.join(EVENNIA_LIB, "server", "server.py")
PORTAL_PY_FILE = os.path.join(EVENNIA_LIB, "server", "portal", "portal.py")

GAMEDIR = None
SERVERDIR = "server"
SERVER_PIDFILE = None
PORTAL_PIDFILE = None
SERVER_RESTART = None
PORTAL_RESTART = None
SERVER_LOGFILE = None
PORTAL_LOGFILE = None
HTTP_LOGFILE = None
PPROFILER_LOGFILE = None
SPROFILER_LOGFILE = None

# messages

CMDLINE_HELP = """
    This program manages the running Evennia processes. It is called
    by evennia and should not be started manually. Its main task is to
    sit and watch the Server and restart it whenever the user reloads.
    The runner depends on four files for its operation, two PID files
    and two RESTART files for Server and Portal respectively; these
    are stored in the game's server/ directory.
    """

PROCESS_ERROR = """
    {component} process error: {traceback}.
    """

PROCESS_IOERROR = """
    {component} IOError: {traceback}
    One possible explanation is that 'twistd' was not found.
    """

PROCESS_RESTART = "{component} restarting ..."

PROCESS_DOEXIT = "Deferring to external runner."

# Functions


def set_restart_mode(restart_file, flag="reload"):
    """
    This sets a flag file for the restart mode.
    """
    with open(restart_file, "w") as f:
        f.write(str(flag))


def getenv():
    """
    Get current environment and add PYTHONPATH
    """
    sep = ";" if os.name == "nt" else ":"
    env = os.environ.copy()
    sys.path.insert(0, GAMEDIR)
    env["PYTHONPATH"] = sep.join(sys.path)
    return env


def get_restart_mode(restart_file):
    """
    Parse the server/portal restart status
    """
    if os.path.exists(restart_file):
        with open(restart_file, "r") as f:
            return f.read()
    return "shutdown"


def get_pid(pidfile):
    """
    Get the PID (Process ID) by trying to access
    an PID file.
    """
    pid = None
    if os.path.exists(pidfile):
        with open(pidfile, "r") as f:
            pid = f.read()
    return pid


def cycle_logfile(logfile):
    """
    Rotate the old log files to <filename>.old
    """
    logfile_old = logfile + ".old"
    if os.path.exists(logfile):
        # Cycle the old logfiles to *.old
        if os.path.exists(logfile_old):
            # E.g. Windows don't support rename-replace
            os.remove(logfile_old)
        os.rename(logfile, logfile_old)


# Start program management


def start_services(server_argv, portal_argv, doexit=False):
    """
    This calls a threaded loop that launches the Portal and Server
    and then restarts them when they finish.
    """
    global SERVER, PORTAL
    processes = queue.Queue()

    def server_waiter(queue):
        try:
            rc = Popen(server_argv, env=getenv()).wait()
        except Exception as e:
            print(PROCESS_ERROR.format(component="Server", traceback=e))
            return
        # this signals the controller that the program finished
        queue.put(("server_stopped", rc))

    def portal_waiter(queue):
        try:
            rc = Popen(portal_argv, env=getenv()).wait()
        except Exception as e:
            print(PROCESS_ERROR.format(component="Portal", traceback=e))
            return
        # this signals the controller that the program finished
        queue.put(("portal_stopped", rc))

    if portal_argv:
        try:
            if not doexit and get_restart_mode(PORTAL_RESTART) == "True":
                # start portal as interactive, reloadable thread
                PORTAL = _thread.start_new_thread(portal_waiter, (processes,))
            else:
                # normal operation: start portal as a daemon;
                # we don't care to monitor it for restart
                PORTAL = Popen(portal_argv, env=getenv())
        except IOError as e:
            print(PROCESS_IOERROR.format(component="Portal", traceback=e))
            return

    try:
        if server_argv:
            if doexit:
                SERVER = Popen(server_argv, env=getenv())
            else:
                # start server as a reloadable thread
                SERVER = _thread.start_new_thread(server_waiter, (processes,))
    except IOError as e:
        print(PROCESS_IOERROR.format(component="Server", traceback=e))
        return

    if doexit:
        # Exit immediately
        return

    # Reload loop
    while True:

        # this blocks until something is actually returned.
        from twisted.internet.error import ReactorNotRunning

        try:
            try:
                message, rc = processes.get()
            except KeyboardInterrupt:
                # this only matters in interactive mode
                break

            # restart only if process stopped cleanly
            if (
                message == "server_stopped"
                and int(rc) == 0
                and get_restart_mode(SERVER_RESTART) in ("True", "reload", "reset")
            ):
                print(PROCESS_RESTART.format(component="Server"))
                SERVER = _thread.start_new_thread(server_waiter, (processes,))
                continue

            # normally the portal is not reloaded since it's run as a daemon.
            if (
                message == "portal_stopped"
                and int(rc) == 0
                and get_restart_mode(PORTAL_RESTART) == "True"
            ):
                print(PROCESS_RESTART.format(component="Portal"))
                PORTAL = _thread.start_new_thread(portal_waiter, (processes,))
                continue
            break
        except ReactorNotRunning:
            break


def main():
    """
    This handles the command line input of the runner, usually created by
    the evennia launcher
    """

    parser = ArgumentParser(description=CMDLINE_HELP)
    parser.add_argument(
        "--noserver",
        action="store_true",
        dest="noserver",
        default=False,
        help="Do not start Server process",
    )
    parser.add_argument(
        "--noportal",
        action="store_true",
        dest="noportal",
        default=False,
        help="Do not start Portal process",
    )
    parser.add_argument(
        "--logserver",
        action="store_true",
        dest="logserver",
        default=False,
        help="Log Server output to logfile",
    )
    parser.add_argument(
        "--iserver",
        action="store_true",
        dest="iserver",
        default=False,
        help="Server in interactive mode",
    )
    parser.add_argument(
        "--iportal",
        action="store_true",
        dest="iportal",
        default=False,
        help="Portal in interactive mode",
    )
    parser.add_argument(
        "--pserver", action="store_true", dest="pserver", default=False, help="Profile Server"
    )
    parser.add_argument(
        "--pportal", action="store_true", dest="pportal", default=False, help="Profile Portal"
    )
    parser.add_argument(
        "--nologcycle",
        action="store_false",
        dest="nologcycle",
        default=True,
        help="Do not cycle log files",
    )
    parser.add_argument(
        "--doexit",
        action="store_true",
        dest="doexit",
        default=False,
        help="Immediately exit after processes have started.",
    )
    parser.add_argument("gamedir", help="path to game dir")
    parser.add_argument("twistdbinary", help="path to twistd binary")
    parser.add_argument("slogfile", help="path to server log file")
    parser.add_argument("plogfile", help="path to portal log file")
    parser.add_argument("hlogfile", help="path to http log file")

    args = parser.parse_args()

    global GAMEDIR
    global SERVER_LOGFILE, PORTAL_LOGFILE, HTTP_LOGFILE
    global SERVER_PIDFILE, PORTAL_PIDFILE
    global SERVER_RESTART, PORTAL_RESTART
    global SPROFILER_LOGFILE, PPROFILER_LOGFILE

    GAMEDIR = args.gamedir
    sys.path.insert(1, os.path.join(GAMEDIR, SERVERDIR))

    SERVER_PIDFILE = os.path.join(GAMEDIR, SERVERDIR, "server.pid")
    PORTAL_PIDFILE = os.path.join(GAMEDIR, SERVERDIR, "portal.pid")
    SERVER_RESTART = os.path.join(GAMEDIR, SERVERDIR, "server.restart")
    PORTAL_RESTART = os.path.join(GAMEDIR, SERVERDIR, "portal.restart")
    SERVER_LOGFILE = args.slogfile
    PORTAL_LOGFILE = args.plogfile
    HTTP_LOGFILE = args.hlogfile
    TWISTED_BINARY = args.twistdbinary
    SPROFILER_LOGFILE = os.path.join(GAMEDIR, SERVERDIR, "logs", "server.prof")
    PPROFILER_LOGFILE = os.path.join(GAMEDIR, SERVERDIR, "logs", "portal.prof")

    # set up default project calls
    server_argv = [
        TWISTED_BINARY,
        "--nodaemon",
        "--logfile=%s" % SERVER_LOGFILE,
        "--pidfile=%s" % SERVER_PIDFILE,
        "--python=%s" % SERVER_PY_FILE,
    ]
    portal_argv = [
        TWISTED_BINARY,
        "--logfile=%s" % PORTAL_LOGFILE,
        "--pidfile=%s" % PORTAL_PIDFILE,
        "--python=%s" % PORTAL_PY_FILE,
    ]

    # Profiling settings (read file from python shell e.g with
    # p = pstats.Stats('server.prof')
    pserver_argv = ["--savestats", "--profiler=cprofile", "--profile=%s" % SPROFILER_LOGFILE]
    pportal_argv = ["--savestats", "--profiler=cprofile", "--profile=%s" % PPROFILER_LOGFILE]

    # Server

    pid = get_pid(SERVER_PIDFILE)
    if pid and not args.noserver:
        print(
            "\nEvennia Server is already running as process %(pid)s. Not restarted." % {"pid": pid}
        )
        args.noserver = True
    if args.noserver:
        server_argv = None
    else:
        set_restart_mode(SERVER_RESTART, "shutdown")
        if not args.logserver:
            # don't log to server logfile
            del server_argv[2]
            print("\nStarting Evennia Server (output to stdout).")
        else:
            if not args.nologcycle:
                cycle_logfile(SERVER_LOGFILE)
            print("\nStarting Evennia Server (output to server logfile).")
        if args.pserver:
            server_argv.extend(pserver_argv)
            print("\nRunning Evennia Server under cProfile.")

    # Portal

    pid = get_pid(PORTAL_PIDFILE)
    if pid and not args.noportal:
        print(
            "\nEvennia Portal is already running as process %(pid)s. Not restarted." % {"pid": pid}
        )
        args.noportal = True
    if args.noportal:
        portal_argv = None
    else:
        if args.iportal:
            # make portal interactive
            portal_argv[1] = "--nodaemon"
            set_restart_mode(PORTAL_RESTART, True)
            print("\nStarting Evennia Portal in non-Daemon mode (output to stdout).")
        else:
            if not args.nologcycle:
                cycle_logfile(PORTAL_LOGFILE)
                cycle_logfile(HTTP_LOGFILE)
            set_restart_mode(PORTAL_RESTART, False)
            print("\nStarting Evennia Portal in Daemon mode (output to portal logfile).")
        if args.pportal:
            portal_argv.extend(pportal_argv)
            print("\nRunning Evennia Portal under cProfile.")
    if args.doexit:
        print(PROCESS_DOEXIT)

    # Windows fixes (Windows don't support pidfiles natively)
    if os.name == "nt":
        if server_argv:
            del server_argv[-2]
        if portal_argv:
            del portal_argv[-2]

    # Start processes
    start_services(server_argv, portal_argv, doexit=args.doexit)


if __name__ == "__main__":
    main()
