"""
Clothing - Provides a typeclass and commands for wearable clothing,
which is appended to a character's description when worn.

Evennia contribution - Tim Ashley Jenkins 2017

Clothing items, when worn, are added to the character's description
in a list. For example, if wearing the following clothing items:

    a thin and delicate necklace
    a pair of regular ol' shoes
    one nice hat
    a very pretty dress

A character's description may look like this:

    Superuser(#1)
    This is User #1.

    Superuser is wearing one nice hat, a thin and delicate necklace,
    a very pretty dress and a pair of regular ol' shoes.

Characters can also specify the style of wear for their clothing - I.E.
to wear a scarf 'tied into a tight knot around the neck' or 'draped
loosely across the shoulders' - to add an easy avenue of customization.
For example, after entering:

    wear scarf draped loosely across the shoulders

The garment appears like so in the description:

    Superuser(#1)
    This is User #1.

    Superuser is wearing a fanciful-looking scarf draped loosely
    across the shoulders.

Items of clothing can be used to cover other items, and many options
are provided to define your own clothing types and their limits and
behaviors. For example, to have undergarments automatically covered
by outerwear, or to put a limit on the number of each type of item
that can be worn. The system as-is is fairly freeform - you
can cover any garment with almost any other, for example - but it
can easily be made more restrictive, and can even be tied into a
system for armor or other equipment.

To install, import this module and have your default character
inherit from ClothedCharacter in your game's characters.py file:

    from evennia.contrib.game_systems.clothing import ClothedCharacter

    class Character(ClothedCharacter):

And then add ClothedCharacterCmdSet in your character set in your
game's commands/default_cmdsets.py:

    from evennia.contrib.game_systems.clothing import ClothedCharacterCmdSet

    class CharacterCmdSet(default_cmds.CharacterCmdSet):
         ...
         at_cmdset_creation(self):

             super().at_cmdset_creation()
             ...
             self.add(ClothedCharacterCmdSet)    # <-- add this

From here, you can use the default builder commands to create clothes
with which to test the system:

    @create a pretty shirt : evennia.contrib.game_systems.clothing.ContribClothing
    @set shirt/clothing_type = 'top'
    wear shirt

"""
from collections import defaultdict

from django.conf import settings

from evennia import DefaultCharacter, DefaultObject, default_cmds
from evennia.commands.default.muxcommand import MuxCommand
from evennia.utils import at_search_result, evtable, inherits_from, iter_to_str

# Options start here.
# Maximum character length of 'wear style' strings, or None for unlimited.
WEARSTYLE_MAXLENGTH = getattr(settings, "CLOTHING_WEARSTYLE_MAXLENGTH", 50)

# The rest of these options have to do with clothing types. ContribClothing types are optional,
# but can be used to give better control over how different items of clothing behave. You
# can freely add, remove, or change clothing types to suit the needs of your game and use
# the options below to affect their behavior.

# The order in which clothing types appear on the description. Untyped clothing or clothing
# with a type not given in this list goes last.
CLOTHING_TYPE_ORDER = getattr(
    settings,
    "CLOTHING_TYPE_ORDERED",
    [
        "hat",
        "jewelry",
        "top",
        "undershirt",
        "gloves",
        "fullbody",
        "bottom",
        "underpants",
        "socks",
        "shoes",
        "accessory",
    ],
)
# The maximum number of each type of clothes that can be worn. Unlimited if untyped or not specified.
CLOTHING_TYPE_LIMIT = getattr(
    settings, "CLOTHING_TYPE_LIMIT", {"hat": 1, "gloves": 1, "socks": 1, "shoes": 1}
)
# The maximum number of clothing items that can be worn, or None for unlimited.
CLOTHING_OVERALL_LIMIT = getattr(settings, "CLOTHING_OVERALL_LIMIT", 20)
# What types of clothes will automatically cover what other types of clothes when worn.
# Note that clothing only gets auto-covered if it's already worn when you put something
# on that auto-covers it - for example, it's perfectly possible to have your underpants
# showing if you put them on after your pants!
CLOTHING_TYPE_AUTOCOVER = getattr(
    settings,
    "CLOTHING_TYPE_AUTOCOVER",
    {
        "top": ["undershirt"],
        "bottom": ["underpants"],
        "fullbody": ["undershirt", "underpants"],
        "shoes": ["socks"],
    },
)
# Types of clothes that can't be used to cover other clothes.
CLOTHING_TYPE_CANT_COVER_WITH = getattr(settings, "CLOTHING_TYPE_AUTOCOVER", ["jewelry"])


