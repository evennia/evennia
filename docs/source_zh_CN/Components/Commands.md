# 命令

命令与 [命令集合](./Command-Sets.md) 密切相关，您需要阅读该页面以熟悉命令系统的工作原理。这两页已分开以便于阅读。

用户与游戏进行交互的基本方式是通过 *命令*。这些命令可以是与游戏世界直接相关的命令，如 *look*（查看）、*get*（获取）、*drop*（丢弃）等，或者是管理命令，如 *examine*（检查）或 *dig*（挖掘）。

Evennia 附带的 [默认命令](./Default-Commands.md) 是“MUX-like”的，因为它们使用 `@` 符号作为管理命令，支持开关、使用 `=` 符号的语法等，但没有任何东西阻止您为游戏实现完全不同的命令方案。您可以在 `evennia/commands/default` 中找到默认命令。您不应直接编辑这些内容 - 因为它们会随着 Evennia 团队添加新功能而更新。相反，您应以此为灵感，并从中继承自己的设计。

运行命令有两个组成部分 - *命令类* 和 [命令集合](./Command-Sets.md)（命令集合被分为单独的 wiki 页面以便于阅读）。

1. *命令* 是一个包含命令功能代码的 Python 类 - 例如，*get* 命令将包含拾取对象的代码。
2. *命令集合*（通常称为 CmdSet 或 cmdset）就像一个容器，包含一个或多个命令。给定的命令可以进入多个不同的命令集合。只有将命令集合放在角色对象上，您才能使其中的所有命令可供该角色使用。如果您希望用户以各种方式使用对象，还可以将命令集合存储在普通对象上。考虑一个具有命令 *climb*（爬）和 *chop down*（砍倒）的 “Tree” 对象，或者具有单一命令 *check time*（查看时间）的 “Clock” 对象。

本页详细介绍了如何使用命令。如要充分使用这些命令，您必须阅读详细说明的 [命令集合](./Command-Sets.md) 页面。 还有一个逐步的 [添加命令教程](../Howtos/Beginner-Tutorial/Part1/Beginner-Tutorial-Adding-Commands.md)，可以快速帮助您入门，而无需额外的解释。

## 定义命令

所有命令都作为正常的 Python 类实现，继承自基本类 `Command` (`evennia.Command`)。您会发现这个基本类非常“简陋”。Evennia 的默认命令实际上从名为 `MuxCommand` 的 `Command` 子类继承 - 这是一个了解所有 MUX-like 语法的类，如 `/switches`、按 `=` 分割等。下面我们将避免使用与 mux 相关的特定内容，而直接使用基本 `Command` 类。

```python
# 基本命令定义
from evennia import Command

class MyCmd(Command):
   """
   这是命令的帮助文本
   """
   key = "mycommand"

   def parse(self):
       # 在这里解析命令行
       
   def func(self):
       # 在这里执行命令
```

以下是一个没有自定义解析的简约命令：

```python
from evennia import Command

class CmdEcho(Command):
    key = "echo"

    def func(self):
        # 将调用者的输入回显
        self.caller.msg(f"Echo: {self.args}")
```

您通过为继承的类分配几个类全局属性并重载一个或两个钩子函数来定义新命令。命令的运行机制的完整细节将在本页末尾介绍；现在您只需知道命令处理程序会创建该类的一个实例，并在您使用此命令时使用该实例 - 它还会动态分配一些有用的属性，您可以假定始终可用。

### 谁在调用命令？

在 Evennia 中，有三种类型的对象可以调用命令，了解这一点很重要，因为这将为命令体分配适当的 `caller`、`session`、`sessid` 和 `account` 属性。在大多数情况下，调用类型是 `Session`。

* 一个 [会话](./Sessions.md)。当用户在客户端中输入命令时，这种情况是最常见的。
    * `caller` - 如果存在被操纵的 [对象](./Objects.md)，则设置为该对象。如果找不到木偶，则 `caller` 设置等于 `account`。只有当帐户也未找到（如在登录之前）时，它才会设置为会话对象本身。
    * `session` - 对应的 [会话](./Sessions.md) 对象的引用。
    * `sessid` - `sessid.id`，会话的唯一整数标识符。
    * `account` - 连接到此会话的 [帐户](./Accounts.md) 对象。如果未登录，则为 None。
