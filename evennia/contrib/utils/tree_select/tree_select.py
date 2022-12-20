"""
Easy menu selection tree

Contrib - Tim Ashley Jenkins 2017

This module allows you to create and initialize an entire branching EvMenu
instance with nothing but a multi-line string passed to one function.

EvMenu is incredibly powerful and flexible, but using it for simple menus
can often be fairly cumbersome - a simple menu that can branch into five
categories would require six nodes, each with options represented as a list
of dictionaries.

This module provides a function, init_tree_selection, which acts as a frontend
for EvMenu, dynamically sourcing the options from a multi-line string you provide.
For example, if you define a string as such:

    TEST_MENU = '''Foo
    Bar
    Baz
    Qux'''

And then use TEST_MENU as the 'treestr' source when you call init_tree_selection
on a player:

    init_tree_selection(TEST_MENU, caller, callback)

The player will be presented with an EvMenu, like so:

    ___________________________

    Make your selection:
    ___________________________

    Foo
    Bar
    Baz
    Qux

Making a selection will pass the selection's key to the specified callback as a
string along with the caller, as well as the index of the selection (the line number
on the source string) along with the source string for the tree itself.

In addition to specifying selections on the menu, you can also specify categories.
Categories are indicated by putting options below it preceded with a '-' character.
If a selection is a category, then choosing it will bring up a new menu node, prompting
the player to select between those options, or to go back to the previous menu. In
addition, categories are marked by default with a '[+]' at the end of their key. Both
this marker and the option to go back can be disabled.

Categories can be nested in other categories as well - just go another '-' deeper. You
can do this as many times as you like. There's no hard limit to the number of
categories you can go down.

For example, let's add some more options to our menu, turning 'Bar' into a category.

    TEST_MENU = '''Foo
    Bar
    -You've got to know
    --When to hold em
    --When to fold em
    --When to walk away
    Baz
    Qux'''

Now when we call the menu, we can see that 'Bar' has become a category instead of a
selectable option.

    _______________________________

    Make your selection:
    _______________________________

    Foo
    Bar [+]
    Baz
    Qux

Note the [+] next to 'Bar'. If we select 'Bar', it'll show us the option listed under it.

    ________________________________________________________________

    Bar
    ________________________________________________________________

    You've got to know [+]
    << Go Back: Return to the previous menu.

Just the one option, which is a category itself, and the option to go back, which will
take us back to the previous menu. Let's select 'You've got to know'.

    ________________________________________________________________

    You've got to know
    ________________________________________________________________

    When to hold em
    When to fold em
    When to walk away
    << Go Back: Return to the previous menu.

Now we see the three options listed under it, too. We can select one of them or use 'Go
Back' to return to the 'Bar' menu we were just at before. It's very simple to make a
branching tree of selections!

One last thing - you can set the descriptions for the various options simply by adding a
':' character followed by the description to the option's line. For example, let's add a
description to 'Baz' in our menu:

    TEST_MENU = '''Foo
    Bar
    -You've got to know
    --When to hold em
    --When to fold em
    --When to walk away
    Baz: Look at this one: the best option.
    Qux'''

Now we see that the Baz option has a description attached that's separate from its key:

    _______________________________________________________________

    Make your selection:
    _______________________________________________________________

    Foo
    Bar [+]
    Baz: Look at this one: the best option.
    Qux

Once the player makes a selection - let's say, 'Foo' - the menu will terminate and call
your specified callback with the selection, like so:

    callback(caller, TEST_MENU, 0, "Foo")

The index of the selection is given along with a string containing the selection's key.
That way, if you have two selections in the menu with the same key, you can still
differentiate between them.

And that's all there is to it! For simple branching-tree selections, using this system is
much easier than manually creating EvMenu nodes. It also makes generating menus with dynamic
options much easier - since the source of the menu tree is just a string, you could easily
generate that string procedurally before passing it to the init_tree_selection function.
For example, if a player casts a spell or does an attack without specifying a target, instead
of giving them an error, you could present them with a list of valid targets to select by
generating a multi-line string of targets and passing it to init_tree_selection, with the
callable performing the maneuver once a selection is made.

This selection system only works for simple branching trees - doing anything really complicated
like jumping between categories or prompting for arbitrary input would still require a full
EvMenu implementation. For simple selections, however, I'm sure you will find using this function
to be much easier!

Included in this module is a sample menu and function which will let a player change the color
of their name - feel free to mess with it to get a feel for how this system works by importing
this module in your game's default_cmdsets.py module and adding CmdNameColor to your default
character's command set.

"""

