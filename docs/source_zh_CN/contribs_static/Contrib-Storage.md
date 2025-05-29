# 物品存储

由 helpme 贡献于 2024 年

该模块允许将某些房间标记为存储位置。

在这些房间中，玩家可以 `list`、`store` 和 `retrieve` 物品。存储可以是共享的，也可以是个人的。

## 安装

该工具添加了与存储相关的命令。将模块导入你的命令中，并将其添加到你的命令集中以使其可用。

具体来说，在 `mygame/commands/default_cmdsets.py` 中：

```python
...
from evennia.contrib.game_systems.storage import StorageCmdSet   # <---

class CharacterCmdset(default_cmds.Character_CmdSet):
    ...
    def at_cmdset_creation(self):
        ...
        self.add(StorageCmdSet)  # <---

```

然后 `reload` 以使 `list`、`retrieve`、`store` 和 `storage` 命令可用。

## 使用

要将某个位置标记为具有物品存储，请使用 `storage` 命令。默认情况下，这是一个构建者级别的命令。存储可以是共享的，这意味着使用存储的每个人都可以访问存储在那里所有物品，或者是个人的，这意味着只有存储物品的人才能取回它。有关详细信息，请参见 `help storage`。

## 技术信息

这是一个基于标签的系统。被设置为存储房间的房间会被标记为共享或不共享的标识符。在这些房间中存储的物品会被标记为存储房间的标识符，如果存储房间不是共享的，还会被标记为角色标识符，然后它们会从网格中移除，即它们的位置被设置为 `None`。在取回时，物品会被取消标记并移回角色的库存。

当使用 `storage` 命令取消标记房间为存储时，所有存储的物品都会被取消标记并掉落到房间中。你应该使用 `storage` 命令来创建和移除存储，否则存储的物品可能会丢失。
