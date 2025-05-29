# 添加自定义命令

在本课中，我们将学习如何创建自己的 Evennia [命令](../../../Components/Commands.md)。如果您是 Python 新手，您还将学习一些关于如何操作字符串和从 Evennia 获取信息的基础知识。

命令是处理用户输入并导致结果发生的东西。
例如，`look` 命令会检查您当前的位置，并告诉您它看起来像什么以及里面有什么。

```{sidebar} 命令不是类型化的

如果您刚刚从上一课中学习，您可能想知道命令和命令集不是 `typeclassed`。也就是说，它们的实例不会保存到数据库中。它们“只是”普通的 Python 类。
```

在 Evennia 中，命令是一个 Python _类_。如果您不确定类是什么，请查看[关于它的上一课](./Beginner-Tutorial-Python-classes-and-objects.md)！命令继承自 `evennia.Command` 或其他命令类之一，例如 `MuxCommand`，这是大多数默认命令使用的。

所有命令都被分组在另一个称为 _命令集_ 的类中。可以将命令集视为包含许多不同命令的袋子。例如，一个命令集可以包含所有战斗命令，另一个可以用于建筑等。

然后将命令集与对象关联，例如与您的角色关联。这样做会使该命令集中的命令对对象可用。默认情况下，Evennia 将所有角色命令分组到一个称为 `CharacterCmdSet` 的大命令集中。它位于 `DefaultCharacter` 上（因此，通过继承，位于 `typeclasses.characters.Character` 上）。

## 创建自定义命令

打开 `mygame/commands/command.py`。此文件已经为您填充了一些内容。

```python
"""
(module docstring)
"""

from evennia import Command as BaseCommand
# from evennia import default_cmds

class Command(BaseCommand):
    """
    (class docstring)
    """
    pass

# (lots of commented-out stuff)
# ...
```

忽略文档字符串（如果您愿意，可以阅读），这是模块中唯一真正活动的代码。

我们可以看到我们从 `evennia` 导入 `Command`，并使用 `from ... import ... as ...` 形式将其重命名为 `BaseCommand`。这样我们可以让子类也命名为 `Command`，以便更容易引用。类本身没有做任何事情，它只是有一个 `pass`。因此，与前几课中的 `Object` 和 `Character` 一样，此类与其父类相同。

> 注释掉的 `default_cmds` 使我们可以轻松覆盖 Evennia 的默认命令。我们稍后会尝试一下。

我们可以直接修改此模块，但为了尝试，我们在单独的模块中工作。打开一个新文件 `mygame/commands/mycommands.py` 并添加以下代码：

```python
# in mygame/commands/mycommands.py

from commands.command import Command

class CmdEcho(Command):
    key = "echo"

```

这是您能想象到的最简单的命令形式。它只是给自己一个名字，“echo”。这就是您稍后将用来调用此命令的方式。

接下来，我们需要将其放入一个 CmdSet。现在它将是一个单命令 CmdSet！将您的文件更改如下：

```python
# in mygame/commands/mycommands.py

from commands.command import Command
from evennia import CmdSet

class CmdEcho(Command):
    key = "echo"


class MyCmdSet(CmdSet):

    def at_cmdset_creation(self):
        self.add(CmdEcho)

```

我们的 `MyCmdSet` 类必须有一个 `at_cmdset_creation` 方法，名字必须完全一样——这是 Evennia 在稍后设置 cmdset 时会寻找的东西，所以如果您没有设置它，它将使用父类的版本，该版本是空的。在内部，我们通过 `self.add()` 将命令类添加到 cmdset 中。如果您想将更多命令添加到此 CmdSet 中，只需在此之后添加更多 `self.add` 行即可。

最后，让我们将此命令添加到我们自己，以便我们可以尝试一下。在游戏中，您可以再次尝试 `py`：

```
> py me.cmdset.add("commands.mycommands.MyCmdSet")
```

`me.cmdset` 是存储在我们身上的所有 cmdsets 的存储。通过提供我们的 CmdSet 类的路径，它将被添加。

现在尝试

```
> echo
Command "echo" has no defined `func()`. Available properties ...
...(lots of stuff)...
```

`echo` 工作了！您应该会看到一长串输出。您的 `echo` 函数实际上并没有“做”任何事情，因此默认功能是显示使用命令时可用的所有有用资源。让我们看看其中的一些：

