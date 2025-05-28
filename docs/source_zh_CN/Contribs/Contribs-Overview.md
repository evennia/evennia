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

_Contrib by The Right Honourable Reverend (trhr), 2020_

This plugin migrates the Web-based portion of Evennia, namely images,
javascript, and other items located inside staticfiles into Amazon AWS (S3)
cloud hosting. Great for those serving media with the game.

[阅读文档](./Contrib-AWSStorage.md) - [浏览代码](api:evennia.contrib.base_systems.awsstorage)



### `building_menu`

_Contrib by vincent-lg, 2018_

Building menus are in-game menus, not unlike `EvMenu` though using a
different approach. Building menus have been specifically designed to edit
information as a builder. Creating a building menu in a command allows
builders quick-editing of a given object, like a room. If you follow the
steps to add the contrib, you will have access to an `edit` command
that will edit any default object, offering to change its key and description.

[阅读文档](./Contrib-Building-Menu.md) - [浏览代码](api:evennia.contrib.base_systems.building_menu)



### `color_markups`

_Contrib by Griatch, 2017_

Additional color markup styles for Evennia (extending or replacing the default
`|r`, `|234`). Adds support for MUSH-style (`%cr`, `%c123`) and/or legacy-Evennia
(`{r`, `{123`).

[阅读文档](./Contrib-Color-Markups.md) - [浏览代码](api:evennia.contrib.base_systems.color_markups)



### `components`

_Contrib by ChrisLR, 2021_

Expand typeclasses using a components/composition approach.

[阅读文档](./Contrib-Components.md) - [浏览代码](api:evennia.contrib.base_systems.components)



### `custom_gametime`

_Contrib by vlgeoff, 2017 - based on Griatch's core original_

This reimplements the `evennia.utils.gametime` module but with a _custom_
calendar (unusual number of days per week/month/year etc) for your game world.
Like the original, it allows for scheduling events to happen at given
in-game times, but now taking this custom calendar into account.

[阅读文档](./Contrib-Custom-Gametime.md) - [浏览代码](api:evennia.contrib.base_systems.custom_gametime)



### `email_login`

_Contrib by Griatch, 2012_

This is a variant of the login system that asks for an email-address
instead of a username to login. Note that it does not verify the email,
it just uses it as the identifier rather than a username.

[阅读文档](./Contrib-Email-Login.md) - [浏览代码](api:evennia.contrib.base_systems.email_login)



### `godotwebsocket`

_Contribution by ChrisLR, 2022_

This contrib allows you to connect a Godot Client directly to your mud,
and display regular text with color in Godot's RichTextLabel using BBCode.
You can use Godot to provide advanced functionality with proper Evennia support.

[阅读文档](./Contrib-Godotwebsocket.md) - [浏览代码](api:evennia.contrib.base_systems.godotwebsocket)



### `ingame_python`

_Contrib by Vincent Le Goff 2017_

This contrib adds the ability to script with Python in-game. It allows trusted
staff/builders to dynamically add features and triggers to individual objects
without needing to do it in external Python modules. Using custom Python in-game,
specific rooms, exits, characters, objects etc can be made to behave differently from
its "cousins". This is similar to how softcode works for MU or MudProgs for DIKU.
Keep in mind, however, that allowing Python in-game comes with _severe_
security concerns (you must trust your builders deeply), so read the warnings in
this module carefully before continuing.

[阅读文档](./Contrib-Ingame-Python.md) - [浏览代码](api:evennia.contrib.base_systems.ingame_python)



### `ingame_reports`

_Contrib by InspectorCaracal, 2024_

This contrib provides an in-game reports system, handling bug reports, player reports, and idea submissions by default. It also supports adding your own types of reports, or removing any of the default report types.

[阅读文档](./Contrib-Ingame-Reports.md) - [浏览代码](api:evennia.contrib.base_systems.ingame_reports)



### `menu_login`

_Contribution by Vincent-lg 2016. Reworked for modern EvMenu by Griatch, 2019._

This changes the Evennia login to ask for the account name and password as a series
of questions instead of requiring you to enter both at once. It uses Evennia's 
menu system `EvMenu` under the hood.

[阅读文档](./Contrib-Menu-Login.md) - [浏览代码](api:evennia.contrib.base_systems.menu_login)



### `mux_comms_cmds`

