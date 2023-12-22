from evennia import DefaultCharacter
from evennia.utils import inherits_from
from evennia.utils.test_resources import BaseEvenniaCommandTest

from . import character_creator


class TestCharacterCreator(BaseEvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.account.swap_typeclass(character_creator.ContribChargenAccount)
        self.account.unpuppet_all()

    def test_account_look(self):
        self.account.characters.add(self.char1)
        self.char1.db.chargen_step = "start"

        # check that correct output is returning
        output = self.account.at_look(target=self.account.characters.all(), session=self.session)
        # check that char1 is recognized as in progress
        self.assertIn("in progress", output)

    def test_char_create(self):
        with self.settings(START_LOCATION=f"#{self.room1.id}"):
            self.call(
                character_creator.ContribCmdCharCreate(),
                "",
                caller=self.account,
            )
        # verify menu was initialized
        menu = self.session.ndb._menutree
        self.assertNotEqual(menu, None)
        # verify character was created
        new_char = self.session.new_char
        self.assertTrue(inherits_from(new_char, DefaultCharacter))
        # verify character's "start location" was set
        self.assertEqual(self.session.new_char.db.prelogout_location, self.room1)

        # exit the menu, verify it resumes
        menu.parse_input("q")
        del self.session.new_char
        self.assertEqual(self.session.ndb._menutree, None)
        self.call(
            character_creator.ContribCmdCharCreate(),
            "",
            caller=self.account,
        )
        # should be the same new char
        self.assertEqual(new_char, self.session.new_char)
