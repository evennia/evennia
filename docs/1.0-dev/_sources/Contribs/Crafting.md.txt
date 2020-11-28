# Crafting system contrib 

_Contrib by Griatch 2020_
```versionadded:: 1.0
```

This contrib implements a full Crafting system that can be expanded and modified to fit your game. 

- See the [evennia/contrib/crafting/crafting.py API](api:evennia.contrib.crafting.crafting) for installation 
  instructrions.
- See the [sword example](api:evennia.contrib.crafting.example_recipes) for an example of how to design 
  a crafting tree for crafting a sword from base elements.

From in-game it uses the new `craft` command: 

```bash
> craft bread from flour, eggs, salt, water, yeast using oven, roller
> craft bandage from cloth using scissors
```

The syntax is `craft <recipe> [from <ingredient>,...][ using <tool>,...]`. 

The above example uses the `bread` *recipe* and requires `flour`, `eggs`, `salt`, `water` and `yeast` objects 
to be in your inventory. These will be consumed as part of crafting (baking) the bread. 

The `oven` and `roller` are "tools" that can be either in your inventory or in your current location (you are not carrying an oven 
around with you after all). Tools are *not* consumed in the crafting. If the added ingredients/tools matches 
the requirements of the recipe, a new `bread` object will appear in the crafter's inventory.

If you wanted, you could also picture recipes without any consumables: 

```
> craft fireball using wand, spellbook
```

With a little creativity, the 'recipe' concept could be adopted to all sorts of things, like puzzles or 
magic systems.

In code, you can craft using the `evennia.contrib.crafting.crafting.craft` function:

```python
from evennia.contrib.crafting.crafting import craft

result = craft(caller, *inputs)

```
Here, `caller` is the one doing the crafting and `*inputs` is any combination of consumables and/or tool
Objects. The system will identify which is which by the [Tags](../Components/Tags) on them (see below)
The `result` is always a list. 

## Adding new recipes

A *recipe* is a class inheriting from `evennia.contrib.crafting.crafting.CraftingRecipe`. This class
implements the most common form of crafting - that using in-game objects. Each recipe is a separate class
which gets initialized with the consumables/tools you provide. 

For the `craft` command to find your custom recipes, you need to tell Evennia where they are. Add a new 
line to your `mygame/server/conf/settings.py` file, with a list to any new modules with recipe classes.

```python
CRAFT_RECIPE_MODULES = ["world.myrecipes"]
```

(You need to reload after adding this). All global-level classes in these modules (whose names don't start 
with underscore) are considered by the system as viable recipes.

Here we assume you created `mygame/world/myrecipes.py` to match the above example setting:

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

This specifies which tags to look for in the inputs. It defines a [Prototype](../Components/Prototypes) 
for the recipe to use to spawn the result on the fly (a recipe could spawn more than one result if needed). 
Instead of specifying the full prototype-dict, you could also just provide a list of `prototype_key`s to 
existing prototypes you have.

After reloading the server, this recipe would now be available to use. To try it we should 
create materials and tools to insert into the recipe. 


The recipe analyzes inputs, looking for [Tags](../Components/Tags) with specific tag-categories. 
The tag-category used can be set per-recipe using the (`.consumable_tag_category` and 
`.tool_tag_category` respectively). The defaults are `crafting_material` and `crafting_tool`. For 
the puppet we need one object with the `wood` tag and another with the `knife` tag: 

```python
from evennia import create_object

knife = create_object(key="Hobby knife", tags=[("knife", "crafting_tool")])
wood = create_object(key="Piece of wood", tags[("wood", "crafting_material")])
```

Note that the objects can have any name, all that matters is the tag/tag-category. This means if a 
"bayonet" also had the "knife" crafting tag, it could also be used to carve a puppet. This is also 
potentially interesting for use in puzzles and to allow users to experiment and find alternatives to 
know ingredients.

By the way, there is also a simple shortcut for doing this:

```
tools, consumables = WoodenPuppetRecipe.seed()
```

