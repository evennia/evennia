"""
Test eveditor

"""

from evennia.commands.default.tests import BaseEvenniaCommandTest
from evennia.utils import eveditor


class TestEvEditor(BaseEvenniaCommandTest):
    def test_eveditor_ranges(self):
        eveditor.EvEditor(self.char1)
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            raw_string=":",
            msg="Line Editor []\n01\n[l:01 w:000 c:0000](:h for help)",
        )
        self.call(eveditor.CmdLineInput(), "line 1", raw_string="line 1", msg="01line 1")
        self.call(eveditor.CmdLineInput(), "line 2", raw_string="line 2", msg="02line 2")
        self.call(eveditor.CmdLineInput(), "line 3", raw_string="line 3", msg="03line 3")
        self.call(eveditor.CmdLineInput(), "line 4", raw_string="line 4", msg="04line 4")
        self.call(eveditor.CmdLineInput(), "line 5", raw_string="line 5", msg="05line 5")
        self.call(
            eveditor.CmdEditorGroup(),
            "",  # list whole buffer
            raw_string=":",
            msg="Line Editor []\n01line 1\n02line 2\n"
            "03line 3\n04line 4\n05line 5\n"
            "[l:05 w:010 c:0034](:h for help)",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            ":",  # list empty range
            raw_string=":",
            msg="Line Editor []\n01line 1\n02line 2\n"
            "03line 3\n04line 4\n05line 5\n"
            "[l:05 w:010 c:0034](:h for help)",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            ":4",  # list from start to line 4
            raw_string=":",
            msg="Line Editor []\n01line 1\n02line 2\n"
            "03line 3\n04line 4\n"
            "[l:04 w:008 c:0027](:h for help)",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "2:",  # list from line 2 to end
            raw_string=":",
            msg="Line Editor []\n02line 2\n03line 3\n"
            "04line 4\n05line 5\n"
            "[l:04 w:008 c:0027](:h for help)",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "-10:10",  # try to list invalid range (too large)
            raw_string=":",
            msg="Line Editor []\n01line 1\n02line 2\n"
            "03line 3\n04line 4\n05line 5\n"
            "[l:05 w:010 c:0034](:h for help)",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "3:1",  # try to list invalid range (reversed)
            raw_string=":",
            msg="Line Editor []\n03line 3\n" "[l:01 w:002 c:0006](:h for help)",
        )

    def test_eveditor_view_cmd(self):
        eveditor.EvEditor(self.char1)
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            raw_string=":h",
            msg="<txt>  - any non-command is appended to the end of the buffer.",
        )
        # empty buffer
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            raw_string=":",
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
            raw_string=":",  # view buffer
            msg="Line Editor []\n01First test line\n"
            "02Second test line\n[l:02 w:006 c:0032](:h for help)",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            raw_string="::",  # view buffer, no linenums
            msg="Line Editor []\nFirst test line\n"
            "Second test line\n[l:02 w:006 c:0032](:h for help)",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            raw_string=":::",  # add single : alone on row
            msg="Single ':' added to buffer.",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            raw_string=":",
            msg="Line Editor []\n01First test line\n"
            "02Second test line\n03:\n[l:03 w:007 c:0034](:h for help)",
        )

        self.call(
            eveditor.CmdEditorGroup(), "", raw_string=":dd", msg="Deleted line 3."  # delete line
        )
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "First test line\nSecond test line")
        self.call(eveditor.CmdEditorGroup(), "", raw_string=":u", msg="Undid one step.")  # undo
        self.assertEqual(
            self.char1.ndb._eveditor.get_buffer(), "First test line\nSecond test line\n:"
        )
        self.call(eveditor.CmdEditorGroup(), "", raw_string=":uu", msg="Redid one step.")  # redo
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "First test line\nSecond test line")
        self.call(eveditor.CmdEditorGroup(), "", raw_string=":u", msg="Undid one step.")  # undo
        self.assertEqual(
            self.char1.ndb._eveditor.get_buffer(), "First test line\nSecond test line\n:"
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            raw_string=":",
            msg="Line Editor []\n01First test line\n"
            "02Second test line\n03:\n[l:03 w:007 c:0034](:h for help)",
        )

        self.call(
            eveditor.CmdEditorGroup(),
            "Second",
            raw_string=":dw",  # delete by word
            msg="Removed Second for lines 1-4.",
        )
        self.call(eveditor.CmdEditorGroup(), "", raw_string=":u", msg="Undid one step.")  # undo
        self.call(
            eveditor.CmdEditorGroup(),
            "2 Second",
            raw_string=":dw",  # delete by word/line
            msg="Removed Second for line 2.",
        )
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "First test line\n test line\n:")

        self.call(
            eveditor.CmdEditorGroup(), "2", raw_string=":p", msg="Copy buffer is empty."  # paste
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "2",
            raw_string=":y",  # yank
            msg="Line 2, [' test line'] yanked.",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "2",
            raw_string=":p",  # paste
            msg="Pasted buffer [' test line'] to line 2.",
        )
        self.assertEqual(
            self.char1.ndb._eveditor.get_buffer(), "First test line\n test line\n test line\n:"
        )

        self.call(
            eveditor.CmdEditorGroup(),
            "3",
            raw_string=":x",
            msg="Line 3, [' test line'] cut.",  # cut
        )

        self.call(
            eveditor.CmdEditorGroup(),
            "2 New Second line",
            raw_string=":i",  # insert
            msg="Inserted 1 new line(s) at line 2.",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "2 New Replaced Second line",  # replace
            raw_string=":r",
            msg="Replaced 1 line(s) at line 2.",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "2 Inserted-",  # insert beginning line
            raw_string=":I",
            msg="Inserted text at beginning of line 2.",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "2 -End",  # append end line
            raw_string=":A",
            msg="Appended text to end of line 2.",
        )

        self.assertEqual(
            self.char1.ndb._eveditor.get_buffer(),
            "First test line\nInserted-New Replaced Second line-End\n test line\n:",
        )

        self.call(
            eveditor.CmdLineInput(),
            "  Whitespace   echo    test     line.",
            raw_string="  Whitespace   echo    test     line.",
            msg="05  Whitespace   echo    test     line.",
        )

    def test_eveditor_COLON_UU(self):
        eveditor.EvEditor(self.char1)
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            raw_string=":",
            msg="Line Editor []\n01\n[l:01 w:000 c:0000](:h for help)",
        )
        self.call(
            eveditor.CmdLineInput(),
            'First test "line".',
            raw_string='First test "line".',
            msg='01First test "line".',
        )
        self.call(
            eveditor.CmdLineInput(),
            "Second 'line'.",
            raw_string="Second 'line'.",
            msg="02Second 'line'.",
        )
        self.assertEqual(
            self.char1.ndb._eveditor.get_buffer(), "First test \"line\".\nSecond 'line'."
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            raw_string=":UU",
            msg="Reverted all changes to the buffer back to original state.",
        )
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "")

    def test_eveditor_search_and_replace(self):
        eveditor.EvEditor(self.char1)
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            raw_string=":",
            msg="Line Editor []\n01\n[l:01 w:000 c:0000](:h for help)",
        )
        self.call(eveditor.CmdLineInput(), "line 1.", raw_string="line 1.", msg="01line 1.")
        self.call(eveditor.CmdLineInput(), "line 2.", raw_string="line 2.", msg="02line 2.")
        self.call(eveditor.CmdLineInput(), "line 3.", raw_string="line 3.", msg="03line 3.")
        self.call(
            eveditor.CmdEditorGroup(),
            "2:3",
            raw_string=":",
            msg="Line Editor []\n02line 2.\n03line 3.\n[l:02 w:004 c:0015](:h for help)",
        )
        self.call(
            eveditor.CmdEditorGroup(),
            "1:2 line LINE",
            raw_string=":s",
            msg="Search-replaced line -> LINE for lines 1-2.",
        )
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "LINE 1.\nLINE 2.\nline 3.")
        self.call(
            eveditor.CmdEditorGroup(),
            "line MINE",
            raw_string=":s",
            msg="Search-replaced line -> MINE for lines 1-3.",
        )
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "LINE 1.\nLINE 2.\nMINE 3.")

    def test_eveditor_COLON_DD(self):
        eveditor.EvEditor(self.char1)
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            raw_string=":",
            msg="Line Editor []\n01\n[l:01 w:000 c:0000](:h for help)",
        )
        self.call(eveditor.CmdLineInput(), "line 1.", raw_string="line 1.", msg="01line 1.")
        self.call(eveditor.CmdLineInput(), "line 2.", raw_string="line 2.", msg="02line 2.")
        self.call(eveditor.CmdLineInput(), "line 3.", raw_string="line 3.", msg="03line 3.")
        self.call(
            eveditor.CmdEditorGroup(), "", raw_string=":DD", msg="Cleared 3 lines from buffer."
        )
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "")

    def test_eveditor_COLON_F(self):
        eveditor.EvEditor(self.char1)
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            raw_string=":",
            msg="Line Editor []\n01\n[l:01 w:000 c:0000](:h for help)",
        )
        self.call(eveditor.CmdLineInput(), "line 1", raw_string="line 1", msg="01line 1")
        self.call(eveditor.CmdEditorGroup(), "1:2", raw_string=":f", msg="Flood filled line 1.")
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "line 1")

    def test_eveditor_COLON_J(self):
        eveditor.EvEditor(self.char1)
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            raw_string=":",
            msg="Line Editor []\n01\n[l:01 w:000 c:0000](:h for help)",
        )
        self.call(eveditor.CmdLineInput(), "line 1", raw_string="line 1", msg="01line 1")
        self.call(eveditor.CmdLineInput(), "l 2", raw_string="l 2", msg="02l 2")
        self.call(eveditor.CmdLineInput(), "l 3", raw_string="l 3", msg="03l 3")
        self.call(eveditor.CmdLineInput(), "l 4", raw_string="l 4", msg="04l 4")
        self.call(eveditor.CmdEditorGroup(), "2 r", raw_string=":j", msg="Right-justified line 2.")
        self.call(eveditor.CmdEditorGroup(), "3 c", raw_string=":j", msg="Center-justified line 3.")
        self.call(eveditor.CmdEditorGroup(), "4 f", raw_string=":j", msg="Full-justified line 4.")
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
            raw_string=":",
            msg="Line Editor []\n01\n[l:01 w:000 c:0000](:h for help)",
        )
        self.call(eveditor.CmdLineInput(), "line 1.", raw_string="line 1.", msg="01line 1.")
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            raw_string=":dw",
            msg="You must give a search word to delete.",
        )
        # self.call(
        #     eveditor.CmdEditorGroup(),
        #     raw_string="",
        #     raw_string=":i",
        #     msg="You need to enter a new line and where to insert it.",
        # )
        # self.call(
        #     eveditor.CmdEditorGroup(),
        #     "",
        #     raw_string=":I",
        #     msg="You need to enter text to insert.",
        # )
        # self.call(
        #     eveditor.CmdEditorGroup(),
        #     "",
        #     raw_string=":r",
        #     msg="You need to enter a replacement string.",
        # )
        self.call(
            eveditor.CmdEditorGroup(),
            "",
            raw_string=":s",
            msg="You must give a search word and something to replace it with.",
        )
        # self.call(
        #     eveditor.CmdEditorGroup(),
        #     "",
        #     raw_string=":f",
        #     msg="Valid justifications are [f]ull (default), [c]enter, [r]right or [l]eft"
        # )
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), "line 1.")
