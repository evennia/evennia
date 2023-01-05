# Basic Map

Contribution - helpme 2022

This adds an ascii `map` to a given room which can be viewed with the `map` command.
You can easily alter it to add special characters, room colors etc. The map shown is
dynamically generated on use, and supports all compass directions and up/down. Other
directions are ignored.

If you don't expect the map to be updated frequently, you could choose to save the
calculated map as a .ndb value on the room and render that instead of running mapping
calculations anew each time.

## Installation:

Adding the `MapDisplayCmdSet` to the default character cmdset will add the `map` command.

Specifically, in `mygame/commands/default_cmdsets.py`:

```python
...
from evennia.contrib.grid.ingame_map_display import MapDisplayCmdSet   # <---

class CharacterCmdset(default_cmds.CharacterCmdSet):
    ...
    def at_cmdset_creation(self):
        ...
        self.add(MapDisplayCmdSet)  # <---

```

Then `reload` to make the new commands available. 

## Settings:

In order to change your default map size, you can add to `mygame/server/settings.py`:

```python
BASIC_MAP_SIZE = 5  # This changes the default map width/height.

```

## Features:

### ASCII map (and evennia supports UTF-8 characters and even emojis)

This produces an ASCII map for players of configurable size.

### New command

- `CmdMap` - view the map
