"""
Building menu tests.

"""

from evennia.commands.default.tests import BaseEvenniaCommandTest

from .building_menu import BuildingMenu, CmdNoMatch


class Submenu(BuildingMenu):
    def init(self, exit):
        self.add_choice("title", key="t", attr="key")


class TestBuildingMenu(BaseEvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.menu = BuildingMenu(caller=self.char1, obj=self.room1, title="test")
        self.menu.add_choice("title", key="t", attr="key")

    def test_quit(self):
        """Try to quit the building menu."""
        self.assertFalse(self.char1.cmdset.has("building_menu"))
        self.menu.open()
        self.assertTrue(self.char1.cmdset.has("building_menu"))
        self.call(CmdNoMatch(building_menu=self.menu), "q")
        # char1 tries to quit the editor
        self.assertFalse(self.char1.cmdset.has("building_menu"))

    def test_setattr(self):
        """Test the simple setattr provided by building menus."""
        self.menu.open()
        self.call(CmdNoMatch(building_menu=self.menu), "t")
        self.assertIsNotNone(self.menu.current_choice)
        self.call(CmdNoMatch(building_menu=self.menu), "some new title")
        self.call(CmdNoMatch(building_menu=self.menu), "@")
        self.assertIsNone(self.menu.current_choice)
        self.assertEqual(self.room1.key, "some new title")
        self.call(CmdNoMatch(building_menu=self.menu), "q")

    def test_add_choice_without_key(self):
        """Try to add choices without keys."""
        choices = []
        for i in range(20):
            choices.append(self.menu.add_choice("choice", attr="test"))
        self.menu._add_keys_choice()
        keys = [
            "c",
            "h",
            "o",
            "i",
            "e",
            "ch",
            "ho",
            "oi",
            "ic",
            "ce",
            "cho",
            "hoi",
            "oic",
            "ice",
            "choi",
            "hoic",
            "oice",
            "choic",
            "hoice",
            "choice",
        ]
        for i in range(20):
            self.assertEqual(choices[i].key, keys[i])

        # Adding another key of the same title would break, no more available shortcut
        self.menu.add_choice("choice", attr="test")
        with self.assertRaises(ValueError):
            self.menu._add_keys_choice()

    def test_callbacks(self):
        """Test callbacks in menus."""
        self.room1.key = "room1"

        def on_enter(caller, menu):
            caller.msg("on_enter:{}".format(menu.title))

        def on_nomatch(caller, string, choice):
            caller.msg("on_nomatch:{},{}".format(string, choice.key))

        def on_leave(caller, obj):
            caller.msg("on_leave:{}".format(obj.key))

        self.menu.add_choice(
            "test", key="e", on_enter=on_enter, on_nomatch=on_nomatch, on_leave=on_leave
        )
        self.call(CmdNoMatch(building_menu=self.menu), "e", "on_enter:test")
        self.call(CmdNoMatch(building_menu=self.menu), "ok", "on_nomatch:ok,e")
        self.call(CmdNoMatch(building_menu=self.menu), "@", "on_leave:room1")
        self.call(CmdNoMatch(building_menu=self.menu), "q")

    def test_multi_level(self):
        """Test multi-level choices."""
        # Creaste three succeeding menu (t2 is contained in t1, t3 is contained in t2)
        def on_nomatch_t1(caller, menu):
            menu.move("whatever")  # this will be valid since after t1 is a joker

        def on_nomatch_t2(caller, menu):
            menu.move("t3")  # this time the key matters

        t1 = self.menu.add_choice("what", key="t1", on_nomatch=on_nomatch_t1)
        t2 = self.menu.add_choice("and", key="t1.*", on_nomatch=on_nomatch_t2)
        t3 = self.menu.add_choice("why", key="t1.*.t3")
        self.menu.open()

        # Move into t1
        self.assertIn(t1, self.menu.relevant_choices)
        self.assertNotIn(t2, self.menu.relevant_choices)
        self.assertNotIn(t3, self.menu.relevant_choices)
        self.assertIsNone(self.menu.current_choice)
        self.call(CmdNoMatch(building_menu=self.menu), "t1")
        self.assertEqual(self.menu.current_choice, t1)
        self.assertNotIn(t1, self.menu.relevant_choices)
        self.assertIn(t2, self.menu.relevant_choices)
        self.assertNotIn(t3, self.menu.relevant_choices)

        # Move into t2
        self.call(CmdNoMatch(building_menu=self.menu), "t2")
        self.assertEqual(self.menu.current_choice, t2)
        self.assertNotIn(t1, self.menu.relevant_choices)
        self.assertNotIn(t2, self.menu.relevant_choices)
        self.assertIn(t3, self.menu.relevant_choices)

        # Move into t3
        self.call(CmdNoMatch(building_menu=self.menu), "t3")
        self.assertEqual(self.menu.current_choice, t3)
        self.assertNotIn(t1, self.menu.relevant_choices)
        self.assertNotIn(t2, self.menu.relevant_choices)
        self.assertNotIn(t3, self.menu.relevant_choices)

        # Move back to t2
        self.call(CmdNoMatch(building_menu=self.menu), "@")
        self.assertEqual(self.menu.current_choice, t2)
        self.assertNotIn(t1, self.menu.relevant_choices)
        self.assertNotIn(t2, self.menu.relevant_choices)
        self.assertIn(t3, self.menu.relevant_choices)

        # Move back into t1
        self.call(CmdNoMatch(building_menu=self.menu), "@")
        self.assertEqual(self.menu.current_choice, t1)
        self.assertNotIn(t1, self.menu.relevant_choices)
        self.assertIn(t2, self.menu.relevant_choices)
        self.assertNotIn(t3, self.menu.relevant_choices)

        # Moves back to the main menu
        self.call(CmdNoMatch(building_menu=self.menu), "@")
        self.assertIn(t1, self.menu.relevant_choices)
        self.assertNotIn(t2, self.menu.relevant_choices)
        self.assertNotIn(t3, self.menu.relevant_choices)
        self.assertIsNone(self.menu.current_choice)
        self.call(CmdNoMatch(building_menu=self.menu), "q")

    def test_submenu(self):
        """Test to add sub-menus."""

        def open_exit(menu):
            menu.open_submenu("evennia.contrib.base_systems.building_menu.tests.Submenu", self.exit)
            return False

        self.menu.add_choice("exit", key="x", on_enter=open_exit)
        self.menu.open()
        self.call(CmdNoMatch(building_menu=self.menu), "x")
        self.menu = self.char1.ndb._building_menu
        self.call(CmdNoMatch(building_menu=self.menu), "t")
        self.call(CmdNoMatch(building_menu=self.menu), "in")
        self.call(CmdNoMatch(building_menu=self.menu), "@")
        self.call(CmdNoMatch(building_menu=self.menu), "@")
        self.menu = self.char1.ndb._building_menu
        self.assertEqual(self.char1.ndb._building_menu.obj, self.room1)
        self.call(CmdNoMatch(building_menu=self.menu), "q")
        self.assertEqual(self.exit.key, "in")
