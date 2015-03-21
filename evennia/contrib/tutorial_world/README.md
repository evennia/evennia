
# Evennia Tutorial World

Griatch 2011, 2015

This is a stand-alone tutorial area for an unmodified Evennia install.
Think of it as a sort of single-player adventure rather than a
full-fledged multi-player game world. The various rooms and objects
herein are designed to show off features of the engine, not to be a
very challenging (nor long) gaming experience. As such it's of course
only skimming the surface of what is possible.


## Install

Log in as superuser (#1), then run

    @batchcommand tutorial_world.build

Wait a little while for building to complete and don't run the command
again. This should build the world and connect it to Limbo.

If you are a superuser (User `#1`), use the `@quell` command to play
the tutorial as intended. 


## Comments

The tutorial world is intended for your playing around with the engine.
It will help you learn how to accomplish some more advanced effects
and might give some good ideas along the way.

It's suggested you play it through (as a normal user, NOT as
Superuser!) and explore it a bit, then come back here and start
looking into the (heavily documented) build/source code to find out
how things tick - that's the "tutorial" in Tutorial world after all.

Please report bugs in the tutorial to the Evennia issue tracker.






**Spoilers below - don't read on unless you already played the
tutorial game**






## Tutorial World Room map

         ?
         |
     +---+----+    +-------------------+    +--------+   +--------+
     |        |    |                   |    |gate    |   |corner  |
     | cliff  +----+      bridge       +----+        +---+        |
     |        |    |                   |    |        |   |        |
     +---+---\+    +---------------+---+    +---+----+   +---+----+
         |    \                    |            |   castle   |
         |     \  +--------+  +----+---+    +---+----+   +---+----+
         |      \ |under-  |  |ledge   |    |along   |   |court-  |
         |       \|ground  +--+        |    |wall    +---+yard    |
         |        \        |  |        |    |        |   |        |
         |        +------\-+  +--------+    +--------+   +---+----+
         |                \                                  |
        ++---------+       \  +--------+    +--------+   +---+----+
        |intro     |        \ |cell    |    |trap    |   |temple  |
     o--+          |         \|        +----+        |   |        |
    L   |          |          \        |   /|        |   |        |
    I   +----+-----+          +--------+  / ---+-+-+-+   +---+----+
    M        |                           /     | | |         |
    B   +----+-----+          +--------+/   +--+-+-+---------+----+
    O   |outro     |          |tomb    |    |antechamber          |
     o--+          +----------+        |    |                     |
        |          |          |        |    |                     |
        +----------+          +--------+    +---------------------+


## Hints/Notes:

* o-- connections to/from Limbo
* intro/outro areas are rooms that automatically sets/cleans the
  Character of any settings assigned to it during the
  tutorial game.
* The Cliff is a good place to get an overview of the surroundings.
* The Bridge may seem like a big room, but it is really only one room
  with custom move commands to make it take longer to cross. You can
  also fall off the bridge if you are unlucky or take your time to
  take in the view too long.
* In the Castle areas an aggressive mob is patrolling. It implements
  rudimentary AI but packs quite a punch unless you have
  found yourself a weapon that can harm it. Combat is only
  possible once you find a weapon.
* The Antechamber features a puzzle for finding the correct Grave
  chamber.
* The Cell  is your reward if you fail in various ways. Finding a
  way out of it is a small puzzle of its own.
* The Tomb  is a nice place to find a weapon that can hurt the
  castle guardian. This is the goal of the tutorial.
  Explore on, or take the exit to finish the tutorial.
* ?  - look into the code if you cannot find this bonus area!
