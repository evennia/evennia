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

from evennia.utils.evform import EvForm
from evennia.utils.evtable import EvTable

from .enums import Ability
from .random_tables import character_generation as chargen_table
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
                f"Dice roll '{roll_string}' was not recognized. " "Must be `<number>d<dicesize>`."
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

    def heal(self, character, amount):
        """
        Heal specific amount, but not more than our max.

        Args:
            character (EvAdventureCharacter): The character to heal
            amount (int): How many HP to heal.

        """
        damage = character.hp_max - character.hp
        character.hp += min(damage, amount)

    def heal_from_rest(self, character):
        """
        A meal and a full night's rest allow for regaining 1d8 + Const bonus HP.

        Args:
            character (Character): The one resting.

        Returns:
            int: How much HP was healed. This is never more than how damaged we are.

        """
        self.heal(character, self.roll("1d8") + character.constitution)

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
                new_hp = max(character.hp_max, self.roll("1d4"))
                setattr(character, abi, current_abi)
                character.hp = new_hp

                character.msg(
                    "~" * 78 + "\n|yYou survive your brush with death, "
                    f"but are |r{result.upper()}|y and permenently |rlose {loss} {abi}|y.|n\n"
                    f"|GYou recover |g{new_hp}|G health|.\n" + "~" * 78
                )


# character generation


