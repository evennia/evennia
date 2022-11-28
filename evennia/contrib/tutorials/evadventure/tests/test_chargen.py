"""
Test chargen.

"""

from unittest.mock import MagicMock, patch

from parameterized import parameterized

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from .. import chargen, enums, objects


class EvAdventureCharacterGenerationTest(BaseEvenniaTest):
    """
    Test the Character generator in the rule engine.

    """

    @patch("evennia.contrib.tutorials.evadventure.rules.randint")
    def setUp(self, mock_randint):
        super().setUp()
        mock_randint.return_value = 10
        self.chargen = chargen.TemporaryCharacterSheet()

    def test_base_chargen(self):
        self.assertEqual(self.chargen.strength, 10)  # not realistic, due to mock
        self.assertEqual(self.chargen.armor, "gambeson")
        self.assertEqual(self.chargen.shield, "shield")
        self.assertEqual(
            self.chargen.backpack, ["ration", "ration", "waterskin", "waterskin", "drill", "twine"]
        )

    def test_build_desc(self):
        self.assertEqual(
            self.chargen.desc,
            "You are scrawny with a broken face, pockmarked skin, greased hair, hoarse speech, and "
            "stained clothing. You were a Herbalist, but you were exiled and ended up a knave. You "
            "are honest but also irascible. You tend towards neutrality.",
        )

    @patch("evennia.contrib.tutorials.evadventure.chargen.spawn")
    def test_apply(self, mock_spawn):

        gambeson = create_object(objects.EvAdventureArmor, key="gambeson")
        mock_spawn.return_value = [gambeson]
        account = MagicMock()
        account.id = 2222

        character = self.chargen.apply(account)

        self.assertIn("Herbalist", character.db.desc)
        self.assertEqual(
            character.equipment.all(),
            [
                (None, enums.WieldLocation.WEAPON_HAND),
                (None, enums.WieldLocation.SHIELD_HAND),
                (None, enums.WieldLocation.TWO_HANDS),
                (gambeson, enums.WieldLocation.BODY),
                (None, enums.WieldLocation.HEAD),
            ],
        )

        gambeson.delete()
        character.delete()
