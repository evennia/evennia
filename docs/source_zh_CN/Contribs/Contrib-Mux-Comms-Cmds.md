# Legacy Comms-commands

Contribution by Griatch 2021

In Evennia 1.0+, the old Channel commands (originally inspired by MUX) were
replaced by the single `channel` command that performs all these functions.
This contrib (extracted from Evennia 0.9.5) breaks out the functionality into 
separate Commands more familiar to MU* users. This is just for show though, the 
main `channel` command is still called under the hood.

| Contrib syntax | Default `channel` syntax                                  |
| -------------- | --------------------------------------------------------- |
| `allcom`       |  `channel/all` and `channel`                              |
| `addcom`       | `channel/alias`, `channel/sub` and `channel/unmute`       |
| `delcom`       | `channel/unalias`, `alias/unsub` and `channel/mute`       |
| `cboot`        | `channel/boot` (`channel/ban` and `/unban` not supported) |
| `cwho`         | `channel/who`                                             |
| `ccreate`      | `channel/create`                                          |
| `cdestroy`     | `channel/destroy`                                         |
| `clock`        | `channel/lock`                                            |
| `cdesc`        | `channel/desc`                                            |

##  Installation

- Import the `CmdSetLegacyComms` cmdset from this module into `mygame/commands/default_cmdsets.py`
- Add it to the CharacterCmdSet's `at_cmdset_creation` method (see below).
- Reload the server.

```python
# in mygame/commands/default_cmdsets.py

# ..
from evennia.contrib.base_systems.mux_comms_cmds import CmdSetLegacyComms   # <----

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ...
    def at_cmdset_creation(self):
        # ...
        self.add(CmdSetLegacyComms)   # <----

```

Note that you will still be able to use the `channel` command; this is actually
still used under the hood by these commands.


----

<small>此文档页面生成自 `evennia/contrib/base_systems/mux_comms_cmds/README.md`。对此文件的更改将被覆盖，因此请编辑该文件而不是此文件。</small>
