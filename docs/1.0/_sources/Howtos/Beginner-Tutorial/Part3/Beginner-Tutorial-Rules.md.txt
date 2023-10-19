# Rules and dice rolling

In _EvAdventure_ we have decided to use the [Knave](https://www.drivethrurpg.com/product/250888/Knave) 
RPG ruleset. This is commercial, but released under Creative Commons 4.0, meaning it's okay to share and 
adapt _Knave_ for any purpose, even commercially. If you don't want to buy it but still follow 
along, you can find a [free fan-version here](http://abominablefancy.blogspot.com/2018/10/knaves-fancypants.html).

## Summary of _Knave_ rules

Knave, being inspired by early Dungeons & Dragons, is very simple. 

- It uses six Ability bonuses
_Strength_ (STR), _Dexterity_ (DEX), _Constitution_ (CON), _Intelligence_ (INT), _Wisdom_ (WIS)
and _Charisma_ (CHA). These are rated from `+1` to `+10`.
- Rolls are made with a twenty-sided die (`1d20`), usually adding a suitable Ability bonus to the roll.
- If you roll _with advantage_, you roll `2d20` and pick the 
_highest_ value, If you roll _with disadvantage_, you roll `2d20` and pick the _lowest_. 
- Rolling a natural `1` is a _critical failure_. A natural `20` is a _critical success_. Rolling such
in combat means your weapon or armor loses quality, which will eventually destroy it.
- A _saving throw_ (trying to succeed against the environment) means making a roll to beat `15` (always).
So if you are lifting a heavy stone and have `STR +2`, you'd roll `1d20 + 2` and hope the result
is higher than `15`. 
- An _opposed saving throw_ means beating the enemy's suitable Ability 'defense', which is always their 
`Ability bonus + 10`. So if you have `STR +1` and are arm wrestling someone with `STR +2`, you roll
`1d20 + 1` and hope to roll higher than `2 + 10 = 12`. 
- A special bonus is `Armor`, `+1` is unarmored, additional armor is given by equipment. Melee attacks 
test `STR` versus the `Armor` defense value while ranged attacks uses `WIS` vs `Armor`.
- _Knave_ has no skills or classes. Everyone can use all items and using magic means having a special 
'rune stone' in your hands; one spell per stone and day.
- A character has `CON + 10` carry 'slots'. Most normal items uses one slot, armor and large weapons uses
two or three.
- Healing is random, `1d8 + CON` health healed after food and sleep.
- Monster difficulty is listed by hy many 1d8 HP they have; this is called their "hit die" or HD. If
needing to test Abilities, monsters have HD bonus in every Ability.
- Monsters have a _morale rating_. When things go bad, they have a chance to panic and flee if 
rolling `2d6` over their morale rating.
- All Characters in _Knave_ are mostly randomly generated. HP is `<level>d8` but we give every 
new character max HP to start. 
- _Knave_ also have random tables, such as for starting equipment and to see if dying when 
hitting 0. Death, if it happens, is permanent.


## Making a rule module 

> Create a new module mygame/evadventure/rules.py 

```{sidebar}
A complete version of the rule module is found in 
[evennia/contrib/tutorials/evadventure/rules.py](../../../api/evennia.contrib.tutorials.evadventure.rules.md).
```
There are three broad sets of rules for most RPGS:

- Character generation rules, often only used during character creation
- Regular gameplay rules - rolling dice and resolving game situations
- Character improvement - getting and spending experience to improve the character

We want our `rules` module to cover as many aspeects of what we'd otherwise would have to look up 
in a rulebook. 


## Rolling dice 

We will start by making a dice roller. Let's group all of our dice rolling into a structure like this
(not functional code yet): 

```python 
class EvAdventureRollEngine:

   def roll(...):
       # get result of one generic roll, for any type and number of dice
       
   def roll_with_advantage_or_disadvantage(...)
       # get result of normal d20 roll, with advantage/disadvantage (or not)
       
   def saving_throw(...):
       # do a saving throw against a specific target number
       
   def opposed_saving_throw(...):
       # do an opposed saving throw against a target's defense

   def roll_random_table(...):
       # make a roll against a random table (loaded elsewere)
  
   def morale_check(...):
       # roll a 2d6 morale check for a target
      
   def heal_from_rest(...):
       # heal 1d8 when resting+eating, but not more than max value.
       
   def roll_death(...):
       # roll to determine penalty when hitting 0 HP. 
       
       
dice = EvAdventureRollEngine() 
       
```
```{sidebar}
This groups all dice-related code into one 'container' that is easy to import. But it's mostly a matter 
of taste. You _could_ also break up the class' methods into normal functions at the top-level of the 
module if you wanted.
```

This structure (called a _singleton_) means we group all dice rolls into one class that we then initiate 
into a variable `dice` at the end of the module. This means that we can do the following from other 
modules: 

```python
    from .rules import dice 

    dice.roll("1d8")
```

### Generic dice roller 

We want to be able to do `roll("1d20")` and get a random result back from the roll. 

```python
# in mygame/evadventure/rules.py 

from random import randint

class EvAdventureRollEngine:
    
    def roll(self, roll_string):
        """ 
        Roll XdY dice, where X is the number of dice 
        and Y the number of sides per die. 
        
        Args:
            roll_string (str): A dice string on the form XdY.
        Returns:
            int: The result of the roll. 
            
        """ 
        
        # split the XdY input on the 'd' one time
        number, diesize = roll_string.split("d", 1)     
        
        # convert from string to integers
        number = int(number) 
        diesize = int(diesize)
            
        # make the roll
        return sum(randint(1, diesize) for _ in range(number))
```

```{sidebar}
For this tutorial we have opted to not use any contribs, so we create 
our own dice roller. But normally you could instead use the [dice](../../../Contribs/Contrib-Dice.md) contrib for this. 
We'll point out possible helpful contribs in sidebars as we proceed.
```

The `randint` standard Python library module produces a random integer  
in a specific range. The line 

```python 
sum(randint(1, diesize) for _ in range(number))
```
works like this: 

- For a certain `number` of times ... 
- ... create a random integer between `1` and `diesize` ...
- ... and `sum` all those integers together.

You could write the same thing less compactly like this:

```python 
rolls = []
for _ in range(number): 
   random_result = randint(1, diesize)
   rolls.append(random_result)
return sum(rolls)
```

```{sidebar}
Note that `range` generates a value `0...number-1`. We use `_` in the `for` loop to 
indicate we don't really care what this value is - we just want to repeat the loop 
a certain amount of times.
```

We don't ever expect end users to call this method; if we did, we would have to validate the inputs 
much more - We would have to make sure that `number` or `diesize` are valid inputs and not 
crazy big so the loop takes forever!

### Rolling with advantage 

Now that we have the generic roller, we can start using it to do a more complex roll. 

```
# in mygame/evadventure/rules.py 

# ... 

class EvAdventureRollEngine:

    def roll(roll_string):
        # ... 
    
    def roll_with_advantage_or_disadvantage(self, advantage=False, disadvantage=False):
        
        if not (advantage or disadvantage) or (advantage and disadvantage):
            # normal roll - advantage/disadvantage not set or they cancel 
            # each other out 
            return self.roll("1d20")
        elif advantage:
             # highest of two d20 rolls
             return max(self.roll("1d20"), self.roll("1d20"))
        else:
             # disadvantage - lowest of two d20 rolls 
             return min(self.roll("1d20"), self.roll("1d20"))
```

The `min()` and `max()` functions are standard Python fare for getting the biggest/smallest
of two arguments.

### Saving throws 

We want the saving throw to itself figure out if it succeeded or not. This means it needs to know 
the Ability bonus (like STR `+1`). It would be convenient if we could just pass the entity 
doing the saving throw to this method, tell it what type of save was needed, and then 
have it figure things out: 

```python 
result, quality = dice.saving_throw(character, Ability.STR)
```
The return will be a boolean `True/False` if they pass, as well as a `quality` that tells us if 
a perfect fail/success was rolled or not.

To make the saving throw method this clever, we need to think some more about how we want to store our 
data on the character. 

For our purposes it sounds reasonable that we will be using [Attributes](../../../Components/Attributes.md) for storing 
the Ability scores. To make it easy, we will name them the same as the 
[Enum values](./Beginner-Tutorial-Utilities.md#enums) we set up in the previous lesson. So if we have 
an enum `STR = "strength"`, we want to store the Ability on the character as an Attribute `strength`.

From the Attribute documentation, we can see that we can use `AttributeProperty` to make it so the 
Attribute is available as `character.strength`, and this is what we will do. 

So, in short, we'll create the saving throws method with the assumption that we will be able to do 
`character.strength`, `character.constitution`, `character.charisma` etc to get the relevant Abilities.

```python 
# in mygame/evadventure/rules.py 
# ...
from .enums import Ability

class EvAdventureRollEngine: 

   def roll(...)
       # ...
   
   def roll_with_advantage_or_disadvantage(...)
       # ...
       
   def saving_throw(self, character, bonus_type=Ability.STR, target=15, 
                    advantage=False, disadvantage=False):
       """ 
       Do a saving throw, trying to beat a target.
       
       Args:
          character (Character): A character (assumed to have Ability bonuses
              stored on itself as Attributes).
          bonus_type (Ability): A valid Ability bonus enum.
          target (int): The target number to beat. Always 15 in Knave.
          advantage (bool): If character has advantage on this roll.
          disadvantage (bool): If character has disadvantage on this roll.
          
       Returns:
           tuple: A tuple (bool, Ability), showing if the throw succeeded and 
               the quality is one of None or Ability.CRITICAL_FAILURE/SUCCESS
               
       """
                    
       # make a roll 
       dice_roll = self.roll_with_advantage_or_disadvantage(advantage, disadvantage)
       
       # figure out if we had critical failure/success
       quality = None
       if dice_roll == 1:
           quality = Ability.CRITICAL_FAILURE
       elif dice_roll == 20:
           quality = Ability.CRITICAL_SUCCESS 

       # figure out bonus
       bonus = getattr(character, bonus_type.value, 1) 

       # return a tuple (bool, quality)
       return (dice_roll + bonus) > target, quality
```

The `getattr(obj, attrname, default)` function is a very useful Python tool for getting an attribute 
off an object and getting a default value if the attribute is not defined.

### Opposed saving throw 

With the building pieces we already created, this method is simple. Remember that the defense you have 
to beat is always the relevant bonus + 10 in _Knave_. So if the enemy defends with `STR +3`, you must 
roll higher than `13`.

```python
# in mygame/evadventure/rules.py 

from .enums import Ability

class EvAdventureRollEngine:
    
    def roll(...):
        # ... 

    def roll_with_advantage_or_disadvantage(...):
        # ... 

    def saving_throw(...):
        # ... 

    def opposed_saving_throw(self, attacker, defender, 
                             attack_type=Ability.STR, defense_type=Ability.ARMOR,
                             advantage=False, disadvantage=False):
        defender_defense = getattr(defender, defense_type.value, 1) + 10 
        result, quality = self.saving_throw(attacker, bonus_type=attack_type,
                                            target=defender_defense, 
                                            advantage=advantave, disadvantage=disadvantage)
        
        return result, quality 
```

### Morale check 

We will make the assumption that the `morale` value is available from the creature simply as 
`monster.morale` - we need to remember to make this so later! 

In _Knave_, a creature have roll with `2d6` equal or under its morale to not flee or surrender
when things go south. The standard morale value is 9.

```python 
# in mygame/evadventure/rules.py 

class EvAdventureRollEngine:

    # ...
    
    def morale_check(self, defender): 
        return self.roll("2d6") <= getattr(defender, "morale", 9)
    
```

### Roll for Healing 

To be able to handle healing, we need to make some more assumptions about how we store 
health on game entities. We will need `hp_max` (the total amount of available HP) and `hp`
(the current health value). We again assume these will be available as `obj.hp` and `obj.hp_max`.

According to the rules, after consuming a ration and having a full night's sleep, a character regains 
`1d8 + CON` HP. 

```python 
# in mygame/evadventure/rules.py 

from .enums import Ability

class EvAdventureRollEngine: 

    # ... 
    
    def heal_from_rest(self, character): 
        """ 
        A night's rest retains 1d8 + CON HP  
        
        """
        con_bonus = getattr(character, Ability.CON.value, 1)
        character.heal(self.roll("1d8") + con_bonus)
```

We make another assumption here - that `character.heal()` is a thing. We tell this function how 
much the character should heal, and it will do so, making sure to not heal more than its max 
number of HPs

> Knowing what is available on the character and what rule rolls we need is a bit of a chicken-and-egg 
> problem. We will make sure to implement the matching _Character_ class next lesson.


### Rolling on a table 

We occasionally need to roll on a 'table' - a selection of choices. There are two main table-types
we need to support:

Simply one element per row of the table (same odds to get each result).

| Result |
|:------:|
| item1  |
| item2  | 
| item3  | 
| item4  | 

This we will simply represent as a plain list 
    
```python
["item1", "item2", "item3", "item4"]
```

Ranges per item (varying odds per result):

| Range | Result | 
|:-----:|:------:|
|  1-5  | item1  |
| 6-15  | item2  |
| 16-19 | item3  |
|  20   | item4  |

This we will represent as a list of tuples: 

```python
[("1-5", "item1"), ("6-15", "item2"), ("16-19", "item4"), ("20", "item5")]
```

We also need to know what die to roll to get a result on the table (it may not always 
be obvious, and in some games you could be asked to roll a lower dice to only get 
early table results, for example).

```python
# in mygame/evadventure/rules.py 

from random import randint, choice

class EvAdventureRollEngine:
    
    # ... 

    def roll_random_table(self, dieroll, table_choices): 
        """ 
        Args: 
             dieroll (str): A die roll string, like "1d20".
             table_choices (iterable): A list of either single elements or 
                of tuples.
        Returns: 
            Any: A random result from the given list of choices.
            
        Raises:
            RuntimeError: If rolling dice giving results outside the table.
            
        """
        roll_result = self.roll(dieroll) 
        
        if isinstance(table_choices[0], (tuple, list)):
            # the first element is a tuple/list; treat as on the form [("1-5", "item"),...]
            for (valrange, choice) in table_choices:
                minval, *maxval = valrange.split("-", 1)
                minval = abs(int(minval))
                maxval = abs(int(maxval[0]) if maxval else minval)
                
                if minval <= roll_result <= maxval:
                    return choice 
                
            # if we get here we must have set a dieroll producing a value 
            # outside of the table boundaries - raise error
            raise RuntimeError("roll_random_table: Invalid die roll")
        else:
            # a simple regular list
            roll_result = max(1, min(len(table_choices), roll_result))
            return table_choices[roll_result - 1]
```
Check that you understand what this does.

This may be confusing: 
```python
minval, *maxval = valrange.split("-", 1)
minval = abs(int(minval))
maxval = abs(int(maxval[0]) if maxval else minval)
```

If `valrange` is the string `1-5`, then `valrange.split("-", 1)` would result in a tuple `("1", "5")`. 
But if the string was in fact just `"20"` (possible for a single entry in an RPG table), this would 
lead to an error since it would only split out a single element - and we expected two. 

By using `*maxval` (with the `*`), `maxval` is told to expect _0 or more_ elements in a tuple. 
So the result for `1-5` will be `("1", ("5",))` and for `20` it will become `("20", ())`. In the line 

```python
maxval = abs(int(maxval[0]) if maxval else minval)
```

we check if `maxval` actually has a value `("5",)` or if its empty `()`. The result is either 
`"5"` or the value of `minval`.


### Roll for death 

While original Knave suggests hitting 0 HP means insta-death, we will grab the optional "death table"
from the "prettified" Knave's optional rules to make it a little less punishing. We also changed the 
result of `2` to 'dead' since we don't simulate 'dismemberment' in this tutorial:

| Roll |  Result  | -1d4 Loss of Ability | 
|:---: |:--------:|:--------------------:|
| 1-2  |   dead   |          -           
| 3 | weakened |         STR          | 
|4 | unsteady |         DEX          | 
| 5 | sickly |         CON          | 
| 6 | addled |         INT          | 
| 7 | rattled |         WIS          | 
| 8 | disfigured |         CHA          |

All the non-dead values map to a loss of 1d4 in one of the six Abilities (but you get HP back).
We need to map back to this from the above table. One also cannot have less than -10 Ability bonus, 
if you do, you die too.

```python 
# in mygame/evadventure/rules.py 

death_table = (
    ("1-2", "dead"),
    ("3": "strength",
    ("4": "dexterity"),
    ("5": "constitution"),
    ("6": "intelligence"),
    ("7": "wisdom"),
    ("8": "charisma"),
)
    
    
class EvAdventureRollEngine:
    
    # ... 

    def roll_random_table(...)
        # ... 
        
    def roll_death(self, character): 
        ability_name = self.roll_random_table("1d8", death_table)

        if ability_name == "dead":
            # TODO - kill the character! 
            pass 
        else: 
            loss = self.roll("1d4")
            
            current_ability = getattr(character, ability_name)
            current_ability -= loss
            
            if current_ability < -10: 
                # TODO - kill the character!
                pass 
            else:
                # refresh 1d4 health, but suffer 1d4 ability loss
                self.heal(character, self.roll("1d4") 
                setattr(character, ability_name, current_ability)
                
                character.msg(
                    "You survive your brush with death, and while you recover "
                    f"some health, you permanently lose {loss} {ability_name} instead."
                )
                
dice = EvAdventureRollEngine()
```

Here we roll on the 'death table' from the rules to see what happens. We give the character 
a message if they survive, to let them know what happened.

We don't yet know what 'killing the character' technically means, so we mark this as `TODO` and 
return to it in a later lesson. We just know that we need to do _something_ here to kill off the 
character!

## Testing 

> Make a new module `mygame/evadventure/tests/test_rules.py`

Testing the `rules` module will also showcase some very useful tools when testing. 

```python 
# mygame/evadventure/tests/test_rules.py 

from unittest.mock import patch 
from evennia.utils.test_resources import BaseEvenniaTest
from .. import rules 

class TestEvAdventureRuleEngine(BaseEvenniaTest):
   
    def setUp(self):
        """Called before every test method"""
        super().setUp()
        self.roll_engine = rules.EvAdventureRollEngine()
    
    @patch("evadventure.rules.randint")
    def test_roll(self, mock_randint):
        mock_randint.return_value = 4 
        self.assertEqual(self.roll_engine.roll("1d6", 4)     
        self.assertEqual(self.roll_engine.roll("2d6", 2 * 4)     
        
    # test of the other rule methods below ...
```

As before, run the specific test with 

    evennia test --settings settings.py .evadventure.tests.test_rules

### Mocking and patching

```{sidebar}
In [evennia/contrib/tutorials/evadventure/tests/test_rules.py](../../../api/evennia.contrib.tutorials.evadventure.tests.test_rules.md)
has a complete example of rule testing.
```
The `setUp` method is a special method of the testing class. It will be run before every 
test method. We use `super().setUp()` to make sure the parent class' version of this method 
always fire. Then we create a fresh `EvAdventureRollEngine` we can test with. 

In our test, we import `patch` from the `unittest.mock` library. This is a very useful tool for testing. 
Normally the `randint` function we imported in `rules` will return a random value. That's very hard to 
test for, since the value will be different every test.

With `@patch` (this is called a _decorator_), we temporarily replace `rules.randint` with a 'mock' - a 
dummy entity. This mock is passed into the testing method. We then take this `mock_randint` and set 
`.return_value = 4` on it. 

Adding `return_value` to the mock means that every time this mock is called, it will return 4. For the 
duration of the test we can now check with `self.assertEqual` that our `roll` method always returns a 
result as-if the random result was 4.

There are [many resources for understanding mock](https://realpython.com/python-mock-library/), refer to 
them for further help.

> The `EvAdventureRollEngine` have many methods to test. We leave this as an extra exercise!

## Summary 

This concludes all the core rule mechanics of _Knave_ - the rules used during play. We noticed here 
that we are going to soon need to establish how our _Character_ actually stores data. So we will 
address that next.





