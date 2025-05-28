# 解析命令参数的理论与最佳实践

本教程将详细讲解多种解析命令参数的方法。在 [添加命令](Beginner-Tutorial/Part1/Beginner-Tutorial-Adding-Commands.md) 后的第一步通常是解析其参数。虽然有很多方法可以做到这一点，但有些确实比其他方法更好，本教程将尝试介绍它们。

如果你是 Python 新手，本教程可能对你帮助很大。如果你已经熟悉 Python 语法，这个教程仍然可能包含有用的信息。在标准库中，仍然有很多内容会让人感到惊讶，尽管它们早就在那。

在本教程中，我们将：

- 解析带有数字的参数。
- 解析带有分隔符的参数。
- 了解可选参数。
- 解析包含对象名称的参数。

## 什么是命令参数？

在本教程中，我将多次讨论命令参数和解析内容。因此，在进一步讨论之前，我们先确认一下术语：

> 命令是一个处理特定用户输入的 Evennia 对象。

例如，默认的 `look` 就是一个命令。在你创建了 Evennia 游戏并连接后，你应该能够输入 `look` 来查看周围情况。在这个上下文中，`look` 是一个命令。

> 命令参数是传递在命令后面的附加文本。

以相同的例子为例，你可以输入 `look self` 来查看自己。在这个上下文中，`self` 是在 `look` 后面指定的文本。`" self"` 是 `look` 命令的参数。

作为游戏开发者的一部分任务是将用户输入（主要是命令）与游戏中的动作连接起来。而且大多数时候，仅输入命令是不够的，我们必须依靠参数来更精确地指定动作。

以 `say` 命令为例。如果不能通过命令参数指定要说的内容（例如 `say hello!`），那么在游戏中进行沟通将会很困难。游戏玩家需要为每种单词或句子创建不同的命令，这显然不切实际。

最后，我们来看看解析是什么？

> 在我们的案例中，解析是将命令参数转换为我们可以使用的内容的过程。

我们通常不会直接使用命令参数（它只是一个类型为 `str` 的文本）。我们需要提取有用的信息。我们可能想要询问用户一个数字，或者另一个在同一房间中的角色的名称。接下来我们将看看如何做到这一点。

## 字符串处理

在对象术语中，当你在 Evennia 中编写命令（当你编写 Python 类时），参数存储在 `args` 属性中。这就是说，在你的 `func` 方法中，你可以通过 `self.args` 访问命令参数。

### self.args

首先，看看这个示例：

```python
class CmdTest(Command):

    """
    测试命令。

    语法：
      test [argument]

    在 test 后输入任何参数。
    """

    key = "test"

    def func(self):
        self.msg(f"You have entered: {self.args}.")
```

如果你添加这个命令并进行测试，你将得到你输入的内容而没有进行任何解析：

```
> test Whatever
You have entered:  Whatever.
> test
You have entered: .
```

> 以 `>` 开头的行表示你在客户端中输入的内容。其他行是你从游戏服务器收到的内容。

注意这里有两个要点：

1. 命令关键字（在这里是 "test"）与命令参数之间的左侧空格没有被移除。这就是为什么在输出的第二行中有两个空格。如果你尝试输入 "testok" 会更明显。
2. 即使你没有输入命令参数，该命令仍然会调用，并且 `self.args` 将为空字符串。

可能对我们的代码稍作修改是合适的，以查看发生了什么。我们将强制 Python 使用一个小技巧来显示命令参数的调试字符串。

```python
class CmdTest(Command):

    """
    测试命令。

    语法：
      test [argument]

    在 test 后输入任何参数。
    """

    key = "test"

    def func(self):
        self.msg(f"You have entered: {self.args!r}.")
```

我们唯一更改的行是最后一行，我们在大括号之间添加了 `!r`，以告诉 Python 打印参数的调试版本（repr 版本）。让我们看看结果：

```
> test Whatever
You have entered: ' Whatever'.
> test
You have entered: ''.
> test And something with '?
You have entered: " And something with '?".
```

这以一种在 Python 解释器中可见的方式显示字符串。它可能更容易阅读……无论如何，有助于调试。

