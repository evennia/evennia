"""
Dungeon system

This creates a procedurally generated dungeon.

The dungone originates in an entrance room with exits that spawn a new dungeon connection every X
minutes. As long as characters go through the same exit within that time, they will all end up in
the same dungeon 'branch', otherwise they will go into separate, un-connected dungeon 'branches'.
They can always go back to the start room, but this will become a one-way exit back.

When moving through the dungeon, a new room is not generated until characters
decided to go in that direction. Each room is tagged with the specific 'instance'
id of that particular branch of dungon. When no characters remain in the branch,
the branch is deleted.

"""

from datetime import datetime
from math import sqrt
from random import randint, random, shuffle

from evennia import AttributeProperty, DefaultExit, DefaultScript
from evennia.utils import create
from evennia.utils.utils import inherits_from

from .rooms import EvAdventureDungeonRoom

# aliases for cardinal directions
_EXIT_ALIASES = {
    "north": ("n",),
    "east": ("w",),
    "south": ("s",),
    "west": ("w",),
    "northeast": ("ne",),
    "southeast": ("se",),
    "southwest": ("sw",),
    "northwest": ("nw",),
}
# finding the reverse cardinal direction
_EXIT_REVERSE_MAPPING = {
    "north": "south",
    "east": "west",
    "south": "north",
    "west": "east",
    "northeast": "southwest",
    "southeast": "northwest",
    "southwest": "northeast",
    "northwest": "southeast",
}

# how xy coordinate shifts by going in direction
_EXIT_GRID_SHIFT = {
    "north": (0, 1),
    "east": (1, 0),
    "south": (0, -1),
    "west": (-1, 0),
    "northeast": (1, 1),
    "southeast": (1, -1),
    "southwest": (-1, -1),
    "northwest": (-1, 1),
}


# --------------------------------------------------
# Dungeon orchestrator and rooms
# --------------------------------------------------


class EvAdventureDungeonExit(DefaultExit):
    """
    Dungeon exit. This will not create the target room until it's traversed.
    It must be created referencing the dungeon_orchestrator it belongs to.

    """

    dungeon_orchestrator = AttributeProperty(None, autocreate=False)

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """
        Called when traversing. `target_location` will be None if the
        target was not yet created.

        """
        if not target_location:
            self.destination = target_location = self.dungeon_orchestrator.new_room(self)
        super().at_traverse(traversing_object, target_location, **kwargs)


