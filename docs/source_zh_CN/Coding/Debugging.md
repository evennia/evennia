# 调试

有时候，错误并不容易解决。简单的 `print` 语句不足以找到问题的原因。回溯信息可能不够详细，甚至不存在。

此时，运行一个 *调试器* 会非常有帮助，并节省大量时间。调试意味着在一个特殊的 *调试器* 程序控制下运行 Evennia。这允许你在给定点停止执行，查看当前状态，并逐步执行程序以了解其逻辑。

Evennia 原生支持以下调试器：

- [Pdb](https://docs.python.org/2/library/pdb.html) 是 Python 发行版的一部分，开箱即用。
- [PuDB](https://pypi.org/project/pudb/) 是一个第三方调试器，具有比 pdb 更“图形化”的基于 curses 的用户界面。可以通过 `pip install pudb` 安装。

## 调试 Evennia

要使用调试器运行 Evennia，请按照以下步骤操作：

1. 找到你希望深入了解的代码位置。在该位置添加以下行：
    ```python
    from evennia import set_trace; set_trace()
    ```
2. 以交互（前台）模式（重新）启动 Evennia，使用 `evennia istart`。这很重要——没有这一步，调试器将无法正确启动——它将在这个交互终端中启动。
3. 执行将触发你添加 `set_trace()` 调用的行的步骤。调试器将在从中交互启动 Evennia 的终端中启动。

`evennia.set_trace` 函数接受以下参数：

```python
evennia.set_trace(debugger='auto', term_size=(140, 40))
```

其中，`debugger` 可以是 `pdb`、`pudb` 或 `auto`。如果是 `auto`，则在可用时使用 `pudb`，否则使用 `pdb`。`term_size` 元组仅设置 `pudb` 的视口大小（`pdb` 会忽略它）。

## 使用 pdb 的简单示例

调试器在不同情况下都很有用，但首先，我们来看看它在命令中的工作方式。添加以下测试命令（其中包含一些故意的错误），并将其添加到你的默认 cmdset 中。然后以交互模式重新启动 Evennia，使用 `evennia istart`。

```python
# 在文件 commands/command.py 中

class CmdTest(Command):
    """
    一个测试命令，仅用于测试 pdb。

    用法：
        test
    """

    key = "test"

    def func(self):
        from evennia import set_trace; set_trace()   # <--- 调试器开始
        obj = self.search(self.args)
        self.msg("You've found {}.".format(obj.get_display_name()))
```

如果你在游戏中输入 `test`，一切都会冻结。你不会从游戏中得到任何反馈，也无法输入任何命令（其他人也不能）。这是因为调试器已在你的控制台中启动，你会在这里找到它。以下是使用 `pdb` 的示例。

```
...
> .../mygame/commands/command.py(79)func()
-> obj = self.search(self.args)
(Pdb)
```

`pdb` 会记录它停止执行的位置，以及即将执行的行（在我们的例子中是 `obj = self.search(self.args)`），并询问你想要做什么。

### 列出周围的代码行

当你看到 `pdb` 提示符 `(Pdb)` 时，你可以输入不同的命令来探索代码。你应该知道的第一个命令是 `list`（你可以简写为 `l`）：

```
(Pdb) l
 43
 44         key = "test"
 45
 46         def func(self):
 47             from evennia import set_trace; set_trace()   # <--- 调试器开始
 48  ->         obj = self.search(self.args)
 49             self.msg("You've found {}.".format(obj.get_display_name()))
 50
 51     # -------------------------------------------------------------
 52     #
 53     # 默认命令继承自
(Pdb)
```

好吧，这没有做任何特别的事情，但当你对 `pdb` 更加熟悉并发现自己在许多不同的文件中时，有时你需要查看周围的代码。注意，在即将执行的行前有一个小箭头（`->`）。

这很重要：**即将**执行，而不是**刚刚**执行。你需要告诉 `pdb` 继续（我们很快会看到如何操作）。

### 检查变量

`pdb` 允许你检查变量（实际上，可以运行任何 Python 指令）。在特定行查看变量的值非常有用。要查看变量，只需输入其名称（就像在 Python 解释器中一样）：

```
(Pdb) self
<commands.command.CmdTest object at 0x045A0990>
(Pdb) self.args
u''
(Pdb) self.caller
<Character: XXX>
(Pdb)
```

如果你尝试查看变量 `obj`，你会得到一个错误：

```
(Pdb) obj
*** NameError: name 'obj' is not defined
(Pdb)
```

这很正常，因为此时我们还没有创建该变量。

> 以这种方式检查变量非常强大。你甚至可以运行 Python 代码并继续执行，这有助于检查你的修复是否确实有效。如果你有与 `pdb` 命令冲突的变量名（比如 `list` 变量），你可以在变量前加上 `!`，以告诉 `pdb` 后面的是 Python 代码。

### 执行当前行

是时候让 `pdb` 执行当前行了。为此，使用 `next` 命令。你可以简写为 `n`：

```
(Pdb) n
AttributeError: "'CmdTest' object has no attribute 'search'"
> .../mygame/commands/command.py(79)func()
-> obj = self.search(self.args)
(Pdb)
```

`Pdb` 抱怨你尝试在命令上调用 `search` 方法，而命令上没有 `search` 方法。执行命令的角色在 `self.caller` 中，所以我们可以更改我们的行：

```python
obj = self.caller.search(self.args)
```

### 让程序运行

`pdb` 正在等待执行相同的指令……它引发了一个错误，但准备再试一次，以防万一。我们在理论上已经修复了它，但我们需要重新加载，所以我们需要输入一个命令。要告诉 `pdb` 终止并继续运行程序，请使用 `continue`（或 `c`）命令：

```
(Pdb) c
...
```

你会看到一个错误被捕获，这是我们已经修复的错误……或者希望已经修复。让我们重新加载游戏并再次尝试。你需要再次运行 `evennia istart`，然后运行 `test` 以再次进入命令。

```
> .../mygame/commands/command.py(79)func()
-> obj = self.caller.search(self.args)
(Pdb)
```

`pdb` 即将再次运行该行。

```
(Pdb) n
> .../mygame/commands/command.py(80)func()
-> self.msg("You've found {}.".format(obj.get_display_name()))
(Pdb)
```

这次该行运行没有错误。让我们看看 `obj` 变量中有什么：

```
(Pdb) obj
(Pdb) print obj
None
(Pdb)
```

我们输入了没有参数的 `test` 命令，因此在搜索中找不到对象（`self.args` 是一个空字符串）。

让我们继续执行命令并尝试使用对象名称作为参数（尽管我们也应该修复该错误，这样会更好）：

```
(Pdb) c
...
```

注意这次游戏中会有一个错误。让我们尝试使用有效的参数。我在这个房间里有另一个角色，`barkeep`：

```
test barkeep
```

再一次，命令冻结，调试器在控制台中打开。

让我们立即执行这一行：

```
> .../mygame/commands/command.py(79)func()
-> obj = self.caller.search(self.args)
(Pdb) n
> .../mygame/commands/command.py(80)func()
-> self.msg("You've found {}.".format(obj.get_display_name()))
(Pdb) obj
<Character: barkeep>
(Pdb)
```

至少这次我们找到了对象。让我们继续……

```
(Pdb) n
TypeError: 'get_display_name() takes exactly 2 arguments (1 given)'
> .../mygame/commands/command.py(80)func()
-> self.msg("You've found {}.".format(obj.get_display_name()))
(Pdb)
```

作为练习，修复此错误，重新加载并再次运行调试器。没有什么比一些实验更好的了！

你的调试通常会遵循相同的策略：

1. 收到你不理解的错误。
2. 在错误发生**之前**放置一个断点。
3. 运行 `evennia istart`
4. 再次运行代码并查看调试器打开。
5. 一行一行地运行程序，检查变量，检查指令的逻辑。
6. 继续并再次尝试，每一步都更接近真相和工作特性。

## pdb/pudb 命令速查表

PuDB 和 Pdb 共享相同的命令。唯一的真正区别是它的呈现方式。由于 `pudb` 直接在其用户界面中显示代码，因此不太需要 `look` 命令。

| Pdb/PuDB 命令 | 功能 |
| ----------- | ---------- |
| list (或 l) | 列出执行点周围的行（对于 `pudb` 不需要，它会直接显示）。 |
| print (或 p) | 显示一个或多个变量。 |
| `!` | 运行 Python 代码（使用 `!` 通常是可选的）。 |
| continue (或 c) | 继续执行并终止本次调试器。 |
| next (或 n) | 执行当前行并转到下一行。 |
| step (或 s) | 进入一个函数或方法以检查它。 |
| `<RETURN>` | 重复最后一个命令（不要重复输入 `n`，只需输入一次，然后按 `<RETURN>` 以重复）。 |

如果你想了解更多关于使用 Pdb 进行调试的信息，你会在[这里找到一个有趣的教程](https://pymotw.com/3/pdb/)。
