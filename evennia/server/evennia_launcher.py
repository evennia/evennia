#!/usr/bin/env python
"""
EVENNIA SERVER LAUNCHER SCRIPT

This is the start point for running Evennia.

Sets the appropriate environmental variables and launches the server
and portal through the evennia_runner. Run without arguments to get a
menu. Run the script with the -h flag to see usage information.

"""
from __future__ import print_function
from builtins import input, range

import os
import sys
import signal
import shutil
import importlib
from distutils.version import LooseVersion
from argparse import ArgumentParser
from subprocess import Popen, check_output, call, CalledProcessError, STDOUT
import django

# Signal processing
SIG = signal.SIGINT
CTRL_C_EVENT = 0 # Windows SIGINT-like signal

# Set up the main python paths to Evennia
EVENNIA_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import evennia
EVENNIA_LIB = os.path.join(os.path.dirname(os.path.abspath(evennia.__file__)))
EVENNIA_SERVER = os.path.join(EVENNIA_LIB, "server")
EVENNIA_RUNNER = os.path.join(EVENNIA_SERVER, "evennia_runner.py")
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
SERVER_RESTART = None
PORTAL_RESTART = None
SERVER_PY_FILE = None
PORTAL_PY_FILE = None
TEST_MODE = False
ENFORCED_SETTING = False

# requirements
PYTHON_MIN = '2.7'
TWISTED_MIN = '16.0.0'
DJANGO_MIN = '1.8'
DJANGO_REC = '1.9'

sys.path[1] = EVENNIA_ROOT

#------------------------------------------------------------
#
# Messages
#
#------------------------------------------------------------

CREATED_NEW_GAMEDIR = \
    """
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

    Make sure to create a superuser when asked for it (the email can
    be blank if you want). You should now be able to (by default)
    connect to your server on 'localhost', port 4000 using a
    telnet/mud client or http://localhost:8000 using your web browser.
    If things don't work, check so those ports are open.

    """

ERROR_INPUT = \
"""
    Command
      {args} {kwargs}
    raised an error: '{traceback}'.
"""

