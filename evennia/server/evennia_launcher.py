#!/usr/bin/python
"""
Evennia launcher program

This is the start point for running Evennia.

Sets the appropriate environmental variables for managing an Evennia game. It will start and connect
to the Portal, through which the Server is also controlled. This pprogram

Run the script with the -h flag to see usage information.

"""

import os
import sys
import re
import signal
import shutil
import importlib
import pickle
from distutils.version import LooseVersion
from argparse import ArgumentParser
import argparse
from subprocess import Popen, check_output, call, CalledProcessError, STDOUT

from twisted.protocols import amp
from twisted.internet import reactor, endpoints
import django
from django.core.management import execute_from_command_line

# Signal processing
SIG = signal.SIGINT
CTRL_C_EVENT = 0  # Windows SIGINT-like signal

# Set up the main python paths to Evennia
EVENNIA_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import evennia  # noqa

EVENNIA_LIB = os.path.join(os.path.dirname(os.path.abspath(evennia.__file__)))
EVENNIA_SERVER = os.path.join(EVENNIA_LIB, "server")
EVENNIA_TEMPLATE = os.path.join(EVENNIA_LIB, "game_template")
EVENNIA_PROFILING = os.path.join(EVENNIA_SERVER, "profiling")
EVENNIA_DUMMYRUNNER = os.path.join(EVENNIA_PROFILING, "dummyrunner.py")

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
HTTP_LOGFILE = None

SERVER_PIDFILE = None
PORTAL_PIDFILE = None

SERVER_PY_FILE = None
PORTAL_PY_FILE = None

SPROFILER_LOGFILE = None
PPROFILER_LOGFILE = None

TEST_MODE = False
ENFORCED_SETTING = False

REACTOR_RUN = False
NO_REACTOR_STOP = False

# communication constants

AMP_PORT = None
AMP_HOST = None
AMP_INTERFACE = None
AMP_CONNECTION = None

SRELOAD = chr(14)  # server reloading (have portal start a new server)
SSTART = chr(15)  # server start
PSHUTD = chr(16)  # portal (+server) shutdown
SSHUTD = chr(17)  # server-only shutdown
PSTATUS = chr(18)  # ping server or portal status
SRESET = chr(19)  # shutdown server in reset mode

# requirements
PYTHON_MIN = "3.7"
TWISTED_MIN = "18.0.0"
DJANGO_MIN = "2.1"
DJANGO_REC = "2.2.5"

try:
    sys.path[1] = EVENNIA_ROOT
except IndexError:
    sys.path.append(EVENNIA_ROOT)

# ------------------------------------------------------------
#
# Messages
#
# ------------------------------------------------------------

CREATED_NEW_GAMEDIR = """
    Welcome to Evennia!
    Created a new Evennia game directory '{gamedir}'.

    You can now optionally edit your new settings file
    at {settings_path}. If you don't, the defaults
    will work out of the box. When ready to continue, 'cd' to your
    game directory and run:

       evennia migrate

    This initializes the database. To start the server for the first
    time, run:

       evennia start

    Make sure to create a superuser when asked for it (the email is optional)
    You should now be able to connect to your server on 'localhost', port 4000
    using a telnet/mud client or http://localhost:4001 using your web browser.
    If things don't work, check the log with `evennia --log`. Also make sure
    ports are open.

    (Finally, why not run `evennia connections` and make the world aware of
    your new Evennia project!)
    """

ERROR_INPUT = """
    Command
      {args} {kwargs}
    raised an error: '{traceback}'.
"""

ERROR_NO_ALT_GAMEDIR = """
    The path '{gamedir}' could not be found.
"""

ERROR_NO_GAMEDIR = """
    ERROR: No Evennia settings file was found. Evennia looks for the
    file in your game directory as ./server/conf/settings.py.

    You must run this command from somewhere inside a valid game
    directory first created with

        evennia --init mygamename

    If you are in a game directory but is missing a settings.py file,
    it may be because you have git-cloned an existing game directory.
    The settings.py file is not cloned by git (it's in .gitignore)
    since it can contain sensitive and/or server-specific information.
    You can create a new, empty settings file with

        evennia --initsettings

    If cloning the settings file is not a problem you could manually
    copy over the old settings file or remove its entry in .gitignore

    """

WARNING_MOVING_SUPERUSER = """
    WARNING: Evennia expects an Account superuser with id=1. No such
    Account was found. However, another superuser ('{other_key}',
    id={other_id}) was found in the database. If you just created this
    superuser and still see this text it is probably due to the
    database being flushed recently - in this case the database's
    internal auto-counter might just start from some value higher than
    one.

    We will fix this by assigning the id 1 to Account '{other_key}'.
    Please confirm this is acceptable before continuing.
    """

WARNING_RUNSERVER = """
    WARNING: There is no need to run the Django development
    webserver to test out Evennia web features (the web client
    will in fact not work since the Django test server knows
    nothing about MUDs).  Instead, just start Evennia with the
    webserver component active (this is the default).
    """

ERROR_SETTINGS = """
    ERROR: There was an error importing Evennia's config file
    {settingspath}.
    There is usually one of three reasons for this:
        1) You are not running this command from your game directory.
           Change directory to your game directory and try again (or
           create a new game directory using evennia --init <dirname>)
        2) The settings file contains a syntax error. If you see a
           traceback above, review it, resolve the problem and try again.
        3) Django is not correctly installed. This usually shows as
           errors mentioning 'DJANGO_SETTINGS_MODULE'. If you run a
           virtual machine, it might be worth to restart it to see if
           this resolves the issue.
    """.format(
    settingspath=SETTINGS_PATH
)

ERROR_INITSETTINGS = """
    ERROR: 'evennia --initsettings' must be called from the root of
    your game directory, since it tries to (re)create the new
    settings.py file in a subfolder server/conf/.
    """

RECREATED_SETTINGS = """
    (Re)created an empty settings file in server/conf/settings.py.

    Note that if you were using an existing database, the password
    salt of this new settings file will be different from the old one.
    This means that any existing accounts may not be able to log in to
    their accounts with their old passwords.
    """

ERROR_INITMISSING = """
    ERROR: 'evennia --initmissing' must be called from the root of
    your game directory, since it tries to create any missing files
    in the server/ subfolder.
    """

RECREATED_MISSING = """
    (Re)created any missing directories or files.  Evennia should
    be ready to run now!
    """

ERROR_DATABASE = """
    ERROR: Your database does not exist or is not set up correctly.
    (error was '{traceback}')

    If you think your database should work, make sure you are running your
    commands from inside your game directory. If this error persists, run

       evennia migrate

    to initialize/update the database according to your settings.
    """

ERROR_WINDOWS_WIN32API = """
    ERROR: Unable to import win32api, which Twisted requires to run.
    You may download it from:

    http://sourceforge.net/projects/pywin32/files/pywin32/

    If you are running in a virtual environment, browse to the
    location of the latest win32api exe file for your computer and
    Python version and copy the url to it; then paste it into a call
    to easy_install:

        easy_install http://<url to win32api exe>
    """

INFO_WINDOWS_BATFILE = """
    INFO: Since you are running Windows, a file 'twistd.bat' was
    created for you. This is a simple batch file that tries to call
    the twisted executable. Evennia determined this to be:

       {twistd_path}

    If you run into errors at startup you might need to edit
    twistd.bat to point to the actual location of the Twisted
    executable (usually called twistd.py) on your machine.

    This procedure is only done once. Run `evennia` again when you
    are ready to start the server.
    """

CMDLINE_HELP = """Starts, initializes, manages and operates the Evennia MU* server.
Most standard django management commands are also accepted."""


VERSION_INFO = """
    Evennia {version}
    OS: {os}
    Python: {python}
    Twisted: {twisted}
    Django: {django}{about}
    """

ABOUT_INFO = """
    Evennia MUD/MUX/MU* development system

    Licence: BSD 3-Clause Licence
    Web: http://www.evennia.com
    Irc: #evennia on FreeNode
    Forum: http://www.evennia.com/discussions
    Maintainer (2006-10): Greg Taylor
    Maintainer (2010-):   Griatch (griatch AT gmail DOT com)

    Use -h for command line options.
    """

