# 贡献

```{sidebar} 更多贡献
在 [社区贡献与代码片段][forum] 论坛中可以找到更多的 Evennia 代码片段和贡献。
```

_贡献_ 是由 Evennia 社区贡献的可选代码片段和系统。它们的大小和复杂性各不相同，可能比 Evennia 的“核心”更具体地针对游戏类型和风格。此页面是自动生成的，汇总了当前 Evennia 发行版中包含的所有 **52** 个贡献。

所有贡献类别都从 `evennia.contrib` 中导入，例如

```python
from evennia.contrib.base_systems import building_menu
```

每个贡献都包含如何将其与其他代码集成的安装说明。如果你想调整贡献的代码，只需将其整个文件夹复制到你的游戏目录中并从那里进行修改/使用。

如果你想添加贡献，请参阅[贡献指南](./Contribs-Guidelines.md)！

[forum]: https://github.com/evennia/evennia/discussions/categories/community-contribs-snippets

## 索引
| | | | | | | |
|---|---|---|---|---|---|---|
| [基础系统](#base_systems) | [完整系统](#full_systems) | [游戏系统](#game_systems) | [网格](#grid) | [角色扮演](#rpg) | [教程](#tutorials) | [实用工具](#utils) |

| | | | | |
|---|---|---|---|---|
| [成就](#achievements) | [审计](#auditing) | [AWS 存储](#awsstorage) | [以物易物](#barter) | [批处理器](#batchprocessor) |
| [身体功能](#bodyfunctions) | [增益](#buffs) | [建筑菜单](#building_menu) | [角色创建器](#character_creator) | [服装](#clothing) |
| [颜色标记](#color_markups) | [组件](#components) | [容器](#containers) | [冷却时间](#cooldowns) | [制作](#crafting) |
| [自定义游戏时间](#custom_gametime) | [骰子](#dice) | [电子邮件登录](#email_login) | [冒险游戏](#evadventure) | [逃脱房间](#evscaperoom) |
| [扩展房间](#extended_room) | [字段填充](#fieldfill) | [性别替换](#gendersub) | [Git 集成](#git_integration) | [Godot WebSocket](#godotwebsocket) |
| [健康条](#health_bar) | [游戏内地图显示](#ingame_map_display) | [游戏内 Python](#ingame_python) | [游戏内报告](#ingame_reports) | [LLM](#llm) |
| [邮件](#mail) | [地图构建器](#mapbuilder) | [菜单登录](#menu_login) | [镜像](#mirror) | [多描述器](#multidescer) |
| [MUX 通讯命令](#mux_comms_cmds) | [名称生成器](#name_generator) | [谜题](#puzzles) | [随机字符串生成器](#random_string_generator) | [红色按钮](#red_button) |
| [角色扮演系统](#rpsystem) | [简单门](#simpledoor) | [慢速出口](#slow_exit) | [存储](#storage) | [会说话的 NPC](#talking_npc) |
| [特质](#traits) | [树选择](#tree_select) | [回合战斗](#turnbattle) | [教程世界](#tutorial_world) | [Unix 命令](#unixcommand) |
| [荒野](#wilderness) | [XYZ 网格](#xyzgrid) |

## 基础系统

_不一定与特定游戏机制相关，但对整个游戏有用的系统。示例包括登录系统、新命令语法和构建助手。_

```{toctree}
:hidden:
Contribs-Guidelines.md
```
```{toctree}
:maxdepth: 1

Contrib-AWSStorage.md
Contrib-Building-Menu.md
Contrib-Color-Markups.md
Contrib-Components.md
Contrib-Custom-Gametime.md
Contrib-Email-Login.md
Contrib-Godotwebsocket.md
Contrib-Ingame-Python.md
Contrib-Ingame-Reports.md
Contrib-Menu-Login.md
Contrib-Mux-Comms-Cmds.md
Contrib-Unixcommand.md
```

### `awsstorage`

_由 The Right Honourable Reverend (trhr) 贡献，2020_

此插件将 Evennia 的基于 Web 的部分（即图像、JavaScript 和其他位于 staticfiles 内的项目）迁移到 Amazon AWS (S3) 云托管。对于那些与游戏一起提供媒体的人来说非常棒。

[阅读文档](./Contrib-AWSStorage.md) - [浏览代码](evennia.contrib.base_systems.awsstorage)

### `building_menu`

_由 vincent-lg 贡献，2018_

建筑菜单是游戏内菜单，与 `EvMenu` 类似，但采用不同的方法。建筑菜单专为编辑信息而设计。通过命令创建建筑菜单允许构建者快速编辑给定对象，例如房间。如果按照添加贡献的步骤操作，你将可以使用一个 `edit` 命令来编辑任何默认对象，并提供更改其键和描述的选项。

[阅读文档](./Contrib-Building-Menu.md) - [浏览代码](evennia.contrib.base_systems.building_menu)

### `color_markups`

_由 Griatch 贡献，2017_

为 Evennia 提供额外的颜色标记样式（扩展或替换默认的 `|r`，`|234`）。添加对 MUSH 风格（`%cr`，`%c123`）和/或旧版 Evennia（`{r`，`{123`）的支持。

[阅读文档](./Contrib-Color-Markups.md) - [浏览代码](evennia.contrib.base_systems.color_markups)

### `components`

_由 ChrisLR 贡献，2021_

使用组件/组合方法扩展类型类。

[阅读文档](./Contrib-Components.md) - [浏览代码](evennia.contrib.base_systems.components)

### `custom_gametime`

_由 vlgeoff 贡献，2017 - 基于 Griatch 的核心原版_

重新实现 `evennia.utils.gametime` 模块，但为你的游戏世界提供一个 _自定义_ 日历（每周/月/年天数不寻常）。与原版一样，它允许在给定的游戏时间安排事件，但现在考虑了这个自定义日历。

[阅读文档](./Contrib-Custom-Gametime.md) - [浏览代码](evennia.contrib.base_systems.custom_gametime)

### `email_login`

_由 Griatch 贡献，2012_

这是登录系统的一个变体，要求使用电子邮件地址而不是用户名进行登录。请注意，它不验证电子邮件，只是将其用作标识符而不是用户名。

[阅读文档](./Contrib-Email-Login.md) - [浏览代码](evennia.contrib.base_systems.email_login)

### `godotwebsocket`

_由 ChrisLR 贡献，2022_

此贡献允许你将 Godot 客户端直接连接到你的 mud，并使用 BBCode 在 Godot 的 RichTextLabel 中显示常规文本和颜色。你可以使用 Godot 提供具有适当 Evennia 支持的高级功能。

[阅读文档](./Contrib-Godotwebsocket.md) - [浏览代码](evennia.contrib.base_systems.godotwebsocket)

### `ingame_python`

_由 Vincent Le Goff 贡献，2017_

此贡献添加了在游戏中使用 Python 脚本的功能。它允许受信任的工作人员/构建者动态地为单个对象添加功能和触发器，而无需在外部 Python 模块中进行操作。使用自定义 Python 游戏，可以使特定房间、出口、角色、对象等的行为与其“同类”不同。这类似于 MU 的软代码或 DIKU 的 MudProgs。然而，请记住，在游戏中允许使用 Python 会带来 _严重_ 的安全问题（你必须非常信任你的构建者），因此在继续之前请仔细阅读此模块中的警告。

[阅读文档](./Contrib-Ingame-Python.md) - [浏览代码](evennia.contrib.base_systems.ingame_python)

### `ingame_reports`

_由 InspectorCaracal 贡献，2024_

此贡献提供了一个游戏内报告系统，默认处理错误报告、玩家报告和想法提交。它还支持添加你自己的报告类型，或删除任何默认报告类型。

[阅读文档](./Contrib-Ingame-Reports.md) - [浏览代码](evennia.contrib.base_systems.ingame_reports)

### `menu_login`

_由 Vincent-lg 贡献，2016。由 Griatch 重新设计为现代 EvMenu，2019。_

这将 Evennia 登录更改为通过一系列问题询问帐户名称和密码，而不是要求你同时输入两者。它在底层使用 Evennia 的菜单系统 `EvMenu`。

[阅读文档](./Contrib-Menu-Login.md) - [浏览代码](evennia.contrib.base_systems.menu_login)

### `mux_comms_cmds`

_由 Griatch 贡献，2021_

在 Evennia 1.0+ 中，旧的频道命令（最初受 MUX 启发）被单个 `channel` 命令替代，该命令执行所有这些功能。此贡献（从 Evennia 0.9.5 中提取）将功能分解为更符合 MU* 用户习惯的单独命令。不过，这只是为了展示，主要的 `channel` 命令仍在底层调用。

[阅读文档](./Contrib-Mux-Comms-Cmds.md) - [浏览代码](evennia.contrib.base_systems.mux_comms_cmds)

### `unixcommand`

_由 Vincent Le Geoff (vlgeoff) 贡献，2017_

此模块包含一个命令类，具有在游戏中实现 Unix 风格命令语法的替代语法解析器。这意味着 `--options`，位置参数和类似 `-n 10` 的内容。对于普通玩家来说，这可能不是最佳语法，但对于构建者来说，当他们需要让单个命令执行许多事情时，这可能非常有用。它在底层使用 Python 标准库中的 `ArgumentParser`。

[阅读文档](./Contrib-Unixcommand.md) - [浏览代码](evennia.contrib.base_systems.unixcommand)

## 完整系统

_可以直接用于开始创建内容的“完整”游戏引擎，无需进一步添加（除非你愿意）。_

```{toctree}
:hidden:
Contribs-Guidelines.md
```
```{toctree}
:maxdepth: 1

Contrib-Evscaperoom.md
```

### `evscaperoom`

_由 Griatch 贡献，2019_

用于在 Evennia 中创建多人逃脱房间的完整引擎。允许玩家生成和加入独立跟踪其状态的谜题房间。任何数量的玩家都可以加入以共同解决一个房间。这是为 'EvscapeRoom' 创建的引擎，该引擎在 2019 年 4 月至 5 月的 MUD Coders Guild "One Room" 游戏开发大赛中获胜。贡献中仅包含非常少量的游戏内容，包含实用程序和基类以及一个空的示例房间。

[阅读文档](./Contrib-Evscaperoom.md) - [浏览代码](evennia.contrib.full_systems.evscaperoom)

## 游戏系统

_游戏内的游戏玩法系统，如制作、邮件、战斗等。每个系统都旨在逐个采用并为你的游戏进行调整。这不包括特定于角色扮演的系统，这些系统在 `rpg` 类别中找到。_

```{toctree}
:hidden:
Contribs-Guidelines.md
```
```{toctree}
:maxdepth: 1

Contrib-Achievements.md
Contrib-Barter.md
Contrib-Clothing.md
Contrib-Containers.md
Contrib-Cooldowns.md
Contrib-Crafting.md
Contrib-Gendersub.md
Contrib-Mail.md
Contrib-Multidescer.md
Contrib-Puzzles.md
Contrib-Storage.md
Contrib-Turnbattle.md
```

### `achievements`

_一个简单但相当全面的系统，用于跟踪成就。成就使用普通的 Python 字典定义，类似于核心原型系统，虽然预计你只会在角色或帐户上使用它，但它们可以跟踪任何类型类对象。_

贡献提供了几个用于跟踪和访问成就的函数，以及一个基本的游戏内命令用于查看成就状态。

[阅读文档](./Contrib-Achievements.md) - [浏览代码](evennia.contrib.game_systems.achievements)

### `barter`

_由 Griatch 贡献，2012_

这实现了一个完整的以物易物系统 - 一种让玩家通过代码而不是简单的 `give/get` 命令来安全交易物品的方式。这增加了安全性（在任何时候都不会让一个玩家同时拥有货物和付款）和速度，因为商定的货物将自动移动）。通过仅用硬币对象替换一方（或硬币和货物的混合），这也适用于常规货币交易。

[阅读文档](./Contrib-Barter.md) - [浏览代码](evennia.contrib.game_systems.barter)

### `clothing`

_由 Tim Ashley Jenkins 贡献，2017_

提供一个类型类和命令用于可穿戴衣物。这些衣物的外观在穿着时会附加到角色的描述中。

[阅读文档](./Contrib-Clothing.md) - [浏览代码](evennia.contrib.game_systems.clothing)

### `containers`

_通过提供容器类型类和扩展某些基本命令，添加将对象放入其他容器对象的能力。_

## 安装

[阅读文档](./Contrib-Containers.md) - [浏览代码](evennia.contrib.game_systems.containers)

### `cooldowns`

_由 owllex 贡献，2021_

冷却时间用于模拟速率限制的动作，例如角色可以执行给定动作的频率；在某个时间过去之前，他们的命令无法再次使用。此贡献提供了一个简单的冷却时间处理程序，可以附加到任何类型类。冷却时间是一个轻量级持久异步计时器，你可以查询以查看某个时间是否已过去。

[阅读文档](./Contrib-Cooldowns.md) - [浏览代码](evennia.contrib.game_systems.cooldowns)

### `crafting`

_由 Griatch 贡献，2020_

这实现了一个完整的制作系统。原则是“配方”，你将物品（标记为成分）组合在一起创造新东西。配方还可以要求某些（不消耗的）工具。一个例子是使用“面包配方”将“面粉”、“水”和“酵母”与“烤箱”结合起来烤一个“面包”。

[阅读文档](./Contrib-Crafting.md) - [浏览代码](evennia.contrib.game_systems.crafting)

### `gendersub`

_由 Griatch 贡献，2015_

这是一个简单的性别感知角色类，允许用户在文本中插入自定义标记以指示性别感知消息。它依赖于修改过的 msg()，旨在作为如何做类似事情的灵感和起点。

[阅读文档](./Contrib-Gendersub.md) - [浏览代码](evennia.contrib.game_systems.gendersub)

### `mail`

_由 grungies1138 贡献，2016_

一个简单的 Brandymail 风格邮件系统，使用 Evennia Core 的 `Msg` 类。它有两个命令，用于在帐户之间（游戏外）或角色之间（游戏内）发送邮件。这两种类型的邮件可以一起使用或单独使用。

[阅读文档](./Contrib-Mail.md) - [浏览代码](evennia.contrib.game_systems.mail)

### `multidescer`

_由 Griatch 贡献，2016_

“多描述器”是 MUSH 世界中的一个概念。它允许将你的描述分割为任意命名的“部分”，然后你可以随时切换。这是一种快速管理你的外观（例如更换衣服）的方式，适用于更自由形式的角色扮演系统。这也将与 `rpsystem` 贡献一起很好地工作。

[阅读文档](./Contrib-Multidescer.md) - [浏览代码](evennia.contrib.game_systems.multidescer)

### `puzzles`

_由 Henddher 贡献，2018_

适用于冒险游戏风格的组合谜题，例如将水果和搅拌机组合在一起制作奶昔。提供一个类型类和命令用于可以组合（即一起使用）的对象。与 `crafting` 贡献不同，每个谜题是由独特的对象构建的，构建者可以完全在游戏中创建谜题。

[阅读文档](./Contrib-Puzzles.md) - [浏览代码](evennia.contrib.game_systems.puzzles)

### `storage`

_由 helpme 贡献（2024）_

此模块允许将某些房间标记为存储位置。

[阅读文档](./Contrib-Storage.md) - [浏览代码](evennia.contrib.game_systems.storage)

### `turnbattle`

_由 Tim Ashley Jenkins 贡献，2017_

这是一个简单的回合制战斗系统框架，类似于 D&D 风格的桌面角色扮演游戏。它允许任何角色在房间中开始战斗，然后滚动先攻并建立回合顺序。每个战斗参与者都有有限的时间来决定他们在该回合的动作（默认情况下为 30 秒），战斗按照回合顺序进行，循环遍历参与者直到战斗结束。

[阅读文档](./Contrib-Turnbattle.md) - [浏览代码](evennia.contrib.game_systems.turnbattle)

## 网格

_与游戏世界的拓扑结构和结构相关的系统。与房间、出口和地图构建相关的贡献。_

```{toctree}
:hidden:
Contribs-Guidelines.md
```
```{toctree}
:maxdepth: 1

Contrib-Extended-Room.md
Contrib-Ingame-Map-Display.md
Contrib-Mapbuilder.md
Contrib-Simpledoor.md
Contrib-Slow-Exit.md
Contrib-Wilderness.md
Contrib-XYZGrid.md
```

### `extended_room`

_贡献 - Griatch 2012，vincent-lg 2019，Griatch 2023_

这扩展了普通的 `Room` 类型类，以允许其描述随时间和/或季节以及任何其他状态（如洪水或黑暗）而变化。在描述中嵌入 `$state(burning, This place is on fire!)` 将允许根据房间状态更改描述。房间还支持玩家在房间中查看的 `details`（无需为每个创建新的游戏对象），以及对随机回声的支持。房间附带一组替代命令用于 `look` 和 `@desc`，以及新命令 `detail`，`roomstate` 和 `time`。

[阅读文档](./Contrib-Extended-Room.md) - [浏览代码](evennia.contrib.grid.extended_room)

### `ingame_map_display`

_贡献 - helpme 2022_

这为给定房间添加了一个 ASCII `map`，可以通过 `map` 命令查看。你可以轻松更改它以添加特殊字符、房间颜色等。显示的地图是在使用时动态生成的，并支持所有罗盘方向和上下。其他方向被忽略。

[阅读文档](./Contrib-Ingame-Map-Display.md) - [浏览代码](evennia.contrib.grid.ingame_map_display)

### `mapbuilder`

_由 Cloud_Keeper 贡献，2016_

从 2D ASCII 地图的绘图中构建游戏地图。

[阅读文档](./Contrib-Mapbuilder.md) - [浏览代码](evennia.contrib.grid.mapbuilder)

### `simpledoor`

_由 Griatch 贡献，2016_

一个简单的双向出口，代表一个可以从两侧打开和关闭的门。可以轻松扩展以使其可锁定、可破坏等。

[阅读文档](./Contrib-Simpledoor.md) - [浏览代码](evennia.contrib.grid.simpledoor)

### `slow_exit`

_由 Griatch 贡献，2014_

一个延迟遍历的出口类型示例。这模拟了许多游戏中常见的缓慢移动。贡献还包含两个命令，`setspeed` 和 `stop`，用于更改移动速度和中止正在进行的遍历。

[阅读文档](./Contrib-Slow-Exit.md) - [浏览代码](evennia.contrib.grid.slow_exit)

### `wilderness`

_由 titeuf87 贡献，2017_

此贡献提供了一个荒野地图，而无需实际创建大量房间 - 当你移动时，你会回到同一个房间，但其描述会改变。这意味着只要房间相对相似（例如仅名称/描述变化），就可以创建巨大的区域而数据库使用量很小。

[阅读文档](./Contrib-Wilderness.md) - [浏览代码](evennia.contrib.grid.wilderness)

### `xyzgrid`

_由 Griatch 贡献，2021_

将 Evennia 的游戏世界放置在 xy（z 为不同地图）坐标网格上。网格由外部创建和维护，通过绘制和解析 2D ASCII 地图，包括传送、地图转换和特殊标记以帮助路径查找。支持每个地图上非常快速的最短路径路径查找。还包括一个快速视图功能，用于仅查看从当前位置有限步数的距离（用于在游戏中显示更新的地图）。

[阅读文档](./Contrib-XYZGrid.md) - [浏览代码](evennia.contrib.grid.xyzgrid)

## 角色扮演

_与角色扮演和规则实现相关的系统，如角色特质、骰子掷骰和表情。_

```{toctree}
:hidden:
Contribs-Guidelines.md
```
```{toctree}
:maxdepth: 1

Contrib-Buffs.md
Contrib-Character-Creator.md
Contrib-Dice.md
Contrib-Health-Bar.md
Contrib-Llm.md
Contrib-RPSystem.md
Contrib-Traits.md
```

### `buffs`

_由 Tegiminis 贡献，2022_

增益是一个定时对象，附加到游戏实体。它能够修改值、触发代码或两者兼而有之。它是 RPG 中的一个常见设计模式，特别是动作游戏中。

[阅读文档](./Contrib-Buffs.md) - [浏览代码](evennia.contrib.rpg.buffs)

### `character_creator`

_由 InspectorCaracal 贡献，2022_

用于管理和启动游戏内角色创建菜单的命令。

[阅读文档](./Contrib-Character-Creator.md) - [浏览代码](evennia.contrib.rpg.character_creator)

### `dice`

_由 Griatch 贡献，2012，2023_

一个用于任意数量和面的骰子掷骰器。添加游戏内骰子掷骰（如 `roll 2d10 + 1`）以及条件（滚动低于/超过/等于目标）和用于在代码中掷骰的函数。命令还支持隐藏或秘密掷骰，以供人类游戏大师使用。

[阅读文档](./Contrib-Dice.md) - [浏览代码](evennia.contrib.rpg.dice)

### `health_bar`

_由 Tim Ashley Jenkins 贡献，2017_

此模块提供的函数让你可以轻松地将视觉条或仪表显示为彩色条，而不仅仅是数字。“健康条”只是最明显的用途，但该条高度可定制，可以用于除玩家健康外的任何适当数据。

[阅读文档](./Contrib-Health-Bar.md) - [浏览代码](evennia.contrib.rpg.health_bar)

### `llm`

_由 Griatch 贡献，2023_

这增加了一个 LLMClient，允许 Evennia 向 LLM 服务器（大型语言模型，如 ChatGPT）发送提示。示例使用本地 OSS LLM 安装。包含一个 NPC，你可以使用新的 `talk` 命令与之聊天。NPC 将使用来自 LLM 服务器的 AI 响应进行回答。所有调用都是异步的，因此如果 LLM 速度较慢，Evennia 不会受到影响。

[阅读文档](./Contrib-Llm.md) - [浏览代码](evennia.contrib.rpg.llm)

### `rpsystem`

_由 Griatch 贡献，2015_

一个完整的角色扮演表情系统。短描述和识别（仅通过外观认识人，直到你为他们指定一个名字）。房间姿势。面具/伪装（隐藏你的描述）。直接在表情中说话，带有可选的语言模糊处理（如果你不知道语言，单词会被模糊，你也可以有不同语言的不同“听起来”模糊）。耳语可以从远处部分被听到。一个非常强大的表情内引用系统，用于引用和区分目标（包括对象）。

[阅读文档](./Contrib-RPSystem.md) - [浏览代码](evennia.contrib.rpg.rpsystem)

### `traits`

_由 Griatch 贡献，2020，基于 Whitenoise 和 Ainneve 贡献的代码，2014_

`Trait` 表示（通常）角色上的可修改属性。它们可以用于表示从属性（str，agi 等）到技能（hunting 10，swords 14 等）以及动态变化的事物（如 HP，XP 等）。特质与普通属性的不同之处在于它们跟踪其变化并限制在特定的值范围内。可以轻松地对它们进行加减操作，甚至可以以特定速度动态变化（如中毒或治疗）。

[阅读文档](./Contrib-Traits.md) - [浏览代码](evennia.contrib.rpg.traits)

## 教程

_专门用于教授开发概念或示例化 Evennia 系统的帮助资源。与文档教程相关的任何额外资源都在这里找到。也是教程世界和 Evadventure 演示代码的所在地。_

```{toctree}
:hidden:
Contribs-Guidelines.md
```
```{toctree}
:maxdepth: 1

Contrib-Batchprocessor.md
Contrib-Bodyfunctions.md
Contrib-Evadventure.md
Contrib-Mirror.md
Contrib-Red-Button.md
Contrib-Talking-Npc.md
Contrib-Tutorial-World.md
```

### `batchprocessor`

_由 Griatch 贡献，2012_

批处理器的简单示例。批处理器用于从一个或多个静态文件生成游戏内内容。文件可以与版本控制一起存储，然后“应用”到游戏中以创建内容。

[阅读文档](./Contrib-Batchprocessor.md) - [浏览代码](evennia.contrib.tutorials.batchprocessor)

### `bodyfunctions`

_由 Griatch 贡献，2012_

用于测试的示例脚本。这添加了一个简单的计时器，让你的角色在不规则的间隔发出小的口头观察。

[阅读文档](./Contrib-Bodyfunctions.md) - [浏览代码](evennia.contrib.tutorials.bodyfunctions)

### `evadventure`

_由 Griatch 贡献，2023_

```{warning}
注意 - 此教程正在进行中，尚未完成！你仍然可以从中学习，但不要期望完美。
```

[阅读文档](./Contrib-Evadventure.md) - [浏览代码](evennia.contrib.tutorials.evadventure)

### `mirror`

_由 Griatch 贡献，2017_

一个用于实验的简单镜子对象。它会对被查看时做出反应。

[阅读文档](./Contrib-Mirror.md) - [浏览代码](evennia.contrib.tutorials.mirror)

### `red_button`

_由 Griatch 贡献，2011_

一个可以按下以产生效果的红色按钮。这是一个更高级的示例对象，具有自己的功能和状态跟踪。

[阅读文档](./Contrib-Red-Button.md) - [浏览代码](evennia.contrib.tutorials.red_button)

### `talking_npc`

_由 Griatch 贡献，2011。由 grungies1138 更新，2016_

这是一个能够进行简单菜单驱动对话的静态 NPC 对象示例。适合用作任务给予者或商人。

[阅读文档](./Contrib-Talking-Npc.md) - [浏览代码](evennia.contrib.tutorials.talking_npc)

### `tutorial_world`

_由 Griatch 贡献，2011，2015_

一个独立的教程区域，适用于未修改的 Evennia 安装。将其视为一种单人冒险，而不是一个完整的多人游戏世界。各种房间和对象旨在展示 Evennia 的功能，而不是提供非常具有挑战性（或长时间）的游戏体验。因此，它当然只是可能性的表面。拆解这个是开始学习系统的好方法。

[阅读文档](./Contrib-Tutorial-World.md) - [浏览代码](evennia.contrib.tutorials.tutorial_world)

## 实用工具

_杂项，用于操作文本、安全审计等的工具。_

```{toctree}
:hidden:
Contribs-Guidelines.md
```
```{toctree}
:maxdepth: 1

Contrib-Auditing.md
Contrib-Fieldfill.md
Contrib-Git-Integration.md
Contrib-Name-Generator.md
Contrib-Random-String-Generator.md
Contrib-Tree-Select.md
```

### `auditing`

_由 Johnny 贡献，2017_

实用程序，拦截和截获发送到/从客户端和服务器的所有数据，并将其传递给你选择的回调。这旨在用于质量保证、事后调查和调试。

[阅读文档](./Contrib-Auditing.md) - [浏览代码](evennia.contrib.utils.auditing)

### `fieldfill`

_由 Tim Ashley Jenkins 贡献，2018_

此模块包含一个为你生成 `EvMenu` 的函数 - 此菜单向玩家显示一个字段表单，可以按任何顺序填写（例如用于角色生成或构建）。每个字段的值可以验证，函数允许轻松检查文本和整数输入、最小和最大值/字符长度，甚至可以通过自定义函数验证。一旦提交表单，表单的数据将作为字典提交给你选择的任何可调用对象。

[阅读文档](./Contrib-Fieldfill.md) - [浏览代码](evennia.contrib.utils.fieldfill)

### `git_integration`

_由 helpme 贡献（2022）_

一个模块，用于在游戏中集成精简版 git，允许开发人员查看其 git 状态、切换分支和拉取更新的代码，包括本地 mygame 仓库和 Evennia 核心。在成功拉取或签出后，git 命令将重新加载游戏：某些更改可能需要手动重启以应用，例如影响持久脚本等。

[阅读文档](./Contrib-Git-Integration.md) - [浏览代码](evennia.contrib.utils.git_integration)

### `name_generator`

_由 InspectorCaracal 贡献（2022）_

一个用于生成随机名称的模块，包括真实世界和幻想名称。真实世界的名称可以生成为名字（个人名）、姓氏（姓）或全名（名、可选中间名和姓）。名称数据来自 [Behind the Name](https://www.behindthename.com/)，根据 [CC BY-SA 4.0 许可证](https://creativecommons.org/licenses/by-sa/4.0/)使用。

[阅读文档](./Contrib-Name-Generator.md) - [浏览代码](evennia.contrib.utils.name_generator)

### `random_string_generator`

_由 Vincent Le Goff (vlgeoff) 贡献，2017_

此实用程序可用于生成具有特定条件的伪随机信息字符串。例如，你可以使用它生成电话号码、车牌号码、验证码、游戏内安全密码等。生成的字符串将被存储，不会重复。

[阅读文档](./Contrib-Random-String-Generator.md) - [浏览代码](evennia.contrib.utils.random_string_generator)

### `tree_select`

_由 Tim Ashley Jenkins 贡献，2017_

此实用程序允许你从传递给一个函数的多行字符串创建并初始化整个分支 EvMenu 实例。

[阅读文档](./Contrib-Tree-Select.md) - [浏览代码](evennia.contrib.utils.tree_select)

----

<small>此文档页面是自动生成的。手动更改将被覆盖。</small>

请检查翻译是否符合你的要求，如果有任何调整需要，请告诉我！