ERROR_NO_GAMEDIR = \
    """
    ERROR: No Evennia settings file was found. Evennia looks for the
    file in your game directory as server/conf/settings.py.

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

WARNING_MOVING_SUPERUSER = \
    """
    WARNING: Evennia expects a Player superuser with id=1. No such
    Player was found. However, another superuser ('{other_key}',
    id={other_id}) was found in the database. If you just created this
    superuser and still see this text it is probably due to the
    database being flushed recently - in this case the database's
    internal auto-counter might just start from some value higher than
    one.

    We will fix this by assigning the id 1 to Player '{other_key}'.
    Please confirm this is acceptable before continuing.
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
    ERROR: There was an error importing Evennia's config file
    {settingspath}.
    There is usually one of three reasons for this:
        1) You are not running this command from your game directory.
           Change directory to your game directory and try again (or
           create a new game directory using evennia --init <dirname>)
        2) The ettings file contains a syntax error. If you see a
           traceback above, review it, resolve the problem and try again.
        3) Django is not correctly installed. This usually shows as
           errors mentioning 'DJANGO_SETTINGS_MODULE'. If you run a
           virtual machine, it might be worth to restart it to see if
           this resolves the issue.
    """.format(settingspath=SETTINGS_PATH)

ERROR_INITSETTINGS = \
    """
    ERROR: 'evennia --initsettings' must be called from the root of
    your game directory, since it tries to (re)create the new
    settings.py file in a subfolder server/conf/.
    """

RECREATED_SETTINGS = \
    """
    (Re)created an empty settings file in server/conf/settings.py.

    Note that if you were using an existing database, the password
    salt of this new settings file will be different from the old one.
    This means that any existing players may not be able to log in to
    their accounts with their old passwords.
    """

ERROR_DATABASE = \
    """
    ERROR: Your database does not seem to be set up correctly.
    (error was '{traceback}')

    Standing in your game directory, run

       evennia migrate

    to initialize/update the database according to your settings.
    """

ERROR_WINDOWS_WIN32API = \
    """
    ERROR: Unable to import win32api, which Twisted requires to run.
    You may download it from:

    http://sourceforge.net/projects/pywin32/files/pywin32/

    If you are running in a virtual environment, browse to the
    location of the latest win32api exe file for your computer and
    Python version and copy the url to it; then paste it into a call
    to easy_install:

        easy_install http://<url to win32api exe>
    """

INFO_WINDOWS_BATFILE = \
    """
    INFO: Since you are running Windows, a file 'twistd.bat' was
    created for you. This is a simple batch file that tries to call
    the twisted executable. Evennia determined this to be:

       {twistd_path}

    If you run into errors at startup you might need to edit
    twistd.bat to point to the actual location of the Twisted
    executable (usually called twistd.py) on your machine.

    This procedure is only done once. Run evennia.py again when you
    are ready to start the server.
    """

CMDLINE_HELP = \
    """
    Starts or operates the Evennia MU* server.  Allows for
    initializing a new game directory and manages the game's database.
    Most standard django-admin arguments and options can also be
    passed.
    """


VERSION_INFO = \
    """
    Evennia {version}
    OS: {os}
    Python: {python}
    Twisted: {twisted}
    Django: {django}{about}
    """

ABOUT_INFO = \
    """
    Evennia MUD/MUX/MU* development system

    Licence: BSD 3-Clause Licence
    Web: http://www.evennia.com
    Irc: #evennia on FreeNode
    Forum: http://www.evennia.com/discussions
    Maintainer (2010-):   Griatch (griatch AT gmail DOT com)
    Maintainer (2006-10): Greg Taylor

    Use -h for command line options.
    """

HELP_ENTRY = \
    """
    Enter 'evennia -h' for command-line options.

    Use option (1) in a production environment.  During development (2) is
    usually enough, portal debugging is usually only useful if you are
    adding new protocols or are debugging Evennia itself.

    Reload with (5) to update the server with your changes without
    disconnecting any players.

    Note: Reload and stop are sometimes poorly supported in Windows. If you
    have issues, log into the game to stop or restart the server instead.
    """

MENU = \
    """
    +----Evennia Launcher-------------------------------------------+
    |                                                               |
    +--- Starting --------------------------------------------------+
    |                                                               |
    |  1) (normal):       All output to logfiles                    |
    |  2) (server devel): Server logs to terminal (-i option)       |
    |  3) (portal devel): Portal logs to terminal                   |
    |  4) (full devel):   Both Server and Portal logs to terminal   |
    |                                                               |
    +--- Restarting ------------------------------------------------+
    |                                                               |
    |  5) Reload the Server                                         |
    |  6) Reload the Portal (only works with portal/full debug)     |
    |                                                               |
    +--- Stopping --------------------------------------------------+
    |                                                               |
    |  7) Stopping both Portal and Server                           |
    |  8) Stopping only Server                                      |
    |  9) Stopping only Portal                                      |
    |                                                               |
    +---------------------------------------------------------------+
    |  h) Help              i) About info               q) Abort    |
    +---------------------------------------------------------------+
    """

ERROR_LOGDIR_MISSING = \
    """
    ERROR: One or more log-file directory locations could not be
    found:

    {logfiles}

    This is simple to fix: Just manually create the missing log
    directory (or directories) and re-launch the server (the log files
    will be created automatically).

    (Explanation: Evennia creates the log directory automatically when
    initializating a new game directory. This error usually happens if
    you used git to clone a pre-created game directory - since log
    files are in .gitignore they will not be cloned, which leads to
    the log directory also not being created.)

    """

ERROR_PYTHON_VERSION = \
    """
    ERROR: Python {pversion} used. Evennia requires version
    {python_min} or higher (but not 3.x).
    """

ERROR_TWISTED_VERSION = \
    """
    ERROR: Twisted {tversion} found. Evennia requires
    version {twisted_min} or higher.
    """

ERROR_NOTWISTED = \
    """
    ERROR: Twisted does not seem to be installed.
    """

ERROR_DJANGO_MIN = \
    """
    ERROR: Django {dversion} found. Evennia requires version {django_min}
    or higher.

    Install it with for example `pip install --upgrade django`
    or with `pip install django=={django_min}` to get a specific version.

    It's also a good idea to run `evennia migrate` after this upgrade.
    """

NOTE_DJANGO_MIN = \
    """
    NOTE: Django {dversion} found. This will work, but v{django_rec}
    is recommended for production.
    """

NOTE_DJANGO_NEW = \
    """
    NOTE: Django {dversion} found. This is newer than Evennia's
    recommended version (v{django_rec}). It might work, but may be new
    enough to not be fully tested yet. Report any issues.
    """

ERROR_NODJANGO = \
    """
    ERROR: Django does not seem to be installed.
    """

NOTE_KEYBOARDINTERRUPT = \
    """
    STOP: Caught keyboard interrupt while in interactive mode.
    """

NOTE_TEST_DEFAULT = \
    """
    TESTING: Using Evennia's default settings file (evennia.settings_default).
    (use 'evennia --settings settings.py test .' to run tests on the game dir)
    """

NOTE_TEST_CUSTOM = \
    """
    TESTING: Using specified settings file '{settings_dotpath}'.

    (Obs: Evennia's full test suite may not pass if the settings are very
    different from the default. Use 'test .' as arguments to run only tests
    on the game dir.)
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
    try:
        version = evennia.__version__
    except ImportError:
        # even if evennia is not found, we should not crash here.
        pass
    try:
        rev = check_output(
            "git rev-parse --short HEAD",
            shell=True, cwd=EVENNIA_ROOT, stderr=STDOUT).strip()
        version = "%s (rev %s)" % (version, rev)
    except (IOError, CalledProcessError):
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
    pversion = ".".join(str(num) for num in sys.version_info if type(num) == int)
    if LooseVersion(pversion) < LooseVersion(PYTHON_MIN):
        print(ERROR_PYTHON_VERSION.format(pversion=pversion, python_min=PYTHON_MIN))
        error = True
    # Twisted
    try:
        import twisted
        tversion = twisted.version.short()
        if LooseVersion(tversion) < LooseVersion(TWISTED_MIN):
            print(ERROR_TWISTED_VERSION.format(
                tversion=tversion, twisted_min=TWISTED_MIN))
            error = True
    except ImportError:
        print(ERROR_NOTWISTED)
        error = True
    # Django
    try:
        dversion = ".".join(str(num) for num in django.VERSION if type(num) == int)
        # only the main version (1.5, not 1.5.4.0)
        dversion_main = ".".join(dversion.split(".")[:2])
        if LooseVersion(dversion) < LooseVersion(DJANGO_MIN):
            print(ERROR_DJANGO_MIN.format(
                dversion=dversion_main, django_min=DJANGO_MIN))
            error = True
        elif LooseVersion(DJANGO_MIN) <= LooseVersion(dversion) < LooseVersion(DJANGO_REC):
            print(NOTE_DJANGO_MIN.format(
                dversion=dversion_main, django_rec=DJANGO_REC))
        elif LooseVersion(DJANGO_REC) < LooseVersion(dversion_main):
            print(NOTE_DJANGO_NEW.format(
                dversion=dversion_main, django_rec=DJANGO_REC))
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
    is inside the directory tree.

    """
    global GAMEDIR

    Ndepth = 10
    settings_path = os.path.join("server", "conf", "settings.py")
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
    secret_key = list((string.letters +
        string.digits + string.punctuation).replace("\\", "")\
                .replace("'", '"').replace("{","_").replace("}","-"))
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
        setting_dict = {"secret_key": "\'%s\'" % create_secret_key()}
    else:
        settings_path = os.path.join(GAMEDIR, "server", "conf", "settings.py")
        setting_dict = {
            "settings_default": os.path.join(EVENNIA_LIB, "settings_default.py"),
            "servername": "\"%s\"" % GAMEDIR.rsplit(os.path.sep, 1)[1].capitalize(),
            "secret_key": "\'%s\'" % create_secret_key()}

    if not init:
        # if not --init mode, settings file may already exist from before
        if os.path.exists(settings_path):
            inp = input("%s already exists. Do you want to reset it? y/[N]> " % settings_path)
            if not inp.lower() == 'y':
                print ("Aborted.")
                return
            else:
                print ("Reset the settings file.")

        default_settings_path = os.path.join(EVENNIA_TEMPLATE, "server", "conf", "settings.py")
        shutil.copy(default_settings_path, settings_path)

    with open(settings_path, 'r') as f:
        settings_string = f.read()

    settings_string = settings_string.format(**setting_dict)

    with open(settings_path, 'w') as f:
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
    os.rename(os.path.join(GAMEDIR, 'gitignore'),
              os.path.join(GAMEDIR, '.gitignore'))

    # pre-build settings file in the new GAMEDIR
    create_settings_file()
    create_settings_file(secret_settings=True)


def create_superuser():
    """
    Create the superuser player

    """
    print(
        "\nCreate a superuser below. The superuser is Player #1, the 'owner' "
        "account of the server.\n")
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
    if not tables or not isinstance(tables[0], basestring): # django 1.8+
        tables = [tableinfo.name for tableinfo in tables]
    if tables and u'players_playerdb' in tables:
        # database exists and seems set up. Initialize evennia.
        evennia._init()
    # Try to get Player#1
    from evennia.players.models import PlayerDB
    try:
        PlayerDB.objects.get(id=1)
    except django.db.utils.OperationalError as e:
        print(ERROR_DATABASE.format(traceback=e))
        sys.exit()
    except PlayerDB.DoesNotExist:
        # no superuser yet. We need to create it.

        other_superuser = PlayerDB.objects.filter(is_superuser=True)
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
            print(WARNING_MOVING_SUPERUSER.format(
                other_key=other_key, other_id=other_id))
            res = ""
            while res.upper() != "Y":
                # ask for permission
                res = input("Continue [Y]/N: ")
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
    sep = ";" if os.name == 'nt' else ":"
    env = os.environ.copy()
    env['PYTHONPATH'] = sep.join(sys.path)
    return env


def get_pid(pidfile):
    """
    Get the PID (Process ID) by trying to access an PID file.

    Args:
        pidfile (str): The path of the pid file.

    Returns:
        pid (str or None): The process id.

    """
    if os.path.exists(pidfile):
        with open(pidfile, 'r') as f:
            pid = f.read()
            return pid
    return None


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


def kill(pidfile, killsignal=SIG, succmsg="", errmsg="",
         restart_file=SERVER_RESTART, restart=False):
    """
    Send a kill signal to a process based on PID. A customized
    success/error message will be returned. If clean=True, the system
    will attempt to manually remove the pid file.

    Args:
        pidfile (str): The path of the pidfile to get the PID from.
        killsignal (int, optional): Signal identifier for signal to send.
        succmsg (str, optional): Message to log on success.
        errmsg (str, optional): Message to log on failure.
        restart_file (str, optional): Restart file location.
        restart (bool, optional): Are we in restart mode or not.

    """
    pid = get_pid(pidfile)
    if pid:
        if os.name == 'nt':
            os.remove(pidfile)
        # set restart/norestart flag
        if restart:
            django.core.management.call_command(
                'collectstatic', interactive=False, verbosity=0)
            with open(restart_file, 'w') as f:
                f.write("reload")
        else:
            with open(restart_file, 'w') as f:
                f.write("shutdown")
        try:
            if os.name == 'nt':
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
            else:
                # Linux can send the SIGINT signal directly
                # to the specified PID.
                os.kill(int(pid), killsignal)

        except OSError:
            print("Process %(pid)s cannot be stopped. "\
                  "The PID file 'server/%(pidfile)s' seems stale. "\
                  "Try removing it." % {'pid': pid, 'pidfile': pidfile})
            return
        print("Evennia:", succmsg)
        return
    print("Evennia:", errmsg)


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
        version=EVENNIA_VERSION, about=ABOUT_INFO if about else "",
        os=os.name, python=sys.version.split()[0],
        twisted=twisted.version.short(),
        django=django.get_version())


def error_check_python_modules():
    """
    Import settings modules in settings. This will raise exceptions on
    pure python-syntax issues which are hard to catch gracefully with
    exceptions in the engine (since they are formatting errors in the
    python source files themselves). Best they fail already here
    before we get any further.

    """

    from django.conf import settings
    def _imp(path, split=True):
        "helper method"
        mod, fromlist = path, "None"
        if split:
            mod, fromlist = path.rsplit('.', 1)
        __import__(mod, fromlist=[fromlist])

    # check the historical deprecations
    from evennia.server import deprecations
    try:
        deprecations.check_errors(settings)
        deprecations.check_warnings(settings)
    except DeprecationWarning as err:
        print(err)
        sys.exit()

    # core modules
    _imp(settings.COMMAND_PARSER)
    _imp(settings.SEARCH_AT_RESULT)
    _imp(settings.CONNECTION_SCREEN_MODULE)
    #imp(settings.AT_INITIAL_SETUP_HOOK_MODULE, split=False)
    for path in settings.LOCK_FUNC_MODULES:
        _imp(path, split=False)

    from evennia.commands import cmdsethandler
    if not cmdsethandler.import_cmdset(settings.CMDSET_UNLOGGEDIN, None):
        print("Warning: CMDSET_UNLOGGED failed to load!")
    if not cmdsethandler.import_cmdset(settings.CMDSET_CHARACTER, None):
        print("Warning: CMDSET_CHARACTER failed to load")
    if not cmdsethandler.import_cmdset(settings.CMDSET_PLAYER, None):
        print("Warning: CMDSET_PLAYER failed to load")
    # typeclasses
    _imp(settings.BASE_PLAYER_TYPECLASS)
    _imp(settings.BASE_OBJECT_TYPECLASS)
    _imp(settings.BASE_CHARACTER_TYPECLASS)
    _imp(settings.BASE_ROOM_TYPECLASS)
    _imp(settings.BASE_EXIT_TYPECLASS)
    _imp(settings.BASE_SCRIPT_TYPECLASS)

def init_game_directory(path, check_db=True):
    """
    Try to analyze the given path to find settings.py - this defines
    the game directory and also sets PYTHONPATH as well as the django
    path.

    Args:
        path (str): Path to new game directory, including its name.
        check_db (bool, optional): Check if the databae exists.

    """
    # set the GAMEDIR path
    set_gamedir(path)

    # Add gamedir to python path
    sys.path.insert(0, GAMEDIR)

    if TEST_MODE:
        if ENFORCED_SETTING:
            print(NOTE_TEST_CUSTOM.format(settings_dotpath=SETTINGS_DOTPATH))
            os.environ['DJANGO_SETTINGS_MODULE'] = SETTINGS_DOTPATH
        else:
            print(NOTE_TEST_DEFAULT)
            os.environ['DJANGO_SETTINGS_MODULE'] = 'evennia.settings_default'
    else:
        os.environ['DJANGO_SETTINGS_MODULE'] = SETTINGS_DOTPATH

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

    # set up the Evennia executables and log file locations
    global SERVER_PY_FILE, PORTAL_PY_FILE
    global SERVER_LOGFILE, PORTAL_LOGFILE, HTTP_LOGFILE
    global SERVER_PIDFILE, PORTAL_PIDFILE
    global SERVER_RESTART, PORTAL_RESTART
    global EVENNIA_VERSION

    SERVER_PY_FILE = os.path.join(EVENNIA_LIB, "server", "server.py")
    PORTAL_PY_FILE = os.path.join(EVENNIA_LIB, "portal", "portal", "portal.py")

    SERVER_PIDFILE = os.path.join(GAMEDIR, SERVERDIR, "server.pid")
    PORTAL_PIDFILE = os.path.join(GAMEDIR, SERVERDIR, "portal.pid")

    SERVER_RESTART = os.path.join(GAMEDIR, SERVERDIR, "server.restart")
    PORTAL_RESTART = os.path.join(GAMEDIR, SERVERDIR, "portal.restart")

    SERVER_LOGFILE = settings.SERVER_LOG_FILE
    PORTAL_LOGFILE = settings.PORTAL_LOG_FILE
    HTTP_LOGFILE = settings.HTTP_LOG_FILE

    # verify existence of log file dir (this can be missing e.g.
    # if the game dir itself was cloned since log files are in .gitignore)
    logdirs = [logfile.rsplit(os.path.sep, 1)
                for logfile in (SERVER_LOGFILE, PORTAL_LOGFILE, HTTP_LOGFILE)]
    if not all(os.path.isdir(pathtup[0]) for pathtup in logdirs):
        errstr = "\n    ".join("%s (log file %s)" % (pathtup[0], pathtup[1]) for pathtup in logdirs
                if not os.path.isdir(pathtup[0]))
        print(ERROR_LOGDIR_MISSING.format(logfiles=errstr))
        sys.exit()

    if os.name == 'nt':
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
                os.path.join(twistd_dir, os.pardir, os.pardir, os.pardir,
                             os.pardir, 'scripts', 'twistd.exe'))

            with open(batpath, 'w') as bat_file:
                # build a custom bat file for windows
                bat_file.write("@\"%s\" %%*" % twistd_path)

            print(INFO_WINDOWS_BATFILE.format(twistd_path=twistd_path))


def run_dummyrunner(number_of_dummies):
    """
    Start an instance of the dummyrunner

    Args:
        number_of_dummies (int): The number of dummy players to start.

    Notes:
        The dummy players' behavior can be customized by adding a
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
            table.add_row(*confs[i:i+4])
    else:
        # a specific key
        table = evtable.EvTable(width=131)
        keys = [key.upper() for key in keys]
        confs = dict((key, var) for key, var in evsettings.__dict__.items()
                     if key in keys)
        for key, val in confs.items():
            table.add_row(key, str(val))
    print(table)


