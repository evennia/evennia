# Basic Map

Contribution - helpme 2022

This adds a `map` to a given room which can be viewed with the `map` command. You can
easily alter it to add special characters denoting environments, room colors and so on.
If you don't expect the map to be updated frequently, you could choose to save the
calculated map as a .ndb value on the room and render that instead of running mapping
calculations anew each time.

## Installation:

Adding the `BasicMapCmdSet` to the default character cmdset will add the `map` command.

Specifically, in `mygame/commands/default_cmdsets.py`:

```python
...
from evennia.contrib.grid.basicmap import basicmap   # <---

class CharacterCmdset(default_cmds.Character_CmdSet):
    ...
    def at_cmdset_creation(self):
        ...
        self.add(basicmap.BasicMapCmdSet)  # <---

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
