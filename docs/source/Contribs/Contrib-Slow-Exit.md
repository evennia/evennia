# Slow Exit

Contribution - Griatch 2014

This is an example of an Exit-type that delays its traversal. This simulates
slow movement, common in many different types of games. The contrib also
contains two commands, `CmdSetSpeed` and CmdStop for changing the movement speed
and abort an ongoing traversal, respectively.

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

simply import and add CmdSetSpeed and CmdStop from this module to your
default cmdset (see tutorials on how to do this if you are unsure).

To try out an exit of this type, you could connect two existing rooms using
something like this:

    @open north:contrib.grid.slow_exit.SlowExit = <destination>


## Notes:

This implementation is efficient but not persistent; so incomplete
movement will be lost in a server reload. This is acceptable for most
game types - to simulate longer travel times (more than the couple of
seconds assumed here), a more persistent variant using Scripts or the
TickerHandler might be better.


----

<small>This document page is generated from `evennia/contrib/grid/slow_exit/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
