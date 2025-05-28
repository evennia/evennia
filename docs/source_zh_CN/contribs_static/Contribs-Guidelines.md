# Evennia contrib 贡献指南

Evennia 有一个 [contrib](./Contribs-Overview.md) 目录，其中包含按类别组织的可选社区共享代码。欢迎任何人贡献。

## 什么适合成为 contrib？

- 通常，您可以贡献任何您认为对其他开发者有用的东西。与 Evennia 的“核心”不同，contrib 也可以是高度特定于游戏类型的。
- 非常小或不完整的代码片段（例如，打算粘贴到其他代码中）最好在 [Community Contribs & Snippets](https://github.com/evennia/evennia/discussions/2488) 讨论论坛类别中分享。
- 如果您的代码主要作为示例或展示概念/原理而不是工作系统，请考虑通过撰写新教程或操作指南来 [贡献文档](../Contributing-Docs.md)。
- 如果可能，请尽量使您的贡献尽可能与类型无关，并假设您的代码将应用于与您创建时考虑的游戏完全不同的游戏。
- 贡献最好能独立于其他 contrib 工作（仅使用核心 Evennia），以便可以轻松地投入使用。如果确实依赖于其他 contrib 或第三方模块，则必须在安装说明中明确记录。
- 如果您不确定您的 contrib 想法是否合适或合理，请在投入任何工作之前*在讨论或聊天中询问*。例如，我们不太可能接受需要大幅修改游戏目录结构的 contrib。

## contrib 的布局

- contrib 必须仅包含在以下 contrib 类别之一的单个文件夹中。如果不确定哪个类别最适合您的 contrib，请询问。

|  |  | 
| --- | --- | 
| `base_systems/` | _不一定与特定游戏机制相关的系统，但对整个游戏有用。示例包括登录系统、新的命令语法和构建助手。_ |
| `full_systems/` | _‘完整’的游戏引擎，可以直接用于开始创建内容，无需进一步添加（除非您愿意）。_ |
| `game_systems/` | _游戏中的游戏玩法系统，如制作、邮件、战斗等。每个系统都旨在被逐步采用并适应您的游戏。这不包括角色扮演特定的系统，这些系统在 `rpg` 类别中。_ |
| `grid/` | _与游戏世界的拓扑和结构相关的系统。与房间、出口和地图构建相关的 contrib。_ |
| `rpg/` | _专门与角色扮演和规则实现相关的系统，如角色特征、掷骰子和表达。_ | 
| `tutorials/` | _专门用于教授开发概念或示范 Evennia 系统的辅助资源。与文档教程相关的任何额外资源都在这里找到。也是 Tutorial-World 和 Evadventure 演示代码的所在地。_ | 
| `utils/` | _用于操作文本、安全审计等的杂项工具。_|

- 文件夹（包）应具有以下形式：

    ```
    evennia/
       contrib/ 
           category/    # rpg/, game_systems/ 等
               mycontribname/
                   __init__.py
                   README.md
                   module1.py
                   module2.py
                   ...
                   tests.py
    ```

    通常在 `__init__.py` 中导入有用的资源是个好主意，以便更容易导入它们。
- 您的代码应遵循 [Evennia 风格指南](../Coding/Evennia-Code-Style.md)。编写易于阅读的代码。
- 您的贡献*必须*由 [单元测试](../Coding/Unit-Testing.md) 覆盖。在您的 contrib 文件夹下的 `tests.py` 模块中放置您的测试（如上所示） - Evennia 将自动找到它们。如果有很多测试跨多个模块，请使用 `tests/` 文件夹来组织您的测试。
- `README.md` 文件将被解析并转换为从 [contrib 概览页面](./Contribs-Overview.md) 链接的文档。它需要以下列形式：

    ```markdown
    # MyContribName

    Contribution by <yourname>, <year>

    一段总结 contrib 的段落（可以是多行）（必需）

    可选的其他文本

    ## 安装

    使用 contrib 的详细安装说明（必需）

    ## 用法

    ## 示例

    等等。

    ```

> 每个贡献的信用和第一段摘要将自动包含在 Contrib 概览页面索引中，因此需要仅以这种形式存在。

## 提交 contrib

```{sidebar} 并非所有 PR 都能被接受
虽然大多数 PR 会被合并，但这并非保证：合并 contrib 意味着 Evennia 项目需要承担维护和支持新代码的责任。由于各种原因，这可能被认为不可行。

如果由于某种原因您的代码未被接受，我们仍然可以从我们的链接页面链接它；它也可以发布在我们的讨论论坛中。
```
- contrib 必须始终以 [拉取请求](../Coding/Version-Control.md#contributing-to-evennia) (PR) 的形式提交。
- PR 会被审核，因此如果您被要求修改或更改代码以便合并，请不要感到惊讶（或灰心）。您的代码可能会经过多次迭代才会被接受。
- 为了明确许可情况，我们假设所有贡献都以与 Evennia 相同的 [许可证](../Licensing.md) 发布。如果由于某种原因这不可能，请与我们联系，我们将根据具体情况处理。
