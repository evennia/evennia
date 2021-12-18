# Dice

Rolls dice for roleplaying, in-game gambling or GM:ing

Evennia contribution - Griatch 2012

# Installation:


Add the `CmdDice` command from this module to your character's cmdset
(and then restart the server):

```python
# in mygame/commands/default_cmdsets.py

# ...
from evennia.contrib.rpg import dice  <---

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ...
    def at_object_creation(self):
        # ...
        self.add(dice.CmdDice())  # <---

```

# Usage:

    > roll 1d100 + 2
    > roll 1d20
    > roll 1d20 - 4

The result of the roll will be echoed to the room

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

To roll dice in code, use the `roll` function from this module:

```python

from evennia.contrib.rpg import dice
dice.roll(3, 10, ("+", 2))  # 3d10 + 2

```
