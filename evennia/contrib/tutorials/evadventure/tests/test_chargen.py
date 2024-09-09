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

    @patch("evennia.contrib.tutorials.evadventure.rules.randint")
    def test_base_chargen(self, mock_randint):
        mock_randint.return_value = 17
        self.assertEqual(self.chargen.strength, 17)  # not realistic, due to mock
        self.assertEqual(self.chargen.armor, "brigandine")
        self.assertEqual(self.chargen.shield, "shield")
        self.assertEqual(
            self.chargen.backpack, ["ration", "ration", "tent", "tent", "lockpicks", "soap"]
        )

    @patch("evennia.contrib.tutorials.evadventure.rules.randint")
    def test_base_chargen_armor_and_shield_None(self, mock_randint):
        mock_randint.return_value = 3
        self.chargen = chargen.TemporaryCharacterSheet()
        self.assertEqual(self.chargen.strength, 3)
        self.assertEqual(self.chargen.armor, None)
        self.assertEqual(self.chargen.shield, None)
        self.assertEqual(
            self.chargen.backpack, ["ration", "ration", "chain, 10ft", "chain, 10ft", "shovel", "lens"]
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
