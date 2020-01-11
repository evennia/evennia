"""
Test eveditor

"""

from mock import MagicMock
from django.test import TestCase
from evennia.utils import eveditor
from evennia.commands.default.tests import CommandTest


class TestEvEditor(CommandTest):
    def test_eveditor_view_cmd(self):
        eveditor.EvEditor(self.char1)
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            cmdstring=":h",
            msg="<txt>  - any non-command is appended to the end of the buffer.",
        )
        # empty buffer
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            cmdstring=":",
            msg="Line Editor []\n01\n[l:01 w:000 c:0000](:h for help)",
        )
        # input a string
        self.call(
            eveditor.CmdLineInput(),
            "First test line",
            raw_string="First test line",
            msg="01First test line",
        )
        self.call(
            eveditor.CmdLineInput(),
            "Second test line",
            raw_string="Second test line",
            msg="02Second test line",
        )
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "First test line\nSecond test line")

        self.call(
            eveditor.CmdEditorGroup(),
            "",
            cmdstring=":",  # view buffer
            msg="Line Editor []\n01First test line\n"
            "02Second test line\n[l:02 w:006 c:0032](:h for help)",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            cmdstring="::",  # view buffer, no linenums
            msg="Line Editor []\nFirst test line\n"
            "Second test line\n[l:02 w:006 c:0032](:h for help)",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            cmdstring=":::",  # add single : alone on row
            msg="Single ':' added to buffer.",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            cmdstring=":",
            msg="Line Editor []\n01First test line\n"
            "02Second test line\n03:\n[l:03 w:007 c:0034](:h for help)",
        )

        self.call(
            eveditor.CmdEditorGroup(), "", cmdstring=":dd", msg="Deleted line 3."  # delete line
        )
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "First test line\nSecond test line")
        self.call(eveditor.CmdEditorGroup(), "", cmdstring=":u", msg="Undid one step.")  # undo
        self.assertEqual(
            self.char1.ndb._eveditor.get_buffer(), "First test line\nSecond test line\n:"
        )
        self.call(eveditor.CmdEditorGroup(), "", cmdstring=":uu", msg="Redid one step.")  # redo
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "First test line\nSecond test line")
        self.call(eveditor.CmdEditorGroup(), "", cmdstring=":u", msg="Undid one step.")  # undo
        self.assertEqual(
            self.char1.ndb._eveditor.get_buffer(), "First test line\nSecond test line\n:"
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            cmdstring=":",
            msg="Line Editor []\n01First test line\n"
            "02Second test line\n03:\n[l:03 w:007 c:0034](:h for help)",
        )

        self.call(
            eveditor.CmdEditorGroup(),
            "Second",
            cmdstring=":dw",  # delete by word
            msg="Removed Second for lines 1-4.",
        )
        self.call(eveditor.CmdEditorGroup(), "", cmdstring=":u", msg="Undid one step.")  # undo
        self.call(
            eveditor.CmdEditorGroup(),
            "2 Second",
            cmdstring=":dw",  # delete by word/line
            msg="Removed Second for line 2.",
        )
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "First test line\n test line\n:")

        self.call(
            eveditor.CmdEditorGroup(), "2", cmdstring=":p", msg="Copy buffer is empty."  # paste
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "2",
            cmdstring=":y",  # yank
            msg="Line 2, [' test line'] yanked.",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "2",
            cmdstring=":p",  # paste
            msg="Pasted buffer [' test line'] to line 2.",
        )
        self.assertEqual(
            self.char1.ndb._eveditor.get_buffer(), "First test line\n test line\n test line\n:"
        )

        self.call(
            eveditor.CmdEditorGroup(), "3", cmdstring=":x", msg="Line 3, [' test line'] cut."  # cut
        )

        self.call(
            eveditor.CmdEditorGroup(),
            "2 New Second line",
            cmdstring=":i",  # insert
            msg="Inserted 1 new line(s) at line 2.",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "2 New Replaced Second line",  # replace
            cmdstring=":r",
            msg="Replaced 1 line(s) at line 2.",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "2 Inserted-",  # insert beginning line
            cmdstring=":I",
            msg="Inserted text at beginning of line 2.",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "2 -End",  # append end line
            cmdstring=":A",
            msg="Appended text to end of line 2.",
        )

        self.assertEqual(
            self.char1.ndb._eveditor.get_buffer(),
            "First test line\nInserted-New Replaced Second line-End\n test line\n:",
        )

    def test_eveditor_COLON_UU(self):
        eveditor.EvEditor(self.char1)
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            cmdstring=":",
            msg="Line Editor []\n01\n[l:01 w:000 c:0000](:h for help)",
        )
        self.call(
            eveditor.CmdLineInput(),
            'First test "line".',
            raw_string='First test "line".',
            msg='01First test "line" .',
        )
        self.call(
            eveditor.CmdLineInput(),
            "Second 'line'.",
            raw_string="Second 'line'.",
            msg="02Second 'line' .",
        )
        self.assertEqual(
            self.char1.ndb._eveditor.get_buffer(), "First test \"line\".\nSecond 'line'."
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            cmdstring=":UU",
            msg="Reverted all changes to the buffer back to original state.",
        )
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "")

    def test_eveditor_search_and_replace(self):
        eveditor.EvEditor(self.char1)
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            cmdstring=":",
            msg="Line Editor []\n01\n[l:01 w:000 c:0000](:h for help)",
        )
        self.call(eveditor.CmdLineInput(), "line 1.", raw_string="line 1.", msg="01line 1.")
        self.call(eveditor.CmdLineInput(), "line 2.", raw_string="line 2.", msg="02line 2.")
        self.call(eveditor.CmdLineInput(), "line 3.", raw_string="line 3.", msg="03line 3.")
        self.call(
            eveditor.CmdEditorGroup(),
            "2:3",
            cmdstring=":",
            msg="Line Editor []\n02line 2.\n03line 3.\n[l:02 w:004 c:0015](:h for help)",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "1:2 line LINE",
            cmdstring=":s",
            msg="Search-replaced line -> LINE for lines 1-2.",
        )
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "LINE 1.\nLINE 2.\nline 3.")
        self.call(
            eveditor.CmdEditorGroup(),
            "line MINE",
            cmdstring=":s",
            msg="Search-replaced line -> MINE for lines 1-3.",
        )
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "LINE 1.\nLINE 2.\nMINE 3.")

    def test_eveditor_COLON_DD(self):
        eveditor.EvEditor(self.char1)
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            cmdstring=":",
            msg="Line Editor []\n01\n[l:01 w:000 c:0000](:h for help)",
        )
        self.call(eveditor.CmdLineInput(), "line 1.", raw_string="line 1.", msg="01line 1.")
        self.call(eveditor.CmdLineInput(), "line 2.", raw_string="line 2.", msg="02line 2.")
        self.call(eveditor.CmdLineInput(), "line 3.", raw_string="line 3.", msg="03line 3.")
        self.call(
            eveditor.CmdEditorGroup(), "", cmdstring=":DD", msg="Cleared 3 lines from buffer."
        )
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "")

    def test_eveditor_COLON_F(self):
        eveditor.EvEditor(self.char1)
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            cmdstring=":",
            msg="Line Editor []\n01\n[l:01 w:000 c:0000](:h for help)",
        )
        self.call(eveditor.CmdLineInput(), "line 1", raw_string="line 1", msg="01line 1")
        self.call(eveditor.CmdEditorGroup(), "1:2", cmdstring=":f", msg="Flood filled lines 1-2.")
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "line 1")

    def test_eveditor_COLON_J(self):
        eveditor.EvEditor(self.char1)
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            cmdstring=":",
            msg="Line Editor []\n01\n[l:01 w:000 c:0000](:h for help)",
        )
        self.call(eveditor.CmdLineInput(), "line 1", raw_string="line 1", msg="01line 1")
        self.call(eveditor.CmdLineInput(), "l 2", raw_string="l 2", msg="02l 2")
        self.call(eveditor.CmdLineInput(), "l 3", raw_string="l 3", msg="03l 3")
        self.call(eveditor.CmdLineInput(), "l 4", raw_string="l 4", msg="04l 4")
        self.call(eveditor.CmdEditorGroup(), "2 r", cmdstring=":j", msg="Right-justified line 2.")
        self.call(eveditor.CmdEditorGroup(), "3 c", cmdstring=":j", msg="Center-justified line 3.")
        self.call(eveditor.CmdEditorGroup(), "4 f", cmdstring=":j", msg="Full-justified line 4.")
        l1, l2, l3, l4 = tuple(self.char1.ndb._eveditor.get_buffer().split("\n"))
        self.assertEqual(l1, "line 1")
        self.assertEqual(l2, " " * 75 + "l 2")
        self.assertEqual(l3, " " * 37 + "l 3" + " " * 38)
        self.assertEqual(l4, "l" + " " * 76 + "4")

    def test_eveditor_bad_commands(self):
        eveditor.EvEditor(self.char1)
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            cmdstring=":",
            msg="Line Editor []\n01\n[l:01 w:000 c:0000](:h for help)",
        )
        self.call(eveditor.CmdLineInput(), "line 1.", raw_string="line 1.", msg="01line 1.")
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            cmdstring=":dw",
            msg="You must give a search word to delete.",
        )
        # self.call(
        #     eveditor.CmdEditorGroup(),
        #     raw_string="",
        #     cmdstring=":i",
        #     msg="You need to enter a new line and where to insert it.",
        # )
        # self.call(
        #     eveditor.CmdEditorGroup(),
        #     "",
        #     cmdstring=":I",
        #     msg="You need to enter text to insert.",
        # )
        # self.call(
        #     eveditor.CmdEditorGroup(),
        #     "",
        #     cmdstring=":r",
        #     msg="You need to enter a replacement string.",
        # )
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            cmdstring=":s",
            msg="You must give a search word and something to replace it with.",
        )
        # self.call(
        #     eveditor.CmdEditorGroup(),
        #     "",
        #     cmdstring=":f",
        #     msg="Valid justifications are [f]ull (default), [c]enter, [r]right or [l]eft"
        # )
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "line 1.")
