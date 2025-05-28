# 当出口不存在时返回自定义错误信息

在 MUD 游戏中，Evennia 允许出口拥有任何名称。命令 "kitchen" 是一个有效的出口名称，"jump out the window" 或 "north" 也是如此。出口实际上由两个部分组成：一个 [Exit Object](../Components/Objects.md) 和存储在该出口对象上的一个 [Exit Command](../Components/Commands.md)。命令与出口对象具有相同的键和别名，这就是为什么你可以在房间中看到出口并只需输入其名称即可穿越。

因此，如果你尝试输入一个不存在的出口名称，Evennia 会将其视为尝试使用不存在的命令：

```
> jump out the window
Command 'jump out the window' is not available. Type "help" for help.
```

许多游戏不需要这种自由度。它们仅将基本方向定义为有效的出口名称（Evennia 的 `tunnel` 命令也提供此功能）。在这种情况下，错误消息开始显得不太合理：

```
> west
Command 'west' is not available. Maybe you meant "set" or "reset"?
```

由于我们在特定游戏中*知道*西是一个出口方向，因此如果错误消息直接告诉我们无法向西移动会更好。

```
> west
You cannot move west.
```

实现这一点的方法是为 Evennia 提供一个 _替代_ 命令，当在房间中找不到出口命令时使用。有关向 Evennia 添加新命令的过程的更多信息，请参见 [Adding Commands](Beginner-Tutorial/Part1/Beginner-Tutorial-Adding-Commands.md)。

在这个例子中，我们只会回显一条错误消息，但你可以做任何事情（比如如果撞到墙会失去生命值）。

```python
# 例如在文件 mygame/commands/movecommands.py 中

from evennia import default_cmds, CmdSet

class CmdExitError(default_cmds.MuxCommand):
    """所有出口错误的父类。"""
    locks = "cmd:all()"
    arg_regex = r"\s|$"
    auto_help = False
    
    def func(self):
        """根据键返回错误"""
        self.caller.msg(f"You cannot move {self.key}.")

class CmdExitErrorNorth(CmdExitError):
    key = "north"
    aliases = ["n"]

class CmdExitErrorEast(CmdExitError):
    key = "east"
    aliases = ["e"]

class CmdExitErrorSouth(CmdExitError):
    key = "south"
    aliases = ["s"]

class CmdExitErrorWest(CmdExitError):
    key = "west"
    aliases = ["w"]

# 你可以将每个命令单独添加到默认命令集中，
# 但在此处将它们全部放入一个命令集允许你
# 仅添加此命令集，并使将来扩展更多出口错误更容易。

class MovementFailCmdSet(CmdSet):
    def at_cmdset_creation(self): 
        self.add(CmdExitErrorNorth())
        self.add(CmdExitErrorEast())
        self.add(CmdExitErrorWest())
        self.add(CmdExitErrorSouth()) 
```

我们将命令打包到一个新的小命令集中；如果我们将其添加到 `CharacterCmdSet`，以后可以轻松地向 `MovementFailCmdSet` 添加更多错误，而无需在两个地方更改代码。

```python
# 在 mygame/commands/default_cmdsets.py 中

from commands import movecommands

# [...]
class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # [...]
    def at_cmdset_creation(self):
        # [...]
        # 这会一次性添加所有命令
        self.add(movecommands.MovementFailCmdSet)
```

`reload` 服务器。此后发生的情况是，如果你在一个有出口对象的房间中（假设是 "north"），适当的出口命令将 _覆盖_ 你的错误命令（也命名为 "north"）。但是如果你输入一个没有匹配出口的方向，你将回退到默认的错误命令：

```
> east
You cannot move east.
```

通过修改 [Exit typeclass](../Components/Typeclasses.md)，可以进一步扩展出口系统（包括操作出口命令本身的创建方式）。

## 为什么不使用单个命令？

那么，为什么我们不创建一个单一的错误命令呢？比如这样：

```python
class CmdExitError(default_cmds.MuxCommand):
    "处理所有出口错误。"
    key = "error_cmd"
    aliases = ["north", "n", 
               "east", "e",
               "south", "s",
               "west", "w"]
    #[...]
```

这将*不会*按我们想要的方式工作。理解原因很重要。

Evennia 的 [命令系统](../Components/Commands.md)通过键和/或别名比较命令。如果 _任何_ 键或别名匹配，这两个命令被视为 _相同_。当命令集合并时，优先级将决定这些“相同”命令中的哪个替换哪个。

因此，上面的例子在房间中 _完全没有出口_ 的情况下工作得很好。但是当我们进入一个有出口 "north" 的房间时，其出口命令（具有更高优先级）将覆盖具有别名 "north" 的单个 `CmdExitError`。因此 `CmdExitError` 将消失，而 "north" 将正常工作，但对于其他方向，我们将再次收到正常的“命令未识别”错误。
