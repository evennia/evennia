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

Installation:

To use, simply add the following property to the typeclass definition of
any object type that you want to support cooldowns. It will expose a
new `cooldowns` property that persists data to the object's attribute
storage. You can set this on your base `Object` typeclass to enable cooldown
tracking on every kind of object, or just put it on your `Character`
typeclass.

By default the CooldownHandler will use the `cooldowns` property, but you
can customize this if desired by passing a different value for the
db_attribute parameter.

    from evennia.contrib.cooldowns import Cooldownhandler
    from evennia.utils.utils import lazy_property

    @lazy_property
    def cooldowns(self):
        return CooldownHandler(self, db_attribute="cooldowns")
"""

import math
import time


class CooldownHandler:
    """
    Handler for cooldowns. This can be attached to any object that
    supports DB attributes (like a Character or Account).

    A cooldown is a timer that is usually used to limit how often
    some action can be performed or some effect can trigger. When a
    cooldown is first set, it counts down from the amount of time
    provided back to zero, at which point it is considered ready again.

    Cooldowns are named with an arbitrary string, and that string is used
    to check on the progression of the cooldown. Each cooldown is tracked
    separately and independently.

    Cooldowns are saved persistently, so they survive reboots. This
    module does not register or provide callback functionality for when
    a cooldown becomes ready again. Users of cooldowns are expected to
    query the state of any cooldowns they are interested in.

    Methods:
    - ready(name): Checks whether a given cooldown name is ready.
    - time_left(name): Returns how much time is left on a cooldown.
    - set(name, seconds): Sets a given cooldown to last for a certain
        amount of time. Until then, ready() will return False for that
        cooldown name.
    - extend(name, seconds): Like set, but adds time to the given
        cooldown name. If it doesn't exist yet, calling this is equivalent
        to calling set.
    - reset(cooldown): Resets a given cooldown, causing ready() to return
        True for that cooldown immediately.
    - clear(): Resets all cooldowns.
    """

    def __init__(self, obj, db_attribute="cooldowns"):
        if not obj.attributes.has(db_attribute):
            obj.attributes.add(db_attribute, {})

        self.data = obj.attributes.get(db_attribute)
        self.cleanup()

    @property
    def all(self):
        """
        Returns a list of all keys in this object.
        """
        return list(self.data.keys())

    def ready(self, *args):
        """
        Checks whether all of the provided cooldowns are ready (expired).
        If a requested cooldown does not exist, it is considered ready.

        Args:
            any (str): One or more cooldown names to check.
        Returns:
            (bool): True if each cooldown has expired or does not exist.
        """
        return self.time_left(*args) <= 0

    def time_left(self, *args):
        """
        Returns the maximum amount of time left on one or more given
        cooldowns. If a requested cooldown does not exist, it is
        considered to have 0 time left.

        Args:
            any (str): One or more cooldown names to check.
        Returns:
            (int): Number of seconds until all provided cooldowns are
                ready. Returns 0 if all cooldowns are ready (or don't
                exist.)
        """
        now = time.time()
        cooldowns = [self.data[x] - now for x in args if x in self.data]
        if not cooldowns:
            return 0
        return math.ceil(max(max(cooldowns), 0))

    def set(self, cooldown, seconds):
        """
        Sets a given cooldown to last for a specific amount of time.

        If this cooldown is already set, this replaces it.

        Args:
            cooldown (str): The name of the cooldown.
            seconds (int): The number of seconds before this cooldown is
                ready again.
        """
        now = time.time()
        self.data[cooldown] = int(now) + (max(seconds, 0) if seconds else 0)

    def extend(self, cooldown, seconds):
        """
        Adds a specific amount of time to an existing cooldown.

        If this cooldown is already ready, this is equivalent to calling
        set. If the cooldown is not ready, it will be extended by the
        provided duration.

        Args:
            cooldown (str): The name of the cooldown.
            seconds (int): The number of seconds to extend this cooldown.
        """
        time_left = self.time_left(cooldown)
        self.set(cooldown, time_left + (seconds if seconds else 0))

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
        for cooldown in list(self.data.keys()):
            del self.data[cooldown]

    def cleanup(self):
        """
        Deletes all expired cooldowns. This helps keep attribute storage
        requirements small.
        """
        now = time.time()
        keys = [x for x in self.data.keys() if self.data[x] - now < 0]
        for key in keys:
            del self.data[key]
