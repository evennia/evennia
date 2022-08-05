# Buffs

Contribution by Tegiminis 2022

A buff is a timed object, attached to a game entity. It is capable of modifying values, triggering code, or both. 
It is a common design pattern in RPGs, particularly action games.

Features: 

- `BuffHandler`: A buff handler to apply to your objects.
- `BaseBuff`: A buff class to extend from to create your own buffs.
- `BuffableProperty`: A sample property class to show how to automatically check modifiers.
- `CmdBuff`: A command which applies buffs.
- `samplebuffs.py`: Some sample buffs to learn from.

## Quick Start
Assign the handler to a property on the object, like so.

```python
@lazy_property
def buffs(self) -> BuffHandler:
    return BuffHandler(self)
```

You may then call the handler to add or manipulate buffs like so: `object.buffs`. See **Using the Handler**.

### Customization

If you want to customize the handler, you can feed the constructor two arguments:
- `dbkey`: The string you wish to use as the attribute key for the buff database. Defaults to "buffs". This allows you to keep separate buff pools - for example, "buffs" and "perks".
- `autopause`: If you want this handler to automatically pause playtime buffs when its owning object is unpuppeted.

> **Note**: If you enable autopausing, you MUST initialize the property in your owning object's
> `at_init` hook. Otherwise, a hot reload can cause playtime buffs to not update properly
> on puppet/unpuppet. You have been warned!

Let's say you want another handler for an object, `perks`, which has a separate database and 
respects playtime buffs. You'd assign this new property as so:

```python
class BuffableObject(Object):
    @lazy_property
    def perks(self) -> BuffHandler:
        return BuffHandler(self, dbkey='perks', autopause=True)

    def at_init(self):
        self.perks
```

## Using the Handler

Here's how to make use of your new handler.

### Apply a Buff

Call the handler's `add` method. This requires a class reference, and also contains a number of 
optional arguments to customize the buff's duration, stacks, and so on. You can also store any arbitrary value 
in the buff's cache by passing a dictionary through the `to_cache` optional argument. This will not overwrite the normal
values on the cache.

```python
self.buffs.add(StrengthBuff)                            # A single stack of StrengthBuff with normal duration
self.buffs.add(DexBuff, stacks=3, duration=60)          # Three stacks of DexBuff, with a duration of 60 seconds
self.buffs.add(ReflectBuff, to_cache={'reflect': 0.5})  # A single stack of ReflectBuff, with an extra cache value
```

Two important attributes on the buff are checked when the buff is applied: `refresh` and `unique`.
- `refresh` (default: True) determines if a buff's timer is refreshed when it is reapplied.
- `unique` (default: True) determines if this buff is unique; that is, only one of it exists on the object.

The combination of these two booleans creates one of three kinds of keys:
- `Unique is True, Refresh is True/False`: The buff's default key.
- `Unique is False, Refresh is True`: The default key mixed with the applier's dbref. This makes the buff "unique-per-player", so you can refresh through reapplication.
- `Unique is False, Refresh is False`: The default key mixed with a randomized number. 

### Get Buffs

The handler has several getter methods which return instanced buffs. You won't need to use these for basic functionality, but if you want to manipulate
buffs after application, they are very useful. The handler's `check`/`trigger` methods utilize some of these getters, while others are just for developer convenience.

`get(key)` is the most basic getter. It returns a single buff instance, or `None` if the buff doesn't exist on the handler. It is also the only getter
that returns a single buff instance, rather than a dictionary.

Group getters, listed below, return a dictionary of values in the format `{buffkey: instance}`. If you want to iterate over all of these buffs,
you should do so via the `dict.values()` method.

- `get_all()` returns all buffs on this handler. You can also use the `handler.all` property.
- `get_by_type(BuffClass)` returns buffs of the specified type.
- `get_by_stat(stat)` returns buffs with a `Mod` object of the specified `stat` string in their `mods` list.
- `get_by_trigger(string)` returns buffs with the specified string in their `triggers` list.
- `get_by_source(Object)` returns buffs applied by the specified `source` object.
- `get_by_cachevalue(key, value)` returns buffs with the matching `key: value` pair in their cache. `value` is optional.

