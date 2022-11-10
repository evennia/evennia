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


## Recipes used for spell casting

This is a simple example modifying the base Recipe to use as a way
to describe magical spells instead. It combines tools with
a skill (an attribute on the caster) in order to produce a magical effect.

The example `CmdCast` command can be added to the CharacterCmdset in
`mygame/commands/default_cmdsets` to test it out. The 'effects' are
just mocked for the example.

::
    # base tools (assumed to already exist)

    spellbook[T], wand[T]

    # skill (stored as Attribute on caster)

    firemagic skill level10+

    # recipe for fireball

    fireball = spellbook[T] + wand[T] + [firemagic skill lvl10+]

----

"""

from random import randint, random

from evennia.commands.command import Command, InterruptCommand

from .crafting import CraftingRecipe, CraftingValidationError, craft

# ------------------------------------------------------------
# Sword recipe
# ------------------------------------------------------------


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


# ------------------------------------------------------------
# Recipes for spell casting
# ------------------------------------------------------------


class _MagicRecipe(CraftingRecipe):
    """
    A base 'recipe' to represent magical spells.

    We *could* treat this just like the sword above - by combining the wand and spellbook to make a
    fireball object that the user can then throw with another command. For this example we instead
    generate 'magical effects' as strings+values that we would then supposedly inject into a
    combat system or other resolution system.

    We also assume that the crafter has skills set on itself as plain Attributes.

    """

    name = ""
    # all spells require a spellbook and a wand (so there!)
    tool_tags = ["spellbook", "wand"]

    error_tool_missing_message = "Cannot cast spells without {missing}."
    success_message = "You successfully cast the spell!"
    # custom properties
    skill_requirement = []  # this should be on the form [(skillname, min_level)]
    skill_roll = ""  # skill to roll for success
    desired_effects = []  # on the form [(effect, value), ...]
    failure_effects = []  # ''
    error_too_low_skill_level = "Your skill {skill_name} is too low to cast {spell}."
    error_no_skill_roll = "You must have the skill {skill_name} to cast the spell {spell}."

    def pre_craft(self, **kwargs):
        """
        This is where we do input validation. We want to do the
        normal validation of the tools, but also check for a skill
        on the crafter. This must set the result on `self.validated_inputs`.
        We also set the crafter's relevant skill value on `self.skill_roll_value`.

        Args:
            **kwargs: Any optional extra kwargs passed during initialization of
                the recipe class.

        Raises:
            CraftingValidationError: If validation fails. At this point the crafter
                is expected to have been informed of the problem already.

        """
        # this will check so the spellbook and wand are at hand.
        super().pre_craft(**kwargs)

        # at this point we have the items available, let's also check for the skill. We
        # assume the  crafter has the skill available as an Attribute
        # on itself.

        crafter = self.crafter
        for skill_name, min_value in self.skill_requirements:
            skill_value = crafter.attributes.get(skill_name)

            if skill_value is None or skill_value < min_value:
                self.msg(
                    self.error_too_low_skill_level.format(skill_name=skill_name, spell=self.name)
                )
                raise CraftingValidationError

        # get the value of the skill to roll
        self.skill_roll_value = self.crafter.attributes.get(self.skill_roll)
        if self.skill_roll_value is None:
            self.msg(self.error_no_skill_roll.format(skill_name=self.skill_roll, spell=self.name))
            raise CraftingValidationError

    def do_craft(self, **kwargs):
        """
        'Craft' the magical effect. When we get to this point we already know we have all the
        prequisite for creating the effect. In this example we will store the effect on the crafter;
        maybe this enhances the crafter or makes a new attack available to them in combat.

        An alternative to this would of course be to spawn an actual object for the effect, like
        creating a potion or an actual fireball-object to throw (this depends on how your combat
        works).

        """
        # we do a simple skill check here.
        if randint(1, 18) <= self.skill_roll_value:
            # a success!
            return True, self.desired_effects
        else:
            # a failure!
            return False, self.failure_effects

    def post_craft(self, craft_result, **kwargs):
        """
        Always called at the end of crafting, regardless of successful or not.

        Since we get a custom craft result (True/False, effects) we need to
        wrap the original post_craft to output the error messages for us
        correctly.

        """
        success = False
        if craft_result:
            success, _ = craft_result
        # default post_craft just checks if craft_result is truthy or not.
        # we don't care about its return value since we already have craft_result.
        super().post_craft(success, **kwargs)
        return craft_result


class FireballRecipe(_MagicRecipe):
    """
    A Fireball is a magical effect that can be thrown at a target to cause damage.

    Note that the magic-effects are just examples, an actual rule system would
    need to be created to understand what they mean when used.

    """

    name = "fireball"
    skill_requirements = [("firemagic", 10)]  # skill 'firemagic' lvl 10 or higher
    skill_roll = "firemagic"
    success_message = "A ball of flame appears!"
    desired_effects = [("target_fire_damage", 25), ("ranged_attack", -2), ("mana_cost", 12)]
    failure_effects = [("self_fire_damage", 5), ("mana_cost", 5)]


class HealingRecipe(_MagicRecipe):
    """
    Healing magic will restore a certain amount of health to the target over time.

    Note that the magic-effects are just examples, an actual rule system would
    need to be created to understand what they mean.

    """

    name = "heal"
    skill_requirements = [("bodymagic", 5), ("empathy", 10)]
    skill_roll = "bodymagic"
    success_message = "You successfully extend your healing aura."
    desired_effects = [("healing", 15), ("mana_cost", 5)]
    failure_effects = []


class CmdCast(Command):
    """
    Cast a magical spell.

    Usage:
        cast <spell> <target>

    """

    key = "cast"

    def parse(self):
        """
        Simple parser, assuming spellname doesn't have spaces.
        Stores result in self.target and self.spellname.

        """
        args = self.args.strip().lower()
        target = None
        if " " in args:
            self.spellname, *target = args.split(" ", 1)
        else:
            self.spellname = args

        if not self.spellname:
            self.caller.msg("You must specify a spell name.")
            raise InterruptCommand

        if target:
            self.target = self.caller.search(target[0].strip())
            if not self.target:
                raise InterruptCommand
        else:
            self.target = self.caller

    def func(self):

        # all items carried by the caller could work
        possible_tools = self.caller.contents

        try:
            # if this completes without an exception, the caster will have
            # a new magic_effect set on themselves, ready to use or apply in some way.
            success, effects = craft(
                self.caller, self.spellname, *possible_tools, raise_exception=True
            )
        except CraftingValidationError:
            return
        except KeyError:
            self.caller.msg(f"You don't know of a spell called '{self.spellname}'")
            return

        # Applying the magical effect to target would happen below.
        # self.caller.db.active_spells[self.spellname] holds all the effects
        # of this particular prepared spell. For a fireball you could perform
        # an attack roll here and apply damage if you hit. For healing you would heal the target
        # (which could be yourself) by a number of health points given by the recipe.
        effect_txt = ", ".join(f"{eff[0]}({eff[1]})" for eff in effects)
        success_txt = "|gsucceeded|n" if success else "|rfailed|n"
        self.caller.msg(
            f"Casting the spell {self.spellname} on {self.target} {success_txt}, "
            f"causing the following effects: {effect_txt}."
        )
