"""
Module containing the task handler for Evennia deferred tasks, persistent or not.
"""

from datetime import datetime, timedelta
from pickle import PickleError

from twisted.internet import reactor
from twisted.internet.defer import CancelledError as DefCancelledError
from twisted.internet.task import deferLater

from evennia.server.models import ServerConfig
from evennia.utils.dbserialize import dbserialize, dbunserialize
from evennia.utils.logger import log_err

TASK_HANDLER = None


def handle_error(*args, **kwargs):
    """Handle errors within deferred objects."""
    for arg in args:
        # suppress cancel errors
        if arg.type == DefCancelledError:
            continue
        raise arg


class TaskHandlerTask:
    """An object to represent a single TaskHandler task.

    Instance Attributes:
        task_id (int): the global id for this task
        deferred (deferred): a reference to this task's deferred
    Property Attributes:
        paused (bool): check if the deferred instance of a task has been paused.
        called(self): A task attribute to check if the deferred instance of a task has been called.

    Methods:
        pause(): Pause the callback of a task.
        unpause(): Process all callbacks made since pause() was called.
        do_task(): Execute the task (call its callback).
        call(): Call the callback of this task.
        remove(): Remove a task without executing it.
        cancel(): Stop a task from automatically executing.
        active(): Check if a task is active (has not been called yet).
        exists(): Check if a task exists.
        get_id(): Returns the global id for this task. For use with

    """

    def __init__(self, task_id):
        self.task_id = task_id
        self.deferred = TASK_HANDLER.get_deferred(task_id)

    def get_deferred(self):
        """Return the instance of the deferred the task id is using.

        Returns:
            bool or deferred: An instance of a deferred or False if there is no task with the id.
                None is returned if there is no deferred affiliated with this id.

        """
        return TASK_HANDLER.get_deferred(self.task_id)

    def pause(self):
        """
        Pause the callback of a task.
        To resume use `TaskHandlerTask.unpause`.

        """
        d = self.deferred
        if d:
            d.pause()

    def unpause(self):
        """
        Unpause a task, run the task if it has passed delay time.

        """
        d = self.deferred
        if d:
            d.unpause()

    @property
    def paused(self):
        """
        A task attribute to check if the deferred instance of a task has been paused.

        This exists to mock usage of a twisted deferred object.

        Returns:
            bool or None: True if the task was properly paused. None if the task does not have
                a deferred instance.

        """
        d = self.deferred
        if d:
            return d.paused
        else:
            return None

    def do_task(self):
        """
        Execute the task (call its callback).
        If calling before timedelay, cancel the deferred instance affliated to this task.
        Remove the task from the dictionary of current tasks on a successful
        callback.

        Returns:
            bool or any: Set to `False` if the task does not exist in task
            handler. Otherwise it will be the return of the task's callback.

        """
        return TASK_HANDLER.do_task(self.task_id)

    def call(self):
        """
        Call the callback of a task.
        Leave the task unaffected otherwise.
        This does not use the task's deferred instance.
        The only requirement is that the task exist in task handler.

        Returns:
            bool or any: Set to `False` if the task does not exist in task
            handler. Otherwise it will be the return of the task's callback.

        """
        return TASK_HANDLER.call_task(self.task_id)

    def remove(self):
        """Remove a task without executing it.
        Deletes the instance of the task's deferred.

        Args:
            task_id (int): an existing task ID.

        Returns:
            bool: True if the removal completed successfully.

        """
        return TASK_HANDLER.remove(self.task_id)

    def cancel(self):
        """Stop a task from automatically executing.
        This will not remove the task.

        Returns:
            bool: True if the cancel completed successfully.
                False if the cancel did not complete successfully.

        """
        return TASK_HANDLER.cancel(self.task_id)

    def active(self):
        """Check if a task is active (has not been called yet).

        Returns:
            bool: True if a task is active (has not been called yet). False if
                it is not (has been called) or if the task does not exist.

        """
        return TASK_HANDLER.active(self.task_id)

    @property
    def called(self):
        """
        A task attribute to check if the deferred instance of a task has been called.

        This exists to mock usage of a twisted deferred object.
        It will not set to True if Task.call has been called. This only happens if
        task's deferred instance calls the callback.

        Returns:
            bool: True if the deferred instance of this task has called the callback.
                False if the deferred instnace of this task has not called the callback.

        """
        d = self.deferred
        if d:
            return d.called
        else:
            return None

    def exists(self):
        """
        Check if a task exists.
        Most task handler methods check for existence for you.

        Returns:
            bool: True the task exists False if it does not.

        """
        return TASK_HANDLER.exists(self.task_id)

    def get_id(self):
        """
        Returns the global id for this task. For use with
        `evennia.scripts.taskhandler.TASK_HANDLER`.

        Returns:
            task_id (int): global task id for this task.

        """
        return self.task_id