All group getters besides `get_all()` can "slice" an existing dictionary through the optional `to_filter` argument.

```python
dict1 = handler.get_by_type(Burned)                     # This finds all "Burned" buffs on the handler
dict2 = handler.get_by_source(self, to_filter=dict1)    # This filters dict1 to find buffs with the matching source
```

> **Note**: Most of these getters also have an associated handler property. For example, `handler.effects` returns all buffs that can be triggered, which
> is then iterated over by the `get_by_trigger` method.

### Remove Buffs

There are also a number of remover methods. Generally speaking, these follow the same format as the getters.

- `remove(key)` removes the buff with the specified key.
- `clear()` removes all buffs.
- `remove_by_type(BuffClass)` removes buffs of the specified type.
- `remove_by_stat(stat)` removes buffs with a `Mod` object of the specified `stat` string in their `mods` list.
- `remove_by_trigger(string)` removes buffs with the specified string in their `triggers` list.
- `remove_by_source(Object)` removes buffs applied by the specified source
- `remove_by_cachevalue(key, value)` removes buffs with the matching `key: value` pair in their cache. `value` is optional.

You can also remove a buff by calling the instance's `remove` helper method. You can do this on the dictionaries returned by the
getters listed above.

```python
to_remove = handler.get_by_trigger(trigger)     # Finds all buffs with the specified trigger
for buff in to_remove.values():                 # Removes all buffs in the to_remove dictionary via helper methods
    buff.remove()   
```

### Check Modifiers

Call the handler `check(value, stat)` method when you want to see the modified value. 
This will return the `value`, modified by any relevant buffs on the handler's owner (identified by 
the `stat` string).

For example, let's say you want to modify how much damage you take. That might look something like this:

```python
# The method we call to damage ourselves
def take_damage(self, source, damage):
    _damage = self.buffs.check(damage, 'taken_damage')
    self.db.health -= _damage
```

This method calls the `at_pre_check` and `at_post_check` methods at the relevant points in the process. You can use to this make
buffs that are reactive to being checked; for example, removing themselves, altering their values, or interacting with the game state.

> **Note**: You can also trigger relevant buffs at the same time as you check them by ensuring the optional argument `trigger` is True in the `check` method.

### Trigger Buffs

Call the handler's `trigger(string)` method when you want an event call. This will call the `at_trigger` hook method on all buffs with the relevant trigger `string`.

For example, let's say you want to trigger a buff to "detonate" when you hit your target with an attack.
You'd write a buff that might look like this:

```python
class Detonate(BaseBuff):
    ...
    triggers = ['take_damage']
    def at_trigger(self, trigger, *args, **kwargs)
        self.owner.take_damage(100)
        self.remove()
```

And then call `handler.trigger('take_damage')` in the method you use to take damage.

> **Note** You could also do this through mods and `at_post_check` if you like, depending on how to want to add the damage.

### Ticking

Ticking buffs are slightly special. They are similar to trigger buffs in that they run code, but instead of
doing so on an event trigger, they do so on a periodic tick. A common use case for a buff like this is a poison,
or a heal over time.

```python
class Poison(BaseBuff):
    ...
    tickrate = 5
    def at_tick(self, initial=True, *args, **kwargs):
        _dmg = self.dmg * self.stacks
        if not initial:
            self.owner.location.msg_contents(
                "Poison courses through {actor}'s body, dealing {damage} damage.".format(
                    actor=self.owner.named, damage=_dmg
                )
            )
```

To make a buff ticking, ensure the `tickrate` is 1 or higher, and it has code in its `at_tick`
method. Once you add it to the handler, it starts ticking!

> **Note**: Ticking buffs always tick on initial application, when `initial` is `True`. If you don't want your hook to fire at that time,
> make sure to check the value of `initial` in your `at_tick` method.

