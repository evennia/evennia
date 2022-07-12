"""
EvAdventure NPCs. This includes both friends and enemies, only separated by their AI.

"""

from evennia import DefaultCharacter
from evennia.typeclasses.attributes import AttributeProperty

from .characters import LivingMixin


class EvAdventureNPC(LivingMixin, DefaultCharacter):
    """
    This is the base class for all non-player entities, including monsters. These
    generally don't advance in level but uses a simplified, abstract measure of how
    dangerous or competent they are - the 'hit dice' (HD).

    HD indicates how much health they have and how hard they hit. In _Knave_, HD also
    defaults to being the bonus for all abilities. HP is 4 x Hit die (this can then be
    customized per-entity of course).

    Morale is set explicitly per-NPC, usually between 7 and 9.

    Monsters don't use equipment in the way PCs do, instead they have a fixed armor
    value, and their Abilities are dynamically generated from the HD (hit_dice).

    If wanting monsters or NPCs that can level and work the same as PCs, base them off the
    EvAdventureCharacter class instead.

    """

    hit_dice = AttributeProperty(default=1)
    armor = AttributeProperty(default=11)
    morale = AttributeProperty(default=9)
    hp = AttributeProperty(default=8)

    @property
    def strength(self):
        return self.hit_dice

    @property
    def dexterity(self):
        return self.hit_dice

    @property
    def constitution(self):
        return self.hit_dice

    @property
    def intelligence(self):
        return self.hit_dice

    @property
    def wisdom(self):
        return self.hit_dice

    @property
    def charisma(self):
        return self.hit_dice

    @property
    def hp_max(self):
        return self.hit_dice * 4

    def at_object_creation(self):
        """
        Start with max health.

        """
        self.hp = self.hp_max


class EvAdventureShopKeeper(EvAdventureNPC):
    """
    ShopKeeper NPC.

    """


class EvAdventureQuestGiver(EvAdventureNPC):
    """
    An NPC that acts as a dispenser of quests.

    """


class EvadventureMob(EvAdventureNPC):
    """
    Mob (mobile) NPC; this is usually an enemy.

    """
