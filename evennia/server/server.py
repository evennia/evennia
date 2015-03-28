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

from twisted.web import server, static
from twisted.application import internet, service
from twisted.internet import reactor, defer
from twisted.internet.task import LoopingCall

import django
django.setup()

import evennia
evennia._init()

from django.db import connection
from django.conf import settings

from evennia.players.models import PlayerDB
from evennia.scripts.models import ScriptDB
from evennia.server.models import ServerConfig
from evennia.server import initial_setup

from evennia.utils.utils import get_evennia_version, mod_import, make_iter
from evennia.comms import channelhandler
from evennia.server.sessionhandler import SESSIONS

_SA = object.__setattr__

if os.name == 'nt':
    # For Windows we need to handle pid files manually.
    SERVER_PIDFILE = os.path.join(settings.GAME_DIR, "server", 'server.pid')

# a file with a flag telling the server to restart after shutdown or not.
SERVER_RESTART = os.path.join(settings.GAME_DIR, "server", 'server.restart')

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

WEBSERVER_PORTS = settings.WEBSERVER_PORTS
WEBSERVER_INTERFACES = settings.WEBSERVER_INTERFACES

GUEST_ENABLED = settings.GUEST_ENABLED

# server-channel mappings
WEBSERVER_ENABLED = settings.WEBSERVER_ENABLED and WEBSERVER_PORTS and WEBSERVER_INTERFACES
IMC2_ENABLED = settings.IMC2_ENABLED
IRC_ENABLED = settings.IRC_ENABLED
RSS_ENABLED = settings.RSS_ENABLED
WEBCLIENT_ENABLED = settings.WEBCLIENT_ENABLED


# Maintenance function - this is called repeatedly by the server

_MAINTENANCE_COUNT = 0
_FLUSH_CACHE = None
_IDMAPPER_CACHE_MAXSIZE = settings.IDMAPPER_CACHE_MAXSIZE
_GAMETIME_MODULE = None

def _server_maintenance():
    """
    This maintenance function handles repeated checks and updates that
    the server needs to do. It is called every 5 minutes.
    """
    global EVENNIA, _MAINTENANCE_COUNT, _FLUSH_CACHE, _GAMETIME_MODULE
    if not _FLUSH_CACHE:
        from evennia.utils.idmapper.models import conditional_flush as _FLUSH_CACHE
    if not _GAMETIME_MODULE:
        from evennia.utils import gametime as _GAMETIME_MODULE

    _MAINTENANCE_COUNT += 1

    now = time.time()
    if _MAINTENANCE_COUNT == 1:
        # first call after a reload
        _GAMETIME_MODULE.SERVER_START_TIME = now
        _GAMETIME_MODULE.SERVER_RUNTIME = ServerConfig.objects.conf("runtime", default=0.0)
    else:
        _GAMETIME_MODULE.SERVER_RUNTIME += 60.0
    # update game time and save it across reloads
    _GAMETIME_MODULE.SERVER_RUNTIME_LAST_UPDATED = now
    ServerConfig.objects.conf("runtime", _GAMETIME_MODULE.SERVER_RUNTIME)

    if _MAINTENANCE_COUNT % 300 == 0:
        # check cache size every 5 minutes
        _FLUSH_CACHE(_IDMAPPER_CACHE_MAXSIZE)
    if _MAINTENANCE_COUNT % 3600 == 0:
        # validate scripts every hour
        evennia.ScriptDB.objects.validate()
    if _MAINTENANCE_COUNT % 3700 == 0:
        # validate channels off-sync with scripts
        evennia.CHANNEL_HANDLER.update()
    ## Commenting this out, it is probably not needed
    ## with CONN_MAX_AGE set. Keeping it as a reminder
    ## if database-gone-away errors appears again /Griatch
    #if _MAINTENANCE_COUNT % 18000 == 0:
    #    connection.close()
