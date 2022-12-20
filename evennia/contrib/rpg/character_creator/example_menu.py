"""
An example EvMenu for the character creator contrib.

This menu is not intended to be a full character creator, but to demonstrate
several different useful node types for your own creator. Any of the different
techniques demonstrated here can be combined into a single decision point.

## Informational Pages

A set of nodes that let you page through information on different choices.

The example shows how to have a single informational page for each option, but
you can expand that into sub-categories by setting the values to dictionaries
instead of simple strings and referencing the "Option Categories" nodes.

## Option Categories

A pair of nodes which let you divide your options into separate categories.
The base node has a list of categories as the options, which is passed to the
child node. That child node then presents the options for that category and
allows the player to choose one.

## Multiple Choice

Allows players to select and deselect options from the list in order to choose
more than one. The example has a requirement of choosing exactly 3 options,
but you can change it to a maximum or minimum number of required options -
or remove the requirement check entirely.

## Simple List Options

If you just want a straightforward list of options, without any of the back-and-forth
navigation or modifying of option text, evennia has an  easy to use decorator
available: `@list_node`

For an example of how to use it, check out the documentation for evennia.utils.evmenu
- there's lots of other useful EvMenu tools too!

## Starting Objects

Allows players to choose from a selection of starting objects.

When creating starting objects e.g. gear, it's best to actually create them
at the end, so you don't have to patch checks in for orphaned objects or
infinite-object player exploits.

## Choosing a Name

The contrib character create command assumes the player will choose their name
during character creation. This section validates name choices before confirming
them.

## The End

It might not seem like an important part, since the players don't make a decision
here, but the final node of character creation is where you finalize all of
the decisions players made earlier. Initializing skills, creating starting gear,
and other one-time method calls and set-up should be put here.
"""

import inflect
from typeclasses.characters import Character

from evennia.prototypes.spawner import spawn
from evennia.utils import dedent
from evennia.utils.evtable import EvTable

_INFLECT = inflect.engine()


#########################################################
#                   Welcome Page
#########################################################


def menunode_welcome(caller):
    """Starting page."""
    text = dedent(
        """\
        |wWelcome to Character Creation!|n

        This is the starting node for all brand new characters. It's a good place to
        remind players that they can exit the character creator and resume later,
        especially if you're going to have a really long chargen process.

        A brief overview of the game could be a good idea here, too, or a link to your
        game wiki if you have one.
    """
    )
    help = "You can explain the commands for exiting and resuming more specifically here."
    options = {"desc": "Let's begin!", "goto": "menunode_info_base"}
    return (text, help), options


#########################################################
#                 Informational Pages
#########################################################

# Storing your information in a dictionary like this makes the menu nodes much cleaner,
# as well as making info easier to update. You can even import it from a different module,
# e.g. wherever you have the classes actually defined, so later updates only happen in one place.
_CLASS_INFO_DICT = {
    # The keys here are the different options you can choose, and the values are the info pages
    "warrior": dedent(
        """\
        Most warriors specialize in melee weapons, although ranged combat
        is not unheard of.

        Warriors like to compete by beating each other up for fun.
        """
    ),
    "mage": dedent(
        """\
        Mages prefer less combative lines of work, such as showmanship or
        selling enchanted charms. Those who choose to be a battle mage are
        highly sought after by adventuring parties.

        Mage schools, being led by the most academic-minded of mages, are
        notorious for intellectual snobbery.
        """
    ),
}


def menunode_info_base(caller):
    """Base node for the informational choices."""
    # this is a base node for a decision, so we want to save the character's progress here
    caller.new_char.db.chargen_step = "menunode_info_base"

    text = dedent(
        """\
        |wInformational Pages|n

        Sometimes you'll want to let players read more about options before choosing
        one of them. This is especially useful for big choices like race or class.
    """
    )
    help = "A link to your wiki for more information on classes could be useful here."
    options = []
    # Build your options from your info dict so you don't need to update this to add new options
    for pclass in _CLASS_INFO_DICT.keys():
        options.append(
            {
                "desc": f"Learn about the |c{pclass}|n class",
                "goto": ("menunode_info_class", {"selected_class": pclass}),
            }
        )
    return (text, help), options


