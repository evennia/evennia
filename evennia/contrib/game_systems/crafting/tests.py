"""
Unit tests for the crafting system contrib.

"""

from unittest import mock

from django.core.exceptions import ObjectDoesNotExist
from django.test import override_settings

from evennia.commands.default.tests import BaseEvenniaCommandTest
from evennia.utils.create import create_object
from evennia.utils.test_resources import BaseEvenniaTestCase

from . import crafting, example_recipes


class TestCraftUtils(BaseEvenniaTestCase):
    """
    Test helper utils for crafting.

    """

    maxDiff = None

    @override_settings(CRAFT_RECIPE_MODULES=[])
    def test_load_recipes(self):
        """This should only load the example module now"""

        crafting._load_recipes()
        self.assertEqual(
            crafting._RECIPE_CLASSES,
            {
                "crucible steel": example_recipes.CrucibleSteelRecipe,
                "leather": example_recipes.LeatherRecipe,
                "fireball": example_recipes.FireballRecipe,
                "heal": example_recipes.HealingRecipe,
                "oak bark": example_recipes.OakBarkRecipe,
                "pig iron": example_recipes.PigIronRecipe,
                "rawhide": example_recipes.RawhideRecipe,
                "sword": example_recipes.SwordRecipe,
                "sword blade": example_recipes.SwordBladeRecipe,
                "sword guard": example_recipes.SwordGuardRecipe,
                "sword handle": example_recipes.SwordHandleRecipe,
                "sword pommel": example_recipes.SwordPommelRecipe,
            },
        )


class _TestMaterial:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


class TestCraftingRecipeBase(BaseEvenniaTestCase):
    """
    Test the parent recipe class.
    """

    def setUp(self):
        self.crafter = mock.MagicMock()
        self.crafter.msg = mock.MagicMock()

        self.inp1 = _TestMaterial("test1")
        self.inp2 = _TestMaterial("test2")
        self.inp3 = _TestMaterial("test3")

        self.kwargs = {"kw1": 1, "kw2": 2}

        self.recipe = crafting.CraftingRecipeBase(
            self.crafter, self.inp1, self.inp2, self.inp3, **self.kwargs
        )

    def test_msg(self):
        """Test messaging to crafter"""

        self.recipe.msg("message")
        self.crafter.msg.assert_called_with("message", {"type": "crafting"})

    def test_pre_craft(self):
        """Test validating hook"""
        self.recipe.pre_craft()
        self.assertEqual(self.recipe.validated_inputs, (self.inp1, self.inp2, self.inp3))

    def test_pre_craft_fail(self):
        """Should rase error if validation fails"""
        self.recipe.allow_craft = False
        with self.assertRaises(crafting.CraftingValidationError):
            self.recipe.pre_craft()

    def test_craft_hook__succeed(self):
        """Test craft hook, the main access method."""

        expected_result = _TestMaterial("test_result")
        self.recipe.do_craft = mock.MagicMock(return_value=expected_result)

        self.assertTrue(self.recipe.allow_craft)

        result = self.recipe.craft()

        # check result
        self.assertEqual(result, expected_result)
        self.recipe.do_craft.assert_called_with(kw1=1, kw2=2)

        # since allow_reuse is False, this usage should now be turned off
        self.assertFalse(self.recipe.allow_craft)
        # trying to re-run again should fail since rerun is False
        with self.assertRaises(crafting.CraftingError):
            self.recipe.craft()

    def test_craft_hook__fail(self):
        """Test failing the call"""

        self.recipe.do_craft = mock.MagicMock(return_value=None)

        # trigger exception
        with self.assertRaises(crafting.CraftingError):
            self.recipe.craft(raise_exception=True)

        # reset and try again without exception
        self.recipe.allow_craft = True
        result = self.recipe.craft()
        self.assertEqual(result, None)


class _MockRecipe(crafting.CraftingRecipe):
    name = "testrecipe"
    tool_tags = ["tool1", "tool2"]
    consumable_tags = ["cons1", "cons2", "cons3"]
    output_prototypes = [
        {
            "key": "Result1",
            "prototype_key": "resultprot",
            "tags": [("result1", "crafting_material")],
        }
    ]


