"""
Testing of TestDice.

"""

from mock import patch

from evennia.commands.default.tests import BaseEvenniaCommandTest

from . import dice


@patch("evennia.contrib.rpg.dice.dice.randint", return_value=5)
class TestDice(BaseEvenniaCommandTest):
    def test_roll_dice(self, mocked_randint):
        self.assertEqual(dice.roll(6, 6, modifier=("+", 4)), mocked_randint() * 6 + 4)
        self.assertEqual(dice.roll(6, 6, conditional=("<", 35)), True)
        self.assertEqual(dice.roll(6, 6, conditional=(">", 33)), False)

    def test_cmddice(self, mocked_randint):
        self.call(
            dice.CmdDice(), "3d6 + 4", "You roll 3d6 + 4.| Roll(s): 5, 5 and 5. Total result is 19."
        )
        self.call(dice.CmdDice(), "100000d1000", "The maximum roll allowed is 10000d10000.")
        self.call(dice.CmdDice(), "/secret 3d6 + 4", "You roll 3d6 + 4 (secret, not echoed).")

    def test_string_form(self, mocked_randint):
        self.assertEqual(dice.roll("6d6 + 4"), mocked_randint() * 6 + 4)
        self.assertEqual(dice.roll("6d6 < 35"), True)
        self.assertEqual(dice.roll("6d6 > 35"), False)
        self.assertEqual(dice.roll("2d10 + 5 >= 14"), True)

    def test_maxvals(self, mocked_randint):
        with self.assertRaises(TypeError):
            dice.roll(11, 1001, max_dicenum=10, max_dicetype=1000)
        with self.assertRaises(TypeError):
            dice.roll(10, 1001, max_dicenum=10, max_dicetype=1000)
