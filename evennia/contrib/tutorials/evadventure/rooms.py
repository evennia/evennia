"""
EvAdventure rooms.



"""

from evennia import AttributeProperty, DefaultRoom


class EvAdventureRoom(DefaultRoom):
    """
    Simple room supporting some EvAdventure-specifics.

    """

    allow_combat = False
    allow_pvp = False
    allow_death = False


class EvAdventurePvPRoom(DefaultRoom):
    """
    Room where PvP can happen, but noone gets killed.

    """

    allow_combat = True
    allow_pvp = True


class EvAdventureDungeonRoom(EvAdventureRoom):
    """
    Dangerous dungeon room.

    """

    allow_combat = True
    allow_death = True