_Contribution by Griatch 2021_

In Evennia 1.0+, the old Channel commands (originally inspired by MUX) were
replaced by the single `channel` command that performs all these functions.
This contrib (extracted from Evennia 0.9.5) breaks out the functionality into 
separate Commands more familiar to MU* users. This is just for show though, the 
main `channel` command is still called under the hood.

[阅读文档](./Contrib-Mux-Comms-Cmds.md) - [浏览代码](api:evennia.contrib.base_systems.mux_comms_cmds)



### `unixcommand`

_Contribution by Vincent Le Geoff (vlgeoff), 2017_

This module contains a command class with an alternate syntax parser implementing
Unix-style command syntax in-game. This means `--options`, positional arguments
and stuff like `-n 10`. It might not the best syntax for the average player
but can be really useful for builders when they need to have a single command do
many things with many options. It uses the `ArgumentParser` from Python's standard
library under the hood.

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

_Contribution by Griatch, 2019_

A full engine for creating multiplayer escape-rooms in Evennia. Allows players to
spawn and join puzzle rooms that track their state independently. Any number of players
can join to solve a room together. This is the engine created for 'EvscapeRoom', which won
the MUD Coders Guild "One Room" Game Jam in April-May, 2019. The contrib has only
very minimal game content, it contains the utilities and base classes and an empty example room.

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

_A simple, but reasonably comprehensive, system for tracking achievements. Achievements are defined using ordinary Python dicts, reminiscent of the core prototypes system, and while it's expected you'll use it only on Characters or Accounts, they can be tracked for any typeclassed object._

The contrib provides several functions for tracking and accessing achievements, as well as a basic in-game command for viewing achievement status.

[阅读文档](./Contrib-Achievements.md) - [浏览代码](api:evennia.contrib.game_systems.achievements)



### `barter`

_Contribution by Griatch, 2012_

This implements a full barter system - a way for players to safely
trade items between each other in code rather than simple `give/get`
commands. This increases both safety (at no time will one player have 
both goods and payment in-hand) and speed, since agreed goods will 
be moved automatically). By just replacing one side with coin objects,
(or a mix of coins and goods), this also works fine for regular money 
transactions.

[阅读文档](./Contrib-Barter.md) - [浏览代码](api:evennia.contrib.game_systems.barter)



### `clothing`

_Contribution by Tim Ashley Jenkins, 2017_

Provides a typeclass and commands for wearable clothing. These 
look of these clothes are appended to the character's description when worn.

[阅读文档](./Contrib-Clothing.md) - [浏览代码](api:evennia.contrib.game_systems.clothing)



### `containers`

_Adds the ability to put objects into other container objects by providing a container typeclass and extending certain base commands._

## Installation

[阅读文档](./Contrib-Containers.md) - [浏览代码](api:evennia.contrib.game_systems.containers)



### `cooldowns`

_Contribution by owllex, 2021_

Cooldowns are used to model rate-limited actions, like how often a
character can perform a given action; until a certain time has passed their
command can not be used again. This contrib provides a simple cooldown
handler that can be attached to any typeclass. A cooldown is a lightweight persistent
asynchronous timer that you can query to see if a certain time has yet passed.

[阅读文档](./Contrib-Cooldowns.md) - [浏览代码](api:evennia.contrib.game_systems.cooldowns)



### `crafting`

_Contribution by Griatch 2020_

This implements a full crafting system. The principle is that of a 'recipe',
where you combine items (tagged as ingredients) create something new. The recipe can also
require certain (non-consumed) tools. An example would be to use the 'bread recipe' to
combine 'flour', 'water' and 'yeast' with an 'oven' to bake a 'loaf of bread'.

[阅读文档](./Contrib-Crafting.md) - [浏览代码](api:evennia.contrib.game_systems.crafting)



### `gendersub`

_Contribution by Griatch 2015_

This is a simple gender-aware Character class for allowing users to
insert custom markers in their text to indicate gender-aware
messaging. It relies on a modified msg() and is meant as an
inspiration and starting point to how to do stuff like this.

[阅读文档](./Contrib-Gendersub.md) - [浏览代码](api:evennia.contrib.game_systems.gendersub)



### `mail`

_Contribution by grungies1138 2016_

A simple Brandymail style mail system that uses the `Msg` class from Evennia
Core. It has two Commands for either sending mails between Accounts (out of game)
or between Characters (in-game). The two types of mails can be used together or
on their own.

