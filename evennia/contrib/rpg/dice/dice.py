"""
# Dice

Rolls dice for roleplaying, in-game gambling or GM:ing

Evennia contribution - Griatch 2012

This module implements a a dice-roller and a `dice`/`roll` command
to go with it. It uses standard RPG 'd'-syntax (e.g. 2d6 to roll two
six-sided die) and also supports modifiers such as 3d6 + 5.

    > roll 1d20 + 2

One can also specify a standard Python operator in order to specify
eventual target numbers and get results in a fair and guaranteed
unbiased way.  For example a GM could (using the dice command) from
the start define the roll as 2d6 < 8 to show that a roll below 8 is
required to succeed. The command will normally echo this result to all
parties (although it also has options for hidden and secret rolls).


# Installation:


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

# Usage:

    roll 1d100 + 10

To roll dice in code, use the `roll` function from this module:

    from evennia.contrib.rpg import dice

    dice.roll("3d10 + 2")


If your system generates the dice dynamically you can also enter each part
of the roll separately:

    dice.roll(3, 10, ("+", 2))  # 3d10 + 2


"""

import re
from ast import literal_eval
from random import randint

from evennia import CmdSet, default_cmds
from evennia.utils.utils import simple_eval


def roll(
    dice,
    dicetype=6,
    modifier=None,
    conditional=None,
    return_tuple=False,
    max_dicenum=10,
    max_dicetype=1000,
):
    """
    This is a standard dice roller.

    Args:
     dice (int or str): If an `int`, this is the number of dice to roll, and `dicetype` is used
        to determine the type. If a `str`, it should be on the form `NdM` where `N` is the number
        of dice and `M` is the number of sides on each die. Also
        `NdM [modifier] [number] [conditional]` is understood, e.g. `1d6 + 3`
        or `2d10 / 2 > 10`.
     dicetype (int, optional): Number of sides of the dice to be rolled. Ignored if
        `dice` is a string.
     modifier (tuple, optional): A tuple `(operator, value)`, where operator is
        one of `"+"`, `"-"`, `"/"` or `"*"`. The result of the dice
        roll(s) will be modified by this value. Ignored if `dice` is a string.
     conditional (tuple, optional): A tuple `(conditional, value)`, where
        conditional is one of `"=="`,`"<"`,`">"`,`">="`,`"<=`" or "`!=`".
        Ignored if `dice` is a string.
     return_tuple (bool): Return a tuple with all individual roll
        results or not.
     max_dicenum (int): The max number of dice to allow to be rolled.
     max_dicetype (int): The max number of sides on the dice to roll.

    Returns:
        int, bool or tuple : By default, this is the result of the roll + modifiers.  If
        `conditional` is given, or `dice` is a string defining a conditional, then a True/False
        value is returned. Finally, if `return_tuple` is set, this is a tuple
        `(result, outcome, diff, rolls)`, where, `result` is the the normal result of the
        roll + modifiers,  `outcome` and `diff` are the boolean absolute difference between the roll
        and the `conditional` input; both will be will be `None` if `conditional` is not set.
        The `rolls` a tuple holding all the individual rolls (one or more depending on how many
        dice were rolled).

    Raises:
        TypeError if non-supported modifiers or conditionals are given.

    Notes:
        All input numbers are converted to integers.

    Examples:
        ::
            # string form
            print roll("3d6 + 2")
            10
            print roll("2d10 + 2 > 10")
            True
            print roll("2d20 - 2 >= 10")
            (8, False, 2, (4, 6)) # roll was 4 + 6 - 2 = 8

            # explicit arguments
            print roll(2, 6) # 2d6
            7
            print roll(1, 100, ('+', 5) # 1d100 + 5
            4
            print roll(1, 20, conditional=('<', 10) # let'say we roll 3
            True
            print roll(3, 10, return_tuple=True)
            (11, None, None, (2, 5, 4))
            print roll(2, 20, ('-', 2), conditional=('>=', 10), return_tuple=True)
            (8, False, 2, (4, 6)) # roll was 4 + 6 - 2 = 8

    """

    modifier_string = ""
    conditional_string = ""
    conditional_value = None
    if isinstance(dice, str) and "d" in dice.lower():
        # A string is given, parse it as NdM dice notation
        roll_string = dice.lower()

        # split to get the NdM syntax
        dicenum, rest = roll_string.split("d", 1)

        # parse packwards right-to-left
        if any(True for cond in ("==", "<", ">", "!=", "<=", ">=") if cond in rest):
            # split out any conditionals, like '< 12'
            rest, *conditionals = re.split(r"(==|<=|>=|<|>|!=)", rest, maxsplit=1)
            try:
                conditional_value = int(conditionals[1])
            except ValueError:
                raise TypeError(
                    f"Conditional '{conditionals[-1]}' was not recognized. Must be a number."
                )
            conditional_string = "".join(conditionals)

        if any(True for op in ("+", "-", "*", "/") if op in rest):
            # split out any modifiers, like '+ 2'
            rest, *modifiers = re.split(r"(\+|-|/|\*)", rest, maxsplit=1)
            modifier_string = "".join(modifiers)

        # whatever is left is the dice type
        dicetype = rest

    else:
        # an integer is given - explicit modifiers and conditionals as part of kwargs
        dicenum = int(dice)
        dicetype = int(dicetype)
        if modifier:
            modifier_string = "".join(str(part) for part in modifier)
        if conditional:
            conditional_value = int(conditional[1])
            conditional_string = "".join(str(part) for part in conditional)

    try:
        dicenum = int(dicenum)
        dicetype = int(dicetype)
    except Exception:
        raise TypeError(
            f"The number of dice and dice-size must both be numerical. Got '{dicenum}' "
            f"and '{dicetype}'."
        )
    if 0 < dicenum > max_dicenum:
        raise TypeError(f"Invalid number of dice rolled (must be between 1 and {max_dicenum}).")
    if 0 < dicetype > max_dicetype:
        raise TypeError(f"Invalid die-size used (must be between 1 and {max_dicetype} sides).")

    # roll all dice, remembering each roll
    rolls = tuple([randint(1, dicetype) for _ in range(dicenum)])
    result = sum(rolls)

    if modifier_string:
        result = simple_eval(f"{result} {modifier_string}")

    outcome, diff = None, None
    if conditional_string and conditional_value:
        outcome = simple_eval(f"{result} {conditional_string}")
        diff = abs(result - conditional_value)

    if return_tuple:
        return result, outcome, diff, rolls
    elif conditional or (conditional_string and conditional_value):
        return outcome  # True|False
    else:
        return result  # integer


