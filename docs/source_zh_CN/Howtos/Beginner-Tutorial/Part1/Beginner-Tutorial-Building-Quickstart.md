# 使用命令和构建内容

在本课中，我们将测试游戏中开箱即用的功能。Evennia 附带[大约 90 个默认命令](../../../Components/Default-Commands.md)，虽然您可以根据需要覆盖这些命令，但默认命令非常有用。

连接并登录到您的新游戏。您会发现自己在“Limbo”位置。此时，这是游戏中唯一的房间。让我们稍微探索一下默认命令。

默认命令的语法[类似于 MUX](../../../Coding/Default-Command-Syntax.md)：

```
command[/switch/switch...] [arguments ...]
```

例如：

```
create/drop box
```

_/switch_ 是一个特殊的可选标志，用于使命令表现不同。开关始终放在命令名称之后，并以正斜杠 (`/`) 开头。_arguments_ 是一个或多个命令的输入。分配某物给对象时，通常使用等号 (`=`)。

> 您是否习惯于以 @ 开头的命令，例如 @create？这也可以使用。Evennia 只是忽略了前面的 @。

## 获取帮助

```
help
```

将为您提供所有可用命令的列表。使用

```
help <commandname>
```

查看该命令的游戏内帮助。

## 环顾四周

最常用的命令是

```
look
```

这将显示您当前位置的描述。`l` 是 look 命令的别名。

在命令中定位对象时，您可以使用两个特殊标签：`here` 表示当前房间，`me`/`self` 表示您自己。因此，

```
look me
```

将为您提供您自己的描述。在这种情况下，`look here` 与简单的 `look` 相同。

## 放下神的身份

如果您刚刚安装了 Evennia，您的第一个玩家帐户称为用户 #1 &mdash; 也称为 _超级用户_ 或 _神用户_。此用户非常强大 &mdash; 强大到可以覆盖许多游戏限制（例如锁）。这可能很有用，但它也隐藏了一些您可能想要测试的功能。

要暂时放下超级用户身份，您可以在游戏中使用 `quell` 命令：

```
quell
```

这将使您开始使用当前角色级别的权限，而不是超级用户级别的权限。如果您没有更改任何设置，您的初始游戏角色应该具有 _Developer_ 级别权限 &mdash; 这是不绕过锁定（如超级用户那样）可以达到的最高权限。这对于本页上的示例来说效果很好。使用

```
unquell
```

在完成后再次获得超级用户状态。

## 创建对象

基本对象可以是任何东西 &mdash; 剑、花和非玩家角色。它们是使用 `create` 命令创建的。例如：

```
create box
```

这会在您的库存中创建一个新的“box”（默认对象类型）。使用命令 `inventory`（或 `i`）查看它。现在，“box”是一个相当短的名称，所以让我们重命名它并添加一些别名：

```
name box = very large box;box;very;crate
```

```{warning} MUD 客户端和分号：
一些传统的 MUD 客户端使用分号 `;` 来分隔客户端输入。如果是这样，上面的行将给出错误，您需要更改客户端以使用其他命令分隔符或将其置于“逐字模式”。如果您仍然遇到问题，请改用 Evennia 网络客户端。
```

我们现在将箱子重命名为 _very large box_ &mdash; 这就是我们在查看它时会看到的内容。但是，我们也会通过我们在上面的名称命令中提供的任何其他名称（即 _crate_ 或简单的 _box_）来识别它。我们也可以在初始 `create` 对象命令中直接在名称后面提供这些别名。这适用于所有创建命令 &mdash; 您始终可以为新对象的名称提供以 `;` 分隔的别名列表。在我们的示例中，如果您不想更改盒子对象本身的名称，而只是添加别名，可以使用 `alias` 命令。

在构建教程的这一点上，我们的角色目前正在携带箱子。让我们把它放下：

```
drop box
```

嘿，瞧，&mdash; 它就在地上，完全正常。还有一个快捷方式可以通过使用 `/drop` 开关一次性创建和放下对象（例如，`create/drop box`）。

让我们仔细看看我们的新盒子：

```
examine box
```

检查命令将显示有关盒子对象的一些技术细节。目前，我们将忽略这些信息的含义。

尝试 `look` 查看盒子的（默认）描述：

```
> look box
You see nothing special.
```

默认描述不是很令人兴奋。让我们添加一些风味：

```
desc box = This is a large and very heavy box.
```

