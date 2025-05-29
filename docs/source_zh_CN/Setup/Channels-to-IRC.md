# 将 Evennia 频道连接到 IRC

[IRC (Internet Relay Chat)](https://en.wikipedia.org/wiki/Internet_Relay_Chat) 是一个长期使用的聊天协议，许多开源项目使用它进行实时通信。通过将 Evennia 的 [Channels](../Components/Channels.md) 连接到 IRC 频道，你可以与不在 MUD 上的人交流。即使你的 Evennia MUD 仅在本地计算机上运行（游戏不需要对公众开放），你也可以使用 IRC！你只需要一个互联网连接。要使用 IRC，你还需要 [twisted.words](https://twistedmatrix.com/trac/wiki/TwistedWords)。在许多 Linux 发行版中可以通过 *python-twisted-words* 包获得，或者直接从链接下载。

## 配置 IRC

要配置 IRC，需要在设置文件中激活它：

```python
IRC_ENABLED = True
```

启动 Evennia 并以特权用户身份登录。现在应该有一个新命令可用：`@irc2chan`。该命令的使用方式如下：

```
@irc2chan[/switches] <evennia_channel> = <ircnetwork> <port> <#irchannel> <botname>
```

如果你已经了解 IRC 的工作原理，这应该很容易使用。阅读帮助条目以了解更多功能。

## IRC 设置步骤

你可以将 IRC 连接到任何 Evennia 频道（例如，可以连接到默认的 *public* 频道），但为了测试，我们将设置一个新频道 `irc`。

```
@ccreate irc = This is connected to an irc channel!
```

你将自动加入新频道。

接下来，我们将创建与外部 IRC 网络和频道的连接。IRC 网络有很多，[这里有一个列表](https://www.irchelp.org/networks/popular.html) 列出了其中一些最大的网络。除非你想连接到特定频道，否则选择哪个并不重要（还要确保网络允许“机器人”连接）。

为了测试，我们选择 *Freenode* 网络，`irc.freenode.net`。我们将连接到一个测试频道，称为 *#myevennia-test*（IRC 频道总是以 `#` 开头）。最好选择一个之前不存在的频道名称——如果它不存在，它将为你创建。

> 不要连接到 `#evennia` 进行测试和调试，那是 Evennia 的官方聊天频道！一旦一切正常，你可以将游戏连接到 `#evennia`，这可能是获得帮助和想法的好方法。但如果这样做，请仅对游戏管理员和开发人员开放游戏内频道。

所需的 *端口* 取决于网络。对于 Freenode，这是 `6667`。

Evennia 服务器将作为普通用户连接到这个 IRC 频道。这个“用户”（或“机器人”）需要一个名称，你也必须提供。我们称之为 "mud-bot"。

为了测试机器人是否正确连接，你还需要使用单独的第三方 IRC 客户端登录此频道。有数百种此类客户端可用。如果你使用 Firefox，*Chatzilla* 插件既好又简单。Freenode 还提供自己的基于网络的聊天页面。一旦连接到网络，加入频道的命令通常是 `/join #channelname`（不要忘记 #）。

接下来，将 Evennia 与 IRC 频道连接。

```
@irc2chan irc = irc.freenode.net 6667 #myevennia-test mud-bot
```

Evennia 现在将创建一个新的 IRC 机器人 `mud-bot` 并将其连接到 IRC 网络和频道 #myevennia。如果你连接到 IRC 频道，很快就会看到用户 *mud-bot* 连接。

在 Evennia 频道 *irc* 中写点东西。

```
irc Hello, World!
[irc] Anna: Hello, World!
```

如果你正在使用单独的 IRC 客户端查看 IRC 频道，应该会看到你的文本出现在那里，由机器人说出：

```
mud-bot> [irc] Anna: Hello, World!
```

在你的 IRC 客户端窗口中写下 `Hello!`，它将出现在你的普通频道中，并标记你使用的 IRC 频道名称（这里是 #evennia）。

```
[irc] Anna@#myevennia-test: Hello!
```

现在，你的 Evennia 玩家可以与外部 IRC 频道的用户聊天了！