我如此强调这一点是因为它至关重要：命令参数仅仅是字符串（类型为 `str`），我们将使用它来解析。你所看到的内容大多数不是特定于 Evennia 的，而是特定于 Python 的，可以在你有相同需求的任何其他项目中使用。

### 去除空格

正如你所看到的，我们的命令参数带有空格。命令与参数之间的空格通常并不重要。

> 为空格存在的原因是什么？

Evennia 会尽力找到匹配的命令。如果用户在输入命令关键字时带上参数（但省略了空格），Evennia 仍然可以找到并调用该命令。你可能已经看到用户如果输入了 `testok` 会发生什么。在这种情况下，`testok` 很可能是一个命令（Evennia 会检查），但没有找到。因此，因为存在 `test` 命令，Evennia 调用它，参数为 `"ok"`。

但大多数情况下，我们并不关心这个左侧的空格，因此你会看到经常有代码去移除它。在 Python 中有不同的方法可以做到这一点，但对于命令的用法，`strip` 方法在 `str` 上及其相关方法 `lstrip` 和 `rstrip` 很有用。

- `strip`: 从字符串的两端删除一个或多个字符（空格或其他字符）。
- `lstrip`: 仅从字符串的左端移除（左侧剔除）。
- `rstrip`: 仅从字符串的右端移除（右侧剔除）。

这里有一些 Python 示例来帮助理解：

```python
>>> '   this is '.strip() # 默认情况下移除空格
'this is'
>>> "   What if I'm right?   ".lstrip() # 从左侧剔除空格
"What if I'm right?   "
>>> 'Looks good to me...'.strip('.') # 移除 '.'
'Looks good to me'
>>> '"Now, what is it?"'.strip('"?') # 移除 '"' 和 '?' 从两端
'Now, what is it'
```

通常情况下，由于我们不需要空格分隔符，但仍然希望我们的命令在没有分隔符的情况下仍能正常工作，因此我们会对命令参数调用 `lstrip`：

```python
class CmdTest(Command):

    """
    测试命令。

    语法：
      test [argument]

    在 test 后输入任何参数。
    """

    key = "test"

    def parse(self):
        """解析参数，仅去除空格。"""
        self.args = self.args.lstrip()

    def func(self):
        self.msg(f"You have entered: {self.args!r}.")
```

> 我们现在开始重写命令的 `parse` 方法，这通常仅用于参数解析。该方法在 `func` 之前执行，因此 `func()` 中的 `self.args` 将包含我们的 `self.args.lstrip()`。

让我们试试：

```
> test Whatever
You have entered: 'Whatever'.
> test
You have entered: ''.
> test And something with '?
You have entered: "And something with '?".
> test     And something with lots of spaces
You have entered: 'And something with lots of spaces'.
```

字符串末尾的空格被保留，但开头的空格被移除：

> `strip`、`lstrip` 和 `rstrip`（没有参数）将删除空格、换行符和其他常见分隔符。你可以指定一个或多个字符作为参数。如果你指定多个字符，它们都将从原始字符串中剔除。

### 将参数转换为数字

正如前面指出的，`self.args` 是一个字符串（类型为 `str`）。如果我们希望用户输入一个数字怎么办？

让我们以一个非常简单的例子为例：创建一个命令 `roll`，允许玩家掷一个六面骰子。玩家必须猜测数字并作为参数指定。要获胜，玩家必须与骰子结果匹配。我们来看一个示例：

```
> roll 3
You roll a die.  It lands on the number 4.
You played 3, you have lost.
> dice 1
You roll a die.  It lands on the number 2.
You played 1, you have lost.
> dice 1
You roll a die.  It lands on the number 1.
You played 1, you have won!
```

如果这是你的第一个命令，这是一个尝试编写它的好机会。一个具有简单且有限作用的命令通常是一个很好的起始选择。下面是我们可能会如何（首先）编写它……但我提醒你，它不会正常工作：

