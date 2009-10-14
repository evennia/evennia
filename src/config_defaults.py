"""
Master configuration file for Evennia.

NOTE: NO MODIFICATIONS SHOULD BE MADE TO THIS FILE! All settings changes should
be done by copy-pasting the variable and its value to your game directory's
settings.py file.
"""
import os

# A list of ports to listen on. Can be one or many.
GAMEPORTS = [4000]

# While DEBUG is False, show a regular server error page on the web stuff,
# email the traceback to the people in the ADMINS tuple below. By default (True),
# show a detailed traceback for the web browser to display.
DEBUG = True

# While true, show "pretty" error messages for template syntax errors.
TEMPLATE_DEBUG = DEBUG

# Emails are sent to these people if the above DEBUG value is False. If you'd
# rather nobody recieve emails, leave this commented out or empty.
ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

# These guys get broken link notifications when SEND_BROKEN_LINK_EMAILS is True.
MANAGERS = ADMINS

# The path that contains this settings.py file (no trailing slash).
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Path to the game directory (containing the database file if using sqlite).
GAME_DIR = os.path.join(BASE_PATH, 'game')

# Logging paths
LOG_DIR = os.path.join(GAME_DIR, 'logs')
DEFAULT_LOG_FILE = os.path.join(LOG_DIR, 'evennia.log')

# Path to the src directory containing the bulk of the codebase's code.
SRC_DIR = os.path.join(BASE_PATH, 'src')

# Absolute path to the directory that holds media (no trailing slash).
# Example: "/home/media/media.lawrence.com"
MEDIA_ROOT = os.path.join(GAME_DIR, 'web', 'media')

# Import style path to the script parent module. Must be in the import path.
SCRIPT_IMPORT_PATH = 'game.gamesrc.parents'
# Default parent associated with non-player objects. This starts from where
# the SCRIPT_IMPORT_PATH left off.
SCRIPT_DEFAULT_OBJECT = 'base.basicobject'
# Default parent associated with player objects. This starts from where
# the SCRIPT_IMPORT_PATH left off.
SCRIPT_DEFAULT_PLAYER = 'base.basicplayer'

# 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3', and 'oracle'.
DATABASE_ENGINE = 'sqlite3'
# Database name, or path to DB file if using sqlite3.
DATABASE_NAME = os.path.join(GAME_DIR, 'evennia.db3')
# Unused for sqlite3
DATABASE_USER = ''
# Unused for sqlite3
DATABASE_PASSWORD = ''
# Empty string defaults to localhost. Not used with sqlite3.
DATABASE_HOST = ''
# Empty string defaults to localhost. Not used with sqlite3.
DATABASE_PORT = ''

## Permissions
## The variables in this section are used by each evennia subsystem to tell which permissions to define.
## These variables are called by the respective subsystem ('application' in django lingo) of Evennia. The final
## look of the permission will be 'app.permission', e.g. 'irc.admin.irc_channels'.
## Note that beyond what is listed here, django automatically creates 3 add/change/delete permissions
## for each model defined in each appliction. These are however not used by any default commands in
## game and are filtered out in e.g. @adminperm/list in order to give the admin more overview.
## Note that all variables here must be proper nested tuples of tuples. ( (),(), )

# irc permissions
PERM_IRC = ( 
    ('admin_irc_channels', 'May administer IRC channels.'),)
# imc2 permissions 
PERM_IMC2 = ( 
    ('admin_imc_channels', 'May administer IMC channels.'),)
# general channel permissions
PERM_CHANNELS = ( 
    ('emit_commchannel', 'May @cemit over channels.'),
    ('channel_admin', 'May administer comm channels.'),
    ('page','May page other users.'),)
# help system access permissions
PERM_HELPSYS = ( 
    ("admin_help","May admin the help system"),
    ("staff_help", "May see staff help topics."),
    ("add_help", "May add or append to help entries"),
    ("del_help", "May delete help entries"),)
