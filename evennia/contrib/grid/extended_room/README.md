# Extended Room

Contribution - Griatch 2012, vincent-lg 2019, Griatch 2023

This extends the normal `Room` typeclass to allow its description to change with
time-of-day and/or season as well as any other state (like flooded or dark).
Embedding `$state(burning, This place is on fire!)` in the description will
allow for changing the description based on room state. The room also supports
`details` for the player to look at in the room (without having to create a new
in-game object for each), as well as support for random echoes. The room
comes with a set of alternate commands for `look` and `@desc`, as well as new
commands `detail`, `roomstate` and `time`.

## Installation

Add the `ExtendedRoomCmdset` to the default character cmdset will add all
new commands for use.

In more detail, in `mygame/commands/default_cmdsets.py`:

```python
...
from evennia.contrib.grid import extended_room   # <---

class CharacterCmdset(default_cmds.CharacterCmdSet):
    ...
    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        ...
        self.add(extended_room.ExtendedRoomCmdSet)  # <---

```

Then reload to make the new commands available. Note that they only work
on rooms with the typeclass `ExtendedRoom`. Create new rooms with the right
typeclass or use the `typeclass` command to swap existing rooms. Note that since
this contrib overrides the `look` and `@desc` commands, you will need to add the
`extended_room.ExtendedRoomCmdSet` to the default character cmdset *after*
`super().at_cmdset_creation()`, or they will be overridden by the default look.

To dig a new extended room:

    dig myroom:evennia.contrib.grid.extended_room.ExtendedRoom = north,south

To make all new rooms ExtendedRooms without having to specify it, make your
`Room` typeclass inherit from the `ExtendedRoom` and then reload:

```python
# in mygame/typeclasses/rooms.py

from evennia.contrib.grid.extended_room import ExtendedRoom

# ...

class Room(ObjectParent, ExtendedRoom):
    # ...

```

## Features

### State-dependent description slots

By default, the normal `room.db.desc` description is used. You can however
add new state-ful descriptions with `room.add_desc(description,
room_state=roomstate)` or with the in-game command

```
@desc/roomstate [<description>]
```

For example

```
@desc/dark This room is pitch black.`.

```


These will be stored in Attributes `desc_<roomstate>`. To set the default,
fallback description, just use `@desc <description>`.
To activate a state on the room, use `room.add/remove_state(*roomstate)` or the in-game
command
```
roomstate <state>      (use it again to toggle the state off)
```
For example
```
roomstate dark
```
There is one in-built, time-based state `season`. By default these are 'spring',
'summer', 'autumn' and 'winter'. The `room.get_season()` method returns the
current season based on the in-game time. By default they change with a 12-month
in-game time schedule. You can control them with
```
ExtendedRoom.months_per_year      # default 12
ExtendedRoom.seasons_per year     # a dict of {"season": (start, end), ...} where
                                  # start/end are given in fractions of the whole year
```
To set a seasonal description, just set it as normal, with `room.add_desc` or
in-game with

```
@desc/winter This room is filled with snow.
@desc/autumn Red and yellow leaves cover the ground.
```

Normally the season changes with the in-game time, you can also 'force' a given
season by setting its state
```
roomstate winter
```
If you set the season manually like this, it won't change automatically again
until you unset it.

You can get the stateful description from the room with `room.get_stateful_desc()`.

### Changing parts of description based on state

All descriptions can have embedded `$state(roomstate, description)`
[FuncParser tags](FuncParser) embedded in them. Here is an example:

```py
room.add_desc("This a nice beach. "
              "$state(empty, It is completely empty)"
              "$state(full, It is full of people).", room_state="summer")
```

This is a summer-description with special embedded strings. If you set the room
with

    > room.add_room_state("summer", "empty")
    > room.get_stateful_desc()

    This is a nice beach. It is completely empty.

    > room.remove_room_state("empty")
    > room.add_room_state("full")
    > room.get_stateful_desc()

    This is a nice beach. It is full of people.

There are four default time-of-day states that are meant to be used with these tags. The
room tracks and changes these automatically. By default they are 'morning',
'afternoon', 'evening' and 'night'. You can get the current time-slot with
`room.get_time_of_day`. You can control them with

```
ExtendedRoom.hours_per_day    # default 24
ExtendedRoom.times_of_day     # dict of {season: (start, end), ...} where
                              # the start/end are given as fractions of the day.
```

You use these inside descriptions as normal:

    "A glade. $(morning, The morning sun shines down through the branches)."

### Details

_Details_ are "virtual" targets to look at in a room, without having to create a
new database instance for every thing. It's good to add more information to a
location. The details are stored as strings in a dictionary.

    detail window = There is a window leading out.
    detail rock = The rock has a text written on it: 'Do not dare lift me'.

When you are in the room you can then do `look window` or `look rock` and get
the matching detail-description. This requires the new custom `look` command.

### Random echoes

The `ExtendedRoom` supports random echoes. Just set them as an Attribute list
`room_messages`:

```
room.room_message_rate = 120   # in seconds. 0 to disable
room.db.room_messages = ["A car passes by.", "You hear the sound of car horns."]
room.start_repeat_broadcast_messages()   # also a server reload works
```

These will start randomly echoing to the room every 120s.


### Extra commands

- `CmdExtendedRoomLook` (`look`) - look command supporting room details
- `CmdExtendedRoomDesc` (`@desc`) - desc command allowing to add stateful descs,
- `CmdExtendeRoomState` (`roomstate`) - toggle room states
- `CmdExtendedRoomDetail` (`detail`) - list and manipulate room details
- `CmdExtendedRoomGameTime` (`time`) - Shows the current time and season in the room.