HELP_ENTRY = """
    Evennia has two processes, the 'Server' and the 'Portal'.
    External users connect to the Portal while the Server runs the
    game/database. Restarting the Server will refresh code but not
    disconnect users.

    To start a new game, use 'evennia --init mygame'.
    For more ways to operate and manage Evennia, see 'evennia -h'.

    If you want to add unit tests to your game, see
        https://github.com/evennia/evennia/wiki/Unit-Testing

    Evennia's manual is found here:
        https://github.com/evennia/evennia/wiki
    """

MENU = """
    +----Evennia Launcher-------------------------------------------+
    {gameinfo}
    +--- Common operations -----------------------------------------+
    |  1) Start                       (also restart stopped Server) |
    |  2) Reload               (stop/start Server in 'reload' mode) |
    |  3) Stop                         (shutdown Portal and Server) |
    |  4) Reboot                            (shutdown then restart) |
    +--- Other operations ------------------------------------------+
    |  5) Reset              (stop/start Server in 'shutdown' mode) |
    |  6) Stop Server only                                          |
    |  7) Kill Server only            (send kill signal to process) |
    |  8) Kill Portal + Server                                      |
    +--- Information -----------------------------------------------+
    |  9) Tail log files      (quickly see errors - Ctrl-C to exit) |
    | 10) Status                                                    |
    | 11) Port info                                                 |
    +--- Testing ---------------------------------------------------+
    | 12) Test gamedir             (run gamedir test suite, if any) |
    | 13) Test Evennia                     (run Evennia test suite) |
    +---------------------------------------------------------------+
    |  h) Help               i) About info                q) Abort  |
    +---------------------------------------------------------------+"""

ERROR_AMP_UNCONFIGURED = """
    Can't find server info for connecting. Either run this command from
    the game dir (it will then use the game's settings file) or specify
    the path to your game's settings file manually with the --settings
    option.
    """

ERROR_LOGDIR_MISSING = """
    ERROR: One or more log-file directory locations could not be
    found:

    {logfiles}

    This is simple to fix: Just manually create the missing log
    directory (or directories) and re-launch the server (the log files
    will be created automatically).

    (Explanation: Evennia creates the log directory automatically when
    initializing a new game directory. This error usually happens if
    you used git to clone a pre-created game directory - since log
    files are in .gitignore they will not be cloned, which leads to
    the log directory also not being created.)
    """

ERROR_PYTHON_VERSION = """
    ERROR: Python {pversion} used. Evennia requires version
    {python_min} or higher.
    """

ERROR_TWISTED_VERSION = """
    ERROR: Twisted {tversion} found. Evennia requires
    version {twisted_min} or higher.
    """

ERROR_NOTWISTED = """
    ERROR: Twisted does not seem to be installed.
    """

ERROR_DJANGO_MIN = """
    ERROR: Django {dversion} found. Evennia requires version {django_min}
    or higher.

    If you are using a virtualenv, use the command `pip install --upgrade -e evennia` where
    `evennia` is the folder to where you cloned the Evennia library. If not
    in a virtualenv you can install django with for example `pip install --upgrade django`
    or with `pip install django=={django_min}` to get a specific version.

    It's also a good idea to run `evennia migrate` after this upgrade. Ignore
    any warnings and don't run `makemigrate` even if told to.
    """

NOTE_DJANGO_MIN = """
    NOTE: Django {dversion} found. This will work, but Django {django_rec} is
    recommended for production.
    """

NOTE_DJANGO_NEW = """
    NOTE: Django {dversion} found. This is newer than Evennia's
    recommended version ({django_rec}). It might work, but may be new
    enough to not be fully tested yet. Report any issues.
    """

ERROR_NODJANGO = """
    ERROR: Django does not seem to be installed.
    """

NOTE_KEYBOARDINTERRUPT = """
    STOP: Caught keyboard interrupt while in interactive mode.
    """

NOTE_TEST_DEFAULT = """
    TESTING: Using Evennia's default settings file (evennia.settings_default).
    (use 'evennia test --settings settings.py .' to run only your custom game tests)
    """

NOTE_TEST_CUSTOM = """
    TESTING: Using specified settings file '{settings_dotpath}'.

    OBS: Evennia's full test suite may not pass if the settings are very
    different from the default (use 'evennia test evennia' to run core tests)
    """

PROCESS_ERROR = """
    {component} process error: {traceback}.
    """

PORTAL_INFO = """{servername} Portal {version}
    external ports:
        {telnet}
        {telnet_ssl}
        {ssh}
        {webserver_proxy}
        {webclient}
    internal_ports (to Server):
        {webserver_internal}
        {amp}
"""


SERVER_INFO = """{servername} Server {version}
    internal ports (to Portal):
        {webserver}
        {amp}
    {irc_rss}
    {info}
    {errors}"""


ARG_OPTIONS = """Actions on installed server. One of:
 start       - launch server+portal if not running
 reload      - restart server in 'reload' mode
 stop        - shutdown server+portal
 reboot      - shutdown server+portal, then start again
 reset       - restart server in 'shutdown' mode
 istart      - start server in foreground (until reload)
 ipstart     - start portal in foreground
 sstop       - stop only server
 kill        - send kill signal to portal+server (force)
 skill       - send kill signal only to server
 status      - show server and portal run state
 info        - show server and portal port info
 menu        - show a menu of options
 connections - show connection wizard
Others, like migrate, test and shell is passed on to Django."""

# ------------------------------------------------------------
#
# Private helper functions
#
# ------------------------------------------------------------


def _is_windows():
    return os.name == "nt"


def _file_names_compact(filepath1, filepath2):
    "Compact the output of filenames with same base dir"
    dirname1 = os.path.dirname(filepath1)
    dirname2 = os.path.dirname(filepath2)
    if dirname1 == dirname2:
        name2 = os.path.basename(filepath2)
        return "{} and {}".format(filepath1, name2)
    else:
        return "{} and {}".format(filepath1, filepath2)


def _print_info(portal_info_dict, server_info_dict):
    """
    Format info dicts from the Portal/Server for display

    """
    ind = " " * 8

    def _prepare_dict(dct):
        out = {}
        for key, value in dct.items():
            if isinstance(value, list):
                value = "\n{}".format(ind).join(str(val) for val in value)
            out[key] = value
        return out

    def _strip_empty_lines(string):
        return "\n".join(line for line in string.split("\n") if line.strip())

    pstr, sstr = "", ""
    if portal_info_dict:
        pdict = _prepare_dict(portal_info_dict)
        pstr = _strip_empty_lines(PORTAL_INFO.format(**pdict))

    if server_info_dict:
        sdict = _prepare_dict(server_info_dict)
        sstr = _strip_empty_lines(SERVER_INFO.format(**sdict))

    info = pstr + ("\n\n" + sstr if sstr else "")
    maxwidth = max(len(line) for line in info.split("\n"))
    top_border = "-" * (maxwidth - 11) + " Evennia " + "---"
    border = "-" * (maxwidth + 1)
    print(top_border + "\n" + info + "\n" + border)


def _parse_status(response):
    "Unpack the status information"
    return pickle.loads(response["status"])


def _get_twistd_cmdline(pprofiler, sprofiler):
    """
    Compile the command line for starting a Twisted application using the 'twistd' executable.

    """
    portal_cmd = [TWISTED_BINARY, "--python={}".format(PORTAL_PY_FILE)]
    server_cmd = [TWISTED_BINARY, "--python={}".format(SERVER_PY_FILE)]

    if os.name != "nt":
        # PID files only for UNIX
        portal_cmd.append("--pidfile={}".format(PORTAL_PIDFILE))
        server_cmd.append("--pidfile={}".format(SERVER_PIDFILE))

    if pprofiler:
        portal_cmd.extend(
            ["--savestats", "--profiler=cprofile", "--profile={}".format(PPROFILER_LOGFILE)]
        )
    if sprofiler:
        server_cmd.extend(
            ["--savestats", "--profiler=cprofile", "--profile={}".format(SPROFILER_LOGFILE)]
        )

    return portal_cmd, server_cmd


def _reactor_stop():
    if not NO_REACTOR_STOP:
        reactor.stop()


# ------------------------------------------------------------
#
#  Protocol Evennia launcher - Portal/Server communication
#
# ------------------------------------------------------------


class MsgStatus(amp.Command):
    """
    Ping between AMP services

    """

    key = "MsgStatus"
    arguments = [(b"status", amp.String())]
    errors = {Exception: b"EXCEPTION"}
    response = [(b"status", amp.String())]


