# 制作一个可以坐的椅子

在本课中，我们将利用所学知识创建一个新的游戏对象：一个可以坐的椅子。

我们的目标是：

- 我们想要一个新的“可坐”的对象，特别是一个 `Chair`。
- 我们希望能够使用命令坐在椅子上。
- 一旦我们坐在椅子上，它应该以某种方式影响我们。为了演示这一点，将当前的椅子存储在属性 `is_sitting` 中。其他系统可以检查这一点以以不同的方式影响我们。
- 角色应该能够站起来并离开椅子。
- 当你坐下时，你不应该能够在不先站起来的情况下走到另一个房间。

## 让我们在坐着时无法移动

当你坐在椅子上时，你不能在不先站起来的情况下直接走开。这需要对我们的角色类型类进行更改。打开 `mygame/typeclasses/characters.py`：

```python
# 在 mygame/typeclasses/characters.py 中

# ...

class Character(DefaultCharacter):
    # ...

    def at_pre_move(self, destination, **kwargs):
       """
       Called by self.move_to when trying to move somewhere. If this returns
       False, the move is immediately cancelled.
       """
       if self.db.is_sitting:
           self.msg("You need to stand up first.")
           return False
       return True
```

当移动到某个地方时，会调用 [character.move_to](evennia.objects.objects.DefaultObject.move_to)。这反过来会调用 `character.at_pre_move`。如果返回 `False`，则移动将被中止。

在这里，我们查找一个属性 `is_sitting`（我们将在下面分配）以确定我们是否被困在椅子上。

## 制作椅子本身

接下来，我们需要椅子本身，或者更确切地说，是一个可以坐的“东西”家族，我们称之为 _sittables_。我们不能仅仅使用默认对象，因为我们希望 sittable 包含一些自定义代码。我们需要一个新的自定义类型类。创建一个新模块 `mygame/typeclasses/sittables.py`，内容如下：

```python
# 在 mygame/typeclasses/sittables.py 中

from typeclasses.objects import Object

class Sittable(Object):

    def do_sit(self, sitter):
        """
        Called when trying to sit on/in this object.

        Args:
            sitter (Object): The one trying to sit down.

        """
        current = self.db.sitter
        if current:
            if current == sitter:
                sitter.msg(f"You are already sitting on {self.key}.")
            else:
                sitter.msg(f"You can't sit on {self.key} "
                        f"- {current.key} is already sitting there!")
            return
        self.db.sitter = sitter
        sitter.db.is_sitting = self
        sitter.msg(f"You sit on {self.key}")
```

这段代码处理有人坐在椅子上的逻辑。

- **第 3 行**：我们继承自 `mygame/typeclasses/objects.py` 中的空 `Object` 类。这意味着我们将来可以理论上修改它，并让这些更改也影响 sittables。
- **第 7 行**：`do_sit` 方法期望使用参数 `sitter` 调用，该参数应该是一个 `Object`（最可能是 `Character`）。这是想要坐下来的人。
- **第 15 行**：注意，如果椅子上没有定义 [Attribute](../../../Components/Attributes.md) `sitter`（因为这是第一次有人坐在上面），这将简单地返回 `None`，这很好。
- **第 16-22 行**：我们检查是否已经有人坐在椅子上，并根据是你还是其他人返回适当的错误消息。我们使用 `return` 来中止坐下动作。
- **第 23 行**：如果我们到达这一点，`sitter` 就可以坐下了。我们将他们存储在椅子上的 `sitter` 属性中。
- **第 24 行**：`self.obj` 是此命令附加到的椅子。我们将其存储在 `sitter` 本身的 `is_sitting` 属性中。
- **第 25 行**：最后，我们告诉坐下的人他们可以坐下。

继续：

```python
# 在同一个类中，在 `do_sit` 方法之后添加

    def do_stand(self, stander):
        """
        Called when trying to stand from this object.

        Args:
            stander (Object): The one trying to stand up.

        """
        current = self.db.sitter
        if not stander == current:
            stander.msg(f"You are not sitting on {self.key}.")
        else:
            self.db.sitter = None
            del stander.db.is_sitting
            stander.msg(f"You stand up from {self.key}.")
```

这是坐下的逆操作；我们需要进行一些清理。

