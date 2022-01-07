# Contribs

_Contribs_ are optional code snippets and systems contributed by
the Evennia community. They vary in size and complexity and
may be more specific about game types and styles than 'core' Evennia.
This page is auto-generated and summarizes all contribs currently included.

All contrib categories are imported from `evennia.contrib`, such as

    from evennia.contrib.base_systems import building_menu

Each contrib contains installation instructions for how to integrate it
with your other code. If you want to tweak the code of a contrib, just
copy its entire folder to your game directory and modify/use it from there.

If you want to contribute yourself, see [here](../Contributing.md)!

> Hint: Additional (potentially un-maintained) code snippets from the community can be found
in our discussion forum's [Community Contribs & Snippets](https://github.com/evennia/evennia/discussions/categories/community-contribs-snippets) category.



## base_systems

_This category contains systems that are not necessarily tied to a specific
in-game mechanic but is useful for the game as a whole. Examples include
login systems, new command syntaxes, and build helpers._


### Contrib: `awsstorage`

Contrib by The Right Honourable Reverend (trhr) 2020

## What is this for?

[Read the documentation](./Contrib-AWSStorage.md)



### Contrib: `building_menu`

Module containing the building menu system.

Evennia contributor: vincent-lg 2018

[Read the documentation](./Contrib-Building-Menu.md)



### Contrib: `color_markups`

Contribution, Griatch 2017

Additional color markup styles for Evennia (extending or replacing the default
`|r`, `|234` etc).

[Read the documentation](./Contrib-Color-Markups.md)



### Contrib: `custom_gametime`

Contrib - Griatch 2017, vlgeoff 2017

This reimplements the `evennia.utils.gametime` module but supporting a custom
calendar for your game world. It allows for scheduling events to happen at given
in-game times, taking this custom calendar into account.

[Read the documentation](./Contrib-Custom-Gametime.md)



### Contrib: `email_login`

Evennia contrib - Griatch 2012

This is a variant of the login system that requires an email-address
instead of a username to login.

[Read the documentation](./Contrib-Email-Login.md)



### Contrib: `ingame_python`

Vincent Le Goff 2017

This contrib adds the system of in-game Python in Evennia, allowing immortals
(or other trusted builders) to dynamically add features to individual objects.
Using custom Python set in-game, every immortal or privileged users could have a
specific room, exit, character, object or something else behave differently from
its "cousins".  For these familiar with the use of softcode in MU`*`, like SMAUG
MudProgs, the ability to add arbitrary behavior to individual objects is a step
toward freedom.  Keep in mind, however, the warning below, and read it carefully
before the rest of the documentation.

[Read the documentation](./Contrib-Ingame-Python.md)



### Contrib: `menu_login`

Contribution - Vincent-lg 2016, Griatch 2019 (rework for modern EvMenu)

This changes the Evennia login to ask for the account name and password in
sequence instead of requiring you to enter both at once. It uses EvMenu under
the hood.

[Read the documentation](./Contrib-Menu-Login.md)



### Contrib: `mux_comms_cmds`

Contribution - Griatch 2021

In Evennia 1.0, the old Channel commands (originally inspired by MUX) were
replaced by the single `channel` command that performs all these function.
That command is still required to talk on channels. This contrib (extracted
from Evennia 0.9.5) reuses the channel-management of the base Channel command
but breaks out its functionality into separate Commands with MUX-familiar names.

[Read the documentation](./Contrib-Mux-Comms-Cmds.md)



### Contrib: `unixcommand`

Evennia contribution, Vincent Le Geoff 2017

This module contains a command class that allows for unix-style command syntax
in-game, using --options, positional arguments and stuff like -n 10 etc
similarly to a unix command. It might not the best syntax for the average player
but can be really useful for builders when they need to have a single command do
many things with many options. It uses the ArgumentParser from Python's standard
library under the hood.

[Read the documentation](./Contrib-Unixcommand.md)






## full_systems

