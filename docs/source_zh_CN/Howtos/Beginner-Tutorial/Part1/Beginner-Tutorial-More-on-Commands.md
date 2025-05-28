# 解析命令输入

在本课中，我们将学习解析命令输入的一些基本知识。我们还将学习如何添加、修改和扩展Evennia的默认命令。

## 更高级的解析

在[上一课](./Beginner-Tutorial-Adding-Commands.md)中，我们创建了一个`hit`命令，并用它击中了龙。你应该还保留着那部分代码。

现在让我们扩展一下这个简单的`hit`命令，以接受更复杂的输入：

    hit <目标> [[with] <武器>]

也就是说，我们希望支持以下几种形式：

    hit 目标
    hit 目标 武器
    hit 目标 with 武器

如果没有指定武器，则使用拳头。快速输入时，跳过"with"也是可以的。现在，让我们再次修改`mygame/commands/mycommands.py`。我们将解析部分提取到一个新的`parse`方法中：

```python
:linenos:
:emphasize-lines: 14,15,16,18,29,35,41
#...

class CmdHit(Command):
    """
    击中目标。

    用法：
      hit <目标>

    """
    key = "hit"

    def parse(self):
        self.args = self.args.strip()  # 去掉前后的空格
        target, *weapon = self.args.split(" with ", 1)  # 按照"with"分割输入
        if not weapon:
            target, *weapon = target.split(" ", 1)  # 如果没有"with"，按空格分割
        self.target = target.strip()  # 去掉目标前后的空格
        if weapon:
            self.weapon = weapon[0].strip()  # 去掉武器前后的空格
        else:
            self.weapon = ""  # 如果没有武器，设置为空

    def func(self):
        if not self.args:
            self.caller.msg("你想打谁？")  # 如果没有指定目标
            return
        # 获取目标
        target = self.caller.search(self.target)
        if not target:
            return
        # 获取武器
        weapon = None
        if self.weapon:
            weapon = self.caller.search(self.weapon)
        if weapon:
            weaponstr = f"{weapon.key}"
        else:
            weaponstr = "拳头"

        self.caller.msg(f"你用{weaponstr}打了{target.key}!")
        target.msg(f"你被{self.caller.key}用{weaponstr}打了!")
```

`parse`方法是Evennia会在`func`之前调用的特殊方法。在这时，它可以访问所有与命令相关的变量。使用`parse`不仅让代码更易于阅读，还可以让其他命令继承你解析的逻辑。如果你想让其他命令也能理解`<arg> with <arg>`这种格式，可以继承这个类，只需要实现`func`方法即可，而不需要重新实现`parse`。

```{sidebar} 元组与列表

- 列表是用`[a, b, c, d, ...]`表示的，可以在创建之后添加或删除元素。
- 元组是用`(a, b, c, d, ...)`表示的，一旦创建就不能修改。

```

- **第14行** - 我们在这里一次性去掉了`self.args`的前后空格，并将去掉空格的版本重新赋值给`self.args`。之后就无法再获取原始的输入了，这对本命令来说是可以接受的。
- **第15行** - 这里我们使用了字符串的`.split`方法，`split(" with ", 1)`表示按照`" with "`分割字符串，只会分割一次。如果字符串中没有`with`，返回的列表将只有一个元素。
    1. 如果输入是`hit smaug`，结果是`["smaug"]`。
    2. 如果输入是`hit smaug sword`，结果是`["smaug sword"]`。
    3. 如果输入是`hit smaug with sword`，结果是`["smaug", "sword"]`。

    所以我们会得到一个包含1个或2个元素的列表。然后我们将它赋值给两个变量，`target, *weapon =`。星号（`*`）的作用是将剩余的部分吸收进一个元组中。
    1. `target`会是`"smaug"`，`weapon`会是空元组`()`。
    2. `target`会是`"smaug sword"`，`weapon`会是空元组`()`。
    3. `target`会是`"smaug"`，`weapon`会是元组`("sword",)`。

- **第16-17行** - 在这个条件判断中，我们检查`weapon`是否为空。如果为空，说明没有输入武器，那么我们就按照空格分割`target`字符串。
    1. 如果输入是`hit smaug`，`target`会是`"smaug"`，`weapon`会是空列表`[]`。
    2. 如果输入是`hit smaug sword`，`target`会是`"smaug"`，`weapon`会是元组`("sword",)`。

- **第18-22行** - 我们将`target`和`weapon`存储到`self.target`和`self.weapon`中。我们必须将它们存储到`self`中，以便在`func`方法中使用。如果`weapon`存在，它就是一个元组（例如`("sword",)`），所以我们用`weapon[0]`来获取第一个元素（字符串），并通过`.strip()`去掉多余的空格。

