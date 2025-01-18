"""
Helper to handle on-demand requests, allowing a system to change state only when a player or system
actually needs the information. This is a very efficient way to handle gradual changes, requiring
not computer resources until the state is actually needed.

For example, consider a flowering system, where a seed sprouts, grows and blooms over a certain
time.  One _could_ implement this with e.g. a Script or a ticker that gradually moves the flower
along its stages of growth. But what if that flower is in a remote location, and no one is around to
see it?  You are then wasting computational resources on something that no one is looking at.

The truth is that most of the time, players are not looking at most of the things in the game. They
_only_ need to know about which state the flower is in when they are actually looking at it, or
when they are in the same room as it (so it can be incorporated in the room description). This is
where on-demand handling comes in.

This is the basic principle, using the flowering system as an example.

1. Someone plants a seed in a room (could also be automated). The seed is in a "seedling" state.
    We store the time it was planted (this is the important bit).
2. A player enters the room or looks at the plant. We check the time it was planted, and calculate
  how much time has passed since it was planted. If enough time has passed, we change the state to
  "sprouting" and probably change its description to reflect this.
3. If a player looks at the plant and not enough time has passed, it keeps the last updated state.
4. Eventually, it will be bloom time, and the plant will change to a "blooming" state when the
   player looks.
5. If no player ever comes around to look at the plant, it will never change state, and if they show
   up after a long time, it may not show as a "wilted" state or be outright deleted when observed,
   since too long time has passed and the plant has died.

With a system like this you could have growing plants all over your world and computing usage would
only scale by how many players you have exploring your world. The players will not know the
difference between this and a system that is always running, but your server will thank you.

There is only one situation where this system is not ideal, and that is when a player should be
informed of the state change _even if they perform no action_. That is, even if they are just idling
in the room, they should get a message like 'the plant suddenly blooms' (or, more commonly, for
messages like 'you are feeling hungry'). For this you still probably need to use one of Evennia's
built-in timers or tickers instead. But most of the time you should really consider using on-demand
handling instead.

## Usage

```python

from evennia import ON_DEMAND_HANDLER

# create a new on-demand task

flower = create_object(Flower, key="rose")

ON_DEMAND_HANDLER.add_task(
    flower, category="flowering",
    stages={0: "seedling", 120: "sprouting",
            300: "blooming", 600: "wilted", 700: "dead"})

# later, when we want to check the state of the plant (e.g. in a command),

state = ON_DEMAND_HANDLER.get_stage("flowering", last_checked=plant.planted_time)

```


"""

from evennia.server.models import ServerConfig
from evennia.utils import logger
from evennia.utils.utils import is_iter

_RUNTIME = None

ON_DEMAND_HANDLER = None
ONDEMAND_HANDLER_SAVE_NAME = "on_demand_timers"


