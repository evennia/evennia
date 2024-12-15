"""
Test of EvAdventure Rooms

"""

from evennia import DefaultExit, create_object
from evennia.utils.ansi import strip_ansi
from evennia.utils.test_resources import EvenniaTestCase

from ..characters import EvAdventureCharacter
from ..rooms import EvAdventureRoom


class EvAdventureRoomTest(EvenniaTestCase):
    def setUp(self):
        self.char = create_object(EvAdventureCharacter, key="TestChar")

    def test_map(self):
        center_room = create_object(EvAdventureRoom, key="room_center")
        n_room = create_object(EvAdventureRoom, key="room_n")
        create_object(DefaultExit, key="north", location=center_room, destination=n_room)
        ne_room = create_object(EvAdventureRoom, key="room_ne")
        create_object(DefaultExit, key="northeast", location=center_room, destination=ne_room)
        e_room = create_object(EvAdventureRoom, key="room_e")
        create_object(DefaultExit, key="east", location=center_room, destination=e_room)
        se_room = create_object(EvAdventureRoom, key="room_se")
        create_object(DefaultExit, key="southeast", location=center_room, destination=se_room)
        s_room = create_object(EvAdventureRoom, key="room_")
        create_object(DefaultExit, key="south", location=center_room, destination=s_room)
        sw_room = create_object(EvAdventureRoom, key="room_sw")
        create_object(DefaultExit, key="southwest", location=center_room, destination=sw_room)
        w_room = create_object(EvAdventureRoom, key="room_w")
        create_object(DefaultExit, key="west", location=center_room, destination=w_room)
        nw_room = create_object(EvAdventureRoom, key="room_nw")
        create_object(DefaultExit, key="northwest", location=center_room, destination=nw_room)

        desc = center_room.return_appearance(self.char)

        expected = r"""
  o o o
   \|/
  o-@-o
   /|\
  o o o
room_center
This is a room.
Exits: north, northeast, east, southeast, south, southwest, west, and northwest"""

        result = "\n".join(part.rstrip() for part in strip_ansi(desc).split("\n"))
        expected = "\n".join(part.rstrip() for part in expected.split("\n"))
        # print(result)
        # print(expected)

        self.assertEqual(result, expected)