@override_settings(CRAFT_RECIPE_MODULES=[])
class TestCraftingRecipe(BaseEvenniaTestCase):
    """
    Test the CraftingRecipe class with one recipe
    """

    maxDiff = None

    def setUp(self):
        self.crafter = mock.MagicMock()
        self.crafter.msg = mock.MagicMock()

        self.tool1 = create_object(key="tool1", tags=[("tool1", "crafting_tool")], nohome=True)
        self.tool2 = create_object(key="tool2", tags=[("tool2", "crafting_tool")], nohome=True)
        self.cons1 = create_object(key="cons1", tags=[("cons1", "crafting_material")], nohome=True)
        self.cons2 = create_object(key="cons2", tags=[("cons2", "crafting_material")], nohome=True)
        self.cons3 = create_object(key="cons3", tags=[("cons3", "crafting_material")], nohome=True)

    def tearDown(self):
        try:
            self.tool1.delete()
            self.tool2.delete()
            self.cons1.delete()
            self.cons2.delete()
            self.cons3.delete()
        except ObjectDoesNotExist:
            pass

    def test_error_format(self):
        """Test the automatic error formatter"""
        recipe = _MockRecipe(
            self.crafter, self.tool1, self.tool2, self.cons1, self.cons2, self.cons3
        )

        msg = "{missing},{tools},{consumables},{inputs},{outputs}" "{i0},{i1},{o0}"
        kwargs = {
            "missing": "foo",
            "tools": ["bar", "bar2", "bar3"],
            "consumables": ["cons1", "cons2"],
        }

        expected = {
            "missing": "foo",
            "i0": "cons1",
            "i1": "cons2",
            "i2": "cons3",
            "o0": "Result1",
            "tools": "bar, bar2, and bar3",
            "consumables": "cons1 and cons2",
            "inputs": "cons1, cons2, and cons3",
            "outputs": "Result1",
        }

        result = recipe._format_message(msg, **kwargs)
        self.assertEqual(result, msg.format_map(expected))

    def test_craft__success(self):
        """Test to create a result from the recipe"""
        recipe = _MockRecipe(
            self.crafter, self.tool1, self.tool2, self.cons1, self.cons2, self.cons3
        )

        result = recipe.craft()

        self.assertEqual(result[0].key, "Result1")
        self.assertEqual(result[0].tags.all(), ["result1", "resultprot"])
        self.crafter.msg.assert_called_with(
            recipe.success_message.format(outputs="Result1"), {"type": "crafting"}
        )

        # make sure consumables are gone
        self.assertIsNone(self.cons1.pk)
        self.assertIsNone(self.cons2.pk)
        self.assertIsNone(self.cons3.pk)
        # make sure tools remain
        self.assertIsNotNone(self.tool1.pk)
        self.assertIsNotNone(self.tool2.pk)

    def test_seed__success(self):
        """Test seed helper classmethod"""

        # needed for other dbs to pass seed
        homeroom = create_object(key="HomeRoom", nohome=True)

        # call classmethod directly
        with override_settings(DEFAULT_HOME=f"#{homeroom.id}"):
            tools, consumables = _MockRecipe.seed()

        # this should be a normal successful crafting
        recipe = _MockRecipe(self.crafter, *(tools + consumables))

        result = recipe.craft()

        self.assertEqual(result[0].key, "Result1")
        self.assertEqual(result[0].tags.all(), ["result1", "resultprot"])
        self.crafter.msg.assert_called_with(
            recipe.success_message.format(outputs="Result1"), {"type": "crafting"}
        )

        # make sure consumables are gone
        for cons in consumables:
            self.assertIsNone(cons.pk)
        # make sure tools remain
        for tool in tools:
            self.assertIsNotNone(tool.pk)

    def test_craft_missing_tool__fail(self):
        """Fail craft by missing tool2"""
        recipe = _MockRecipe(self.crafter, self.tool1, self.cons1, self.cons2, self.cons3)
        result = recipe.craft()
        self.assertFalse(result)
        self.crafter.msg.assert_called_with(
            recipe.error_tool_missing_message.format(outputs="Result1", missing="tool2"),
            {"type": "crafting"},
        )

        # make sure consumables are still there
        self.assertIsNotNone(self.cons1.pk)
        self.assertIsNotNone(self.cons2.pk)
        self.assertIsNotNone(self.cons3.pk)
        # make sure tools remain
        self.assertIsNotNone(self.tool1.pk)
        self.assertIsNotNone(self.tool2.pk)

    def test_craft_missing_cons__fail(self):
        """Fail craft by missing cons3"""
        recipe = _MockRecipe(self.crafter, self.tool1, self.tool2, self.cons1, self.cons2)
        result = recipe.craft()
        self.assertFalse(result)
        self.crafter.msg.assert_called_with(
            recipe.error_consumable_missing_message.format(outputs="Result1", missing="cons3"),
            {"type": "crafting"},
        )

        # make sure consumables are still there
        self.assertIsNotNone(self.cons1.pk)
        self.assertIsNotNone(self.cons2.pk)
        self.assertIsNotNone(self.cons3.pk)
        # make sure tools remain
        self.assertIsNotNone(self.tool1.pk)
        self.assertIsNotNone(self.tool2.pk)

    def test_craft_missing_cons__always_consume__fail(self):
        """Fail craft by missing cons3, with always-consume flag"""

        cons4 = create_object(key="cons4", tags=[("cons4", "crafting_material")], nohome=True)

        recipe = _MockRecipe(self.crafter, self.tool1, self.tool2, self.cons1, self.cons2, cons4)
        recipe.consume_on_fail = True

        result = recipe.craft()

        self.assertFalse(result)
        self.crafter.msg.assert_called_with(
            recipe.error_consumable_missing_message.format(outputs="Result1", missing="cons3"),
            {"type": "crafting"},
        )

        # make sure consumables are deleted even though we failed
        self.assertIsNone(self.cons1.pk)
        self.assertIsNone(self.cons2.pk)
        # the extra should also be gone
        self.assertIsNone(cons4.pk)
        # but cons3 should be fine since it was not included
        self.assertIsNotNone(self.cons3.pk)
        # make sure tools remain as normal
        self.assertIsNotNone(self.tool1.pk)
        self.assertIsNotNone(self.tool2.pk)

    def test_craft_wrong_tool__fail(self):
        """Fail craft by including a wrong tool"""

        wrong = create_object(key="wrong", tags=[("wrongtool", "crafting_tool")], nohome=True)

        recipe = _MockRecipe(self.crafter, self.tool1, self.tool2, self.cons1, self.cons2, wrong)
        result = recipe.craft()
        self.assertFalse(result)
        self.crafter.msg.assert_called_with(
            recipe.error_tool_excess_message.format(
                outputs="Result1", excess=wrong.get_display_name(looker=self.crafter)
            ),
            {"type": "crafting"},
        )
        # make sure consumables are still there
        self.assertIsNotNone(self.cons1.pk)
        self.assertIsNotNone(self.cons2.pk)
        self.assertIsNotNone(self.cons3.pk)
        # make sure tools remain
        self.assertIsNotNone(self.tool1.pk)
        self.assertIsNotNone(self.tool2.pk)

    def test_craft_tool_excess__fail(self):
        """Fail by too many consumables"""

        # note that this is a valid tag!
        tool3 = create_object(key="tool3", tags=[("tool2", "crafting_tool")], nohome=True)

        recipe = _MockRecipe(
            self.crafter, self.tool1, self.tool2, self.cons1, self.cons2, self.cons3, tool3
        )
        result = recipe.craft()
        self.assertFalse(result)
        self.crafter.msg.assert_called_with(
            recipe.error_tool_excess_message.format(
                outputs="Result1", excess=tool3.get_display_name(looker=self.crafter)
            ),
            {"type": "crafting"},
        )

        # make sure consumables are still there
        self.assertIsNotNone(self.cons1.pk)
        self.assertIsNotNone(self.cons2.pk)
        self.assertIsNotNone(self.cons3.pk)
        # make sure tools remain
        self.assertIsNotNone(self.tool1.pk)
        self.assertIsNotNone(self.tool2.pk)
        self.assertIsNotNone(tool3.pk)

    def test_craft_cons_excess__fail(self):
        """Fail by too many consumables"""

        # note that this is a valid tag!
        cons4 = create_object(key="cons4", tags=[("cons3", "crafting_material")], nohome=True)

        recipe = _MockRecipe(
            self.crafter, self.tool1, self.tool2, self.cons1, self.cons2, self.cons3, cons4
        )
        result = recipe.craft()
        self.assertFalse(result)
        self.crafter.msg.assert_called_with(
            recipe.error_consumable_excess_message.format(
                outputs="Result1", excess=cons4.get_display_name(looker=self.crafter)
            ),
            {"type": "crafting"},
        )

        # make sure consumables are still there
        self.assertIsNotNone(self.cons1.pk)
        self.assertIsNotNone(self.cons2.pk)
        self.assertIsNotNone(self.cons3.pk)
        self.assertIsNotNone(cons4.pk)
        # make sure tools remain
        self.assertIsNotNone(self.tool1.pk)
        self.assertIsNotNone(self.tool2.pk)

    def test_craft_tool_excess__sucess(self):
        """Allow too many consumables"""

        tool3 = create_object(key="tool3", tags=[("tool2", "crafting_tool")], nohome=True)

        recipe = _MockRecipe(
            self.crafter, self.tool1, self.tool2, self.cons1, self.cons2, self.cons3, tool3
        )
        recipe.exact_tools = False
        result = recipe.craft()
        self.assertTrue(result)
        self.crafter.msg.assert_called_with(
            recipe.success_message.format(outputs="Result1"), {"type": "crafting"}
        )

        # make sure consumables are gone
        self.assertIsNone(self.cons1.pk)
        self.assertIsNone(self.cons2.pk)
        self.assertIsNone(self.cons3.pk)
        # make sure tools remain
        self.assertIsNotNone(self.tool1.pk)
        self.assertIsNotNone(self.tool2.pk)

    def test_craft_cons_excess__sucess(self):
        """Allow too many consumables"""

        cons4 = create_object(key="cons4", tags=[("cons3", "crafting_material")], nohome=True)

        recipe = _MockRecipe(
            self.crafter, self.tool1, self.tool2, self.cons1, self.cons2, self.cons3, cons4
        )
        recipe.exact_consumables = False
        result = recipe.craft()
        self.assertTrue(result)
        self.crafter.msg.assert_called_with(
            recipe.success_message.format(outputs="Result1"), {"type": "crafting"}
        )

        # make sure consumables are gone
        self.assertIsNone(self.cons1.pk)
        self.assertIsNone(self.cons2.pk)
        self.assertIsNone(self.cons3.pk)
        # make sure tools remain
        self.assertIsNotNone(self.tool1.pk)
        self.assertIsNotNone(self.tool2.pk)

    def test_craft_tool_order__fail(self):
        """Strict tool-order recipe fail"""
        recipe = _MockRecipe(
            self.crafter, self.tool2, self.tool1, self.cons1, self.cons2, self.cons3
        )
        recipe.exact_tool_order = True
        result = recipe.craft()
        self.assertFalse(result)
        self.crafter.msg.assert_called_with(
            recipe.error_tool_order_message.format(
                outputs="Result1", missing=self.tool2.get_display_name(looker=self.crafter)
            ),
            {"type": "crafting"},
        )

        # make sure consumables are still there
        self.assertIsNotNone(self.cons1.pk)
        self.assertIsNotNone(self.cons2.pk)
        self.assertIsNotNone(self.cons3.pk)
        # make sure tools remain
        self.assertIsNotNone(self.tool1.pk)
        self.assertIsNotNone(self.tool2.pk)

    def test_craft_cons_order__fail(self):
        """Strict tool-order recipe fail"""
        recipe = _MockRecipe(
            self.crafter, self.tool1, self.tool2, self.cons3, self.cons2, self.cons1
        )
        recipe.exact_consumable_order = True
        result = recipe.craft()
        self.assertFalse(result)
        self.crafter.msg.assert_called_with(
            recipe.error_consumable_order_message.format(
                outputs="Result1", missing=self.cons3.get_display_name(looker=self.crafter)
            ),
            {"type": "crafting"},
        )

        # make sure consumables are still there
        self.assertIsNotNone(self.cons1.pk)
        self.assertIsNotNone(self.cons2.pk)
        self.assertIsNotNone(self.cons3.pk)
        # make sure tools remain
        self.assertIsNotNone(self.tool1.pk)
        self.assertIsNotNone(self.tool2.pk)