class MsgLauncher2Portal(amp.Command):
    """
    Message Launcher -> Portal

    """

    key = "MsgLauncher2Portal"
    arguments = [(b"operation", amp.String()), (b"arguments", amp.String())]
    errors = {Exception: b"EXCEPTION"}
    response = []


class AMPLauncherProtocol(amp.AMP):
    """
    Defines callbacks to the launcher

    """

    def __init__(self):
        self.on_status = []

    def wait_for_status(self, callback):
        """
        Register a waiter for a status return.

        """
        self.on_status.append(callback)

    @MsgStatus.responder
    def receive_status_from_portal(self, status):
        """
        Get a status signal from portal - fire next queued
        callback

        """
        try:
            callback = self.on_status.pop()
        except IndexError:
            pass
        else:
            status = pickle.loads(status)
            callback(status)
        return {"status": pickle.dumps(b"")}


def send_instruction(operation, arguments, callback=None, errback=None):
    """
    Send instruction and handle the response.

    """
    global AMP_CONNECTION, REACTOR_RUN

    if None in (AMP_HOST, AMP_PORT, AMP_INTERFACE):
        print(ERROR_AMP_UNCONFIGURED)
        sys.exit()

    def _callback(result):
        if callback:
            callback(result)

    def _errback(fail):
        if errback:
            errback(fail)

    def _on_connect(prot):
        """
        This fires with the protocol when connection is established. We
        immediately send off the instruction

        """
        global AMP_CONNECTION
        AMP_CONNECTION = prot
        _send()

    def _on_connect_fail(fail):
        "This is called if portal is not reachable."
        errback(fail)

    def _send():
        if operation == PSTATUS:
            return AMP_CONNECTION.callRemote(MsgStatus, status=b"").addCallbacks(
                _callback, _errback
            )
        else:
            return AMP_CONNECTION.callRemote(
                MsgLauncher2Portal,
                operation=bytes(operation, "utf-8"),
                arguments=pickle.dumps(arguments, pickle.HIGHEST_PROTOCOL),
            ).addCallbacks(_callback, _errback)

    if AMP_CONNECTION:
        # already connected - send right away
        return _send()
    else:
        # we must connect first, send once connected
        point = endpoints.TCP4ClientEndpoint(reactor, AMP_HOST, AMP_PORT)
        deferred = endpoints.connectProtocol(point, AMPLauncherProtocol())
        deferred.addCallbacks(_on_connect, _on_connect_fail)
        REACTOR_RUN = True
        return deferred


def query_status(callback=None):
    """
    Send status ping to portal

    """
    wmap = {True: "RUNNING", False: "NOT RUNNING"}

    def _callback(response):
        if callback:
            callback(response)
        else:
            pstatus, sstatus, ppid, spid, pinfo, sinfo = _parse_status(response)
            print(
                "Portal: {}{}\nServer: {}{}".format(
                    wmap[pstatus],
                    " (pid {})".format(get_pid(PORTAL_PIDFILE, ppid)) if pstatus else "",
                    wmap[sstatus],
                    " (pid {})".format(get_pid(SERVER_PIDFILE, spid)) if sstatus else "",
                )
            )
            _reactor_stop()

    def _errback(fail):
        pstatus, sstatus = False, False
        print("Portal: {}\nServer: {}".format(wmap[pstatus], wmap[sstatus]))
        _reactor_stop()

    send_instruction(PSTATUS, None, _callback, _errback)


def wait_for_status_reply(callback):
    """
    Wait for an explicit STATUS signal to be sent back from Evennia.
    """
    if AMP_CONNECTION:
        AMP_CONNECTION.wait_for_status(callback)
    else:
        print("No Evennia connection established.")


def wait_for_status(
    portal_running=True, server_running=True, callback=None, errback=None, rate=0.5, retries=20
):
    """
    Repeat the status ping until the desired state combination is achieved.

    Args:
        portal_running (bool or None): Desired portal run-state. If None, any state
            is accepted.
        server_running (bool or None): Desired server run-state. If None, any state
            is accepted. The portal must be running.
        callback (callable): Will be called with portal_state, server_state when
            condition is fulfilled.
        errback (callable): Will be called with portal_state, server_state if the
            request is timed out.
        rate (float): How often to retry.
        retries (int): How many times to retry before timing out and calling `errback`.
    """

    def _callback(response):
        prun, srun, _, _, _, _ = _parse_status(response)
        if (portal_running is None or prun == portal_running) and (
            server_running is None or srun == server_running
        ):
            # the correct state was achieved
            if callback:
                callback(prun, srun)
            else:
                _reactor_stop()
        else:
            if retries <= 0:
                if errback:
                    errback(prun, srun)
                else:
                    print("Connection to Evennia timed out. Try again.")
                    _reactor_stop()
            else:
                reactor.callLater(
                    rate,
                    wait_for_status,
                    portal_running,
                    server_running,
                    callback,
                    errback,
                    rate,
                    retries - 1,
                )

    def _errback(fail):
        """
        Portal not running
        """
        if not portal_running:
            # this is what we want
            if callback:
                callback(portal_running, server_running)
            else:
                _reactor_stop()
        else:
            if retries <= 0:
                if errback:
                    errback(portal_running, server_running)
                else:
                    print("Connection to Evennia timed out. Try again.")
                    _reactor_stop()
            else:
                reactor.callLater(
                    rate,
                    wait_for_status,
                    portal_running,
                    server_running,
                    callback,
                    errback,
                    rate,
                    retries - 1,
                )

    return send_instruction(PSTATUS, None, _callback, _errback)


# ------------------------------------------------------------
#
#  Operational functions
#
# ------------------------------------------------------------


def collectstatic():
    "Run the collectstatic django command"
    django.core.management.call_command("collectstatic", interactive=False, verbosity=0)


def start_evennia(pprofiler=False, sprofiler=False):
    """
    This will start Evennia anew by launching the Evennia Portal (which in turn
    will start the Server)

    """
    portal_cmd, server_cmd = _get_twistd_cmdline(pprofiler, sprofiler)

    def _fail(fail):
        print(fail)
        _reactor_stop()

    def _server_started(response):
        print("... Server started.\nEvennia running.")
        if response:
            _, _, _, _, pinfo, sinfo = response
            _print_info(pinfo, sinfo)
        _reactor_stop()

    def _portal_started(*args):
        print(
            "... Portal started.\nServer starting {} ...".format(
                "(under cProfile)" if sprofiler else ""
            )
        )
        wait_for_status_reply(_server_started)
        send_instruction(SSTART, server_cmd)

    def _portal_running(response):
        prun, srun, ppid, spid, _, _ = _parse_status(response)
        print("Portal is already running as process {pid}. Not restarted.".format(pid=ppid))
        if srun:
            print("Server is already running as process {pid}. Not restarted.".format(pid=spid))
            _reactor_stop()
        else:
            print("Server starting {}...".format("(under cProfile)" if sprofiler else ""))
            send_instruction(SSTART, server_cmd, _server_started, _fail)

    def _portal_not_running(fail):
        print("Portal starting {}...".format("(under cProfile)" if pprofiler else ""))
        try:
            if _is_windows():
                # Windows requires special care
                create_no_window = 0x08000000
                Popen(portal_cmd, env=getenv(), bufsize=-1, creationflags=create_no_window)
            else:
                Popen(portal_cmd, env=getenv(), bufsize=-1)
        except Exception as e:
            print(PROCESS_ERROR.format(component="Portal", traceback=e))
            _reactor_stop()
        wait_for_status(True, None, _portal_started)

    collectstatic()
    send_instruction(PSTATUS, None, _portal_running, _portal_not_running)


def reload_evennia(sprofiler=False, reset=False):
    """
    This will instruct the Portal to reboot the Server component. We
    do this manually by telling the server to shutdown (in reload mode)
    and wait for the portal to report back, at which point we start the
    server again. This way we control the process exactly.

    """
    _, server_cmd = _get_twistd_cmdline(False, sprofiler)

    def _server_restarted(*args):
        print("... Server re-started.")
        _reactor_stop()

    def _server_reloaded(status):
        print("... Server {}.".format("reset" if reset else "reloaded"))
        _reactor_stop()

    def _server_stopped(status):
        wait_for_status_reply(_server_reloaded)
        send_instruction(SSTART, server_cmd)

    def _portal_running(response):
        _, srun, _, _, _, _ = _parse_status(response)
        if srun:
            print("Server {}...".format("resetting" if reset else "reloading"))
            wait_for_status_reply(_server_stopped)
            send_instruction(SRESET if reset else SRELOAD, {})
        else:
            print("Server down. Re-starting ...")
            wait_for_status_reply(_server_restarted)
            send_instruction(SSTART, server_cmd)

    def _portal_not_running(fail):
        print("Evennia not running. Starting up ...")
        start_evennia()

    collectstatic()
    send_instruction(PSTATUS, None, _portal_running, _portal_not_running)


