"""
Module containing the task handler for Evennia deferred tasks, persistent or not.
"""

from datetime import datetime, timedelta

from twisted.internet import reactor
from twisted.internet.task import deferLater
from evennia.server.models import ServerConfig
from evennia.utils.logger import log_err
from evennia.utils.dbserialize import dbserialize, dbunserialize

TASK_HANDLER = None


class TaskHandler(object):

    """
    A light singleton wrapper allowing to access permanent tasks.

    When `utils.delay` is called, the task handler is used to create
    the task.  If `utils.delay`  is called with `persistent=True`, the
    task handler stores the new task and saves.

    It's easier to access these tasks (should it be necessary) using
    `evennia.scripts.taskhandler.TASK_HANDLER`, which contains one
    instance of this class, and use its `add` and `remove` methods.

    """

    def __init__(self):
        self.tasks = {}
        self.to_save = {}

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
            self.tasks[task_id] = (date, callback, args, kwargs)

        if to_save:
            self.save()

    def save(self):
        """Save the tasks in ServerConfig."""
        for task_id, (date, callback, args, kwargs) in self.tasks.items():
            if task_id in self.to_save:
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

        Kwargs:
            persistent (bool, optional): persist the task (store it).
            any (any): additional keyword arguments to send to the callback

        """
        persistent = kwargs.get("persistent", False)
        if persistent:
            del kwargs["persistent"]
            now = datetime.now()
            delta = timedelta(seconds=timedelay)

            # Choose a free task_id
            safe_args = []
            safe_kwargs = {}
            used_ids = list(self.tasks.keys())
            task_id = 1
            while task_id in used_ids:
                task_id += 1

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

            self.tasks[task_id] = (now + delta, callback, safe_args, safe_kwargs)
            self.save()
            callback = self.do_task
            args = [task_id]
            kwargs = {}

        return deferLater(reactor, timedelay, callback, *args, **kwargs)

    def remove(self, task_id):
        """Remove a persistent task without executing it.

        Args:
            task_id (int): an existing task ID.

        Note:
            A non-persistent task doesn't have a task_id, it is not stored
            in the TaskHandler.

        """
        del self.tasks[task_id]
        if task_id in self.to_save:
            del self.to_save[task_id]

        self.save()

    def do_task(self, task_id):
        """Execute the task (call its callback).

        Args:
            task_id (int): a valid task ID.

        Note:
            This will also remove it from the list of current tasks.

        """
        date, callback, args, kwargs = self.tasks.pop(task_id)
        if task_id in self.to_save:
            del self.to_save[task_id]

        self.save()
        callback(*args, **kwargs)

    def create_delays(self):
        """Create the delayed tasks for the persistent tasks.

        Note:
            This method should be automatically called when Evennia starts.

        """
        now = datetime.now()
        for task_id, (date, callbac, args, kwargs) in self.tasks.items():
            seconds = max(0, (date - now).total_seconds())
            deferLater(reactor, seconds, self.do_task, task_id)


# Create the soft singleton
TASK_HANDLER = TaskHandler()