_This category contains 'complete' game engines that can be used directly
to start creating content without no further additions (unless you want to)._


### Contrib: `evscaperoom`

Evennia contrib - Griatch 2019

This 'Evennia escaperoom game engine' was created for the MUD Coders Guild game
Jam, April 14-May 15 2019. The theme for the jam was "One Room". This contains the
utilities and base classes and an empty example room.

[Read the documentation](./Contrib-Evscaperoom.md)






## game_systems

_This category holds code implementing in-game gameplay systems like
crafting, mail, combat and more. Each system is meant to be adopted
piecemeal and adopted for your game. This does not include
roleplaying-specific systems, those are found in the `rpg` folder._


### Contrib: `barter`

Evennia contribution - Griatch 2012

This implements a full barter system - a way for players to safely
trade items between each other using code rather than simple free-form
talking.  The advantage of this is increased buy/sell safety but it
also streamlines the process and makes it faster when doing many
transactions (since goods are automatically exchanged once both
agree).

[Read the documentation](./Contrib-Barter.md)



### Contrib: `clothing`

Evennia contribution - Tim Ashley Jenkins 2017

Provides a typeclass and commands for wearable clothing,
which is appended to a character's description when worn.

[Read the documentation](./Contrib-Clothing.md)



### Contrib: `cooldowns`

Evennia contrib - owllex, 2021

This contrib provides a simple cooldown handler that can be attached to any
typeclassed Object or Account. A cooldown is a lightweight persistent
asynchronous timer that you can query to see if it is ready.

[Read the documentation](./Contrib-Cooldowns.md)



### Contrib: `crafting`

Contrib - Griatch 2020

This implements a full crafting system. The principle is that of a 'recipe':

[Read the documentation](./Contrib-Crafting.md)



### Contrib: `gendersub`

Contrib - Griatch 2015

This is a simple gender-aware Character class for allowing users to
insert custom markers in their text to indicate gender-aware
messaging. It relies on a modified msg() and is meant as an
inspiration and starting point to how to do stuff like this.

[Read the documentation](./Contrib-Gendersub.md)



### Contrib: `mail`

Evennia Contribution - grungies1138 2016

A simple Brandymail style mail system that uses the Msg class from Evennia
Core. It has two Commands, both of which can be used on their own:

[Read the documentation](./Contrib-Mail.md)



### Contrib: `multidescer`

Contrib - Griatch 2016

A "multidescer" is a concept from the MUSH world. It allows for
creating, managing and switching between multiple character
descriptions. This multidescer will not require any changes to the
Character class, rather it will use the `multidescs` Attribute (a
list) and create it if it does not exist.

[Read the documentation](./Contrib-Multidescer.md)



### Contrib: `puzzles`

Evennia contribution - Henddher 2018

Provides a typeclass and commands for objects that can be combined (i.e. 'use'd)
to produce new objects.

[Read the documentation](./Contrib-Puzzles.md)



### Contrib: `turnbattle`

Contrib - Tim Ashley Jenkins 2017

This is a framework for a simple turn-based combat system, similar
to those used in D&D-style tabletop role playing games. It allows
any character to start a fight in a room, at which point initiative
is rolled and a turn order is established. Each participant in combat
has a limited time to decide their action for that turn (30 seconds by
default), and combat progresses through the turn order, looping through
the participants until the fight ends.

[Read the documentation](./Contrib-Turnbattle.md)






## grid

_Systems related to the game world's topology and structure. This has
contribs related to rooms, exits and map building._


### Contrib: `extended_room`

Evennia Contribution - Griatch 2012, vincent-lg 2019

This is an extended Room typeclass for Evennia. It is supported
by an extended `Look` command and an extended `desc` command, also
in this module.

[Read the documentation](./Contrib-Extended-Room.md)



### Contrib: `mapbuilder`

Contribution - Cloud_Keeper 2016

Build a map from a 2D ASCII map.

[Read the documentation](./Contrib-Mapbuilder.md)



### Contrib: `simpledoor`

