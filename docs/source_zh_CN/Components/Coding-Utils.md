# 编码工具

Evennia 提供了许多实用工具来帮助完成常见的编码任务。大多数工具可以直接从扁平 API 访问，其他工具可以在 `evennia/utils/` 文件夹中找到。

> 这里只是 `evennia/utils` 中工具的小部分选择。浏览 [该目录](evennia.utils) 尤其是 [evennia/utils/utils.py](evennia.utils.utils) 的内容，以发现更多有用的工具，值得一看。

## 搜索

常见的操作是搜索对象。最简单的方法是使用定义在所有对象上的 `search` 方法。该方法会在相同位置和自己对象中搜索对象：

```python
     obj = self.search(objname)
```

通常需要这样做的时间是在命令体内。`obj = self.caller.search(objname)` 将在调用者（通常是输入命令的角色）的 `.contents`（他们的“背包”）和 `.location`（他们的“房间”）中进行搜索。

给出关键字 `global_search=True` 以扩展搜索至整个数据库。别名也将通过此搜索匹配。您可以在默认命令集中找到多个此功能的示例。

如果您需要在代码模块中搜索对象，可以使用 `evennia.utils.search` 中的函数。您可以像短路一样访问这些函数 `evennia.search_*`。

```python
     from evennia import search_object
     obj = search_object(objname)
```

- [evennia.search_account](evennia.accounts.manager.AccountDBManager.search_account)
- [evennia.search_object](evennia.objects.manager.ObjectDBManager.search_object)
- [evennia.search_object_by_tag](evennia.utils.search.search_tag)
- [evennia.search_script](evennia.scripts.manager.ScriptDBManager.search_script)
- [evennia.search_channel](evennia.comms.managers.ChannelDBManager.search_channel)
- [evennia.search_message](evennia.comms.managers.MsgManager.search_message)
- [evennia.search_help](evennia.help.manager.HelpEntryManager.search_help)

请注意，这些方法将始终返回一个结果的 `list`，即使该列表只有一个或零个条目。

## 创建

除了游戏内的构建命令（如 `@create` 等），您还可以直接在代码中构建所有 Evennia 的游戏实体（例如在定义新创建命令时）。

```python
   import evennia

   myobj = evennia.create_objects("game.gamesrc.objects.myobj.MyObj", key="MyObj")
```

- [evennia.create_account](evennia.utils.create.create_account)
- [evennia.create_object](evennia.utils.create.create_object)
- [evennia.create_script](evennia.utils.create.create_script)
- [evennia.create_channel](evennia.utils.create.create_channel)
- [evennia.create_help_entry](evennia.utils.create.create_help_entry)
- [evennia.create_message](evennia.utils.create.create_message)

这些创建函数都具有大量参数，以进一步自定义创建的实体。有关更多信息，请参见 `evennia/utils/create.py`。

## 日志记录

通常，您可以使用 Python 的 `print` 语句查看终端/日志中的输出。`print` 语句应仅用于调试。对于生产输出，请使用 `logger`，它将创建适当的日志记录到终端或文件。

```python
     from evennia import logger
     #
     logger.log_err("这是一个错误！")
     logger.log_warn("这是一个警告！")
     logger.log_info("这是正常信息")
     logger.log_dep("此功能已弃用")
```

有一种特殊的日志消息类型 `log_trace()`，旨在从回溯内部调用 - 这对于将回溯消息传递回日志而不使服务器崩溃非常有用。

```python
     try:
       # [可能失败的代码...]
     except Exception:
       logger.log_trace("这段文字将显示在回溯本身之下。")
```

