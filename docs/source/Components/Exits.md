# Exits

**Inheritance Tree:** 
```
┌─────────────┐
│DefaultObject│
└─────▲───────┘
      │
┌─────┴─────┐
│DefaultExit│
└─────▲─────┘
      │       ┌────────────┐
      │ ┌─────►ObjectParent│
      │ │     └────────────┘
    ┌─┴─┴┐
    │Exit│
    └────┘
```

*Exits* are in-game [Objects](./Objects.md) connecting other objects (usually [Rooms](./Rooms.md)) together. 

> Note that Exits are one-way objects, so in order for two Rooms to be linked bi-directionally, there will need to be two exits.

An object named `north` or `in` might be exits, as well as `door`, `portal` or `jump out the window`. 

An exit has two things that separate them from other objects. 
1. Their `.destination` property is set and points to a valid target location. This fact makes it easy and fast to locate exits in the database. 
2. Exits define a special [Transit Command](./Commands.md) on themselves when they are created. This command is named the same as the exit object and will, when called, handle the practicalities of moving the character to the Exits's `.destination` - this allows you to just enter the name of the exit on its own to move around, just as you would expect.

The default exit functionality is all defined on the [DefaultExit](DefaultExit) typeclass. You could in principle completely change how exits work in your game by overriding this - it's not recommended though, unless you really know what you are doing). 

Exits are [locked](./Locks.md) using an `access_type` called *traverse* and also make use of a few hook methods for giving feedback if the traversal fails.  See `evennia.DefaultExit` for more info. 

Exits are normally overridden on a case-by-case basis, but if you want to change the default exit created by rooms like `dig`, `tunnel` or `open` you can change it in settings:

    BASE_EXIT_TYPECLASS = "typeclasses.exits.Exit"

In `mygame/typeclasses/exits.py` there is an empty `Exit` class for you to modify.

### Exit details 

The process of traversing an exit is as follows:

1. The traversing `obj` sends a command that matches the Exit-command name on the Exit object. The [cmdhandler](./Commands.md) detects this and triggers the command defined on the Exit. Traversal always involves the "source" (the current location) and the `destination` (this is stored on the Exit object).
1. The Exit command checks the `traverse` lock on the Exit object
1. The Exit command triggers `at_traverse(obj, destination)` on the Exit object.
1. In `at_traverse`, `object.move_to(destination)` is triggered. This triggers the following hooks, in order:
    1. `obj.at_pre_move(destination)` - if this returns False, move is aborted.
    1. `origin.at_pre_leave(obj, destination)`
    1. `obj.announce_move_from(destination)`
    1. Move is performed by changing `obj.location` from source location to `destination`.
    1. `obj.announce_move_to(source)`
    1. `destination.at_object_receive(obj, source)`
    1. `obj.at_post_move(source)`
1. On the Exit object, `at_post_traverse(obj, source)` is triggered.

If the move fails for whatever reason, the Exit will look for an Attribute `err_traverse` on itself and display this as an error message. If this is not found, the Exit will instead call `at_failed_traverse(obj)` on itself. 

### Creating Exits in code

For an example of how to create Exits programatically please see [this guide](../Howtos/Beginner-Tutorial/Part1/Beginner-Tutorial-Creating-Things.md#linking-exits-and-rooms-in-code).
