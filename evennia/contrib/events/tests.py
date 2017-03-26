"""
Module containing the test cases for the event system.
"""

from mock import Mock
from textwrap import dedent

from django.conf import settings
from evennia import ScriptDB
from evennia.commands.default.tests import CommandTest
from evennia.objects.objects import ExitCommand
from evennia.utils import ansi, utils
from evennia.utils.create import create_object, create_script
from evennia.utils.test_resources import EvenniaTest
from evennia.contrib.events.commands import CmdEvent

# Force settings
settings.EVENTS_CALENDAR = "standard"

class TestEventHandler(EvenniaTest):

    """
    Test cases of the event handler to add, edit or delete events.
    """

    def setUp(self):
        """Create the event handler."""
        super(TestEventHandler, self).setUp()
        self.handler = create_script(
                "evennia.contrib.events.scripts.EventHandler")

    def tearDown(self):
        """Stop the event handler."""
        self.handler.stop()
        super(TestEventHandler, self).tearDown()

    def test_start(self):
        """Simply make sure the handler runs with proper initial values."""
        self.assertEqual(self.handler.db.events, {})
        self.assertEqual(self.handler.db.to_valid, [])
        self.assertEqual(self.handler.db.locked, [])
        self.assertEqual(self.handler.db.tasks, {})
        self.assertEqual(self.handler.db.task_id, 0)
        self.assertIsNotNone(self.handler.ndb.event_types)

    def test_add(self):
        """Add a single event on room1."""
        author = self.char1
        self.handler.add_event(self.room1, "dummy",
                "character.db.strength = 50", author=author, valid=True)
        event = self.handler.get_events(self.room1).get("dummy")
        event = event[0]
        self.assertIsNotNone(event)
        self.assertEqual(event["obj"], self.room1)
        self.assertEqual(event["name"], "dummy")
        self.assertEqual(event["number"], 0)
        self.assertEqual(event["author"], author)
        self.assertEqual(event["valid"], True)

        # Since this event is valid, it shouldn't appear in 'to_valid'
        self.assertNotIn((self.room1, "dummy", 0), self.handler.db.to_valid)

        # Run this dummy event
        self.char1.db.strength = 10
        locals = {"character": self.char1}
        self.assertTrue(self.handler.call_event(
                self.room1, "dummy", locals=locals))
        self.assertEqual(self.char1.db.strength, 50)

    def test_add_validation(self):
        """Add an event while needing validation."""
        author = self.char1
        self.handler.add_event(self.room1, "dummy",
                "character.db.strength = 40", author=author, valid=False)
        event = self.handler.get_events(self.room1).get("dummy")
        event = event[0]
        self.assertIsNotNone(event)
        self.assertEqual(event["author"], author)
        self.assertEqual(event["valid"], False)

        # Since this event is not valid, it should appear in 'to_valid'
        self.assertIn((self.room1, "dummy", 0), self.handler.db.to_valid)

        # Run this dummy event (shouldn't do anything)
        self.char1.db.strength = 10
        locals = {"character": self.char1}
        self.assertTrue(self.handler.call_event(
                self.room1, "dummy", locals=locals))
        self.assertEqual(self.char1.db.strength, 10)

    def test_edit(self):
        """Test editing an event."""
        author = self.char1
        self.handler.add_event(self.room1, "dummy",
                "character.db.strength = 60", author=author, valid=True)

        # Edit it right away
        self.handler.edit_event(self.room1, "dummy", 0,
                "character.db.strength = 65", author=self.char2, valid=True)

        # Check that the event was written
        event = self.handler.get_events(self.room1).get("dummy")
        event = event[0]
        self.assertIsNotNone(event)
        self.assertEqual(event["author"], author)
        self.assertEqual(event["valid"], True)
        self.assertEqual(event["updated_by"], self.char2)

        # Run this dummy event
        self.char1.db.strength = 10
        locals = {"character": self.char1}
        self.assertTrue(self.handler.call_event(
                self.room1, "dummy", locals=locals))
        self.assertEqual(self.char1.db.strength, 65)

    def test_edit_validation(self):
        """Edit an event when validation isn't automatic."""
        author = self.char1
        self.handler.add_event(self.room1, "dummy",
                "character.db.strength = 70", author=author, valid=True)

        # Edit it right away
        self.handler.edit_event(self.room1, "dummy", 0,
                "character.db.strength = 80", author=self.char2, valid=False)

        # Run this dummy event (shouldn't do anything)
        self.char1.db.strength = 10
        locals = {"character": self.char1}
        self.assertTrue(self.handler.call_event(
                    self.room1, "dummy", locals=locals))
        self.assertEqual(self.char1.db.strength, 10)

    def test_del(self):
        """Try to delete an event."""
        # Add 3 events
        self.handler.add_event(self.room1, "dummy",
                "character.db.strength = 5", author=self.char1, valid=True)
        self.handler.add_event(self.room1, "dummy",
                "character.db.strength = 8", author=self.char2, valid=False)
        self.handler.add_event(self.room1, "dummy",
                "character.db.strength = 9", author=self.char1, valid=True)

        # Note that the second event isn't valid
        self.assertIn((self.room1, "dummy", 1), self.handler.db.to_valid)

        # Lock the third event
        self.handler.db.locked.append((self.room1, "dummy", 2))

        # Delete the first event
        self.handler.del_event(self.room1, "dummy", 0)

        # The event #1 that was to valid should be #0 now
        self.assertIn((self.room1, "dummy", 0), self.handler.db.to_valid)
        self.assertNotIn((self.room1, "dummy", 1), self.handler.db.to_valid)

        # The lock has been updated too
        self.assertIn((self.room1, "dummy", 1), self.handler.db.locked)
        self.assertNotIn((self.room1, "dummy", 2), self.handler.db.locked)

        # Now delete the first (not valid) event
        self.handler.del_event(self.room1, "dummy", 0)
        self.assertEqual(self.handler.db.to_valid, [])
        self.assertIn((self.room1, "dummy", 0), self.handler.db.locked)
        self.assertNotIn((self.room1, "dummy", 1), self.handler.db.locked)

        # Call the remaining event
        self.char1.db.strength = 10
        locals = {"character": self.char1}
        self.assertTrue(self.handler.call_event(
                    self.room1, "dummy", locals=locals))
        self.assertEqual(self.char1.db.strength, 9)

    def test_accept(self):
        """Accept an event."""
        # Add 2 events
        self.handler.add_event(self.room1, "dummy",
                "character.db.strength = 5", author=self.char1, valid=True)
        self.handler.add_event(self.room1, "dummy",
                "character.db.strength = 8", author=self.char2, valid=False)

        # Note that the second event isn't valid
        self.assertIn((self.room1, "dummy", 1), self.handler.db.to_valid)

        # Accept the second event
        self.handler.accept_event(self.room1, "dummy", 1)
        event = self.handler.get_events(self.room1).get("dummy")
        event = event[1]
        self.assertIsNotNone(event)
        self.assertEqual(event["valid"], True)

        # Call the dummy event
        self.char1.db.strength = 10
        locals = {"character": self.char1}
        self.assertTrue(self.handler.call_event(
                    self.room1, "dummy", locals=locals))
        self.assertEqual(self.char1.db.strength, 8)

    def test_call(self):
        """Test to call amore complex event."""
        self.char1.key = "one"
        self.char2.key = "two"

        # Add an event
        code = dedent("""
            if character.key == "one":
                character.db.health = 50
            else:
                character.db.health = 0
        """.strip("\n"))
        self.handler.add_event(self.room1, "dummy", code,
                author=self.char1, valid=True)

        # Call the dummy event
        self.assertTrue(self.handler.call_event(
                    self.room1, "dummy", locals={"character": self.char1}))
        self.assertEqual(self.char1.db.health, 50)
        self.assertTrue(self.handler.call_event(
                    self.room1, "dummy", locals={"character": self.char2}))
        self.assertEqual(self.char2.db.health, 0)

    def test_handler(self):
        """Test the object handler."""
        self.assertIsNotNone(self.char1.events)

        # Add an event
        event = self.room1.events.add("say", "pass", author=self.char1,
                valid=True)
        self.assertEqual(event.obj, self.room1)
        self.assertEqual(event.name, "say")
        self.assertEqual(event.code, "pass")
        self.assertEqual(event.author, self.char1)
        self.assertEqual(event.valid, True)
        self.assertIn([event], self.room1.events.all().values())

        # Edit this very event
        new = self.room1.events.edit("say", 0, "character.db.say = True",
                author=self.char1, valid=True)
        self.assertIn([new], self.room1.events.all().values())
        self.assertNotIn([event], self.room1.events.all().values())

        # Try to call this event
        self.assertTrue(self.room1.events.call("say",
                locals={"character": self.char2}))
        self.assertTrue(self.char2.db.say)

        # Delete the event
        self.room1.events.remove("say", 0)
        self.assertEqual(self.room1.events.all(), {})