# putting your kwarg in the menu declaration helps keep track of what variables the node needs
def menunode_info_class(caller, raw_string, selected_class=None, **kwargs):
    """Informational overview of a particular class"""

    # sometimes weird bugs happen - it's best to check for them rather than let the game break
    if not selected_class:
        # reset back to the previous step
        caller.new_char.db.chargen_step = "menunode_welcome"
        # print error to player and quit the menu
        return "Something went wrong. Please try again."

    # Since you have all the info in a nice dict, you can just grab it to display here
    text = _CLASS_INFO_DICT[selected_class]
    help = "If you want option-specific help, you can define it in your info dict and reference it."
    options = []

    # set an option for players to choose this class
    options.append(
        {
            "desc": f"Become {_INFLECT.an(selected_class)}",
            "goto": (_set_class, {"selected_class": selected_class}),
        }
    )

    # once again build your options from the same info dict
    for pclass in _CLASS_INFO_DICT.keys():
        # make sure you don't print the currently displayed page as an option
        if pclass != selected_class:
            options.append(
                {
                    "desc": f"Learn about the |c{pclass}|n class",
                    "goto": ("menunode_info_class", {"selected_class": pclass}),
                }
            )
    return (text, help), options


def _set_class(caller, raw_string, selected_class=None, **kwargs):
    # a class should always be selected here
    if not selected_class:
        # go back to the base node for this decision
        return "menunode_info_base"

    char = caller.new_char
    # any special code for setting this option would go here!
    # but we'll just set an attribute
    char.db.player_class = selected_class

    # move on to the next step!
    return "menunode_categories"


#########################################################
#                Option Categories
#########################################################

# for these subcategory options, we make a dict of categories and option lists
_APPEARANCE_DICT = {
    # the key is your category; the value is a list of options, in the order you want them to appear
    "body type": [
        "skeletal",
        "skinny",
        "slender",
        "slim",
        "athletic",
        "muscular",
        "broad",
        "round",
        "curvy",
        "stout",
        "chubby",
    ],
    "height": ["diminutive", "short", "average", "tall", "towering"],
}


def menunode_categories(caller, **kwargs):
    """Base node for categorized options."""
    # this is a new decision step, so save your resume point here
    caller.new_char.db.chargen_step = "menunode_categories"

    text = dedent(
        """\
        |wOption Categories|n

        Some character attributes are part of the same mechanic or decision,
        but need to be divided up into sub-categories. Character appearance
        details are an example of where this can be useful.
        """
    )

    help = "Some helpful extra information on what's affected by these choices works well here."
    options = []

    # just like for informational categories, build the options off of a dictionary to make it
    # easier to manage
    for category in _APPEARANCE_DICT.keys():
        options.append(
            {
                "desc": f"Choose your |c{category}|n",
                "goto": ("menunode_category_options", {"category": category}),
            }
        )

    # since this node goes in and out of sub-nodes, you need an option to proceed to the next step
    options.append(
        {
            "key": ("(Next)", "next", "n"),
            "desc": "Continue to the next step.",
            "goto": "menunode_multi_choice",
        }
    )
    # once past the first decision, it's also a good idea to include a "back to previous step"
    # option
    options.append(
        {
            "key": ("(Back)", "back", "b"),
            "desc": "Go back to the previous step",
            "goto": "menunode_info_base",
        }
    )
    return (text, help), options


def menunode_category_options(caller, raw_string, category=None, **kwargs):
    """Choosing an option within the categories."""
    if not category:
        # this shouldn't have happened, so quit and retry
        return "Something went wrong. Please try again."

    # for mechanics-related choices, you can combine this with the
    # informational options approach to give specific info
    text = f"Choose your {category}:"
    help = f"This will define your {category}."

    options = []
    # build the list of options from the right category of your dictionary
    for option in _APPEARANCE_DICT[category]:
        options.append(
            {"desc": option, "goto": (_set_category_opt, {"category": category, "value": option})}
        )
    # always include a "back" option in case they aren't ready to pick yet
    options.append(
        {
            "key": ("(Back)", "back", "b"),
            "desc": f"Don't change {category}",
            "goto": "menunode_categories",
        }
    )
    return (text, help), options