def run_menu():
    """
    This launches an interactive menu.

    """
    while True:
        # menu loop

        print(MENU)
        inp = input(" option > ")

        # quitting and help
        if inp.lower() == 'q':
            return
        elif inp.lower() == 'h':
            print(HELP_ENTRY)
            input("press <return> to continue ...")
            continue
        elif inp.lower() in ('v', 'i', 'a'):
            print(show_version_info(about=True))
            input("press <return> to continue ...")
            continue

        # options
        try:
            inp = int(inp)
        except ValueError:
            print("Not a valid option.")
            continue
        if inp == 1:
            # start everything, log to log files
            server_operation("start", "all", False, False)
        elif inp == 2:
            # start everything, server interactive start
            server_operation("start", "all", True, False)
        elif inp == 3:
            # start everything, portal interactive start
            server_operation("start", "server", False, False)
            server_operation("start", "portal", True, False)
        elif inp == 4:
            # start both server and portal interactively
            server_operation("start", "server", True, False)
            server_operation("start", "portal", True, False)
        elif inp == 5:
            # reload the server
            server_operation("reload", "server", None, None)
        elif inp == 6:
            # reload the portal
            server_operation("reload", "portal", None, None)
        elif inp == 7:
            # stop server and portal
            server_operation("stop", "all", None, None)
        elif inp == 8:
            # stop server
            server_operation("stop", "server", None, None)
        elif inp == 9:
            # stop portal
            server_operation("stop", "portal", None, None)
        else:
            print("Not a valid option.")
            continue
        return


