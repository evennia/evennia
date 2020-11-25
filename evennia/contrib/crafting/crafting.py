"""
Crafting - Griatch 2020

This is a general crafting engine. The basic functionality of crafting is to
combine any number of of items in a 'recipe' to produce a new result. This is
useful not only for traditional crafting but also for puzzle-solving or
similar.

## Installation

- Create a new module and add it to a new list in your settings file
  (`server/conf/settings.py`) named `CRAFT_MODULE_RECIPES`.
- In the new module, create one or more classes, each a child of
  `CraftingRecipe` from this module. Each such class must have a unique `.name`
  property. It also defines what inputs are required and what is created using
  this recipe.
- Objects to use for crafting should (by default) be tagged with tags using the
  tag-category `crafting_material`. The name of the object doesn't matter, only
  its tag.
- Add the `CmdCraft` command from this module to your default cmdset. This is a
  very simple example-command (your real command will most likely need to do
  skill-checks etc!).

## Usage

By default the crafter needs to specify which components
should be used for the recipe:

    craft spiked club from club, nails

Here, `spiked club` specifies the recipe while `club` and `nails` are objects
the crafter must have in their inventory. These will be consumed during
crafting (by default only if crafting was successful).

A recipe can also require _tools_. These must be either in inventory or in
the current location. Tools are not consumed during the crafting.

    craft wooden doll from wood with knife

In code, you should use the helper function `craft` from this module. This
specifies the name of the recipe to use and expects all suitable
ingredients/tools as arguments (consumables and tools should be added together,
tools will be identified before consumables).

    spiked_club = craft(crafter, "spiked club", club, nails)

A fail leads to an empty return. The crafter should already have been notified
of any error in this case (this should be handle by the recipe itself).

## Recipes

A _recipe_ works like an input/output blackbox: you put consumables (and/or
tools) into it and if they match the recipe, a new result is spit out.
Consumables are consumed in the process while tools are not.

This module contains a base class for making new ingredient types
(`CraftingRecipeBase`) and an implementation of the most common form of
crafting (`CraftingRecipe`) using objects and prototypes.

Recipes are put in one or more modules added as a list to the
`CRAFT_MODULE_RECIPES` setting, for example:

    CRAFT_MODULE_RECIPES = ['world.recipes_weapons', 'world.recipes_potions']

Below is an example of a crafting recipe. See the `CraftingRecipe` class for
details of which properties and methods are available.

```python

    from evennia.contrib.crafting.crafting import CraftingRecipe

    class PigIronRecipe(CraftingRecipe):
        # Pig iron is a high-carbon result of melting iron in a blast furnace.

        name = "pig iron"
        tool_tags = ["blast furnace"]
        consumable_tags = ["iron ore", "coal", "coal"]
        output_prototypes = [
            {"key": "Pig Iron ingot",
             "desc": "An ingot of crude pig iron.",
             "tags": [("pig iron", "crafting_material")]}
        ]

```

The `evennia/contrib/crafting/example_recipes.py` module has more examples of
recipes.

----

"""

from copy import copy
from evennia.utils.utils import (
    iter_to_str, callables_from_module, inherits_from)
from evennia.prototypes.spawner import spawn
from evennia.utils.create import create_object

_RECIPE_CLASSES = {}


def _load_recipes():
    """
    Delayed loading of recipe classes. This parses
    `settings.CRAFT_RECIPE_MODULES`.

    """
    from django.conf import settings
    global _RECIPE_CLASSES
    if not _RECIPE_CLASSES:
        for path in settings.CRAFT_RECIPE_MODULES:
            for cls in callables_from_module(path):
                if inherits_from(cls, CraftingRecipe):
                    _RECIPE_CLASSES[cls.name] = cls


class CraftingError(RuntimeError):
    """
    Crafting error.

    """

