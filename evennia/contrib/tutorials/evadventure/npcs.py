"""
EvAdventure NPCs. This includes both friends and enemies, only separated by their AI.

"""

from .characters import EvAdventureCharacter

class EvAdventureNPC(EvAdventureCharacter):
    """
    Base typeclass for NPCs. They have the features of a Character except
    they have tooling for AI and for acting as quest-gives and shop-keepers.

    """


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
