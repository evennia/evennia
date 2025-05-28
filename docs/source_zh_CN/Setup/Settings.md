# 更改游戏设置

Evennia 可以在不更改任何设置的情况下开箱即用。但是，有几种重要的方法可以自定义服务器并通过自己的插件扩展它。

所有特定于游戏的设置都位于 `mygame/server/conf/` 目录中。

## 设置文件

文档中引用的“设置”文件是 `mygame/server/conf/settings.py` 文件。

你的新 `settings.py` 开箱即用时相对简单。Evennia 的核心设置文件是 [Settings-Default 文件](./Settings-Default.md)，它更为详尽。它还经过详细的文档记录并保持最新，因此你应该直接参考此文件以获取可用设置。

由于 `mygame/server/conf/settings.py` 是一个普通的 Python 模块，因此它在顶部简单地导入了 `evennia/settings_default.py`。

这意味着，如果你想更改的任何设置依赖于其他默认设置，则可能需要复制并粘贴两者以更改它们并获得所需的效果（对于大多数常见的更改设置，这不是你需要担心的事情）。

你永远不应该编辑 `evennia/settings_default.py`。相反，你应该将想要更改的变量复制并粘贴到 `settings.py` 中并在那里编辑它们。这将覆盖先前导入的默认值。

```{warning} 不要复制全部内容！
可能会有将 `settings_default.py` 中的*所有内容*复制到你自己的设置文件中的诱惑，以便将所有内容集中在一个地方。不要这样做。通过仅复制你需要的内容，你可以更轻松地跟踪你更改了什么。
```

在代码中，设置通过以下方式访问：

```python
from django.conf import settings
# 或者（更短）：
from evennia import settings
# 示例：
servername = settings.SERVER_NAME
```

每个设置都作为导入的 `settings` 对象上的属性出现。你还可以使用 `evennia.settings_full` 探索所有可能的选项（这还包括默认 Evennia 未触及的高级 Django 默认值）。

> 当像这样将 `settings` 导入代码时，它将是*只读*的。你*不能*从代码中编辑你的设置！更改 Evennia 设置的唯一方法是直接编辑 `mygame/server/conf/settings.py`。你还需要重新启动服务器（可能还需要重新启动门户）才能使更改的设置生效。

## `server/conf` 目录中的其他文件

除了主要的 `settings.py` 文件外，还有：

- `at_initial_setup.py` - 这允许你添加一个自定义启动方法，在 Evennia 首次启动时（仅在创建用户 #1 和 Limbo 时）调用。可以用来启动你自己的全局脚本或设置游戏需要从一开始就运行的其他系统/世界相关的东西。
- `at_server_startstop.py` - 此模块包含 Evennia 每次服务器启动和停止时分别调用的函数 - 这包括由于重载和重置而停止以及完全关闭。这是一个放置处理程序和其他必须在游戏中运行但没有数据库持久性的自定义启动代码的有用位置。
- `connection_screens.py` - 此模块中的所有全局字符串变量都被 Evennia 解释为在账户首次连接时显示的欢迎屏幕。如果模块中存在多个字符串变量，将随机选择一个。
- `inlinefuncs.py` - 这是你可以定义自定义 [FuncParser 函数](../Components/FuncParser.md) 的地方。
- `inputfuncs.py` - 这是你定义自定义 [输入函数](../Components/Inputfuncs.md) 以处理来自客户端的数据的地方。
- `lockfuncs.py` - 这是用于保存你自己的“安全”*锁定函数*以提供给 Evennia 的 [锁](../Components/Locks.md) 的许多可能模块之一。
- `mssp.py` - 这包含有关你游戏的元信息。它被 MUD 搜索引擎使用（通常需要注册）以显示你正在运行的游戏类型以及在线账户数量和在线状态等统计信息。
- `oobfuncs.py` - 你可以在这里定义自定义 [OOB 函数](../Concepts/OOB.md)。
- `portal_services_plugin.py` - 这允许向门户添加你自己的自定义服务/协议。它必须定义一个特定的函数，该函数将在启动时由 Evennia 调用。可以有任意数量的服务插件模块，如果定义了所有模块，它们都将被导入和使用。更多信息可以在 [这里](https://code.google.com/p/evennia/wiki/SessionProtocols#Adding_custom_Protocols) 找到。
- `server_services_plugin.py` - 这相当于前一个，但用于向服务器添加新服务。更多信息可以在 [这里](https://code.google.com/p/evennia/wiki/SessionProtocols#Adding_custom_Protocols) 找到。

其他一些 Evennia 系统可以通过插件模块进行自定义，但在 `conf/` 中没有明确的模板：

- `cmdparser.py` - 自定义模块可用于完全替换 Evennia 的默认命令解析器。所有这些只是将传入的字符串拆分为“命令名称”和“其余部分”。它还处理无匹配和多匹配的错误消息等其他事情，使得这比听起来更复杂。默认解析器非常通用，因此通常最好在命令解析级别而不是在这里进行进一步修改。
- `at_search.py` - 这允许替换 Evennia 处理搜索结果的方式。它允许更改错误的回显方式以及多重匹配的解决和报告方式（例如默认解析器如何理解“2-ball”应该匹配房间中两个“球”对象中的第二个）。