def server_operation(mode, service, interactive, profiler, logserver=False, doexit=False):
    """
    Handle argument options given on the command line.

    Args:
        mode (str): Start/stop/restart and so on.
        service (str): "server", "portal" or "all".
        interactive (bool). Use interactive mode or daemon.
        profiler (bool): Run the service under the profiler.
        logserver (bool, optional): Log Server data to logfile
            specified by settings.SERVER_LOG_FILE.
        doexit (bool, optional): If True, immediately exit the runner after
            starting the relevant processes. If the runner exits, Evennia
            cannot be reloaded. This is meant to be used with an external
            process manager like Linux' start-stop-daemon.

    """

    cmdstr = [sys.executable, EVENNIA_RUNNER]
    errmsg = "The %s does not seem to be running."

    if mode == 'start':

        # launch the error checker. Best to catch the errors already here.
        error_check_python_modules()

        # starting one or many services
        if service == 'server':
            if profiler:
                cmdstr.append('--pserver')
            if interactive:
                cmdstr.append('--iserver')
            if logserver:
                cmdstr.append('--logserver')
            cmdstr.append('--noportal')
        elif service == 'portal':
            if profiler:
                cmdstr.append('--pportal')
            if interactive:
                cmdstr.append('--iportal')
            cmdstr.append('--noserver')
            django.core.management.call_command(
                'collectstatic', verbosity=1, interactive=False)
        else:
            # all
            # for convenience we don't start logging of
            # portal, only of server with this command.
            if profiler:
                # this is the common case
                cmdstr.append('--pserver')
            if interactive:
                cmdstr.append('--iserver')
            if logserver:
                cmdstr.append('--logserver')
            django.core.management.call_command(
                'collectstatic', verbosity=1, interactive=False)
        if doexit:
            cmdstr.append('--doexit')
        cmdstr.extend([
            GAMEDIR, TWISTED_BINARY, SERVER_LOGFILE,
            PORTAL_LOGFILE, HTTP_LOGFILE])
        # start the server
        process = Popen(cmdstr, env=getenv())

        if interactive:
            try:
                process.wait()
            except KeyboardInterrupt:
                server_operation("stop", "portal", False, False)
                return
            finally:
                print(NOTE_KEYBOARDINTERRUPT)

    elif mode == 'reload':
        # restarting services
        if os.name == 'nt':
            print(
                "Restarting from command line is not supported under Windows. "
                "Use the in-game command (@reload by default) "
                "or use 'evennia stop && evennia start' for a cold reboot.")
            return
        if service == 'server':
            kill(SERVER_PIDFILE, SIG, "Server reloaded.",
                 errmsg % 'Server', SERVER_RESTART, restart=True)
        elif service == 'portal':
            print(
                "Note: Portal usually doesnt't need to be reloaded unless you "
                "are debugging in interactive mode. If Portal was running in "
                "default Daemon mode, it cannot be restarted. In that case "
                "you have to restart it manually with 'evennia.py "
                "start portal'")
            kill(PORTAL_PIDFILE, SIG,
                 "Portal reloaded (or stopped, if it was in daemon mode).",
                 errmsg % 'Portal', PORTAL_RESTART, restart=True)
        else:
            # all
            # default mode, only restart server
            kill(SERVER_PIDFILE, SIG,
                 "Server reload.",
                 errmsg % 'Server', SERVER_RESTART, restart=True)

    elif mode == 'stop':
        if os.name == "nt":
            print (
                    "(Obs: You can use a single Ctrl-C to skip "
                    "Windows' annoying 'Terminate batch job (Y/N)?' prompts.)")
        # stop processes, avoiding reload
        if service == 'server':
            kill(SERVER_PIDFILE, SIG,
                 "Server stopped.", errmsg % 'Server', SERVER_RESTART)
        elif service == 'portal':
            kill(PORTAL_PIDFILE, SIG,
                 "Portal stopped.", errmsg % 'Portal', PORTAL_RESTART)
        else:
            kill(PORTAL_PIDFILE, SIG,
                 "Portal stopped.", errmsg % 'Portal', PORTAL_RESTART)
            kill(SERVER_PIDFILE, SIG,
                 "Server stopped.", errmsg % 'Server', SERVER_RESTART)


