"""
Cooldown contrib module.

Evennia contrib - owllex, 2021

This contrib provides a simple cooldown handler that can be attached to any
typeclassed Object or Account. A cooldown is a lightweight persistent
asynchronous timer that you can query to see if it is ready.

Cooldowns are good for modelling rate-limited actions, like how often a
character can perform a given command.

Cooldowns are completely asynchronous and must be queried to know their
state. They do not fire callbacks, so are not a good fit for use cases
where something needs to happen on a specific schedule (use delay or
a TickerHandler for that instead).

See also the evennia documentation for command cooldowns
(https://github.com/evennia/evennia/wiki/Command-Cooldown) for more information
about the concept.

Installation:

To use, simply add the following property to the typeclass definition of any
object type that you want to support cooldowns. It will expose a new `cooldowns`
property that persists data to the object's attribute storage. You can set this
on your base `Object` typeclass to enable cooldown tracking on every kind of
object, or just put it on your `Character` typeclass.

By default the CooldownHandler will use the `cooldowns` property, but you can
customize this if desired by passing a different value for the db_attribute
parameter.

    from evennia.contrib.game_systems.cooldowns import Cooldownhandler
    from evennia.utils.utils import lazy_property

    @lazy_property
    def cooldowns(self):
        return CooldownHandler(self, db_attribute="cooldowns")

Example:

Assuming you've installed cooldowns on your Character typeclasses, you can use a
cooldown to limit how often you can perform a command. The following code
snippet will limit the use of a Power Attack command to once every 10 seconds
per character.

class PowerAttack(Command):
    def func(self):
        if self.caller.cooldowns.ready("power attack"):
            self.do_power_attack()
            self.caller.cooldowns.add("power attack", 10)
        else:
            self.caller.msg("That's not ready yet!")

"""

import math
import time


class CooldownHandler:
    """
    Handler for cooldowns. This can be attached to any object that supports DB
    attributes (like a Character or Account).

    A cooldown is a timer that is usually used to limit how often some action
    can be performed or some effect can trigger. When a cooldown is first added,
    it counts down from the amount of time provided back to zero, at which point
    it is considered ready again.

    Cooldowns are named with an arbitrary string, and that string is used to
    check on the progression of the cooldown. Each cooldown is tracked
    separately and independently from other cooldowns on that same object. A
    cooldown is unique per-object.

    Cooldowns are saved persistently, so they survive reboots. This module does
    not register or provide callback functionality for when a cooldown becomes
    ready again. Users of cooldowns are expected to query the state of any
    cooldowns they are interested in.

    Methods:
    - ready(name): Checks whether a given cooldown name is ready.
    - time_left(name): Returns how much time is left on a cooldown.
    - add(name, seconds): Sets a given cooldown to last for a certain
        amount of time. Until then, ready() will return False for that
        cooldown name. set() is an alias.
    - extend(name, seconds): Like add(), but adds more time to the given
        cooldown if it already exists. If it doesn't exist yet, calling
        this is equivalent to calling add().
    - reset(cooldown): Resets a given cooldown, causing ready() to return
        True for that cooldown immediately.
    - clear(): Resets all cooldowns.
    """

    __slots__ = ("data", "db_attribute", "obj")

    def __init__(self, obj, db_attribute="cooldowns"):
        if not obj.attributes.has(db_attribute):
            obj.attributes.add(db_attribute, {})

        self.data = obj.attributes.get(db_attribute)
        self.obj = obj
        self.db_attribute = db_attribute
        self.cleanup()

    @property
    def all(self):
        """
        Returns a list of all keys in this object.
        """
        return list(self.data.keys())

    def ready(self, *args):
        """
        Checks whether all of the provided cooldowns are ready (expired). If a
        requested cooldown does not exist, it is considered ready.

        Args:
            *args (str): One or more cooldown names to check.
        Returns:
            bool: True if each cooldown has expired or does not exist.
        """
        return self.time_left(*args, use_int=True) <= 0

    def time_left(self, *args, use_int=False):
        """
        Returns the maximum amount of time left on one or more given cooldowns.
        If a requested cooldown does not exist, it is considered to have 0 time
        left.

        Args:
            *args (str): One or more cooldown names to check.
            use_int (bool): True to round the return value up to an int,
                False (default) to return a more precise float.
        Returns:
            float or int: Number of seconds until all provided cooldowns are
                ready. Returns 0 if all cooldowns are ready (or don't exist.)
        """
        now = time.time()
        cooldowns = [self.data[x] - now for x in args if x in self.data]
        if not cooldowns:
            return 0 if use_int else 0.0
        left = max(max(cooldowns), 0)
        return math.ceil(left) if use_int else left

    def add(self, cooldown, seconds):
        """
        Adds/sets a given cooldown to last for a specific amount of time.

        If this cooldown already exits, this call replaces it.

        Args:
            cooldown (str): The name of the cooldown.
            seconds (float or int): The number of seconds before this cooldown
                is ready again.
        """
        now = time.time()
        self.data[cooldown] = now + (max(seconds, 0) if seconds else 0)

    set = add

    def extend(self, cooldown, seconds):
        """
        Adds a specific amount of time to an existing cooldown.

        If this cooldown is already ready, this is equivalent to calling set. If
        the cooldown is not ready, it will be extended by the provided duration.

        Args:
            cooldown (str): The name of the cooldown.
            seconds (float or int): The number of seconds to extend this cooldown.
        Returns:
            float: The number of seconds until the cooldown will be ready again.
        """
        time_left = self.time_left(cooldown) + (seconds if seconds else 0)
        self.set(cooldown, time_left)
        return max(time_left, 0)

    def reset(self, cooldown):
        """
        Resets a given cooldown.

        Args:
            cooldown (str): The name of the cooldown.
        """
        if cooldown in self.data:
            del self.data[cooldown]

    def clear(self):
        """
        Resets all cooldowns.
        """
        self.data.clear()

    def cleanup(self):
        """
        Deletes all expired cooldowns. This helps keep attribute storage
        requirements small.
        """
        now = time.time()
        cooldowns = dict(self.data)
        keys = [x for x in cooldowns.keys() if cooldowns[x] - now < 0]
        if keys:
            for key in keys:
                del cooldowns[key]
            self.obj.attributes.add(self.db_attribute, cooldowns)
            self.data = self.obj.attributes.get(self.db_attribute)