### Context

Every important handler method optionally accepts a `context` dictionary.

Context is an important concept for this handler. Every method which checks, triggers, or ticks a buff passes this 
dictionary (default: empty) to the buff hook methods as keyword arguments (`**kwargs`). It is used for nothing else. This allows you to make those 
methods "event-aware" by storing relevant data in the dictionary you feed to the method.

For example, let's say you want a "thorns" buff which damages enemies that attack you. Let's take our `take_damage` method
and add a context to the mix.

```python
def take_damage(attacker, damage):
    context = {'attacker': attacker, 'damage': damage}
    _damage = self.buffs.check(damage, 'taken_damage', context=context)
    self.buffs.trigger('taken_damage', context=context)
    self.db.health -= _damage
```
Now we use the values that context passes to the buff kwargs to customize our logic.
```python
class ThornsBuff(BaseBuff):
    ...
    triggers = ['taken_damage']
    # This is the hook method on our thorns buff
    def at_trigger(self, trigger, attacker=None, damage=0, **kwargs):
        if not attacker: 
            return
        attacker.db.health -= damage * 0.2
```
Apply the buff, take damage, and watch the thorns buff do its work!

## Creating New Buffs

Creating a new buff is very easy: extend `BaseBuff` into a new class, and fill in all the relevant buff details.
However, there are a lot of individual moving parts to a buff. Here's a step-through of the important stuff.

### Basics

Regardless of any other functionality, all buffs have the following class attributes:

- They have customizable `key`, `name`, and `flavor` strings.
- They have a `duration` (float), and automatically clean-up at the end. Use -1 for infinite duration, and 0 to clean-up immediately. (default: -1)
- They can stack, if `maxstacks` (int) is not equal to 1. If it's 0, the buff stacks forever. (default: 1)
- They can be `unique` (bool), which determines if they have a unique namespace or not. (default: True)
- They can `refresh` (bool), which resets the duration when stacked or reapplied. (default: True)
- They can be `playtime` (bool) buffs, where duration only counts down during active play. (default: False)

They also always store some useful mutable information about themselves in the cache:

- `ref` (class): The buff class path we use to construct the buff.
- `start` (float): The timestamp of when the buff was applied.
- `source` (Object): If specified; this allows you to track who or what applied the buff.
- `prevtick` (float): The timestamp of the previous tick.
- `duration` (float): The cached duration. This can vary from the class duration, depending on if the duration has been modified (paused, extended, shortened, etc).
- `stacks` (int): How many stacks they have.
- `paused` (bool): Paused buffs do not clean up, modify values, tick, or fire any hook methods.

You can always access the raw cache dictionary through the `cache` attribute on an instanced buff. This is grabbed when you get the buff through
a handler method, so it may not always reflect recent changes you've made, depending on how you structure your buff calls. All of the above
mutable information can be found in this cache, as well as any arbitrary information you pass through the handler `add` method (via `to_cache`).

### Modifiers

Mods are stored in the `mods` list attribute. Buffs which have one or more Mod objects in them can modify stats. You can use the handler method to check all 
mods of a specific stat string and apply their modifications to the value; however, you are encouraged to use `check` in a getter/setter, for easy access.

Mod objects consist of only four values, assigned by the constructor in this order:

- `stat`: The stat you want to modify. When `check` is called, this string is used to find all the mods that are to be collected.
- `mod`: The modifier. Defaults are 'add' and 'mult'. Modifiers are calculated additively, and in standard arithmetic order (see `_calculate_mods` for more)
- `value`: How much value the modifier gives regardless of stacks
- `perstack`: How much value the modifier grants per stack, INCLUDING the first. (default: 0)

The most basic way to add a Mod to a buff is to do so in the buff class definition, like this:

```python
class DamageBuff(BaseBuff):
    mods = [Mod('damage', 'add', 10)]
```

