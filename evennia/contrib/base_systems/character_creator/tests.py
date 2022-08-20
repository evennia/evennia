from django.test import override_settings
from evennia.utils import inherits_from
from evennia.utils.test_resources import BaseEvenniaCommandTest
from . import character_creator

class TestAccount(BaseEvenniaCommandTest):
    def test_ooc_look(self):
        if settings.MULTISESSION_MODE < 2:
            self.call(
                account.CmdOOCLook(), "", "You are out-of-character (OOC).", caller=self.account
            )
        if settings.MULTISESSION_MODE == 2:
            # test both normal output and also inclusion of in-progress character
            account.db._playable_characters = [self.char1]
            self.char1.db.chargen_step = "start"
            output = self.call(
                account.CmdOOCLook(),
                "",
                "Account TestAccount (you are Out-of-Character)",
                caller=self.account,
            )
            self.assertIn("|Yin progress|n", output)

    @override_settings(CHARGEN_MENU="evennia.contrib.base_systems.example_menu")
    def test_char_create(self):
        account = self.account
        session = self.session
        self.call(
            character_creator.ContribCmdCharCreate(),
            "",
            caller=account,
        )
        menu = session.ndb._menutree
        self.assertNotNone(menu)
        self.assertTrue(inherits_from(session.new_char, DefaultCharacter) )
