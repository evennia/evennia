# 教程世界

*教程世界*是Evennia附带的一个小型、可运行的MUD风格游戏世界。它展示了可能实现的功能，对于通过解构现有代码学习的人来说也可能很有用。

## 安装教程世界

站在Limbo房间并输入以下命令安装教程世界：

    batchcommand tutorial_world.build

这个命令运行[evennia/contrib/tutorials/tutorial_world/build.ev](github:evennia/contrib/tutorials/tutorial_world/build.ev)中的构建脚本。基本上，这个脚本是`batchcommand`命令按顺序执行的一系列构建命令。等待构建完成，不要运行两次。

> 运行batchcommand后，`intro`命令在Limbo中可用。尝试使用[EvMenu](../../../Components/EvMenu.md)的示例获取游戏内帮助，EvMenu是Evennia内置的菜单生成系统！

教程世界包含一个单人任务，有大约20个房间可供探索，寻找一件神话武器的下落。

一个新的出口_Tutorial_应该会出现。输入`tutorial`进入教程世界。

进入时会自动`quell`(退出时会`unquell`)，所以你可以按预期方式游玩。无论你是胜利还是使用`give up`命令，最终都会回到Limbo。

```{important}
只有LOSERS和QUITTERS才会使用`give up`命令。
```

## 游戏玩法

![沼泽外的城堡](https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/22916c25-6299-453d-a221-446ec839f567/da2pmzu-46d63c6d-9cdc-41dd-87d6-1106db5a5e1a.jpg/v1/fill/w_600,h_849,q_75,strp/the_castle_off_the_moor_by_griatch_art_da2pmzu-fullview.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOiIsImlzcyI6InVybjphcHA6Iiwib2JqIjpbW3siaGVpZ2h0IjoiPD04NDkiLCJwYXRoIjoiXC9mXC8yMjkxNmMyNS02Mjk5LTQ1M2QtYTIyMS00NDZlYzgzOWY1NjdcL2RhMnBtenUtNDZkNjNjNmQtOWNkYy00MWRkLTg3ZDYtMTEwNmRiNWE1ZTFhLmpwZyIsIndpZHRoIjoiPD02MDAifV1dLCJhdWQiOlsidXJuOnNlcnZpY2U6aW1hZ2Uub3BlcmF0aW9ucyJdfQ.omuS3D1RmFiZCy9OSXiIita-HxVGrBok3_7asq0rflw)
(图片由Griatch提供)

*为了体验我们迷你任务的气氛，想象你是一个寻找名声和财富的冒险者。你听说海岸边有一座古老的城堡废墟。在其深处，一位战士公主与她那强大的魔法武器一起被埋葬——如果属实，这将是一件宝贵的战利品。当然，这是一个你无法拒绝的冒险机会！*

*你在猛烈的雷暴中到达海边。面对呼啸的风雨，你站在沼泽与大海相接的高耸岩石海岸上...*

---

### 游戏提示

- 使用`tutorial`命令获取每个房间背后的代码洞察。
- 查看所有东西。虽然是演示，但教程世界不一定容易解决——这取决于你对文本冒险游戏的体验。只需记住一切都可以解决或绕过。
- 有些对象有多种交互方式。使用普通的`help`命令随时了解可用的命令。
- 要战斗，首先需要找到某种武器。
    - *slash*是普通攻击
    - *stab*发动伤害更大但命中率更低的攻击。
    - *defend*会降低敌人下次攻击时受到伤害的几率。
- 有些东西_无法_被普通武器伤害。那样的话逃跑是可以的。准备好被追逐...
- 失败是体验的一部分。你实际上不会死，但被击倒意味着被留在黑暗中...

## 完成后(或受够了)

之后你要么征服了古老的废墟，凯旋而归...要么通过使用`give up`命令一瘸一拐地退出挑战。无论哪种方式，你现在应该回到Limbo，能够反思这段经历。

教程世界展示的一些功能：

- 具有自定义细节显示能力的房间(如在黑暗房间看墙)
- 在满足某些条件前隐藏或无法通过的出口
- 具有多种自定义交互的对象(如剑、井、方尖碑...)
- 大面积房间(那座桥实际上只是一个房间！)
- 有天气的户外房间(雨水拍打着你)
- 需要光源揭示的黑暗房间(燃烧的碎片过一会儿会熄灭)
- 谜题对象(黑暗地窖中的酒；希望你没被困住！)
- 多房间谜题(方尖碑和墓室)
- 具有漫游、追击和战斗状态引擎AI的攻击性生物(在找到合适的武器前相当致命)
- 武器，也被生物使用(大多数对大坏蛋确实没那么有用)
- 带有攻击/防御命令的简单战斗系统(失败时传送)
- 对象生成(桶中的武器和最终武器实际上是随机的)
- 传送陷阱房间(如果方尖碑谜题失败)

```{sidebar} 额外学分

如果你已经熟悉Python并想提前体验，深入研究教程世界以了解它如何实现功能是有益的。代码有大量注释。你可以在[evennia/contrib/tutorials/tutorial_world](../../../api/evennia.contrib.tutorials.tutorial_world.md)找到所有代码。
构建脚本在[这里](github:evennia/contrib/tutorials/tutorial_world/build.ev)。

阅读教程世界代码时，请注意教程世界设计为易于安装且不永久修改游戏的其他部分。因此它确保只使用临时解决方案并在完成后清理。在你制作自己的游戏时通常不需要担心这一点。
```

在这么小的区域里塞了这么多东西！

## 卸载教程世界

玩完教程世界后，让我们卸载它。卸载教程世界基本上意味着删除它包含的所有房间和对象。确保你回到Limbo，然后

     find tut#01
     find tut#16

这应该能找到`build.ev`创建的第一个和最后一个房间——*Intro*和*Outro*。如果正常安装，这两个数字之间的所有内容都应该是教程的一部分。记下它们的#dbref编号，例如5和80。接下来我们只需删除该范围内的所有对象：

     del 5-80

你会看到一些错误，因为有些对象会自动删除，所以删除机制处理它们时找不到。这没关系。命令完成后，你应该已经完全删除了教程。

即使教程世界的游戏风格与你感兴趣的不相似，它也应该让你对Evennia的一些可能性有所了解。现在我们将继续学习如何通过代码访问这些功能。