```python
from random import randint

from evennia import Command

class CmdRoll(Command):

    """
    随机游戏，输入一个数字并试试运气。

    使用：
      roll <number>

    输入一个有效的数字作为参数。将掷骰，只有在你指定了正确数字时你才能胜利。

    示例：
      roll 3

    """

    key = "roll"

    def parse(self):
        """将参数转换为数字。"""
        self.args = self.args.lstrip()

    def func(self):
        # 掷一个随机骰子
        figure = randint(1, 6) # 返回一个伪随机数，范围在1到6之间，包括两端
        self.msg(f"You roll a die.  It lands on the number {figure}.")

        if self.args == figure: # 这会出错！
            self.msg(f"You played {self.args}, you have won!")
        else:
            self.msg(f"You played {self.args}, you have lost.")
```

如果你尝试这段代码，Python 会抱怨你试图将数字与字符串进行比较：`figure` 是一个数字，而 `self.args` 是一个字符串，不能直接进行比较。Python 不会像某些语言那样进行“隐式转换”。顺便说一句，这有时可能会令人恼火，而其他时候你会非常高兴它始终鼓励你明确而非隐式地处理事情。这在程序员中一直是一个争论话题。让我们继续！

因此，我们需要将命令参数从 `str` 转换为 `int`。有几种方法可以做到这一点。但正确的方法是尝试转换并处理 Python 异常 `ValueError`。

在 Python 中，将 `str` 转换为 `int` 非常简单：只需使用 `int` 函数，给它字符串，它会返回一个整数（如果可以的话）。如果不能，它将引发 `ValueError`。因此，我们需要捕获这个异常。然而，我们还必须向 Evennia 指明，如果数字无效，则不应进行进一步的解析。以下是我们对命令的新尝试，进行了转换：

```python
from random import randint

from evennia import Command, InterruptCommand

class CmdRoll(Command):

    """
    随机游戏，输入一个数字并试试运气。

    使用：
      roll <number>

    输入一个有效的数字作为参数。将掷骰，只有在你指定了正确数字时你才能胜利。

    示例：
      roll 3

    """

    key = "roll"

    def parse(self):
        """尽可能将参数转换为数字。"""
        args = self.args.lstrip()

        # 尝试转换为整数
        # 如果不行，引发 InterruptCommand。Evennia 会捕获这个异常并不调用 'func' 方法。
        try:
            self.entered = int(args)
        except ValueError:
            self.msg(f"{args} is not a valid number.")
            raise InterruptCommand

    def func(self):
        # 掷一个随机骰子
        figure = randint(1, 6) # 返回一个伪随机数，范围在1到6之间，包括两端
        self.msg(f"You roll a die.  It lands on the number {figure}.")

        if self.entered == figure:
            self.msg(f"You played {self.entered}, you have won!")
        else:
            self.msg(f"You played {self.entered}, you have lost.")
```

在享受结果之前，让我们仔细看看 `parse` 方法：它尝试将输入的参数从 `str` 转换为 `int`。这可能会失败（如果用户输入 `roll something`）。在这种情况下，Python 会引发 `ValueError` 异常。我们在 `try/except` 块中捕获它，向用户发送消息，并引发 `InterruptCommand` 异常，以告诉 Evennia 不运行 `func()`，因为我们没有有效的数字可以提供给它。

在 `func` 方法中，我们不再使用 `self.args`，而是使用我们在 `parse` 方法中定义的 `self.entered`。你可以预期，如果执行了 `func()`，那么 `self.entered` 会包含一个有效的数字。

如果你尝试这个命令，它应该如预期那样工作：数字会被正确转换，并与骰子结果进行比较。你可能会花一些时间玩这个游戏。太好玩了！

我们还可能想要处理一些事情：在我们的简单示例中，我们只希望用户输入一个介于 1 到 6 的正数。用户可以输入 `roll 0`、`roll -8` 或 `roll 208`，游戏仍然能正常工作。值得关注。再次，你可以写一个条件来处理，但由于我们捕获一个异常，通过分组来做到这一点，可能会更干净：