def _set_category_opt(caller, raw_string, category, value, **kwargs):
    """Set the option for a category"""

    # this is where you would put any more complex code involved in setting the option,
    # but we're just doing simple attributes
    caller.new_char.attributes.add(category, value)

    # go back to the base node for the categories choice to pick another
    return "menunode_categories"


#########################################################
#                  Multiple Choice
#########################################################

# it's not as important to make this a separate list, but like all the others,
# it's easier to read and to update if you do!
_SKILL_OPTIONS = [
    "alchemy",
    "archery",
    "blacksmithing",
    "brawling",
    "dancing",
    "fencing",
    "pottery",
    "tailoring",
    "weaving",
]


def menunode_multi_choice(caller, raw_string, **kwargs):
    """A multiple-choice menu node."""
    char = caller.new_char

    # another decision, so save the resume point
    char.db.chargen_step = "menunode_multi_choice"

    # in order to support picking up from where we left off, get the options from the character
    # if they weren't passed in
    # this is again just a simple attribute, but you could retrieve this list however
    selected = kwargs.get("selected") or char.attributes.get("skill_list", [])

    text = dedent(
        """\
        |wMultiple Choice|n

        Sometimes you want players to be able to pick more than one option -
        for example, starting skills.

        You can easily define it as a minimum, maximum, or exact number of
        selected options.
    """
    )

    help = (
        "This is a good place to specify how many choices are allowed or required. This example"
        " requires exactly 3."
    )

    options = []
    for option in _SKILL_OPTIONS:
        # check if the option has been selected
        if option in selected:
            # if it's been selected, we want to highlight that
            opt_desc = f"|y{option} (selected)|n"
        else:
            opt_desc = option
        options.append(
            {"desc": opt_desc, "goto": (_set_multichoice, {"selected": selected, "option": option})}
        )

    # only display the Next option if the requirements are met!
    # for this example, you need exactly 3 choices, but you can use an inequality
    # for "no more than X", or "at least X"
    if len(selected) == 3:
        options.append(
            {
                "key": ("(Next)", "next", "n"),
                "desc": "Continue to the next step",
                "goto": "menunode_choose_objects",
            }
        )
    options.append(
        {
            "key": ("(Back)", "back", "b"),
            "desc": "Go back to the previous step",
            "goto": "menunode_categories",
        }
    )

    return (text, help), options


def _set_multichoice(caller, raw_string, selected=[], **kwargs):
    """saves the current choices to the character"""
    # get the option being chosen
    if option := kwargs.get("option"):
        # if the option is already in the list, then we want to remove it
        if option in selected:
            selected.remove(option)
        # otherwise, we're adding it
        else:
            selected.append(option)

        # now that the options are updated, save it to the character
        # this is just setting an attribute but it could be anything
        caller.new_char.attributes.add("skill_list", selected)

    # pass the list back so we don't need to retrieve it again
    return ("menunode_multi_choice", {"selected": selected})


#########################################################
#                  Starting Objects
#########################################################

# for a real game, you would most likely want to build this list from
# your existing game prototypes module(s), but for a demo this'll do!
_EXAMPLE_PROTOTYPES = [
    # starter sword prototype
    {
        "key": "basic sword",
        "desc": "This sword will do fine for stabbing things.",
        "tags": [("sword", "weapon")],
    },
    # starter staff prototype
    {
        "key": "basic staff",
        "desc": "You could hit things with it, or maybe use it as a spell focus.",
        "tags": [("staff", "weapon"), ("staff", "focus")],
    },
]


# this method will be run to create the starting objects
def create_objects(character):
    """do the actual object spawning"""
    # since our example chargen saves the starting prototype to an attribute, we retrieve that here
    proto = dict(character.db.starter_weapon)
    # set the location to our character, so they actually have it
    proto["location"] = character
    # create the object
    spawn(proto)


