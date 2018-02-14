# Slots Handler
DamnedScholar 2017

It's pretty common for RPG systems to have mechanics where a character is limited to, or must choose, a specific number of items. This contrib is designed to be adaptable to handle as many permutations of this style of mechanic as possible.

## How to use
### Simple walkthrough
This walkthrough will help you get started with `SlotsHandler` right away. First, create an object. For the sake of simplicity, we're using a newly created object, but the slots can exist on anything as long as it has a typeclass.
```python
> @py from evennia.utils import create;self.ndb.spells = create.create_object(typeclass="evennia.contrib.slots_handler.slots.SlottedObject", location=self, key="spellbook")
```
This gives you an object in your inventory, and a temporary shortcut to it: `self.ndb.spells` (which will disappear when the server restarts). You now need to configure the kinds and number of slots:
```python
> @py self.ndb.spells.slots.add({"ready": [2, "bonus"], "known": [4, "fire", "air"]})
```
If the handler is behaving itself, you will see it return a dict of all current slots on the object. At this point, that should read as follows:
```python
{
    'ready': {1: '', 2: '', 'bonus': ''},
    'known': {1: '', 2: '', 3: '', 4: '', 'air': '', 'fire': ''}
}
```
You can see that numbers and strings are handled a bit differently. Numerical arguments are summed and an equal number of numbered slots are added to the slot array. Let's try attaching an object.
```python
> @py self.ndb.spells.slots.attach("Fireball", {"ready": [2], "known": ["fire"]})
```
You can use `self.ndb.spells.slots.all()` at this point to see that the contents have changed.
```python
{
    'ready': {1: 'Fireball', 2: 'Fireball', 'bonus': ''},
    'known': {1: '', 2: '', 3: '', 4: '', 'air': '', 'fire': 'Fireball'}
}
```
Our hypothetical probably mage (but definite pyromaniac) has the "fireball" spell as both of their ready slots and also the known spell they get because it has something to do with fire. As with attributes, you can store any kind of object in a slot. So if you want to store a complex dict of information about the item, go for it. The system was built with the intent of keeping track of external objects in the Evennia typeclass sense, but we'll get to more of that later.

Now, let's say our mage casts one of fireball spells they had prepared. We can represent that with a simple drop command. We need to indicate the slot to make sure that the spell isn't removed from everywhere.
```python
> @py self.ndb.spells.slots.drop('Fireball', {'ready': [1]})
```
The results show that one of the instances of `"Fireball"` has been removed.
```python
{
    'ready': {1: 'Fireball', 2: '', 'bonus': ''},
    'known': {1: '', 2: '', 3: '', 4: '', 'air': '', 'fire': 'Fireball'}
}
```
When attaching objects, `SlotsHandler` checks them for an attribute called `.db.slots`, `.ndb.slots`, or `.slots` (in that order of preference), which is expected to contain a slot dict in the same format that we've been using. You can also look at the second object example below.
```python
> @py from evennia.utils import create;self.ndb.summon_elemental = create.create_object(typeclass="evennia.contrib.slots_handler.slots.SlottableObject", location=self, key="Summon Elemental")
> @py self.ndb.summon_elemental.db.slots={'known': ['air']}
```
Pretend that this object, `Summon Elemental`, represents a spell, but also contains the information for the elemental being conjured and so the developer has decided to use a database-connected object to store the summon stats. You can add the object like so:
```python
> @py self.ndb.spells.slots.attach(self.ndb.summon_elemental)
```
And our dict changes as we would expect:
```python
{
    'ready': {1: 'Fireball', 2: '', 'bonus': ''},
    'known': {1: '', 2: '', 3: '', 4: '', 'air': <SlottableObject: Summon Elemental>, 'fire': 'Fireball'}
}
```
Note that the default (no slots specified) behaviors of `.attach()` and `.drop()` differ fundamentally in whether they care about the object being targeted. `.drop()` does not pay attention to the list of slots on the object. Instead, it tries to remove that object from *every* slot.

Finally, if an object has a `dbid`, it will remember objects of slots it's attached to and will run a `.slots.drop(self)` command on each of them if you delete it. So for cleanup, this is all we have to do:
```python
> @py self.ndb.summon_elemental.delete()
```

#### A note on data safety
All commands in this contrib return some form of useful information, either about all slots or just about the ones that have been modified, so the best way to guard against accidentally removing the wrong slot is to catch that information. The commands here are pretty straightforward, so there also aren't any safeguards against developers telling the handler something other than what they wanted to tell it.