def stop_evennia():
    """
    This instructs the Portal to stop the Server and then itself.

    """

    def _portal_stopped(*args):
        print("... Portal stopped.\nEvennia shut down.")
        _reactor_stop()

    def _server_stopped(*args):
        print("... Server stopped.\nStopping Portal ...")
        send_instruction(PSHUTD, {})
        wait_for_status(False, None, _portal_stopped)

    def _portal_running(response):
        prun, srun, ppid, spid, _, _ = _parse_status(response)
        if srun:
            print("Server stopping ...")
            send_instruction(SSHUTD, {})
            wait_for_status_reply(_server_stopped)
        else:
            print("Server already stopped.\nStopping Portal ...")
            send_instruction(PSHUTD, {})
            wait_for_status(False, None, _portal_stopped)

    def _portal_not_running(fail):
        print("Evennia not running.")
        _reactor_stop()

    send_instruction(PSTATUS, None, _portal_running, _portal_not_running)


def reboot_evennia(pprofiler=False, sprofiler=False):
    """
    This is essentially an evennia stop && evennia start except we make sure
    the system has successfully shut down before starting it again.

    If evennia was not running, start it.

    """
    global AMP_CONNECTION

    def _portal_stopped(*args):
        print("... Portal stopped. Evennia shut down. Rebooting ...")
        global AMP_CONNECTION
        AMP_CONNECTION = None
        start_evennia(pprofiler, sprofiler)

    def _server_stopped(*args):
        print("... Server stopped.\nStopping Portal ...")
        send_instruction(PSHUTD, {})
        wait_for_status(False, None, _portal_stopped)

    def _portal_running(response):
        prun, srun, ppid, spid, _, _ = _parse_status(response)
        if srun:
            print("Server stopping ...")
            send_instruction(SSHUTD, {})
            wait_for_status_reply(_server_stopped)
        else:
            print("Server already stopped.\nStopping Portal ...")
            send_instruction(PSHUTD, {})
            wait_for_status(False, None, _portal_stopped)

    def _portal_not_running(fail):
        print("Evennia not running. Starting up ...")
        start_evennia()

    collectstatic()
    send_instruction(PSTATUS, None, _portal_running, _portal_not_running)


def start_only_server():
    """
    Tell portal to start server (debug)
    """
    portal_cmd, server_cmd = _get_twistd_cmdline(False, False)
    print("launcher: Sending to portal: SSTART + {}".format(server_cmd))
    collectstatic()
    send_instruction(SSTART, server_cmd)


def start_server_interactive():
    """
    Start the Server under control of the launcher process (foreground)

    """

    def _iserver():
        _, server_twistd_cmd = _get_twistd_cmdline(False, False)
        server_twistd_cmd.append("--nodaemon")
        print("Starting Server in interactive mode (stop with Ctrl-C)...")
        try:
            Popen(server_twistd_cmd, env=getenv(), stderr=STDOUT).wait()
        except KeyboardInterrupt:
            print("... Stopped Server with Ctrl-C.")
        else:
            print("... Server stopped (leaving interactive mode).")

    collectstatic()
    stop_server_only(when_stopped=_iserver, interactive=True)


def start_portal_interactive():
    """
    Start the Portal under control of the launcher process (foreground)

    Notes:
        In a normal start, the launcher waits for the Portal to start, then
        tells it to start the Server. Since we can't do this here, we instead
        start the Server first and then starts the Portal - the Server will
        auto-reconnect to the Portal. To allow the Server to be reloaded, this
        relies on a fixed server server-cmdline stored as a fallback on the
        portal application in evennia/server/portal/portal.py.

    """

    def _iportal(fail):
        portal_twistd_cmd, server_twistd_cmd = _get_twistd_cmdline(False, False)
        portal_twistd_cmd.append("--nodaemon")

        # starting Server first - it will auto-connect once Portal comes up
        if _is_windows():
            # Windows requires special care
            create_no_window = 0x08000000
            Popen(server_twistd_cmd, env=getenv(), bufsize=-1, creationflags=create_no_window)
        else:
            Popen(server_twistd_cmd, env=getenv(), bufsize=-1)

        print("Starting Portal in interactive mode (stop with Ctrl-C)...")
        try:
            Popen(portal_twistd_cmd, env=getenv(), stderr=STDOUT).wait()
        except KeyboardInterrupt:
            print("... Stopped Portal with Ctrl-C.")
        else:
            print("... Portal stopped (leaving interactive mode).")

    def _portal_running(response):
        print("Evennia must be shut down completely before running Portal in interactive mode.")
        _reactor_stop()

    send_instruction(PSTATUS, None, _portal_running, _iportal)


def stop_server_only(when_stopped=None, interactive=False):
    """
    Only stop the Server-component of Evennia (this is not useful except for debug)

    Args:
        when_stopped (callable): This will be called with no arguments when Server has stopped (or
            if it had already stopped when this is called).
        interactive (bool, optional): Set if this is called as part of the interactive reload
            mechanism.

    """

    def _server_stopped(*args):
        if when_stopped:
            when_stopped()
        else:
            print("... Server stopped.")
            _reactor_stop()

    def _portal_running(response):
        _, srun, _, _, _, _ = _parse_status(response)
        if srun:
            print("Server stopping ...")
            wait_for_status_reply(_server_stopped)
            if interactive:
                send_instruction(SRELOAD, {})
            else:
                send_instruction(SSHUTD, {})
        else:
            if when_stopped:
                when_stopped()
            else:
                print("Server is not running.")
                _reactor_stop()

    def _portal_not_running(fail):
        print("Evennia is not running.")
        if interactive:
            print("Start Evennia normally first, then use `istart` to switch to interactive mode.")
        _reactor_stop()

    send_instruction(PSTATUS, None, _portal_running, _portal_not_running)


def query_info():
    """
    Display the info strings from the running Evennia

    """

    def _got_status(status):
        _, _, _, _, pinfo, sinfo = _parse_status(status)
        _print_info(pinfo, sinfo)
        _reactor_stop()

    def _portal_running(response):
        query_status(_got_status)

    def _portal_not_running(fail):
        print("Evennia is not running.")

    send_instruction(PSTATUS, None, _portal_running, _portal_not_running)


def tail_log_files(filename1, filename2, start_lines1=20, start_lines2=20, rate=1):
    """
    Tail two logfiles interactively, combining their output to stdout

    When first starting, this will display the tail of the log files. After
    that it will poll the log files repeatedly and display changes.

    Args:
        filename1 (str): Path to first log file.
        filename2 (str): Path to second log file.
        start_lines1 (int): How many lines to show from existing first log.
        start_lines2 (int): How many lines to show from existing second log.
        rate (int, optional): How often to poll the log file.

    """
    global REACTOR_RUN

    def _file_changed(filename, prev_size):
        "Get size of file in bytes, get diff compared with previous size"
        try:
            new_size = os.path.getsize(filename)
        except FileNotFoundError:
            return False, 0
        return new_size != prev_size, new_size

    def _get_new_lines(filehandle, old_linecount):
        "count lines, get the ones not counted before"

        def _block(filehandle, size=65536):
            "File block generator for quick traversal"
            while True:
                dat = filehandle.read(size)
                if not dat:
                    break
                yield dat

        # count number of lines in file
        new_linecount = sum(blck.count("\n") for blck in _block(filehandle))

        if new_linecount < old_linecount:
            # this happens if the file was cycled or manually deleted/edited.
            print(
                " ** Log file {filename} has cycled or been edited. "
                "Restarting log. ".format(filehandle.name)
            )
            new_linecount = 0
            old_linecount = 0

        lines_to_get = max(0, new_linecount - old_linecount)

        if not lines_to_get:
            return [], old_linecount

        lines_found = []
        buffer_size = 4098
        block_count = -1

        while len(lines_found) < lines_to_get:
            try:
                # scan backwards in file, starting from the end
                filehandle.seek(block_count * buffer_size, os.SEEK_END)
            except IOError:
                # file too small for current seek, include entire file
                filehandle.seek(0)
                lines_found = filehandle.readlines()
                break
            lines_found = filehandle.readlines()
            block_count -= 1

        # only actually return the new lines
        return lines_found[-lines_to_get:], new_linecount

    def _tail_file(filename, file_size, line_count, max_lines=None):
        """This will cycle repeatedly, printing new lines"""

        # poll for changes
        has_changed, file_size = _file_changed(filename, file_size)

        if has_changed:
            try:
                with open(filename, "r") as filehandle:
                    new_lines, line_count = _get_new_lines(filehandle, line_count)
            except IOError:
                # the log file might not exist yet. Wait a little, then try again ...
                pass
            else:
                if max_lines == 0:
                    # don't show any lines from old file
                    new_lines = []
                elif max_lines:
                    # show some lines from first startup
                    new_lines = new_lines[-max_lines:]

                # print to stdout without line break (log has its own line feeds)
                sys.stdout.write("".join(new_lines))
                sys.stdout.flush()

        # set up the next poll
        reactor.callLater(rate, _tail_file, filename, file_size, line_count, max_lines=100)

    reactor.callLater(0, _tail_file, filename1, 0, 0, max_lines=start_lines1)
    reactor.callLater(0, _tail_file, filename2, 0, 0, max_lines=start_lines2)

    REACTOR_RUN = True


