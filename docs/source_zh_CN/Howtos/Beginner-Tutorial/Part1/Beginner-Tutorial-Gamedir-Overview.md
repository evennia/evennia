# 新游戏目录概述

到目前为止，我们已经“运行了游戏”并开始在 Evennia 中使用 Python。现在是时候看看游戏外的结构了。

让我们来参观一下你的游戏目录（假设它叫做 `mygame`）。

> 在查看文件时，忽略以 `.pyc` 结尾的文件和 `__pycache__` 文件夹（如果存在）。这些是内部 Python 编译文件，你不需要碰它们。文件 `__init__.py` 通常也是空的，可以忽略（它们与 Python 包管理有关）。

你可能注意到，当我们在游戏中构建东西时，我们经常通过“Python 路径”引用代码，例如：

```
create/drop button:tutorial_examples.red_button.RedButton
```

这是 Evennia 编码的一个基本方面——_你创建代码，然后告诉 Evennia 代码的位置以及何时使用它_。上面我们通过从 `contrib/` 文件夹中提取特定代码来创建一个红色按钮。同样的原则在任何地方都适用。因此，了解代码的位置以及如何正确指向它是很重要的。

```{sidebar} Python 路径
'Python 路径' 使用 '.' 而不是 '/' 或 '`\\`'，并跳过文件的 `.py` 结尾。它还可以指向 Python 文件的代码内容。由于 Evennia 已经在查找你的游戏目录中的代码，所以你的 Python 路径可以从那里开始。因此，路径 `/home/foo/devel/mygame/commands/command.py` 将转换为 Python 路径 `commands.command`。
```

- `mygame/`
  - `commands/` - 这里存放所有自定义命令（用户输入处理器）。你可以在这里添加自己的命令并覆盖 Evennia 的默认命令。
  - `server/` - 这个文件夹的结构不应改变，因为 Evennia 期望它保持不变。
    - `conf/` - 所有服务器配置文件都在这里。最重要的文件是 `settings.py`。
    - `logs/` - 服务器日志文件存储在这里。当你使用 `evennia --log` 时，你实际上是在跟踪该目录中的文件。
  - `typeclasses/` - 这里包含描述游戏中所有数据库绑定实体的空模板，如角色、脚本、账户等。在这里添加代码可以自定义和扩展默认设置。
  - `web/` - 这是你覆盖和扩展 Evennia 的网络存在（如网站和 HTML5 网络客户端）的默认模板、视图和静态文件的地方。
  - `world/` - 这是一个“杂项”文件夹，包含与构建的世界相关的所有内容，如构建脚本和不适合其他文件夹的规则模块。

> `server/` 子文件夹应保持原样——Evennia 期望如此。但你可以根据自己的喜好更改其余游戏目录的结构。
> 也许你不想要单个 world/ 文件夹，而是更喜欢多个文件夹来处理世界的不同方面？为你的 RPG 规则创建一个新文件夹 'rules'？将命令与对象分组而不是分开？这都可以。如果你移动了东西，只需更新 Evennia 的默认设置以指向新结构中的正确位置。

## commands/

`commands/` 文件夹包含与创建和扩展 Evennia 的 [Commands](../../../Components/Commands.md) 相关的 Python 模块。这些命令在游戏中表现为服务器理解的输入，如 `look` 或 `dig`。

```{sidebar} 类

`类` 是 Python 中用于创建特定类型对象实例的模板。我们将在下一课中更详细地解释类。

```
- [command.py](github:evennia/game_template/commands/command.py) (Python 路径: `commands.command`) - 这包含设计新输入命令或覆盖默认命令的基本 _类_。
- [default_cmdsets.py](github:evennia/game_template/commands/default_cmdsets.py) (Python 路径: `commands.default_commands`) - 命令集 (Command-Set) 将命令组合在一起。命令集可以动态地添加和移除对象，这意味着用户可以根据游戏中的情况拥有不同的命令集（或命令版本）。为了将新命令添加到游戏中，通常会从 `command.py` 导入新命令类并将其添加到此模块中的默认命令集中之一。

## server/

此文件夹包含运行 Evennia 所需的资源。与其他文件夹不同，其结构应保持不变。

- `evennia.db3` - 如果你使用的是默认的 SQLite3 数据库，你将只有这个文件。此文件包含整个数据库。只需复制它即可进行备份。对于开发，你也可以在设置好所需的一切后复制一次，然后只需复制回来以“重置”状态。如果删除此文件，可以通过运行 `evennia migrate` 轻松重建它。

### server/logs/

