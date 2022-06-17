# Extended Room

Contribution - Griatch 2012, vincent-lg 2019

This extends the normal `Room` typeclass to allow its description to change 
with time-of-day and/or season. It also adds 'details' for the player to look at 
in the room (without having to create a new in-game object for each). The room is 
supported by new `look` and `desc` commands.

## Installation/testing:

Adding the `ExtendedRoomCmdset` to the default character cmdset will add all
new commands for use.

In more detail, in `mygame/commands/default_cmdsets.py`:

```python
...
from evennia.contrib import extended_room   # <---

class CharacterCmdset(default_cmds.Character_CmdSet):
    ...
    def at_cmdset_creation(self):
        ...
        self.add(extended_room.ExtendedRoomCmdSet)  # <---

```

Then reload to make the bew commands available. Note that they only work
on rooms with the typeclass `ExtendedRoom`. Create new rooms with the right
typeclass or use the `typeclass` command to swap existing rooms.

## Features

### Time-changing description slots

This allows to change the full description text the room shows
depending on larger time variations. Four seasons (spring, summer,
autumn and winter) are used by default. The season is calculated
on-demand (no Script or timer needed) and updates the full text block.

There is also a general description which is used as fallback if
one or more of the seasonal descriptions are not set when their
time comes.

An updated `desc` command allows for setting seasonal descriptions.

The room uses the `evennia.utils.gametime.GameTime` global script. This is
started by default, but if you have deactivated it, you need to
supply your own time keeping mechanism.

### In-description changing tags

Within each seasonal (or general) description text, you can also embed
time-of-day dependent sections. Text inside such a tag will only show
during that particular time of day. The tags looks like `<timeslot> ...
</timeslot>`. By default there are four timeslots per day - morning,
afternoon, evening and night.

### Details

The Extended Room can be "detailed" with special keywords. This makes
use of a special `Look` command. Details are "virtual" targets to look
at, without there having to be a database object created for it. The
Details are simply stored in a dictionary on the room and if the look
command cannot find an object match for a `look <target>` command it
will also look through the available details at the current location
if applicable. The `detail` command is used to change details.

### Extra commands

- `CmdExtendedRoomLook` - look command supporting room details
- `CmdExtendedRoomDesc` - desc command allowing to add seasonal descs,
- `CmdExtendedRoomDetail` - command allowing to manipulate details in this room
  as well as listing them
- `CmdExtendedRoomGameTime` - A simple `time` command, displaying the current
  time and season.


----

<small>This document page is generated from `evennia/contrib/grid/extended_room/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
