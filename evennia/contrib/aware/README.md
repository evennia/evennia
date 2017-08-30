# Aware contrib

Evennia contributors: Chainsol, Vincent Le Goff, 2017

The goal of this contrib is to add simple awareness from characters (or really, any object) in an
Evennia world.  This awareness would present the first opportunity for artificial intelligence to set in,
particularly with NPCs (Non-Playing Characters).  Although the aware contrib doesn't add all the features
of a responsive game and intelligent characters, it provides a good basis on which truly advanced behavior
could be created and expanded.

## Installation

All that is required to install this contrib is to have the signal handler and action handler available
to the typeclass on which you want to add awareness.  Usually, you would want to edit the `Character` class,
but notice that you can easily add this feature to all your typeclasses (particularly `Object`, `Room`
and `Exit`).

The details of the two handlers, `AcitonHandler` and `SignalHandler` will be discussed in the following
sections.  In short:

- The `ActionHandler` (available under `obj.actions` once installed) allows to add actions with priorities, like flee or do a command or
    move one or several rooms following a path.  There is no real interest to place this handler except on
    the `Character` class (or the `NPC` class, if you have one).
- The `SignalHandler` (available under `obj.signals` once installed) allows to subscribe to signals
    (particular inputs) and to throw them.  The latter might be useful for other typeclasses (a room
    might want to throw a "warning"  signal to all its content, for instance).

To have access to these features, you can inherit from:

- `evennia.contrib.aware.mixins.AwareMixin`: gives both the `ActionHandler` and `SignalHandler`.
- `evennia.contrib.aware.mixins.SignalsMixin`: gives the ability to throw signals (and subscribe to them), but not to have an action queue.

A possible setup would be:

- In `typeclasses.characters.py`:

```python
"""
Characters.
"""

from evennia import DefaultCharacter
from evennia.contrib.aware.mixins import AwareMixin

class Character(AwareMixin, DefaultCharactert):

    pass
```

Your objects using the `Character`  class will now be able to do `obj.signals` to access the `SignalHandler`
and `obj.actions` to access the `ActionHandler`.

- In `typeclasses.rooms.py`:

```python
"""
Rooms.
"""

from evennia import DefaultRoom
from evennia.contrib.aware.mixins import SignalsMixin

class Room(SignalsMixin, DefaultRoom):

    pass
```

Your objects using the `Room`  class will now be able to do `obj.signals` to access the `SignalHandler`, but not `obj.actions` to access the `ActionHandler`.

## Basic principle

Character awareness in this contrib relies on two main features:

- Signals are used to warn objects about specific events around them.  These signals could be awareness of a
    dangerous situation.  For instance, if you start to attack an NPC, it might throw the "threat" signal to
    all the other NPCs in the same room, so they would know something threatening is happening, and will
    be able to react appropriately (by helping the first NPC, or fleeing away, or calling the guards, or whatever).
- Actions are taken to react to a signal.  NPCs could react in different ways to identical signals, as shown above.

This combined system of signals and actions will determine what characters will do in response to a given
situation.  Both signals and actions can be extended to a great extent.  The cycle could be described as follow:

1. A signal is thrown.  Let's say gunfire erupted to the south of this room.  All characters will be
    notified of this signal.  It allows, virtually, to add the same system to players or objects or even exits.
2. An object (like a character) is subscribed to this signal.  It has defined that it should flee in the
    opposite direction if such a signal should be thrown.  So it adds the action "flee to the north"  to its action queue.
3. The action queue will be executed, making this character start to flee to the north.

## List of actions
## Example 1: an idle citizen
## Actions with priorities
## Example 2: a weary guard
## Add a new action
## Example 3: a caring mother
## Appendix: plugging in the in-game Python system