from evennia import Command
from evennia.utils import evmenu
from evennia.utils.logger import log_trace


def init_tree_selection(
    treestr,
    caller,
    callback,
    index=None,
    mark_category=True,
    go_back=True,
    cmd_on_exit="look",
    start_text="Make your selection:",
):
    """
    Prompts a player to select an option from a menu tree given as a multi-line string.

    Args:
        treestr (str): Multi-lne string representing menu options
        caller (obj): Player to initialize the menu for
        callback (callable): Function to run when a selection is made. Must take 4 args:
            caller (obj): Caller given above
            treestr (str): Menu tree string given above
            index (int): Index of final selection
            selection (str): Key of final selection

    Options:
        index (int or None): Index to start the menu at, or None for top level
        mark_category (bool): If True, marks categories with a [+] symbol in the menu
        go_back (bool): If True, present an option to go back to previous categories
        start_text (str): Text to display at the top level of the menu
        cmd_on_exit(str): Command to enter when the menu exits - 'look' by default


    Notes:
        This function will initialize an instance of EvMenu with options generated
        dynamically from the source string, and passes the menu user's selection to
        a function of your choosing. The EvMenu is made of a single, repeating node,
        which will call itself over and over at different levels of the menu tree as
        categories are selected.

        Once a non-category selection is made, the user's selection will be passed to
        the given callable, both as a string and as an index number. The index is given
        to ensure every selection has a unique identifier, so that selections with the
        same key in different categories can be distinguished between.

        The menus called by this function are not persistent and cannot perform
        complicated tasks like prompt for arbitrary input or jump multiple category
        levels at once - you'll have to use EvMenu itself if you want to take full
        advantage of its features.
    """

    # Pass kwargs to store data needed in the menu
    kwargs = {
        "index": index,
        "mark_category": mark_category,
        "go_back": go_back,
        "treestr": treestr,
        "callback": callback,
        "start_text": start_text,
    }

    # Initialize menu of selections
    evmenu.EvMenu(
        caller,
        "evennia.contrib.utils.tree_select",
        startnode="menunode_treeselect",
        startnode_input=None,
        cmd_on_exit=cmd_on_exit,
        **kwargs,
    )


def dashcount(entry):
    """
    Counts the number of dashes at the beginning of a string. This
    is needed to determine the depth of options in categories.

    Args:
        entry (str): String to count the dashes at the start of

    Returns:
        dashes (int): Number of dashes at the start
    """
    dashes = 0
    for char in entry:
        if char == "-":
            dashes += 1
        else:
            return dashes
    return dashes


def is_category(treestr, index):
    """
    Determines whether an option in a tree string is a category by
    whether or not there are additional options below it.

    Args:
        treestr (str): Multi-line string representing menu options
        index (int): Which line of the string to test

    Returns:
        is_category (bool): Whether the option is a category
    """
    opt_list = treestr.split("\n")
    # Not a category if it's the last one in the list
    if index == len(opt_list) - 1:
        return False
    # Not a category if next option is not one level deeper
    return not bool(dashcount(opt_list[index + 1]) != dashcount(opt_list[index]) + 1)


def parse_opts(treestr, category_index=None):
    """
    Parses a tree string and given index into a list of options. If
    category_index is none, returns all the options at the top level of
    the menu. If category_index corresponds to a category, returns a list
    of options under that category. If category_index corresponds to
    an option that is not a category, it's a selection and returns True.

    Args:
        treestr (str): Multi-line string representing menu options
        category_index (int): Index of category or None for top level

    Returns:
        kept_opts (list or True): Either a list of options in the selected
                                  category or True if a selection was made
    """
    dash_depth = 0
    opt_list = treestr.split("\n")
    kept_opts = []

    # If a category index is given
    if category_index != None:
        # If given index is not a category, it's a selection - return True.
        if not is_category(treestr, category_index):
            return True
        # Otherwise, change the dash depth to match the new category.
        dash_depth = dashcount(opt_list[category_index]) + 1
        # Delete everything before the category index
        opt_list = opt_list[category_index + 1 :]

    # Keep every option (referenced by index) at the appropriate depth
    cur_index = 0
    for option in opt_list:
        if dashcount(option) == dash_depth:
            if category_index == None:
                kept_opts.append((cur_index, option[dash_depth:]))
            else:
                kept_opts.append((cur_index + category_index + 1, option[dash_depth:]))
        # Exits the loop if leaving a category
        if dashcount(option) < dash_depth:
            return kept_opts
        cur_index += 1
    return kept_opts


