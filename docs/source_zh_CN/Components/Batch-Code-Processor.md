# 批量代码处理器

有关批量处理器的介绍和动机，请参见 [此处](./Batch-Processors.md)。本页面描述了批量-*代码* 处理器。批量-*命令* 处理器涵盖 [此处](./Batch-Command-Processor.md)。

批量代码处理器是一个超级用户专用功能，通过以下命令调用：

```
> batchcode path.to.batchcodefile
```

其中 `path.to.batchcodefile` 是指向 *批量代码文件* 的路径。这样的文件应以 "`.py`" 结尾（但您不应在路径中包含该扩展名）。路径是相对于您定义用于保存批量文件的文件夹的 Python 路径，由 `BATCH_IMPORT_PATH` 在您的设置中设置。默认文件夹是（假设您的游戏称为 "mygame"）`mygame/world/`。因此，如果要运行位于 `mygame/world/batch_code.py` 中的示例批量文件，您可以简单使用：

```
> batchcode batch_code
```

这将尝试一次性运行整个批量文件。为了更逐步的、*交互式* 控制，您可以使用 `/interactive` 开关。开关 `/debug` 将使处理器进入 *调试* 模式。有关更多信息，请参见下面的描述。

## 批量文件

批量代码文件是一个普通的 Python 文件。不同之处在于，批量处理器加载并执行该文件，而不是导入它，因此您可以可靠地更新文件，然后重复调用它，查看您的更改而无需 `reload` 服务器。这使得测试变得简单。在批量代码文件中，您还可以访问以下全局变量：

- `caller` - 是运行批处理器的对象的引用。
- `DEBUG` - 这是一个布尔值，允许您确定该文件当前是否在调试模式下运行。看看下面如何使用这点将非常有用。

通过处理器运行普通的 Python 文件将从头到尾执行该文件。如果您想要更多的执行控制，可以使用处理器的 *交互式* 模式。此模式会单独运行某些代码块，仅在您满意之前反复运行该部分。要做到这一点，您需要在文件中添加特殊标记以将其划分为较小的块。这些标记采用注释的形式，因此文件仍然是有效的 Python。

- `#CODE` 作为行首的内容标记一个 *代码* 块的开始。该块将持续到下一个标记或文件结束。代码块包含功能性的 Python 代码。每个 `#CODE` 块将与文件的其他部分完全隔离地运行，因此请确保其是自包含的。
- `#HEADER` 作为行首的内容标记一个 *头部* 块的开始。它持续到下一个标记或文件结束。此块用于保存您将需要的其他所有块的导入和变量。在每个 `#CODE` 块的顶部，始终会插入在头部块中定义的所有 Python 代码。您可以拥有多个 `#HEADER` 块，但这相当于拥有一个大型块。请注意，您无法在代码块之间交换数据，因此在一个代码块中编辑头部变量不会影响其他代码块中的该变量！
- `#INSERT path.to.file` 将在该位置插入另一个批量代码（Python）文件。一个不以 `#HEADER`、`#CODE` 或 `#INSERT` 指令开头的 `#` 被视为注释。
- 在块内，正常的 Python 语法规则适用。出于缩进的考虑，每个块充当一个单独的 Python 模块。

以下是位于 `evennia/contrib/tutorial_examples/` 中找到的示例文件的一个版本。

```python
#
# 这是 Evennia 的一个示例批处理构建文件。
#

#HEADER

# 这将在所有其他 #CODE 块中包含

from evennia import create_object, search_object
from evennia.contrib.tutorial_examples import red_button
from typeclasses.objects import Object

limbo = search_object('Limbo')[0]


#CODE 

red_button = create_object(red_button.RedButton, key="Red button", 
                           location=limbo, aliases=["button"])

# caller 指向运行脚本的对象
caller.msg("A red button was created.")

# 从另一个批量代码文件导入更多代码
#INSERT batch_code_insert

#CODE

table = create_object(Object, key="Blue Table", location=limbo)
chair = create_object(Object, key="Blue Chair", location=limbo)

string = f"A {table} and {chair} were created."
if DEBUG:
    table.delete()
    chair.delete()
    string += " Since debug was active, they were deleted again." 
caller.msg(string)
```

这使用 Evennia 的 Python API 顺序创建三个对象。

## 调试模式

尝试运行示例脚本：

```
> batchcode/debug tutorial_examples.example_batch_code
```

批处理脚本将运行到结束并告诉您完成。您也会收到按钮和两个家具被创建的消息。四处看看，您应该会看到按钮在那里。但是您不会看到任何椅子或桌子！这是因为我们使用了 `/debug` 开关，这在脚本内部直接显示为 `DEBUG==True`。在上述示例中，我们处理了这种状态，通过再次删除椅子和桌子来处理。

调试模式旨在用于测试批处理脚本。也许您正在查找代码中的错误，或者尝试查看事物是否按预期工作。反复运行脚本将创建越来越多的椅子和桌子，所有对象名称都相同。您必须返回并费力地删除它们。

## 交互模式

交互模式的工作原理与 [批量命令处理器对应部分](./Batch-Command-Processor.md) 非常相似。它允许您更逐步地控制批量文件的执行。这对于调试或选择只运行特定块非常有用。使用 `batchcode` 与 `/interactive` 标志进入交互模式。