[阅读文档](./Contrib-Mail.md) - [浏览代码](api:evennia.contrib.game_systems.mail)



### `multidescer`

_Contribution by Griatch 2016_

A "multidescer" is a concept from the MUSH world. It allows for
splitting your descriptions into arbitrary named 'sections' which you can
then swap out at will. It is a way for quickly managing your look (such as when
changing clothes) in more free-form roleplaying systems. This will also
work well together with the `rpsystem` contrib.

[阅读文档](./Contrib-Multidescer.md) - [浏览代码](api:evennia.contrib.game_systems.multidescer)



### `puzzles`

_Contribution by Henddher 2018_

Intended for adventure-game style combination puzzles, such as combining fruits
and a blender to create a smoothie. Provides a typeclass and commands for objects 
that can be combined (i.e. used together). Unlike the `crafting` contrib, each 
puzzle is built from unique objects rather than using tags and a builder can create 
the puzzle entirely from in-game.

[阅读文档](./Contrib-Puzzles.md) - [浏览代码](api:evennia.contrib.game_systems.puzzles)



### `storage`

_Contribution by helpme (2024)_

This module allows certain rooms to be marked as storage locations.

[阅读文档](./Contrib-Storage.md) - [浏览代码](api:evennia.contrib.game_systems.storage)



### `turnbattle`

_Contribution by Tim Ashley Jenkins, 2017_

This is a framework for a simple turn-based combat system, similar
to those used in D&D-style tabletop role playing games. It allows
any character to start a fight in a room, at which point initiative
is rolled and a turn order is established. Each participant in combat
has a limited time to decide their action for that turn (30 seconds by
default), and combat progresses through the turn order, looping through
the participants until the fight ends.

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

_Contribution - Griatch 2012, vincent-lg 2019, Griatch 2023_

This extends the normal `Room` typeclass to allow its description to change with
time-of-day and/or season as well as any other state (like flooded or dark).
Embedding `$state(burning, This place is on fire!)` in the description will
allow for changing the description based on room state. The room also supports
`details` for the player to look at in the room (without having to create a new
in-game object for each), as well as support for random echoes. The room
comes with a set of alternate commands for `look` and `@desc`, as well as new
commands `detail`, `roomstate` and `time`.

[阅读文档](./Contrib-Extended-Room.md) - [浏览代码](api:evennia.contrib.grid.extended_room)



### `ingame_map_display`

_Contribution - helpme 2022_

This adds an ascii `map` to a given room which can be viewed with the `map` command.
You can easily alter it to add special characters, room colors etc. The map shown is
dynamically generated on use, and supports all compass directions and up/down. Other
directions are ignored.

[阅读文档](./Contrib-Ingame-Map-Display.md) - [浏览代码](api:evennia.contrib.grid.ingame_map_display)



### `mapbuilder`

_Contribution by Cloud_Keeper 2016_

Build a game map from the drawing of a 2D ASCII map.

[阅读文档](./Contrib-Mapbuilder.md) - [浏览代码](api:evennia.contrib.grid.mapbuilder)



### `simpledoor`

_Contribution by Griatch, 2016_

A simple two-way exit that represents a door that can be opened and
closed from both sides. Can easily be expanded to make it lockable, 
destroyable etc. 

[阅读文档](./Contrib-Simpledoor.md) - [浏览代码](api:evennia.contrib.grid.simpledoor)



### `slow_exit`

_Contribution by Griatch 2014_

An example of an Exit-type that delays its traversal. This simulates
slow movement, common in many games. The contrib also
contains two commands, `setspeed` and `stop` for changing the movement speed
and abort an ongoing traversal, respectively.

[阅读文档](./Contrib-Slow-Exit.md) - [浏览代码](api:evennia.contrib.grid.slow_exit)



### `wilderness`

_Contribution by titeuf87, 2017_

This contrib provides a wilderness map without actually creating a large number
of rooms - as you move, you instead end up back in the same room but its description
changes. This means you can make huge areas with little database use as
long as the rooms are relatively similar (e.g. only the names/descs changing).

[阅读文档](./Contrib-Wilderness.md) - [浏览代码](api:evennia.contrib.grid.wilderness)



### `xyzgrid`

_Contribution by Griatch 2021_

