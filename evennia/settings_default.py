"""
Master configuration file for Evennia.

NOTE: NO MODIFICATIONS SHOULD BE MADE TO THIS FILE!

All settings changes should be done by copy-pasting the variable and
its value to <gamedir>/conf/settings.py.

Hint: Don't copy&paste over more from this file than you actually want
to change.  Anything you don't copy&paste will thus retain its default
value - which may change as Evennia is developed. This way you can
always be sure of what you have changed and what is default behaviour.

"""
from django.contrib.messages import constants as messages
from django.urls import reverse_lazy

import os
import sys

######################################################################
# Evennia base server config
######################################################################

# This is the name of your game. Make it catchy!
SERVERNAME = "Evennia"
# Short one-sentence blurb describing your game. Shown under the title
# on the website and could be used in online listings of your game etc.
GAME_SLOGAN = "Python MU* creation system"
# Lockdown mode will cut off the game from any external connections
# and only allow connections from localhost. Requires a cold reboot.
LOCKDOWN_MODE = False
# Activate telnet service
TELNET_ENABLED = True
# A list of ports the Evennia telnet server listens on Can be one or many.
TELNET_PORTS = [4000]
# Interface addresses to listen to. If 0.0.0.0, listen to all. Use :: for IPv6.
TELNET_INTERFACES = ["0.0.0.0"]
# Activate Telnet+SSL protocol (SecureSocketLibrary) for supporting clients
SSL_ENABLED = False
# Ports to use for Telnet+SSL
SSL_PORTS = [4003]
# Telnet+SSL Interface addresses to listen to. If 0.0.0.0, listen to all. Use :: for IPv6.
SSL_INTERFACES = ["0.0.0.0"]
# OOB (out-of-band) telnet communication allows Evennia to communicate
# special commands and data with enabled Telnet clients. This is used
# to create custom client interfaces over a telnet connection. To make
# full use of OOB, you need to prepare functions to handle the data
# server-side (see INPUT_FUNC_MODULES). TELNET_ENABLED is required for this
# to work.
TELNET_OOB_ENABLED = False
# Activate SSH protocol communication (SecureShell)
SSH_ENABLED = False
# Ports to use for SSH
SSH_PORTS = [4004]
# Interface addresses to listen to. If 0.0.0.0, listen to all. Use :: for IPv6.
SSH_INTERFACES = ["0.0.0.0"]
# Start the evennia django+twisted webserver so you can
# browse the evennia website and the admin interface
# (Obs - further web configuration can be found below
# in the section  'Config for Django web features')
WEBSERVER_ENABLED = True
# This is a security setting protecting against host poisoning
# attacks.  It defaults to allowing all. In production, make
# sure to change this to your actual host addresses/IPs.
ALLOWED_HOSTS = ["*"]
# The webserver sits behind a Portal proxy. This is a list
# of tuples (proxyport,serverport) used. The proxyports are what
# the Portal proxy presents to the world. The serverports are
# the internal ports the proxy uses to forward data to the Server-side
# webserver (these should not be publicly open)
WEBSERVER_PORTS = [(4001, 4005)]
# Interface addresses to listen to. If 0.0.0.0, listen to all. Use :: for IPv6.
WEBSERVER_INTERFACES = ["0.0.0.0"]
# IP addresses that may talk to the server in a reverse proxy configuration,
# like NginX.
UPSTREAM_IPS = ["127.0.0.1"]
# The webserver uses threadpool for handling requests. This will scale
# with server load. Set the minimum and maximum number of threads it
# may use as (min, max) (must be > 0)
WEBSERVER_THREADPOOL_LIMITS = (1, 20)
# Start the evennia webclient. This requires the webserver to be running and
# offers the fallback ajax-based webclient backbone for browsers not supporting
# the websocket one.
WEBCLIENT_ENABLED = True
# Activate Websocket support for modern browsers. If this is on, the
# default webclient will use this and only use the ajax version if the browser
# is too old to support websockets. Requires WEBCLIENT_ENABLED.
WEBSOCKET_CLIENT_ENABLED = True
# Server-side websocket port to open for the webclient. Note that this value will
# be dynamically encoded in the webclient html page to allow the webclient to call
# home. If the external encoded value needs to be different than this, due to
# working through a proxy or docker port-remapping, the environment variable
# WEBCLIENT_CLIENT_PROXY_PORT can be used to override this port only for the
# front-facing client's sake.
WEBSOCKET_CLIENT_PORT = 4002
# Interface addresses to listen to. If 0.0.0.0, listen to all. Use :: for IPv6.
WEBSOCKET_CLIENT_INTERFACE = "0.0.0.0"
# Actual URL for webclient component to reach the websocket. You only need
# to set this if you know you need it, like using some sort of proxy setup.
# If given it must be on the form "ws[s]://hostname[:port]". If left at None,
# the client will itself figure out this url based on the server's hostname.
# e.g. ws://external.example.com or wss://external.example.com:443
WEBSOCKET_CLIENT_URL = None
# This determine's whether Evennia's custom admin page is used, or if the
# standard Django admin is used.
EVENNIA_ADMIN = True
# The Server opens an AMP port so that the portal can
# communicate with it. This is an internal functionality of Evennia, usually
# operating between two processes on the same machine. You usually don't need to
# change this unless you cannot use the default AMP port/host for
# whatever reason.
AMP_HOST = "localhost"
AMP_PORT = 4006
AMP_INTERFACE = "127.0.0.1"