class EvAdventureCharacterGeneration:
    """
    This collects all the rules for generating a new character. An instance of this class can be
    used to track all the stats during generation and will be used to apply all the data to the
    character at the end. This class instance can also be saved on the menu to make sure a user
    is not losing their half-created character.

    Note:
        Unlike standard Knave, characters will come out more similar here. This is because in
        a table top game it's fun to roll randomly and have to live with a crappy roll - but
        online players can (and usually will) just disconnect and reroll until they get values
        they are happy with.

        In standard Knave, the character's attribute bonus is rolled randomly and will give a
        value 1-6; and there is no guarantee for 'equal' starting characters. Instead we
        homogenize the results to a flat +2 bonus and let people redistribute the
        points afterwards. This also allows us to show off some more advanced concepts in the
        chargen menu.

        In the same way, Knave uses a d8 roll to get the initial hit points. Instead we use a
        flat max of 8 HP to start, in order to give players a little more survivability.

        We *will* roll random start equipment though. Contrary to standard Knave, we'll also
        randomly assign the starting weapon among a small selection of equal-dmg weapons (since
        there is no GM to adjudicate a different choice).

    """

    def __init__(self):
        """
        Initialize starting values

        """
        # for clarity we initialize the engine here rather than use the
        # global singleton at the end of the module
        roll_engine = EvAdventureRollEngine()

        # name will likely be modified later
        self.name = roll_engine.roll_random_table("1d282", chargen_table["name"])

        # base attribute bonuses (flat +1 bonus)
        self.strength = 2
        self.dexterity = 2
        self.constitution = 2
        self.intelligence = 2
        self.wisdom = 2
        self.charisma = 2

        # physical attributes (only for rp purposes)
        self.physique = roll_engine.roll_random_table("1d20", chargen_table["physique"])
        self.face = roll_engine.roll_random_table("1d20", chargen_table["face"])
        self.skin = roll_engine.roll_random_table("1d20", chargen_table["skin"])
        self.hair = roll_engine.roll_random_table("1d20", chargen_table["hair"])
        self.clothing = roll_engine.roll_random_table("1d20", chargen_table["clothing"])
        self.speech = roll_engine.roll_random_table("1d20", chargen_table["speech"])
        self.virtue = roll_engine.roll_random_table("1d20", chargen_table["virtue"])
        self.vice = roll_engine.roll_random_table("1d20", chargen_table["vice"])
        self.background = roll_engine.roll_random_table("1d20", chargen_table["background"])
        self.misfortune = roll_engine.roll_random_table("1d20", chargen_table["misfortune"])
        self.alignment = roll_engine.roll_random_table("1d20", chargen_table["alignment"])

        # same for all
        self.exploration_speed = 120
        self.combat_speed = 40
        self.hp_max = 8
        self.hp = self.hp_max
        self.xp = 0
        self.level = 1

        # random equipment
        self.armor = roll_engine.roll_random_table("1d20", chargen_table["armor"])

        _helmet_and_shield = roll_engine.roll_random_table(
            "1d20", chargen_table["helmets and shields"]
        )
        self.helmet = "helmet" if "helmet" in _helmet_and_shield else "none"
        self.shield = "shield" if "shield" in _helmet_and_shield else "none"

        self.weapon = roll_engine.roll_random_table("1d20", chargen_table["starting weapon"])

        self.backpack = [
            "ration",
            "ration",
            roll_engine.roll_random_table("1d20", chargen_table["dungeoning gear"]),
            roll_engine.roll_random_table("1d20", chargen_table["dungeoning gear"]),
            roll_engine.roll_random_table("1d20", chargen_table["general gear 1"]),
            roll_engine.roll_random_table("1d20", chargen_table["general gear 2"]),
        ]

    def build_desc(self):
        """
        Generate a backstory / description paragraph from random elements.

        """
        return (
            f"{self.background.title()}. Wears {self.clothing} clothes, and has {self.speech} "
            f"speech. Has a {self.physique} physique, a {self.face} face, {self.skin} skin and "
            f"{self.hair} hair. Is {self.virtue}, but {self.vice}. Has been {self.misfortune} in "
            f"the past. Favors {self.alignment}."
        )

    def adjust_attribute(self, source_attribute, target_attribute, value):
        """
        Redistribute bonus from one attribute to another. The resulting values
        must not be lower than +1 and not above +6.

        Args:
            source_attribute (enum.Ability): The name of the attribute to deduct bonus from,
                like 'strength'
            target_attribute (str): The attribute to give the bonus to, like 'dexterity'.
            value (int): How much to change. This is always 1 for the current chargen.

        Raises:
            ValueError: On input error, using invalid values etc.

        Notes:
            We assume the strings are provided by the chargen, so we don't do
            much input validation here, we do make sure we don't overcharge ourselves though.

        """
        if source_attribute == target_attribute:
            return

        # we use getattr() to fetch the Ability of e.g. the .strength property etc
        source_current = getattr(self, source_attribute.value, 1)
        target_current = getattr(self, target_attribute.value, 1)

        if source_current - value < 1:
            raise ValueError(f"You can't reduce the {source_attribute} bonus below +1.")
        if target_current + value > 6:
            raise ValueError(f"You can't increase the {target_attribute} bonus above +6.")

        # all is good, apply the change.
        setattr(self, source_attribute.value, source_current - value)
        setattr(self, target_attribute.value, target_current + value)

    def apply(self, character):
        """
        Once the chargen is complete, call this to transfer all the data to the character
        permanently.

        """
        character.key = self.name
        character.strength = self.strength
        character.dexterity = self.dexterity
        character.constitution = self.constitution
        character.intelligence = self.intelligence
        character.wisdom = self.wisdom
        character.charisma = self.charisma

        character.weapon = self.weapon
        character.armor = self.armor

        character.hp = self.hp
        character.level = self.level
        character.xp = self.xp

        character.db.desc = self.build_desc()

        # TODO - spawn the actual equipment objects before adding them to equipment!

        if self.weapon:
            character.equipment.use(self.weapon)
        if self.shield:
            character.equipment.use(self.shield)
        if self.armor:
            character.equipment.use(self.armor)
        if self.helmet:
            character.equipment.use(self.helmet)

        for item in self.backpack:
            # TODO create here
            character.equipment.store(item)


# character improvement


