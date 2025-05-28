# 将 Evennia 频道连接到 Discord

[Discord](https://discord.com) 是一个流行的聊天服务，尤其适合游戏社区。如果你的游戏有一个 Discord 服务器，可以将其连接到你的游戏内频道，实现游戏内外的沟通。

## 配置 Discord

首先，你需要设置一个 Discord 机器人来连接到你的游戏。访问 [bot applications](https://discord.com/developers/applications) 页面并创建一个新应用程序。需要将“MESSAGE CONTENT”选项切换为开启，并将你的机器人令牌添加到设置中。

```python
# mygame/server/conf/secret_settings.py
DISCORD_BOT_TOKEN = '<your Discord bot token>'
```

如果还没有安装 `pyopenssl` 模块，则需要安装它。在你的 Evennia Python 环境中执行以下命令：

```
pip install pyopenssl
```

最后，在设置中启用 Discord：

```python
DISCORD_ENABLED = True
```

启动或重新加载 Evennia 并以特权用户身份登录。现在应该有一个新命令可用：`discord2chan`。输入 `help discord2chan` 以获取其选项的说明。

添加新频道链接的命令如下：

```
discord2chan <evennia_channel> = <discord_channel_id>
```

`evennia_channel` 参数必须是现有 Evennia 频道的名称，而 `discord_channel_id` 是 Discord 频道的完整数字 ID。

> 你的机器人需要被添加到正确的 Discord 服务器，并具有访问频道的权限才能发送或接收消息。此命令不会验证你的机器人是否具有 Discord 权限！

## Discord 设置步骤

本节将逐步介绍为你的 Evennia 游戏设置 Discord 连接的整个过程。如果你已经完成了其中的某些步骤，可以直接跳到下一个步骤。

### 创建 Discord 机器人应用程序

> 你需要一个活跃的 Discord 账户和对 Discord 服务器的管理员访问权限才能连接 Evennia。

确保你已在 Discord 网站上登录，然后访问 https://discord.com/developers/applications。点击右上角的“New Application”按钮，然后输入新应用程序的名称——使用你的 Evennia 游戏名称是一个不错的选择。

接下来，你将进入新应用程序的设置页面。点击侧边栏菜单中的“Bot”，然后点击“Build-a-Bot”以创建你的机器人账户。

**保存显示的令牌！** 这将是 Discord 唯一一次允许你查看该令牌——如果丢失，你将不得不重置它。此令牌用于确认机器人的身份，因此非常重要。

接下来，将此令牌添加到你的 _secret_ 设置中。

```python
# file: mygame/server/conf/secret_settings.py

DISCORD_BOT_TOKEN = '<token>'
```

保存后，向下滚动到 Bot 页面，找到“Message Content Intent”选项并将其切换为开启，否则你的机器人将无法读取任何人的消息。

最后，你可以为新机器人账户添加任何其他设置：显示图像、显示昵称、简介等。你可以随时返回更改这些设置，因此现在不必过于担心。

### 将机器人添加到服务器

在你的新应用程序中，点击侧边菜单中的“OAuth2”，然后点击“URL Generator”。在此页面上，你将生成一个邀请 URL，然后访问该 URL 将其添加到你的服务器。

在顶部框中，找到 `bot` 复选框并选中它：这将使第二个权限框出现。在该框中，你需要至少勾选以下选项：

- 读取消息/查看频道（在“General Permissions”中）
- 发送消息（在“Text Permissions”中）

最后，向下滚动到页面底部并复制生成的 URL。它应类似于以下内容：

```
https://discord.com/api/oauth2/authorize?client_id=55555555555555555&permissions=3072&scope=bot
```

访问该链接，选择你的 Evennia 连接的服务器并确认。

将机器人添加到你的服务器后，可以通过常规的 Discord 服务器管理进一步微调权限。

### 在 Evennia 中激活 Discord

在你的 Evennia 游戏中，你需要执行两个额外的步骤才能连接到 Discord。

首先，如果尚未安装 `pyopenssl`，请在你的虚拟环境中安装它。

```
pip install pyopenssl
```

其次，在设置文件中启用 Discord 集成。

```python
# file: server/conf/settings.py
DISCORD_ENABLED = True
```

启动或重新加载游戏以应用更改的设置，然后以至少具有 `Developer` 权限的账户登录，并使用 `discord2chan` 命令在 Evennia 上初始化机器人账户。你应该会收到一条消息，表示机器人已创建，并且没有与 Discord 的活动连接。

### 将 Evennia 频道连接到 Discord 频道

你将需要 Evennia 频道的名称和 Discord 频道的频道 ID。频道 ID 是你访问频道时 URL 的最后一部分。

例如，如果 URL 是 `https://discord.com/channels/55555555555555555/12345678901234567890`，那么你的频道 ID 是 `12345678901234567890`

使用以下命令链接两个频道：

```
discord2chan <evennia channel> = <discord channel id>
```

现在两个频道应该可以相互传递消息。通过在 Evennia 频道和 Discord 频道上分别发送一条消息来确认这一点——它们应该都出现在另一端。

> 如果你没有看到任何消息从 Discord 发送或接收，请确保你的机器人有权限读取和发送消息，并且你的应用程序已设置“Message Content Intents”标志。

### 进一步自定义

`discord2chan` 的帮助文件中有更多关于如何使用命令自定义传递消息的信息。

然而，对于更复杂的需求，你可以创建自己的 `DiscordBot` 子类并将其添加到你的设置中。

```python
# file: mygame/server/conf/settings.py
# 示例
DISCORD_BOT_CLASS = 'accounts.bots.DiscordBot'
```

> 如果你已经设置了 Discord 中继并正在更改此设置，请确保要么删除 Evennia 中的旧机器人账户，要么更改其类型类，否则它将不会生效。

核心的 DiscordBot 账户类已经设置了几个有用的钩子，用于在 Discord 和 Evennia 频道之间处理和传递频道消息，以及（默认未使用的）`direct_msg` 钩子，用于处理在 Discord 上发送给机器人的私信。

默认情况下，仅处理消息和服务器更新，但 Discord 自定义协议会将所有其他未处理的调度数据传递给 Evennia 机器人账户，以便你可以自己添加额外的处理。然而，**此集成并不是一个完整的库**，并没有记录 Discord 事件的全部可能范围。
