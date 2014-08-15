"""
This module contains the base Script class that all
scripts are inheriting from.

It also defines a few common scripts.
"""

from twisted.internet.defer import Deferred, maybeDeferred
from twisted.internet.task import LoopingCall
from django.conf import settings
from django.utils.translation import ugettext as _
from src.typeclasses.typeclass import TypeClass
from src.scripts.models import ScriptDB
from src.comms import channelhandler
from src.utils import logger

__all__ = ["Script", "DoNothing", "CheckSessions",
           "ValidateScripts", "ValidateChannelHandler"]

_GA = object.__getattribute__
_SESSIONS = None

class ExtendedLoopingCall(LoopingCall):
    """
    LoopingCall that can start at a delay different
    than self.interval.
    """
    start_delay = None
    callcount = 0

    def start(self, interval, now=True, start_delay=None, count_start=0):
        """
        Start running function every interval seconds.

        This overloads the LoopingCall default by offering
        the start_delay keyword and ability to repeat.

        start_delay: The number of seconds before starting.
                     If None, wait interval seconds. Only
                     valid is now is False.
        repeat_start: the task will track how many times it has run.
                      this will change where it starts counting from.
                      Note that as opposed to Twisted's inbuild
                      counter, this will count also if force_repeat()
                      was called (so it will not just count the number
                      of interval seconds since start).
        """
        assert not self.running, ("Tried to start an already running "
                                  "ExtendedLoopingCall.")
        if interval < 0:
            raise ValueError, "interval must be >= 0"

        self.running = True
        d = self.deferred = Deferred()
        self.starttime = self.clock.seconds()
        self._expectNextCallAt = self.starttime
        self.interval = interval
        self._runAtStart = now
        self.callcount = max(0, count_start)

        if now:
            self()
        else:
            if start_delay is not None and start_delay >= 0:
                # we set start_delay after the _reshedule call to make
                # next_call_time() find it until next reshedule.
                self.interval = start_delay
                self._reschedule()
                self.interval = interval
                self.start_delay = start_delay
            else:
                self._reschedule()
        return d

    def __call__(self):
        "tick one step"
        self.callcount += 1
        super(ExtendedLoopingCall, self).__call__()

    def _reschedule(self):
        """
        Handle call rescheduling including
        nulling start_delay and stopping if
        number of repeats is reached.
        """
        self.start_delay = None
        super(ExtendedLoopingCall, self)._reschedule()

    def force_repeat(self):
        "Force-fire the callback"
        assert self.running, ("Tried to fire an ExtendedLoopingCall "
                              "that was not running.")
        if self.call is not None:
            self.call.cancel()
            self._expectNextCallAt = self.clock.seconds()
            self()

    def next_call_time(self):
        """
        Return the time in seconds until the next call. This takes
        start_delay into account.
        """
        if self.running:
            currentTime = self.clock.seconds()
            return self._expectNextCallAt - currentTime
        return None