Contribution - Griatch 2016

A simple two-way exit that represents a door that can be opened and
closed. Can easily be expanded from to make it lockable, destroyable
etc.  Note that the simpledoor is based on Evennia locks, so it will
not work for a superuser (which bypasses all locks) - the superuser
will always appear to be able to close/open the door over and over
without the locks stopping you. To use the door, use `@quell` or a
non-superuser account.

[Read the documentation](./Contrib-Simpledoor.md)



### Contrib: `slow_exit`

Contribution - Griatch 2014

This is an example of an Exit-type that delays its traversal. This simulates
slow movement, common in many different types of games. The contrib also
contains two commands, `CmdSetSpeed` and CmdStop for changing the movement speed
and abort an ongoing traversal, respectively.

[Read the documentation](./Contrib-Slow-Exit.md)



### Contrib: `wilderness`

Evennia contrib - titeuf87 2017

This contrib provides a wilderness map without actually creating a large number
of rooms - as you move, your room is instead updated with different
descriptions. This means you can make huge areas with little database use as
long as the rooms are relatively similar (name/desc changing).

[Read the documentation](./Contrib-Wilderness.md)



### Contrib: `xyzgrid`

Full grid coordinate- pathfinding and visualization system
Evennia Contrib by Griatch 2021

The default Evennia's rooms are non-euclidian - they can connect
to each other with any types of exits without necessarily having a clear
position relative to each other. This gives maximum flexibility, but many games
want to use cardinal movements (north, east etc) and also features like finding
the shortest-path between two points.

[Read the documentation](./Contrib-XYZGrid.md)






## rpg

_These are systems specifically related to roleplaying
and rule implementation like character traits, dice rolling and emoting._


### Contrib: `dice`

Rolls dice for roleplaying, in-game gambling or GM:ing

Evennia contribution - Griatch 2012

[Read the documentation](./Contrib-Dice.md)



### Contrib: `health_bar`

Contrib - Tim Ashley Jenkins 2017

The function provided in this module lets you easily display visual
bars or meters - "health bar" is merely the most obvious use for this,
though these bars are highly customizable and can be used for any sort
of appropriate data besides player health.

[Read the documentation](./Contrib-Health-Bar.md)



### Contrib: `rpsystem`

Roleplaying emotes/sdescs - Griatch, 2015
Language/whisper emotes - Griatch, 2015

## Roleplaying emotes

[Read the documentation](./Contrib-RPSystem.md)



### Contrib: `traits`

Whitenoise 2014, Ainneve contributors,
Griatch 2020

A `Trait` represents a modifiable property on (usually) a Character. They can
be used to represent everything from attributes (str, agi etc) to skills
(hunting 10, swords 14 etc) and dynamically changing things like HP, XP etc.

[Read the documentation](./Contrib-Traits.md)






## tutorials

_Helper resources specifically meant to teach a development concept or
to exemplify an Evennia system. Any extra resources tied to documentation
tutorials are found here. Also the home of the Tutorial World demo adventure._


### Contrib: `batchprocessor`

Contibution - Griatch 2012

The batch processor is used for generating in-game content from one or more
static files. Files can be stored with version control and then 'applied'
to the game to create content.

[Read the documentation](./Contrib-Batchprocessor.md)



### Contrib: `bodyfunctions`

Griatch - 2012

Example script for testing. This adds a simple timer that has your
character make observations and notices at irregular intervals.

[Read the documentation](./Contrib-Bodyfunctions.md)



### Contrib: `mirror`

A simple mirror object to experiment with.

A simple mirror object that

[Read the documentation](./Contrib-Mirror.md)



### Contrib: `red_button`

Griatch - 2011

This is a more advanced example object with its own functionality (commands)
on it.

[Read the documentation](./Contrib-Red-Button.md)



### Contrib: `talking_npc`

Contribution - Griatch 2011, grungies1138, 2016

This is a static NPC object capable of holding a simple menu-driven
conversation. It's just meant as an example.

