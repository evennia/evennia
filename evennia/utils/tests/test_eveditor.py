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
        self.call(eveditor.CmdEditorGroup(), "", cmdstring=":h",
                  msg="<txt>  - any non-command is appended to the end of the buffer.")
        # empty buffer
        self.call(eveditor.CmdEditorGroup(), "", cmdstring=":",
                  msg="Line Editor []\n01\n[l:01 w:000 c:0000](:h for help)")
        # input a string
        self.call(eveditor.CmdLineInput(), "First test line", raw_string="First test line",
                  msg="01First test line")
        self.call(eveditor.CmdLineInput(), "Second test line", raw_string="Second test line",
                  msg="02Second test line")
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(), 'First test line\nSecond test line')

        self.call(eveditor.CmdEditorGroup(), "", cmdstring=":",  # view buffer
                  msg="Line Editor []\n01First test line\n"
                      "02Second test line\n[l:02 w:006 c:0032](:h for help)")
        self.call(eveditor.CmdEditorGroup(), "", cmdstring="::",  # view buffer, no linenums
                  msg="Line Editor []\nFirst test line\n"
                      "Second test line\n[l:02 w:006 c:0032](:h for help)")
        self.call(eveditor.CmdEditorGroup(), "", cmdstring=":::",  # add single : alone on row
                  msg="Single ':' added to buffer.")
        self.call(eveditor.CmdEditorGroup(), "", cmdstring=":",
                  msg="Line Editor []\n01First test line\n"
                      "02Second test line\n03:\n[l:03 w:007 c:0034](:h for help)")

        self.call(eveditor.CmdEditorGroup(), "", cmdstring=":dd",  # delete line
                  msg="Deleted line 3.")
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(),
                         'First test line\nSecond test line')
        self.call(eveditor.CmdEditorGroup(), "", cmdstring=":u",  # undo
                  msg="Undid one step.")
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(),
                         'First test line\nSecond test line\n:')
        self.call(eveditor.CmdEditorGroup(), "", cmdstring=":uu",  # redo
                  msg="Redid one step.")
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(),
                         'First test line\nSecond test line')
        self.call(eveditor.CmdEditorGroup(), "", cmdstring=":u",  # undo
                  msg="Undid one step.")
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(),
                         'First test line\nSecond test line\n:')
        self.call(eveditor.CmdEditorGroup(), "", cmdstring=":",
                  msg="Line Editor []\n01First test line\n"
                      "02Second test line\n03:\n[l:03 w:007 c:0034](:h for help)")

        self.call(eveditor.CmdEditorGroup(), "Second", cmdstring=":dw",  # delete by word
                  msg="Removed Second for lines 1-4.")
        self.call(eveditor.CmdEditorGroup(), "", cmdstring=":u",  # undo
                  msg="Undid one step.")
        self.call(eveditor.CmdEditorGroup(), "2 Second", cmdstring=":dw",  # delete by word/line
                  msg="Removed Second for line 2.")
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(),
                         'First test line\n test line\n:')


        self.call(eveditor.CmdEditorGroup(), "2", cmdstring=":p",  # paste
                  msg="Copy buffer is empty.")
        self.call(eveditor.CmdEditorGroup(), "2", cmdstring=":y",  # yank
                  msg="Line 2, [' test line'] yanked.")
        self.call(eveditor.CmdEditorGroup(), "2", cmdstring=":p",  # paste
                  msg="Pasted buffer [' test line'] to line 2.")
        self.assertEqual(self.char1.ndb._eveditor.get_buffer(),
                         'First test line\n test line\n test line\n:')

        self.call(eveditor.CmdEditorGroup(), "3", cmdstring=":x",  # cut
                  msg="Line 3, [' test line'] cut.")

        self.call(eveditor.CmdEditorGroup(), "2 New Second line", cmdstring=":i",  # insert
                  msg="Inserted 1 new line(s) at line 2.")
        self.call(eveditor.CmdEditorGroup(), "2 New Replaced Second line",  # replace
                  cmdstring=":r", msg="Replaced 1 line(s) at line 2.")
        self.call(eveditor.CmdEditorGroup(), "2 Inserted-",  # insert beginning line
                  cmdstring=":I", msg="Inserted text at beginning of line 2.")
        self.call(eveditor.CmdEditorGroup(), "2 -End",  # append end line
                  cmdstring=":A", msg="Appended text to end of line 2.")

        self.assertEqual(
            self.char1.ndb._eveditor.get_buffer(),
            'First test line\nInserted-New Replaced Second line-End\n test line\n:')