# ------------------------------------------------------------
#
# Environment setup
#
# ------------------------------------------------------------


def evennia_version():
    """
    Get the Evennia version info from the main package.

    """
    version = "Unknown"
    try:
        version = evennia.__version__
    except ImportError:
        # even if evennia is not found, we should not crash here.
        pass
    try:
        rev = (
            check_output("git rev-parse --short HEAD", shell=True, cwd=EVENNIA_ROOT, stderr=STDOUT)
            .strip()
            .decode()
        )
        version = "%s (rev %s)" % (version, rev)
    except (IOError, CalledProcessError, OSError):
        # move on if git is not answering
        pass
    return version


EVENNIA_VERSION = evennia_version()


def check_main_evennia_dependencies():
    """
    Checks and imports the Evennia dependencies. This must be done
    already before the paths are set up.

    Returns:
        not_error (bool): True if no dependency error was found.

    """
    error = False

    # Python
    pversion = ".".join(str(num) for num in sys.version_info if isinstance(num, int))
    if LooseVersion(pversion) < LooseVersion(PYTHON_MIN):
        print(ERROR_PYTHON_VERSION.format(pversion=pversion, python_min=PYTHON_MIN))
        error = True
    # Twisted
    try:
        import twisted

        tversion = twisted.version.short()
        if LooseVersion(tversion) < LooseVersion(TWISTED_MIN):
            print(ERROR_TWISTED_VERSION.format(tversion=tversion, twisted_min=TWISTED_MIN))
            error = True
    except ImportError:
        print(ERROR_NOTWISTED)
        error = True
    # Django
    try:
        dversion = ".".join(str(num) for num in django.VERSION if isinstance(num, int))
        # only the main version (1.5, not 1.5.4.0)
        dversion_main = ".".join(dversion.split(".")[:3])
        if LooseVersion(dversion) < LooseVersion(DJANGO_MIN):
            print(ERROR_DJANGO_MIN.format(dversion=dversion_main, django_min=DJANGO_MIN))
            error = True
        elif LooseVersion(DJANGO_MIN) <= LooseVersion(dversion) < LooseVersion(DJANGO_REC):
            print(NOTE_DJANGO_MIN.format(dversion=dversion_main, django_rec=DJANGO_REC))
        elif LooseVersion(DJANGO_REC) < LooseVersion(dversion_main):
            print(NOTE_DJANGO_NEW.format(dversion=dversion_main, django_rec=DJANGO_REC))
    except ImportError:
        print(ERROR_NODJANGO)
        error = True
    if error:
        sys.exit()

    # return True/False if error was reported or not
    return not error


def set_gamedir(path):
    """
    Set GAMEDIR based on path, by figuring out where the setting file
    is inside the directory tree. This allows for running the launcher
    from elsewhere than the top of the gamedir folder.

    """
    global GAMEDIR

    Ndepth = 10
    settings_path = os.path.join("server", "conf", "settings.py")
    os.chdir(GAMEDIR)
    for i in range(Ndepth):
        gpath = os.getcwd()
        if "server" in os.listdir(gpath):
            if os.path.isfile(settings_path):
                GAMEDIR = gpath
                return
        os.chdir(os.pardir)
    print(ERROR_NO_GAMEDIR)
    sys.exit()


def create_secret_key():
    """
    Randomly create the secret key for the settings file

    """
    import random
    import string

    secret_key = list(
        (string.ascii_letters + string.digits + string.punctuation)
        .replace("\\", "")
        .replace("'", '"')
        .replace("{", "_")
        .replace("}", "-")
    )
    random.shuffle(secret_key)
    secret_key = "".join(secret_key[:40])
    return secret_key


def create_settings_file(init=True, secret_settings=False):
    """
    Uses the template settings file to build a working settings file.

    Args:
        init (bool): This is part of the normal evennia --init
            operation.  If false, this function will copy a fresh
            template file in (asking if it already exists).
        secret_settings (bool, optional): If False, create settings.py, otherwise
            create the secret_settings.py file.

    """
    if secret_settings:
        settings_path = os.path.join(GAMEDIR, "server", "conf", "secret_settings.py")
        setting_dict = {"secret_key": "'%s'" % create_secret_key()}
    else:
        settings_path = os.path.join(GAMEDIR, "server", "conf", "settings.py")
        setting_dict = {
            "settings_default": os.path.join(EVENNIA_LIB, "settings_default.py"),
            "servername": '"%s"' % GAMEDIR.rsplit(os.path.sep, 1)[1],
            "secret_key": "'%s'" % create_secret_key(),
        }

    if not init:
        # if not --init mode, settings file may already exist from before
        if os.path.exists(settings_path):
            inp = eval(input("%s already exists. Do you want to reset it? y/[N]> " % settings_path))
            if not inp.lower() == "y":
                print("Aborted.")
                return
            else:
                print("Reset the settings file.")

        if secret_settings:
            default_settings_path = os.path.join(
                EVENNIA_TEMPLATE, "server", "conf", "secret_settings.py"
            )
        else:
            default_settings_path = os.path.join(EVENNIA_TEMPLATE, "server", "conf", "settings.py")
        shutil.copy(default_settings_path, settings_path)

    with open(settings_path, "r") as f:
        settings_string = f.read()

    settings_string = settings_string.format(**setting_dict)

    with open(settings_path, "w") as f:
        f.write(settings_string)


def create_game_directory(dirname):
    """
    Initialize a new game directory named dirname
    at the current path. This means copying the
    template directory from evennia's root.

    Args:
        dirname (str): The directory name to create.

    """
    global GAMEDIR
    GAMEDIR = os.path.abspath(os.path.join(CURRENT_DIR, dirname))
    if os.path.exists(GAMEDIR):
        print("Cannot create new Evennia game dir: '%s' already exists." % dirname)
        sys.exit()
    # copy template directory
    shutil.copytree(EVENNIA_TEMPLATE, GAMEDIR)
    # rename gitignore to .gitignore
    os.rename(os.path.join(GAMEDIR, "gitignore"), os.path.join(GAMEDIR, ".gitignore"))

    # pre-build settings file in the new GAMEDIR
    create_settings_file()
    create_settings_file(secret_settings=True)


def create_superuser():
    """
    Create the superuser account

    """
    print(
        "\nCreate a superuser below. The superuser is Account #1, the 'owner' "
        "account of the server. Email is optional and can be empty.\n"
    )
    django.core.management.call_command("createsuperuser", interactive=True)


