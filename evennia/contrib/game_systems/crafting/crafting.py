"""
Crafting - Griatch 2020

This is a general crafting engine. The basic functionality of crafting is to
combine any number of of items or tools in a 'recipe' to produce a new result.

    item + item + item + tool + tool  -> recipe -> new result

This is useful not only for traditional crafting but the engine is flexible
enough to also be useful for puzzles or similar.

## Installation

- Add the `CmdCraft` Command from this module to your default cmdset. This
  allows for crafting from in-game using a simple syntax.
- Create a new module and add it to a new list in your settings file
  (`server/conf/settings.py`) named `CRAFT_RECIPES_MODULES`, such as
  `CRAFT_RECIPE_MODULES = ["world.recipes_weapons"]`.
- In the new module(s), create one or more classes, each a child of
  `CraftingRecipe` from this module. Each such class must have a unique `.name`
  property. It also defines what inputs are required and what is created using
  this recipe.
- Objects to use for crafting should (by default) be tagged with tags using the
  tag-category `crafting_material` or `crafting_tool`. The name of the object
  doesn't matter, only its tag.

## Crafting in game

The default `craft` command handles all crafting needs.
::

    > craft spiked club from club, nails

Here, `spiked club` specifies the recipe while `club` and `nails` are objects
the crafter must have in their inventory. These will be consumed during
crafting (by default only if crafting was successful).

A recipe can also require *tools* (like the `hammer` above). These must be
either in inventory *or* be in the current location. Tools are *not* consumed
during the crafting process.
::

    > craft wooden doll from wood with knife

## Crafting in code

In code, you should use the helper function `craft` from this module. This
specifies the name of the recipe to use and expects all suitable
ingredients/tools as arguments (consumables and tools should be added together,
tools will be identified before consumables).

```python

    from evennia.contrib.game_systems.crafting import crafting

    spiked_club = crafting.craft(crafter, "spiked club", club, nails)

```

The result is always a list with zero or more objects. A fail leads to an empty
list. The crafter should already have been notified of any error in this case
(this should be handle by the recipe itself).

## Recipes

A *recipe* is a class that works like an input/output blackbox: you initialize
it with consumables (and/or tools) if they match the recipe, a new
result is spit out.  Consumables are consumed in the process while tools are not.

This module contains a base class for making new ingredient types
(`CraftingRecipeBase`) and an implementation of the most common form of
crafting (`CraftingRecipe`) using objects and prototypes.

Recipes are put in one or more modules added as a list to the
`CRAFT_RECIPE_MODULES` setting, for example:

```python

    CRAFT_RECIPE_MODULES = ['world.recipes_weapons', 'world.recipes_potions']

```

Below is an example of a crafting recipe and how `craft` calls it under the
hood. See the `CraftingRecipe` class for details of which properties and
methods are available to override - the craft behavior can be modified
substantially this way.

```python

    from evennia.contrib.game_systems.crafting.crafting import CraftingRecipe

    class PigIronRecipe(CraftingRecipe):
        # Pig iron is a high-carbon result of melting iron in a blast furnace.

        name = "pig iron"  # this is what crafting.craft and CmdCraft uses
        tool_tags = ["blast furnace"]
        consumable_tags = ["iron ore", "coal", "coal"]
        output_prototypes = [
            {"key": "Pig Iron ingot",
             "desc": "An ingot of crude pig iron.",
             "tags": [("pig iron", "crafting_material")]}
        ]

    # for testing, conveniently spawn all we need based on the tags on the class
    tools, consumables = PigIronRecipe.seed()

    recipe = PigIronRecipe(caller, *(tools + consumables))
    result = recipe.craft()

```

If the above class was added to a module in `CRAFT_RECIPE_MODULES`, it could be
called using its `.name` property, as "pig iron".

The [example_recipies](api:evennia.contrib.game_systems.crafting.example_recipes) module has
a full example of the components for creating a sword from base components.

----

"""

import functools
from copy import copy

