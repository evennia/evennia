# 频道

在多人游戏中，玩家通常需要比移动到同一房间并使用 `say` 或 `emote` 更为丰富的游戏内通信方式。

_频道_ 使 Evennia 能够充当一个华丽的聊天程序。当玩家连接到某个频道时，发送到该频道的消息会自动分发给所有其他订阅者。

频道可以用于 [帐户](./Accounts.md) 之间和 [对象](./Objects.md)（通常是角色）之间的聊天。聊天可以是 OOC（角色外）或 IC（角色内）的。这里有一些例子：

- 联系工作人员的支持频道（OOC）
- 讨论任何事情并促进社区的公共聊天（OOC）
- 私密工作人员讨论的管理员频道（OOC）
- 用于规划和组织的私人公会频道（根据游戏可为 IC/OOC）
- 网络朋克风格的复古聊天室（IC）
- 游戏内电台频道（IC）
- 群体意念传达（IC）
- 对讲机（IC）

```{versionchanged} 1.0

频道系统更改为使用中央 “channel” 命令和昵称，而非自动生成的频道命令和命令集。ChannelHandler 被移除。
```

## 使用频道

### 观看和加入频道

在默认命令集中，频道通过强大的 [channel 命令](evennia.commands.default.comms.CmdChannel) `channel`（或 `chan`）进行处理。默认情况下，该命令会假定所有与频道相关的实体均为 `Accounts`。

查看频道

```
channel       - 显示您的订阅
channel/all   - 显示您可以订阅的所有频道
channel/who   - 显示who在这个频道上
```

要加入/取消订阅频道，您可以使用

```
channel/sub channelname
channel/unsub channelname
```

如果您暂时不想听这个频道（而不想实际取消订阅），可以将其静音：

```
channel/mute channelname
channel/unmute channelname
```

### 在频道上交谈

要在频道上发言，请执行

```
channel public Hello world!
```

如果频道名称中有空格，您需要使用 '`=`'：

```
channel rest room = Hello world!
```

现在，这比我们希望输入的更麻烦，因此当您加入频道时，系统会自动设置一个个人别名，这样您只需执行：

```
public Hello world
```

```{warning}
此快捷方式在频道名称中有空格时将无法使用。因此，频道使用较长名称时应确保提供一个单词的别名。
```

任何用户都可以自定义自己的频道别名：

```
channel/alias public = foo;bar
```

现在您可以这样操作：

```
foo Hello world!
bar Hello again!
```

如果他们不想使用，可以删除默认别名：

```
channel/unalias public
public Hello  (现在会给出命令未找到的错误)
```

但您也可以使用您的别名与 `channel` 命令结合：

```
channel foo Hello world!
```

> 别名创建的过程是映射您的别名 + 参数到调用 `channel` 命令的 [nick](./Nicks.md)。因此，当您输入 `foo hello` 时，服务器看到的实际命令是 `channel foo = hello`。系统还很聪明，知道在您搜索频道时应考虑到您的频道别名，以便将您的输入转换为现有频道名称。

您可以通过查看频道的回滚，检查是否错过了频道对话：

```
channel/history public
```

这将检索最后 20 行文本（也包括您离线时的内容）。您可以通过指定起始的行数来进一步向后推：

```
channel/history public = 30
```

这将再次检索 20 行，但从第 30 行开始（因此您将获得倒数第 30-50 行的内容）。

### 频道管理

Evennia 可以在启动时创建某些频道。频道也可以在游戏中动态创建。

#### 从设置中获取的默认频道

您可以在 Evennia 设置中指定要自动创建的“默认”频道。如果新帐户具有正确的权限，则将自动订阅这些“默认”频道。下面是一个每个频道一个字典的列表（示例为默认的公共频道）：

```python
# 在 mygame/server/conf/settings.py 文件中
DEFAULT_CHANNELS = [ 
    {
         "key": "Public",
         "aliases": ("pub",),
         "desc": "公共讨论",
         "locks": "control:perm(Admin);listen:all();send:all()",
     },
]
```

每个字典作为 `**channeldict` 提供给 [create_channel](evennia.utils.create.create_channel) 函数，因此支持所有相同关键词。

Evennia 还有两个与系统相关的频道：