### Slotted object example
The `@lazy_property` declaration below can be put on any typeclass parent. The functionality of `SlotsHandler` relies on the `AttributesHandler`, so any deviations from the standard typeclass system have to at least include that. This document will assume that you're using the name `slots` for the property.
```python
from evennia.objects.objects import DefaultObject

class SlottedObject(DefaultObject):
    "This is a test object for SlotsHandler."

    @lazy_property
    def slots(self):
        return SlotsHandler(self)
```
### Slottable object example
By giving a typeclass to slottable objects, the system has additional options. Objects can define their own slots, and typeclassed objects specifically are able to remember all of the objects to which they're attached, and then automate their own dropping when deleted.
```python
from evennia.objects.objects import DefaultObject

class SlottableObject(DefaultObject):
    "This is a test object for SlotsHandler."

    def at_object_creation(self):
        self.db.slots = {"addons": ["left"]}

    def at_object_deletion(self):
        "Called at object deletion."
        # It's necessary to clean up typeclassed objects from slots they
        # occupied, since they don't get completely deleted when `.delete()`
        # is invoked.
        if self.db.slots_holders:
            for h in self.db.slots_holders:
                try:
                    h.slots.drop(self)
                except Exception:
                    raise Exception("This object can't be deleted because the "
                                    "attempt to remove it from slots it was "
                                    "attached to resulted in an error.")
```
### Concepts
**Slots format:** In this contrib, all arguments and attributes labeled slots are intended to come in one of two formats:
```python
["magic items", "spells", "stunts"]
```
This represents a list of categories, and is used for targeting every slot in each of the named categories. There's no point in using this format for `add()`, but it can be used to delete a whole category, list specific categories, or attach/drop in broad strokes.
```python
{"spells": [2, "class bonus", "racial bonus"], "stunts": ["athletics", "weaponry"]}
```
This format is used to target specific slots. If numerical values are included, they will be treated in specific ways. For `add()` and `delete()`, the numerical values will be summed and an equal number of numbered slots will be added to or deleted from the category. For `attach()` and `drop()`, they will be summed and that number of slots will be used or freed up. For `check()`, the first *n* numbered slots will be returned.

**Slot category:** SlotsHandler interprets the top-level keys of a dict, or the values of a list, to be categories. Categories are important as they factor into the storage name of the slot list, so if you don't want to separate your slots, give them a very general category such as `"slots"`.

**Numbered vs named slots:** Slot keys must be integers or strings. Numbered slots are anonymous and mostly will not be referred to directly. Named slots are for cases where you want to refer to them directly.

**Nesting:** The system is designed with simplicity in mind. You should not try to force individual slot attributes to be more than a basic `dict`. However, since we're storing objects in these slots, it's perfectly possible to store one slot attribute inside a slot in a different attribute. Your code just has to know to look for that, because `SlotsHandler` does not. The individual building blocks are simple, but they may be assembled in more complicated ways than they can achieve on their own.

### How do I use it?
The first way is just to record how many of a thing a character has. One object can be stored in multiple slots for systems where one mechanic might fill more than one requirement. The handler doesn't support querying for specific slots, because I feel like `.all()` is sufficient for those purposes. To retrieve a specific slot, it's easy enough to use syntax like the following:
```python
spells = obj.slots.all()['spells']
weapon = obj.slots.all()['equipped']['weapon']
```

### What's next?
While I consider `SlotsHandler` complete as-is, there is room for sample commands that interact with the handler and a set of classes that a new user can plug into their game to instantly see how it works without altering their own typeclasses.

## SlottedObject.slots.add
```
add(self, slots)
```
> Create an array of slots, or add additional slots to an existing array.

**Args:**
* **slots (dict):** A dict of slots to add. Since you can't add empty categories, it would be pointless to pass a list to this function, and so it doesn't accept lists for input.

## SlottedObject.slots.delete
```
delete(self, slots)
```
> Delete the named category or slots.
> WARNING: If you have anything attached in slots when they are removed, the slots' contents will also be removed. This function will return a dict of any removed slots and their contents, so it can act as a pop(), but if you don't catch that data, it WILL be lost.

**Args:**
* **slots (list or dict):** Slot categories or individual slots to delete.

## SlottedObject.slots.attach
```
attach(self, target, slots=None)
```
> Attempt to attach the target in all slots it consumes. Optionally, the target's slots may be overridden.

**Args:**
* **target (object):** The object being attached.
* **slots (list or dict, optional):** Slot categories or individual slots to drop from.

## SlottedObject.slots.drop
```
drop(self, target=None, slots=None)
```
> Attempt to drop the target from all slots it occupies. Optionally, you may choose to drop only specific slots. This function is messy in that it doesn't care if the slots exist or not, it just tries to drop everything it is given. This function will return a dict of any emptied slots, so it can act as a pop(), but if you don't catch that data, it WILL be lost.

**Args:**
* **target (object):** The object being dropped.
* **slots (list or dict, optional):** Slot categories or individual slots to drop from.

## SlottedObject.slots.replace
```
replace(self, target, slots=None)
```
> Works exactly like `.slots.attach`, but first invokes `.slots.drop` on all requested slots. The results of both commands are returned as a tuple in the form `(drop, attach)`.

**Args:**
* **target (object):** The object being attached.
* **slots (list or dict, optional):** Slot categories or individual slots to drop from.

## SlottedObject.slots.where
```
where(self, target=None)
```
> Return a dict of slots representing where target is attached.

**Args:**
* **target (object):** The object being searched for.
