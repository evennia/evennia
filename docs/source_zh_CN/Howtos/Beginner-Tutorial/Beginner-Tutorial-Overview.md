# 初学者教程

```{sidebar} 初学者教程部分
- **[介绍](./Beginner-Tutorial-Overview.md)**
<br>准备工作。
- 第 1 部分: [我们的现状](Part1/Beginner-Tutorial-Part1-Overview.md)
<br>Evennia 的介绍以及如何使用工具，包括 Python 的简介。
- 第 2 部分: [我们的目标](Part2/Beginner-Tutorial-Part2-Overview.md)
<br>规划我们的教程游戏以及在规划你自己的游戏时需要考虑的事项。
- 第 3 部分: [我们该如何到达](Part3/Beginner-Tutorial-Part3-Overview.md)
<br>深入扩展 Evennia 以制作你的游戏的实质内容。
- 第 4 部分: [使用我们创建的内容](Part4/Beginner-Tutorial-Part4-Overview.md)
<br>构建一个技术演示和与我们代码相配套的世界内容。
- 第 5 部分: [展示世界](Part5/Beginner-Tutorial-Part5-Overview.md)
<br>将我们的新游戏上线并让玩家尝试。
```

欢迎来到 Evennia！这个多部分的初学者教程将帮助你顺利起步。

你可以选择一些看起来有趣的主题，不过，如果你按照此教程一直到最后，你将创建自己的小型在线游戏，与他人一起玩和分享！

使用右侧菜单导航每个教程部分的索引。使用每页顶部/底部的 [下一步](Part1/Beginner-Tutorial-Part1-Overview.md) 和 [上一步](../Howtos-Overview.md) 链接在课程之间跳转。

## 你需要的东西

- 命令行界面
- MUD 客户端（或网页浏览器）
- 文本编辑器/IDE
- 已安装 Evennia 且已初始化的游戏目录

### 命令行界面

你需要知道如何在你的操作系统中找到终端/控制台。Evennia 服务器可以在游戏中控制，但你 _将_ 需要使用命令行界面来实现许多功能。以下是一些入门链接：

- [不同操作系统的命令行在线简介](https://tutorial.djangogirls.org/en/intro_to_command_line/)

> 请注意，文档中通常使用正斜杠 (`/`) 作为文件系统路径。Windows 用户应该将这些转换为反斜杠 (`\`)。

### 新游戏目录？

你应该确保已成功 [安装 Evennia](../../Setup/Installation.md)。如果你遵循了说明，你应该已经创建了一个游戏目录。文档将继续使用此游戏目录称为 `mygame`，所以你可以选择重复使用它或创建一个只针对本教程的新目录——这取决于你。

如果你已有一个游戏目录，并希望为此教程创建一个新的目录，请使用 `evennia stop` 命令停止正在运行的服务器。然后，在其他地方（_而不是_ 之前的游戏目录内部） [初始化一个新的游戏目录](../../Setup/Installation.md#initialize-a-new-game)。

### MUD 客户端

你可能已经有了自己喜欢的 MUD 客户端。查看 [支持的客户端列表](../../Setup/Client-Support-Grid.md)。或者，如果你不喜欢 telnet，你也可以在你喜欢的浏览器中使用 Evennia 的 Web 客户端。

确保你知道如何连接并登录到本地运行的 Evennia 服务器。

> 在本文件中，我们通常交替使用 'MUD'、'MU' 和 'MU*' 等术语，来代表所有历史上不同形式的基于文本的多人游戏风格（即：MUD、MUX、MUSH、MUCK、MOO 等等）。Evennia 可以用来创建任何这些游戏风格……以及更多！

### 文本编辑器或 IDE

你需要一个文本编辑器应用程序来编辑 Python 源文件。大多数可以编辑和输出原始文本的应用都应该可以使用（……所以不是 Microsoft Word）。

- [这是一个博客文章，概述了各种文本编辑器选项](https://www.elegantthemes.com/blog/resources/best-code-editors) - 这些东西每年变化不大。Python 的热门选择有 PyCharm、VSCode、Atom、Sublime Text 和 Notepad++。Evennia 在很大程度上使用 VIM 编写，但对于初学者来说并不适合。

```{important} 使用空格，而不是制表符< br/>
确保配置你的文本编辑器，使按下 'Tab' 键时插入 _4 个空格_ 而不是制表符字符。由于 Python 是基于空白的，这一简单做法将使你的生活轻松许多。
```

### 在游戏外运行 Python 命令（可选）

本教程将主要假设你通过游戏客户端使用 `py` 命令在游戏中尝试 Python。不过，你也可以在游戏外探索 Python 指令。在你的游戏目录文件夹中运行以下命令：

    $ evennia shell 

```{sidebar}
`evennia shell` 控制台非常方便实验 Python。但请注意，如果你从 `evennia shell` 操作数据库对象，那些更改在重新加载服务器之前在游戏中是不可见的。同样，游戏中的更改在重新启动 `evennia shell` 控制台之前也可能无法显示。作为一个指南，使用 `evennia shell` 来测试各种内容。不要用它来改变正在运行的游戏状态。初学者教程使用游戏内的 `py` 命令以避免混淆。
```
这将打开一个 Evennia/Django 了解的 Python shell。你应该使用这个，而不是仅仅运行普通的 `python`，因为后者不会为你设置 Django，且你无法在没有大量额外设置的情况下导入 `evennia`。为了获得更好的体验，推荐你安装 `ipython` 程序：

     $ pip install ipython3

`evennia shell` 命令会自动使用安装的 `ipython`。 

---

现在你应该准备好继续阅读 [初学者教程的第一部分](Part1/Beginner-Tutorial-Part1-Overview.md)！（将来，请使用页面顶部/底部的 `上一部分 | 下一部分` 按钮继续。）

<details>

<summary>
点击此处查看整个初学者教程的所有部分和课程的完整索引。
</summary>

```{toctree}
Part1/Beginner-Tutorial-Part1-Overview
Part2/Beginner-Tutorial-Part2-Overview
Part3/Beginner-Tutorial-Part3-Overview
Part4/Beginner-Tutorial-Part4-Overview
Part5/Beginner-Tutorial-Part5-Overview
```

</details>
