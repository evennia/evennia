"""
Module containing the task handler for Evennia deferred tasks, persistent or not.
"""

from datetime import datetime, timedelta

from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.internet.defer import CancelledError as DefCancelledError
from evennia.server.models import ServerConfig
from evennia.utils.logger import log_err
from evennia.utils.dbserialize import dbserialize, dbunserialize

TASK_HANDLER = None


def handle_error(*args, **kwargs):
    """
    Handle errors withing deferred objects.
    """
    for arg in args:
        # suppress cancel errors
        if arg.type == DefCancelledError:
            continue
        raise arg


class TaskHandler(object):

    """
    A light singleton wrapper allowing to access permanent tasks.

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
        self._now = False # used in unit testing to manually set now time

    def load(self):
        """Load from the ServerConfig.

        Note:
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
            self.tasks[task_id] = date, callback, args, kwargs, True, None

        if self.stale_timeout > 0:  # cleanup stale tasks.
            self.clean_stale_tasks()
        if to_save:
            self.save()

    def clean_stale_tasks(self):
        """
        remove uncalled but canceled from task handler.

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

            if getattr(callback, "__self__", None):
                # `callback` is an instance method
                obj = callback.__self__
                name = callback.__name__
                callback = (obj, name)

            # Check if callback can be pickled. args and kwargs have been checked
            safe_callback = None

            try:
                dbserialize(callback)
            except (TypeError, AttributeError):
                raise ValueError(
                    "the specified callback {} cannot be pickled. "
                    "It must be a top-level function in a module or an "
                    "instance method.".format(callback)
                )
            else:
                safe_callback = callback

            self.to_save[task_id] = dbserialize((date, safe_callback, args, kwargs))
        ServerConfig.objects.conf("delayed_tasks", self.to_save)

    def add(self, timedelay, callback, *args, **kwargs):
        """Add a new persistent task in the configuration.

        Args:
            timedelay (int or float): time in sedconds before calling the callback.
            callback (function or instance method): the callback itself
            any (any): any additional positional arguments to send to the callback

        Keyword Args:
            persistent (bool, optional): persist the task (stores it).
                Add will return the task's id for use with the global TASK_HANDLER.
            any (any): additional keyword arguments to send to the callback

        Returns:
            task_id (int), the task's id intended for use with this class.
            False, if the task has completed before addition finishes.

        Notes:
            This method has two return types.
            An instance of twisted's Deferred class is standard.
            If the persistent kwarg is truthy instead a task ID will be returned.
            This task id can be used with task handler's do_task and remove methods.

            If the persistent kwarg is truthy:
            The callback, args and values for kwarg will be serialized. Type
            and attribute errors during the serialization will be logged,
            but will not throw exceptions.
            Do not use memory references in the callback function or arguments.
            As those memory references will no longer acurately point to
            the variable desired.
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
        if persistent:
            del kwargs["persistent"]
            safe_args = []
            safe_kwargs = {}

            # Check that args and kwargs contain picklable information
            for arg in args:
                try:
                    dbserialize(arg)
                except (TypeError, AttributeError):
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
                except (TypeError, AttributeError):
                    log_err(
                        "The {} keyword argument {} cannot be "
                        "pickled and will not be present in the arguments "
                        "fed to the callback {}".format(key, value, callback)
                    )
                else:
                    safe_kwargs[key] = value

            self.tasks[task_id] = (comp_time, callback, safe_args, safe_kwargs, True, None)
            self.save()
        else:  # this is a non-persitent task
            self.tasks[task_id] = (comp_time, callback, args, kwargs, True, None)

        # defer the task
        callback = self.do_task
        args = [task_id]
        kwargs = {}
        d = deferLater(self.clock, timedelay, callback, *args, **kwargs)
        d.addErrback(handle_error)

        # some tasks may complete before the deferal can be added
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
        return Task(task_id)

    def exists(self, task_id):
        """
        Test if a task exists.

        Args:
            task_id (int): an existing task ID.

        Returns:
            True (bool): if the task exists.
            False (bool): if the task does not exist.

        Note:
            Most task handler methods check for existence for you.
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
            True (bool): If a task is active (has not been called yet).
            False (bool): if the task
                is not active (has already been called),
                does not exist
        """
        if task_id in self.tasks:
            # if the task has not been run, cancel it
            d = self.get_deferred(task_id)
            if d:  # it is remotely possible for a task to not have a deferral
                if d.called:
                    return False
                else:  # the callback has not been called yet.
                    return True
            else:  # this task has no deferral, and could not have been called
                return True
        else:
            return False

    def cancel(self, task_id):
        """
        Stop a task from automatically executing.
        This will not remove the task.

        Args:
            task_id (int): an existing task ID.

        Returns:
            True (bool): if the removal completed successfully.
            False (bool): if the task:
                does not exist,
                has already run,
                does not have a deferral instance created for the task.
            None, if there was a raised exception
        """
        if task_id in self.tasks:
            # if the task has not been run, cancel it
            d = self.get_deferred(task_id)
            if d:  # it is remotely possible for a task to not have a deferral
                if d.called:
                    return False
                else:  # the callback has not been called yet.
                    d.cancel()
                    return True
            else:  # this task has no deferral
                return False
        else:
            return False

    def remove(self, task_id):
        """
        Remove a task without executing it.
        Deletes the instance of the task's deferral.

        Args:
            task_id (int): an existing task ID.

        Returns:
            True (bool): if the removal completed successfully or if the a
            task with the id does not exist.
            None: if there was a raised exception

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
        # delete the instance of the deferral
        if d:
            del d
        return True

    def remove_all(self, save=True, cancel=True):
        """
        Remove all tasks.
        By default tasks are canceled and removed from the database also.

        Arguments:
            save=True (bool): Should changes to persistent tasks be saved to database.
            cancel=True (bool): Cancel scheduled tasks before removing it from task handler.

        Returns:
            True (bool): if the removal completed successfully.
        """
        tasks_ids = tuple(self.tasks.keys())
        for task_id in tasks_ids:
            if cancel:
                self.cancel(task_id)
            del self.tasks[task_id]
        tasks_ids = tuple(self.to_save.keys())
        for task_id in tasks_ids:
            del self.to_save[task_id]
        if save:
            self.save()
        return True

    def do_task(self, task_id):
        """
        Execute the task (call its callback).
        If calling before timedelay cancel the deferral affliated to this task.
        Remove the task from the dictionary of current tasks on a successful
        callback.

        Args:
            task_id (int): a valid task ID.

        Returns:
            False (bool): if the:
                task no longer exists,
                has no affliated instance of deferral
            The return of the callback passed on task creation.
                This makes it possible for the callback to also return False
            None: if there was a raised exception

        Note:
            On a successful call the task will be removed from the dictionary
            of current tasks.

        """
        callback_return = False
        if task_id in self.tasks:
            date, callback, args, kwargs, persistent, d = self.tasks.get(task_id)
        else:  # the task does not exist
            return False
        if d:  # it is remotely possible for a task to not have a deferral
            if not d.called:  # the task has not been called yet
                d.cancel()  # cancel the automated callback
        else:  # this task has no deferral, and should not be called
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
            An instance of a deferral or False if there is no task with the id.
            None is returned if there is no deferral affiliated with this id.
        """
        if task_id in self.tasks:
            return self.tasks[task_id][5]
        else:
            return False

    def create_delays(self):
        """Create the delayed tasks for the persistent tasks.

        Note:
            This method should be automatically called when Evennia starts.

        """
        now = datetime.now()
        for task_id, (date, callbac, args, kwargs, _, _) in self.tasks.items():
            self.tasks[task_id] = date, callbac, args, kwargs, True, None
            seconds = max(0, (date - now).total_seconds())
            d = deferLater(self.clock, seconds, self.do_task, task_id)
            d.addErrback(handle_error)
            # some tasks may complete before the deferal can be added
            if self.tasks.get(task_id, False):
                self.tasks[task_id] = date, callbac, args, kwargs, True, d


