"""
Test Dungeon orchestrator / procedurally generated dungeon rooms.

"""

from unittest.mock import MagicMock

from evennia.utils.create import create_object
from evennia.utils.test_resources import BaseEvenniaTest
from evennia.utils.utils import inherits_from

from .. import dungeon
from .mixins import EvAdventureMixin


class TestDungeon(EvAdventureMixin, BaseEvenniaTest):
    """
    Test with a starting room and a character moving through the dungeon,
    generating more and more rooms as they go.

    """

    def setUp(self):
        """
        Create a start room with exits leading away from it

        """
        super().setUp()
        droomclass = dungeon.EvAdventureDungeonStartRoom
        droomclass.recycle_time = 0  # disable the tick
        droomclass.branch_check_time = 0

        self.start_room = create_object(droomclass, key="bottom of well")

        self.assertEqual(
            self.start_room.scripts.get("evadventure_dungeon_startroom_resetter")[0].interval, -1
        )
        self.start_north = create_object(
            dungeon.EvAdventureDungeonStartRoomExit,
            key="north",
            location=self.start_room,
            destination=self.start_room,
        )
        self.start_north
        self.start_south = create_object(
            dungeon.EvAdventureDungeonStartRoomExit,
            key="south",
            location=self.start_room,
            destination=self.start_room,
        )
        self.character.location = self.start_room

    def _move_character(self, direction):
        old_location = self.character.location
        for exi in old_location.exits:
            if exi.key == direction:
                # by setting target to old-location we trigger the
                # special behavior of this Exit type
                exi.at_traverse(self.character, exi.destination)
                break
        return self.character.location

    def test_start_room(self):
        """
        Test move through one of the start room exits.

        """
        # begin in start room
        self.assertEqual(self.character.location, self.start_room)

        # first go north, this should generate a new room
        new_room_north = self._move_character("north")
        self.assertNotEqual(self.start_room, new_room_north)
        self.assertTrue(inherits_from(new_room_north, dungeon.EvAdventureDungeonRoom))

        # check if Orchestrator was created
        orchestrator = new_room_north.db.dungeon_orchestrator
        self.assertTrue(bool(orchestrator))
        self.assertTrue(orchestrator.key.startswith("dungeon_orchestrator_north_"))

    def test_different_start_directions(self):
        # first go north, this should generate a new room
        new_room_north = self._move_character("north")
        self.assertNotEqual(self.start_room, new_room_north)

        # back to start room
        start_room = self._move_character("south")
        self.assertEqual(self.start_room, start_room)

        # next go south, this should generate a new room
        new_room_south = self._move_character("south")
        self.assertNotEqual(self.start_room, new_room_south)
        self.assertNotEqual(new_room_north, new_room_south)

        # back to start room again
        start_room = self._move_character("north")
        self.assertEqual(self.start_room, start_room)
