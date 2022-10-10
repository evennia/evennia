"""
Enums are constants representing different things in EvAdventure. The advantage
of using an Enum over, say, a string is that if you make a typo using an unknown
enum, Python will give you an error while a typo in a string may go through silently.

It's used as a direct reference:

    from enums import Ability

    if abi is Ability.STR:
        # ...

To get the `value` of an enum (must always be hashable, useful for Attribute lookups), use
`Ability.STR.value` (which would return 'strength' in our case).

"""
from enum import Enum


class Ability(Enum):
    """
    The six base abilities (defense is always bonus + 10)

    """

    STR = "strength"
    DEX = "dexterity"
    CON = "constitution"
    INT = "intelligence"
    WIS = "wisdom"
    CHA = "charisma"

    ARMOR = "armor"

    CRITICAL_FAILURE = "critical_failure"
    CRITICAL_SUCCESS = "critical_success"

    ALLEGIANCE_HOSTILE = "hostile"
    ALLEGIANCE_NEUTRAL = "neutral"
    ALLEGIANCE_FRIENDLY = "friendly"


class WieldLocation(Enum):
    """
    Wield (or wear) locations.

    """

    # wield/wear location
    BACKPACK = "backpack"
    WEAPON_HAND = "weapon_hand"
    SHIELD_HAND = "shield_hand"
    TWO_HANDS = "two_handed_weapons"
    BODY = "body"  # armor
    HEAD = "head"  # helmets


class ObjType(Enum):
    """
    Object types

    """

    WEAPON = "weapon"
    ARMOR = "armor"
    SHIELD = "shield"
    HELMET = "helmet"
    CONSUMABLE = "consumable"
    GEAR = "gear"
    MAGIC = "magic"
    QUEST = "quest"
    TREASURE = "treasure"
