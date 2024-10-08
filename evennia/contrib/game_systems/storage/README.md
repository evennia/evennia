# Item Storage

Contribution by helpme (2024)

This module allows certain rooms to be marked as storage locations.

In those rooms, players can `list`, `store`, and `retrieve` items. Storages can be shared or individual.

## Installation

This utility adds the storage-related commands. Import the module into your commands and add it to your command set to make it available.

Specifically, in `mygame/commands/default_cmdsets.py`:

```python
...
from evennia.contrib.game_systems.storage import StorageCmdSet   # <---

class CharacterCmdset(default_cmds.Character_CmdSet):
    ...
    def at_cmdset_creation(self):
        ...
        self.add(StorageCmdSet)  # <---

```

Then `reload` to make the `list`, `retrieve`, `store`, and `storage` commands available.

## Usage

To mark a location as having item storage, use the `storage` command. By default this is a builder-level command. Storage can be shared, which means everyone using the storage can access all items stored there, or individual, which means only the person who stores an item can retrieve it. See `help storage` for further details.

## Technical info

This is a tag-based system. Rooms set as storage rooms are tagged with an identifier marking them as shared or not. Items stored in those rooms are tagged with the storage room identifier and, if the storage room is not shared, the character identifier, and then they are removed from the grid i.e. their location is set to `None`. Upon retrieval, items are untagged and moved back to character inventories.

When a room is unmarked as storage with the `storage` command, all stored objects are untagged and dropped to the room. You should use the `storage` command to create and remove storages, as otherwise stored objects may become lost.