class EvAdventureDungeonOrchestrator(DefaultScript):
    """
    One script is created per dungeon 'branch' created. The orchestrator is
    responsible for determining what is created next when a character enters an
    exit within the dungeon.

    """

    # this determines how branching the dungeon will be
    max_unexplored_exits = 5
    max_new_exits_per_room = 3

    rooms = AttributeProperty(list())
    n_unvisited_exits = AttributeProperty(list())
    highest_depth = AttributeProperty(0)

    # (x,y): room
    xy_grid = AttributeProperty(dict())

    def register_exit_traversed(self, exit):
        """
        Tell the system the given exit was traversed. This allows us to track how many unvisited
        paths we have so as to not have it grow exponentially.

        """
        if exit.id in self.unvisited_exits:
            self.unvisited_exits.remove(exit.id)

    def create_out_exit(self, location, exit_direction="north"):
        """
        Create outgoing exit from a room. The target room is not yet created.

        """
        out_exit, _ = EvAdventureDungeonExit.create(
            key=exit_direction, location=location, aliases=_EXIT_ALIASES[exit_direction]
        )
        self.unvisited_exits.append(out_exit.id)

    def _generate_room(self, depth, coords):
        # TODO - determine what type of room to create here based on location and depth
        room_typeclass = EvAdventureDungeonRoom
        new_room = create.create_object(
            room_typeclass,
            key="Dungeon room",
            tags=((self.key,),),
            attributes=(("xy_coord", coords, "dungeon_xygrid"),),
        )
        return new_room

    def new_room(self, from_exit):
        """
        Create a new Dungeon room leading from the provided exit.

        """
        # figure out coordinate of old room and figure out what coord the
        # new one would get
        source_location = from_exit.location
        x, y = source_location.get("xy_coord", category="dungeon_xygrid", default=(0, 0))
        dx, dy = _EXIT_GRID_SHIFT.get(from_exit.key, (1, 0))
        new_x, new_y = (x + dx, y + dy)

        # the dungeon's depth acts as a measure of the current difficulty level. This is the radial
        # distance from the (0, 0) (the entrance). The Orchestrator also tracks the highest
        # depth achieved.
        depth = int(sqrt(new_x**2 + new_y**2))

        new_room = self._generate_room(depth, (new_x, new_y))

        self.xy_grid[(new_x, new_y)] = new_room

        # always make a return exit back to where we came from
        back_exit_key = (_EXIT_REVERSE_MAPPING.get(from_exit.key, "back"),)
        EvAdventureDungeonExit(
            key=back_exit_key,
            aliases=_EXIT_ALIASES.get(back_exit_key, ()),
            location=new_room,
            destination=from_exit.location,
            attributes=(("desc", "A dark passage."),),
        )

        # figure out what other exits should be here, if any
        n_unexplored = len(self.unvisited_exits)
        if n_unexplored >= self.max_unexplored_exits:
            # no more exits to open - this is a dead end.
            return
        else:
            n_exits = randint(1, min(self.max_new_exits_per_room, n_unexplored))
            back_exit = from_exit.key
            available_directions = [
                direction for direction in _EXIT_ALIASES if direction != back_exit
            ]
            # randomize order of exits
            shuffle(available_directions)
            for _ in range(n_exits):
                while available_directions:
                    # get a random direction and check so there isn't a room already
                    # created in that direction
                    direction = available_directions.pop(0)
                    dx, dy = _EXIT_GRID_SHIFT(direction)
                    target_coord = (new_x + dx, new_y + dy)
                    if target_coord not in self.xy_grid:
                        # no room there - make an exit to it
                        self.create_out_exit(new_room, direction)
                        break

        self.highest_depth = max(self.highest_depth, depth)


# --------------------------------------------------
# Start room
# --------------------------------------------------


class EvAdventureStartRoomExit(DefaultExit):
    """
    Traversing this exit will either lead to an existing dungeon branch or create
    a new one.

    """

    dungeon_orchestrator = AttributeProperty(None, autocreate=False)

    def reset_exit(self):
        """
        Flush the exit, so next traversal creates a new dungeon branch.

        """
        self.dungeon_orchestrator = self.destination = None

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """
        When traversing create a new orchestrator if one is not already assigned.

        """
        if target_location is None or self.dungeon_orchestrator is None:
            self.dungeon_orchestrator, _ = EvAdventureDungeonOrchestrator.create(
                f"dungeon_orchestrator_{datetime.utcnow()}",
            )
            target_location = self.destination = self.dungeon_orchestrator.new_room(self)

        super().at_traverse(traversing_object, target_location, **kwargs)


class EvAdventureStartRoomResetter(DefaultScript):
    """
    Simple ticker-script. Introduces a chance of the room's exits cycling every interval.

    """

    def at_repeat(self):
        """
        Called every time the script repeats.

        """
        room = self.obj
        for exi in room.exits:
            if inherits_from(exi, EvAdventureStartRoomExit) and random() < 0.5:
                exi.reset_exit()


class EvAdventureDungeonRoomStart(EvAdventureDungeonRoom):
    """
    Exits leading out of the start room, (except one leading outside) will lead to a different
    dungeon-branch, and after a certain time, the given exit will instead spawn a new branch. This
    room is responsible for cycling these exits regularly.

    The actual exits should be created in the build script.

    """

    recycle_time = 5 * 60  # seconds

    def at_object_creation(self):
        self.scripts.add(EvAdventureStartRoomResetter, interval=self.recycle_time, autostart=True)