# HELPER FUNCTIONS START HERE
def order_clothes_list(clothes_list):
    """
    Orders a given clothes list by the order specified in CLOTHING_TYPE_ORDER.

    Args:
        clothes_list (list): List of clothing items to put in order

    Returns:
        ordered_clothes_list (list): The same list as passed, but re-ordered
                                     according to the hierarchy of clothing types
                                     specified in CLOTHING_TYPE_ORDER.
    """
    ordered_clothes_list = clothes_list
    # For each type of clothing that exists...
    for current_type in reversed(CLOTHING_TYPE_ORDER):
        # Check each item in the given clothes list.
        for clothes in clothes_list:
            # If the item has a clothing type...
            if clothes.db.clothing_type:
                item_type = clothes.db.clothing_type
                # And the clothing type matches the current type...
                if item_type == current_type:
                    # Move it to the front of the list!
                    ordered_clothes_list.remove(clothes)
                    ordered_clothes_list.insert(0, clothes)
    return ordered_clothes_list


def get_worn_clothes(character, exclude_covered=False):
    """
    Get a list of clothes worn by a given character.

    Args:
        character (obj): The character to get a list of worn clothes from.

    Keyword Args:
        exclude_covered (bool): If True, excludes clothes covered by other
                                clothing from the returned list.

    Returns:
        ordered_clothes_list (list): A list of clothing items worn by the
                                     given character, ordered according to
                                     the CLOTHING_TYPE_ORDER option specified
                                     in this module.
    """
    clothes_list = []
    for thing in character.contents:
        # If uncovered or not excluding covered items
        if not thing.db.covered_by or exclude_covered is False:
            # If 'worn' is True, add to the list
            if thing.db.worn:
                clothes_list.append(thing)
    # Might as well put them in order here too.
    ordered_clothes_list = order_clothes_list(clothes_list)
    return ordered_clothes_list


def clothing_type_count(clothes_list):
    """
    Returns a dictionary of the number of each clothing type
    in a given list of clothing objects.

    Args:
        clothes_list (list): A list of clothing items from which
                             to count the number of clothing types
                             represented among them.

    Returns:
        types_count (dict): A dictionary of clothing types represented
                            in the given list and the number of each
                            clothing type represented.
    """
    types_count = {}
    for garment in clothes_list:
        if garment.db.clothing_type:
            type = garment.db.clothing_type
            if type not in list(types_count.keys()):
                types_count[type] = 1
            else:
                types_count[type] += 1
    return types_count


def single_type_count(clothes_list, type):
    """
    Returns an integer value of the number of a given type of clothing in a list.

    Args:
        clothes_list (list): List of clothing objects to count from
        type (str): Clothing type to count

    Returns:
        type_count (int): Number of garments of the specified type in the given
                          list of clothing objects
    """
    type_count = 0
    for garment in clothes_list:
        if garment.db.clothing_type:
            if garment.db.clothing_type == type:
                type_count += 1
    return type_count