最后，`log_file` logger 是一个非常有用的 logger 用于输出任意日志消息。这是一个经过优化的异步日志机制，使用 [线程](https://en.wikipedia.org/wiki/Thread_%28computing%29) 来避免开销。您应该可以使用它进行非常重的自定义日志记录，而不必担心磁盘写入延迟。

```python
 logger.log_file(message, filename="mylog.log")
```

如果没有给出绝对路径，则日志文件将出现在 `mygame/server/logs/` 目录中。如果文件已经存在，则将其附加到该文件中。与普通 Evennia 日志相同格式的时间戳将自动添加到每个条目中。如果没有指定文件名，则输出将写入文件 `game/logs/game.log`。

有关查找难以捉摸的错误的帮助，请参见 [调试](../Coding/Debugging.md) 文档。

## 时间工具

### 游戏时间

Evennia 跟踪当前服务器时间。您可以通过 `evennia.gametime` 快捷方式访问此时间：

```python
from evennia import gametime

# 以下所有函数均以秒为单位返回时间。

# 服务器的总运行时间
runtime = gametime.runtime()
# 自上次硬重启以来的时间（不包括重载）
uptime = gametime.uptime()
# 服务器纪元（开始时间）
server_epoch = gametime.server_epoch()

# 进行中的纪元（可由 `settings.TIME_GAME_EPOCH` 设置）。
# 如果没有设置，则使用服务器纪元。
game_epoch = gametime.game_epoch()
# 自时间开始运行以来的游戏内时间
gametime = gametime.gametime()
# 当前游戏内时间戳（即当前游戏时间），加上游戏纪元
gametime = gametime.gametime(absolute=True)
# 重置游戏时间（回到游戏纪元）
gametime.reset_gametime()
```

设置 `TIME_FACTOR` 确定游戏内时间相对于现实世界的快慢。设置 `TIME_GAME_EPOCH` 设置开始的游戏纪元（以秒为单位）。来自 `gametime` 模块的函数都以秒为单位返回它们的时间。您可以将其转换为您希望在游戏中使用的任何时间单位。您可以使用 `@time` 命令查看服务器时间信息。

您还可以使用 [gametime.schedule](evennia.utils.gametime.schedule) 函数安排在特定游戏内时间发生的事件：

```python
import evennia

def church_clock():
    limbo = evennia.search_object(key="Limbo")
    limbo.msg_contents("教堂的钟声敲响了两点。")

gametime.schedule(church_clock, hour=2)
```

### utils.time_format()

此函数以秒为输入（例如来自上面的 `gametime` 模块），并将其转换为一个美观的文本输出，显示天数、小时等。这在您想要显示某个事物的年龄时非常有用。使用 *style* 关键字可以转换为四种不同样式的输出： 

- style 0 - `5d:45m:12s`（标准冒号输出）
- style 1 - `5d`（仅显示最长时间单位）
- style 2 - `5 days, 45 minutes`（完整格式，忽略秒）
- style 3 - `5 days, 45 minutes, 12 seconds`（完整格式，包含秒）

### utils.delay()

该函数允许进行延迟调用。

```python
from evennia import utils

def _callback(obj, text):
    obj.msg(text)

# 等待 10 秒后向 obj（假定已定义）发送“Echo！”
utils.delay(10, _callback, obj, "Echo!", persistent=False)

# 这里的代码将立即运行，而不会等待延迟触发！
```

有关更多信息，请参见 [异步过程](../Concepts/Async-Process.md#delay)。

## 查找类

### utils.inherits_from()

这个有用的函数接受两个参数 - 一个要检查的对象和一个父类。如果对象在任何距离上都继承自父类，则返回 `True`（与 Python 内置的 `isinstance()` 仅捕获直接依赖的功能相对）。该函数还接受任何组合的类、实例或指向类的 Python 路径作为输入。

请注意，Python 代码通常应该使用 [鸭子类型](https://en.wikipedia.org/wiki/Duck_typing)。但在 Evennia 的情况下，有时检查对象是否继承自给定 [Typeclass](./Typeclasses.md) 作为识别方式是有用的。例如，假设我们有一个类型类 *Animal*。这个类有一个子类 *Felines*，而 *Felines* 又有一个子类 *HouseCat*。也许还有其他一些动物类型，比如马和狗。使用 `inherits_from`，您可以一次检查所有动物：

```python
     from evennia import utils
     if utils.inherits_from(obj, "typeclasses.objects.animals.Animal"):
        obj.msg("保安拦住你说：‘不允许会说话的动物。’")
```

## 文本工具

在文本游戏中，自然会进行大量的文本来回操作。这里是 `evennia/utils/utils.py` 中的一个 *非完整* 选择的文本工具（快捷方式为 `evennia.utils`）。如果没有其他选择，在开始开发自己的解决方案之前查看这里也是不错的主意。

### utils.fill()

此函数将文本填充到给定宽度（调整单词以使每一行均匀宽）。它还会根据需要缩进。

```python
     outtxt = fill(intxt, width=78, indent=4)
```

### utils.crop()

此函数将剪裁一行非常长的文本，添加后缀以显示该行实际上是继续的。这在显示多个行可能搞乱的情况下特别有用。

```python
     intxt = "这是一个我们想要剪裁的长文本。"
     outtxt = crop(intxt, width=19, suffix="[...]")
     # outtxt 现在是 "这是一个我们想要剪裁的长文本[...]"
```

### utils.dedent()

此函数解决了在文本中看似微不足道的问题 - 删除缩进。它用于将整个段落向左移动，而不会干扰任何进一步的格式。一个常见的例子是使用 Python 三重引号字符串时 - 它们将在代码中保留任何缩进，并且为了使源代码易于阅读，通常不希望将字符串移至左边缘。

```python
    #python 代码在给定缩进时输入
          intxt = """
          这是一个示例文本，将以大量的空白结束
          在左侧。
                    它也有自己的缩进。"""
          outtxt = dedent(intxt)
          # outtxt 现在将保留所有内部缩进
          # 但被移到最左边。
```

通常，您在显示代码中进行缩进（例如帮助系统如何标准化帮助条目）。

### to_str() 和 to_bytes()

Evennia 提供了两个实用函数，用于将文本转换为正确的编码。`to_str()` 和 `to_bytes()`。除非您正在添加自定义协议并需要将字节数据发送到网络，否则 `to_str` 是您唯一需要的。

Evennia 的这些函数与 Python 内置的 `str()` 和 `bytes()` 运算符的不同之处在于，Evennia 的函数利用了 `ENCODINGS` 设置，并将非常努力地避免引发回溯，而是通过日志记录回显错误。有关更多信息，请参见 [这里](../Concepts/Text-Encodings.md)。