# Path to the lib directory containing the bulk of the codebase's code.
EVENNIA_DIR = os.path.dirname(os.path.abspath(__file__))
# Path to the game directory (containing the server/conf/settings.py file)
# This is dynamically created- there is generally no need to change this!
if EVENNIA_DIR.lower() == os.getcwd().lower() or (
    sys.argv[1] == "test" if len(sys.argv) > 1 else False
):
    # unittesting mode
    GAME_DIR = os.getcwd()
else:
    # Fallback location (will be replaced by the actual game dir at runtime)
    GAME_DIR = os.path.join(EVENNIA_DIR, "game_template")
    for i in range(10):
        gpath = os.getcwd()
        if "server" in os.listdir(gpath):
            if os.path.isfile(os.path.join("server", "conf", "settings.py")):
                GAME_DIR = gpath
                break
        os.chdir(os.pardir)

# Place to put log files
LOG_DIR = os.path.join(GAME_DIR, "server", "logs")
SERVER_LOG_FILE = os.path.join(LOG_DIR, "server.log")
PORTAL_LOG_FILE = os.path.join(LOG_DIR, "portal.log")
HTTP_LOG_FILE = os.path.join(LOG_DIR, "http_requests.log")
# if this is set to the empty string, lockwarnings will be turned off.
LOCKWARNING_LOG_FILE = os.path.join(LOG_DIR, "lockwarnings.log")
# Rotate log files when server and/or portal stops. This will keep log
# file sizes down. Turn off to get ever growing log files and never
# lose log info.
CYCLE_LOGFILES = True
# Number of lines to append to rotating channel logs when they rotate
CHANNEL_LOG_NUM_TAIL_LINES = 20
# Max size (in bytes) of channel log files before they rotate
CHANNEL_LOG_ROTATE_SIZE = 1000000
# Local time zone for this installation. All choices can be found here:
# http://www.postgresql.org/docs/8.0/interactive/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
TIME_ZONE = "UTC"
# Activate time zone in datetimes
USE_TZ = True
# Authentication backends. This is the code used to authenticate a user.
AUTHENTICATION_BACKENDS = ["evennia.web.utils.backends.CaseInsensitiveModelBackend"]
# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
LANGUAGE_CODE = "en-us"
# How long time (in seconds) a user may idle before being logged
# out. This can be set as big as desired. A user may avoid being
# thrown off by sending the empty system command 'idle' to the server
# at regular intervals. Set <=0 to deactivate idle timeout completely.
IDLE_TIMEOUT = -1
# The idle command can be sent to keep your session active without actually
# having to spam normal commands regularly. It gives no feedback, only updates
# the idle timer. Note that "idle" will *always* work, even if a different
# command-name is given here; this is because the webclient needs a default
# to send to avoid proxy timeouts.
IDLE_COMMAND = "idle"
# The set of encodings tried. An Account object may set an attribute "encoding" on
# itself to match the client used. If not set, or wrong encoding is
# given, this list is tried, in order, aborting on the first match.
# Add sets for languages/regions your accounts are likely to use.
# (see http://en.wikipedia.org/wiki/Character_encoding)
# Telnet default encoding, unless specified by the client, will be ENCODINGS[0].
ENCODINGS = ["utf-8", "latin-1", "ISO-8859-1"]
# Regular expression applied to all output to a given session in order
# to strip away characters (usually various forms of decorations) for the benefit
# of users with screen readers. Note that ANSI/MXP doesn't need to
# be stripped this way, that is handled automatically.
SCREENREADER_REGEX_STRIP = r"\+-+|\+$|\+~|--+|~~+|==+"
# Database objects are cached in what is known as the idmapper. The idmapper
# caching results in a massive speedup of the server (since it dramatically
# limits the number of database accesses needed) and also allows for
# storing temporary data on objects. It is however also the main memory
# consumer of Evennia. With this setting the cache can be capped and
# flushed when it reaches a certain size. Minimum is 50 MB but it is
# not recommended to set this to less than 100 MB for a distribution
# system.
# Empirically, N_objects_in_cache ~ ((RMEM - 35) / 0.0157):
#  mem(MB)   |  objs in cache   ||   mem(MB)   |   objs in cache
#      50    |       ~1000      ||      800    |     ~49 000
#     100    |       ~4000      ||     1200    |     ~75 000
#     200    |      ~10 000     ||     1600    |    ~100 000
#     500    |      ~30 000     ||     2000    |    ~125 000
# Note that the estimated memory usage is not exact (and the cap is only
# checked every 5 minutes), so err on the side of caution if
# running on a server with limited memory. Also note that Python
# will not necessarily return the memory to the OS when the idmapper
# flashes (the memory will be freed and made available to the Python
# process only). How many objects need to be in memory at any given
# time depends very much on your game so some experimentation may
# be necessary (use @server to see how many objects are in the idmapper
# cache at any time). Setting this to None disables the cache cap.
IDMAPPER_CACHE_MAXSIZE = 200  # (MB)
# This determines how many connections per second the Portal should
# accept, as a DoS countermeasure. If the rate exceeds this number, incoming
# connections will be queued to this rate, so none will be lost.
# Must be set to a value > 0.
MAX_CONNECTION_RATE = 2
# Determine how many commands per second a given Session is allowed
# to send to the Portal via a connected protocol. Too high rate will
# drop the command and echo a warning. Note that this will also cap
# OOB messages so don't set it too low if you expect a lot of events
# from the client! To turn the limiter off, set to <= 0.
MAX_COMMAND_RATE = 80
# The warning to echo back to users if they send commands too fast
COMMAND_RATE_WARNING = "You entered commands too fast. Wait a moment and try again."
# Determine how large of a string can be sent to the server in number
# of characters. If they attempt to enter a string over this character
# limit, we stop them and send a message. To make unlimited, set to
# 0 or less.
MAX_CHAR_LIMIT = 6000
# The warning to echo back to users if they enter a very large string
MAX_CHAR_LIMIT_WARNING = (
    "You entered a string that was too long. " "Please break it up into multiple parts."
)
# If this is true, errors and tracebacks from the engine will be
# echoed as text in-game as well as to the log. This can speed up
# debugging. OBS: Showing full tracebacks to regular users could be a
# security problem -turn this off in a production game!
IN_GAME_ERRORS = True

