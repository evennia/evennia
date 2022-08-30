# Handling Equipment 

In _Knave_, you have a certain number of inventory "slots". The amount of slots is given by `CON + 10`. 
All items (except coins) have a `size`, indicating how many slots it uses. You can't carry more items 
than you have slot-space for. Also items wielded or worn count towards the slots. 

We still need to track what the character is using however: What weapon they have readied affects the damage
they can do. The shield, helmet and armor they use affects their defense. 

We have already set up the possible 'wear/wield locations' when we defined our Objects
[in the previous lesson](./Beginner-Tutorial-Objects.md). This is what we have in `enums.py`:

```python 
# mygame/evadventure/enums.py

# ...

class WieldLocation(Enum):
    
    BACKPACK = "backpack"
    WEAPON_HAND = "weapon_hand"
    SHIELD_HAND = "shield_hand"
    TWO_HANDS = "two_handed_weapons"
    BODY = "body"  # armor
    HEAD = "head"  # helmets
```

Basically, all the weapon/armor locations are exclusive - you can only have one item in each (or none). 
The BACKPACK is special - it contains any number of items (up to the maximum slot usage).

## EquipmentHandler that saves

> Create a new module `mygame/evadventure/equipment.py`.

```{sidebar}
If you want to understand more about behind how Evennia uses handlers, there is a 
[dedicated tutorial](../../Tutorial-Persistent-Handler.md) talking about the principle.
```
In default Evennia, everything you pick up will end up "inside" your character object (that is, have
you as its `.location`). This is called your _inventory_ and has no limit. We will keep 'moving items into us'
when we pick them up, but we will add more functionality using an _Equipment handler_.

A handler is (for our purposes) an object that sits "on" another entity, containing functionality 
for doing one specific thing (managing equipment, in our case).

This is the start of our handler: 

```python 
# in mygame/evadventure/equipment.py 

from .enums import WieldLocation

class EquipmentHandler: 
    save_attribute = "inventory_slots"
    
    def __init__(self, obj): 
        # here obj is the character we store the handler on 
        self.obj = obj 
        self._load() 
        
    def _load(self):
        """Load our data from an Attribute on `self.obj`"""
        self.slots = self.obj.attributes.get(
            self.save_attribute,
            category="inventory",
            default={
                WieldLocation.WEAPON_HAND: None, 
                WieldLocation.SHIELD_HAND: None, 
                WieldLocation.TWO_HANDS: None, 
                WieldLocation.BODY: None,
                WieldLocation.HEAD: None,
                WieldLocation.BACKPACK: []
            } 
        )
    
    def _save(self):
        """Save our data back to the same Attribute"""
        self.obj.attributes.add(self.save_attribute, self.slots, category="inventory") 
```

This is a compact and functional little handler. Before analyzing how it works, this is how 
we will add it to the Character: 

```python
# mygame/evadventure/characters.py

# ... 

from evennia.utils.utils import lazy_property
from .equipment import EquipmentHandler 

# ... 

class EvAdventureCharacter(LivingMixin, DefaultCharacter):
    
    # ... 

    @lazy_property 
    def equipment(self):
        return EquipmentHandler(self)
```

After reloading the server, the equipment-handler will now be accessible on character-instances as

    character.equipment

The `@lazy_property` works such that it will not load the handler until someone actually tries to 
fetch it with `character.equipment`. When that 
happens, we start up the handler and feed it `self` (the `Character` instance itself). This is what 
enters `__init__` as `.obj` in the `EquipmentHandler` code above.

So we now have a handler on the character, and the handler has a back-reference to the character it sits
on. 

Since the handler itself is just a regular Python object, we need to use the `Character` to store
our data - our _Knave_ "slots". We must save them to the database, because we want the server to remember
them even after reloading.

Using `self.obj.attributes.add()` and `.get()` we save the data to the Character in a specially named
[Attribute](../../../Components/Attributes.md). Since we use a `category`, we are unlikely to collide with 
other Attributes.

Our storage structure is a `dict` with keys after our available `WieldLocation` enums. Each can only 
have one item except `WieldLocation.BACKPACK`, which is a list.

