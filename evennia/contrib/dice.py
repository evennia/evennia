"""
Dice - rolls dice for roleplaying, in-game gambling or GM:ing

Evennia contribution - Griatch 2012


This module implements a full-fledged dice-roller and a 'dice' command
to go with it. It uses standard RPG 'd'-syntax (e.g. 2d6 to roll two
six-sided die) and also supports modifiers such as 3d6 + 5.

One can also specify a standard Python operator in order to specify
eventual target numbers and get results in a fair and guaranteed
unbiased way.  For example a GM could (using the dice command) from
the start define the roll as 2d6 < 8 to show that a roll below 8 is
required to succeed. The command will normally echo this result to all
parties (although it also has options for hidden and secret rolls).


Installation:

To use in your code, just import the roll_dice function from this module.

To use  the dice/roll command, just import this module in your custom
cmdset module and add the following line to the end of DefaultCmdSet's
at_cmdset_creation():

   self.add(dice.CmdDice())

After a reload the dice (or roll) command will be available in-game.

"""
import re
from random import randint
from evennia import default_cmds, CmdSet


def roll_dice(dicenum, dicetype, modifier=None, conditional=None, return_tuple=False):
    """
    This is a standard dice roller.

    Args:
     dicenum (int): Number of dice to roll (the result to be added).
     dicetype (int): Number of sides of the dice to be rolled.
     modifier (tuple): A tuple `(operator, value)`, where operator is
        one of `"+"`, `"-"`, `"/"` or `"*"`. The result of the dice
        roll(s) will be modified by this value.
     conditional (tuple): A tuple `(conditional, value)`, where
        conditional is one of `"=="`,`"<"`,`">"`,`">="`,`"<=`" or "`!=`".
        This allows the roller to directly return a result depending
        on if the conditional was passed or not.
     return_tuple (bool): Return a tuple with all individual roll
        results or not.

    Returns:
        roll_result (int): The result of the roll + modifiers. This is the
             default return.
        condition_result (bool): A True/False value returned if `conditional`
            is set but not `return_tuple`. This effectively hides the result
            of the roll.
        full_result (tuple): If, return_tuple` is `True`, instead
            return a tuple `(result, outcome, diff, rolls)`. Here,
            `result` is the normal result of the roll + modifiers.
            `outcome` and `diff` are the boolean result of the roll and
            absolute difference to the `conditional` input; they will
            be will be `None` if `conditional` is not set. `rolls` is
            itself a tuple holding all the individual rolls in the case of
            multiple die-rolls.

    Raises:
        TypeError if non-supported modifiers or conditionals are given.

    Notes:
        All input numbers are converted to integers.

    Examples:
        print roll_dice(2, 6) # 2d6
        <<< 7
        print roll_dice(1, 100, ('+', 5) # 1d100 + 5
        <<< 34
        print roll_dice(1, 20, conditional=('<', 10) # let'say we roll 3
        <<< True
        print roll_dice(3, 10, return_tuple=True)
        <<< (11, None, None, (2, 5, 4))
        print roll_dice(2, 20, ('-', 2), conditional=('>=', 10), return_tuple=True)
        <<< (8, False, 2, (4, 6)) # roll was 4 + 6 - 2 = 8

    """
    dicenum = int(dicenum)
    dicetype = int(dicetype)

    # roll all dice, remembering each roll
    rolls = tuple([randint(1, dicetype) for roll in range(dicenum)])
    result = sum(rolls)

    if modifier:
        # make sure to check types well before eval
        mod, modvalue = modifier
        if mod not in ("+", "-", "*", "/"):
            raise TypeError("Non-supported dice modifier: %s" % mod)
        modvalue = int(modvalue)  # for safety
        result = eval("%s %s %s" % (result, mod, modvalue))
    outcome, diff = None, None
    if conditional:
        # make sure to check types well before eval
        cond, condvalue = conditional
        if cond not in (">", "<", ">=", "<=", "!=", "=="):
            raise TypeError("Non-supported dice result conditional: %s" % conditional)
        condvalue = int(condvalue)  # for safety
        outcome = eval("%s %s %s" % (result, cond, condvalue))  # True/False
        diff = abs(result - condvalue)
    if return_tuple:
        return result, outcome, diff, rolls
    else:
        if conditional:
            return outcome
        else:
            return result


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
