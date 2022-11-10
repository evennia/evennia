"""
This module defines Scripts, out-of-character entities that can store
data both on themselves and on other objects while also having the
ability to run timers.

"""

from django.utils.translation import gettext as _
from twisted.internet.defer import Deferred, maybeDeferred
from twisted.internet.task import LoopingCall

from evennia.scripts.manager import ScriptManager
from evennia.scripts.models import ScriptDB
from evennia.typeclasses.models import TypeclassBase
from evennia.utils import create, logger

__all__ = ["DefaultScript", "DoNothing", "Store"]


class ExtendedLoopingCall(LoopingCall):
    """
    Custom child of LoopingCall that can start at a delay different than
    `self.interval` and self.count=0. This allows it to support pausing
    by resuming at a later period.

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
            start_delay (int, optional): This only applies is `now=False`. It gives
                number of seconds to wait before starting. If `None`, use
                `interval` as this value instead. Internally, this is used as a
                way to start with a variable start time after a pause.
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
        assert not self.running, "Tried to start an already running ExtendedLoopingCall."
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
        if self._deferred:
            LoopingCall.__call__(self)

    def force_repeat(self):
        """
        Force-fire the callback

        Raises:
            AssertionError: When trying to force a task that is not
                running.

        """
        assert self.running, "Tried to fire an ExtendedLoopingCall that was not running."
        self.call.cancel()
        self.call = None
        self.starttime = self.clock.seconds()
        self()

    def next_call_time(self):
        """
        Get the next call time. This also takes the eventual effect
        of start_delay into account.

        Returns:
            int or None: The time in seconds until the next call. This
                takes `start_delay` into account. Returns `None` if
                the task is not running.

        """
        if self.running and self.interval > 0:
            total_runtime = self.clock.seconds() - self.starttime
            interval = self.start_delay or self.interval
            return max(0, interval - (total_runtime % self.interval))


class ScriptBase(ScriptDB, metaclass=TypeclassBase):
    """
    Base class for scripts. Don't inherit from this, inherit from the
    class `DefaultScript` below instead.

    This handles the timer-component of the Script.

    """

    objects = ScriptManager()

    def __str__(self):
        return "<{cls} {key}>".format(cls=self.__class__.__name__, key=self.key)

    def __repr__(self):
        return str(self)

    def at_idmapper_flush(self):
        """
        If we're flushing this object, make sure the LoopingCall is gone too.
        """
        ret = super().at_idmapper_flush()
        if ret and self.ndb._task:
            self.ndb._pause_task(auto_pause=True)
        # TODO - restart anew ?
        return ret

    def _start_task(
        self,
        interval=None,
        start_delay=None,
        repeats=None,
        force_restart=False,
        auto_unpause=False,
        **kwargs,
    ):
        """
        Start/Unpause task runner, optionally with new values. If given, this will
        update the Script's fields.

        Keyword Args:
            interval (int): How often to tick the task, in seconds. If this is <= 0,
                no task will start and properties will not be updated on the Script.
            start_delay (int): If the start should be delayed.
            repeats (int): How many repeats. 0 for infinite repeats.
            force_restart (bool): If set, always create a new task running even if an
                old one already was running. Otherwise this will only happen if
                new script properties were passed.
            auto_unpause (bool): This is an automatic unpaused (used e.g by Evennia after
                a reload) and should not un-pause manually paused Script timers.
        Note:
            If setting the `start-delay` of a *paused* Script, the Script will
            restart exactly after that new start-delay, ignoring the time it
            was paused at. If only changing the `interval`, the Script will
            come out of pause comparing the time it spent in the *old* interval
            with the *new* interval in order to determine when next to fire.

        Examples:
            - Script previously had an interval of 10s and was paused 5s into that interval.
              Script is now restarted with a 20s interval. It will next fire after 15s.
            - Same Script is restarted with a 3s interval. It will fire immediately.

        """
        if self.pk is None:
            # script object already deleted from db - don't start a new timer
            raise ScriptDB.DoesNotExist

        # handle setting/updating fields
        update_fields = []
        old_interval = self.db_interval
        if interval is not None:
            self.db_interval = interval
            update_fields.append("db_interval")
        if start_delay is not None:
            self.db_start_delay = start_delay
            update_fields.append("db_start_delay")
        if repeats is not None:
            self.db_repeats = repeats
            update_fields.append("db_repeats")

        # validate interval
        if self.db_interval and self.db_interval > 0:
            if not self.is_active:
                self.db_is_active = True
                update_fields.append("db_is_active")
        else:
            # no point in starting a task with no interval.
            return

        restart = bool(update_fields) or force_restart
        self.save(update_fields=update_fields)

        if self.ndb._task and self.ndb._task.running:
            if restart:
                # a change needed/forced; stop/remove old task
                self._stop_task()
            else:
                # task alreaady running and no changes needed
                return

        if not self.ndb._task:
            # we should have a fresh task after this point
            self.ndb._task = ExtendedLoopingCall(self._step_task)

        self._unpause_task(
            interval=interval,
            start_delay=start_delay,
            auto_unpause=auto_unpause,
            old_interval=old_interval,
        )

        if not self.ndb._task.running:
            # if not unpausing started it, start script anew with the new values
            self.ndb._task.start(self.db_interval, now=not self.db_start_delay)

        self.at_start(**kwargs)

    def _pause_task(self, auto_pause=False, **kwargs):
        """
        Pause task where it is, saving the current status.

        Args:
            auto_pause (str):

        """
        if not self.db._paused_time:
            # only allow pause if not already paused
            task = self.ndb._task
            if task:
                self.db._paused_time = task.next_call_time()
                self.db._paused_callcount = task.callcount
                self.db._manually_paused = not auto_pause
                if task.running:
                    task.stop()
            self.ndb._task = None

            self.at_pause(auto_pause=auto_pause, **kwargs)

    def _unpause_task(
        self, interval=None, start_delay=None, auto_unpause=False, old_interval=0, **kwargs
    ):
        """
        Unpause task from paused status. This is used for auto-paused tasks, such
        as tasks paused on a server reload.

        Args:
            interval (int): How often to tick the task, in seconds.
            start_delay (int): If the start should be delayed.
            auto_unpause (bool): If set, this will only unpause scripts that were unpaused
                automatically (useful during a system reload/shutdown).
            old_interval (int): The old Script interval (or current one if nothing changed). Used
                to recalculate the unpause startup interval.

        """
        paused_time = self.db._paused_time
        if paused_time:
            if auto_unpause and self.db._manually_paused:
                # this was manually paused.
                return

            # task was paused. This will use the new values as needed.
            callcount = self.db._paused_callcount or 0
            if start_delay is None and interval is not None:
                # adjust start-delay based on how far we were into previous interval
                start_delay = max(0, interval - (old_interval - paused_time))
            else:
                start_delay = paused_time

            if not self.ndb._task:
                self.ndb._task = ExtendedLoopingCall(self._step_task)

            self.ndb._task.start(
                self.db_interval, now=False, start_delay=start_delay, count_start=callcount
            )
            self.db._paused_time = None
            self.db._paused_callcount = None
            self.db._manually_paused = None

            self.at_start(**kwargs)

    def _stop_task(self, **kwargs):
        """
        Stop task runner and delete the task.

        """
        task_stopped = False
        task = self.ndb._task
        if task and task.running:
            task.stop()
            task_stopped = True

        self.ndb._task = None
        self.db_is_active = False

        # make sure this is not confused as a paused script
        self.db._paused_time = None
        self.db._paused_callcount = None
        self.db._manually_paused = None

        self.save(update_fields=["db_is_active"])
        if task_stopped:
            self.at_stop(**kwargs)

    def _step_errback(self, e):
        """
        Callback for runner errors

        """
        cname = self.__class__.__name__
        estring = _(
            "Script {key}(#{dbid}) of type '{name}': at_repeat() error '{err}'.".format(
                key=self.key, dbid=self.dbid, name=cname, err=e.getErrorMessage()
            )
        )
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
        if not self.ndb._task:
            # if there is no task, we have no business using this method
            return

        if not self.is_valid():
            self.stop()
            return

        # call hook
        try:
            self.at_repeat()
        except Exception:
            logger.log_trace()
            raise

        # check repeats
        if self.ndb._task:
            # we need to check for the task in case stop() was called
            # inside at_repeat() and it already went away.
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

    # Access methods / hooks

    def at_first_save(self, **kwargs):
        """
        This is called after very first time this object is saved.
        Generally, you don't need to overload this, but only the hooks
        called by this method.

        Args:
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        self.basetype_setup()
        self.at_script_creation()
        # initialize Attribute/TagProperties
        self.init_evennia_properties()

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
                self.db_interval = max(0, cdict["interval"])
                updates.append("db_interval")
            if cdict.get("start_delay") and self.start_delay != cdict["start_delay"]:
                self.db_start_delay = cdict["start_delay"]
                updates.append("db_start_delay")
            if cdict.get("repeats") and self.repeats != cdict["repeats"]:
                self.db_repeats = max(0, cdict["repeats"])
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

            if cdict.get("autostart"):
                # autostart the script
                self._start_task(force_restart=True)

    def delete(self):
        """
        Delete the Script. Normally stops any timer task. This fires at_script_delete before
        deletion.

        Returns:
            bool: If deletion was successful or not. Only time this can fail would be if
                the script was already previously deleted, or `at_script_delete` returns
                False.

        """
        if not self.pk or not self.at_script_delete():
            return False

        self._stop_task()
        super().delete()
        return True

    def basetype_setup(self):
        """
        Changes fundamental aspects of the type. Usually changes are made in at_script creation
        instead.

        """
        pass

    def at_init(self):
        """
        Called when the Script is cached in the idmapper. This is usually more reliable
        than overriding `__init__` since the latter can be called at unexpected times.

        """
        pass

    def at_script_creation(self):
        """
        Should be overridden in child.

        """
        pass

    def at_script_delete(self):
        """
        Called when script is deleted, before the script timer stops.

        Returns:
            bool: If False, deletion is aborted.

        """
        return True

    def is_valid(self):
        """
        If returning False, `at_repeat` will not be called and timer will stop
        updating.
        """
        return True

    def at_repeat(self, **kwargs):
        """
        Called repeatedly every `interval` seconds, once `.start()` has
        been called on the Script at least once.

        Args:
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        pass

    def at_start(self, **kwargs):
        pass

    def at_pause(self, **kwargs):
        pass

    def at_stop(self, **kwargs):
        pass

    def start(self, interval=None, start_delay=None, repeats=None, **kwargs):
        """
        Start/Unpause timer component, optionally with new values. If given,
        this will update the Script's fields. This will start `at_repeat` being
        called every `interval` seconds.

        Keyword Args:
            interval (int): How often to fire `at_repeat` in seconds.
            start_delay (int): If the start of ticking should be delayed.
            repeats (int): How many repeats. 0 for infinite repeats.
            **kwargs: Optional (default unused) kwargs passed on into the `at_start` hook.

        Notes:
            If setting the `start-delay` of a *paused* Script, the Script will
            restart exactly after that new start-delay, ignoring the time it
            was paused at. If only changing the `interval`, the Script will
            come out of pause comparing the time it spent in the *old* interval
            with the *new* interval in order to determine when next to fire.

        Examples:
            - Script previously had an interval of 10s and was paused 5s into that interval.
              Script is now restarted with a 20s interval. It will next fire after 15s.
            - Same Script is restarted with a 3s interval. It will fire immediately.

        """
        self._start_task(interval=interval, start_delay=start_delay, repeats=repeats, **kwargs)

    # legacy alias
    update = start

    def stop(self, **kwargs):
        """
        Stop the Script's timer component. This will not delete the Sctipt,
        just stop the regular firing of `at_repeat`. Running `.start()` will
        start the timer anew, optionally with new settings..

        Args:
            **kwargs: Optional (default unused) kwargs passed on into the `at_stop` hook.

        """
        self._stop_task(**kwargs)

    def pause(self, **kwargs):
        """
        Manually the Script's timer component manually.

        Args:
            **kwargs: Optional (default unused) kwargs passed on into the `at_pause` hook.

        """
        self._pause_task(manual_pause=True, **kwargs)

    def unpause(self, **kwargs):
        """
        Manually unpause a Paused Script.

        Args:
            **kwargs: Optional (default unused) kwargs passed on into the `at_start` hook.

        """
        self._unpause_task(**kwargs)

    def time_until_next_repeat(self):
        """
        Get time until the script fires it `at_repeat` hook again.

        Returns:
            int or None: Time in seconds until the script runs again.
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
            int or None: The number of repeats remaining until the Script
                stops. Returns `None` if it has unlimited repeats.

        """
        task = self.ndb._task
        if task:
            return max(0, self.db_repeats - task.callcount)
        return None

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
        except Exception:
            logger.log_trace()
            errors.append("The script '%s' encountered errors and could not be created." % key)

        return obj, errors

    def at_script_creation(self):
        """
        Only called once, when script is first created.

        """
        pass

    def is_valid(self):
        """
        Is called to check if the script's timer is valid to run at this time.
        Should return a boolean. If False, the timer will be stopped.

        """
        return True

    def at_start(self, **kwargs):
        """
        Called whenever the script timer is started, which for persistent
        timed scripts is at least once every server start. It will also be
        called when starting again after a pause (including after a
        server reload).

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

    def at_pause(self, manual_pause=True, **kwargs):
        """
        Called when this script's timer pauses.

        Args:
            manual_pause (bool): If set, pausing was done by a direct call. The
                non-manual pause indicates the script was paused as part of
                the server reload.

        """
        pass

    def at_stop(self, **kwargs):
        """
        Called whenever when it's time for this script's timer to stop (either
        because is_valid returned False, it ran out of iterations or it was manuallys
        stopped.

        Args:
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        pass

    def at_script_delete(self):
        """
        Called when the Script is deleted, before stopping the timer.

        Returns:
            bool: If False, the deletion is aborted.

        """
        return True

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

    def at_server_start(self):
        """
        This hook is called after the server has started. It can be used to add
        post-startup setup for Scripts without a timer component (for which at_start
        could be used).

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
