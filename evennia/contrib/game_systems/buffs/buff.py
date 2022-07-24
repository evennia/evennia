"""
Buffs - Tegiminis 2022

A buff is a timed object, attached to a game entity, that modifies values, triggers 
code, or both. It is a common design pattern in RPGs, particularly action games.

This contrib gives you a buff handler to apply to your objects, a buff class to extend them,
and a sample property class to show how to automatically check modifiers.

## Quick Start
Assign the handler to a property on the object, like so.

```python
@lazy_property
def buffs(self) -> BuffHandler:
    return BuffHandler(self)```

You may then call the handler to add or manipulate buffs.

### Customization

If you want to customize the handler, you can feed the constructor two arguments:
- `dbkey`: The string you wish to use as a key for the buff database. Defaults to "buffs". This allows you to keep separate buff pools - for example, "buffs" and "perks".
- `autopause`: If you want this handler to automatically pause certain buffs when its owning object is unpuppeted.

> IMPORTANT: If you enable autopausing, you MUST initialize the property in your object's
> `at_init` hook to cache. Otherwise, a hot reload can cause playtime buffs to not update properly
> on puppet/unpuppet. You have been warned!

Let's say you want another handler for an object, `perks`, which has a separate database and 
respects playtime buffs. You'd assign this new property as so:

```python
    @lazy_property
    def perks(self) -> BuffHandler:
        return BuffHandler(self, dbkey='perks', autopause=True)
```

And add `self.perks` to the object's `at_init`.

### Using the Handler

To actually make use of the handler, you still have to do some leg work.

#### Apply a Buff

Call the handler `add(BuffClass)` method. This requires a class reference, and also contains a number of 
optional arguments to customize the buff's duration, stacks, and so on. You can also store any arbitrary value 
in the buff's cache by passing a dictionary through the `to_cache` argument. This will not overwrite the normal
values on the cache.

```python
self.buffs.add(StrengthBuff)    # A single stack of StrengthBuff with normal duration
self.buffs.add(DexBuff, stacks=3, duration=60)  # Three stacks of DexBuff, with a duration of 60 seconds
self.buffs.add(ReflectBuff, to_cache={'reflect': 0.5})  # A single stack of ReflectBuff, with an extra cache value
```

Two important attributes on the buff are checked when the buff is applied: `refresh` and `unique`.
- `refresh` (default: True) determines if a buff's timer is refreshed when it is reapplied.
- `unique` (default: True) determines if the buff uses the buff's normal key (True) or one created with the key and the applier's dbref (False)

#### Modify

Call the handler `check(value, stat)` method wherever you want to see the modified value. 
This will return the value, modified by and relevant buffs on the handler's owner (identified by 
the `stat` string).

For example, let's say you want to modify how much damage you take. That might look something like this

```python
# The method we call to damage ourselves
def take_damage(self, source, damage):
    _damage = self.buffs.check(damage, 'taken_damage')
    self.db.health -= _damage
```

#### Trigger

Call the handler `trigger(triggerstring)` method wherever you want an event call. This 
will call the `at_trigger` hook method on all buffs with the relevant trigger.

For example, let's say you want to trigger a buff to "detonate" when you hit your target with an attack.
You'd write a buff with at least the following stats:

```python
triggers = ['take_damage']
def at_trigger(self, trigger, *args, **kwargs)
    self.owner.take_damage(100)
```

And then call `handler.trigger('take_damage')` in the method you use to take damage.

#### Tick

Ticking buffs are slightly special. They are similar to trigger buffs in that they run code, but instead of
doing so on an event trigger, they do so are a periodic tick. A common use case for a buff like this is a poison,
or a heal over time.

All you need to do to make a buff tick is ensure the `tickrate` is 1 or higher, and it has code in its `at_tick`
method. Once you add it to the handler, it starts ticking!

## Buffs

But wait! You still have to actually create the buffs you're going to be applying.

Creating a buff is very easy: extend BaseBuff into a new class, and fill in all the relevant buff details.
However, there are a lot of individual moving parts to a buff! Here's a step-through of the important stuff.

### Basics

Regardless of any mods or hook methods, all buffs have the following qualities:

- They have customizable `key`, `name`, and `flavor` strings.
- They can stack, if `maxstacks` is not equal to 1. If it's 0, the buff stacks forever. 
- They have a `duration`, and automatically clean up at the end of it (-1 for infinite duration, 0 to cleanup immediately).

### Modifiers

Buffs which have one or more Mod objects in them can modify stats. You can use the handler method to check all 
mods of a specific stat string and apply their modifications to the value; however, you are encouraged to use 
`check` in a getter/setter, for easy access.

Mod objects consist of only four values, assigned by the constructor in this order:

- `stat`: The stat you want to modify. When `check` is called, this string is used to find all the mods that are to be collected.
- `mod`: The modifier. Defaults are 'add' and 'mult'. Modifiers are calculated additively, and in standard arithmetic order (see `_calculate_mods` for more)
- `value`: How much value the modifier gives regardless of stacks
- `perstack`: How much value the modifier grants per stack, INCLUDING the first. (default: 0)

To add a mod to a buff, you do so in the buff definition, like this:
```python
def DamageBuff(BaseBuff):
    mods = [Mod('damage', 'add', 10)]
```

No mods applied to the value are permanent in any way. All calculations are done at
runtime, and the mod values are never stored anywhere except on the buff in question. In
other words: you don't need to track the origin of particular stat mods, and you
will never permanently change a stat modified by a trait buff. To remove the modification, simply
remove the buff off the object.

### Triggers

Buffs which have one or more strings in the `triggers` attribute can be triggered by events.

When the handler `trigger` method is called, it searches all buffs on the handler for any with a matching
trigger, then calls their `at_trigger` methods. You can tell which trigger is the one it fired with by the `trigger`
argument in the method.

```python 
def AmplifyBuff(BaseBuff):
    triggers = ['damage', 'heal'] 

    def at_trigger(self, trigger, **kwargs):
        if trigger == 'damage': print('Damage trigger called!')
        if trigger == 'heal': print('Heal trigger called!')
```

### Ticking

A buff with ticking isn't much different than one which triggers. You're still executing arbitrary code off
the buff class. The main thing is you need to have a `tickrate` higher than 1.
```python
# this buff will tick 6 times between application and cleanup.
duration = 30
tickrate = 5
def at_tick(self, initial, **kwargs):
    self.owner.take_damage(10)
```
It's important to note the buff always ticks once when applied. For this first tick only, `initial` will be True 
in the `at_tick` hook method.

### Extras

Buffs have a grab-bag of extra functionality to make your life easier!

You can restrict whether or not the buff will check or trigger through defining the `conditional` hook. As long
as it returns a "truthy" value, the buff will apply itself. This is useful for making buffs dependent on game state - for
example, if you want a buff that makes the player take more damage when they are on fire.

```python
def conditional(self, *args, **kwargs):
    if self.owner.buffs.get_by_type(FireBuff): return True
    return False
```

There are a number of helper methods. If you have a buff instance - for example, because you got the buff with
`handler.get(key)` - you can `pause`, `unpause`, `remove`, `dispel`, etc.

Finally, if your handler has `autopause` enabled, any buffs with truthy `playtime` value will automatically pause
and unpause when the object the handler is attached to is puppetted or unpuppetted. This even works with ticking buffs,
although if you have less than 1 second of tick duration remaining, it will round up to 1s.

If you want more control over this process, you can comment out the signal subscriptions on the handler and move the autopause logic
to your object's at_pre/post_puppet/unpuppet hooks.

### How Does It Work?

Buffs are stored in two parts alongside each other in the cache: a reference to the buff class, and as mutable data.
You can technically store any information you like in the cache; by default, it's all the basic timing and event
information necessary for the system to run. When the buff is instanced, this cache is fed to the constructor

When you use the handler to get a buff, you get an instanced version of that buff created from these two parts, or
a dictionary of these buffs in the format of {buffkey: instance}. Buffs are only instanced as long as is necessary to
run methods on them.

## Context

You may have noticed that almost every important handler method optionally accepts a `context` dictionary.

Context is an important concept for this handler. Every method which modifies, triggers, or checks a buff passes this 
dictionary (default: empty) to the buff hook methods as keyword arguments (**kwargs). It is used for nothing else. This allows you to make those 
methods "event-aware" by storing relevant data in the dictionary you feed to the method.

For example, let's say you want a "thorns" buff which damages enemies that attack you. Let's take our `take_damage` method
and add a context to the mix.

```
def take_damage(attacker, damage):
    context = {'attacker': attacker, 'damage': damage}
    _damage = self.buffs.check(damage, 'taken_damage', context=context)
    self.buffs.trigger('taken_damage', context=context)
    self.db.health -= _damage
```
Now we use the values that context passes to the buff kwargs to customize our logic.
```
triggers = ['taken_damage']
# This is the hook method on our thorns buff
def at_trigger(self, trigger, attacker=None, damage=0, **kwargs):
    if not attacker: return
    attacker.db.health -= damage * 0.2
```
Apply the buff, take damage, and watch the thorns buff do its work!
"""

