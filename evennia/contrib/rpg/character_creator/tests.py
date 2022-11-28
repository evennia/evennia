from unittest.mock import patch

from django.conf import settings
from django.test import override_settings

from evennia import DefaultCharacter
from evennia.commands.default import account
from evennia.utils import inherits_from
from evennia.utils.test_resources import BaseEvenniaCommandTest

from . import character_creator


class TestCharacterCreator(BaseEvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.account.swap_typeclass(character_creator.ContribChargenAccount)

    def test_ooc_look(self):
        self.account.db._playable_characters = [self.char1]
        self.account.unpuppet_all()

        self.char1.db.chargen_step = "start"

        with patch("evennia.commands.default.account._AUTO_PUPPET_ON_LOGIN", new=False):
            # check that correct output is returning
            output = self.call(
                account.CmdOOCLook(),
                "",
                "Account TestAccount (you are Out-of-Character)",
                caller=self.account,
            )
            # check that char1 is recognized as in progress
            self.assertIn("in progress", output)

    @override_settings(CHARGEN_MENU="evennia.contrib.rpg.character_creator.example_menu")
    def test_char_create(self):
        self.call(
            character_creator.ContribCmdCharCreate(),
            "",
            caller=self.account,
        )
        menu = self.session.ndb._menutree
        self.assertNotEqual(menu, None)
        self.assertTrue(inherits_from(self.session.new_char, DefaultCharacter))