- `CHANNEL_MUDINFO` 是描述“泥浆信息”频道的字典。假定该频道存在，它是 Evennia 回显重要服务器信息的地方。服务器管理员和工作人员可以订阅该频道以保持更新。
- `CHANNEL_CONNECTINFO` 默认不定义。它将接收连接/断开消息，并可能对普通玩家可见。如果没有提供，连接信息将安静地记录。

#### 在游戏中管理频道

要动态创建/销毁新频道，可以执行

```
channel/create channelname;alias;alias = description
channel/destroy channelname
```

别名是可选的，但可以作为每个人都想使用的显而易见的快捷方式。描述用于频道列表。您创建的频道会自动加入，并且您将控制它。您也可以稍后使用 `channel/desc` 更改您拥有的频道的描述。

如果您控制一个频道，还可以将人踢出该频道：

```
channel/boot mychannel = annoyinguser123 : stop spamming!
```

最后一部分是一个可选的理由，在踢出用户之前发送给他们。您可以使用逗号分隔的频道列表来一次性踢出该用户在所有这些频道中的订阅。该用户将被从频道取消订阅，其所有别名将被删除。但他们仍然可以随时重新加入。

```
channel/ban mychannel = annoyinguser123
channel/ban      - 查看禁止名单
channel/unban mychannel = annoyinguser123
```

禁止会将用户添加到频道黑名单。这意味着如果您将他们踢出，他们将无法 _重新加入_。您需要运行 `channel/boot` 实际地将他们踢出。

有关详细信息，请查看 [Channel 命令](evennia.commands.default.comms.CmdChannel) 的 API 文档（以及游戏内帮助）。

管理员级用户还可以修改频道的 [locks](./Locks.md):

```
channel/lock buildchannel = listen:all();send:perm(Builders)
```

频道默认使用三种锁类型：

- `listen` - 谁可以倾听频道。没有该访问权的用户将无法加入频道，且该频道对于他们不会出现在列表中。
- `send` - 谁可以发送消息到频道。
- `control` - 该锁会在您创建频道时自动分配给您。控制频道后，您可以编辑其内容、踢出用户并执行其他管理任务。

#### 限制频道管理权限

默认情况下，所有人都可以使用频道命令 ([evennia.commands.default.comms.CmdChannel](evennia.commands.default.comms.CmdChannel)) 来创建频道，并将控制权限分配给他们创建的频道（以便踢人/禁止等）。如果您作为开发人员不希望普通玩家执行此操作（可能您只希望工作人员能够创建新频道），您可以重写 `channel` 命令并更改其 `locks` 属性。

默认的 `help` 命令具有以下 `locks` 属性：

```python
    locks = "cmd:not perm(channel_banned); admin:all(); manage:all(); changelocks: perm(Admin)"
```

这是一个常规的 [lockstring](./Locks.md)。

- `cmd: not pperm(channel_banned)` - `cmd` 锁定类型是用于所有命令的标准锁。未通过访问的对象甚至不会知道该命令存在。`pperm()` 锁函数检查一个账户的 [权限](Building Permissions) 'channel_banned' - `not` 表示如果他们 _持有_ 该“权限”，则无法使用 `channel` 命令。您通常不需要更改此锁。
- `admin:all()` - 这是在 `channel` 命令本身中检查的锁。它控制对 `/boot`、`/ban` 和 `/unban` 开关的访问（默认允许所有人使用）。
- `manage:all()` - 这控制对 `/create`、`/destroy`、`/desc` 开关的访问。
- `changelocks: perm(Admin)` - 这控制对 `/lock` 和 `/unlock` 开关的访问。默认情况下，这只是 [管理员](Building Permissions) 可以更改的内容。

> 注意 - 虽然 `admin:all()` 和 `manage:all()` 将允许每个人使用这些开关，但用户仍然只能管理或销毁他们实际控制的频道！

如果您只想让（例如）构建者及以上级别的用户能够创建和管理频道，则可以重写 `help` 命令并更改锁字符串为：

```python
# 例如在 mygame/commands/commands.py 中

from evennia import default_cmds

class MyCustomChannelCmd(default_cmds.CmdChannel):
    locks = "cmd: not pperm(channel_banned);admin:perm(Builder);manage:perm(Builder);changelocks:perm(Admin)"
```