Places Evennia's game world on an xy (z being different maps) coordinate grid.
Grid is created and maintained externally by drawing and parsing 2D ASCII maps,
including teleports, map transitions and special markers to aid pathfinding.
Supports very fast shortest-route pathfinding on each map. Also includes a
fast view function for seeing only a limited number of steps away from your
current location (useful for displaying the grid as an in-game, updating map).

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

_Contribution by Tegiminis 2022_

A buff is a timed object, attached to a game entity. It is capable of modifying values, triggering code, or both. 
It is a common design pattern in RPGs, particularly action games.

[阅读文档](./Contrib-Buffs.md) - [浏览代码](api:evennia.contrib.rpg.buffs)



### `character_creator`

_Contribution by InspectorCaracal, 2022_

Commands for managing and initiating an in-game character-creation menu.

[阅读文档](./Contrib-Character-Creator.md) - [浏览代码](api:evennia.contrib.rpg.character_creator)



### `dice`

_Contribution by Griatch, 2012, 2023_

A dice roller for any number and side of dice. Adds in-game dice rolling
(like `roll 2d10 + 1`) as well as conditionals (roll under/over/equal to a target)
and functions for rolling dice in code. Command also supports hidden or secret
rolls for use by a human game master.

[阅读文档](./Contrib-Dice.md) - [浏览代码](api:evennia.contrib.rpg.dice)



### `health_bar`

_Contribution by Tim Ashley Jenkins, 2017_

The function provided in this module lets you easily display visual
bars or meters as a colorful bar instead of just a number. A "health bar"
is merely the most obvious use for this, but the bar is highly customizable
and can be used for any sort of appropriate data besides player health.

[阅读文档](./Contrib-Health-Bar.md) - [浏览代码](api:evennia.contrib.rpg.health_bar)



### `llm`

_Contribution by Griatch 2023_

This adds an LLMClient that allows Evennia to send prompts to a  LLM server (Large Language Model, along the lines of ChatGPT). Example uses a local OSS LLM install. Included is an NPC you can chat with using a new `talk` command. The NPC will respond using the AI responses from the LLM server. All calls are asynchronous, so if the LLM is slow, Evennia is not affected.

[阅读文档](./Contrib-Llm.md) - [浏览代码](api:evennia.contrib.rpg.llm)



### `rpsystem`

_Contribution by Griatch, 2015_

