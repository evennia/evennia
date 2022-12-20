"""
MUD ruleset based on the _Knave_ OSR tabletop RPG by Ben Milton (modified for MUD use).

The rules are divided into a set of classes. While each class (except chargen) could
also have been stand-alone functions, having them as classes makes it a little easier
to use them as the base for your own variation (tweaking values etc).

- Roll-engine: Class with methods for making all dice rolls needed by the rules. Knave only
  has a few resolution rolls, but we define helper methods for different actions the
  character will be able to do in-code.
- Character generation - this is a container used for holding, tweaking and setting
  all character data during character generation. At the end it will save itself
  onto the Character for permanent storage.
- Improvement - this container holds rules used with experience to improve the
  character over time.
- Charsheet - a container with tools for visually displaying the character sheet in-game.

This module presents several singletons to import

- `dice` - the `EvAdventureRollEngine` for all random resolution and table-rolling.
- `character_sheet` - the `EvAdventureCharacterSheet` visualizer.
- `improvement` - the EvAdventureImprovement` class for handling char xp and leveling.

"""
from random import randint

from .enums import Ability
from .random_tables import death_and_dismemberment as death_table

# Basic rolls


class EvAdventureRollEngine:
    """
    This groups all dice rolls of EvAdventure. These could all have been normal functions, but we
    are group them in a class to make them easier to partially override and replace later.

    """

    def roll(self, roll_string, max_number=10):
        """
        NOTE: In evennia/contribs/rpg/dice/ is a more powerful dice roller with
        more features, such as modifiers, secret rolls etc. This is much simpler and only
        gets a simple sum of normal rpg-dice.

        Args:
            roll_string (str): A roll using standard rpg syntax, <number>d<diesize>, like
                1d6, 2d10 etc. Max die-size is 1000.
            max_number (int): The max number of dice to roll. Defaults to 10, which is usually
                more than enough.

        Returns:
            int: The rolled result - sum of all dice rolled.

        Raises:
            TypeError: If roll_string is not on the right format or otherwise doesn't validate.

        Notes:
            Since we may see user input to this function, we make sure to validate the inputs (we
            wouldn't bother much with that if it was just for developer use).

        """
        max_diesize = 1000
        roll_string = roll_string.lower()
        if "d" not in roll_string:
            raise TypeError(
                f"Dice roll '{roll_string}' was not recognized. Must be `<number>d<dicesize>`."
            )
        number, diesize = roll_string.split("d", 1)
        try:
            number = int(number)
            diesize = int(diesize)
        except Exception:
            raise TypeError(f"The number and dice-size of '{roll_string}' must be numerical.")
        if 0 < number > max_number:
            raise TypeError(f"Invalid number of dice rolled (must be between 1 and {max_number})")
        if 0 < diesize > max_diesize:
            raise TypeError(f"Invalid die-size used (must be between 1 and {max_diesize} sides)")

        # At this point we know we have valid input - roll and add dice together
        return sum(randint(1, diesize) for _ in range(number))

    def roll_with_advantage_or_disadvantage(self, advantage=False, disadvantage=False):
        """
        Base roll of d20, or 2d20, based on dis/advantage given.

        Args:
            bonus (int): The ability bonus to apply, like strength or charisma.
            advantage (bool): Roll 2d20 and use the bigger number.
            disadvantage (bool): Roll 2d20 and use the smaller number.

        Notes:
            Disadvantage and advantage cancel each other out.

        """
        if not (advantage or disadvantage) or (advantage and disadvantage):
            # normal roll, or advantage cancels disadvantage
            return self.roll("1d20")
        elif advantage:
            return max(self.roll("1d20"), self.roll("1d20"))
        else:
            return min(self.roll("1d20"), self.roll("1d20"))

    def saving_throw(
        self,
        character,
        bonus_type=Ability.STR,
        target=15,
        advantage=False,
        disadvantage=False,
        modifier=0,
    ):
        """
        A saving throw without a clear enemy to beat. In _Knave_ all unopposed saving
        throws always tries to beat 15, so (d20 + bonus + modifier) > 15.

        Args:
            character (Object): The one attempting to save themselves.
            bonus_type (enum.Ability): The ability bonus to apply, like strength or
                charisma.
            target (int, optional): Used for opposed throws (in Knave any regular
                saving through must always beat 15).
            advantage (bool, optional): Roll 2d20 and use the bigger number.
            disadvantage (bool, optional): Roll 2d20 and use the smaller number.
            modifier (int, optional): An additional +/- modifier to the roll.

        Returns:
            tuple: A tuple `(bool, str, str)`. The bool indicates if the save was passed or not.
                The second element is the quality of the roll - None (normal),
                "critical fail" and "critical success". Last element is a text detailing
                the roll, for display purposes.
        Notes:
            Advantage and disadvantage cancel each other out.

        Example:
            Trying to overcome the effects of poison, roll d20 + Constitution-bonus above 15.

        """
        bonus = getattr(character, bonus_type.value, 1)
        dice_roll = self.roll_with_advantage_or_disadvantage(advantage, disadvantage)
        if dice_roll == 1:
            quality = Ability.CRITICAL_FAILURE
        elif dice_roll == 20:
            quality = Ability.CRITICAL_SUCCESS
        else:
            quality = None
        result = dice_roll + bonus + modifier > target

        # determine text output
        rolltxt = "d20 "
        if advantage and disadvantage:
            rolltxt = "d20 (advantage canceled by disadvantage)"
        elif advantage:
            rolltxt = "|g2d20|n (advantage: picking highest) "
        elif disadvantage:
            rolltxt = "|r2d20|n (disadvantage: picking lowest) "
        bontxt = f"(+{bonus})"
        modtxt = ""
        if modifier:
            modtxt = f" + {modifier}" if modifier > 0 else f" - {abs(modifier)}"
        qualtxt = f" ({quality.value}!)" if quality else ""

        txt = (
            f"rolled {dice_roll} on {rolltxt} "
            f"+ {bonus_type.value}{bontxt}{modtxt} vs "
            f"{target} -> |w{result}{qualtxt}|n"
        )

        return (dice_roll + bonus + modifier) > target, quality, txt

    def opposed_saving_throw(
        self,
        attacker,
        defender,
        attack_type=Ability.STR,
        defense_type=Ability.ARMOR,
        advantage=False,
        disadvantage=False,
        modifier=0,
    ):
        """
        An saving throw that tries to beat an active opposing side.

        Args:
            attacker (Character): The attacking party.
            defender (Character): The one defending.
            attack_type (str): Which ability to use in the attack, like 'strength' or 'willpower'.
                Minimum is always 1.
            defense_type (str): Which ability to defend with, in addition to 'armor'.
                Minimum is always 11 (bonus + 10 is always the defense in _Knave_).
            advantage (bool): Roll 2d20 and use the bigger number.
            disadvantage (bool): Roll 2d20 and use the smaller number.
            modifier (int): An additional +/- modifier to the roll.

        Returns:
            tuple: (bool, str, str): If the attack succeed or not. The second element is the
                quality of the roll - None (normal), "critical fail" and "critical success". Last
                element is a text that summarizes the details of the roll.
        Notes:
            Advantage and disadvantage cancel each other out.

        """
        # what is stored on the character/npc is the bonus; we add 10 to get the defense target
        defender_defense = getattr(defender, defense_type.value, 1) + 10

        result, quality, txt = self.saving_throw(
            attacker,
            bonus_type=attack_type,
            target=defender_defense,
            advantage=advantage,
            disadvantage=disadvantage,
            modifier=modifier,
        )
        txt = f"Roll vs {defense_type.value}({defender_defense}):\n{txt}"

        return result, quality, txt

    def roll_random_table(self, dieroll, table_choices):
        """
        Make a roll on a random table.

        Args:
            dieroll (str): The dice to roll, like 1d6, 1d20, 3d6 etc).
            table_choices (iterable): If a list of single elements, the die roll
                should fully encompass the table, like a 1d20 roll for a table
                with 20 elements. If each element is a tuple, the first element
                of the tuple is assumed to be a string 'X-Y' indicating the
                range of values that should match the roll.

        Returns:
            Any: The result of the random roll.

        Example:
            `roll table_choices = [('1-5', "Blue"), ('6-9': "Red"), ('10', "Purple")]`

        Notes:
            If the roll is outside of the listing, the closest edge value is used.

        """
        roll_result = self.roll(dieroll)
        if not table_choices:
            return None

        if isinstance(table_choices[0], (tuple, list)):
            # tuple with range conditional, like ('1-5', "Blue") or ('10', "Purple")
            max_range = -1
            min_range = 10**6
            for (valrange, choice) in table_choices:

                minval, *maxval = valrange.split("-", 1)
                minval = abs(int(minval))
                maxval = abs(int(maxval[0]) if maxval else minval)

                # we store the largest/smallest values so far in case we need to use them
                max_range = max(max_range, maxval)
                min_range = min(min_range, minval)

                if minval <= roll_result <= maxval:
                    return choice

            # if we have no result, we are outside of the range, we pick the edge values. It is also
            # possible the range contains 'gaps', but that'd be an error in the random table itself.
            if roll_result > max_range:
                return table_choices[-1][1]
            else:
                return table_choices[0][1]
        else:
            # regular list - one line per value.
            roll_result = max(1, min(len(table_choices), roll_result))
            return table_choices[roll_result - 1]

    # specific rolls / actions

    def morale_check(self, defender):
        """
        A morale check is done for NPCs/monsters. It's done with a 2d6 against
        their morale.

        Args:
            defender (NPC): The entity trying to defend its morale.

        Returns:
            bool: False if morale roll failed, True otherwise.

        """
        return self.roll("2d6") <= defender.morale

    def heal_from_rest(self, character):
        """
        A meal and a full night's rest allow for regaining 1d8 + Const bonus HP.

        Args:
            character (Character): The one resting.

        """
        character.heal(self.roll("1d8") + character.constitution)

    death_map = {
        "weakened": "strength",
        "unsteady": "dexterity",
        "sickly": "constitution",
        "addled": "intelligence",
        "rattled": "wisdom",
        "disfigured": "charisma",
    }

    def roll_death(self, character):
        """
        Happens when hitting <= 0 hp. unless dead,

        """

        result = self.roll_random_table("1d8", death_table)
        if result == "dead":
            character.at_death()
        else:
            # survives with degraded abilities (1d4 roll)
            abi = self.death_map[result]

            current_abi = getattr(character, abi)
            loss = self.roll("1d4")

            current_abi -= loss

            if current_abi < -10:
                # can't lose more - die
                character.at_death()
            else:
                # refresh health, but get permanent ability loss
                new_hp = self.roll("1d4")
                character.heal(new_hp)
                setattr(character, abi, current_abi)

                character.msg(
                    "~" * 78 + "\n|yYou survive your brush with death, "
                    f"but are |r{result.upper()}|y and permanently |rlose {loss} {abi}|y.|n\n"
                    f"|GYou recover |g{new_hp}|G health|.\n" + "~" * 78
                )


# singletons

# access rolls e.g. with rules.dice.opposed_saving_throw(...)
dice = EvAdventureRollEngine()
