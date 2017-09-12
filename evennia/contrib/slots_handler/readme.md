# Slots Handler
It's pretty common for RPG systems to have mechanics where a character is limited to, or must choose, a specific number of items. This contrib is designed to be adaptable to handle as many permutations of this style of mechanic as possible.

## How to use
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
```python
from evennia.objects.objects import DefaultObject

class SlottableObject(DefaultObject):
    "This is a test object for SlotsHandler."

    def at_object_creation(self):
        self.slots = {"addons": ["left"]}
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