# object manipulation/information permissions
PERM_OBJECTS = ( 
    ("teleport","May teleport an object to any location."),
    ("wipe","May wipe all attributes on an object."),
    ("modify_attributes","May modify/delete/add attributes to an object."),
    ("info","May search for and examine objects."),
    ("create", "May create, copy and destroy objects."),
    ("dig", "May dig new rooms, open new exits and link them."),
    ("admin_ownership", "May change ownership of any object."),
    ("see_dbref","May see an object's dbref."),)
# misc general and admin permissions 
PERM_GENPERMS = ( 
    ("announce", "May make announcements to everyone."),
    ("admin_perm", "Can modify individual permissions."),
    ("admin_group", "Can manage membership in groups."),
    ("process_control", "May shutdown/restart/reload the game"),
    ("manage_players", "Can change passwords, siteban, etc."),
    ("game_info", "Can review game metadata"),)

    ## These permissions are not yet used in the default engine. 
    ## ("boot", "May use @boot to kick players"),
    ## ("chown_all", "Can @chown anything to anyone."),    
    ## ("free_money", "Has infinite money"),
    ## ("long_fingers", "May get/look/examine etc. from a distance"),
    ## ("steal", "May give negative money"),
    ## ("set_hide", "May set themself invisible"),
    ## ("tel_anywhere", "May @teleport anywhere"),
    ## ("tel_anyone", "May @teleport anything"),
    ## ("see_session_data", "May see detailed player session data"),)

# Gathering of all permission tuple groups. This is used by e.g. @adminperm to only show these permissions.
PERM_ALL_DEFAULTS = (PERM_IRC, PERM_IMC2, PERM_CHANNELS, PERM_HELPSYS, PERM_OBJECTS, PERM_GENPERMS)
# If you defined your own tuple groups, add them below. 
PERM_ALL_CUSTOM = ()

## Permission Groups 
## Permission groups clump the permissions into larger chunks for quick assigning to
## a user (e.g. a builder). Each permission is written on the form app.permission,
## e.g. 'helpsys.view_staff_help'. Each group can contain an arbitrary number of
## permissions. A user is added to a group with the default @admingroup command.
## Superusers are automatically members of all groups.

# A dict defining the groups, on the form {group_name:(perm1,perm2,...),...}
PERM_GROUPS = \
    {"Immortals":('irc.admin_irc_channels', 'imc2.admin_imc_channels', 'channels.emit_commchannel',
                  'channels.channel_admin', 'channels.page', 'helpsys.admin_help',
                  'helpsys.staff_help', 'helpsys.add_help',
                  'helpsys.del_help', 'objects.teleport', 'objects.wipe', 'objects.modify_attributes',
                  'objects.info','objects.create','objects.dig','objects.see_dbref',
                  'objects.admin_ownership', 'genperms.announce', 'genperms.admin_perm',
                  'genperms.admin_group', 'genperms.process_control', 'genperms.manage_players',
                  'genperms.game_info'),
    "Wizards": ('irc.admin_irc_channels', 'imc2.admin_imc_channels', 'channels.emit_commchannel',
                'channels.channel_admin', 'channels.page', 'helpsys.admin_help',
                'helpsys.staff_help', 'helpsys.add_help',
                'helpsys.del_help', 'objects.teleport', 'objects.wipe', 'objects.see_dbref',
                'objects.modify_attributes', 'objects.info', 'objects.create', 'objects.dig',
                'objects.admin_ownership', 'genperms.announce', 'genperms.game_info'),
     "Builders":('channels.emit_commchannel', 'channels.page', 'helpsys.staff_help',
                 'helpsys.add_help', 'helpsys.del_help',
                 'objects.teleport', 'objects.wipe', 'objects.see_dbref',
                 'objects.modify_attributes', 'objects.info',
                 'objects.create', 'objects.dig', 'genperms.game_info'),
     "Player Helpers":('channels.emit_commchannel', 'channels.page', 'helpsys.staff_help',
                       'helpsys.add_help', 'helpsys.del_help'),
     "Players":('channels.emit_commchannel', 'channels.page')
             }
