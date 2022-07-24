# Buffs

Contribution by Tegiminis 2022

A buff is a timed object, attached to a game entity, that modifies values, triggers 
code, or both. It is a common design pattern in RPGs, particularly action games.

This contrib gives you a buff handler to apply to your objects, a buff class to extend them,
and a sample property class to show how to automatically check modifiers.

## Quick Start
Assign the handler to a property on the object, like so.

```python
@lazy_property
def buffs(self) -> BuffHandler:
    return BuffHandler(self)
```

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

### Context

You may have noticed that almost every important handler method optionally accepts a `context` dictionary.

Context is an important concept for this handler. Every method which modifies, triggers, or checks a buff passes this 
dictionary (default: empty) to the buff hook methods as keyword arguments (**kwargs). It is used for nothing else. This allows you to make those 
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
def ThornsBuff(BaseBuff):
    ...
    triggers = ['taken_damage']
    # This is the hook method on our thorns buff
    def at_trigger(self, trigger, attacker=None, damage=0, **kwargs):
        if not attacker: return
        attacker.db.health -= damage * 0.2
```
Apply the buff, take damage, and watch the thorns buff do its work!

## Buffs

But wait! You still have to actually create the buffs you're going to be applying.

Creating a buff is very easy: extend `BaseBuff` into a new class, and fill in all the relevant buff details.
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
def Poison(BaseBuff):
    ...
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