######################################################################
# Evennia Database config
######################################################################

# Database config syntax:
# ENGINE - path to the the database backend. Possible choices are:
#            'django.db.backends.sqlite3', (default)
#            'django.db.backends.mysql',
#            'django.db.backends.postgresql_psycopg2',
#            'django.db.backends.oracle' (untested).
# NAME - database name, or path to the db file for sqlite3
# USER - db admin (unused in sqlite3)
# PASSWORD - db admin password (unused in sqlite3)
# HOST - empty string is localhost (unused in sqlite3)
# PORT - empty string defaults to localhost (unused in sqlite3)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("TEST_DB_PATH", os.path.join(GAME_DIR, "server", "evennia.db3")),
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    }
}
# How long the django-database connection should be kept open, in seconds.
# If you get errors about the database having gone away after long idle
# periods, shorten this value (e.g. MySQL defaults to a timeout of 8 hrs)
CONN_MAX_AGE = 3600 * 7
# When removing or renaming models, such models stored in Attributes may
# become orphaned and will return as None. If the change is a rename (that
# is, there is a 1:1 pk mapping between the old and the new), the unserializer
# can convert old to new when retrieving them. This is a list of tuples
# (old_natural_key, new_natural_key). Note that Django ContentTypes'
# natural_keys are themselves tuples (appname, modelname). Creation-dates will
# not be checked for models specified here. If new_natural_key does not exist,
# `None` will be returned and stored back as if no replacement was set.
ATTRIBUTE_STORED_MODEL_RENAME = [
    (("players", "playerdb"), ("accounts", "accountdb")),
    (("typeclasses", "defaultplayer"), ("typeclasses", "defaultaccount")),
]


######################################################################
# Evennia pluggable modules
######################################################################
# Plugin modules extend Evennia in various ways. In the cases with no
# existing default, there are examples of many of these modules
# in contrib/examples.

