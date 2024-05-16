"""
Testing of ExtendedRoom contrib

"""

import datetime

from django.conf import settings
from mock import Mock, patch
from parameterized import parameterized

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaCommandTest, EvenniaTestCase

from . import extended_room


def _get_timestamp(season, time_of_day):
    """
    Utility to get a timestamp for a given season and time of day.

    """
    # grab a month / time given a season and time of day
    seasons = {"spring": 3, "summer": 6, "autumn": 9, "winter": 12}
    times_of_day = {"morning": 6, "afternoon": 12, "evening": 18, "night": 0}
    # return a datetime object for the 1st of the month at the given hour
    return datetime.datetime(2064, seasons[season], 1, times_of_day[time_of_day]).timestamp()


class TestExtendedRoom(EvenniaTestCase):
    """
    Test Extended Room typeclass.

    """

    base_room_desc = "Base room description."

    def setUp(self):
        super().setUp()
        self.room = create_object(extended_room.ExtendedRoom, key="Test Room")
        self.room.desc = self.base_room_desc

    def tearDown(self):
        super().tearDown()
        self.room.delete()

    def test_room_description(self):
        """
        Test that the vanilla room description is returned as expected.
        """
        room_desc = self.room.get_display_desc(None)
        self.assertEqual(room_desc, self.base_room_desc)

    @parameterized.expand(
        [
            ("spring", "Spring room description."),
            ("summer", "Summer room description."),
            ("autumn", "Autumn room description."),
            ("winter", "Winter room description."),
        ]
    )
    @patch("evennia.utils.gametime.gametime")
    def test_seasonal_room_descriptions(self, season, desc, mock_gametime):
        """
        Test that the room description changes with the season.
        """
        mock_gametime.return_value = _get_timestamp(season, "morning")
        self.room.add_desc(desc, room_state=season)

        room_desc = self.room.get_display_desc(None)
        self.assertEqual(room_desc, desc)

    @parameterized.expand(
        [
            ("morning", "Morning room description."),
            ("afternoon", "Afternoon room description."),
            ("evening", "Evening room description."),
            ("night", "Night room description."),
        ]
    )
    @patch("evennia.utils.gametime.gametime")
    def test_get_time_of_day_tags(self, time_of_day, desc, mock_gametime):
        """
        Test room with $
        """
        mock_gametime.return_value = _get_timestamp("spring", time_of_day)
        room_time_of_day = self.room.get_time_of_day()
        self.assertEqual(room_time_of_day, time_of_day)

        self.room.add_desc(
            "$state(morning, Morning room description.)"
            "$state(afternoon, Afternoon room description.)"
            "$state(evening, Evening room description.)"
            "$state(night, Night room description.)"
            " What a great day!"
        )
        char = Mock()
        room_desc = self.room.get_display_desc(char)
        self.assertEqual(room_desc, f"{desc} What a great day!")

    def test_room_states(self):
        """
        Test rooms with custom game states.

        """
        self.room.add_desc(
            "$state(under_construction, This room is under construction.)"
            " $state(under_repair, This room is under repair.)"
        )
        self.room.add_room_state("under_construction")
        self.assertEqual(self.room.room_states, ["under_construction"])
        char = Mock()
        self.assertEqual(self.room.get_display_desc(char), "This room is under construction. ")

        self.room.add_room_state("under_repair")
        self.assertEqual(set(self.room.room_states), set(["under_construction", "under_repair"]))
        self.assertEqual(
            self.room.get_display_desc(char),
            "This room is under construction. This room is under repair.",
        )

        self.room.remove_room_state("under_construction")
        self.assertEqual(
            self.room.get_display_desc(char),
            " This room is under repair.",
        )

    def test_alternative_descs(self):
        """
        Test rooms with alternate descriptions.

        """
        from evennia import ObjectDB

        ObjectDB.objects.all()  # TODO - fixes an issue with home FK missing

        self.room.add_desc("The room is burning!", room_state="burning")
        self.room.add_desc("The room is flooding!", room_state="flooding")
        self.assertEqual(self.room.get_display_desc(None), self.base_room_desc)

        self.room.add_room_state("burning")
        self.assertEqual(self.room.get_display_desc(None), "The room is burning!")

        self.room.add_room_state("flooding")
        self.room.remove_room_state("burning")
        self.assertEqual(self.room.get_display_desc(None), "The room is flooding!")

        self.room.clear_room_state()
        self.assertEqual(self.room.get_display_desc(None), self.base_room_desc)

    def test_details(self):
        """
        Test room details.

        """
        self.room.add_detail("test", "Test detail.")
        self.room.add_detail("test2", "Test detail 2.")
        self.room.add_detail("window", "Window detail.")
        self.room.add_detail("window pane", "Window Pane detail.")

        self.assertEqual(self.room.get_detail("test"), "Test detail.")
        self.assertEqual(self.room.get_detail("test2"), "Test detail 2.")
        self.assertEqual(self.room.get_detail("window"), "Window detail.")
        self.assertEqual(self.room.get_detail("window pane"), "Window Pane detail.")
        self.assertEqual(self.room.get_detail("win"), "Window detail.")
        self.assertEqual(self.room.get_detail("window p"), "Window Pane detail.")

        self.room.remove_detail("test")
        self.assertEqual(self.room.get_detail("test"), "Test detail 2.")  # finding nearest
        self.room.remove_detail("test2")
        self.assertEqual(self.room.get_detail("test"), None)  # all test* gone