from random import random
import time
from evennia.server import signals
from evennia.utils import utils, search
from evennia.typeclasses.attributes import AttributeProperty


class BaseBuff:
    key = "template"  # The buff's unique key. Will be used as the buff's key in the handler
    name = "Template"  # The buff's name. Used for user messaging
    flavor = "Template"  # The buff's flavor text. Used for user messaging
    visible = True  # If the buff is considered "visible" to the "view" method

    triggers = []  # The effect's trigger strings, used for functions.

    handler = None
    start = 0
    # Default buff duration; -1 or lower for permanent, 0 for "instant" (removed immediately)
    duration = -1

    playtime = False  # Does this buff autopause when owning object is unpuppeted?

    refresh = True  # Does the buff refresh its timer on application?
    unique = True  # Does the buff overwrite existing buffs with the same key on the same target?
    maxstacks = 1  # The maximum number of stacks the buff can have. If >1, this buff will stack.
    stacks = 1  # If >1, used as the default when applying this buff
    tickrate = 0  # How frequent does this buff tick, in seconds (cannot be lower than 1)

    mods = []  # List of mod objects. See Mod class below for more detail
    cache = {}

    @property
    def ticknum(self):
        """Returns how many ticks this buff has gone through as an integer."""
        x = (time.time() - self.start) / self.tickrate
        return int(x)

    @property
    def owner(self):
        """Return this buff's owner (the object its handler is attached to)"""
        if not self.handler:
            return None
        return self.handler.owner

    @property
    def ticking(self) -> bool:
        """Returns if this buff ticks or not (tickrate => 1)"""
        return self.tickrate >= 1

    @property
    def stacking(self) -> bool:
        """Returns if this buff stacks or not (maxstacks > 1)"""
        return self.maxstacks > 1

    def __init__(self, handler, buffkey, cache) -> None:
        """
        Args:
            handler:    The handler this buff is attached to
            buffkey:    The key this buff uses on the cache
            cache:      The cache dictionary (what you get if you use `handler.buffcache.get(key)`)"""
        self.handler: BuffHandler = handler
        self.buffkey = buffkey
        # Cache assignment
        self.cache = cache
        # Default system cache values
        self.start = self.cache.get("start")
        self.duration = self.cache.get("duration")
        self.prevtick = self.cache.get("prevtick")
        self.paused = self.cache.get("paused")
        self.stacks = self.cache.get("stacks")
        self.source = self.cache.get("source")

    def conditional(self, *args, **kwargs):
        """Hook function for conditional evaluation.

        This must return True for a buff to apply modifiers, trigger effects, or tick."""
        return True

    # region helper methods
    def remove(self, loud=True, expire=False, context=None):
        """Helper method which removes this buff from its handler. Use dispel if you are dispelling it instead.

        Args:
            loud:   (optional) Whether to call at_remove or not (default: True)
            expire: (optional) Whether to call at_expire or not (default: False)
            delay:  (optional) How long you want to delay the remove call for
            context:    (optional) A dictionary you wish to pass to the at_remove/at_expire method as kwargs"""
        if not context:
            context = {}
        self.handler.remove(self.buffkey, loud=loud, expire=expire, context=context)

    def dispel(self, loud=True, delay=0, context=None):
        """Helper method which dispels this buff (removes and calls at_dispel).

        Args:
            loud:   (optional) Whether to call at_remove or not (default: True)
            delay:  (optional) How long you want to delay the remove call for
            context:    (optional) A dictionary you wish to pass to the at_remove/at_dispel method as kwargs"""
        if not context:
            context = {}
        self.handler.remove(self.buffkey, loud=loud, dispel=True, delay=delay, context=context)

    def pause(self, context=None):
        """Helper method which pauses this buff on its handler.

        Args:
            context:    (optional) A dictionary you wish to pass to the at_pause method as kwargs"""
        if not context:
            context = {}
        self.handler.pause(self.buffkey, context)

    def unpause(self, context=None):
        """Helper method which unpauses this buff on its handler.

        Args:
            context:    (optional) A dictionary you wish to pass to the at_unpause method as kwargs"""
        if not context:
            context = {}
        self.handler.unpause(self.buffkey, context)

    def reset(self):
        """Resets the buff start time as though it were just applied; functionally identical to a refresh"""
        self.handler.buffcache[self.buffkey]["start"] = time.time()

    # endregion

    # region hook methods
    def at_apply(self, *args, **kwargs):
        """Hook function to run when this buff is applied to an object."""
        pass

    def at_remove(self, *args, **kwargs):
        """Hook function to run when this buff is removed from an object."""
        pass

    def at_dispel(self, *args, **kwargs):
        """Hook function to run when this buff is dispelled from an object (removed by someone other than the buff holder)."""
        pass

    def at_expire(self, *args, **kwargs):
        """Hook function to run when this buff expires from an object."""
        pass

    def at_pre_check(self, *args, **kwargs):
        """Hook function to run before this buff's modifiers are checked."""
        pass

    def at_post_check(self, *args, **kwargs):
        """Hook function to run after this buff's mods are checked."""
        pass

    def at_trigger(self, trigger: str, *args, **kwargs):
        """Hook for the code you want to run whenever the effect is triggered.
        Passes the trigger string to the function, so you can have multiple
        triggers on one buff."""
        pass

    def at_tick(self, initial: bool, *args, **kwargs):
        """Hook for actions that occur per-tick, a designer-set sub-duration.
        `initial` tells you if it's the first tick that happens (when a buff is applied)."""
        pass

    def at_pause(self, *args, **kwargs):
        """Hook for when this buff is paused"""
        pass

    def at_unpause(self, *args, **kwargs):
        """Hook for when this buff is unpaused."""
        pass

    # endregion


