# 输入函数

Inputfunc 是 Evennia 中处理从客户端传来的 `commandtuple` 的最后一个固定步骤。Inputfunc 的任务是执行请求的操作，比如触发命令、执行数据库查询等。

给定一个 `commandtuple` 格式如下：

```
(commandname, (args), {kwargs})
```

Evennia 将尝试找到并调用一个格式如下的 Inputfunc：

```python
def commandname(session, *args, **kwargs):
    # ...
```

如果没有找到匹配项，它将调用名为 "default" 的 inputfunc，格式如下：

```python
def default(session, cmdname, *args, **kwargs):
    # cmdname 是不匹配的输入命令的名称
```

默认的 inputfuncs 位于 [evennia/server/inputfuncs.py](evennia.server.inputfuncs) 中。

## 添加自定义的 inputfuncs

1. 在 `mygame/server/conf/inputfuncs.py` 中添加一个符合上述格式的函数。你的函数必须位于该模块的全局、最外层作用域，并且不能以下划线 (`_`) 开头，以便被识别为 inputfunc。
2. `reload` 服务器。

要重载默认的 inputfunc，只需添加一个同名的函数。你还可以扩展设置列表 `INPUT_FUNC_MODULES`。

```python
INPUT_FUNC_MODULES += ["path.to.my.inputfunc.module"]
```

在这些模块中，所有全局级别的函数（名称不以 `_` 开头）都将被 Evennia 用作 inputfunc。列表从左到右导入，因此后导入的函数将替换先前的函数。

## 默认的 inputfuncs

Evennia 定义了一些默认的 inputfuncs 来处理常见情况。这些定义在 `evennia/server/inputfuncs.py` 中。

### text

- 输入：`("text", (textstring,), {})`
- 输出：取决于触发的命令

这是最常见的输入，也是每个传统 MUD 支持的唯一输入。参数通常是用户从命令行发送的内容。由于用户的所有文本输入都被视为 [Command](./Commands.md)，此 inputfunc 将执行诸如昵称替换等操作，然后将输入传递给中央 Commandhandler。

### echo

- 输入：`("echo", (args), {})`
- 输出：`("text", ("Echo returns: %s" % args), {})`

这是一个测试输入，只是将参数作为文本回显给会话。可以用于测试自定义客户端输入。

### default

如上所述，默认函数吸收所有未识别的输入命令。默认情况下，它只会记录一个错误。

### client_options

- 输入：`("client_options, (), {key:value, ...})`
- 输出：
  - 正常：None
  - 获取：`("client_options", (), {key:value, ...})`

这是一个用于设置协议选项的直接命令。可以通过 `@option` 命令设置，但这提供了一种客户端侧设置它们的方法。并非所有连接协议都使用所有标志，但以下是可能的关键字：

- get (bool): 如果为 true，忽略所有其他 kwargs 并立即返回当前设置作为输出命令 `("client_options", (), {key=value, ...})`。
- client (str): 客户端标识符，如 "mushclient"。
- version (str): 客户端版本
- ansi (bool): 支持 ansi 颜色
- xterm256 (bool): 支持 xterm256 颜色
- mxp (bool): 支持 MXP
- utf-8 (bool): 支持 UTF-8
- screenreader (bool): 屏幕阅读器模式开/关
- mccp (bool): MCCP 压缩开/关
- screenheight (int): 屏幕高度（行数）
- screenwidth (int): 屏幕宽度（字符数）
- inputdebug (bool): 调试输入函数
- nomarkup (bool): 去除所有文本标签
- raw (bool): 保留未解析的文本标签

> 注意，此 inputfunc 有两个 GMCP 别名 - `hello` 和 `supports_set`，这意味着它将通过一些客户端假定的 GMCP `Hello` 和 `Supports.Set` 指令访问。

### get_client_options

- 输入：`("get_client_options, (), {key:value, ...})`
- 输出：`("client_options, (), {key:value, ...})`

这是一个便利包装，通过向上面的 `client_options` 发送 "get" 来检索当前选项。

### get_inputfuncs

- 输入：`("get_inputfuncs", (), {})`
- 输出：`("get_inputfuncs", (), {funcname:docstring, ...})`

返回一个输出命令，格式为 `("get_inputfuncs", (), {funcname:docstring, ...})` - 所有可用 inputfunctions 的列表以及它们的文档字符串。

### login

> 注意：这目前是实验性的，测试不充分。

- 输入：`("login", (username, password), {})`
- 输出：取决于登录钩子

这在当前会话上执行登录操作的 inputfunc 版本。它旨在用于自定义客户端设置。

### get_value

- 输入：`("get_value", (name, ), {})`
- 输出：`("get_value", (value, ), {})`

从当前会话控制的角色或账户中检索一个值。接受一个参数，这只接受特定白名单名称，你需要重载函数以扩展。默认情况下，可以检索以下值：

- "name" 或 "key": 账户或操控角色的键。
- "location": 当前位置的名称，或 "None"。
- "servername": 连接的 Evennia 服务器的名称。

### repeat

- 输入：`("repeat", (), {"callback":funcname, "interval": secs, "stop": False})`
- 输出：取决于重复的函数。如果给定了不熟悉的回调名称，将返回 `("text", (repeatlist),{})` 和接受的名称列表。

这将告诉 Evennia 以给定的间隔重复调用一个命名函数。在后台，这将设置一个 [Ticker](./TickerHandler.md)。只有先前可接受的函数才能以这种方式重复调用，你需要重载此 inputfunc 以添加你想提供的函数。默认情况下，只允许两个示例函数 "test1" 和 "test2"，它们只会在给定的间隔回显一个文本。通过发送 `"stop": True` 停止重复（注意你必须包括回调名称和间隔，以便 Evennia 知道要停止什么）。

### unrepeat

- 输入：`("unrepeat", (), ("callback":funcname, "interval": secs)`
- 输出：None

这是一个便利包装，用于向 `repeat` inputfunc 发送 "stop"。

### monitor

- 输入：`("monitor", (), ("name":field_or_argname, stop=False)`
- 输出（更改时）：`("monitor", (), {"name":name, "value":value})`

这设置了对属性或数据库字段的对象监视。每当字段或属性以任何方式更改时，输出命令将被发送。这在后台使用 [MonitorHandler](./MonitorHandler.md)。传递 "stop" 键以停止监视。注意，停止时必须提供名称，以便系统知道应取消哪个监视器。

只有白名单中的字段/属性可以使用，你必须重载此函数以添加更多。默认情况下，可以监视以下字段/属性：

- "name": 当前角色名称
- "location": 当前位置
- "desc": 描述参数

### unmonitor

- 输入：`("unmonitor", (), {"name":name})`
- 输出：None

一个便利包装，将 "stop" 发送到 `monitor` 函数。
