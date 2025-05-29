# Evennia 游戏索引

[Evennia 游戏索引](http://games.evennia.com) 是一个使用 Evennia 构建或正在构建的游戏列表。任何人都可以将他们的游戏添加到索引中——即使你刚刚开始开发，还不接受外部玩家。这是一个让我们知道你的存在的机会，也是让我们对你的即将推出的游戏感到好奇或兴奋的机会！

我们唯一的要求是确保你的游戏名称不会与列表中已有的名称冲突——请友好对待他人！

## 使用向导连接

在你的游戏目录中运行

```bash
evennia connections
```

这将启动 Evennia _连接向导_。在菜单中选择将你的游戏添加到 Evennia 游戏索引中。按照提示操作，最后不要忘记保存你的新设置。如果你改变主意，可以随时使用 `quit` 退出。

> 向导将创建一个新的文件 `mygame/server/conf/connection_settings.py`，其中包含你选择的设置。这个文件会从你的主设置文件的末尾导入，因此会覆盖主设置文件中的内容。如果你愿意，可以编辑这个新文件，但请记住，如果你再次运行向导，你的更改可能会被覆盖。

## 手动设置

如果你不想使用向导（可能因为你已经从早期版本安装了客户端），你也可以在你的设置文件中配置索引条目（`mygame/server/conf/settings.py`）。添加以下内容：

```python
GAME_INDEX_ENABLED = True 

GAME_INDEX_LISTING = {
    # 必填项
    'game_status': 'pre-alpha',            # pre-alpha, alpha, beta, launched
    'listing_contact': "dummy@dummy.com",  # 不公开显示。
    'short_description': '简短描述',

    # 选填项
    'long_description':
        "更长的描述，可以使用 Markdown，比如 *加粗*，_斜体_"
        "和 [链接名](https://link.com)。用 \n 换行。"
    'telnet_hostname': 'dummy.com',            
    'telnet_port': '1234',                     
    'web_client_url': 'dummy.com/webclient',   
    'game_website': 'dummy.com',              
    # 'game_name': 'MyGame',  # 仅在与 settings.SERVERNAME 不同时设置
}
```

其中，`game_status`、`short_description` 和 `listing_contact` 是必填项。`listing_contact` 不会公开显示，仅用于在出现任何列表问题/错误时作为最后的联系方式（到目前为止，这种情况从未发生过）。

如果未设置 `game_name`，将使用 `settings.SERVERNAME`。对于你暂时不想指定的可选字段，请使用空字符串 (`''`)。

## 非公开游戏

如果你没有指定 `telnet_hostname + port` 或 `web_client_url`，游戏索引将把你的游戏列为 _尚未公开_。非公开游戏会被移动到索引的底部，因为人们无法尝试它们。但这是一种表明你存在的好方法，即使你还没有准备好迎接玩家。
