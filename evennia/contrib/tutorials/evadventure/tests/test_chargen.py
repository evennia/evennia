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
        # setUp mocks randint to always return 10
        self.assertEqual(self.chargen.strength, 10)
        # armor: roll 10 -> "gambeson" (range 4-14)
        self.assertEqual(self.chargen.armor, "gambeson")
        # helmets and shields: roll 10 -> "no helmet or shield" (range 1-13) -> None
        self.assertEqual(self.chargen.helmet, None)
        self.assertEqual(self.chargen.shield, None)
        # backpack: dungeoning gear index 9 = "waterskin", general gear 1 index 9 = "drill",
        # general gear 2 index 9 = "twine"
        self.assertEqual(
            self.chargen.backpack,
            ["ration", "ration", "waterskin", "waterskin", "drill", "twine"],
        )

    @patch("evennia.contrib.tutorials.evadventure.rules.randint")
    def test_chargen_with_armor_and_shield(self, mock_randint):
        """Roll 17 gives armor, shield, and different gear."""
        mock_randint.return_value = 17
        sheet = chargen.TemporaryCharacterSheet()
        # armor: roll 17 -> "brigandine" (range 15-19)
        self.assertEqual(sheet.armor, "brigandine")
        # helmets and shields: roll 17 -> "shield" (range 17-19)
        self.assertEqual(sheet.helmet, None)
        self.assertEqual(sheet.shield, "shield")
        # backpack: dungeoning gear index 16 = "sack", general gear 1 index 16 = "tongs",
        # general gear 2 index 16 = "whistle"
        self.assertEqual(
            sheet.backpack,
            ["ration", "ration", "sack", "sack", "tongs", "whistle"],
        )

    @patch("evennia.contrib.tutorials.evadventure.rules.randint")
    def test_chargen_no_armor(self, mock_randint):
        """Roll 3 gives no armor and no helmet/shield."""
        mock_randint.return_value = 3
        sheet = chargen.TemporaryCharacterSheet()
        # armor: roll 3 -> "no armor" (range 1-3) -> None
        self.assertEqual(sheet.armor, None)
        # helmets and shields: roll 3 -> "no helmet or shield" (range 1-13) -> None
        self.assertEqual(sheet.helmet, None)
        self.assertEqual(sheet.shield, None)
        # backpack: dungeoning gear index 2 = "candles, 5", general gear 1 index 2 = "shovel",
        # general gear 2 index 2 = "lens"
        self.assertEqual(
            sheet.backpack,
            ["ration", "ration", "candles, 5", "candles, 5", "shovel", "lens"],
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
