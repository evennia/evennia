"""
Unit tests for the Evscaperoom

"""
import inspect
import pkgutil
from os import path
from evennia.commands.default.tests import CommandTest
from evennia import InterruptCommand
from evennia.utils.test_resources import EvenniaTest
from evennia.utils import mod_import
from . import commands
from . import state as basestate
from . import objects
from . import utils


class TestEvscaperoomCommands(CommandTest):
    def setUp(self):
        super().setUp()
        self.room1 = utils.create_evscaperoom_object("evscaperoom.room.EvscapeRoom", key="Testroom")
        self.char1.location = self.room1
        self.obj1.location = self.room1

    def test_base_search(self):

        cmd = commands.CmdEvscapeRoom()
        cmd.caller = self.char1

        self.assertEqual((self.obj1, None), cmd._search("Obj", True))
        self.assertEqual((None, "Obj"), cmd._search("Obj", False))
        self.assertEqual((None, "Foo"), cmd._search("Foo", False))
        self.assertEqual((None, "Foo"), cmd._search("Foo", None))
        self.assertRaises(InterruptCommand, cmd._search, "Foo", True)

    def test_base_parse(self):

        cmd = commands.CmdEvscapeRoom()
        cmd.caller = self.char1

        cmd.obj1_search = None
        cmd.obj2_search = None
        cmd.args = "obj"
        cmd.parse()

        self.assertEqual(cmd.obj1, self.obj1)
        self.assertEqual(cmd.room, self.char1.location)

        cmd = commands.CmdEvscapeRoom()
        cmd.caller = self.char1
        cmd.obj1_search = False
        cmd.obj2_search = False
        cmd.args = "obj"
        cmd.parse()

        self.assertEqual(cmd.arg1, "obj")
        self.assertEqual(cmd.obj1, None)

        cmd = commands.CmdEvscapeRoom()
        cmd.caller = self.char1
        cmd.obj1_search = None
        cmd.obj2_search = None
        cmd.args = "obj"
        cmd.parse()

        self.assertEqual(cmd.obj1, self.obj1)
        self.assertEqual(cmd.arg1, None)
        self.assertEqual(cmd.arg2, None)

        cmd = commands.CmdEvscapeRoom()
        cmd.caller = self.char1
        cmd.obj1_search = True
        cmd.obj2_search = True
        cmd.args = "obj at obj"
        cmd.parse()

        self.assertEqual(cmd.obj1, self.obj1)
        self.assertEqual(cmd.obj2, self.obj1)
        self.assertEqual(cmd.arg1, None)
        self.assertEqual(cmd.arg2, None)

        cmd = commands.CmdEvscapeRoom()
        cmd.caller = self.char1
        cmd.obj1_search = False
        cmd.obj2_search = False
        cmd.args = "obj at obj"
        cmd.parse()

        self.assertEqual(cmd.obj1, None)
        self.assertEqual(cmd.obj2, None)
        self.assertEqual(cmd.arg1, "obj")
        self.assertEqual(cmd.arg2, "obj")

        cmd = commands.CmdEvscapeRoom()
        cmd.caller = self.char1
        cmd.obj1_search = None
        cmd.obj2_search = None
        cmd.args = "obj at obj"
        cmd.parse()

        self.assertEqual(cmd.obj1, self.obj1)
        self.assertEqual(cmd.obj2, self.obj1)
        self.assertEqual(cmd.arg1, None)
        self.assertEqual(cmd.arg2, None)

        cmd = commands.CmdEvscapeRoom()
        cmd.caller = self.char1
        cmd.obj1_search = None
        cmd.obj2_search = None
        cmd.args = "foo in obj"
        cmd.parse()

        self.assertEqual(cmd.obj1, None)
        self.assertEqual(cmd.obj2, self.obj1)
        self.assertEqual(cmd.arg1, "foo")
        self.assertEqual(cmd.arg2, None)

        cmd = commands.CmdEvscapeRoom()
        cmd.caller = self.char1
        cmd.obj1_search = None
        cmd.obj2_search = None
        cmd.args = "obj on foo"
        cmd.parse()

        self.assertEqual(cmd.obj1, self.obj1)
        self.assertEqual(cmd.obj2, None)
        self.assertEqual(cmd.arg1, None)
        self.assertEqual(cmd.arg2, "foo")

        cmd = commands.CmdEvscapeRoom()
        cmd.caller = self.char1
        cmd.obj1_search = None
        cmd.obj2_search = True
        cmd.args = "obj on foo"
        self.assertRaises(InterruptCommand, cmd.parse)

        cmd = commands.CmdEvscapeRoom()
        cmd.caller = self.char1
        cmd.obj1_search = None
        cmd.obj2_search = True
        cmd.args = "on obj"
        cmd.parse()
        self.assertEqual(cmd.obj1, None)
        self.assertEqual(cmd.obj2, self.obj1)
        self.assertEqual(cmd.arg1, "")
        self.assertEqual(cmd.arg2, None)

    def test_set_focus(self):
        cmd = commands.CmdEvscapeRoom()
        cmd.caller = self.char1
        cmd.room = self.room1
        cmd.focus = self.obj1
        self.assertEqual(
            self.char1.attributes.get("focus", category=self.room1.tagcategory), self.obj1
        )

    def test_focus(self):
        # don't focus on a non-room object
        self.call(commands.CmdFocus(), "obj")
        self.assertEqual(self.char1.attributes.get("focus", category=self.room1.tagcategory), None)
        # should focus correctly
        myobj = utils.create_evscaperoom_object(
            objects.EvscaperoomObject, "mytestobj", location=self.room1
        )
        self.call(commands.CmdFocus(), "mytestobj")
        self.assertEqual(self.char1.attributes.get("focus", category=self.room1.tagcategory), myobj)

    def test_look(self):
        self.call(commands.CmdLook(), "at obj", "Obj")
        self.call(commands.CmdLook(), "obj", "Obj")
        self.call(commands.CmdLook(), "obj", "Obj")

    def test_speech(self):
        self.call(commands.CmdSpeak(), "", "What do you want to say?", cmdstring="")
        self.call(commands.CmdSpeak(), "Hello!", "You say: Hello!", cmdstring="")
        self.call(commands.CmdSpeak(), "", "What do you want to whisper?", cmdstring="whisper")
        self.call(commands.CmdSpeak(), "Hi.", "You whisper: Hi.", cmdstring="whisper")
        self.call(commands.CmdSpeak(), "Hi.", "You whisper: Hi.", cmdstring="whisper")
        self.call(commands.CmdSpeak(), "HELLO!", "You shout: HELLO!", cmdstring="shout")

        self.call(commands.CmdSpeak(), "Hello to obj", "You say: Hello", cmdstring="say")
        self.call(commands.CmdSpeak(), "Hello to obj", "You shout: Hello", cmdstring="shout")

    def test_emote(self):
        self.call(
            commands.CmdEmote(),
            "/me smiles to /obj",
            f"Char(#{self.char1.id}) smiles to Obj(#{self.obj1.id})",
        )

    def test_focus_interaction(self):
        self.call(commands.CmdFocusInteraction(), "", "Hm?")


