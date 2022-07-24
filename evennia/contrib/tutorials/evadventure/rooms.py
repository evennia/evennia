"""
EvAdventure rooms.



"""

from evennia import AttributeProperty, DefaultRoom, TagProperty


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

    def get_display_footer(self, looker, **kwargs):
        """
        Show if the room is 'cleared' or not as part of its description.

        """
        return "|yNon-lethal PvP combat is allowed here!|n"
