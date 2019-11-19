# -*- coding: utf-8 -*-

"""
Evennia World Builder

Contribution - Cloud_Keeper 2016

Build a map from a 2D ASCII map.

This is a command which takes two inputs:

≈≈≈≈≈
≈♣n♣≈   MAP_LEGEND = {("♣", "♠"): build_forest,
≈∩▲∩≈                 ("∩", "n"): build_mountains,
≈♠n♠≈                 ("▲"): build_temple}
≈≈≈≈≈

A string of ASCII characters representing a map and a dictionary of functions
containing build instructions. The characters of the map are iterated over and
compared to a list of trigger characters. When a match is found the
corresponding function is executed generating the rooms, exits and objects as
defined by the users build instructions. If a character is not a match to
a provided trigger character (including spaces) it is simply skipped and the
process continues.

For instance, the above map represents a temple (▲) amongst mountains (n,∩)
in a forest (♣,♠) on an island surrounded by water (≈). Each character on the
first line is iterated over but as there is no match with our MAP_LEGEND it
is skipped. On the second line it finds "♣" which is a match and so the
`build_forest` function is called. Next the `build_mountains` function is
called and so on until the map is completed. Building instructions are passed
the following arguments:
    x         - The rooms position on the maps x axis
    y         - The rooms position on the maps y axis
    caller    - The account calling the command
    iteration - The current iterations number (0, 1 or 2)
    room_dict - A dictionary containing room references returned by build
                functions where tuple coordinates are the keys (x, y).
                ie room_dict[(2, 2)] will return the temple room above.

Building functions should return the room they create. By default these rooms
are used to create exits between valid adjacent rooms to the north, south,
east and west directions. This behaviour can turned off with the use of switch
arguments. In addition to turning off automatic exit generation the switches
allow the map to be iterated over a number of times. This is important for
something like custom exit building. Exits require a reference to both the
exits location and the exits destination. During the first iteration it is
possible that an exit is created pointing towards a destination that
has not yet been created resulting in error. By iterating over the map twice
the rooms can be created on the first iteration and room reliant code can be
be used on the second iteration. The iteration number and a dictionary of
references to rooms previously created is passed to the build commands.

Use by importing and including the command in your default_cmdsets module.
For example:

    # mygame/commands/default_cmdsets.py

    from evennia.contrib import mapbuilder

    ...

    self.add(mapbuilder.CmdMapBuilder())

You then call the command in-game using the path to the MAP and MAP_LEGEND vars
The path you provide is relative to the evennia or mygame folder.

Usage:
    @mapbuilder[/switch] <path.to.file.MAPNAME> <path.to.file.MAP_LEGEND>

Switches:
  one - execute build instructions once without automatic exit creation.
  two - execute build instructions twice without automatic exit creation.

Example:
    @mapbuilder world.gamemap.MAP world.maplegend.MAP_LEGEND
    @mapbuilder evennia.contrib.mapbuilder.EXAMPLE1_MAP EXAMPLE1_LEGEND
    @mapbuilder/two evennia.contrib.mapbuilder.EXAMPLE2_MAP EXAMPLE2_LEGEND
            (Legend path defaults to map path)

Below are two examples showcasing the use of automatic exit generation and
custom exit generation. Whilst located, and can be used, from this module for
convenience The below example code should be in mymap.py in mygame/world.

"""

from django.conf import settings
from evennia.utils import utils

# ---------- EXAMPLE 1 ---------- #
# @mapbuilder evennia.contrib.mapbuilder.EXAMPLE1_MAP EXAMPLE1_LEGEND

# -*- coding: utf-8 -*-

# Add the necessary imports for your instructions here.
from evennia import create_object
from typeclasses import rooms, exits
from random import randint
import random


# A map with a temple (▲) amongst mountains (n,∩) in a forest (♣,♠) on an
# island surrounded by water (≈). By giving no instructions for the water
# characters we effectively skip it and create no rooms for those squares.
EXAMPLE1_MAP = """\
≈≈≈≈≈
≈♣n♣≈
≈∩▲∩≈
≈♠n♠≈
≈≈≈≈≈
"""


