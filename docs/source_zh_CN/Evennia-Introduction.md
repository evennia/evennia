# Evennia 简介

> *MUD（最初指多用户地下城，后衍生为多用户维度和多用户领域）是基于文本描述的多人实时虚拟世界。它融合了角色扮演、砍杀战斗、玩家对抗、互动小说和在线聊天等元素。玩家通过输入类自然语言指令，与虚拟世界中的场景、物品、其他玩家及NPC互动。* - [维基百科](https://en.wikipedia.org/wiki/MUD)

如果您正在阅读本文，很可能您正梦想着打造属于自己的文字类多人在线游戏（[MUD/MUX/MUSH](https://tinyurl.com/c5sc4bm)等）。或许这个想法刚刚萌芽，又或许那个"完美游戏"的构想已在您脑海中酝酿多年...您深知它会有多棒，只待将其实现。

我们理解这种感受——这也正是Evennia诞生的初衷。

## 什么是Evennia？

Evennia是一个MU*游戏开发框架：一个高度可扩展的Python代码库与服务器，适用于构建任何风格的文本游戏。

### 极简内核？
"极简"意味着我们尽可能避免强加游戏特定规则。您不会找到预设的战斗系统、怪物AI、种族设定或职业系统——这些正是留待您亲手实现的部分！

### 框架特性？
虽然极简，但Evennia仍提供基础构建模块：
- 对象/角色/房间等核心元素
- 内置聊天频道
- 管理工具和建造命令
开箱即得一个可运行的"社交型"游戏雏形，包含行走、聊天等基础功能。Evennia已处理好所有底层数据库、网络通信等必要架构。

我们还提供大量可选[扩展模块](Contribs/Contribs-Overview.md)，这些更具游戏特色，可作为开发起点。

### 服务器功能？
Evennia自带Web服务器，启动后立即提供：
- 游戏官网
- 网页版客户端
玩家可通过浏览器或传统MUD客户端连接，所有功能在您准备好前都不会对外公开。

### 为什么选择Python？
[Python](https://en.wikipedia.org/wiki/Python_(programming_language))不仅是当下最流行的语言之一，也被公认为最易入门的编程语言。在Evennia社区，许多人正是通过开发游戏学会了Python编程，甚至有人因此获得工作机会！

所有游戏逻辑——从对象定义、自定义命令到AI脚本和经济系统——都通过标准Python模块实现，无需学习特殊脚本语言。

## 在线体验
访问官方演示站：[https://demo.evennia.com](https://demo.evennia.com) 或通过MUD客户端连接 `demo.evennia.com:4000`

安装Evennia后，还可通过命令一键生成教程游戏世界，详情参见[新手教程](Howtos/Beginner-Tutorial/Part1/Beginner-Tutorial-Tutorial-World.md)。

## 需要掌握哪些技能？

### 完全不想编程？
Evennia自带基础命令集，可立即运行简单的"社交型"游戏：
- 建造描述性场景
- 基础物品交互
- 聊天/角色扮演功能
但若想实现战斗等复杂机制，仍需编写代码。

### Python初学者？
建议从[新手教程](Howtos/Beginner-Tutorial/Beginner-Tutorial-Overview.md)起步，您需要掌握：
- 模块导入
- 变量/条件语句/循环/函数
- 列表/字典操作
- 字符串处理
- 面向对象基础概念

```{sidebar}
推荐阅读[学习资源](./Links.md)获取更多Python教程
```

### 熟练开发者？
Python高手可以：
- 开发复杂AI和经济系统
- 重构核心机制（命令/房间/频道等）
- 结合Web技术（HTML/CSS/JS）定制界面
通过标准Python模块实现功能，几乎没有限制！

## 下一步行动
- 通过[图解指南](./Evennia-In-Pictures.md)了解架构
- 跟随[新手教程](Howtos/Beginner-Tutorial/Beginner-Tutorial-Overview.md)实践
- 探索更多[进阶教程](Howtos/Howtos-Overview.md#howtos)
- 加入[Discord社区](https://discord.gg/AJJpcRUhtF)获取实时帮助
- 参与[论坛讨论](https://github.com/evennia/evennia/discussions)

欢迎来到Evennia的世界！
