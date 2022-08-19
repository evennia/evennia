from evennia.utils.test_resources import (
    BaseEvenniaTest,
    BaseEvenniaCommandTest,
    EvenniaCommandTest,
)  # noqa
from . import character_creator

class TestAccount(BaseEvenniaCommandTest):
    def test_ooc_look(self):
        if settings.MULTISESSION_MODE < 2:
            self.call(
                account.CmdOOCLook(), "", "You are out-of-character (OOC).", caller=self.account
            )
        if settings.MULTISESSION_MODE == 2:
						# with no playable characters
            self.call(
                account.CmdOOCLook(),
                "",
                "Account TestAccount (you are Out-of-Character)",
                caller=self.account,
            )
						# with in-progress character


    def test_char_create(self):
        self.call(
            character_creator.ContribCmdCharCreate(),
            "Test1=Test char",
            "Created new character Test1. Use ic Test1 to enter the game",
            caller=self.account,
        )