# The command parser module to use. See the default module for which
# functions it must implement
COMMAND_PARSER = "evennia.commands.cmdparser.cmdparser"
# On a multi-match when search objects or commands, the user has the
# ability to search again with an index marker that differentiates
# the results. If multiple "box" objects
# are found, they can by default be separated as 1-box, 2-box. Below you
# can change the regular expression used. The regex must have one
# have two capturing groups (?P<number>...) and (?P<name>...) - the default
# parser expects this. It should also involve a number starting from 1.
# When changing this you must also update SEARCH_MULTIMATCH_TEMPLATE
# to properly describe the syntax.
SEARCH_MULTIMATCH_REGEX = r"(?P<number>[0-9]+)-(?P<name>.*)"
# To display multimatch errors in various listings we must display
# the syntax in a way that matches what SEARCH_MULTIMATCH_REGEX understand.
# The template will be populated with data and expects the following markup:
# {number} - the order of the multimatch, starting from 1; {name} - the
# name (key) of the multimatched entity; {aliases} - eventual
# aliases for the entity; {info} - extra info like #dbrefs for staff. Don't
# forget a line break if you want one match per line.
SEARCH_MULTIMATCH_TEMPLATE = " {number}-{name}{aliases}{info}\n"
# The handler that outputs errors when using any API-level search
# (not manager methods). This function should correctly report errors
# both for command- and object-searches. This allows full control
# over the error output (it uses SEARCH_MULTIMATCH_TEMPLATE by default).
SEARCH_AT_RESULT = "evennia.utils.utils.at_search_result"
# Single characters to ignore at the beginning of a command. When set, e.g.
# cmd, @cmd and +cmd will all find a command "cmd" or one named "@cmd" etc. If
# you have defined two different commands cmd and @cmd you can still enter
# @cmd to exactly target the second one. Single-character commands consisting
# of only a prefix character will not be stripped. Set to the empty
# string ("") to turn off prefix ignore.
CMD_IGNORE_PREFIXES = "@&/+"
# The module holding text strings for the connection screen.
# This module should contain one or more variables
# with strings defining the look of the screen.
CONNECTION_SCREEN_MODULE = "server.conf.connection_screens"
# Delay to use before sending the evennia.syscmdkeys.CMD_LOGINSTART Command
# when a new session connects (this defaults the unloggedin-look for showing
# the connection screen). The delay is useful mainly for telnet, to allow
# client/server to establish client capabilities like color/mxp etc before
# sending any text. A value of 0.3 should be enough. While a good idea, it may
# cause issues with menu-logins and autoconnects since the menu will not have
# started when the autoconnects starts sending menu commands.
DELAY_CMD_LOGINSTART = 0.3
# An optional module that, if existing, must hold a function
# named at_initial_setup(). This hook method can be used to customize
# the server's initial setup sequence (the very first startup of the system).
# The check will fail quietly if module doesn't exist or fails to load.
AT_INITIAL_SETUP_HOOK_MODULE = "server.conf.at_initial_setup"
# Module containing your custom at_server_start(), at_server_reload() and
# at_server_stop() methods. These methods will be called every time
# the server starts, reloads and resets/stops respectively.
AT_SERVER_STARTSTOP_MODULE = "server.conf.at_server_startstop"
# List of one or more module paths to modules containing a function start_
# plugin_services(application). This module will be called with the main
# Evennia Server application when the Server is initiated.
# It will be called last in the startup sequence.
SERVER_SERVICES_PLUGIN_MODULES = ["server.conf.server_services_plugins"]
# List of one or more module paths to modules containing a function
# start_plugin_services(application). This module will be called with the
# main Evennia Portal application when the Portal is initiated.
# It will be called last in the startup sequence.
PORTAL_SERVICES_PLUGIN_MODULES = ["server.conf.portal_services_plugins"]
# Module holding MSSP meta data. This is used by MUD-crawlers to determine
# what type of game you are running, how many accounts you have etc.
MSSP_META_MODULE = "server.conf.mssp"
# Module for web plugins.
WEB_PLUGINS_MODULE = "server.conf.web_plugins"
# Tuple of modules implementing lock functions. All callable functions
# inside these modules will be available as lock functions.
LOCK_FUNC_MODULES = ("evennia.locks.lockfuncs", "server.conf.lockfuncs")
# Module holding handlers for managing incoming data from the client. These
# will be loaded in order, meaning functions in later modules may overload
# previous ones if having the same name.
INPUT_FUNC_MODULES = ["evennia.server.inputfuncs", "server.conf.inputfuncs"]
# Modules that contain prototypes for use with the spawner mechanism.
PROTOTYPE_MODULES = ["world.prototypes"]
# Modules containining Prototype functions able to be embedded in prototype
# definitions from in-game.
PROT_FUNC_MODULES = ["evennia.prototypes.protfuncs"]
# Module holding settings/actions for the dummyrunner program (see the
# dummyrunner for more information)
DUMMYRUNNER_SETTINGS_MODULE = "evennia.server.profiling.dummyrunner_settings"
# Mapping to extend Evennia's normal ANSI color tags. The mapping is a list of
# tuples mapping the exact tag (not a regex!) to the ANSI convertion, like
# `(r"%c%r", ansi.ANSI_RED)` (the evennia.utils.ansi module contains all
# ANSI escape sequences). Default is to use `|` and `|[` -prefixes.
COLOR_ANSI_EXTRA_MAP = []
# Extend the available regexes for adding XTERM256 colors in-game. This is given
# as a list of regexes, where each regex must contain three anonymous groups for
# holding integers 0-5 for the red, green and blue components Default is
# is r'\|([0-5])([0-5])([0-5])', which allows e.g. |500 for red.
# XTERM256 foreground color replacement
COLOR_XTERM256_EXTRA_FG = []
# XTERM256 background color replacement. Default is \|\[([0-5])([0-5])([0-5])'
COLOR_XTERM256_EXTRA_BG = []
# Extend the available regexes for adding XTERM256 grayscale values in-game. Given
# as a list of regexes, where each regex must contain one anonymous group containing
# a single letter a-z to mark the level from white to black. Default is r'\|=([a-z])',
# which allows e.g. |=k for a medium gray.
# XTERM256 grayscale foreground
COLOR_XTERM256_EXTRA_GFG = []
# XTERM256 grayscale background. Default is \|\[=([a-z])'
COLOR_XTERM256_EXTRA_GBG = []
# ANSI does not support bright backgrounds, so Evennia fakes this by mapping it to
# XTERM256 backgrounds where supported. This is a list of tuples that maps the wanted
# ansi tag (not a regex!) to a valid XTERM256 background tag, such as `(r'{[r', r'{[500')`.
COLOR_ANSI_XTERM256_BRIGHT_BG_EXTRA_MAP = []
# If set True, the above color settings *replace* the default |-style color markdown
# rather than extend it.
COLOR_NO_DEFAULT = False


######################################################################
# Default command sets
######################################################################
# Note that with the exception of the unloggedin set (which is not
# stored anywhere in the database), changing these paths will only affect
# NEW created characters/objects, not those already in play. So if you plan to
# change this, it's recommended you do it before having created a lot of objects
# (or simply reset the database after the change for simplicity).

