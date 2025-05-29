# 带外消息传递

OOB（Out-Of-Band，带外）意味着在 Evennia 和用户客户端之间发送数据，而无需用户提示或意识到数据正在传递。常见的用途包括更新客户端健康条、处理客户端按钮按下事件或在不同的窗口面板中显示某些标记的文本。

如果你还没有，你应该熟悉 [Messagepath](./Messagepath.md)，它描述了消息如何进入和离开 Evennia，以及在此过程中，所有消息如何被转换为一种称为 `commandtuple` 的通用格式：

```
(commandname, (args), {kwargs})
```

## 发送和接收 OOB 消息

发送消息很简单。你只需使用要发送到的对象的会话的正常 `msg` 方法。

```python
caller.msg(commandname=((args, ...), {key:value, ...}))
```

关键字成为 `commandtuple` 的命令名称部分，值则成为其 `args` 和 `kwargs` 部分。你还可以同时发送多个不同 `commandname` 的消息。

一个特殊情况是 `text` 调用。它如此常见，以至于成为 `msg` 方法的默认值。因此，这两者是等价的：

```python
caller.msg("Hello")
caller.msg(text="Hello")
```

你不必指定完整的 `commandtuple` 定义。因此，例如，如果你的特定命令只需要 kwargs，你可以跳过 `(args)` 部分。就像在 `text` 情况下，如果只有一个参数，你可以跳过编写元组……等等——输入非常灵活。如果根本没有参数，你需要给出空元组 `msg(cmdname=(,)`（给 `None` 将意味着一个单独的参数 `None`）。

### 可以发送哪些命令名称？

这取决于客户端和协议。如果你使用 Evennia [webclient](../Components/Webclient.md)，你可以修改它以支持你喜欢的任何命令名称。

许多第三方 MUD 客户端支持以下列出的各种 OOB 协议。如果客户端不支持特定的 OOB 指令/命令，Evennia 将只向他们发送 `text` 命令，并静默丢弃所有其他 OOB 指令。

> 请注意，给定消息可能会发送到具有不同功能的多个客户端。因此，除非你完全关闭 telnet 并仅依赖 webclient，否则你不应该依赖非 `text` 的 OOB 消息总是能到达所有目标。

### 可以接收哪些命令名称？

这由你定义的 [Inputfuncs](../Components/Inputfuncs.md) 决定。你可以根据需要扩展 Evennia 的默认设置，但要在 `settings.INPUT_FUNC_MODULES` 指向的模块中添加你自己的函数。

## 支持的 OOB 协议

Evennia 支持使用以下协议之一的客户端：

### Telnet

默认情况下，telnet（和 telnet+SSL）仅支持普通的 `text` 输出命令。Evennia 检测客户端是否支持标准 telnet 协议的两个 MUD 特定 OOB *扩展*之一 - GMCP 或 MSDP。Evennia 同时支持这两者，并将切换到客户端使用的协议。如果客户端同时支持两者，将使用 GMCP。

> 请注意，对于 Telnet，`text` 具有作为“带内”操作的特殊状态。因此，`text` 输出命令直接通过线路发送 `text` 参数，而不经过下面描述的 OOB 转换。

#### Telnet + GMCP

