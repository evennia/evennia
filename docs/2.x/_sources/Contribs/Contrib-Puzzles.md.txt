# Puzzles System

Contribution by Henddher 2018

Intended for adventure-game style combination puzzles, such as combining fruits
and a blender to create a smoothie. Provides a typeclass and commands for objects 
that can be combined (i.e. used together). Unlike the `crafting` contrib, each 
puzzle is built from unique objects rather than using tags and a builder can create 
the puzzle entirely from in-game.

A `Puzzle` is a recipe of what objects (aka parts) must be combined by a player so
a new set of objects (aka results) are automatically created.

## Installation

Add the `PuzzleSystemCmdSet` to all players (e.g. in their Character typeclass).

Alternatively (for quick testing):

    py self.cmdset.add('evennia.contrib.game_systems.puzzles.PuzzleSystemCmdSet')

## Usage

Consider this simple Puzzle:

    orange, mango, yogurt, blender = fruit smoothie

As a Builder:

    create/drop orange
    create/drop mango
    create/drop yogurt
    create/drop blender
    create/drop fruit smoothie

    puzzle smoothie, orange, mango, yogurt, blender = fruit smoothie
    ...
    Puzzle smoothie(#1234) created successfuly.

    destroy/force orange, mango, yogurt, blender, fruit smoothie

    armpuzzle #1234
    Part orange is spawned at ...
    Part mango is spawned at ...
    ....
    Puzzle smoothie(#1234) has been armed successfully

As Player:

    use orange, mango, yogurt, blender
    ...
    Genius, you blended all fruits to create a fruit smoothie!

## Details

Puzzles are created from existing objects. The given
objects are introspected to create prototypes for the
puzzle parts and results. These prototypes become the
puzzle recipe. (See PuzzleRecipe and `puzzle`
command). Once the recipe is created, all parts and result
can be disposed (i.e. destroyed).

At a later time, a Builder or a Script can arm the puzzle
and spawn all puzzle parts in their respective
locations (See armpuzzle).

A regular player can collect the puzzle parts and combine
them (See use command). If player has specified
all pieces, the puzzle is considered solved and all
its puzzle parts are destroyed while the puzzle results
are spawened on their corresponding location.


----

<small>This document page is generated from `evennia/contrib/game_systems/puzzles/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
