# EvscapeRoom

Evennia contrib - Griatch 2019

This 'Evennia escaperoom game engine' was created for the MUD Coders Guild game
Jam, April 14-May 15 2019. The theme for the jam was "One Room". This contains the
utilities and base classes and an empty example room. The code for the full
in-production game 'Evscaperoom' is found at https://github.com/Griatch/evscaperoom
and you can play the full game (for now) at `http://experimental.evennia.com`.

# Introduction

Evscaperoom is, as it sounds, an escaperoom in text form. You start locked into
a room and have to figure out how to get out. This engine contains everything needed
to make a fully-featured puzzle game of this type!

# Installation

The Evscaperoom is installed by adding the `evscaperoom` command to your
character cmdset. When you run that command in-game you're ready to play!

In `mygame/commands/default_cmdsets.py`:

```python

from evennia.contrib.evscaperoom.commands import CmdEvscapeRoomStart

class CharacterCmdSet(...):

  # ...

  self.add(CmdEvscapeRoomStart())

```
Reload the server and the `evscaperoom` command will be available. The contrib comes
with a small (very small) escape room as an example.

# Making your own evscaperoom

To do this, you need to make your own states. First make sure you can play the
simple example room installed above.

Copy `evennia/contrib/evscaperoom/states` to somewhere in your game folder (let's
assume you put it under `mygame/world/`).

Next you need to re-point Evennia to look for states in this new location. Add
the following to your `mygame/server/conf/settings.py` file:

```python
  EVSCAPEROOM_STATE_PACKAGE = "world.states"

```

Reload and the example evscaperoom should still work, but you can now modify and expand
it from your game dir!

## Other useful settings

There are a few other settings that may be useful:

- `EVSCAPEROOM_START_STATE` - default is `state_001_start` and is the name of the
  state-module to start from (without `.py`). You can change this if you want some
  other naming scheme.
- `HELP_SUMMARY_TEXT` - this is the help blurb shown when entering `help` in
  the room without an argument. The original is found at the top of
  `evennia/contrib/evscaperoom/commands.py`.


# Playing the game

You should start by `look`ing around and at objects.

The `examine <object>` command allows you to 'focus' on an object. When you do
you'll learn actions you could try for the object you are focusing on, such as
turning it around, read text on it or use it with some other object. Note that
more than one player can focus on the same object, so you won't block anyone
when you focus. Focusing on another object or use `examine` again will remove
focus.

There is also a full hint system.

# Technical

When connecting to the game, the user has the option to join an existing room
(which may already be in some state of ongoing progress), or may create a fresh
room for them to start solving on their own (but anyone may still join them later).

The room will go through a series of 'states' as the players progress through
its challenges. These states are describes as modules in .states/ and the
room will load and execute the State-object within each module to set up
and transition between states as the players progress. This allows for isolating
the states from each other and will hopefully make it easier to track
the logic and (in principle) inject new puzzles later.

Once no players remain in the room, the room and its state will be wiped.

# Design Philosophy

Some basic premises inspired the design of this.

- You should be able to resolve the room alone. So no puzzles should require the
  collaboration of multiple players. This is simply because there is no telling
  if others will actually be online at a given time (or stay online throughout).
- You should never be held up by the actions/inactions of other players. This
  is why you cannot pick up anything (no inventory system) but only
  focus/operate on items. This avoids the annoying case of a player picking up
  a critical piece of a puzzle and then logging off.
- A room's state changes for everyone at once. My first idea was to have a given
  room have different states depending on who looked (so a chest could be open
  and closed to two different players at the same time). But not only does this
  add a lot of extra complexity, it also defeats the purpose of having multiple
  players. This way people can help each other and collaborate like in a 'real'
  escape room. For people that want to do it all themselves I instead made it
  easy to start "fresh" rooms for them to take on.

All other design decisions flowed from these.