# Command set used on session before account has logged in
CMDSET_UNLOGGEDIN = "commands.default_cmdsets.UnloggedinCmdSet"
# Command set used on the logged-in session
CMDSET_SESSION = "commands.default_cmdsets.SessionCmdSet"
# Default set for logged in account with characters (fallback)
CMDSET_CHARACTER = "commands.default_cmdsets.CharacterCmdSet"
# Command set for accounts without a character (ooc)
CMDSET_ACCOUNT = "commands.default_cmdsets.AccountCmdSet"
# Location to search for cmdsets if full path not given
CMDSET_PATHS = ["commands", "evennia", "evennia.contrib"]
# Fallbacks for cmdset paths that fail to load. Note that if you change the path for your
# default cmdsets, you will also need to copy CMDSET_FALLBACKS after your change in your
# settings file for it to detect the change.
CMDSET_FALLBACKS = {
    CMDSET_CHARACTER: "evennia.commands.default.cmdset_character.CharacterCmdSet",
    CMDSET_ACCOUNT: "evennia.commands.default.cmdset_account.AccountCmdSet",
    CMDSET_SESSION: "evennia.commands.default.cmdset_session.SessionCmdSet",
    CMDSET_UNLOGGEDIN: "evennia.commands.default.cmdset_unloggedin.UnloggedinCmdSet",
}
# Parent class for all default commands. Changing this class will
# modify all default commands, so do so carefully.
COMMAND_DEFAULT_CLASS = "evennia.commands.default.muxcommand.MuxCommand"
# Command.arg_regex is a regular expression desribing how the arguments
# to the command must be structured for the command to match a given user
# input. By default there is no restriction as long as the input string
# starts with the command name.
COMMAND_DEFAULT_ARG_REGEX = None
# By default, Command.msg will only send data to the Session calling
# the Command in the first place. If set, Command.msg will instead return
# data to all Sessions connected to the Account/Character associated with
# calling the Command. This may be more intuitive for users in certain
# multisession modes.
COMMAND_DEFAULT_MSG_ALL_SESSIONS = False
# The help category of a command if not otherwise specified.
COMMAND_DEFAULT_HELP_CATEGORY = "general"
# The default lockstring of a command.
COMMAND_DEFAULT_LOCKS = ""
# The Channel Handler will create a command to represent each channel,
# creating it with the key of the channel, its aliases, locks etc. The
# default class logs channel messages to a file and allows for /history.
# This setting allows to override the command class used with your own.
CHANNEL_COMMAND_CLASS = "evennia.comms.channelhandler.ChannelCommand"

######################################################################
# Typeclasses and other paths
######################################################################

# Server-side session class used.
SERVER_SESSION_CLASS = "evennia.server.serversession.ServerSession"

# These are paths that will be prefixed to the paths given if the
# immediately entered path fail to find a typeclass. It allows for
# shorter input strings. They must either base off the game directory
# or start from the evennia library.
TYPECLASS_PATHS = ["typeclasses", "evennia", "evennia.contrib", "evennia.contrib.tutorial_examples"]

# Typeclass for account objects (linked to a character) (fallback)
BASE_ACCOUNT_TYPECLASS = "typeclasses.accounts.Account"
# Typeclass and base for all objects (fallback)
BASE_OBJECT_TYPECLASS = "typeclasses.objects.Object"
# Typeclass for character objects linked to an account (fallback)
BASE_CHARACTER_TYPECLASS = "typeclasses.characters.Character"
# Typeclass for rooms (fallback)
BASE_ROOM_TYPECLASS = "typeclasses.rooms.Room"
# Typeclass for Exit objects (fallback).
BASE_EXIT_TYPECLASS = "typeclasses.exits.Exit"
# Typeclass for Channel (fallback).
BASE_CHANNEL_TYPECLASS = "typeclasses.channels.Channel"
# Typeclass for Scripts (fallback). You usually don't need to change this
# but create custom variations of scripts on a per-case basis instead.
BASE_SCRIPT_TYPECLASS = "typeclasses.scripts.Script"
# The default home location used for all objects. This is used as a
# fallback if an object's normal home location is deleted. Default
# is Limbo (#2).
DEFAULT_HOME = "#2"
# The start position for new characters. Default is Limbo (#2).
#  MULTISESSION_MODE = 0, 1 - used by default unloggedin create command
#  MULTISESSION_MODE = 2, 3 - used by default character_create command
START_LOCATION = "#2"
# Lookups of Attributes, Tags, Nicks, Aliases can be aggressively
# cached to avoid repeated database hits. This often gives noticeable
# performance gains since they are called so often. Drawback is that
# if you are accessing the database from multiple processes (such as
# from a website -not- running Evennia's own webserver) data may go
# out of sync between the processes. Keep on unless you face such
# issues.
TYPECLASS_AGGRESSIVE_CACHE = True

######################################################################
# Options and validators
######################################################################

# Options available on Accounts. Each such option is described by a
# class available from evennia.OPTION_CLASSES, in turn making use
# of validators from evennia.VALIDATOR_FUNCS to validate input when
# the user changes an option. The options are accessed through the
# `Account.options` handler.

# ("Description", 'Option Class name in evennia.OPTION_CLASS_MODULES', 'Default Value')

OPTIONS_ACCOUNT_DEFAULT = {
    "border_color": ("Headers, footers, table borders, etc.", "Color", "n"),
    "header_star_color": ("* inside Header lines.", "Color", "n"),
    "header_text_color": ("Text inside Header lines.", "Color", "w"),
    "header_fill": ("Fill for Header lines.", "Text", "="),
    "separator_star_color": ("* inside Separator lines.", "Color", "n"),
    "separator_text_color": ("Text inside Separator lines.", "Color", "w"),
    "separator_fill": ("Fill for Separator Lines.", "Text", "-"),
    "footer_star_color": ("* inside Footer lines.", "Color", "n"),
    "footer_text_color": ("Text inside Footer Lines.", "Color", "n"),
    "footer_fill": ("Fill for Footer Lines.", "Text", "="),
    "column_names_color": ("Table column header text.", "Color", "w"),
    "help_category_color": ("Help category names.", "Color", "n"),
    "help_entry_color": ("Help entry names.", "Color", "n"),
    "timezone": ("Timezone for dates. @tz for a list.", "Timezone", "UTC"),
}
# Modules holding Option classes, responsible for serializing the option and
# calling validator functions on it. Same-named functions in modules added
# later in this list will override those added earlier.
OPTION_CLASS_MODULES = ["evennia.utils.optionclasses"]
# Module holding validator functions. These are used as a resource for
# validating options, but can also be used as input validators in general.
# Same-named functions in modules added later in this list will override those
# added earlier.
VALIDATOR_FUNC_MODULES = ["evennia.utils.validatorfuncs"]