这里保存服务器日志。当你执行 `evennia --log` 时，evennia 程序实际上是在跟踪和连接该目录中的 `server.log` 和 `portal.log` 文件。日志每周轮换一次。根据你的设置，其他日志，如网络服务器 HTTP 请求日志，也可以在这里找到。

### server/conf/

此处包含 Evennia 服务器的所有配置文件。这些是常规的 Python 模块，这意味着它们必须用有效的 Python 扩展。如果需要，你也可以向它们添加逻辑。

设置的共同点是你通常不会通过其 Python 路径直接导入它们；相反，Evennia 知道它们的位置，并将在启动时读取它们以进行配置。

- `settings.py` - 这是迄今为止最重要的文件。默认情况下几乎是空的，而是期望你从 [evennia/default_settings.py](../../../Setup/Settings-Default.md) 复制并粘贴所需的更改。默认设置文件有详细的文档。以特殊方式导入/访问设置文件中的值，如下所示：

```python
from django.conf import settings
```

要获取设置文件中的 `TELNET_PORT` 设置，你可以这样做：

```python
telnet_port = settings.TELNET_PORT
```

你不能动态地分配给设置文件；必须直接更改 `settings.py` 文件以更改设置。有关更多详细信息，请参阅 [设置](../../../Setup/Settings.md) 文档。
- `secret_settings.py` - 如果你将代码公开，你可能不希望在线共享所有设置。可能有服务器特定的秘密或只是你希望对玩家保密的游戏系统的微调。将此类设置放在这里，它将覆盖 `settings.py` 中的值，并且不会包含在版本控制中。
- `at_initial_setup.py` - 当 Evennia 第一次启动时，它会执行一些基本任务，如创建超级用户和 Limbo 房间。向此文件添加内容可以为首次启动添加更多操作。
- `at_search.py` - 当搜索对象并且找不到匹配项或找到多个匹配项时，它将通过给出警告或提供用户区分多个匹配项来响应。修改此处的代码将根据你的喜好更改此行为。
- `at_server_startstop.py` - 这允许在服务器以不同方式启动、停止或重新加载时注入要执行的代码。
- `connection_screens.py` - 这允许更改首次连接到游戏时看到的连接屏幕。
- `inlinefuncs.py` - [Inlinefuncs](../../../Concepts/Inline-Functions.md) 是可选且有限的“函数”，可以嵌入到发送给玩家的任何字符串中。它们被写为 `$funcname(args)`，用于根据接收它的用户自定义输出。例如，发送给人们的文本 `"Let's meet at $realtime(13:00, GMT)!` 会向每个看到该字符串的玩家显示其所在时区的时间。添加到此模块中的函数将成为游戏中的新 inlinefuncs。另请参阅 [FuncParser](../../../Components/FuncParser.md)。
- `inputfuncs.py` - 当服务器接收到类似 `look` 的命令时，它由一个 [Inputfunc](InputFuncs) 处理，该函数将其重定向到 cmdhandler 系统。但客户端可能还有其他输入，如按钮按下或请求更新生命值栏。虽然大多数常见情况已经涵盖，但这是添加新函数以处理新类型输入的地方。
- `lockfuncs.py` - [Locks](../../../Components/Locks.md) 及其组件 _LockFuncs_ 限制对游戏内事物的访问。锁函数用于定义更复杂的锁。例如，你可以有一个锁函数来检查用户是否携带给定物品、正在流血或具有某个技能值。添加到此模块中的新函数将可用于锁定义。
- `mssp.py` - Mud 服务器状态协议是一种在线 MUD 存档/列表（通常需要注册）用于跟踪当前在线的 MUD、玩家数量等的方法。虽然 Evennia 会自动处理动态信息，但这是你设置有关游戏的元信息的地方，例如其主题、是否允许玩家杀戮等。这是 Evennia 游戏目录的更通用形式。
- `portal_services_plugins.py` - 如果你想向 Evennia 添加新的外部连接协议，这是添加它们的地方。
- `server_services_plugins.py` - 这允许覆盖内部服务器连接协议。
- `web_plugins.py` - 这允许在 Evennia 网络服务器启动时添加插件。

### typeclasses/

Evennia 的 [Typeclasses](../../../Components/Typeclasses.md) 是 Evennia 特定的 Python 类，其实例会保存到数据库中。这使得角色可以保持在同一位置，并且在服务器重启后更新的力量统计仍然相同。

