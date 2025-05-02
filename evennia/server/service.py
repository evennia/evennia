"""
This module contains the main EvenniaService class, which is the very core of the
Evennia server. It is instantiated by the evennia/server/server.py module.
"""

import importlib
import time
import traceback

import django
from django.conf import settings
from django.db import connection
from django.db.utils import OperationalError
from django.utils.translation import gettext as _
from twisted.application import internet
from twisted.application.service import MultiService
from twisted.internet import defer, reactor
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall

import evennia
from evennia.utils import logger
from evennia.utils.utils import get_evennia_version, make_iter, mod_import

_SA = object.__setattr__


class EvenniaServerService(MultiService):
    def _wrap_sigint_handler(self, *args):
        if hasattr(self, "web_root"):
            d = self.web_root.empty_threadpool()
            d.addCallback(lambda _: self.shutdown("reload", _reactor_stopping=True))
        else:
            d = Deferred(lambda _: self.shutdown("reload", _reactor_stopping=True))
        d.addCallback(lambda _: reactor.stop())
        reactor.callLater(1, d.callback, None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maintenance_count = 0
        self.amp_protocol = None  # set by amp factory
        self.amp_service = None
        self.info_dict = {
            "servername": settings.SERVERNAME,
            "version": get_evennia_version(),
            "amp": "",
            "errors": "",
            "info": "",
            "webserver": "",
            "irc_rss": "",
        }
        self._flush_cache = None
        self._last_server_time_snapshot = 0
        self.maintenance_task = None

        # Database-specific startup optimizations.
        self.sqlite3_prep()

        self.start_time = 0

        # wrap the SIGINT handler to make sure we empty the threadpool
        # even when we reload and we have long-running requests in queue.
        # this is necessary over using Twisted's signal handler.
        # (see https://github.com/evennia/evennia/issues/1128)

        reactor.sigInt = self._wrap_sigint_handler

        self.start_stop_modules = [
            mod_import(mod)
            for mod in make_iter(settings.AT_SERVER_STARTSTOP_MODULE)
            if isinstance(mod, str)
        ]

    def server_maintenance(self):
        """
        This maintenance function handles repeated checks and updates that
        the server needs to do. It is called every minute.
        """
        if not self._flush_cache:
            from evennia.utils.idmapper.models import conditional_flush as _FLUSH_CACHE

            self._flush_cache = _FLUSH_CACHE

        self.maintenance_count += 1

        now = time.time()
        if self.maintenance_count == 1:
            # first call after a reload
            evennia.gametime.SERVER_START_TIME = now
            evennia.gametime.SERVER_RUNTIME = evennia.ServerConfig.objects.conf(
                "runtime", default=0.0
            )
            _LAST_SERVER_TIME_SNAPSHOT = now
        else:
            # adjust the runtime not with 60s but with the actual elapsed time
            # in case this may varies slightly from 60s.
            evennia.gametime.SERVER_RUNTIME += now - self._last_server_time_snapshot
        self._last_server_time_snapshot = now

        # update game time and save it across reloads
        evennia.gametime.SERVER_RUNTIME_LAST_UPDATED = now
        evennia.ServerConfig.objects.conf("runtime", evennia.gametime.SERVER_RUNTIME)

        if self.maintenance_count % 5 == 0:
            # check cache size every 5 minutes
            self._flush_cache(settings.IDMAPPER_CACHE_MAXSIZE)
        if self.maintenance_count % (60 * 7) == 0:
            # drop database connection every 7 hrs to avoid default timeouts on MySQL
            # (see https://github.com/evennia/evennia/issues/1376)
            connection.close()

        self.process_idle_timeouts()

        # run unpuppet hooks for objects that are marked as being puppeted,
        # but which lacks an account (indicates a broken unpuppet operation
        # such as a server crash)
        if self.maintenance_count > 1:
            unpuppet_count = 0
            for obj in evennia.ObjectDB.objects.get_by_tag(key="puppeted", category="account"):
                if not obj.has_account:
                    obj.at_pre_unpuppet()
                    obj.at_post_unpuppet(None, reason=_(" (connection lost)"))
                    obj.tags.remove("puppeted", category="account")
                    unpuppet_count += 1
            if unpuppet_count:
                logger.log_msg(f"Ran unpuppet-hooks for {unpuppet_count} link-dead puppets.")

    def process_idle_timeouts(self):
        # handle idle timeouts
        if settings.IDLE_TIMEOUT > 0:
            now = time.time()
            reason = _("idle timeout exceeded")
            to_disconnect = []
            for session in (
                sess
                for sess in evennia.SESSION_HANDLER.values()
                if (now - sess.cmd_last) > settings.IDLE_TIMEOUT
            ):
                if not session.account or not session.account.access(
                    session.account, "noidletimeout", default=False
                ):
                    to_disconnect.append(session)

            for session in to_disconnect:
                evennia.SESSION_HANDLER.disconnect(session, reason=reason)

    # Server startup methods
    def privilegedStartService(self):
        self.start_time = time.time()

        # Tell the system the server is starting up; some things are not available yet
        try:
            evennia.ServerConfig.objects.conf("server_starting_mode", True)
        except OperationalError:
            print("Server server_starting_mode couldn't be set - database not set up.")

        self.register_amp()

        if settings.WEBSERVER_ENABLED:
            self.register_webserver()

        ENABLED = []
        if settings.IRC_ENABLED:
            # IRC channel connections
            ENABLED.append("irc")

        if settings.RSS_ENABLED:
            # RSS feed channel connections
            ENABLED.append("rss")

        if settings.GRAPEVINE_ENABLED:
            # Grapevine channel connections
            ENABLED.append("grapevine")

        if settings.GAME_INDEX_ENABLED:
            from evennia.server.game_index_client.service import EvenniaGameIndexService

            egi_service = EvenniaGameIndexService()
            egi_service.setServiceParent(self)

        if ENABLED:
            self.info_dict["irc_rss"] = ", ".join(ENABLED) + " enabled."

        self.register_plugins()

        super().privilegedStartService()

        # clear server startup mode
        try:
            evennia.ServerConfig.objects.conf("server_starting_mode", delete=True)
        except OperationalError:
            print("Server server_starting_mode couldn't unset - db not set up.")

    def register_plugins(self):
        SERVER_SERVICES_PLUGIN_MODULES = make_iter(settings.SERVER_SERVICES_PLUGIN_MODULES)
        for plugin_module in SERVER_SERVICES_PLUGIN_MODULES:
            # external plugin protocols - load here
            plugin_module = mod_import(plugin_module)
            if plugin_module:
                plugin_module.start_plugin_services(self)
            else:
                print(f"Could not load plugin module {plugin_module}")

    def register_amp(self):
        # The AMP protocol handles the communication between
        # the portal and the mud server. Only reason to ever deactivate
        # it would be during testing and debugging.

        ifacestr = ""
        if settings.AMP_INTERFACE != "127.0.0.1":
            ifacestr = "-%s" % settings.AMP_INTERFACE

        self.info_dict["amp"] = "amp %s: %s" % (ifacestr, settings.AMP_PORT)

        from evennia.server import amp_client

        factory = amp_client.AMPClientFactory(self)
        self.amp_service = internet.TCPClient(settings.AMP_HOST, settings.AMP_PORT, factory)
        self.amp_service.setName("ServerAMPClient")
        self.amp_service.setServiceParent(self)

    def register_webserver(self):
        # Start a django-compatible webserver.

        from evennia.server.webserver import (
            DjangoWebRoot,
            LockableThreadPool,
            PrivateStaticRoot,
            Website,
            WSGIWebServer,
        )

        # start a thread pool and define the root url (/) as a wsgi resource
        # recognized by Django
        threads = LockableThreadPool(
            minthreads=max(1, settings.WEBSERVER_THREADPOOL_LIMITS[0]),
            maxthreads=max(1, settings.WEBSERVER_THREADPOOL_LIMITS[1]),
        )

        web_root = DjangoWebRoot(threads)
        # point our media resources to url /media
        web_root.putChild(b"media", PrivateStaticRoot(settings.MEDIA_ROOT))
        # point our static resources to url /static
        web_root.putChild(b"static", PrivateStaticRoot(settings.STATIC_ROOT))
        self.web_root = web_root

        try:
            WEB_PLUGINS_MODULE = mod_import(settings.WEB_PLUGINS_MODULE)
        except ImportError:
            WEB_PLUGINS_MODULE = None
            self.info_dict["errors"] = (
                "WARNING: settings.WEB_PLUGINS_MODULE not found - "
                "copy 'evennia/game_template/server/conf/web_plugins.py to mygame/server/conf."
            )

        if WEB_PLUGINS_MODULE:
            # custom overloads
            web_root = WEB_PLUGINS_MODULE.at_webserver_root_creation(web_root)

        web_site = Website(web_root, logPath=settings.HTTP_LOG_FILE)
        web_site.is_portal = False

        self.info_dict["webserver"] = ""
        for proxyport, serverport in settings.WEBSERVER_PORTS:
            # create the webserver (we only need the port for this)
            webserver = WSGIWebServer(threads, serverport, web_site, interface="127.0.0.1")
            webserver.setName("EvenniaWebServer%s" % serverport)
            webserver.setServiceParent(self)

            self.info_dict["webserver"] += "webserver: %s" % serverport

    def sqlite3_prep(self):
        """
        Optimize some SQLite stuff at startup since we
        can't save it to the database.
        """
        if (
            ".".join(str(i) for i in django.VERSION) < "1.2"
            and settings.DATABASES.get("default", {}).get("ENGINE") == "sqlite3"
        ) or (
            hasattr(settings, "DATABASES")
            and settings.DATABASES.get("default", {}).get("ENGINE", None)
            == "django.db.backends.sqlite3"
        ):
            # sqlite3 database pragmas (directives)
            cursor = connection.cursor()
            for pragma in settings.SQLITE3_PRAGMAS:
                cursor.execute(pragma)

    def update_defaults(self):
        """
        We make sure to store the most important object defaults here, so
        we can catch if they change and update them on-objects automatically.
        This allows for changing default cmdset locations and default
        typeclasses in the settings file and have them auto-update all
        already existing objects.

        """

        # setting names
        settings_names = (
            "CMDSET_CHARACTER",
            "CMDSET_ACCOUNT",
            "BASE_ACCOUNT_TYPECLASS",
            "BASE_OBJECT_TYPECLASS",
            "BASE_CHARACTER_TYPECLASS",
            "BASE_ROOM_TYPECLASS",
            "BASE_EXIT_TYPECLASS",
            "BASE_SCRIPT_TYPECLASS",
            "BASE_CHANNEL_TYPECLASS",
        )
        # get previous and current settings so they can be compared
        settings_compare = list(
            zip(
                [evennia.ServerConfig.objects.conf(name) for name in settings_names],
                [settings.__getattr__(name) for name in settings_names],
            )
        )
        mismatches = [
            i for i, tup in enumerate(settings_compare) if tup[0] and tup[1] and tup[0] != tup[1]
        ]
        if len(
            mismatches
        ):  # can't use any() since mismatches may be [0] which reads as False for any()
            # we have a changed default. Import relevant objects and
            # run the update

            # from evennia.accounts.models import AccountDB
            for i, prev, curr in (
                (i, tup[0], tup[1]) for i, tup in enumerate(settings_compare) if i in mismatches
            ):
                # update the database
                self.info_dict["info"] = (
                    " %s:\n '%s' changed to '%s'. Updating unchanged entries in database ..."
                    % (
                        settings_names[i],
                        prev,
                        curr,
                    )
                )
                if i == 0:
                    evennia.ObjectDB.objects.filter(db_cmdset_storage__exact=prev).update(
                        db_cmdset_storage=curr
                    )
                if i == 1:
                    evennia.AccountDB.objects.filter(db_cmdset_storage__exact=prev).update(
                        db_cmdset_storage=curr
                    )
                if i == 2:
                    evennia.AccountDB.objects.filter(db_typeclass_path__exact=prev).update(
                        db_typeclass_path=curr
                    )
                if i in (3, 4, 5, 6):
                    evennia.ObjectDB.objects.filter(db_typeclass_path__exact=prev).update(
                        db_typeclass_path=curr
                    )
                if i == 7:
                    evennia.ScriptDB.objects.filter(db_typeclass_path__exact=prev).update(
                        db_typeclass_path=curr
                    )
                if i == 8:
                    evennia.ChannelDB.objects.filter(db_typeclass_path__exact=prev).update(
                        db_typeclass_path=curr
                    )
                # store the new default and clean caches
                evennia.ServerConfig.objects.conf(settings_names[i], curr)
                evennia.ObjectDB.flush_instance_cache()
                evennia.AccountDB.flush_instance_cache()
                evennia.ScriptDB.flush_instance_cache()
                evennia.ChannelDB.flush_instance_cache()
        # if this is the first start we might not have a "previous"
        # setup saved. Store it now.
        [
            evennia.ServerConfig.objects.conf(settings_names[i], tup[1])
            for i, tup in enumerate(settings_compare)
            if not tup[0]
        ]

    def run_initial_setup(self):
        """
        This is triggered by the amp protocol when the connection
        to the portal has been established.
        This attempts to run the initial_setup script of the server.
        It returns if this is not the first time the server starts.
        Once finished the last_initial_setup_step is set to 'done'

        """

        initial_setup = importlib.import_module(settings.INITIAL_SETUP_MODULE)
        last_initial_setup_step = evennia.ServerConfig.objects.conf("last_initial_setup_step")
        try:
            if not last_initial_setup_step:
                # None is only returned if the config does not exist,
                # i.e. this is an empty DB that needs populating.
                self.info_dict["info"] = " Server started for the first time. Setting defaults."
                initial_setup.handle_setup()
            elif last_initial_setup_step not in ("done", -1):
                # last step crashed, so we weill resume from this step.
                # modules and setup will resume from this step, retrying
                # the last failed module. When all are finished, the step
                # is set to 'done' to show it does not need to be run again.
                self.info_dict["info"] = " Resuming initial setup from step '{last}'.".format(
                    last=last_initial_setup_step
                )
                initial_setup.handle_setup(last_initial_setup_step)
        except Exception:
            # stop server if this happens.
            print(traceback.format_exc())
            if not settings.TEST_ENVIRONMENT or not evennia.SESSION_HANDLER:
                print("Error in initial setup. Stopping Server + Portal.")
                evennia.SESSION_HANDLER.portal_shutdown()

    def create_default_channels(self):
        """
        check so default channels exist on every restart, create if not.

        """

        from evennia import AccountDB, ChannelDB
        from evennia.utils.create import create_channel

        superuser = AccountDB.objects.get(id=1)

        # mudinfo
        mudinfo_chan = settings.CHANNEL_MUDINFO
        if mudinfo_chan and not ChannelDB.objects.filter(db_key__iexact=mudinfo_chan["key"]):
            channel = create_channel(**mudinfo_chan)
            channel.connect(superuser)
        # connectinfo
        connectinfo_chan = settings.CHANNEL_CONNECTINFO
        if connectinfo_chan and not ChannelDB.objects.filter(
            db_key__iexact=connectinfo_chan["key"]
        ):
            channel = create_channel(**connectinfo_chan)
        # default channels
        for chan_info in settings.DEFAULT_CHANNELS:
            if not ChannelDB.objects.filter(db_key__iexact=chan_info["key"]):
                channel = create_channel(**chan_info)
                channel.connect(superuser)

    def run_init_hooks(self, mode):
        """
        Called by the amp client once receiving sync back from Portal

        Args:
            mode (str): One of shutdown, reload or reset

        """
        from evennia.typeclasses.models import TypedObject

        # start server time and maintenance task
        self.maintenance_task = LoopingCall(self.server_maintenance)
        self.maintenance_task.start(60, now=True)  # call every minute

        # update eventual changed defaults
        self.update_defaults()

        # run at_init() on all cached entities on reconnect
        [
            [entity.at_init() for entity in typeclass_db.get_all_cached_instances()]
            for typeclass_db in TypedObject.__subclasses__()
        ]

        self.at_server_init()

        # call correct server hook based on start file value
        if mode == "reload":
            logger.log_msg("Server successfully reloaded.")
            self.at_server_reload_start()
        elif mode == "reset":
            # only run hook, don't purge sessions
            self.at_server_cold_start()
            logger.log_msg("Evennia Server successfully restarted in 'reset' mode.")
        elif mode == "shutdown":
            from evennia.objects.models import ObjectDB

            self.at_server_cold_start()
            # clear eventual lingering session storages
            ObjectDB.objects.clear_all_sessids()
            logger.log_msg("Evennia Server successfully started.")

        # always call this regardless of start type
        self.at_server_start()

        # initialize and start global scripts
        evennia.GLOBAL_SCRIPTS.start()

    @defer.inlineCallbacks
    def shutdown(self, mode="reload", _reactor_stopping=False):
        """
        Shuts down the server from inside it.

        mode - sets the server restart mode.
           - 'reload' - server restarts, no "persistent" scripts
             are stopped, at_reload hooks called.
           - 'reset' - server restarts, non-persistent scripts stopped,
             at_shutdown hooks called but sessions will not
             be disconnected.
           - 'shutdown' - like reset, but server will not auto-restart.
        _reactor_stopping - this is set if server is stopped by a kill
           command OR this method was already called
           once - in both cases the reactor is
           dead/stopping already.
        """
        if _reactor_stopping and hasattr(self, "shutdown_complete"):
            # this means we have already passed through this method
            # once; we don't need to run the shutdown procedure again.
            defer.returnValue(None)

        if mode == "reload":
            # call restart hooks
            evennia.ServerConfig.objects.conf("server_restart_mode", "reload")
            yield [o.at_server_reload() for o in evennia.ObjectDB.get_all_cached_instances()]
            yield [p.at_server_reload() for p in evennia.AccountDB.get_all_cached_instances()]
            yield [
                (s._pause_task(auto_pause=True) if s.is_active else None, s.at_server_reload())
                for s in evennia.ScriptDB.get_all_cached_instances()
                if s.id
            ]
            yield evennia.SESSION_HANDLER.all_sessions_portal_sync()
            self.at_server_reload_stop()
            # only save monitor state on reload, not on shutdown/reset
            from evennia.scripts.monitorhandler import MONITOR_HANDLER

            MONITOR_HANDLER.save()
        else:
            if mode == "reset":
                # like shutdown but don't unset the is_connected flag and don't disconnect sessions
                yield [o.at_server_shutdown() for o in evennia.ObjectDB.get_all_cached_instances()]
                yield [p.at_server_shutdown() for p in evennia.AccountDB.get_all_cached_instances()]
                if self.amp_protocol:
                    yield evennia.SESSION_HANDLER.all_sessions_portal_sync()
            else:  # shutdown
                yield [
                    _SA(p, "is_connected", False)
                    for p in evennia.AccountDB.get_all_cached_instances()
                ]
                yield [o.at_server_shutdown() for o in evennia.ObjectDB.get_all_cached_instances()]
                yield [
                    (p.unpuppet_all(), p.at_server_shutdown())
                    for p in evennia.AccountDB.get_all_cached_instances()
                ]
                yield evennia.ObjectDB.objects.clear_all_sessids()
            yield [
                (s._pause_task(auto_pause=True), s.at_server_shutdown())
                for s in evennia.ScriptDB.get_all_cached_instances()
                if s.id and s.is_active
            ]
            evennia.ServerConfig.objects.conf("server_restart_mode", "reset")
            self.at_server_cold_stop()

        # tickerhandler state should always be saved.
        from evennia.scripts.tickerhandler import TICKER_HANDLER

        TICKER_HANDLER.save()

        # on-demand handler state should always be saved.
        from evennia.scripts.ondemandhandler import ON_DEMAND_HANDLER

        ON_DEMAND_HANDLER.save()

        # always called, also for a reload
        self.at_server_stop()

        if hasattr(self, "web_root"):  # not set very first start
            yield self.web_root.empty_threadpool()

        if not _reactor_stopping:
            # kill the server
            self.shutdown_complete = True
            reactor.callLater(1, reactor.stop)

        # we make sure the proper gametime is saved as late as possible
        evennia.ServerConfig.objects.conf("runtime", evennia.gametime.runtime())

    def get_info_dict(self):
        """
        Return the server info, for display.

        """
        return self.info_dict

    # server start/stop hooks

    def _call_start_stop(self, hookname):
        """
        Helper method for calling hooks on all modules.

        Args:
            hookname (str): Name of hook to call.

        """
        for mod in self.start_stop_modules:
            if hook := getattr(mod, hookname, None):
                hook()

    def at_server_init(self):
        """
        This is called first when the server is starting, before any other hooks, regardless of how it's starting.
        """
        self._call_start_stop("at_server_init")

    def at_server_start(self):
        """
        This is called every time the server starts up, regardless of
        how it was shut down.

        """
        self._call_start_stop("at_server_start")

    def at_server_stop(self):
        """
        This is called just before a server is shut down, regardless
        of it is fore a reload, reset or shutdown.

        """
        self._call_start_stop("at_server_stop")

    def at_server_reload_start(self):
        """
        This is called only when server starts back up after a reload.

        """
        self._call_start_stop("at_server_reload_start")

    def at_post_portal_sync(self, mode):
        """
        This is called just after the portal has finished syncing back data to the server
        after reconnecting.

        Args:
            mode (str): One of 'reload', 'reset' or 'shutdown'.

        """

        from evennia.scripts.monitorhandler import MONITOR_HANDLER

        MONITOR_HANDLER.restore(mode == "reload")

        from evennia.scripts.tickerhandler import TICKER_HANDLER

        TICKER_HANDLER.restore(mode == "reload")

        # Un-pause all scripts, stop non-persistent timers
        evennia.ScriptDB.objects.update_scripts_after_server_start()

        # start the task handler
        from evennia.scripts.taskhandler import TASK_HANDLER

        TASK_HANDLER.load()
        TASK_HANDLER.create_delays()

        # start the On-demand handler
        from evennia.scripts.ondemandhandler import ON_DEMAND_HANDLER

        ON_DEMAND_HANDLER.load()

        # create/update channels
        self.create_default_channels()

        # delete the temporary setting
        evennia.ServerConfig.objects.conf("server_restart_mode", delete=True)

    def at_server_reload_stop(self):
        """
        This is called only time the server stops before a reload.

        """
        self._call_start_stop("at_server_reload_stop")

    def at_server_cold_start(self):
        """
        This is called only when the server starts "cold", i.e. after a
        shutdown or a reset.

        """
        # Remove non-persistent scripts
        from evennia.scripts.models import ScriptDB

        for script in ScriptDB.objects.filter(db_persistent=False):
            script._stop_task()

        if settings.GUEST_ENABLED:
            for guest in evennia.AccountDB.objects.all().filter(
                db_typeclass_path=settings.BASE_GUEST_TYPECLASS
            ):
                for character in guest.db._playable_characters:
                    if character:
                        character.delete()
                guest.delete()
        self._call_start_stop("at_server_cold_start")

    def at_server_cold_stop(self):
        """
        This is called only when the server goes down due to a shutdown or reset.

        """
        self._call_start_stop("at_server_cold_stop")