* 一个 [帐户](./Accounts.md)。这只会发生在使用了 `account.execute_cmd()` 的情况下。在此情况下无法获得会话信息。
    * `caller` - 如果可以确定木偶，则设置为被操纵的对象（在没有会话信息的情况下，这只能在 `MULTISESSION_MODE=0` 或 `1` 时进行确定）。如果找不到木偶，则等于帐户。
    * `session` - `None`
    * `sessid` - `None`
    * `account` - 设置为帐户对象。
* 一个 [对象](./Objects.md)。这只会发生在使用了 `object.execute_cmd()` 的情况下（例如由 NPC）。
    * `caller` - 设置为相应的调用对象。
    * `session` - `None`
    * `sessid` - `None`
    * `account` - `None`

> `*)`：有一种方法可以在直接在帐户和对象上运行的测试中使会话可用，即像这样将其传递给 `execute_cmd`：`account.execute_cmd("...", session=<Session>)`。这样做 *会*使得在命令中可用 `.session` 和 `.sessid` 属性。

### 在运行时分配给命令实例的属性

假设帐户 *Bob* 的角色 *BigGuy* 输入命令 *look at sword*。在系统成功识别出这是 “look” 命令并确定 *BigGuy* 确实有权访问名为 `look` 的命令后，它会从存储中拉出 `look` 命令类，并加载现有的命令实例（如果有缓存）或创建一个。在经过一些检查后，它将为命令实例分配以下属性：