- [accounts.py](github:evennia/game_template/typeclasses/accounts.py) (Python 路径: `typeclasses.accounts`) - 一个 [Account](../../../Components/Accounts.md) 代表连接到游戏的玩家。它包含电子邮件、密码和其他非角色信息。
- [channels.py](github:evennia/game_template/typeclasses/channels.py) (Python 路径: `typeclasses.channels`) - [Channels](../../../Components/Channels.md) 用于管理玩家之间的游戏内通信。
- [objects.py](github:evennia/game_template/typeclasses/objects.py) (Python 路径: `typeclasses.objects`) - [Objects](../../../Components/Objects.md) 代表游戏世界中所有具有位置的事物。
- [characters.py](github:evennia/game_template/typeclasses/characters.py) (Python 路径: `typeclasses.characters`) - [Character](../../../Components/Objects.md#characters) 是 Objects 的子类，由 Accounts 控制——它们是游戏世界中玩家的化身。
- [rooms.py](github:evennia/game_template/typeclasses/rooms.py) (Python 路径: `typeclasses.rooms`) - [Room](../../../Components/Objects.md#rooms) 也是 Object 的子类；描述离散位置。虽然传统术语是“房间”，但这样的地点可以是任何东西，并且可以是任何适合你游戏的规模，从森林空地、整个星球或实际的地牢房间。
- [exits.py](github:evennia/game_template/typeclasses/exits.py) (Python 路径: `typeclasses.exits`) - [Exits](../../../Components/Objects.md#exits) 是 Object 的另一个子类。出口将一个房间连接到另一个房间。
- [scripts.py](github:evennia/game_template/typeclasses/scripts.py) (Python 路径: `typeclasses.scripts`) - [Scripts](../../../Components/Scripts.md) 是“非角色”对象。它们在游戏中没有位置，可以作为任何需要数据库持久性的基础，例如战斗、天气或经济系统。它们还具有定时执行代码的能力。

### web/

此文件夹包含用于覆盖 Evennia 默认网络存在的子文件夹，使用你自己的设计。除了 README 文件或其他空文件夹的子集外，大多数这些文件夹都是空的。有关详细信息，请参阅 [网络概述](../../../Components/Components-Overview.md#web-components)（我们将在本初学者教程的后面部分回到网络）。

- `media/` - 这个空文件夹是你可以放置自己的图像或其他媒体文件的地方，网络服务器将提供这些文件。如果你发布的游戏包含大量媒体（尤其是视频），你应该考虑重新指向 Evennia 使用一些外部服务来提供你的媒体。
- `static_overrides/` - '静态' 文件包括字体、CSS 和 JS。在此文件夹中，你会找到用于覆盖 `admin`（这是 Django 网络管理）、`webclient`（这是 HTML5 网络客户端）和 `website` 的静态文件的子文件夹。将文件添加到此文件夹将替换默认网络存在中的同名文件。
- `template_overrides/` - 这些是 HTML 文件，适用于 `webclient` 和 `website`。HTML 文件是使用 [Jinja](https://jinja.palletsprojects.com/en/2.11.x/) 模板编写的，这意味着可以只覆盖默认模板的特定部分而不影响其他部分。
- `static/` - 这是网络系统的工作目录，不应手动修改。基本上，Evennia 会在服务器启动时将静态数据从 `static_overrides` 复制到这里。
- `urls.py` - 此模块将 Python 代码链接到浏览器中访问的 URL。

### world/

此文件夹仅包含一些示例文件。它的目的是容纳游戏实现的“其余部分”。许多人以各种方式更改和重组此文件夹以更好地适应他们的想法。

- [batch_cmds.ev](github:evennia/game_template/world/batch_cmds.ev) - 这是一个 `.ev` 文件，基本上只是一个按顺序执行的 Evennia 命令列表。这个是空的，可以扩展。[教程世界](./Beginner-Tutorial-Tutorial-World.md) 是用这样的批处理文件构建的。
- [prototypes.py](github:evennia/game_template/world/prototypes.py) - [prototype](../../../Components/Prototypes.md) 是一种无需更改其基础类型类即可轻松变化对象的方法。例如，可以使用原型来表示两个地精虽然都属于“地精”类（因此遵循相同的代码逻辑），但应具有不同的装备、统计数据和外观。
- [help_entries.py](github:evennia/game_template/world/help_entries.py) - 你可以通过多种方式添加新的游戏内 [帮助条目](../../../Components/Help-System.md)，例如使用 `sethelp` 命令在数据库中添加，或者（对于命令）直接从源代码读取帮助。你也可以通过 Python 模块添加它们。此模块是如何做到这一点的示例。