class TestUtils(EvenniaTest):
    def test_overwrite(self):
        room = utils.create_evscaperoom_object("evscaperoom.room.EvscapeRoom", key="Testroom")
        obj1 = utils.create_evscaperoom_object(
            objects.EvscaperoomObject, key="testobj", location=room
        )
        id1 = obj1.id

        obj2 = utils.create_evscaperoom_object(
            objects.EvscaperoomObject, key="testobj", location=room
        )
        id2 = obj2.id

        # we should have created a new object, deleting the old same-named one
        self.assertTrue(id1 != id2)
        self.assertFalse(bool(obj1.pk))
        self.assertTrue(bool(obj2.pk))

    def test_parse_for_perspectives(self):

        second, third = utils.parse_for_perspectives("~You ~look at the nice book", "TestGuy")
        self.assertTrue(second, "You look at the nice book")
        self.assertTrue(third, "TestGuy looks at the nice book")
        # irregular
        second, third = utils.parse_for_perspectives("With a smile, ~you ~were gone", "TestGuy")
        self.assertTrue(second, "With a smile, you were gone")
        self.assertTrue(third, "With a smile, TestGuy was gone")

    def test_parse_for_things(self):

        string = "Looking at *book and *key."
        self.assertEqual(utils.parse_for_things(string, 0), "Looking at book and key.")
        self.assertEqual(utils.parse_for_things(string, 1), "Looking at |ybook|n and |ykey|n.")
        self.assertEqual(utils.parse_for_things(string, 2), "Looking at |y[book]|n and |y[key]|n.")


class TestEvScapeRoom(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = utils.create_evscaperoom_object(
            "evscaperoom.room.EvscapeRoom", key="Testroom", home=self.room1
        )
        self.roomtag = "evscaperoom_{}".format(self.room.key)

    def tearDown(self):
        self.room.delete()

    def test_room_methods(self):

        room = self.room
        self.char1.location = room

        self.assertEqual(room.tagcategory, self.roomtag)
        self.assertEqual(list(room.get_all_characters()), [self.char1])

        room.tag_character(self.char1, "opened_door")
        self.assertEqual(self.char1.tags.get("opened_door", category=self.roomtag), "opened_door")

        room.tag_all_characters("tagged_all")
        self.assertEqual(self.char1.tags.get("tagged_all", category=self.roomtag), "tagged_all")

        room.character_cleanup(self.char1)
        self.assertEqual(self.char1.tags.get(category=self.roomtag), None)


class TestStates(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = utils.create_evscaperoom_object(
            "evscaperoom.room.EvscapeRoom", key="Testroom", home=self.room1
        )
        self.roomtag = "evscaperoom_#{}".format(self.room.id)

    def tearDown(self):
        self.room.delete()

    def _get_all_state_modules(self):
        dirname = path.join(path.dirname(__file__), "states")
        states = []
        for imp, module, ispackage in pkgutil.walk_packages(
            path=[dirname], prefix="evscaperoom.states."
        ):
            mod = mod_import(module)
            states.append(mod)
        return states

    def test_base_state(self):

        st = basestate.BaseState(self.room.statehandler, self.room)
        st.init()
        obj = st.create_object(objects.Edible, key="apple")
        self.assertEqual(obj.key, "apple")
        self.assertEqual(obj.__class__, objects.Edible)
        obj.delete()

    def test_all_states(self):
        "Tick through all defined states"

        for mod in self._get_all_state_modules():

            state = mod.State(self.room.statehandler, self.room)
            state.init()

            for obj in self.room.contents:
                if obj.pk:
                    methods = inspect.getmembers(obj, predicate=inspect.ismethod)
                    for name, method in methods:
                        if name.startswith("at_focus_"):
                            method(self.char1, args="dummy")

            next_state = state.next()
            self.assertEqual(next_state, mod.State.next_state)
