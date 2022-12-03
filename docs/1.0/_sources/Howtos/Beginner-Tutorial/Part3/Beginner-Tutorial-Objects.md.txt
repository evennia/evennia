# In-game Objects and items

In the previous lesson we established what a 'Character' is in our game. Before we continue 
we also need to have a notion what an 'item' or 'object' is. 

Looking at _Knave_'s item lists, we can get some ideas of what we need to track: 

- `size` - this is how many 'slots' the item uses in the character's inventory.
- `value` - a base value if we want to sell or buy the item. 
- `inventory_use_slot` - some items can be worn or wielded. For example, a helmet needs to be 
worn on the head and a shield in the shield hand. Some items can't be used this way at all, but 
only belong in the backpack.
- `obj_type` - Which 'type' of item this is.
  

## New Enums 

We added a few enumberations for Abilities back in the [Utilities tutorial](./Beginner-Tutorial-Utilities.md).
Before we continue, let's expand with enums for use-slots and object types.

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

class ObjType(Enum):
    
    WEAPON = "weapon"
    ARMOR = "armor"
    SHIELD = "shield"
    HELMET = "helmet"
    CONSUMABLE = "consumable"
    GEAR = "gear"
    MAGIC = "magic"
    QUEST = "quest"
    TREASURE = "treasure"
```

Once we have these enums, we will use them for referencing things.

## The base object

> Create a new module `mygame/evadventure/objects.py`

```{sidebar}
[evennia/contrib/tutorials/evadventure/objects.py](../../../api/evennia.contrib.tutorials.evadventure.objects.md) has 
a full set of objects implemented.
```
<div style="clear: right;"></div>

We will make a base `EvAdventureObject` class off Evennia's standard `DefaultObject`. We will then add 
child classes to represent the relevant types: 

```python 
# mygame/evadventure/objects.py

from evennia import AttributeProperty, DefaultObject 
from evennia.utils.utils import make_iter
from .utils import get_obj_stats 
from .enums import WieldLocation, ObjType


class EvAdventureObject(DefaultObject): 
    """ 
    Base for all evadventure objects. 
    
    """ 
    inventory_use_slot = WieldLocation.BACKPACK
    size = AttributeProperty(1, autocreate=False)
    value = AttributeProperty(0, autocreate=False)
    
    # this can be either a single type or a list of types (for objects able to be 
    # act as multiple). This is used to tag this object during creation.
    obj_type = ObjType.GEAR
    
    def at_object_creation(self): 
        """Called when this object is first created. We convert the .obj_type 
        property to a database tag."""
        
        for obj_type in make_iter(self.obj_type):
            self.tags.add(self.obj_type.value, category="obj_type")
        
    def get_help(self):
        """Get any help text for this item"""
        return "No help for this item"
```

### Using Attributes or not

In theory, `size` and `value` does not change and _could_ also be just set as a regular Python 
property on the class: 

```python 
class EvAdventureObject(DefaultObject):
    inventory_use_slot = WieldLocation.BACKPACK 
    size = 1 
    value = 0 
```

The problem with this is that if we want to make a new object of `size 3` and `value 20`, we have to 
make a new class for it. We can't change it on the fly because the change would only be in memory and 
be lost on next server reload. 

Because we use `AttributeProperties`, we can set `size` and `value` to whatever we like when we 
create the object (or later), and the Attributes will remember our changes to that object indefinitely.

To make this a little more efficient, we use `autocreate=False`. Normally when you create a
new object with defined `AttributeProperties`, a matching `Attribute` is immediately created at 
the same time. So normally, the object would be created along with two Attributes `size` and `value`.
With `autocreate=False`, no Attribute will be created _unless the default is changed_. That is, as 
long as your object has `size=1` no database `Attribute` will be created at all. This saves time and 
resources when creating large number of objects.

The drawback is that since no Attribute is created you can't refer to it
with `obj.db.size` or `obj.attributes.get("size")` _unless you change its default_. You also can't query 
the database for all objects with `size=1`, since most objects would not yet have an in-database
`size` Attribute to search for.

In our case, we'll only refer to these properties as `obj.size` etc, and have no need to find 
all objects of a particular size. So we should be safe.

### Creating tags in `at_object_creation`

The `at_object_creation` is a method Evennia calls on every child of `DefaultObject` whenever it is
first created. 

We do a tricky thing here, converting our `.obj_type` to one or more [Tags](../../../Components/Tags.md). Tagging the 
object like this means you can later efficiently find all objects of a given type (or combination of 
types) with Evennia's search functions:

```python
    from .enums import ObjType 
    from evennia.utils import search 
    
    # get all shields in the game
    all_shields = search.search_object_by_tag(ObjType.SHIELD.value, category="obj_type")
