# Code structure and Utilities 

In this lesson we will set up the file structure for _EvAdventure_. We will make some 
utilities that will be useful later. We will also learn how to write _tests_.

## Folder structure

Create a new folder under your `mygame` folder, named `evadventure`. Inside it, create 
another folder `tests/` and make sure to put empty `__init__.py` files in both. This turns both 
folders into packages Python understands to import from.

```
mygame/
   commands/
   evadventure/         <---
      __init__.py       <---
      tests/            <---
          __init__.py   <---
   __init__.py
   README.md
   server/
   typeclasses/
   web/
   world/

```

Importing anything from inside this folder from anywhere else under `mygame` will be done by 

```python 
# from anywhere in mygame/
from evadventure.yourmodulename import whatever 
```

This is the 'absolute path` type of import. 

Between two modules both in `evadventure/`, you can use a 'relative' import with `.`:

```python 
# from a module inside mygame/evadventure
from .yourmodulename import whatever
```

From e.g. inside `mygame/evadventure/tests/` you can import from one level above using `..`:

```python 
# from mygame/evadventure/tests/ 
from ..yourmodulename import whatever
```


## Enums 

```{sidebar}
A full example of the enum module is found in 
[evennia/contrib/tutorials/evadventure/enums.py](evennia.contrib.tutorials.evadventure.enums).
```
Create a new file `mygame/evadventure/enums.py`.

