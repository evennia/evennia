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


class EvAdventureDungeonRoom(EvAdventureRoom):
    """
    Dangerous dungeon room.

    """

    allow_combat = True
    allow_death = True

    # dungeon generation attributes; set when room is created
    back_exit = AttributeProperty(None, autocreate=False)
    dungeon_orchestrator = AttributeProperty(None, autocreate=False)
    xy_coords = AttributeProperty(None, autocreate=False)

    def at_object_creation(self):
        """
        Set the `not_clear` tag on the room. This is removed when the room is
        'cleared', whatever that means for each room.

        We put this here rather than in the room-creation code so we can override
        easier (for example we may want an empty room which auto-clears).

        """
        self.tags.add("not_clear")

    def get_display_footer(self, looker, **kwargs):
        """
        Show if the room is 'cleared' or not as part of its description.

        """
        if self.tags.get("not_clear", "dungeon_room"):
            # this tag is cleared when the room is resolved, whatever that means.
            return "|rThe path forwards is blocked!|n"
        return ""
