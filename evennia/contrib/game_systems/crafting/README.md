# Crafting system

Contribution by Griatch 2020

This implements a full crafting system. The principle is that of a 'recipe',
where you combine items (tagged as ingredients) create something new. The recipe can also
require certain (non-consumed) tools. An example would be to use the 'bread recipe' to
combine 'flour', 'water' and 'yeast' with an 'oven' to bake a 'loaf of bread'.

The recipe process can be understood like this:

    ingredient(s) + tool(s) + recipe -> object(s)

Here, 'ingredients' are consumed by the crafting process, whereas 'tools' are
necessary for the process but will not be destroyed by it.

The included `craft` command works like this:

    craft <recipe> [from <ingredient>,...] [using <tool>, ...]

## Examples

Using the `craft` command:

    craft toy car from plank, wooden wheels, nails using saw, hammer

A recipe does not have to use tools or even multiple ingredients:

    snow + snowball_recipe -> snowball

Conversely one could also imagine using tools without consumables, like

    spell_book + wand + fireball_recipe -> fireball

The system is generic enough to be used also for adventure-like puzzles (but
one would need to change the command and determine the recipe on based on what
is being combined instead):

    stick + string + hook -> makeshift_fishing_rod
    makeshift_fishing_rod + storm_drain -> key

See the [sword example](evennia.contrib.game_systems.crafting.example_recipes) for an example
of how to design a recipe tree for crafting a sword from base elements.

## Intallation and Usage

Import the `CmdCraft` command from evennia/contrib/crafting/crafting.py  and
add it to your Character cmdset. Reload and the `craft` command will be
available to you:

    craft <recipe> [from <ingredient>,...] [using <tool>, ...]

In code, you can craft using the
`evennia.contrib.game_systems.crafting.craft` function:

```python
from evennia.contrib.game_systems.crafting import craft

result = craft(caller, "recipename", *inputs)

```
Here, `caller` is the one doing the crafting and `*inputs` is any combination of
consumables and/or tool Objects. The system will identify which is which by the
[Tags](../Components/Tags.md) on them (see below) The `result` is always a list.

To use crafting you need recipes. Add a new variable to
`mygame/server/conf/settings.py`:

    CRAFT_RECIPE_MODULES = ['world.recipes']

All top-level classes in these modules (whose name does not start with `_`) will
be parsed by Evennia as recipes to make available to the crafting system.  Using
the above example, create `mygame/world/recipes.py` and add your recipies in
there:

A quick example (read on for more details):

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

  def do_craft(self, **kwargs):
    # performs the craft - report errors directly to user and return None (if
    # failed) and the created object(s) if successful.

  def post_craft(self, result, **kwargs):
    # any post-crafting effects. Always called, even if do_craft failed (the
    # result would be None then)

```

## Adding new recipes

A *recipe* is a class inheriting from
`evennia.contrib.crafting.crafting.CraftingRecipe`. This class implements the
most common form of crafting - that using in-game objects. Each recipe is a
separate class which gets initialized with the consumables/tools you provide.

For the `craft` command to find your custom recipes, you need to tell Evennia
where they are. Add a new line to your `mygame/server/conf/settings.py` file,
with a list to any new modules with recipe classes.

```python
CRAFT_RECIPE_MODULES = ["world.myrecipes"]
```

(You need to reload after adding this). All global-level classes in these
modules (whose names don't start with underscore) are considered by the system
as viable recipes.

Here we assume you created `mygame/world/myrecipes.py` to match the above
example setting:

```python
# in mygame/world/myrecipes.py

from evennia.contrib.crafting.crafting import CraftingRecipe

class WoodenPuppetRecipe(CraftingRecipe):
    """A puppet""""
    name = "wooden puppet"  # name to refer to this recipe as
    tool_tags = ["knife"]
    consumable_tags = ["wood"]
    output_prototypes = [
        {"key": "A carved wooden doll",
         "typeclass": "typeclasses.objects.decorations.Toys",
         "desc": "A small carved doll"}
    ]

```

This specifies which tags to look for in the inputs. It defines a
[Prototype](../Components/Prototypes.md) for the recipe to use to spawn the
result on the fly (a recipe could spawn more than one result if needed).
Instead of specifying the full prototype-dict, you could also just provide a
list of `prototype_key`s to existing prototypes you have.

After reloading the server, this recipe would now be available to use. To try it
we should create materials and tools to insert into the recipe.


The recipe analyzes inputs, looking for [Tags](../Components/Tags.md) with
specific tag-categories.  The tag-category used can be set per-recipe using the
(`.consumable_tag_category` and `.tool_tag_category` respectively). The defaults
are `crafting_material` and `crafting_tool`. For
the puppet we need one object with the `wood` tag and another with the `knife`
tag:

```python
from evennia import create_object