def example1_build_forest(x, y, **kwargs):
    """A basic example of build instructions. Make sure to include **kwargs
    in the arguments and return an instance of the room for exit generation."""

    # Create a room and provide a basic description.
    room = create_object(rooms.Room, key="forest" + str(x) + str(y))
    room.db.desc = "Basic forest room."

    # Send a message to the account
    kwargs["caller"].msg(room.key + " " + room.dbref)

    # This is generally mandatory.
    return room


def example1_build_mountains(x, y, **kwargs):
    """A room that is a little more advanced"""

    # Create the room.
    room = create_object(rooms.Room, key="mountains" + str(x) + str(y))

    # Generate a description by randomly selecting an entry from a list.
    room_desc = [
        "Mountains as far as the eye can see",
        "Your path is surrounded by sheer cliffs",
        "Haven't you seen that rock before?",
    ]
    room.db.desc = random.choice(room_desc)

    # Create a random number of objects to populate the room.
    for i in range(randint(0, 3)):
        rock = create_object(key="Rock", location=room)
        rock.db.desc = "An ordinary rock."

    # Send a message to the account
    kwargs["caller"].msg(room.key + " " + room.dbref)

    # This is generally mandatory.
    return room


def example1_build_temple(x, y, **kwargs):
    """A unique room that does not need to be as general"""

    # Create the room.
    room = create_object(rooms.Room, key="temple" + str(x) + str(y))

    # Set the description.
    room.db.desc = (
        "In what, from the outside, appeared to be a grand and "
        "ancient temple you've somehow found yourself in the the "
        "Evennia Inn! It consists of one large room filled with "
        "tables. The bardisk extends along the east wall, where "
        "multiple barrels and bottles line the shelves. The "
        "barkeep seems busy handing out ale and chatting with "
        "the patrons, which are a rowdy and cheerful lot, "
        "keeping the sound level only just below thunderous. "
        "This is a rare spot of mirth on this dread moor."
    )

    # Send a message to the account
    kwargs["caller"].msg(room.key + " " + room.dbref)

    # This is generally mandatory.
    return room


# Include your trigger characters and build functions in a legend dict.
EXAMPLE1_LEGEND = {
    ("♣", "♠"): example1_build_forest,
    ("∩", "n"): example1_build_mountains,
    ("▲"): example1_build_temple,
}

# ---------- EXAMPLE 2 ---------- #
# @mapbuilder/two evennia.contrib.mapbuilder.EXAMPLE2_MAP EXAMPLE2_LEGEND

# -*- coding: utf-8 -*-

# Add the necessary imports for your instructions here.
# from evennia import create_object
# from typeclasses import rooms, exits
# from evennia.utils import utils
# from random import randint
# import random

# This is the same layout as Example 1 but included are characters for exits.
# We can use these characters to determine which rooms should be connected.
EXAMPLE2_MAP = """\
≈ ≈ ≈ ≈ ≈

≈ ♣-♣-♣ ≈
  |   |
≈ ♣ ♣ ♣ ≈
  | | |
≈ ♣-♣-♣ ≈

≈ ≈ ≈ ≈ ≈
"""


def example2_build_forest(x, y, **kwargs):
    """A basic room"""
    # If on anything other than the first iteration - Do nothing.
    if kwargs["iteration"] > 0:
        return None

    room = create_object(rooms.Room, key="forest" + str(x) + str(y))
    room.db.desc = "Basic forest room."

    kwargs["caller"].msg(room.key + " " + room.dbref)

    return room