```
Command "echo" has no defined `func()` method. Available properties on this command are:

     self.key (<class 'str'>): "echo"
     self.cmdname (<class 'str'>): "echo"
     self.raw_cmdname (<class 'str'>): "echo"
     self.raw_string (<class 'str'>): "echo
"
     self.aliases (<class 'list'>): []
     self.args (<class 'str'>): ""
     self.caller (<class 'typeclasses.characters.Character'>): YourName
     self.obj (<class 'typeclasses.characters.Character'>): YourName
     self.session (<class 'evennia.server.serversession.ServerSession'>): YourName(#1)@1:2:7:.:0:.:0:.:1
     self.locks (<class 'str'>): "cmd:all();"
     self.help_category (<class 'str'>): "general"
     self.cmdset (... a long list of commands ...)
```

这些都是您可以在命令实例上通过 `.` 访问的属性，例如 `.key`、`.args` 等。Evennia 使这些对您可用，并且每次运行命令时它们都会有所不同。我们现在将使用的最重要的几个是：

- `caller` - 这是“您”，调用命令的人。
- `args` - 这是命令的所有参数。现在它是空的，但如果您尝试 `echo foo bar`，您会发现它将是 `" foo bar"`（包括 `echo` 和 `foo` 之间的额外空格，您可能想要去掉它）。
- `obj` - 这是此命令（和 CmdSet）“位于”其上的对象。所以在这种情况下是您。
- `raw_string` 不常用，但它是用户的完全未修改的输入。它甚至包括用于将命令发送到服务器的换行符（这就是为什么结束引号出现在下一行的原因）。

我们的命令还没有做任何事情的原因是因为它缺少一个 `func` 方法。这是 Evennia 用来确定命令实际做什么的方法。修改您的 `CmdEcho` 类：

```python
# in mygame/commands/mycommands.py
# ...

class CmdEcho(Command):
    """
    A simple echo command

    Usage:
        echo <something>

    """
    key = "echo"

    def func(self):
        self.caller.msg(f"Echo: '{self.args}'")

# ...
```

首先，我们添加了一个文档字符串。这通常是一个好习惯，但对于命令类，它也会自动成为游戏中的帮助条目！

```{sidebar} 使用 Command.msg
在命令类中，`self.msg()` 作为 `self.caller.msg()` 的便捷快捷方式。不仅更短，它还具有一些优势，因为命令可以在消息中包含更多元数据。因此，使用 `self.msg()` 通常更好。但在本教程中，`self.caller.msg()` 更明确地显示了发生了什么。
```

接下来，我们添加了 `func` 方法。它有一个活动行，利用了命令类提供给我们的那些变量之一。如果您完成了 [基本 Python 教程](./Beginner-Tutorial-Python-basic-introduction.md)，您会认识到 `.msg` - 这将向附加到我们的对象发送消息 - 在这种情况下是 `self.caller`，也就是我们。我们获取 `self.args` 并将其包含在消息中。

由于我们没有更改 `MyCmdSet`，它将像以前一样工作。重新加载并重新将此命令添加到我们自己以尝试新版本：

```
> reload
> py self.cmdset.add("commands.mycommands.MyCmdSet")
> echo
Echo: ''
```

尝试传递一个参数：

```
> echo Woo Tang!
Echo: ' Woo Tang!'
```

请注意，`Woo` 前面有一个额外的空格。这是因为 `self.args` 包含命令名称之后的 _所有内容_，包括空格。让我们通过一个小调整去掉那个额外的空格：

```python
# in mygame/commands/mycommands.py
# ...

class CmdEcho(Command):
    """
    A simple echo command

    Usage:
        echo <something>

    """
    key = "echo"

    def func(self):
        self.caller.msg(f"Echo: '{self.args.strip()}'")

# ...
```

唯一的区别是我们在 `self.args` 上调用了 `.strip()`。这是所有字符串上可用的辅助方法 - 它会去掉字符串前后的所有空白。现在命令参数前面将不再有任何空格。

```
> reload
> py self.cmdset.add("commands.mycommands.MyCmdSet")
> echo Woo Tang!
Echo: 'Woo Tang!'
```

不要忘记查看 echo 命令的帮助：

```
> help echo
```

您将获得您在命令类中放置的文档字符串！

### 使我们的 cmdset 持久化

每次重新加载时都必须重新添加我们的 cmdset 有点烦人，对吧？不过，将 `echo` 设为 _持久性_ 更改很简单：

```
> py self.cmdset.add("commands.mycommands.MyCmdSet", persistent=True)
```

现在您可以随意 `reload`，您的代码更改将直接可用，而无需再次重新添加 MyCmdSet。