######################################################################
# Batch processors
######################################################################

# Python path to a directory to be searched for batch scripts
# for the batch processors (.ev and/or .py files).
BASE_BATCHPROCESS_PATHS = ["world", "evennia.contrib", "evennia.contrib.tutorial_examples"]

######################################################################
# Game Time setup
######################################################################

# You don't actually have to use this, but it affects the routines in
# evennia.utils.gametime.py and allows for a convenient measure to
# determine the current in-game time. You can of course interpret
# "week", "month" etc as your own in-game time units as desired.

# The time factor dictates if the game world runs faster (timefactor>1)
# or slower (timefactor<1) than the real world.
TIME_FACTOR = 2.0
# The starting point of your game time (the epoch), in seconds.
# In Python a value of 0 means Jan 1 1970 (use negatives for earlier
# start date). This will affect the returns from the utils.gametime
# module. If None, the server's first start-time is used as the epoch.
TIME_GAME_EPOCH = None
# Normally, game time will only increase when the server runs. If this is True,
# game time will not pause when the server reloads or goes offline. This setting
# together with a time factor of 1 should keep the game in sync with
# the real time (add a different epoch to shift time)
TIME_IGNORE_DOWNTIMES = False

######################################################################
# Inlinefunc, PrototypeFuncs
######################################################################
# Evennia supports inline function preprocessing. This allows users
# to supply inline calls on the form $func(arg, arg, ...) to do
# session-aware text formatting and manipulation on the fly. If
# disabled, such inline functions will not be parsed.
INLINEFUNC_ENABLED = False
# Only functions defined globally (and not starting with '_') in
# these modules will be considered valid inlinefuncs. The list
# is loaded from left-to-right, same-named functions will overload
INLINEFUNC_MODULES = ["evennia.utils.inlinefuncs", "server.conf.inlinefuncs"]
# Module holding handlers for OLCFuncs. These allow for embedding
# functional code in prototypes
PROTOTYPEFUNC_MODULES = ["evennia.utils.prototypefuncs", "server.conf.prototypefuncs"]

######################################################################
# Global Scripts
######################################################################

# Global scripts started here will be available through
# 'evennia.GLOBAL_SCRIPTS.key'. The scripts will survive a reload and be
# recreated automatically if deleted. Each entry must have the script keys,
# whereas all other fields in the specification are optional. If 'typeclass' is
# not given, BASE_SCRIPT_TYPECLASS will be assumed.  Note that if you change
# typeclass for the same key, a new Script will replace the old one on
# `evennia.GLOBAL_SCRIPTS`.
GLOBAL_SCRIPTS = {
    # 'key': {'typeclass': 'typeclass.path.here',
    #         'repeats': -1, 'interval': 50, 'desc': 'Example script'},
}

######################################################################
# Default Account setup and access
######################################################################

# Different Multisession modes allow a player (=account) to connect to the
# game simultaneously with multiple clients (=sessions). In modes 0,1 there is
# only one character created to the same name as the account at first login.
# In modes 2,3 no default character will be created and the MAX_NR_CHARACTERS
# value (below) defines how many characters the default char_create command
# allow per account.
#  0 - single session, one account, one character, when a new session is
#      connected, the old one is disconnected
#  1 - multiple sessions, one account, one character, each session getting
#      the same data
#  2 - multiple sessions, one account, many characters, one session per
#      character (disconnects multiplets)
#  3 - like mode 2, except multiple sessions can puppet one character, each
#      session getting the same data.
MULTISESSION_MODE = 0
# The maximum number of characters allowed by the default ooc char-creation command
MAX_NR_CHARACTERS = 1
# The access hierarchy, in climbing order. A higher permission in the
# hierarchy includes access of all levels below it. Used by the perm()/pperm()
# lock functions, which accepts both plural and singular (Admin & Admins)
PERMISSION_HIERARCHY = [
    "Guest",  # note-only used if GUEST_ENABLED=True
    "Player",
    "Helper",
    "Builder",
    "Admin",
    "Developer",
]
# The default permission given to all new accounts
PERMISSION_ACCOUNT_DEFAULT = "Player"
# Default sizes for client window (in number of characters), if client
# is not supplying this on its own
CLIENT_DEFAULT_WIDTH = 78
# telnet standard height is 24; does anyone use such low-res displays anymore?
CLIENT_DEFAULT_HEIGHT = 45
# Help output from CmdHelp are wrapped in an EvMore call
# (excluding webclient with separate help popups). If continuous scroll
# is preferred, change 'HELP_MORE' to False. EvMORE uses CLIENT_DEFAULT_HEIGHT
HELP_MORE = True

######################################################################
# Guest accounts
######################################################################

# This enables guest logins, by default via "connect guest". Note that
# you need to edit your login screen to inform about this possibility.
GUEST_ENABLED = False
# Typeclass for guest account objects (linked to a character)
BASE_GUEST_TYPECLASS = "typeclasses.accounts.Guest"
# The permission given to guests
PERMISSION_GUEST_DEFAULT = "Guests"
# The default home location used for guests.
GUEST_HOME = DEFAULT_HOME
# The start position used for guest characters.
GUEST_START_LOCATION = START_LOCATION
# The naming convention used for creating new guest
# accounts/characters. The size of this list also determines how many
# guests may be on the game at once. The default is a maximum of nine
# guests, named Guest1 through Guest9.
GUEST_LIST = ["Guest" + str(s + 1) for s in range(9)]

