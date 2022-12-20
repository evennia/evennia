"""
Test menu_login

"""

from evennia.commands.default.tests import BaseEvenniaCommandTest

from . import menu_login


class TestMenuLogin(BaseEvenniaCommandTest):
    def test_cmdunloggedlook(self):
        self.call(menu_login.CmdUnloggedinLook(), "", "======")
