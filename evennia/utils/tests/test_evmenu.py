"""
Unit tests for the EvMenu system

TODO: This need expansion.

"""

from django.test import TestCase
from evennia.utils import evmenu
from mock import Mock


class TestEvMenu(TestCase):
    "Run the EvMenu testing."

    def setUp(self):
        self.caller = Mock()
        self.caller.msg = Mock()
        self.menu = evmenu.EvMenu(self.caller, "evennia.utils.evmenu", startnode="test_start_node",
                                  persistent=True, cmdset_mergetype="Replace", testval="val",
                                  testval2="val2")

    def test_kwargsave(self):
        self.assertTrue(hasattr(self.menu, "testval"))
        self.assertTrue(hasattr(self.menu, "testval2"))