def index_to_selection(treestr, index, desc=False):
    """
    Given a menu tree string and an index, returns the corresponding selection's
    name as a string. If 'desc' is set to True, will return the selection's
    description as a string instead.

    Args:
        treestr (str): Multi-line string representing menu options
        index (int): Index to convert to selection key or description

    Options:
        desc (bool): If true, returns description instead of key

    Returns:
        selection (str): Selection key or description if 'desc' is set
    """
    opt_list = treestr.split("\n")
    # Fetch the given line
    selection = opt_list[index]
    # Strip out the dashes at the start
    selection = selection[dashcount(selection) :]
    # Separate out description, if any
    if ":" in selection:
        # Split string into key and description
        selection = selection.split(":", 1)
        selection[1] = selection[1].strip(" ")
    else:
        # If no description given, set description to None
        selection = [selection, None]
    if not desc:
        return selection[0]
    else:
        return selection[1]


def go_up_one_category(treestr, index):
    """
    Given a menu tree string and an index, returns the category that the given option
    belongs to. Used for the 'go back' option.

    Args:
        treestr (str): Multi-line string representing menu options
        index (int): Index to determine the parent category of

    Returns:
        parent_category (int): Index of parent category
    """
    opt_list = treestr.split("\n")
    # Get the number of dashes deep the given index is
    dash_level = dashcount(opt_list[index])
    # Delete everything after the current index
    opt_list = opt_list[: index + 1]

    # If there's no dash, return 'None' to return to base menu
    if dash_level == 0:
        return None
    current_index = index
    # Go up through each option until we find one that's one category above
    for selection in reversed(opt_list):
        if dashcount(selection) == dash_level - 1:
            return current_index
        current_index -= 1


def optlist_to_menuoptions(treestr, optlist, index, mark_category, go_back):
    """
    Takes a list of options processed by parse_opts and turns it into
    a list/dictionary of menu options for use in menunode_treeselect.

    Args:
        treestr (str): Multi-line string representing menu options
        optlist (list): List of options to convert to EvMenu's option format
        index (int): Index of current category
        mark_category (bool): Whether or not to mark categories with [+]
        go_back (bool): Whether or not to add an option to go back in the menu

    Returns:
        menuoptions (list of dicts): List of menu options formatted for use
            in EvMenu, each passing a different "newindex" kwarg that changes
            the menu level or makes a selection
    """

    menuoptions = []
    cur_index = 0
    for option in optlist:
        index_to_add = optlist[cur_index][0]
        menuitem = {}
        keystr = index_to_selection(treestr, index_to_add)
        if mark_category and is_category(treestr, index_to_add):
            # Add the [+] to the key if marking categories, and the key by itself as an alias
            menuitem["key"] = [keystr + " [+]", keystr]
        else:
            menuitem["key"] = keystr
        # Get the option's description
        desc = index_to_selection(treestr, index_to_add, desc=True)
        if desc:
            menuitem["desc"] = desc
        # Passing 'newindex' as a kwarg to the node is how we move through the menu!
        menuitem["goto"] = ["menunode_treeselect", {"newindex": index_to_add}]
        menuoptions.append(menuitem)
        cur_index += 1
    # Add option to go back, if needed
    if index != None and go_back == True:
        gobackitem = {
            "key": ["<< Go Back", "go back", "back"],
            "desc": "Return to the previous menu.",
            "goto": ["menunode_treeselect", {"newindex": go_up_one_category(treestr, index)}],
        }
        menuoptions.append(gobackitem)
    return menuoptions