No mods applied to the value are permanent in any way. All calculations are done at runtime, and the mod values are never stored 
anywhere except on the buff in question. In other words: you don't need to track the origin of particular stat mods, and you will 
never permanently change a stat modified by a buff. To remove the modification, simply remove the buff from the object.

> **Note**: You can add your own modifier types by overloading the `_calculate_mods` method, which contains the basic modifier application logic.

#### Generating Mods (Advanced)

An advanced way to do mods is to generate them when the buff is initialized. This lets you create mods on the fly that are reactive to the game state.

```python
class GeneratedStatBuff(BaseBuff):
    ...
    def __init__(self, handler, buffkey, cache={}) -> None:
        super().__init__(handler, buffkey, cache)
        # Finds our "modgen" cache value, and generates a mod from it
        modgen = list(self.cache.get("modgen"))
        if modgen:
            self.mods = [Mod(*modgen)]
```

### Triggers

Buffs which have one or more strings in the `triggers` attribute can be triggered by events.

When the handler's `trigger` method is called, it searches all buffs on the handler for any with a matchingtrigger, 
then calls their `at_trigger` hooks. Buffs can have multiple triggers, and you can tell which trigger was used by 
the `trigger` argument in the hook.

```python 
class AmplifyBuff(BaseBuff):
    triggers = ['damage', 'heal'] 

    def at_trigger(self, trigger, **kwargs):
        if trigger == 'damage': print('Damage trigger called!')
        if trigger == 'heal': print('Heal trigger called!')
```

### Ticking

A buff which ticks isn't much different than one which triggers. You're still executing arbitrary hooks on
the buff class. To tick, the buff must have a `tickrate` of 1 or higher.

```python
class Poison(BaseBuff):
    ...
    # this buff will tick 6 times between application and cleanup.
    duration = 30
    tickrate = 5
    def at_tick(self, initial, **kwargs):
        self.owner.take_damage(10)
```
> **Note**: The buff always ticks once when applied. For this **first tick only**, `initial` will be True in the `at_tick` hook method. `initial` will be False on subsequent ticks.

Ticks utilize a persistent delay, so they should be pickleable. As long as you are not adding new properties to your buff class, this shouldn't be a concern.
If you **are** adding new properties, try to ensure they do not end up with a circular code path to their object or handler, as this will cause pickling errors.

### Extras

Buffs have a grab-bag of extra functionality to let you add complexity to your designs.

#### Conditionals

You can restrict whether or not the buff will `check`, `trigger`, or `tick` through defining the `conditional` hook. As long
as it returns a "truthy" value, the buff will apply itself. This is useful for making buffs dependent on game state - for
example, if you want a buff that makes the player take more damage when they are on fire:

```python
class FireSick(BaseBuff):
    ...
    def conditional(self, *args, **kwargs):
        if self.owner.buffs.get_by_type(FireBuff): 
            return True
        return False
```

Conditionals for `check`/`trigger` are checked when the buffs are gathered by the handler methods for the respective operations. `Tick`
conditionals are checked each tick.

#### Helper Methods

Buff instances have a number of helper methods.

- `remove`/`dispel`: Allows you to remove or dispel the buff. Calls `at_remove`/`at_dispel`, depending on optional arguments.
- `pause`/`unpause`: Pauses and unpauses the buff. Calls `at_pause`/`at_unpause`.
- `reset`: Resets the buff's start to the current time; same as "refreshing" it.

#### Playtime Duration

If your handler has `autopause` enabled, any buffs with truthy `playtime` value will automatically pause
and unpause when the object the handler is attached to is puppetted or unpuppetted. This even works with ticking buffs,
although if you have less than 1 second of tick duration remaining, it will round up to 1s.

> **Note**: If you want more control over this process, you can comment out the signal subscriptions on the handler and move the autopause logic
> to your object's `at_pre/post_puppet/unpuppet` hooks.


----

<small>This document page is generated from `evennia/contrib/rpg/buffs/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
