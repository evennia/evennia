"""
Test gendersub contrib.

"""


from mock import patch

from evennia.commands.default.tests import BaseEvenniaCommandTest
from evennia.utils.create import create_object

from . import gendersub


class TestGenderSub(BaseEvenniaCommandTest):
    def test_setgender(self):
        self.call(gendersub.SetGender(), "male", "Your gender was set to male.")
        self.call(gendersub.SetGender(), "ambiguous", "Your gender was set to ambiguous.")
        self.call(gendersub.SetGender(), "Foo", "Usage: @gender")

    def test_gendercharacter(self):
        char = create_object(gendersub.GenderCharacter, key="Gendered", location=self.room1)
        txt = "Test |p gender"
        self.assertEqual(
            gendersub._RE_GENDER_PRONOUN.sub(char._get_pronoun, txt), "Test their gender"
        )
        with patch(
            "evennia.contrib.game_systems.gendersub.gendersub.DefaultCharacter.msg"
        ) as mock_msg:
            char.db.gender = "female"
            char.msg("Test |p gender")
            mock_msg.assert_called_with("Test her gender", from_obj=None, session=None)
