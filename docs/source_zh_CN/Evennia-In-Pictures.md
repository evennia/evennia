# Evennia 图解指南

```{sidebar}
本文并非完整概述，而是帮助您快速了解一些关键概念的入门指南。
```

本文旨在通过图解方式展示 Evennia 服务器的核心架构与运行机制，帮助您理解各组件如何协同工作。

<div style="clear: right;"></div>

## 两大核心组件
![Evennia门户与服务器][image1]

图中展示的是您从我们这里下载的 Evennia 核心部分，它本身不会直接运行游戏。接下来我们将创建缺失的"拼图块"，但首先让我们了解现有组件。

Evennia 由两个独立进程组成：[Portal 和 Server](Components/Portal-And-Server.md)。  
- **Portal** 管理所有外部连接（Telnet/WebSocket/SSH等），不涉及数据库或游戏状态。其与 Server 的通信采用协议无关格式，使得 Server 可以完全重启而不断开用户连接。  
- **Server** 是核心游戏引擎，采用异步框架 [Twisted](http://twistedmatrix.com/trac/)，负责游戏世界和数据库的所有逻辑。  
- **Web服务器** 与 Server 同进程运行，提供游戏网站服务。  
<div style="clear: right;"></div>

### 初始化游戏目录
![创建游戏目录][image2]

[安装Evennia](Setup/Installation.md) 后，使用 `evennia` 命令创建游戏目录（如 `mygame`）。这是图中深灰色部分，也是您实现游戏梦想的地方！

初始化过程会：
1. 在 `mygame/` 生成Python模板文件
2. 完成所有配置链接
3. 创建数据库后即可启动服务器

启动后可通过 telnet localhost:4000 或浏览器访问 http://localhost:4001 连接游戏。

## 数据库系统
![数据库结构][image3]

Evennia 使用 [Django](https://www.djangoproject.com/) 实现全持久化数据库。如图示：
- `ObjectDB` Python类对应数据库表
- 类属性对应表的列（如名称字段）
- 每行数据代表一个游戏实体（如角色/物品）
- `db_typeclass_path` 字段指向具体的子类，这是 [Typeclass系统](Components/Typeclasses.md) 的核心

图中示例显示 _Trigger_ 位于 _Dungeon_ 场景中，携带十字弩 _Old Betsy_。

### 从数据库到Python对象
![Python类继承][image4]

简化版的Python类继承结构：
- [Objects](Components/Objects.md) 代表游戏内可见实体
- 子类实现具体功能（如 `Crossbow` 特有逻辑）
- 新建实体时自动创建数据库记录
- 查询数据库返回的是可操作的Python对象

### 属性系统
![属性存储][image5]

[Attribute](Components/Attributes.md) 系统实现灵活数据存储：
- 每个属性包含键/值对
- 通过外键关联到 `ObjectDB`
- 支持序列化任意Python数据（如图中的技能字典）
- 可直接通过 `Trigger` 对象访问"strength"等属性

<div style="clear: right;"></div>

## 游戏控制机制

### 会话与账号
![多会话控制][image6]

玩家通过 [Sessions](Components/Sessions.md) 连接游戏：
- [Account](Components/Accounts.md) 存储账号信息（如密码）
- 单个账号可通过多客户端同时连接（不同 `Session`）
- 支持同时操控多个游戏角色（如 _Trigger_ 和 _Sir Hiss_）
- 可通过 [连接风格](Concepts/Connection-Styles.md) 配置控制权限

### 命令系统
![命令结构][image7]

[Commands](Components/Commands.md) 是玩家与游戏交互的核心方式：
- 每个命令处理输入解析与执行逻辑
- 可通过继承实现通用解析（如图中 `DIKUCommand`）
- 示例：`look`/`get`/`emote` 等指令

### 命令集
![角色命令集][image8]
![场景命令集][image9]

命令通过 [CommandSet](Components/Commands.md#command-sets) 组织：
- 可附加到任意游戏实体
- 场景中的命令可覆盖角色自带命令（如图中不同颜色命令）
- 实现动态游戏机制（如黑暗场景中修改 `look` 行为）

<div style="clear: right;"></div>

### 命令集合并
![命令合并][image10]

支持动态合并多个命令集：
- 采用类似 [集合论](https://en.wikipedia.org/wiki/Set_theory) 的合并逻辑
- 优先级可自定义配置
- 非破坏性合并（离开场景后恢复原命令集）
- 支持复杂状态叠加（如黑暗+战斗+醉酒状态）

## 探索更多

本文仅展示部分核心功能，完整内容请参考：
- [核心组件](Components/Components-Overview.md)
- [核心概念](Concepts/Concepts-Overview.md) 
- [Evennia 简介](./Evennia-Introduction.md)

[image1]: https://2.bp.blogspot.com/-0-oir21e76k/W3kaUuGrg3I/AAAAAAAAJLU/qlQWmXlAiGUz_eKG_oYYVRf0yP6KVDdmQCEwYBhgL/s1600/Evennia_illustrated_fig1.png
[image2]: https://4.bp.blogspot.com/-TuLk-PIVyK8/W3kaUi-e-MI/AAAAAAAAJLc/DA9oMA6m5ooObZlf0Ao6ywW1jHqsPQZAQCEwYBhgL/s1600/Evennia_illustrated_fig2.png
[image3]: https://3.bp.blogspot.com/-81zsySVi_EE/W3kaVRn4IWI/AAAAAAAAJLc/yA-j1Nwy4H8F28BF403EDdCquYZ9sN4ZgCEwYBhgL/s1600/Evennia_illustrated_fig3.png
[image4]: https://2.bp.blogspot.com/--4_MqVdHj8Q/W3kaVpdAZKI/AAAAAAAAJLk/jvTsuBBUlkEbBCaV9vyIU0IWiuF6PLsSwCEwYBhgL/s1600/Evennia_illustrated_fig4.png
[image5]: https://3.bp.blogspot.com/-6ulv5T_gUCI/W3kaViWBBfI/AAAAAAAAJLU/0NqeAsz3YVsQKwpODzsmjzR-7tICw1pTQCEwYBhgL/s1600/Evennia_illustrated_fig5.png
[image6]: https://4.bp.blogspot.com/-u-npXjlq6VI/W3kaVwAoiUI/AAAAAAAAJLY/T9bhrzhJJuQwTR8nKHH9GUxQ74hyldKOgCEwYBhgL/s1600/Evennia_illustrated_fig6.png
[image7]: https://3.bp.blogspot.com/-_RM9-Pb2uKg/W3kaWIs4ndI/AAAAAAAAJLc/n45Hcvk1PiYhNdBbAAr_JjkebRVReffTgCEwYBhgL/s1600/Evennia_illustrated_fig7.png
[image8]: https://2.bp.blogspot.com/-pgpYPsd4CLM/W3kaWG2ffuI/AAAAAAAAJLg/LKl4m4-1xkYxVA7JXXuVP28Q9ZqhNZXTACEwYBhgL/s1600/Evennia_illustrated_fig8.png
[image9]: https://3.bp.blogspot.com/-acmVo7kUZCk/W3kaWZWlT0I/AAAAAAAAJLk/nnFrNaq_TNoO08MDleadwhHfVQLdO74eACEwYBhgL/s1600/Evennia_illustrated_fig9.png
[image10]: https://4.bp.blogspot.com/--lixKOYjEe4/W3kaUl9SFXI/AAAAAAAAJLQ/tCGd-dFhZ8gfLH1HAsQbZdaIS_OQuvU3wCEwYBhgL/s1600/Evennia_illustrated_fig10.png