class CraftingRecipeBase:
    """
    This is the base of the crafting system. The recipe handles all aspects of
    performing a 'craft' operation.

    Example of usage:
    ::

        recipe = CraftRecipe(crafter, obj1, obj2, obj3)
        result = recipe.craft()

    Note that the most common crafting operation is that the inputs are
    consumed - so in that case the recipe cannot be used a second time (doing so
    will raise a `CraftingError`)

    """
    name = "recipe base"

    # if set, allow running `.craft` more than once on the same instance.
    # don't set this unless crafting inputs are *not* consumed by the crafting
    # process (otherwise subsequent calls will fail).
    allow_reuse = False

    def __init__(self, crafter, *inputs, **kwargs):
        """
        Initialize the recipe.

        Args:
            crafter (Object): The one doing the crafting.
            *inputs (any): The ingredients of the recipe to use.
            **kwargs (any): Any other parameters that are relevant for
                this recipe.

        """
        self.crafter = crafter
        self.inputs = self.inputs
        self.craft_kwargs = kwargs
        self.allow_craft = True

    def msg(self, message, **kwargs):
        """
        Send message to crafter. This is a central point to override if wanting
        to change crafting return style in some way.

        Args:
            message(str): The message to send.
            **kwargs: Any optional properties relevant to this send.

        """
        self.crafter.msg(message, {"type": "crafting"})

    def validate_inputs(self, *inputs, **kwargs):
        """
        Hook to override.

        Make sure the provided inputs are valid. This should always be run.

        Args:
            inputs (any): Items to be tried. .
        Returns:
            list or None: Return whichever items were validated (some recipes
                may allow for partial/too many ingredients) or `None` if validation failed.

        Note:
            This method is also responsible for properly sending error messages
                to e.g. self.crafter (usually via `self.msg`).

        """
        if self.allow_craft:
            return self.inputs[:]

    def pre_craft(self, validated_inputs, **kwargs):
        """
        Hook to override.

        This is called just before crafting operation, after inputs have
        been validated.

        Args:
            validated_inputs (any): Data previously returned from `validate_inputs`.
            **kwargs (any): Passed from `self.craft`.

        Returns:
            any: The validated_inputs, modified or not.

        """
        if not validated_inputs:
            raise CraftingError()

        return validated_inputs

    def do_craft(self, validated_inputs, **kwargs):
        """
        Hook to override.

        This performs the actual crafting. At this point the inputs are
        expected to have been verified already.

        Args:
            validated_inputs (any): Data previously returned from `pre_craft`.
            kwargs (any): Passed from `self.craft`.

        Returns:
            any: The result of the crafting.

        """
        pass

    def post_craft(self, validated_inputs, craft_result, **kwargs):
        """
        Hook to override.

        This is called just after crafting has finished. A common use of
        this method is to delete the inputs.

        Args:
            validated_inputs (any): The inputs used as part of the crafting.
            craft_result (any): The crafted result, provided by `self.do_craft`.
            kwargs (any): Passed from `self.craft`.

        Returns:
            any: The return of the craft, possibly modified in this method.


        """
        return craft_result

    def craft(self, raise_exception=False, **kwargs):
        """
        Main crafting call method. Call this to produce a result and make
        sure all hooks run correctly.

        Args:
            raise_exception (bool): If crafting would return `None`, raise
                exception instead.
            **kwargs (any): Any other parameters that is relevant
                for this particular craft operation. This will temporarily
                override same-named kwargs given at the creation of this recipe
                and be passed into all of the crafting hooks.

        Returns:
            any: The result of the craft, or `None` if crafting failed.

        Raises:
            CraftingError: If crafting would return `None` and raise_exception`
                is set.

        """
        craft_result = None
        err = ""
        if self.allow_craft:
            craft_kwargs = copy(self.craft_kwargs)
            craft_kwargs.update(kwargs)

            try:
                # this assigns to self.validated_inputs
                validated_inputs = self.validate_inputs(*self.inputs, **craft_kwargs)

                # run the crafting process
                self.pre_craft(validated_inputs, **craft_kwargs)
                craft_result = self.do_craft(validated_inputs, **craft_kwargs)
                craft_result = self.post_craft(validated_inputs, craft_result, **craft_kwargs)
            except CraftingError as exc:
                # use this to abort crafting early
                if exc.message:
                    self.msg(exc.message)
            # possibly turn off re-use depending on class setting
            self.allow_craft = self.allow_reuse
        else:
            err = "Cannot re-run crafting without refreshing recipe first."
        if craft_result is None and raise_exception:
            raise CraftingError(err)
        return craft_result