######################################################################
# In-game Channels created from server start
######################################################################

# The mudinfo channel must always exist; it is used by Evennia itself to
# relay status messages, connection info etc to staff. The superuser will be
# automatically subscribed to this channel and it will be recreated on a
# reload if deleted. This is a dict specifying the kwargs needed to create
# the channel .
CHANNEL_MUDINFO = {
    "key": "MudInfo",
    "aliases": "",
    "desc": "Connection log",
    "locks": "control:perm(Developer);listen:perm(Admin);send:false()",
}
# These are additional channels to offer. Usually, at least 'public'
# should exist. The superuser will automatically be subscribed to all channels
# in this list. New entries will be created on the next reload. But
# removing or updating a same-key channel from this list will NOT automatically
# change/remove it in the game, that needs to be done manually.
DEFAULT_CHANNELS = [
    # public channel
    {
        "key": "Public",
        "aliases": ("pub"),
        "desc": "Public discussion",
        "locks": "control:perm(Admin);listen:all();send:all()",
    }
]
# Optional channel info (same form as CHANNEL_MUDINFO) for the channel to
# receive connection messages ("<account> has (dis)connected").  While the
# MudInfo channel will also receieve this info, this channel is meant for
# non-staffers.
CHANNEL_CONNECTINFO = None

######################################################################
# External Connections
######################################################################

# Note: You do *not* have to make your MUD open to
# the public to use the external connections, they
# operate as long as you have an internet connection,
# just like stand-alone chat clients.

# The Evennia Game Index is a dynamic listing of Evennia games. You can add your game
# to this list also if it is in closed pre-alpha development.
GAME_INDEX_ENABLED = False
# This dict
GAME_INDEX_LISTING = {
    "game_name": SERVERNAME,
    "game_status": "pre-alpha",  # pre-alpha, alpha, beta or launched
    "short_description": GAME_SLOGAN,
    "long_description": "",
    "listing_contact": "",  # email
    "telnet_hostname": "",  # mygame.com
    "telnet_port": "",  # 1234
    "game_website": "",  # http://mygame.com
    "web_client_url": "",  # http://mygame.com/webclient
}
# Evennia can connect to external IRC channels and
# echo what is said on the channel to IRC and vice
# versa. Obs - make sure the IRC network allows bots.
# When enabled, command @irc2chan will be available in-game
# IRC requires that you have twisted.words installed.
IRC_ENABLED = False
# RSS allows to connect RSS feeds (from forum updates, blogs etc) to
# an in-game channel. The channel will be updated when the rss feed
# updates. Use @rss2chan in game to connect if this setting is
# active. OBS: RSS support requires the python-feedparser package to
# be installed (through package manager or from the website
# http://code.google.com/p/feedparser/)
RSS_ENABLED = False
RSS_UPDATE_INTERVAL = 60 * 10  # 10 minutes
# Grapevine (grapevine.haus) is a network for listing MUDs as well as allow
# users of said MUDs to communicate with each other on shared channels. To use,
# your game must first be registered by logging in and creating a game entry at
# https://grapevine.haus. Evennia links grapevine channels to in-game channels
# with the @grapevine2chan command, available once this flag is set
# Grapevine requires installing the pyopenssl library (pip install pyopenssl)
GRAPEVINE_ENABLED = False
# Grapevine channels to allow connection to. See https://grapevine.haus/chat
# for the available channels. Only channels in this list can be linked to in-game
# channels later.
GRAPEVINE_CHANNELS = ["gossip", "testing"]
# Grapevine authentication. Register your game at https://grapevine.haus to get
# them. These are secret and should thus be overridden in secret_settings file
GRAPEVINE_CLIENT_ID = ""
GRAPEVINE_CLIENT_SECRET = ""

######################################################################
# Django web features
######################################################################

# While DEBUG is False, show a regular server error page on the web
# stuff, email the traceback to the people in the ADMINS tuple
# below. If True, show a detailed traceback for the web
# browser to display. Note however that this will leak memory when
# active, so make sure to turn it off for a production server!
DEBUG = False
# Emails are sent to these people if the above DEBUG value is False. If you'd
# rather prefer nobody receives emails, leave this commented out or empty.
ADMINS = ()  # 'Your Name', 'your_email@domain.com'),)
# These guys get broken link notifications when SEND_BROKEN_LINK_EMAILS is True.
MANAGERS = ADMINS
# This is a public point of contact for players or the public to contact
# a staff member or administrator of the site. It is publicly posted.
STAFF_CONTACT_EMAIL = None
# Absolute path to the directory that holds file uploads from web apps.
# Example: "/home/media/media.lawrence.com"
MEDIA_ROOT = os.path.join(GAME_DIR, "web", "media")
# If using Sites/Pages from the web admin, this value must be set to the
# database-id of the Site (domain) we want to use with this game's Pages.
SITE_ID = 1
# The age for sessions.
# Default: 1209600 (2 weeks, in seconds)
SESSION_COOKIE_AGE = 1209600
# Session cookie domain
# Default: None
SESSION_COOKIE_DOMAIN = None
# The name of the cookie to use for sessions.
# Default: 'sessionid'
SESSION_COOKIE_NAME = "sessionid"
# Should the session expire when the browser closes?
# Default: False
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False
# Where to find locales (no need to change this, most likely)
LOCALE_PATHS = [os.path.join(EVENNIA_DIR, "locale/")]
# This should be turned off unless you want to do tests with Django's
# development webserver (normally Evennia runs its own server)
SERVE_MEDIA = False
# The master urlconf file that contains all of the sub-branches to the
# applications. Change this to add your own URLs to the website.
ROOT_URLCONF = "web.urls"
# Where users are redirected after logging in via contrib.auth.login.
LOGIN_REDIRECT_URL = "/"
# Where to redirect users when using the @login_required decorator.
LOGIN_URL = reverse_lazy("login")
# Where to redirect users who wish to logout.
LOGOUT_URL = reverse_lazy("logout")
# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = "/media/"
# URL prefix for admin media -- CSS, JavaScript and images. Make sure
# to use a trailing slash. Django1.4+ will look for admin files under
# STATIC_URL/admin.
STATIC_URL = "/static/"

