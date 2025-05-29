# Evennia in-game Python system

由 Vincent Le Goff 贡献于在 2017 年

这个模块增加了在游戏中使用 Python 脚本的能力。它允许值得信任的工作人员或建造者动态地为单个对象添加功能和触发器，而无需在外部 Python 模块中进行操作。通过在游戏中使用自定义 Python，可以使特定的房间、出口、角色、对象等表现得与其“同类”不同。这类似于 MU 的软代码或 DIKU 的 MudProgs。然而，请记住，允许在游戏中使用 Python 会带来严重的安全问题（您必须非常信任您的建造者），因此在继续之前请仔细阅读此模块中的警告。

## 关于安全的警告

Evennia 的游戏内 Python 系统将运行任意 Python 代码，几乎没有限制。这样的系统既强大又可能危险，在决定安装它之前，您需要牢记以下几点：

1. 不可信的人可以通过此系统在您的游戏服务器上运行 Python 代码。请注意谁可以使用此系统（请参阅下面的权限）。
2. 您可以在游戏外的 Python 中完成所有这些。游戏内 Python 系统不是为了替换您所有的游戏功能。

## 额外教程

这些教程涵盖了使用游戏内 Python 的示例。一旦您安装了系统（见下文），它们可能比从头到尾阅读完整文档更容易学习。

- [对话事件](./Contrib-Ingame-Python-Tutorial-Dialogue.md)，NPC 对所说内容做出反应。
- [语音操控电梯](./Contrib-Ingame-Python-Tutorial-Elevator.md)，使用游戏内 Python 事件。

## 基本结构和术语

- 游戏内 Python 系统的基础是**事件**。一个**事件**定义了我们希望调用一些任意代码的上下文。例如，一个事件是在出口上定义的，并将在角色通过此出口时触发。事件在 [typeclass](../Components/Typeclasses.md) 上描述（在我们的示例中是 [exits](../Components/Exits.md)）。所有继承自此 typeclass 的对象都可以访问此事件。
- 可以在代码中定义的事件上为单个对象设置**回调**。这些**回调**可以包含任意代码，并描述对象的特定行为。当事件触发时，连接到此对象事件的所有回调将被执行。

要在上下文中查看系统，当一个对象被拾取时（使用默认的 `get` 命令），将触发一个特定事件：

1. 事件“get”设置在对象上（在 `Object` typeclass 上）。
2. 当使用“get”命令拾取对象时，将调用此对象的 `at_get` 钩子。
3. 事件系统设置了一个修改过的 DefaultObject 钩子。此钩子将执行（或调用）此对象上的“get”事件。
4. 所有与此对象的“get”事件相关的回调将按顺序执行。这些回调充当包含您可以在游戏中编写的 Python 代码的函数，使用在编辑回调时列出的特定变量。
5. 在各个回调中，您可以添加将在此时触发的多行 Python 代码。在此示例中，`character` 变量将包含拾取对象的角色，而 `obj` 将包含被拾取的对象。

按照此示例，如果您在对象“a sword”上创建一个“get”回调，并在其中放入：

```python
character.msg("You have picked up {} and have completed this quest!".format(obj.get_display_name(character)))
```

当您拾取此对象时，您应该会看到类似以下内容：

```
You pick up a sword.
You have picked up a sword and have completed this quest!
```

## 安装

作为一个单独的贡献模块，游戏内 Python 系统默认未安装。您需要手动安装，按照以下步骤：

这是快速总结。向下滚动以获取每个步骤的详细帮助。

1. 启动主脚本（重要！）：

    ```bash
    py evennia.create_script("evennia.contrib.base_systems.ingame_python.scripts.EventHandler")
    ```

2. 设置权限（可选）：
   - `EVENTS_WITH_VALIDATION`：一个可以编辑回调但需要批准的组（默认为 `None`）。
   - `EVENTS_WITHOUT_VALIDATION`：一个有权编辑回调且无需验证的组（默认为 `"immortals"`）。
   - `EVENTS_VALIDATING`：一个可以验证回调的组（默认为 `"immortals"`）。
   - `EVENTS_CALENDAR`：要使用的日历类型（`None`、`"standard"` 或 `"custom"`，默认为 `None`）。