class CraftingRecipe(CraftingRecipeBase):
    """
    The CraftRecipe implements the most common form of crafting: Combining (and
    optionally consuming) inputs to produce a new result. This type of recipe
    only works with typeclassed entities as inputs and outputs, since it's
    based on Tags and prototypes.

    There are two types of crafting ingredients: 'tools' and 'consumables'. The
    difference between them is that the former is not consumed in the crafting
    process. So if you need a hammer and anvil to craft a sword, they are 'tools'
    whereas the materials of the sword are 'consumables'.

    Examples:
    ::

        class SwordRecipe(CraftRecipe):
            name = "sword"
            input_tags = ["hilt", "pommel", "strips of leather", "sword blade"]
            output_prototypes = [
                {"key": "sword",
                 "typeclass": "typeclassess.weapons.bladed.Sword",
                 "tags": [("sword", "weapon"), ("melee", "weapontype"),
                          ("edged", "weapontype")]
                }
            ]

    ## Properties on the class level:

    - `name` (str): The name of this recipe. This should be globally unique.
    - `tool_tag_category` (str): What tag-category tools must use. Default is
      'crafting_tool'.
    - `consumable_tag_category` (str): What tag-category consumables must use.
      Default is 'crafting_material'.
    - `tool_tags` (list): Object-tags to use for tooling. If more than one instace
      of a tool is needed, add multiple entries here.

    ### cool-settings

    - `tool_names` (list): Human-readable names for tools. These are used for informative
      messages/errors. If not given, tags will be used. If given, this list should
      match the length of `tool_tags`.
    - `exact_tools` (bool, default True): Must have exactly the right tools, any extra
      leads to failure.
    - `exact_tool_order` (bool, default False): Tools must be added in exactly the
      right order for crafting to pass.

    ### consumables

    - `consumable_tags` (list): Tags for objects that will be consumed as part of
      running the recipe.
    - `consumable_names` (list): Human-readable names for consumables. Same as for tools.
    - `exact_consumables` (bool, default True): Normally, adding more consumables
      than needed leads to a a crafting error. If this is False, the craft will
      still succeed (only the needed ingredients will be consumed).
    - `exact_consumable_order` (bool, default False): Normally, the order in which
      ingredients are added does not matter. With this set, trying to add consumables in
      another order than given will lead to failing crafting.
    - `consume_on_fail` (bool, default False): Normally, consumables remain if
      crafting fails. With this flag, a failed crafting will still consume
      ingredients.

    ### outputs (result of crafting)

    - `output_prototypes` (list): One or more prototypes (`prototype_keys` or
      full dicts) describing how to create the result(s) of this recipe.
    - `output_names` (list): Human-readable names for (prospective) prototypes.
      This is used in error messages. If not given, this is extracted from the
      prototypes' `key` if possible.

    ### custom error messages

    custom messages all have custom formatting markers (default strings are shown):

        {missing}: Comma-separated list of components missing for missing/out of order errors.
        {inputs}: Comma-separated list of any inputs (tools + consumables) involved in error.
        {tools}: Comma-sepatated list of tools involved in error.
        {consumables}: Comma-separated list of consumables involved in error.
        {outputs}: Comma-separated list of (expected) outputs
        {t0}..{tN-1}: Individual tools, same order as `.tool_names`.
        {c0}..{cN-1}: Individual consumables, same order as `.consumable_names`.
        {o0}..{oN-1}: Individual outputs, same order as `.output_names`.

    - `error_tool_missing_message`: "Could not craft {outputs} without {missing}."
    - `error_tool_order_message`: "Could not craft {outputs} since
      {missing} was added in the wrong order."
    - `error_consumable_missing_message`: "Could not craft {outputs} without {missing}."
    - `error_consumable_order_message`: "Could not craft {outputs} since
      {missing} was added in the wrong order."
    - `success_message`: "You successfuly craft {outputs}!"
    - `failed_message`: "You failed to craft {outputs}."

    ## Hooks

    1. Crafting starts by calling `.craft` on the parent class.
    2. `.validate_inputs` is called. This returns all valid `(tools, consumables)`
    3. `.pre_craft` is called with the valid `(tools, consumables)`.
    4. `.do_craft` is called, it should return the final result, if any
    5. `.post_craft` is called with both inputs and final result, if any. It should
        return the final result or None. By default, this calls the
        success/error messages and deletes consumables.

    Use `.msg` to conveniently send messages to the crafter. Raise
    `evennia.contrib.crafting.crafting.CraftingError` exception to abort
    crafting at any time in the sequence. If raising with a text, this will be
    shown to the crafter automatically

    """
    name = "crafting recipe"

    # this define the overall category all material tags must have
    consumable_tag_category = "crafting_material"
    # tag category for tool objects
    tool_tag_category = "crafting_tool"

    # the tools needed to perform this crafting. Tools are never consumed (if they were,
    # they'd need to be a consumable). If more than one instance of a tool is needed,
    # there should be multiple entries in this list.
    tool_tags = []
    # human-readable names for the tools. This will be used for informative messages
    # or when usage fails. If empty
    tool_names = []
    # if we must have exactly the right tools, no more
    exact_tools = True
    # if the order of the tools matters
    exact_tool_order = False
    # error to show if missing tools
    error_tool_missing_message = "Could not craft {outputs} without {missing}."
    # error to show if tool-order matters and it was wrong. Missing is the first
    # tool out of order
    error_tool_order_message = \
        "Could not craft {outputs} since {missing} was added in the wrong order."

    # a list of tag-keys (of the `tag_category`). If more than one of each type
    # is needed, there should be multiple same-named entries in this list.
    consumable_tags = []
    # these are human-readable names for the items to use. This is used for informative
    # messages or when usage fails. If empty, the tag-names will be used. If given, this
    # must have the same length as `consumable_tags`.
    consumable_names = []
    # if True, consume valid inputs also if crafting failed (returned None)
    consume_on_fail = False
    # if True, having any wrong input result in failing the crafting. If False,
    # extra components beyond the recipe are ignored.
    exact_consumables = True
    # if True, the exact order in which inputs are provided matters and must match
    # the order of `consumable_tags`. If False, order doesn't matter.
    exact_consumable_order = False
    # error to show if missing consumables
    error_consumable_missing_message = "Could not craft {outputs} without {missing}."
    # error to show if consumable order matters and it was wrong. Missing is the first
    # consumable out of order
    error_consumable_order_message = \
        "Could not craft {outputs} since {missing} was added in the wrong order."

    # this is a list of one or more prototypes (prototype_keys to existing
    # prototypes or full prototype-dicts) to use to build the result. All of
    # these will be returned (as a list) if crafting succeeded.
    output_prototypes = []
    # human-readable name(s) for the (expected) result of this crafting. This will usually only
    # be used for error messages (to report what would have been). If not given, the
    # prototype's key or typeclass will be used. If given, this must have the same length
    # as `output_prototypes`.
    output_names = []

    success_message = "You successfully craft {outputs}!"
    # custom craft-failure.
    failed_message = "Failed to craft {outputs}."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.consumable_names:
            assert len(self.consumable_names) == len(self.consumable_tags), \
                "Crafting .consumable_names list must have the same length as .consumable_tags."
        else:
            self.consumable_names = self.consumable_tags
        if self.output_names:
            assert len(self.consumable_names) == len(self.consumable_tags), \
                "Crafting .output_names list must have the same length as .output_prototypes."
        else:
            self.output_names = [
                prot.get("key", prot.get("typeclass"), "unnamed")
                for prot in self.output_prototypes]

        self.allow_reuse = not self.consume_inputs

    def _format_message(self, message, **kwargs):

        missing = iter_to_str(kwargs.get("missing", "nothing"))

        # build template context
        mapping = {"missing": iter_to_str(missing)}
        mapping.update({
            f"i{ind}": self.consumable_names[ind]
            for ind, name in enumerate(self.consumable_names.values())
        })
        mapping.update({
            f"o{ind}": self.output_names[ind]
            for ind, name in enumerate(self.output_names.values())
        })
        mapping["inputs"] = iter_to_str(self.consumable_names)
        mapping["outputs"] = iter_to_str(self.output_names)

        # populate template and return
        return message.format(**mapping)

    def seed(self, tool_kwargs=None, consumable_kwargs=None):
        """
        This is a helper method for easy testing and application of this
        recipe. When called, it will create simple dummy ingredients with
        names and tags needed by this recipe.

        Args:
            consumable_kwargs (dict, optional): This will be passed as
                `**kwargs` into the `create_object` call for each consumable.
                If not given, matching `consumable_name` or `consumable_tag`
                will  be used for key.
            tool_kwargs (dict, optional): Will be passed as `**kwargs` into the `create_object`
                call for each tool.  If not given, the matching
                `tool_name` or `tool_tag` will  be used for key.

        Returns:
            tuple: A tuple `(tools, consumables)` with newly created dummy
            objects matching the recipe ingredient list.

        Notes:
            If `key` is given in `consumable/tool_kwargs` then _every_ created item
            of each type will have the same key.

        """
        if not tool_kwargs:
            tool_kwargs = {}
        if not consumable_kwargs:
            consumable_kwargs = {}
        tool_key = tool_kwargs.pop("key", None)
        cons_key = consumable_kwargs.pop("key", None)
        tool_tags = tool_kwargs.pop("tags", [])
        cons_tags = consumable_kwargs.pop("tags", [])

        tools = []
        for itag, tag in enumerate(self.tool_tags):
            tools.append(
                create_object(
                    key=tool_key or (self.tool_names[itag] if self.tool_names
                                     else tag.capitalize()),
                    tags=[(tag, self.tool_tag_category), *tool_tags],
                    **tool_kwargs
                )
            )
        consumables = []
        for itag, tag in enumerate(self.consumable_tags):
            consumables.append(
                create_object(
                    key=cons_key or (self.consumable_names[itag] if
                                     self.consumable_names else
                                     tag.capitalize()),
                    tags=[(tag, self.consumable_tag_category), *cons_tags]

                )
            )
        return tools, consumables

    def validate_inputs(self, *inputs, **kwargs):
        """
        Check so the given inputs are what is needed.

        Note that on successful validation we return a tuple `(tools, consumables)`.

        """

        def _check_completeness(
                tagmap, taglist, namelist, exact_match, exact_order,
                error_missing_message, error_order_message):
            """Compare tagmap to taglist"""
            valids = []
            for itag, tagkey in enumerate(taglist):
                found_obj = None
                for obj, taglist in tagmap.items():
                    if tagkey in taglist:
                        found_obj = obj
                        break
                    if exact_match:
                        # if we get here, we have a no-match
                        self.msg(self._format_message(
                            error_missing_message,
                            missing=namelist[itag] if namelist else tagkey.capitalize()))
                        return []
                    if exact_order:
                        # if we get here order is wrong
                        self.msg(self._format_message(
                            error_order_message,
                            missing=namelist[itag] if namelist else tagkey.capitalize()))
                        return []

                # since we pop from the mapping, it gets ever shorter
                match = tagmap.pop(found_obj, None)
                if match:
                    valids.append(match)
            return valids

        # get tools and consumables from inputs from
        tool_map = {obj: obj.tags.get(category=self.tool_tag_category, return_list=True)
                    for obj in inputs if obj and hasattr(obj, "tags")}
        consumable_map = {obj: obj.tags.get(category=self.tag_category, return_list=True)
                          for obj in inputs
                          if obj and hasattr(obj, "tags") and obj not in tool_map}

        tools = _check_completeness(
            tool_map,
            self.tool_tags,
            self.tool_names,
            self.exact_tools,
            self.exact_tool_order,
            self.error_tool_message,
            self.error_tool_order_message
        )
        consumables = _check_completeness(
            consumable_map,
            self.consumable_tags,
            self.consumable_names,
            self.exact_consumables,
            self.exact_consumable_order,
            self.error_consumable_missing_message,
            self.error_consumable_order_message
        )
        # regardless of flags, the tools/consumable lists much contain exactly
        # all the recipe needs now.
        if (len(tools) == len(self.tool_tags) and len(consumables) == len(self.consumable_tags)):
            return tools, consumables
        return None

    # including also empty hooks here for easier reference

    def pre_craft(self, validated_inputs, **kwargs):
        """
        Hook to override.

        This is called just before crafting operation, after inputs have
        been validated.

        Args:
            validated_inputs (tuple): Data previously returned from
                `validate_inputs`. This is a tuple `(tools, consumables)`.
            **kwargs (any): Passed from `self.craft`.

        Returns:
            any: The validated_inputs, modified or not.

        """
        if not validated_inputs:
            # abort crafting here, remove if wanting some other action
            raise CraftingError(f"Crafting validation error {self.name}")

        return validated_inputs

    def do_craft(self, validated_inputs, **kwargs):
        """
        Hook to override.

        This performs the actual crafting. At this point the inputs are
        expected to have been verified already.

        Args:
            validated_inputs (tuple): A tuple `(tools, consumables)`.

        Returns:
            list: A list of spawned objects created from the inputs.

        Notes:
            We may want to analyze the tools in some way here to affect the
            crafting process.

        """
        return spawn(*self.output_prototypes)

    def post_craft(self, validated_inputs, craft_result, **kwargs):
        """
        Hook to override.

        This is called just after crafting has finished. A common use of
        this method is to delete the inputs.

        Args:
            validated_inputs (tuple): the validated inputs, a tuple `(tools, consumables)`.
            craft_result (any): The crafted result, provided by `self.do_craft`.
            **kwargs (any): Passed from `self.craft`.


        Returns:
            any: The return of the craft, possibly modified in this method.


        """
        consume = self.consume_inputs

        _, consumables = validated_inputs or (None, None)

        if craft_result:
            self.msg(self._format_message(self.success_message))
        else:
            self.msg(self._format_message(self.failure_message))
            consume = self.consume_on_fail

        if consume and consumables:
            # consume the inputs
            for obj in consumables:
                obj.delete()

        return craft_result


