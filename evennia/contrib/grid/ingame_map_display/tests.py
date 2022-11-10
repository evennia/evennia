"""
Tests of ingame_map_display.

"""


from typeclasses import exits, rooms

from evennia.commands.default.tests import BaseEvenniaCommandTest
from evennia.utils.create import create_object

from . import ingame_map_display


class TestIngameMap(BaseEvenniaCommandTest):
    """
    Test the ingame map display by building two rooms and checking their connections are found

    Expected output:
    [ ]--[ ]
    """

    def setUp(self):
        super().setUp()
        self.west_room = create_object(rooms.Room, key="Room 1")
        self.east_room = create_object(rooms.Room, key="Room 2")
        create_object(
            exits.Exit,
            key="east",
            aliases=["e"],
            location=self.west_room,
            destination=self.east_room,
        )
        create_object(
            exits.Exit,
            key="west",
            aliases=["w"],
            location=self.east_room,
            destination=self.west_room,
        )

    def test_west_room_map_room(self):
        self.char1.location = self.west_room
        map_here = ingame_map_display.Map(self.char1).show_map()
        self.assertEqual(map_here.strip(), "[|n|[x|co|n]|n--[|n ]|n")

    def test_east_room_map_room(self):
        self.char1.location = self.east_room
        map_here = ingame_map_display.Map(self.char1).show_map()
        self.assertEqual(map_here.strip(), "[|n ]|n--[|n|[x|co|n]|n")