```
> batchcode/interactive tutorial_examples.batch_code
```

您应该会看到：

```
01/02: red_button = create_object(red_button.RedButton, [...]         (hh for help) 
```

这表明您处于第一个 `#CODE` 块中，这是该批处理文件中仅有的两个命令中的第一个。请注意，该块 *尚未* 实际执行！

要查看您即将运行的完整代码片段，请使用 `ll`（批处理处理器版的 `look`）。

```python
from evennia.utils import create, search
from evennia.contrib.tutorial_examples import red_button
from typeclasses.objects import Object

limbo = search.objects(caller, 'Limbo', global_search=True)[0]

red_button = create.create_object(red_button.RedButton, key="Red button", 
                                  location=limbo, aliases=["button"])

# caller 指向运行脚本的对象
caller.msg("A red button was created.")
```

将其与之前给出的示例代码进行比较。请注意，`#HEADER` 的内容已被添加到 `#CODE` 块的顶部。使用 `pp` 确实执行这个块（这将创建按钮并给您消息）。使用 `nn` （下一个）转到下一个命令。使用 `hh` 获取命令列表。

如果出现追溯，请在批量文件中修复它们，然后使用 `rr` 重新加载文件。您仍将在相同的代码块中，可以根据需要轻松再次运行它。这样形成简单的调试周期。它还允许您重新运行单个问题块——如前所述，在大型批量文件中这非常有用（也不要忘记 `/debug` 模式）。

使用 `nn` 和 `bb`（下一个和向后）逐步浏览文件；例如，`nn 12` 将跳转 12 步向前（而不处理其中的任何块）。在交互模式下，所有正常的 Evennia 命令都应照常工作。

## 限制和注意事项

批量代码处理器是通过 Evennia 建立世界的最灵活方式。然而，您需要记住一些注意事项。

### 安全
或者说缺乏安全性。默认情况下，只有 *超级用户* 被允许运行批量代码处理器。代码处理器 **没有任何 Evennia 安全检查**，并允许全面访问 Python。如果不受信任的一方可以运行代码处理器，他们可能会在您的机器上执行任意 Python 代码，这可能是非常危险的事情。如果您想允许其他用户访问批量代码处理器，您应该确保在您的机器上以单独的、非常有限的访问用户身份运行 Evennia（即在 “监狱” 中）。相比之下，批量命令处理器要安全得多，因为运行它的用户仍然“在”游戏内，实际上无法执行游戏命令外的任何操作。

### 代码块之间没有通信
全局变量在代码批量文件中无法工作，每个块作为独立环境执行。 `#HEADER` 块字面上被粘贴到每个 `#CODE` 块的顶部，因此在您的块中更新某些头部变量，不会使该更改在另一个块中可用。尽管这是 Python 执行的局限性，允许这样做会导致在使用交互模式时出现很难调试的代码——这将是一个经典的 “意大利面条代码” 的例子。

与此主要的实际问题是，当在一段代码块中建立房间，而在当前块中希望连接那个房间时。有两种方法可以做到这一点：

- 对您创建的房间名称进行数据库搜索（因为您无法预先知道它被分配的 dbref）。问题在于名称可能并不唯一（您可能有很多 `A dark forest` 的房间）。但有个简单的方法可以处理此问题——使用 [标签](./Tags.md) 或别名。您可以为任何对象分配任意数量的标签和/或别名。确保其中一个标签或别名对于该房间是唯一的（例如 “room56”），那么您随时都可以唯一地搜索并找到它。
- 使用 `caller` 全局属性作为跨块存储。例如，您可以在 `ndb` 中创建一个房间引用字典：
    ```python
    #HEADER 
    if caller.ndb.all_rooms is None:
        caller.ndb.all_rooms = {}

    #CODE 
    # 创建并存储城堡
    castle = create_object("rooms.Room", key="Castle")
    caller.ndb.all_rooms["castle"] = castle

    #CODE 
    # 在另一个节点中访问城堡
    castle = caller.ndb.all_rooms.get("castle")
    ```
注意我们在 `#HEADER` 中检查 `caller.ndb.all_rooms` 是否已经存在，然后创建字典。请记住，`#HEADER` 会在每个 `#CODE` 块前面逐个复制。如果没有那个 `if` 语句，我们将清空每个块的字典！

### 不要将批量代码文件视为普通 Python 文件

尽管是一个有效的 Python 文件，但批量代码文件 **仅** 应由批量代码处理器运行。您不应在其中定义类型类或命令，或将它们导入到其他代码中。在 Python 中导入模块将执行模块的基本级别，这意味着，在您普通的批量代码文件中，这可能意味着每次创建大量新对象。

### 不要让代码依赖于批量文件的真实文件路径

当导入内容到批量代码文件时，不要使用相对导入，而应始终使用从游戏目录根目录或 Evennia 库开始的路径进行导入。依赖于批量文件“实际”位置的代码将会失败。批量代码文件被作为文本读取，并执行字符串。当代码运行时，它对这些字符串之前属于什么文件没有知识。
