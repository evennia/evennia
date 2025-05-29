# Soft Code

Softcode 是一种简单的编程语言，专为 TinyMUD 衍生产品（如 MUX、PennMUSH、TinyMUSH 和 RhostMUSH）中的游戏开发而创建。其理念是通过提供一种简化的、极简的游戏内语言，可以让构建者在不必学习这些服务器的“硬编码”语言（C/C++）的情况下，快速轻松地进行构建和游戏开发。此外，不必为所有开发者提供 shell 访问权限。Softcode 中的权限可以用来缓解许多安全问题。

编写和安装 softcode 是通过 MUD 客户端完成的。因此，它不是一种格式化的语言。每个 softcode 函数都是单行的，大小不一。有些函数可以长达半页或更多，显然不太可读，也不易于维护。

## Softcode 示例

这是一个简单的“Hello World!”命令：

```bash
@set me=HELLO_WORLD.C:$hello:@pemit %#=Hello World!
```

将此粘贴到 MUD 客户端，发送到 MUX/MUSH 服务器并输入“hello”理论上将显示“Hello World!”，假设您的账户对象上没有设置某些标志。

在 Softcode 中设置属性是通过 `@set` 完成的。Softcode 还允许使用符号 `&`。这种更短的版本如下所示：

```bash
&HELLO_WORLD.C me=$hello:@pemit %#=Hello World!
```

我们还可以从一个属性中读取文本，该属性在发出时被检索：

```bash
&HELLO_VALUE.D me=Hello World
&HELLO_WORLD.C me=$hello:@pemit %#=[v(HELLO_VALUE.D)]
```

函数 `v()` 返回命令所在对象（在本例中是您自己）的 `HELLO_VALUE.D` 属性。这应该会产生与第一个示例相同的输出。

如果您对 MUSH/MUX Softcode 的工作原理感兴趣，请查看一些外部资源：

- https://wiki.tinymux.org/index.php/Softcode
- https://www.duh.com/discordia/mushman/man2x1

## Softcode 的问题

Softcode 在其预期用途上表现出色：*简单的事情*。它是制作互动对象、具有氛围的房间、简单的全局命令、简单的经济和编码系统的绝佳工具。然而，一旦您开始尝试编写复杂的战斗系统或更高级的经济，您可能会发现自己被埋在跨越整个代码的多个对象的函数山中。

更不用说，softcode 本质上不是一种快速的语言。它不是编译的，而是在每次调用函数时进行解析。尽管 MUX 和 MUSH 解析器已经比以前先进了许多，但如果设计不当，它们在处理更复杂的系统时仍可能会出现卡顿。

此外，Softcode 不是一种标准化的语言。不同的服务器各有其略微的变化。代码工具和资源也仅限于这些服务器的文档。

## 时代的变化

现在，启动基于文本的游戏变得简单，即使是技术上不太熟练的人也可以选择。每天都有各种承诺和能力的新项目启动。由于这种从较少的大型、人员充足的游戏到大量小型、一两个开发者游戏的转变，softcode 的优势逐渐减弱。

Softcode 的优点在于，它允许中到大型的工作人员在没有 shell 访问权限的情况下在同一个游戏上工作而不互相干扰。然而，现代代码协作工具（如私人 github/gitlab 仓库）的兴起使得代码协作变得微不足道。

## 我们的解决方案

Evennia 拒绝游戏内的 softcode，转而使用磁盘上的 Python 模块。Python 是一种流行、成熟且专业的编程语言。Evennia 开发者可以访问市面上所有的 Python 模块库——更不用说大量的在线帮助资源。Python 代码不受限于对象上的单行函数；复杂的系统可以整齐地组织到真正的源代码模块、子模块，甚至可以根据需要分解为整个 Python 包。

因此，Evennia 中不包括 MUX/MOO 类似的在线玩家编码系统（即 Softcode）。Evennia 的高级编码主要在游戏外进行，使用完整的 Python 模块（MUSH 称之为“硬编码”）。高级构建最好通过扩展 Evennia 的命令系统来处理，使用您自己的复杂构建命令。

在 Evennia 中，您可以像开发任何现代软件一样开发您的 MU——使用您喜欢的代码编辑器/IDE 和在线代码共享工具。

## 您的解决方案

为您的游戏添加高级和灵活的构建命令很简单，并且可能足以满足大多数创意构建者的需求。然而，如果您真的、*真的*想提供在线编码，当然没有什么能阻止您在 Evennia 中添加它，无论我们的建议如何。您甚至可以在 Python 中重新实现 MUX 的 softcode，如果您非常有雄心。

在默认的 Evennia 中，Funcparser 系统允许在不成为完整 softcode 语言的情况下按需简单地重新映射文本。contribs 中有几个工具和实用程序，可以在添加更复杂的游戏内构建时作为起点。