```

We allow `.obj_type` to be given as a single value or a list of values. We use `make_iter` from the 
evennia utility library to make sure we don't balk at either. This means you could have a Shield that 
is also Magical, for example.

## Other object types 

Some of the other object types are very simple so far. 

```python 
# mygame/evadventure/objects.py 

from evennia import AttributeProperty, DefaultObject
from .enums import ObjType 

class EvAdventureObject(DefaultObject): 
    # ... 
    
    
class EvAdventureQuestObject(EvAdventureObject):
    """Quest objects should usually not be possible to sell or trade."""
    obj_type = ObjType.QUEST
 
class EvAdventureTreasure(EvAdventureObject):
    """Treasure is usually just for selling for coin"""
    obj_type = ObjType.TREASURE
    value = AttributeProperty(100, autocreate=False)
    
```

## Consumables 

A 'consumable' is an item that has a certain number of 'uses'. Once fully consumed, it can't be used 
anymore. An example would be a health potion.


```python 
# mygame/evadventure/objects.py 

# ... 

class EvAdventureConsumable(EvAdventureObject): 
    """An item that can be used up""" 
    
    obj_type = ObjType.CONSUMABLE
    value = AttributeProperty(0.25, autocreate=False)
    uses = AttributeProperty(1, autocreate=False)
    
    def at_pre_use(self, user, *args, **kwargs):
        """Called before using. If returning False, abort use."""
        return uses > 0 
        
    def at_use(self, user, *args, **kwargs):
        """Called when using the item""" 
        pass 
        
    def at_post_use(self. user, *args, **kwargs):
        """Called after using the item""" 
        # detract a usage, deleting the item if used up.
        self.uses -= 1
        if self.uses <= 0: 
            user.msg(f"{self.key} was used up.")
            self.delete()
```

What exactly each consumable does will vary - we will need to implement children of this class 
later, overriding `at_use` with different effects.

## Weapons

All weapons need properties that describe how efficient they are in battle.

```python 
# mygame/evadventure/objects.py 

from .enums import WieldLocation, ObjType, Ability

# ... 

class EvAdventureWeapon(EvAdventureObject): 
    """Base class for all weapons"""

    obj_type = ObjType.WEAPON 
    inventory_use_slot = AttributeProperty(WieldLocation.WEAPON_HAND, autocreate=False)
    quality = AttributeProperty(3, autocreate=False)
    
    attack_type = AttibuteProperty(Ability.STR, autocreate=False)
    defend_type = AttibuteProperty(Ability.ARMOR, autocreate=False)
    
    damage_roll = AttibuteProperty("1d6", autocreate=False)
```

The `quality` is something we need to track in _Knave_. When getting critical failures on attacks, 
a weapon's quality will go down. When it reaches 0, it will break. 

The attack/defend type tracks how we resolve attacks with the weapon, like `roll + STR vs ARMOR + 10`.

## Magic 

In _Knave_, anyone can use magic if they are wielding a rune stone (our name for spell books) in both 
hands. You can only use a rune stone once per rest. So a rune stone is an example of a 'magical weapon'
that is also a 'consumable' of sorts.


```python 
# mygame/evadventure/objects.py 

# ... 
class EvAdventureConsumable(EvAdventureObject): 
    # ... 