[Read the documentation](./Contrib-Talking-Npc.md)



### Contrib: `tutorial_world`

Griatch 2011, 2015

This is a stand-alone tutorial area for an unmodified Evennia install.
Think of it as a sort of single-player adventure rather than a
full-fledged multi-player game world. The various rooms and objects
herein are designed to show off features of the engine, not to be a
very challenging (nor long) gaming experience. As such it's of course
only skimming the surface of what is possible.

[Read the documentation](./Contrib-Tutorial-World.md)






## utils

_Miscellaneous, optional tools for manipulating text, auditing connections
and more._


### Contrib: `auditing`

Contrib - Johnny 2017

This is a tap that optionally intercepts all data sent to/from clients and the
server and passes it to a callback of your choosing.

[Read the documentation](./Contrib-Auditing.md)



### Contrib: `fieldfill`

Contrib - Tim Ashley Jenkins 2018

This module contains a function that calls an easily customizable EvMenu - this
menu presents the player with a fillable form, with fields that can be filled
out in any order. Each field's value can be verified, with the function
allowing easy checks for text and integer input, minimum and maximum values /
character lengths, or can even be verified by a custom function. Once the form
is submitted, the form's data is submitted as a dictionary to any callable of
your choice.

[Read the documentation](./Contrib-Fieldfill.md)



### Contrib: `random_string_generator`

Contribution - Vincent Le Goff 2017

This contrib can be used to generate pseudo-random strings of information
with specific criteria.  You could, for instance, use it to generate
phone numbers, license plate numbers, validation codes, non-sensivite
passwords and so on.  The strings generated by the generator will be
stored and won't be available again in order to avoid repetition.
Here's a very simple example:

[Read the documentation](./Contrib-Random-String-Generator.md)



### Contrib: `tree_select`

Contrib - Tim Ashley Jenkins 2017

This module allows you to create and initialize an entire branching EvMenu
instance with nothing but a multi-line string passed to one function.

[Read the documentation](./Contrib-Tree-Select.md)






```{toctree}
:depth: 2

Contribs/Contrib-AWSStorage.md
Contribs/Contrib-Building-Menu.md
Contribs/Contrib-Color-Markups.md
Contribs/Contrib-Custom-Gametime.md
Contribs/Contrib-Email-Login.md
Contribs/Contrib-Ingame-Python.md
Contribs/Contrib-Menu-Login.md
Contribs/Contrib-Mux-Comms-Cmds.md
Contribs/Contrib-Unixcommand.md
Contribs/Contrib-Evscaperoom.md
Contribs/Contrib-Barter.md
Contribs/Contrib-Clothing.md
Contribs/Contrib-Cooldowns.md
Contribs/Contrib-Crafting.md
Contribs/Contrib-Gendersub.md
Contribs/Contrib-Mail.md
Contribs/Contrib-Multidescer.md
Contribs/Contrib-Puzzles.md
Contribs/Contrib-Turnbattle.md
Contribs/Contrib-Extended-Room.md
Contribs/Contrib-Mapbuilder.md
Contribs/Contrib-Simpledoor.md
Contribs/Contrib-Slow-Exit.md
Contribs/Contrib-Wilderness.md
Contribs/Contrib-XYZGrid.md
Contribs/Contrib-Dice.md
Contribs/Contrib-Health-Bar.md
Contribs/Contrib-RPSystem.md
Contribs/Contrib-Traits.md
Contribs/Contrib-Batchprocessor.md
Contribs/Contrib-Bodyfunctions.md
Contribs/Contrib-Mirror.md
Contribs/Contrib-Red-Button.md
Contribs/Contrib-Talking-Npc.md
Contribs/Contrib-Tutorial-World.md
Contribs/Contrib-Auditing.md
Contribs/Contrib-Fieldfill.md
Contribs/Contrib-Random-String-Generator.md
Contribs/Contrib-Tree-Select.md




----

<small>This document page is auto-generated from the sources. Manual changes
will be overwritten.</small>