def example2_build_verticle_exit(x, y, **kwargs):
    """Creates two exits to and from the two rooms north and south."""
    # If on the first iteration - Do nothing.
    if kwargs["iteration"] == 0:
        return

    north_room = kwargs["room_dict"][(x, y - 1)]
    south_room = kwargs["room_dict"][(x, y + 1)]

    # create exits in the rooms
    create_object(
        exits.Exit, key="south", aliases=["s"], location=north_room, destination=south_room
    )

    create_object(
        exits.Exit, key="north", aliases=["n"], location=south_room, destination=north_room
    )

    kwargs["caller"].msg("Connected: " + north_room.key + " & " + south_room.key)


def example2_build_horizontal_exit(x, y, **kwargs):
    """Creates two exits to and from the two rooms east and west."""
    # If on the first iteration - Do nothing.
    if kwargs["iteration"] == 0:
        return

    west_room = kwargs["room_dict"][(x - 1, y)]
    east_room = kwargs["room_dict"][(x + 1, y)]

    create_object(exits.Exit, key="east", aliases=["e"], location=west_room, destination=east_room)

    create_object(exits.Exit, key="west", aliases=["w"], location=east_room, destination=west_room)

    kwargs["caller"].msg("Connected: " + west_room.key + " & " + east_room.key)


# Include your trigger characters and build functions in a legend dict.
EXAMPLE2_LEGEND = {
    ("♣", "♠"): example2_build_forest,
    ("|"): example2_build_verticle_exit,
    ("-"): example2_build_horizontal_exit,
}

# ---------- END OF EXAMPLES ---------- #

COMMAND_DEFAULT_CLASS = utils.class_from_module(settings.COMMAND_DEFAULT_CLASS)


# Helper function for readability.
def _map_to_list(game_map):
    """
    Splits multi line map string into list of rows.

    Args:
        game_map (str): An ASCII map

    Returns:
        list (list): The map split into rows

    """
    return game_map.split("\n")


def build_map(caller, game_map, legend, iterations=1, build_exits=True):
    """
    Receives the fetched map and legend vars provided by the player.

    Args:
        caller (Object): The creator of the map.
        game_map (str): An ASCII map string.
        legend (dict): Mapping of map symbols to object types.
        iterations (int): The number of iteration passes.
        build_exits (bool): Create exits between new rooms.

    Notes:
        The map
        is iterated over character by character, comparing it to the trigger
        characters in the legend var and executing the build instructions on
        finding a match. The map is iterated over according to the `iterations`
        value and exits are optionally generated between adjacent rooms according
        to the `build_exits` value.

    """

    # Split map string to list of rows and create reference list.
    caller.msg("Creating Map...")
    caller.msg(game_map)
    game_map = _map_to_list(game_map)

    # Create a reference dictionary which be passed to build functions and
    # will store obj returned by build functions so objs can be referenced.
    room_dict = {}

    caller.msg("Creating Landmass...")
    for iteration in range(iterations):
        for y in range(len(game_map)):
            for x in range(len(game_map[y])):
                for key in legend:
                    # obs - we must use == for strings
                    if game_map[y][x] == key:
                        room = legend[key](
                            x, y, iteration=iteration, room_dict=room_dict, caller=caller
                        )
                        if iteration == 0:
                            room_dict[(x, y)] = room

    if build_exits:
        # Creating exits. Assumes single room object in dict entry
        caller.msg("Connecting Areas...")
        for loc_key, location in room_dict.items():
            x = loc_key[0]
            y = loc_key[1]

            # north
            if (x, y - 1) in room_dict:
                if room_dict[(x, y - 1)]:
                    create_object(
                        exits.Exit,
                        key="north",
                        aliases=["n"],
                        location=location,
                        destination=room_dict[(x, y - 1)],
                    )

            # east
            if (x + 1, y) in room_dict:
                if room_dict[(x + 1, y)]:
                    create_object(
                        exits.Exit,
                        key="east",
                        aliases=["e"],
                        location=location,
                        destination=room_dict[(x + 1, y)],
                    )

            # south
            if (x, y + 1) in room_dict:
                if room_dict[(x, y + 1)]:
                    create_object(
                        exits.Exit,
                        key="south",
                        aliases=["s"],
                        location=location,
                        destination=room_dict[(x, y + 1)],
                    )

            # west
            if (x - 1, y) in room_dict:
                if room_dict[(x - 1, y)]:
                    create_object(
                        exits.Exit,
                        key="west",
                        aliases=["w"],
                        location=location,
                        destination=room_dict[(x - 1, y)],
                    )

    caller.msg("Map Created.")


