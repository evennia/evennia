"""
Test map builder.

"""

import random
from random import randint

from typeclasses import exits, rooms

# Add the necessary imports for your instructions here.
from evennia import create_object
from evennia.commands.default.tests import BaseEvenniaCommandTest

from . import mapbuilder

# -*- coding: utf-8 -*-


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

# Example two

# @mapbuilder/two evennia.contrib.grid.mapbuilder.EXAMPLE2_MAP EXAMPLE2_LEGEND

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


class TestMapBuilder(BaseEvenniaCommandTest):
    def test_cmdmapbuilder(self):
        self.call(
            mapbuilder.CmdMapBuilder(),
            "evennia.contrib.grid.mapbuilder.tests.EXAMPLE1_MAP "
            "evennia.contrib.grid.mapbuilder.tests.EXAMPLE1_LEGEND",
            """Creating Map...|≈≈≈≈≈
≈♣n♣≈
≈∩▲∩≈
≈♠n♠≈
≈≈≈≈≈
|Creating Landmass...|""",
        )
        self.call(
            mapbuilder.CmdMapBuilder(),
            "evennia.contrib.grid.mapbuilder.tests.EXAMPLE2_MAP "
            "evennia.contrib.grid.mapbuilder.tests.EXAMPLE2_LEGEND",
            """Creating Map...|≈ ≈ ≈ ≈ ≈

≈ ♣-♣-♣ ≈
    ≈ ♣ ♣ ♣ ≈
  ≈ ♣-♣-♣ ≈

≈ ≈ ≈ ≈ ≈
|Creating Landmass...|""",
        )