class EvAdventureImprovement:
    """
    Handle XP gains and level upgrades. Grouped in a class in order to
    make it easier to override the mechanism.

    """

    xp_per_level = 1000
    amount_of_abilities_to_upgrade = 3
    max_ability_bonus = 10  # bonus +10, defense 20

    @staticmethod
    def add_xp(character, xp):
        """
        Add new XP.

        Args:
            character (Character): The character to improve.
            xp (int): The amount of gained XP.

        Returns:
            bool: If a new level was reached or not.

        Notes:
            level 1 -> 2 = 1000 XP
            level 2 -> 3 = 2000 XP etc

        """
        character.xp += xp
        next_level_xp = character.level * EvAdventureImprovement.xp_per_level
        return character.xp >= next_level_xp

    @staticmethod
    def level_up(character, *abilities):
        """
        Perform the level-up action.

        Args:
            character (Character): The entity to level-up.
            *abilities (str): A set of abilities (like 'strength', 'dexterity' (normally 3)
                to upgrade by 1. Max is usually +10.
        Notes:
            We block increases above a certain value, but we don't raise an error here, that
            will need to be done earlier, when the user selects the ability to increase.

        """
        roll_engine = EvAdventureRollEngine()

        character.level += 1
        for ability in set(abilities[: EvAdventureImprovement.amount_of_abilities_to_upgrades]):
            # limit to max amount allowed, each one unique
            try:
                # set at most to the max bonus
                current_bonus = getattr(character, ability)
                setattr(
                    character,
                    ability,
                    min(EvAdventureImprovement.max_ability_bonus, current_bonus + 1),
                )
            except AttributeError:
                pass

        character.hp_max = max(character.max_hp + 1, roll_engine.roll(f"{character.level}d8"))


# character sheet visualization


class EvAdventureCharacterSheet:
    """
    Generate a character sheet. This is grouped in a class in order to make
    it easier to override the look of the sheet.

    """

    sheet = """
    +----------------------------------------------------------------------------+
    | Name: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx |
    +----------------------------------------------------------------------------+
    | STR: x2xxxxx  DEX: x3xxxxx  CON: x4xxxxx  WIS: x5xxxxx  CHA: x6xxxxx       |
    +----------------------------------------------------------------------------+
    | HP: x7xxxxx  XP: x8xxxxx        Exploration speed: x9x  Combat speed: xAx  |
    +----------------------------------------------------------------------------+
    | Desc: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx |
    | xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx |
    | xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx |
    +----------------------------------------------------------------------------+
    | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
    | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
    | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
    | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
    | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
    | cccccccccccccccccccccccccccccccccc1ccccccccccccccccccccccccccccccccccccccc |
    | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
    | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
    | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
    | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
    | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
    | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
    | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
    +----------------------------------------------------------------------------+
    """

    @staticmethod
    def get(character):
        """
        Generate a character sheet from the character's stats.

        """
        equipment = character.equipment.wielded + character.equipment.worn + character.carried
        # divide into chunks of max 10 length (to go into two columns)
        equipment_table = EvTable(
            table=[equipment[i : i + 10] for i in range(0, len(equipment), 10)]
        )
        form = EvForm({"FORMCHAR": "x", "TABLECHAR": "c", "SHEET": EvAdventureCharacterSheet.sheet})
        form.map(
            cells={
                1: character.key,
                2: f"+{character.strength}({character.strength + 10})",
                3: f"+{character.dexterity}({character.dexterity + 10})",
                4: f"+{character.constitution}({character.constitution + 10})",
                5: f"+{character.wisdom}({character.wisdom + 10})",
                6: f"+{character.charisma}({character.charisma + 10})",
                7: f"{character.hp}/{character.hp_max}",
                8: character.xp,
                9: character.exploration_speed,
                "A": character.combat_speed,
                "B": character.db.desc,
            },
            tables={
                1: equipment_table,
            },
        )
        return str(form)


# singletons

# access sheet as rules.character_sheet.get(character)
character_sheet = EvAdventureCharacterSheet()
# access rolls e.g. with rules.dice.opposed_saving_throw(...)
dice = EvAdventureRollEngine()
# access improvement e.g. with rules.improvement.add_xp(character, xp)
improvement = EvAdventureImprovement()