from evennia.commands.cmdset import CmdSet
from evennia.commands.command import Command
from evennia.prototypes.spawner import spawn
from evennia.utils.create import create_object
from evennia.utils.utils import (
    callables_from_module,
    inherits_from,
    iter_to_str,
    make_iter,
)

_RECIPE_CLASSES = {}


def _load_recipes():
    """
    Delayed loading of recipe classes. This parses
    `settings.CRAFT_RECIPE_MODULES`.

    """
    from django.conf import settings

    global _RECIPE_CLASSES
    if not _RECIPE_CLASSES:
        paths = ["evennia.contrib.game_systems.crafting.example_recipes"]
        if hasattr(settings, "CRAFT_RECIPE_MODULES"):
            paths += make_iter(settings.CRAFT_RECIPE_MODULES)
        for path in paths:
            for cls in callables_from_module(path).values():
                if inherits_from(cls, CraftingRecipeBase):
                    _RECIPE_CLASSES[cls.name] = cls


class CraftingError(RuntimeError):
    """
    Crafting error.

    """


class CraftingValidationError(CraftingError):
    """
    Error if crafting validation failed.

    """


class CraftingRecipeBase:
    """
    The recipe handles all aspects of performing a 'craft' operation. This is
    the base of the crafting system, intended to be replace if you want to
    adapt it for very different functionality - see the `CraftingRecipe` child
    class for an implementation of the most common type of crafting using
    objects.

    Example of usage:
    ::

        recipe = CraftRecipe(crafter, obj1, obj2, obj3)
        result = recipe.craft()

    Note that the most common crafting operation is that the inputs are
    consumed - so in that case the recipe cannot be used a second time (doing so
    will raise a `CraftingError`)

    Process:

    1. `.craft(**kwargs)` - this starts the process on the initialized recipe. The kwargs
       are optional but will be passed into all of the following hooks.
    2. `.pre_craft(**kwargs)` - this normally validates inputs and stores them in
       `.validated_inputs.`. Raises `CraftingValidationError` otherwise.
    4. `.do_craft(**kwargs)` - should return the crafted item(s) or the empty list. Any
       crafting errors should be immediately reported to user.
    5. `.post_craft(crafted_result, **kwargs)`- always called, even if `pre_craft`
       raised a `CraftingError` or `CraftingValidationError`.
       Should return `crafted_result` (modified or not).


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
        self.inputs = inputs
        self.craft_kwargs = kwargs
        self.allow_craft = True
        self.validated_inputs = []

    def msg(self, message, **kwargs):
        """
        Send message to crafter. This is a central point to override if wanting
        to change crafting return style in some way.

        Args:
            message(str): The message to send.
            **kwargs: Any optional properties relevant to this send.

        """
        self.crafter.msg(message, {"type": "crafting"})

    def pre_craft(self, **kwargs):
        """
        Hook to override.

        This is called just before crafting operation and is normally
        responsible for validating the inputs, storing data on
        `self.validated_inputs`.

        Args:
            **kwargs: Optional extra flags passed during initialization or
            `.craft(**kwargs)`.

        Raises:
            CraftingValidationError: If validation fails.

        """
        if self.allow_craft:
            self.validated_inputs = self.inputs[:]
        else:
            raise CraftingValidationError

    def do_craft(self, **kwargs):
        """
        Hook to override.

        This performs the actual crafting. At this point the inputs are
        expected to have been verified already. If needed, the validated
        inputs are available on this recipe instance.

        Args:
            **kwargs: Any extra flags passed at initialization.

        Returns:
            any: The result of crafting.

        """
        return None

    def post_craft(self, crafting_result, **kwargs):
        """
        Hook to override.

        This is called just after crafting has finished. A common use of this
        method is to delete the inputs.

        Args:
            crafting_result (any): The outcome of crafting, as returned by `do_craft`.
            **kwargs: Any extra flags passed at initialization.

        Returns:
            any: The final crafting result.

        """
        return crafting_result

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
            CraftingValidationError: If recipe validation failed and
                `raise_exception` is True.
            CraftingError: On If trying to rerun a no-rerun recipe, or if crafting
                would return `None` and raise_exception` is set.

        """
        craft_result = None
        if self.allow_craft:

            # override/extend craft_kwargs from initialization.
            craft_kwargs = copy(self.craft_kwargs)
            craft_kwargs.update(kwargs)

            try:
                try:
                    # this assigns to self.validated_inputs
                    self.pre_craft(**craft_kwargs)
                except (CraftingError, CraftingValidationError):
                    if raise_exception:
                        raise
                else:
                    craft_result = self.do_craft(**craft_kwargs)
                finally:
                    craft_result = self.post_craft(craft_result, **craft_kwargs)
            except (CraftingError, CraftingValidationError):
                if raise_exception:
                    raise

            # possibly turn off re-use depending on class setting
            self.allow_craft = self.allow_reuse
        elif not self.allow_reuse:
            raise CraftingError("Cannot re-run crafting without re-initializing recipe first.")
        if craft_result is None and raise_exception:
            raise CraftingError(f"Crafting of {self.name} failed.")
        return craft_result


