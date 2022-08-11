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

In default Evennia, everything you pick up will end up "inside" your character object (that is, have
you as its `.location`). This is called your _inventory_ and has no limit. We will keep 'moving items into us'
when we pick them up, but we will add more functionality using an _Equipment handler_.

```{sidebar}
If you want to understand more about behind how Evennia uses handlers, there is a 
[dedicated tutorial](../../Tutorial-Persistent-Handler.md) talking about the principle.
```

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

After reloading the server, the equipment-handler will now be accessible on the character as

    character.equipment

The `@lazy_property` works such that it will not load the handler until it is first accessed. When that 
happens, we start up the handler and feed it `self` (the Character itself). This is what enters `__init__`
as `.obj` in the `EquipmentHandler` code above.

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

We already made `EquipmentHandler` available on the Character as `.equipment`. Now we want it to come into 
play automatically whenever we pick up or drop something. To do this we need to override two hooks
on the Character class: 

```python 
# mygame/evadventure/character.py 

# ... 

class EvAdventureCharacter(LivingMixin, DefaultCharacter): 

    # ... 
    
    def at_pre_object_receive(self, moved_object, source_location, **kwargs): 
        """Called by Evennia before object arrives 'in' this character (that is,
        if they pick up something). If it returns False, move is aborted.
        
        """ 
        # we haven't written this yet!
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




