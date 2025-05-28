# 将 Evennia 连接到 Twitter

[Twitter](https://en.wikipedia.org/wiki/twitter) 是一个在线社交网络服务，允许用户发送和阅读称为“推文”的短消息。以下是一个简短的教程，解释如何让用户从 Evennia 内部发送推文。

## 配置 Twitter

首先，你需要有一个 Twitter 账户。登录并在 [Twitter 开发者网站](https://apps.twitter.com/)上注册一个应用。确保你启用了“写”推文的权限！

要从 Evennia 发送推文，你需要“API Token”和“API Secret”字符串，以及“Access Token”和“Access Secret”字符串。

Twitter 改变了他们的要求，现在需要在 Twitter 账户上注册一个手机号码才能注册具有写权限的新应用。如果你无法做到这一点，请参阅[这个开发者帖子](https://dev.twitter.com/notifications/new-apps-registration)，其中描述了如何解决这个问题。

要使用 Twitter，你必须安装 [Twitter](https://pypi.python.org/pypi/twitter) Python 模块：

```
pip install python-twitter
```

## 设置 Twitter，逐步指南

### 基本的推文命令

Evennia 默认没有 `tweet` 命令，因此你需要编写自己的小[命令](../Components/Commands.md)来发送推文。如果你不确定命令如何工作以及如何添加它们，可以在继续之前查看[添加命令教程](../Howtos/Beginner-Tutorial/Part1/Beginner-Tutorial-Adding-Commands.md)。

你可以在一个单独的命令模块中创建命令（例如 `mygame/commands/tweet.py`），也可以与其他自定义命令一起创建，随你喜欢。代码如下：

```python
# 例如在 mygame/commands/tweet.py 中

import twitter
from evennia import Command

# 在这里插入你从 Twitter 开发者网站获取的唯一应用令牌
TWITTER_API = twitter.Api(consumer_key='api_key',
                          consumer_secret='api_secret',
                          access_token_key='access_token_key',
                          access_token_secret='access_token_secret')

class CmdTweet(Command):
    """
    发送推文

    用法: 
      tweet <message>

    这将发送一条推文到预配置的 Twitter 账户。
    推文的最大长度为 280 个字符。
    """

    key = "tweet"
    locks = "cmd:pperm(tweet) or pperm(Developers)"
    help_category = "Comms"

    def func(self):
        "执行推文操作"
 
        caller = self.caller
        tweet = self.args

        if not tweet:
            caller.msg("用法: tweet <message>")      
            return
 
        tlen = len(tweet)
        if tlen > 280:
            caller.msg(f"你的推文有 {tlen} 个字符长（最多 280 个字符）。")
            return

        # 发布推文        
        TWITTER_API.PostUpdate(tweet)

        caller.msg(f"你发送了推文:\n{tweet}")
```

请确保在适当的地方替换为你自己的 API/Access 密钥和秘密。

默认情况下，我们限制推文访问权限为具有 `Developers` 级别访问权限的玩家或拥有“tweet”权限的玩家。

要允许单个角色发送推文，请使用以下命令设置 `tweet` 权限：

```
perm/player playername = tweet
```

你可以根据需要更改[锁](../Components/Locks.md)。如果希望所有人都可以发送推文，可以将整体权限更改为 `Players`。

现在，将此命令添加到你的默认命令集中（例如在 `mygame/commands/default_cmdsets.py` 中）并重新加载服务器。从现在起，有权限的用户可以简单地使用 `tweet <message>` 来从游戏的 Twitter 账户发送推文。

### 下一步

这只是一个基本的推文设置，其他可以做的事情包括：

- 自动将角色名称添加到推文中
- 增加更多的错误检查
- 更改锁以开放更多人发送推文的权限
- 将推文回显到游戏内频道

你可以设置一个脚本来发送自动推文，例如发布更新的游戏统计信息。有关帮助，请参阅[推送游戏统计信息教程](../Howtos/Web-Tweeting-Game-Stats.md)。