class ContribClothing(DefaultObject):
    def wear(self, wearer, wearstyle, quiet=False):
        """
        Sets clothes to 'worn' and optionally echoes to the room.

        Args:
            wearer (obj): character object wearing this clothing object
            wearstyle (True or str): string describing the style of wear or True for none

        Keyword Args:
            quiet (bool): If false, does not message the room

        Notes:
            Optionally sets db.worn with a 'wearstyle' that appends a short passage to
            the end of the name  of the clothing to describe how it's worn that shows
            up in the wearer's desc - I.E. 'around his neck' or 'tied loosely around
            her waist'. If db.worn is set to 'True' then just the name will be shown.
        """
        # Set clothing as worn
        self.db.worn = wearstyle
        # Auto-cover appropriate clothing types
        to_cover = []
        if clothing_type := self.db.clothing_type:
            if autocover_types := CLOTHING_TYPE_AUTOCOVER.get(clothing_type):
                to_cover.extend(
                    [
                        garment
                        for garment in get_worn_clothes(wearer)
                        if garment.db.clothing_type in autocover_types
                    ]
                )
        for garment in to_cover:
            garment.db.covered_by = self

        # Echo a message to the room
        if not quiet:
            if type(wearstyle) is str:
                message = f"$You() $conj(wear) {self.name} {wearstyle}"
            else:
                message = f"$You() $conj(put) on {self.name}"
            if to_cover:
                message += ", covering {iter_to_str(to_cover)}"
            wearer.location.msg_contents(message + ".", from_obj=wearer)

    def remove(self, wearer, quiet=False):
        """
        Removes worn clothes and optionally echoes to the room.

        Args:
            wearer (obj): character object wearing this clothing object

        Keyword Args:
            quiet (bool): If false, does not message the room
        """
        self.db.worn = False
        uncovered_list = []

        # Check to see if any other clothes are covered by this object.
        for thing in wearer.contents:
            if thing.db.covered_by == self:
                thing.db.covered_by = False
                uncovered_list.append(thing.name)
        # Echo a message to the room
        if not quiet:
            remove_message = f"$You() $conj(remove) {self.name}"
            if len(uncovered_list) > 0:
                remove_message += f", revealing {iter_to_str(uncovered_list)}"
            wearer.location.msg_contents(remove_message + ".", from_obj=wearer)

    def at_get(self, getter):
        """
        Makes absolutely sure clothes aren't already set as 'worn'
        when they're picked up, in case they've somehow had their
        location changed without getting removed.
        """
        self.db.worn = False

    def at_pre_move(self, destination, **kwargs):
        """
        Called just before starting to move this object to
        destination. Return False to abort move.

        Notes:
            If this method returns False/None, the move is cancelled
            before it is even started.
        """
        # Covered clothing cannot be removed, dropped, or otherwise relocated
        if self.db.covered_by:
            return False
        return True


class ClothedCharacter(DefaultCharacter):
    """
    Character that displays worn clothing when looked at. You can also
    just copy the return_appearance hook defined below to your own game's
    character typeclass.
    """

    def get_display_desc(self, looker, **kwargs):
        """
        Get the 'desc' component of the object description. Called by `return_appearance`.

        Args:
            looker (Object): Object doing the looking.
            **kwargs: Arbitrary data for use when overriding.
        Returns:
            str: The desc display string.
        """
        desc = self.db.desc

        outfit_list = []
        # Append worn, uncovered clothing to the description
        for garment in get_worn_clothes(self, exclude_covered=True):
            wearstyle = garment.db.worn
            if type(wearstyle) is str:
                outfit_list.append(f"{garment.name} {wearstyle}")
            else:
                outfit_list.append(garment.name)

        # Create outfit string
        if outfit_list:
            outfit = (
                f"{self.get_display_name(looker, **kwargs)} is wearing {iter_to_str(outfit_list)}."
            )
        else:
            outfit = f"{self.get_display_name(looker, **kwargs)} is wearing nothing."

        # Add on to base description
        if desc:
            desc += f"\n\n{outfit}"
        else:
            desc = outfit

        return desc

    def get_display_things(self, looker, **kwargs):
        """
        Get the 'things' component of the object's contents. Called by `return_appearance`.

        Args:
            looker (Object): Object doing the looking.
            **kwargs: Arbitrary data for use when overriding.
        Returns:
            str: A string describing the things in object.
        """

        def _filter_visible(obj_list):
            return (
                obj
                for obj in obj_list
                if obj != looker and obj.access(looker, "view") and not obj.db.worn
            )

        # sort and handle same-named things
        things = _filter_visible(self.contents_get(content_type="object"))

        grouped_things = defaultdict(list)
        for thing in things:
            grouped_things[thing.get_display_name(looker, **kwargs)].append(thing)

        thing_names = []
        for thingname, thinglist in sorted(grouped_things.items()):
            nthings = len(thinglist)
            thing = thinglist[0]
            singular, plural = thing.get_numbered_name(nthings, looker, key=thingname)
            thing_names.append(singular if nthings == 1 else plural)
        thing_names = iter_to_str(thing_names)
        return (
            f"\n{self.get_display_name(looker, **kwargs)} is carrying {thing_names}"
            if thing_names
            else ""
        )