STATIC_ROOT = os.path.join(GAME_DIR, "web", "static")

# Location of static data to overload the defaults from
# evennia/web/webclient and evennia/web/website's static/ dirs.
STATICFILES_DIRS = [os.path.join(GAME_DIR, "web", "static_overrides")]
# Patterns of files in the static directories. Used here to make sure that
# its readme file is preserved but unused.
STATICFILES_IGNORE_PATTERNS = ["README.md"]
# The name of the currently selected web template. This corresponds to the
# directory names shown in the templates directory.
WEBSITE_TEMPLATE = "website"
WEBCLIENT_TEMPLATE = "webclient"
# The default options used by the webclient
WEBCLIENT_OPTIONS = {
    "gagprompt": True,  # Gags prompt from the output window and keep them
    # together with the input bar
    "helppopup": False,  # Shows help files in a new popup window
    "notification_popup": False,  # Shows notifications of new messages as
    # popup windows
    "notification_sound": False  # Plays a sound for notifications of new
    # messages
}

# We setup the location of the website template as well as the admin site.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(GAME_DIR, "web", "template_overrides", WEBSITE_TEMPLATE),
            os.path.join(GAME_DIR, "web", "template_overrides", WEBCLIENT_TEMPLATE),
            os.path.join(GAME_DIR, "web", "template_overrides"),
            os.path.join(EVENNIA_DIR, "web", "website", "templates", WEBSITE_TEMPLATE),
            os.path.join(EVENNIA_DIR, "web", "website", "templates"),
            os.path.join(EVENNIA_DIR, "web", "webclient", "templates", WEBCLIENT_TEMPLATE),
            os.path.join(EVENNIA_DIR, "web", "webclient", "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.i18n",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.media",
                "django.template.context_processors.debug",
                "django.contrib.messages.context_processors.messages",
                "sekizai.context_processors.sekizai",
                "evennia.web.utils.general_context.general_context",
            ],
            # While true, show "pretty" error messages for template syntax errors.
            "debug": DEBUG,
        },
    }
]

# MiddleWare are semi-transparent extensions to Django's functionality.
# see http://www.djangoproject.com/documentation/middleware/ for a more detailed
# explanation.
MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",  # 1.4?
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.admindocs.middleware.XViewMiddleware",
    "django.contrib.flatpages.middleware.FlatpageFallbackMiddleware",
    "evennia.web.utils.middleware.SharedLoginMiddleware",
]

######################################################################
# Evennia components
######################################################################

# Global and Evennia-specific apps. This ties everything together so we can
# refer to app models and perform DB syncs.
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.admin",
    "django.contrib.admindocs",
    "django.contrib.flatpages",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "django.contrib.messages",
    "sekizai",
    "evennia.utils.idmapper",
    "evennia.server",
    "evennia.typeclasses",
    "evennia.accounts",
    "evennia.objects",
    "evennia.comms",
    "evennia.help",
    "evennia.scripts",
    "evennia.web.website",
    "evennia.web.webclient",
]
# The user profile extends the User object with more functionality;
# This should usually not be changed.
AUTH_USER_MODEL = "accounts.AccountDB"

# Password validation plugins
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "evennia.server.validators.EvenniaPasswordValidator"},
]

# Username validation plugins
AUTH_USERNAME_VALIDATORS = [
    {"NAME": "django.contrib.auth.validators.ASCIIUsernameValidator"},
    {"NAME": "django.core.validators.MinLengthValidator", "OPTIONS": {"limit_value": 3}},
    {"NAME": "django.core.validators.MaxLengthValidator", "OPTIONS": {"limit_value": 30}},
    {"NAME": "evennia.server.validators.EvenniaUsernameAvailabilityValidator"},
]

# Use a custom test runner that just tests Evennia-specific apps.
TEST_RUNNER = "evennia.server.tests.testrunner.EvenniaTestSuiteRunner"

# Messages and Bootstrap don't classify events the same way; this setting maps
# messages.error() to Bootstrap 'danger' classes.
MESSAGE_TAGS = {messages.ERROR: "danger"}

######################################################################
# Django extensions
######################################################################

# Django extesions are useful third-party tools that are not
# always included in the default django distro.
try:
    import django_extensions  # noqa

    INSTALLED_APPS = INSTALLED_APPS.append("django_extensions")
except ImportError:
    # Django extensions are not installed in all distros.
    pass

#######################################################################
# SECRET_KEY
#######################################################################
# This is the signing key for the cookies generated by Evennia's
# web interface.
#
# It is a fallback for the SECRET_KEY setting in settings.py, which
# is randomly seeded when settings.py is first created. If copying
# from here, make sure to change it!
SECRET_KEY = "changeme!(*#&*($&*(#*(&SDFKJJKLS*(@#KJAS"