class TestCmdEvent(CommandTest):

    """Test the @event command."""

    def setUp(self):
        """Create the event handler."""
        super(TestCmdEvent, self).setUp()
        self.handler = create_script(
                "evennia.contrib.events.scripts.EventHandler")

    def tearDown(self):
        """Stop the event handler."""
        self.handler.stop()
        for script in ScriptDB.objects.filter(
                db_typeclass_path="evennia.contrib.events.scripts.TimeEventScript"):
            script.stop()

        super(TestCmdEvent, self).tearDown()

    def test_list(self):
        """Test listing events with different rights."""
        table = self.call(CmdEvent(), "out")
        lines = table.splitlines()[3:-1]
        self.assertNotEqual(lines, [])

        # Check that the second column only contains 0 (0) (no event yet)
        for line in lines:
            cols = line.split("|")
            self.assertIn(cols[2].strip(), ("0 (0)", ""))

        # Add some event
        self.handler.add_event(self.exit, "traverse", "pass",
                author=self.char1, valid=True)

        # Try to obtain more details on a specific event on exit
        table = self.call(CmdEvent(), "out = traverse")
        lines = table.splitlines()[3:-1]
        self.assertEqual(len(lines), 1)
        line = lines[0]
        cols = line.split("|")
        self.assertIn(cols[1].strip(), ("1", ""))
        self.assertIn(cols[2].strip(), (str(self.char1), ""))
        self.assertIn(cols[-1].strip(), ("Yes", "No", ""))

        # Run the same command with char2
        # char2 shouldn't see the last column (Valid)
        table = self.call(CmdEvent(), "out = traverse", caller=self.char2)
        lines = table.splitlines()[3:-1]
        self.assertEqual(len(lines), 1)
        line = lines[0]
        cols = line.split("|")
        self.assertEqual(cols[1].strip(), "1")
        self.assertNotIn(cols[-1].strip(), ("Yes", "No"))

        # In any case, display the event
        # The last line should be "pass" (the event code)
        details = self.call(CmdEvent(), "out = traverse 1")
        self.assertEqual(details.splitlines()[-1], "pass")

    def test_add(self):
        """Test to add an event."""
        self.call(CmdEvent(), "/add out = traverse")
        editor = self.char1.ndb._eveditor
        self.assertIsNotNone(editor)

        # Edit the event
        editor.update_buffer(dedent("""
            if character.key == "one":
                character.msg("You can pass.")
            else:
                character.msg("You can't pass.")
                deny()
        """.strip("\n")))
        editor.save_buffer()
        editor.quit()
        event = self.exit.events.get("traverse")[0]
        self.assertEqual(event.author, self.char1)
        self.assertEqual(event.valid, True)
        self.assertTrue(len(event.code) > 0)

        # We're going to try the same thing but with char2
        # char2 being a player for our test, the event won't be validated.
        er = self.call(CmdEvent(), "/add out = traverse", caller=self.char2)
        editor = self.char2.ndb._eveditor
        self.assertIsNotNone(editor)

        # Edit the event
        editor.update_buffer(dedent("""
            character.msg("No way.")
        """.strip("\n")))
        editor.save_buffer()
        editor.quit()
        event = self.exit.events.get("traverse")[1]
        self.assertEqual(event.author, self.char2)
        self.assertEqual(event.valid, False)
        self.assertTrue(len(event.code) > 0)

    def test_del(self):
        """Add and remove an event."""
        self.handler.add_event(self.exit, "traverse", "pass",
                author=self.char1, valid=True)

        # Try to delete the event
        # char2 shouldn't be allowed to do so (that's not HIS event)
        self.call(CmdEvent(), "/del out = traverse 1", caller=self.char2)
        self.assertTrue(len(self.handler.get_events(self.exit).get(
                "traverse", [])) == 1)

        # Now, char1 should be allowed to delete it
        self.call(CmdEvent(), "/del out = traverse 1")
        self.assertTrue(len(self.handler.get_events(self.exit).get(
                "traverse", [])) == 0)

    def test_lock(self):
        """Test the lock of multiple editing."""
        self.call(CmdEvent(), "/add here = time 8:00", caller=self.char2)
        self.assertIsNotNone(self.char2.ndb._eveditor)

        # Now ask char1 to edit
        line = self.call(CmdEvent(), "/edit here = time 1")
        self.assertIsNone(self.char1.ndb._eveditor)

        # Try to delete this event while char2 is editing it
        line = self.call(CmdEvent(), "/del here = time 1")

    def test_accept(self):
        """Accept an event."""
        self.call(CmdEvent(), "/add here = time 8:00", caller=self.char2)
        editor = self.char2.ndb._eveditor
        self.assertIsNotNone(editor)

        # Edit the event
        editor.update_buffer(dedent("""
            room.msg_contents("It's 8 PM, everybody up!")
        """.strip("\n")))
        editor.save_buffer()
        editor.quit()
        event = self.room1.events.get("time")[0]
        self.assertEqual(event.valid, False)

        # chars shouldn't be allowed to the event
        self.call(CmdEvent(), "/accept here = time 1", caller=self.char2)
        event = self.room1.events.get("time")[0]
        self.assertEqual(event.valid, False)

        # char1 will accept the event
        self.call(CmdEvent(), "/accept here = time 1")
        event = self.room1.events.get("time")[0]
        self.assertEqual(event.valid, True)


