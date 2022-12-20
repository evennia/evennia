# Contrib folder

`evennia/contrib/` contains 'contributions': extra snippets of code that are
potentially very useful for the game coder but which are considered
too game-specific to be a part of the main Evennia game server.  These
modules are not used unless you explicitly import them. See each file
for more detailed instructions on how to install.

Modules in this folder are distributed under the same licence as
Evennia unless noted differently in the individual module.

If you want to edit, tweak or expand on this code you should copy the
things you want from here into your game folder and change them there.

## base systems

This folder contains systems that are not necessarily tied to a specific
in-game mechanic but is useful for the game as a whole. Examples include
login systems, new command syntaxes, and build helpers.

## full systems

This folder contains 'complete' game engines that can be used directly
to start creating content without no further additions (unless you want to).

## game systems

This folder holds code implementing in-game gameplay systems like
crafting, mail, combat and more. Each system is meant to be adopted
piecemeal and adopted for your game. This does not include
roleplaying-specific systems, those are found in the `rpg` folder.

## grid

Systems related to the game world's topology and structure. This has
contribs related to rooms, exits and map building.

## rpg

This folder has systems specifically related to roleplaying systems
and rule implementation - character traits, dice rolling, emoting etc.

## tutorials

Helper resources specifically meant to teach a development concept or
to exemplify an Evennia system. Any extra resources tied to documentation
tutorials are found here. Also the home of the Tutorial World demo adventure.

## utils

Miscellaneous, optional tools for manipulating text, auditing connections
and more.