maintenance_task = LoopingCall(_server_maintenance)
maintenance_task.start(60, now=True) # call every minute

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
        sys.path.insert(1, '.')

        # create a store of services
        self.services = service.IServiceCollection(application)
        self.amp_protocol = None  # set by amp factory
        self.sessions = SESSIONS
        self.sessions.server = self

        # Database-specific startup optimizations.
        self.sqlite3_prep()

        self.start_time = time.time()

        # Run the initial setup if needed
        self.run_initial_setup()

        # initialize channelhandler
        channelhandler.CHANNELHANDLER.update()

        # set a callback if the server is killed abruptly,
        # by Ctrl-C, reboot etc.
        reactor.addSystemEventTrigger('before', 'shutdown',
                                          self.shutdown, _reactor_stopping=True)
        self.game_running = True

        # track the server time
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
        We make sure to store the most important object defaults here, so
        we can catch if they change and update them on-objects automatically.
        This allows for changing default cmdset locations and default
        typeclasses in the settings file and have them auto-update all
        already existing objects.
        """
        # setting names
        settings_names = ("CMDSET_CHARACTER", "CMDSET_PLAYER",
                          "BASE_PLAYER_TYPECLASS", "BASE_OBJECT_TYPECLASS",
                          "BASE_CHARACTER_TYPECLASS", "BASE_ROOM_TYPECLASS",
                          "BASE_EXIT_TYPECLASS", "BASE_SCRIPT_TYPECLASS",
                          "BASE_CHANNEL_TYPECLASS")
        # get previous and current settings so they can be compared
        settings_compare = zip([ServerConfig.objects.conf(name) for name in settings_names],
                               [settings.__getattr__(name) for name in settings_names])
        mismatches = [i for i, tup in enumerate(settings_compare) if tup[0] and tup[1] and tup[0] != tup[1]]
        if len(mismatches):  # can't use any() since mismatches may be [0] which reads as False for any()
            # we have a changed default. Import relevant objects and
            # run the update
            from evennia.objects.models import ObjectDB
            from evennia.comms.models import ChannelDB
            #from evennia.players.models import PlayerDB
            for i, prev, curr in ((i, tup[0], tup[1]) for i, tup in enumerate(settings_compare) if i in mismatches):
                # update the database
                print " %s:\n '%s' changed to '%s'. Updating unchanged entries in database ..." % (settings_names[i], prev, curr)
                if i == 0:
                    ObjectDB.objects.filter(db_cmdset_storage__exact=prev).update(db_cmdset_storage=curr)
                if i == 1:
                    PlayerDB.objects.filter(db_cmdset_storage__exact=prev).update(db_cmdset_storage=curr)
                if i == 2:
                    PlayerDB.objects.filter(db_typeclass_path__exact=prev).update(db_typeclass_path=curr)
                if i in (3, 4, 5, 6):
                    ObjectDB.objects.filter(db_typeclass_path__exact=prev).update(db_typeclass_path=curr)
                if i == 7:
                    ScriptDB.objects.filter(db_typeclass_path__exact=prev).update(db_typeclass_path=curr)
                if i == 8:
                    ChannelDB.objects.filter(db_typeclass_path__exact=prev).update(db_typeclass_path=curr)
                # store the new default and clean caches
                ServerConfig.objects.conf(settings_names[i], curr)
                ObjectDB.flush_instance_cache()
                PlayerDB.flush_instance_cache()
                ScriptDB.flush_instance_cache()
                ChannelDB.flush_instance_cache()
        # if this is the first start we might not have a "previous"
        # setup saved. Store it now.
        [ServerConfig.objects.conf(settings_names[i], tup[1])
                        for i, tup in enumerate(settings_compare) if not tup[0]]

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
            print '-' * 50
        elif int(last_initial_setup_step) >= 0:
            # a positive value means the setup crashed on one of its
            # modules and setup will resume from this step, retrying
            # the last failed module. When all are finished, the step
            # is set to -1 to show it does not need to be run again.
            print ' Resuming initial setup from step %(last)s.' % \
                {'last': last_initial_setup_step}
            initial_setup.handle_setup(int(last_initial_setup_step))
            print '-' * 50

    def run_init_hooks(self):
        """
        Called every server start
        """
        from evennia.objects.models import ObjectDB
        #from evennia.players.models import PlayerDB

        #update eventual changed defaults
        self.update_defaults()

        #print "run_init_hooks:", ObjectDB.get_all_cached_instances()
        [o.at_init() for o in ObjectDB.get_all_cached_instances()]
        [p.at_init() for p in PlayerDB.get_all_cached_instances()]

        with open(SERVER_RESTART, 'r') as f:
            mode = f.read()
        if mode in ('True', 'reload'):
            from evennia.server.oobhandler import OOB_HANDLER
            OOB_HANDLER.restore()

        from evennia.scripts.tickerhandler import TICKER_HANDLER
        TICKER_HANDLER.restore()

        # call correct server hook based on start file value
        if mode in ('True', 'reload'):
            # True was the old reload flag, kept for compatibilty
            self.at_server_reload_start()
        elif mode in ('reset', 'shutdown'):
            self.at_server_cold_start()
            # clear eventual lingering session storages
            ObjectDB.objects.clear_all_sessids()
        # always call this regardless of start type
        self.at_server_start()

    def set_restart_mode(self, mode=None):
        """
        This manages the flag file that tells the runner if the server is
        reloading, resetting or shutting down. Valid modes are
          'reload', 'reset', 'shutdown' and None.
        If mode is None, no change will be done to the flag file.

        Either way, the active restart setting (Restart=True/False) is
        returned so the server knows which more it's in.
        """
        if mode is None:
            with open(SERVER_RESTART, 'r') as f:
                # mode is either shutdown, reset or reload
                mode = f.read()
        else:
            with open(SERVER_RESTART, 'w') as f:
                f.write(str(mode))
        return mode

    @defer.inlineCallbacks
    def shutdown(self, mode=None, _reactor_stopping=False):
        """
        Shuts down the server from inside it.

        mode - sets the server restart mode.
               'reload' - server restarts, no "persistent" scripts
                          are stopped, at_reload hooks called.
               'reset' - server restarts, non-persistent scripts stopped,
                         at_shutdown hooks called.
               'shutdown' - like reset, but server will not auto-restart.
               None - keep currently set flag from flag file.
        _reactor_stopping - this is set if server is stopped by a kill
                            command OR this method was already called
                             once - in both cases the reactor is
                             dead/stopping already.
        """
        if _reactor_stopping and hasattr(self, "shutdown_complete"):
            # this means we have already passed through this method
            # once; we don't need to run the shutdown procedure again.
            defer.returnValue(None)

        mode = self.set_restart_mode(mode)
        # call shutdown hooks on all cached objects

        from evennia.objects.models import ObjectDB
        #from evennia.players.models import PlayerDB
        from evennia.server.models import ServerConfig

        if mode == 'reload':
            # call restart hooks
            yield [o.at_server_reload() for o in ObjectDB.get_all_cached_instances()]
            yield [p.at_server_reload() for p in PlayerDB.get_all_cached_instances()]
            yield [(s.pause(), s.at_server_reload()) for s in ScriptDB.get_all_cached_instances()]
            yield self.sessions.all_sessions_portal_sync()
            ServerConfig.objects.conf("server_restart_mode", "reload")

            from evennia.server.oobhandler import OOB_HANDLER
            OOB_HANDLER.save()
            from evennia.scripts.tickerhandler import TICKER_HANDLER
            TICKER_HANDLER.save()

            self.at_server_reload_stop()

        else:
            if mode == 'reset':
                # don't unset the is_connected flag on reset, otherwise
                # same as shutdown
                yield [o.at_server_shutdown() for o in ObjectDB.get_all_cached_instances()]
                yield [p.at_server_shutdown() for p in PlayerDB.get_all_cached_instances()]
            else:  # shutdown
                yield [_SA(p, "is_connected", False) for p in PlayerDB.get_all_cached_instances()]
                yield [o.at_server_shutdown() for o in ObjectDB.get_all_cached_instances()]
                yield [(p.unpuppet_all(), p.at_server_shutdown())
                                       for p in PlayerDB.get_all_cached_instances()]
            yield [(s.pause(), s.at_server_reload()) for s in ScriptDB.get_all_cached_instances()]
            yield [s.at_server_shutdown() for s in ScriptDB.get_all_cached_instances()]
            yield ObjectDB.objects.clear_all_sessids()
            ServerConfig.objects.conf("server_restart_mode", "reset")

            self.at_server_cold_stop()

        self.at_server_stop()
        # if _reactor_stopping is true, reactor does not need to
        # be stopped again.
        if os.name == 'nt' and os.path.exists(SERVER_PIDFILE):
            # for Windows we need to remove pid files manually
            os.remove(SERVER_PIDFILE)
        if not _reactor_stopping:
            # this will also send a reactor.stop signal, so we set a
            # flag to avoid loops.
            self.shutdown_complete = True
            reactor.callLater(0, reactor.stop)

    # server start/stop hooks

    def at_server_start(self):
        """
        This is called every time the server starts up, regardless of
        how it was shut down.
        """
        if SERVER_STARTSTOP_MODULE:
            SERVER_STARTSTOP_MODULE.at_server_start()


    def at_server_stop(self):
        """
        This is called just before a server is shut down, regardless
        of it is fore a reload, reset or shutdown.
        """
        if SERVER_STARTSTOP_MODULE:
            SERVER_STARTSTOP_MODULE.at_server_stop()


    def at_server_reload_start(self):
        """
        This is called only when server starts back up after a reload.
        """
        if SERVER_STARTSTOP_MODULE:
            SERVER_STARTSTOP_MODULE.at_server_reload_start()


    def at_server_reload_stop(self):
        """
        This is called only time the server stops before a reload.
        """
        if SERVER_STARTSTOP_MODULE:
            SERVER_STARTSTOP_MODULE.at_server_reload_stop()


    def at_server_cold_start(self):
        """
        This is called only when the server starts "cold", i.e. after a
        shutdown or a reset.
        """
        if GUEST_ENABLED:
            for guest in PlayerDB.objects.all().filter(db_typeclass_path=settings.BASE_GUEST_TYPECLASS):
                for character in filter(None, guest.db._playable_characters):
                    character.delete()
                guest.delete()
        if SERVER_STARTSTOP_MODULE:
            SERVER_STARTSTOP_MODULE.at_server_cold_start()

    def at_server_cold_stop(self):
        """
        This is called only when the server goes down due to a shutdown or reset.
        """
        if SERVER_STARTSTOP_MODULE:
            SERVER_STARTSTOP_MODULE.at_server_cold_stop()

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

if AMP_ENABLED:

    # The AMP protocol handles the communication between
    # the portal and the mud server. Only reason to ever deactivate
    # it would be during testing and debugging.

    ifacestr = ""
    if AMP_INTERFACE != '127.0.0.1':
        ifacestr = "-%s" % AMP_INTERFACE
    print '  amp (to Portal)%s: %s' % (ifacestr, AMP_PORT)

    from evennia.server import amp

    factory = amp.AmpServerFactory(EVENNIA)
    amp_service = internet.TCPServer(AMP_PORT, factory, interface=AMP_INTERFACE)
    amp_service.setName("EvenniaPortal")
    EVENNIA.services.addService(amp_service)

if WEBSERVER_ENABLED:

    # Start a django-compatible webserver.

    from twisted.python import threadpool
    from evennia.server.webserver import DjangoWebRoot, WSGIWebServer

    # start a thread pool and define the root url (/) as a wsgi resource
    # recognized by Django
    threads = threadpool.ThreadPool(minthreads=max(1, settings.WEBSERVER_THREADPOOL_LIMITS[0]),
                                    maxthreads=max(1, settings.WEBSERVER_THREADPOOL_LIMITS[1]))
    web_root = DjangoWebRoot(threads)
    # point our media resources to url /media
    web_root.putChild("media", static.File(settings.MEDIA_ROOT))
    # point our static resources to url /static
    web_root.putChild("static", static.File(settings.STATIC_ROOT))
    web_site = server.Site(web_root, logPath=settings.HTTP_LOG_FILE)

    for proxyport, serverport in WEBSERVER_PORTS:
        # create the webserver (we only need the port for this)
        webserver = WSGIWebServer(threads, serverport, web_site, interface='127.0.0.1')
        webserver.setName('EvenniaWebServer%s' % serverport)
        EVENNIA.services.addService(webserver)

        print "  webserver: %s" % serverport

ENABLED = []
if IRC_ENABLED:
    # IRC channel connections
    ENABLED.append('irc')

if IMC2_ENABLED:
    # IMC2 channel connections
    ENABLED.append('imc2')

if RSS_ENABLED:
    # RSS feed channel connections
    ENABLED.append('rss')

if ENABLED:
    print "  " + ", ".join(ENABLED) + " enabled."

for plugin_module in SERVER_SERVICES_PLUGIN_MODULES:
    # external plugin protocols
    plugin_module.start_plugin_services(EVENNIA)

print '-' * 50  # end of terminal output

# clear server startup mode
ServerConfig.objects.conf("server_starting_mode", delete=True)

if os.name == 'nt':
    # Windows only: Set PID file manually
    with open(SERVER_PIDFILE, 'w') as f:
        f.write(str(os.getpid()))

