"""
This module defines Scripts, out-of-character entities that can store
data both on themselves and on other objects while also having the
ability to run timers.

"""

from twisted.internet.defer import Deferred, maybeDeferred
from twisted.internet.task import LoopingCall
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _
from evennia.typeclasses.models import TypeclassBase
from evennia.scripts.models import ScriptDB
from evennia.scripts.manager import ScriptManager
from evennia.utils import create, logger

__all__ = ["DefaultScript", "DoNothing", "Store"]


FLUSHING_INSTANCES = False  # whether we're in the process of flushing scripts from the cache
SCRIPT_FLUSH_TIMERS = {}  # stores timers for scripts that are currently being flushed


def restart_scripts_after_flush():
    """After instances are flushed, validate scripts so they're not dead for a long period of time"""
    global FLUSHING_INSTANCES
    ScriptDB.objects.validate()
    FLUSHING_INSTANCES = False


class ExtendedLoopingCall(LoopingCall):
    """
    LoopingCall that can start at a delay different
    than `self.interval`.

    """

    start_delay = None
    callcount = 0

    def start(self, interval, now=True, start_delay=None, count_start=0):
        """
        Start running function every interval seconds.

        This overloads the LoopingCall default by offering the
        start_delay keyword and ability to repeat.

        Args:
            interval (int): Repeat interval in seconds.
            now (bool, optional): Whether to start immediately or after
                `start_delay` seconds.
            start_delay (int): The number of seconds before starting.
                If None, wait interval seconds. Only valid if `now` is `False`.
                It is used as a way to start with a variable start time
                after a pause.
            count_start (int): Number of repeats to start at. The  count
                goes up every time the system repeats. This is used to
                implement something repeating `N` number of times etc.

        Raises:
            AssertError: if trying to start a task which is already running.
            ValueError: If interval is set to an invalid value < 0.

        Notes:
            As opposed to Twisted's inbuilt count mechanism, this
            system will count also if force_repeat() was called rather
            than just the number of `interval` seconds since the start.
            This allows us to force-step through a limited number of
            steps if we want.

        """
        assert not self.running, "Tried to start an already running " "ExtendedLoopingCall."
        if interval < 0:
            raise ValueError("interval must be >= 0")
        self.running = True
        deferred = self._deferred = Deferred()
        self.starttime = self.clock.seconds()
        self.interval = interval
        self._runAtStart = now
        self.callcount = max(0, count_start)
        self.start_delay = start_delay if start_delay is None else max(0, start_delay)

        if now:
            # run immediately
            self()
        elif start_delay is not None and start_delay >= 0:
            # start after some time: for this to work we need to
            # trick _scheduleFrom by temporarily setting a different
            # self.interval for it to check.
            real_interval, self.interval = self.interval, start_delay
            self._scheduleFrom(self.starttime)
            # re-set the actual interval (this will be picked up
            # next time it runs
            self.interval = real_interval
        else:
            self._scheduleFrom(self.starttime)
        return deferred

    def __call__(self):
        """
        Tick one step. We update callcount (tracks number of calls) as
        well as null start_delay (needed in order to correctly
        estimate next_call_time at all times).

        """
        self.callcount += 1
        if self.start_delay:
            self.start_delay = None
            self.starttime = self.clock.seconds()
        LoopingCall.__call__(self)

    def force_repeat(self):
        """
        Force-fire the callback

        Raises:
            AssertionError: When trying to force a task that is not
                running.

        """
        assert self.running, "Tried to fire an ExtendedLoopingCall " "that was not running."
        self.call.cancel()
        self.call = None
        self.starttime = self.clock.seconds()
        self()

    def next_call_time(self):
        """
        Get the next call time. This also takes the eventual effect
        of start_delay into account.

        Returns:
            next (int or None): The time in seconds until the next call. This
                takes `start_delay` into account. Returns `None` if
                the task is not running.

        """
        if self.running:
            total_runtime = self.clock.seconds() - self.starttime
            interval = self.start_delay or self.interval
            return interval - (total_runtime % self.interval)
        return None