class OnDemandTask:
    """
    Stores information about an on-demand task.

    Default property:
    - `default_stage_function (callable)`: This is called if no stage function is given in the
       stages dict.  This is meant for changing the task itself (such as restarting it). Actual
       game code should be handled elsewhere, by checking this task. See the `stagefunc_*` static
       methods for examples of how to manipulate the task when a stage is reached.

    """

    # useful stage-functions. Use with OnDemandTask.endfunc_stop etc

    @staticmethod
    def runtime():
        """
        Wraps the gametime.runtime() function.

        Need to import here to avoid circular imports during server reboot.
        It's a callable to allow easier unit testing.

        """
        global _RUNTIME
        if not _RUNTIME:
            from evennia.utils.gametime import runtime as _RUNTIME
        return _RUNTIME()

    @staticmethod
    def stagefunc_loop(task, **kwargs):
        """
        Attach this to the last stage to have the task start over from
        the beginning

        Example:
            stages = {0: "seedling", 120: "flowering", 300: "dead", ("_loop",
            OnDemandTask.stagefunc_loop)}

            Note that the "respawn" state will never actually be visible as a state to
            the user, instead once it reaches this state, it will *immediately* loop
            and the new looped state will be shown and returned to the user. So it
            can an idea to mark that end state with a `_` just to indicate this fact.

        """

        now = OnDemandTask.runtime()
        original_start_time = (
            task.start_time
        )  # this can be set on start or previous call of this func
        dts = list(task.stages.keys())
        total_dt = max(dts) - min(dts)

        # figure out how many times we've looped since last start-time was set
        task.iterations += (now - original_start_time) // total_dt
        # figure out how far we are into the current loop.
        current_loop_time = (now - original_start_time) % total_dt
        # We need to adjust the start_time to the start of the current loop
        task.start_time = now - current_loop_time

    @staticmethod
    def stagefunc_bounce(task, **kwargs):
        """
        This endfunc will have the task reverse direction and go through the stages in
        reverse order. This stage-function must be placed at both 'ends' of the stage sequence
        for the bounce to continue indefinitely.

        Example:
            stages = {0: ("cool", OnDemandTask.stagefunc_bounce),
                      50: "lukewarm",
                      150: "warm",
                      300: "hot",
                      300: ("HOT!", OnDemandTask.stagefunc_bounce)}

        """
        now = OnDemandTask.runtime()
        original_start_time = (
            task.start_time
        )  # this can be set on start or previous call of this func
        dts = list(task.stages.keys())
        max_dt = max(dts)
        total_dt = max_dt - min(dts)
        task.iterations += (now - original_start_time) // total_dt
        current_loop_time = (now - original_start_time) % total_dt
        task.start_time = now - current_loop_time

        if task.iterations > 0:
            # reverse the stages
            stages = task.stages
            task.stages = {abs(k - max_dt): v for k, v in sorted(stages.items())}

    # default fallback stage function. This is called if no stage function is given in the stages
    # dict.
    default_stage_function = None

    def __init__(self, key, category, stages=None, autostart=True):
        """
        Args:
            key (str): A unique identifier for the task.
            stages (dict, optional): A dictionary `{dt: str}` or `{int or float: (str, callable)}`
                of time-deltas (in seconds) and the stage name they represent. If the value is a
                tuple, the first element is the name of the stage and the second is a callable
                that will be called when that stage is *first* reached. Warning: This callable
                is *only* triggered if the stage is actually checked/retrieved while the task is
                in that stage checks - it's _not_ guaranteed to be called, even if the task
                time-wise goes through all its stages. Each callable must be picklable (so normally
                it should be a stand-alone function), and takes one argument - this OnDemandTask,
                which it can be modified in-place as needed.  This can be used to loop a task or do
                other changes to the task.
            autostart (bool, optional): If `last_checked` is `None`, and this is `False`, then the
                time will not start counting until the first call of `get_dt` or `get_stage`. If
                `True`, creating the task will immediately make a hidden check and start the timer.

        Examples:

           stages = {0: "seedling",
                     120: "sprouting",
                     300: "blooming",
                     600: "wilted",
                     700: "dead"
                    }

        """
        self.key = key
        self.category = category
        self.start_time = None
        self.last_stage = None
        self.iterations = 0  # only used with looping staging functions

        self.stages = None
        self.stages_by_name = None

        if isinstance(stages, dict):
            # sort the stages by ending time, inserting each state as {dt: (statename, callable)}
            _stages = {}
            for dt, tup in stages.items():
                # validate the input
                if not isinstance(dt, (int, float)):
                    raise ValueError(
                        "Each stage must given as a time-delta in seconds (int or float)."
                    )
                if is_iter(tup):
                    if len(tup) != 2:
                        raise ValueError(
                            "Each stage must be a tuple (name, callable) or a name-string."
                        )
                    if not callable(tup[1]):
                        raise ValueError(
                            "The second element of each stage-tuple must be a callable."
                        )
                else:
                    tup = (tup, None)
                _stages[dt] = tup

            self.stages = {dt: tup for dt, tup in sorted(_stages.items(), reverse=True)}
            self.stages_by_name = {tup[0]: dt for dt, tup in self.stages.items()}

        self.check(autostart=autostart)

    def __str__(self):
        """Note that we don't check the state here"""
        # we visualize stages with ascending key order
        dt, stage = self.check(autostart=False)
        return f"OnDemandTask({self.key}[{self.category}] (dt={dt}s), stage={stage})"

    def __eq__(self, other):
        if not isinstance(other, OnDemandTask):
            return False
        return (self.key, self.category) == (other.key, other.category)

    def check(self, autostart=True, **kwargs):
        """
        Check the current stage of the task and return the time-delta to the next stage.

        Keyword Args:
            autostart (bool, optional): If this is set, and the task has not been started yet,
                it will be started by this check. This is mainly used internally.
            **kwargs: Will be passed to the stage function, if one is called.

        Returns:
            tuple: A tuple (dt, stage) where `dt` is the time-delta (in seconds) since the test
            started (or since it started its latest iteration). and `stage` is the name of the
            current stage. If no stages are defined, `stage` will always be `None`. Use `get_dt` and
            `get_stage` to get only one of these values.

        """

        def _find_stage(delta_dt, _rerun=False):
            if not self.stages:
                return None

            for dt, (stage, stage_func) in self.stages.items():
                if delta_dt < dt:
                    continue

                if autostart and stage != self.last_stage and not _rerun:
                    self.last_stage = stage

                    if stage_func:
                        try:
                            stage_func(self, **kwargs)
                        except Exception as err:
                            logger.log_trace(
                                f"Error getting stage of on-demand task {self} "
                                f"(last_stage: {self.last_stage}, trying to call stage-func "
                                f"{stage_func}: {err}"
                            )
                        else:
                            # rerun the check in case the endfunc changed things
                            return _find_stage(delta_dt, _rerun=True)
                return stage

        def _find_dt(self, autostart=False):
            if self.start_time is None:
                if autostart:
                    # start timer
                    self.start_time = now
                dt = 0
            else:
                dt = now - self.start_time
            return dt

        now = OnDemandTask.runtime()

        dt = _find_dt(self, autostart=autostart)

        # we must always fetch the stage since a stage_func may fire
        stage = _find_stage(dt)

        # need to fetch dt again in case stage_func changed it
        dt = _find_dt(self, autostart=autostart)

        return dt, stage

    def get_dt(self, **kwargs):
        """
        Get the time-delta since last check.

        Returns:
            int: The time since the last check, or 0 if this is the first time the task is checked.
            **kwargs: Will be passed to the stage function, if one is called.

        """

        return self.check(autostart=True, **kwargs)[0]

    def set_dt(self, dt):
        """
        Set the time-delta since the task started manually. This allows you to 'cheat' the system
        and set the time manually. This is useful for testing or when a system manipulates the state
        somehow (like using a potion that speeds up the growth of a plant).

        Args:
            dt (int): The time-delta to set. This is an absolute value in seconds, same as returned
                by `get_dt`.

        Notes:
            Setting this will not on its own trigger any stage functions - this will only happen
            as normal, next time the state is checked and the stage is found to have changed.

        """
        self.start_time = OnDemandTask.runtime() - dt

    def get_stage(self, **kwargs):
        """
        Get the current stage of the task. If no stage was given, this will return `None` but
        still update the last_checked time.

        Returns:
            str or None: The current stage of the task, or `None` if no stages are set.
            **kwargs: Will be passed to the stage function, if one is called.

        """
        return self.check(autostart=True, **kwargs)[1]

    def set_stage(self, stage=None):
        """
        Set the stage of the task manually. This allows you to 'cheat' the system and set the stage
        manually. This is useful for testing or when a system manipulates the state somehow (like
        using a potion that speeds up the growth of a plant). The given stage must be previously
        created for the given task. If task has no stages, this will do nothing.

        Args:
            stage (str, optional): The stage to set. If `None`, the task will be reset to its
                initial (first) state.

        Notes:
            Setting this will not on its own trigger any stage functions - this will only happen
            as normal, next time the state is checked and the stage is found to have changed.

        """
        if not self.stages:
            return

        if stage is None:
            self.start_time = OnDemandTask.runtime() - min(self.stages.keys())
        elif stage in self.stages_by_name:
            self.start_time = OnDemandTask.runtime() - self.stages_by_name[stage]