# access command


class CmdMapBuilder(COMMAND_DEFAULT_CLASS):
    """
    Build a map from a 2D ASCII map.

    Usage:
        @mapbuilder[/switch] <path.to.file.MAPNAME> <path.to.file.MAP_LEGEND>

    Switches:
      one - execute build instructions once without automatic exit creation
      two - execute build instructions twice without automatic exit creation

    Example:
        @mapbuilder world.gamemap.MAP world.maplegend.MAP_LEGEND
        @mapbuilder evennia.contrib.mapbuilder.EXAMPLE1_MAP EXAMPLE1_LEGEND
        @mapbuilder/two evennia.contrib.mapbuilder.EXAMPLE2_MAP EXAMPLE2_LEGEND
                (Legend path defaults to map path)

    This is a command which takes two inputs:
    A string of ASCII characters representing a map and a dictionary of
    functions containing build instructions. The characters of the map are
    iterated over and compared to a list of trigger characters. When a match
    is found the corresponding function is executed generating the rooms,
    exits and objects as defined by the users build instructions. If a
    character is not a match to a provided trigger character (including spaces)
    it is simply skipped and the process continues. By default exits are
    automatically generated but is turned off by switches which also determines
    how many times the map is iterated over.
    """

    key = "@mapbuilder"
    aliases = ["@buildmap"]
    locks = "cmd:superuser()"
    help_category = "Building"

    def func(self):
        """Starts the processor."""

        caller = self.caller
        args = self.args.split()

        # Check if arguments passed.
        if not self.args or (len(args) != 2):
            caller.msg("Usage: @mapbuilder <path.to.module.VARNAME> " "<path.to.module.MAP_LEGEND>")
            return

        # Set up base variables.
        game_map = None
        legend = None

        # OBTAIN MAP FROM MODULE

        # Breaks down path_to_map into [PATH, VARIABLE]
        path_to_map = args[0]
        path_to_map = path_to_map.rsplit(".", 1)

        try:
            # Retrieves map variable from module or raises error.
            game_map = utils.variable_from_module(path_to_map[0], path_to_map[1])
            if not game_map:
                raise ValueError(
                    "Command Aborted!\n"
                    "Path to map variable failed.\n"
                    "Usage: @mapbuilder <path.to.module."
                    "VARNAME> <path.to.module.MAP_LEGEND>"
                )

        except Exception as exc:
            # Or relays error message if fails.
            caller.msg(exc)
            return

        # OBTAIN MAP_LEGEND FROM MODULE

        # Breaks down path_to_legend into [PATH, VARIABLE]
        path_to_legend = args[1]
        path_to_legend = path_to_legend.rsplit(".", 1)

        # If no path given default to path_to_map's path
        if len(path_to_legend) == 1:
            path_to_legend.insert(0, path_to_map[0])

        try:
            # Retrieves legend variable from module or raises error if fails.
            legend = utils.variable_from_module(path_to_legend[0], path_to_legend[1])
            if not legend:
                raise ValueError(
                    "Command Aborted!\n"
                    "Path to legend variable failed.\n"
                    "Usage: @mapbuilder <path.to.module."
                    "VARNAME> <path.to.module.MAP_LEGEND>"
                )

        except Exception as exc:
            # Or relays error message if fails.
            caller.msg(exc)
            return

        # Set up build_map arguments from switches
        iterations = 1
        build_exits = True

        if "one" in self.switches:
            build_exits = False

        if "two" in self.switches:
            iterations = 2
            build_exits = False

        # Pass map and legend to the build function.
        build_map(caller, game_map, legend, iterations, build_exits)
