"""
Module containing the test cases for the in-game Python system.
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
from evennia.contrib.ingame_python.commands import CmdCallback
from evennia.contrib.ingame_python.callbackhandler import CallbackHandler

# Force settings
settings.EVENTS_CALENDAR = "standard"

# Constants
OLD_EVENTS = {}


class TestEventHandler(EvenniaTest):

    """
    Test cases of the event handler to add, edit or delete events.
    """

    def setUp(self):
        """Create the event handler."""
        super().setUp()
        self.handler = create_script("evennia.contrib.ingame_python.scripts.EventHandler")

        # Copy old events if necessary
        if OLD_EVENTS:
            self.handler.ndb.events = dict(OLD_EVENTS)

        # Alter typeclasses
        self.char1.swap_typeclass("evennia.contrib.ingame_python.typeclasses.EventCharacter")
        self.char2.swap_typeclass("evennia.contrib.ingame_python.typeclasses.EventCharacter")
        self.room1.swap_typeclass("evennia.contrib.ingame_python.typeclasses.EventRoom")
        self.room2.swap_typeclass("evennia.contrib.ingame_python.typeclasses.EventRoom")
        self.exit.swap_typeclass("evennia.contrib.ingame_python.typeclasses.EventExit")

    def tearDown(self):
        """Stop the event handler."""
        OLD_EVENTS.clear()
        OLD_EVENTS.update(self.handler.ndb.events)
        self.handler.stop()
        CallbackHandler.script = None
        super().tearDown()

    def test_start(self):
        """Simply make sure the handler runs with proper initial values."""
        self.assertEqual(self.handler.db.callbacks, {})
        self.assertEqual(self.handler.db.to_valid, [])
        self.assertEqual(self.handler.db.locked, [])
        self.assertEqual(self.handler.db.tasks, {})
        self.assertIsNotNone(self.handler.ndb.events)

    def test_add_validation(self):
        """Add a callback while needing validation."""
        author = self.char1
        self.handler.add_callback(
            self.room1, "dummy", "character.db.strength = 40", author=author, valid=False
        )
        callback = self.handler.get_callbacks(self.room1).get("dummy")
        callback = callback[0]
        self.assertIsNotNone(callback)
        self.assertEqual(callback["author"], author)
        self.assertEqual(callback["valid"], False)

        # Since this callback is not valid, it should appear in 'to_valid'
        self.assertIn((self.room1, "dummy", 0), self.handler.db.to_valid)

        # Run this dummy callback (shouldn't do anything)
        self.char1.db.strength = 10
        locals = {"character": self.char1}
        self.assertTrue(self.handler.call(self.room1, "dummy", locals=locals))
        self.assertEqual(self.char1.db.strength, 10)

    def test_edit(self):
        """Test editing a callback."""
        author = self.char1
        self.handler.add_callback(
            self.room1, "dummy", "character.db.strength = 60", author=author, valid=True
        )

        # Edit it right away
        self.handler.edit_callback(
            self.room1, "dummy", 0, "character.db.strength = 65", author=self.char2, valid=True
        )

        # Check that the callback was written
        callback = self.handler.get_callbacks(self.room1).get("dummy")
        callback = callback[0]
        self.assertIsNotNone(callback)
        self.assertEqual(callback["author"], author)
        self.assertEqual(callback["valid"], True)
        self.assertEqual(callback["updated_by"], self.char2)

        # Run this dummy callback
        self.char1.db.strength = 10
        locals = {"character": self.char1}
        self.assertTrue(self.handler.call(self.room1, "dummy", locals=locals))
        self.assertEqual(self.char1.db.strength, 65)

    def test_edit_validation(self):
        """Edit a callback when validation isn't automatic."""
        author = self.char1
        self.handler.add_callback(
            self.room1, "dummy", "character.db.strength = 70", author=author, valid=True
        )

        # Edit it right away
        self.handler.edit_callback(
            self.room1, "dummy", 0, "character.db.strength = 80", author=self.char2, valid=False
        )

        # Run this dummy callback (shouldn't do anything)
        self.char1.db.strength = 10
        locals = {"character": self.char1}
        self.assertTrue(self.handler.call(self.room1, "dummy", locals=locals))
        self.assertEqual(self.char1.db.strength, 10)

    def test_del(self):
        """Try to delete a callback."""
        # Add 3 callbacks
        self.handler.add_callback(
            self.room1, "dummy", "character.db.strength = 5", author=self.char1, valid=True
        )
        self.handler.add_callback(
            self.room1, "dummy", "character.db.strength = 8", author=self.char2, valid=False
        )
        self.handler.add_callback(
            self.room1, "dummy", "character.db.strength = 9", author=self.char1, valid=True
        )

        # Note that the second callback isn't valid
        self.assertIn((self.room1, "dummy", 1), self.handler.db.to_valid)

        # Lock the third callback
        self.handler.db.locked.append((self.room1, "dummy", 2))

        # Delete the first callback
        self.handler.del_callback(self.room1, "dummy", 0)

        # The callback #1 that was to valid should be #0 now
        self.assertIn((self.room1, "dummy", 0), self.handler.db.to_valid)
        self.assertNotIn((self.room1, "dummy", 1), self.handler.db.to_valid)

        # The lock has been updated too
        self.assertIn((self.room1, "dummy", 1), self.handler.db.locked)
        self.assertNotIn((self.room1, "dummy", 2), self.handler.db.locked)

        # Now delete the first (not valid) callback
        self.handler.del_callback(self.room1, "dummy", 0)
        self.assertEqual(self.handler.db.to_valid, [])
        self.assertIn((self.room1, "dummy", 0), self.handler.db.locked)
        self.assertNotIn((self.room1, "dummy", 1), self.handler.db.locked)

        # Call the remaining callback
        self.char1.db.strength = 10
        locals = {"character": self.char1}
        self.assertTrue(self.handler.call(self.room1, "dummy", locals=locals))
        self.assertEqual(self.char1.db.strength, 9)

    def test_accept(self):
        """Accept an callback."""
        # Add 2 callbacks
        self.handler.add_callback(
            self.room1, "dummy", "character.db.strength = 5", author=self.char1, valid=True
        )
        self.handler.add_callback(
            self.room1, "dummy", "character.db.strength = 8", author=self.char2, valid=False
        )

        # Note that the second callback isn't valid
        self.assertIn((self.room1, "dummy", 1), self.handler.db.to_valid)

        # Accept the second callback
        self.handler.accept_callback(self.room1, "dummy", 1)
        callback = self.handler.get_callbacks(self.room1).get("dummy")
        callback = callback[1]
        self.assertIsNotNone(callback)
        self.assertEqual(callback["valid"], True)

        # Call the dummy callback
        self.char1.db.strength = 10
        locals = {"character": self.char1}
        self.assertTrue(self.handler.call(self.room1, "dummy", locals=locals))
        self.assertEqual(self.char1.db.strength, 8)

    def test_call(self):
        """Test to call amore complex callback."""
        self.char1.key = "one"
        self.char2.key = "two"

        # Add an callback
        code = dedent(
            """
            if character.key == "one":
                character.db.health = 50
            else:
                character.db.health = 0
        """.strip(
                "\n"
            )
        )
        self.handler.add_callback(self.room1, "dummy", code, author=self.char1, valid=True)

        # Call the dummy callback
        self.assertTrue(self.handler.call(self.room1, "dummy", locals={"character": self.char1}))
        self.assertEqual(self.char1.db.health, 50)
        self.assertTrue(self.handler.call(self.room1, "dummy", locals={"character": self.char2}))
        self.assertEqual(self.char2.db.health, 0)

    def test_handler(self):
        """Test the object handler."""
        self.assertIsNotNone(self.char1.callbacks)

        # Add an callback
        callback = self.room1.callbacks.add("dummy", "pass", author=self.char1, valid=True)
        self.assertEqual(callback.obj, self.room1)
        self.assertEqual(callback.name, "dummy")
        self.assertEqual(callback.code, "pass")
        self.assertEqual(callback.author, self.char1)
        self.assertEqual(callback.valid, True)
        self.assertIn([callback], list(self.room1.callbacks.all().values()))

        # Edit this very callback
        new = self.room1.callbacks.edit(
            "dummy", 0, "character.db.say = True", author=self.char1, valid=True
        )
        self.assertIn([new], list(self.room1.callbacks.all().values()))
        self.assertNotIn([callback], list(self.room1.callbacks.all().values()))

        # Try to call this callback
        self.assertTrue(self.room1.callbacks.call("dummy", locals={"character": self.char2}))
        self.assertTrue(self.char2.db.say)

        # Delete the callback
        self.room1.callbacks.remove("dummy", 0)
        self.assertEqual(self.room1.callbacks.all(), {})