class OnDemandHandler:
    """
    A singleton handler for managing on-demand state changes. Its main function is to persistently
    track the time (in seconds) between a state change and the next. How you make use of this
    information is up to your particular system.

    Contrary to just using the `time` module, this will also account for server restarts.

    """

    def __init__(self):
        self.tasks = dict()

    def load(self):
        """
        Load the on-demand timers from ServerConfig storage.

        This should be automatically called when Evennia starts.

        """
        self.tasks = dict(ServerConfig.objects.conf(ONDEMAND_HANDLER_SAVE_NAME, default=dict))

    def save(self):
        """
        Save the on-demand timers to ServerConfig storage. Should be called when Evennia shuts down.

        """
        for key, category in list(self.tasks.keys()):
            # in case an object was used for categories, and were since deleted, drop the task
            if hasattr(category, "id") and category.id is None:
                self.tasks.pop((key, category))
        ServerConfig.objects.conf(ONDEMAND_HANDLER_SAVE_NAME, self.tasks)

    def _build_key(self, key, category):
        """
        Build a unique key for the task.

        Args:
            key (str, callable, OnDemandTask or Object): The task key. If callable, it will be
                called without arguments. If an Object, will be converted to a string. If
                an `OnDemandTask`, then all other arguments are ignored and the task will be used
                to build the internal storage key.
            category (str or callable): The task category. If callable, it will be called without
                arguments.

        Returns:
            tuple (str, str or None): The unique key.

        """
        if isinstance(key, OnDemandTask):
            return (key.key, key.category)

        return (
            str(key() if callable(key) else key),
            category() if callable(category) else str(category) if category is not None else None,
        )

    def add(self, key, category=None, stages=None, autostart=True):
        """
        Add a new on-demand task.

        Args:
            key (str, callable, OnDemandTask or Object): A unique identifier for the task. If this
                is a callable, it will be called without arguments. If a db-Object, it will be
                converted to a string representation (which will include its (#dbref). If an
                `OnDemandTask`, then all other arguments are ignored and the task is simply added
                as-is.
            category (str or callable, optional): A category to group the task under. If given, it
                must also be given when checking the task.
            stages (dict, optional): A dictionary {dt: str}, of time-deltas (in seconds) and the
                stage which should be entered after that much time has passed.  autostart (bool,
            optional): If `True`, creating the task will immediately make a hidden
                check and start the timer.

        Returns:
            OnDemandTask: The created task (or the same that was added, if given an `OnDemandTask`
                as a `key`).  Use `task.get_dt()` and `task.get_stage()` to get data from it
                manually.

        """
        if isinstance(key, OnDemandTask):
            self.tasks[self._build_key(key.key, key.category)] = key
            return key
        task = OnDemandTask(key, category, stages, autostart=autostart)
        self.tasks[self._build_key(key, category)] = task
        return task

    def batch_add(self, *tasks):
        """
        Add multiple on-demand tasks at once.

        Args:
            *tasks (OnDemandTask): A set of OnDemandTasks to add.

        """
        for task in tasks:
            self.tasks[self._build_key(task.key, task.category)] = task

    def remove(self, key, category=None):
        """
        Remove an on-demand task.

        Args:
            key (str, callable, OnDemandTask or Object): The unique identifier for the task. If a
                callable, will be called without arguments. If an Object, will be converted to a
                string.  If an `OnDemandTask`, then all other arguments are ignored and the task
                will be used to identify the task to remove.
            category (str or callable, optional): The category of the task.

        Returns:
            OnDemandTask or None: The removed task, or `None` if no task was found.

        """
        return self.tasks.pop(self._build_key(key, category), None)

    def batch_remove(self, *keys, category=None):
        """
        Remove multiple on-demand tasks at once, potentially within a given category.

        Args:
            *keys (str, callable, OnDemandTask or Object): The unique identifiers for the tasks. If
                a callable, will be called without arguments. If an Object, will be converted to a
                string. If an `OnDemandTask`, then all other arguments are ignored and the task will
                be used to identify the task to remove.
            category (str or callable, optional): The category of the tasks.

        """
        for key in keys:
            self.remove(key, category=category)

    def all(self, category=None, all_on_none=True):
        """
        Get all on-demand tasks.

        Args:
            category (str, optional): The category of the tasks.
            all_on_none (bool, optional): Determines what to return if `category` is `None`.
                If `True`, all tasks will be returned. If `False`, only tasks without a category
                will be returned.

        Returns:
            dict: A dictionary of all on-demand task, on the form `{(key, category): task), ...}`.
            Use `task.get_dt()` or `task.get_stage()` to get the time-delta or stage of each task
            manually.

        """
        if category is None and all_on_none:
            # return all
            return self.tasks

        # filter by category (treat no-category as its own category)
        return {keytuple: task for keytuple, task in self.tasks.items() if keytuple[1] == category}

    def clear(self, category=None, all_on_none=True):
        """
        Clear all on-demand tasks.

        Args:
            category (str, optional): The category of the tasks to clear. What `None` means is
                determined by the `all_on_none` kwarg.
            all_on_none (bool, optional): Determines what to clear if `category` is `None`. If
                `True`, clear all tasks, if `False`, only clear tasks with no category.

        """
        if category is None and all_on_none:
            # clear all
            self.tasks = {}

        # filter and clear only those matching the category
        self.tasks = {
            keytuple: task for keytuple, task in self.tasks.items() if keytuple[1] != category
        }

    def get(self, key, category=None):
        """
        Get an on-demand task. This will _not_ check it.

        Args:
            key (str, callable, OnDemandTask or Object): The unique identifier for the task. If a
                callable, will be called without arguments. If an Object, will be converted to a
                string.  If an `OnDemandTask`, then all other arguments are ignored and the task
                will be used (only useful to check the task is the same).

            category (str, optional): The category of the task. If unset, this will only return
                tasks with no category.

        Returns:
            OnDemandTask or None: The task, or `None` if no task was found.

        """
        return self.tasks.get(self._build_key(key, category))

    def get_dt(self, key, category=None, **kwargs):
        """
        Get the time-delta since the task started.

        Args:
            key (str, callable, OnDemandTask or Object): The unique identifier for the task. If a
                callable, will be called without arguments. If an Object, will be converted to a
                string.  If an `OnDemandTask`, then all other arguments are ignored and the task
                will be used to identify the task to get the time-delta from.
            **kwargs: Will be passed to the stage function, if one is called.

        Returns:
            int or None: The time since the last check, or `None` if no task was found.

        """
        task = self.get(key, category)
        return task.get_dt(**kwargs) if task else None

    def set_dt(self, key, category, dt):
        """
        Set the time-delta since the task started manually. This allows you to 'cheat' the system
        and set the time manually. This is useful for testing or when a system manipulates the state
        somehow (like using a potion that speeds up the growth of a plant).

        Args:
            key (str, callable, OnDemandTask or Object): The unique identifier for the task. If a
                callable, will be called without arguments. If an Object, will be converted to a
                string. If an `OnDemandTask`, then all other arguments are ignored and the task will
                be used to identify the task to set the time-delta for.
            category (str, optional): The category of the task.
            dt (int): The time-delta to set. This is an absolute value in seconds, same as returned
                by `get_dt`.

        Notes:
            Setting this will not on its own trigger any stage functions - this will only happen
            as normal, next time the state is checked and the stage is found to have changed.

        """
        task = self.get(key, category)
        if task:
            task.set_dt(dt)

    def get_stage(self, key, category=None, **kwargs):
        """
        Get the current stage of an on-demand task.

        Args:
            key (str, callable, OnDemandTask or Object): The unique identifier for the task. If a
                callable, will be called without arguments. If an Object, will be converted to a
                string.  If an `OnDemandTask`, then all other arguments are ignored and the task
                will be used to identify the task to get the stage from.
            category (str, optional): The category of the task.
            **kwargs: Will be passed to the stage function, if one is called.

        Returns:
            str or None: The current stage of the task, or `None` if no task was found.

        """
        task = self.get(key, category)
        return task.get_stage(**kwargs) if task else None

    def set_stage(self, key, category=None, stage=None):
        """
        Set the stage of an on-demand task manually. This allows you to 'cheat' the system and set
        the stage manually. This is useful for testing or when a system manipulates the state
        somehow (like using a potion that speeds up the growth of a plant). The given stage must
        be previously created for the given task. If task has no stages, this will do nothing.

        Args:
            key (str, callable, OnDemandTask or Object): The unique identifier for the task. If a
                callable, will be called without arguments. If an Object, will be converted to a
                string.  If an `OnDemandTask`, then all other arguments are ignored and the task
                will be used to identify the task to set the stage for.
            category (str, optional): The category of the task.
            stage (str, optional): The stage to set. If `None`, the task will be reset to its
                initial (first) state.

        Notes:
            Setting this will not on its own trigger any stage functions - this will only happen
            as normal, next time the state is checked and the stage is found to have changed.

        """
        task = self.get(key, category)
        if task:
            task.set_stage(stage)


# Create singleton
ON_DEMAND_HANDLER = OnDemandHandler()