class TestCraftSword(BaseEvenniaTestCase):
    """
    Test the `craft` function by crafting the example sword.

    """

    def setUp(self):
        self.crafter = mock.MagicMock()
        self.crafter.msg = mock.MagicMock()

    @override_settings(CRAFT_RECIPE_MODULES=[], DEFAULT_HOME="#999999")
    @mock.patch("evennia.contrib.game_systems.crafting.example_recipes.random")
    def test_craft_sword(self, mockrandom):
        """
        Craft example sword. For the test, every crafting works.

        """
        # make sure every craft succeeds
        mockrandom.random = mock.MagicMock(return_value=0.2)

        def _co(key, tagkey, is_tool=False):
            tagcat = "crafting_tool" if is_tool else "crafting_material"
            return create_object(key=key, tags=[(tagkey, tagcat)], nohome=True)

        def _craft(recipe_name, *inputs):
            """shortcut to shorten and return only one element"""
            result = crafting.craft(self.crafter, recipe_name, *inputs, raise_exception=True)
            return result[0] if len(result) == 1 else result

        # generate base materials
        iron_ore1 = _co("Iron ore ingot", "iron ore")
        iron_ore2 = _co("Iron ore ingot", "iron ore")
        iron_ore3 = _co("Iron ore ingot", "iron ore")

        ash1 = _co("Pile of Ash", "ash")
        ash2 = _co("Pile of Ash", "ash")
        ash3 = _co("Pile of Ash", "ash")

        sand1 = _co("Pile of sand", "sand")
        sand2 = _co("Pile of sand", "sand")
        sand3 = _co("Pile of sand", "sand")

        coal01 = _co("Pile of coal", "coal")
        coal02 = _co("Pile of coal", "coal")
        coal03 = _co("Pile of coal", "coal")
        coal04 = _co("Pile of coal", "coal")
        coal05 = _co("Pile of coal", "coal")
        coal06 = _co("Pile of coal", "coal")
        coal07 = _co("Pile of coal", "coal")
        coal08 = _co("Pile of coal", "coal")
        coal09 = _co("Pile of coal", "coal")
        coal10 = _co("Pile of coal", "coal")
        coal11 = _co("Pile of coal", "coal")
        coal12 = _co("Pile of coal", "coal")

        oak_wood = _co("Pile of oak wood", "oak wood")
        water = _co("Bucket of water", "water")
        fur = _co("Bundle of Animal fur", "fur")

        # tools
        blast_furnace = _co("Blast furnace", "blast furnace", is_tool=True)
        furnace = _co("Smithing furnace", "furnace", is_tool=True)
        crucible = _co("Smelting crucible", "crucible", is_tool=True)
        anvil = _co("Smithing anvil", "anvil", is_tool=True)
        hammer = _co("Smithing hammer", "hammer", is_tool=True)
        knife = _co("Working knife", "knife", is_tool=True)
        cauldron = _co("Cauldron", "cauldron", is_tool=True)

        # making pig iron
        inputs = [iron_ore1, coal01, coal02, blast_furnace]
        pig_iron1 = _craft("pig iron", *inputs)

        inputs = [iron_ore2, coal03, coal04, blast_furnace]
        pig_iron2 = _craft("pig iron", *inputs)

        inputs = [iron_ore3, coal05, coal06, blast_furnace]
        pig_iron3 = _craft("pig iron", *inputs)

        # making crucible steel
        inputs = [pig_iron1, ash1, sand1, coal07, coal08, crucible]
        crucible_steel1 = _craft("crucible steel", *inputs)

        inputs = [pig_iron2, ash2, sand2, coal09, coal10, crucible]
        crucible_steel2 = _craft("crucible steel", *inputs)

        inputs = [pig_iron3, ash3, sand3, coal11, coal12, crucible]
        crucible_steel3 = _craft("crucible steel", *inputs)

        # smithing
        inputs = [crucible_steel1, hammer, anvil, furnace]
        sword_blade = _craft("sword blade", *inputs)

        inputs = [crucible_steel2, hammer, anvil, furnace]
        sword_pommel = _craft("sword pommel", *inputs)

        inputs = [crucible_steel3, hammer, anvil, furnace]
        sword_guard = _craft("sword guard", *inputs)

        # stripping fur
        inputs = [fur, knife]
        rawhide = _craft("rawhide", *inputs)

        # making bark (tannin) and cleaned wood
        inputs = [oak_wood, knife]
        oak_bark, cleaned_oak_wood = _craft("oak bark", *inputs)

        # leathermaking
        inputs = [rawhide, oak_bark, water, cauldron]
        leather = _craft("leather", *inputs)

        # sword handle
        inputs = [cleaned_oak_wood, knife]
        sword_handle = _craft("sword handle", *inputs)

        # sword (order matters)
        inputs = [
            sword_blade,
            sword_guard,
            sword_pommel,
            sword_handle,
            leather,
            knife,
            hammer,
            furnace,
        ]
        sword = _craft("sword", *inputs)

        self.assertEqual(sword.key, "Sword")

        # make sure all materials and intermediaries are deleted
        self.assertIsNone(iron_ore1.pk)
        self.assertIsNone(iron_ore2.pk)
        self.assertIsNone(iron_ore3.pk)
        self.assertIsNone(ash1.pk)
        self.assertIsNone(ash2.pk)
        self.assertIsNone(ash3.pk)
        self.assertIsNone(sand1.pk)
        self.assertIsNone(sand2.pk)
        self.assertIsNone(sand3.pk)
        self.assertIsNone(coal01.pk)
        self.assertIsNone(coal02.pk)
        self.assertIsNone(coal03.pk)
        self.assertIsNone(coal04.pk)
        self.assertIsNone(coal05.pk)
        self.assertIsNone(coal06.pk)
        self.assertIsNone(coal07.pk)
        self.assertIsNone(coal08.pk)
        self.assertIsNone(coal09.pk)
        self.assertIsNone(coal10.pk)
        self.assertIsNone(coal11.pk)
        self.assertIsNone(coal12.pk)
        self.assertIsNone(oak_wood.pk)
        self.assertIsNone(water.pk)
        self.assertIsNone(fur.pk)
        self.assertIsNone(pig_iron1.pk)
        self.assertIsNone(pig_iron2.pk)
        self.assertIsNone(pig_iron3.pk)
        self.assertIsNone(crucible_steel1.pk)
        self.assertIsNone(crucible_steel2.pk)
        self.assertIsNone(crucible_steel3.pk)
        self.assertIsNone(sword_blade.pk)
        self.assertIsNone(sword_pommel.pk)
        self.assertIsNone(sword_guard.pk)
        self.assertIsNone(rawhide.pk)
        self.assertIsNone(oak_bark.pk)
        self.assertIsNone(leather.pk)
        self.assertIsNone(sword_handle.pk)

        # make sure all tools remain
        self.assertIsNotNone(blast_furnace)
        self.assertIsNotNone(furnace)
        self.assertIsNotNone(crucible)
        self.assertIsNotNone(anvil)
        self.assertIsNotNone(hammer)
        self.assertIsNotNone(knife)
        self.assertIsNotNone(cauldron)


