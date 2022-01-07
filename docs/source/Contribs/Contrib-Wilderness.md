# Wilderness system

Evennia contrib - titeuf87 2017

This contrib provides a wilderness map without actually creating a large number
of rooms - as you move, your room is instead updated with different
descriptions. This means you can make huge areas with little database use as
long as the rooms are relatively similar (name/desc changing).

## Installation

This contrib does not provide any new commands. Instead the default `py` command
is used to call functions/classes in this contrib directly.

## Usage

A wilderness map needs to created first. There can be different maps, all
with their own name. If no name is provided, then a default one is used. Internally,
the wilderness is stored as a Script with the name you specify. If you don't
specify the name, a script named "default" will be created and used.

    @py from evennia.contrib.grid import wilderness; wilderness.create_wilderness()

Once created, it is possible to move into that wilderness map:

    @py from evennia.contrib.grid import wilderness; wilderness.enter_wilderness(me)

All coordinates used by the wilderness map are in the format of `(x, y)`
tuples. x goes from left to right and y goes from bottom to top. So `(0, 0)`
is the bottom left corner of the map.

## Customisation

The defaults, while useable, are meant to be customised. When creating a
new wilderness map it is possible to give a "map provider": this is a
python object that is smart enough to create the map.

The default provider, `WildernessMapProvider`, just creates a grid area that
is unlimited in size.
This `WildernessMapProvider` can be subclassed to create more interesting
maps and also to customize the room/exit typeclass used.

There is also no command that allows players to enter the wilderness. This
still needs to be added: it can be a command or an exit, depending on your
needs.

## Example

To give an example of how to customize, we will create a very simple (and
small) wilderness map that is shaped like a pyramid. The map will be
provided as a string: a "." symbol is a location we can walk on.

Let's create a file `world/pyramid.py`:

```python
# mygame/world/pyramid.py

map_str = '''
     .
    ...
   .....
  .......
'''

from evennia.contrib.grid import wilderness

class PyramidMapProvider(wilderness.WildernessMapProvider):

    def is_valid_coordinates(self, wilderness, coordinates):
        "Validates if these coordinates are inside the map"
        x, y = coordinates
        try:
            lines = map_str.split("\n")
            # The reverse is needed because otherwise the pyramid will be
            # upside down
            lines.reverse()
            line = lines[y]
            column = line[x]
            return column == "."
        except IndexError:
            return False

    def get_location_name(self, coordinates):
        "Set the location name"
        x, y = coordinates
        if y == 3:
            return "Atop the pyramid."
        else:
            return "Inside a pyramid."

    def at_prepare_room(self, coordinates, caller, room):
        "Any other changes done to the room before showing it"
        x, y = coordinates
        desc = "This is a room in the pyramid."
        if y == 3 :
            desc = "You can see far and wide from the top of the pyramid."
        room.db.desc = desc
```

Now we can use our new pyramid-shaped wilderness map. From inside Evennia we
create a new wilderness (with the name "default") but using our new map provider:

    py from world import pyramid as p; p.wilderness.create_wilderness(mapprovider=p.PyramidMapProvider())
    py from evennia.contrib import wilderness; wilderness.enter_wilderness(me, coordinates=(4, 1))

## Implementation details

When a character moves into the wilderness, they get their own room. If they
move, instead of moving the character, the room changes to match the new
coordinates.  If a character meets another character in the wilderness, then
their room merges. When one of the character leaves again, they each get their
own separate rooms.  Rooms are created as needed. Unneeded rooms are stored away
to avoid the overhead cost of creating new rooms again in the future.


----

<small>This document page is generated from `evennia/contrib/grid/wilderness/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