def menunode_choose_objects(caller, raw_string, **kwargs):
    """Selecting objects to start with"""
    char = caller.new_char

    # another decision, so save the resume point
    char.db.chargen_step = "menunode_choose_objects"

    text = dedent(
        """\
        |wStarting Objects|n

        Whether it's a cosmetic outfit, a starting weapon, or a professional
        tool kit, you probably want to let your players have a choice in
        what objects they start out with.
        """
    )

    help = (
        "An overview of what the choice affects - whether it's purely aesthetic or mechanical, and"
        " whether you can change it later - are good here."
    )

    options = []

    for proto in _EXAMPLE_PROTOTYPES:
        # use the key as the option description, but pass the whole prototype
        options.append(
            {
                "desc": f"Choose {_INFLECT.an(proto['key'])}",
                "goto": (_set_object_choice, {"proto": proto}),
            }
        )

    options.append(
        {
            "key": ("(Back)", "back", "b"),
            "desc": "Go back to the previous step",
            "goto": "menunode_multi_choice",
        }
    )

    return (text, help), options


def _set_object_choice(caller, raw_string, proto, **kwargs):
    """Save the selected starting object(s)"""

    # we DON'T want to actually create the object, yet! that way players can still go back and
    # change their mind instead, we save what object was chosen - in this case, by saving the
    # prototype dict to the character
    caller.new_char.db.starter_weapon = proto

    # continue to the next step
    return "menunode_choose_name"


#########################################################
#                Choosing a Name
#########################################################


def menunode_choose_name(caller, raw_string, **kwargs):
    """Name selection"""
    char = caller.new_char

    # another decision, so save the resume point
    char.db.chargen_step = "menunode_choose_name"

    # check if an error message was passed to the node. if so, you'll want to include it
    # into your "name prompt" at the end of the node text.
    if error := kwargs.get("error"):
        prompt_text = f"{error}. Enter a different name."
    else:
        # there was no error, so just ask them to enter a name.
        prompt_text = "Enter a name here to check if it's available."

    # this will print every time the player is prompted to choose a name,
    # including the prompt text defined above
    text = dedent(
        f"""\
        |wChoosing a Name|n

        Especially for roleplaying-centric games, being able to choose your
        character's name after deciding everything else, instead of before,
        is really useful.

        {prompt_text}
        """
    )

    help = "You'll have a chance to change your mind before confirming, even if the name is free."
    # since this is a free-text field, we just have the one
    options = {"key": "_default", "goto": _check_charname}
    return (text, help), options


def _check_charname(caller, raw_string, **kwargs):
    """Check and confirm name choice"""

    # strip any extraneous whitespace from the raw text
    # if you want to do any other validation on the name, e.g. no punctuation allowed, this
    # is the place!
    charname = raw_string.strip()

    # aside from validation, the built-in normalization function from the caller's Account does
    # some useful cleanup on the input, just in case they try something sneaky
    charname = caller.account.normalize_username(charname)

    # check to make sure that the name doesn't already exist
    candidates = Character.objects.filter_family(db_key__iexact=charname)
    if len(candidates):
        # the name is already taken - report back with the error
        return (
            "menunode_choose_name",
            {"error": f"|w{charname}|n is unavailable.\n\nEnter a different name."},
        )
    else:
        # it's free! set the character's key to the name to reserve it
        caller.new_char.key = charname
        # continue on to the confirmation node
        return "menunode_confirm_name"


def menunode_confirm_name(caller, raw_string, **kwargs):
    """Confirm the name choice"""
    char = caller.new_char

    # since we reserved the name by assigning it, you can reference the character key
    # if you have any extra validation or normalization that changed the player's input
    # this also serves to show the player exactly what name they'll get
    text = f"|w{char.key}|n is available! Confirm?"
    # let players change their mind and go back to the name choice, if they want
    options = [
        {"key": ("Yes", "y"), "goto": "menunode_end"},
        {"key": ("No", "n"), "goto": "menunode_choose_name"},
    ]
    return text, options


#########################################################
#                     The End
#########################################################


def menunode_end(caller, raw_string):
    """End-of-chargen cleanup."""
    char = caller.new_char
    # since everything is finished and confirmed, we actually create the starting objects now
    create_objects(char)

    # clear in-progress status
    caller.new_char.attributes.remove("chargen_step")
    text = dedent(
        """
        Congratulations!

        You have completed character creation. Enjoy the game!
    """
    )
    return text, None