我们将以另一种方式添加此 cmdset，因此手动将其删除：

```
> py self.cmdset.remove("commands.mycommands.MyCmdSet")
```

### 将 echo 命令添加到默认 cmdset

上面我们将 `echo` 命令添加到我们自己。这将 _仅_ 对我们可用，而对游戏中的其他人不可用。但 Evennia 中的所有命令都是命令集的一部分，包括我们一直在使用的正常 `look` 和 `py` 命令。您可以轻松地将默认命令集扩展为您的 `echo` 命令 - 这样游戏中的 _每个人_ 都可以访问它！

在 `mygame/commands/` 中，您会发现一个名为 `default_cmdsets.py` 的现有模块。打开它，您会发现四个空的 cmdset 类：

- `CharacterCmdSet` - 它位于所有角色上（这是我们通常想要修改的）
- `AccountCmdSet` - 它位于所有帐户上（在角色之间共享，例如 `logout` 等）
- `UnloggedCmdSet` - 登录前可用的命令，例如用于创建密码和连接到游戏的命令。
- `SessionCmdSet` - 您的会话（您的特定客户端连接）唯一的命令。默认情况下未使用。

按如下方式调整此文件：

```python
# in mygame/commands/default_cmdsets.py 

# ... 

from . import mycommands    # <-------  

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """
 
    key = "DefaultCharacter"
 
    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(mycommands.CmdEcho)    # <-----------
# ... 
```

```{sidebar} super() 和覆盖默认值
`super()` Python 关键字意味着调用 _父类_。在这种情况下，父类将所有默认命令添加到此 cmdset 中。

巧合的是，这也是您在 Evennia 中替换默认命令的方式！要替换例如命令 `get`，只需将您的替换命令命名为 `key` 'get' 并将其添加到此处 - 由于它是在 `super()` 之后添加的，它将替换 `get` 的默认版本。
```

这与您将 `CmdEcho` 添加到 `MyCmdSet` 的方式相同。唯一的区别是 cmdsets 会自动添加到所有角色/帐户等，因此您不必手动执行此操作。我们还必须确保从您的 `mycommands` 模块中导入 `CmdEcho` 以便此模块了解它。`from . import mycommands` 中的句号 ''`.`'' 表示我们告诉 Python `mycommands.py` 位于与当前模块相同的目录中。我们想要导入整个模块。稍后我们访问 `mycommands.CmdEcho` 以将其添加到角色 cmdset 中。

只需 `reload` 服务器，您的 `echo` 命令将再次可用。一个给定命令可以成为多少个 cmdsets 的一部分是没有限制的。

要删除，只需注释掉或删除 `self.add()` 行。不过现在保持这样 - 我们将在下面扩展它。

### 确定要击打的对象

让我们尝试一些比 echo 更令人兴奋的东西。让我们制作一个 `hit` 命令，用来打某人的脸！我们希望它的工作方式如下：

```
> hit <target>
You hit <target> with full force!
```

不仅如此，我们还希望 `<target>` 看到

```
You got hit by <hitter> with full force!
```

这里，`<hitter>` 是使用 `hit` 命令的人，而 `<target>` 是进行击打的人；所以如果你的名字是 `Anna`，你打了一个名叫 `Bob` 的人，这看起来像这样：

```
> hit bob
You hit Bob with full force!
```

而 Bob 会看到

```
You got hit by Anna with full force!
```

仍然在 `mygame/commands/mycommands.py` 中，在 `CmdEcho` 和 `MyCmdSet` 之间添加一个新类。

```python
# in mygame/commands/mycommands.py

# ...

class CmdHit(Command):
    """
    Hit a target.

    Usage:
      hit <target>

    """
    key = "hit"

    def func(self):
        args = self.args.strip()
        if not args:
            self.caller.msg("Who do you want to hit?")
            return
        target = self.caller.search(args)
        if not target:
            return
        self.caller.msg(f"You hit {target.key} with full force!")
        target.msg(f"You got hit by {self.caller.key} with full force!")

# ...
```

这里有很多事情需要剖析：
- **第 5 行**：正常的 `class` 头。我们继承自 `Command`，我们在此文件顶部导入。
- **第 6-12 行**：命令的文档字符串和帮助条目。您可以根据需要尽可能多地扩展此内容。
- **第 13 行**：我们希望编写 `hit` 来使用此命令。
- **第 16 行**：我们像以前一样去掉参数中的空白。由于我们不想一遍又一遍地执行 `self.args.strip()`，因此我们将去掉空白的版本存储在 _局部变量_ `args` 中。请注意，通过这样做，我们不会修改 `self.args`，`self.args` 仍然会有空白，并且在此示例中与 `args` 不同。

