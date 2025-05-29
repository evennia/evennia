# Msg

[Msg](evennia.comms.models.Msg) 对象表示一个保存在数据库中的通信片段。可以将其视为一封离散的电子邮件——它包含消息、一些元数据，并且总会有一个发送者和一个或多个接收者。

一旦创建，Msg 通常不会更改。它会持久地保存在数据库中。这允许对通信进行全面的日志记录。以下是 `Msg` 对象的一些良好用途：

- 页面/消息（`page` 命令是 Evennia 开箱即用的方式）
- 布告栏中的消息
- 存储在“邮箱”中的游戏范围内的电子邮件。

```{important}
  `Msg` 没有任何游戏内的表示。因此，如果你想用它们来表示游戏内的邮件/信件，物理信件将永远不会在房间中可见（可能被偷窃、监视等），除非你让你的间谍系统直接访问 Msgs（或费心根据 Msg 生成一个实际的游戏内信件对象）。
```

```{versionchanged} 1.0
  Channels 不再支持 Msg。现在默认仅用于 `page` 命令。
```

## 使用 Msg

Msg 旨在仅在代码中使用，以构建其他游戏系统。它不是一个 [Typeclassed](./Typeclasses.md) 实体，这意味着它不能（轻松地）被重写。它不支持属性（但支持 [Tags](./Tags.md)）。由于每条消息都会创建一个新的 Msg，因此它尽量保持精简和小巧。你可以使用 `evennia.create_message` 创建新消息：

```python
from evennia import create_message
message = create_message(senders, message, receivers,
                         locks=..., tags=..., header=...)
```

你可以通过多种方式搜索 `Msg` 对象：

```python
from evennia import search_message, Msg

# 参数是可选的。只应传递单个发送者/接收者
messages = search_message(sender=..., receiver=..., freetext=..., dbref=...)

# 获取给定发送者/接收者的所有消息
messages = Msg.objects.get_msg_by_sender(sender)
messages = Msg.objects.get_msg_by_receiver(recipient)
```

### Msg 的属性

- `senders` - 必须至少有一个发送者。这是一个包含 [Account](./Accounts.md)、[Object](./Objects.md)、[Script](./Scripts.md) 或 `str` 的集合（通常消息仅针对一种类型）。使用 `str` 作为发送者表示它是一个“外部”发送者，可以用于指向不是类型化实体的发送者。这不是默认使用的，其含义取决于系统（例如，它可以是唯一 ID 或 Python 路径）。虽然大多数系统期望单个发送者，但可以有任意数量的发送者。
- `receivers` - 这些是可以看到 Msg 的对象。这同样可以是 [Account](./Accounts.md)、[Object](./Objects.md) 或 [Script](./Scripts.md) 或 `str`（一个“外部”接收者）的任意组合。原则上可以有零个接收者，但大多数 Msg 的用法期望有一个或多个。
- `header` - 这是一个可选的文本字段，可以包含有关消息的元信息。对于类似电子邮件的系统，它将是主题行。可以独立搜索此字段，使其成为快速查找消息的强大工具。
- `message` - 实际发送的文本。
- `date_sent` - 自动设置为 Msg 创建（因此推测为发送）的时间。
- `locks` - Evennia [lock handler](./Locks.md)。使用 `locks.add()` 等，并像其他所有可锁定实体一样使用 `msg.access()` 检查锁。这可以用于限制对 Msg 内容的访问。默认的锁类型是 `'read'`。
- `hide_from` - 这是一个可选的 [Accounts](./Accounts.md) 或 [Objects](./Objects.md) 列表，这些对象将看不到此 Msg。此关系主要用于优化，因为它允许快速过滤不针对给定目标的消息。

## TempMsg

[evennia.comms.models.TempMsg](evennia.comms.models.TempMsg) 是一个实现了与常规 `Msg` 相同 API 的对象，但没有数据库组件（因此无法搜索）。它旨在插入期望 `Msg` 的系统中，但你只想处理消息而不保存它。
