# 角色连接方式

```shell
> login Foobar password123
```

Evennia 支持多种方式让玩家连接到游戏。这使得 Evennia 可以模拟其他服务器的行为，或者为自定义解决方案打开可能性。

## 更改登录界面

可以通过修改 `mygame/server/conf/connection_screens.py` 并重新加载来实现。如果你不喜欢默认的登录界面，可以参考以下两个贡献模块：

- [Email 登录](../Contribs/Contrib-Email-Login.md) - 在安装时要求输入电子邮件，并使用电子邮件进行登录。
- [菜单登录](../Contribs/Contrib-Menu-Login.md) - 通过多个提示登录，依次输入用户名和密码。

## 自定义登录命令

当玩家连接到游戏时，会运行 `CMD_LOGINSTART` [系统命令](../Components/Commands.md#system-commands)。默认情况下，这是 [CmdUnconnectedLook](evennia.commands.default.unloggedin.CmdUnconnectedLook)，它显示欢迎界面。其他命令在 [UnloggedinCmdSet](evennia.commands.default.cmdset_unloggedin.UnloggedinCmdSet) 中定义了登录体验。因此，如果你想自定义它，只需替换或移除这些命令。

```{sidebar}
如果你的命令继承自 `default_cmds.UnConnectedLook`，你甚至不需要指定键（因为你的类会继承它）！
```

```python
# 在 mygame/commands/mylogin_commands.py 中

from evennia import syscmdkeys, default_cmds, Command

class MyUnloggedinLook(Command):

    # 这将成为连接时调用的第一个命令
    key = syscmdkeys.CMD_LOGINSTART 

    def func(self):
        # ... 
```

接下来，将其添加到 `UnloggedinCmdSet` 的正确位置：

```python
# 在 mygame/commands/default_cmdsets.py 中

from commands.mylogin_commands import MyUnloggedinLook
# ... 

class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    # ... 
    def at_cmdset_creation(self):
        super().at_cmdset_creation
        self.add(MyUnloggedinLook())
```

`reload` 后，你的替代命令将被使用。查看默认命令，你可以更改有关登录的一切。

## 多会话模式和多角色游戏

可以同时连接到给定账户的会话数量及其工作方式由 `MULTISESSION_MODE` 设置决定：

* `MULTISESSION_MODE=0`：每个账户一个会话。当用新会话连接时，旧会话将断开。这是默认模式，模拟许多经典 mud 代码库。
    ```
    ┌──────┐ │   ┌───────┐    ┌───────┐   ┌─────────┐
    │Client├─┼──►│Session├───►│Account├──►│Character│
    └──────┘ │   └───────┘    └───────┘   └─────────┘
    ```
* `MULTISESSION_MODE=1`：每个账户多个会话，来自每个会话的输入/输出被视为相同。对于玩家来说，这意味着他们可以从多个客户端连接到游戏，并在所有客户端中看到相同的输出。在一个客户端中给出的命令的结果（即，通过一个会话）将返回给*所有*连接的会话/客户端，没有区别。
    ```
             │
    ┌──────┐ │   ┌───────┐
    │Client├─┼──►│Session├──┐
    └──────┘ │   └───────┘  └──►┌───────┐   ┌─────────┐
             │                  │Account├──►│Character│
    ┌──────┐ │   ┌───────┐  ┌──►└───────┘   └─────────┘
    │Client├─┼──►│Session├──┘
    └──────┘ │   └───────┘
             │
    ```

* `MULTISESSION_MODE=2`：每个账户多个会话，每个会话一个角色。在此模式下，控制一个对象/角色将仅将控制链接回进行控制的特定会话。也就是说，来自该会话的输入将使用该对象/角色的 CmdSet，传出的消息（例如 `look` 的结果）将仅传回给进行控制的会话。如果另一个会话尝试控制相同的角色，旧会话将自动解除控制。从玩家的角度来看，这意味着他们可以打开单独的游戏客户端，并使用一个游戏账户在每个客户端中玩不同的角色。
    ```
             │                 ┌───────┐
    ┌──────┐ │   ┌───────┐     │Account│    ┌─────────┐
    │Client├─┼──►│Session├──┐  │       │  ┌►│Character│
    └──────┘ │   └───────┘  └──┼───────┼──┘ └─────────┘
             │                 │       │
    ┌──────┐ │   ┌───────┐  ┌──┼───────┼──┐ ┌─────────┐
    │Client├─┼──►│Session├──┘  │       │  └►│Character│
    └──────┘ │   └───────┘     │       │    └─────────┘
             │                 └───────┘
    ```
* `MULTISESSION_MODE=3`：每个账户和角色多个会话。这是完整的多控制模式，多个会话不仅可以连接到玩家账户，还可以同时控制单个角色。从用户的角度来看，这意味着可以打开多个客户端窗口，有些用于控制不同的角色，有些则像模式 1 一样共享角色的输入/输出。此模式的其他工作方式与模式 2 相同。
    ```
             │                 ┌───────┐
    ┌──────┐ │   ┌───────┐     │Account│    ┌─────────┐
    │Client├─┼──►│Session├──┐  │       │  ┌►│Character│
    └──────┘ │   └───────┘  └──┼───────┼──┘ └─────────┘
             │                 │       │
    ┌──────┐ │   ┌───────┐  ┌──┼───────┼──┐
    │Client├─┼──►│Session├──┘  │       │  └►┌─────────┐
    └──────┘ │   └───────┘     │       │    │Character│
             │                 │       │  ┌►└─────────┘
    ┌──────┐ │   ┌───────┐  ┌──┼───────┼──┘             ▼
    │Client├─┼──►│Session├──┘  │       │
    └──────┘ │   └───────┘     └───────┘
             │
    ```

> 请注意，即使多个会话控制一个角色，该角色也只有一个实例。

模式 `0` 是默认的，模拟了许多传统代码库的工作方式，特别是在 DIKU 世界中。更高模式的等效性通常被“黑客”用来允许玩家拥有多个角色。

    MAX_NR_SIMULTANEOUS_PUPPETS = 1

此设置限制了你的账户可以同时控制的不同角色的数量。这用于限制真正的多角色游戏。除非 `MULTISESSION_MODE` 也设置为 `>1`，否则设置为高于 1 的值没有意义。设置为 `None` 表示没有限制。

## 角色创建和自动控制

当玩家首次创建账户时，Evennia 会自动创建一个同名的 `Character` 控制对象。当玩家登录时，他们将自动控制此角色。此默认设置将账户-角色分离隐藏起来，并立即将玩家放入游戏中。此默认行为类似于许多传统 MU 服务器的工作方式。

要控制此行为，你需要调整设置。以下是默认设置：

    AUTO_CREATE_CHARACTER_WITH_ACCOUNT = True
    AUTO_PUPPET_ON_LOGIN = True 
    MAX_NR_CHARACTERS = 1
    
有一个默认的 `charcreate` 命令。它遵循 `MAX_NR_CHARACTERS`；如果你创建自己的角色创建命令，也应遵循这一点。至少需要设置为 `1`。设置为 `None` 表示没有限制。有关如何制作更高级角色生成系统的想法，请参阅 [初学者教程](../Howtos/Beginner-Tutorial/Beginner-Tutorial-Overview.md)。

```{sidebar}
结合这些设置和 `MAX_NR_SIMULTANEOUS_PUPPETS`，可以创建一个游戏，例如，玩家可以创建一个角色“稳定”，但一次只能玩一个角色。
```

如果你选择不自动创建角色，则需要提供角色生成，并且最初将没有（初始）角色进行控制。在这两种设置中，登录后你将最初进入 `ooc` 模式。这是放置角色生成屏幕/菜单的好地方（例如，可以替换 [CmdOOCLook](evennia.commands.default.account.CmdOOCLook) 以触发正常的 ooc-look 之外的内容）。

一旦创建了角色，如果设置了自动控制，则每次登录时将自动控制你最近控制的角色。如果未设置，你将始终从 OOC 开始（并应能够选择要控制的角色）。