A full roleplaying emote system. Short-descriptions and recognition (only know people by their looks until you assign a name to them). Room poses. Masks/disguises (hide your description). Speak directly in emote, with optional language obscuration (words get garbled if you don't know the language, you can also have different languages with different 'sounding' garbling). Whispers can be partly overheard from a distance. A very powerful in-emote reference system, for referencing and differentiate targets (including objects).

[阅读文档](./Contrib-RPSystem.md) - [浏览代码](api:evennia.contrib.rpg.rpsystem)



### `traits`

_Contribution by Griatch 2020, based on code by Whitenoise and Ainneve contribs, 2014_

A `Trait` represents a modifiable property on (usually) a Character. They can
be used to represent everything from attributes (str, agi etc) to skills
(hunting 10, swords 14 etc) and dynamically changing things like HP, XP etc.
Traits differ from normal Attributes in that they track their changes and limit
themselves to particular value-ranges. One can add/subtract from them easily and
they can even change dynamically at a particular rate (like you being poisoned or
healed).

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

_Contibution by Griatch, 2012_

Simple examples for the batch-processor. The batch processor is used for generating 
in-game content from one or more static files. Files can be stored with version 
control and then 'applied' to the game to create content.

[阅读文档](./Contrib-Batchprocessor.md) - [浏览代码](api:evennia.contrib.tutorials.batchprocessor)



### `bodyfunctions`

_Contribution by Griatch, 2012_

Example script for testing. This adds a simple timer that has your
character make small verbal observations at irregular intervals.

[阅读文档](./Contrib-Bodyfunctions.md) - [浏览代码](api:evennia.contrib.tutorials.bodyfunctions)



### `evadventure`

_Contrib by Griatch 2023-_


```{warning}
NOTE - this tutorial is WIP and NOT complete yet! You will still learn
things from it, but don't expect perfection.
```

[阅读文档](./Contrib-Evadventure.md) - [浏览代码](api:evennia.contrib.tutorials.evadventure)



### `mirror`

_Contribution by Griatch, 2017_

A simple mirror object to experiment with. It will respond to being looked at.

[阅读文档](./Contrib-Mirror.md) - [浏览代码](api:evennia.contrib.tutorials.mirror)



### `red_button`

_Contribution by Griatch, 2011_

A red button that you can press to have an effect. This is a more advanced example 
object with its own functionality and state tracking.

[阅读文档](./Contrib-Red-Button.md) - [浏览代码](api:evennia.contrib.tutorials.red_button)



### `talking_npc`

_Contribution by Griatch 2011. Updated by grungies1138, 2016_

This is an example of a static NPC object capable of holding a simple menu-driven
conversation. Suitable for example as a quest giver or merchant.

[阅读文档](./Contrib-Talking-Npc.md) - [浏览代码](api:evennia.contrib.tutorials.talking_npc)



### `tutorial_world`

_Contribution by Griatch 2011, 2015_

A stand-alone tutorial area for an unmodified Evennia install.
Think of it as a sort of single-player adventure rather than a
full-fledged multi-player game world. The various rooms and objects
are designed to show off features of Evennia, not to be a
very challenging (nor long) gaming experience. As such it's of course
only skimming the surface of what is possible. Taking this apart 
is a great way to start learning the system.

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

_Contribution by Johnny, 2017_

Utility that taps and intercepts all data sent to/from clients and the
server and passes it to a callback of your choosing. This is intended for 
quality assurance, post-incident investigations and debugging.

[阅读文档](./Contrib-Auditing.md) - [浏览代码](api:evennia.contrib.utils.auditing)



### `debugpy`

_Contribution by electroglyph, 2025_

This registers an in-game command `debugpy` which starts the debugpy debugger and listens on port 5678.
For now this is only available for Visual Studio Code (VS Code).

[阅读文档](./Contrib-Debugpy.md) - [浏览代码](api:evennia.contrib.utils.debugpy)



### `fieldfill`

_Contribution by Tim Ashley Jenkins, 2018_

This module contains a function that generates an `EvMenu` for you - this
menu presents the player with a form of fields that can be filled
out in any order (e.g. for character generation or building). Each field's value can 
be verified, with the function allowing easy checks for text and integer input, 
minimum and maximum values / character lengths, or can even be verified by a custom 
function. Once the form is submitted, the form's data is submitted as a dictionary 
to any callable of your choice.

[阅读文档](./Contrib-Fieldfill.md) - [浏览代码](api:evennia.contrib.utils.fieldfill)



### `git_integration`

_Contribution by helpme (2022)_

A module to integrate a stripped-down version of git within the game, allowing developers to view their git status, change branches, and pull updated code of both their local mygame repo and Evennia core. After a successful pull or checkout, the git command will reload the game: Manual restarts may be required to to apply certain changes that would impact persistent scripts etc.

[阅读文档](./Contrib-Git-Integration.md) - [浏览代码](api:evennia.contrib.utils.git_integration)



### `name_generator`

_Contribution by InspectorCaracal (2022)_

A module for generating random names, both real-world and fantasy. Real-world
names can be generated either as first (personal) names, family (last) names, or
full names (first, optional middles, and last). The name data is from [Behind the Name](https://www.behindthename.com/)
and used under the [CC BY-SA 4.0 license](https://creativecommons.org/licenses/by-sa/4.0/).

[阅读文档](./Contrib-Name-Generator.md) - [浏览代码](api:evennia.contrib.utils.name_generator)



### `random_string_generator`

_Contribution by Vincent Le Goff (vlgeoff), 2017_

This utility can be used to generate pseudo-random strings of information
with specific criteria.  You could, for instance, use it to generate
phone numbers, license plate numbers, validation codes, in-game security 
passwords and so on. The strings generated will be stored and won't be repeated.

[阅读文档](./Contrib-Random-String-Generator.md) - [浏览代码](api:evennia.contrib.utils.random_string_generator)



### `tree_select`

_Contribution by Tim Ashley Jenkins, 2017_

This utility allows you to create and initialize an entire branching EvMenu
instance from a multi-line string passed to one function.

[阅读文档](./Contrib-Tree-Select.md) - [浏览代码](api:evennia.contrib.utils.tree_select)







----

<small>此文档页面是自动生成的。手动更改将被覆盖。</small>
