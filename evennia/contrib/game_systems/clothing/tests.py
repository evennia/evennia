"""
Testing clothing contrib

"""

from evennia.commands.default.tests import EvenniaCommandTest
from evennia.utils.create import create_object
from evennia.objects.objects import DefaultRoom
from evennia.utils.test_resources import BaseEvenniaTest
from . import clothing


class TestClothingCmd(EvenniaCommandTest):
    def test_clothingcommands(self):
        wearer = create_object(clothing.ClothedCharacter, key="Wearer")
        friend = create_object(clothing.ClothedCharacter, key="Friend")
        room = create_object(DefaultRoom, key="room")
        wearer.location = room
        friend.location = room
        # Make a test hat
        test_hat = create_object(clothing.ContribClothing, key="test hat")
        test_hat.db.clothing_type = "hat"
        test_hat.location = wearer
        # Make a test scarf
        test_scarf = create_object(clothing.ContribClothing, key="test scarf")
        test_scarf.db.clothing_type = "accessory"
        test_scarf.location = wearer
        # Test wear command
        self.call(clothing.CmdWear(), "", "Usage: wear <obj> [wear style]", caller=wearer)
        self.call(clothing.CmdWear(), "hat", "Wearer puts on test hat.", caller=wearer)
        self.call(
            clothing.CmdWear(),
            "scarf stylishly",
            "Wearer wears test scarf stylishly.",
            caller=wearer,
        )
        # Test cover command.
        self.call(
            clothing.CmdCover(),
            "",
            "Usage: cover <worn clothing> [with] <clothing object>",
            caller=wearer,
        )
        self.call(
            clothing.CmdCover(),
            "hat with scarf",
            "Wearer covers test hat with test scarf.",
            caller=wearer,
        )
        # Test remove command.
        self.call(clothing.CmdRemove(), "", "Could not find ''.", caller=wearer)
        self.call(
            clothing.CmdRemove(), "hat", "You have to take off test scarf first.", caller=wearer
        )
        self.call(
            clothing.CmdRemove(),
            "scarf",
            "Wearer removes test scarf, revealing test hat.",
            caller=wearer,
        )
        # Test uncover command.
        test_scarf.wear(wearer, True)
        test_hat.db.covered_by = test_scarf
        self.call(clothing.CmdUncover(), "", "Usage: uncover <worn clothing object>", caller=wearer)
        self.call(clothing.CmdUncover(), "hat", "Wearer uncovers test hat.", caller=wearer)
        # Test drop command.
        test_hat.db.covered_by = test_scarf
        self.call(clothing.CmdDrop(), "", "Drop what?", caller=wearer)
        self.call(
            clothing.CmdDrop(),
            "hat",
            "You can't drop that because it's covered by test scarf.",
            caller=wearer,
        )
        self.call(clothing.CmdDrop(), "scarf", "You drop test scarf.", caller=wearer)
        # Test give command.
        self.call(
            clothing.CmdGive(), "", "Usage: give <inventory object> = <target>", caller=wearer
        )
        self.call(
            clothing.CmdGive(),
            "hat = Friend",
            "Wearer removes test hat.|You give test hat to Friend.",
            caller=wearer,
        )
        # Test inventory command.
        self.call(
            clothing.CmdInventory(), "", "You are not carrying or wearing anything.", caller=wearer
        )


class TestClothingFunc(BaseEvenniaTest):
    def test_clothingfunctions(self):
        wearer = create_object(clothing.ClothedCharacter, key="Wearer")
        room = create_object(DefaultRoom, key="room")
        wearer.location = room
        # Make a test hat
        test_hat = create_object(clothing.ContribClothing, key="test hat")
        test_hat.db.clothing_type = "hat"
        test_hat.location = wearer
        # Make a test shirt
        test_shirt = create_object(clothing.ContribClothing, key="test shirt")
        test_shirt.db.clothing_type = "top"
        test_shirt.location = wearer
        # Make a test pants
        test_pants = create_object(clothing.ContribClothing, key="test pants")
        test_pants.db.clothing_type = "bottom"
        test_pants.location = wearer

        test_hat.wear(wearer, "on the head")
        self.assertEqual(test_hat.db.worn, "on the head")

        test_hat.remove(wearer)
        self.assertEqual(test_hat.db.worn, False)

        test_hat.worn = True
        test_hat.at_get(wearer)
        self.assertEqual(test_hat.db.worn, False)

        clothes_list = [test_shirt, test_hat, test_pants]
        self.assertEqual(
            clothing.order_clothes_list(clothes_list), [test_hat, test_shirt, test_pants]
        )

        test_hat.wear(wearer, True)
        test_pants.wear(wearer, True)
        self.assertEqual(clothing.get_worn_clothes(wearer), [test_hat, test_pants])

        self.assertEqual(
            clothing.clothing_type_count(clothes_list), {"hat": 1, "top": 1, "bottom": 1}
        )

        self.assertEqual(clothing.single_type_count(clothes_list, "hat"), 1)
