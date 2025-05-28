# 贡献

```{sidebar} 更多贡献
额外的 Evennia 代码片段和贡献可以在 [社区贡献和片段][forum] 论坛中找到。
```
_贡献_ 是由 Evennia 社区贡献的可选代码片段和系统。它们的大小和复杂性各不相同，并且可能比 '核心' Evennia 更具体地针对游戏类型和风格。此页面是自动生成的，汇总了当前 Evennia 发行版中包含的所有 **53** 个贡献。

所有贡献类别都从 `evennia.contrib` 导入，例如

    from evennia.contrib.base_systems import building_menu

每个贡献都包含如何将其与其他代码集成的安装说明。如果你想调整贡献的代码，只需将其整个文件夹复制到你的游戏目录并从那里修改/使用即可。

如果你想添加贡献，请参阅 [贡献指南](Contribs-Guidelines)!

[forum]: https://github.com/evennia/evennia/discussions/categories/community-contribs-snippets

## 索引
| | | | | | | |
|---|---|---|---|---|---|---|
| [base_systems](#base_systems) | [full_systems](#full_systems) | [game_systems](#game_systems) | [grid](#grid) | [rpg](#rpg) | [tutorials](#tutorials) | [utils](#utils) |

| | | | | |
|---|---|---|---|---|
| [achievements](#achievements) | [auditing](#auditing) | [awsstorage](#awsstorage) | [barter](#barter) | [batchprocessor](#batchprocessor) |
| [bodyfunctions](#bodyfunctions) | [buffs](#buffs) | [building_menu](#building_menu) | [character_creator](#character_creator) | [clothing](#clothing) |
| [color_markups](#color_markups) | [components](#components) | [containers](#containers) | [cooldowns](#cooldowns) | [crafting](#crafting) |
| [custom_gametime](#custom_gametime) | [debugpy](#debugpy) | [dice](#dice) | [email_login](#email_login) | [evadventure](#evadventure) |
| [evscaperoom](#evscaperoom) | [extended_room](#extended_room) | [fieldfill](#fieldfill) | [gendersub](#gendersub) | [git_integration](#git_integration) |
| [godotwebsocket](#godotwebsocket) | [health_bar](#health_bar) | [ingame_map_display](#ingame_map_display) | [ingame_python](#ingame_python) | [ingame_reports](#ingame_reports) |
| [llm](#llm) | [mail](#mail) | [mapbuilder](#mapbuilder) | [menu_login](#menu_login) | [mirror](#mirror) |
| [multidescer](#multidescer) | [mux_comms_cmds](#mux_comms_cmds) | [name_generator](#name_generator) | [puzzles](#puzzles) | [random_string_generator](#random_string_generator) |
| [red_button](#red_button) | [rpsystem](#rpsystem) | [simpledoor](#simpledoor) | [slow_exit](#slow_exit) | [storage](#storage) |
| [talking_npc](#talking_npc) | [traits](#traits) | [tree_select](#tree_select) | [turnbattle](#turnbattle) | [tutorial_world](#tutorial_world) |
| [unixcommand](#unixcommand) | [wilderness](#wilderness) | [xyzgrid](#xyzgrid) |



## base_systems

_系统不一定与特定的游戏机制相关，但对整个游戏有用。例子包括登录系统、新的命令语法和构建助手。_


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

_由 The Right Honourable Reverend (trhr) 提供的贡献，2020年_

此插件将 Evennia 的基于 Web 的部分迁移到 Amazon AWS（S3）云托管，主要涉及图像、JavaScript 和其他位于 staticfiles 中的项目。非常适合那些在游戏中提供媒体的服务器。

[阅读文档](./Contrib-AWSStorage.md) - [浏览代码](api:evennia.contrib.base_systems.awsstorage)



### `building_menu`

_由 vincent-lg 贡献，2018年_

构建菜单是在游戏内的菜单，类似于 `EvMenu`，但采用了不同的方法。构建菜单特别设计用于作为构建者编辑信息。在命令中创建构建菜单可以让构建者快速编辑给定对象，比如一个房间。如果你按照步骤添加这个贡献，你将可以使用 `edit` 命令来编辑任何默认对象，提供更改其键和描述的功能。

[阅读文档](./Contrib-Building-Menu.md) - [浏览代码](api:evennia.contrib.base_systems.building_menu)



### `color_markups`

_由 Griatch 贡献，2017年_

为 Evennia 提供额外的颜色标记样式（扩展或替换默认的 `|r`, `|234`）。添加对 MUSH 风格 (`%cr`, `%c123`) 和/或 传统 Evennia (`{r`, `{123`) 的支持。

[阅读文档](./Contrib-Color-Markups.md) - [浏览代码](api:evennia.contrib.base_systems.color_markups)



### `components`

_由 ChrisLR 贡献，2021年_

使用组件/组合方法扩展类型类。

[阅读文档](./Contrib-Components.md) - [浏览代码](api:evennia.contrib.base_systems.components)



### `custom_gametime`

_由 vlgeoff 贡献（2017）- 基于 Griatch 的核心原始实现_

这个模块重写了 `evennia.utils.gametime`，但使用了一个 _自定义_ 日历（每周/月/年等的天数不寻常）以适应您的游戏世界。与原始模块一样，它允许安排在指定的游戏时间发生的事件，但现在考虑到这个自定义日历。

[阅读文档](./Contrib-Custom-Gametime.md) - [浏览代码](api:evennia.contrib.base_systems.custom_gametime)



### `email_login`

_贡献者：Griatch, 2012_

这是一个登录系统的变体，它要求用户输入电子邮件地址而不是用户名进行登录。请注意，它不验证电子邮件，只使用其作为标识符，而不是用户名。

[阅读文档](./Contrib-Email-Login.md) - [浏览代码](api:evennia.contrib.base_systems.email_login)



### `godotwebsocket`

_由 ChrisLR 贡献于 2022 年_

此模块允许您将 Godot 客户端直接连接到您的 MUD，并在 Godot 的 RichTextLabel 中使用 BBCode 显示带颜色的常规文本。您可以使用 Godot 提供具有适当 Evennia 支持的高级功能。

[阅读文档](./Contrib-Godotwebsocket.md) - [浏览代码](api:evennia.contrib.base_systems.godotwebsocket)



### `ingame_python`

_由 Vincent Le Goff 贡献于在 2017 年_

这个模块增加了在游戏中使用 Python 脚本的能力。它允许值得信任的工作人员或建造者动态地为单个对象添加功能和触发器，而无需在外部 Python 模块中进行操作。通过在游戏中使用自定义 Python，可以使特定的房间、出口、角色、对象等表现得与其“同类”不同。这类似于 MU 的软代码或 DIKU 的 MudProgs。然而，请记住，允许在游戏中使用 Python 会带来严重的安全问题（您必须非常信任您的建造者），因此在继续之前请仔细阅读此模块中的警告。

[阅读文档](./Contrib-Ingame-Python.md) - [浏览代码](api:evennia.contrib.base_systems.ingame_python)



### `ingame_reports`

_由 InspectorCaracal 贡献，2024_

这个贡献提供了一个游戏内报告系统，默认处理错误报告、玩家报告和创意提交。它还支持添加您自己的报告类型，或删除任何默认的报告类型。

[阅读文档](./Contrib-Ingame-Reports.md) - [浏览代码](api:evennia.contrib.base_systems.ingame_reports)



### `menu_login`

_由 Vincent-lg 贡献于 2016 年，Griatch 于 2019 年为现代 EvMenu 重新制作。_

此系统将 Evennia 的登录过程更改为通过一系列问题询问账户名和密码，而不是要求一次性输入。这是通过 Evennia 的菜单系统 `EvMenu` 实现的。

[阅读文档](./Contrib-Menu-Login.md) - [浏览代码](api:evennia.contrib.base_systems.menu_login)



### `mux_comms_cmds`

_由 Griatch 贡献于 2021 年_

在 Evennia 1.0+ 中，旧的频道命令（最初受 MUX 启发）被一个执行所有这些功能的单一 `channel` 命令所取代。这个贡献模块（从 Evennia 0.9.5 中提取）将功能分解为更符合 MU* 用户习惯的独立命令。不过，这仅仅是为了展示，主要的 `channel` 命令在底层仍然被调用。

[阅读文档](./Contrib-Mux-Comms-Cmds.md) - [浏览代码](api:evennia.contrib.base_systems.mux_comms_cmds)



### `unixcommand`

_由 Vincent Le Geoff (vlgeoff) 于 2017 年贡献_

此模块包含一个命令类，使用替代语法解析器在游戏中实现 Unix 风格的命令语法。这意味着可以使用 `--options`、位置参数以及类似 `-n 10` 的语法。对于普通玩家来说，这可能不是最佳语法，但对于构建者来说，当他们需要一个命令执行多种功能并带有多种选项时，这可能非常有用。它在底层使用 Python 标准库中的 `ArgumentParser`。

[阅读文档](./Contrib-Unixcommand.md) - [浏览代码](api:evennia.contrib.base_systems.unixcommand)






## full_systems

_'完整'的游戏引擎，可以直接用于开始创建内容，无需进一步添加（除非你想要）。_


```{toctree}
:hidden:
Contribs-Guidelines.md
```
```{toctree}
:maxdepth: 1

Contrib-Evscaperoom.md
```


### `evscaperoom`

_贡献者：Griatch, 2019_

这是一个完整的引擎，用于在 Evennia 中创建多人逃脱室。允许玩家生成和加入独立跟踪状态的解谜房间。任何数量的玩家可以加入，共同解决一个房间。这是为 “EvscapeRoom” 创建的引擎，该游戏在2019年4月至5月期间的 MUD Coders Guild “单房间” 游戏创作竞赛中获胜。此贡献仅包含非常少量的游戏内容，仅包含实用工具和基础类以及一个空的示例房间。

[阅读文档](./Contrib-Evscaperoom.md) - [浏览代码](api:evennia.contrib.full_systems.evscaperoom)






## game_systems

_游戏内的游戏玩法系统，如制作、邮件、战斗等。每个系统都可以单独采用并用于你的游戏。这不包括角色扮演特定的系统，那些在 `rpg` 类别中。_


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

_一个简单但相当全面的成就追踪系统。成就使用普通的 Python 字典定义，类似于核心原型系统，虽然期望你只在角色或账户上使用，但它们可以在任何类型类对象上跟踪。_

该贡献提供了几个用于追踪和访问成就的函数，以及一个基本的游戏内命令用于查看成就状态。

[阅读文档](./Contrib-Achievements.md) - [浏览代码](api:evennia.contrib.game_systems.achievements)



### `barter`

_由 Griatch 贡献，2012年_

此模块实现了完整的物物交换系统——一个安全地让玩家之间在代码中交易物品的方式，而不是简单的 `give/get` 命令。这提高了安全性（任何时候一名玩家都不会同时拥有商品和付款）和效率，因为已经达成的交易会自动进行。通过将一方替换为金币对象（或金币与商品的组合），这也适用于常规货币交易。

[阅读文档](./Contrib-Barter.md) - [浏览代码](api:evennia.contrib.game_systems.barter)



### `clothing`

_由 Tim Ashley Jenkins 贡献，2017年_

提供了可穿戴衣物的类型类和命令。这些衣物的外观在角色穿戴时会附加到角色描述中。

[阅读文档](./Contrib-Clothing.md) - [浏览代码](api:evennia.contrib.game_systems.clothing)



### `containers`

_由 InspectorCaracal 贡献（2023）_

添加将对象放入其他容器对象的能力，提供容器类型类并扩展某些基本命令。

[阅读文档](./Contrib-Containers.md) - [浏览代码](api:evennia.contrib.game_systems.containers)



### `cooldowns`

_由 owllex 贡献（2021）_

冷却时间用于建模速率限制的操作，如角色可执行特定操作的频率；在某些时间过去之前，其命令不能再次使用。此贡献提供了一个简单的冷却时间处理器，可以附加到任何类型类上。冷却时间是一个轻量级的持久异步计时器，您可以查询以查看某段时间是否已经过去。

[阅读文档](./Contrib-Cooldowns.md) - [浏览代码](api:evennia.contrib.game_systems.cooldowns)



### `crafting`

_由 Griatch 贡献（2020）_

这实现了一个完整的制作系统。其原理是基于“配方”，您可以将物品（标记为原料）组合起来创造出新的东西。配方还可以要求某些（不被消耗的）工具。例如，使用“面包配方”将“面粉”、“水”和“酵母”与“烤箱”组合在一起，以烘焙“一个面包条”。

[阅读文档](./Contrib-Crafting.md) - [浏览代码](api:evennia.contrib.game_systems.crafting)



### `gendersub`

_由 Griatch 贡献于 2015 年_

这是一个简单的性别感知角色类，允许用户在文本中插入自定义标记以指示性别感知消息。它依赖于一个修改过的 `msg()` 方法，旨在为如何实现此类功能提供灵感和起点。

[阅读文档](./Contrib-Gendersub.md) - [浏览代码](api:evennia.contrib.game_systems.gendersub)



### `mail`

_由 grungies1138 贡献，2016_

这是一个简单的 Brandymail 风格邮件系统，使用 Evennia Core 的 `Msg` 类。它提供了两个命令，用于在账户之间（游戏外）或角色之间（游戏内）发送邮件。这两种类型的邮件可以一起使用，也可以单独使用。

[阅读文档](./Contrib-Mail.md) - [浏览代码](api:evennia.contrib.game_systems.mail)



### `multidescer`

_由 Griatch 贡献于 2016 年_

“多重描述器”是来自 MUSH 世界的一个概念。它允许将你的描述拆分为任意命名的“部分”，然后可以随意替换。这是一种快速管理外观的方法（例如更换衣服），适用于更自由形式的角色扮演系统。这也可以很好地与 `rpsystem` 贡献模块配合使用。

[阅读文档](./Contrib-Multidescer.md) - [浏览代码](api:evennia.contrib.game_systems.multidescer)



### `puzzles`

_由 Henddher 贡献于 2018 年_

该系统旨在用于冒险游戏风格的组合谜题，例如将水果和搅拌机组合以制作奶昔。它为可以组合（即一起使用）的对象提供了一个类型类和命令。与 `crafting` 贡献不同，每个谜题都是由独特的对象构建的，构建者可以完全在游戏中创建谜题。

[阅读文档](./Contrib-Puzzles.md) - [浏览代码](api:evennia.contrib.game_systems.puzzles)



### `storage`

_由 helpme 贡献于 2024 年_

该模块允许将某些房间标记为存储位置。

[阅读文档](./Contrib-Storage.md) - [浏览代码](api:evennia.contrib.game_systems.storage)



### `turnbattle`

_由 Tim Ashley Jenkins 于 2017 年贡献_

这是一个简单的回合制战斗系统框架，类似于 D&D 风格的桌面角色扮演游戏。它允许任何角色在房间中开始战斗，此时将掷骰决定先攻顺序，并建立回合顺序。战斗中的每个参与者在该回合中有有限的时间来决定他们的行动（默认情况下为 30 秒），战斗按照回合顺序进行，循环遍历参与者直到战斗结束。

[阅读文档](./Contrib-Turnbattle.md) - [浏览代码](api:evennia.contrib.game_systems.turnbattle)






## grid

_与游戏世界的拓扑和结构相关的系统。与房间、出口和地图构建相关的贡献。_


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

_贡献者 - Griatch 2012, vincent-lg 2019, Griatch 2023_

该功能扩展了正常的 `Room` 类型类，允许其描述根据时间、季节或其他状态（如洪水或黑暗）而变化。在描述中嵌入 `$state(burning, This place is on fire!)` 将允许根据房间状态更改描述。该房间还支持供玩家查看的 `details`（无需为每一个对象创建新的游戏内对象），并支持随机回声。该房间带有一组替代的 `look` 和 `@desc` 命令，以及新的命令 `detail`、`roomstate` 和 `time`。

[阅读文档](./Contrib-Extended-Room.md) - [浏览代码](api:evennia.contrib.grid.extended_room)



### `ingame_map_display`

_贡献者 - helpme 2022_

这个模块为给定的房间添加一个 ASCII `地图`，可以通过 `map` 命令查看。您可以轻松修改它以添加特殊字符、房间颜色等。显示的地图是在使用时动态生成的，支持所有罗盘方向以及上下方向。其他方向将被忽略。

[阅读文档](./Contrib-Ingame-Map-Display.md) - [浏览代码](api:evennia.contrib.grid.ingame_map_display)



### `mapbuilder`

_贡献者：Cloud_Keeper 2016_

根据2D ASCII地图的绘图构建游戏地图。

[阅读文档](./Contrib-Mapbuilder.md) - [浏览代码](api:evennia.contrib.grid.mapbuilder)



### `simpledoor`

_由 Griatch 贡献于 2016 年_

这是一个简单的双向出口，代表可以从两侧打开和关闭的门。可以轻松扩展以使其可锁定、可破坏等。

[阅读文档](./Contrib-Simpledoor.md) - [浏览代码](api:evennia.contrib.grid.simpledoor)



### `slow_exit`

_由 Griatch 于 2014 年贡献_

这是一个延迟穿越的 Exit 类型示例。这模拟了许多游戏中常见的缓慢移动。该 contrib 还包含两个命令，`setspeed` 和 `stop`，分别用于更改移动速度和中止正在进行的穿越。

[阅读文档](./Contrib-Slow-Exit.md) - [浏览代码](api:evennia.contrib.grid.slow_exit)



### `wilderness`

_由 titeuf87 贡献，2017年_

这个贡献提供了一个荒野地图，而不需要实际创建大量房间——在你移动时，你实际上会回到同一个房间，但其描述会发生变化。这意味着你可以用较少的数据库存储创建大面积的地图，只要房间相对相似（例如，只有名称/描述变化）。

[阅读文档](./Contrib-Wilderness.md) - [浏览代码](api:evennia.contrib.grid.wilderness)



### `xyzgrid`

_贡献者：Griatch 2021_

将Evennia的游戏世界放置在一个xy（z代表不同地图）坐标网格上。通过绘制和解析2D ASCII 地图，包括传送、地图转换和特殊标记，外部创建和维护网格，以帮助寻路。支持每个地图的非常快速的最短路由寻路。还包括一个快速查看功能，可以查看离当前地点仅限数量的步骤（在游戏中显示网格作为更新地图时非常有用）。

[阅读文档](./Contrib-XYZGrid.md) - [浏览代码](api:evennia.contrib.grid.xyzgrid)






## rpg

_专门与角色扮演和规则实现相关的系统，如角色特征、掷骰子和表情。_


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

_由 Tegiminis 贡献，2022年_

Buff 是一个定时对象，附加到游戏实体上。它能够修改值、触发代码，或两者兼而有之。这在 RPG，特别是动作游戏中是一种常见的设计模式。

[阅读文档](./Contrib-Buffs.md) - [浏览代码](api:evennia.contrib.rpg.buffs)



### `character_creator`

_由 InspectorCaracal 贡献，2022年_

用于管理和启动游戏内角色创建菜单的命令。

[阅读文档](./Contrib-Character-Creator.md) - [浏览代码](api:evennia.contrib.rpg.character_creator)



### `dice`

_由 Griatch 贡献，2012, 2023_

一个骰子滚动器，可以处理任意数量和面数的骰子。支持游戏内骰子掷骰（例如 `roll 2d10 + 1`），以及条件掷骰（低于/高于/等于目标）和用于代码中掷骰的函数。命令还支持隐藏或秘密掷骰，以供人类游戏主持人使用。

[阅读文档](./Contrib-Dice.md) - [浏览代码](api:evennia.contrib.rpg.dice)



### `health_bar`

_由 Tim Ashley Jenkins 贡献于 2017 年_

此模块提供的函数让您可以轻松地将视觉条或计量器显示为彩色条，而不仅仅是一个数字。"血条" 只是其中最明显的用途，但该条高度可定制，可以用于除玩家健康外的任何适当数据。

[阅读文档](./Contrib-Health-Bar.md) - [浏览代码](api:evennia.contrib.rpg.health_bar)



### `llm`

_由 Griatch 贡献，2023_

此贡献添加了一个 LLMClient，使 Evennia 能够将提示发送到 LLM 服务器（大型语言模型，如 ChatGPT）。示例使用本地 OSS LLM 安装。包括一个可以使用新 `talk` 命令聊天的 NPC。NPC 将使用 LLM 服务器的 AI 响应进行回复。所有调用都是异步的，因此即使 LLM 速度慢，Evennia 也不受影响。

[阅读文档](./Contrib-Llm.md) - [浏览代码](api:evennia.contrib.rpg.llm)



### `rpsystem`

_由 Griatch 贡献于 2015 年_

这是一个完整的角色扮演表情系统。包括简短描述和识别（在你为他们分配名字之前，只能通过外貌认识人）。房间姿势。面具/伪装（隐藏你的描述）。可以直接在表情中说话，带有可选的语言混淆（如果你不懂语言，单词会被混淆，你也可以有不同语言的不同“声音”混淆）。耳语可以从远处部分听到。一个非常强大的表情内引用系统，用于引用和区分目标（包括对象）。

[阅读文档](./Contrib-RPSystem.md) - [浏览代码](api:evennia.contrib.rpg.rpsystem)



### `traits`

_由 Griatch 于 2020 年贡献，基于 Whitenoise 和 Ainneve 的贡献代码，2014 年_

`Trait` 代表一个（通常是）角色上的可修改属性。它们可以用于表示从属性（力量、敏捷等）到技能（狩猎 10、剑术 14 等）以及动态变化的事物（如 HP、XP 等）。特质与普通属性的不同之处在于，它们跟踪其变化并限制在特定的数值范围内。可以轻松地对它们进行加减运算，甚至可以以特定的速率动态变化（例如中毒或治疗）。

[阅读文档](./Contrib-Traits.md) - [浏览代码](api:evennia.contrib.rpg.traits)






## tutorials

_专门用于教授开发概念或示例 Evennia 系统的帮助资源。任何与文档教程相关的额外资源都在这里。也是教程世界和 Evadventure 演示代码的家。_


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

_由 Griatch 贡献，2012年_

这是用于批处理器的简单示例。批处理器用于从一个或多个静态文件生成游戏内内容。文件可以使用版本控制存储，然后“应用”到游戏中以创建内容。

[阅读文档](./Contrib-Batchprocessor.md) - [浏览代码](api:evennia.contrib.tutorials.batchprocessor)



### `bodyfunctions`

_由 Griatch 贡献，2012年_

这是一个用于测试的示例脚本。该脚本添加了一个简单的计时器，让你的角色在不规则的间隔内进行小的口头观察。

[阅读文档](./Contrib-Bodyfunctions.md) - [浏览代码](api:evennia.contrib.tutorials.bodyfunctions)



### `evadventure`

_贡献者：Griatch 2023-_

> **注意** - 本教程仍在进行中，尚未完成！您仍然可以从中学习，但不要期待完美。

[阅读文档](./Contrib-Evadventure.md) - [浏览代码](api:evennia.contrib.tutorials.evadventure)



### `mirror`

_由 Griatch 贡献于 2017 年_

这是一个简单的镜子对象，用于实验。它会对被查看时做出响应。

[阅读文档](./Contrib-Mirror.md) - [浏览代码](api:evennia.contrib.tutorials.mirror)



### `red_button`

_由 Griatch 贡献于 2011 年_

一个可以按下以产生效果的红色按钮。这是一个更高级的示例对象，具有自己的功能和状态跟踪。

[阅读文档](./Contrib-Red-Button.md) - [浏览代码](api:evennia.contrib.tutorials.red_button)



### `talking_npc`

_由 Griatch 于 2011 年贡献，grungies1138 于 2016 年更新_

这是一个能够进行简单菜单驱动对话的静态 NPC 对象示例。适合作为任务发布者或商人。

[阅读文档](./Contrib-Talking-Npc.md) - [浏览代码](api:evennia.contrib.tutorials.talking_npc)



### `tutorial_world`

_由 Griatch 于 2011 和 2015 年贡献_

这是一个适用于未修改的 Evennia 安装的独立教程区域。可以将其视为一种单人冒险，而不是一个完整的多人游戏世界。各种房间和物品旨在展示 Evennia 的功能，而不是提供非常具有挑战性（或长时间）的游戏体验。因此，它当然只是略微触及了可能性。拆解这个教程是学习系统的一个很好的起点。

[阅读文档](./Contrib-Tutorial-World.md) - [浏览代码](api:evennia.contrib.tutorials.tutorial_world)






## utils

_杂项，文本操作工具、安全审计等。_


```{toctree}
:hidden:
Contribs-Guidelines.md
```
```{toctree}
:maxdepth: 1

Contrib-Auditing.md
Contrib-Debugpy.md
Contrib-Fieldfill.md
Contrib-Git-Integration.md
Contrib-Name-Generator.md
Contrib-Random-String-Generator.md
Contrib-Tree-Select.md
```


### `auditing`

_由 Johnny 提供的贡献，2017年_

这是一个实用工具，可以拦截与客户端和服务器之间发送的所有数据，并将其传递给你选择的回调。这旨在进行质量保证、事故后的调查和调试。

[阅读文档](./Contrib-Auditing.md) - [浏览代码](api:evennia.contrib.utils.auditing)



### `debugpy`

_由 electroglyph 贡献（2025）_

此模块注册了一个游戏内命令 `debugpy`，该命令启动 debugpy 调试器并监听 5678 端口。现在，它仅适用于 Visual Studio Code (VS Code)。

[阅读文档](./Contrib-Debugpy.md) - [浏览代码](api:evennia.contrib.utils.debugpy)



### `fieldfill`

_贡献者 - Tim Ashley Jenkins, 2018_

此模块包含一个生成 `EvMenu` 的函数，该菜单为玩家提供了一个可以按任意顺序填写的表单（例如用于角色生成或构建）。每个字段的值可以进行验证，函数允许对文本和整数输入进行轻松检查，设定最小值和最大值/字符长度，或者通过自定义函数进行验证。一旦表单提交，表单的数据将作为字典提交给您选择的任何可调用对象。

[阅读文档](./Contrib-Fieldfill.md) - [浏览代码](api:evennia.contrib.utils.fieldfill)



### `git_integration`

_由 helpme 贡献于 2022 年_

这是一个模块，用于在游戏中集成精简版的 git，允许开发者查看 git 状态、更改分支，以及拉取本地 mygame 仓库和 Evennia 核心的更新代码。在成功拉取或检出后，git 命令将重载游戏：某些更改可能需要手动重启，以影响持久化脚本等。

[阅读文档](./Contrib-Git-Integration.md) - [浏览代码](api:evennia.contrib.utils.git_integration)



### `name_generator`

_由 InspectorCaracal 贡献（2022 年）_

这是一个用于生成真实世界和幻想世界名字的模块。真实世界的名字可以生成为名字（个人名）、姓氏（家族名）或全名（名字、可选的中间名和姓氏）。名字数据来自 [Behind the Name](https://www.behindthename.com/)，并在 [CC BY-SA 4.0 许可](https://creativecommons.org/licenses/by-sa/4.0/)下使用。

[阅读文档](./Contrib-Name-Generator.md) - [浏览代码](api:evennia.contrib.utils.name_generator)



### `random_string_generator`

_由 Vincent Le Goff (vlgeoff) 贡献于 2017 年_

这个实用程序可以用于根据特定标准生成伪随机的信息字符串。例如，你可以用它来生成电话号码、车牌号、验证码、游戏内的安全密码等。生成的字符串将被存储且不会重复。

[阅读文档](./Contrib-Random-String-Generator.md) - [浏览代码](api:evennia.contrib.utils.random_string_generator)



### `tree_select`

_由 Tim Ashley Jenkins 于 2017 年贡献_

此工具允许您通过传递给一个函数的多行字符串创建和初始化整个分支的 EvMenu 实例。

[阅读文档](./Contrib-Tree-Select.md) - [浏览代码](api:evennia.contrib.utils.tree_select)







----

<small>此文档页面是自动生成的。手动更改将被覆盖。</small>