def check_database():
    """
    Check so the database exists.

    Returns:
        exists (bool): `True` if the database exists, otherwise `False`.
    """
    # Check so a database exists and is accessible
    from django.db import connection

    tables = connection.introspection.get_table_list(connection.cursor())
    if not tables or not isinstance(tables[0], str):  # django 1.8+
        tables = [tableinfo.name for tableinfo in tables]
    if tables and "accounts_accountdb" in tables:
        # database exists and seems set up. Initialize evennia.
        evennia._init()
    # Try to get Account#1
    from evennia.accounts.models import AccountDB

    try:
        AccountDB.objects.get(id=1)
    except django.db.utils.OperationalError as e:
        print(ERROR_DATABASE.format(traceback=e))
        sys.exit()
    except AccountDB.DoesNotExist:
        # no superuser yet. We need to create it.

        other_superuser = AccountDB.objects.filter(is_superuser=True)
        if other_superuser:
            # Another superuser was found, but not with id=1. This may
            # happen if using flush (the auto-id starts at a higher
            # value). Wwe copy this superuser into id=1. To do
            # this we must deepcopy it, delete it then save the copy
            # with the new id. This allows us to avoid the UNIQUE
            # constraint on usernames.
            other = other_superuser[0]
            other_id = other.id
            other_key = other.username
            print(WARNING_MOVING_SUPERUSER.format(other_key=other_key, other_id=other_id))
            res = ""
            while res.upper() != "Y":
                # ask for permission
                res = eval(input("Continue [Y]/N: "))
                if res.upper() == "N":
                    sys.exit()
                elif not res:
                    break
            # continue with the
            from copy import deepcopy

            new = deepcopy(other)
            other.delete()
            new.id = 1
            new.save()
        else:
            create_superuser()
            check_database()
    return True


def getenv():
    """
    Get current environment and add PYTHONPATH.

    Returns:
        env (dict): Environment global dict.

    """
    sep = ";" if _is_windows() else ":"
    env = os.environ.copy()
    env["PYTHONPATH"] = sep.join(sys.path)
    return env


def get_pid(pidfile, default=None):
    """
    Get the PID (Process ID) by trying to access an PID file.

    Args:
        pidfile (str): The path of the pid file.
        default (int, optional): What to return if file does not exist.

    Returns:
        pid (str): The process id or `default`.

    """
    if os.path.exists(pidfile):
        with open(pidfile, "r") as f:
            pid = f.read()
            return pid
    return default


def del_pid(pidfile):
    """
    The pidfile should normally be removed after a process has
    finished, but when sending certain signals they remain, so we need
    to clean them manually.

    Args:
        pidfile (str): The path of the pid file.

    """
    if os.path.exists(pidfile):
        os.remove(pidfile)


def kill(pidfile, component="Server", callback=None, errback=None, killsignal=SIG):
    """
    Send a kill signal to a process based on PID. A customized
    success/error message will be returned. If clean=True, the system
    will attempt to manually remove the pid file. On Windows, no arguments
    are useful since Windows has no ability to direct signals except to all
    children of a console.

    Args:
        pidfile (str): The path of the pidfile to get the PID from. This is ignored
            on Windows.
        component (str, optional): Usually one of 'Server' or 'Portal'. This is
            ignored on Windows.
        errback (callable, optional): Called if signal failed to send. This
            is ignored on Windows.
        callback (callable, optional): Called if kill signal was sent successfully.
            This is ignored on Windows.
        killsignal (int, optional): Signal identifier for signal to send. This is
            ignored on Windows.

    """
    if _is_windows():
        # Windows signal sending is very limited.
        from win32api import GenerateConsoleCtrlEvent, SetConsoleCtrlHandler

        try:
            # Windows can only send a SIGINT-like signal to
            # *every* process spawned off the same console, so we must
            # avoid killing ourselves here.
            SetConsoleCtrlHandler(None, True)
            GenerateConsoleCtrlEvent(CTRL_C_EVENT, 0)
        except KeyboardInterrupt:
            # We must catch and ignore the interrupt sent.
            pass
        print("Sent kill signal to all spawned processes")

    else:
        # Linux/Unix/Mac can send kill signal directly to specific PIDs.
        pid = get_pid(pidfile)
        if pid:
            if _is_windows():
                os.remove(pidfile)
            try:
                os.kill(int(pid), killsignal)
            except OSError:
                print(
                    "{component} ({pid}) cannot be stopped. "
                    "The PID file '{pidfile}' seems stale. "
                    "Try removing it manually.".format(
                        component=component, pid=pid, pidfile=pidfile
                    )
                )
                return
            if callback:
                callback()
            else:
                print("Sent kill signal to {component}.".format(component=component))
                return
        if errback:
            errback()
        else:
            print(
                "Could not send kill signal - {component} does "
                "not appear to be running.".format(component=component)
            )


def show_version_info(about=False):
    """
    Display version info.

    Args:
        about (bool): Include ABOUT info as well as version numbers.

    Returns:
        version_info (str): A complete version info string.

    """
    import sys
    import twisted

    return VERSION_INFO.format(
        version=EVENNIA_VERSION,
        about=ABOUT_INFO if about else "",
        os=os.name,
        python=sys.version.split()[0],
        twisted=twisted.version.short(),
        django=django.get_version(),
    )


def error_check_python_modules(show_warnings=False):
    """
    Import settings modules in settings. This will raise exceptions on
    pure python-syntax issues which are hard to catch gracefully with
    exceptions in the engine (since they are formatting errors in the
    python source files themselves). Best they fail already here
    before we get any further.

    Kwargs:
        show_warnings (bool): If non-fatal warning messages should be shown.

    """

    from django.conf import settings

    def _imp(path, split=True):
        "helper method"
        mod, fromlist = path, "None"
        if split:
            mod, fromlist = path.rsplit(".", 1)
        __import__(mod, fromlist=[fromlist])

    # check the historical deprecations
    from evennia.server import deprecations

    try:
        deprecations.check_errors(settings)
    except DeprecationWarning as err:
        print(err)
        sys.exit()

    if show_warnings:
        deprecations.check_warnings(settings)

    # core modules
    _imp(settings.COMMAND_PARSER)
    _imp(settings.SEARCH_AT_RESULT)
    _imp(settings.CONNECTION_SCREEN_MODULE)
    # imp(settings.AT_INITIAL_SETUP_HOOK_MODULE, split=False)
    for path in settings.LOCK_FUNC_MODULES:
        _imp(path, split=False)

    from evennia.commands import cmdsethandler

    if not cmdsethandler.import_cmdset(settings.CMDSET_UNLOGGEDIN, None):
        print("Warning: CMDSET_UNLOGGED failed to load!")
    if not cmdsethandler.import_cmdset(settings.CMDSET_CHARACTER, None):
        print("Warning: CMDSET_CHARACTER failed to load")
    if not cmdsethandler.import_cmdset(settings.CMDSET_ACCOUNT, None):
        print("Warning: CMDSET_ACCOUNT failed to load")
    # typeclasses
    _imp(settings.BASE_ACCOUNT_TYPECLASS)
    _imp(settings.BASE_OBJECT_TYPECLASS)
    _imp(settings.BASE_CHARACTER_TYPECLASS)
    _imp(settings.BASE_ROOM_TYPECLASS)
    _imp(settings.BASE_EXIT_TYPECLASS)
    _imp(settings.BASE_SCRIPT_TYPECLASS)


# ------------------------------------------------------------
#
# Options
#
# ------------------------------------------------------------


