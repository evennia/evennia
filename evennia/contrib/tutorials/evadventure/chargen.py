"""
EvAdventure character generation

"""
from evennia.prototypes.spawner import spawn
from evennia.utils.evmenu import EvMenu

from .random_tables import chargen_table
from .rules import dice

_ABILITIES = {
    "STR": "strength",
    "DEX": "dexterity",
    "CON": "constitution",
    "INT": "intelligence",
    "WIS": "wisdom",
    "CHA": "charisma",
}

_TEMP_SHEET = """
{name}

STR +{strength}
DEX +{dexterity}
CON +{constitution}
INT +{intelligence}
WIS +{wisdom}
CHA +{charisma}

{description}

Your belongings:
{equipment}
"""


class EvAdventureChargenStorage:
    """
    This collects all the rules for generating a new character. An instance of this class is used
    to pass around the current character state during character generation and also applied to
    the character at the end. This class instance can also be saved on the menu to make sure a user
    is not losing their half-created character.

    Note:
        In standard Knave, the character's attribute bonus is rolled randomly and will give a
        value 1-6; and there is no guarantee for 'equal' starting characters.

        Knave uses a d8 roll to get the initial hit points. We will follow the recommendation
        from the rule that we will use a minimum of 5 HP.

        We *will* roll random start equipment though. Contrary to standard Knave, we'll also
        randomly assign the starting weapon among a small selection of equal-dmg weapons (since
        there is no GM to adjudicate a different choice).

    """

    def __init__(self):
        # you are only allowed to tweak abilities once
        self.ability_changes = 0

    def _random_ability(self):
        return min(dice.roll("1d6"), dice.roll("1d6"), dice.roll("1d6"))

    def generate(self):
        """
        Generate random values for character.

        """

        # name will likely be modified later
        self.name = dice.roll_random_table("1d282", chargen_table["name"])

        # base attribute values
        self.strength = self._random_ability()
        self.dexterity = self._random_ability()
        self.constitution = self._random_ability()
        self.intelligence = self._random_ability()
        self.wisdom = self._random_ability()
        self.charisma = self._random_ability()

        # physical attributes (only for rp purposes)
        physique = dice.roll_random_table("1d20", chargen_table["physique"])
        face = dice.roll_random_table("1d20", chargen_table["face"])
        skin = dice.roll_random_table("1d20", chargen_table["skin"])
        hair = dice.roll_random_table("1d20", chargen_table["hair"])
        clothing = dice.roll_random_table("1d20", chargen_table["clothing"])
        speech = dice.roll_random_table("1d20", chargen_table["speech"])
        virtue = dice.roll_random_table("1d20", chargen_table["virtue"])
        vice = dice.roll_random_table("1d20", chargen_table["vice"])
        background = dice.roll_random_table("1d20", chargen_table["background"])
        misfortune = dice.roll_random_table("1d20", chargen_table["misfortune"])
        alignment = dice.roll_random_table("1d20", chargen_table["alignment"])

        self.desc = (
            f"You are {physique} with a {face} face and {hair} hair, {speech} speech, "
            f"and {clothing} clothing. "
            f"You were a {background.title()}, but you were {misfortune} and ended up a knave. "
            f"You are {virtue} but also {vice}. You are of the {alignment} alignment."
        )

        # same for all
        self.hp_max = max(5, dice.roll("1d8"))
        self.hp = self.hp_max
        self.xp = 0
        self.level = 1

        # random equipment
        self.armor = dice.roll_random_table("1d20", chargen_table["armor"])

        _helmet_and_shield = dice.roll_random_table("1d20", chargen_table["helmets and shields"])
        self.helmet = "helmet" if "helmet" in _helmet_and_shield else "none"
        self.shield = "shield" if "shield" in _helmet_and_shield else "none"

        self.weapon = dice.roll_random_table("1d20", chargen_table["starting weapon"])

        self.backpack = [
            "ration",
            "ration",
            dice.roll_random_table("1d20", chargen_table["dungeoning gear"]),
            dice.roll_random_table("1d20", chargen_table["dungeoning gear"]),
            dice.roll_random_table("1d20", chargen_table["general gear 1"]),
            dice.roll_random_table("1d20", chargen_table["general gear 2"]),
        ]

    def show_sheet(self):
        """
        Show a temp character sheet, a compressed version of the real thing.

        """
        equipment = (
            str(item)
            for item in [self.armor, self.helmet, self.shield, self.weapon] + self.backpack
            if item
        )

        return _TEMP_SHEET.format(
            name=self.name,
            strength=self.strength,
            dexterity=self.dexterity,
            constitution=self.constitution,
            intelligence=self.intelligence,
            wisdom=self.wisdom,
            charisma=self.charisma,
            description=self.desc,
            equipment=", ".join(equipment),
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

        character.hp = self.hp
        character.level = self.level
        character.xp = self.xp

        character.db.desc = self.build_desc()

        if self.weapon:
            weapon = spawn(self.weapon)
            character.equipment.move(weapon)
        if self.shield:
            shield = spawn(self.shield)
            character.equipment.move(shield)
        if self.armor:
            armor = spawn(self.armor)
            character.equipment.move(armor)
        if self.helmet:
            helmet = spawn(self.helmet)
            character.equipment.move(helmet)

        for item in self.backpack:
            item = spawn(item)
            character.equipment.store(item)


# chargen menu


def node_chargen(caller, raw_string, **kwargs):
    """
    This node is the central point of chargen. We return here to see our current
    sheet and break off to edit different parts of it.

    In Knave, not so much can be changed.
    """
    tmp_character = kwargs["tmp_character"]

    text = tmp_character.show_sheet()

    options = [{"desc": "Change your name", "goto": ("node_change_name", kwargs)}]
    if tmp_character.ability_changes <= 0:
        options.append(
            {
                "desc": "Swap two of your ability scores (once)",
                "goto": ("node_swap_abilities", kwargs),
            }
        )
    options.append(
        {"desc": "Accept and create character", "goto": ("node_apply_character", kwargs)},
    )

    return text, options


def _update_name(caller, raw_string, **kwargs):
    """
    Used by node_change_name below to check what user entered and update the name if appropriate.

    """
    if raw_string:
        tmp_character = kwargs["tmp_character"]
        tmp_character.name = raw_string.lower().capitalize()

    return "node_chargen", kwargs


def node_change_name(caller, raw_string, **kwargs):
    """
    Change the random name of the character.

    """
    tmp_character = kwargs["tmp_character"]

    text = (f"Your current name is |w{tmp_character.name}|n. "
            "Enter a new name or leave empty to abort."

    options = {"key": "_default", "goto": (_update_name, kwargs)}

    return text, options


def _swap_abilities(caller, raw_string, **kwargs):
    """
    Used by node_swap_abilities to parse the user's input and swap ability
    values.

    """
    if raw_string:
        abi1, *abi2 = raw_string.split(" ", 1)
        if not abi2:
            caller.msg("That doesn't look right.")
            return None, kwargs
        abi2 = abi2[0]
        abi1, abi2 = abi1.upper().strip(), abi2.upper().strip()
        if abi1 not in _ABILITIES or abi2 not in _ABILITIES:
            caller.msg("Not a familiar set of abilites.")
            return None, kwargs

        # looks okay = swap values. We need to convert STR to strength etc
        tmp_character = kwargs["tmp_character"]
        abi1 = _ABILITIES[abi1]
        abi2 = _ABILITIES[abi2]
        abival1 = getattr(tmp_character, abi1)
        abival2 = getattr(tmp_character, abi2)

        setattr(tmp_character, abi1, abival2)
        setattr(tmp_character, abi2, abival1)

    return "node_chargen", kwargs


def node_swap_abilities(caller, raw_string, **kwargs):
    """
    One is allowed to swap the values of two abilities around, once.

    """
    tmp_character = kwargs["tmp_character"]

    text = f"""
Your current abilities:

STR +{tmp_character.strength}
DEX +{tmp_character.dexterity}
CON +{tmp_character.constitution}
INT +{tmp_character.intelligence}
WIS +{tmp_character.wisdom}
CHA +{tmp_character.charisma}

You can swap the values of two abilities around.
You can only do this once, so choose carefully!

To swap the values of e.g.  STR and INT, write |wSTR INT|n. Empty to abort.
"""

    options = {"key": "_default", "goto": (_swap_abilities, kwargs)}

    return text, options


def node_apply_character(caller, raw_string, **kwargs):
    """
    End chargen and create the character. We will also puppet it.

    """
    tmp_character = kwargs["tmp_character"]

    tmp_character.apply(caller)

    caller.msg("Character created!")


def start_chargen(caller, session=None):
    """
    This is a start point for spinning up the chargen from a command later.

    """

    menutree = {
        "node_chargen": node_chargen,
        "node_change_name": node_change_name,
        "node_swap_abilities": node_swap_abilities,
    }

    # this generates all random components of the character
    tmp_character = EvAdventureChargenStorage()

    EvMenu(caller, menutree, startnode="node_chargen", session=session, tmp_character=tmp_character)