class TestCmdCallback(CommandTest):

    """Test the @callback command."""

    def setUp(self):
        """Create the callback handler."""
        super().setUp()
        self.handler = create_script("evennia.contrib.ingame_python.scripts.EventHandler")

        # Copy old events if necessary
        if OLD_EVENTS:
            self.handler.ndb.events = dict(OLD_EVENTS)

        # Alter typeclasses
        self.char1.swap_typeclass("evennia.contrib.ingame_python.typeclasses.EventCharacter")
        self.char2.swap_typeclass("evennia.contrib.ingame_python.typeclasses.EventCharacter")
        self.room1.swap_typeclass("evennia.contrib.ingame_python.typeclasses.EventRoom")
        self.room2.swap_typeclass("evennia.contrib.ingame_python.typeclasses.EventRoom")
        self.exit.swap_typeclass("evennia.contrib.ingame_python.typeclasses.EventExit")

    def tearDown(self):
        """Stop the callback handler."""
        OLD_EVENTS.clear()
        OLD_EVENTS.update(self.handler.ndb.events)
        self.handler.stop()
        for script in ScriptDB.objects.filter(
            db_typeclass_path="evennia.contrib.ingame_python.scripts.TimeEventScript"
        ):
            script.stop()

        CallbackHandler.script = None
        super().tearDown()

    def test_list(self):
        """Test listing callbacks with different rights."""
        table = self.call(CmdCallback(), "out")
        lines = table.splitlines()[3:-1]
        self.assertNotEqual(lines, [])

        # Check that the second column only contains 0 (0) (no callback yet)
        for line in lines:
            cols = line.split("|")
            self.assertIn(cols[2].strip(), ("0 (0)", ""))

        # Add some callback
        self.handler.add_callback(self.exit, "traverse", "pass", author=self.char1, valid=True)

        # Try to obtain more details on a specific callback on exit
        table = self.call(CmdCallback(), "out = traverse")
        lines = table.splitlines()[3:-1]
        self.assertEqual(len(lines), 1)
        line = lines[0]
        cols = line.split("|")
        self.assertIn(cols[1].strip(), ("1", ""))
        self.assertIn(cols[2].strip(), (str(self.char1), ""))
        self.assertIn(cols[-1].strip(), ("Yes", "No", ""))

        # Run the same command with char2
        # char2 shouldn't see the last column (Valid)
        table = self.call(CmdCallback(), "out = traverse", caller=self.char2)
        lines = table.splitlines()[3:-1]
        self.assertEqual(len(lines), 1)
        line = lines[0]
        cols = line.split("|")
        self.assertEqual(cols[1].strip(), "1")
        self.assertNotIn(cols[-1].strip(), ("Yes", "No"))

        # In any case, display the callback
        # The last line should be "pass" (the callback code)
        details = self.call(CmdCallback(), "out = traverse 1")
        self.assertEqual(details.splitlines()[-1], "pass")

    def test_add(self):
        """Test to add an callback."""
        self.call(CmdCallback(), "/add out = traverse")
        editor = self.char1.ndb._eveditor
        self.assertIsNotNone(editor)

        # Edit the callback
        editor.update_buffer(
            dedent(
                """
            if character.key == "one":
                character.msg("You can pass.")
            else:
                character.msg("You can't pass.")
                deny()
        """.strip(
                    "\n"
                )
            )
        )
        editor.save_buffer()
        editor.quit()
        callback = self.exit.callbacks.get("traverse")[0]
        self.assertEqual(callback.author, self.char1)
        self.assertEqual(callback.valid, True)
        self.assertTrue(len(callback.code) > 0)

        # We're going to try the same thing but with char2
        # char2 being a player for our test, the callback won't be validated.
        self.call(CmdCallback(), "/add out = traverse", caller=self.char2)
        editor = self.char2.ndb._eveditor
        self.assertIsNotNone(editor)

        # Edit the callback
        editor.update_buffer(
            dedent(
                """
            character.msg("No way.")
        """.strip(
                    "\n"
                )
            )
        )
        editor.save_buffer()
        editor.quit()
        callback = self.exit.callbacks.get("traverse")[1]
        self.assertEqual(callback.author, self.char2)
        self.assertEqual(callback.valid, False)
        self.assertTrue(len(callback.code) > 0)

    def test_del(self):
        """Add and remove an callback."""
        self.handler.add_callback(self.exit, "traverse", "pass", author=self.char1, valid=True)

        # Try to delete the callback
        # char2 shouldn't be allowed to do so (that's not HIS callback)
        self.call(CmdCallback(), "/del out = traverse 1", caller=self.char2)
        self.assertTrue(len(self.handler.get_callbacks(self.exit).get("traverse", [])) == 1)

        # Now, char1 should be allowed to delete it
        self.call(CmdCallback(), "/del out = traverse 1")
        self.assertTrue(len(self.handler.get_callbacks(self.exit).get("traverse", [])) == 0)

    def test_lock(self):
        """Test the lock of multiple editing."""
        self.call(CmdCallback(), "/add here = time 8:00", caller=self.char2)
        self.assertIsNotNone(self.char2.ndb._eveditor)

        # Now ask char1 to edit
        line = self.call(CmdCallback(), "/edit here = time 1")
        self.assertIsNone(self.char1.ndb._eveditor)

        # Try to delete this callback while char2 is editing it
        line = self.call(CmdCallback(), "/del here = time 1")

    def test_accept(self):
        """Accept an callback."""
        self.call(CmdCallback(), "/add here = time 8:00", caller=self.char2)
        editor = self.char2.ndb._eveditor
        self.assertIsNotNone(editor)

        # Edit the callback
        editor.update_buffer(
            dedent(
                """
            room.msg_contents("It's 8 PM, everybody up!")
        """.strip(
                    "\n"
                )
            )
        )
        editor.save_buffer()
        editor.quit()
        callback = self.room1.callbacks.get("time")[0]
        self.assertEqual(callback.valid, False)

        # chars shouldn't be allowed to the callback
        self.call(CmdCallback(), "/accept here = time 1", caller=self.char2)
        callback = self.room1.callbacks.get("time")[0]
        self.assertEqual(callback.valid, False)

        # char1 will accept the callback
        self.call(CmdCallback(), "/accept here = time 1")
        callback = self.room1.callbacks.get("time")[0]
        self.assertEqual(callback.valid, True)