def init_game_directory(path, check_db=True, need_gamedir=True):
    """
    Try to analyze the given path to find settings.py - this defines
    the game directory and also sets PYTHONPATH as well as the django
    path.

    Args:
        path (str): Path to new game directory, including its name.
        check_db (bool, optional): Check if the databae exists.
        need_gamedir (bool, optional): set to False if Evennia doesn't require to
            be run in a valid game directory.

    """
    # set the GAMEDIR path
    if need_gamedir:
        set_gamedir(path)

    # Add gamedir to python path
    sys.path.insert(0, GAMEDIR)

    if TEST_MODE or not need_gamedir:
        if ENFORCED_SETTING:
            print(NOTE_TEST_CUSTOM.format(settings_dotpath=SETTINGS_DOTPATH))
            os.environ["DJANGO_SETTINGS_MODULE"] = SETTINGS_DOTPATH
        else:
            print(NOTE_TEST_DEFAULT)
            os.environ["DJANGO_SETTINGS_MODULE"] = "evennia.settings_default"
    else:
        os.environ["DJANGO_SETTINGS_MODULE"] = SETTINGS_DOTPATH

    # required since django1.7
    django.setup()

    # test existence of the settings module
    try:
        from django.conf import settings
    except Exception as ex:
        if not str(ex).startswith("No module named"):
            import traceback

            print(traceback.format_exc().strip())
        print(ERROR_SETTINGS)
        sys.exit()

    # this will both check the database and initialize the evennia dir.
    if check_db:
        check_database()

    # if we don't have to check the game directory, return right away
    if not need_gamedir:
        return

    # set up the Evennia executables and log file locations
    global AMP_PORT, AMP_HOST, AMP_INTERFACE
    global SERVER_PY_FILE, PORTAL_PY_FILE
    global SERVER_LOGFILE, PORTAL_LOGFILE, HTTP_LOGFILE
    global SERVER_PIDFILE, PORTAL_PIDFILE
    global SPROFILER_LOGFILE, PPROFILER_LOGFILE
    global EVENNIA_VERSION

    AMP_PORT = settings.AMP_PORT
    AMP_HOST = settings.AMP_HOST
    AMP_INTERFACE = settings.AMP_INTERFACE

    SERVER_PY_FILE = os.path.join(EVENNIA_LIB, "server", "server.py")
    PORTAL_PY_FILE = os.path.join(EVENNIA_LIB, "server", "portal", "portal.py")

    SERVER_PIDFILE = os.path.join(GAMEDIR, SERVERDIR, "server.pid")
    PORTAL_PIDFILE = os.path.join(GAMEDIR, SERVERDIR, "portal.pid")

    SPROFILER_LOGFILE = os.path.join(GAMEDIR, SERVERDIR, "logs", "server.prof")
    PPROFILER_LOGFILE = os.path.join(GAMEDIR, SERVERDIR, "logs", "portal.prof")

    SERVER_LOGFILE = settings.SERVER_LOG_FILE
    PORTAL_LOGFILE = settings.PORTAL_LOG_FILE
    HTTP_LOGFILE = settings.HTTP_LOG_FILE

    # verify existence of log file dir (this can be missing e.g.
    # if the game dir itself was cloned since log files are in .gitignore)
    logdirs = [
        logfile.rsplit(os.path.sep, 1) for logfile in (SERVER_LOGFILE, PORTAL_LOGFILE, HTTP_LOGFILE)
    ]
    if not all(os.path.isdir(pathtup[0]) for pathtup in logdirs):
        errstr = "\n    ".join(
            "%s (log file %s)" % (pathtup[0], pathtup[1])
            for pathtup in logdirs
            if not os.path.isdir(pathtup[0])
        )
        print(ERROR_LOGDIR_MISSING.format(logfiles=errstr))
        sys.exit()

    if _is_windows():
        # We need to handle Windows twisted separately. We create a
        # batchfile in game/server, linking to the actual binary

        global TWISTED_BINARY
        # Windows requires us to use the absolute path for the bat file.
        server_path = os.path.dirname(os.path.abspath(__file__))
        TWISTED_BINARY = os.path.join(server_path, "twistd.bat")

        # add path so system can find the batfile
        sys.path.insert(1, os.path.join(GAMEDIR, SERVERDIR))

        try:
            importlib.import_module("win32api")
        except ImportError:
            print(ERROR_WINDOWS_WIN32API)
            sys.exit()

        batpath = os.path.join(EVENNIA_SERVER, TWISTED_BINARY)
        if not os.path.exists(batpath):
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
            # Update: In 2016, it seems Twisted 16 has changed the name of
            # of its executable from 'twistd.py' to 'twistd.exe'.
            twistd_path = os.path.abspath(
                os.path.join(
                    twistd_dir, os.pardir, os.pardir, os.pardir, os.pardir, "scripts", "twistd.exe"
                )
            )

            with open(batpath, "w") as bat_file:
                # build a custom bat file for windows
                bat_file.write('@"%s" %%*' % twistd_path)

            print(INFO_WINDOWS_BATFILE.format(twistd_path=twistd_path))


def run_dummyrunner(number_of_dummies):
    """
    Start an instance of the dummyrunner

    Args:
        number_of_dummies (int): The number of dummy accounts to start.

    Notes:
        The dummy accounts' behavior can be customized by adding a
        `dummyrunner_settings.py` config file in the game's conf/
        directory.

    """
    number_of_dummies = str(int(number_of_dummies)) if number_of_dummies else 1
    cmdstr = [sys.executable, EVENNIA_DUMMYRUNNER, "-N", number_of_dummies]
    config_file = os.path.join(SETTINGS_PATH, "dummyrunner_settings.py")
    if os.path.exists(config_file):
        cmdstr.extend(["--config", config_file])
    try:
        call(cmdstr, env=getenv())
    except KeyboardInterrupt:
        # this signals the dummyrunner to stop cleanly and should
        # not lead to a traceback here.
        pass


def run_connect_wizard():
    """
    Run the linking wizard, for adding new external connections.

    """
    from .connection_wizard import ConnectionWizard, node_start

    wizard = ConnectionWizard()
    node_start(wizard)


def list_settings(keys):
    """
    Display the server settings. We only display the Evennia specific
    settings here. The result will be printed to the terminal.

    Args:
        keys (str or list): Setting key or keys to inspect.

    """
    from importlib import import_module
    from evennia.utils import evtable

    evsettings = import_module(SETTINGS_DOTPATH)
    if len(keys) == 1 and keys[0].upper() == "ALL":
        # show a list of all keys
        # a specific key
        table = evtable.EvTable()
        confs = [key for key in sorted(evsettings.__dict__) if key.isupper()]
        for i in range(0, len(confs), 4):
            table.add_row(*confs[i : i + 4])
    else:
        # a specific key
        table = evtable.EvTable(width=131)
        keys = [key.upper() for key in keys]
        confs = dict((key, var) for key, var in evsettings.__dict__.items() if key in keys)
        for key, val in confs.items():
            table.add_row(key, str(val))
    print(table)


def run_menu():
    """
    This launches an interactive menu.

    """
    while True:
        # menu loop
        gamedir = "/{}".format(os.path.basename(GAMEDIR))
        leninfo = len(gamedir)
        line = "|" + " " * (61 - leninfo) + gamedir + " " * 2 + "|"

        print(MENU.format(gameinfo=line))
        inp = input(" option > ")

        # quitting and help
        if inp.lower() == "q":
            return
        elif inp.lower() == "h":
            print(HELP_ENTRY)
            eval(input("press <return> to continue ..."))
            continue
        elif inp.lower() in ("v", "i", "a"):
            print(show_version_info(about=True))
            eval(input("press <return> to continue ..."))
            continue

        # options
        try:
            inp = int(inp)
        except ValueError:
            print("Not a valid option.")
            continue
        if inp == 1:
            start_evennia(False, False)
        elif inp == 2:
            reload_evennia(False, False)
        elif inp == 3:
            stop_evennia()
        elif inp == 4:
            reboot_evennia(False, False)
        elif inp == 5:
            reload_evennia(False, True)
        elif inp == 6:
            stop_server_only()
        elif inp == 7:
            if _is_windows():
                print("This option is not supported on Windows.")
            else:
                kill(SERVER_PIDFILE, "Server")
        elif inp == 8:
            if _is_windows():
                print("This option is not supported on Windows.")
            else:
                kill(SERVER_PIDFILE, "Server")
                kill(PORTAL_PIDFILE, "Portal")
        elif inp == 9:
            if not SERVER_LOGFILE:
                init_game_directory(CURRENT_DIR, check_db=False)
            tail_log_files(PORTAL_LOGFILE, SERVER_LOGFILE, 20, 20)
            print(
                "   Tailing logfiles {} (Ctrl-C to exit) ...".format(
                    _file_names_compact(SERVER_LOGFILE, PORTAL_LOGFILE)
                )
            )
        elif inp == 10:
            query_status()
        elif inp == 11:
            query_info()
        elif inp == 12:
            print("Running 'evennia --settings settings.py test .' ...")
            Popen(
                [sys.executable, __file__, "--settings", "settings.py", "test", "."], env=getenv()
            ).wait()
        elif inp == 13:
            print("Running 'evennia test evennia' ...")
            Popen([sys.executable, __file__, "test", "evennia"], env=getenv()).wait()
        else:
            print("Not a valid option.")
            continue
        return


