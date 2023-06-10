# SimpleDoor

Contribution by Griatch, 2016

A simple two-way exit that represents a door that can be opened and
closed from both sides. Can easily be expanded to make it lockable, 
destroyable etc. 

Note that the simpledoor is based on Evennia locks, so it will
not work for a superuser (which bypasses all locks). The superuser
will always appear to be able to close/open the door over and over
without the locks stopping you. To use the door, use `quell` or a
non-superuser account.

## Installation:

Import `SimpleDoorCmdSet` from this module into `mygame/commands/default_cmdsets`
and add it to your `CharacterCmdSet`:

```python
# in mygame/commands/default_cmdsets.py

from evennia.contrib.grid import simpledoor  <---

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ...
    def at_cmdset_creation(self):
        # ...
        self.add(simpledoor.SimpleDoorCmdSet)

```

## Usage:

To try it out, `dig` a new room and then use the (overloaded) `@open`
commmand to open a new doorway to it like this:

    @open doorway:contrib.grid.simpledoor.SimpleDoor = otherroom

    open doorway
    close doorway

Note: This uses locks, so if you are a superuser you will not be blocked by
a locked door - `quell` yourself, if so. Normal users will find that they
cannot pass through either side of the door once it's closed from the other
side.


----

<small>This document page is generated from `evennia/contrib/grid/simpledoor/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