```{sidebar} if 语句
if 语句的完整形式是

	if condition:
	    ...
	elif othercondition:
	    ...
	else:
	    ...

可以有任意数量的 `elif` 来标记代码的不同分支何时应该运行。如果提供了 `else`，它将在没有其他条件为真时运行。
```

- **第 17 行** 有我们的第一个 _条件_，一个 `if` 语句。它的写法是 `if <condition>:`，只有当该条件为“真”时，`if` 语句下的缩进代码块才会运行。要了解 Python 中的真值，通常更容易学习什么是“假值”：
    - `False` - 这是 Python 中的保留布尔词。相反的是 `True`。
    - `None` - 另一个保留字。这表示没有结果或值。
    - `0` 或 `0.0`
    - 空字符串 `""`、`''`，或空的三引号字符串如 `""""""`、`''''''`
    - 我们尚未使用的空 _可迭代对象_，如空列表 `[]`、空元组 `()` 和空字典 `{}`。
    - 其他一切都是“真值”。

    **第 16 行** 的条件是 `not args`。`not` 会 _反转_ 结果，因此如果 `args` 是空字符串（假值），整个条件就会变为真值。让我们继续看代码：

```{sidebar} 代码中的错误

随着要尝试的代码片段越来越长，您犯错并在重新加载时收到 `traceback` 的可能性越来越大。这将直接出现在游戏中或在您的日志中（在终端中使用 `evennia -l` 查看）。

不要惊慌 - traceback 是您的朋友！它们是自下而上读取的，通常会准确描述您的问题所在。有关更多提示，请参阅 [Python 介绍课程](./Beginner-Tutorial-Python-basic-introduction.md)。如果您遇到困难，请向 Evennia 社区寻求帮助。
```

- **第 16-17 行**：此代码仅在 `if` 语句为真时运行，在这种情况下，如果 `args` 是空字符串。
- **第 19 行**：`return` 是一个保留的 Python 词，立即退出 `func`。
- **第 20 行**：我们使用 `self.caller.search` 在当前位置查找目标。
- **第 21-22 行**：`.search` 的一个功能是它已经会通知 `self.caller` 如果找不到目标。在这种情况下，`target` 将为 `None`，我们应该直接 `return`。
- **第 23-24 行**：此时我们有一个合适的目标，可以向每个目标发送我们的击打字符串。

最后，我们还必须将其添加到 CmdSet 中。让我们将其添加到 `MyCmdSet`。

```python
# in mygame/commands/mycommands.py

# ...
class MyCmdSet(CmdSet):

    def at_cmdset_creation(self):
        self.add(CmdEcho)
        self.add(CmdHit)

```

请注意，由于我们之前执行了 `py self.cmdset.remove("commands.mycommands.MyCmdSet")`，此 cmdset 不再在我们的角色上可用。相反，我们将这些命令直接添加到我们的默认 cmdset 中。

```python
# in mygame/commands/default_cmdsets.py 

# ,.. 

from . import mycommands    

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """
 
    key = "DefaultCharacter"
 
    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(mycommands.MyCmdSet)    # <-----------
# ... 
```

我们从添加单个 `echo` 命令更改为一次性添加整个 `MyCmdSet`！这将把该 cmdset 中的所有命令添加到 `CharacterCmdSet` 中，是一次性添加大量命令的实用方法。一旦您进一步探索 Evennia，您会发现 [Evennia contribs](../../../Contribs/Contribs-Overview.md) 都在 cmdsets 中分发他们的新命令，因此您可以像这样轻松地将它们添加到您的游戏中。

接下来我们重新加载，让 Evennia 知道这些代码更改并尝试一下：

```
> reload
hit
Who do you want to hit?
hit me
You hit YourName with full force!
You got hit by YourName with full force!
```

没有目标，我们打了自己。如果您还有前一课中的一条龙，您可以尝试击打它（如果您敢的话）：

```
hit smaug
You hit Smaug with full force!
```

您不会看到第二个字符串。只有 Smaug 看到了（而且不高兴）。

## 总结

在本课中，我们学习了如何创建自己的命令，将其添加到 CmdSet 中，然后添加到我们自己身上。我们还激怒了一条龙。

在下一课中，我们将学习如何用不同的武器打击 Smaug。我们还将了解如何替换和扩展 Evennia 的默认命令。
