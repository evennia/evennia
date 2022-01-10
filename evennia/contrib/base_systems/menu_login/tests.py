"""
Test menu_login

"""

from evennia.commands.default.tests import EvenniaCommandTest
from . import menu_login


class TestMenuLogin(EvenniaCommandTest):
    def test_cmdunloggedlook(self):
        self.call(menu_login.CmdUnloggedinLook(), "", "======")