3. 添加 `call` 命令。
4. 继承游戏内 Python 系统的自定义 typeclasses。
   - `evennia.contrib.base_systems.ingame_python.typeclasses.EventCharacter`：替换 `DefaultCharacter`。
   - `evennia.contrib.base_systems.ingame_python.typeclasses.EventExit`：替换 `DefaultExit`。
   - `evennia.contrib.base_systems.ingame_python.typeclasses.EventObject`：替换 `DefaultObject`。
   - `evennia.contrib.base_systems.ingame_python.typeclasses.EventRoom`：替换 `DefaultRoom`。

以下部分详细描述了安装的每个步骤。

> 注意：如果您在未启动主脚本的情况下启动游戏（例如在重置数据库时），您很可能会在登录时遇到回溯，告诉您未定义“callback”属性。执行步骤 `1` 后，错误将消失。

### 启动事件脚本

要启动事件脚本，您只需要一个命令，使用 `@py`。

```bash
py evennia.create_script("evennia.contrib.base_systems.ingame_python.scripts.EventHandler")
```

此命令将创建一个全局脚本（即独立于任何对象的脚本）。此脚本将保存基本配置、各个回调等。您可以直接访问它，但您可能会使用回调处理程序。创建此脚本还将在所有对象上创建一个 `callback` 处理程序（有关详细信息，请参见下文）。

### 编辑权限

此贡献模块带有其自己的权限集。它们定义了谁可以在无需验证的情况下编辑回调，谁可以编辑回调但需要验证。验证是一个过程，其中管理员（或被信任的人）将检查其他人生成的回调并接受或拒绝它们。如果被接受，回调将被连接，否则它们永远不会运行。

默认情况下，回调只能由不朽者创建：除了不朽者之外，没有人可以编辑回调，并且不朽者不需要验证。可以通过设置或动态更改用户权限轻松更改。

游戏内 Python 贡献模块在设置中添加了三个[权限](../Components/Permissions.md))。您可以通过将设置更改为 `server/conf/settings.py` 文件来覆盖它们（请参阅下面的示例）。事件贡献中定义的设置是：

- `EVENTS_WITH_VALIDATION`：这定义了一个可以编辑回调但需要批准的权限。如果您将其设置为 `"wizards"`，例如，具有 `"wizards"` 权限的用户将能够编辑回调。但这些回调不会被连接，必须由管理员检查和批准。此设置可以包含 `None`，这意味着没有用户被允许编辑需要验证的回调。
- `EVENTS_WITHOUT_VALIDATION`：此设置定义了允许编辑回调且无需验证的权限。默认情况下，此设置为 `"immortals"`。这意味着不朽者可以编辑回调，并且在他们离开编辑器时将被连接，无需批准。
- `EVENTS_VALIDATING`：此最后一个设置定义了谁可以验证回调。默认情况下，此设置为 `"immortals"`，这意味着只有不朽者可以看到需要验证的回调并接受或拒绝它们。

您可以在 `server/conf/settings.py` 文件中覆盖所有这些设置。例如：

```python
# ... 其他设置 ...

# 事件设置
EVENTS_WITH_VALIDATION = "wizards"
EVENTS_WITHOUT_VALIDATION = "immortals"
EVENTS_VALIDATING = "immortals"
```

此外，如果您计划使用与时间相关的事件（在特定游戏时间安排的事件），则必须设置另一个设置。您需要指定您正在使用的日历类型。默认情况下，与时间相关的事件被禁用。您可以更改 `EVENTS_CALENDAR` 以将其设置为：

- `"standard"`：标准日历，具有标准的天、月、年等。
- `"custom"`：使用 `custom_gametime` 贡献来安排事件的自定义日历。

此贡献模块定义了两个可以在各个用户上设置的附加权限：

- `events_without_validation`：这将赋予此用户编辑回调的权限，但在连接之前不需要验证。
- `events_validating`：此权限允许此用户对需要验证的回调进行验证检查。

例如，要授予玩家 'kaldara' 编辑回调而无需批准的权限，您可以执行以下操作：

```bash
perm *kaldara = events_without_validation
```

要删除此权限，只需使用 `/del` 开关：

```bash
perm/del *kaldara = events_without_validation
```

使用 `call` 命令的权限直接与这些权限相关：默认情况下，只有具有 `events_without_validation` 权限的用户或在 `EVENTS_WITH_VALIDATION` 设置中定义的组（或以上）中的用户才能调用命令（具有不同的开关）。

### 添加 `call` 命令

