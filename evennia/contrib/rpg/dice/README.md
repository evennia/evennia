# Dice roller

Contribution by Griatch, 2012

A dice roller for any number and side of dice. Adds in-game dice rolling
(`roll 2d10 + 1`) as well as conditionals (roll under/over/equal to a target)
and functions for rolling dice in code. Command also supports hidden or secret
rolls for use by a human game master.


## Installation:


Add the `CmdDice` command from this module to your character's cmdset
(and then restart the server):

```python
# in mygame/commands/default_cmdsets.py

# ...
from evennia.contrib.rpg import dice  <---

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ...
    def at_cmdset_creation(self):
        # ...
        self.add(dice.CmdDice())  # <---

```

## Usage:

    > roll 1d100 + 2
    > roll 1d20
    > roll 1d20 - 4

The result of the roll will be echoed to the room.

One can also specify a standard Python operator in order to specify
eventual target numbers and get results in a fair and guaranteed
unbiased way.  For example:

    > roll 2d6 + 2 < 8

Rolling this will inform all parties if roll was indeed below 8 or not.

    > roll/hidden

Informs the room that the roll is being made without telling what the result
was.

    > roll/secret

Is a hidden roll that does not inform the room it happened.

## Rolling dice from code

You can specify the first argument as a string on standard RPG d-syntax (NdM,
where N is the number of dice to roll, and M is the number sides per dice):

```python
from evennia.contrib.rpg.dice import roll

roll("3d10 + 2")
```

You can also give a conditional (you'll then get a `True`/`False` back):

```python
roll("2d6 - 1 >= 10")
```

If you specify the first argument as an integer, it's interpret as the number of
dice to roll and you can then build the roll more explicitly. This can be
useful if you are using the roller together with some other system and want to
construct the roll from components.


```python
roll(dice, dicetype=6, modifier=None, conditional=None, return_tuple=False,
      max_dicenum=10, max_dicetype=1000)
```

Here's how to roll `3d10 + 2` with explicit syntax:

```python
roll(3, 10, modifier=("+", 2))
```

Here's how to roll `2d6 - 1 >= 10` (you'll get back `True`/`False` back):

```python
roll(2, 6, modifier=("-", 1), conditional=(">=", 10))
```

You can only roll one set of dice. If your RPG requires you to roll multiple
sets of dice and combine them in more advanced ways, you can do so with multiple
`roll()` calls.

### Get all roll details

If you need the individual rolls (e.g. for a dice pool), set the `return_tuple` kwarg:

```python
roll("3d10 > 10", return_tuple=True)
(13, True, 3, (3, 4, 6))  # (result, outcome, diff, rolls)
```

The return is a tuple `(result, outcome, diff, rolls)`, where `result` is the
result of the roll, `outcome` is `True/False` if a conditional was
given (`None` otherwise), `diff` is the absolute difference between the
conditional and the result (`None` otherwise) and `rolls` is a tuple containing
the individual roll results.
