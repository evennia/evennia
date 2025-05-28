# EvMore

当向用户客户端发送非常长的文本时，可能会超出客户端窗口的高度。`evennia.utils.evmore.EvMore` 类为用户提供了在游戏中一次只查看一页文本的功能。通常通过其访问函数 `evmore.msg` 使用。

这个名字来源于著名的 Unix 分页工具 *more*，它执行的正是这个功能。

要使用分页器，只需通过它传递长文本：

```python
from evennia.utils import evmore

evmore.msg(receiver, long_text)
```

其中，receiver 是一个 [Object](./Objects.md) 或 [Account](./Accounts.md)。如果文本长度超过客户端的屏幕高度（由 NAWS 握手或 `settings.CLIENT_DEFAULT_HEIGHT` 确定），分页器将会出现，类似这样：

> [...]
aute irure dolor in reprehenderit in voluptate velit
esse cillum dolore eu fugiat nulla pariatur. Excepteur
sint occaecat cupidatat non proident, sunt in culpa qui
officia deserunt mollit anim id est laborum.

>(**more** [1/6] retur**n**|**b**ack|**t**op|**e**nd|**a**bort)

用户可以按回车键移动到下一页，或使用建议的命令跳转到前一页、文档顶部或底部，以及中止分页。

分页器接受多个关键字参数来控制消息输出。更多信息请参见 [evmore-API](github:evennia.utils.evmore)。