将此自定义命令添加到您的默认命令集合，普通用户现在在尝试使用这些开关时将会收到拒绝访问的错误。

## 在代码中使用频道

对于大多数常见的更改，默认频道、接收者钩子以及可能重写 `channel` 命令将为您提供极大的便利。但您也可以直接修改频道本身。

### 允许角色使用频道

默认 `channel` 命令 ([evennia.commands.default.comms.CmdChannel](evennia.commands.default.comms.CmdChannel)) 位于 `Account` [命令集](./Command-Sets.md) 中。它被设置为始终在 `Accounts` 上操作，即使您将其添加到 `CharacterCmdSet` 中。

只需一行即可使该命令接受非帐户调用者。但为了方便起见，我们提供了一个适用于角色/对象的版本。只需导入 [evennia.commands.default.comms.CmdObjectChannel](evennia.commands.default.comms.CmdObjectChannel) 并继承即可。

### 自定义频道输出和行为

在分发消息时，频道将对其自身及每个接收者调用一系列钩子。因此，您可以通过简单地修改正常对象/账户类型类上的钩子来实现很大的自定义。

在内部，消息使用 `channel.msg(message, senders=sender, bypass_mute=False, **kwargs)` 发送，其中 `bypass_mute=True` 表示忽略静音（适合警报或删除频道等情况），`**kwargs` 是您可能想要传递给钩子的额外信息。`senders`（在默认实现中始终只有一个，但原则上可以包含多个）和 `bypass_mute` 是下面的 `kwargs` 参数：

1. `channel.at_pre_msg(message, **kwargs)`
2. 对每个接收者：
   - `message = recipient.at_pre_channel_msg(message, channel, **kwargs)` - 允许每个接收者修改消息（例如根据用户的偏好对其着色）。如果此方法返回 `False/None`，则该接收者将被跳过。
   - `recipient.channel_msg(message, channel, **kwargs)` - 实际上发送给接收者。
   - `recipient.at_post_channel_msg(message, channel, **kwargs)` - 所有后接收效果。
3. `channel.at_post_channel_msg(message, **kwargs)`

请注意，`Accounts` 和 `Objects` 都具有各自独立的钩子集。因此确保您修改实际用于订阅者的钩子集（或两者）。默认频道都使用 `Account` 订阅者。

### 频道类

频道是 [类型类](./Typeclasses.md) 实体。这意味着它们在数据库中是持久的，可以具有 [属性](./Attributes.md) 和 [标签](./Tags.md)，并且可以轻松扩展。

要更改 Evennia 用于默认命令的频道类型类，请更改 `settings.BASE_CHANNEL_TYPECLASS`。基础命令类是 [`evennia.comms.comms.DefaultChannel`](evennia.comms.comms.DefaultChannel)。在 `mygame/typeclasses/channels.py` 中有一个空的子类，与其他类型类基础相同。

在代码中，您可以使用 `evennia.create_channel` 或 `Channel.create` 创建新频道：

```python
from evennia import create_channel, search_object
from typeclasses.channels import Channel

channel = create_channel("my channel", aliases=["mychan"], locks=..., typeclass=...)
# 或者
channel = Channel.create("my channel", aliases=["mychan"], locks=...)

# 连接到它
me = search_object(key="Foo")[0]
channel.connect(me)

# 发送消息（这将触发之前描述的 channel_msg 钩子）
channel.msg("Hello world!", senders=me)

# 查看订阅情况（订阅处理程序在后台处理所有订阅）
channel.subscriptions.has(me)    # 检查我们是否订阅
channel.subscriptions.all()      # 获取所有订阅
channel.subscriptions.online()   # 仅获取当前在线的订阅
channel.subscriptions.clear()    # 取消所有订阅

# 离开频道
channel.disconnect(me)

# 永久删除频道（将取消所有人的订阅）
channel.delete()
```

频道的 `.connect` 方法将接受 `Account` 和 `Object` 订阅者，并透明处理。

频道还有许多其他钩子，既有与所有类型类共享的钩子，也有与静音/禁止等相关的特定钩子。有关详细信息，请参见频道类。

### 频道日志

```{versionchanged} 0.7

频道的消息改为使用 Msg 到 TmpMsg 和可选日志文件。
```
```{versionchanged} 1.0

频道停止支持 Msg 和 TmpMsg，仅使用日志文件。
```