[GMCP](https://www.gammon.com.au/gmcp)，即*通用 MUD 通信协议*，以 `cmdname + JSONdata` 的形式发送数据。这里的 cmdname 预计为 "Package.Subpackage" 的形式。也可能有额外的子子包等。这些“包”和“子包”的名称并没有超出各个 MUD 或公司多年来选择使用的标准化。你可以决定自己的包名称，但以下是其他人使用的：

- [Aardwolf GMCP](https://www.aardwolf.com/wiki/index.php/Clients/GMCP)
- [Discworld GMCP](https://discworld.starturtle.net/lpc/playing/documentation.c?path=/concepts/gmcp)
- [Avatar GMCP](https://www.outland.org/infusions/wiclear/index.php?title=MUD%20Protocols&lang=en)
- [IRE games GMCP](https://nexus.ironrealms.com/GMCP)

Evennia 会将下划线翻译为 `.` 并大写以符合规范。因此，输出命令 `foo_bar` 将变为 GMCP 命令名称 `Foo.Bar`。GMCP 命令 "Foo.Bar" 将变为 `foo_bar`。要发送一个 GMCP 命令，该命令在 Evennia 中变为没有下划线的输入命令，请使用 `Core` 包。因此 `Core.Cmdname` 在 Evennia 中仅变为 `cmdname`，反之亦然。

在传输过程中，`commandtuple`

```
("cmdname", ("arg",), {})
```

将作为此 GMCP telnet 指令通过线路发送

```
IAC SB GMCP "cmdname" "arg" IAC SE
```

其中所有大写的词都是 telnet 字符常量，指定在 `evennia/server/portal/telnet_oob` 中。这些由协议解析/添加，我们不会在下面的列表中包括这些。

| `commandtuple` | GMCP-Command | 
| --- | ---| 
| `(cmd_name, (), {})`  |  `Cmd.Name` |
| `(cmd_name, (arg,), {})` |      `Cmd.Name arg` | 
| `(cmd_na_me, (args,...),{})`  |     `Cmd.Na.Me [arg, arg...]` | 
| `(cmd_name, (), {kwargs})` |    `Cmd.Name {kwargs}` | 
| `(cmdname, (arg,), {kwargs})` | `Core.Cmdname [[args],{kwargs}]` | 

由于 Evennia 已经提供了与最常见的 GMCP 实现不匹配的默认 Inputfuncs，因此我们为这些实现提供了一些硬编码的映射：

| GMCP command name | `commandtuple` command name |
| --- | --- | 
| `"Core.Hello"` | `"client_options"` | 
| `"Core.Supports.Get"` | `"client_options"` | 
| `"Core.Commands.Get"` | `"get_inputfuncs"` | 
| `"Char.Value.Get"` | `"get_value"` | 
| `"Char.Repeat.Update"` | `"repeat"` |
| `"Char.Monitor.Update"`| `"monitor"` | 

#### Telnet + MSDP

[MSDP](http://tintin.sourceforge.net/msdp/)，即*Mud 服务器数据协议*，是 GMCP 的竞争标准。MSDP 协议页面指定了一系列“推荐”的可用 MSDP 命令名称。Evennia *不* 支持这些——由于 MSDP 没有为其命令名称指定特殊格式（如 GMCP 那样），客户端可以并且应该直接调用内部 Evennia 输入函数的实际名称。

MSDP 使用 Telnet 字符常量通过线路传输各种结构化数据。MSDP 支持字符串、数组（列表）和表（字典）。这些用于定义所需的 cmdname、args 和 kwargs。发送 `("cmdname", ("arg",), {})` 的 MSDP 时，生成的 MSDP 指令将如下所示：

```
IAC SB MSDP VAR cmdname VAL arg IAC SE
```

各种可用的 MSDP 常量如 `VAR`（变量）、`VAL`（值）、`ARRAYOPEN`/`ARRAYCLOSE` 和 `TABLEOPEN`/`TABLECLOSE` 在 `evennia/server/portal/telnet_oob` 中指定。

| `commandtuple` | MSDP instruction | 
| --- | --- | 
| `(cmdname, (), {})` | `VAR cmdname VAL` | 
| `(cmdname, (arg,), {})` | `VAR cmdname VAL arg` | 
| `(cmdname, (arg,...),{})`  | `VAR cmdname VAL ARRAYOPEN VAL arg VAL arg ... ARRAYCLOSE` | 
| `(cmdname, (), {kwargs})`  | `VAR cmdname VAL TABLEOPEN VAR key VAL val ... TABLECLOSE` | 
| `(cmdname, (args,...), {kwargs})` | `VAR cmdname VAL ARRAYOPEN VAL arg VAL arg ... ARRAYCLOSE VAR cmdname VAL TABLEOPEN VAR key VAL val ... TABLECLOSE` |

注意 `VAR ... VAL` 始终标识 `cmdnames`，因此如果有多个数组/字典标记有相同的 cmdname，它们将附加到该输入函数的 args、kwargs 中。反之，一个不同的 `VAR ... VAL`（在表之外）将作为第二个不同的命令输入。

### SSH

SSH 仅支持 `text` 输入/输出命令。

### Web 客户端

我们的 Web 客户端使用纯 [JSON](https://en.wikipedia.org/wiki/JSON) 结构进行所有通信，包括 `text`。这直接映射到 Evennia 内部的输出/输入命令，包括最终的空 args/kwargs。

| `commandtuple` | Evennia Webclient JSON | 
| --- | --- | 
| `(cmdname, (), {})` |  `["cmdname", [], {}]` | 
| `(cmdname, (arg,), {})` | `["cmdname", [arg], {}]` |
| `(cmdname, (arg,...),{})`  |  `["cmdname", [arg, ...], {})` |
| `(cmdname, (), {kwargs})`  | `["cmdname", [], {kwargs})` | 
| `(cmdname, (arg,...), {kwargs})` | `["cmdname", [arg, ...], {kwargs})` | 

由于 JSON 是 Javascript 的原生格式，这使得 Web 客户端处理起来非常容易。