- **第 12 行**：如果我们没有坐在椅子上，从椅子上站起来是没有意义的。
- **第 15 行**：如果我们到达这里，我们可以站起来。我们确保取消设置 `sitter` 属性，以便以后其他人可以使用椅子。
- **第 16 行**：角色不再坐着，因此我们删除他们的 `is_sitting` 属性。我们也可以在这里执行 `stander.db.is_sitting = None`，但删除属性感觉更干净。
- **第 17 行**：最后，我们通知他们成功站起来。

可以想象，将来可以让 `sit` 命令（我们还没有创建）检查是否已经有人坐在椅子上。这也可以工作，但让 `Sittable` 类处理谁可以坐在上面的逻辑是有意义的。

我们让类型类处理逻辑，并让它执行所有的返回消息。这使得可以轻松地制作一堆椅子供人们坐。

### 坐在上面还是里面？

坐在椅子上是可以的。但如果我们的 Sittable 是扶手椅呢？

```plaintext
> py evennia.create_object("typeclasses.sittables.Sittable", key="armchair", location=here)
> py self.search("armchair").do_sit(me)
You sit on armchair.
```

这在语法上不正确，你实际上是坐“在”扶手椅里，而不是“在”上面。椅子的类型很重要（英语很奇怪）。我们希望能够控制这一点。

我们_可以_创建一个名为 `SittableIn` 的 `Sittable` 子类来进行此更改，但这感觉过于繁琐。相反，我们将修改我们已有的内容：

```python
# 在 mygame/typeclasses/sittables.py 中

from typeclasses.objects import Object

class Sittable(Object):

    def do_sit(self, sitter):
        """
        Called when trying to sit on/in this object.

        Args:
            sitter (Object): The one trying to sit down.

        """
        preposition = self.db.preposition or "on"
        current = self.db.sitter
        if current:
            if current == sitter:
                sitter.msg(f"You are already sitting {preposition} {self.key}.")
            else:
                sitter.msg(
                    f"You can't sit {preposition} {self.key} "
                    f"- {current.key} is already sitting there!")
            return
        self.db.sitter = sitter
        sitter.db.is_sitting = self
        sitter.msg(f"You sit {preposition} {self.key}")

    def do_stand(self, stander):
        """
        Called when trying to stand from this object.

        Args:
            stander (Object): The one trying to stand up.

        """
        current = self.db.sitter
        if not stander == current:
            stander.msg(f"You are not sitting {self.db.preposition} {self.key}.")
        else:
            self.db.sitter = None
            del stander.db.is_sitting
            stander.msg(f"You stand up from {self.key}.")
```