## Connecting the EquipmentHandler

Whenever an object leaves from one location to the next, Evennia will call a set of _hooks_ (methods) on the 
object that moves, on the source-location and on its destination. This is the same for all moving things -
whether it's a character moving between rooms or an item being dropping from your hand to the ground. 

We need to tie our new `EquipmentHandler` into this system. By reading the doc page on [Objects](../../../Components/Objects.md),
or looking at the [DefaultObject.move_to](evennia.objects.objects.DefaultObject.move_to) docstring, we'll 
find out what hooks Evennia will call. Here `self` is the object being moved from 
`source_location` to `destination`: 


1. `self.at_pre_move(destination)` (abort if return False)
2. `source_location.at_pre_object_leave(self, destination)` (abort if return False)
3. `destination.at_pre_object_receive(self, source_location)` (abort if return False)
4. `source_location.at_object_leave(self, destination)`
5. `self.announce_move_from(destination)`
6. (move happens here)
7. `self.announce_move_to(source_location)`
8. `destination.at_object_receive(self, source_location)`
9. `self.at_post_move(source_location)`

All of these hooks can be overridden to customize movement behavior. In this case we are interested in 
controlling how items 'enter' and 'leave' our character - being 'inside' the character is the same as 
them 'carrying' it. We have three good hook-candidates to use for this. 

- `.at_pre_object_receive` - used to check if you can actually pick something up, or if your equipment-store is full.
- `.at_object_receive` - used to add the item to the equipmenthandler
- `.at_object_leave` - used to remove the item from the equipmenthandler

You could also picture using `.at_pre_object_leave` to restrict dropping (cursed?) items, but 
we will skip that for this tutorial.

```python 
# mygame/evadventure/character.py 

# ... 

class EvAdventureCharacter(LivingMixin, DefaultCharacter): 

    # ... 
    
    def at_pre_object_receive(self, moved_object, source_location, **kwargs): 
        """Called by Evennia before object arrives 'in' this character (that is,
        if they pick up something). If it returns False, move is aborted.
        
        """ 
        return self.equipment.validate_slot_usage(moved_object)
    
    def at_object_receive(self, moved_object, source_location, **kwargs): 
        """ 
        Called by Evennia when an object arrives 'in' the character.
        
        """
        self.equipment.add(moved_object)

    def at_object_leave(self, moved_object, destination, **kwargs):
        """ 
        Called by Evennia when object leaves the Character. 
        
        """
        self.equipment.remove(moved_object)
```

Above we have assumed the `EquipmentHandler` (`.equipment`) has methods `.validate_slot_usage`, 
`.add` and `.remove`. But we haven't actually added them yet - we just put some reasonable names! Before 
we can use this, we need to go actually adding those methods. 

## Expanding the Equipmenthandler

## `.validate_slot_usage`

Let's start with implementing the first method we came up with above, `validate_slot_usage`:

```python 
# mygame/evadventure/equipment.py 

from .enums import WieldLocation, Ability

class EquipmentError(TypeError):
    """All types of equipment-errors"""
    pass

class EquipmentHandler: 

    # ... 
    
    @property
    def max_slots(self):
        """Max amount of slots, based on CON defense (CON + 10)""" 
        return getattr(self.obj, Ability.CON.value, 1) + 10
        
    def count_slots(self):
        """Count current slot usage""" 
        slots = self.slots
        wield_usage = sum(
            getattr(slotobj, "size", 0) or 0
            for slot, slotobj in slots.items()
            if slot is not WieldLocation.BACKPACK
        )
        backpack_usage = sum(
            getattr(slotobj, "size", 0) or 0 for slotobj in slots[WieldLocation.BACKPACK]
        )
        return wield_usage + backpack_usage
    
    def validate_slot_usage(self, obj):
          """
          Check if obj can fit in equipment, based on its size.
          
          """
          if not inherits_from(obj, EvAdventureObject):
              # in case we mix with non-evadventure objects
              raise EquipmentError(f"{obj.key} is not something that can be equipped.")
  
         size = obj.size
         max_slots = self.max_slots
         current_slot_usage = self.count_slots()
         return current_slot_usage + size <= max_slots:

```

