"""
How to make a sword - example crafting tree for the crafting system.

See the `SwordSmithingBaseRecipe` in this module for an example of extendng the
recipe with a mocked 'skill' system (just random chance in our case). The skill
system used is game-specific but likely to be needed for most 'real' crafting
systems.

Note that 'tools' are references to the tools used - they don't need to be in
the inventory of the crafter. So when 'blast furnace' is given below, it is a
reference to a blast furnace used, not suggesting the crafter is carrying it
around with them.

## Sword crafting tree

::

    # base materials (consumables)

    iron ore, ash, sand, coal, oak wood, water, fur

    # base tools (marked with [T] for clarity and assumed to already exist)

    blast furnace[T], furnace[T], crucible[T], anvil[T],
    hammer[T], knife[T], cauldron[T]

    # recipes for making a sword

    pig iron = iron ore + 2xcoal + blast furnace[T]
    crucible_steel = pig iron + ash + sand + 2xcoal + crucible[T]
    sword blade = crucible steel + hammer[T] + anvil[T] + furnace[T]
    sword pommel = crucible steel + hammer[T] + anvil[T] + furnace[T]
    sword guard = crucible steel + hammer[T] + anvil[T] + furnace[T]

    rawhide = fur + knife[T]
    oak bark + cleaned oak wood = oak wood + knife[T]
    leather = rawhide + oak bark + water + cauldron[T]

    sword handle = cleaned oak wood + knife[T]

    sword = sword blade + sword guard + sword pommel
            + sword handle + leather + knife[T] + hammer[T] + furnace[T]

----

"""

from random import random
from .crafting import CraftingRecipe


class PigIronRecipe(CraftingRecipe):
    """
    Pig iron is a high-carbon result of melting iron in a blast furnace.

    """

    name = "pig iron"
    tool_tags = ["blast furnace"]
    consumable_tags = ["iron ore", "coal", "coal"]
    output_prototypes = [
        {
            "key": "Pig Iron ingot",
            "desc": "An ingot of crude pig iron.",
            "tags": [("pig iron", "crafting_material")],
        }
    ]


class CrucibleSteelRecipe(CraftingRecipe):
    """
    Mixing pig iron with impurities like ash and sand and melting it in a
    crucible produces a medieval level of steel (like damascus steel).

    """

    name = "crucible steel"
    tool_tags = ["crucible"]
    consumable_tags = ["pig iron", "ash", "sand", "coal", "coal"]
    output_prototypes = [
        {
            "key": "Crucible steel ingot",
            "desc": "An ingot of multi-colored crucible steel.",
            "tags": [("crucible steel", "crafting_material")],
        }
    ]


class _SwordSmithingBaseRecipe(CraftingRecipe):
    """
    A parent for all metallurgy sword-creation recipes. Those have a chance to
    failure but since steel is not lost in the process you can always try
    again.

    """

    success_message = "Your smithing work bears fruit and you craft {outputs}!"
    failed_message = (
        "You work and work but you are not happy with the result. You need to start over."
    )

    def craft(self, **kwargs):
        """
        Making a sword blade takes skill. Here we emulate this by introducing a
        random chance of failure (in a real game this could be a skill check
        against a skill found on `self.crafter`). In this case you can always
        start over since steel is not lost but can be re-smelted again for
        another try.

        Args:
            validated_inputs (list): all consumables/tools being used.
            **kwargs: any extra kwargs passed during crafting.

        Returns:
            any: The result of the craft, or None if a failure.

        Notes:
            Depending on if we return a crafting result from this
            method or not, `success_message` or `failure_message`
            will be echoed to the crafter.

            (for more control we could also message directly and raise
            crafting.CraftingError to abort craft process on failure).

        """
        if random.random() < 0.8:
            # 80% chance of success. This will spawn the sword and show
            # success-message.
            return super().craft(**kwargs)
        else:
            # fail and show failed message
            return None


class SwordBladeRecipe(_SwordSmithingBaseRecipe):
    """
    A [sword]blade requires hammering the steel out into shape using heat and
    force. This also includes the tang, which is the base for the hilt (the
    part of the sword you hold on to).

    """

    name = "sword blade"
    tool_tags = ["hammer", "anvil", "furnace"]
    consumable_tags = ["crucible steel"]
    output_prototypes = [
        {
            "key": "Sword blade",
            "desc": "A long blade that may one day become a sword.",
            "tags": [("sword blade", "crafting_material")],
        }
    ]