class TestExtendedRoomCommands(BaseEvenniaCommandTest):
    """
    Test the ExtendedRoom commands.

    """

    base_room_desc = "Base room description."

    def setUp(self):
        super().setUp()
        self.room1.swap_typeclass("evennia.contrib.grid.extended_room.ExtendedRoom")
        self.room1.desc = self.base_room_desc

    @patch("evennia.utils.gametime.gametime")
    def test_cmd_desc(self, mock_gametime):
        """Test new desc command"""

        mock_gametime.return_value = _get_timestamp("autumn", "afternoon")

        # view base desc
        self.call(
            extended_room.CmdExtendedRoomDesc(),
            "",
            f"""
Room Room Season: autumn. Time: afternoon. States: None

Room state (default) (active):
Base room description.
                  """.strip(),
        )

        # add spring desc
        self.call(
            extended_room.CmdExtendedRoomDesc(),
            "/spring Spring description.",
            "The spring-description was set on Room",
        )
        self.call(
            extended_room.CmdExtendedRoomDesc(),
            "/burning Burning description.",
            "The burning-description was set on Room",
        )

        self.call(
            extended_room.CmdExtendedRoomDesc(),
            "",
            f"""
Room Room Season: autumn. Time: afternoon. States: None

Room state burning:
Burning description.

Room state spring:
Spring description.

Room state (default) (active):
Base room description.
                 """.strip(),
        )

        # remove a desc
        self.call(
            extended_room.CmdExtendedRoomDesc(),
            "/del/burning/spring",
            (
                "The burning-description was deleted, if it existed.|The spring-description was"
                " deleted, if it existed"
            ),
        )
        # add autumn, which should be active
        self.call(
            extended_room.CmdExtendedRoomDesc(),
            "/autumn Autumn description.",
            "The autumn-description was set on Room",
        )
        self.call(
            extended_room.CmdExtendedRoomDesc(),
            "",
            f"""
Room Room Season: autumn. Time: afternoon. States: None

Room state autumn (active):
Autumn description.

Room state (default):
Base room description.
                  """.strip(),
        )

    def test_cmd_detail(self):
        """Test adding details"""
        self.call(
            extended_room.CmdExtendedRoomDetail(),
            "test=Test detail.",
            "Set detail 'test': 'Test detail.'",
        )

        self.call(
            extended_room.CmdExtendedRoomDetail(),
            "",
            """
Details on Room:
test: Test detail.
            """.strip(),
        )

        # remove a detail
        self.call(
            extended_room.CmdExtendedRoomDetail(),
            "/del test",
            "Deleted detail 'test', if it existed.",
        )

        self.call(
            extended_room.CmdExtendedRoomDetail(),
            "",
            """
The room Room doesn't have any details.
            """.strip(),
        )

    @patch("evennia.utils.gametime.gametime")
    def test_cmd_roomstate(self, mock_gametime):
        """
        Test the roomstate command

        """

        mock_gametime.return_value = _get_timestamp("autumn", "afternoon")

        # show existing room states (season/time doesn't count)

        self.assertEqual(self.room1.room_states, [])

        self.call(
            extended_room.CmdExtendedRoomState(),
            "",
            "Room states (not counting automatic time/season) on Room:\n None",
        )

        # add room states
        self.call(
            extended_room.CmdExtendedRoomState(),
            "burning",
            "Added room state 'burning' to this room.",
        )
        self.call(
            extended_room.CmdExtendedRoomState(),
            "windy",
            "Added room state 'windy' to this room.",
        )
        self.call(
            extended_room.CmdExtendedRoomState(),
            "",
            f"Room states (not counting automatic time/season) on Room:\n 'burning' and 'windy'",
        )
        # toggle windy
        self.call(
            extended_room.CmdExtendedRoomState(),
            "windy",
            "Cleared room state 'windy' from this room.",
        )
        self.call(
            extended_room.CmdExtendedRoomState(),
            "",
            f"Room states (not counting automatic time/season) on Room:\n 'burning'",
        )
        # add a autumn state and make sure we override it
        self.room1.add_desc("Autumn description.", room_state="autumn")
        self.room1.add_desc("Spring description.", room_state="spring")

        self.assertEqual(self.room1.get_stateful_desc(), "Autumn description.")
        self.call(
            extended_room.CmdExtendedRoomState(),
            "spring",
            "Added room state 'spring' to this room.",
        )
        self.assertEqual(self.room1.get_stateful_desc(), "Spring description.")

    @patch("evennia.utils.gametime.gametime")
    def test_cmd_roomtime(self, mock_gametime):
        """
        Test the time command
        """

        mock_gametime.return_value = _get_timestamp("autumn", "afternoon")

        self.call(
            extended_room.CmdExtendedRoomGameTime(), "", "It's an autumn day, in the afternoon."
        )

    @patch("evennia.utils.gametime.gametime")
    def test_cmd_look(self, mock_gametime):
        """
        Test the look command.
        """
        mock_gametime.return_value = _get_timestamp("autumn", "afternoon")

        autumn_desc = (
            "This is a nice autumnal forest."
            "$state(morning,|_The morning sun is just rising)"
            "$state(afternoon,|_The afternoon sun is shining through the trees)"
            "$state(burning,|_and this place is on fire!)"
            "$state(afternoon, .)"
            "$state(flooded, and it's raining heavily!)"
        )
        self.room1.add_desc(autumn_desc, room_state="autumn")

        self.call(
            extended_room.CmdExtendedRoomLook(),
            "",
            f"Room(#{self.room1.id})\nThis is a nice autumnal forest.",
        )
        self.call(
            extended_room.CmdExtendedRoomLook(),
            "",
            (
                f"Room(#{self.room1.id})\nThis is a nice autumnal forest. The afternoon sun is"
                " shining through the trees."
            ),
        )
        self.room1.add_room_state("burning")
        self.call(
            extended_room.CmdExtendedRoomLook(),
            "",
            (
                f"Room(#{self.room1.id})\nThis is a nice autumnal forest. The afternoon sun is"
                " shining through the trees and this place is on fire!"
            ),
        )
