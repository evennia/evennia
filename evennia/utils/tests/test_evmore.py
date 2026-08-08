"""
Unit and integration tests for the EvMore pager system.
"""

from evennia.commands.default.tests import BaseEvenniaCommandTest
from evennia.utils import evmore


class TestEvMore(BaseEvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.text = "\n".join([f"Line {i}" for i in range(1, 100)])

    def test_evmore_quit_commands(self):
        """Test that 'quit', 'q', 'abort', and 'a' exit the pager."""
        for quit_cmd in ("quit", "q", "abort", "a"):
            evmore.EvMore(self.char1, self.text, always_page=True)
            self.assertIsNotNone(self.char1.ndb._more)
            self.call(evmore.CmdMore(), "", cmdstring=quit_cmd)
            self.assertIsNone(self.char1.ndb._more)

    def test_evmore_navigation_commands(self):
        """Test pager navigation commands: next, previous, top, end."""
        pager = evmore.EvMore(self.char1, self.text, always_page=True)
        self.assertEqual(pager._npos, 0)

        # Next page
        self.call(evmore.CmdMore(), "", cmdstring="next")
        self.assertEqual(pager._npos, 1)

        # Top page
        self.call(evmore.CmdMore(), "", cmdstring="top")
        self.assertEqual(pager._npos, 0)

        # End page
        self.call(evmore.CmdMore(), "", cmdstring="end")
        self.assertEqual(pager._npos, pager._npages - 1)

        # Previous page
        self.call(evmore.CmdMore(), "", cmdstring="previous")
        self.assertEqual(pager._npos, pager._npages - 2)