class EvAdventureWeapon(EvAdventureObject): 
    # ... 

class EvAdventureRuneStone(EvAdventureWeapon, EvAdventureConsumable): 
    """Base for all magical rune stones"""
    
    obj_type = (ObjType.WEAPON, ObjType.MAGIC)
    inventory_use_slot = WieldLocation.TWO_HANDS  # always two hands for magic
    quality = AttributeProperty(3, autocreate=False)

    attack_type = AttibuteProperty(Ability.INT, autocreate=False)
    defend_type = AttibuteProperty(Ability.DEX, autocreate=False)
    
    damage_roll = AttibuteProperty("1d8", autocreate=False)

    def at_post_use(self, user, *args, **kwargs):
        """Called after usage/spell was cast""" 
        self.uses -= 1 
        # we don't delete the rune stone here, but 
        # it must be reset on next rest.
        
    def refresh(self):
        """Refresh the rune stone (normally after rest)"""
        self.uses = 1
```

We make the rune stone a mix of weapon and consumable. Note that we don't have to add `.uses` 
again, it's inherited from `EvAdventureConsumable` parent. The `at_pre_use` and `at_use` methods 
are also inherited; we only override `at_post_use` since we don't want the runestone to be deleted 
when it runs out of uses.

We add a little convenience method `refresh` - we should call this when the character rests, to 
make the runestone active again.

Exactly what rune stones _do_ will be implemented in the `at_use` methods of subclasses to this 
base class. Since magic in _Knave_ tends to be pretty custom, it makes sense that it will lead to a lot 
of custom code.


## Armor 

Armor, shields and helmets increase the `ARMOR` stat of the character. In _Knave_, what is stored is the 
defense value of the armor (values 11-20). We will instead store the 'armor bonus' (1-10). As we know, 
defending is always `bonus + 10`, so the result will be the same - this means 
we can use `Ability.ARMOR` as any other defensive ability without worrying about a special case.

``
```python 
# mygame/evadventure/objects.py 

# ... 

class EvAdventureAmor(EvAdventureObject): 
    obj_type = ObjType.ARMOR
    inventory_use_slot = WieldLocation.BODY 

    armor = AttributeProperty(1, autocreate=False)
    quality = AttributeProperty(3, autocreate=False)


class EvAdventureShield(EvAdventureArmor):
    obj_type = ObjType.SHIELD
    inventory_use_slot = WieldLocation.SHIELD_HAND 


class EvAdventureHelmet(EvAdventureArmor): 
    obj_type = ObjType.HELMET
    inventory_use_slot = WieldLocation.HEAD
``` 

## Your Bare hands 

This is a 'dummy' object that is not stored in the database. We will use this in the upcoming 
[Equipment tutorial lesson](./Beginner-Tutorial-Equipment.md) to represent when you have 'nothing' 
in your hands. This way we don't need to add any special case for this.

```python
class WeaponEmptyHand:
     obj_type = ObjType.WEAPON
     key = "Empty Fists"
     inventory_use_slot = WieldLocation.WEAPON_HAND
     attack_type = Ability.STR
     defense_type = Ability.ARMOR
     damage_roll = "1d4"
     quality = 100000  # let's assume fists are always available ...
 
     def __repr__(self):
         return "<WeaponEmptyHand>"
```

## Testing and Extra credits 

Remember the `get_obj_stats` function from the [Utility Tutorial](./Beginner-Tutorial-Utilities.md) earlier? 
We had to use dummy-values since we didn't yet know how we would store properties on Objects in the game. 

Well, we just figured out all we need! You can go back and update `get_obj_stats` to properly read the data 
from the object it receives. 

When you change this function you must also update the related unit test - so your existing test becomes a 
nice way to test your new Objects as well! Add more tests showing the output of feeding different object-types
to `get_obj_stats`.

Try it out yourself. If you need help, a finished utility example is found in [evennia/contrib/tutorials/evadventure/utils.py](get_obj_stats).