# COMMANDS START HERE


class CmdWear(MuxCommand):
    """
    Puts on an item of clothing you are holding.

    Usage:
      wear <obj> [=] [wear style]

    Examples:
      wear red shirt
      wear scarf wrapped loosely about the shoulders
      wear blue hat = at a jaunty angle

    All the clothes you are wearing are appended to your description.
    If you provide a 'wear style' after the command, the message you
    provide will be displayed after the clothing's name.
    """

    key = "wear"
    help_category = "clothing"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: wear <obj> [=] [wear style]")
            return
        if not self.rhs:
            # check if the whole string is an object
            clothing = self.caller.search(self.lhs, candidates=self.caller.contents, quiet=True)
            if not clothing:
                # split out the first word as the object and the rest as the wearstyle
                argslist = self.lhs.split()
                self.lhs = argslist[0]
                self.rhs = " ".join(argslist[1:])
                clothing = self.caller.search(self.lhs, candidates=self.caller.contents)
            else:
                # pass the result through the search-result hook
                clothing = at_search_result(clothing, self.caller, self.lhs)

        else:
            # it had an explicit separator - just do a normal search for the lhs
            clothing = self.caller.search(self.lhs, candidates=self.caller.contents)

        if not clothing:
            return
        if not inherits_from(clothing, ContribClothing):
            self.caller.msg(f"{clothing.name} isn't something you can wear.")
            return

        if clothing.db.worn:
            if not self.rhs:
                # If no wearstyle was provided and the clothing is already being worn, do nothing
                self.caller.msg(f"You're already wearing your {clothing.name}.")
                return
            elif len(self.rhs) > WEARSTYLE_MAXLENGTH:
                self.caller.msg(
                    f"Please keep your wear style message to less than {WEARSTYLE_MAXLENGTH} characters."
                )
                return
            else:
                # Adjust the wearstyle
                clothing.db.worn = self.rhs
                self.caller.location.msg_contents(
                    f"$You() $conj(wear) {clothing.name} {self.rhs}.", from_obj=self.caller
                )
                return

        already_worn = get_worn_clothes(self.caller)

        # Enforce overall clothing limit.
        if CLOTHING_OVERALL_LIMIT and len(already_worn) >= CLOTHING_OVERALL_LIMIT:
            self.caller.msg("You can't wear any more clothes.")
            return

        # Apply individual clothing type limits.
        if clothing_type := clothing.db.type:
            if clothing_type in CLOTHING_TYPE_LIMIT:
                type_count = single_type_count(already_worn, clothing_type)
                if type_count >= CLOTHING_TYPE_LIMIT[clothing_type]:
                    self.caller.msg(
                        "You can't wear any more clothes of the type '{clothing_type}'."
                    )
                    return

        wearstyle = self.rhs or True
        clothing.wear(self.caller, wearstyle)


class CmdRemove(MuxCommand):
    """
    Takes off an item of clothing.

    Usage:
       remove <obj>

    Removes an item of clothing you are wearing. You can't remove
    clothes that are covered up by something else - you must take
    off the covering item first.
    """

    key = "remove"
    help_category = "clothing"

    def func(self):
        clothing = self.caller.search(self.args, candidates=self.caller.contents)
        if not clothing:
            self.caller.msg("You don't have anything like that.")
            return
        if not clothing.db.worn:
            self.caller.msg("You're not wearing that!")
            return
        if covered := clothing.db.covered_by:
            self.caller.msg(f"You have to take off {covered} first.")
            return
        clothing.remove(self.caller)