def main():
    """
    Run the evennia launcher main program.

    """

    # set up argument parser

    parser = ArgumentParser(description=CMDLINE_HELP)
    parser.add_argument(
        '-v', '--version', action='store_true',
        dest='show_version', default=False,
        help="Show version info.")
    parser.add_argument(
        '-i', '--interactive', action='store_true',
        dest='interactive', default=False,
        help="Start given processes in interactive mode.")
    parser.add_argument(
        '-l', '--log', action='store_true',
        dest="logserver", default=False,
        help="Log Server data to log file.")
    parser.add_argument(
        '--init', action='store', dest="init", metavar="name",
        help="Creates a new game directory 'name' at the current location.")
    parser.add_argument(
        '--list', nargs='+', action='store', dest='listsetting', metavar="key",
        help=("List values for server settings. Use 'all' to list all "
              "available keys."))
    parser.add_argument(
        '--profiler', action='store_true', dest='profiler', default=False,
        help="Start given server component under the Python profiler.")
    parser.add_argument(
        '--dummyrunner', nargs=1, action='store', dest='dummyrunner',
        metavar="N",
        help="Test a running server by connecting N dummy players to it.")
    parser.add_argument(
        '--settings', nargs=1, action='store', dest='altsettings',
        default=None, metavar="filename.py",
        help=("Start evennia with alternative settings file from "
              "gamedir/server/conf/. (default is settings.py)"))
    parser.add_argument(
        '--initsettings', action='store_true', dest="initsettings",
        default=False,
        help="Create a new, empty settings file as gamedir/server/conf/settings.py.")
    parser.add_argument(
        '--external-runner', action='store_true', dest="doexit",
        default=False,
        help="Handle server restart with an external process manager.")
    parser.add_argument(
        "operation", nargs='?', default="noop",
        help="Operation to perform: 'start', 'stop', 'reload' or 'menu'.")
    parser.add_argument(
        "service", metavar="component", nargs='?', default="all",
        help=("Which component to operate on: "
              "'server', 'portal' or 'all' (default if not set)."))
    parser.epilog = (
            "Common usage: evennia start|stop|reload. Django-admin database commands:"
        "evennia migration|flush|shell|dbshell (see the django documentation for more django-admin commands.)")

    args, unknown_args = parser.parse_known_args()

    # handle arguments
    option, service = args.operation, args.service

    # make sure we have everything
    check_main_evennia_dependencies()

    if not args:
        # show help pane
        print(CMDLINE_HELP)
        sys.exit()
    elif args.init:
        # initialization of game directory
        create_game_directory(args.init)
        print(CREATED_NEW_GAMEDIR.format(
            gamedir=args.init,
            settings_path=os.path.join(args.init, SETTINGS_PATH)))
        sys.exit()

    if args.show_version:
        # show the version info
        print(show_version_info(option == "help"))
        sys.exit()

    if args.altsettings:
        # use alternative settings file
        sfile = args.altsettings[0]
        global SETTINGSFILE, SETTINGS_DOTPATH, ENFORCED_SETTING
        SETTINGSFILE = sfile
        ENFORCED_SETTING = True
        SETTINGS_DOTPATH = "server.conf.%s" % sfile.rstrip(".py")
        print("Using settings file '%s' (%s)." % (
            SETTINGSFILE, SETTINGS_DOTPATH))


    if args.initsettings:
        # create new settings file
        global GAMEDIR
        GAMEDIR = os.getcwd()
        try:
            create_settings_file(init=False)
            print(RECREATED_SETTINGS)
        except IOError:
            print(ERROR_INITSETTINGS)
        sys.exit()

    if args.dummyrunner:
        # launch the dummy runner
        init_game_directory(CURRENT_DIR, check_db=True)
        run_dummyrunner(args.dummyrunner[0])
    elif args.listsetting:
        # display all current server settings
        init_game_directory(CURRENT_DIR, check_db=False)
        list_settings(args.listsetting)
    elif option == 'menu':
        # launch menu for operation
        init_game_directory(CURRENT_DIR, check_db=True)
        run_menu()
    elif option in ('start', 'reload', 'stop'):
        # operate the server directly
        init_game_directory(CURRENT_DIR, check_db=True)
        server_operation(option, service, args.interactive, args.profiler, args.logserver, doexit=args.doexit)
    elif option != "noop":
        # pass-through to django manager
        check_db = False
        if option in ('runserver', 'testserver'):
            print(WARNING_RUNSERVER)
        if option == "shell":
            # to use the shell we need to initialize it first,
            # and this only works if the database is set up
            check_db = True
        if option == "test":
            global TEST_MODE
            TEST_MODE = True
        init_game_directory(CURRENT_DIR, check_db=check_db)

        args = [option]
        kwargs = {}
        if service not in ("all", "server", "portal"):
            args.append(service)
        if unknown_args:
            for arg in unknown_args:
                if arg.startswith("--"):
                    print("arg:", arg)
                    if "=" in arg:
                        arg, value = [p.strip() for p in arg.split("=", 1)]
                    else:
                        value = True
                    kwargs[arg.lstrip("--")] = [value]
                else:
                    args.append(arg)
        try:
            django.core.management.call_command(*args, **kwargs)
        except django.core.management.base.CommandError as exc:
            args = ", ".join(args)
            kwargs = ", ".join(["--%s" % kw for kw in kwargs])
            print(ERROR_INPUT.format(traceback=exc, args=args, kwargs=kwargs))
    else:
        # no input; print evennia info
        print(ABOUT_INFO)


if __name__ == '__main__':
    # start Evennia from the command line
    main()
