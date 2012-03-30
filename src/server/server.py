"""
This module implements the main Evennia server process, the core of
the game engine.

This module should be started with the 'twistd' executable since it
sets up all the networking features.  (this is done automatically
by game/evennia.py).

"""
import time
import sys
import os
import signal
if os.name == 'nt':
    # For Windows batchfile we need an extra path insertion here.
    sys.path.insert(0, os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))))

from twisted.application import internet, service
from twisted.internet import protocol, reactor, defer
from twisted.web import server, static
import django
from django.db import connection
from django.conf import settings

from src.scripts.models import ScriptDB
from src.server.models import ServerConfig
from src.server import initial_setup

from src.utils.utils import get_evennia_version, mod_import
from src.comms import channelhandler
from src.server.sessionhandler import SESSIONS

if os.name == 'nt':
    # For Windows we need to handle pid files manually.
    SERVER_PIDFILE = os.path.join(settings.GAME_DIR, 'server.pid')

# a file with a flag telling the server to restart after shutdown or not.
SERVER_RESTART = os.path.join(settings.GAME_DIR, 'server.restart')

# module containing hook methods
SERVER_HOOK_MODULE = mod_import(settings.AT_SERVER_STARTSTOP_MODULE)

# i18n
from django.utils.translation import ugettext as _

#------------------------------------------------------------
# Evennia Server settings
#------------------------------------------------------------

SERVERNAME = settings.SERVERNAME
VERSION = get_evennia_version()

AMP_ENABLED = True
AMP_HOST = settings.AMP_HOST
AMP_PORT = settings.AMP_PORT

# server-channel mappings
IMC2_ENABLED = settings.IMC2_ENABLED
IRC_ENABLED = settings.IRC_ENABLED
RSS_ENABLED = settings.RSS_ENABLED

