"""
EvAdventure rooms.



"""

from copy import deepcopy

from evennia import AttributeProperty, DefaultCharacter, DefaultRoom, TagProperty
from evennia.utils.utils import inherits_from

_MAP_GRID = [
    [" ", " ", " ", " ", " "],
    [" ", " ", " ", " ", " "],
    [" ", " ", "@", " ", " "],
    [" ", " ", " ", " ", " "],
    [" ", " ", " ", " ", " "],
]
_EXIT_GRID_SHIFT = {
    "north": (0, 1, "|"),
    "east": (1, 0, "-"),
    "south": (0, -1, "|"),
    "west": (-1, 0, "-"),
    "northeast": (1, 1, "/"),
    "southeast": (1, -1, "\\"),
    "southwest": (-1, -1, "/"),
    "northwest": (-1, 1, "\\"),
}


class EvAdventureRoom(DefaultRoom):
    """
    Simple room supporting some EvAdventure-specifics.

    """

    allow_combat = False
    allow_pvp = False
    allow_death = False

    def format_appearance(self, appearance, looker, **kwargs):
        """Don't left-strip the appearance string"""
        return appearance.rstrip()

    def get_display_header(self, looker, **kwargs):
        """
        Display the current location as a mini-map.
        """
        if not inherits_from(looker, DefaultCharacter):
            # we don't need a map for npcs/mobs
            return ""

        # build a map
        map_grid = deepcopy(_MAP_GRID)
        dx0, dy0 = 2, 2
        map_grid[dy0][dx0] = "|w@|n"
        for exi in self.exits:
            dx, dy, symbol = _EXIT_GRID_SHIFT.get(exi.key, (None, None, None))
            if symbol is None:
                # we have a non-cardinal direction to go to - mark us blue to indicate this
                map_grid[dy0][dx0] = "|b>|n"
                continue
            map_grid[dy0 + dy][dx0 + dx] = symbol
            if exi.destination != self:
                map_grid[dy0 + dy + dy][dx0 + dx + dx] = "X"

        # Note that on the grid, dy is really going *downwards* (origo is
        # in the top left), so we need to reverse the order at the end to mirror it
        # vertically and have it come out right.
        return "  " + "\n  ".join("".join(line) for line in reversed(map_grid))


class EvAdventurePvPRoom(EvAdventureRoom):
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