```python
from random import randint

from evennia import Command, InterruptCommand

class CmdRoll(Command):

    """
    随机游戏，输入一个数字并试试运气。

    使用：
      roll <number>

    输入一个有效的数字作为参数。将掷骰，只有在你指定了正确数字时你才能胜利。

    示例：
      roll 3

    """

    key = "roll"

    def parse(self):
        """尽可能将参数转换为数字。"""
        args = self.args.lstrip()

        # 尝试转换为整数
        try:
            self.entered = int(args)
            if not 1 <= self.entered <= 6:
                # self.entered 不在1到6之间（包括两端）
                raise ValueError
        except ValueError:
            self.msg(f"{args} is not a valid number.")
            raise InterruptCommand

    def func(self):
        # 掷一个随机骰子
        figure = randint(1, 6) # 返回一个伪随机数，范围在1到6之间，包括两端
        self.msg(f"You roll a die.  It lands on the number {figure}.")

        if self.entered == figure:
            self.msg(f"You played {self.entered}, you have won!")
        else:
            self.msg(f"You played {self.entered}, you have lost.")
```

像这样使用分组异常使我们的代码更易读，但如果你觉得在之后检查用户输入的数字是否在正确范围内会更令人满意，也可以在后续条件中执行。

> 请注意，我们只在这最后一次尝试中更新了 `parse` 方法，而没有修改 `func()` 方法，后者保持不变。这是将参数解析与命令处理分离的一个目标，这两项操作最好是隔离开的。

### 处理多个参数

通常，一个命令期望多个参数。到目前为止，在我们的 "roll" 命令示例中，我们只期望一个参数：一个数字，仅此而已。如果我们希望用户指定几个数字怎么办？首先是掷骰的数量，然后是猜测的数字？

> 如果你掷 5 个骰子，你不会经常赢，但这是示例的目的。

因此，我们希望将命令解释为：

```
> roll 3 12
```

（意思是：滚动 3 个骰子，我的猜测是总和为 12。）

我们需要将命令参数，该参数是一个 `str`，通过空格分开（我们使用空格作为分隔符）。Python 提供了 `str.split` 方法，我们将使用它。以下是一些来自 Python 解释器的示例：

```python
>>> args = "3 12"
>>> args.split(" ")
['3', '12']
>>> args = "a command with several arguments"
>>> args.split(" ")
['a', 'command', 'with', 'several', 'arguments']
```

正如你所看到的，`str.split` 将我们的字符串“转换”为字符串列表。指定的参数（在我们这种情况下为 `"`）用作分隔符。因此 Python 遍历我们的原始字符串。当它看到分隔符时，它会将分隔符之前的内容取出并附加到列表中。

这里的关键是 `str.split` 将被用来分割我们的参数。但是，正如你从上述输出所见，我们不能确定此时返回列表的长度：

```python
>>> args = "something"
>>> args.split(" ")
['something']
>>> args = ""
>>> args.split(" ")
['']
```

我们可以使用条件来检查拆分参数的数量，但 Python 提供了一种更好的方法，即利用其异常机制。我们将给 `str.split` 传递第二个参数，即最大拆分次数。让我们看看一个示例，这个功能可能在第一眼看上去会让人困惑：

```python
>>> args = "that is something great"
>>> args.split(" ", 1) # 一次拆分，返回一个包含两个元素的列表（前后）
['that', 'is something great']
```

请多次阅读此示例，直到了解其含义。我们传递给 `str.split` 的第二个参数并不是应该返回的列表长度，而是我们要拆分的次数。因此，我们在这里指定了 1，但我们得到的列表包含两个元素（分隔符之前的内容，分隔符之后的内容）。

> 如果 Python 无法按我们要求的次数拆分，会发生什么？

它不会：

```python
>>> args = "whatever"
>>> args.split(" ", 1) # 这里甚至没有空格 ...
['whatever']
```

这是我希望获得异常却没有得到的时刻。不过，还有另一种方式可以在出错时引发异常：变量解包。

我们在此将不深入讨论该特性。这样做会变得复杂。但代码使用起来非常简单。让我们以滚动命令为例，但添加一个第一个参数：要滚动的骰子数量。