class SwordPommelRecipe(_SwordSmithingBaseRecipe):
    """
    The pommel is the 'button' or 'ball' etc the end of the sword hilt, holding
    it together.

    """

    name = "sword pommel"
    tool_tags = ["hammer", "anvil", "furnace"]
    consumable_tags = ["crucible steel"]
    output_prototypes = [
        {
            "key": "Sword pommel",
            "desc": "The pommel for a future sword.",
            "tags": [("sword pommel", "crafting_material")],
        }
    ]


class SwordGuardRecipe(_SwordSmithingBaseRecipe):
    """
    The guard stops the hand from accidentally sliding off the hilt onto the
    sword's blade and also protects the hand when parrying.

    """

    name = "sword guard"
    tool_tags = ["hammer", "anvil", "furnace"]
    consumable_tags = ["crucible steel"]
    output_prototypes = [
        {
            "key": "Sword guard",
            "desc": "The cross-guard for a future sword.",
            "tags": [("sword guard", "crafting_material")],
        }
    ]


class RawhideRecipe(CraftingRecipe):
    """
    Rawhide is animal skin cleaned and stripped of hair.

    """

    name = "rawhide"
    tool_tags = ["knife"]
    consumable_tags = ["fur"]
    output_prototypes = [
        {
            "key": "Rawhide",
            "desc": "Animal skin, cleaned and with hair removed.",
            "tags": [("rawhide", "crafting_material")],
        }
    ]


class OakBarkRecipe(CraftingRecipe):
    """
    The actual thing needed for tanning leather is Tannin, but we skip
    the step of refining tannin from the bark and use the bark as-is.

    This produces two outputs - the bark and the cleaned wood.
    """

    name = "oak bark"
    tool_tags = ["knife"]
    consumable_tags = ["oak wood"]
    output_prototypes = [
        {
            "key": "Oak bark",
            "desc": "Bark of oak, stripped from the core wood.",
            "tags": [("oak bark", "crafting_material")],
        },
        {
            "key": "Oak Wood (cleaned)",
            "desc": "Oakwood core, stripped of bark.",
            "tags": [("cleaned oak wood", "crafting_material")],
        },
    ]


class LeatherRecipe(CraftingRecipe):
    """
    Leather is produced by tanning rawhide in a process traditionally involving
    the chemical Tannin. Here we abbreviate this process a bit. Maybe a
    'tanning rack' tool should be required too ...

    """

    name = "leather"
    tool_tags = ["cauldron"]
    consumable_tags = ["rawhide", "oak bark", "water"]
    output_prototypes = [
        {
            "key": "Piece of Leather",
            "desc": "A piece of leather.",
            "tags": [("leather", "crafting_material")],
        }
    ]


class SwordHandleRecipe(CraftingRecipe):
    """
    The handle is the part of the hilt between the guard and the pommel where
    you hold the sword. It consists of wooden pieces around the steel tang. It
    is wrapped in leather, but that will be added at the end.

    """

    name = "sword handle"
    tool_tags = ["knife"]
    consumable_tags = ["cleaned oak wood"]
    output_prototypes = [
        {
            "key": "Sword handle",
            "desc": "Two pieces of wood to be be fitted onto a sword's tang as its handle.",
            "tags": [("sword handle", "crafting_material")],
        }
    ]


class SwordRecipe(_SwordSmithingBaseRecipe):
    """
    A finished sword consists of a Blade ending in a non-sharp part called the
    Tang. The cross Guard is put over the tang against the edge of the blade.
    The Handle is put over the tang to give something easier to hold. The
    Pommel locks everything in place. The handle is wrapped in leather
    strips for better grip.

    This covers only a single 'sword' type.

    """

    name = "sword"
    tool_tags = ["hammer", "furnace", "knife"]
    consumable_tags = ["sword blade", "sword guard", "sword pommel", "sword handle", "leather"]
    output_prototypes = [
        {
            "key": "Sword",
            "desc": "A bladed weapon.",
            # setting the tag as well - who knows if one can make something from this too!
            "tags": [("sword", "crafting_material")],
        }
        # obviously there would be other properties of a 'sword' added here
        # too, depending on how combat works in the your game!
    ]
    # this requires more precision
    exact_consumable_order = True