class Mod:
    """A single stat mod object. One buff or trait can hold multiple mods, for the same or different stats."""

    stat = "null"  # The stat string that is checked to see if this mod should be applied
    value = 0  # Buff's value
    perstack = 0  # How much additional value is added to the buff per stack
    modifier = "add"  # The modifier the buff applies. 'add' or 'mult'

    def __init__(self, stat: str, modifier: str, value, perstack=0.0) -> None:
        """
        Args:
            stat:       The stat the buff affects. Normally matches the object attribute name
            mod:        The modifier the buff applies. "add" for add/sub or "mult" for mult/div
            value:      The value of the modifier
            perstack:   How much is added to the base, per stack (including first)."""
        self.stat = stat
        self.modifier = modifier
        self.value = value
        self.perstack = perstack


class BuffHandler(object):

    ownerref = None
    dbkey = "buffs"
    autopause = False
    _owner = None

    def __init__(self, owner, dbkey=dbkey, autopause=autopause):
        """
        Args:
            owner:  The object this handler is attached to
            dbkey:  (optional) The string key of the db attribute to use for the buff cache
            autopause:  (optional) Whether this handler autopauses playtime buffs on owning object's unpuppet"""
        self.ownerref = owner.dbref
        self.dbkey = dbkey
        self.autopause = autopause
        if autopause:
            signals.SIGNAL_OBJECT_POST_UNPUPPET.connect(self._pause_playtime)
            signals.SIGNAL_OBJECT_POST_PUPPET.connect(self._unpause_playtime)

    # region properties
    @property
    def owner(self):
        """The object this handler is attached to."""
        if self.ownerref:
            _owner = search.search_object(self.ownerref)
        if _owner:
            return _owner[0]
        else:
            return None

    @property
    def buffcache(self):
        """The object attribute we use for the buff cache. Auto-creates if not present."""
        if not self.owner:
            return {}
        if not self.owner.attributes.has(self.dbkey):
            self.owner.attributes.add(self.dbkey, {})
        return self.owner.attributes.get(self.dbkey)

    @property
    def traits(self):
        """All buffs on this handler that modify a stat."""
        _t = {k: buff for k, buff in self.get_all().items() if buff.mods}
        return _t

    @property
    def effects(self):
        """All buffs on this handler that trigger off an event."""
        _e = {k: buff for k, buff in self.get_all().items() if buff.triggers}
        return _e

    @property
    def playtime(self):
        """All buffs on this handler that only count down during active playtime."""
        _pt = {k: buff for k, buff in self.get_all().items() if buff.playtime}
        return _pt

    @property
    def paused(self):
        """All buffs on this handler that are paused."""
        _p = {k: buff for k, buff in self.get_all().items() if buff.paused}
        return _p

    @property
    def expired(self):
        """All buffs on this handler that have expired (no duration or no stacks)."""
        _cache = self.all
        _e = {
            k: buff
            for k, buff in _cache.items()
            if not buff.paused
            if buff.duration > -1
            if buff.duration < time.time() - buff.start
        }
        _nostacks = {k: buff for k, buff in _cache.items() if buff.stacks <= 0}
        _e.update(_nostacks)
        return _e

    @property
    def visible(self):
        """All buffs on this handler that are visible."""
        _v = {k: buff for k, buff in self.get_all().items() if buff.visible}
        return _v

    @property
    def all(self):
        """Returns dictionary of instanced buffs equivalent to ALL buffs on this handler,
        regardless of state, type, or anything else."""
        _a = self.get_all()
        return _a

    # endregion

    # region methods
    def add(
        self,
        buff: BaseBuff,
        key: str = None,
        stacks=0,
        duration=None,
        source=None,
        to_cache=None,
        context=None,
        *args,
        **kwargs,
    ):

        """Add a buff to this object, respecting all stacking/refresh/reapplication rules. Takes
        a number of optional parameters to allow for customization.

        Args:
            buff:       The buff class type you wish to add
            key:        (optional) The key you wish to use for this buff; overrides defaults
            stacks:     (optional) The number of stacks you want to add, if the buff is stacking
            duration:   (optional) The amount of time, in seconds, you want the buff to last; overrides defaults
            source:     (optional) The source of this buff. (default: None)
            to_cache:   (optional) A dictionary to store in the buff's cache; does not overwrite default cache keys
            context:    (optional) A dictionary you wish to pass to the at_apply method as kwargs
        """
        if not isinstance(buff, type):
            raise ValueError
        if not context:
            context = {}
        b = {}
        _context = dict(context)
        if to_cache:
            b = dict(to_cache)
        if stacks < 1:
            stacks = min(1, buff.stacks)

        # Create the buff dict that holds a reference and all runtime information.
        b.update(
            {
                "ref": buff,
                "start": time.time(),
                "duration": buff.duration,
                "prevtick": time.time(),
                "paused": False,
                "stacks": stacks,
                "source": source,
            }
        )

        # Generate the buffkey from the object's dbref and the default buff key.
        # This is the actual key the buff uses on the dictionary
        buffkey = key
        if not buffkey:
            if source:
                mix = str(source.dbref).replace("#", "")
            elif not (buff.unique or buff.refresh) or not source:
                mix = str(random() * 10000)
            buffkey = buff.key if buff.unique is True else buff.key + mix

        # Rules for applying over an existing buff
        if buffkey in self.buffcache.keys():
            existing = dict(self.buffcache[buffkey])
            # Stacking
            if buff.maxstacks > 1:
                b["stacks"] = min(existing["stacks"] + stacks, buff.maxstacks)
            elif buff.maxstacks < 1:
                b["stacks"] = existing["stacks"] + stacks
            # Carrying over old arbitrary cache values
            cur_cache = {k: v for k, v in existing.items() if k not in b.keys()}
            b.update(cur_cache)
        # Setting overloaded duration
        if duration:
            b["duration"] = duration

        # Apply the buff!
        self.buffcache[buffkey] = b

        # Create the buff instance and run the on-application hook method
        instance: BaseBuff = buff(self, buffkey, b)
        instance.at_apply(**_context)
        if instance.ticking:
            tick_buff(self, buffkey, _context)

        # Clean up the buff at the end of its duration through a delayed cleanup call
        if b["duration"] > -1:
            utils.delay(b["duration"], self.cleanup, persistent=True)

    def remove(self, key, stacks=0, loud=True, dispel=False, expire=False, context=None):
        """Remove a buff or effect with matching key from this object. Normally calls at_remove,
        calls at_expire if the buff expired naturally, and optionally calls at_dispel. Can also
        remove stacks instead of the entire buff (still calls at_remove). Typically called via a helper method
        on the buff instance, or other methods on the handler.

        Args:
            key:        The buff key
            loud:       (optional) Calls at_remove when True. (default: True)
            dispel:     (optional) Calls at_dispel when True. (default: False)
            expire:     (optional) Calls at_expire when True. (default: False)
            context:    (optional) A dictionary you wish to pass to the at_remove/at_dispel/at_expire method as kwargs
        """
        if not context:
            context = {}
        if key not in self.buffcache:
            return None

        buff: BaseBuff = self.buffcache[key]
        instance: BaseBuff = buff["ref"](self, key, buff)

        if loud:
            if dispel:
                instance.at_dispel(**context)
            elif expire:
                instance.at_expire(**context)
            instance.at_remove(**context)

        del instance
        if not stacks:
            del self.buffcache[key]
        elif stacks:
            self.buffcache[key]["stacks"] -= stacks

    def remove_by_type(
        self,
        bufftype: BaseBuff,
        loud=True,
        dispel=False,
        expire=False,
        context=None,
    ):
        """Removes all buffs of a specified type from this object. Functionally similar to remove, but takes a type instead.

        Args:
            bufftype:   The buff class to remove
            loud:       (optional) Calls at_remove when True. (default: True)
            dispel:     (optional) Calls at_dispel when True. (default: False)
            expire:     (optional) Calls at_expire when True. (default: False)
            context:    (optional) A dictionary you wish to pass to the at_remove/at_dispel/at_expire method as kwargs
        """
        _remove = self.get_by_type(bufftype)
        if not _remove:
            return None
        self._remove_via_dict(_remove, loud, dispel, expire, context)

    def remove_by_source(
        self,
        source,
        loud=True,
        dispel=False,
        expire=False,
        context=None,
    ):
        """Removes all buffs from the specified source from this object. Functionally similar to remove, but takes a source instead.

        Args:
            source:     The source to search for
            loud:       (optional) Calls at_remove when True. (default: True)
            dispel:     (optional) Calls at_dispel when True. (default: False)
            expire:     (optional) Calls at_expire when True. (default: False)
            context:    (optional) A dictionary you wish to pass to the at_remove/at_dispel/at_expire method as kwargs
        """
        _remove = self.get_by_source(source)
        if not _remove:
            return None
        self._remove_via_dict(_remove, loud, dispel, expire, context)

    def remove_by_cachevalue(
        self,
        key,
        value=None,
        loud=True,
        dispel=False,
        expire=False,
        context=None,
    ):
        """Removes all buffs with the cachevalue from this object. Functionally similar to remove, but checks the buff's cache values instead.

        Args:
            key:         The key of the cache value to check
            value:      (optional) The value to match to. If None, merely checks to see if the value exists
            loud:       (optional) Calls at_remove when True. (default: True)
            dispel:     (optional) Calls at_dispel when True. (default: False)
            expire:     (optional) Calls at_expire when True. (default: False)
            context:    (optional) A dictionary you wish to pass to the at_remove/at_dispel/at_expire method as kwargs
        """
        _remove = self.get_by_cachevalue(key, value)
        if not _remove:
            return None
        self._remove_via_dict(_remove, loud, dispel, expire, context)

    def clear(self, loud=True, dispel=False, expire=False, context=None):
        """Removes all buffs on this handler"""
        cache = self.all
        self._remove_via_dict(cache, loud, dispel, expire, context)

    def get(self, key: str):
        """If the specified key is on this handler, return the instanced buff. Otherwise return None.
        You should delete this when you're done with it, so that garbage collection doesn't have to.

        Args:
            key:    The key for the buff you wish to get"""
        buff = self.buffcache.get(key)
        if buff:
            return buff["ref"](self, key, buff)
        else:
            return None

    def get_all(self):
        """Returns a dictionary of instanced buffs (all of them) on this handler in the format {buffkey: instance}"""
        _cache = dict(self.buffcache)
        return {k: buff["ref"](self, k, buff) for k, buff in _cache.items()}

    def get_by_type(self, buff: BaseBuff, to_filter=None):
        """Finds all buffs matching the given type.

        Args:
            buff:       The buff class to search for
            to_filter:  (optional) A dictionary you wish to slice. If not provided, uses the whole buffcache.

        Returns a dictionary of instanced buffs of the specified type in the format {buffkey: instance}."""
        _cache = self.get_all() if not to_filter else to_filter
        return {k: _buff for k, _buff in _cache.items() if isinstance(_buff, buff)}

    def get_by_stat(self, stat: str, context=None, to_filter=None):
        """Finds all buffs which contain a Mod object that modifies the specified stat.

        Args:
            stat:       The string identifier to find relevant mods
            context:    (optional) A dictionary you wish to pass to the conditional method as kwargs
            to_filter:  (optional) A dictionary you wish to slice. If not provided, uses the whole buffcache.

        Returns a dictionary of instanced buffs which modify the specified stat in the format {buffkey: instance}."""
        _cache = self.traits if not to_filter else to_filter
        if not _cache:
            return None
        if not context:
            context = {}

        buffs = {
            k: buff
            for k, buff in _cache.items()
            for m in buff.mods
            if m.stat == stat
            if not buff.paused
            if buff.conditional(**context)
        }
        return buffs

    def get_by_trigger(self, trigger: str, context=None, to_filter=None):
        """Finds all buffs with the matching string in their triggers.

        Args:
            trigger:    The string identifier to find relevant buffs
            context:    (optional) A dictionary you wish to pass to the conditional method as kwargs
            to_filter:  (optional) A dictionary you wish to slice. If not provided, uses the whole buffcache.

        Returns a dictionary of instanced buffs which fire off the designated trigger, in the format {buffkey: instance}."""
        _cache = self.effects if not to_filter else to_filter
        if not context:
            context = {}
        buffs = {
            k: buff
            for k, buff in _cache.items()
            if trigger in buff.triggers
            if not buff.paused
            if buff.conditional(**context)
        }
        return buffs

    def get_by_source(self, source, to_filter=None):
        """Find all buffs with the matching source.

        Args:
            source: The source you want to filter buffs by
            to_filter:  (optional) A dictionary you wish to slice. If not provided, uses the whole buffcache.

        Returns a dictionary of instanced buffs which came from the provided source, in the format {buffkey: instance}."""
        _cache = self.all if not to_filter else to_filter
        buffs = {k: buff for k, buff in _cache.items() if buff.source == source}
        return buffs

    def get_by_cachevalue(self, key, value=None, to_filter=None):
        """Find all buffs with a matching {key: value} pair in its cache. Allows you to search buffs by arbitrary cache values

        Args:
            key:    The key of the cache value to check
            value:  (optional) The value to match to. If None, merely checks to see if the value exists
            to_filter:  (optional) A dictionary you wish to slice. If not provided, uses the whole buffcache.

        Returns a dictionary of instanced buffs with cache values matching the specified value, in the format {buffkey: instance}."""
        _cache = self.all if not to_filter else to_filter
        if not value:
            buffs = {k: buff for k, buff in _cache.items() if buff.cache.get(key)}
        elif value:
            buffs = {k: buff for k, buff in _cache.items() if buff.cache.get(key) == value}
        return buffs

    def check(self, value: float, stat: str, loud=True, context=None, trigger=False):
        """Finds all buffs and perks related to a stat and applies their effects.

        Args:
            value:  The value you intend to modify
            stat:   The string that designates which stat buffs you want
            loud:   (optional) Call the buff's at_post_check method after checking (default: True)
            context: (optional) A dictionary you wish to pass to the at_pre_check/at_post_check methods as kwargs
            trigger: (optional) Trigger buffs with the `stat` string as well. (default: False)

        Returns the value modified by relevant buffs."""
        # Buff cleanup to make sure all buffs are valid before processing
        self.cleanup()

        # Find all buffs and traits related to the specified stat.
        if not context:
            context = {}
        applied = self.get_by_stat(stat, context)
        if not applied:
            return value
        for buff in applied.values():
            buff.at_pre_check(**context)

        # The final result
        final = self._calculate_mods(value, stat, applied)

        # Run the "after check" functions on all relevant buffs
        for buff in applied.values():
            buff: BaseBuff
            if loud:
                buff.at_post_check(**context)
            del buff

        # If you want to, also trigger buffs with the same stat string
        if trigger:
            self.trigger(stat, context)

        return final

    def trigger(self, trigger: str, context: dict = None):
        """Calls the at_trigger method on all buffs with the matching trigger.

        Args:
            trigger:    The string identifier to find relevant buffs. Passed to the at_trigger method.
            context:    (optional) A dictionary you wish to pass to the at_trigger method as kwargs
        """
        self.cleanup()
        _effects = self.get_by_trigger(trigger, context)
        if _effects is None:
            return None
        if not context:
            context = {}

        # Trigger all buffs whose trigger matches the trigger string
        for buff in _effects.values():
            buff: BaseBuff
            if trigger in buff.triggers and not buff.paused:
                buff.at_trigger(trigger, **context)

    def pause(self, key: str, context=None):
        """Pauses the buff. This excludes it from being checked for mods, triggered, or cleaned up. Used to make buffs 'playtime' instead of 'realtime'.

        Args:
            key:    The key for the buff you wish to pause
            context:    (optional) A dictionary you wish to pass to the at_pause method as kwargs
        """
        if key in self.buffcache.keys():
            # Mark the buff as paused
            buff = dict(self.buffcache[key])
            if buff["paused"]:
                return
            if not context:
                context = {}
            buff["paused"] = True

            # Math assignments
            current = time.time()  # Current Time
            start = buff["start"]  # Start
            duration = buff["duration"]  # Duration
            prevtick = buff["prevtick"]  # Previous tick timestamp
            tickrate = buff["ref"].tickrate  # Buff's tick rate

            # Original buff ending, and new duration
            end = start + duration  # End
            newduration = end - current  # New duration

            # Apply the new duration
            if newduration > 0:
                buff["duration"] = newduration
                if buff["ref"].ticking:
                    buff["tickleft"] = max(1, tickrate - (current - prevtick))
                self.buffcache[key] = buff
                instance: BaseBuff = buff["ref"](self, key, buff)
                instance.at_pause(**context)
            else:
                self.remove(key)
        return

    def unpause(self, key: str, context=None):
        """Unpauses a buff. This makes it visible to the various buff systems again.

        Args:
            key:    The key for the buff you wish to pause
            context:    (optional) A dictionary you wish to pass to the at_unpause method as kwargs"""
        if key in self.buffcache.keys():
            # Mark the buff as unpaused
            buff = dict(self.buffcache[key])
            if not buff["paused"]:
                return
            if not context:
                context = {}
            buff["paused"] = False

            # Math assignments
            tickrate = buff["ref"].tickrate
            if buff["ref"].ticking:
                tickleft = buff["tickleft"]
            current = time.time()  # Current Time

            # Start our new timer, adjust prevtick
            buff["start"] = current
            if buff["ref"].ticking:
                buff["prevtick"] = current - (tickrate - tickleft)
            self.buffcache[key] = buff
            instance: BaseBuff = buff["ref"](self, key, buff)
            instance.at_unpause(**context)
            utils.delay(buff["duration"], cleanup_buffs, self, persistent=True)
            if buff["ref"].ticking:
                utils.delay(
                    tickrate, tick_buff, handler=self, buffkey=key, initial=False, persistent=True
                )
        return

    def set_duration(self, key, value):
        """Sets the duration of the specified buff.

        Args:
            key:    The key of the buff whose duration you want to set
            value:  The value you want the new duration to be"""
        if key in self.buffcache.keys():
            self.buffcache[key]["duration"] = value

    def view(self) -> dict:
        """Returns a buff flavor text as a dictionary of tuples in the format {key: (name, flavor)}. Common use for this is a buff readout of some kind."""
        self.cleanup()
        _flavor = {k: (buff.name, buff.flavor) for k, buff in self.visible}

        return _flavor

    def cleanup(self):
        """Removes expired buffs, ensures pause state is respected."""
        self._validate_state()
        cleanup_buffs(self)

    # region private methods
    def _validate_state(self):
        """Validates the state of paused/unpaused playtime buffs."""
        if not self.autopause:
            return
        if self.owner.has_account:
            self._unpause_playtime()
        elif not self.owner.has_account:
            self._pause_playtime()

    def _pause_playtime(self, sender=owner, **kwargs):
        """Pauses all playtime buffs when attached object is unpuppeted."""
        if sender != self.owner:
            return
        buffs = self.playtime
        for buff in buffs.values():
            buff.pause()

    def _unpause_playtime(self, sender=owner, **kwargs):
        """Unpauses all playtime buffs when attached object is puppeted."""
        if sender != self.owner:
            return
        buffs = self.playtime
        for buff in buffs.values():
            buff.unpause()
        pass

    def _calculate_mods(self, value, stat: str, buffs: dict):
        """Calculates a return value from a base value, a stat string, and a dictionary of instanced buffs with associated mods.

        Args:
            value:  The base value to modify
            stat:   The string identifier to search mods for
            buffs:  The dictionary of buffs to apply"""
        if not buffs:
            return value
        add = 0
        mult = 0

        for buff in buffs.values():
            for mod in buff.mods:
                buff: BaseBuff
                mod: Mod
                if mod.stat == stat:
                    if mod.modifier == "add":
                        add += mod.value + ((buff.stacks) * mod.perstack)
                    if mod.modifier == "mult":
                        mult += mod.value + ((buff.stacks) * mod.perstack)

        final = (value + add) * max(0, 1.0 + mult)
        return final

    def _remove_via_dict(self, buffs: dict, loud=True, dispel=False, expire=False, context=None):
        """Removes buffs within the provided dictionary from this handler. Used for remove methods besides the basic remove."""
        if not context:
            context = {}
        for k, instance in buffs.items():
            instance: BaseBuff
            if loud:
                if dispel:
                    instance.at_dispel(**context)
                elif expire:
                    instance.at_expire(**context)
                instance.at_remove(**context)
            del instance
            del self.buffcache[k]

    # endregion
    # endregion