```python
from random import randint

from evennia import Command, InterruptCommand

class CmdRoll(Command):

    """
    随机游戏，输入一个数字并试试运气。

    输入两个用空格分开的数字。第一个数字是
    要投掷的骰子的数量（1、2、3），第二个是预期的总和。

    使用：
      roll <dice> <number>

    例如，要掷两个 6 面骰子，输入 2 作为第一个参数。
    如果你认为这两个骰子之和将为 10，则可以输入：

        roll 2 10
    """

    key = "roll"

    def parse(self):
        """拆分参数并转换。"""
        args = self.args.lstrip()

        # 拆分：我们期望两个用空格分开的参数
        try:
            number, guess = args.split(" ", 1)
        except ValueError:
            self.msg("Invalid usage.  Enter two numbers separated by a space.")
            raise InterruptCommand

        # 转换输入的数字（第一个参数）
        try:
            self.number = int(number)
            if self.number <= 0:
                raise ValueError
        except ValueError:
            self.msg(f"{number} is not a valid number of dice.")
            raise InterruptCommand

        # 转换输入的猜测（第二个参数）
        try:
            self.guess = int(guess)
            if not 1 <= self.guess <= self.number * 6:
                raise ValueError
        except ValueError:
            self.msg(f"{self.guess} is not a valid guess.")
            raise InterruptCommand

    def func(self):
        # 扔出 X 次随机骰子（X 由 self.number 确定）
        figure = 0
        for _ in range(self.number):
            figure += randint(1, 6)

        self.msg(f"You roll {self.number} dice and obtain the sum {figure}.")

        if self.guess == figure:
            self.msg(f"You played {self.guess}, you have won!")
        else:
            self.msg(f"You played {self.guess}, you have lost.")
```

`parse()` 方法的开始部分是我们最感兴趣的：

```python
try:
    number, guess = args.split(" ", 1)
except ValueError:
    self.msg("Invalid usage.  Enter two numbers separated by a space.")
    raise InterruptCommand
```

我们使用 `str.split` 拆分参数，但将结果捕获到两个变量中。Python 足够聪明，可以知道我们想要在第一个变量中获取分隔符之前的内容，在第二个变量中获取分隔符之后的内容。如果字符串中甚至没有空格，Python 将引发 `ValueError` 异常。

这段代码比浏览 `str.split` 返回的字符串简单得多。我们可以像之前那样转换两个变量。实际上，这个版本与之前的版本没有太多变化，主要是出于清晰性而改名。

> 使用最大拆分的字符串是一种常见情况，可用于解析命令参数。你还可以看到 `str.rsplit` 方法，它执行相同的操作，但从字符串的右侧开始。因此，它将试图在字符串末尾找到分隔符并向开头移动。

我们使用空格作为分隔符。这是绝对不必要的。你可能还记得，Most default Evennia commands 可能将 `=` 符号作为分隔符。现在你知道如何解析它们：

```python
>>> cmd_key = "tel"
>>> cmd_args = "book = chest"
>>> left, right = cmd_args.split("=") # 可能会引发 ValueError!
>>> left
'book '
>>> right
' chest'
```

### 可选参数

有时，你会遇到具有可选参数的命令。这些参数并不是必要的，但如果需要更多信息，则可以设置。我不会在这里提供整个命令代码，只提供足够的代码来展示 Python 中的机制：

我们再用 `str.split`，知道我们可能根本没有分隔符。例如，玩家可以输入 "tel" 命令，如下所示：

```
> tel book
> tell book = chest
```

等号是可选的，后面指定的内容也是可选的。在我们的 `parse` 方法中的可能解决方案是：

```python
def parse(self):
    args = self.args.lstrip()

    # = 是可选的
    try:
        obj, destination = args.split("=", 1)
    except ValueError:
        obj = args
        destination = None
```

此代码将放置在 `obj` 中用户输入的所有内容，如果她没有指定任何等号。否则，等号之前的内容将放入 `obj`，等号之后的内容将放入 `destination`。这使得对之后的测试更快，更强健的代码，减少了过于简单且易于破坏代码的条件。

> 同样，在这里我们指定了最大拆分数。如果用户输入：

```
> tel book = chest = chair
```

那么 `destination` 将包含 `" chest = chair"`。这通常是所需的，但由你决定设置参数解析的方式。