#------------------------------------------------------------
# Evennia Main Server object
#------------------------------------------------------------
class Evennia(object):

    """
    The main Evennia server handler. This object sets up the database and
    tracks and interlinks all the twisted network services that make up
    evennia.
    """

    def __init__(self, application):
        """
        Setup the server.

        application - an instantiated Twisted application

        """
        sys.path.append('.')

        # create a store of services
        self.services = service.IServiceCollection(application)
        self.amp_protocol = None # set by amp factory
        self.sessions = SESSIONS
        self.sessions.server = self

        print '\n' + '-'*50

        # Database-specific startup optimizations.
        self.sqlite3_prep()

        # Run the initial setup if needed
        self.run_initial_setup()

        self.start_time = time.time()

        # initialize channelhandler
        channelhandler.CHANNELHANDLER.update()

        # Make info output to the terminal.
        self.terminal_output()

        print '-'*50

        # set a callback if the server is killed abruptly,
        # by Ctrl-C, reboot etc.
        reactor.addSystemEventTrigger('before', 'shutdown', self.shutdown, _abrupt=True)

        self.game_running = True

        self.run_init_hooks()

    # Server startup methods

    def sqlite3_prep(self):
        """
        Optimize some SQLite stuff at startup since we
        can't save it to the database.
        """
        if ((".".join(str(i) for i in django.VERSION) < "1.2" and settings.DATABASE_ENGINE == "sqlite3")
            or (hasattr(settings, 'DATABASES')
                and settings.DATABASES.get("default", {}).get('ENGINE', None)
                == 'django.db.backends.sqlite3')):
            cursor = connection.cursor()
            cursor.execute("PRAGMA cache_size=10000")
            cursor.execute("PRAGMA synchronous=OFF")
            cursor.execute("PRAGMA count_changes=OFF")
            cursor.execute("PRAGMA temp_store=2")

    def run_initial_setup(self):
        """
        This attempts to run the initial_setup script of the server.
        It returns if this is not the first time the server starts.
        """
        last_initial_setup_step = ServerConfig.objects.conf('last_initial_setup_step')
        if not last_initial_setup_step:
            # None is only returned if the config does not exist,
            # i.e. this is an empty DB that needs populating.
            print _(' Server started for the first time. Setting defaults.')
            initial_setup.handle_setup(0)
            print '-'*50
        elif int(last_initial_setup_step) >= 0:
            # a positive value means the setup crashed on one of its
            # modules and setup will resume from this step, retrying
            # the last failed module. When all are finished, the step
            # is set to -1 to show it does not need to be run again.
            print _(' Resuming initial setup from step %(last)s.' % \
                {'last': last_initial_setup_step})
            initial_setup.handle_setup(int(last_initial_setup_step))
            print '-'*50

    def run_init_hooks(self):
        """
        Called every server start
        """
        from src.objects.models import ObjectDB
        from src.players.models import PlayerDB

        #print "run_init_hooks:", ObjectDB.get_all_cached_instances()
        [(o.typeclass, o.at_init()) for o in ObjectDB.get_all_cached_instances()]
        [(p.typeclass, p.at_init()) for p in PlayerDB.get_all_cached_instances()]

        # call server hook.
        if SERVER_HOOK_MODULE:
            SERVER_HOOK_MODULE.at_server_start()

    def terminal_output(self):
        """
        Outputs server startup info to the terminal.
        """
        print _(' %(servername)s Server (%(version)s) started.') % {'servername': SERVERNAME, 'version': VERSION}
        print '  amp (Portal): %s' % AMP_PORT

    def set_restart_mode(self, mode=None):
        """
        This manages the flag file that tells the runner if the server is
        reloading, resetting or shutting down. Valid modes are
          'reload', 'reset', 'shutdown' and None.
        If mode is None, no change will be done to the flag file.

        Either way, the active restart setting (Restart=True/False) is
        returned so the server knows which more it's in.
        """
        if mode == None:
            if os.path.exists(SERVER_RESTART) and 'True' == open(SERVER_RESTART, 'r').read():
                mode = 'reload'
            else:
                mode = 'shutdown'
        else:
            restart = mode in ('reload', 'reset')
            f = open(SERVER_RESTART, 'w')
            f.write(str(restart))
            f.close()
        return mode

    def shutdown(self, mode=None, _abrupt=False):
        """
        Shuts down the server from inside it.

        mode - sets the server restart mode.
               'reload' - server restarts, no "persistent" scripts are stopped, at_reload hooks called.
               'reset' - server restarts, non-persistent scripts stopped, at_shutdown hooks called.
               'shutdown' - like reset, but server will not auto-restart.
               None - keep currently set flag from flag file.
        _abrupt - this is set if server is stopped by a kill command,
                  in which case the reactor is dead anyway.
        """
        mode = self.set_restart_mode(mode)

        # call shutdown hooks on all cached objects

        from src.objects.models import ObjectDB
        from src.players.models import PlayerDB
        from src.server.models import ServerConfig

        if mode == 'reload':
            # call restart hooks
            [(o.typeclass, o.at_server_reload()) for o in ObjectDB.get_all_cached_instances()]
            [(p.typeclass, p.at_server_reload()) for p in PlayerDB.get_all_cached_instances()]
            [(s.typeclass, s.pause(), s.at_server_reload()) for s in ScriptDB.get_all_cached_instances()]

            ServerConfig.objects.conf("server_restart_mode", "reload")

        else:
            if mode == 'reset':
                # don't call disconnect hooks on reset
                [(o.typeclass, o.at_server_shutdown()) for o in ObjectDB.get_all_cached_instances()]
            else: # shutdown
                [(o.typeclass, o.at_disconnect(), o.at_server_shutdown()) for o in ObjectDB.get_all_cached_instances()]

            [(p.typeclass, p.at_server_shutdown()) for p in PlayerDB.get_all_cached_instances()]
            [(s.typeclass, s.at_server_shutdown()) for s in ScriptDB.get_all_cached_instances()]

            ServerConfig.objects.conf("server_restart_mode", "reset")

        if not _abrupt:
            if SERVER_HOOK_MODULE:
                SERVER_HOOK_MODULE.at_server_stop()
            reactor.callLater(0, reactor.stop)
        if os.name == 'nt' and os.path.exists(SERVER_PIDFILE):
            # for Windows we need to remove pid files manually
            os.remove(SERVER_PIDFILE)

#------------------------------------------------------------
#
# Start the Evennia game server and add all active services
#
#------------------------------------------------------------

# Tell the system the server is starting up; some things are not available yet
ServerConfig.objects.conf("server_starting_mode", True)

# twistd requires us to define the variable 'application' so it knows
# what to execute from.
application = service.Application('Evennia')

# The main evennia server program. This sets up the database
# and is where we store all the other services.
EVENNIA = Evennia(application)

# The AMP protocol handles the communication between
# the portal and the mud server. Only reason to ever deactivate
# it would be during testing and debugging.

if AMP_ENABLED:

    from src.server import amp

    factory = amp.AmpServerFactory(EVENNIA)
    amp_service = internet.TCPServer(AMP_PORT, factory)
    amp_service.setName("EvenniaPortal")
    EVENNIA.services.addService(amp_service)


if IRC_ENABLED:

    # IRC channel connections

    from src.comms import irc
    irc.connect_all()

if IMC2_ENABLED:

    # IMC2 channel connections

    from src.comms import imc2
    imc2.connect_all()

if RSS_ENABLED:

    # RSS feed channel connections
    from src.comms import rss
    rss.connect_all()

# clear server startup mode
ServerConfig.objects.conf("server_starting_mode", delete=True)

if os.name == 'nt':
    # Windows only: Set PID file manually
    f = open(os.path.join(settings.GAME_DIR, 'server.pid'), 'w')
    f.write(str(os.getpid()))
    f.close()