class BuffableProperty(AttributeProperty):
    """An example of a way you can extend AttributeProperty to create properties that automatically check buffs for you."""

    def at_get(self, value, obj):
        _value = obj.buffs.check(value, self._key)
        return _value


def cleanup_buffs(handler: BuffHandler):
    """Cleans up all expired buffs from a handler."""
    _remove = handler.expired
    for v in _remove.values():
        v.remove(expire=True)


def tick_buff(handler: BuffHandler, buffkey: str, context=None, initial=True):
    """Ticks a buff. If a buff's tickrate is 1 or larger, this is called when the buff is applied, and then once per tick cycle.

    Args:
        handler:    The handler managing the ticking buff
        buffkey:    The key of the ticking buff
        context:    (optional) A dictionary you wish to pass to the at_tick method as kwargs
        initial:    (optional) Whether this tick_buff call is the first one. Starts True, changes to False for future ticks"""
    # Cache a reference and find the buff on the object
    if buffkey not in handler.buffcache.keys():
        return

    # Instantiate the buff and tickrate
    buff: BaseBuff = handler.get(buffkey)
    tr = buff.tickrate

    # This stops the old ticking process if you refresh/stack the buff
    if tr > time.time() - buff.prevtick and initial != True:
        return

    # Only fire the at_tick methods if the conditional is truthy
    if buff.conditional():
        # Always tick this buff on initial
        if initial:
            buff.at_tick(initial, **context)

        # Tick this buff one last time, then remove
        if buff.duration <= time.time() - buff.start:
            if tr < time.time() - buff.prevtick:
                buff.at_tick(initial, **context)
            buff.remove(expire=True)
            return

        # Tick this buff on-time
        if tr <= time.time() - buff.prevtick:
            buff.at_tick(initial, **context)

    handler.buffcache[buffkey]["prevtick"] = time.time()

    # Recur this function at the tickrate interval, if it didn't stop/fail
    utils.delay(
        tr,
        tick_buff,
        handler=handler,
        buffkey=buffkey,
        context=context,
        initial=False,
        persistent=True,
    )