如果您尝试 `get` 命令，我们将拿起箱子。到目前为止一切顺利。但是，如果我们真的希望这是一个大而重的盒子，人们不应该如此轻易地跑掉。为防止这种情况发生，我们必须将其锁定。这是通过为其分配一个 _lock_ 来完成的。首先确保盒子已放在房间里，然后使用锁命令：

```
lock box = get:false()
```

锁代表一个相当[大的话题](../../../Components/Locks.md)，但目前，这将满足我们的需求。上面的命令将锁定盒子，以便没有人可以抬起它 &mdash; 只有一个例外。请记住，超级用户会覆盖所有锁，并且无论如何都会将其拾起。确保您正在抑制您的超级用户权限，然后尝试再次获取它：

```
> get box
You can't get that.
```

觉得这个默认错误消息看起来很无聊吗？`get` 命令会查找名为 `get_err_msg` 的 [Attribute](../../../Components/Attributes.md) 以返回自定义错误消息。我们使用 `set` 命令设置属性：

```
set box/get_err_msg = It's way too heavy for you to lift.
```

现在尝试获取盒子，您应该会看到一个更相关的错误消息回显给您。要查看此消息字符串的未来内容，您可以使用“examine”。

```
examine box/get_err_msg
```

`Examine` 将返回属性的值，包括颜色代码。例如，`examine here/desc` 将返回当前房间的原始描述（包括颜色代码），以便您可以复制并粘贴以将其描述设置为其他内容。

您可以在游戏外的 Python 代码中创建新命令 &mdash; 或修改现有命令。我们稍后将在 [Commands tutorial](./Beginner-Tutorial-Adding-Commands.md) 中探索这样做。

## 获取个性

[Scripts](../../../Components/Scripts.md) 是功能强大的角色外对象，可用于许多“底层”事物。它们的一个可选功能是按计时器执行操作。为了尝试我们的第一个脚本，让我们将其应用于自己。在 `evennia/contrib/tutorials/bodyfunctions/bodyfunctions.py` 中有一个名为 `BodyFunctions` 的示例脚本。要将其添加到我们自己，我们可以使用 `script` 命令：

```
script self = tutorials.bodyfunctions.BodyFunctions
```

上面的字符串告诉 Evennia 挖掘我们指示位置的 Python 代码。它已经知道在 `contrib/` 文件夹中查找，因此我们不必提供完整路径。