class TaskHandler(object):

    """A light singleton wrapper allowing to access permanent tasks.

    When `utils.delay` is called, the task handler is used to create
    the task.

    Task handler will automatically remove uncalled but canceled from task
    handler. By default this will not occur until a canceled task
    has been uncalled for 60 second after the time it should have been called.
    To adjust this time use TASK_HANDLER.stale_timeout. If stale_timeout is 0
    stale tasks will not be automatically removed.
    This is not done on a timer. I is done as new tasks are added or the load method is called.

    """

    def __init__(self):
        self.tasks = {}
        self.to_save = {}
        self.clock = reactor
        # number of seconds before an uncalled canceled task is removed from TaskHandler
        self.stale_timeout = 60
        self._now = False  # used in unit testing to manually set now time

    def load(self):
        """Load from the ServerConfig.

        This should be automatically called when Evennia starts.
        It populates `self.tasks` according to the ServerConfig.

        """
        to_save = False
        value = ServerConfig.objects.conf("delayed_tasks", default={})
        if isinstance(value, str):
            tasks = dbunserialize(value)
        else:
            tasks = value

        # At this point, `tasks` contains a dictionary of still-serialized tasks
        for task_id, value in tasks.items():
            date, callback, args, kwargs = dbunserialize(value)
            if isinstance(callback, tuple):
                # `callback` can be an object and name for instance methods
                obj, method = callback
                if obj is None:
                    to_save = True
                    continue

                callback = getattr(obj, method)
            self.tasks[task_id] = (date, callback, args, kwargs, True, None)

        if self.stale_timeout > 0:  # cleanup stale tasks.
            self.clean_stale_tasks()
        if to_save:
            self.save()

    def clean_stale_tasks(self):
        """remove uncalled but canceled from task handler.

        By default this will not occur until a canceled task
        has been uncalled for 60 second after the time it should have been called.
        To adjust this time use TASK_HANDLER.stale_timeout.

        """
        clean_ids = []
        for task_id, (date, callback, args, kwargs, persistent, _) in self.tasks.items():
            if not self.active(task_id):
                stale_date = date + timedelta(seconds=self.stale_timeout)
                # if a now time is provided use it (intended for unit testing)
                now = self._now if self._now else datetime.now()
                # the task was canceled more than stale_timeout seconds ago
                if now > stale_date:
                    clean_ids.append(task_id)
        for task_id in clean_ids:
            self.remove(task_id)
        return True

    def save(self):
        """
        Save the tasks in ServerConfig.

        """

        for task_id, (date, callback, args, kwargs, persistent, _) in self.tasks.items():
            if task_id in self.to_save:
                continue
            if not persistent:
                continue

            safe_callback = callback
            if getattr(callback, "__self__", None):
                # `callback` is an instance method
                obj = callback.__self__
                name = callback.__name__
                safe_callback = (obj, name)

            # Check if callback can be pickled. args and kwargs have been checked
            try:
                dbserialize(safe_callback)
            except (TypeError, AttributeError, PickleError) as err:
                raise ValueError(
                    "the specified callback {callback} cannot be pickled. "
                    "It must be a top-level function in a module or an "
                    "instance method ({err}).".format(callback=callback, err=err)
                )

            self.to_save[task_id] = dbserialize((date, safe_callback, args, kwargs))

        ServerConfig.objects.conf("delayed_tasks", self.to_save)

    def add(self, timedelay, callback, *args, **kwargs):
        """
        Add a new task.

        If the persistent kwarg is truthy:
        The callback, args and values for kwarg will be serialized. Type
        and attribute errors during the serialization will be logged,
        but will not throw exceptions.
        For persistent tasks do not use memory references in the callback
        function or arguments. After a restart those memory references are no
        longer accurate.

        Args:
            timedelay (int or float): time in seconds before calling the callback.
            callback (function or instance method): the callback itself
            any (any): any additional positional arguments to send to the callback
            *args: positional arguments to pass to callback.
            **kwargs: keyword arguments to pass to callback.
                - persistent (bool, optional): persist the task (stores it).
                    Persistent key and value is removed from kwargs it will
                    not be passed to callback.

        Returns:
            TaskHandlerTask: An object to represent a task.
                Reference `evennia.scripts.taskhandler.TaskHandlerTask` for complete details.

        """
        # set the completion time
        # Only used on persistent tasks after a restart
        now = datetime.now()
        delta = timedelta(seconds=timedelay)
        comp_time = now + delta
        # get an open task id
        used_ids = list(self.tasks.keys())
        task_id = 1
        while task_id in used_ids:
            task_id += 1

        # record the task to the tasks dictionary
        persistent = kwargs.get("persistent", False)
        if "persistent" in kwargs:
            del kwargs["persistent"]
        if persistent:
            safe_args = []
            safe_kwargs = {}

            # Check that args and kwargs contain picklable information
            for arg in args:
                try:
                    dbserialize(arg)
                except (TypeError, AttributeError, PickleError):
                    log_err(
                        "The positional argument {} cannot be "
                        "pickled and will not be present in the arguments "
                        "fed to the callback {}".format(arg, callback)
                    )
                else:
                    safe_args.append(arg)

            for key, value in kwargs.items():
                try:
                    dbserialize(value)
                except (TypeError, AttributeError, PickleError):
                    log_err(
                        "The {} keyword argument {} cannot be "
                        "pickled and will not be present in the arguments "
                        "fed to the callback {}".format(key, value, callback)
                    )
                else:
                    safe_kwargs[key] = value

            self.tasks[task_id] = (comp_time, callback, safe_args, safe_kwargs, persistent, None)
            self.save()
        else:  # this is a non-persitent task
            self.tasks[task_id] = (comp_time, callback, args, kwargs, persistent, None)

        # defer the task
        callback = self.do_task
        args = [task_id]
        kwargs = {}
        d = deferLater(self.clock, timedelay, callback, *args, **kwargs)
        d.addErrback(handle_error)

        # some tasks may complete before the deferred can be added
        if task_id in self.tasks:
            task = self.tasks.get(task_id)
            task = list(task)
            task[4] = persistent
            task[5] = d
            self.tasks[task_id] = task
        else:  # the task already completed
            return False
        if self.stale_timeout > 0:
            self.clean_stale_tasks()
        return TaskHandlerTask(task_id)

    def exists(self, task_id):
        """
        Check if a task exists.
        Most task handler methods check for existence for you.

        Args:
            task_id (int): an existing task ID.

        Returns:
            bool: True the task exists False if it does not.

        """
        if task_id in self.tasks:
            return True
        else:
            return False

    def active(self, task_id):
        """
        Check if a task is active (has not been called yet).

        Args:
            task_id (int): an existing task ID.

        Returns:
            bool: True if a task is active (has not been called yet). False if
                it is not (has been called) or if the task does not exist.

        """
        if task_id in self.tasks:
            # if the task has not been run, cancel it
            deferred = self.get_deferred(task_id)
            return not (deferred and deferred.called)
        else:
            return False

    def cancel(self, task_id):
        """
        Stop a task from automatically executing.
        This will not remove the task.

        Args:
            task_id (int): an existing task ID.

        Returns:
            bool: True if the cancel completed successfully.
                False if the cancel did not complete successfully.

        """
        if task_id in self.tasks:
            # if the task has not been run, cancel it
            d = self.get_deferred(task_id)
            if d:  # it is remotely possible for a task to not have a deferred
                if d.called:
                    return False
                else:  # the callback has not been called yet.
                    d.cancel()
                    return True
            else:  # this task has no deferred instance
                return False
        else:
            return False

    def remove(self, task_id):
        """
        Remove a task without executing it.
        Deletes the instance of the task's deferred.

        Args:
            task_id (int): an existing task ID.

        Returns:
            bool: True if the removal completed successfully.

        """
        d = None
        # delete the task from the tasks dictionary
        if task_id in self.tasks:
            # if the task has not been run, cancel it
            self.cancel(task_id)
            del self.tasks[task_id]  # delete the task from the tasks dictionary
        # remove the task from the persistent dictionary and ServerConfig
        if task_id in self.to_save:
            del self.to_save[task_id]
            self.save()  # remove from ServerConfig.objects
        # delete the instance of the deferred
        if d:
            del d
        return True

    def clear(self, save=True, cancel=True):
        """
        Clear all tasks. By default tasks are canceled and removed from the database as well.

        Args:
            save=True (bool): Should changes to persistent tasks be saved to database.
            cancel=True (bool): Cancel scheduled tasks before removing it from task handler.

        Returns:
            True (bool): if the removal completed successfully.

        """
        if self.tasks:
            for task_id in self.tasks.keys():
                if cancel:
                    self.cancel(task_id)
            self.tasks = {}
        if self.to_save:
            self.to_save = {}
        if save:
            self.save()
        return True

    def call_task(self, task_id):
        """
        Call the callback of a task.
        Leave the task unaffected otherwise.
        This does not use the task's deferred instance.
        The only requirement is that the task exist in task handler.

        Args:
            task_id (int): an existing task ID.

        Returns:
            bool or any: Set to `False` if the task does not exist in task
            handler. Otherwise it will be the return of the task's callback.

        """
        if task_id in self.tasks:
            date, callback, args, kwargs, persistent, d = self.tasks.get(task_id)
        else:  # the task does not exist
            return False
        return callback(*args, **kwargs)

    def do_task(self, task_id):
        """
        Execute the task (call its callback).
        If calling before timedelay cancel the deferred instance affliated to this task.
        Remove the task from the dictionary of current tasks on a successful
        callback.

        Args:
            task_id (int): a valid task ID.

        Returns:
            bool or any: Set to `False` if the task does not exist in task
            handler. Otherwise it will be the return of the task's callback.

        """
        callback_return = False
        if task_id in self.tasks:
            date, callback, args, kwargs, persistent, d = self.tasks.get(task_id)
        else:  # the task does not exist
            return False
        if d:  # it is remotely possible for a task to not have a deferred
            if not d.called:  # the task's deferred has not been called yet
                d.cancel()  # cancel the automated callback
        else:  # this task has no deferred, and should not be called
            return False
        callback_return = callback(*args, **kwargs)
        self.remove(task_id)
        return callback_return

    def get_deferred(self, task_id):
        """
        Return the instance of the deferred the task id is using.

        Args:
            task_id (int): a valid task ID.

        Returns:
            bool or deferred: An instance of a deferred or False if there is no task with the id.
                None is returned if there is no deferred affiliated with this id.

        """
        if task_id in self.tasks:
            return self.tasks[task_id][5]
        else:
            return None

    def create_delays(self):
        """
        Create the delayed tasks for the persistent tasks.
        This method should be automatically called when Evennia starts.

        """
        now = datetime.now()
        for task_id, (date, callback, args, kwargs, _, _) in self.tasks.items():
            self.tasks[task_id] = date, callback, args, kwargs, True, None
            seconds = max(0, (date - now).total_seconds())
            d = deferLater(self.clock, seconds, self.do_task, task_id)
            d.addErrback(handle_error)
            # some tasks may complete before the deferred can be added
            if self.tasks.get(task_id, False):
                self.tasks[task_id] = date, callback, args, kwargs, True, d


# Create the soft singleton
TASK_HANDLER = TaskHandler()