# Create the soft singleton
TASK_HANDLER = TaskHandler()


class Task:
    """
    A object to represent a single TaskHandler task.

    Instance Attributes:
        task_id (int): the global id for this task
        deferred (deferred): a reference to this task's deferred
    Propert Attributes:
        paused (bool): check if the deferral of a task has been paused.
        called(self): A task attribute to check if the deferral of a task has been called.

    Methods:
        pause(): Pause the callback of a task.
        unpause(): Process all callbacks made since pause() was called.
        do_task(): Execute the task (call its callback).
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
        """
        Return the instance of the deferred the task id is using.

        Returns:
            An instance of a deferral or False if there is no task with the id.
            None is returned if there is no deferral affiliated with this id.
        """
        return TASK_HANDLER.get_deferred(self.task_id)

    def pause(self):
        """
        Pause the callback of a task.
        To resume use Task.unpause
        """
        d = self.deferred
        if d:
            d.pause()

    def unpause(self):
        """
        Process all callbacks made since pause() was called.
        """
        d = self.deferred
        if d:
            d.unpause()

    @property
    def paused(self):
        """
        A task attribute to check if the deferral of a task has been paused.

        This exists to mock usage of a twisted deferred object.

        This will return None if the deferred object for the task does not
        exist or if the task no longer exists.
        """
        d = self.deferred
        if d:
            return d.paused
        else:
            return None

    def do_task(self):
        """
        Execute the task (call its callback).
        If calling before timedelay cancel the deferral affliated to this task.
        Remove the task from the dictionary of current tasks on a successful
        callback.

        Returns:
            False (bool): if the:
                task no longer exists,
                has no affliated instance of deferral
            The return of the callback passed on task creation.
                This makes it possible for the callback to also return False
            None: if there was a raised exception

        Note:
            On a successful call the task will be removed from the dictionary
            of current tasks.

        """
        return TASK_HANDLER.do_task(self.task_id)

    def remove(self):
        """
        Remove a task without executing it.
        Deletes the instance of the task's deferral.

        Returns:
            True (bool): if the removal completed successfully or if the a
            task with the id does not exist.
            None: if there was a raised exception

        """
        return TASK_HANDLER.remove(self.task_id)

    def cancel(self):
        """
        Stop a task from automatically executing.
        This will not remove the task.

        Returns:
            True (bool): if the removal completed successfully.
            False (bool): if the task:
                does not exist,
                has already run,
                does not have a deferral instance created for the task.
            None, if there was a raised exception
        """
        return TASK_HANDLER.cancel(self.task_id)

    def active(self):
        """
        Check if a task is active (has not been called yet).

        Returns:
            True (bool): If a task is active (has not been called yet).
            False (bool): if the task
                is not active (has already been called),
                does not exist
        """
        return TASK_HANDLER.active(self.task_id)

    @property
    def called(self):
        """
        A task attribute to check if the deferral of a task has been called.

        This exists to mock usage of a twisted deferred object.
        It will not set to false if Task.call has been called.

        """
        d = self.deferred
        if d:
            return d.called
        else:
            return None

    def exists(self):
        """
        Test if a task exists.

        Returns:
            True (bool): if the task exists.
            False (bool): if the task does not exist.

        Note:
            Most task handler methods check for existence for you.
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