> 还要注意我们如何使用 `.` 而不是 `/`（或 Windows 上的 `\`）。这种约定称为“Python 路径”。在 Python 路径中，您用 `.` 分隔路径的各个部分，并跳过 `.py` 文件结尾。重要的是，它还允许您指向文件 _内部_ 的 Python 代码，就像我们的示例中 `BodyFunctions` 类位于 `bodyfunctions.py` 文件中一样。我们稍后会介绍类。这些“Python 路径”在 Evennia 中被广泛使用。

等一会儿，您会注意到自己开始做出随机观察...

```
script self =
```

上面的命令将显示给定对象上的脚本的详细信息，在这种情况下是您自己。`examine` 命令也包含此类详细信息。

您将看到它下一次“触发”的时间。不必担心倒计时到零时没有任何反应 &mdash; 这个特定的脚本有一个随机化器来确定它是否会说些什么。因此，您不会在每次触发时看到输出。

当您厌倦了角色的“洞察力”时，使用以下命令停止脚本：

```
script/stop self = tutorials.bodyfunctions.BodyFunctions
```

您可以在游戏外的 Python 中创建自己的脚本；您提供给 `script` 的路径实际上是脚本文件的 Python 路径。[Scripts](../../../Components/Scripts.md) 页面解释了更多详细信息。

## 按下你的按钮

如果我们回到我们制作的盒子，此时您只能对它进行有限的操作。它只是一个愚蠢的通用对象。如果您将其重命名为 `stone` 并更改其描述，没有人会知道。然而，通过自定义 [Typeclasses](../../../Components/Typeclasses.md)、[Scripts](../../../Components/Scripts.md) 和基于对象的 [Commands](../../../Components/Commands.md) 的结合使用，您可以扩展它 &mdash; 以及其他项目 &mdash; 使其变得独特、复杂和互动。

所以，让我们通过这样一个例子来工作。到目前为止，我们只创建了使用默认对象类型类（简单地命名为 `Object`）的对象。让我们创建一个更有趣的对象。在 `evennia/contrib/tutorials` 下有一个模块 `red_button.py`。它包含神秘的 `RedButton` 类。

让我们给自己做一个 _这样的_ 按钮！

```
create/drop button:tutorials.red_button.RedButton
```

输入上面的命令和 Python 路径，然后你就有了 &mdash; 一个红色按钮！就像前面的脚本示例一样，我们指定了一个 Python 路径来创建对象的 Python 代码。

RedButton 是一个示例对象，旨在展示 Evennia 的一些功能。您会发现控制它的 [Typeclass](../../../Components/Typeclasses.md) 和 [Commands](../../../Components/Commands.md) 位于 [evennia/contrib/tutorials/red_button](../../../api/evennia.contrib.tutorials.red_button.md) 中。

如果您等一会儿（确保您放下了它！），按钮会诱人地闪烁。

为什么不试着按一下呢...？

当然，大红色按钮就是用来按的。

您知道您想要。

```{warning} 不要按诱人地闪烁的红色按钮。
```

## 给自己建个房子

塑造游戏世界的主要命令是 `dig`。例如，如果您站在 Limbo 中，您可以像这样挖出通往新房间的位置：

```
dig house = large red door;door;in,to the outside;out
```

上面的命令将创建一个名为“house”的新房间。它还将在您当前位置创建一个名为“大红色门”的出口，以及一个名为“通往外面”的出口，该出口位于通往 Limbo 的新房间中。在上面，我们还为这些出口定义了一些别名，以便玩家无需输入完整的出口名称。

如果您想使用常规的罗盘方向（北、西、西南等），您也可以使用 `dig`。然而，Evennia 还有一个专门用于帮助处理基本方向（以及上下和进出）的 `dig` 版本。它被称为 `tunnel`：

```
tunnel sw = cliff
```

这将创建一个名为“cliff”的新房间，带有通向那里的“西南”出口，以及从悬崖返回到您当前位置的“东北”路径。

您可以使用 `open` 命令从您所站的位置创建新出口：

```
open north;n = house
```

这将打开一个通往先前创建的房间 `house` 的出口 `north`（带有别名 `n`）。

如果您有很多名为 `house` 的房间，您将获得一个匹配列表，必须选择要链接到哪个特定房间。

接下来，通过向北行走，跟随北方出口到您的“house”。您也可以 `teleport` 到那里：

```
north
```

或者：

```
teleport house
```

要手动打开返回 Limbo 的出口（如果您没有使用 `dig` 命令自动执行此操作）：

```
open door = limbo
```

（您也可以使用 Limbo 的 `#dbref`，您可以在 Limbo 中使用 `examine here` 找到它。）

## 重组世界

假设您回到了 `Limbo`，让我们将 _large box_ 传送到我们的 `house`：

```
teleport box = house
    very large box is leaving Limbo, heading for house.
    Teleported very large box -> house.
```

您可以使用 `find` 命令在游戏世界中找到东西，例如我们的 `box`：

```
find box
    One Match(#1-#8):
    very large box(#8) - src.objects.objects.Object
```

知道盒子的 `#dbref`（在此示例中为 #8），您可以抓住盒子并将其带回这里，而无需先去 `house`：

```
teleport #8 = here
```

如前所述，`here` 是“您当前位置”的别名。盒子现在应该回到 Limbo 和您在一起。

我们厌倦了这个盒子。让我们销毁它：

```
destroy box
```

发出 `destroy` 命令将要求您确认。一旦确认，盒子将消失。

您可以通过向命令提供逗号分隔的对象列表（或 `#dbrefs` 范围，如果它们不在同一位置）一次性 `destroy` 多个对象。

## 添加帮助条目

与命令相关的 `help` 条目是您在 Python 代码中修改的内容 &mdash; 我们将在解释如何添加命令时介绍这一点 &mdash; 但您也可以添加与命令无关的帮助条目。例如，解释有关您的游戏世界的历史：

```
sethelp History = At the dawn of time ...
```

您现在将在 `help` 列表中找到新的 `History` 条目，并可以使用 `help History` 阅读您的帮助文本。

## 添加一个世界

在对构建和使用游戏内命令进行简要介绍之后，您可能已经准备好查看一个更充实的示例。幸运的是，Evennia 附带了一个供您探索的教程世界 &mdash; 我们将在下一课中尝试。
