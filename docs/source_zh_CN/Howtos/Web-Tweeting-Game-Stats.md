# 自动推送游戏统计数据到 Twitter

本教程将创建一个简单的脚本，该脚本会向您已配置的 Twitter 账户发送推文。如果您尚未完成，请参阅 [如何将 Evennia 连接到 Twitter](../Setup/Channels-to-Twitter.md)。

该脚本可以扩展，以涵盖您希望定期推送的各种统计数据，从玩家死亡到经济中有多少货币等。

```python
# evennia/typeclasses/tweet_stats.py

import twitter
from random import randint
from django.conf import settings
from evennia import ObjectDB
from evennia.prototypes import prototypes
from evennia import logger
from evennia import DefaultScript

class TweetStats(DefaultScript):
    """
    实现将统计信息推送到注册的 Twitter 账户
    """

    # 标准脚本钩子 

    def at_script_creation(self):
        "脚本首次创建时调用"

        self.key = "tweet_stats"
        self.desc = "推送有关游戏的有趣统计数据"
        self.interval = 86400  # 1天超时
        self.start_delay = False
        
    def at_repeat(self):
        """
        每自定义的 self.interval 秒调用一次 
        推送有关游戏的有趣统计数据。
        """
        
        api = twitter.Api(consumer_key='consumer_key',
          consumer_secret='consumer_secret',
          access_token_key='access_token_key',
          access_token_secret='access_token_secret')
        
        # 从 `stats` 命令获取游戏角色、房间、对象
        nobjs = ObjectDB.objects.count()
        base_char_typeclass = settings.BASE_CHARACTER_TYPECLASS
        nchars = (              
            ObjectDB.objects
           .filter(db_typeclass_path=base_char_typeclass)
           .count()
        )
        nrooms = (
            ObjectDB.objects
            .filter(db_location__isnull=True)
            .exclude(db_typeclass_path=base_char_typeclass)
            .count()
        )
        nexits = (
            ObjectDB.objects
            .filter(db_location__isnull=False,
                    db_destination__isnull=False)
            .count()
        )
        nother = nobjs - nchars - nrooms - nexits
        tweet = f"角色数: {nchars}, 房间数: {nrooms}, 其他/对象数: {nother}"

        # 发布推文 
        try:
            response = api.PostUpdate(tweet)
        except:
            logger.log_trace(f"推文错误: 尝试推送 {tweet} 时出错")
```

在 `at_script_creation` 方法中，我们配置脚本以立即触发（对于测试很有用），并设置延迟（1 天）以及您在使用 `@scripts` 时看到的脚本信息。

在 `at_repeat` 方法中（第一次调用立即，然后在指定的时间间隔后再次调用），我们配置 Twitter API（就像在 Twitter 的初始配置中一样）。然后我们显示玩家角色、房间和其他对象的数量。

有关如何将其作为全局脚本添加的详细信息，请参阅 [脚本文档](../Components/Scripts.md)，不过在测试时，您可能希望在游戏中快速启动/停止它。假设您将文件创建为 `mygame/typeclasses/tweet_stats.py`，可以使用以下命令启动它：

```
script Here = tweet_stats.TweetStats
```
