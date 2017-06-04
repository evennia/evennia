"""
This module implements the main Evennia server process, the core of
the game engine.

This module should be started with the 'twistd' executable since it
sets up all the networking features.  (this is done automatically
by evennia/server/server_runner.py).

"""
from __future__ import print_function
from builtins import object
import time
import sys
import os

from twisted.web import static
from twisted.application import internet, service
from twisted.internet import reactor, defer
from twisted.internet.task import LoopingCall, deferLater

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

SERVER_PIDFILE = ""
if os.name == 'nt':
    # For Windows we need to handle pid files manually.
    SERVER_PIDFILE = os.path.join(settings.GAME_DIR, "server", 'server.pid')

# a file with a flag telling the server to restart after shutdown or not.
SERVER_RESTART = os.path.join(settings.GAME_DIR, "server", 'server.restart')

# module containing hook methods called during start_stop
SERVER_STARTSTOP_MODULE = mod_import(settings.AT_SERVER_STARTSTOP_MODULE)

# modules containing plugin services
SERVER_SERVICES_PLUGIN_MODULES = [mod_import(module) for module in make_iter(settings.SERVER_SERVICES_PLUGIN_MODULES)]
try:
    WEB_PLUGINS_MODULE = mod_import(settings.WEB_PLUGINS_MODULE)
