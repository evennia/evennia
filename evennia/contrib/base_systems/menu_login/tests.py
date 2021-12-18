"""
Test menu_login

"""

from evennia.commands.default.tests import CommandTest
from . import menu_login


class TestMenuLogin(CommandTest):
    def test_cmdunloggedlook(self):
        self.call(menu_login.CmdUnloggedinLook(), "", "======")
