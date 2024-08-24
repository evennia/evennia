# Traits

Contribution by Griatch 2020, based on code by Whitenoise and Ainneve contribs, 2014

A `Trait` represents a modifiable property on (usually) a Character. They can
be used to represent everything from attributes (str, agi etc) to skills
(hunting 10, swords 14 etc) and dynamically changing things like HP, XP etc.
Traits differ from normal Attributes in that they track their changes and limit
themselves to particular value-ranges. One can add/subtract from them easily and
they can even change dynamically at a particular rate (like you being poisoned or
healed).

Traits use Evennia Attributes under the hood, making them persistent (they survive
a server reload/reboot).

## Installation

Traits are always added to a typeclass, such as the Character class.

There are two ways to set up Traits on a typeclass. The first sets up the `TraitHandler`
as a property `.traits` on your class and you then access traits as e.g. `.traits.strength`.
The other alternative uses a `TraitProperty`, which makes the trait available directly
as e.g. `.strength`. This solution also uses the `TraitHandler`, but you don't need to
define it explicitly. You can combine both styles if you like.

### Traits with TraitHandler

Here's an example for adding the TraitHandler to the Character class:

```python
# mygame/typeclasses/objects.py

from evennia import DefaultCharacter
from evennia.utils import lazy_property
from evennia.contrib.rpg.traits import TraitHandler

# ...

class Character(DefaultCharacter):
    ...
    @lazy_property
    def traits(self):
        # this adds the handler as .traits
        return TraitHandler(self)


    def at_object_creation(self):
        # (or wherever you want)
        self.traits.add("str", "Strength", trait_type="static", base=10, mod=2)
        self.traits.add("hp", "Health", trait_type="gauge", min=0, max=100)
        self.traits.add("hunting", "Hunting Skill", trait_type="counter",
                        base=10, mod=1, min=0, max=100)
```
When adding the trait, you supply the name of the property (`hunting`) along
with a more human-friendly name ("Hunting Skill"). The latter will show if you
print the trait etc. The `trait_type` is important, this specifies which type
of trait this is (see below).

### TraitProperties

Using `TraitProperties` makes the trait available directly on the class, much like Django model
fields. The drawback is that you must make sure that the name of your Traits don't collide with any
other properties/methods on your class.

```python
# mygame/typeclasses/objects.py

from evennia import DefaultObject
from evennia.utils import lazy_property
from evennia.contrib.rpg.traits import TraitProperty

# ...

class Object(DefaultObject):
    ...
    strength = TraitProperty("Strength", trait_type="static", base=10, mod=2)
    health = TraitProperty("Health", trait_type="gauge", min=0, base=100, mod=2)
    hunting = TraitProperty("Hunting Skill", trait_type="counter", base=10, mod=1, min=0, max=100)
```

> Note that the property-name will become the name of the trait and you don't supply `trait_key`
> separately.