except ImportError:
    WEB_PLUGINS_MODULE = None
    print ("WARNING: settings.WEB_PLUGINS_MODULE not found - "
           "copy 'evennia/game_template/server/conf/web_plugins.py to mygame/server/conf.")

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
        self.services = service.MultiService()
        self.services.setServiceParent(application)
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

        # wrap the SIGINT handler to make sure we empty the threadpool
        # even when we reload and we have long-running requests in queue.
        # this is necessary over using Twisted's signal handler.
        # (see https://github.com/evennia/evennia/issues/1128)
        def _wrap_sigint_handler(*args):
            from twisted.internet.defer import Deferred
            if hasattr(self, "web_root"):
                d = self.web_root.empty_threadpool()
                d.addCallback(lambda _: self.shutdown(_reactor_stopping=True))
            else:
                d = Deferred(lambda _: self.shutdown(_reactor_stopping=True))
            d.addCallback(lambda _: reactor.stop())
            reactor.callLater(1, d.callback, None)
        reactor.sigInt = _wrap_sigint_handler

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
                print(" %s:\n '%s' changed to '%s'. Updating unchanged entries in database ..." % (settings_names[i], prev, curr))
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
            print(' Server started for the first time. Setting defaults.')
            initial_setup.handle_setup(0)
            print('-' * 50)
        elif int(last_initial_setup_step) >= 0:
            # a positive value means the setup crashed on one of its
            # modules and setup will resume from this step, retrying
            # the last failed module. When all are finished, the step
            # is set to -1 to show it does not need to be run again.
            print(' Resuming initial setup from step %(last)s.' % \
                {'last': last_initial_setup_step})
            initial_setup.handle_setup(int(last_initial_setup_step))
            print('-' * 50)

    def run_init_hooks(self):
        """
        Called every server start
        """
        from evennia.objects.models import ObjectDB
        #from evennia.players.models import PlayerDB

        #update eventual changed defaults
        self.update_defaults()

        [o.at_init() for o in ObjectDB.get_all_cached_instances()]
        [p.at_init() for p in PlayerDB.get_all_cached_instances()]

        mode = self.getset_restart_mode()

        # call correct server hook based on start file value
        if mode == 'reload':
            # True was the old reload flag, kept for compatibilty
            self.at_server_reload_start()
        elif mode == 'reset':
            # only run hook, don't purge sessions
            self.at_server_cold_start()
        elif mode in ('reset', 'shutdown'):
            self.at_server_cold_start()
            # clear eventual lingering session storages
            ObjectDB.objects.clear_all_sessids()
        # always call this regardless of start type
        self.at_server_start()

    def getset_restart_mode(self, mode=None):
        """
        This manages the flag file that tells the runner if the server is
        reloading, resetting or shutting down.

        Args:
            mode (string or None, optional): Valid values are
                'reload', 'reset', 'shutdown' and `None`. If mode is `None`,
                no change will be done to the flag file.
        Returns:
            mode (str): The currently active restart mode, either just
                set or previously set.

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
                         at_shutdown hooks called but sessions will not
                         be disconnected.
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

        mode = self.getset_restart_mode(mode)

        from evennia.objects.models import ObjectDB
        #from evennia.players.models import PlayerDB
        from evennia.server.models import ServerConfig
        from evennia.utils import gametime as _GAMETIME_MODULE

        if mode == 'reload':
            # call restart hooks
            ServerConfig.objects.conf("server_restart_mode", "reload")
            yield [o.at_server_reload() for o in ObjectDB.get_all_cached_instances()]
            yield [p.at_server_reload() for p in PlayerDB.get_all_cached_instances()]
            yield [(s.pause(manual_pause=False), s.at_server_reload()) for s in ScriptDB.get_all_cached_instances() if s.is_active]
            yield self.sessions.all_sessions_portal_sync()
            self.at_server_reload_stop()
            # only save monitor state on reload, not on shutdown/reset
            from evennia.scripts.monitorhandler import MONITOR_HANDLER
            MONITOR_HANDLER.save()
        else:
            if mode == 'reset':
                # like shutdown but don't unset the is_connected flag and don't disconnect sessions
                yield [o.at_server_shutdown() for o in ObjectDB.get_all_cached_instances()]
                yield [p.at_server_shutdown() for p in PlayerDB.get_all_cached_instances()]
                if self.amp_protocol:
                    yield self.sessions.all_sessions_portal_sync()
            else:  # shutdown
                yield [_SA(p, "is_connected", False) for p in PlayerDB.get_all_cached_instances()]
                yield [o.at_server_shutdown() for o in ObjectDB.get_all_cached_instances()]
                yield [(p.unpuppet_all(), p.at_server_shutdown())
                                       for p in PlayerDB.get_all_cached_instances()]
                yield ObjectDB.objects.clear_all_sessids()
            yield [(s.pause(manual_pause=False), s.at_server_shutdown()) for s in ScriptDB.get_all_cached_instances()]
            ServerConfig.objects.conf("server_restart_mode", "reset")
            self.at_server_cold_stop()

        # tickerhandler state should always be saved.
        from evennia.scripts.tickerhandler import TICKER_HANDLER
        TICKER_HANDLER.save()

        # always called, also for a reload
        self.at_server_stop()

        if os.name == 'nt' and os.path.exists(SERVER_PIDFILE):
            # for Windows we need to remove pid files manually
            os.remove(SERVER_PIDFILE)

        if hasattr(self, "web_root"): # not set very first start
            yield self.web_root.empty_threadpool()

        if not _reactor_stopping:
            # kill the server
            self.shutdown_complete = True
            reactor.callLater(1, reactor.stop)

        # we make sure the proper gametime is saved as late as possible
        ServerConfig.objects.conf("runtime", _GAMETIME_MODULE.runtime())

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

    def at_post_portal_sync(self):
        """
        This is called just after the portal has finished syncing back data to the server
        after reconnecting.
        """
        # one of reload, reset or shutdown
        mode = self.getset_restart_mode()

        from evennia.scripts.monitorhandler import MONITOR_HANDLER
        MONITOR_HANDLER.restore(mode == 'reload')

        from evennia.scripts.tickerhandler import TICKER_HANDLER
        TICKER_HANDLER.restore(mode == 'reload')

        # after sync is complete we force-validate all scripts
        # (this also starts any that didn't yet start)
        ScriptDB.objects.validate(init_mode=mode)

        # delete the temporary setting
        ServerConfig.objects.conf("server_restart_mode", delete=True)

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
        # We need to do this just in case the server was killed in a way where
        # the normal cleanup operations did not have time to run.
        from evennia.objects.models import ObjectDB
        ObjectDB.objects.clear_all_sessids()

        # Remove non-persistent scripts
        from evennia.scripts.models import ScriptDB
        for script in ScriptDB.objects.filter(db_persistent=False):
            script.stop()

        if GUEST_ENABLED:
            for guest in PlayerDB.objects.all().filter(db_typeclass_path=settings.BASE_GUEST_TYPECLASS):
                for character in guest.db._playable_characters:
                    if character: character.delete()
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

print('-' * 50)
print(' %(servername)s Server (%(version)s) started.' % {'servername': SERVERNAME, 'version': VERSION})

if AMP_ENABLED:

    # The AMP protocol handles the communication between
    # the portal and the mud server. Only reason to ever deactivate
    # it would be during testing and debugging.

    ifacestr = ""
    if AMP_INTERFACE != '127.0.0.1':
        ifacestr = "-%s" % AMP_INTERFACE
    print('  amp (to Portal)%s: %s' % (ifacestr, AMP_PORT))

    from evennia.server import amp

    factory = amp.AmpServerFactory(EVENNIA)
    amp_service = internet.TCPServer(AMP_PORT, factory, interface=AMP_INTERFACE)
    amp_service.setName("EvenniaPortal")
    EVENNIA.services.addService(amp_service)

if WEBSERVER_ENABLED:

    # Start a django-compatible webserver.

    #from twisted.python import threadpool
    from evennia.server.webserver import DjangoWebRoot, WSGIWebServer, Website, LockableThreadPool

    # start a thread pool and define the root url (/) as a wsgi resource
    # recognized by Django
    threads = LockableThreadPool(minthreads=max(1, settings.WEBSERVER_THREADPOOL_LIMITS[0]),
                                    maxthreads=max(1, settings.WEBSERVER_THREADPOOL_LIMITS[1]))

    web_root = DjangoWebRoot(threads)
    # point our media resources to url /media
    web_root.putChild("media", static.File(settings.MEDIA_ROOT))
    # point our static resources to url /static
    web_root.putChild("static", static.File(settings.STATIC_ROOT))
    EVENNIA.web_root = web_root

    if WEB_PLUGINS_MODULE:
        # custom overloads
        web_root = WEB_PLUGINS_MODULE.at_webserver_root_creation(web_root)

    web_site = Website(web_root, logPath=settings.HTTP_LOG_FILE)

    for proxyport, serverport in WEBSERVER_PORTS:
        # create the webserver (we only need the port for this)
        webserver = WSGIWebServer(threads, serverport, web_site, interface='127.0.0.1')
        webserver.setName('EvenniaWebServer%s' % serverport)
        EVENNIA.services.addService(webserver)

        print("  webserver: %s" % serverport)

ENABLED = []
if IRC_ENABLED:
    # IRC channel connections
    ENABLED.append('irc')

if RSS_ENABLED:
    # RSS feed channel connections
    ENABLED.append('rss')

if ENABLED:
    print("  " + ", ".join(ENABLED) + " enabled.")

for plugin_module in SERVER_SERVICES_PLUGIN_MODULES:
    # external plugin protocols
    plugin_module.start_plugin_services(EVENNIA)

print('-' * 50)  # end of terminal output

# clear server startup mode
ServerConfig.objects.conf("server_starting_mode", delete=True)

if os.name == 'nt':
    # Windows only: Set PID file manually
    with open(SERVER_PIDFILE, 'w') as f:
        f.write(str(os.getpid()))

