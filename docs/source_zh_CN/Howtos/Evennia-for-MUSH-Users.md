# Evennia 给 MUSH 用户

*本页面改编自为 MUSH 社区发布的文章，原文见 [musoapbox.net](https://musoapbox.net/topic/1150/evennia-for-mushers)。*

[MUSH](https://en.wikipedia.org/wiki/MUSH) 是一种文本多人游戏，传统上用于以角色扮演为重点的游戏风格。它们通常（但不总是）利用游戏大师和人工监督来代替代码自动化。MUSH 通常建立在 TinyMUSH 系列的游戏服务器上，如 PennMUSH、TinyMUSH、TinyMUX 和 RhostMUSH。它们的兄弟 [MUCK](https://en.wikipedia.org/wiki/TinyMUCK) 和 [MOO](https://en.wikipedia.org/wiki/MOO) 也经常与 MUSH 一起提及，因为它们都继承自相同的 [TinyMUD](https://en.wikipedia.org/wiki/MUD_trees#TinyMUD_family_tree) 基础。一个主要特征是能够通过自定义脚本语言在游戏内修改和编程游戏世界。我们将在此将这种在线脚本称为 *软代码*。

Evennia 的工作方式与 MUSH 在整体设计和底层机制上有很大不同。虽然可以实现相同的功能，但方式不同。如果您来自 MUSH 世界，请记住以下一些基本差异。

## 开发者 vs 玩家

在 MUSH 中，用户倾向于使用软代码从内部编码和扩展游戏的各个方面。因此，可以说 MUSH 完全由具有不同访问级别的 *玩家* 管理。而 Evennia 则区分了 *玩家* 和 *开发者* 的角色。

- Evennia 的 *开发者* 在游戏外使用 Python 工作，这在 MUSH 中被视为“硬代码”。开发者实现大规模的代码更改，并可以从根本上改变游戏的工作方式。然后，他们将更改加载到正在运行的 Evennia 服务器中。这样的更改通常不会断开任何已连接的玩家。
- Evennia 的 *玩家* 从游戏内部操作。一些员工级玩家可能会兼任开发者。根据访问级别，玩家可以通过挖掘新房间、创建新对象、别名命令、定制他们的体验等方式修改和扩展游戏世界。信任的员工可以通过 `@py` 命令访问 Python，但这对普通玩家来说是一个安全风险。因此，*玩家* 通常通过使用 *开发者* 为他们准备的工具来操作——这些工具可以根据开发者的意图变得非常严格或灵活。

## 在游戏中协作 - Python vs 软代码

对于 *玩家* 来说，在游戏中协作在 MUSH 和 Evennia 之间不必有太大不同。游戏世界的构建和描述仍然可以主要在游戏中通过构建命令、使用文本标签和 [内联函数](../Components/FuncParser.md) 来美化和定制体验。Evennia 提供了外部构建世界的方法，但这些是可选的。原则上，也没有什么能阻止开发者为玩家提供类似软代码的语言，如果认为有必要的话。

对于游戏的 *开发者* 来说，差异更大：代码主要是在游戏外的 Python 模块中编写，而不是在游戏内的命令行上。Python 是一种非常流行且支持良好的语言，拥有大量文档和帮助。Python 标准库也是一个很大的帮助，不必重新发明轮子。但话虽如此，虽然 Python 被认为是最容易学习和使用的语言之一，但它无疑与 MUSH 的软代码非常不同。

虽然软代码允许在游戏中协作，但 Evennia 的外部编码反而打开了使用专业版本控制工具和错误跟踪的可能性，可以使用像 GitHub（或 Bitbucket 提供的免费私人仓库）这样的网站。源代码可以在合适的文本编辑器和 IDE 中编写，具有重构、语法高亮和所有其他便利。简而言之，Evennia 游戏的协作开发与世界上大多数专业协作开发的方式相同，这意味着可以使用所有最好的工具。

## `@parent` vs `@typeclass` 和 `@spawn`

Python 中的继承与软代码中的继承不同。Evennia 没有“主对象”概念，其他对象从中继承。实际上，根本没有理由在游戏世界中引入“虚拟对象”——代码和数据彼此分离。

在 Python 中（这是一种 [面向对象](https://en.wikipedia.org/wiki/Object-oriented_programming) 的语言），创建的是 *类*——这些类就像蓝图，可以从中生成任意数量的 *对象实例*。Evennia 还添加了一个额外的功能，即每个实例在数据库中都是持久的（这意味着不需要 SQL）。举个例子，Evennia 中的一个独特角色是类 `Character` 的实例。

MUSH 的 `@parent` 命令的一个平行可能是 Evennia 的 `@typeclass` 命令，该命令更改一个已存在对象的实例所属的类。这样，您可以直接将一个 `Character` 变成一个 `Flowerpot`。

如果您是面向对象设计的新手，重要的是要注意一个类的所有对象实例不必完全相同。如果它们相同，所有角色将具有相同的名称。Evennia 允许以多种不同方式自定义单个对象。一个方法是通过 *属性*，它是可以链接到任何对象的数据库绑定属性。例如，您可以有一个 `Orc` 类，定义了一个兽人应该能够做的所有事情（可能反过来继承自所有怪物共享的某个 `Monster` 类）。在不同实例上设置不同的属性（不同的力量、装备、外观等）会使每个兽人独特，尽管它们都共享相同的类。

`@spawn` 命令允许方便地选择不同的属性“集合”来放置在每个新兽人上（如“战士”集合或“萨满”集合）。这样的集合甚至可以相互继承，这至少在某种程度上与 MUSH 的 `@parent` 和基于对象的继承的 *效果* 相似。

当然，还有其他差异，但这应该能让您感受到一些不同。理论讲够了，接下来让我们进入更实际的事项。要安装，请参见 [入门说明](../Setup/Installation.md)。

## 迈出让事情更熟悉的第一步

我们将在这里给出两个示例，以便让 Evennia 对 MUSH *玩家* 更加熟悉。

### 激活多描述器

默认情况下，Evennia 的 `desc` 命令更新您的描述，仅此而已。然而，在 `evennia/contrib/multidesc.py` 中有一个功能更丰富的可选“多描述器”。这种替代方案允许管理和组合大量的键描述。

要激活多描述器，请 `cd` 到您的游戏文件夹并进入 `commands` 子文件夹。在那里您会找到文件 `default_cmdsets.py`。在 Python 术语中，所有 `*.py` 文件都称为 *模块*。在文本编辑器中打开该模块。我们在这里不会进一步讨论 Evennia 游戏内的 *命令* 和 *命令集*，但可以说 Evennia 允许您根据情况随时更改玩家可用的命令（或命令版本）。

在模块中添加两行新代码，如下所示：

```python
# 文件 mygame/commands/default_cmdsets.py
# [...] 

from evennia.contrib import multidescer   # <- 现在添加

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    CharacterCmdSet 包含游戏内角色对象上可用的通用游戏内命令，如 look、get 等。
    当一个账户控制一个角色时，它会与 AccountCmdSet 合并。
    """
    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        填充命令集
        """
        super().at_cmdset_creation()
        #
        # 您在下面添加的任何命令都将覆盖默认命令。
        #
        self.add(multidescer.CmdMultiDesc())      # <- 现在添加 
# [...]
```

请注意，Python 对缩进很敏感，因此请确保使用与上面显示的相同数量的空格进行缩进！

那么，上面发生了什么？我们在顶部 [导入模块](https://www.linuxtopia.org/online_books/programming_books/python_programming/python_ch28s03.html) `evennia/contrib/multidescer.py`。导入后，我们可以使用句点（`.`）访问该模块中的内容。多描述器被定义为类 `CmdMultiDesc`（我们可以通过在文本编辑器中打开该模块来发现这一点）。在底部，我们创建了该类的新实例，并将其添加到 `CharacterCmdSet` 类中。就本教程而言，我们只需要知道 `CharacterCmdSet` 包含所有默认情况下应该对 `Character` 可用的命令。

整个过程将在命令集首次创建时触发，这发生在服务器启动时。因此，我们需要使用 `@reload` 重新加载 Evennia——这样做不会断开任何人的连接。如果一切顺利，您现在应该能够使用 `desc`（或 `+desc`）并发现您有更多的可能性：

```text
> help +desc                  # 获取命令帮助
> +desc eyes = 他的眼睛是蓝色的。
> +desc basic = 一个大个子。
> +desc/set basic + + eyes    # 我们在中间添加了一个额外的空格
> look me
一个大个子。他的眼睛是蓝色的。
```

如果出现错误，服务器日志中会显示 *回溯*——几行文本显示错误发生的位置。通过定位与 `default_cmdsets.py` 文件相关的行号来找到错误的位置（这是您迄今为止唯一更改的文件）。很可能您拼写错误或遗漏了缩进。修复它，然后再次 `@reload` 或根据需要运行 `evennia start`。

### 自定义多描述器语法

如上所见，多描述器使用这样的语法（其中 `|/` 是 Evennia 的换行标签）：

```text
> +desc/set basic + |/|/ + cape + footwear + |/|/ + attitude 
``` 

这种 `+` 的使用是由编写此 `+desc` 命令的 *开发者* 规定的。如果 *玩家* 不喜欢这种语法呢？玩家需要烦扰开发者来更改它吗？不一定。虽然 Evennia 不允许玩家在命令行上构建自己的多描述器，但它确实允许 *重新映射* 命令语法为他们喜欢的语法。这是通过使用 `nick` 命令完成的。

以下是一个更改如何输入上述命令的 nick：

```text
> nick setdesc $1 $2 $3 $4 = +desc/set $1 + |/|/ + $2 + $3 + |/|/ + $4
```

左侧的字符串将与您的输入匹配，如果匹配，它将被右侧的字符串替换。`$` 类型的标签将存储空格分隔的参数并将其放入替换中。nick 允许 [shell-like 通配符](http://www.linfo.org/wildcard.html)，因此您可以使用 `*`、`?`、`[...]`、`[!... ]` 等来匹配输入的部分。

现在可以将之前的描述设置为：

```text
> setdesc basic cape footwear attitude 
```

通过 `nick` 功能，玩家即使在开发者没有更改底层 Python 代码的情况下，也可以缓解许多语法不满。

## 下一步

如果您是 *开发者* 并有兴趣制作一个更像 MUSH 的 Evennia 游戏，一个好的开始是查看 Evennia [第一个 MUSH-like 游戏的教程](./Tutorial-for-basic-MUSH-like-game.md)。这一步步地从头开始构建一个简单的小游戏，并帮助您熟悉 Evennia 的各个角落。还有一个 [运行角色扮演会话的教程](./Evennia-for-roleplaying-sessions.md)，可能会引起您的兴趣。

让 *玩家* 更加熟悉的一个重要方面是添加新命令和调整现有命令。如何做到这一点在 [添加新命令的教程](Adding-Commands) 中进行了介绍。您可能还会发现浏览 `evennia/contrib/` 文件夹很有用。[教程世界](Beginner-Tutorial/Part1/Beginner-Tutorial-Tutorial-World.md) 是一个小型单人任务，您可以尝试（它不是很像 MUSH，但它确实展示了许多 Evennia 概念的实际应用）。除此之外，还有 [更多教程](./Howtos-Overview.md) 可以尝试。如果您希望获得更直观的概览，您还可以查看 [Evennia in pictures](https://evennia.blogspot.se/2016/05/evennia-in-pictures.html)。

……当然，如果您需要进一步的帮助，您可以随时进入 [Evennia 聊天室](https://webchat.freenode.net/?channels=evennia&uio=MT1mYWxzZSY5PXRydWUmMTE9MTk1JjEyPXRydWUbb) 或在我们的 [论坛/邮件列表](https://groups.google.com/forum/#%21forum/evennia) 上发布问题！
