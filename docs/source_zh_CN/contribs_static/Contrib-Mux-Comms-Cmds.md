# 传统通讯命令

由 Griatch 贡献于 2021 年

在 Evennia 1.0+ 中，旧的频道命令（最初受 MUX 启发）被一个执行所有这些功能的单一 `channel` 命令所取代。这个贡献模块（从 Evennia 0.9.5 中提取）将功能分解为更符合 MU* 用户习惯的独立命令。不过，这仅仅是为了展示，主要的 `channel` 命令在底层仍然被调用。

| 贡献语法 | 默认 `channel` 语法                                          |
| -------- | ------------------------------------------------------------ |
| `allcom` | `channel/all` 和 `channel`                                   |
| `addcom` | `channel/alias`、`channel/sub` 和 `channel/unmute`           |
| `delcom` | `channel/unalias`、`alias/unsub` 和 `channel/mute`           |
| `cboot`  | `channel/boot`（`channel/ban` 和 `/unban` 不支持）           |
| `cwho`   | `channel/who`                                                |
| `ccreate`| `channel/create`                                             |
| `cdestroy`| `channel/destroy`                                           |
| `clock`  | `channel/lock`                                               |
| `cdesc`  | `channel/desc`                                               |

## 安装

- 从此模块中导入 `CmdSetLegacyComms` 命令集到 `mygame/commands/default_cmdsets.py`
- 将其添加到 `CharacterCmdSet` 的 `at_cmdset_creation` 方法中（见下文）。
- 重新加载服务器。

```python
# 在 mygame/commands/default_cmdsets.py 中

# ..
from evennia.contrib.base_systems.mux_comms_cmds import CmdSetLegacyComms   # <----

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ...
    def at_cmdset_creation(self):
        # ...
        self.add(CmdSetLegacyComms)   # <----

```

请注意，你仍然可以使用 `channel` 命令；实际上这些命令在底层仍然使用该命令。
