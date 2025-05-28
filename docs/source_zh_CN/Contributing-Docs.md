# 贡献 Evennia 文档

```{sidebar} 本地构建文档？
你不需要在本地测试/构建文档即可贡献文档 PR。我们会在合并和构建文档时解决任何问题。如果你真的想为自己构建文档，说明在[本文档末尾](#building-the-docs-locally)。
```

- 你可以通过创建一个[文档问题](github:issue)来贡献文档。
- 你可以像对待其他代码一样，通过创建一个 [PR](./Contributing.md) 来贡献文档。文档源文件位于 `evennia/docs/source/`。

文档源文件是 `*.md`（Markdown）文件。Markdown 文件是简单的文本文件，可以用普通的文本编辑器编辑。它们也可以包含原始的 HTML 指令（但这很少需要）。它们使用 [Markdown][commonmark] 语法和 [MyST 扩展][MyST]。

## 源文件结构

源文件被组织成几个大致的类别，只有少数管理文档位于 `evennia/docs/source/` 的根目录。

- `source/Components/` 是描述 Evennia 各个构建模块的文档，即你可以导入和使用的东西。这扩展并详细说明了通过阅读 API 文档本身可以了解到的内容。例如 `Accounts`、`Objects` 和 `Commands` 的文档。
- `source/Concepts/` 描述了 Evennia 的大规模特性如何结合在一起——这些特性不能轻易地分解为一个独立的组件。这可以是关于模型和类型类如何交互的一般描述，或者是消息从客户端到服务器再返回的路径。
- `source/Setup/` 包含有关安装、运行和维护 Evennia 服务器及其相关基础设施的详细文档。
- `source/Coding/` 提供了关于如何与 Evennia 代码库本身交互、使用和导航的帮助。这也有关于一般开发概念和如何设置一个合理的开发环境的非 Evennia 特定的帮助。
- `source/Contribs/` 专门为 `evennia/contribs/` 文件夹中的包提供文档。任何特定于 contrib 的教程将在这里找到，而不是在 `Howtos` 中。
- `source/Howtos/` 包含描述如何在 Evennia 中实现特定目标、效果或结果的文档。这通常是以教程或 FAQ 形式出现，并会引用其余文档以供进一步阅读。
- `source/Howtos/Beginner-Tutorial/` 包含初始教程序列的所有文档。

其他文件和文件夹：
- `source/api/` 包含自动生成的 API 文档作为 `.html` 文件。不要手动编辑这些文件，它们是从源代码自动生成的。
- `source/_templates` 和 `source/_static` 保存文档本身的文件。它们只应在希望更改文档生成的外观和结构时修改。
- `conf.py` 保存 Sphinx 配置。通常不应修改它，除非要在新分支上更新 Evennia 版本。

## 自动生成的文档页面

某些文档页面是自动生成的。对其生成的 Markdown 文件的更改将被覆盖。相反，它们必须在自动化读取文本的地方进行修改。

- `source/api` 下的所有 API 文档都是从 Evennia 核心代码的文档字符串构建的。对此的文档修复需要在相关模块、函数、类或方法的文档字符串中进行。
- [Contribs/Contribs-Overview.md](Contribs/Contribs-Overview.md) 是在构建文档时由脚本 `evennia/docs/pylib/contrib_readmes2docs.py` 完全生成的。
  - 上述页面中的所有 contrib 简介都取自每个 contrib 的 `README.md` 的第一段，位于 `evennia/contrib/*/*/README.md` 下。
  - 类似地，链接自上述页面的所有 contrib 文档都是从每个 contrib 的 `README.md` 文件生成的。
- [Components/Default-Commands.md](Components/Default-Commands.md) 是从 `evennia/commands/default/` 下的命令类生成的。
- [Coding/Evennia-Code-Style.md](Coding/Evennia-Code-Style.md) 是从 `evennia/CODING_STYLE.md` 生成的。
- [Coding/Changelog.md](Coding/Changelog.md) 是从 `evennia/CHANGELOG.md` 生成的。
- [Setup/Settings-Default.md](Setup/Settings-Default.md) 是从默认设置文件 `evennia/default_settings.py` 生成的。

大多数自动生成的页面在标题中都有一个警告，指示它是自动生成的。

## 编辑语法