## Evennia 搜索

在对一些 `str` 方法进行快速了解之后，我们将查看一些你在标准 Python 中找不到的 Evennia 特定功能。

一个非常常见的任务是将 `str` 转换为一个 Evennia 对象。拿之前的例子来说，拥有 `"book"` 这个字符串是很好的，但我们想知道用户在说什么……这个 `"book"` 是什么？

要从字符串中获取对象，我们执行 Evennia 搜索。Evennia 在所有类型类对象上提供了一个 `search` 方法（你最有可能使用角色或账户的搜索）。该方法支持非常广泛的参数，并且有 [自己的教程](Beginner-Tutorial/Part1/Beginner-Tutorial-Searching-Things.md)。以下是一些有用情况的示例：

### 局部搜索

当一个账户或角色输入命令时，账户或角色在 `caller` 属性中可以找到。因此，`self.caller` 将包含一个账户或角色（或者如果这是一个会话命令，则包含会话，但这种情况并不常见）。`search` 方法将在此可用。

让我们以我们的 "tel" 命令为例。用户可以将一个对象指定为参数：

```python
def parse(self):
    name = self.args.lstrip()
```

然后，我们需要“转换”这个字符串为一个 Evennia 对象。Evennia 对象将在调用者的位置和内容中默认搜索（也就是说，如果命令是由一个角色输入，它将在角色的房间和角色的背包中搜索对象）。

```python
def parse(self):
    name = self.args.lstrip()

    self.obj = self.caller.search(name)
```

我们在这里只指定一个参数给 `search` 方法：要搜索的字符串。如果 Evennia 找到匹配，将返回它并将其保存在 `obj` 属性中。如果没有找到任何东西，它将返回 `None`，因此我们需要对此进行检查：

```python
def parse(self):
    name = self.args.lstrip()

    self.obj = self.caller.search(name)
    if self.obj is None:
        # 已发送了适当的错误消息给调用者
        raise InterruptCommand
```

就是这样。在此条件后，你知道 `self.obj` 中的任何内容都是一个有效的 Evennia 对象（另一个角色、一个对象、一个出口……）。

### 安静搜索

默认情况下，当在搜索中发现多个匹配时，Evennia 会处理这种情况。系统将要求用户缩小范围并重新输入命令。然而，你可以要求返回匹配的列表并自行处理该列表：

```python
def parse(self):
    name = self.args.lstrip()

    objs = self.caller.search(name, quiet=True)
    if not objs:
        # 这是一个空列表，没有匹配
        self.msg(f"No {name!r} was found.")
        raise InterruptCommand

    self.obj = objs[0] # 即使有多个，也取第一个匹配项
```

我们为获得列表所做的唯一更改是 `search` 方法中的一个关键字参数：`quiet`。如果设置为 `True`，则忽略错误，始终返回列表，因此我们需要在此基础上进行处理。注意，在这个示例中，`self.obj` 将也包含一个有效的对象，但如果发现多个匹配项，`self.obj` 将包含第一个，即使还有其他匹配项。

### 全局搜索

默认情况下，Evennia 将执行局部搜索，即局限于调用者所在的位置。如果你想执行全局搜索（在整个数据库中搜索），只需将 `global_search` 关键字参数设置为 `True`：

```python
def parse(self):
    name = self.args.lstrip()
    self.obj = self.caller.search(name, global_search=True)
```

## 结论

解析命令参数对于大多数游戏设计师来说至关重要。如果你设计“智能”命令，用户应该能够猜到如何使用它们，而无需阅读帮助，或者仅需快速浏览提供的帮助。好的命令对用户是直观的。更好的命令会做用户所要求的事情。对于在 MUDs 上工作的游戏设计师来说，命令是用户进入游戏的主要入口。这绝非小事。如果命令能够正确执行（如果它们的参数被解析，且不会以意外方式行为并准确报告错误），你将拥有更快乐的玩家，他们可能会在你的游戏上停留更长时间。我希望这个教程能够为你提供一些改进命令解析的建议。当然，还有其他方式，你可能会发现，或者你已经在代码中使用。
