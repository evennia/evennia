# Contributions

The [evennia/contrib/](api:evennia.contrib) folder holds Game-specific tools, systems and utilities created by the community. This gathers 
longer-form documentation associated with particular contribs. 

## Crafting
A full, extendable crafting system.

- [Crafting overview](./Crafting)
- [Crafting API documentation](api:evennia.contrib.crafting.crafting)
- [Example of a sword crafting tree](api:evennia.contrib.crafting.example_recipes)

## In-Game-Python

Allow Builders to add Python-scripted events to their objects (OBS-not for untrusted users!)

- [A voice-operated elevator using events](./A-voice-operated-elevator-using-events)
- [Dialogues using events](./Dialogues-in-events)

## Maps

Solutions for generating and displaying maps in-game.

- [Dynamic in-game map](./Dynamic-In-Game-Map)
- [Static in-game map](./Static-In-Game-Map)

## The tutorial-world

The Evennia single-player sole quest. Made to be analyzed to learn.

- [The tutorial world introduction](../Howto/Starting/Part1/Tutorial-World-Introduction)

## Menu-builder

A tool for building using an in-game menu instead of the normal build commands. Meant to 
be expanded for the needs of your game.

- [Building Menus](./Building-menus)


```toctree::
    :hidden:

    ./Crafting
    ../api/evennia.contrib.crafting.crafting 
    ../api/evennia.contrib.crafting.example_recipes
    ./A-voice-operated-elevator-using-events
    ./Dialogues-in-events
    ./Dynamic-In-Game-Map
    ./Static-In-Game-Map
    ../Howto/Starting/Part1/Tutorial-World-Introduction
    ./Building-menus

```