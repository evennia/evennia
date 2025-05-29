# 禁止用户

无论是由于滥用、明显违反规则，还是其他原因，你最终可能会发现不得不将一个特别麻烦的玩家踢出。默认命令集提供了管理工具来处理这种情况，主要包括 `ban`、`unban` 和 `boot`。

假设我们有一个麻烦的玩家 "YouSuck"——这是一个拒绝基本礼貌的用户，一个明显是由无聊的网络恶棍创建的滥用和垃圾邮件账户，只是为了制造麻烦。你已经尝试过友好对待。现在你只想让这个捣乱者消失。

## 创建封禁

### 名称封禁

最简单的办法是阻止 YouSuck 账户再次连接。

```plaintext
ban YouSuck
```

这将锁定名称 YouSuck（以及 'yousuck' 和其他大小写组合），下次他们尝试使用此名称登录时，服务器将不允许他们连接！

你还可以给出一个理由，以便以后记住为什么这样做是正确的（被封禁的账户永远不会看到这个理由）。

```plaintext
ban YouSuck:This is just a troll.
```

如果你确定这只是一个垃圾邮件账户，你甚至可以考虑直接删除该玩家账户：

```plaintext
accounts/delete YouSuck
```

通常，封禁名称是阻止账户使用的更简单和更安全的方法——如果你改变主意，你可以随时解除封禁，而删除是永久性的。

### IP 封禁

仅仅因为你封禁了 YouSuck 的名称，并不意味着该账户背后的捣乱者会放弃。他们可以创建一个新账户 YouSuckMore 并继续捣乱。使他们难以继续捣乱的一种方法是告诉服务器不允许从他们的特定 IP 地址连接。

首先，当违规账户在线时，检查他们使用的 IP 地址。你可以使用 `who` 命令查看，如下所示：

```plaintext
Account Name     On for     Idle     Room     Cmds     Host          
YouSuckMore      01:12      2m       22       212      237.333.0.223 
```

"Host" 部分是账户连接的 IP 地址。使用这个地址来定义封禁，而不是名称：

```plaintext
ban 237.333.0.223
```

这将阻止 YouSuckMore 从他们的计算机连接。但请注意，IP 地址可能会很容易更改——无论是由于玩家的互联网服务提供商的运作方式，还是用户简单地更换计算机。你可以通过在地址的三位数字组中使用星号 `*` 作为通配符来进行更广泛的封禁。因此，如果你发现 YouSuckMore 主要从 `237.333.0.223`、`237.333.0.225` 和 `237.333.0.256`（仅在其子网内变化）连接，可能需要这样设置一个封禁，以包括该子网中的任何号码：

```plaintext
ban 237.333.0.*
```

当然，你应该将 IP 封禁与名称封禁结合使用，以确保无论他们从哪里连接，账户 YouSuckMore 都被真正锁定。

但要小心设置过于宽泛的 IP 封禁（更多星号）。如果运气不好，你可能会阻止那些恰好从与违规者相同子网连接的无辜玩家。

### 解除封禁

使用 `unban`（或 `ban`）命令不带任何参数，你将看到所有当前活动的封禁列表：

```plaintext
Active bans
id   name/ip       date                      reason 
1    yousuck       Fri Jan 3 23:00:22 2020   This is just a Troll.
2    237.333.0.*   Fri Jan 3 23:01:03 2020   YouSuck's IP.
```

使用此列表中的 `id` 来找出要解除的封禁。

```plaintext
unban 2

Cleared ban 2: 237.333.0.*
```

## 踢出

YouSuck 还没有注意到所有这些封禁——直到他们下线并尝试重新登录。让我们帮助这个捣乱者离开。

```plaintext
boot YouSuck
```

好走。你也可以给出踢出的理由（在被踢出之前会回显给玩家）。

```plaintext
boot YouSuck:Go troll somewhere else.
```

## 滥用处理工具总结

以下是处理烦人玩家的其他有用命令。

- **who** -- （作为管理员）查找账户的 IP。请注意，根据你的设置，一个账户可以从多个 IP 连接。
- **examine/account thomas** -- 获取有关账户的所有详细信息。你也可以使用 `*thomas` 来获取账户。如果没有给出，你将获得 *Object* thomas（如果它存在于同一位置），这在这种情况下不是你想要的。
- **boot thomas**  -- 踢出给定账户名称的所有会话。
- **boot 23** -- 通过其唯一 id 踢出一个特定的客户端会话/IP。
- **ban** -- 列出所有封禁（带有 id）
- **ban thomas** -- 封禁具有给定账户名称的用户
- **ban/ip `134.233.2.111`** -- 通过 IP 封禁
- **ban/ip `134.233.2.*`** -- 扩大 IP 封禁
- **ban/ip `134.233.*.*`** -- 更广泛的 IP 封禁
- **unban 34** -- 移除 id 为 #34 的封禁

- **cboot mychannel = thomas** -- 从你控制的频道中踢出订阅者
- **clock mychannel = control:perm(Admin);listen:all();send:all()** -- 使用[锁定定义](../Components/Locks.md)对你的频道访问进行精细控制。

锁定特定命令（如 `page`）的方法如下：
1. 检查命令的来源。[默认 `page` 命令类](https://github.com/evennia/evennia/blob/main/evennia/commands/default/comms.py#L686) 的锁定字符串为 **"cmd:not pperm(page_banned)"**。这意味着除非玩家具有“权限”"page_banned"，否则他们可以使用此命令。你可以分配任何锁定字符串，以便在命令中进行更精细的自定义。你可能会查找[属性](../Components/Attributes.md)或[标签](../Components/Tags.md)的值、当前位置等。
2. **perm/account thomas = page_banned** -- 给账户赋予导致（在这种情况下）锁定失败的“权限”。

- **perm/del/account thomas = page_banned** -- 删除给定的权限
- **tel thomas = jail** -- 将玩家传送到指定位置或 #dbref
- **type thomas = FlowerPot** -- 将烦人的玩家变成花盆（假设你有一个 `FlowerPot` 类型类准备好）
- **userpassword thomas = fooBarFoo** -- 更改用户密码
- **accounts/delete thomas** -- 删除玩家账户（不推荐，使用 **ban** 代替）

- **server** -- 显示服务器统计信息，例如 CPU 负载、内存使用情况以及缓存了多少对象
- **time** -- 提供服务器正常运行时间、运行时间等
- **reload** -- 重新加载服务器而不与任何人断开连接
- **reset** -- 重启服务器，踢出所有连接
- **shutdown** -- 停止服务器而不再自动启动
- **py** -- 执行原始 Python 代码，允许即时直接检查数据库和账户对象。适用于高级用户。
