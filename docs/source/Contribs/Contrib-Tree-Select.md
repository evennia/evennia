# Easy menu selection tree

Contribution by Tim Ashley Jenkins, 2017

This utility allows you to create and initialize an entire branching EvMenu
instance from a multi-line string passed to one function.

> Note: Since the time this contrib was created, EvMenu itself got its own templating 
> language that has more features and is not compatible with the style used in 
> this contrib. Both can still be used in parallel.

`EvMenu` is incredibly powerful and flexible but it can be a little overwhelming
and offers a lot of power that may not be needed for a simple multiple-choice menu.

This module provides a function, `init_tree_selection`, which acts as a frontend
for EvMenu, dynamically sourcing the options from a multi-line string you
provide.  For example, if you define a string as such:

    TEST_MENU = '''Foo
    Bar
    Baz
    Qux'''

And then use `TEST_MENU` as the 'treestr' source when you call
`init_tree_selection` on a player:

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
string along with the caller, as well as the index of the selection (the line
number on the source string) along with the source string for the tree itself.

In addition to specifying selections on the menu, you can also specify
categories.  Categories are indicated by putting options below it preceded with
a '-' character.  If a selection is a category, then choosing it will bring up a
new menu node, prompting the player to select between those options, or to go
back to the previous menu. In addition, categories are marked by default with a
'[+]' at the end of their key. Both this marker and the option to go back can be
disabled.

Categories can be nested in other categories as well - just go another '-'
deeper. You can do this as many times as you like. There's no hard limit to the
number of categories you can go down.

For example, let's add some more options to our menu, turning 'Bar' into a
category.

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

Note the [+] next to 'Bar'. If we select 'Bar', it'll show us the option listed
under it.

    ________________________________________________________________

    Bar
    ________________________________________________________________

    You've got to know [+]
    << Go Back: Return to the previous menu.

Just the one option, which is a category itself, and the option to go back,
which will take us back to the previous menu. Let's select 'You've got to know'.

    ________________________________________________________________

    You've got to know
    ________________________________________________________________

    When to hold em
    When to fold em
    When to walk away
    << Go Back: Return to the previous menu.

Now we see the three options listed under it, too. We can select one of them or
use 'Go Back' to return to the 'Bar' menu we were just at before. It's very
simple to make a branching tree of selections!

One last thing - you can set the descriptions for the various options simply by
adding a ':' character followed by the description to the option's line. For
example, let's add a description to 'Baz' in our menu:

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

Once the player makes a selection - let's say, 'Foo' - the menu will terminate
and call your specified callback with the selection, like so:

    callback(caller, TEST_MENU, 0, "Foo")

The index of the selection is given along with a string containing the
selection's key.  That way, if you have two selections in the menu with the same
key, you can still differentiate between them.

And that's all there is to it! For simple branching-tree selections, using this
system is much easier than manually creating EvMenu nodes. It also makes
generating menus with dynamic options much easier - since the source of the menu
tree is just a string, you could easily generate that string procedurally before
passing it to the `init_tree_selection` function.  For example, if a player casts
a spell or does an attack without specifying a target, instead of giving them an
error, you could present them with a list of valid targets to select by
generating a multi-line string of targets and passing it to
`init_tree_selection`, with the callable performing the maneuver once a
selection is made.

This selection system only works for simple branching trees - doing anything
really complicated like jumping between categories or prompting for arbitrary
input would still require a full EvMenu implementation. For simple selections,
however, I'm sure you will find using this function to be much easier!

Included in this module is a sample menu and function which will let a player
change the color of their name - feel free to mess with it to get a feel for how
this system works by importing this module in your game's `default_cmdsets.py`
module and adding `CmdNameColor` to your default character's command set.


----

<small>This document page is generated from `evennia/contrib/utils/tree_select/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