# legacy alias
roll_dice = roll


RE_PARTS = re.compile(r"(d|\+|-|/|\*|<|>|<=|>=|!=|==)")
RE_MOD = re.compile(r"(\+|-|/|\*)")
RE_COND = re.compile(r"(<|>|<=|>=|!=|==)")


class CmdDice(default_cmds.MuxCommand):
    """
    roll dice

    Usage:
      dice[/switch] <nr>d<sides> [modifier] [success condition]

    Switch:
      hidden - tell the room the roll is being done, but don't show the result
      secret - don't inform the room about neither roll nor result

    Examples:
      dice 3d6 + 4
      dice 1d100 - 2 < 50

    This will roll the given number of dice with given sides and modifiers.
    So e.g. 2d6 + 3 means to 'roll a 6-sided die 2 times and add the result,
    then add 3 to the total'.
    Accepted modifiers are +, -, * and /.
    A success condition is given as normal Python conditionals
    (<,>,<=,>=,==,!=). So e.g. 2d6 + 3 > 10 means that the roll will succeed
    only if the final result is above 8. If a success condition is given, the
    outcome (pass/fail) will be echoed along with how much it succeeded/failed
    with. The hidden/secret switches will hide all or parts of the roll from
    everyone but the person rolling.
    """

    key = "dice"
    aliases = ["roll", "@dice"]
    locks = "cmd:all()"

    def func(self):
        """Mostly parsing for calling the dice roller function"""

        if not self.args:
            self.caller.msg("Usage: @dice <nr>d<sides> [modifier] [conditional]")
            return
        argstring = "".join(str(arg) for arg in self.args)

        parts = [part for part in RE_PARTS.split(self.args) if part]
        len_parts = len(parts)
        modifier = None
        conditional = None

        if len_parts < 3 or parts[1] != "d":
            self.caller.msg(
                "You must specify the die roll(s) as <nr>d<sides>."
                " For example, 2d6 means rolling a 6-sided die 2 times."
            )
            return

        # Limit the number of dice and sides a character can roll to prevent server slow down and crashes
        ndicelimit = 10000  # Maximum number of dice
        nsidelimit = 10000  # Maximum number of sides
        if int(parts[0]) > ndicelimit or int(parts[2]) > nsidelimit:
            self.caller.msg("The maximum roll allowed is %sd%s." % (ndicelimit, nsidelimit))
            return

        ndice, nsides = parts[0], parts[2]
        if len_parts == 3:
            # just something like 1d6
            pass
        elif len_parts == 5:
            # either e.g. 1d6 + 3  or something like 1d6 > 3
            if parts[3] in ("+", "-", "*", "/"):
                modifier = (parts[3], parts[4])
            else:  # assume it is a conditional
                conditional = (parts[3], parts[4])
        elif len_parts == 7:
            # the whole sequence, e.g. 1d6 + 3 > 5
            modifier = (parts[3], parts[4])
            conditional = (parts[5], parts[6])
        else:
            # error
            self.caller.msg("You must specify a valid die roll")
            return
        # do the roll
        try:
            result, outcome, diff, rolls = roll_dice(
                ndice, nsides, modifier=modifier, conditional=conditional, return_tuple=True
            )
        except ValueError:
            self.caller.msg(
                "You need to enter valid integer numbers, modifiers and operators."
                " |w%s|n was not understood." % self.args
            )
            return
        # format output
        if len(rolls) > 1:
            rolls = ", ".join(str(roll) for roll in rolls[:-1]) + " and " + str(rolls[-1])
        else:
            rolls = rolls[0]
        if outcome is None:
            outcomestring = ""
        elif outcome:
            outcomestring = " This is a |gsuccess|n (by %s)." % diff
        else:
            outcomestring = " This is a |rfailure|n (by %s)." % diff
        yourollstring = "You roll %s%s."
        roomrollstring = "%s rolls %s%s."
        resultstring = " Roll(s): %s. Total result is |w%s|n."

        if "secret" in self.switches:
            # don't echo to the room at all
            string = yourollstring % (argstring, " (secret, not echoed)")
            string += "\n" + resultstring % (rolls, result)
            string += outcomestring + " (not echoed)"
            self.caller.msg(string)
        elif "hidden" in self.switches:
            # announce the roll to the room, result only to caller
            string = yourollstring % (argstring, " (hidden)")
            self.caller.msg(string)
            string = roomrollstring % (self.caller.key, argstring, " (hidden)")
            self.caller.location.msg_contents(string, exclude=self.caller)
            # handle result
            string = resultstring % (rolls, result)
            string += outcomestring + " (not echoed)"
            self.caller.msg(string)
        else:
            # normal roll
            string = yourollstring % (argstring, "")
            self.caller.msg(string)
            string = roomrollstring % (self.caller.key, argstring, "")
            self.caller.location.msg_contents(string, exclude=self.caller)
            string = resultstring % (rolls, result)
            string += outcomestring
            self.caller.location.msg_contents(string)


class DiceCmdSet(CmdSet):
    """
    a small cmdset for testing purposes.
    Add with @py self.cmdset.add("contrib.dice.DiceCmdSet")
    """

    def at_cmdset_creation(self):
        """Called when set is created"""
        self.add(CmdDice())
