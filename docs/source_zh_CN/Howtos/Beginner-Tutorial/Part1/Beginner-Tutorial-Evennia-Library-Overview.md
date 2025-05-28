# Evennia 库概述

```{sidebar} API

API 代表 `应用程序编程接口`，是描述如何访问程序或库资源的接口。
```
有几种很好的方法可以探索 Evennia 库。
- 本文档包含 [Evennia-API 文档](../../../Evennia-API.md)，这些文档是从源码自动生成的。尝试点击一些条目——一旦深入，你会看到每个组件的完整描述及其文档。你也可以点击 `[source]` 查看每个内容的完整 Python 源代码。
- 如果你想要更详细的解释，可以查看 [每个组件的独立文档页面](../../../Components/Components-Overview.md)。
- 你可以浏览 [GitHub 上的 Evennia 仓库](https://github.com/evennia/evennia)。这就是你可以从我们这里下载的内容。
- 最后，你可以将 Evennia 仓库克隆到自己的电脑上并阅读源码。如果你想 *真正* 理解发生了什么，或者帮助 Evennia 的开发，这是必要的。请参阅 [扩展安装说明](../../../Setup/Installation-Git.md) 以了解如何操作。

## 它在哪里？

如果安装了 Evennia，你可以通过以下方式简单地导入它：

```python
import evennia
from evennia import some_module
from evennia.some_module.other_module import SomeClass
```

等等。

如果你是通过 `pip install` 安装的 Evennia，库文件夹将被安装在你的 Python 安装目录深处；你最好 [在 GitHub 上查看它](github:evennia)。如果你是克隆的，你应该有一个 `evennia` 文件夹可以查看。

你会发现这是最外层的结构：

```
evennia/
    bin/
    CHANGELOG.md
    ...
    ...
    docs/
    evennia/
```

这个外层是用于 Evennia 的安装和包分发。内部文件夹 `evennia/evennia/` 是 _实际的_ 库，即 API 自动文档所涵盖的内容，也是你执行 `import evennia` 时得到的内容。

> `evennia/docs/` 文件夹包含本文档的源文件。查看 [贡献文档](../../../Contributing-Docs.md) 以了解更多关于其工作原理的信息。

这是 Evennia 库的结构：

- evennia
  - [`__init__.py`](../../../Evennia-API.md#shortcuts) - Evennia 的“扁平 API”位于此处。
  - [`settings_default.py`](../../../Setup/Settings.md#settings-file) - Evennia 的根设置。从这里复制设置到 `mygame/server/settings.py` 文件。
  - [`commands/`](../../../Components/Commands.md) - 命令解析器和处理器。
    - `default/` - [默认命令](../../../Components/Default-Commands.md)和命令集。
  - [`comms/`](../../../Components/Channels.md) - 游戏内通信系统。
  - `contrib/` - 太过于游戏特定的可选插件，不适合 Evennia 核心。
  - `game_template/` - 使用 `evennia --init` 时复制为“游戏目录”。
  - [`help/`](../../../Components/Help-System.md) - 处理帮助条目的存储和创建。
  - `locale/` - 语言文件 ([i18n](../../../Concepts/Internationalization.md))。
  - [`locks/`](../../../Components/Locks.md) - 用于限制游戏内实体访问的锁系统。
  - [`objects/`](../../../Components/Objects.md) - 游戏内实体（所有类型的物品和角色）。
  - [`prototypes/`](../../../Components/Prototypes.md) - 对象原型/生成系统和 OLC 菜单。
  - [`accounts/`](../../../Components/Accounts.md) - 游戏外由会话控制的实体（账户、机器人等）。
  - [`scripts/`](../../../Components/Scripts.md) - 游戏外实体对应于对象，也支持计时器。
  - [`server/`](../../../Components/Portal-And-Server.md) - 核心服务器代码和会话处理。
    - `portal/` - 门户代理和连接协议。
  - [`typeclasses/`](../../../Components/Typeclasses.md) - 类型类存储和数据库系统的抽象类。
  - [`utils/`](../../../Components/Coding-Utils.md) - 各种杂项有用的编码资源。
  - [`web/`](../../../Concepts/Web-Features.md) - 网络资源和网络服务器。初始化时部分复制到游戏目录。

```{sidebar} __init__.py

`__init__.py` 文件是一个特殊的 Python 文件名，用于表示一个 Python '包'。当你单独导入 `evennia` 时，你导入的是这个文件。当你执行 `evennia.foo` 时，Python 会首先在 `__init__.py` 中查找属性 `.foo`，然后在同一位置查找具有该名称的模块或文件夹。
```

虽然所有实际的 Evennia 代码都位于各个文件夹中，但 `__init__.py` 代表整个包 `evennia`。它包含了指向实际位于其他地方的代码的“快捷方式”。如果你在 Evennia-API 页面上 [向下滚动一点](../../../Evennia-API.md)，大多数这些快捷方式都列在那里。

## 探索库的一个示例

在 [上一课](./Beginner-Tutorial-Python-classes-and-objects.md#on-classes-and-objects) 中，我们简要查看了 `mygame/typeclasses/objects` 作为 Python 模块的一个示例。让我们再打开它。

```python
"""
模块文档字符串
"""
from evennia import DefaultObject

class Object(DefaultObject):
    """
    类文档字符串
    """
    pass
```

我们有 `Object` 类，它继承自 `DefaultObject`。模块顶部附近有这一行：

```python
from evennia import DefaultObject
```

我们想弄清楚这个 DefaultObject 提供了什么。由于这是直接从 `evennia` 导入的，我们实际上是从 `evennia/__init__.py` 导入的。

[查看 `evennia/__init__.py` 的第 160 行](github:evennia/__init__.py#L160)，你会发现这一行：

```python
from .objects.objects import DefaultObject
```

```{sidebar} 相对和绝对导入

`from .objects.objects ...` 中的第一个句点表示我们从当前位置导入。这称为 `相对导入`。相比之下，`from evennia.objects.objects` 是 `绝对导入`。在这个特定情况下，两者会得到相同的结果。
```

> 你也可以查看 [API 首页的右侧部分](../../../Evennia-API.md#typeclasses) 并通过这种方式点击查看代码。

`DefaultObject` 被导入到 `__init__.py` 这里，这使得即使类的代码实际上不在这里，也可以通过 `from evennia import DefaultObject` 导入它。

因此，要找到 `DefaultObject` 的代码，我们需要查看 `evennia/objects/objects.py`。以下是在文档中查找的方法：

1. 打开 [API 首页](../../../Evennia-API.md)
2. 找到并点击 [evennia.objects.objects](../../../api/evennia.objects.objects.md) 的链接。
3. 你现在进入了 Python 模块。向下滚动（或在你的网页浏览器中搜索）以找到 `DefaultObject` 类。
4. 你现在可以阅读它的功能和方法。如果想查看完整源代码，点击旁边的 \[source\] 链接。

## 结论

这是一个重要的课程。它教你如何自己寻找信息。知道如何跟随类继承树并导航到你需要的东西是学习像 Evennia 这样的新库的重要部分。

接下来，我们将开始利用迄今为止学到的知识，并将其与 Evennia 提供的构建块结合起来。