Evennia 的文档使用的格式是 [Markdown][commonmark-help]（Commonmark）。虽然 Markdown 支持一些替代形式，但为了保持一致性，我们尝试坚持以下形式。

### 斜体/粗体

我们通常使用下划线表示斜体，使用双星号表示粗体：

- `_Italic text_` - _Italic text_
- `**Bold Text**` - **Bold text**

### 标题

我们使用 `#` 来表示章节/标题。`#` 越多，子标题就越多（字体会越来越小）。

- `# Heading`
- `## SubHeading`
- `### SubSubHeading`
- `#### SubSubSubHeading`

> 不要在同一页面中多次使用相同的标题/子标题名称。虽然 Markdown 不会阻止这样做，但这将使得无法唯一地引用该标题。Evennia 文档预处理器会检测到这一点并给出错误。

### 列表

可以创建项目符号列表和编号列表：

```
- first bulletpoint
- second bulletpoint
- third bulletpoint
```

- first bulletpoint
- second bulletpoint
- third bulletpoint

```
1. Numbered point one
2. Numbered point two
3. Numbered point three
```

1. Numbered point one
2. Numbered point two
3. Numbered point three

### 块引用

块引用将创建一个缩进块。它用于强调，通过用 `>` 开始一行或多行来添加。对于“注意”你也可以使用一个显式的 [Note](#note)。

```
> This is an important
> thing to remember.
```

> 注意：这是一个重要的事情要记住。

### 链接

链接语法是 `[linktext](url_or_ref)` - 这将生成一个可点击的链接 [linktext](#links)。

#### 内部链接

大多数链接将指向文档的其他页面或 Evennia 的 API 文档。每个文档标题都可以被引用。引用总是以 `#` 开头。标题名称总是以小写字母表示，并忽略任何非字母字符。标题中的空格用单个破折号 `-` 替代。

例如，假设以下是文件 `Menu-stuff.md` 的内容：

```
# Menu items

Some text...

## A yes/no? example

Some more text...
```

- 从_同一文件内_可以引用每个标题为

      [menus](#menu-items)
      [example](#a-yesno-example)

- 从_另一个文件_中，可以引用它们为

      [menus](Menu-Stuff.md#menu-items)
      [example](Menu-Stuff.md#a-yesno-example)

> 在引用中不包括 `.md` 文件扩展名是可以的。Evennia 文档预处理器会对此进行修正（并在引用中插入任何所需的相对路径）。

#### API 链接

文档包含所有 Evennia 源代码的自动生成文档。你可以通过只给出资源位置的 python 路径来直接引导读者到源代码，方法是以 `evennia.` 前缀开头：

      [DefaultObject](evennia.objects.objects.DefaultObject) <- 就像这样！

[DefaultObject](evennia.objects.objects.DefaultObject)  <- 就像这样！

> 请注意，不能通过这种方式引用 `mygame` 文件夹中的文件。游戏文件夹是动态生成的，不是 API 文档的一部分。最接近的是 `evennia.game_template`，它是用来在 `evennia --init` 时创建游戏目录的。

#### 外部链接

这些是指向文档之外资源的链接。我们还提供了一些方便的快捷方式。

```
[evennia.com](https://evennia.com) - 链接到外部网站。
```

- 使用 `(github:evennia/objects/objects.py)` 作为链接目标，可以指向 Evennia github 页面（主分支）上的某个地方。
- 使用 `(github:issue)` 指向 github 问题创建页面。

 > 请注意，如果你想引用代码，通常最好[链接到 API](#api-links)而不是指向 github。

### URL/引用在一个地方

URL 可能会变长，如果你在许多地方使用相同的 URL/引用，它可能会变得有些混乱。因此，你也可以将 URL 放在文档末尾作为“脚注”。然后可以通过将引用放在方括号 `[ ]` 中来引用它。以下是一个示例：

```
这是一个[可点击的链接][mylink]。这是[另一个链接][1]。

...

[mylink]: http://...
[1]: My-Document.md#this-is-a-long-ref

```

这使得正文稍微简短一些。

### 表格

表格的实现方式如下：

````
| heading1 | heading2 | heading3 |
| --- | --- | --- |
| value1 | value2 | value3 |
|  | value 4 | |
| value 5 | value 6 | |
````

| heading1 | heading2 | heading3 |
| --- | --- | --- |
| value1 | value2 | value3 |
|  | value 4 | |
| value 5 | value 6 | |

如所见，Markdown 语法可以相当随意（列不需要对齐），只要你包含标题分隔符并确保在每行添加正确数量的 `|` 即可。

### 原样文本

通常需要标记某些内容以原样显示——就是按原样显示——不进行任何 Markdown 解析。在运行文本中，这是通过使用反引号（\`）完成的，例如 \`verbatim text\` 变为 `verbatim text`。

如果你想将原样文本放在自己的行上，可以通过简单地缩进 4 个空格来轻松实现（在每侧添加空行以提高可读性）：

```
这是普通文本

    这是原样文本

这是普通文本
```

另一种方法是使用三重反引号：

````
```
这些反引号内的所有内容都将是原样的。

```
````

### 代码块

一个特殊的“原样”情况是代码示例——我们希望它们获得代码高亮以提高可读性。这是通过使用三重反引号并指定我们使用的语言来完成的：

````
```python
from evennia import Command
class CmdEcho(Command):
    """
    Usage: echo <arg>
    """
    key = "echo"
    def func(self):
        self.caller.msg(self.args.strip())
```
````

```python
from evennia import Command
class CmdEcho(Command):
  """
  Usage: echo <arg>
  """
  key = "echo"
  def func(self):
    self.caller.msg(self.args.strip())
```

对于使用 Python 命令行的示例，使用 `python` 语言和 `>>>` 提示符。
````
```python
>>> print("Hello World")
Hello World
```
````

```python
>>> print("Hello World")
Hello World
```

在显示游戏内命令时，使用 `shell` 语言类型和 `>` 作为提示符。缩进来自游戏的返回。

````
```shell
> look at flower
  Red Flower(#34)
  A flower with red petals.
```
````

```shell
> look at flower
  Red Flower(#34)
  A flower with red petals.
```

对于实际的 shell 提示符，你可以使用 `bash` 语言类型或只是缩进行。使用 `$` 作为提示符以显示输入和输出的区别，否则跳过它——对于不太熟悉命令行的用户来说可能会造成混淆。

````
```bash
$ ls
evennia/ mygame/
```
    evennia start --log
````

```bash
$ ls
evennia/ mygame/
```

    evennia start --log

### MyST 指令

Markdown 易于阅读和使用。但尽管它可以满足我们的大部分需求，但在某些方面它不够表达。为此，我们使用扩展的 [MyST][MyST] 语法。这是以以下形式：

````
```{directive} any_options_here

content

```
````

#### 注意

这种类型的注意可能比使用 `> Note: ...` 更突出。

````
```{note}

这是一些值得注意的内容，跨越多行以显示内容的缩进方式。
此外，重要/警告注意事项也会这样缩进。

```
````

```{note}

这是一些值得注意的内容，跨越多行以显示内容的缩进方式。
此外，重要/警告注意事项也会这样缩进。

```

#### 重要

这用于特别重要和显眼的注意事项。

````
```{important}
  这很重要，因为它就是重要的！
```

````
```{important}
  这很重要，因为它就是重要的！
```

#### 警告

警告块用于引起对特别危险的事情或容易出错的特性的注意。

````
```{warning}
  小心这个...
```
````

```{warning}
  小心这个...
```

#### 版本更改和弃用

这些将显示为建议某个版本开始的添加、更改或弃用功能的单行警告。

````
```{versionadded} 1.0
```
````

```{versionadded} 1.0
```

````
```{versionchanged} 1.0
  此版本中功能的更改方式。
```
````

```{versionchanged} 1.0
  此版本中功能的更改方式。
```

````
```{deprecated} 1.0
```
````

```{deprecated} 1.0
```

#### 侧边栏

这将显示一个信息丰富的侧边栏，浮动在常规内容的旁边。这对于提醒读者与文本相关的某些概念很有用。

````
```{sidebar} 需要记住的事情

- 可以在这里有项目符号列表
- 在这里。

用空行分隔部分。

```
````

```{sidebar} 需要记住的事情

- 可以在这里有项目符号列表
- 在这里。

用空行分隔部分。

```

提示：如果希望确保下一个标题出现在自己的行上（而不是被挤到侧边栏的左边），可以在 Markdown 中嵌入一个简单的 HTML 字符串，如下所示：

```html
<div style="clear: right;"></div>
```

<div style="clear: right;"></div>

#### 更灵活的代码块

常规的 Markdown Python 代码块通常足够，但为了更直接地控制样式，还可以使用 `{code-block}` 指令，它接受一组附加的 `:options:`：

````
```{code-block} python
:linenos:
:emphasize-lines: 1-2,8
:caption: An example code block
:name: A full code block example

from evennia import Command
class CmdEcho(Command):
    """
    Usage: echo <arg>
    """
    key = "echo"
    def func(self):
        self.caller.msg(self.args.strip())
```
````

```{code-block} python
:linenos:
:emphasize-lines: 1-2,8
:caption: An example code block
:name: A full code block example

from evennia import Command
class CmdEcho(Command):
    """
    Usage: echo <arg>
    """
    key = "echo"
    def func(self):
        self.caller.msg(self.args.strip())
```
在这里，`:linenos:` 打开行号，`:emphasize-lines:` 允许以不同颜色强调某些行。`:caption:` 显示说明性文本，`:name:` 用于通过将出现的链接引用此块（因此它在给定文档中应是唯一的）。

#### eval-rst 指令

作为最后的手段，我们还可以退回到直接编写 [ReST][ReST] 指令：

````
```{eval-rst}

    这将被评估为 ReST。
    所有内容必须缩进。

```
````

在 ReST 块中，必须使用重构文本语法，这与 Markdown 不同。

- 单个反引号围绕文本使其为_斜体_。
- 双反引号围绕文本使其为 `原样文本`。
- 链接用反引号写，末尾带下划线：

      `python <www.python.org>`_

[这里是 ReST 格式化速查表](https://thomas-cokelaer.info/tutorials/sphinx/rest_syntax.html)。

## 为自动文档编写代码文档字符串

源代码文档字符串将被解析为 Markdown。在编写模块文档字符串时，可以使用 Markdown 格式，包括到第 4 级标题（`#### SubSubSubHeader`）。

在模块文档之后，最好以四个破折号 `----` 结尾。这将在文档和后续类/函数文档之间创建一个可见的分隔线。参见例如 [Traits 文档](evennia.contrib.rpg.traits)。

所有非私有类、方法和函数必须有一个 Google 风格的文档字符串，按照 [Evennia 编码风格指南][github:evennia/CODING_STYLE.md]。这将被正确格式化为漂亮的 API 文档。

## 本地构建文档

Evennia 使用 [Sphinx][sphinx] 和 [MyST][MyST] 扩展，这使我们能够使用轻量级 Markdown（更具体地说是 [CommonMark][commonmark]，如在 github 上）编写文档，而不是 Sphinx 的常规 ReST 语法。`MyST` 解析器允许一些额外的语法，使我们能够表达比普通 Markdown 更复杂的显示。

对于 [autodoc-generation][sphinx-autodoc] 生成，我们使用 sphinx-[napoleon][sphinx-napoleon] 扩展来理解我们在类和函数等中使用的友好的 Google 风格文档字符串。

`evennia/docs/source/` 中的源文件使用 Sphinx 静态生成器系统与 Evennia 自定义 _预处理器_（也包含在 repo 中）一起构建为文档。

为此，你需要在本地使用带有 `make` 的系统（Linux/Unix/Mac 或 [Windows-WSL][Windows-WSL]）。如果没有，你原则上也可以手动运行 sphinx 构建命令 - 阅读 `evennia/docs/Makefile` 以查看 `make` 命令在本文档中引用的命令。

```{important}
如顶部所述，你不必在本地构建文档即可贡献。Markdown 并不难，可以在不查看处理结果的情况下编写得很好。我们可以在合并前进行润色。

你还可以通过使用 Markdown 查看器如 [Grip][grip] 来很好地感受效果。编辑器如 [ReText][retext] 或 IDE 如 [PyCharm][pycharm] 也有原生的 Markdown 预览。

尽管如此，在本地构建文档是确保结果完全符合预期的唯一方法。处理器还会发现你所犯的任何错误，例如在链接中输入错误。

```
### 仅构建主文档

这是编译和查看更改的最快方法。它只会构建主文档页面，而不是 API 自动文档或版本。所有操作都在终端/控制台中完成。

- （可选，但推荐）：激活一个 Python 3.11 的虚拟环境。
- `cd` 到 `evennia/docs` 文件夹。
- 安装文档构建需求：

    ```
    make install
    或
    pip install -r requirements.txt
    ```

- 接下来，构建基于 html 的文档（将来重新运行此命令以构建更改）：

    ```
    make quick
    ```

- 注意你编辑的文件中的任何错误。
- 基于 html 的文档将出现在新文件夹 `evennia/docs/build/html/` 中。
- 使用 Web 浏览器打开 `file://<path-to-folder>/evennia/docs/build/html/index.html` 并查看文档。请注意，如果点击链接到自动文档，你将收到错误，因为你没有构建它们！

### 构建主文档和 API 文档

完整的文档包括文档页面和从 Evennia 源代码生成的 API 文档。为此，你必须安装 Evennia 并使用默认数据库初始化一个新游戏（你不需要运行任何服务器）。

- 建议你使用虚拟环境。通过指向 repo 文件夹（包含 `/docs` 的文件夹）安装你克隆的 Evennia 版本：

    ```
    pip install -e evennia
    ```

- 确保你在包含 `evennia/` repo 的父文件夹中（因此从 `evennia/docs/` 向上两级）。
- 创建一个名为 `gamedir` 的新游戏文件夹，与 `evennia` repo 位于同一级别

    ```
    evennia --init gamedir
    ```

- 然后 `cd` 进入它并创建一个新的空数据库。之后不需要启动游戏或进行任何进一步的更改。

    ```
    evennia migrate
    ```

- 此时结构应如下所示：

    ```
      (顶层)
      |
      ----- evennia/  (顶级文件夹，包含 docs/)
      |
      ----- gamedir/
    ```

（如果你已经在开发游戏，当然可以在那里有你的“真实”游戏文件夹。我们不会碰那个。）

- 转到 `evennia/docs/` 并安装文档构建需求（你只需执行一次）：

    ```
    make install
    或
    pip install -r requirements.txt
    ```

- 最后，构建完整的文档，包括自动文档：

    ```
    make local
    ```

- 渲染的文件将出现在新文件夹 `evennia/docs/build/html/` 中。注意你编辑的文件中的任何错误。
- 将你的 Web 浏览器指向 `file://<path-to-folder>/evennia/docs/build/html/index.html` 以查看完整文档。

#### 使用其他 gamedir 构建

如果你出于某种原因想要使用其他位置的 `gamedir/`，或者想要将其命名为其他名称（也许你已经在开发中使用了“gamedir”这个名称...），可以通过将 `EVGAMEDIR` 环境变量设置为你的替代游戏目录的绝对路径来实现。例如：

```
EVGAMEDIR=/my/path/to/mygamedir make local
```

### 构建多版本文档

完整的 Evennia 文档包含来自许多 Evennia 版本的文档，新旧版本都有。这是通过从 Evennia 的旧发布分支中提取文档并构建它们，以便读者可以选择查看哪个版本。只有特定的官方 Evennia 分支将被构建，因此你不能用它来构建自己的测试分支。

- 所有本地更改必须首先提交到 git，因为版本化文档是通过查看 git 树构建的。
- 要进行本地检查构建，请运行（`mv` 代表“多版本”）：

    ```
    make mv-local
    ```

这与本地能获得的“真实”版本文档最接近。不同版本将在 `evennia/docs/build/versions/` 下找到。在部署期间，符号链接 `latest` 将指向最新版本的文档。

[sphinx]: https://www.sphinx-doc.org/en/master/
[MyST]: https://myst-parser.readthedocs.io/en/latest/syntax/reference.html
[commonmark]: https://spec.commonmark.org/current/
[commonmark-help]: https://commonmark.org/help/
[sphinx-autodoc]: https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#module-sphinx.ext.autodoc
[sphinx-napoleon]: https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
[getting-started]: Setup/Installation
[contributing]: ./Contributing
[ReST]: https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
[ReST-tables]: https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html#tables
[ReST-directives]: https://www.sphinx-doc.org/en/master/usage/restruturedtext/directives.html
[Windows-WSL]: https://docs.microsoft.com/en-us/windows/wsl/install-win10
[linkdemo]: #Links
[retext]: https://github.com/retext-project/retext
[grip]: https://github.com/joeyespo/grip
[pycharm]: https://www.jetbrains.com/pycharm/
