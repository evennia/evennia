# 将 Evennia 频道连接到 RSS

[RSS](https://en.wikipedia.org/wiki/RSS) 是一种用于轻松跟踪网站更新的格式。其原理很简单——每当网站更新时，一个小的文本文件也会更新。RSS 阅读器可以定期在线检查此文件的更新，并让用户知道有什么新内容。

Evennia 允许将任意数量的 RSS 源连接到任意数量的游戏内频道。源的更新将被方便地回显到频道中。这有很多潜在的用途：例如，MUD 可能使用一个独立的网站来托管其论坛。通过 RSS，玩家可以在有新帖子时收到通知。另一个例子是让所有人知道你更新了开发博客。管理员可能还希望通过我们自己的 RSS 源 [这里](https://code.google.com/feeds/p/evennia/updates/basic) 跟踪最新的 Evennia 更新。

## 配置 RSS

要使用 RSS，首先需要安装 [feedparser](https://code.google.com/p/feedparser/) Python 模块。

```
pip install feedparser
```

接下来，在配置文件中激活 RSS 支持，设置 `RSS_ENABLED=True`。

以特权用户身份启动/重新加载 Evennia。现在应该有一个新命令可用：`@rss2chan`：

```
@rss2chan <evennia_channel> = <rss_url>
```

## RSS 设置步骤

你可以将 RSS 连接到任何 Evennia 频道，但为了测试，我们将设置一个新频道 "rss"。

```
@ccreate rss = RSS feeds are echoed to this channel!
```

让我们将 Evennia 的代码更新源连接到此频道。Evennia 更新的 RSS URL 是 `https://github.com/evennia/evennia/commits/main.atom`，所以我们添加它：

```
@rss2chan rss = https://github.com/evennia/evennia/commits/main.atom
```

就这样，新的 Evennia 更新现在将作为一行标题和链接显示在频道中。单独使用 `@rss2chan` 命令可以显示所有连接。要从频道中删除一个源，再次指定连接（使用命令查看列表中的连接）并添加 `/delete` 开关：

```
@rss2chan/delete rss = https://github.com/evennia/evennia/commits/main.atom
```

你可以通过这种方式将任意数量的 RSS 源连接到一个频道。你也可以将它们连接到与 [Channels-to-IRC](./Channels-to-IRC.md) 相同的频道，以便将源回显到外部聊天频道。