@mock.patch("evennia.contrib.game_systems.crafting.crafting._load_recipes", new=mock.MagicMock())
@mock.patch(
    "evennia.contrib.game_systems.crafting.crafting._RECIPE_CLASSES",
    new={"testrecipe": _MockRecipe},
)
@override_settings(CRAFT_RECIPE_MODULES=[])
class TestCraftCommand(BaseEvenniaCommandTest):
    """Test the crafting command"""

    def setUp(self):
        super().setUp()

        tools, consumables = _MockRecipe.seed(
            tool_kwargs={"location": self.char1}, consumable_kwargs={"location": self.char1}
        )

    def test_craft__success(self):
        "Successfully craft using command"
        self.call(
            crafting.CmdCraft(),
            "testrecipe from cons1, cons2, cons3 using tool1, tool2",
            _MockRecipe.success_message.format(outputs="Result1"),
        )

    def test_craft__notools__failure(self):
        "Craft fail no tools"
        self.call(
            crafting.CmdCraft(),
            "testrecipe from cons1, cons2, cons3",
            _MockRecipe.error_tool_missing_message.format(outputs="Result1", missing="tool1"),
        )

    def test_craft__nocons__failure(self):
        self.call(
            crafting.CmdCraft(),
            "testrecipe using tool1, tool2",
            _MockRecipe.error_consumable_missing_message.format(outputs="Result1", missing="cons1"),
        )

    def test_craft__unknown_recipe__failure(self):
        self.call(
            crafting.CmdCraft(),
            "nonexistent from cons1, cons2, cons3 using tool1, tool2",
            "Unknown recipe 'nonexistent'",
        )
