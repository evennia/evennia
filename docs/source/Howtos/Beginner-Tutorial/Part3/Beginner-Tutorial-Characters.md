# Player Characters

In the [previous lesson about rules and dice rolling](Beginner-Gutorial-Rules) we made some assumptions
about the "Player Character" entity: 

- It should store Abilities on itself as `character.strength`, `character.constitution` etc.
- It should have a `.heal(amount)`  method.

So we have some guidelines of how it should look! A Character is a database entity with values that 
should be able to be changed over time. It makes sense to base it off Evennia's 
[DefaultCharacter Typeclass](../../../Components/Typeclasses.md). The Character class is like a 'character sheet' in a tabletop 
RPG, it will hold everything relevant to that PC.

## Inheritance structure

Player Characters (PCs) are not the only "living" things in our world. We also have _NPCs_ 
(like shopkeepers and other friendlies) as well as _monsters_ (mobs) that can attack us. 

In code, there are a few ways we could structure this. If NPCs/monsters were just special cases of PCs, 
we could use a class inheritance like this: 

```python
from evennia import DefaultCharacter 

class EvAdventureCharacter(DefaultCharacter): 
    # stuff 
    
class EvAdventureNPC(EvAdventureCharacter):
    # more stuff 
    
class EvAdventureMob(EvAdventureNPC): 
    # more stuff 
```

All code we put on the `Character` class would now be inherited to `NPC` and `Mob` automatically. 

However, in _Knave_, NPCs and particularly monsters are _not_ using the same rules as PCs - they are 
simplified to use a Hit-Die (HD) concept. So while still character-like, NPCs should be separate from 
PCs like this:

```python
from evennia import DefaultCharacter 

class EvAdventureCharacter(DefaultCharacter): 
    # stuff 

class EvAdventureNPC(DefaultCharacter):
    # separate stuff 
    
class EvAdventureMob(EvadventureNPC):
    # more separate stuff
```

Nevertheless, there are some things that _should_ be common for all 'living things':

- All can take damage.
- All can die.
- All can heal
- All can hold and lose coins
- All can loot their fallen foes.
- All can get looted when defeated.

We don't want to code this separately for every class but we no longer have a common parent 
class to put it on. So instead we'll use the concept of a _mixin_ class:

```python 
from evennia import DefaultCharacter 

class LivingMixin:
    # stuff common for all living things

class EvAdventureCharacter(LivingMixin, DefaultCharacter): 
    # stuff 

class EvAdventureNPC(LivingMixin, DefaultCharacter):
    # stuff 
    
class EvAdventureMob(LivingMixin, EvadventureNPC):
    # more stuff
```

```{sidebar}
In [evennia/contrib/tutorials/evadventure/characters.py](evennia.contrib.tutorials.evadventure.characters)
is an example of a character class structure.
```
Above, the `LivingMixin` class cannot work on its own - it just 'patches' the other classes with some 
extra functionality all living things should be able to do. This is an example of 
_multiple inheritance_. It's useful to know about, but one should not over-do multiple inheritance 
since it can also get confusing to follow the code.

## Living mixin class

> Create a new module `mygame/evadventure/characters.py`

Let's get some useful common methods all living things should have in our game.

```python 
# in mygame/evadventure/characters.py 

from .rules import dice 

class LivingMixin:

    # makes it easy for mobs to know to attack PCs
    is_pc = False  

    def heal(self, hp): 
        """ 
        Heal hp amount of health, not allowing to exceed our max hp
         
        """ 
        damage = self.hp_max - self.hp 
        healed = min(damage, hp) 
        self.hp += healed 
        
        self.msg("You heal for {healed} HP.") 
        
    def at_pay(self, amount):
        """When paying coins, make sure to never detract more than we have"""
        amount = min(amount, self.coins)
        self.coins -= amount
        return amount
        
    def at_damage(self, damage, attacker=None):
        """Called when attacked and taking damage."""
        self.hp -= damage  
        
    def at_defeat(self): 
        """Called when defeated. By default this means death."""
        self.at_death()
        
    def at_death(self):
        """Called when this thing dies."""
        # this will mean different things for different living things
        pass 
        
    def at_do_loot(self, looted):
        """Called when looting another entity""" 
        looted.at_looted(self)
        
    def at_looted(self, looter):
        """Called when looted by another entity""" 
        
        # default to stealing some coins 
        max_steal = dice.roll("1d10") 
        stolen = self.at_pay(max_steal)
        looter.coins += stolen

```
Most of these are empty since they will behave differently for characters and npcs. But having them 
in the mixin means we can expect these methods to be available for all living things.


## Character class 

We will now start making the basic Character class, based on what we need from _Knave_.