The `seed` class-method will create simple dummy objects that fulfills the recipe's requirements. This 
is great for testing.

Assuming these objects were put in our inventory, we could now craft using the in-game command: 

```bash
> craft wooden puppet from wood using hobby knife
```
In code we would do 

```python
from evennia.contrub.crafting.crafting import craft
puppet = craft(crafter, "wooden puppet", knife, wood)

```
In the call to `craft`, the order of `knife` and `wood` doesn't matter - the recipe will sort out which
is which based on their tags. 

## Deeper customization of recipes

For customizing recipes further, it helps to understand how to use the recipe-class directly:

```python
class MyRecipe(CraftingRecipe):
    # ...

tools, consumables = MyRecipe.seed()
recipe = MyRecipe(crafter, *(tools + consumables))
result = recipe.craft()

```
This is useful for testing and allows you to use the class directly without adding it to a module 
in `settings.CRAFTING_RECIPE_MODULES`. 

Even without modifying more than the class properties, there are a lot of options to set on 
the `CraftingRecipe` class. Easiest is to refer to the 
[CraftingRecipe api documentation](evennia.contrib.crafting.crafting.html#evennia.contrib.crafting.crafting.CraftingRecipe).
For example, you can customize the validation-error messages, decide if the ingredients have 
to be exactly right, if a failure still consumes the ingredients or not, and much more.

For even more control you can override hooks in your own class:

- `pre_craft` - this should handle input validation and store its data in `.validated_consumables` and 
  `validated_tools` respectively. On error, this reports the error to the crafter and raises the
  `CraftingValidationError`.
- `do_craft` - this will only be called if `pre_craft` finished without an exception. This should 
  return the result of the crafting, by spawnging the prototypes. Or the empty list if crafting 
  fails for some reason. This is the place to add skill-checks or random chance if you need it 
  for your game. 
- `post_craft` - this receives the result from `do_craft` and handles error messages and also deletes
  any consumables as needed. It may also modify the result before returning it.
- `msg` - this is a wrapper for `self.crafter.msg` and should be used to send messages to the 
  crafter. Centralizing this means you can also easily modify the sending style in one place later.

The class constructor (and the `craft` access function) takes optional `**kwargs`. These are passed 
into each crafting hook. These are unused by default but could be used to customize things per-call.

### Skilled crafters

What the crafting system does not have out of the box is a 'skill' system - the notion of being able 
to fail the craft if you are not skilled enough. Just how skills work is game-dependent, so to add 
this you need to make your own recipe parent class and have your recipes inherit from this.


```python
from random import randint
from evennia.contrib.crafting.crafting import CraftingRecipe

class SkillRecipe(CraftingRecipe):
   """A recipe that considers skill"""

    difficulty = 20

    def do_craft(self, **kwargs):
        """The input is ok. Determine if crafting succeeds"""

        # this is set at initialization
        crafter = self.crafte

        # let's assume the skill is stored directly on the crafter
        # - the skill is 0..100.
        crafting_skill = crafter.db.skill_crafting
        # roll for success:
        if randint(1, 100) <= (crafting_skill - self.difficulty):
            # all is good, craft away
            return super().do_craft()
        else:
            self.msg("You are not good enough to craft this. Better luck next time!")
            return []
```
In this example we introduce a `.difficulty` for the recipe and makes a 'dice roll' to see 
if we succed. We would of course make this a lot more immersive and detailed in a full game. In 
principle you could customize each recipe just the way you want it, but you could also inherit from 
a central parent like this to cut down on work. 

The [sword recipe example module](api:evennia.contrib.crafting.example_recipes) also shows an example
of a random skill-check being implemented in a parent and then inherited for multiple use.

## Even more customization

If you want to build something even more custom (maybe using different input types of validation logic)
you could also look at the `CraftingRecipe` parent class `CraftingRecipeBase`.
It implements just the minimum needed to be a recipe and for big changes you may be better off starting 
from this rather than the more opinionated `CraftingRecipe`.