接下来是`func`方法。主要的区别是，我们现在可以直接使用`self.target`和`self.weapon`了。

```{sidebar}
这里我们明确地创建了两个消息来分别发送给攻击者和目标。稍后我们将介绍如何使用Evennia的[内联函数](../../../Components/FuncParser.md)来根据不同的观众显示不同的字符串。
```

- **第29行和第35行** - 我们使用之前解析出的目标和武器来找到相应的资源。
- **第34-39行** - 由于武器是可选的，我们需要为没有武器的情况提供默认值（用拳头！）。我们将这个信息保存在`weaponstr`中。
- **第41-42行** - 我们将`weaponstr`与攻击文本合并并发送给攻击者和目标。

现在，让我们试试这个命令！

    > reload
    > hit smaug with sword
    找不到 'sword'。
    你用拳头打了smaug！

哎呀，`self.caller.search(self.weapon)`找不到剑。这是合理的（我们没有剑）。由于我们没有像对待`target`一样在找不到武器时`return`，程序继续使用拳头进行攻击。

我们来创建一把剑：

    > create sword

剑会出现在我们的物品栏中，使用`i`或者`inventory`命令可以看到它。`.search`函数会找到它。这里不需要重新加载（因为没有修改代码，只是数据库中的物品发生了变化）。

    > hit smaug with sword
    你用剑打了smaug！

可怜的Smaug。

## 向对象添加命令

```{sidebar} 对象上的命令集 
如果你有疑问，`Character CmdSet`是在角色上设置的命令集，只会对该角色有效。如果不这样做，你在同一房间里的其他角色可能会出现命令冲突。你可以查看[命令集](../../../Components/Command-Sets.md)文档了解更多信息。
```

正如我们在[添加命令](./Beginner-Tutorial-Adding-Commands.md)一课中学到的，命令是按命令集进行分组的。这些命令集可以通过`obj.cmdset.add()`添加到对象上，然后该对象就能使用这些命令。

之前我们没有提到的一点是，默认情况下，这些命令也会对与该对象处于同一位置的角色有效。如果你在[快速构建教程](./Beginner-Tutorial-Building-Quickstart.md)中做过练习，你应该见过"Red Button"对象的示例。在[教程世界](./Beginner-Tutorial-Tutorial-World.md)中也有许多带有命令的对象示例。

为了展示这个如何工作，让我们把`hit`命令添加到前面创建的`sword`对象上。

    > py self.search("sword").cmdset.add("commands.mycommands.MyCmdSet", persistent=True)

我们找到剑（它还在物品栏中，所以`self.search`能够找到它），然后将`MyCmdSet`添加到它。这样，`hit`和`echo`命令都会被添加到剑上。