```python
# in mygame/evadventure/characters.py

from evennia import DefaultCharacter, AttributeProperty
from .rules import dice 

class LivingMixin:
    # ... 


class EvAdventureCharacter(LivingMixin, DefaultCharacter):
    """ 
    A character to use for EvAdventure. 
    """
    is_pc = True 

    strength = AttributeProperty(1) 
    dexterity = AttributeProperty(1)
    constitution = AttributeProperty(1)
    intelligence = AttributeProperty(1)
    wisdom = AttributeProperty(1)
    charisma = AttributeProperty(1)
    
    hp = AttributeProperty(8) 
    hp_max = AttributeProperty(8)
    
    level = AttributeProperty(1)
    xp = AttributeProperty(0)
    coins = AttributeProperty(0)

    def at_defeat(self):
        """Characters roll on the death table"""
        if self.location.allow_death:
            # this allow rooms to have non-lethal battles
            dice.roll_death(self)
        else:
            self.location.msg_contents(
                "$You() $conj(collapse) in a heap, alive but beaten.",
                from_obj=self)
            self.heal(self.hp_max)
            
    def at_death(self):
        """We rolled 'dead' on the death table."""
        self.location.msg_contents(
            "$You() collapse in a heap, embraced by death.",
            from_obj=self) 
        # TODO - go back into chargen to make a new character!            
```

We make an assumption about our rooms here - that they have a property `.allow_death`. We need 
to make a note to actually add such a property to rooms later!

In our `Character` class we implement all attributes we want to simulate from the _Knave_ ruleset.
The `AttributeProperty` is one way to add an Attribute in a field-like way; these will be accessible 
on every character in several ways: 

- As `character.strength`
- As `character.db.strength`
- As `character.attributes.get("strength")`

See [Attributes](../../../Components/Attributes.md) for seeing how Attributes work.

Unlike in base _Knave_, we store `coins` as a separate Attribute rather than as items in the inventory,
this makes it easier to handle barter and trading later.

We implement the Player Character versions of `at_defeat` and `at_death`. We also make use of `.heal()` 
from the `LivingMixin` class. 

### Funcparser inlines

This piece of code is worth some more explanation:

```python
self.location.msg_contents(
    "$You() $conj(collapse) in a heap, alive but beaten.",
    from_obj=self)
```

Remember that `self` is the Character instance here. So `self.location.msg_contents` means "send a 
message to everything inside my current location". In other words, send a message to everyone 
in the same place as the character.

The `$You() $conj(collapse)` are [Funcparser inlines](Funcparser). These are functions that execute 
in the string. The resulting string may look different for different audiences. The `$You()` inline 
function will use `from_obj` to figure out who 'you' are and either show your name or 'You'. 
The `$conj()` (verb conjugator) will tweak the (English) verb to match.

- You will see: `"You collapse in a heap, alive but beaten."`
- Others in the room will see: `"Thomas collapses in a heap, alive but beaten."`

Note how `$conj()` chose `collapse/collapses` to make the sentences grammatically correct.

### Backtracking

We make our first use of the `rules.dice` roller to roll on the death table! As you may recall, in the
previous lesson, we didn't know just what to do when rolling 'dead' on this table. Now we know - we
should be calling `at_death` on the character. So let's add that where we had TODOs before:

```python 
# mygame/evadventure/rules.py 

class EvAdventureRollEngine:
    
    # ... 

    def roll_death(self, character): 
        ability_name = self.roll_random_table("1d8", death_table)

        if ability_name == "dead":
            # kill the character!
            character.at_death()  # <------ TODO no more
        else: 
            # ... 
                        
            if current_ability < -10: 
                # kill the character!
                character.at_death()  # <------- TODO no more
            else:
                # ... 
```


## Unit Testing 

> Create a new module `mygame/evadventure/tests/test_characters.py`

For testing, we just need to create a new EvAdventure character and check 
that calling the methods on it doesn't error out. 

```python
# mygame/evadventure/tests/test_characters.py 

from evennia.utils import create
from evennia.utils.test_resources import BaseEvenniaTest 

from ..characters import EvAdventureCharacter 

class TestCharacters(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        self.character = create.create_object(EvAdventureCharacter, key="testchar")

    def test_heal(self):
        self.character.hp = 0 
        self.character.hp_max = 8 
        
        self.character.heal(1)
        self.assertEqual(self.character.hp, 1)
        # make sure we can't heal more than max
        self.character.heal(100)
        self.assertEqual(self.character.hp, 8)
        
    def test_at_pay(self):
        self.character.coins = 100 
        
        result = self.character.at_pay(60)
        self.assertEqual(result, 60) 
        self.assertEqual(self.character.coins, 40)
        
        # can't get more coins than we have 
        result = self.character.at_pay(100)
        self.assertEqual(result, 40)
        self.assertEqual(self.character.coins, 0)
        
    # tests for other methods ... 

```
If you followed the previous lessons, these tests should look familiar. Consider adding 
tests for other methods as practice. Refer to previous lessons for details. 

For running the tests you do: 

     evennia test --settings settings.py .evadventure.tests.test_character

## Summary


With the `EvAdventureCharacter` class in place, we have a better understanding of how our PCs will look 
like under _Knave_. 

For now, we only have bits and pieces and haven't been testing this code in-game. But if you want 
you can swap yourself into `EvAdventureCharacter` right now. Log into your game and run
the command 

    type self = evadventure.characters.EvAdventureCharacter 

If all went well, `ex self` will now show your typeclass as being `EvAdventureCharacter`. 
Check out your strength with 

    py self.strength = 3

```{important}
When doing `ex self` you will _not_ see all your Abilities listed yet. That's because 
Attributes added with `AttributeProperty` are not available until they have been accessed at 
least once. So once you set (or look at) `.strength` above, `strength` will show in `examine` from 
then on.
```
