# 将 Evennia 频道连接到 Grapevine

[Grapevine](https://grapevine.haus) 是一个新的 `MU*` 游戏聊天网络。通过将游戏内频道连接到 Grapevine 网络，你的游戏玩家可以与其他游戏（包括非 Evennia 游戏）的玩家聊天。

## 配置 Grapevine

要使用 Grapevine，首先需要安装 `pyopenssl` 模块。在你的 Evennia Python 环境中执行以下命令：

```
pip install pyopenssl
```

要配置 Grapevine，需要在你的设置文件中激活它：

```python
GRAPEVINE_ENABLED = True
```

接下来，在 https://grapevine.haus 注册一个账户。登录后，进入你的设置/个人资料，然后选择 `Games` 子菜单。在这里，通过填写信息注册你的新游戏。注册结束时，你会获得一个 `Client ID` 和一个 `Client Secret`。这些信息不应共享。

打开或创建文件 `mygame/server/conf/secret_settings.py` 并添加以下内容：

```python
GRAPEVINE_CLIENT_ID = "<client ID>"
GRAPEVINE_CLIENT_SECRET = "<client_secret>"
```

你还可以自定义允许连接的 Grapevine 频道。这需要添加到 `GRAPEVINE_CHANNELS` 设置中。可以通过访问 Grapevine 在线聊天查看可用频道：https://grapevine.haus/chat。

启动或重新加载 Evennia 并以特权用户身份登录。现在应该有一个新命令可用：`@grapevine2chan`。该命令的使用方式如下：

```
@grapevine2chan[/switches] <evennia_channel> = <grapevine_channel>
```

其中，`evennia_channel` 必须是现有 Evennia 频道的名称，`grapevine_channel` 是 `GRAPEVINE_CHANNELS` 中支持的频道之一。

> 在撰写本文时，Grapevine 网络只有两个频道：`testing` 和 `gossip`。Evennia 默认允许连接到这两个频道。使用 `testing` 来测试你的连接。

## Grapevine 设置步骤

你可以将 Grapevine 连接到任何 Evennia 频道（例如，可以连接到默认的 *public* 频道），但为了测试，我们将设置一个新频道 `gw`。

```
@ccreate gw = This is connected to a gw channel!
```

你将自动加入新频道。

接下来，我们将创建与 Grapevine 网络的连接。

```
@grapevine2chan gw = gossip
```

Evennia 现在将创建一个新连接并连接到 Grapevine。可以连接到 https://grapevine.haus/chat 进行检查。

在 Evennia 频道 *gw* 中写点东西，并检查消息是否出现在 Grapevine 聊天中。在聊天中回复，Grapevine 机器人应该会将其回显到游戏内的频道。

现在，你的 Evennia 玩家可以与外部 Grapevine 频道的用户聊天了！
