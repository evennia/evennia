"""
Testing clothing contrib

"""

from evennia.commands.default.tests import BaseEvenniaCommandTest
from evennia.objects.objects import DefaultRoom
from evennia.utils.create import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from . import clothing


class TestClothingCmd(BaseEvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(DefaultRoom, key="Room")
        self.wearer = create_object(clothing.ClothedCharacter, key="Wearer")
        self.wearer.location = self.room
        # Make a test hat
        self.test_hat = create_object(clothing.ContribClothing, key="test hat")
        self.test_hat.db.clothing_type = "hat"
        # Make a test scarf
        self.test_scarf = create_object(clothing.ContribClothing, key="test scarf")
        self.test_scarf.db.clothing_type = "accessory"

    def test_clothingcommands(self):
        # Test inventory command.
        self.call(
            clothing.CmdInventory(),
            "",
            "You are not carrying or wearing anything.",
            caller=self.wearer,
        )

        # Test wear command
        self.test_scarf.location = self.wearer
        self.test_hat.location = self.wearer
        self.call(clothing.CmdWear(), "", "Usage: wear <obj> [=] [wear style]", caller=self.wearer)
        self.call(clothing.CmdWear(), "hat", "You put on test hat.", caller=self.wearer)
        self.call(
            clothing.CmdWear(),
            "scarf stylishly",
            "You wear test scarf stylishly.",
            caller=self.wearer,
        )
        # Test cover command.
        self.call(
            clothing.CmdCover(),
            "",
            "Usage: cover <worn clothing> with <clothing object>",
            caller=self.wearer,
        )
        self.call(
            clothing.CmdCover(),
            "hat with scarf",
            "You cover test hat with test scarf.",
            caller=self.wearer,
        )
        # Test remove command.
        self.call(clothing.CmdRemove(), "", "Could not find ''.", caller=self.wearer)
        self.call(
            clothing.CmdRemove(),
            "hat",
            "You have to take off test scarf first.",
            caller=self.wearer,
        )
        self.call(
            clothing.CmdRemove(),
            "scarf",
            "You remove test scarf, revealing test hat.",
            caller=self.wearer,
        )
        # Test uncover command.
        self.test_scarf.wear(self.wearer, True)
        self.test_hat.db.covered_by = self.test_scarf
        self.call(
            clothing.CmdUncover(), "", "Usage: uncover <worn clothing object>", caller=self.wearer
        )
        self.call(clothing.CmdUncover(), "hat", "You uncover test hat.", caller=self.wearer)


class TestClothingFunc(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(DefaultRoom, key="Room")
        self.wearer = create_object(clothing.ClothedCharacter, key="Wearer")
        self.wearer.location = self.room
        # Make a test hat
        self.test_hat = create_object(clothing.ContribClothing, key="test hat")
        self.test_hat.db.clothing_type = "hat"
        self.test_hat.location = self.wearer
        # Make a test shirt
        self.test_shirt = create_object(clothing.ContribClothing, key="test shirt")
        self.test_shirt.db.clothing_type = "top"
        self.test_shirt.location = self.wearer
        # Make test pants
        self.test_pants = create_object(clothing.ContribClothing, key="test pants")
        self.test_pants.db.clothing_type = "bottom"
        self.test_pants.location = self.wearer

    def test_clothingfunctions(self):
        self.test_hat.wear(self.wearer, "on the head")
        self.assertEqual(self.test_hat.db.worn, "on the head")

        self.test_hat.remove(self.wearer)
        self.assertFalse(self.test_hat.db.worn)

        self.test_hat.db.worn = True
        self.test_hat.at_get(self.wearer)
        self.assertFalse(self.test_hat.db.worn)

        self.test_hat.db.covered_by = self.test_shirt
        can_move = self.test_hat.at_pre_move(self.room)
        self.assertFalse(can_move)

        clothes_list = [self.test_shirt, self.test_hat, self.test_pants]
        self.assertEqual(
            clothing.order_clothes_list(clothes_list),
            [self.test_hat, self.test_shirt, self.test_pants],
        )

        self.test_hat.wear(self.wearer, True)
        self.test_pants.wear(self.wearer, True)
        self.assertEqual(clothing.get_worn_clothes(self.wearer), [self.test_hat, self.test_pants])

        self.assertEqual(
            clothing.clothing_type_count(clothes_list), {"hat": 1, "top": 1, "bottom": 1}
        )

        self.assertEqual(clothing.single_type_count(clothes_list, "hat"), 1)
