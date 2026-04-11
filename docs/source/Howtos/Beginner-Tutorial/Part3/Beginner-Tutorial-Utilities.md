# Code Structure and Utilities

In this lesson, we will set up the file structure for _EvAdventure_. We will make some
utilities that will be useful later. We will also learn how to write _tests_.

## Folder Structure

```{sidebar} This layout is for the tutorial!
We make the `evadventure` folder stand-alone for the sake of the tutorial only. Leaving the code isolated in this way makes it clear what we have changed &mdash; and for you to grab what you want later. It also makes it easier to refer to the matching code in `evennia/contrib/tutorials/evadventure`.

For your own game, you are instead encouraged to modify your game dir in-place (i.e, directly add to `commands/commands.py` and  modify the `typeclasses/` modules directly). Except for the `server/` folder, you are, in fact, free to structure your game dir code pretty much as you like.
```
Create a new folder named `evadventure` under your `mygame` folder. Inside it the new folder, create  another folder named `tests/`. Make sure to put empty `__init__.py` files in both new folders. Doing so turns both new folders into packages from which Python understands to import automatically.

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
[evennia/contrib/tutorials/evadventure/enums.py](../../../api/evennia.contrib.tutorials.evadventure.enums.md).
```
Create a new file `mygame/evadventure/enums.py`.

An [enum](https://docs.python.org/3/library/enum.html) (enumeration) is a way to establish constants in Python. For example:

```python
# in a file mygame/evadventure/enums.py

from enum import Enum

class Ability(Enum):

    STR = "strength"

```

You can then access an enum like this:

```
# from another module in mygame/evadventure

from .enums import Ability

Ability.STR   # the enum itself
Ability.STR.value  # this is the string "strength"

```

Using enums is a recommended practice. With enums set up, we can make sure to refer to the same constant or variable every time. Keeping all enums in one place also means we have a good overview of the constants with which we are dealing.

The alternative to enums would be, for example, to pass around a string named `"constitution"`. If you mis-spelled this as, say, `"consitution"`, you would not necessarily know it right away because the error would happen later when the string is not recognized. By using the enum practice,should you make a typo getting `Ability.COM` instead of `Ability.CON`, Python will immediately raise an error becase this enum with the typo will not be recognized.

With enums, you can also do nice direct comparisons like `if ability is Ability.WIS: <do stuff>`.

Note that the `Ability.STR` enum does not have the actual _value_ of, for instance, your Strength. `Ability.STR` is just a fixed label for the Strength ability.

Below is the `enum.py` module needed for _Knave_. It covers the basic aspects of the rule system we need to track. (Check out the _Knave_ rules.) Should you later use another rule system, you'll likely expand on your enums gradually as you figure out what you'll need.

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

    CRITICAL_FAILURE = "critical_failure"
    CRITICAL_SUCCESS = "critical_success"

    ALLEGIANCE_HOSTILE = "hostile"
    ALLEGIANCE_NEUTRAL = "neutral"
    ALLEGIANCE_FRIENDLY = "friendly"


ABILITY_REVERSE_MAP =  {
    "str": Ability.STR,
    "dex": Ability.DEX,
    "con": Ability.CON,
    "int": Ability.INT,
    "wis": Ability.WIS,
    "cha": Ability.CHA
}

```

Above, the `Ability` class holds some basic properties of a character sheet.

The `ABILITY_REVERSE_MAP` is a convenient map to convert a string to an Enum. The most common use of this would be in a Command; the Player don't know anything about Enums, they can only send strings. So we'd only get the string "cha". Using this `ABILITY_REVERSE_MAP` we can conveniently convert this input to an `Ability.CHA` Enum you can then pass around in code 

    ability = ABILITY_REVERSE_MAP.get(user_input)


## Utility Module

> Create a new module `mygame/evadventure/utils.py`

```{sidebar}
An example of the utility module is found in
[evennia/contrib/tutorials/evadventure/utils.py](../../../api/evennia.contrib.tutorials.evadventure.utils.md)
```

The utility module is used to contain general functions we may need to call repeatedly from various other modules. In this tutorial example, we only crate one utility: a function that produces a pretty display of any object we pass to it.

Here's how it could look: 

```python
# in mygame/evadventure/utils.py

_OBJ_STATS = """
|c{key}|n
Value: ~|y{value}|n coins{carried}

{desc}

Slots: |w{size}|n, Used from: |w{use_slot_name}|n
Quality: |w{quality}|n, Uses: |w{uses}|n
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
        uses="infinite",
        use_slot_name="backpack",
        attack_type_name="strength",
        defense_type_name="armor",
        damage_roll="1d6"
    )
```

Previously throughout these tutorial lessons, we have seen the `""" ... """` multi-line string used mainly for function help strings, but a triple-quoted string in Python is used for any multi-line string. 

