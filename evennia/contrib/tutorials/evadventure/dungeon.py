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

from evennia.objects.objects import DefaultExit
from evennia.scripts.scripts import DefaultScript
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils import create, search
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

    def at_object_creation(self):
        """
        We want to block progressing forward unless the room is clear.

        """
        self.locks.add("traverse:not tag(not_clear, dungeon_room)")

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """
        Called when traversing. `target_location` will be None if the
        target was not yet created.

        """
        if target_location == self.location:
            self.destination = target_location = self.location.db.dungeon_orchestrator.new_room(
                self
            )
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
    unvisited_exits = AttributeProperty(list())
    highest_depth = AttributeProperty(0)

    # (x,y): room coordinates used up by orchestrator
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
        out_exit = create.create_object(
            EvAdventureDungeonExit,
            key=exit_direction,
            location=location,
            aliases=_EXIT_ALIASES[exit_direction],
        )
        self.unvisited_exits.append(out_exit.id)

    def _generate_dungeon_room(self, depth, coords):
        # TODO - determine what type of room to create here based on location and depth
        room_typeclass = EvAdventureDungeonRoom
        new_room = create.create_object(
            room_typeclass,
            key="Dungeon room",
            attributes=(
                ("xy_coords", coords, "dungeon_xygrid"),
                ("dungeon_orchestrator", self),
            ),
        )
        return new_room

    def delete(self):
        """
        Clean up the entire dungeon along with the orchestrator.

        """
        rooms = search.search_object_by_tag(self.key, category="dungeon_room")
        for room in rooms:
            room.delete()
        super().delete()

    def new_room(self, from_exit):
        """
        Create a new Dungeon room leading from the provided exit.

        Args:
            from_exit (Exit): The exit leading to this new room.

        """
        # figure out coordinate of old room and figure out what coord the
        # new one would get
        source_location = from_exit.location
        x, y = source_location.attributes.get("xy_coord", category="dungeon_xygrid", default=(0, 0))
        dx, dy = _EXIT_GRID_SHIFT.get(from_exit.key, (1, 0))
        new_x, new_y = (x + dx, y + dy)

        # the dungeon's depth acts as a measure of the current difficulty level. This is the radial
        # distance from the (0, 0) (the entrance). The Orchestrator also tracks the highest
        # depth achieved.
        depth = int(sqrt(new_x**2 + new_y**2))

        new_room = self._generate_dungeon_room(depth, (new_x, new_y))

        self.xy_grid[(new_x, new_y)] = new_room

        # always make a return exit back to where we came from
        back_exit_key = _EXIT_REVERSE_MAPPING.get(from_exit.key, "back")
        create.create_object(
            EvAdventureDungeonExit,
            key=back_exit_key,
            aliases=_EXIT_ALIASES.get(back_exit_key, ()),
            location=new_room,
            destination=from_exit.location,
            attributes=(
                (
                    "desc",
                    "A dark passage.",
                ),
            ),
            # we default to allowing back-tracking (also used for fleeing)
            locks=("traverse: true()",),
        )

        # figure out what other exits should be here, if any
        n_unexplored = len(self.unvisited_exits)

        if n_unexplored < self.max_unexplored_exits:
            # we have a budget of unexplored exits to open
            n_exits = min(self.max_new_exits_per_room, self.max_unexplored_exits)
            if n_exits > 1:
                n_exits = randint(1, n_exits)
            available_directions = [
                direction for direction in _EXIT_ALIASES if direction != back_exit_key
            ]
            # randomize order of exits
            shuffle(available_directions)
            for _ in range(n_exits):
                while available_directions:
                    # get a random direction and check so there isn't a room already
                    # created in that direction
                    direction = available_directions.pop(0)
                    dx, dy = _EXIT_GRID_SHIFT[direction]
                    target_coord = (new_x + dx, new_y + dy)
                    if target_coord not in self.xy_grid and target_coord != (0, 0):
                        # no room there (and not back to start room) - make an exit to it
                        self.create_out_exit(new_room, direction)
                        # we create this to avoid other rooms linking here, but don't create the
                        # room yet
                        self.xy_grid[target_coord] = None
                        break

        self.highest_depth = max(self.highest_depth, depth)

        return new_room


# --------------------------------------------------
# Start room
# --------------------------------------------------


class EvAdventureStartRoomExit(DefaultExit):
    """
    Traversing this exit will either lead to an existing dungeon branch or create
    a new one.

    Since exits need to have a destination, we start out having them loop back to
    the same location and change this whenever someone actually traverse them. The
    act of passing through creates a room on the other side.

    """

    def reset_exit(self):
        """
        Flush the exit, so next traversal creates a new dungeon branch.

        """
        self.destination = self.location

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """
        When traversing create a new orchestrator if one is not already assigned.

        """
        if target_location == self.location:
            # make a global orchestrator script for this dungeon branch
            dungeon_orchestrator = create.create_script(
                EvAdventureDungeonOrchestrator,
                key=f"dungeon_orchestrator_{self.key}_{datetime.utcnow()}",
            )
            self.destination = target_location = dungeon_orchestrator.new_room(self)

        super().at_traverse(traversing_object, target_location, **kwargs)


class EvAdventureStartRoomResetter(DefaultScript):
    """
    Simple ticker-script. Introduces a chance of the room's exits cycling every interval.

    """

    def at_script_creation(self):
        self.key = "evadventure_startroom_resetter"

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
        # want to set the script interval on creation time, so we use create_script with obj=self
        # instead of self.scripts.add() here
        create.create_script(
            EvAdventureStartRoomResetter, obj=self, interval=self.recycle_time, autostart=True
        )