#
# Base script, inherit from Script below instead.
#
class ScriptBase(TypeClass):
    """
    Base class for scripts. Don't inherit from this, inherit
    from the class 'Script'  instead.
    """
    # private methods

    def __eq__(self, other):
        """
        This has to be located at this level, having it in the
        parent doesn't work.
        """
        try:
            return other.dbid == self.dbid
        except Exception:
            return False

    def _start_task(self):
        "start task runner"

        self.ndb._task = ExtendedLoopingCall(self._step_task)

        if self.db._paused_time:
            # the script was paused; restarting
            callcount = self.db._paused_callcount or 0
            self.ndb._task.start(self.dbobj.db_interval,
                                 now=False,
                                 start_delay=self.db._paused_time,
                                 count_start=callcount)
            del self.db._paused_time
            del self.db._paused_repeats
        else:
            # starting script anew
            self.ndb._task.start(self.dbobj.db_interval,
                                 now=not self.dbobj.db_start_delay)

    def _stop_task(self):
        "stop task runner"
        task = self.ndb._task
        if task and task.running:
            task.stop()

    def _step_errback(self, e):
        "callback for runner errors"
        cname = self.__class__.__name__
        estring = _("Script %(key)s(#%(dbid)s) of type '%(cname)s': at_repeat() error '%(err)s'.") % \
                          {"key": self.key, "dbid": self.dbid, "cname": cname,
                           "err": e.getErrorMessage()}
        try:
            self.dbobj.db_obj.msg(estring)
        except Exception:
            pass
        logger.log_errmsg(estring)

    def _step_callback(self):
        "step task runner. No try..except needed due to defer wrap."

        if not self.is_valid():
            self.stop()
            return

        # call hook
        self.at_repeat()

        # check repeats
        callcount = self.ndb._task.callcount
        maxcount = self.dbobj.db_repeats
        if maxcount > 0 and maxcount <= callcount:
            #print "stopping script!"
            self.stop()

    def _step_task(self):
        "Step task. This groups error handling."
        try:
            return maybeDeferred(self._step_callback).addErrback(self._step_errback)
        except Exception:
            logger.log_trace()

    # Public methods

    def time_until_next_repeat(self):
        """
        Returns the time in seconds until the script will be
        run again. If this is not a stepping script, returns None.
        This is not used in any way by the script's stepping
        system; it's only here for the user to be able to
        check in on their scripts and when they will next be run.
        """
        task = self.ndb._task
        if task:
            try:
                return int(round(task.next_call_time()))
            except TypeError:
                pass
        return None

    def remaining_repeats(self):
        "Get the number of returning repeats. Returns None if unlimited repeats."
        task = self.ndb._task
        if task:
            return max(0, self.dbobj.db_repeats - task.callcount)

    def start(self, force_restart=False):
        """
        Called every time the script is started (for
        persistent scripts, this is usually once every server start)

        force_restart - if True, will always restart the script, regardless
                        of if it has started before.

        returns 0 or 1 to indicated the script has been started or not.
                Used in counting.
        """

        #print "Script %s (%s) start (active:%s, force:%s) ..." % (self.key, id(self.dbobj),
        #                                                         self.is_active, force_restart)

        if self.dbobj.is_active and not force_restart:
            # script already runs and should not be restarted.
            return 0

        obj = self.obj
        if obj:
            # check so the scripted object is valid and initalized
            try:
                _GA(obj.dbobj, 'cmdset')
            except AttributeError:
                # this means the object is not initialized.
                logger.log_trace()
                self.dbobj.is_active = False
                return 0

        # try to restart a paused script
        if self.unpause():
            return 1

        # start the script from scratch
        self.dbobj.is_active = True
        try:
            self.at_start()
        except Exception:
            logger.log_trace()

        if self.dbobj.db_interval > 0:
            self._start_task()
        return 1

    def stop(self, kill=False):
        """
        Called to stop the script from running.
        This also deletes the script.

        kill - don't call finishing hooks.
        """
        #print "stopping script %s" % self.key
        #import pdb
        #pdb.set_trace()
        if not kill:
            try:
                self.at_stop()
            except Exception:
                logger.log_trace()
        self._stop_task()
        try:
            self.dbobj.delete()
        except AssertionError:
            logger.log_trace()
            return 0
        return 1

    def pause(self):
        """
        This stops a running script and stores its active state.
        It WILL NOT call that at_stop() hook.
        """
        if not self.db._paused_time:
            # only allow pause if not already paused
            task = self.ndb._task
            if task:
                self.db._paused_time = task.next_call_time()
                self.db._paused_callcount = task.callcount
                self._stop_task()
            self.dbobj.is_active = False

    def unpause(self):
        """
        Restart a paused script. This WILL call the at_start() hook.
        """
        if self.db._paused_time:
            # only unpause if previously paused
            self.dbobj.is_active = True

            try:
                self.at_start()
            except Exception:
                logger.log_trace()

            self._start_task()
            return True

    def force_repeat(self):
        """
        Fire a premature triggering of the script callback. This
        will reset the timer and count down repeats as if the script
        had fired normally.
        """
        task = self.ndb._task
        if task:
            task.force_repeat()

    # hooks
    def at_script_creation(self):
        "placeholder"
        pass

    def is_valid(self):
        "placeholder"
        pass

    def at_start(self):
        "placeholder."
        pass

    def at_stop(self):
        "placeholder"
        pass

    def at_repeat(self):
        "placeholder"
        pass

    def at_init(self):
        "called when typeclass re-caches. Usually not used for scripts."
        pass


