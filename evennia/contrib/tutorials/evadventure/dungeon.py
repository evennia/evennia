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

Each room in the dungeon starts with a Tag `not_clear`; while this is set, all exits out
of the room (not the one they came from) is blocked. When whatever problem the room
offers has been solved (such as a puzzle or a battle), the tag is removed and the player(s)
can choose which exit to leave through.

"""

from datetime import datetime, timedelta
from math import sqrt
from random import randint, random, shuffle

from evennia.objects.objects import DefaultExit
from evennia.scripts.scripts import DefaultScript
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils import create, search
from evennia.utils.utils import inherits_from

from .rooms import EvAdventureRoom

# aliases for cardinal directions
_AVAILABLE_DIRECTIONS = [
    "north",
    "east",
    "south",
    "west",
    # commented out to make the dungeon simpler to navigate
    # "northeast", "southeast", "southwest", "northwest",
]

_EXIT_ALIASES = {
    "north": ("n",),
    "east": ("e",),
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
# Dungeon orchestrator and room / exits
# --------------------------------------------------


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

    @property
    def is_room_clear(self):
        return not bool(self.tags.get("not_clear", category="dungeon_room"))

    def clear_room(self):
        self.tags.remove("not_clear", category="dungeon_room")

    def at_object_creation(self):
        """
        Set the `not_clear` tag on the room. This is removed when the room is
        'cleared', whatever that means for each room.

        We put this here rather than in the room-creation code so we can override
        easier (for example we may want an empty room which auto-clears).

        """
        self.tags.add("not_clear", category="dungeon_room")

    def get_display_footer(self, looker, **kwargs):
        """
        Show if the room is 'cleared' or not as part of its description.

        """
        if self.is_room_clear:
            return ""
        else:
            return "|rThe path forwards is blocked!|n"


class EvAdventureDungeonExit(DefaultExit):
    """
    Dungeon exit. This will not create the target room until it's traversed.
    It must be created referencing the dungeon_orchestrator it belongs to.

    """

    def at_object_creation(self):
        """
        We want to block progressing forward unless the room is clear.

        """
        self.locks.add("traverse:not objloctag(not_clear, dungeon_room)")

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """
        Called when traversing. `target_location` will be None if the
        target was not yet created.

        """
        if target_location == self.location:
            self.destination = target_location = self.location.db.dungeon_orchestrator.new_room(
                self
            )
            if self.id in self.location.dungeon_orchestrator.unvisited_exits:
                self.location.dungeon_orchestrator.unvisited_exits.remove(self.id)

        super().at_traverse(traversing_object, target_location, **kwargs)

    def at_failed_traverse(self, traversing_object, **kwargs):
        """
        Called when failing to traverse.

        """
        traversing_object.msg("You can't get through this way yet!")


def room_generator(dungeon_orchestrator, depth, coords):
    """
    Plugin room generator

    This default one returns the same empty room.

    Args:
        dungeon_orchestrator (EvAdventureDungeonOrchestrator): The current orchestrator.
        depth (int): The 'depth' of the dungeon (radial distance from start room) this
            new room will be placed at.
        coords (tuple): The `(x,y)` coords that the new room will be created at.

    """
    room_typeclass = EvAdventureDungeonRoom

    # simple map of depth to name and desc of room
    name_depth_map = {
        1: ("Water-logged passage", "This earth-walled passage is dripping of water."),
        2: ("Passage with roots", "Roots are pushing through the earth walls."),
        3: ("Hardened clay passage", "The walls of this passage is of hardened clay."),
        4: ("Clay with stones", "This passage has clay with pieces of stone embedded."),
        5: ("Stone passage", "Walls are crumbling stone, with roots passing through it."),
        6: ("Stone hallway", "Walls are cut from rough stone."),
        7: ("Stone rooms", "A stone room, built from crude and heavy blocks."),
        8: ("Granite hall", "The walls are of well-fitted granite blocks."),
        9: ("Marble passages", "The walls are blank and shiny marble."),
        10: ("Furnished rooms", "The marble walls have tapestries and furnishings."),
    }
    key, desc = name_depth_map.get(depth, ("Dark rooms", "There is very dark here."))

    new_room = create.create_object(
        room_typeclass,
        key=key,
        attributes=(
            ("desc", desc),
            ("xy_coords", coords),
            ("dungeon_orchestrator", dungeon_orchestrator),
        ),
    )
    return new_room


class EvAdventureDungeonOrchestrator(DefaultScript):
    """
    One script is created per dungeon 'branch' created. The orchestrator is
    responsible for determining what is created next when a character enters an
    exit within the dungeon.

    """

    # this determines how branching the dungeon will be
    max_unexplored_exits = 2
    max_new_exits_per_room = 2

    rooms = AttributeProperty(list())
    unvisited_exits = AttributeProperty(list())
    highest_depth = AttributeProperty(0)

    last_updated = AttributeProperty(datetime.utcnow())

    # the room-generator function; copied from the same-name value on the start-room when the
    # orchestrator is first created
    room_generator = AttributeProperty(None, autocreate=False)

    # (x,y): room coordinates used up by orchestrator
    xy_grid = AttributeProperty(dict())
    start_room = AttributeProperty(None, autocreate=False)

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

    def delete(self):
        """
        Clean up the entire dungeon along with the orchestrator.

        """
        # first secure all characters in this branch back to the start room
        characters = search.search_object_by_tag(self.key, category="dungeon_character")
        start_room = self.start_room
        for character in characters:
            start_room.msg_contents(
                "Suddenly someone stumbles out of a dark exit, covered in dust!"
            )
            character.location = start_room
            character.msg(
                "|rAfter a long time of silence, the room suddenly rumbles and then collapses! "
                "All turns dark ...|n\n\nThen you realize you are back where you started."
            )
            character.tags.remove(self.key, category="dungeon_character")
        # next delete all rooms in the dungeon (this will also delete exits)
        rooms = search.search_object_by_tag(self.key, category="dungeon_room")
        for room in rooms:
            room.delete()
        # finally delete the orchestrator itself
        super().delete()

    def new_room(self, from_exit):
        """
        Create a new Dungeon room leading from the provided exit.

        Args:
            from_exit (Exit): The exit leading to this new room.

        """
        self.last_updated = datetime.utcnow()
        # figure out coordinate of old room and figure out what coord the
        # new one would get
        source_location = from_exit.location
        x, y = source_location.attributes.get("xy_coords", default=(0, 0))
        dx, dy = _EXIT_GRID_SHIFT.get(from_exit.key, (0, 1))
        new_x, new_y = (x + dx, y + dy)

        # the dungeon's depth acts as a measure of the current difficulty level. This is the radial
        # distance from the (0, 0) (the entrance). The Orchestrator also tracks the highest
        # depth achieved.
        depth = int(sqrt(new_x**2 + new_y**2))

        new_room = self.room_generator(self, depth, (new_x, new_y))

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
                direction for direction in _AVAILABLE_DIRECTIONS if direction != back_exit_key
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


class EvAdventureDungeonStartRoomExit(DefaultExit):
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
            self.location.room_generator
            dungeon_orchestrator = create.create_script(
                EvAdventureDungeonOrchestrator,
                key=f"dungeon_orchestrator_{self.key}_{datetime.utcnow()}",
                attributes=(
                    ("start_room", self.location),
                    ("room_generator", self.location.room_generator),
                ),
            )
            self.destination = target_location = dungeon_orchestrator.new_room(self)
            # make sure to tag character when entering so we can find them again later
            traversing_object.tags.add(dungeon_orchestrator.key, category="dungeon_character")

        super().at_traverse(traversing_object, target_location, **kwargs)


class EvAdventureStartRoomResetter(DefaultScript):
    """
    Simple ticker-script. Introduces a chance of the room's exits cycling every interval.

    """

    def at_script_creation(self):
        self.key = "evadventure_dungeon_startroom_resetter"

    def at_repeat(self):
        """
        Called every time the script repeats.

        """
        room = self.obj
        for exi in room.exits:
            if inherits_from(exi, EvAdventureDungeonStartRoomExit) and random() < 0.5:
                exi.reset_exit()


class EvAdventureDungeonBranchDeleter(DefaultScript):
    """
    Cleanup script. After some time a dungeon branch will 'collapse', forcing all players in it
    back to the start room.

    """

    # set at creation time when the start room is created
    branch_max_life = AttributeProperty(0, autocreate=False)

    def at_script_creation(self):
        self.key = "evadventure_dungeon_branch_deleter"

    def at_repeat(self):
        """
        Go through all dungeon-orchestrators and find which ones are too old.

        """
        max_dt = timedelta(seconds=self.branch_max_life)
        max_allowed_date = datetime.utcnow() - max_dt

        for orchestrator in EvAdventureDungeonOrchestrator.objects.all():
            if orchestrator.last_updated < max_allowed_date:
                # orchestrator is too old; tell it to clean up and delete itself
                orchestrator.delete()


class EvAdventureDungeonStartRoom(EvAdventureDungeonRoom):
    """
    The start room is the only permanent part of the dungeon. Exits leading from this room (except
    one leading back outside) each create/links to a separate dungeon branch/instance.

    - A script will reset each exit every 5 mins; after that time, entering the exit will spawn
        a new branch-instance instead of leading to the one before.
    - Another script will check age of branch instance every hour; once an instance has been
        inactive for a week, it will 'collapse', forcing everyone inside back to the start room.

    The actual exits should be created in the build script.

    """

    recycle_time = 60 * 5  # 5 mins
    branch_check_time = 60 * 60  # one hour
    branch_max_life = 60 * 60 * 24 * 7  # 1 week

    # allow for a custom room_generator function
    room_generator = AttributeProperty(lambda: room_generator, autocreate=False)

    def get_display_footer(self, looker, **kwargs):
        return (
            "|yYou sense that if you want to team up, "
            "you must all pick the same path from here ... or you'll quickly get separated.|n"
        )

    def at_object_creation(self):
        # want to set the script interval on creation time, so we use create_script with obj=self
        # instead of self.scripts.add() here
        create.create_script(
            EvAdventureStartRoomResetter, obj=self, interval=self.recycle_time, autostart=True
        )
        create.create_script(
            EvAdventureDungeonBranchDeleter,
            obj=self,
            interval=self.branch_check_time,
            autostart=True,
            attributes=(("branch_max_life", self.branch_max_life),),
        )

    def at_object_receive(self, obj, source_location, **kwargs):
        """
        Make sure to clean the dungeon branch-tag from characters when leaving a dungeon branch.

        """
        obj.tags.remove(category="dungeon_character")