> The `.traits` TraitHandler will still be created (it's used under the
> hood. But it will only be created when the TraitProperty has been accessed at least once,
> so be careful if mixing the two styles. If you want to make sure `.traits` is always available,
> add the `TraitHandler` manually like shown earlier - the `TraitProperty` will by default use
> the same handler (`.traits`).

## Using traits

A trait are entities added to the traithandler (if you use `TraitProperty` the handler is just created under
the hood) after which one can access it as a property on the handler (similarly to how you can do
.db.attrname for Attributes in Evennia).

All traits have a _read-only_ field `.value`. This is only used to read out results, you never
manipulate it directly (if you try, it will just remain unchanged). The `.value` is calculated based
on combining fields, like `.base` and `.mod` - which fields are available and how they relate to
each other depends on the trait type.

```python
> obj.traits.strength.value
12                                  # base + mod

> obj.traits.strength.base += 5
obj.traits.strength.value
17

> obj.traits.hp.value
102                                 # base + mod

> obj.traits.hp.base -= 200
> obj.traits.hp.value
0                                   # min of 0

> obj.traits.hp.reset()
> obj.traits.hp.value
100

# you can also access properties like a dict
> obj.traits.hp["value"]
100

# you can store arbitrary data persistently for easy reference
> obj.traits.hp.effect = "poisoned!"
> obj.traits.hp.effect
"poisoned!"

# with TraitProperties:

> obj.hunting.value
12

> obj.strength.value += 5
> obj.strength.value
17
```

### Relating traits to one another

From a trait you can access its own Traithandler as `.traithandler`. You can
also find another trait on the same handler by using the
`Trait.get_trait("traitname")` method.

```python
> obj.strength.get_trait("hp").value
100
```

This is not too useful for the default trait types - they are all operating
independently from one another. But if you create your own trait classes, you
can use this to make traits that depend on each other.

For example, you could picture making a Trait that is the sum of the values of
two other traits and capped by the value of a third trait. Such complex
interactions are common in RPG rule systems but are by definition game specific.

See an example in the section about [making your own Trait classes](#expanding-with-your-own-traits).


## Trait types

All default traits have a read-only `.value` property that shows the relevant or
'current' value of the trait. Exactly what this means depends on the type of trait.

Traits can also be combined to do arithmetic with their .value, if both have a
compatible type.

```python
> trait1 + trait2
54

> trait1.value
3

> trait1 + 2
> trait1.value
5
```

Two numerical traits can also be compared (bigger-than etc), which is useful in
all sorts of rule-resolution.

```python

if trait1 > trait2:
    # do stuff
```

### Trait

A single value of any type.

This is the 'base' Trait, meant to inherit from if you want to invent
trait-types from scratch (most of the time you'll probably inherit from some of
the more advanced trait-type classes though).

Unlike other Trait-types, the single `.value` property of the base `Trait` can
be editied. The value can hold any data that can be stored in an Attribute. If
it's an integer/float you can do arithmetic with it, but otherwise this acts just
like a glorified Attribute.


```python
> obj.traits.add("mytrait", "My Trait", trait_type="trait", value=30)
> obj.traits.mytrait.value
30

> obj.traits.mytrait.value = "stringvalue"
> obj.traits.mytrait.value
"stringvalue"
```

### Static trait

`value = base + mod`

The static trait has a `base` value and an optional `mod`-ifier. A typical use
of a static trait would be a Strength stat or Skill value. That is, something
that varies slowly or not at all, and which may be modified in-place.

```python
> obj.traits.add("str", "Strength", trait_type="static", base=10, mod=2)
> obj.traits.mytrait.value

12   # base + mod
> obj.traits.mytrait.base += 2
> obj.traits.mytrait.mod += 1
> obj.traits.mytrait.value
15

> obj.traits.mytrait.mod = 0
> obj.traits.mytrait.value
12
```

### Counter


    min/unset     base    base+mod                       max/unset
    |--------------|--------|---------X--------X------------|
                                  current    value
                                             = current
                                             + mod

A counter describes a value that can move from a base. The `.current` property
is the thing usually modified. It starts at the `.base`. One can also add a
modifier, which will both be added to the base and to current (forming
`.value`).  The min/max of the range are optional, a boundary set to None will
remove it. A suggested use for a Counter Trait would be to track skill values.

```python
> obj.traits.add("hunting", "Hunting Skill", trait_type="counter",
                   base=10, mod=1, min=0, max=100)
> obj.traits.hunting.value
11  # current starts at base + mod

> obj.traits.hunting.current += 10
> obj.traits.hunting.value
21

# reset back to base+mod by deleting current
> del obj.traits.hunting.current
> obj.traits.hunting.value
11
> obj.traits.hunting.max = None  # removing upper bound

# for TraitProperties, pass the args/kwargs of traits.add() to the
# TraitProperty constructor instead.
```

Counters have some extra properties:

#### .descs

The `descs` property is a dict `{upper_bound:text_description}`. This allows for easily
storing a more human-friendly description of the current value in the
interval. Here is an example for skill values between 0 and 10:

    {0: "unskilled", 1: "neophyte", 5: "trained", 7: "expert", 9: "master"}

The keys must be supplied from smallest to largest. Any values below the lowest and above the
highest description will be considered to be included in the closest description slot.
By calling `.desc()` on the Counter, you will get the text matching the current `value`.

```python
# (could also have passed descs= to traits.add())
> obj.traits.hunting.descs = {
    0: "unskilled", 10: "neophyte", 50: "trained", 70: "expert", 90: "master"}
> obj.traits.hunting.value
11

> obj.traits.hunting.desc()
"neophyte"
> obj.traits.hunting.current += 60
> obj.traits.hunting.value
71

> obj.traits.hunting.desc()
"expert"
```

#### .rate

The `rate` property defaults to 0. If set to a value different from 0, it
allows the trait to change value dynamically. This could be used for example
for an attribute that was temporarily lowered but will gradually (or abruptly)
recover after a certain time. The rate is given as change of the current
`.value` per-second, and this will still be restrained by min/max boundaries,
if those are set.

It is also possible to set a `.ratetarget`, for the auto-change to stop at
(rather than at the min/max boundaries). This allows the value to return to
a previous value.

```python

> obj.traits.hunting.value
71

> obj.traits.hunting.ratetarget = 71
# debuff hunting for some reason
> obj.traits.hunting.current -= 30
> obj.traits.hunting.value
41

> obj.traits.hunting.rate = 1  # 1/s increase
# Waiting 5s
> obj.traits.hunting.value
46

# Waiting 8s
> obj.traits.hunting.value
54

# Waiting 100s
> obj.traits.hunting.value
71    # we have stopped at the ratetarget

> obj.traits.hunting.rate = 0  # disable auto-change
```
Note that when retrieving the `current`, the result will always be of the same
type as the `.base` even `rate` is a non-integer value. So if `base` is an `int`
(default), the `current` value will also be rounded the closest full integer.
If you want to see the exact `current` value, set `base` to a float - you
will then need to use `round()` yourself on the result if you want integers.

#### .percent()

If both min and max are defined, the `.percent()` method of the trait will
return the value as a percentage.

```python
> obj.traits.hunting.percent()
"71.0%"

> obj.traits.hunting.percent(formatting=None)
71.0
```

### Gauge

This emulates a [fuel-] gauge that empties from a base+mod value.

    min/0                                            max=base+mod
     |-----------------------X---------------------------|
                           value
                          = current

The `.current` value will start from a full gauge. The .max property is
read-only and is set by `.base` + `.mod`. So contrary to a `Counter`, the
`.mod` modifier only applies to the max value of the gauge and not the current
value. The minimum bound defaults to 0 if not set explicitly.

This trait is useful for showing commonly depletable resources like health,
stamina and the like.

```python
> obj.traits.add("hp", "Health", trait_type="gauge", base=100)
> obj.traits.hp.value  # (or .current)
100

> obj.traits.hp.mod = 10
> obj.traits.hp.value
110

> obj.traits.hp.current -= 30
> obj.traits.hp.value
80
```

The Gauge trait is subclass of the Counter, so you have access to the same
methods and properties where they make sense. So gauges can also have a
`.descs` dict to describe the intervals in text, and can use `.percent()` to
get how filled it is as a percentage etc.

The `.rate` is particularly relevant for gauges - useful for everything
from poison slowly draining your health, to resting gradually increasing it.

## Expanding with your own Traits

A Trait is a class inhering from `evennia.contrib.rpg.traits.Trait` (or from one of
the existing Trait classes).

```python
# in a file, say, 'mygame/world/traits.py'

from evennia.contrib.rpg.traits import StaticTrait

class RageTrait(StaticTrait):

    trait_type = "rage"
    default_keys = {
        "rage": 0
    }

    def berserk(self):
        self.mod = 100

    def sedate(self):
        self.mod = 0
```

Above is an example custom-trait-class "rage" that stores a property "rage" on
itself, with a default value of 0. This has all the functionality of a Trait -
for example, if you do del on the `rage` property, it will be set back to its
default (0). Above we also added some helper methods.

To add your custom RageTrait to Evennia, add the following to your settings file
(assuming your class is in mygame/world/traits.py):

    TRAIT_CLASS_PATHS = ["world.traits.RageTrait"]

Reload the server and you should now be able to use your trait:

```python
> obj.traits.add("mood", "A dark mood", rage=30, trait_type='rage')
> obj.traits.mood.rage
30
```

Remember that you can use `.get_trait("name")` to access other traits on the
same handler.  Let's say that the rage modifier is actually limited by
the characters's current STR value times 3, with a max of 100:

```python
class RageTrait(StaticTrait):
    #...
    def berserk(self):
        self.mod = min(100, self.get_trait("STR").value * 3)
```

# as TraitProperty

```
class Character(DefaultCharacter):
    rage = TraitProperty("A dark mood", rage=30, trait_type='rage')
```

## Adding additional TraitHandlers

Sometimes, it is easier to top-level classify traits, such as stats, skills, or other categories of traits you want to handle independantly of each other. Here is an example showing an example on the object typeclass, expanding on the first installation example:

```python
# mygame/typeclasses/objects.py

from evennia import DefaultCharacter
from evennia.utils import lazy_property
from evennia.contrib.rpg.traits import TraitHandler

# ...

class Character(DefaultCharacter):
    ...
    @lazy_property
    def traits(self):
        # this adds the handler as .traits
        return TraitHandler(self)

    @lazy_property
    def stats(self):
        # this adds the handler as .stats
        return TraitHandler(self, db_attribute_key="stats")

    @lazy_property
    def skills(self):
        # this adds the handler as .skills
        return TraitHandler(self, db_attribute_key="skills")


    def at_object_creation(self):
        # (or wherever you want)
        self.stats.add("str", "Strength", trait_type="static", base=10, mod=2)
        self.traits.add("hp", "Health", trait_type="gauge", min=0, max=100)
        self.skills.add("hunting", "Hunting Skill", trait_type="counter",
                        base=10, mod=1, min=0, max=100)
```

> Rememebr that the `.get_traits()` method only works for accessing Traits within the
_same_ TraitHandler.
