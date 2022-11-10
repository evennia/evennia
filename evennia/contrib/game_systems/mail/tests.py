"""
Test mail contrib

"""

from evennia.commands.default.tests import BaseEvenniaCommandTest

from . import mail


class TestMail(BaseEvenniaCommandTest):
    def test_mail(self):
        self.call(mail.CmdMail(), "2", "'2' is not a valid mail id.", caller=self.account)
        self.call(mail.CmdMail(), "test", "'test' is not a valid mail id.", caller=self.account)
        self.call(mail.CmdMail(), "", "There are no messages in your inbox.", caller=self.account)
        self.call(
            mail.CmdMailCharacter(),
            "Char=Message 1",
            "You have received a new @mail from Char|You sent your message.",
            caller=self.char1,
        )
        self.call(
            mail.CmdMailCharacter(), "Char=Message 2", "You sent your message.", caller=self.char2
        )
        self.call(
            mail.CmdMail(),
            "TestAccount2=Message 2",
            "You have received a new @mail from TestAccount2",
            caller=self.account2,
        )
        self.call(
            mail.CmdMail(), "TestAccount=Message 1", "You sent your message.", caller=self.account2
        )
        self.call(
            mail.CmdMail(), "TestAccount=Message 2", "You sent your message.", caller=self.account2
        )
        self.call(mail.CmdMail(), "", "| ID    From              Subject", caller=self.account)
        self.call(mail.CmdMail(), "2", "From: TestAccount2", caller=self.account)
        self.call(
            mail.CmdMail(),
            "/forward TestAccount2 = 1/Forward message",
            "You sent your message.|Message forwarded.",
            caller=self.account,
        )
        self.call(
            mail.CmdMail(), "/reply 2=Reply Message2", "You sent your message.", caller=self.account
        )
        self.call(mail.CmdMail(), "/delete 2", "Message 2 deleted", caller=self.account)