def main():
    """
    Run the evennia launcher main program.

    """
    # set up argument parser

    parser = ArgumentParser(description=CMDLINE_HELP, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "--gamedir",
        nargs=1,
        action="store",
        dest="altgamedir",
        metavar="<path>",
        help="location of gamedir (default: current location)",
    )
    parser.add_argument(
        "--init",
        action="store",
        dest="init",
        metavar="<gamename>",
        help="creates a new gamedir 'name' at current location",
    )
    parser.add_argument(
        "--log",
        "-l",
        action="store_true",
        dest="tail_log",
        default=False,
        help="tail the portal and server logfiles and print to stdout",
    )
    parser.add_argument(
        "--list",
        nargs="+",
        action="store",
        dest="listsetting",
        metavar="all|<key>",
        help=("list settings, use 'all' to list all available keys"),
    )
    parser.add_argument(
        "--settings",
        nargs=1,
        action="store",
        dest="altsettings",
        default=None,
        metavar="<path>",
        help=(
            "start evennia with alternative settings file from\n"
            " gamedir/server/conf/. (default is settings.py)"
        ),
    )
    parser.add_argument(
        "--initsettings",
        action="store_true",
        dest="initsettings",
        default=False,
        help="create a new, empty settings file as\n gamedir/server/conf/settings.py",
    )
    parser.add_argument(
        "--initmissing",
        action="store_true",
        dest="initmissing",
        default=False,
        help="checks for missing secret_settings or server logs\n directory, and adds them if needed",
    )
    parser.add_argument(
        "--profiler",
        action="store_true",
        dest="profiler",
        default=False,
        help="start given server component under the Python profiler",
    )
    parser.add_argument(
        "--dummyrunner",
        nargs=1,
        action="store",
        dest="dummyrunner",
        metavar="<N>",
        help="test a server by connecting <N> dummy accounts to it",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        dest="show_version",
        default=False,
        help="show version info",
    )

    parser.add_argument("operation", nargs="?", default="noop", help=ARG_OPTIONS)
    parser.epilog = (
        "Common Django-admin commands are shell, dbshell, test and migrate.\n"
        "See the Django documentation for more management commands."
    )

    args, unknown_args = parser.parse_known_args()

    # handle arguments
    option = args.operation

    # make sure we have everything
    check_main_evennia_dependencies()

    if not args:
        # show help pane
        print(CMDLINE_HELP)
        sys.exit()

    if args.altgamedir:
        # use alternative gamedir path
        global GAMEDIR
        altgamedir = args.altgamedir[0]
        if not os.path.isdir(altgamedir) and not args.init:
            print(ERROR_NO_ALT_GAMEDIR.format(gamedir=altgamedir))
            sys.exit()
        GAMEDIR = altgamedir

    if args.init:
        # initialization of game directory
        create_game_directory(args.init)
        print(
            CREATED_NEW_GAMEDIR.format(
                gamedir=args.init, settings_path=os.path.join(args.init, SETTINGS_PATH)
            )
        )
        sys.exit()

    if args.show_version:
        # show the version info
        print(show_version_info(option == "help"))
        sys.exit()

    if args.altsettings:
        # use alternative settings file
        global SETTINGSFILE, SETTINGS_DOTPATH, ENFORCED_SETTING
        sfile = args.altsettings[0]
        SETTINGSFILE = sfile
        ENFORCED_SETTING = True
        SETTINGS_DOTPATH = "server.conf.%s" % sfile.rstrip(".py")
        print("Using settings file '%s' (%s)." % (SETTINGSFILE, SETTINGS_DOTPATH))

    if args.initsettings:
        # create new settings file
        try:
            create_settings_file(init=False)
            print(RECREATED_SETTINGS)
        except IOError:
            print(ERROR_INITSETTINGS)
        sys.exit()

    if args.initmissing:
        created = False
        try:
            log_path = os.path.join(SERVERDIR, "logs")
            if not os.path.exists(log_path):
                os.makedirs(log_path)
                print(f"    ... Created missing log dir {log_path}.")
                created = True

            settings_path = os.path.join(CONFDIR, "secret_settings.py")
            if not os.path.exists(settings_path):
                create_settings_file(init=False, secret_settings=True)
                print(f"    ... Created missing secret_settings.py file as {settings_path}.")
                created = True

            if created:
                print(RECREATED_MISSING)
            else:
                print("    ... No missing resources to create/init. You are good to go.")
        except IOError:
            print(ERROR_INITMISSING)
        sys.exit()

    if args.tail_log:
        # set up for tailing the log files
        global NO_REACTOR_STOP
        NO_REACTOR_STOP = True
        if not SERVER_LOGFILE:
            init_game_directory(CURRENT_DIR, check_db=False)

        # adjust how many lines we show from existing logs
        start_lines1, start_lines2 = 20, 20
        if option not in ("reload", "reset", "noop"):
            start_lines1, start_lines2 = 0, 0

        tail_log_files(PORTAL_LOGFILE, SERVER_LOGFILE, start_lines1, start_lines2)
        print(
            "   Tailing logfiles {} (Ctrl-C to exit) ...".format(
                _file_names_compact(SERVER_LOGFILE, PORTAL_LOGFILE)
            )
        )
    if args.dummyrunner:
        # launch the dummy runner
        init_game_directory(CURRENT_DIR, check_db=True)
        run_dummyrunner(args.dummyrunner[0])
    elif args.listsetting:
        # display all current server settings
        init_game_directory(CURRENT_DIR, check_db=False)
        list_settings(args.listsetting)
    elif option == "menu":
        # launch menu for operation
        init_game_directory(CURRENT_DIR, check_db=True)
        run_menu()
    elif option in (
        "status",
        "info",
        "start",
        "istart",
        "ipstart",
        "reload",
        "restart",
        "reboot",
        "reset",
        "stop",
        "sstop",
        "kill",
        "skill",
        "sstart",
        "connections",
    ):
        # operate the server directly
        if not SERVER_LOGFILE:
            init_game_directory(CURRENT_DIR, check_db=True)
        if option == "status":
            query_status()
        elif option == "info":
            query_info()
        elif option == "start":
            init_game_directory(CURRENT_DIR, check_db=True)
            error_check_python_modules(show_warnings=args.tail_log)
            start_evennia(args.profiler, args.profiler)
        elif option == "istart":
            init_game_directory(CURRENT_DIR, check_db=True)
            error_check_python_modules(show_warnings=args.tail_log)
            start_server_interactive()
        elif option == "ipstart":
            start_portal_interactive()
        elif option in ("reload", "restart"):
            reload_evennia(args.profiler)
        elif option == "reboot":
            reboot_evennia(args.profiler, args.profiler)
        elif option == "reset":
            reload_evennia(args.profiler, reset=True)
        elif option == "stop":
            stop_evennia()
        elif option == "sstop":
            stop_server_only()
        elif option == "sstart":
            start_only_server()
        elif option == "kill":
            if _is_windows():
                print("This option is not supported on Windows.")
            else:
                kill(SERVER_PIDFILE, "Server")
                kill(PORTAL_PIDFILE, "Portal")
        elif option == "skill":
            if _is_windows():
                print("This option is not supported on Windows.")
            else:
                kill(SERVER_PIDFILE, "Server")
        elif option == "connections":
            run_connect_wizard()

    elif option != "noop":
        # pass-through to django manager, but set things up first
        check_db = False
        need_gamedir = True
        # some commands don't require the presence of a game directory to work
        if option in ("makemessages", "compilemessages"):
            need_gamedir = False

        # handle special django commands
        if option in ("runserver", "testserver"):
            print(WARNING_RUNSERVER)
        if option in ("shell", "check"):
            # some django commands requires the database to exist,
            # or evennia._init to have run before they work right.
            check_db = True
        if option == "test":
            global TEST_MODE
            TEST_MODE = True

        init_game_directory(CURRENT_DIR, check_db=check_db, need_gamedir=need_gamedir)

        if option in ("migrate", "makemigrations"):
            # we have to launch migrate within the program to make sure migrations
            # run within the scope of the launcher (otherwise missing a db will cause errors)
            django.core.management.call_command(*([option] + unknown_args))
        else:
            # pass on to the core django manager - re-parse the entire input line
            # but keep 'evennia' as the name instead of django-admin. This is
            # an exit condition.
            sys.argv[0] = re.sub(r"(-script\.pyw?|\.exe)?$", "", sys.argv[0])
            sys.exit(execute_from_command_line())

    elif not args.tail_log:
        # no input; print evennia info (don't pring if we're tailing log)
        print(ABOUT_INFO)

    if REACTOR_RUN:
        reactor.run()


if __name__ == "__main__":
    # start Evennia from the command line
    main()