class ScriptBase(ScriptDB, metaclass=TypeclassBase):
    """
    Base class for scripts. Don't inherit from this, inherit from the
    class `DefaultScript` below instead.

    """

    objects = ScriptManager()

    def __str__(self):
        return "<{cls} {key}>".format(cls=self.__class__.__name__, key=self.key)

    def __repr__(self):
        return str(self)

    def _start_task(self):
        """
        Start task runner.

        """
        if self.ndb._task:
            return
        self.ndb._task = ExtendedLoopingCall(self._step_task)

        if self.db._paused_time:
            # the script was paused; restarting
            callcount = self.db._paused_callcount or 0
            self.ndb._task.start(
                self.db_interval, now=False, start_delay=self.db._paused_time, count_start=callcount
            )
            del self.db._paused_time
            del self.db._paused_repeats
        else:
            # starting script anew
            self.ndb._task.start(self.db_interval, now=not self.db_start_delay)

    def _stop_task(self):
        """
        Stop task runner

        """
        task = self.ndb._task
        if task and task.running:
            task.stop()

    def _step_errback(self, e):
        """
        Callback for runner errors

        """
        cname = self.__class__.__name__
        estring = _(
            "Script %(key)s(#%(dbid)s) of type '%(cname)s': at_repeat() error '%(err)s'."
        ) % {"key": self.key, "dbid": self.dbid, "cname": cname, "err": e.getErrorMessage()}
        try:
            self.db_obj.msg(estring)
        except Exception:
            # we must not crash inside the errback, even if db_obj is None.
            pass
        logger.log_err(estring)

    def _step_callback(self):
        """
        Step task runner. No try..except needed due to defer wrap.

        """

        if not self.is_valid():
            self.stop()
            return

        # call hook
        self.at_repeat()

        # check repeats
        callcount = self.ndb._task.callcount
        maxcount = self.db_repeats
        if maxcount > 0 and maxcount <= callcount:
            self.stop()

    def _step_task(self):
        """
        Step task. This groups error handling.
        """
        try:
            return maybeDeferred(self._step_callback).addErrback(self._step_errback)
        except Exception:
            logger.log_trace()
        return None

    def at_script_creation(self):
        """
        Should be overridden in child.

        """
        pass

    def at_first_save(self, **kwargs):
        """
        This is called after very first time this object is saved.
        Generally, you don't need to overload this, but only the hooks
        called by this method.

        Args:
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        self.at_script_creation()

        if hasattr(self, "_createdict"):
            # this will only be set if the utils.create_script
            # function was used to create the object. We want
            # the create call's kwargs to override the values
            # set by hooks.
            cdict = self._createdict
            updates = []
            if not cdict.get("key"):
                if not self.db_key:
                    self.db_key = "#%i" % self.dbid
                    updates.append("db_key")
            elif self.db_key != cdict["key"]:
                self.db_key = cdict["key"]
                updates.append("db_key")
            if cdict.get("interval") and self.interval != cdict["interval"]:
                self.db_interval = cdict["interval"]
                updates.append("db_interval")
            if cdict.get("start_delay") and self.start_delay != cdict["start_delay"]:
                self.db_start_delay = cdict["start_delay"]
                updates.append("db_start_delay")
            if cdict.get("repeats") and self.repeats != cdict["repeats"]:
                self.db_repeats = cdict["repeats"]
                updates.append("db_repeats")
            if cdict.get("persistent") and self.persistent != cdict["persistent"]:
                self.db_persistent = cdict["persistent"]
                updates.append("db_persistent")
            if cdict.get("desc") and self.desc != cdict["desc"]:
                self.db_desc = cdict["desc"]
                updates.append("db_desc")
            if updates:
                self.save(update_fields=updates)

            if cdict.get("permissions"):
                self.permissions.batch_add(*cdict["permissions"])
            if cdict.get("locks"):
                self.locks.add(cdict["locks"])
            if cdict.get("tags"):
                # this should be a list of tags, tuples (key, category) or (key, category, data)
                self.tags.batch_add(*cdict["tags"])
            if cdict.get("attributes"):
                # this should be tuples (key, val, ...)
                self.attributes.batch_add(*cdict["attributes"])
            if cdict.get("nattributes"):
                # this should be a dict of nattrname:value
                for key, value in cdict["nattributes"]:
                    self.nattributes.add(key, value)

            if not cdict.get("autostart"):
                # don't auto-start the script
                return

        # auto-start script (default)
        self.start()


class DefaultScript(ScriptBase):
    """
    This is the base TypeClass for all Scripts. Scripts describe
    events, timers and states in game, they can have a time component
    or describe a state that changes under certain conditions.

    """

    @classmethod
    def create(cls, key, **kwargs):
        """
        Provides a passthrough interface to the utils.create_script() function.

        Args:
            key (str): Name of the new object.

        Returns:
            object (Object): A newly created object of the given typeclass.
            errors (list): A list of errors in string form, if any.

        """
        errors = []
        obj = None

        kwargs["key"] = key

        # If no typeclass supplied, use this class
        kwargs["typeclass"] = kwargs.pop("typeclass", cls)

        try:
            obj = create.create_script(**kwargs)
        except Exception as e:
            errors.append("The script '%s' encountered errors and could not be created." % key)
            logger.log_err(e)

        return obj, errors

    def at_script_creation(self):
        """
        Only called once, when script is first created.

        """
        pass

    def time_until_next_repeat(self):
        """
        Get time until the script fires it `at_repeat` hook again.

        Returns:
            next (int): Time in seconds until the script runs again.
                If not a timed script, return `None`.

        Notes:
            This hook is not used in any way by the script's stepping
            system; it's only here for the user to be able to check in
            on their scripts and when they will next be run.

        """
        task = self.ndb._task
        if task:
            try:
                return int(round(task.next_call_time()))
            except TypeError:
                pass
        return None

    def remaining_repeats(self):
        """
        Get the number of returning repeats for limited Scripts.

        Returns:
            remaining (int or `None`): The number of repeats
                remaining until the Script stops. Returns `None`
                if it has unlimited repeats.

        """
        task = self.ndb._task
        if task:
            return max(0, self.db_repeats - task.callcount)
        return None

    def at_idmapper_flush(self):
        """If we're flushing this object, make sure the LoopingCall is gone too"""
        ret = super(DefaultScript, self).at_idmapper_flush()
        if ret and self.ndb._task:
            try:
                from twisted.internet import reactor

                global FLUSHING_INSTANCES
                # store the current timers for the _task and stop it to avoid duplicates after cache flush
                paused_time = self.ndb._task.next_call_time()
                callcount = self.ndb._task.callcount
                self._stop_task()
                SCRIPT_FLUSH_TIMERS[self.id] = (paused_time, callcount)
                # here we ensure that the restart call only happens once, not once per script
                if not FLUSHING_INSTANCES:
                    FLUSHING_INSTANCES = True
                    reactor.callLater(2, restart_scripts_after_flush)
            except Exception:
                import traceback

                traceback.print_exc()
        return ret

    def start(self, force_restart=False):
        """
        Called every time the script is started (for persistent
        scripts, this is usually once every server start)

        Args:
            force_restart (bool, optional): Normally an already
                started script will not be started again. if
                `force_restart=True`, the script will always restart
                the script, regardless of if it has started before.

        Returns:
            result (int): 0 or 1 depending on if the script successfully
                started or not. Used in counting.

        """
        if self.is_active and not force_restart:
            # The script is already running, but make sure we have a _task if
            # this is after a cache flush
            if not self.ndb._task and self.db_interval >= 0:
                self.ndb._task = ExtendedLoopingCall(self._step_task)
                try:
                    start_delay, callcount = SCRIPT_FLUSH_TIMERS[self.id]
                    del SCRIPT_FLUSH_TIMERS[self.id]
                    now = False
                except (KeyError, ValueError, TypeError):
                    now = not self.db_start_delay
                    start_delay = None
                    callcount = 0
                self.ndb._task.start(
                    self.db_interval, now=now, start_delay=start_delay, count_start=callcount
                )
            return 0

        obj = self.obj
        if obj:
            # check so the scripted object is valid and initalized
            try:
                obj.cmdset
            except AttributeError:
                # this means the object is not initialized.
                logger.log_trace()
                self.is_active = False
                return 0

        # try to restart a paused script
        try:
            if self.unpause(manual_unpause=False):
                return 1
        except RuntimeError:
            # manually paused.
            return 0

        # start the script from scratch
        self.is_active = True
        try:
            self.at_start()
        except Exception:
            logger.log_trace()

        if self.db_interval > 0:
            self._start_task()
        return 1

    def stop(self, kill=False):
        """
        Called to stop the script from running.  This also deletes the
        script.

        Args:
            kill (bool, optional): - Stop the script without
                calling any relevant script hooks.

        Returns:
            result (int): 0 if the script failed to stop, 1 otherwise.
                Used in counting.

        """
        if not kill:
            try:
                self.at_stop()
            except Exception:
                logger.log_trace()
        self._stop_task()
        try:
            self.delete()
        except AssertionError:
            logger.log_trace()
            return 0
        except ObjectDoesNotExist:
            return 0
        return 1

    def pause(self, manual_pause=True):
        """
        This stops a running script and stores its active state.
        It WILL NOT call the `at_stop()` hook.

        """
        self.db._manual_pause = manual_pause
        if not self.db._paused_time:
            # only allow pause if not already paused
            task = self.ndb._task
            if task:
                self.db._paused_time = task.next_call_time()
                self.db._paused_callcount = task.callcount
                self._stop_task()
            self.is_active = False

    def unpause(self, manual_unpause=True):
        """
        Restart a paused script. This WILL call the `at_start()` hook.

        Args:
            manual_unpause (bool, optional): This is False if unpause is
                called by the server reload/reset mechanism.
        Returns:
            result (bool): True if unpause was triggered, False otherwise.

        Raises:
            RuntimeError: If trying to automatically resart this script
                (usually after a reset/reload), but it was manually paused,
                and so should not the auto-unpaused.

        """
        if not manual_unpause and self.db._manual_pause:
            # if this script was paused manually (by a direct call of pause),
            # it cannot be automatically unpaused (e.g. by a @reload)
            raise RuntimeError

        # Ensure that the script is fully unpaused, so that future calls
        # to unpause do not raise a RuntimeError
        self.db._manual_pause = False

        if self.db._paused_time:
            # only unpause if previously paused
            self.is_active = True

            try:
                self.at_start()
            except Exception:
                logger.log_trace()

            self._start_task()
            return True

    def restart(self, interval=None, repeats=None, start_delay=None):
        """
        Restarts an already existing/running Script from the
        beginning, optionally using different settings. This will
        first call the stop hooks, and then the start hooks again.

        Args:
            interval (int, optional): Allows for changing the interval
                of the Script. Given in seconds.  if `None`, will use the
                already stored interval.
            repeats (int, optional): The number of repeats. If unset, will
                use the previous setting.
            start_delay (bool, optional): If we should wait `interval` seconds
                before starting or not. If `None`, re-use the previous setting.

        """
        try:
            self.at_stop()
        except Exception:
            logger.log_trace()
        self._stop_task()
        self.is_active = False
        # remove all pause flags
        del self.db._paused_time
        del self.db._manual_pause
        del self.db._paused_callcount
        # set new flags and start over
        if interval is not None:
            self.interval = interval
        if repeats is not None:
            self.repeats = repeats
        if start_delay is not None:
            self.start_delay = start_delay
        self.start()

    def reset_callcount(self, value=0):
        """
        Reset the count of the number of calls done.

        Args:
            value (int, optional): The repeat value to reset to. Default
                is to set it all the way back to 0.

        Notes:
            This is only useful if repeats != 0.

        """
        task = self.ndb._task
        if task:
            task.callcount = max(0, int(value))

    def force_repeat(self):
        """
        Fire a premature triggering of the script callback. This
        will reset the timer and count down repeats as if the script
        had fired normally.
        """
        task = self.ndb._task
        if task:
            task.force_repeat()

    def is_valid(self):
        """
        Is called to check if the script is valid to run at this time.
        Should return a boolean. The method is assumed to collect all
        needed information from its related self.obj.

        """
        return not self._is_deleted

    def at_start(self, **kwargs):
        """
        Called whenever the script is started, which for persistent
        scripts is at least once every server start. It will also be
        called when starting again after a pause (such as after a
        server reload)

        Args:
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        pass

    def at_repeat(self, **kwargs):
        """
        Called repeatedly if this Script is set to repeat regularly.

        Args:
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        pass

    def at_stop(self, **kwargs):
        """
        Called whenever when it's time for this script to stop (either
        because is_valid returned False or it runs out of iterations)

        Args
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        pass

    def at_server_reload(self):
        """
        This hook is called whenever the server is shutting down for
        restart/reboot. If you want to, for example, save
        non-persistent properties across a restart, this is the place
        to do it.
        """
        pass

    def at_server_shutdown(self):
        """
        This hook is called whenever the server is shutting down fully
        (i.e. not for a restart).
        """
        pass


# Some useful default Script types used by Evennia.


class DoNothing(DefaultScript):
    """
    A script that does nothing. Used as default fallback.
    """

    def at_script_creation(self):
        """
        Setup the script
        """
        self.key = "sys_do_nothing"
        self.desc = "This is an empty placeholder script."


class Store(DefaultScript):
    """
    Simple storage script
    """

    def at_script_creation(self):
        """
        Setup the script
        """
        self.key = "sys_storage"
        self.desc = "This is a generic storage container."
