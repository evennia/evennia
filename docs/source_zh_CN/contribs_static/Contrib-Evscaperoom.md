# EvscapeRoom

贡献者：Griatch, 2019

这是一个完整的引擎，用于在 Evennia 中创建多人逃脱室。允许玩家生成和加入独立跟踪状态的解谜房间。任何数量的玩家可以加入，共同解决一个房间。这是为 “EvscapeRoom” 创建的引擎，该游戏在2019年4月至5月期间的 MUD Coders Guild “单房间” 游戏创作竞赛中获胜。此贡献仅包含非常少量的游戏内容，仅包含实用工具和基础类以及一个空的示例房间。

## 介绍

EvscapeRoom，顾名思义，是一种文本形式的 [逃脱室](https://en.wikipedia.org/wiki/Escape_room)。你被锁在一个房间里，必须想办法逃出来。此贡献包含制作此类完整解谜游戏所需的一切。它还包含一个“大厅”，用于创建新房间，允许玩家加入其他人的房间进行合作解谜！

这是原始 _EvscapeRoom_ 的游戏引擎。它允许您重现相同的游戏体验，但不包含为游戏创作竞赛而创建的任何故事内容。如果您想查看完整的游戏（您必须逃离一个非常狡猾的小丑女孩的 cottage 或失去村庄的吃饼比赛……），可以在 Griatch 的 GitHub 页面找到 [这里](https://github.com/Griatch/evscaperoom)（但推荐使用以前在 Evennia 演示服务器上运行的版本，包含更多错误修复，可以在 [这里](https://github.com/evennia/evdemo/tree/master/evdemo/evscaperoom)找到）。

如果您想了解更多关于 _EvscapeRoom_ 的创建和设计的内容，可以阅读开发博客， [第一部分](https://www.evennia.com/devblog/2019.html#2019-05-18-creating-evscaperoom-part-1) 和 [第二部分](https://www.evennia.com/devblog/2019.html#2019-05-26-creating-evscaperoom-part-2)。

## 安装

EvscapeRoom 通过将 `evscaperoom` 命令添加到您的角色 cmdset 中进行安装。当您在游戏中运行该命令时，您就准备好开始游戏了！

在 `mygame/commands/default_cmdsets.py` 中：

```python
from evennia.contrib.full_systems.evscaperoom.commands import CmdEvscapeRoomStart

class CharacterCmdSet(...):

    # ...

    self.add(CmdEvscapeRoomStart())
```

重启服务器后，`evscaperoom` 命令将可用。该贡献附带一个小（非常小的）作为示例的逃脱房间。

## 创建您自己的 EvscapeRoom

要做到这一点，您需要创建自己的状态。首先确保您可以玩上面安装的简单示例房间。

将 `evennia/contrib/full_systems/evscaperoom/states` 复制到您的游戏文件夹中的某个地方（我们假设您将其放在 `mygame/world/` 下）。

接下来，您需要重新指向 Evennia 以查看这个新位置的状态。将以下内容添加到您的 `mygame/server/conf/settings.py` 文件中：

```python
EVSCAPEROOM_STATE_PACKAGE = "world.states"
```

重新加载后，示例 EvscapeRoom 应该仍然可以工作，但您现在可以从您的游戏目录修改和扩展它！

### 其他有用的设置

以下是一些可能有用的其他设置：

- `EVSCAPEROOM_START_STATE` - 默认值是 `state_001_start`，是您希望从（不带 `.py` 的）状态模块开始的名称。如果您想要其他命名方案，可以更改此值。
- `HELP_SUMMARY_TEXT` - 这是在房间中输入 `help` 时（没有参数）显示的帮助摘要。原始内容位于 `evennia/contrib/full_systems/evscaperoom/commands.py` 的顶部。

## 游戏玩法

您应该首先四处 `look` 看看和观察物体。

`examine <object>` 命令允许您“专注”于一个物体。当您这样做时，您将了解到您可以尝试对所专注的物体执行的操作，例如转动它、阅读其中的文本或与其他物体一起使用。请注意，多位玩家可以专注于同一物体，因此当您专注时不会阻碍他人。专注于另一个物体或再次使用 `examine` 将移除专注。

游戏中还有完整的提示系统。

## 技术信息

连接到游戏时，用户可以选择加入现有房间（该房间可能已在某种正在进行中的状态中），或者可以创建一个新的房间以便自己开始解决（但任何人仍然可以稍后加入他们）。

房间将随着玩家的挑战进度经历一系列“状态”。这些状态在 .states/ 中描述为模块，房间将加载并执行每个模块中的 State 对象，以便在玩家进展时设置和切换状态。这允许将状态相互隔离，并希望使跟踪逻辑变得更容易（从原则上讲，后期可以注入新谜题）。

一旦房间内没有玩家，房间及其状态将被清除。

## 设计理念

设计的灵感来源于一些基本原则。

- 您应该能够单独解决房间。因此，没有谜题应要求多个玩家的协作。这是因为无法确保其他玩家在特定时间在线（或在整个过程中保持在线）。
- 您不应因其他玩家的行为/不作为而受到阻碍。因此，您不能捡起任何物品（没有库存系统），只能专注/操作物品。这避免了玩家捡起关键谜题的部分后又在线下线的烦人情况。
- 房间的状态一次性变化对所有人都是相同的。最初的想法是，让每个房间根据谁在查看而具有不同的状态（因此一个箱子对两个玩家可以同时打开和关闭）。但这不仅增加了额外的复杂性，而且还削弱了多位玩家的目的。通过这种方式，人们可以像在“真实”的逃脱室中一样互相帮助和合作。对于那些想要独自完成的玩家，我还创建了轻松启动“新鲜”房间的功能。

所有其他设计决策都源于此。
