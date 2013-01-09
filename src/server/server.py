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
if os.name == 'nt':
    # For Windows batchfile we need an extra path insertion here.
    sys.path.insert(0, os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))))

from twisted.application import internet, service
from twisted.internet import reactor, defer
import django
from django.db import connection
from django.conf import settings

from src.players.models import PlayerDB
from src.scripts.models import ScriptDB
from src.server.models import ServerConfig
from src.server import initial_setup

from src.utils.utils import get_evennia_version, mod_import, make_iter
from src.comms import channelhandler
from src.server.sessionhandler import SESSIONS

_SA = object.__setattr__

if os.name == 'nt':
    # For Windows we need to handle pid files manually.
    SERVER_PIDFILE = os.path.join(settings.GAME_DIR, 'server.pid')

# a file with a flag telling the server to restart after shutdown or not.
SERVER_RESTART = os.path.join(settings.GAME_DIR, 'server.restart')

# module containing hook methods called during start_stop
SERVER_STARTSTOP_MODULE = mod_import(settings.AT_SERVER_STARTSTOP_MODULE)

# module containing plugin services
SERVER_SERVICES_PLUGIN_MODULES = [mod_import(module) for module in make_iter(settings.SERVER_SERVICES_PLUGIN_MODULES)]

#------------------------------------------------------------
# Evennia Server settings
#------------------------------------------------------------

SERVERNAME = settings.SERVERNAME
VERSION = get_evennia_version()