An [enum](https://docs.python.org/3/library/enum.html) (enumeration) is a way to establish constants
in Python. Best is to show an example: 

```python 
# in a file mygame/evadventure/enums.py

from enum import Enum

class Ability(Enum): 

    STR = "strength"

```

You access an enum like this: 

``` 
# from another module in mygame/evadventure

from .enums import Ability 

Ability.STR   # the enum itself 
Ability.STR.value  # this is the string "strength"

```

Having enums is recommended practice. With them set up, it means we can make sure to refer to the 
same thing every time. Having all enums in one place also means you have a good overview of the 
constants you are dealing with.

The alternative would be to for example pass around a string `"constitution"`. If you mis-spell 
this (`"consitution"`), you would not necessarily know it right away - the error would happen later 
when the string is not recognized. If you make a typo getting `Ability.COM` instead of `Ability.CON`, 
Python will immediately raise an error since this enum is not recognized.

With enums you can also do nice direct comparisons like `if ability is Ability.WIS: <do stuff>`.

Note that the `Ability.STR` enum does not have the actual _value_ of e.g. your Strength. 
It's just a fixed label for the Strength ability.

Here is the `enum.py` module needed for _Knave_. It covers the basic aspects of 
rule systems we need to track (check out the _Knave_ rules. If you use another rule system you'll 
likely gradually expand on your enums as you figure out what you'll need). 

```python 
# mygame/evadventure/enums.py

class Ability(Enum):
    """
    The six base ability-bonuses and other 
    abilities

    """

    STR = "strength"
    DEX = "dexterity"
    CON = "constitution"
    INT = "intelligence"
    WIS = "wisdom"
    CHA = "charisma"
     
    ARMOR = "armor"
    HP = "hp"
    LEVEL = "level"
    XP = "xp"
    
    CRITICAL_FAILURE = "critical_failure"
    CRITICAL_SUCCESS = "critical_success"
    
    ALLEGIANCE_HOSTILE = "hostile"
    ALLEGIANCE_NEUTRAL = "neutral"
    ALLEGIANCE_FRIENDLY = "friendly"
    

class WieldLocation(Enum):
    """
    Wield (or wear) locations.

    """

    # wield/wear location
    BACKPACK = "backpack"
    WEAPON_HAND = "weapon_hand"
    SHIELD_HAND = "shield_hand"
    TWO_HANDS = "two_handed_weapons"
    BODY = "body"  # armor
    HEAD = "head"  # helmets


class ObjType(Enum):
    """
    Object types.

    """

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

Here the `Ability` class holds basic properties of a character sheet, while `WieldLocation` tracks 
equipment and where a character would wield and wear things - since _Knave_ has these, it makes sense 
to track it. Finally we have a set of different `ObjType`s, for differentiate game items. These are 
extracted by reading the _Knave_ object lists and figuring out how they should be categorized.


## Utility module

> Create a new module `mygame/evadventure/utils.py`

```{sidebar}
An example of the utility module is found in 
[evennia/contrib/tutorials/evadventure/utils.py](evennia.contrib.tutorials.evadventure.utils)
```

This is for general functions we may need from all over. In this case we only picture one utility,
a function that produces a pretty display of any object we pass to it.

This is an example of the string we want to see:

```
Chipped Sword 
Value: ~10 coins [wielded in Weapon hand]
 
A simple sword used by mercenaries all over 
the world.
 
Slots: 1, Used from: weapon hand
Quality: 3, Uses: None
Attacks using strength against armor.
Damage roll: 1d6
```

Here's the start of how the function could look:

```python
# in mygame/evadventure/utils.py

_OBJ_STATS = """
|c{key}|n
Value: ~|y{value}|n coins{carried}

{desc}

Slots: |w{size}|n, Used from: |w{use_slot_name}|n
Quality: |w{quality}|n, Uses: |wuses|n
Attacks using |w{attack_type_name}|n against |w{defense_type_name}|n
Damage roll: |w{damage_roll}|n
""".strip()


def get_obj_stats(obj, owner=None): 
    """ 
    Get a string of stats about the object.
    
    Args:
        obj (Object): The object to get stats for.
        owner (Object): The one currently owning/carrying `obj`, if any. Can be 
            used to show e.g. where they are wielding it.
    Returns:
        str: A nice info string to display about the object.
     
    """
    return _OBJ_STATS.format(
        key=obj.key, 
        value=10, 
        carried="[Not carried]", 
        desc=obj.db.desc, 
        size=1,
        quality=3,
        uses="infinite"
        use_slot_name="backpack",
        attack_type_name="strength"
        defense_type_name="armor"
        damage_roll="1d6"
    )
```
Here we set up the string template with place holders for where every piece of info should go. 
Study this string so you understand what it does. The `|c`, `|y`, `|w` and `|n` markers are 
[Evennia color markup](../../../Concepts/Colors.md) for making the text cyan, yellow, white and neutral-color respectively.

We can guess some things, such that `obj.key` is the name of the object, and that `obj.db.desc` will 
hold its description (this is how it is in default Evennia).

But so far we have not established how to get any of the other properties like `size` or `attack_type`.
So we just set them to dummy values. We'll need to get back to this when we have more code in place!

## Testing 

> create a new module `mygame/evadventure/tests/test_utils.py`

How do you know if you made a typo in the code above? You could _manually_ test it by reloading your 
Evennia server and do the following from in-game: 

    py from evadventure.utils import get_obj_stats;print(get_obj_stats(self))

You should get back a nice string about yourself! If that works, great! But you'll need to remember
doing that test when you change this code later. 

```{sidebar}
In [evennia/contrib/evadventure/tests/test_utils.py](evennia.contrib.evadventure.tests.test_utils)
is the final test module. To dive deeper into unit testing in Evennia, see the 
[Unit testing](../../../Coding/Unit-Testing.md) documentation.
```

A _unit test_ allows you to set up automated testing of code. Once you've written your test you 
can run it over and over and make sure later changes to your code didn't break things. 

In this particular case, we _expect_ to later have to update the test when `get_obj_stats` becomes more 
complete and returns more reasonable data.

Evennia comes with extensive functionality to help you test your code. Here's a module for 
testing `get_obj_stats`.

```python 
# mygame/evadventure/tests/test_utils.py

from evennia.utils import create 
from evennia.utils.test_resources import BaseEvenniaTest 

from ..import utils

class TestUtils(BaseEvenniaTest):
    def test_get_obj_stats(self):
        # make a simple object to test with 
        obj = create.create_object(
            key="testobj", 
            attributes=(("desc", "A test object"),)
        ) 
        # run it through the function 
        result = utils.get_obj_stats(obj)
        # check that the result is what we expected
        self.assertEqual(
            result, 
            """ 
|ctestobj|n
Value: ~|y10|n coins

A test object

Slots: |w1|n, Used from: |wbackpack|n
Quality: |w3|n, Uses: |winfinite|n
Attacks using |wstrength|n against |warmor|n
Damage roll: |w1d6|n
""".strip()
)

```

What happens here is that we create a new test-class `TestUtils` that inherits from `BaseEvenniaTest`. 
This inheritance is what makes this a testing class.

We can have any number of methods on this class. To have a method recognized as one containing 
code to test, its name _must_ start with `test_`. We have one - `test_get_obj_stats`. 

In this method we create a dummy `obj` and gives it a `key` "testobj". Note how we add the 
`desc` [Attribute](../../../Components/Attributes.md) directly in the `create_object` call by specifying the attribute as a 
tuple `(name, value)`!  

We then get the result of passing this dummy-object through `get_obj_stats` we imported earlier. 

The `assertEqual` method is available on all testing classes and checks that the `result` is equal 
to the string we specify. If they are the same, the test _passes_, otherwise it _fails_ and we 
need to investigate what went wrong.

### Running your test

To run your test you need to stand inside your `mygame` folder and execute the following command:

    evennia test --settings settings.py .evadventure.tests

This will run all your `evadventure` tests (if you had more of them). To only run your utility tests 
you could do 

    evennia test --settings settings.py .evadventure.tests.test_utils

If all goes well, you should get an `OK` back. Otherwise you need to check the failure, maybe 
your return string doesn't quite match what you expected.

## Summary 

It's very important to understand how you import code between modules in Python, so if this is still 
confusing to you, it's worth to read up on this more. 

That said, many newcomers are confused with how to begin, so by creating the folder structure, some 
small modules and even making your first unit test, you are off to a great start!