def menunode_treeselect(caller, raw_string, **kwargs):
    """
    This is the repeating menu node that handles the tree selection.
    """

    # If 'newindex' is in the kwargs, change the stored index.
    if "newindex" in kwargs:
        caller.ndb._menutree.index = kwargs["newindex"]

    # Retrieve menu info
    index = caller.ndb._menutree.index
    mark_category = caller.ndb._menutree.mark_category
    go_back = caller.ndb._menutree.go_back
    treestr = caller.ndb._menutree.treestr
    callback = caller.ndb._menutree.callback
    start_text = caller.ndb._menutree.start_text

    # List of options if index is 'None' or category, or 'True' if a selection
    optlist = parse_opts(treestr, category_index=index)

    # If given index returns optlist as 'True', it's a selection. Pass to callback and end the menu.
    if optlist == True:
        selection = index_to_selection(treestr, index)
        try:
            callback(caller, treestr, index, selection)
        except Exception:
            log_trace("Error in tree selection callback.")

        # Returning None, None ends the menu.
        return None, None

    # Otherwise, convert optlist to a list of menu options.
    else:
        options = optlist_to_menuoptions(treestr, optlist, index, mark_category, go_back)
        if index == None:
            # Use start_text for the menu text on the top level
            text = start_text
        else:
            # Use the category name and description (if any) as the menu text
            if index_to_selection(treestr, index, desc=True) != None:
                text = (
                    "|w"
                    + index_to_selection(treestr, index)
                    + "|n: "
                    + index_to_selection(treestr, index, desc=True)
                )
            else:
                text = "|w" + index_to_selection(treestr, index) + "|n"
        return text, options


# The rest of this module is for the example menu and command! It'll change the color of your name.

"""
Here's an example string that you can initialize a menu from. Note the dashes at
the beginning of each line - that's how menu option depth and hierarchy is determined.
"""

NAMECOLOR_MENU = """Set name color: Choose a color for your name!
-Red shades: Various shades of |511red|n
--Red: |511Set your name to Red|n
--Pink: |533Set your name to Pink|n
--Maroon: |301Set your name to Maroon|n
-Orange shades: Various shades of |531orange|n
--Orange: |531Set your name to Orange|n
--Brown: |321Set your name to Brown|n
--Sienna: |420Set your name to Sienna|n
-Yellow shades: Various shades of |551yellow|n
--Yellow: |551Set your name to Yellow|n
--Gold: |540Set your name to Gold|n
--Dandelion: |553Set your name to Dandelion|n
-Green shades: Various shades of |141green|n
--Green: |141Set your name to Green|n
--Lime: |350Set your name to Lime|n
--Forest: |032Set your name to Forest|n
-Blue shades: Various shades of |115blue|n
--Blue: |115Set your name to Blue|n
--Cyan: |155Set your name to Cyan|n
--Navy: |113Set your name to Navy|n
-Purple shades: Various shades of |415purple|n
--Purple: |415Set your name to Purple|n
--Lavender: |535Set your name to Lavender|n
--Fuchsia: |503Set your name to Fuchsia|n
Remove name color: Remove your name color, if any"""


class CmdNameColor(Command):
    """
    Set or remove a special color on your name. Just an example for the
    easy menu selection tree contrib.
    """

    key = "namecolor"

    def func(self):
        # This is all you have to do to initialize a menu!
        init_tree_selection(
            NAMECOLOR_MENU, self.caller, change_name_color, start_text="Name color options:"
        )


def change_name_color(caller, treestr, index, selection):
    """
    Changes a player's name color.

    Args:
        caller (obj): Character whose name to color.
        treestr (str): String for the color change menu - unused
        index (int): Index of menu selection - unused
        selection (str): Selection made from the name color menu - used
            to determine the color the player chose.
    """

    # Store the caller's uncolored name
    if not caller.db.uncolored_name:
        caller.db.uncolored_name = caller.key

    # Dictionary matching color selection names to color codes
    colordict = {
        "Red": "|511",
        "Pink": "|533",
        "Maroon": "|301",
        "Orange": "|531",
        "Brown": "|321",
        "Sienna": "|420",
        "Yellow": "|551",
        "Gold": "|540",
        "Dandelion": "|553",
        "Green": "|141",
        "Lime": "|350",
        "Forest": "|032",
        "Blue": "|115",
        "Cyan": "|155",
        "Navy": "|113",
        "Purple": "|415",
        "Lavender": "|535",
        "Fuchsia": "|503",
    }

    # I know this probably isn't the best way to do this. It's just an example!
    if selection == "Remove name color":  # Player chose to remove their name color
        caller.key = caller.db.uncolored_name
        caller.msg("Name color removed.")
    elif selection in colordict:
        newcolor = colordict[selection]  # Retrieve color code based on menu selection
        caller.key = newcolor + caller.db.uncolored_name + "|n"  # Add color code to caller's name
        caller.msg(newcolor + ("Name color changed to %s!" % selection) + "|n")