AMP_ENABLED = True
AMP_HOST = settings.AMP_HOST
AMP_PORT = settings.AMP_PORT
AMP_INTERFACE = settings.AMP_INTERFACE

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

        # Database-specific startup optimizations.
        self.sqlite3_prep()

        # Run the initial setup if needed
        self.run_initial_setup()

        self.start_time = time.time()

        # initialize channelhandler
        channelhandler.CHANNELHANDLER.update()

        # set a callback if the server is killed abruptly,
        # by Ctrl-C, reboot etc.
        reactor.addSystemEventTrigger('before', 'shutdown', self.shutdown, _reactor_stopping=True)

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

    def update_defaults(self):
        """
        We make sure to store the most important object defaults here, so we can catch if they
        change and update them on-objects automatically. This allows for changing default cmdset locations
        and default typeclasses in the settings file and have them auto-update all already existing
        objects.
        """
        # setting names
        settings_names = ("CMDSET_DEFAULT", "CMDSET_OOC", "BASE_PLAYER_TYPECLASS", "BASE_OBJECT_TYPECLASS",
                          "BASE_CHARACTER_TYPECLASS", "BASE_ROOM_TYPECLASS", "BASE_EXIT_TYPECLASS", "BASE_SCRIPT_TYPECLASS")
        # get previous and current settings so they can be compared
        settings_compare = zip([ServerConfig.objects.conf(name) for name in settings_names],
                               [settings.__getattr__(name) for name in settings_names])
        mismatches = [i for i, tup in enumerate(settings_compare) if tup[0] and tup[1] and tup[0] != tup[1]]
        if len(mismatches): # can't use any() since mismatches may be [0] which reads as False for any()
            # we have a changed default. Import relevant objects and run the update
            from src.objects.models import ObjectDB
            #from src.players.models import PlayerDB
            for i, prev, curr in ((i, tup[0], tup[1]) for i, tup in enumerate(settings_compare) if i in mismatches):
                # update the database
                print " one or more default cmdset/typeclass settings changed. Updating defaults stored in database ..."
                if i == 0: [obj.__setattr__("cmdset_storage", curr) for obj in ObjectDB.objects.filter(db_cmdset_storage__exact=prev)]
                if i == 1: [ply.__setattr__("cmdset_storage", curr) for ply in PlayerDB.objects.filter(db_cmdset_storage__exact=prev)]
                if i == 2: [ply.__setattr__("typeclass_path", curr) for ply in PlayerDB.objects.filter(db_typeclass_path__exact=prev)]
                if i in (3,4,5,6): [obj.__setattr__("typeclass_path",curr)
                                    for obj in ObjectDB.objects.filter(db_typeclass_path__exact=prev)]
                if i == 7: [scr.__setattr__("typeclass_path", curr) for scr in ScriptDB.objects.filter(db_typeclass_path__exact=prev)]
                # store the new default and clean caches
                ServerConfig.objects.conf(settings_names[i], curr)
                ObjectDB.flush_instance_cache()
                PlayerDB.flush_instance_cache()
                ScriptDB.flush_instance_cache()
        # if this is the first start we might not have a "previous" setup saved. Store it now.
        [ServerConfig.objects.conf(settings_names[i], tup[1]) for i, tup in enumerate(settings_compare) if not tup[0]]

    def run_initial_setup(self):
        """
        This attempts to run the initial_setup script of the server.
        It returns if this is not the first time the server starts.
        Once finished the last_initial_setup_step is set to -1.
        """
        last_initial_setup_step = ServerConfig.objects.conf('last_initial_setup_step')
        if not last_initial_setup_step:
            # None is only returned if the config does not exist,
            # i.e. this is an empty DB that needs populating.
            print ' Server started for the first time. Setting defaults.'
            initial_setup.handle_setup(0)
            print '-'*50
        elif int(last_initial_setup_step) >= 0:
            # a positive value means the setup crashed on one of its
            # modules and setup will resume from this step, retrying
            # the last failed module. When all are finished, the step
            # is set to -1 to show it does not need to be run again.
            print ' Resuming initial setup from step %(last)s.' % \
                {'last': last_initial_setup_step}
            initial_setup.handle_setup(int(last_initial_setup_step))
            print '-'*50

    def run_init_hooks(self):
        """
        Called every server start
        """
        from src.objects.models import ObjectDB
        #from src.players.models import PlayerDB

        #update eventual changed defaults
        self.update_defaults()

        #print "run_init_hooks:", ObjectDB.get_all_cached_instances()
        [(o.typeclass, o.at_init()) for o in ObjectDB.get_all_cached_instances()]
        [(p.typeclass, p.at_init()) for p in PlayerDB.get_all_cached_instances()]

        if SERVER_STARTSTOP_MODULE:
            # call correct server hook based on start file value
            with open(SERVER_RESTART, 'r') as f:
                mode = f.read()
            if mode in ('True', 'reload'):
                # True was the old reload flag, kept for compatibilty
                SERVER_STARTSTOP_MODULE.at_server_reload_start()
            elif mode in ('reset', 'shutdown'):
                SERVER_STARTSTOP_MODULE.at_server_cold_start()
            # always call this regardless of start type
            SERVER_STARTSTOP_MODULE.at_server_start()

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
            with open(SERVER_RESTART, 'r') as f:
                # mode is either shutdown, reset or reload
                mode = f.read()
        else:
            with open(SERVER_RESTART, 'w') as f:
                f.write(str(mode))
        return mode

        #if mode == None:
        #    f = open(SERVER_RESTART, 'r')
        #    if os.path.exists(SERVER_RESTART) and 'True' == f.read():
        #        mode = 'reload'
        #    else:
        #        mode = 'shutdown'
        #    f.close()
        #else:
        #    restart = mode in ('reload', 'reset')
        #    f = open(SERVER_RESTART, 'w')
        #    f.write(str(restart))
        #    f.close()
        #return mode

    @defer.inlineCallbacks
    def shutdown(self, mode=None, _reactor_stopping=False):
        """
        Shuts down the server from inside it.

        mode - sets the server restart mode.
               'reload' - server restarts, no "persistent" scripts are stopped, at_reload hooks called.
               'reset' - server restarts, non-persistent scripts stopped, at_shutdown hooks called.
               'shutdown' - like reset, but server will not auto-restart.
               None - keep currently set flag from flag file.
        _reactor_stopping - this is set if server is stopped by a kill command OR this method was already called
                  once - in both cases the reactor is dead/stopping already.
        """
        if _reactor_stopping and hasattr(self, "shutdown_complete"):
            # this means we have already passed through this method once; we don't need
            # to run the shutdown procedure again.
            defer.returnValue(None)

        mode = self.set_restart_mode(mode)
        # call shutdown hooks on all cached objects

        from src.objects.models import ObjectDB
        #from src.players.models import PlayerDB
        from src.server.models import ServerConfig

        if mode == 'reload':
            # call restart hooks
            yield [(o.typeclass, o.at_server_reload()) for o in ObjectDB.get_all_cached_instances()]
            yield [(p.typeclass, p.at_server_reload()) for p in PlayerDB.get_all_cached_instances()]
            yield [(s.typeclass, s.pause(), s.at_server_reload()) for s in ScriptDB.get_all_cached_instances()]
            yield self.sessions.all_sessions_portal_sync()
            ServerConfig.objects.conf("server_restart_mode", "reload")

            if SERVER_STARTSTOP_MODULE:
                SERVER_STARTSTOP_MODULE.at_server_reload_stop()

        else:
            if mode == 'reset':
                # don't call disconnect hooks on reset
                yield [(o.typeclass, o.at_server_shutdown()) for o in ObjectDB.get_all_cached_instances()]
            else: # shutdown
                yield [_SA(p, "is_connected", False) for p in PlayerDB.get_all_cached_instances()]
                yield [(o.typeclass, o.at_disconnect(), o.at_server_shutdown()) for o in ObjectDB.get_all_cached_instances()]

            yield [(p.typeclass, p.at_server_shutdown()) for p in PlayerDB.get_all_cached_instances()]
            yield [(s.typeclass, s.at_server_shutdown()) for s in ScriptDB.get_all_cached_instances()]

            ServerConfig.objects.conf("server_restart_mode", "reset")

            if SERVER_STARTSTOP_MODULE:
                SERVER_STARTSTOP_MODULE.at_server_cold_stop()

        if SERVER_STARTSTOP_MODULE:
            SERVER_STARTSTOP_MODULE.at_server_stop()
        # if _reactor_stopping is true, reactor does not need to be stopped again.
        if os.name == 'nt' and os.path.exists(SERVER_PIDFILE):
            # for Windows we need to remove pid files manually
            os.remove(SERVER_PIDFILE)
        if not _reactor_stopping:
            # this will also send a reactor.stop signal, so we set a flag to avoid loops.
            self.shutdown_complete = True
            reactor.callLater(0, reactor.stop)

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