Above, we set up a string template (`_OBJ_STATS`) with place holders (`{...}`) for where every element of stats information should go. In the `_OBJ_STATS.format(...)` call, we then dynamically fill those place holders with data from the object we pass into `get_obj_stats`. 

Here's what you'd get back if you were to pass a 'chipped sword'  to `get_obj_stats` (note that these docs don't show the text colors): 

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

We will later use this to let the player inspect any object without us having to make a new utility for every object type. 

Study the `_OBJ_STATS` template string so that you understand what it does. The `|c`, `|y`, `|w` and `|n` markers are  [Evennia color markup](../../../Concepts/Colors.md) for making the text cyan, yellow, white and neutral-color, respectively.

Some stats elements are easy to identify in the above code. For instance, `obj.key` is the name of an object and `obj.db.desc` will hold an object's description &mdash; this is also how default Evennia works.

So far, here in our tutorial, we have not yet established how to get any of the other properties like `size`, `damage_roll`  or `attack_type_name`. For our current purposes, we will just set them to fixed dummy values so they work. We'll need to revisit them later when we have more code in place!

## Testing

Evennia comes with extensive functionality to help you test your code. A _unit test_ allows you to set up automated testing of code. Once you've written your test, you can then run it over and over again to ensure later changes to your code didn't break things by introducing errors.

> create a new module `mygame/evadventure/tests/test_utils.py`

How would you know if you made a typo in the code above? You can _manually_ test it by reloading your Evennia server and issuing the following in-game python command:

    py from evadventure.utils import get_obj_stats;print(get_obj_stats(self))

Doing so should spit back a nice bit of string ouput about yourself! If that works, great! But, you'll need to remember re-running that test manually when you later change the code.

```{sidebar}
In [evennia/contrib/tutorials/evadventure/tests/test_utils.py](evennia.contrib.tutorials.evadventure.tests.test_utils)
is an example of the testing module. To dive deeper into unit testing in Evennia, see the [Unit testing](../../../Coding/Unit-Testing.md) documentation.
```

In our particular case of this tutorial, we should _expect_ to need to later update the test when the `get_obj_stats` code becomes more complete and returns more pertinent data.

Here's a module for  testing `get_obj_stats`.

```python
# mygame/evadventure/tests/test_utils.py

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from ..import utils

class TestUtils(EvenniaTest):
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
Value: ~|y10|n coins[Not carried]

A test object

Slots: |w1|n, Used from: |wbackpack|n
Quality: |w3|n, Uses: |winfinite|n
Attacks using |wstrength|n against |warmor|n
Damage roll: |w1d6|n
""".strip()
)

```

What happens in the above code is that we create a new test-class named `TestUtils` that inherits from `EvenniaTest`. It is this inheritance that makes this a testing class.


```{important}
It's useful for any game dev to know how to test their code effectively. So, we'll try to include a *Testing* section at the end of each implementation lesson that follows in this tutorial.

Writing tests for your code is optional, but highly recommended. Initially, unit testing may feel a little cumbersome or time-consuming... but you'll thank yourself later.
```

We can have any number of methods called on this class. To have Evennia automatically recognize a method as one containing code to test, its name _must_ start with the `test_` prefix. We have one here as `test_get_obj_stats`.

In our `test_get_obj_stats` method, we create a dummy `obj` and assign it a `key` "testobj". Note that we add the`desc` [Attribute](../../../Components/Attributes.md) directly in the `create_object` call by specifying the attribute as a tuple `(name, value)`!

Then, we can get the result of passing this dummy-object through the `get_obj_stats` function that we imported earlier.

The `assertEqual` method is available on all testing classes and checks that the `result` is equal to the string we specify. If they are the same, the test _passes_. Otherwise, it _fails_ and we need to investigate what went wrong.

### Running your Test

To run our utility module test, we need to issue the following command directly from the `mygame` folder:

    evennia test --settings settings.py evadventure.tests

The above command will run all `evadventure` tests found in the `mygame/evadventure/tests` folder. To run only our utility tests we might instead specify the test individually:

    evennia test --settings settings.py evadventure.tests.test_utils

If all goes well, the above utility test should produce output ending with `OK` to indicate our code has passed the test.

However, if our return string doesn't quite match what we expected, the test will fail. We will then need to begin examining and troubleshooting our failing code.

> Hint: The above example unit test code contains a deliberate error in capitalization. See if you can examine the output to interpret the deliberate error, and then fix it!

## Summary

It's very important to understand how you import code among modules in Python. If importing from Python modules is still confusing to you, it's worth it to read more on the topic.

That said, many newcomers are confused with how to tackle these concepts. In this lesson, by creating the folder structure, two small modules and even making our first unit test, you are off to a great start!
