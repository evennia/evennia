from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from mock import patch
from parameterized import parameterized

from evennia import create_script, GLOBAL_SCRIPTS
from evennia.utils.test_resources import BaseEvenniaTest, BaseEvenniaCommandTest  # noqa
from . import events_calendar
from .commands import CmdEvents

_test_time = datetime(2020, 6, 7, 8, tzinfo=ZoneInfo("UTC"))


@patch.object(events, "datetime", wraps=datetime)
# @patch.object(events_calendar.time, "time", test_time)
class TestEventCalendar(BaseEvenniaTest):
    # TODO: redo this to mock the current time
    def setUp(self):
        super().setUp()
        now = _test_time
        start = now + timedelta(days=-1)
        end = now + timedelta(days=1)
        self.calendar = create_script(events_calendar.EventCalendar, key="event_calendar_script")
        self.event1 = events_calendar.Event(
            "test event", "This is an event running now.", start, end, creator=self.char1
        )
        start = now + timedelta(weeks=1)
        end = now + timedelta(weeks=1, days=2)
        self.event2 = events_calendar.Event("test event 2", "This is a future event.", start, end)
        start = now + timedelta(weeks=-1)
        end = now + timedelta(weeks=-1, days=2)
        self.event3 = events_calendar.Event("test event 3", "This is a past event.", start, end)

    def tearDown(self):
        super().tearDown()
        self.calendar.delete()

    def test_add_event(self, mock_datetime):
        mock_datetime.now.return_value = _test_time
        self.assertTrue(self.calendar.add_event(self.event1))
        self.assertEqual(len(self.calendar.list_events(as_data=True)), 1)
        # cannot add an event twice
        self.assertFalse(self.calendar.add_event(self.event1))
        self.assertEqual(len(self.calendar.list_events(as_data=True)), 1)

    def test_list_events(self, mock_datetime):
        mock_datetime.now.return_value = _test_time
        self.calendar.add_event(self.event2)
        self.assertEqual(len(self.calendar.list_events(as_data=True)), 1)
        self.assertEqual(self.event2, self.calendar.list_events(as_data=True)[0])
        self.assertTrue(self.calendar.list_events().startswith("|ctest event 2|n"))
        self.calendar.add_event(self.event1)
        self.assertEqual(len(self.calendar.list_events(as_data=True)), 2)
        # newly added event should be first, since it's sooner
        self.assertEqual(self.event1, self.calendar.list_events(as_data=True)[0])
        self.assertEqual(self.event2, self.calendar.list_events(as_data=True)[1])

    def test_current_list(self, mock_datetime):
        mock_datetime.now.return_value = _test_time
        self.calendar.add_event(self.event1)
        self.calendar.add_event(self.event2)
        # event 1 is currently active so should be in this list
        self.assertIn(self.event1, self.calendar.current_events(as_data=True))
        # event 2 is in the future so should NOT be in this list
        self.assertNotIn(self.event2, self.calendar.current_events(as_data=True))

    def test_future_list(self, mock_datetime):
        mock_datetime.now.return_value = _test_time
        self.calendar.add_event(self.event1)
        self.calendar.add_event(self.event2)
        # event 1 is currently active so should NOT be in this list
        self.assertNotIn(self.event1, self.calendar.future_events(as_data=True))
        # event 2 is in the future so should be in this list
        self.assertIn(self.event2, self.calendar.future_events(as_data=True))

    def test_clean_up(self, mock_datetime):
        mock_datetime.now.return_value = _test_time
        self.calendar.add_event(self.event1)
        self.calendar.add_event(self.event3)
        self.assertIn(self.event3, self.calendar.list_events(as_data=True))
        self.calendar.clean_up()
        # event 3 is in the past and so should have been removed
        self.assertNotIn(self.event3, self.calendar.list_events(as_data=True))

    def test_delete_event(self, mock_datetime):
        mock_datetime.now.return_value = _test_time
        self.calendar.add_event(self.event1)
        self.calendar.add_event(self.event2)
        self.assertIn(self.event2, self.calendar.list_events(as_data=True))
        self.calendar.delete_event(self.event2)
        self.assertNotIn(self.event2, self.calendar.list_events(as_data=True))


@patch.object(events, "datetime", wraps=datetime)
class TestEventCommand(BaseEvenniaCommandTest):
    def setUp(self):
        super().setUp()
        now = _test_time
        start = now + timedelta(days=-1)
        end = now + timedelta(days=1)
        self.calendar = create_script(events_calendar.EventCalendar, key="event_calendar_script")
        self.calendar.add_event(
            events_calendar.Event(
                "test event", "This is an event running now.", start, end, creator=self.char1
            )
        )
        start = now + timedelta(weeks=1)
        end = now + timedelta(weeks=1, days=2)
        self.calendar.add_event(
            events_calendar.Event(
                "test event 2", "This is a future event.", start, end, creator=self.char2
            )
        )
        self.calendar.add_event(
            events_calendar.Event(
                "staff event test", "This is an admin-level event.", start, end, view_perm="admin"
            )
        )
        start = now + timedelta(weeks=-1)
        end = now + timedelta(weeks=-1, days=2)
        self.calendar.add_event(
            events_calendar.Event("test event 3", "This is a past event.", start, end)
        )

    def tearDown(self):
        super().tearDown()
        self.calendar.delete()

    def test_event_list(self, mock_datetime):
        mock_datetime.now.return_value = _test_time
        header = "Events|"
        event_1 = """\
test event (by Char)
Starts: 06 Jun 2020, 08:00 UTC (happening now!)
Ends:   08 Jun 2020, 08:00 UTC
This is an event running now.
"""

        event_2 = """\
test event 2 (by Char2)
Starts: 14 Jun 2020, 08:00 UTC
Ends:   16 Jun 2020, 08:00 UTC
This is a future event.
"""

        short_list = """\
test event (by Char), starts 06 Jun 2020, 08:00 UTC (happening now!)
test event 2 (by Char2), starts 14 Jun 2020, 08:00 UTC
staff event test, starts 14 Jun 2020, 08:00 UTC
"""

        self.call(CmdEvents(), "", header + short_list)
        self.call(
            CmdEvents(), "/current", header + "test event (by Char), starts 06 Jun 2020, 08:00 UTC"
        )
        self.call(
            CmdEvents(),
            "/future",
            header + "test event 2 (by Char2), starts 14 Jun 2020, 08:00 UTC",
        )

        self.call(CmdEvents(), "/view event 2", event_2)
        self.call(CmdEvents(), "/view/current", header + event_1)
        self.call(CmdEvents(), "/view/future", header + event_2)

    def test_event_perms(self, mock_datetime):
        mock_datetime.now.return_value = _test_time
        # default caller, char1, has developer perms
        event_list = self.call(CmdEvents(), "", "Events")
        self.assertIn("staff event test", event_list)
        # char2 does not, and should not see the staff event
        event_list = self.call(CmdEvents(), "", "Events", caller=self.char2)
        self.assertNotIn("staff event test", event_list)

    def test_view_mine(self, mock_datetime):
        mock_datetime.now.return_value = _test_time
        # event 1 was by Char
        self.call(
            CmdEvents(),
            "/mine",
            "My Events|test event (by Char), starts 06 Jun 2020, 08:00 UTC",
            caller=self.char1,
        )
        # event 2 was by Char2
        self.call(
            CmdEvents(),
            "/mine",
            "My Events|test event 2 (by Char2), starts 14 Jun 2020, 08:00 UTC",
            caller=self.char2,
        )
