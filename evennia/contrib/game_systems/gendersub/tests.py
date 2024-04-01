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
            char.msg(txt)
            mock_msg.assert_called_with("Test her gender", from_obj=None, session=None)

    def test_gendering_others(self):
        """ensure characters see the gender of the sender, not themselves"""
        fem = create_object(
            gendersub.GenderCharacter,
            key="Gendered",
            location=self.room2,
            attributes=[("gender", "female")],
        )
        masc = create_object(
            gendersub.GenderCharacter,
            key="Gendered",
            location=self.room2,
            attributes=[("gender", "male")],
        )
        txt = "Test |p gender"

        with patch(
            "evennia.contrib.game_systems.gendersub.gendersub.DefaultCharacter.msg"
        ) as mock_msg:
            fem.msg(txt, from_obj=masc)
            self.assertIn("Test his gender", mock_msg.call_args.args)
            masc.msg(txt, from_obj=fem)
            self.assertIn("Test her gender", mock_msg.call_args.args)

    def test_ungendered_source(self):
        char = create_object(gendersub.GenderCharacter, key="Gendered", location=self.room1)
        txt = "Test |p gender"
        with patch(
            "evennia.contrib.game_systems.gendersub.gendersub.DefaultCharacter.msg"
        ) as mock_msg:
            char.msg(txt, from_obj=self.char1)
            self.assertIn("Test their gender", mock_msg.call_args.args)
