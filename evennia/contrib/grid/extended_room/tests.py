"""
Testing of ExtendedRoom contrib

"""

import datetime

from django.conf import settings
from mock import Mock, patch

from evennia.commands.default.tests import BaseEvenniaCommandTest
from evennia.objects.objects import DefaultRoom

from . import extended_room


class ForceUTCDatetime(datetime.datetime):

    """Force UTC datetime."""

    @classmethod
    def fromtimestamp(cls, timestamp):
        """Force fromtimestamp to run with naive datetimes."""
        return datetime.datetime.utcfromtimestamp(timestamp)


@patch("evennia.contrib.grid.extended_room.extended_room.datetime.datetime", ForceUTCDatetime)
# mock gametime to return April 9, 2064, at 21:06 (spring evening)
@patch("evennia.utils.gametime.gametime", new=Mock(return_value=2975000766))
class TestExtendedRoom(BaseEvenniaCommandTest):
    room_typeclass = extended_room.ExtendedRoom
    DETAIL_DESC = "A test detail."
    SPRING_DESC = "A spring description."
    OLD_DESC = "Old description."
    settings.TIME_ZONE = "UTC"

    def setUp(self):
        super().setUp()
        self.room1.ndb.last_timeslot = "afternoon"
        self.room1.ndb.last_season = "winter"
        self.room1.db.details = {"testdetail": self.DETAIL_DESC}
        self.room1.db.spring_desc = self.SPRING_DESC
        self.room1.db.desc = self.OLD_DESC

    def test_return_appearance(self):
        # get the appearance of a non-extended room for contrast purposes
        old_desc = DefaultRoom.return_appearance(self.room1, self.char1)
        # the new appearance should be the old one, but with the desc switched
        self.assertEqual(
            old_desc.replace(self.OLD_DESC, self.SPRING_DESC),
            self.room1.return_appearance(self.char1),
        )
        self.assertEqual("spring", self.room1.ndb.last_season)
        self.assertEqual("evening", self.room1.ndb.last_timeslot)

    def test_return_detail(self):
        self.assertEqual(self.DETAIL_DESC, self.room1.return_detail("testdetail"))

    def test_cmdextendedlook(self):
        rid = self.room1.id
        self.call(
            extended_room.CmdExtendedRoomLook(),
            "here",
            "Room(#{})\n{}".format(rid, self.SPRING_DESC),
        )
        self.call(extended_room.CmdExtendedRoomLook(), "testdetail", self.DETAIL_DESC)
        self.call(
            extended_room.CmdExtendedRoomLook(), "nonexistent", "Could not find 'nonexistent'."
        )

    def test_cmdsetdetail(self):
        self.call(extended_room.CmdExtendedRoomDetail(), "", "Details on Room")
        self.call(
            extended_room.CmdExtendedRoomDetail(),
            "thingie = newdetail with spaces",
            "Detail set 'thingie': 'newdetail with spaces'",
        )
        self.call(extended_room.CmdExtendedRoomDetail(), "thingie", "Detail 'thingie' on Room:\n")
        self.call(
            extended_room.CmdExtendedRoomDetail(),
            "/del thingie",
            "Detail thingie deleted, if it existed.",
            cmdstring="detail",
        )
        self.call(extended_room.CmdExtendedRoomDetail(), "thingie", "Detail 'thingie' not found.")

        # Test with aliases
        self.call(extended_room.CmdExtendedRoomDetail(), "", "Details on Room")
        self.call(
            extended_room.CmdExtendedRoomDetail(),
            "thingie;other;stuff = newdetail with spaces",
            "Detail set 'thingie;other;stuff': 'newdetail with spaces'",
        )
        self.call(extended_room.CmdExtendedRoomDetail(), "thingie", "Detail 'thingie' on Room:\n")
        self.call(extended_room.CmdExtendedRoomDetail(), "other", "Detail 'other' on Room:\n")
        self.call(extended_room.CmdExtendedRoomDetail(), "stuff", "Detail 'stuff' on Room:\n")
        self.call(
            extended_room.CmdExtendedRoomDetail(),
            "/del other;stuff",
            "Detail other;stuff deleted, if it existed.",
        )
        self.call(extended_room.CmdExtendedRoomDetail(), "other", "Detail 'other' not found.")
        self.call(extended_room.CmdExtendedRoomDetail(), "stuff", "Detail 'stuff' not found.")

    def test_cmdgametime(self):
        self.call(extended_room.CmdExtendedRoomGameTime(), "", "It's a spring day, in the evening.")