# By defining a default player group, all players may start with some permissions pre-set. 
PERM_DEFAULT_PLAYER_GROUP = "Players"

## Help system
## Evennia allows automatic help-updating of commands by use of the auto-help system
## which use the command's docstrings for documentation, automatically updating it
## as commands are reloaded. Auto-help is a powerful way to keep your help database
## up-to-date, but it will also overwrite manual changes made
## to the help database using other means (@set_help, admin interface etc), so 
## for a production environment you might want to turn auto-help off. You can
## later activate auto-help on a per-command basis (e.g. when developing a new command)
## using the auto_help_override argument to add_command(). 

# activate the auto-help system
HELP_AUTO_ENABLED = True 
# Add a dynamically calculated 'See also' footer to help entries
HELP_SHOW_RELATED = True

## Channels
## Your names of various default comm channels for emitting debug- or informative messages.

COMMCHAN_MUD_INFO = 'MUDInfo'
COMMCHAN_MUD_CONNECTIONS = 'MUDConnections'
COMMCHAN_IMC2_INFO = 'MUDInfo'
COMMCHAN_IRC_INFO = 'MUDInfo'

## IMC Configuration
## IMC (Inter-MUD communication) allows for an evennia chat channel that connects
## to people on other MUDs also using the IMC. Your evennia server do *not* have
## to be open to the public to use IMC; it works as a stand-alone chat client.
## 
## Copy and paste this section to your game/settings.py file and change the
## values to fit your needs.
## 
## Evennia's IMC2 client was developed against MudByte's network. You must
## register your MUD on the network before you can use it, go to
## http://www.mudbytes.net/imc2-intermud-join-network.
## 
## Choose 'Other unsupported IMC2 version' from the choices and
## and enter your information there. You have to enter the same
## 'short mud name', 'client password' and 'server password' as you
## define in this file. 
## The Evennia discussion channel is on server02.mudbytes.net:9000.

# Change to True if you want IMC active at all.
IMC2_ENABLED = False
# The hostname/ip address of your IMC2 server of choice.
IMC2_SERVER_ADDRESS = 'server02.mudbytes.net' 
#IMC2_SERVER_ADDRESS = None
# The port to connect to on your IMC2 server.
IMC2_SERVER_PORT = 9000
#IMC2_SERVER_PORT = None
# This is your game's IMC2 name on the network (e.g. "MyMUD").
IMC2_MUDNAME = None 
# Your IMC2 client-side password. Used to authenticate with your network. 
IMC2_CLIENT_PW = None 
# Your IMC2 server-side password. Used to verify your network's identity.
IMC2_SERVER_PW = None 
# Emit additional debugging info to log.
IMC2_DEBUG = False
# This isn't something you should generally change.
IMC2_PROTOCOL_VERSION = '2'

## IRC config. This allows your evennia channels to connect to an external IRC
## channel. Evennia will connect under a nickname that then echoes what is
## said on the channel to IRC and vice versa.
## Obs - make sure the IRC network allows bots. 

#Activate the IRC bot. 
IRC_ENABLED = False
#Which IRC network (e.g. irc.freenode.net)
IRC_NETWORK = "irc.freenode.net"
#Which IRC port to connect to (e.g. 6667)
IRC_PORT = 6667
#Which channel on the network to connect to (including the #)
IRC_CHANNEL = ""
#Under what nickname should Evennia connect to the channel
IRC_NICKNAME = ""

# Local time zone for this installation. All choices can be found here:
# http://www.postgresql.org/docs/8.0/interactive/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
LANGUAGE_CODE = 'en-us'

# It's safe to dis-regard this, as it's a Django feature we only half use as a
# dependency, not actually what it's primarily meant for.
SITE_ID = 1

# The age for sessions.
# Default: 1209600 (2 weeks, in seconds)
SESSION_COOKIE_AGE = 1209600