您还必须将 `@call` 命令添加到您的 Character CmdSet。这条命令允许您的用户在游戏中添加、编辑和删除回调。在您的 `commands/default_cmdsets` 中，它可能看起来像这样：

```python
from evennia import default_cmds
from evennia.contrib.base_systems.ingame_python.commands import CmdCallback

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    `CharacterCmdSet` 包含游戏中的一般命令，如 `look`、`get` 等，可用于游戏中的角色对象。
    当玩家操控角色时，它会与 `PlayerCmdSet` 合并。
    """
    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        填充命令集
        """
        super().at_cmdset_creation()
        self.add(CmdCallback())
```

### 更改 typeclasses 的父类

最后，要使用游戏内 Python 系统，您需要让您的 typeclasses 继承自修改过的事件类。例如，在您的 `typeclasses/characters.py` 模块中，您应该像这样更改继承：

```python
from evennia.contrib.base_systems.ingame_python.typeclasses import EventCharacter

class Character(EventCharacter):

    # ...
```

您应该对您的房间、出口和对象做同样的事情。请注意，游戏内 Python 系统通过覆盖一些钩子来工作。如果您在覆盖钩子时不调用父方法，则某些功能可能在您的游戏中不可用。

## 使用 `call` 命令

游戏内 Python 系统在很大程度上依赖于其 `call` 命令。谁可以执行此命令，以及谁可以使用它做什么，将取决于您的权限设置。

`call` 命令允许在特定对象的事件上添加、编辑和删除回调。事件系统可以用于大多数 Evennia 对象，主要是 typeclassed 对象（不包括玩家）。`call` 命令的第一个参数是您要编辑的对象的名称。它还可以用于了解此特定对象可用的事件。

### 检查回调和事件

要查看连接到对象的事件，请使用 `call` 命令并提供要检查的对象的名称或 ID。例如，`call here` 用于检查您当前所在位置的事件。或者 `call self` 查看您自己的事件。

此命令将显示一个表格，包含：

- 第一列中每个事件的名称。
- 第二列中这些回调的名称数量和总行数。
- 第三列中告诉您事件何时触发的简短帮助。

如果您执行 `call #1`，您可能会看到这样的表格：

```
+------------------+---------+-----------------------------------------------+
| Event name       |  Number | Description                                   |
+~~~~~~~~~~~~~~~~~~+~~~~~~~~~+~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~+
| can_delete       |   0 (0) | Can the character be deleted?                 |
| can_move         |   0 (0) | Can the character move?                       |
| can_part         |   0 (0) | Can the departing character leave this room?  |
| delete           |   0 (0) | Before deleting the character.                |
| greet            |   0 (0) | A new character arrives in the location of    |
|                  |         | this character.                               |
| move             |   0 (0) | After the character has moved into its new    |
|                  |         | room.                                         |
| puppeted         |   0 (0) | When the character has been puppeted by a     |
|                  |         | player.                                       |
| time             |   0 (0) | A repeated event to be called regularly.      |
| unpuppeted       |   0 (0) | When the character is about to be un-         |
|                  |         | puppeted.                                     |
+------------------+---------+-----------------------------------------------+
```

### 创建新回调

`/add` 开关应用于添加回调。它需要两个参数，除了对象的名称/DBREF：

1. 在等号后，事件的名称（如果未提供，将显示可能事件的列表，如上所示）。
2. 参数（可选）。

稍后我们将看到带参数的回调。目前，让我们尝试阻止角色通过此房间的“北”出口：

```
call north
+------------------+---------+-----------------------------------------------+
| Event name       |  Number | Description                                   |
+~~~~~~~~~~~~~~~~~~+~~~~~~~~~+~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~+
| can_traverse     |   0 (0) | Can the character traverse through this exit? |
| msg_arrive       |   0 (0) | Customize the message when a character        |
|                  |         | arrives through this exit.                    |
| msg_leave        |   0 (0) | Customize the message when a character leaves |
|                  |         | through this exit.                            |
| time             |   0 (0) | A repeated event to be called regularly.      |
| traverse         |   0 (0) | After the character has traversed through     |
|                  |         | this exit.                                    |
+------------------+---------+-----------------------------------------------+
```

如果我们想阻止角色通过此出口，最好的事件是“can_traverse”。

