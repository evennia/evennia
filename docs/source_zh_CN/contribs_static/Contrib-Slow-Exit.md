# Slow Exit

由 Griatch 于 2014 年贡献

这是一个延迟穿越的 Exit 类型示例。这模拟了许多游戏中常见的缓慢移动。该 contrib 还包含两个命令，`setspeed` 和 `stop`，分别用于更改移动速度和中止正在进行的穿越。

## 安装：

要尝试这种类型的出口，您可以使用如下命令连接两个现有房间：

```
@open north:contrib.grid.slow_exit.SlowExit = <destination>
```

要将其设为新的默认出口，请修改 `mygame/typeclasses/exits.py` 以导入此模块，并将默认的 `Exit` 类更改为继承自 `SlowExit`。

```python
# 在 mygame/typeclasses/exits.py 中

from evennia.contrib.grid.slowexit import SlowExit

class Exit(SlowExit):
    # ...
```

要获取更改速度和中止移动的功能，请导入以下内容：

```python
# 在 mygame/commands/default_cmdsets.py 中

from evennia.contrib.grid import slow_exit  # <---

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ...
    def at_cmdset_creation(self):
        # ...
        self.add(slow_exit.SlowDoorCmdSet)  # <---
```

只需从此模块导入并添加 CmdSetSpeed 和 CmdStop 到您的默认 cmdset（如果不确定如何操作，请参阅教程）。

要尝试这种类型的出口，您可以使用如下命令连接两个现有房间：

```
@open north:contrib.grid.slow_exit.SlowExit = <destination>
```

## 注意事项：

此实现是高效的但不是持久的；因此，在服务器重新加载时，不完整的移动将会丢失。对于大多数游戏类型来说，这是可以接受的——要模拟更长的旅行时间（超过此处假定的几秒钟），使用 Scripts 或 TickerHandler 的更持久的变体可能更好。