- **第 15 行**：我们获取 `preposition` 属性。使用 `self.db.preposition or "on"` 意味着如果属性未设置（为 `None`/falsy），则假定默认的 "on" 字符串。这是因为 `or` 关系将返回第一个为真的条件。更明确的写法是使用 [三元运算符](https://www.dataquest.io/blog/python-ternary-operator/) `self.db.preposition if self.db.preposition else "on"`。
- **第 19、22、27、39 和 43 行**：我们使用这个介词来修改我们看到的返回文本。

`reload` 服务器。使用这样的属性的一个优点是可以在游戏中动态修改它们。让我们看看构建者如何使用普通的构建命令（不需要 `py`）：

```plaintext
> set armchair/preposition = in 
```

由于我们还没有添加 `sit` 命令，我们仍然必须使用 `py` 进行测试：

```plaintext
> py self.search("armchair").do_sit(me)
You sit in armchair.
```

### 额外奖励

如果我们希望在某些椅子上坐下时有更多戏剧性的效果怎么办？

```
You sit down and a whoopie cushion makes a loud fart noise!
```

你可以通过调整你的 `Sittable` 类，使返回消息可以通过你创建的对象上设置的 `Attributes` 来替换，从而实现这一点。你想要这样的东西：

```plaintext
> py 
> chair = evennia.create_object("typeclasses.sittables.Sittable", key="pallet", location=here)
> chair.do_sit(me)
You sit down on pallet.
> chair.do_stand(me)
You stand up from pallet.
> chair.db.msg_sitting_down = "You sit down and a whoopie cushion makes a loud fart noise!"
> chair.do_sit(me)
You sit down and a whoopie cushion makes a loud fart noise!
```

也就是说，如果你没有设置属性，你应该得到一个默认值。我们将此实现留给读者。

## 添加命令

正如我们在 [关于添加命令的课程](./Beginner-Tutorial-More-on-Commands.md) 中讨论的那样，有两种主要方式来设计坐下和站起来的命令：
- 你可以将命令存储在椅子上，这样它们只有在房间里有椅子时才可用
- 你可以将命令存储在角色上，这样它们始终可用，并且你必须始终指定要坐在哪个椅子上。

这两种方式都非常有用，所以在本课中我们将尝试两者。

### 命令变体 1：椅子上的命令

这种实现 `sit` 和 `stand` 的方式将新的 cmdsets 放在 Sittable 本身上。正如我们之前所学，房间中的其他人可以使用对象上的命令。这样命令很简单，但增加了 cmdset 管理的复杂性。

如果 `armchair` 在房间里，它可能看起来像这样（额外奖励：更改扶手椅上的坐下消息以匹配此输出，而不是获取默认的 `You sit in armchair`！）：

```plaintext
> sit
As you sit down in armchair, life feels easier.
```

如果房间里还有 sittables `sofa` 和 `barstool` 会发生什么？Evennia 将自动为我们处理这一点，并允许我们指定我们想要哪个：

```plaintext
> sit
More than one match for 'sit' (please narrow target):
 sit-1 (armchair)
 sit-2 (sofa)
 sit-3 (barstool)
> sit-1
As you sit down in armchair, life feels easier.
```

为了保持事情的分离，我们将创建一个新模块 `mygame/commands/sittables.py`：

```{sidebar} 分离命令和类型类？

你可以根据自己的喜好组织这些东西。如果你愿意，可以将坐命令和 cmdset 与 `Sittable` 类型类一起放在 `mygame/typeclasses/sittables.py` 中。这样做的好处是将所有与坐有关的东西放在一个地方。但也有一些组织上的优点，比如将所有命令放在一个地方，如我们在这里所做的。
```

```python
# 在 mygame/commands/sittables.py 中

from evennia import Command, CmdSet

class CmdSit(Command):
    """
    Sit down.
    """
    key = "sit"
    def func(self):
        self.obj.do_sit(self.caller)

class CmdStand(Command):
     """
     Stand up.
     """
     key = "stand"
     def func(self):
         self.obj.do_stand(self.caller)


class CmdSetSit(CmdSet):
    priority = 1
    def at_cmdset_creation(self):
        self.add(CmdSit)
        self.add(CmdStand)
```

如所见，命令几乎是微不足道的。

- **第 11 和 19 行**：`self.obj` 是我们用此命令添加 cmdset 的对象（所以是椅子）。我们只需在该对象上调用 `do_sit/stand` 并传递 `caller`（坐下的人）。`Sittable` 将完成其余工作。
- **第 23 行**：`CmdSetSit` 上的 `priority = 1` 意味着此 cmdset 中的同名命令与角色 cmdset 中的命令合并时优先级略高（角色 cmdset 的优先级为 `0`）。这意味着如果你在角色上有一个 `sit` 命令，并进入一个有椅子的房间，椅子上的 `sit` 命令将优先于我们定义的 `sit`。

我们还需要对我们的 `Sittable` 类型类进行更改。打开 `mygame/typeclasses/sittables.py`：

```python
# 在 mygame/typeclasses/sittables.py 中

from typeclasses.objects import Object
from commands.sittables import CmdSetSit 

class Sittable(Object):
    """
    (docstring)
    """
    def at_object_creation(self):
        self.cmdset.add_default(CmdSetSit)
    # ... 
```

- **第 4 行**：我们必须安装 `CmdSetSit`。
- **第 10 行**：`at_object_creation` 方法只会在对象首次创建时调用一次。
- **第 11 行**：我们将命令集添加为“默认” cmdset，使用 `add_default`。这使其持久化，并保护它不被删除，以防添加其他 cmdset。有关更多信息，请参阅 [Command Sets](../../../Components/Command-Sets.md)。

确保 `reload` 以使代码更改可用。

所有_新_的 Sittables 现在将拥有你的 `sit` 命令。你的现有 `armchair` 不会有，因为 `at_object_creation` 不会为已经存在的对象重新运行。我们可以手动更新它：

```plaintext
> update armchair
```

我们还可以更新所有现有的 sittables（全部在一行上）：

```{sidebar} 列表推导式
`[obj for obj in iterator]` 是一个_列表推导式_的示例。可以将其视为一种高效地在一行中构建新列表的方法。你可以在 [Python 文档](https://docs.python.org/3/tutorial/datastructures.html#list-comprehensions) 中阅读有关列表推导式的更多信息。
```

```plaintext
> py from typeclasses.sittables import Sittable ;
       [sittable.at_object_creation() for sittable in Sittable.objects.all()]
```

我们现在应该能够在房间里有扶手椅时使用 `sit`。

```plaintext
> sit
As you sit down in armchair, life feels easier.
> stand
You stand up from armchair.
```

将 `sit`（或 `stand`）命令“放”在椅子上的一个问题是，当房间里没有 Sittable 对象时，它将不可用：

```plaintext
> sit
Command 'sit' is not available. ...
```

这很实用，但看起来不太好；这使得用户更难知道是否可以执行 `sit` 操作。这里有一个修复此问题的技巧。让我们在 `mygame/commands/sittables.py` 的底部添加_另一个_命令：

```python
# 在 mygame/commands/sittables.py 中的其他命令之后
# ...

class CmdNoSitStand(Command):
    """
    Sit down or Stand up
    """
    key = "sit"
    aliases = ["stand"]

    def func(self):
        if self.cmdname == "sit":
            self.msg("You have nothing to sit on.")
        else:
            self.msg("You are not sitting down.")
```

- **第 9 行**：此命令响应 `sit` 和 `stand`，因为我们将 `stand` 添加到其 `aliases` 列表中。命令别名与命令的 `key` 具有相同的“权重”，两者都同样标识命令。
- **第 12 行**：`Command` 的 `.cmdname` 保存用于调用它的名称。这将是 `"sit"` 或 `"stand"` 中的一个。这导致不同的返回消息。

我们不需要为此创建新的 CmdSet，而是将其添加到默认角色 cmdset 中。打开 `mygame/commands/default_cmdsets.py`：

```python
# 在 mygame/commands/default_cmdsets.py 中

# ...
from commands import sittables

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    (docstring)
    """
    def at_cmdset_creation(self):
        # ...
        self.add(sittables.CmdNoSitStand)
```

像往常一样，确保 `reload` 服务器以识别新代码。

为了测试，我们将在没有舒适扶手椅的新位置构建并前往那里：

```plaintext
> tunnel n = kitchen
north
> sit
You have nothing to sit on.
> south
sit
As you sit down in armchair, life feels easier.
```

我们现在有一个完全功能的 `sit` 动作，它包含在椅子本身中。当没有椅子时，会显示默认错误消息。

这是如何工作的？有两个 cmdsets 在起作用，它们都有一个 `sit/stand` 命令——一个在 `Sittable`（扶手椅）上，另一个在我们身上（通过 `CharacterCmdSet`）。由于我们在椅子的 cmdset 上设置了 `priority=1`（而 `CharacterCmdSet` 的优先级为 `0`），因此不会发生命令冲突：椅子的 `sit` 优先于我们定义的 `sit` ... 直到没有椅子。

所以这处理了 `sit`。那么 `stand` 呢？这将正常工作：

```plaintext
> stand
You stand up from armchair.
> north
> stand
You are not sitting down.
```

不过，我们在 `stand` 上还有一个问题——当你坐着并尝试在有多个 `Sittable` 的房间中 `stand` 时会发生什么：

```plaintext
> stand
More than one match for 'stand' (please narrow target):
 stand-1 (armchair)
 stand-2 (sofa)
 stand-3 (barstool)
```

由于所有 sittables 上都有 `stand` 命令，你会得到一个多重匹配错误。这_有效_... 但你可以选择_任何_这些 sittables 来“站起来”。这真的很奇怪。

对于 `sit`，获得一个选择是可以的——Evennia 无法知道我们打算坐在哪个椅子上。但一旦我们坐下，我们肯定知道我们应该从哪个椅子上站起来！我们必须确保我们只从我们实际坐着的椅子上获取命令。

我们将使用 [Lock](../../../Components/Locks.md) 和自定义 `lock function` 来解决此问题。我们希望在 `stand` 命令上设置一个锁，仅当调用者实际坐在该特定 `stand` 命令附加到的椅子上时才使其可用。

首先，让我们添加锁，以便我们看到我们想要的内容。打开 `mygame/commands/sittables.py`：

```python
# 在 mygame/commands/sittables.py 中

# ...

class CmdStand(Command):
     """
     Stand up.
     """
     key = "stand"
     locks = "cmd:sitsonthis()"

     def func(self):
         self.obj.do_stand(self.caller)
# ...
```

- **第 10 行**：这是锁的定义。它的形式为 `condition:lockfunc`。`cmd:` 类型的锁由 Evennia 检查，以确定用户是否可以访问命令。我们希望锁函数仅在此命令位于调用者坐着的椅子上时返回 `True`。将要检查的是 `sitsonthis` _lock function_，它尚不存在。

打开 `mygame/server/conf/lockfuncs.py` 来添加它！

```python
# mygame/server/conf/lockfuncs.py

"""
(module lockstring)
"""
# ...

def sitsonthis(accessing_obj, accessed_obj, *args, **kwargs):
    """
    True if accessing_obj is sitting on/in the accessed_obj.
    """
    return accessed_obj.obj.db.sitter == accessing_obj

# ...
```

Evennia 知道 `mygame/server/conf/lockfuncs` 中的_所有_函数都应该可以在锁定义中使用。

所有锁函数必须接受相同的参数。这些参数是必需的，Evennia 将根据需要传递所有相关对象。

```{sidebar} Lockfuncs

Evennia 提供了大量默认的 lockfuncs，例如检查权限级别、你是否携带或在访问对象内等。然而，默认 Evennia 中没有“坐”的概念，所以我们需要自己指定。
```

- `accessing_obj` 是尝试访问锁的对象。在本例中是我们。
- `accessed_obj` 是我们尝试获得特定类型访问的实体。由于我们在 `CmdStand` 类上定义锁，因此这是_命令实例_。然而我们对这个不感兴趣，而是对命令分配到的对象（椅子）感兴趣。对象在命令上可用作 `.obj`。所以在这里，`accessed_obj.obj` 是椅子。
- `args` 是一个包含传递给 lockfunc 的任何参数的元组。由于我们使用 `sitsonthis()`，这将是空的（如果我们添加任何内容，它将被忽略）。
- `kwargs` 是一个传递给 lockfuncs 的关键字参数的元组。在我们的示例中，这也将是空的。

确保你 `reload`。

如果你是超级用户，重要的是在尝试此操作之前 `quell` 自己。这是因为超级用户绕过所有锁——它永远不会被锁定，但这也意味着它不会看到这样的锁的效果。

```plaintext
> quell
> stand
You stand up from armchair
```

没有其他 sittables 的 `stand` 命令通过了锁，只有我们实际坐着的那个通过了！这现在是一个完全功能的椅子！

像这样将命令添加到椅子对象是强大的，并且是一种值得了解的好技术。然而，正如我们所见，它确实有一些注意事项。

我们现在将尝试另一种添加 `sit/stand` 命令的方法。

### 命令变体 2：角色上的命令

在开始之前，删除你创建的椅子：

```plaintext
> del armchair 
> del sofa 
> (etc)
```

然后进行以下更改：

- 在 `mygame/typeclasses/sittables.py` 中，注释掉整个 `at_object_creation` 方法。
- 在 `mygame/commands/default_cmdsets.py` 中，注释掉 `self.add(sittables.CmdNoSitStand)` 行。

这禁用了对象上的命令解决方案，以便我们可以尝试另一种方法。确保 `reload` 以便 Evennia 知道更改。

在这个变体中，我们将 `sit` 和 `stand` 命令放在 `Character` 上，而不是椅子上。这使得某些事情变得更容易，但使命令本身更复杂，因为它们将不知道要坐在哪个椅子上。我们不能再简单地执行 `sit`。这就是它的工作方式：

```plaintext
> sit <chair>
You sit on chair.
> stand
You stand up from chair.
```

再次打开 `mygame/commands/sittables.py`。我们将添加一个新的坐命令。由于我们已经有了前一个示例中的 `CmdSit`，我们将类命名为 `CmdSit2`。我们将所有内容放在模块的末尾以保持分离。

```python
# 在 mygame/commands/sittables.py 中

from evennia import Command, CmdSet
from evennia import InterruptCommand

class CmdSit(Command):
    # ...

# ...

# 从这里开始新内容

class CmdSit2(Command):
    """
    Sit down.

    Usage:
        sit <sittable>

    """
    key = "sit"

    def parse(self):
        self.args = self.args.strip()
        if not self.args:
            self.caller.msg("Sit on what?")
            raise InterruptCommand

    def func(self):

        # self.search handles all error messages etc.
        sittable = self.caller.search(self.args)
        if not sittable:
            return
        try:
            sittable.do_sit(self.caller)
        except AttributeError:
            self.caller.msg("You can't sit on that!")
```

```{sidebar} 引发异常

引发异常允许立即中断当前程序流程。当 Python 检测到代码问题时，会自动引发错误异常。它将沿着调用代码的序列（“堆栈”）向上引发，直到它被 `try ... except` 捕获或到达最外层范围，在那里它将被记录或显示。在这种情况下，Evennia 知道捕获 `InterruptCommand` 异常并提前停止命令执行。
```

- **第 4 行**：我们需要 `InterruptCommand` 来能够提前中止命令解析（见下文）。
- **第 27 行**：`parse` 方法在 `Command` 上的 `func` 方法之前运行。如果没有为命令提供参数，我们希望在 `parse` 中提前失败，因此 `func` 永远不会触发。仅仅 `return` 不足以做到这一点，我们需要 `raise InterruptCommand`。Evennia 将看到引发的 `InterruptCommand` 作为应立即中止命令执行的信号。
- **第 32 行**：我们使用解析的命令参数作为目标椅子进行搜索。如在 [搜索教程](./Beginner-Tutorial-Searching-Things.md) 中讨论的那样，`self.caller.search()` 将自行处理错误消息。因此，如果它返回 `None`，我们可以直接 `return`。
- **第 35-38 行**：`try...except` 块“捕获”异常并处理它。在这种情况下，我们尝试在对象上运行 `do_sit`。如果我们找到的对象不是 `Sittable`，它可能没有 `do_sit` 方法，并且会引发 `AttributeError`。我们应该优雅地处理这种情况。

让我们在这里也完成 `stand` 命令。由于命令在椅子之外，我们需要确定我们是否坐着。

```python
# 在 mygame/commands/sittables.py 末尾

class CmdStand2(Command):
    """
    Stand up.

    Usage:
        stand

    """
    key = "stand"

    def func(self):
        caller = self.caller
        # if we are sitting, this should be set on us
        sittable = caller.db.is_sitting
        if not sittable:
            caller.msg("You are not sitting down.")
        else:
            sittable.do_stand(caller)
```

- **第 17 行**：我们不需要第一个版本的这些命令的 `is_sitting` 属性，但现在我们需要它。由于我们有这个，我们不需要搜索并知道我们坐在哪个椅子上。如果我们没有设置这个属性，我们就不会坐在任何地方。
- **第 21 行**：我们使用找到的 sittable 站起来。

现在剩下的就是让 `sit` 和 `stand` 对我们可用。这种类型的命令应该始终对我们可用，因此我们可以将其放在角色的默认 Cmdset 中。打开 `mygame/commands/default_cmdsets.py`。

```python
# 在 mygame/commands/default_cmdsets.py 中

# ...
from commands import sittables

class CharacterCmdSet(CmdSet):
    """
    (docstring)
    """
    def at_cmdset_creation(self):
        # ...
        self.add(sittables.CmdSit2)
        self.add(sittables.CmdStand2)
```

确保 `reload`。

现在让我们试试：

```plaintext
> create/drop sofa : sittables.Sittable
> sit sofa
You sit down on sofa.
> stand
You stand up from sofa.
> north 
> sit sofa 
> You can't find 'sofa'.
```

将命令存储在角色上使它们集中化，但你必须搜索或存储你希望该命令与之交互的任何外部对象。

## 结论

在本课中，我们为自己建造了一把椅子，甚至还有一张沙发！

- 我们修改了 `Character` 类，以避免在坐下时移动。
- 我们创建了一个新的 `Sittable` 类型类。
- 我们尝试了两种方法来允许用户使用 `sit` 和 `stand` 命令与 sittables 交互。

眼尖的读者会注意到，坐在椅子上的 `stand` 命令（变体 1）与坐在角色上的 `sit` 命令（变体 2）可以很好地一起工作。没有什么可以阻止你混合它们，甚至尝试第三种解决方案，以更好地适应你的想法。

这就结束了初学者教程的第一部分！