> 为什么不是“traverse”？如果您阅读两个事件的描述，您会看到“traverse”是在角色通过此出口后调用的。阻止它为时已晚。另一方面，“can_traverse”显然是在角色穿越之前检查的。

当我们编辑事件时，我们有更多信息：

```bash
call/add north = can_traverse
```

角色是否可以通过此出口？
当角色即将通过此出口时，将调用此事件。您可以使用 deny() 事件函数来阻止角色这次退出。

您可以在此事件中使用的变量：

- character: 想要通过此出口的角色。
- exit: 要穿越的出口。
- room: 角色在移动前所处的房间。

[事件函数](#事件函数)部分将详细说明 `deny()` 函数和其他事件函数。暂时说，它可以阻止一个动作（在这种情况下，它可以阻止角色通过此出口）。在您使用 `call/add` 时打开的编辑器中，您可以输入类似的内容：

```python
if character.id == 1:
    character.msg("You're the superuser, 'course I'll let you pass.")
else:
    character.msg("Hold on, what do you think you're doing?")
    deny()
```

您现在可以输入 `:wq` 保存回调并离开编辑器。

如果您输入 `call north`，您应该会看到“can_traverse”现在有一个活动回调。您可以使用 `call north = can_traverse` 查看有关连接回调的更多详细信息：

```
call north = can_traverse
+--------------+--------------+----------------+--------------+--------------+
|       Number | Author       | Updated        | Param        | Valid        |
+~~~~~~~~~~~~~~+~~~~~~~~~~~~~~+~~~~~~~~~~~~~~~~+~~~~~~~~~~~~~~+~~~~~~~~~~~~~~+
|            1 | XXXXX        | 5 seconds ago  |              | Yes          |
+--------------+--------------+----------------+--------------+--------------+
```

左列包含回调编号。您可以使用它们来获取有关特定事件的更多信息。例如，在这里：

```
call north = can_traverse 1
Callback can_traverse 1 of north:
Created by XXXXX on 2017-04-02 17:58:05.
Updated by XXXXX on 2017-04-02 18:02:50
This callback is connected and active.
Callback code:
if character.id == 1:
    character.msg("You're the superuser, 'course I'll let you pass.")
else:
    character.msg("Hold on, what do you think you're doing?")
    deny()
```

然后尝试通过此出口。尽可能用另一个角色也这样做，以查看差异。

### 编辑和删除回调

您可以使用 `@call` 命令的 `/edit` 开关编辑回调。在要编辑的对象名称和等号后，您应该提供：

1. 事件的名称（如上所示）。
2. 如果在此位置连接了多个回调，则提供一个编号。

您可以输入 `call/edit <object> = <event name>` 查看在此位置链接的回调。如果只有一个回调，它将在编辑器中打开；如果定义了更多，您将被要求提供一个编号（例如，`call/edit north = can_traverse 2`）。

`call` 命令还提供一个 `/del` 开关来删除回调。它接受与 `/edit` 开关相同的参数。

删除时，回调会被记录，因此管理员可以检索其内容，假设 `/del` 是一个错误。

### 代码编辑器

在添加或编辑回调时，事件编辑器应以代码模式打开。编辑器在此模式下支持的附加选项在 [EvEditor 的文档专用部分](https://github.com/evennia/evennia/wiki/EvEditor#the-eveditor-to-edit-code)中进行了描述。

## 使用事件

以下部分描述了如何使用事件来完成各种任务，从最简单到最复杂。

### 事件函数

为了使开发更容易，游戏内 Python 系统提供了可以在回调中使用的事件函数。您不必使用它们，它们只是快捷方式。事件函数只是可以在回调代码中使用的简单函数。

| 函数        | 参数                     | 描述                                 | 示例                                      |
|-------------|--------------------------|--------------------------------------|-------------------------------------------|
| deny        | `()`                     | 阻止某个动作发生。                   | `deny()`                                  |
| get         | `(**kwargs)`             | 获取单个对象。                       | `char = get(id=1)`                        |
| call_event  | `(obj, name, seconds=0)` | 调用另一个事件。                     | `call_event(char, "chain_1", 20)`         |

#### deny

`deny()` 函数允许中断回调和调用它的动作。在 `can_*` 事件中，它可以用于阻止动作发生。例如，在房间的 `can_say` 中，它可以阻止角色在房间中说话。可以在食物上设置一个 `can_eat` 事件，以防止此角色吃掉这食物。

在幕后，`deny()` 函数引发了一个被事件处理程序拦截的异常。然后处理程序将报告动作被取消。

#### get

`get` 事件函数是获取具有特定身份的单个对象的快捷方式。它通常用于检索具有给定 ID 的对象。在专门针对[链式事件](#链式事件)的部分中，您将看到此函数的具体示例。

#### call_event

一些回调将调用其他事件。对于在专门部分中描述的[链式事件](#链式事件)特别有用。此事件函数用于立即或在定义的时间内调用另一个事件。

您需要指定包含事件的对象作为第一个参数。第二个参数是要调用的事件的名称。第三个参数是调用此事件之前的秒数。默认情况下，此参数设置为 0（事件立即被调用）。

### 回调中的变量

在您将在各个回调中输入的 Python 代码中，您将可以访问本地变量。这些变量将取决于事件，并将在您添加或编辑回调时明确列出。如您在前面的示例中所见，当我们操作角色或角色动作时，我们通常有一个 `character` 变量，包含执行动作的角色。

在大多数情况下，当事件触发时，将调用此事件的所有回调。每个事件都会创建变量。然而，有时回调会执行，然后在您的本地中请求一个变量：换句话说，一些回调可以通过更改变量值来改变正在执行的动作。这在事件帮助中总是清楚地指定的。

一个将说明此系统的示例是可以设置在出口上的“msg_leave”事件。此事件可以更改当有人通过此出口离开时将发送给其他角色的消息。

```bash
call/add down = msg_leave
```

这应该显示：

```
自定义角色通过此出口离开时的消息。
当角色通过此出口离开时，将调用此事件。
要自定义将发送到角色来自的房间的消息，请更改变量“message”的值以提供您的自定义消息。角色本身不会收到通知。您可以使用括号之间的映射，如下所示：
    message = "{character} falls into a hole!"
在您的映射中，您可以使用 {character}（即将离开的角色）、{exit}（出口）、{origin}（角色所在的房间）和 {destination}（角色要去的房间）。如果您需要使用其他信息自定义消息，您还可以将“message”设置为 None 并发送其他内容。

您可以在此事件中使用的变量：
    character: 通过此出口离开的角色。
    exit: 正在穿越的出口。
    origin: 角色的位置。
    destination: 角色的目的地。
    message: 在位置显示的消息。
    mapping: 包含附加映射的字典。
```

如果您在事件中写入类似的内容：

```python
message = "{character} falls into a hole in the ground!"
```

如果角色 Wilfred 走这条出口，房间里的其他人将看到：

```
Wildred falls into a hole in the ground!
```

在这种情况下，游戏内 Python 系统将变量“message”放置在回调本地中，但将在事件执行后从中读取。

### 带参数的回调

一些回调是在没有参数的情况下调用的。对于我们之前看到的所有示例都是这种情况。在某些情况下，您可以创建仅在某些条件下触发的回调。一个典型的例子是房间的“say”事件。此事件在有人在房间中说话时触发。设置在此事件上的各个回调可以配置为仅在句子中使用某些词时触发。

例如，假设我们想创建一个很酷的语音操控电梯。您进入电梯并说出楼层号……电梯朝正确的方向移动。在这种情况下，我们可以创建一个带有参数“one”的回调：

```bash
call/add here = say one
```

此回调仅在用户说出包含“one”的句子时触发。

但如果我们希望在用户说 1 或 one 时触发回调呢？我们可以提供多个参数，用逗号分隔。

```bash
call/add here = say 1, one
```

或者，更多的关键词：

```bash
call/add here = say 1, one, ground
```

这次，用户可以说“take me to the ground floor”之类的话（“ground”是我们在上述回调中定义的关键词之一）。

并非所有事件都可以接受参数，并且这些事件处理参数的方式各不相同。没有一个适用于所有事件的参数含义。有关详细信息，请参阅事件文档。

> 如果您在回调变量和参数之间感到困惑，请将参数视为在运行回调之前执行的检查。带参数的事件将只触发某些特定的回调，而不是所有回调。

### 与时间相关的事件

事件通常与命令相关联，如我们之前所见。然而，这并不总是如此。事件可以由其他动作触发，正如我们稍后将看到的，甚至可以从其他事件中调用！

在所有对象上有一个特定的事件，可以在特定时间触发。这是一个具有强制参数的事件，即您希望此事件触发的时间。

例如，让我们在此房间添加一个事件，该事件应每天在 12:00 PM（时间以游戏时间而非实际时间给出）触发：

```bash
call here = time 12:00
```

```python
# 这将在每天的 MUD 中午 12:00 调用
room.msg_contents("It's noon, time to have lunch!")
```

现在，在每天的 MUD 中午，此事件将触发并执行此回调。您可以在每种类型的 typeclassed 对象上使用此事件，以便在每天的 MUD 中同时执行特定动作。

与时间相关的事件可能比这复杂得多。它们可以每小时或更频繁地触发（在许多对象上如此频繁地触发事件可能不是一个好主意）。您可以拥有每周、每月或每年运行的事件。它将根据您游戏中使用的日历类型而大不相同。时间单位的数量在游戏配置中描述。

例如，使用标准日历，您有以下单位：分钟、小时、天、月和年。您将它们指定为由冒号（:）、空格（）、或短划线（-）分隔的数字。选择感觉更合适的（通常，我们用冒号分隔小时和分钟，用短划线分隔其他单位）。

一些语法示例：

- `18:30`：每天晚上 6:30。
- `01 12:00`：每月的第一天，中午 12 点。
- `06-15 09:58`：每年 6 月 15 日（月份在日期之前），上午 9:58。
- `2025-01-01 00:00`：2025 年 1 月 1 日午夜（显然，这只会触发一次）。

请注意，我们以相反的顺序指定单位（年、月、日、小时和分钟），并用逻辑分隔符分隔它们。未定义的最小单位将设置事件应触发的频率。这就是为什么如果您使用 `12:00`，未定义的最小单位是“天”：事件将在指定时间每天触发。

> 您可以将链式事件（见下文）与时间相关的事件结合使用，以在事件中创建更多随机或频繁的动作。

### 链式事件

回调可以立即或稍后调用其他事件。这可能非常强大。

要使用链式事件，只需使用 `call_event` 事件函数。它接受 2-3 个参数：

- 包含事件的对象。
- 要调用的事件的名称。
- 可选地，在调用此事件之前等待的秒数。

所有对象都有不由命令或游戏相关操作触发的事件。它们被称为“chain_X”，如“chain_1”、“chain_2”、“chain_3”等。您可以给它们更具体的名称，只要它以“chain_”开头，如“chain_flood_room”。

与其进行长篇解释，不如看一个例子：一个地铁将在固定时间从一个地方到另一个地方。连接出口（打开门），等待片刻，关闭它们，滚动并在不同的站点停下来。这是一个相当复杂的回调集，但让我们只看打开和关闭门的部分：

```bash
call/add here = time 10:00
```

```python
# 在上午 10:00，地铁到达 ID 为 22 的房间。
# 注意，出口 #23 和 #24 分别是通往站台和返回地铁的出口。
station = get(id=22)
to_exit = get(id=23)
back_exit = get(id=24)

# 打开门
to_exit.name = "platform"
to_exit.aliases = ["p"]
to_exit.location = room
to_exit.destination = station
back_exit.name = "subway"
back_exit.location = station
back_exit.destination = room

# 显示一些消息
room.msg_contents("The doors open and wind gushes in the subway")
station.msg_contents("The doors of the subway open with a dull clank.")

# 设置门在 20 秒后关闭
call_event(room, "chain_1", 20)
```

此回调将：

1. 在上午 10:00 被调用（指定 22:00 将其设置为晚上 10:00）。
2. 在地铁和站台之间设置一个出口。注意，出口已经存在（您不需要创建它们），但它们不需要有特定的位置和目的地。
3. 在地铁和站台上显示一条消息。
4. 调用事件“chain_1”以在 20 秒后执行。

现在，“chain_1”中应该有什么？

```bash
call/add here = chain_1
```

```python
# 关闭门
to_exit.location = None
to_exit.destination = None
back_exit.location = None
back_exit.destination = None
room.msg_content("After a short warning signal, the doors close and the subway begins moving.")
station.msg_content("After a short warning signal, the doors close and the subway begins moving.")
```

在幕后，`call_event` 函数冻结了所有变量（在我们的示例中是“room”、“station”、“to_exit”、“back_exit”），因此您不需要再次定义它们。

关于调用链式事件的回调的注意事项：在某些递归级别上，回调调用自身并非不可能。如果 `chain_1` 调用 `chain_2`，然后调用 `chain_3`，然后调用 `chain_`，特别是如果它们之间没有暂停，您可能会遇到无限循环。

在处理可能在事件调用之间的暂停期间移动的角色或对象时也要小心。当您使用 `call_event()` 时，MUD 不会暂停，玩家可以输入命令，幸运的是。这也意味着，角色可以启动一个暂停一段时间的事件，但在链式事件被调用时已经离开。您需要检查这一点，甚至在暂停时将角色锁定在原地（某些动作需要锁定），或者至少检查角色是否仍在房间中，否则如果您不这样做，可能会产生不合逻辑的情况。

> 链式事件是一个特殊情况：与标准事件相反，它们是在游戏中创建的，而不是通过代码创建的。它们通常只包含一个回调，尽管没有什么可以阻止您在同一对象中创建多个链式事件。

## 在代码中使用事件

本节描述了代码中的回调和事件，如何创建新事件，如何在命令中调用它们，以及如何处理参数等特定情况。

在本节中，我们将看到如何实现以下示例：我们想创建一个“push”命令，可以用来推对象。对象可以对这个命令做出反应并触发特定事件。

### 添加新事件

添加新事件应该在您的 typeclasses 中完成。事件包含在 `_events` 类变量中，这是一个事件名称作为键的字典，以及描述这些事件的元组作为值。您还需要注册此类，以告知游戏内 Python 系统它包含要添加到此 typeclass 的事件。

在这里，我们想在对象上添加一个“push”事件。在您的 `typeclasses/objects.py` 文件中，您应该写类似的内容：

```python
from evennia.contrib.base_systems.ingame_python.utils import register_events
from evennia.contrib.base_systems.ingame_python.typeclasses import EventObject

EVENT_PUSH = """
角色推对象。
当角色在同一房间中使用“push”命令对对象时，将调用此事件。

您可以在此事件中使用的变量：
    character: 推动此对象的角色。
    obj: 连接到此事件的对象。
"""

@register_events
class Object(EventObject):
    """
    表示对象的类。
    """

    _events = {
        "push": (["character", "obj"], EVENT_PUSH),
    }
```

- 第 1-2 行：我们从游戏内 Python 系统导入了几个我们需要的东西。注意我们使用 `EventObject` 作为父类而不是 `DefaultObject`，如安装中所述。
- 第 4-12 行：我们通常在单独的变量中定义事件的帮助信息，这样更具可读性，但没有规则反对以其他方式进行。通常，帮助信息应包含单行的简短说明、几行的更长说明，然后是带有说明的变量列表。
- 第 14 行：我们在类上调用装饰器以指示它包含事件。如果您不熟悉装饰器，您不必太担心，只需记住将此行放在类定义上方即可，如果您的类包含事件。
- 第 15 行：我们创建继承自 `EventObject` 的类。
- 第 20-22 行：我们在 `_events` 类变量中定义对象的事件。这是一个字典。键是事件名称。值是一个包含以下内容的元组：
  - 变量名称的列表（字符串列表）。这将确定事件触发时需要哪些变量。这些变量将在回调中使用（我们将在下面看到）。
  - 事件帮助（字符串，我们在上面定义的）。

如果您添加此代码并重新加载游戏，创建一个对象并使用 `@call` 检查其事件，您应该会看到带有帮助信息的“push”事件。当然，目前事件存在，但尚未触发。

### 在代码中调用事件

游戏内 Python 系统可以通过所有对象上的处理程序访问。此处理程序名为 `callbacks`，可以从任何 typeclassed 对象（您的角色、房间、出口等）访问。此处理程序提供了几个方法来检查和调用此对象上的事件或回调。

要调用事件，请在对象中使用 `callbacks.call` 方法。它接受以下参数：

- 要调用的事件名称。
- 将在事件中可访问的所有变量作为位置参数。它们应按[创建新事件](#添加新事件)时选择的顺序指定。

按照相同的示例，到目前为止，我们在所有对象上创建了一个名为“push”的事件。目前此事件从未被触发。我们可以添加一个“push”命令，接受对象名称作为参数。如果此对象有效，它将调用其“push”事件。

```python
from commands.command import Command

class CmdPush(Command):

    """
    推动某物。

    用法：
        push <something>

    推动您所在位置的某物，比如电梯按钮。

    """

    key = "push"

    def func(self):
        """在推动某物时调用。"""
        if not self.args.strip():
            self.msg("Usage: push <something>")
            return

        # 搜索此对象
        obj = self.caller.search(self.args)
        if not obj:
            return

        self.msg("You push {}.".format(obj.get_display_name(self.caller)))

        # 调用此对象的“push”事件
        obj.callbacks.call("push", self.caller, obj)
```

在这里我们使用 `callbacks.call`，参数如下：

- `"push"`：要调用的事件名称。
- `self.caller`：按下按钮的人（这是我们的第一个变量，`character`）。
- `obj`：被推动的对象（我们的第二个变量，`obj`）。

在我们对象的“push”回调中，我们可以使用“character”变量（包含推动对象的人）和“obj”变量（包含被推动的对象）。

### 查看一切工作

要查看上述两个修改的效果（添加的事件和“push”命令），让我们创建一个简单的对象：

```
@create/drop rock
@desc rock = It's a single rock, apparently pretty heavy.  Perhaps you can try to push it though.
@call/add rock = push
```

在回调中您可以写：

```python
from random import randint
number = randint(1, 6)
character.msg("You push a rock... is... it... going... to... move?")
if number == 6:
    character.msg("The rock topples over to reveal a beautiful ant-hill!")
```

您现在可以尝试“push rock”。您将尝试推动岩石，而每六次中有一次，您将看到关于“美丽的蚁丘”的消息。

### 添加新的事件函数

事件函数，如 `deny()`，定义在 `contrib/base_systesm/ingame_python/eventfuncs.py` 中。您可以通过在 `world` 目录中创建一个名为 `eventfuncs.py` 的文件来添加自己的事件函数。此文件中定义的函数将作为助手添加。

您还可以决定在其他位置，甚至在多个位置创建您的事件函数。为此，请在 `server/conf/settings.py` 文件中编辑 `EVENTFUNCS_LOCATION` 设置，指定一个 Python 路径或一个定义了您的助手函数的 Python 路径列表。例如：

```python
EVENTFUNCS_LOCATIONS = [
        "world.events.functions",
]
```

### 创建带参数的事件

如果您想创建带参数的事件（例如，如果您创建一个“whisper”或“ask”命令，并需要让一些角色自动对单词做出反应），您可以在 typeclass 的 `_events` 类变量中的事件元组中设置一个附加参数。此第三个参数必须包含一个回调，该回调将在事件触发时调用以过滤回调列表。通常使用两种类型的参数（但您可以定义更多参数类型，尽管这超出了本文档的范围）。

- 关键字参数：将根据特定关键字过滤此事件的回调。如果您希望用户指定一个单词并将其与列表进行比较，这很有用。
- 短语参数：将使用整个短语过滤回调并检查其所有单词。“say”命令使用短语参数（您可以设置一个“say”回调以在短语包含一个特定单词时触发）。

在这两种情况下，您需要从 `evennia.contrib.base_systems.ingame_python.utils` 导入一个函数，并在事件定义中将其用作第三个参数。

- `keyword_event` 应用于关键字参数。
- `phrase_event` 应用于短语参数。

例如，以下是“say”事件的定义：

```python
from evennia.contrib.base_systems.ingame_python.utils import register_events, phrase_event
# ...
@register_events
class SomeTypeclass:
    _events = {
        "say": (["speaker", "character", "message"], CHARACTER_SAY, phrase_event),
    }
```

当您使用 `obj.callbacks.call` 方法调用事件时，您还应使用 `parameters` 关键字提供参数：

```python
obj.callbacks.call(..., parameters="<put parameters here>")
```

必须使用参数专门调用事件，否则系统将无法知道如何过滤回调列表。

## 一次禁用所有事件

当回调在无限循环中运行时，例如，或向玩家或其他来源发送不需要的信息时，您作为游戏管理员有权在没有事件的情况下重新启动。执行此操作的最佳方法是在您的设置文件（`server/conf/settings.py`）中使用自定义设置：

```python
# 禁用所有事件
EVENTS_DISABLED = True
```

游戏内 Python 系统仍然可以访问（您将可以访问 `call` 命令进行调试），但不会自动调用任何事件。


```{toctree}
:hidden:

Contrib-Ingame-Python-Tutorial-Dialogue
Contrib-Ingame-Python-Tutorial-Elevator

```