class NonExistentRecipe(CraftingRecipeBase):
    """A recipe that does not exist and never produces anything."""

    allow_craft = True
    allow_reuse = True

    def __init__(self, crafter, *inputs, name="", **kwargs):
        super().__init__(crafter, *inputs, **kwargs)
        self.name = name

    def pre_craft(self, **kwargs):
        msg = f"Unknown recipe '{self.name}'"
        self.msg(msg)
        raise CraftingError(msg)


class CraftingRecipe(CraftingRecipeBase):
    """
    The CraftRecipe implements the most common form of crafting: Combining (and
    consuming) inputs to produce a new result. This type of recipe only works
    with typeclassed entities as inputs and outputs, since it's based on Tags
    and Prototypes.

    There are two types of crafting ingredients: 'tools' and 'consumables'. The
    difference between them is that the former is not consumed in the crafting
    process. So if you need a hammer and anvil to craft a sword, they are
    'tools' whereas the materials of the sword are 'consumables'.

    Examples:
    ::

        class FlourRecipe(CraftRecipe):
            name = "flour"
            tool_tags = ['windmill']
            consumable_tags = ["wheat"]
            output_prototypes = [
                {"key": "Bag of flour",
                 "typeclass": "typeclasses.food.Flour",
                 "desc": "A small bag of flour."
                 "tags": [("flour", "crafting_material"),
                }

        class BreadRecipe(CraftRecipe):
            name = "bread"
            tool_tags = ["roller", "owen"]
            consumable_tags = ["flour", "egg", "egg", "salt", "water", "yeast"]
            output_prototypes = [
                {"key": "bread",
                 "desc": "A tasty bread."
                }


    ## Properties on the class level:

    - `name` (str): The name of this recipe. This should be globally unique.

    ### tools

    - `tool_tag_category` (str): What tag-category tools must use. Default is
      'crafting_tool'.
    - `tool_tags` (list): Object-tags to use for tooling. If more than one instace
      of a tool is needed, add multiple entries here.
    - `tool_names` (list): Human-readable names for tools. These are used for informative
      messages/errors. If not given, the tags will be used. If given, this list should
      match the length of `tool_tags`.:
    - `exact_tools` (bool, default True): Must have exactly the right tools, any extra
      leads to failure.
    - `exact_tool_order` (bool, default False): Tools must be added in exactly the
      right order for crafting to pass.

    ### consumables

    - `consumable_tag_category` (str): What tag-category consumables must use.
      Default is 'crafting_material'.
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
      consumables. Note that this will also consume any 'extra' consumables
      added not part of the recipe!

    ### outputs (result of crafting)

    - `output_prototypes` (list): One or more prototypes (`prototype_keys` or
      full dicts) describing how to create the result(s) of this recipe.
    - `output_names` (list): Human-readable names for (prospective) prototypes.
      This is used in error messages. If not given, this is extracted from the
      prototypes' `key` if possible.

    ### custom error messages

    custom messages all have custom formatting markers. Many are empty strings
    when not applicable.
    ::

        {missing}: Comma-separated list of tool/consumable missing for missing/out of order errors.
        {excess}: Comma-separated list of tool/consumable added in excess of recipe
        {inputs}: Comma-separated list of any inputs (tools + consumables) involved in error.
        {tools}: Comma-sepatated list of tools involved in error.
        {consumables}: Comma-separated list of consumables involved in error.
        {outputs}: Comma-separated list of (expected) outputs
        {t0}..{tN-1}: Individual tools, same order as `.tool_names`.
        {c0}..{cN-1}: Individual consumables, same order as `.consumable_names`.
        {o0}..{oN-1}: Individual outputs, same order as `.output_names`.

    - `error_tool_missing_message`: "Could not craft {outputs} without {missing}."
    - `error_tool_order_message`:
      "Could not craft {outputs} since {missing} was added in the wrong order."
    - `error_tool_excess_message`: "Could not craft {outputs} (extra {excess})."
    - `error_consumable_missing_message`: "Could not craft {outputs} without {missing}."
    - `error_consumable_order_message`:
      "Could not craft {outputs} since {missing} was added in the wrong order."
    - `error_consumable_excess_message`: "Could not craft {outputs} (excess {excess})."
    - `success_message`: "You successfuly craft {outputs}!"
    - `failure_message`: ""  (this is handled by the other error messages by default)

    ## Hooks

    1. Crafting starts by calling `.craft(**kwargs)` on the parent class. The
       `**kwargs` are optional, extends any `**kwargs` passed to the class
       constructor and will be passed into all the following hooks.
    3. `.pre_craft(**kwargs)` should handle validation of inputs. Results should
       be stored in `validated_consumables/tools` respectively. Raises `CraftingValidationError`
       otherwise.
    4. `.do_craft(**kwargs)` will not be called if validation failed. Should return
       a list of the things crafted.
    5. `.post_craft(crafting_result, **kwargs)` is always called, also if validation
       failed (`crafting_result` will then be falsy). It does any cleanup. By default
       this deletes consumables.

    Use `.msg` to conveniently send messages to the crafter. Raise
    `evennia.contrib.game_systems.crafting.crafting.CraftingError` exception to abort
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
    # or when usage fails. If empty, use tag-names.
    tool_names = []
    # if we must have exactly the right tools, no more
    exact_tools = True
    # if the order of the tools matters
    exact_tool_order = False
    # error to show if missing tools
    error_tool_missing_message = "Could not craft {outputs} without {missing}."
    # error to show if tool-order matters and it was wrong. Missing is the first
    # tool out of order
    error_tool_order_message = (
        "Could not craft {outputs} since {missing} was added in the wrong order."
    )
    # if .exact_tools is set and there are more than needed
    error_tool_excess_message = (
        "Could not craft {outputs} without the exact tools (extra {excess})."
    )

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
    error_consumable_order_message = (
        "Could not craft {outputs} since {missing} was added in the wrong order."
    )
    # if .exact_consumables is set and there are more than needed
    error_consumable_excess_message = (
        "Could not craft {outputs} without the exact ingredients (extra {excess})."
    )

    # this is a list of one or more prototypes (prototype_keys to existing
    # prototypes or full prototype-dicts) to use to build the result. All of
    # these will be returned (as a list) if crafting succeeded.
    output_prototypes = []
    # human-readable name(s) for the (expected) result of this crafting. This will usually only
    # be used for error messages (to report what would have been). If not given, the
    # prototype's key or typeclass will be used. If given, this must have the same length
    # as `output_prototypes`.
    output_names = []
    # general craft-failure msg to show after other error-messages.
    failure_message = ""
    # show after a successful craft
    success_message = "You successfully craft {outputs}!"

    def __init__(self, crafter, *inputs, **kwargs):
        """
        Args:
            crafter (Object): The one doing the crafting.
            *inputs (Object): The ingredients (+tools) of the recipe to use. The
                The recipe will itself figure out (from tags) which is a tool and
                which is a consumable.
            **kwargs (any): Any other parameters that are relevant for
                this recipe. These will be passed into the crafting hooks.

        Notes:
            Internally, this class stores validated data in
            `.validated_consumables`  and `.validated_tools` respectively. The
            `.validated_inputs` property (from parent) holds a list of everything
            types in the order inserted to the class constructor.

        """

        super().__init__(crafter, *inputs, **kwargs)

        self.validated_consumables = []
        self.validated_tools = []

        # validate class properties
        if self.consumable_names:
            assert len(self.consumable_names) == len(self.consumable_tags), (
                f"Crafting {self.__class__}.consumable_names list must "
                "have the same length as .consumable_tags."
            )
        else:
            self.consumable_names = self.consumable_tags

        if self.tool_names:
            assert len(self.tool_names) == len(self.tool_tags), (
                f"Crafting {self.__class__}.tool_names list must "
                "have the same length as .tool_tags."
            )
        else:
            self.tool_names = self.tool_tags

        if self.output_names:
            assert len(self.consumable_names) == len(self.consumable_tags), (
                f"Crafting {self.__class__}.output_names list must "
                "have the same length as .output_prototypes."
            )
        else:
            self.output_names = [
                prot.get("key", prot.get("typeclass", "unnamed"))
                if isinstance(prot, dict)
                else str(prot)
                for prot in self.output_prototypes
            ]

        assert isinstance(
            self.output_prototypes, (list, tuple)
        ), "Crafting {self.__class__}.output_prototypes must be a list or tuple."

        # don't allow reuse if we have consumables. If only tools we can reuse
        # over and over since nothing changes.
        self.allow_reuse = not bool(self.consumable_tags)

    def _format_message(self, message, **kwargs):

        missing = iter_to_str(kwargs.get("missing", ""))
        excess = iter_to_str(kwargs.get("excess", ""))
        involved_tools = iter_to_str(kwargs.get("tools", ""))
        involved_cons = iter_to_str(kwargs.get("consumables", ""))

        # build template context
        mapping = {"missing": missing, "excess": excess}
        mapping.update(
            {
                f"i{ind}": self.consumable_names[ind]
                for ind, name in enumerate(self.consumable_names or self.consumable_tags)
            }
        )
        mapping.update(
            {f"o{ind}": self.output_names[ind] for ind, name in enumerate(self.output_names)}
        )
        mapping["tools"] = involved_tools
        mapping["consumables"] = involved_cons

        mapping["inputs"] = iter_to_str(self.consumable_names)
        mapping["outputs"] = iter_to_str(self.output_names)

        # populate template and return
        return message.format_map(mapping)

    @classmethod
    def seed(cls, tool_kwargs=None, consumable_kwargs=None, location=None):
        """
        This is a helper class-method for easy testing and application of this
        recipe. When called, it will create simple dummy ingredients with names
        and tags needed by this recipe.

        Args:
            tool_kwargs (dict, optional): Will be passed as `**tool_kwargs` into the `create_object`
                call for each tool.  If not given, the matching
                `tool_name` or `tool_tag` will  be used for key.
            consumable_kwargs (dict, optional): This will be passed as
                `**consumable_kwargs` into the `create_object` call for each consumable.
                If not given, matching `consumable_name` or `consumable_tag`
                will  be used for key.
            location (Object, optional): If given, the created items will be created in this
                location. This is a shortcut for adding {"location": <obj>} to both the
                consumable/tool kwargs (and will *override* any such setting in those kwargs).

        Returns:
            tuple: A tuple `(tools, consumables)` with newly created dummy
            objects matching the recipe ingredient list.

        Example:
        ::
            tools, consumables = SwordRecipe.seed(location=caller)
            recipe = SwordRecipe(caller, *(tools + consumables))
            result = recipe.craft()

        Notes:
            If `key` is given in `consumable/tool_kwargs` then _every_ created item
            of each type will have the same key.

        """
        if not tool_kwargs:
            tool_kwargs = {}
        if not consumable_kwargs:
            consumable_kwargs = {}

        if location:
            tool_kwargs["location"] = location
            consumable_kwargs["location"] = location

        tool_key = tool_kwargs.pop("key", None)
        cons_key = consumable_kwargs.pop("key", None)
        tool_tags = tool_kwargs.pop("tags", [])
        cons_tags = consumable_kwargs.pop("tags", [])

        tools = []
        for itag, tag in enumerate(cls.tool_tags):

            tools.append(
                create_object(
                    key=tool_key or (cls.tool_names[itag] if cls.tool_names else tag.capitalize()),
                    tags=[(tag, cls.tool_tag_category), *tool_tags],
                    **tool_kwargs,
                )
            )
        consumables = []
        for itag, tag in enumerate(cls.consumable_tags):
            consumables.append(
                create_object(
                    key=cons_key
                    or (cls.consumable_names[itag] if cls.consumable_names else tag.capitalize()),
                    tags=[(tag, cls.consumable_tag_category), *cons_tags],
                    **consumable_kwargs,
                )
            )
        return tools, consumables

    def pre_craft(self, **kwargs):
        """
        Do pre-craft checks, including input validation.

        Check so the given inputs are what is needed. This operates on
        `self.inputs` which is set to the inputs added to the class
        constructor. Validated data is stored as lists on `.validated_tools`
        and `.validated_consumables` respectively.

        Args:
            **kwargs: Any optional extra kwargs passed during initialization of
                the recipe class.

        Raises:
            CraftingValidationError: If validation fails. At this point the crafter
                is expected to have been informed of the problem already.

        """

        def _check_completeness(
            tagmap,
            taglist,
            namelist,
            exact_match,
            exact_order,
            error_missing_message,
            error_order_message,
            error_excess_message,
        ):
            """Compare tagmap (inputs) to taglist (required)"""
            valids = []
            for itag, tagkey in enumerate(taglist):
                found_obj = None
                for obj, objtags in tagmap.items():
                    if tagkey in objtags:
                        found_obj = obj
                        break
                    if exact_order:
                        # if we get here order is wrong
                        err = self._format_message(
                            error_order_message, missing=obj.get_display_name(looker=self.crafter)
                        )
                        self.msg(err)
                        raise CraftingValidationError(err)

                # since we pop from the mapping, it gets ever shorter
                match = tagmap.pop(found_obj, None)
                if match:
                    valids.append(found_obj)
                elif exact_match:
                    err = self._format_message(
                        error_missing_message,
                        missing=namelist[itag] if namelist else tagkey.capitalize(),
                    )
                    self.msg(err)
                    raise CraftingValidationError(err)

            if exact_match and tagmap:
                # something is left in tagmap, that means it was never popped and
                # thus this is not an exact match
                err = self._format_message(
                    error_excess_message,
                    excess=[obj.get_display_name(looker=self.crafter) for obj in tagmap],
                )
                self.msg(err)
                raise CraftingValidationError(err)

            return valids

        # get tools and consumables from self.inputs
        tool_map = {
            obj: obj.tags.get(category=self.tool_tag_category, return_list=True)
            for obj in self.inputs
            if obj
            and hasattr(obj, "tags")
            and inherits_from(obj, "evennia.objects.models.ObjectDB")
        }
        tool_map = {obj: tags for obj, tags in tool_map.items() if tags}
        consumable_map = {
            obj: obj.tags.get(category=self.consumable_tag_category, return_list=True)
            for obj in self.inputs
            if obj
            and hasattr(obj, "tags")
            and obj not in tool_map
            and inherits_from(obj, "evennia.objects.models.ObjectDB")
        }
        consumable_map = {obj: tags for obj, tags in consumable_map.items() if tags}

        # we set these so they are available for error management at all times,
        # they will be updated with the actual values at the end
        self.validated_tools = [obj for obj in tool_map]
        self.validated_consumables = [obj for obj in consumable_map]

        tools = _check_completeness(
            tool_map,
            self.tool_tags,
            self.tool_names,
            self.exact_tools,
            self.exact_tool_order,
            self.error_tool_missing_message,
            self.error_tool_order_message,
            self.error_tool_excess_message,
        )
        consumables = _check_completeness(
            consumable_map,
            self.consumable_tags,
            self.consumable_names,
            self.exact_consumables,
            self.exact_consumable_order,
            self.error_consumable_missing_message,
            self.error_consumable_order_message,
            self.error_consumable_excess_message,
        )

        # regardless of flags, the tools/consumable lists much contain exactly
        # all the recipe needs now.
        if len(tools) != len(self.tool_tags):
            raise CraftingValidationError(
                f"Tools {tools}'s tags do not match expected tags {self.tool_tags}"
            )
        if len(consumables) != len(self.consumable_tags):
            raise CraftingValidationError(
                f"Consumables {consumables}'s tags do not match "
                f"expected tags {self.consumable_tags}"
            )

        self.validated_tools = tools
        self.validated_consumables = consumables

    def do_craft(self, **kwargs):
        """
        Hook to override. This will not be called if validation in `pre_craft`
        fails.

        This performs the actual crafting. At this point the inputs are
        expected to have been verified already.

        Returns:
            list: A list of spawned objects created from the inputs, or None
                on a failure.

        Notes:
            This method should use `self.msg` to inform the user about the
            specific reason of failure immediately.
            We may want to analyze the tools in some way here to affect the
            crafting process.

        """
        return spawn(*self.output_prototypes)

    def post_craft(self, craft_result, **kwargs):
        """
        Hook to override.
        This is called just after crafting has finished. A common use of
        this method is to delete the inputs.

        Args:
            craft_result (list): The crafted result, provided by `self.do_craft`.
            **kwargs (any): Passed from `self.craft`.

        Returns:
            list: The return(s) of the craft, possibly modified in this method.

        Notes:
            This is _always_ called, also if validation in `pre_craft` fails
            (`craft_result` will then be `None`).

        """
        if craft_result:
            self.msg(self._format_message(self.success_message))
        elif self.failure_message:
            self.msg(self._format_message(self.failure_message))

        if craft_result or self.consume_on_fail:
            # consume the inputs
            for obj in self.validated_consumables:
                obj.delete()

        return craft_result


# access function


def craft(crafter, recipe_name, *inputs, raise_exception=False, **kwargs):
    """
    Access function. Craft a given recipe from a source recipe module. A
    recipe module is a Python module containing recipe classes. Note that this
    requires `settings.CRAFT_RECIPE_MODULES` to be added to a list of one or
    more python-paths to modules holding Recipe-classes.

    Args:
        crafter (Object): The one doing the crafting.
        recipe_name (str): The `CraftRecipe.name` to use. This uses fuzzy-matching
            if the result is unique.
        *inputs: Suitable ingredients and/or tools (Objects) to use in the crafting.
        raise_exception (bool, optional): If crafting failed for whatever
            reason, raise `CraftingError`. The user will still be informed by the
            recipe.
        **kwargs: Optional kwargs to pass into the recipe (will passed into
            recipe.craft).

    Returns:
        list: Crafted objects, if any.

    Raises:
        CraftingError: If `raise_exception` is True and crafting failed to
        produce an output.  KeyError: If `recipe_name` failed to find a
        matching recipe class (or the hit was not precise enough.)

    Notes:
        If no recipe_module is given, will look for a list `settings.CRAFT_RECIPE_MODULES` and
        lastly fall back to the example module
        `"evennia.contrib.game_systems.crafting.example_recipes"`

    """
    # delayed loading/caching of recipes
    _load_recipes()

    RecipeClass = _RECIPE_CLASSES.get(recipe_name, None)
    if not RecipeClass:
        # try a startswith fuzzy match
        matches = [key for key in _RECIPE_CLASSES if key.startswith(recipe_name)]
        if not matches:
            # try in-match
            matches = [key for key in _RECIPE_CLASSES if recipe_name in key]
        if len(matches) == 1:
            RecipeClass = matches[0]

    if not RecipeClass:
        if raise_exception:
            raise KeyError(
                f"No recipe in settings.CRAFT_RECIPE_MODULES has a name matching {recipe_name}"
            )
        else:
            RecipeClass = functools.partial(NonExistentRecipe, name=recipe_name)
    recipe = RecipeClass(crafter, *inputs, **kwargs)
    return recipe.craft(raise_exception=raise_exception)


# craft command/cmdset


class CraftingCmdSet(CmdSet):
    """
    Store crafting command.
    """

    key = "Crafting cmdset"

    def at_cmdset_creation(self):
        self.add(CmdCraft())


class CmdCraft(Command):
    """
    Craft an item using ingredients and tools

    Usage:
      craft <recipe> [from <ingredient>,...] [using <tool>, ...]

    Examples:
      craft snowball from snow
      craft puppet from piece of wood using knife
      craft bread from flour, butter, water, yeast using owen, bowl, roller
      craft fireball using wand, spellbook

    Notes:
        Ingredients must be in the crafter's inventory. Tools can also be
        things in the current location, like a furnace, windmill or anvil.

    """

    key = "craft"
    locks = "cmd:all()"
    help_category = "General"
    arg_regex = r"\s|$"

    def parse(self):
        """
        Handle parsing of:
        ::

            <recipe> [FROM <ingredients>] [USING <tools>]

        Examples:
        ::

            craft snowball from snow
            craft puppet from piece of wood using knife
            craft bread from flour, butter, water, yeast using owen, bowl, roller
            craft fireball using wand, spellbook

        """
        self.args = args = self.args.strip().lower()
        recipe, ingredients, tools = "", "", ""

        if "from" in args:
            recipe, *rest = args.split(" from ", 1)
            rest = rest[0] if rest else ""
            ingredients, *tools = rest.split(" using ", 1)
        elif "using" in args:
            recipe, *tools = args.split(" using ", 1)
        tools = tools[0] if tools else ""

        self.recipe = recipe.strip()
        self.ingredients = [ingr.strip() for ingr in ingredients.split(",")]
        self.tools = [tool.strip() for tool in tools.split(",")]

    def func(self):
        """
        Perform crafting.

        Will check the `craft` locktype. If a consumable/ingredient does not pass
        this check, we will check for the 'crafting_consumable_err_msg'
        Attribute, otherwise will use a default. If failing on a tool, will use
        the `crafting_tool_err_msg` if available.

        """
        caller = self.caller

        if not self.args or not self.recipe:
            self.caller.msg("Usage: craft <recipe> from <ingredient>, ... [using <tool>,...]")
            return

        ingredients = []
        for ingr_key in self.ingredients:
            if not ingr_key:
                continue
            obj = caller.search(ingr_key, location=self.caller)
            # since ingredients are consumed we need extra check so we don't
            # try to include characters or accounts etc.
            if not obj:
                return
            if (
                not inherits_from(obj, "evennia.objects.models.ObjectDB")
                or obj.sessions.all()
                or not obj.access(caller, "craft", default=True)
            ):
                # We don't allow to include puppeted objects nor those with the
                # 'negative' permission 'nocraft'.
                caller.msg(
                    obj.attributes.get(
                        "crafting_consumable_err_msg",
                        default=f"{obj.get_display_name(looker=caller)} can't be used for this.",
                    )
                )
                return
            ingredients.append(obj)

        tools = []
        for tool_key in self.tools:
            if not tool_key:
                continue
            # tools are not consumed, can also exist in the current room
            obj = caller.search(tool_key)
            if not obj:
                return None
            if not obj.access(caller, "craft", default=True):
                caller.msg(
                    obj.attributes.get(
                        "crafting_tool_err_msg",
                        default=f"{obj.get_display_name(looker=caller)} can't be used for this.",
                    )
                )
                return
            tools.append(obj)

        # perform craft and make sure result is in inventory
        # (the recipe handles all returns to caller)
        result = craft(caller, self.recipe, *(tools + ingredients))
        if result:
            for obj in result:
                obj.location = caller