print '-' * 50
print ' %(servername)s Server (%(version)s) started.' % {'servername': SERVERNAME, 'version': VERSION}

if not settings.GAME_CACHE_TYPE:
    print "  caching disabled"

if AMP_ENABLED:

    # The AMP protocol handles the communication between
    # the portal and the mud server. Only reason to ever deactivate
    # it would be during testing and debugging.

    ifacestr = ""
    if AMP_INTERFACE != '127.0.0.1':
        ifacestr = "-%s" % AMP_INTERFACE
    print '  amp (to Portal)%s:%s' % (ifacestr, AMP_PORT)

    from src.server import amp

    factory = amp.AmpServerFactory(EVENNIA)
    amp_service = internet.TCPServer(AMP_PORT, factory, interface=AMP_INTERFACE)
    amp_service.setName("EvenniaPortal")
    EVENNIA.services.addService(amp_service)

if IRC_ENABLED:

    # IRC channel connections

    print '  irc enabled'

    from src.comms import irc
    irc.connect_all()

if IMC2_ENABLED:

    # IMC2 channel connections

    print '  imc2 enabled'

    from src.comms import imc2
    imc2.connect_all()

if RSS_ENABLED:

    # RSS feed channel connections

    print '  rss enabled'

    from src.comms import rss
    rss.connect_all()

for plugin_module in SERVER_SERVICES_PLUGIN_MODULES:
    # external plugin protocols
    plugin_module.start_plugin_services(EVENNIA)

print '-' * 50 # end of terminal output

# clear server startup mode
ServerConfig.objects.conf("server_starting_mode", delete=True)

if os.name == 'nt':
    # Windows only: Set PID file manually
    f = open(os.path.join(settings.GAME_DIR, 'server.pid'), 'w')
    f.write(str(os.getpid()))
    f.close()