#
# Base Script - inherit from this
#

class Script(ScriptBase):
    """
    This is the class you should inherit from, it implements
    the hooks called by the script machinery.
    """

    def __init__(self, dbobj):
        """
        This is the base TypeClass for all Scripts. Scripts describe events,
        timers and states in game, they can have a time component or describe
        a state that changes under certain conditions.

        Script API:

        * Available properties (only available on initiated Typeclass objects)

         key (string) - name of object
         name (string)- same as key
         aliases (list of strings) - aliases to the object. Will be saved to
         database as AliasDB entries but returned as strings.
         dbref (int, read-only) - unique #id-number. Also "id" can be used.
         dbobj (Object, read-only) - link to database model. dbobj.typeclass
               points back to this class
         typeclass (Object, read-only) - this links back to this class as an
                 identified only. Use self.swap_typeclass() to switch.
         date_created (string) - time stamp of object creation
         permissions (list of strings) - list of permission strings

         desc (string)      - optional description of script, shown in listings
         obj (Object)       - optional object that this script is connected to
                              and acts on (set automatically
                              by obj.scripts.add())
         interval (int)     - how often script should run, in seconds.
                              <=0 turns off ticker
         start_delay (bool) - if the script should start repeating right
                              away or wait self.interval seconds
         repeats (int)      - how many times the script should repeat before
                              stopping. <=0 means infinite repeats
         persistent (bool)  - if script should survive a server shutdown or not
         is_active (bool)   - if script is currently running

        * Handlers

         locks - lock-handler: use locks.add() to add new lock strings
         db - attribute-handler: store/retrieve database attributes on this
              self.db.myattr=val, val=self.db.myattr
         ndb - non-persistent attribute handler: same as db but does not
               create a database entry when storing data

        * Helper methods

         start() - start script (this usually happens automatically at creation
                   and obj.script.add() etc)
         stop()  - stop script, and delete it
         pause() - put the script on hold, until unpause() is called. If script
                   is persistent, the pause state will survive a shutdown.
         unpause() - restart a previously paused script. The script will
                     continue as if it was never paused.
         force_repeat() - force-step the script, regardless of how much remains
                    until next step. This counts like a normal firing in all ways.
         time_until_next_repeat() - if a timed script (interval>0), returns
                    time until next tick
         remaining_repeats() - number of repeats remaining, if limited

        * Hook methods

         at_script_creation() - called only once, when an object of this
                                class is first created.
         is_valid() - is called to check if the script is valid to be running
                      at the current time. If is_valid() returns False, the
                      running script is stopped and removed from the game. You
                      can use this to check state changes (i.e. an script
                      tracking some combat stats at regular intervals is only
                      valid to run while there is actual combat going on).
          at_start() - Called every time the script is started, which for
                      persistent scripts is at least once every server start.
                      Note that this is unaffected by self.delay_start, which
                      only delays the first call to at_repeat(). It will also
                      be called after a pause, to allow for setting up the script.
          at_repeat() - Called every self.interval seconds. It will be called
                      immediately upon launch unless self.delay_start is True,
                      which will delay the first call of this method by
                      self.interval seconds. If self.interval<=0, this method
                      will never be called.
          at_stop() - Called as the script object is stopped and is about to
                      be removed from the game, e.g. because is_valid()
                      returned False or self.stop() was called manually.
          at_server_reload() - Called when server reloads. Can be used to save
                      temporary variables you want should survive a reload.
          at_server_shutdown() - called at a full server shutdown.


          """
        super(Script, self).__init__(dbobj)

    def at_script_creation(self):
        """
        Only called once, by the create function.
        """
        self.key = "<unnamed>"
        self.desc = ""
        self.interval = 0  # infinite
        self.start_delay = False
        self.repeats = 0  # infinite
        self.persistent = False

    def is_valid(self):
        """
        Is called to check if the script is valid to run at this time.
        Should return a boolean. The method is assumed to collect all needed
        information from its related self.obj.
        """
        return not self._is_deleted

    def at_start(self):
        """
        Called whenever the script is started, which for persistent
        scripts is at least once every server start. It will also be called
        when starting again after a pause (such as after a server reload)
        """
        pass

    def at_repeat(self):
        """
        Called repeatedly if this Script is set to repeat
        regularly.
        """
        pass

    def at_stop(self):
        """
        Called whenever when it's time for this script to stop
        (either because is_valid returned False or it runs out of iterations)
        """
        pass

    def at_server_reload(self):
        """
        This hook is called whenever the server is shutting down for
        restart/reboot. If you want to, for example, save non-persistent
        properties across a restart, this is the place to do it.
        """
        pass

    def at_server_shutdown(self):
        """
        This hook is called whenever the server is shutting down fully
        (i.e. not for a restart).
        """
        pass


