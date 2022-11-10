"""
Slow Exit typeclass

Contribution - Griatch 2014


This is an example of an Exit-type that delays its traversal. This
simulates slow movement, common in many different types of games. The
contrib also contains two commands, `CmdSetSpeed` and CmdStop for changing
the movement speed and abort an ongoing traversal, respectively.

## Installation:

To try out an exit of this type, you could connect two existing rooms
using something like this:

@open north:contrib.grid.slow_exit.SlowExit = <destination>

To make this your new default exit, modify `mygame/typeclasses/exits.py`
to import this module and change the default `Exit` class to inherit
from `SlowExit` instead.

```
# in mygame/typeclasses/exits.py

from evennia.contrib.grid.slowexit import SlowExit

class Exit(SlowExit):
    # ...

```

To get the ability to change your speed and abort your movement, import

```python
# in mygame/commands/default_cmdsets.py

from evennia.contrib.grid import slow_exit  <---

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ...
    def at_cmdset_creation(self):
        # ...
        self.add(slow_exit.SlowDoorCmdSet)  <---

```

## Notes:

This implementation is efficient but not persistent; so incomplete
movement will be lost in a server reload. This is acceptable for most
game types - to simulate longer travel times (more than the couple of
seconds assumed here), a more persistent variant using Scripts or the
TickerHandler might be better.

"""

from evennia.commands.cmdset import CmdSet
from evennia.commands.command import Command
from evennia.objects.objects import DefaultExit
from evennia.utils import utils

MOVE_DELAY = {"stroll": 6, "walk": 4, "run": 2, "sprint": 1}


class SlowExit(DefaultExit):
    """
    This overloads the way moving happens.
    """

    def at_traverse(self, traversing_object, target_location):
        """
        Implements the actual traversal, using utils.delay to delay the move_to.
        """

        # if the traverser has an Attribute move_speed, use that,
        # otherwise default to "walk" speed
        move_speed = traversing_object.db.move_speed or "walk"
        move_delay = MOVE_DELAY.get(move_speed, 4)

        def move_callback():
            "This callback will be called by utils.delay after move_delay seconds."
            source_location = traversing_object.location
            if traversing_object.move_to(target_location, move_type="traverse"):
                self.at_post_traverse(traversing_object, source_location)
            else:
                if self.db.err_traverse:
                    # if exit has a better error message, let's use it.
                    self.caller.msg(self.db.err_traverse)
                else:
                    # No shorthand error message. Call hook.
                    self.at_failed_traverse(traversing_object)

        traversing_object.msg("You start moving %s at a %s." % (self.key, move_speed))
        # create a delayed movement
        t = utils.delay(move_delay, move_callback)
        # we store the deferred on the character, this will allow us
        # to abort the movement. We must use an ndb here since
        # deferreds cannot be pickled.
        traversing_object.ndb.currently_moving = t


#
# set speed - command
#

SPEED_DESCS = {"stroll": "strolling", "walk": "walking", "run": "running", "sprint": "sprinting"}


class CmdSetSpeed(Command):
    """
    set your movement speed

    Usage:
      setspeed stroll|walk|run|sprint

    This will set your movement speed, determining how long time
    it takes to traverse exits. If no speed is set, 'walk' speed
    is assumed.
    """

    key = "setspeed"

    def func(self):
        """
        Simply sets an Attribute used by the SlowExit above.
        """
        speed = self.args.lower().strip()
        if speed not in SPEED_DESCS:
            self.caller.msg("Usage: setspeed stroll||walk||run||sprint")
        elif self.caller.db.move_speed == speed:
            self.caller.msg("You are already %s." % SPEED_DESCS[speed])
        else:
            self.caller.db.move_speed = speed
            self.caller.msg("You are now %s." % SPEED_DESCS[speed])


#
# stop moving - command
#


class CmdStop(Command):
    """
    stop moving

    Usage:
      stop

    Stops the current movement, if any.
    """

    key = "stop"

    def func(self):
        """
        This is a very simple command, using the
        stored deferred from the exit traversal above.
        """
        currently_moving = self.caller.ndb.currently_moving
        if currently_moving and not currently_moving.called:
            currently_moving.cancel()
            self.caller.msg("You stop moving.")
            for observer in self.caller.location.contents_get(self.caller):
                observer.msg("%s stops." % self.caller.get_display_name(observer))
        else:
            self.caller.msg("You are not moving.")


class SlowExitCmdSet(CmdSet):
    def at_cmdset_creation(self):
        self.add(CmdSetSpeed())
        self.add(CmdStop())