# Session cookie domain
# Default: None
# SESSION_COOKIE_DOMAIN = None

# The name of the cookie to use for sessions.
# Default: 'sessionid'
SESSION_COOKIE_NAME = 'sessionid'

# Should the session expire when the browser closes?
# Default: False
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you'd like to serve media files via Django (strongly not recommended!),
# set SERVE_MEDIA to True. This is appropriate on a developing site, or if 
# you're running Django's built-in test server. Normally you want a webserver 
# that is optimized for serving static content to handle media files (apache, 
# lighttpd).
SERVE_MEDIA = True

# The master urlconf file that contains all of the sub-branches to the
# applications.
ROOT_URLCONF = 'game.web.urls'

# Where users are redirected after logging in via contribu.auth.login.
LOGIN_REDIRECT_URL = '/'

# Where to redirect users when using the @login_required decorator.
LOGIN_URL = '/accounts/login'

# Where to redirect users who wish to logout.
LOGOUT_URL = '/accounts/login'

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/amedia/'

# Make this unique, and don't share it with anybody.
# NOTE: If you change this after creating any accounts, your users won't be
# able to login, as the SECRET_KEY is used to salt passwords.
SECRET_KEY = 'changeme!(*#&*($&*(#*(&SDFKJJKLS*(@#KJAS'

# The name of the currently selected web template. This corresponds to the
# directory names shown in the webtemplates directory.
ACTIVE_TEMPLATE = 'prosimii'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(GAME_DIR, "web", "html", ACTIVE_TEMPLATE),
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

# MiddleWare are semi-transparent extensions to Django's functionality.
# see http://www.djangoproject.com/documentation/middleware/ for a more detailed
# explanation.
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
)

# Context processors define context variables, generally for the template
# system to use.
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.i18n',
    'django.core.context_processors.request',
    'django.core.context_processors.auth',
    'django.core.context_processors.media',
    'django.core.context_processors.debug',
    'game.web.apps.website.webcontext.general_context',
)

# Global and Evennia-specific apps. This ties everything together so we can
# refer to app models and perform DB syncs.
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.sites',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.flatpages',
    'src.config',
    'src.objects',
    'src.channels',
    'src.imc2',
    'src.irc',
    'src.helpsys',
    'src.genperms',
    'game.web.apps.news',
    'game.web.apps.website',    
)

"""
A tuple of strings representing all of the Evennia (IE: non-custom) command
modules that are used at the login screen in the UNLOGGED command table. Do
not modify this directly, add your custom command modules to
CUSTOM_UNLOGGED_COMMAND_MODULES.
"""
UNLOGGED_COMMAND_MODULES = (
    'src.commands.unloggedin',
)

"""
Add your custom command modules under game/gamesrc/commands and to this list.
These will be loaded after the Evennia codebase modules, meaning that any
duplicate command names will be overridden by your version.
"""
CUSTOM_UNLOGGED_COMMAND_MODULES = ()

"""
A tuple of strings representing all of the Evennia (IE: non-custom)
command modules. Do not modify this directly, add your custom command
modules to CUSTOM_COMMAND_MODULES.
"""
COMMAND_MODULES = (
    'src.commands.comsys',
    'src.commands.general',
    'src.commands.info',
    'src.commands.objmanip',
    'src.commands.paging',
    'src.commands.parents',
    'src.commands.privileged',
    'src.commands.search',
    'src.commands.imc2',
    'src.commands.irc',
    'src.commands.batchprocess'
)

"""
Add your custom command modules under game/gamesrc/commands and to this list.
These will be loaded after the Evennia codebase modules, meaning that any
duplicate command names will be overridden by your version.
"""
CUSTOM_COMMAND_MODULES = ()

# If django_extensions is present, import it and install it. Otherwise fail
# silently.
try:
    import django_extensions
    INSTALLED_APPS = INSTALLED_APPS + ('django_extensions',)
except ImportError:
    pass