knife = create_object(key="Hobby knife", tags=[("knife", "crafting_tool")])
wood = create_object(key="Piece of wood", tags[("wood", "crafting_material")])
```

Note that the objects can have any name, all that matters is the
tag/tag-category. This means if a "bayonet" also had the "knife" crafting tag,
it could also be used to carve a puppet. This is also potentially interesting
for use in puzzles and to allow users to experiment and find alternatives to
know ingredients.

By the way, there is also a simple shortcut for doing this:

```
tools, consumables = WoodenPuppetRecipe.seed()
```

The `seed` class-method will create simple dummy objects that fulfills the
recipe's requirements. This is great for testing.

Assuming these objects were put in our inventory, we could now craft using the
in-game command:

```bash
> craft wooden puppet from wood using hobby knife
```
In code we would do

```python
from evennia.contrub.crafting.crafting import craft
puppet = craft(crafter, "wooden puppet", knife, wood)

```
In the call to `craft`, the order of `knife` and `wood` doesn't matter - the
recipe will sort out which is which based on their tags.

## Deeper customization of recipes

For customizing recipes further, it helps to understand how to use the
recipe-class directly:

```python
class MyRecipe(CraftingRecipe):
    # ...

tools, consumables = MyRecipe.seed()
recipe = MyRecipe(crafter, *(tools + consumables))
result = recipe.craft()

```
This is useful for testing and allows you to use the class directly without
adding it to a module in `settings.CRAFTING_RECIPE_MODULES`.

Even without modifying more than the class properties, there are a lot of
options to set on the `CraftingRecipe` class. Easiest is to refer to the
[CraftingRecipe api
documentation](evennia.contrib.game_systems.crafting.crafting.CraftingRecipe).  For example,
you can customize the validation-error messages, decide if the ingredients have
to be exactly right, if a failure still consumes the ingredients or not, and
much more.

For even more control you can override hooks in your own class:

- `pre_craft` - this should handle input validation and store its data in `.validated_consumables` and
  `validated_tools` respectively. On error, this reports the error to the crafter and raises the
  `CraftingValidationError`.
- `craft` - this will only be called if `pre_craft` finished without an exception. This should
  return the result of the crafting, by spawnging the prototypes. Or the empty list if crafting
  fails for some reason. This is the place to add skill-checks or random chance if you need it
  for your game.
- `post_craft` - this receives the result from `craft` and handles error messages and also deletes
  any consumables as needed. It may also modify the result before returning it.
- `msg` - this is a wrapper for `self.crafter.msg` and should be used to send messages to the
  crafter. Centralizing this means you can also easily modify the sending style in one place later.

The class constructor (and the `craft` access function) takes optional `**kwargs`. These are passed
into each crafting hook. These are unused by default but could be used to customize things per-call.

### Skilled crafters

What the crafting system does not have out of the box is a 'skill' system - the
notion of being able to fail the craft if you are not skilled enough. Just how
skills work is game-dependent, so to add this you need to make your own recipe
parent class and have your recipes inherit from this.


```python
from random import randint
from evennia.contrib.crafting.crafting import CraftingRecipe

class SkillRecipe(CraftingRecipe):
   """A recipe that considers skill"""

    difficulty = 20

    def craft(self, **kwargs):
        """The input is ok. Determine if crafting succeeds"""

        # this is set at initialization
        crafter = self.crafte

        # let's assume the skill is stored directly on the crafter
        # - the skill is 0..100.
        crafting_skill = crafter.db.skill_crafting
        # roll for success:
        if randint(1, 100) <= (crafting_skill - self.difficulty):
            # all is good, craft away
            return super().craft()
        else:
            self.msg("You are not good enough to craft this. Better luck next time!")
            return []
```
In this example we introduce a `.difficulty` for the recipe and makes a 'dice roll' to see
if we succed. We would of course make this a lot more immersive and detailed in a full game. In
principle you could customize each recipe just the way you want it, but you could also inherit from
a central parent like this to cut down on work.

The [sword recipe example module](evennia.contrib.game_systems.crafting.example_recipes) also shows an example
of a random skill-check being implemented in a parent and then inherited for multiple use.

## Even more customization

If you want to build something even more custom (maybe using different input types of validation logic)
you could also look at the `CraftingRecipe` parent class `CraftingRecipeBase`.
It implements just the minimum needed to be a recipe and for big changes you may be better off starting
from this rather than the more opinionated `CraftingRecipe`.

