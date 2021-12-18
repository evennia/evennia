# Crafting system

Contrib - Griatch 2020

This implements a full crafting system. The principle is that of a 'recipe':

    ingredient1 + ingredient2 + ... + tool1 + tool2 + ... +  craft_recipe -> objectA, objectB, ...

Here, 'ingredients' are consumed by the crafting process, whereas 'tools' are
necessary for the process by will not be destroyed by it.

An example would be to use the tools 'bowl' and 'oven' to use the ingredients
'flour', 'salt', 'yeast' and 'water' to create 'bread' using the 'bread recipe'.

A recipe does not have to use tools, like 'snow' + 'snowball-recipe' becomes
'snowball'. Conversely one could also imagine using tools without consumables,
like using 'spell book' and 'wand' to produce 'fireball' by having the recipe
check some magic skill on the character.

The system is generic enough to be used also for adventure-like puzzles, like
combining 'stick', 'string' and 'hook' to get a 'makeshift fishing rod' that
you can use with 'storm drain' (treated as a tool) to get 'key' ...

## Intallation and Usage

Import the `CmdCraft` command from evennia/contrib/crafting/crafting.py  and
add it to your Character cmdset. Reload and the `craft` command will be
available to you:

    craft <recipe> [from <ingredient>,...] [using <tool>, ...]

For example

    craft toy car from plank, wooden wheels, nails using saw, hammer

To use crafting you need recipes. Add a new variable to `mygame/server/conf/settings.py`:

    CRAFT_RECIPE_MODULES = ['world.recipes']

All top-level classes in these modules (whose name does not start with `_`)
will be parsed by Evennia as recipes to make available to the crafting system.
Using the above example, create `mygame/world/recipes.py` and add your recipies
in there:

```python

from evennia.contrib.game_systems.crafting import CraftingRecipe, CraftingValidationError


class RecipeBread(CraftingRecipe):
  """
  Bread is good for making sandwitches!

  """

  name = "bread"   # used to identify this recipe in 'craft' command
  tool_tags = ["bowl", "oven"]
  consumable_tags = ["flour", "salt", "yeast", "water"]
  output_prototypes = [
    {"key": "Loaf of Bread",
     "aliases": ["bread"],
     "desc": "A nice load of bread.",
     "typeclass": "typeclasses.objects.Food",  # assuming this exists
     "tags": [("bread", "crafting_material")]  # this makes it usable in other recipes ...
    }

  ]

  def pre_craft(self, **kwargs):
    # validates inputs etc. Raise `CraftingValidationError` if fails

  def craft(self, **kwargs):
    # performs the craft - but it can still fail (check skills etc here)

  def craft(self, result, **kwargs):
    # any post-crafting effects. Always called, even if crafting failed (be
    # result would be None then)

```

## Technical

The Recipe is a class that specifies the consumables, tools and output along
with various methods (that you can override) to do the the validation of inputs
and perform the crafting itself.

By default the input is a list of object-tags (using the "crafting_material"
and "crafting_tool" tag-categories respectively). Providing a set of objects
matching these tags are required for the crafting to be done. The use of tags
means that multiple different objects could all work for the same recipe, as
long as they have the right tag. This can be very useful for allowing players
to experiment and explore alternative ways to create things!

The output is given by a set of prototype-dicts. If the input is correct and
other checks are passed (such as crafting skill, for example), these prototypes
will be used to generate the new object(s) being crafted.

Each recipe is a stand-alone entity which allows for very advanced
customization for every recipe - for example one could have a recipe that
checks other properties of the inputs (like quality, color etc) and have that
affect the result. Your recipes could also (and likely would) tie into your
game's skill system to determine the success or outcome of the crafting.
