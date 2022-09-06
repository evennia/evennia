"""
EvAdventure character generation

"""
from evennia.prototypes.spawner import spawn
from evennia.utils.evmenu import EvMenu

from .random_tables import chargen_table
from .rules import dice

_TEMP_SHEET = """
STR +{strength} DEX +{dexterity} CON +{constitution} INT +{intelligence} WIS +{wisdom} CHA +{charisma}

{description}

{equipment}
"""


class EvAdventureCharacterGeneration:
    """
    This collects all the rules for generating a new character. An instance of this class can be
    used to track all the stats during generation and will be used to apply all the data to the
    character at the end. This class instance can also be saved on the menu to make sure a user
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
            f"{background.title()}. Wears {clothing} clothes, and has {speech} "
            f"speech. Has a {physique} physique, a {face} face, {skin} skin and "
            f"{hair} hair. Is {virtue}, but {vice}. Has been {misfortune} in "
            f"the past. Favors {alignment}."
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