class TestDefaultEvents(CommandTest):

    """Test the default events."""

    def setUp(self):
        """Create the event handler."""
        super(TestDefaultEvents, self).setUp()
        self.handler = create_script(
                "evennia.contrib.events.scripts.EventHandler")

    def tearDown(self):
        """Stop the event handler."""
        self.handler.stop()
        super(TestDefaultEvents, self).tearDown()

    def test_exit(self):
        """Test the events of an exit."""
        self.char1.key = "char1"
        code = dedent("""
            if character.key == "char1":
                character.msg("You can leave.")
            else:
                character.msg("You cannot leave.")
                deny()
        """.strip("\n"))
        # Try the can_traverse event
        self.handler.add_event(self.exit, "can_traverse", code,
                author=self.char1, valid=True)

        # Have char1 move through the exit
        self.call(ExitCommand(), "", "You can leave.", obj=self.exit)
        self.assertIs(self.char1.location, self.room2)

        # Have char2 move through this exit
        self.call(ExitCommand(), "", "You cannot leave.", obj=self.exit,
                caller=self.char2)
        self.assertIs(self.char2.location, self.room1)

        # Try the traverse event
        self.handler.del_event(self.exit, "can_traverse", 0)
        self.handler.add_event(self.exit, "traverse", "character.msg('Fine!')",
                author=self.char1, valid=True)

        # Have char2 move through the exit
        self.call(ExitCommand(), "", obj=self.exit, caller=self.char2)
        self.assertIs(self.char2.location, self.room2)
        self.handler.del_event(self.exit, "traverse", 0)

        # Move char1 and char2 back
        self.char1.location = self.room1
        self.char2.location = self.room1

        # Test msg_arrive and msg_leave
        code = 'message = "{character} goes out."'
        self.handler.add_event(self.exit, "msg_leave", code,
                author=self.char1, valid=True)

        # Have char1 move through the exit
        old_msg = self.char2.msg
        try:
            self.char2.msg = Mock()
            self.call(ExitCommand(), "", obj=self.exit)
            stored_msg = [args[0] if args and args[0] else kwargs.get("text",utils.to_str(kwargs, force_string=True))
                    for name, args, kwargs in self.char2.msg.mock_calls]
            # Get the first element of a tuple if msg received a tuple instead of a string
            stored_msg = [smsg[0] if isinstance(smsg, tuple) else smsg for smsg in stored_msg]
            returned_msg = ansi.parse_ansi("\n".join(stored_msg), strip_ansi=True)
            self.assertEqual(returned_msg, "char1 goes out.")
        finally:
            self.char2.msg = old_msg

        # Create a return exit
        back = create_object("evennia.objects.objects.DefaultExit",
                key="in", location=self.room2, destination=self.room1)
        code = 'message = "{character} goes in."'
        self.handler.add_event(self.exit, "msg_arrive", code,
                author=self.char1, valid=True)

        # Have char1 move through the exit
        old_msg = self.char2.msg
        try:
            self.char2.msg = Mock()
            self.call(ExitCommand(), "", obj=back)
            stored_msg = [args[0] if args and args[0] else kwargs.get("text",utils.to_str(kwargs, force_string=True))
                    for name, args, kwargs in self.char2.msg.mock_calls]
            # Get the first element of a tuple if msg received a tuple instead of a string
            stored_msg = [smsg[0] if isinstance(smsg, tuple) else smsg for smsg in stored_msg]
            returned_msg = ansi.parse_ansi("\n".join(stored_msg), strip_ansi=True)
            self.assertEqual(returned_msg, "char1 goes in.")
        finally:
            self.char2.msg = old_msg