```{sidebar}
The `@property` decorator turns a method into a property so you don't need to 'call' it. 
That is, you can access `.max_slots` instead of `.max_slots()`. In this case, it's just a 
little less to type.
```
We add two helpers - the `max_slots` _property_ and `count_slots`, a method that calculate the current
slots being in use. Let's figure out how they work. 

### `.max_slots`

For `max_slots`, remember that `.obj` on the handler is a back-reference to the `EvAdventureCharacter` we 
put this handler on. `getattr` is a Python method for retrieving a named property on an object. 
The `Enum` `Ability.CON.value` is the string `Constitution` (check out the 
[first Utility and Enums tutorial](./Beginner-Tutorial-Utilities.md) if you don't recall).

So to be clear, 

```python 
getattr(self.obj, Ability.CON.value) + 10
```
is the same as writing 

```python 
getattr(your_character, "Constitution") + 10 
```

which is the same as doing something like this: 

```python 
your_character.Constitution + 10 
```

In our code we write `getattr(self.obj, Ability.CON.value, 1)` - that extra `1`   means that if there 
should happen to _not_ be a property "Constitution" on `self.obj`, we should not error out but just 
return 1.


### `.count_slots`

In this helper we use two Python tools - the `sum()` function and a 
[list comprehension](https://www.w3schools.com/python/python_lists_comprehension.asp). The former 
simply adds the values of any iterable together. The latter is a more efficient way to create a list: 

    new_list = [item for item in some_iterable if condition]
    all_above_5 = [num for num in range(10) if num > 5]  # [6, 7, 8, 9]
    all_below_5 = [num for num in range(10) if num < 5]  # [0, 1, 2, 3, 4]

To make it easier to understand, try reading the last line above as "for every number in the range 0-9, 
pick all with a value below 5 and make a list of them". You can also embed such comprehensions 
directly in a function call like `sum()` without using `[]` around it. 

In `count_slots` we have this code: 

```python 
wield_usage = sum(
    getattr(slotobj, "size", 0)
    for slot, slotobj in slots.items()
    if slot is not WieldLocation.BACKPACK
)
```

We should be able to follow all except `slots.items()`. Since `slots` is a `dict`, we can use `.items()`
to get a sequence of `(key, value)` pairs. We store these in `slot` and `slotobj`. So the above can 
be understood as "for every `slot` and `slotobj`-pair in `slots`, check which slot location it is. 
If it is _not_ in the backpack, get its size and add it to the list. Sum over all these 
sizes". 

A less compact but maybe more readonable way to write this would be: 

```python 
backpack_item_sizes = [] 
for slot, slotobj in slots.items(): 
    if slot is not WieldLocation.BACKPACK:
       size = getattr(slotobj, "size", 0) 
       backpack_item_sizes.append(size)
wield_usage = sum(backpack_item_sizes)
```

The same is done for the items actually in the BACKPACK slot. The total sizes are added 
together. 

### Validating slots 

With these helpers in place, `validate_slot_usage` now becomes simple. We use `max_slots` to see how much we can carry. 
We then get how many slots we are already using (with `count_slots`) and see if our new `obj`'s size 
would be too much for us. 

## `.add` and `.remove`

We will make it so `.add` puts something in the `BACKPACK` location and `remove` drops it, wherever
it is (even if it was in your hands).

```python 
# mygame/evadventure/equipment.py 

from .enums import WieldLocation, Ability

# ... 

class EquipmentHandler: 

    # ... 
     
    def add(self, obj):
        """
        Put something in the backpack.
        """
        self.validate_slot_usage(obj)
        self.slots[WieldLocation.BACKPACK].append(obj)
        self._save()

    def remove(self, slot):
        """
        Remove contents of a particular slot, for
        example `equipment.remove(WieldLocation.SHIELD_HAND)`
        """
        slots = self.slots
        ret = []
        if slot is WieldLocation.BACKPACK:
            # empty entire backpack! 
            ret.extend(slots[slot])
            slots[slot] = []
        else:
            ret.append(slots[slot])
            slots[slot] = None
        if ret:
            self._save()
        return ret
```

Both of these should be straight forward to follow. In `.add`, we make use of `validate_slot_usage` to 
double-check we can actually fit the thing, then we add the item to the backpack. 

In `.delete`, we allow emptying by `WieldLocation` - we figure out what slot it is and return 
the item within (if any). If we gave `BACKPACK` as the slot, we empty the backpack and 
return all items. 

Whenever we change the equipment loadout we must make sure to `._save()` the result, or it will 
be lost after a server reload.

## Moving things around 
 
With the help of `.remove()` and `.add()`  we can get things in and out of the `BACKPACK` equipment 
location. We also need to grab stuff from the backpack and wield or wear it. We add a `.move` method 
on the `EquipmentHandler` to do this:

```python 
# mygame/evadventure/equipment.py 

from .enums import WieldLocation, Ability

# ... 

class EquipmentHandler: 

    # ... 
    
    def move(self, obj): 
         """Move object from backpack to its intended `inventory_use_slot`.""" 
         
        # make sure to remove from equipment/backpack first, to avoid double-adding
        self.remove(obj) 
        
        slots = self.slots
        use_slot = getattr(obj, "inventory_use_slot", WieldLocation.BACKPACK)

        to_backpack = []
        if use_slot is WieldLocation.TWO_HANDS:
            # two-handed weapons can't co-exist with weapon/shield-hand used items
            to_backpack = [slots[WieldLocation.WEAPON_HAND], slots[WieldLocation.SHIELD_HAND]]
            slots[WieldLocation.WEAPON_HAND] = slots[WieldLocation.SHIELD_HAND] = None
            slots[use_slot] = obj
        elif use_slot in (WieldLocation.WEAPON_HAND, WieldLocation.SHIELD_HAND):
            # can't keep a two-handed weapon if adding a one-handed weapon or shield
            to_backpack = [slots[WieldLocation.TWO_HANDS]]
            slots[WieldLocation.TWO_HANDS] = None
            slots[use_slot] = obj
        elif use_slot is WieldLocation.BACKPACK:
            # it belongs in backpack, so goes back to it
            to_backpack = [obj]
        else:
            # for others (body, head), just replace whatever's there
            replaced = [obj]
            slots[use_slot] = obj
       
        for to_backpack_obj in to_backpack:
            # put stuff in backpack
            slots[use_slot].append(to_backpack_obj)
       
        # store new state
        self._save() 
``` 

Here we remember that every `EvAdventureObject` has an `inventory_use_slot` property that tells us where
it goes. So we just need to move the object to that slot, replacing whatever is in that place 
from before. Anything we replace goes back to the backpack. 

## Get everything 

In order to visualize our inventory, we need some method to get everything we are carrying. 


```python 
# mygame/evadventure/equipment.py 

from .enums import WieldLocation, Ability

# ... 

class EquipmentHandler: 

    # ... 

    def all(self):
        """
        Get all objects in inventory, regardless of location.
        """
        slots = self.slots
        lst = [
            (slots[WieldLocation.WEAPON_HAND], WieldLocation.WEAPON_HAND),
            (slots[WieldLocation.SHIELD_HAND], WieldLocation.SHIELD_HAND),
            (slots[WieldLocation.TWO_HANDS], WieldLocation.TWO_HANDS),
            (slots[WieldLocation.BODY], WieldLocation.BODY),
            (slots[WieldLocation.HEAD], WieldLocation.HEAD),
        ] + [(item, WieldLocation.BACKPACK) for item in slots[WieldLocation.BACKPACK]]
        return lst
```

Here we get all the equipment locations and add their contents together into a list of tuples 
`[(item, WieldLocation), ...]`. This is convenient for display.

## Weapon and armor 

It's convenient to have the `EquipmentHandler` easily tell you what weapon is currently wielded 
and what _armor_ level all worn equipment provides. Otherwise you'd need to figure out what item is 
in which wield-slot and to add up armor slots manually every time you need to know. 


```python 
# mygame/evadventure/equipment.py 

from .objects import WeaponEmptyHand
from .enums import WieldLocation, Ability

# ... 

class EquipmentHandler: 

    # ... 
    
    @property
    def armor(self):
        slots = self.slots
        return sum(
            (
                # armor is listed using its defense, so we remove 10 from it
                # (11 is base no-armor value in Knave)
                getattr(slots[WieldLocation.BODY], "armor", 1),
                # shields and helmets are listed by their bonus to armor
                getattr(slots[WieldLocation.SHIELD_HAND], "armor", 0),
                getattr(slots[WieldLocation.HEAD], "armor", 0),
            )
        )

    @property
    def weapon(self):
        # first checks two-handed wield, then one-handed; the two
        # should never appear simultaneously anyhow (checked in `move` method).
        slots = self.slots
        weapon = slots[WieldLocation.TWO_HANDS]
        if not weapon:
            weapon = slots[WieldLocation.WEAPON_HAND]
        if not weapon:
            weapon = WeaponEmptyHand()
        return weapon

```

In the `.armor()` method we get the item (if any) out of each relevant wield-slot (body, shield, head), 
and grab their `armor` Attribute. We then `sum()` them all up. 

In `.weapon()`, we simply check which of the possible weapon slots (weapon-hand or two-hands) have 
something in them. If not we fall back to the 'fake' weapon `WeaponEmptyHand` which is just a 'dummy' 
object that represents your bare hands with damage and all.
(created in [The Object tutorial](./Beginner-Tutorial-Objects.md#your-bare-hands) earlier).


## Extra credits 

This covers the basic functionality of the equipment handler. There are other useful methods that 
can be added: 

- Given an item, figure out which equipment slot it is currently in
- Make a string representing the current loadout
- Get everything in the backpack (only)
- Get all wieldable items (weapons, shields) from backpack 
- Get all usable items (items with a use-location of `BACKPACK`) from the backpack

Experiment with adding those. A full example is found in 
[evennia/contrib/tutorials/evadventure/equipment.py](evennia.contrib.tutorials.evadventure.equipment).

## Unit Testing 

> Create a new module `mygame/evadventure/tests/test_equipment.py`.

```{sidebar}
See [evennia/contrib/tutorials/evadventure/tests/test_equipment.py](evennia.contrib.tutorials.evadventure.tests.test_equipment)
for a finished testing example.
```

To test the `EquipmentHandler`, easiest is create an `EvAdventureCharacter` (this should by now 
have `EquipmentHandler` available on itself as `.equipment`) and a few test objects; then test 
passing these into the handler's methods.


```python 
# mygame/evadventure/tests/test_equipment.py 

from evennia.utils import create 
from evennia.utils.test_resources import BaseEvenniaTest 

from ..objects import EvAdventureRoom
from ..enums import WieldLocation

class TestEquipment(BaseEvenniaTest): 
    
    def setUp(self): 
        self.character = create.create_object(EvAdventureCharacter, key='testchar')
        self.helmet = create.create_object(EvAdventureHelmet, key="helmet") 
        self.weapon = create.create_object(EvAdventureWeapon, key="weapon") 
         
    def test_add_remove): 
        self.character.equipment.add(self.helmet)
        self.assertEqual(
            self.character.equipment.slots[WieldLocation.BACKPACK],
            [self.helmet]
        )
        self.character.equipment.remove(self.helmet)
        self.assertEqual(self.character.equipment.slots[WieldLocation.BACKPACK], []) 
        
    # ... 
```

## Summary 

_Handlers_ are useful for grouping functionality together. Now that we spent our time making the 
`EquipmentHandler`, we shouldn't need to worry about item-slots anymore - the handler 'handles' all 
the details for us. As long as we call its methods, the details can be forgotten about.

We also learned to use _hooks_ to tie _Knave_'s custom equipment handling into Evennia.

With `Characters`, `Objects` and now `Equipment` in place, we should be able to move on to character
generation - where players get to make their own character!