# Some useful default Script types used by Evennia.

class DoNothing(Script):
    "An script that does nothing. Used as default fallback."
    def at_script_creation(self):
        "Setup the script"
        self.key = "sys_do_nothing"
        self.desc = _("This is an empty placeholder script.")


class Store(Script):
    "Simple storage script"
    def at_script_creation(self):
        "Setup the script"
        self.key = "sys_storage"
        self.desc = _("This is a generic storage container.")


class CheckSessions(Script):
    "Check sessions regularly."
    def at_script_creation(self):
        "Setup the script"
        self.key = "sys_session_check"
        self.desc = _("Checks sessions so they are live.")
        self.interval = 60  # repeat every 60 seconds
        self.persistent = True

    def at_repeat(self):
        "called every 60 seconds"
        global _SESSIONS
        if not _SESSIONS:
            from src.server.sessionhandler import SESSIONS as _SESSIONS
        #print "session check!"
        #print "ValidateSessions run"
        _SESSIONS.validate_sessions()

_FLUSH_CACHE = None
_IDMAPPER_CACHE_MAX_MEMORY = settings.IDMAPPER_CACHE_MAXSIZE
class ValidateIdmapperCache(Script):
    """
    Check memory use of idmapper cache
    """
    def at_script_creation(self):
        self.key = "sys_cache_validate"
        self.desc = _("Restrains size of idmapper cache.")
        self.interval = 61 * 5 # staggered compared to session check
        self.persistent = True

    def at_repeat(self):
        "Called every ~5 mins"
        global _FLUSH_CACHE
        if not _FLUSH_CACHE:
            from src.utils.idmapper.base import conditional_flush as _FLUSH_CACHE
        _FLUSH_CACHE(_IDMAPPER_CACHE_MAX_MEMORY)

class ValidateScripts(Script):
    "Check script validation regularly"
    def at_script_creation(self):
        "Setup the script"
        self.key = "sys_scripts_validate"
        self.desc = _("Validates all scripts regularly.")
        self.interval = 3600  # validate every hour.
        self.persistent = True

    def at_repeat(self):
        "called every hour"
        #print "ValidateScripts run."
        ScriptDB.objects.validate()


class ValidateChannelHandler(Script):
    "Update the channelhandler to make sure it's in sync."
    def at_script_creation(self):
        "Setup the script"
        self.key = "sys_channels_validate"
        self.desc = _("Updates the channel handler")
        self.interval = 3700  # validate a little later than ValidateScripts
        self.persistent = True

    def at_repeat(self):
        "called every hour+"
        #print "ValidateChannelHandler run."
        channelhandler.CHANNELHANDLER.update()