- `caller` - 在此示例中为角色 *BigGuy*。这是正在执行命令的对象的引用。该值取决于调用命令的对象类型；请参见前一节。
- `session` - Bob 用于连接游戏并控制 *BigGuy* 的 [会话](./Sessions.md)（请参见前一节）。
- `sessid` - `self.session` 的唯一 id，便于快速查找。
- `account` - Bob 的 [帐户](./Accounts.md)（参见前一节）。
- `cmdstring` - 与命令匹配的键。我们的示例中将是 *look*。
- `args` - 除命令名外的其余字符串。因此，如果输入的字符串是 *look at sword*，则 `args` 将是 " *at sword*”。请注意保留的空格 - Evennia 也会正确解析 *lookat sword*。这对诸如 `/switches` 的使用很有帮助，它们不应使用空格。在用于默认命令的 `MuxCommand` 类中，这个空格会被去掉。另请参见 `arg_regex` 属性，如果您想强制要求空格，可以使得 *lookat sword* 给出命令未找到的错误。
- `obj` - 定义此命令的游戏 [对象](./Objects.md)。这不一定是调用者，但由于 `look` 是常见的（默认）命令，因此可能直接定义在 *BigGuy* 上 - 所以 `obj` 将指向 *BigGuy*。否则，`obj` 可能是帐户或任何定义有命令的交互对象，就像 “Clock” 对象上的 “check time” 命令的示例。
- `cmdset` - 这是一个指向合并的 CmdSet 的引用（详见下文），该命令从中匹配。此变量很少使用，主要用于 [自动帮助系统](./Help-System.md#command-auto-help-system)（*高级说明：合并的 cmdset 不必与 `BigGuy.cmdset` 相同。合并集合可能是来自房间内其他对象的 cmdsets 的组合，例如*）。
- `raw_string` - 来自用户的原始输入，而不去掉任何周围的空格字符。唯一去掉的是结束换行符。

#### 其他有用的实用方法：

- `.get_help(caller, cmdset)` - 获取此命令的帮助条目。默认情况下不使用参数，但可用于实现替代帮助显示系统。
- `.client_width()` - 快捷方式以获取客户端的屏幕宽度。请注意，并非所有客户端都会如实报告此值 - 在这种情况下，将返回 `settings.DEFAULT_SCREEN_WIDTH`。
- `.styled_table(*args, **kwargs)` - 基于调用此命令的会话返回样式化的 [EvTable](module-evennia.utils.evtable)。args/kwargs 与 EvTable 使用的参数相同，但样式默认设置已设置。
- `.styled_header`、`_footer`、`separator` - 这些将为显示用户生成样式装饰。它们对于创建带有可调颜色的列表和表单非常有用。

### 定义您自己的命令类

除了 Evennia 始终在运行时为命令分配的属性（如上所列），您的工作是定义以下类属性：

- `key`（字符串） - 命令的标识符，如 `look`。这应该（理想情况下）是唯一的。键可以由多个单词组成，如 “press button” 或 “pull left lever”。请注意 *key* 和下面的 `aliases` 都决定了命令的身份。如果其中任何一个匹配，则视为两个命令。这对于下面描述的合并 cmdsets 很重要。
- `aliases`（可选列表） - 命令的替代名称列表（`["glance", "see", "l"]`）。相同命名规则适用于 `key`。
- `locks`（字符串） - 一个 [锁定义](./Locks.md)，通常形式为 `cmd:<lockfuncs>`。锁是一个相当庞大的主题，所以在您了解更多有关锁的信息之前，建议仅给命令提供锁字符串 `"cmd:all()"`，以使其可供每个人使用（如果您不提供锁字符串，则会为您分配该字符串）。
- `help_category`（可选字符串） - 设置此项有助于将自动帮助结构化为类别。如果未设置，则将设置为 *General*。
- `save_for_next`（可选布尔值） - 默认值为 `False`。如果为 `True`，则系统将存储此命令对象的副本（以及您对其所做的任何更改），并可通过检索 `self.caller.ndb.last_cmd` 在下一个命令中访问。下一个运行命令将清除或替换存储。
- `arg_regex`（可选原始字符串） - 用于强制解析器限制自身并告诉它命令名何时结束以及参数何时开始（例如，要求作为空格或 `/switch`）。这是通过正则表达式完成的。 [请参见 arg_regex 部分](./Commands.md#arg_regex) 的详细信息。
- `auto_help`（可选布尔值） - 默认值为 `True`。这允许逐个命令关闭 [自动帮助系统](./Help-System.md#command-auto-help-system)。如果您要手动编写帮助条目或隐藏命令的存在以避免生成 `help` 列表，这可能会很有用。
- `is_exit`（布尔值） - 这将命令标记为用于游戏内出口。默认情况下，所有出口对象均设置此标志，除非您创建自己的出口系统，则无需手动设置。它用于优化，允许命令处理程序在其 cmdset 设置了 `no_exits` 标志时轻松无视此命令。
- `is_channel`（布尔值） - 这将命令标记为用于游戏内频道。默认情况下，所有频道对象均设置此标志，除非您创建自己的频道系统，则无需手动设置。它用于优化，允许命令处理程序在其 cmdset 设置了 `no_channels` 标志时轻松无视此命令。
- `msg_all_sessions`（布尔值）：此属性影响 `Command.msg` 方法的行为。如果未设置（默认），则从命令中调用 `self.msg(text)` 将仅向实际触发此命令的会话发送文本。但是如果设置，则 `self.msg(text)` 将发送至与此命令所在对象相关的所有会话。哪些会话接收文本取决于对象和服务器的 `MULTISESSION_MODE`。

您还应该实现至少两个方法，`parse()` 和 `func()`（也可以实现 `perm()`，但除非您想根本改变访问检查的工作方式，否则不需要）。

- `at_pre_cmd()` 在命令的最开始被调用。如果此函数返回任何有效的真值，命令执行将在这一点被中止。
- `parse()` 打算解析参数（`self.args`）。您可以以任何方式做到这一点，然后将结果存储在命令对象（即 `self`）上的变量中。例如，默认的 mux-like 系统使用此方法检测“命令开关”并将其作为列表存储在 `self.switches` 中。由于解析通常在命令方案中相似，因此您应该尽可能使 `parse()` 通用，然后继承它，而不是反复重新实现它。在这种方式中，默认的 `MuxCommand` 类实现了一个供所有子命令使用的 `parse()`。
- `func()` 在 `parse()` 之后被调用，应利用预先解析的输入来实际执行命令应该做的事情。这是命令的主要部分。此方法的返回值将在执行时作为 Twisted Deferred 返回。
- `at_post_cmd()` 在 `func()` 之后调用以处理可能的清理。

最后，您应该始终在类顶部添加一个信息丰富的 [文档字符串](https://www.python.org/dev/peps/pep-0257/#what-is-a-docstring)（`__doc__`）。该字符串会动态读取 [帮助系统](./Help-System.md) 以创建此命令的帮助条目。您应决定一种格式化帮助的方法并遵循该格式。

以下是如何定义一个简单的替代 "`smile`" 命令的示例：

```python
from evennia import Command

class CmdSmile(Command):
    """
    一个微笑命令

    用法：
      smile [at] [<someone>]
      grin [at] [<someone>]

    微笑到您附近的某人或()房间的总之。

    （此初始字符串（__doc__ 字符串）
    还用于自动生成此命令的帮助）
    """

    key = "smile"
    aliases = ["smile at", "grin", "grin at"]
    locks = "cmd:all()"
    help_category = "General"

    def parse(self):
        "非常简单的解析器"
        self.target = self.args.strip()

    def func(self):
        "这实际上是做事情"
        caller = self.caller

        if not self.target or self.target == "here":
            string = f"{caller.key} 微笑"
        else:
            target = caller.search(self.target)
            if not target:
                return
            string = f"{caller.key} 微笑着看向 {target.key}"

        caller.location.msg_contents(string)
```

将命令作为类并拆分 `parse()` 和 `func()` 的优势在于可以继承功能，而不必单独解析每个命令。例如，正如前面提到的，默认命令都继承自 `MuxCommand`。`MuxCommand` 实现了自己的 `parse()` 方法，理解了所有 MUX-like 命令的细节。因此，几乎没有默认命令需要实现 `parse()`，但可以假设传入的字符串已经被其父级以合适的方式分割和解析。

在您实际上可以在游戏中使用命令之前，您现在必须将其存储在 *命令集合* 中。请参阅 [命令集合](./Command-Sets.md) 页面。

### 命令前缀 

历史上，许多 MU* 服务器使用前缀，如 `@` 或 `&`，来表示命令用于管理或需要工作人员权限。这样做的问题在于，新人往往会对这些额外符号感到困惑。Evennia 允许可以使用带有或不带有这样的前缀的命令。

    CMD_IGNORE_PREFIXES = "@&/+`

这是一个由字符组成的设置字符串，每个字符都是可跳过的前缀 - _如果在跳过前缀后命令在其 cmdset 中仍然唯一_。

因此，如果您希望编写 `@look` 而不是 `look`，也是可以的 - `@` 将被忽略。但如果我们添加一个实际的 `@look` 命令（其键或别名为 `@look`），那么我们需要使用 `@` 来分开这两个。

这也用于默认命令。例如，`@open` 是一个建筑命令，允许您创建新的出口以链接两个房间。其 `key` 设置为 `@open`，包括 `@`（没有设置别名）。默认情况下，您可以使用 `@open` 和 `open` 这两个命令。但“open”是一个相当常见的单词，假设开发者添加了一个新的 `open` 命令用于打开门。那么 `@open` 和 `open` 就是两个不同的命令，必须使用 `@` 来分隔它们。

> `help` 命令将首选显示所有命令名称而不附加前缀。如果可能，只有在存在冲突时，前缀才会在帮助系统中显示。

### arg_regex

命令解析器非常通用，并不要求在命令名称后面跟一个空格。这意味着别名 `:` 可以像 `:smiles` 一样使用，而无需修改。这也意味着 `getstone` 将获取石头（除非确实存在一个名为 `getstone` 的命令，那么会使用该命令）。如果您希望告诉解析器在命令名称和参数之间强制要求特定分隔符（使得 `get stone` 工作，但 `getstone` 给出 '命令未找到' 错误），可以使用 `arg_regex` 属性。

`arg_regex` 是一个 [原始正则表达式字符串](https://docs.python.org/library/re.html)。系统将在运行时编译该正则表达式。这使您能够自定义*直接跟随*命令名（或别名）部分的格式，以便解析器匹配此命令。一些示例：

- `commandname argument` (`arg_regex = r"\s.+"`)：这强制解析器要求命令名称后面跟一个或多个空格。输入后面的内容将视为参数。但是，如果忘记空格（例如，命令没有参数），则不会匹配 `commandname`。
- `commandname` 或 `commandname argument` (`arg_regex = r"\s.+|$"`)：这使得 `look` 和 `look me` 工作，但 `lookme` 将无效。
- `commandname/switches arguments` (`arg_regex = r"(?:^(?:\s+|\/).*$)|^$"`）。如果您使用 Evennia 的 `MuxCommand` 命令父类，则可能希望使用此功能，因为它将允许 `/switche` 工作，同时有空格或没有空格。

`arg_regex` 允许您自定义命令的行为。您可以将其放在命令的父类中，以便自定义所有子类命令。但是，您也可以通过修改 `settings.COMMAND_DEFAULT_ARG_REGEX` 来更改所有命令的基本默认行为。

## 退出命令

通常，您只需在命令类的钩子方法之一中使用 `return` 退出该方法。然而，这仍然会按顺序触发命令的其他钩子方法。通常这就是您想要的，但有时可能有用，以便在解析方法中发现某些不合法的输入时中止命令。为了以这种方式退出命令，您可以引发 `evennia.InterruptCommand`：

```python
from evennia import InterruptCommand

class MyCommand(Command):

   # ...

   def parse(self):
       # ...
       # 如果这被调用，`func()` 和 `at_post_cmd` 将不会被调用
       raise InterruptCommand()
```

## 命令中的暂停

有时，您想在继续之前暂停命令的执行 - 也许您想模拟一次重击需要一些时间才能完成，也许您希望自己的声音回声在越来越长的延迟中返回。由于 Evennia 是异步运行的，因此不能在命令中使用 `time.sleep()` （实际上在任何地方都不能这样做）。如果这样做，则 *整个游戏* 将冻结，影响所有人！所以不要这样做。幸运的是，Evennia 提供了一种快速语法来在命令中进行暂停。

在您的 `func()` 方法中，您可以使用 `yield` 关键字。这是一个 Python 关键字，它会冻结当前执行的命令，等待更多处理。

> 请注意，您 *不能* 仅在任何代码中插入 `yield` 并期望它暂停。Evennia 只会在您 `yield` 在命令的 `func()` 方法内部时暂停。在其他地方不要指望它能工作。

以下是一个使用 5 秒的小暂停的命令示例：

```python
from evennia import Command

class CmdWait(Command):
    """
    一个演示如何等待的虚拟命令

    用法：
      wait

    """

    key = "wait"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        """命令执行。"""
        self.msg("开始...等待...")
        yield 5
        self.msg("... 5 秒后显示此消息...等待中...")
        yield 2
        self.msg("... 还有 2 秒过去了。")
```

重要行是 `yield 5` 和 `yield 2`。它将告诉 Evennia 在此处暂停执行，直到经过指定的秒数。

使用 `yield` 在您的命令 `func` 方法中有两件事情要记住：

1. 由 `yield` 创建的暂停状态不会保存。因此，如果服务器在命令暂停过程中重载，它将 *不会* 恢复，命令的其余部分将永远不会触发。所以要小心不要以不清除重载的方式冻结角色或帐户。
2. 如果您使用 `yield`，则不可以在 `func` 方法中使用 `return <values>`。您将收到关于此的错误消息。这是由于 Python 生成器的工作原理。然而，您可以正常使用“裸”的 `return`。通常情况下，`func` 没有必要返回值，但如果您确实需要在同一 `func` 中混合使用 `yield` 和最后的返回值，可以查看 [twisted.internet.defer.returnValue](https://twistedmatrix.com/documents/current/api/twisted.internet.defer.html#returnValue)。

## 请求用户输入

`yield` 关键字也可用于请求用户输入。同样，您不能在命令中使用 Python 的 `input`，因为它会冻结 Evennia，等待用户输入文本。在命令的 `func` 方法内部，可以使用以下语法：

```python
answer = yield("您的问题")
```

以下是一个非常简单的示例：

```python
class CmdConfirm(Command):

    """
    一个演示确认的虚拟命令

    用法：
        confirm

    """

    key = "confirm"

    def func(self):
        answer = yield("您确定要继续吗？")
        if answer.strip().lower() in ("yes", "y"):
            self.msg("是的！")
        else:
            self.msg("不！")
```

这一次，当用户输入 `confirm` 命令时，将询问她是否想继续。输入 “yes” 或 “y”（不区分大小写）将给出第一个回复，否则将显示第二个回复。

> 再次注意，`yield` 关键字不会存储状态。如果游戏在等待用户回答时重新加载，用户将必须重新开始。使用 `yield` 来做重要或复杂的选择并不是一个好主意，持久的 [EvMenu](./EvMenu.md) 可能在这种情况下更合适。

## 系统命令

*注意：这是一个高级主题。如果您是第一次学习命令，则可以跳过此部分。*

有几种命令情况在服务器的眼中是特殊的。帐户输入空字符串会发生什么？如果给定的“命令”实际上是用户要发送消息的频道的名称怎么办？或者如果存在多个命令可能性呢？

此类“特殊情况”由称为 *系统命令* 的内容处理。系统命令的定义方式与其他命令相同，只是其名称（键）必须设置为引擎保留的名称（这些名称在 `evennia/commands/cmdhandler.py` 的顶部定义）。您可以在 `evennia/commands/default/system_commands.py` 中找到（未使用的）系统命令的实现。由于这些默认情况下未包含在任何 `CmdSet` 中，因此它们实际上未被使用，仅供展示。当发生特殊情况时，Evennia 会在所有有效 `CmdSet` 中查找您自定义的系统命令。只有在此之后，它才会退回到硬编码的实现。

以下是触发系统命令的异常情况。您可以在 `evennia.syscmdkeys` 上找到它们使用的命令键：

- 无输入（`syscmdkeys.CMD_NOINPUT`） - 帐户在没有任何输入的情况下按下了 return。默认什么也不做，但在某些实现（如将非命令解释为文本输入的行编辑器）中这样做可能会有用（编辑缓冲区中的空行）。
- 找不到命令（`syscmdkeys.CMD_NOMATCH`） - 找不到任何匹配命令。默认是显示 “Huh?” 错误消息。
- 找到多个匹配命令（`syscmdkeys.CMD_MULTIMATCH`） - 默认是显示匹配列表。
- 用户没有权限执行该命令（`syscmdkeys.CMD_NOPERM`） - 默认是显示 “Huh?” 错误消息。
- 渠道（`syscmdkeys.CMD_CHANNEL`） - 这是您订阅的频道的 [频道](./Channels.md) 名称 - 默认是将命令的参数转发到该频道。这些命令由通讯系统根据您的订阅动态创建。
- 新会话连接（`syscmdkeys.CMD_LOGINSTART`）。此命令名称应放入 `settings.CMDSET_UNLOGGEDIN` 中。每当建立新连接时，默认总是在服务器上调用此命令（默认是显示登录界面）。

以下是重新定义帐户未提供任何输入时会发生的事情的示例（例如，仅按下回车）。当然，新的系统命令也必须添加到 cmdset 中，才能生效。

```python
from evennia import syscmdkeys, Command

class MyNoInputCommand(Command):
    "用法：只需按下 return，我敢打赌"
    key = syscmdkeys.CMD_NOINPUT

    def func(self):
        self.caller.msg("别这样按回车，跟我说句话！")
```

## 动态命令

*注意：这是一个高级主题。*

通常，命令作为固定类创建并使用而不进行修改。但是在某些情况下，确切的键、别名或其他属性不可能（或不实际）被预编码。

要创建一个具有动态调用签名的命令，首先正常在一个类中定义命令体（将 `key` 和 `aliases` 设置为默认值），然后使用以下调用（假设您创建的命令类名为 `MyCommand`）：

```python
cmd = MyCommand(key="newname",
                aliases=["test", "test2"],
                locks="cmd:all()",
                ...)
```

您传递给命令构造函数的 *所有* 关键字参数将作为属性存储在该命令对象上。此属性将重载在父类上定义的现有属性。

通常，您会定义类并仅在运行时重载 `key` 和 `aliases` 之类的内容。但是，原则上，您还可以将方法对象（如 `func`）作为关键字参数传递，以使命令在运行时完全自定义。

### 动态命令 - 出口

出口是 [动态命令](./Commands.md#dynamic-commands) 的示例。

Evennia 中的 [Exit](./Objects.md) 对象的功能并不是在引擎中硬编码的。相反，出口是正常的 [类型类](./Typeclasses.md) 对象，加载时将自动创建一个 [CmdSet](./Command-Sets.md)。该命令集合只有一个动态创建的命令，其属性（键、别名和锁）与出口对象本身相同。当输入出口名称时，此动态出口命令被触发，执行访问检查后将角色移动到出口的目标。

尽管您可以自定义出口对象及其命令以实现完全不同的行为，但通常只需使用适当的 `traverse_*` 钩子便可以满足需求。但是，如果您有兴趣真正改变内部工作原理，请查看 `evennia/objects/objects.py`，了解 `Exit` 类型类是如何设置的。

## 命令实例被重用

*注意：这是一个高级主题，可以在第一次学习命令时跳过。*

一个对象上的命令类只实例化一次，然后重复使用。因此，如果您从 `object1` 运行命令一次又一次，实际上您是在重复运行同一个命令实例（但是，如果您运行同一命令，但位于 `object2` 上，则会是不同的实例）。这通常是不显而易见的，因为每次使用命令实例时，所有相关属性都会被覆盖。但是，了解这一点后，您可以实现一些更奇特的命令机制，比如命令拥有之前输入的“记忆”，以便您可以反向引用之前的参数等。

> 注意：在服务器重载时，所有命令都会重建，内存会被清空。

要展示这一点，请考虑以下命令：

```python
class CmdTestID(Command):
    key = "testid"

    def func(self):
        if not hasattr(self, "xval"):
            self.xval = 0
        self.xval += 1

        self.caller.msg(f"命令内存 ID: {id(self)} (xval={self.xval})")
```

将此命令添加到默认角色的命令集合中，可以在游戏中获得如下结果：

```
> testid
命令内存 ID: 140313967648552 (xval=1)
> testid
命令内存 ID: 140313967648552 (xval=2)
> testid
命令内存 ID: 140313967648552 (xval=3)
```

注意 `testid` 命令的内存地址始终不变，而 `xval` 逐渐增加。

## 动态创建命令

*这也是一个高级主题。*

命令还可以在运行时创建并添加到命令集合中。使用关键字参数创建类实例时，将该关键字参数分配为该特定命令的属性：

```python
class MyCmdSet(CmdSet):

    def at_cmdset_creation(self):
        self.add(MyCommand(myvar=1, foo="test"))
```

这样将启动 `MyCommand`，并设置 `myvar` 和 `foo` 为属性（可以访问为 `self.myvar` 和 `self.foo`）。如何使用它们取决于命令。请记住上节的讨论 - 由于命令实例被重用，这些属性将 *保留* 在命令中，只要此命令集合和其对象在内存中（即，直到下一个重载）。除非在命令运行时以某种方式重置 `myvar` 和 `foo`，否则它们可以被修改，并且这些更改会记住在后续使用命令时。

## 命令的实际工作方式

*注意：这是一个主要对服务器开发人员感兴趣的高级主题。*

每当用户向 Evennia 发送文本时，服务器会尝试查明所输入的文本是否对应于已知命令。对于登录用户，命令处理程序的顺序如下：

1. 用户输入一串文本并按下回车。
2. 用户的会话确定文本不是某个特定于协议的控制序列或 OOB 命令，而是将其发送给命令处理程序。
3. Evennia 的 *命令处理程序* 分析会话并获取对帐户和可能当前木偶角色的引用（这些将在稍后存储在命令对象上）。适当设置 *caller* 属性。
4. 如果输入为空字符串，则重新发送命令为 `CMD_NOINPUT`。如果在 cmdset 中找不到此类命令，则忽略。
5. 如果 `command.key` 匹配 `settings.IDLE_COMMAND`，则更新计时器，但不进行其他操作。
6. 命令处理程序收集当前 *caller* 可用的 CmdSets：
    - 调用者当前活动的 CmdSet。
    - 如果调用者是一个操纵对象，则定义在当前帐户上的 CmdSets。
    - 定义在会话自身上的 CmdSets。
    - 同一位置中可能存在的对象的活动 CmdSets（如果有）。这包括 [出口](./Objects.md#exits) 上的命令。
    - 代表可用 [通讯](./Channels.md) 的动态创建的系统命令集。
7. 所有 *同一优先级* 的 CmdSets 被分组在一起进行合并。分组可避免将多个同一优先级的集合合并到较低优先级集合中的顺序依赖问题。
8. 所有分组的 CmdSets 根据每个集合的合并规则反转优先级合并为一个合并 CmdSet。
9. Evennia 的 *命令解析器* 获取合并的 cmdset，根据每个命令（使用其键和别名）与 *caller* 输入的字符串开头进行匹配。这会生成一组候选者。
10. *命令解析器* 接下来根据匹配的字符数和相应已知命令的匹配百分比对匹配进行评分。只有当候选者无法区分时，才会返回多个匹配项。
    - 如果返回多个匹配，重新发送为 `CMD_MULTIMATCH`。如果在 cmdset 中找不到此类命令，则返回硬编码的匹配列表。
    - 如果未找到匹配，将重新发送为 `CMD_NOMATCH`。如果在 cmdset 中找不到此类命令，则返回硬编码的错误消息。
11. 如果解析器找到单个命令，则将正确的命令对象从存储中取出。这通常并不意味着重新初始化。
12. 检查调用者是否实际上有权访问该命令，通过验证命令的 *lockstring*。如果没有，则不将其视为合适的匹配，并触发 `CMD_NOMATCH`。
13. 如果新命令标记为频道命令，则重新发送为 `CMD_CHANNEL`。如果在 cmdset 中找不到此类命令，则使用硬编码实现。
14. 为命令实例分配多个有用的变量（见前面几节）。
15. 在命令实例上调用 `at_pre_command()`。
16. 在命令实例上调用 `parse()`。此方法将给出其余字符串，即命令名称之后的字符串。此方法旨在将字符串预解析为对 `func()` 方法有用的形式。
17. 在命令实例上调用 `func()`。这是命令的功能主体，实际上执行有用操作。
18. 在命令实例上调用 `at_post_command()`。

## 其他说明

`Command.func()` 的返回值是 Twisted [deferred](https://twistedmatrix.com/documents/current/core/howto/defer.html)。Evennia 默认不会使用此返回值。如果您使用此返回值，则必须以异步方式执行，使用回调。

```python
# 在命令类的 func() 中
def callback(ret, caller):
    caller.msg(f"返回值为 {ret}")

deferred = self.execute_command("longrunning")
deferred.addCallback(callback, self.caller)
```

这对大多数高级/异域设计来说可能不相关（例如，可能会用来创建嵌套命令结构）。

`save_for_next` 类变量可用于实现状态持久的命令。例如，这可以使命令在“它”上操作，其中由先前命令处理的内容决定。