频道消息不存储在数据库中。相反，频道始终记录到常规文本日志文件 `mygame/server/logs/channel_<channelname>.log` 中。这也是 `channels/history channelname` 获取数据的来源。频道的日志在增长过大时会自动轮换，从而自动限制用户使用 `/history` 可以查看的最大历史记录数量。

日志文件名在频道类中设置为 `log_file` 属性。该属性是一个字符串，接受格式化标记 `{channelname}`，会被频道调用时（小写）名称替换。默认情况下，日志写入频道的 `at_post_channel_msg` 方法中。

### 频道上的属性

频道具有所有类型类实体的标准属性（`key`、`aliases`、`attributes`、`tags`、`locks` 等）。这不是一个详尽的列表；有关详细信息，请参见 [Channel API 文档](evennia.comms.comms.DefaultChannel)。

- `send_to_online_only` - 该类布尔值默认为 `True`，这是一个明智的优化，因为离线用户反正看不到消息。
- `log_file` - 该字符串用于确定频道日志文件的名称。默认为 `"channel_{channelname}.log"`。日志文件将出现在 `settings.LOG_DIR` 中（通常是 `mygame/server/logs/`）。通常不应更改此项。
- `channel_prefix_string` - 此属性是一个字符串，便于更改频道前缀。它采取 `channelname` 格式标记。默认为 `"[{channelname}] "`，呈现时产生类似 `[public] ...` 的输出。
- `subscriptions` - 这是 [SubscriptionHandler](evennia.comms.models.SubscriptionHandler)，具有 `has`、`add`、`remove`、`all`、`clear` 和 `online` 等方法（以仅获取当前在线的频道成员）。
- `wholist`、`mutelist`、`banlist` 是返回订阅者列表的属性，以及当前被静音或禁止的用户。
- `channel_msg_nick_pattern` - 这是执行在线昵称替换的正则表达式模式（检测 `channelalias <msg` 意味着您想向频道发送消息）。该模式接受 `{alias}` 格式标记。除非您确实想更改频道的工作方式，否则不要碰这个。
- `channel_msg_nick_replacement` - 这是与频道消息的 [nick 替换形式](./Nicks.md) 相关的属性。它接受 `{channelname}` 格式标记。该属性与 `channel` 命令密切相关，默认值为 `channel {channelname} = $1`。

值得注意的 `Channel` 钩子：

- `at_pre_channel_msg(message, **kwargs)` - 在发送消息之前调用，以修改消息。默认未使用。
- `msg(message, senders=..., bypass_mute=False, **kwargs)` - 将消息发送到频道。 `**kwargs` 会传递给其他调用钩子（接收者上的钩子也是如此）。
- `at_post_channel_msg(message, **kwargs)` - 默认情况下用于将消息存储到日志文件。
- `channel_prefix(message)` - 这是为了允许频道进行前缀操作。该过程在对象/账户构建消息时调用，因此若希望更改为其他形式，也可以直接删除该调用。
- 每条频道消息。默认情况下，它返回 `channel_prefix_string`。
- `has_connection(subscriber)` - 检查实体是否订阅此频道的快捷方式。
- `mute/unmute(subscriber)` - 为该用户静音该频道。
- `ban/unban(subscriber)` - 将用户添加到/从禁止名单中移除。
- `connect/disconnect(subscriber)` - 添加/删除订阅者。
- `add_user_channel_alias(user, alias, **kwargs)` - 为该频道设置用户昵称。它能将 `alias <msg>` 映射到 `channel channelname = <msg>`。
- `remove_user_channel_alias(user, alias, **kwargs)` - 移除别名。请注意，这是一个类方法，将乐于从与该用户相关联的任何频道中删除找到的频道别名，而不仅仅是从调用该方法的频道中。
- `pre_join_channel(subscriber)` - 如果返回 `False`，则拒绝连接。
- `post_join_channel(subscriber)` - 默认执行用户的频道昵称/别名设置。
- `pre_leave_channel(subscriber)` - 如果返回 `False`，用户将无法离开。
- `post_leave_channel(subscriber)` - 这将清除与用户相关的任何频道别名/昵称。
- `delete` - 标准的类型类删除机制会自动取消所有订阅者的订阅（因此会清除他们所有的别名）。