让我们试试攻击它！

    > hit
    找到多个与 'hit' 匹配的命令（请缩小目标）:
    hit-1 (剑 #11)
    hit-2

```{sidebar} 多重匹配

一些游戏引擎在找到多个匹配时会直接选择第一个。Evennia 总是会给你一个选择。这是因为 Evennia 无法知道 `hit` 和 `hit` 是否是不同的——也许它们的行为取决于它们所在的物体？此外，想象一下，如果你有一个红色按钮和一个蓝色按钮，它们都能执行 `push` 命令。那么如果你只写 `push`，你会希望被问到到底是哪个按钮吗？
```

哇，这不按计划执行。Evennia 实际上找到了两个 `hit` 命令，并且不知道该使用哪一个（我们知道它们是一样的，但 Evennia 不确定）。如我们所见，`hit-1` 是在剑上找到的，另一个是我们之前将 `MyCmdSet` 添加到自己身上的结果。我们可以轻松地告诉 Evennia 你到底是指哪个命令：

    > hit-1
    你想打谁？
    > hit-2
    你想打谁？

在这个情况下，我们不需要两个命令集，我们应该删除那个位于自己身上的 `hit` 命令。

进入 `mygame/commands/default_cmdsets.py`，找到你在上一节中添加 `MyCmdSet` 的那一行。删除或注释掉它：

```python
# mygame/commands/default_cmdsets.py 

# ...

class CharacterCmdSet(default_cmds.CharacterCmdSet):

    # ... 
    def at_object_creation(self): 

        # self.add(MyCmdSet)    # <---------

```

接下来，执行 `reload`，你只会有一个 `hit` 命令可用：

    > hit
    你想打谁？

现在尝试创建一个新位置，并把剑放到那里。

    > tunnel n = kitchen
    > n
    > drop sword
    > s
    > hit
    命令 'hit' 不可用。也许你是想 ...
    > n
    > hit
    你想打谁？

`hit` 命令只有在你持有或与剑处于同一房间时才可用。

### 你需要持有剑！

```{sidebar} 锁定

Evennia 锁定是一个在 `lockstrings` 中定义的迷你语言。锁定字符串的格式是 `<情况>:<锁定函数>`，其中 `情况` 决定了此锁定何时适用，`锁定函数`（可以有多个）会在特定情况下判断锁定是否通过。
```

让我们提前一步，让 `hit` 命令仅在你 _持有_ 剑时可用。这需要用到一个 [锁定](../../../Components/Locks.md)。我们会在稍后详细讲解锁定，只需要知道它们对于限制你能在物体上做的事情非常有用，包括限制何时可以对其执行命令。

    > py self.search("sword").locks.add("call:holds()")

我们向剑上添加了一个新的锁定。这个 _锁定字符串_ `"call:holds()"` 表示，只有当你 _持有_ 这个物体（即它在你的物品栏中）时，你才能对这个物体执行命令。

为了让锁定生效，你不能是 _超级用户_，因为超级用户会绕过所有锁定。你需要先 `quell` 自己：

```{sidebar} quell/unquell

`quell` 允许你作为开发者扮演权限较低的玩家角色。这样做对于测试和调试非常有用，特别是因为超级用户有时权限过大。使用 `unquell` 可以恢复到正常的身份。
```

    > quell
	
如果剑在地上，尝试以下操作：

    > hit
    命令 'hit' 不可用。..
    > get sword
    > hit
    你想打谁？

在挥舞了剑之后（打了一两只龙），我们将把剑丢掉，以便清除所有 `hit` 命令。我们可以通过两种方式做到这一点：

    delete sword

或者

    py self.search("sword").delete()


## 将命令添加到默认 Cmdset

如我们所见，我们可以使用 `obj.cmdset.add()` 将新的 cmdset 添加到对象上，无论该对象是我们自己（`self`）还是其他对象，比如 `sword`。不过，这种方法有些繁琐。更好的方法是将命令添加到所有角色中。

默认的 cmdset 定义在 `mygame/commands/default_cmdsets.py` 文件中。现在打开该文件：

```python
"""
（模块文档字符串）
"""

from evennia import default_cmds

class CharacterCmdSet(default_cmds.CharacterCmdSet):

    key = "DefaultCharacter"

    def at_cmdset_creation(self):

        super().at_cmdset_creation()
        #
        # 你在下面添加的任何命令都会重载默认命令
        #

class AccountCmdSet(default_cmds.AccountCmdSet):

    key = "DefaultAccount"

    def at_cmdset_creation(self):

        super().at_cmdset_creation()
        #
        # 你在下面添加的任何命令都会重载默认命令
        #

class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):

        super().at_cmdset_creation()
        #
        # 你在下面添加的任何命令都会重载默认命令
        #

class SessionCmdSet(default_cmds.SessionCmdSet):

    key = "DefaultSession"

    def at_cmdset_creation(self):

        super().at_cmdset_creation()
        #
        # 你在下面添加的任何命令都会重载默认命令
        #
```

```{sidebar} super()

`super()` 函数指代当前类的父类，通常用于调用父类中同名的方法。
```

`evennia.default_cmds` 是一个包含所有 Evennia 默认命令和 cmdsets 的容器模块。在这个模块中，我们可以看到已经导入了 `default_cmds`，然后为每个 cmdset 创建了一个新的子类。每个类看起来都很熟悉（除了 `key`，它主要用来方便在列表中识别该 cmdset）。在每个 `at_cmdset_creation` 方法中，我们只是调用 `super().at_cmdset_creation()`，这意味着我们调用父类中的 `at_cmdset_creation()` 方法。

这就是为什么所有新创建的角色都会有这个 cmdset。当你添加了更多命令后，只需重新加载，所有角色就会看到这些命令。

- 角色（即游戏世界中的“你”）使用 `CharacterCmdSet`。
- 账户（表示你在服务器上的角色）使用 `AccountCmdSet`。
- 会话（表示一个客户端连接）使用 `SessionCmdSet`。
- 在登录前（连接屏幕时）会话使用 `UnloggedinCmdSet`。

现在，让我们将我们自己的 `hit` 和 `echo` 命令添加到 `CharacterCmdSet`：

```python
# ...

from commands import mycommands

class CharacterCmdSet(default_cmds.CharacterCmdSet):

    key = "DefaultCharacter"

    def at_cmdset_creation(self):

        super().at_cmdset_creation()
        #
        # 你在下面添加的任何命令都会重载默认命令
        #
        self.add(mycommands.CmdEcho)
        self.add(mycommands.CmdHit)

```

    > reload
    > hit
    你想打谁？

现在你的新命令已经可以在所有玩家角色中使用了。如果你想一次性添加一堆命令，也可以将你自己的 _CmdSet_ 添加到其他 cmdset 中。

```python
from commands import mycommands

class CharacterCmdSet(default_cmds.CharacterCmdSet):

    key = "DefaultCharacter"

    def at_cmdset_creation(self):

        super().at_cmdset_creation()
        #
        # 你在下面添加的任何命令都会重载默认命令
        #
        self.add(mycommands.MyCmdSet)
```

你使用哪种方式取决于你想要多少控制，但如果你已经有了一个 CmdSet，这种方式更方便。一个命令可以是任何多个 CmdSet 的一部分。

## 移除命令

如果你想删除自己添加的自定义命令，当然只需删除你在 `mygame/commands/default_cmdsets.py` 中做的修改。但如果你想删除一个默认命令呢？

我们已经知道，我们可以使用 `cmdset.remove()` 来移除一个 cmdset。事实上，你也可以在 `at_cmdset_creation` 中做到这一点。例如，我们想删除默认的 `get` 命令。如果你查看 `default_cmds.CharacterCmdSet` 父类的实现，你会发现它的类是 `default_cmds.CmdGet`（它的“真实”位置是 `evennia.commands.default.general.CmdGet`）。

```python
# ...
from commands import mycommands

class CharacterCmdSet(default_cmds.CharacterCmdSet):

    key = "DefaultCharacter"

    def at_cmdset_creation(self):

        super().at_cmdset_creation()
        #
        # 你在下面添加的任何命令都会重载默认命令
        #
        self.add(mycommands.MyCmdSet)
        self.remove(default_cmds.CmdGet)
# ...
```

    > reload
    > get
    命令“get”不可用...

## 替换默认命令

到此为止，你已经掌握了所有替换命令的步骤！我们只需要添加一个新的命令，并确保它与默认命令的 `key` 一致。

让我们结合我们对类的了解，以及如何覆盖父类的方法。打开 `mygame/commands/mycommands.py` 文件，创建一个新的 `get` 命令：

```{code-block} python
:linenos:
:emphasize-lines: 2,7,8,9

# 在顶部，导入其他模块
from evennia import default_cmds

# 在下面某处
class MyCmdGet(default_cmds.CmdGet):

    def func(self):
        super().func()
        self.caller.msg(str(self.caller.location.contents))
```

- **第 2 行**：我们导入了 `default_cmds`，以便获取父类。
我们创建了一个新的类，并让它继承 `default_cmds.CmdGet`。我们不需要设置 `.key` 或 `.parse`，这些已经由父类处理了。
在 `func` 中，我们调用了 `super().func()` 以让父类执行它的正常操作。
- **第 7 行**：通过添加我们自己的 `func` 方法，我们替换了父类中的方法。
- **第 8 行**：对于这个简单的修改，我们仍然希望命令像以前一样工作，因此我们使用 `super()` 调用了父类的 `func` 方法。
- **第 9 行**：`.location` 是一个对象所在的位置，`.contents` 包含了该对象的内容。比如，如果你尝试 `py self.contents`，你会得到一个与你的背包相同的列表。而对于房间，`contents` 是该房间中所有物品的列表。
因此，`self.caller.location.contents` 获取了当前地点的所有物品。这是一个列表。为了使用 `.msg` 将其发送给我们，我们将列表转化为字符串。Python 有一个特殊的 `str()` 函数可以做到这一点。

现在我们只需要确保它替换默认的 `get` 命令。再次打开 `mygame/commands/default_cmdsets.py` 文件：

```python
# ...
from commands import mycommands

class CharacterCmdSet(default_cmds.CharacterCmdSet):

    key = "DefaultCharacter"

    def at_cmdset_creation(self):

        super().at_cmdset_creation()
        #
        # 你在下面添加的任何命令都会重载默认命令
        #
        self.add(mycommands.MyCmdSet)
        self.add(mycommands.MyCmdGet)
# ...
```

我们不需要先使用 `self.remove()`，只要添加一个与默认 `get` 命令相同 `key` 的新命令，就会替换掉默认的 `get` 命令。

```{sidebar} 另一种方式

除了在 `default_cmdset.py` 中显式添加 `MyCmdGet`，你还可以将它添加到 `mycommands.MyCmdSet` 中，让它在这里自动添加。
```

    > reload
    > get
    获取什么？
    [smaug, fluffy, YourName, ...]

我们刚刚创建了一个新的 `get` 命令，它会告诉我们所有可以捡起的物品（当然，我们不能捡起自己，所以还有改进的空间...）。

## 总结

在本节中，我们介绍了一些更高级的字符串格式化技巧——这些技巧将对你未来的工作大有帮助！我们还做了一个功能完备的剑。最后，我们学习了如何向我们自己添加、扩展和替换默认命令。了解如何添加命令是制作游戏的一个重要部分！

我们已经把可怜的 Smaug 打了太久。接下来我们将创建更多的东西来玩！