class CmdCover(MuxCommand):
    """
    Covers a worn item of clothing with another you're holding or wearing.

    Usage:
        cover <worn obj> with <obj>

    When you cover a clothing item, it is hidden and no longer appears in
    your description until it's uncovered or the item covering it is removed.
    You can't remove an item of clothing if it's covered.
    """

    key = "cover"
    help_category = "clothing"
    rhs_split = (" with ", "=")

    def func(self):
        if not len(self.args) or not self.rhs:
            self.caller.msg("Usage: cover <worn clothing> with <clothing object>")
            return

        to_cover = self.caller.search(self.lhs, candidates=get_worn_clothes(self.caller))
        cover_with = self.caller.search(self.rhs, candidates=self.caller.contents)
        if not to_cover or not cover_with:
            return
        if to_cover == cover_with:
            self.caller.msg("You can't cover an item with itself!")
            return

        if not inherits_from(cover_with, ContribClothing):
            self.caller.msg(f"{cover_with.name} isn't something you can wear.")
            rturn

        if cover_with.db.clothing_type in CLOTHING_TYPE_CANT_COVER_WITH:
            self.caller.msg(f"You can't cover anything with {cover_with.name}.")
            return

        if covered_by := cover_with.db.covered_by:
            self.caller.msg(f"{cover_with.name} is already covered by {covered_by.name}.")
            return
        if covered_by := to_cover.db.covered_by:
            self.caller.msg(f"{to_cover.name} is already covered by {covered_by.name}.")
            return

        # Put on the item to cover with if it's not on already
        if not cover_with.db.worn:
            cover_with.wear(self.caller, True)
        to_cover.db.covered_by = cover_with

        self.caller.location.msg_contents(
            f"$You() $conj(cover) {to_cover.name} with {cover_with.name}.", from_obj=self.caller
        )


class CmdUncover(MuxCommand):
    """
    Reveals a worn item of clothing that's currently covered up.

    Usage:
        uncover <obj>

    When you uncover an item of clothing, you allow it to appear in your
    description without having to take off the garment that's currently
    covering it. You can't uncover an item of clothing if the item covering
    it is also covered by something else.
    """

    key = "uncover"
    help_category = "clothing"

    def func(self):
        """
        This performs the actual command.
        """

        if not self.args:
            self.caller.msg("Usage: uncover <worn clothing object>")
            return

        clothing = self.caller.search(self.args, candidates=get_worn_clothes(self.caller))
        if not clothing:
            return
        if covered_by := clothing.db.covered_by:
            if covered_by.db.covered_by:
                self.caller.msg(f"{clothing.name} is under too many layers to uncover.")
                return
            clothing.db.covered_by = None
            self.caller.location.msg_contents(
                f"$You() $conj(uncover) {clothing.name}.", from_obj=self.caller
            )

        else:
            self.caller.msg(f"{clothing.name} isn't covered by anything.")
            return


class CmdInventory(MuxCommand):
    """
    view inventory

    Usage:
      inventory
      inv

    Shows your inventory.
    """

    # Alternate version of the inventory command which separates
    # worn and carried items.

    key = "inventory"
    aliases = ["inv", "i"]
    locks = "cmd:all()"
    arg_regex = r"$"

    def func(self):
        """check inventory"""
        if not self.caller.contents:
            self.caller.msg("You are not carrying or wearing anything.")
            return

        message_list = []

        items = self.caller.contents

        carry_table = evtable.EvTable(border="header")
        wear_table = evtable.EvTable(border="header")

        carried = [obj for obj in items if not obj.db.worn]
        worn = [obj for obj in items if obj.db.worn]

        message_list.append("|wYou are carrying:|n")
        for item in carried:
            carry_table.add_row(
                item.get_display_name(self.caller), item.get_display_desc(self.caller)
            )
        if carry_table.nrows == 0:
            carry_table.add_row("Nothing.", "")
        message_list.append(str(carry_table))

        message_list.append("|wYou are wearing:|n")
        for item in worn:
            item_name = item.get_display_name(self.caller)
            if item.db.covered_by:
                item_name += " (hidden)"
            wear_table.add_row(item_name, item.get_display_desc(self.caller))
        if wear_table.nrows == 0:
            wear_table.add_row("Nothing.", "")
        message_list.append(str(wear_table))

        self.caller.msg("\n".join(message_list))


class ClothedCharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    Command set for clothing, including new versions of 'give' and 'drop'
    that take worn and covered clothing into account, as well as a new
    version of 'inventory' that differentiates between carried and worn
    items.
    """

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(CmdWear())
        self.add(CmdRemove())
        self.add(CmdCover())
        self.add(CmdUncover())
        self.add(CmdInventory())