class TestDefaultCallbacks(CommandTest):

    """Test the default callbacks."""

    def setUp(self):
        """Create the callback handler."""
        super().setUp()
        self.handler = create_script("evennia.contrib.ingame_python.scripts.EventHandler")

        # Copy old events if necessary
        if OLD_EVENTS:
            self.handler.ndb.events = dict(OLD_EVENTS)

        # Alter typeclasses
        self.char1.swap_typeclass("evennia.contrib.ingame_python.typeclasses.EventCharacter")
        self.char2.swap_typeclass("evennia.contrib.ingame_python.typeclasses.EventCharacter")
        self.room1.swap_typeclass("evennia.contrib.ingame_python.typeclasses.EventRoom")
        self.room2.swap_typeclass("evennia.contrib.ingame_python.typeclasses.EventRoom")
        self.exit.swap_typeclass("evennia.contrib.ingame_python.typeclasses.EventExit")

    def tearDown(self):
        """Stop the callback handler."""
        OLD_EVENTS.clear()
        OLD_EVENTS.update(self.handler.ndb.events)
        self.handler.stop()
        CallbackHandler.script = None
        super().tearDown()

    def test_exit(self):
        """Test the callbacks of an exit."""
        self.char1.key = "char1"
        code = dedent(
            """
            if character.key == "char1":
                character.msg("You can leave.")
            else:
                character.msg("You cannot leave.")
                deny()
        """.strip(
                "\n"
            )
        )
        # Enforce self.exit.destination since swapping typeclass lose it
        self.exit.destination = self.room2

        # Try the can_traverse callback
        self.handler.add_callback(self.exit, "can_traverse", code, author=self.char1, valid=True)

        # Have char1 move through the exit
        self.call(ExitCommand(), "", "You can leave.", obj=self.exit)
        self.assertIs(self.char1.location, self.room2)

        # Have char2 move through this exit
        self.call(ExitCommand(), "", "You cannot leave.", obj=self.exit, caller=self.char2)
        self.assertIs(self.char2.location, self.room1)

        # Try the traverse callback
        self.handler.del_callback(self.exit, "can_traverse", 0)
        self.handler.add_callback(
            self.exit, "traverse", "character.msg('Fine!')", author=self.char1, valid=True
        )

        # Have char2 move through the exit
        self.call(ExitCommand(), "", obj=self.exit, caller=self.char2)
        self.assertIs(self.char2.location, self.room2)
        self.handler.del_callback(self.exit, "traverse", 0)

        # Move char1 and char2 back
        self.char1.location = self.room1
        self.char2.location = self.room1

        # Test msg_arrive and msg_leave
        code = 'message = "{character} goes out."'
        self.handler.add_callback(self.exit, "msg_leave", code, author=self.char1, valid=True)

        # Have char1 move through the exit
        old_msg = self.char2.msg
        try:
            self.char2.msg = Mock()
            self.call(ExitCommand(), "", obj=self.exit)
            stored_msg = [
                args[0] if args and args[0] else kwargs.get("text", utils.to_str(kwargs))
                for name, args, kwargs in self.char2.msg.mock_calls
            ]
            # Get the first element of a tuple if msg received a tuple instead of a string
            stored_msg = [smsg[0] if isinstance(smsg, tuple) else smsg for smsg in stored_msg]
            returned_msg = ansi.parse_ansi("\n".join(stored_msg), strip_ansi=True)
            self.assertEqual(returned_msg, "char1 goes out.")
        finally:
            self.char2.msg = old_msg

        # Create a return exit
        back = create_object(
            "evennia.objects.objects.DefaultExit",
            key="in",
            location=self.room2,
            destination=self.room1,
        )
        code = 'message = "{character} goes in."'
        self.handler.add_callback(self.exit, "msg_arrive", code, author=self.char1, valid=True)

        # Have char1 move through the exit
        old_msg = self.char2.msg
        try:
            self.char2.msg = Mock()
            self.call(ExitCommand(), "", obj=back)
            stored_msg = [
                args[0] if args and args[0] else kwargs.get("text", utils.to_str(kwargs))
                for name, args, kwargs in self.char2.msg.mock_calls
            ]
            # Get the first element of a tuple if msg received a tuple instead of a string
            stored_msg = [smsg[0] if isinstance(smsg, tuple) else smsg for smsg in stored_msg]
            returned_msg = ansi.parse_ansi("\n".join(stored_msg), strip_ansi=True)
            self.assertEqual(returned_msg, "char1 goes in.")
        finally:
            self.char2.msg = old_msg
