# 账户

```
┌──────┐ │   ┌───────┐    ┌───────┐   ┌──────┐
│Client├─┼──►│Session├───►│Account├──►│Object│  
└──────┘ │   └───────┘    └───────┘   └──────┘
                              ^
```

**账户**代表一个独特的游戏账户——一个玩家在游戏中的身份。虽然玩家可以通过多个客户端/会话连接到游戏，但通常只有一个账户。

账户对象在游戏中没有实际表现。为了能够进入游戏，账户必须“控制”一个 [对象](./Objects.md)（通常是一个 [角色](./Objects.md#characters)）。

可以与一个账户及其控制的对象互动的会话数量由 Evennia 的 [MULTISESSION_MODE](../Concepts/Connection-Styles.md#multisession-mode-and-multiplaying) 决定。

除了存储登录信息和其他账户特定数据外，账户对象也是在 Evennia 默认的 [频道](./Channels.md) 上进行聊天的对象。它也是存储 [权限](./Locks.md) 的好地方，以便在不同的游戏角色之间保持一致。它还可以存储玩家级别的配置选项。

账户对象有自己的默认 [CmdSet](./Command-Sets.md)，名为 `AccountCmdSet`。该命令集中的命令无论玩家控制哪个角色都可用。最值得注意的是，默认游戏中的 `exit`、`who` 和聊天频道命令都在此账户命令集中。

> ooc 

默认的 `ooc` 命令会导致您离开当前的控制角色并进入 OOC 模式。在此模式下，您没有位置，并且只有账户命令集可用。它充当切换角色的中转区（如果您的游戏支持此功能），也是一个安全的后备选项，以防您的角色意外被删除。

> ic 

此命令重新控制最后一个角色。

请注意，账户对象可以具有并且通常与其控制的角色拥有不同的 [权限](./Permissions.md)。通常，您应该将权限放在账户级别——这将覆盖在角色级别上设置的权限。要使用角色的权限，可以使用默认的 `quell` 命令。这允许在游戏中使用不同的权限集进行探索（但您无法通过这种方式提升权限——对于像 `Builder`、`Admin` 等等级权限，角色/账户上较低的权限将始终被使用）。

## 处理账户

通常，您不需要为所有新账户定义多个账户类型类。

Evennia 账户按定义为一个包含 `evennia.DefaultAccount` 的 Python 类。在 `mygame/typeclasses/accounts.py` 中有一个空类，您可以修改。Evennia 默认使用这个类（它直接继承自 `DefaultAccount`）。

以下是修改默认账户类的代码示例：

```python
# in mygame/typeclasses/accounts.py

from evennia import DefaultAccount

class Account(DefaultAccount): 
    # [...]
    def at_account_creation(self): 
        "此方法仅在账户首次创建时调用"
        self.db.real_name = None      # 稍后设置 
        self.db.real_address = None   #       "
        self.db.config_1 = True       # 默认配置 
        self.db.config_2 = False      #       "
        self.db.config_3 = 1          #       "

        # ... 其他游戏需要知道的信息 
```

重新加载服务器使用 `reload`。

然而，如果您使用 `examine *self`（星号使您检查账户对象而不是角色），您不会立即看到新的属性。这是因为 `at_account_creation` 仅在账户首次调用时被触发，而您的账户对象已经存在（任何新连接的账户将会看到这些属性）。要更新自己，您需要确保在所有已创建的账户上重新触发此钩子。以下是使用 `py` 的示例：

```python
[account.at_account_creation() for account in evennia.managers.accounts.all()]
```

您现在应该会看到属性更新到您的账户上。

> 如果您希望 Evennia 默认使用一个完全 *不同* 的账户类，您需要指定它。在设置文件中添加 `BASE_ACCOUNT_TYPECLASS`，并将其值指向您的自定义类的 Python 路径。默认情况下，它指向 `typeclasses.accounts.Account`，即我们上面使用的空模板。

### 账户的属性

除了分配给所有类型类对象的属性（参见 [Typeclasses](./Typeclasses.md)），账户还具有以下自定义属性：

- `user` - 唯一链接到表示登录用户的 `User` Django 对象。
- `obj` - 角色的别名。
- `name` - `user.username` 的别名。
- `sessions` - 一个 [ObjectSessionHandler](github:evennia.objects.objects#objectsessionhandler) 实例，管理此对象监听的所有连接会话（物理连接）（注意：在 Evennia 的旧版本中，这是一个列表）。所谓的 `session-id`（在许多地方使用）可在每个会话实例的属性 `sessid` 中找到。
- `is_superuser` （布尔值：真/假）- 如果该账户是超级用户。

特殊处理：
- `cmdset` - 这个属性保存账户的当前 [命令](./Commands.md)。默认情况下，这些命令来自由 `settings.CMDSET_ACCOUNT` 定义的命令集。
- `nicks` - 这存储和处理 [昵称](./Nicks.md)，与对象的昵称处理方式相同。对于账户，昵称主要用于存储频道的自定义别名。

选择的一些特殊方法（详见 `evennia.DefaultAccount`）：
- `get_puppet` - 获取与账户和给定会话 ID 连接的当前控制对象（如果有）。
- `puppet_object` - 连接会话到可控制的对象。
- `unpuppet_object` - 从可控制对象断开连接。
- `msg` - 向账户发送文本。
- `execute_cmd` - 像这个账户执行命令一样运行命令。
- `search` - 搜索账户。