# access functions


def craft(crafter, recipe_name, *inputs, raise_exception=False, **kwargs):
    """
    Craft a given recipe from a source recipe module. A recipe module is a
    Python module containing recipe classes. Note that this requires
    `settings.CRAFT_RECIPE_MODULES` to be added to a list of one or more
    python-paths to modules holding Recipe-classes.

    Args:
        crafter (Object): The one doing the crafting.
        recipe_name (str): This should match the `CraftRecipe.name` to use.
        *inputs: Suitable ingredients (Objects) to use in the crafting.
        raise_exception (bool, optional): If crafting failed for whatever
            reason, raise `CraftingError`.
        **kwargs: Optional kwargs to pass into the recipe (will passed into recipe.craft).

    Returns:
        list: Crafted objects, if any.

    Raises:
        CraftingError: If `raise_exception` is True and crafting failed to produce an output.
        KeyError: If `recipe_name` failed to find a matching recipe class.

    Notes:
        If no recipe_module is given, will look for a list `settings.CRAFT_RECIPE_MODULES` and
        lastly fall back to the example module `"evennia.contrib."`

    """
    # delayed loading/caching of recipes
    _load_recipes()

    RecipeClass = _RECIPE_CLASSES.get(recipe_name, None)
    if not RecipeClass:
        raise KeyError("No recipe in settings.CRAFT_RECIPE_MODULES "
                       f"has a name matching {recipe_name}")
    recipe = RecipeClass(crafter, *inputs, **kwargs)
    return recipe.craft(raise_exception=raise_exception)
