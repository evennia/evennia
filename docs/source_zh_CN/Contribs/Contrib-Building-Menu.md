# 构建菜单

由 vincent-lg 贡献，2018年

构建菜单是在游戏内的菜单，类似于 `EvMenu`，但采用了不同的方法。构建菜单特别设计用于作为构建者编辑信息。在命令中创建构建菜单可以让构建者快速编辑给定对象，比如一个房间。如果你按照步骤添加这个贡献，你将可以使用 `edit` 命令来编辑任何默认对象，提供更改其键和描述的功能。

## 安装

1. 在 `mygame/commands/default_cmdset.py` 文件中导入这个贡献的 `GenericBuildingCmd` 类：

    ```python
    from evennia.contrib.base_systems.building_menu import GenericBuildingCmd
    ```

2. 在 `CharacterCmdSet` 中添加命令：

    ```python
    # ... 这些行应该存在于文件中
    class CharacterCmdSet(default_cmds.CharacterCmdSet):
        key = "DefaultCharacter"

        def at_cmdset_creation(self):
            super().at_cmdset_creation()
            # ... 添加下面的行
            self.add(GenericBuildingCmd())
    ```

## 基本用法

`edit` 命令将允许你编辑任何对象。你需要指定对象的名称或 ID 作为参数。例如：`edit here` 将编辑当前房间。但是，构建菜单可以执行比这个非常简单的示例更多的功能，继续阅读以获取更多详情。

构建菜单可以被设置为编辑任何东西。以下是你在编辑房间时获得的输出示例：

```
 正在编辑房间： Limbo(#2)

 [T]itle: the limbo room
 [D]escription
    This is the limbo room.  You can easily change this default description,
    either by using the |y@desc/edit|n command, or simply by entering this
    menu (enter |yd|n).
 [E]xits:
     north to A parking(#4)
 [Q]uit this menu
```

从那里，你可以通过按 t 来打开标题选项。你可以一路输入文本来改变房间标题，然后输入 @ 以返回主菜单（这些都是可自定义的）。按 q 退出此菜单。

首先，创建一个新模块并在其中放置一个继承自 `BuildingMenu` 的类。

```python
from evennia.contrib.base_systems.building_menu import BuildingMenu

class RoomBuildingMenu(BuildingMenu):
    # ...
```

接下来，重写 `init` 方法（而不是 `__init__`！）。你可以使用 `add_choice` 方法添加选项（如上面看到的标题、描述和出口选项）。

```python
class RoomBuildingMenu(BuildingMenu):
    def init(self, room):
        self.add_choice("title", "t", attr="key")
```

这将创建第一个选项，即标题选项。如果有人打开你的菜单并输入 t，她将进入标题选项。她可以更改标题（它将写入房间的 `key` 属性），然后通过输入 `@` 返回主菜单。

`add_choice` 有很多参数，并提供了很大的灵活性。最有用的可能是回调的使用，因为几乎可以将 `add_choice` 中的任何参数设置为回调，这是你在模块上方定义的函数。当菜单元素被触发时，这个函数将被调用。

请注意，要编辑描述，最好的方法不是调用 `add_choice`，而是调用 `add_choice_edit`。这是一个方便的快捷方式，可以快速打开 `EvEditor`，然后在编辑器关闭时返回菜单。

```python
class RoomBuildingMenu(BuildingMenu):
    def init(self, room):
        self.add_choice("title", "t", attr="key")
        self.add_choice_edit("description", key="d", attr="db.desc")
```

当你想创建一个构建菜单时，只需导入你的类，创建它并指定你的意图呼叫者和要编辑的对象，然后调用 `open`：

```python
from <wherever> import RoomBuildingMenu

class CmdEdit(Command):

    key = "redit"

    def func(self):
        menu = RoomBuildingMenu(self.caller, self.caller.location)
        menu.open()
```

## 简单菜单示例

在深入之前，有一些事情需要指出：

- 构建菜单作用于一个对象。此对象将在菜单操作中被编辑。因此，你可以创建一个菜单来添加/编辑房间、出口、角色等等。
- 构建菜单以选项的层次结构排列。一个选项可以访问一个子菜单。选项与命令链接（通常非常简短）。例如，在下面的示例中，要编辑房间键，在打开构建菜单后，可以输入 `k`。这将带你进入键选项，你可以输入新的键以房间的名称。然后你可以通过输入 `@` 离开这个选项并返回到整个菜单。（所有这些都可以更改）。
- 要打开菜单，你将需要类似于命令的东西。此贡献提供了一个基本命令以供演示，但我们将在此示例中使用相同的代码重写它，以获得更多灵活性。

那么让我们添加一个非常基本的示例开始。

### 通用编辑命令

首先添加一个新命令。你可以添加或编辑以下文件（这里没有技巧，随意以不同的方式组织代码）：

```python
# 文件: commands/building.py
from evennia.contrib.building_menu import BuildingMenu
from commands.command import Command

class EditCmd(Command):

    """
    编辑命令。

    使用：
      @edit [object]

    打开一个构建菜单以编辑指定对象。此菜单允许你指定此对象的相关信息。

    示例：
      @edit here
      @edit self
      @edit #142

    """

    key = "@edit"
    locks = "cmd:id(1) or perm(Builders)"
    help_category = "Building"

    def func(self):
        if not self.args.strip():
            self.msg("|r你应该提供一个参数来执行此功能：要编辑的对象.|n")
            return

        obj = self.caller.search(self.args.strip(), global_search=True)
        if not obj:
            return

        if obj.typename == "Room":
            Menu = RoomBuildingMenu
        else:
            obj_name = obj.get_display_name(self.caller)
            self.msg(f"|r对象 {obj_name} 不能被编辑.|n")
            return

        menu = Menu(self.caller, obj)
        menu.open()
```

这个命令本身相当简单：

1. 它有一个键 `@edit`，并且锁定以仅允许构建者使用它。
2. 在其 `func` 方法中，它首先检查参数，如果没有指定参数则返回错误。
3. 然后，它搜索给定的参数。我们全局搜索。以这种方式使用的 `search` 方法将返回找到的对象或 `None`。如果需要，`search` 还会向调用者发送错误消息。
4. 假设我们找到了一个对象，我们检查对象的 `typename`。以后我们将用到这一点，当我们想显示多个构建菜单时。当前我们只处理 `Room`。如果调用者指定了其他内容，我们将显示错误。
5. 假设这个对象是一个 `Room`，我们定义了一个 `Menu` 对象，包含我们的构建菜单类。我们构建这个类（创建一个实例），将调用者和要编辑的对象传递给它。
6. 然后，我们打开构建菜单，使用 `open` 方法。

最后一点可能乍一看让人感到惊讶。但过程仍然非常简单：我们创建一个构建菜单实例并调用它的 `open` 方法。没有更多了。

> 我们的构建菜单在哪里？

如果你继续添加这个命令并进行测试，你将遇到错误。我们还没有定义 `RoomBuildingMenu`。

要添加此命令，请编辑 `commands/default_cmdsets.py`。导入我们的命令，在文件顶部添加一行导入：

```python
"""
...
"""

from evennia import default_cmds

# 添加以下行
from commands.building import EditCmd
```

并在下面的类中（`CharacterCmdSet`），添加这行代码：

```python
class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    `CharacterCmdSet` 包含像 `look`、`get` 等的常规游戏内命令，这些命令在游戏内角色对象上可用。
    它与 `AccountCmdSet` 合并，当一个帐户木偶化角色时。
    """
    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        填充 cmdset
        """
        super().at_cmdset_creation()
        #
        # 你在下面添加的所有命令都会覆盖默认命令。
        #
        self.add(EditCmd())
```

### 我们的第一个菜单

到目前为止，我们无法使用我们的构建菜单。我们的 `@edit` 命令将抛出错误。我们必须定义 `RoomBuildingMenu` 类。打开 `commands/building.py` 文件，在文件末尾添加：

```python
# ... 在 commands/building.py 的末尾
# 我们的构建菜单

class RoomBuildingMenu(BuildingMenu):

    """
    用于编辑房间的构建菜单。

    目前我们只有一个选项：键，用来编辑房间的键。

    """

    def init(self, room):
        self.add_choice("key", "k", attr="key")
```

保存这些更改，重新加载你的游戏。现在你可以使用 `@edit` 命令。请看我们得到的内容（请注意，输入游戏的命令前将会有 `>` 前缀，虽然此前缀可能不会出现在你的 MUD 客户端中）：

```
> look
Limbo(#2)
欢迎来到你的新 Evennia 基于的游戏！如需帮助、想要贡献、报告问题或只是想加入社区，请访问 https://www.evennia.com。
作为账户 #1，你可以通过 @batchcommand tutorial_world.build 创建一个演示/教程区域。

> @edit here
构建菜单： Limbo

 [K]ey: Limbo
 [Q]uit the menu

> q
关闭构建菜单。

> @edit here
构建菜单： Limbo

 [K]ey: Limbo
 [Q]uit the menu

> k
-------------------------------------------------------------------------------
Limbo(#2) 的键

你可以通过输入它来简单地更改这个值。

使用 @ 返回主菜单。

当前值： Limbo

> A beautiful meadow
-------------------------------------------------------------------------------

A beautiful meadow(#2) 的键

你可以通过输入它来简单地更改这个值。

使用 @ 返回主菜单。

当前值： A beautiful meadow

> @
构建菜单： A beautiful meadow

 [K]ey: A beautiful meadow
 [Q]uit the menu

> q

关闭构建菜单。

> look
A beautiful meadow(#2)
欢迎来到你的新 Evennia 基于的游戏！如需帮助、想要贡献、报告问题或只是想加入社区，请访问 https://www.evennia.com。
作为账户 #1，你可以通过 @batchcommand tutorial_world.build 创建一个演示/教程区域。
```

在我们开始代码之前，让我们检查一下我们有什么：

- 当我们使用 `@edit here` 命令时，房间的构建菜单出现。
- 此菜单有两个选项：
    - 输入 `k` 来编辑房间键。你将进入一个选项，你可以简单地输入房间键（正如我们在这里做的那样）。你可以使用 `@` 返回菜单。
    - 你可以使用 `q` 来退出菜单。

接下来我们检查，使用 `look` 命令确认菜单已修改了这个房间的键。因此，通过添加一个类、一个方法和一行代码，我们已经添加了一个包含两个选项的菜单。

### 代码说明

让我们再次检查我们的代码：

```python
class RoomBuildingMenu(BuildingMenu):

    """
    用于编辑房间的构建菜单。

    目前我们只有一个选项：键，用来编辑房间的键。

    """

    def init(self, room):
        self.add_choice("key", "k", attr="key")
```

- 我们首先创建一个继承自 `BuildingMenu` 的类。当我们想要使用这个贡献创建构建菜单时，通常会这样做。
- 在这个类中，我们重写 `init` 方法，当菜单打开时会被调用。
- 在这个 `init` 方法中，我们调用 `add_choice`。这接受多个参数，但在这里我们只定义了三个：
    - 选项名称。这是强制性的，构建菜单会使用它来知道如何显示这个选项。
    - 访问此选项的命令键。我们给予了简单的 `"k"`。菜单命令通常是相当简短的（这正是构建菜单受到构建者喜爱的部分原因）。你还可以指定额外的别名，稍后我们将看到。
    - 我们添加了一个关键字参数 `attr`。这告诉构建菜单，当我们在选项中时，输入的文本进入这个属性名称。它叫做 `attr`，但它可以是房间的属性或类型类的持久性或非持久性属性（我们还会看到其他示例）。

> 我们在这里添加了 `key` 的菜单选项，但为什么会为 `quit` 定义另一个菜单选项？

我们的构建菜单会在选项列表的末尾创建一个选项，如果它是顶级菜单（子菜单没有这个特性）。但是你可以覆盖它，提供一个不同的“退出”消息或执行某些操作。

我鼓励你与这段代码互动。虽然它相当简单，但已经提供了一些功能。

## 自定义构建菜单

这一段较长的部分解释了如何自定义构建菜单。具体的方法取决于你想要实现的目标。我们将从具体到更高级的方法进行介绍。

### 通用选项

在之前的示例中，我们使用了 `add_choice`。这是三种可以用来添加选项的方法之一。其他两种用于处理更通用的操作：

- `add_choice_edit`：这被称为添加一个指向 `EvEditor` 的选项。它通常用于编辑描述，尽管你可以编辑其他内容。我们将很快看到示例。`add_choice_edit` 使用我们将看到的大多数 `add_choice` 关键字参数，但通常我们只指定两个（有时三个）：
    - 选项标题如往常一样。
    - 选项键（命令键）如往常一样。
    - 可选地，使用 `attr` 关键字参数指定要编辑的对象的属性。默认 `attr` 的值为 `db.desc`，这意味着该持久数据属性将由 `EvEditor` 编辑。尽管你可以将其更改为任何你想要的。
- `add_choice_quit`：这允许添加一个选择以退出编辑器。大多数情况下，建议使用此选项！如果你不这样做，构建菜单将自动执行该操作，除非你真的告诉它不这样。再次，你可以指定选项的标题和键。你还可以在此菜单关闭时调用一个函数。

所以这是一个更完整的示例（你可以用以下代码替换 `commands/building.py` 中的 `RoomBuildingMenu` 类以查看效果）：

```python
class RoomBuildingMenu(BuildingMenu):

    """
    用于编辑房间的构建菜单。
    """

    def init(self, room):
        self.add_choice("key", "k", attr="key")
        self.add_choice_edit("description", "d")
        self.add_choice_quit("退出此编辑器", "q")
```

到目前为止，我们的构建菜单类仍然很薄...但我们已经有一些有趣的特性。看看下面的 MUD 客户端输出（同样，输入游戏的命令前将会有 `>` 前缀，以区分）：

```
> @reload

> @edit here
构建菜单： A beautiful meadow

 [K]ey: A beautiful meadow
 [D]escription:
   欢迎来到你的新 Evennia 基于的游戏！如需帮助、想要贡献、报告问题或只是想加入社区，请访问 https://www.evennia.com。
   作为账户 #1，你可以通过 @batchcommand tutorial_world.build 创建一个演示/教程区域。
 [Q]uit this editor

> d

----------行编辑器 [editor]----------------------------------------------------
01| 欢迎来到你的新 |wEvennia|n 基于的游戏！如需帮助、想要贡献、报告问题或只是想加入社区，请访问 https://www.evennia.com。
02| 作为账户 #1，你可以通过 |w@batchcommand tutorial_world.build|n 创建一个演示/教程区域。

> :DD

----------[l:03 w:034 c:0247]------------(:h for help)----------------------------
清除了缓冲区中的 3 行。

> 这是一个美丽的草地，但太美了以至于我无法描述它。

01| 这是一个美丽的草地，但太美了以至于我无法描述它。

> :wq
构建菜单： A beautiful meadow

 [K]ey: A beautiful meadow
 [D]escription:
   这是一个美丽的草地，但太美了以至于我无法描述它。
 [Q]uit this editor

> q
关闭构建菜单。

> look
A beautiful meadow(#2)
这是一个美丽的草地，但太美了。
```

通过使用构建菜单中的 `d` 快捷键，打开了 `EvEditor`。你可以使用 `EvEditor` 命令（就像我们在这里做的那样，使用 `:DD` 来移除所有，使用 `:wq` 来保存并退出）。当你退出编辑器时，描述被保存（在这里，即 `room.db.desc`）并返回构建菜单。

请注意，退出选项的选择也发生了变化，这是由于我们添加了 `add_choice_quit`。在大多数情况下，你可能不需要使用此方法，因为退出菜单会被自动添加。

### `add_choice` 选项

`add_choice` 和两个方法 `add_choice_edit` 和 `add_choice_quit` 采取许多可选参数以便于自定义。某些这些选项可能并不适用于 `add_choice_edit` 或 `add_choice_quit`。

以下是 `add_choice` 的选项，作为参数指定它们：

- 第一个位置参数，强制性参数是选择的标题，如我们所见。这将影响该选择在菜单中的显示方式。
- 第二个位置参数，强制性参数是访问此菜单的命令键。最好使用关键字参数用于其他参数。
- `aliases` 关键字参数可以包含一个别名列表，用于访问此菜单。例如：`add_choice(..., aliases=['t'])`
- `attr` 关键字参数包含在选择被选中时要编辑的属性。它是一个字符串，必须是对象（在菜单构造函数中指定的对象）到达此属性的名称。例如，`attr` 为 `"key"` 将尝试找到 `obj.key` 以读取和写入属性。你可以指定更复杂的属性名称，例如，`attr="db.desc"` 以设置持久属性 `desc`，或者使用 `attr="ndb.something"` 以使用对象上的非持久性数据属性。
- `text` 关键字参数用于更改在选择被选择时所显示的文本。菜单选项提供默认文本，你可以更改它。因为这是一个较长的文本，所以有多行字符串非常有用（见下文的示例）。
- `glance` 关键字参数用于指定当前信息的显示方式，当菜单选择未被打开时。在前面的示例中，你会看到当前的（`key` 或 `db.desc`）在菜单中显示，位于命令键旁边。这个功能对于查看当前值（因此命名为 glance）非常有用。再次，菜单选择将提供默认的 glance，如果不指定则将显示。
- `on_enter` 关键字参数允许在菜单选择被打开时添加一个回调。这更高级，但在某些情况下非常有用。
- `on_nomatch` 关键字参数在进入菜单时，调用者输入的文本与任何命令不匹配时被调用（包括 `@` 命令）。默认情况下，这将编辑指定的 `attr`。
- `on_leave` 关键字参数允许指定当调用者离开菜单选择时使用的回调。这对清理非常有用。

这些是许多可能性，但大多数情况下，你不会需要它们。以下是一个简短的示例，使用这些参数的一些（同样，用以下代码替换 `commands/building.py` 中的 `RoomBuildingMenu` 类以查看效果）：

```python
class RoomBuildingMenu(BuildingMenu):

    """
    用于编辑房间的构建菜单。

    目前我们只有一个选项：键，用来编辑房间的键。

    """

    def init(self, room):
        self.add_choice("title", key="t", attr="key", glance="{obj.key}", text="""
                -------------------------------------------------------------------------------
                编辑 {{obj.key}}(#{{obj.id}}) 的标题

                你可以简单通过输入来更改标题。
                使用 |y{back}|n 返回主菜单。

                当前标题： |c{{obj.key}}|n
        """.format(back="|n 或 |y".join(self.keys_go_back)))
        self.add_choice_edit("description", "d")
```

重新加载你的游戏，看它如何运作：

```
> @edit here
构建菜单： A beautiful meadow

 [T]itle: A beautiful meadow
 [D]escription:
   欢迎来到你的新 Evennia 基于的游戏！如需帮助、想要贡献、报告问题或只是想加入社区，请访问 https://www.evennia.com。
   作为账户 #1，你可以通过 @batchcommand tutorial_world.build 创建一个演示/教程区域。
 [Q]uit the menu

> t
-------------------------------------------------------------------------------

编辑 {{obj.key}}(#{{obj.id}}) 的标题

你可以简单通过输入来更改标题。
使用 |y{back}|n 返回主菜单。

当前标题： A beautiful meadow

> @

构建菜单： A beautiful meadow

 [T]itle: A beautiful meadow
 [D]escription:
   欢迎来到你的新 Evennia 基于的游戏！如需帮助、想要贡献、报告问题或只是想加入社区，请访问 https://www.evennia.com。
   作为账户 #1，你可以通过 @batchcommand tutorial_world.build 创建一个演示/教程区域。
 [Q]uit the menu

> q
关闭构建菜单。
```

最令人惊讶的部分无疑是文本。我们使用多行语法（使用 `"""`）。过多的空格将自动从每一行的左侧移除。我们在大括号之间指定了一些信息...有时使用双大括号。这可能有点奇怪：

- `{back}` 是我们将使用的直接格式参数（请查看 `.format` 指定符）。
- `{{obj...}}` 指的是正在编辑的对象。我们用两个大括号，因为 `.format` 会删除它们。

在 `glance` 中，我们也使用 `{obj.key}` 来指示我们想显示房间的键。

### 一切都可以是函数

`add_choice` 的关键字参数通常是字符串（类型 `str`）。但是，这些参数中的每一个也可以是一个函数。这允许了很多自定义，因为我们定义将执行的回调来实现某种操作。

为了演示这一点，我们将尝试添加一个新特性。我们的房间构建菜单仍然不错，但能够编辑出口就更好了。所以我们可以在描述下方添加一个新选项...但怎么实际编辑出口呢？出口不仅是一个要设置的属性：出口是介于两个房间之间的对象（默认是 `Exit` 类型）。那么，我们该如何显示这个呢？

首先，让我们在 limbo 中添加几个出口，因此我们有东西可以使用：

```
@tunnel n
@tunnel s
```

这应该在 limbo 中创建两个新房间，出口分别通向它们，并且可以从 limbo 返回。

```
> look
A beautiful meadow(#2)
这是一个美丽的草地，但太美了。
出口： north(#4) 和 south(#7)
```

我们可以使用 `exits` 属性访问房间出口：

```
> @py here.exits
[<Exit: north>, <Exit: south>]
```

所以我们需要在构建菜单中显示这个列表...并且能够编辑它会很棒。也许甚至添加新出口？

首先，让我们写一个函数来显示当前出口的 `glance`。以下是代码，下面进行解释：

```python
class RoomBuildingMenu(BuildingMenu):

    """
    用于编辑房间的构建菜单。

    """

    def init(self, room):
        self.add_choice("title", key="t", attr="key", glance="{obj.key}", text="""
                -------------------------------------------------------------------------------
                编辑 {{obj.key}}(#{{obj.id}}) 的标题

                你可以简单通过输入来更改标题。
                使用 |y{back}|n 返回主菜单。

                当前标题： |c{{obj.key}}|n
        """.format(back="|n 或 |y".join(self.keys_go_back)))
        self.add_choice_edit("description", "d")
        self.add_choice("exits", "e", glance=glance_exits, attr="exits")


# 菜单函数
def glance_exits(room):
    """显示房间出口。"""
    if room.exits:
        glance = ""
        for exit in room.exits:
            glance += f"\n  |y{exit.key}|n"

        return glance

    return "\n  |g尚无出口|n"
```

当构建菜单打开时，它向调用者显示每个选项。一个选项以其标题显示（稍微渲染得好看一点，以显示键和 glance）。在 `exits` 选项的情况下，glance 是一个函数，因此构建菜单会调用这个函数，给它提供正在编辑的对象（在这里是房间）。这个函数应返回文本。

```
> @edit here
构建菜单： A beautiful meadow

 [T]itle: A beautiful meadow
 [D]escription:
   这是一个美丽的草地，但太美了。
 [E]xits:
  north
  south
 [Q]uit the menu

> q
关闭编辑器。
```

> 我怎么知道函数的参数？

你提供的函数可以接受许多不同的参数。这允许更灵活的方法，但可能看起来在开始时有点复杂。基本上，你的函数可以接受任何参数，构建菜单将根据参数名称发送参数。如果你的函数定义了名为 `caller` 的参数（例如 `def func(caller):`），那么构建菜单知道第一个参数应该包含构建菜单的调用者。以下是参数列表，你不必明确指定（如果你这样做，则参数名称必须相同）：

- `menu`：如果你的函数定义了名为 `menu` 的参数，它将含有构建菜单本身。
- `choice`：如果你的函数定义了名为 `choice` 的参数，它将含有表示此菜单选择的 `Choice` 对象。
- `string`：如果你的函数定义了名为 `string` 的参数，它将包含用户输入以到达此菜单选择。这在 `nomatch` 回调（我们稍后将看到）中不是很有用。
- `obj`：如果你的函数定义了名为 `obj` 的参数，它将包含通过构建菜单所编辑的对象。
- `caller`：如果你的函数定义了名为 `caller` 的参数，它将包含构建菜单的调用者。
- 其他任何内容：任何其他参数将包含通过构建菜单编辑的对象。

所以在我们的案例中：

```python
def glance_exits(room):
```

唯一需要的参数是 `room`。它不在可能参数列表中，因此将构建菜单（在这里是房间）给出的编辑对象。

> 获取菜单或选择对象有什么好处？

大多数情况下，你不需要这些参数。很少情况下，你会使用它们来获得特定数据（例如，设置的默认属性）。本教程不会详细阐述这些可能性。只需了解它们的存在。

我们还应该定义一个文本回调，以便能够进入菜单以查看房间的出口。我们将看到如何编辑它们在下一部分，但这是一个展示更完整回调的好机会。为了让它在操作时生效，通常用以下代码替换 `commands/building.py` 中的类和函数：

```python
# 我们的构建菜单

class RoomBuildingMenu(BuildingMenu):

    """
    用于编辑房间的构建菜单。

    """

    def init(self, room):
        self.add_choice("title", key="t", attr="key", glance="{obj.key}", text="""
                -------------------------------------------------------------------------------
                编辑 {{obj.key}}(#{{obj.id}}) 的标题

                你可以简单通过输入来更改标题。
                使用 |y{back}|n 返回主菜单。

                当前标题： |c{{obj.key}}|n
        """.format(back="|n 或 |y".join(self.keys_go_back)))
        self.add_choice_edit("description", "d")
        self.add_choice("exits", "e", glance=glance_exits, attr="exits", text=text_exits)


# 菜单函数
def glance_exits(room):
    """显示房间出口。"""
    if room.exits:
        glance = ""
        for exit in room.exits:
            glance += f"\n  |y{exit.key}|n"

        return glance

    return "\n  |g尚无出口|n"

def text_exits(caller, room):
    """在选择本身显示房间出口。"""
    text = "-" * 79
    text += "\n\n房间出口:"
    text += "\n 使用 |y@c|n 创建新出口。"
    text += "\n\n现有出口:"
    if room.exits:
        for exit in room.exits:
            text += f"\n  |y@e {exit.key}|n"
            if exit.aliases.all():
                text += " (|y{aliases}|n)".format(aliases="|n, |y".join(
                    alias for alias in exit.aliases.all()
                ))
            if exit.destination:
                text += f" 向 {exit.get_display_name(caller)}"
    else:
        text += "\n\n |g尚未定义任何出口.|n"

    return text
```

特别注意第二个回调。它接受一个额外的参数，调用者（记住，参数名称很重要，参数顺序并不相关）。这在准确显示出口目标时非常有用。以下是这个菜单的演示：

```
> @edit here
构建菜单： A beautiful meadow

 [T]itle: A beautiful meadow
 [D]escription:
   这是一个美丽的草地，但太美了。
 [E]xits:
  north
  south
 [Q]uit the menu

> e
-------------------------------------------------------------------------------

房间出口：
 使用 |y@c|n 创建新出口。

现有出口：
  @e north (n) 向 north(#4)
  @e south (s) 向 south(#7)

> @
构建菜单： A beautiful meadow

 [T]itle: A beautiful meadow
 [D]escription:
   这是一个美丽的草地，但太美了。
 [E]xits:
  north
  south
 [Q]uit the menu

> q
关闭构建菜单。
```

使用回调允许了巨大的灵活性。我们现在将看到如何处理子菜单。

### 复杂菜单的子菜单

一个菜单相对简单：它有一个根（你能够看到所有的菜单选择）和一个用户可以通过菜单选择键到达的单个选项。一旦在选项中，你可以输入一些内容或通过输入返回命令（通常是 `@`）返回根菜单。

然而，个别出口为什么不可以拥有自己的菜单呢？假设你编辑一个出口，可以更改其键、描述或别名...也许甚至目标？为什么不呢？这将使建筑变得更简单！

构建菜单系统提供了两种方法来实现这一点。第一种是嵌套键：嵌套键允许你添加带有子菜单的选项。使用它们很快，但起初可能会感觉有点反直觉。另一种选择是创建一个不同的菜单类并从第一个重定向到第二个。这种方式可能需要更多行，但更加明确，并且可以重复使用以便于多个菜单。根据你的兴趣选择其中一种。

#### 嵌套菜单键

到目前为止，我们只使用了长度为一个字母的菜单键。当然，我们可以添加更多，但菜单键在其简单形式下只是命令键。按“e”将转到“exits”选项。

但是菜单键可以嵌套。嵌套键允许添加具有子菜单的选项。例如，输入“e”转到“exits”选项，再输入“c”打开创建新出口的菜单，或输入“d”打开删除出口的菜单。第一个菜单将具有 “e.c” 键，第二个菜单具有 “e.d” 的键。

这需要一点代码和说明。以下是代码，接下来会进行解释：

```python
# ... 从 commands/building.py
# 我们的构建菜单

class RoomBuildingMenu(BuildingMenu):

    """
    用于编辑房间的构建菜单。

    目前我们只有一个选项：键，用来编辑房间的键。

    """

    def init(self, room):
        self.add_choice("title", key="t", attr="key", glance="{obj.key}", text="""
                -------------------------------------------------------------------------------
                编辑 {{obj.key}}(#{{obj.id}}) 的标题

                你可以简单通过输入来更改标题。
                使用 |y{back}|n 返回主菜单。

                当前标题： |c{{obj.key}}|n
        """.format(back="|n 或 |y".join(self.keys_go_back)))
        self.add_choice_edit("description", "d")
        self.add_choice("exits", "e", glance=glance_exits, text=text_exits, on_nomatch=nomatch_exits)

        # 出口子菜单
        self.add_choice("exit", "e.*", text=text_single_exit, on_nomatch=nomatch_single_exit)


# 菜单函数
def glance_exits(room):
    """显示房间出口。"""
    if room.exits:
        glance = ""
        for exit in room.exits:
            glance += f"\n  |y{exit.key}|n"

        return glance

    return "\n  |g尚无出口|n"

def text_exits(caller, room):
    """在选择本身显示房间出口。"""
    text = "-" * 79
    text += "\n\n房间出口:"
    text += "\n 使用 |y@c|n 创建新出口。"
    text += "\n\n现有出口:"
    if room.exits:
        for exit in room.exits:
            text += f"\n  |y@e {exit.key}|n"
            if exit.aliases.all():
                text += " (|y{aliases}|n)".format(aliases="|n, |y".join(
                    alias for alias in exit.aliases.all()
                ))
            if exit.destination:
                text += f" 向 {exit.get_display_name(caller)}"
    else:
        text += "\n\n |g尚未定义任何出口.|n"

    return text

def nomatch_exits(menu, caller, room, string):
    """
    用户在出口列表中输入了某些内容。也许是出口名称？
    """
    string = string[3:]
    exit = caller.search(string, candidates=room.exits)
    if exit is None:
        return

    # 打开子菜单，使用嵌套键
    caller.msg(f"正在编辑： {exit.key}")
    menu.move(exit)
    return False

# 出口子菜单
def text_single_exit(menu, caller):
    """显示以编辑单个出口的文本。"""
    exit = menu.keys[1]
    if exit is None:
        return ""

    return f"""
        出口 {exit.key}：

        输入出口键以更改，或 |y@|n 返回。

        新出口键：
    """

def nomatch_single_exit(menu, caller, room, string):
    """用户在出口子菜单中输入了某些内容。替换出口键。"""
    # exit 是第二个键元素：键应该包含 ['e', <Exit object>]
    exit = menu.keys[1]
    if exit is None:
        caller.msg("|r无法找到出口.|n")
        menu.move(back=True)
        return False

    exit.key = string
    return True
```

> 这很多代码！而且我们只处理出口键的编辑！

这就是你某个时候可能想要写一个真实子菜单的原因，而不是使用简单的嵌套键。但你可能同时需要两者，以构建漂亮的菜单！

1. 新的内容在我们的菜单类中。在为出口菜单创建了 `on_nomatch` 回调后（这没什么惊讶的），我们需要添加一个嵌套键。我们给这个菜单一个 `e.*` 键。这有点奇怪！"e" 是我们的出口选择的键，"." 是分隔符，表示一个嵌套菜单，而 "*" 表示任何内容。所以基本上，我们创建一个嵌套菜单，包含在出口菜单内以及任何内容。我们将在实际操作中看到这个“任何内容”。
2. `glance_exits` 和 `text_exits` 基本上是相同的。
3. `nomatch_exits` 很短但很有趣。当我们在“出口”菜单中输入一些文本时调用（即，在出口列表中）。我们说过，用户应该输入 `@e` 后跟出口名称以进行编辑。所以在 `nomatch_exits` 回调中，我们检查该输入。如果输入的文本以 `@e` 开头，我们尝试在房间中找到出口。如果找到...
4. 我们调用 `menu.move` 方法。这是事情变得有点复杂的地方，使用嵌套菜单：我们需要使用 `menu.move` 从一个层次切换到另一个层次。在这里，我们在出口的选择中（钥匙是“e”）。我们需要向下一个层次去编辑一个出口。因此，我们调用 `menu.move`，并给它一个出口对象。菜单系统记住用户基于她输入的键所处的位置：当用户打开菜单时，没有关键字。如果她选择出口选项，则当前菜单键为 'e'，（一个包含菜单键的列表）。如果我们调用 `menu.move`，我们给任何内容传递到这个方法，将附加到键的列表中，因此用户位置变为 `["e", <Exit object>]`。
5. 在菜单类中，我们定义了菜单 `"e.*"`，表示“包含在出口选择中的菜单加任何内容”。“任何内容”在这里是一个出口：我们调用 `menu.move(exit)`，因此选择了 `e.*` 菜单。
6. 在该菜单中，文本被设置为回调。当用户输入某些文本时，还定义了一个 `on_nomatch` 回调。

像这样使用 `menu.move` 一开始可能有点混乱。在某些情况下，它非常有用。在这种情况下，如果我们希望出口有更复杂的菜单，就更明智地使用真实的子菜单，而不是像这样嵌套键。但有时，你会发现自己处于一个不需要完整菜单来处理选择的情况。

## 完全子菜单作为单独类

处理单个出口的最佳方式是创建两个单独的类：

- 一个用于房间菜单。
- 一个用于单个出口菜单。

第一个将需要重定向到第二个。这可能更直观和灵活，具体取决于你想要实现的目标。因此，让我们构建两个菜单：

```python
# 仍在 commands/building.py，替换菜单类和函数为...
# 我们的构建菜单

class RoomBuildingMenu(BuildingMenu):

    """
    用于编辑房间的构建菜单。
    """

    def init(self, room):
        self.add_choice("title", key="t", attr="key", glance="{obj.key}", text="""
                -------------------------------------------------------------------------------
                编辑 {{obj.key}}(#{{obj.id}}) 的标题

                你可以简单通过输入来更改标题。
                使用 |y{back}|n 返回主菜单。

                当前标题： |c{{obj.key}}|n
        """.format(back="|n 或 |y".join(self.keys_go_back)))
        self.add_choice_edit("description", "d")
        self.add_choice("exits", "e", glance=glance_exits, text=text_exits,
on_nomatch=nomatch_exits)


# 菜单函数
def glance_exits(room):
    """显示房间出口。"""
    if room.exits:
        glance = ""
        for exit in room.exits:
            glance += f"\n  |y{exit.key}|n"

        return glance

    return "\n  |g尚无出口|n"

def text_exits(caller, room):
    """显示在选择本身的房间出口。"""
    text = "-" * 79
    text += "\n\n房间出口:"
    text += "\n 使用 |y@c|n 创建新出口。"
    text += "\n\n现有出口:"
    if room.exits:
        for exit in room.exits:
            text += f"\n  |y@e {exit.key}|n"
            if exit.aliases.all():
                text += " (|y{aliases}|n)".format(aliases="|n, |y".join(
                    alias for alias in exit.aliases.all()
                ))
            if exit.destination:
                text += f" 向 {exit.get_display_name(caller)}"
    else:
        text += "\n\n |g尚未定义任何出口.|n"

    return text

def nomatch_exits(menu, caller, room, string):
    """
    用户在出口列表中输入了某些内容。也许是出口名称？
    """
    string = string[3:]
    exit = caller.search(string, candidates=room.exits)
    if exit is None:
        return

    # 打开子菜单，使用嵌套键
    caller.msg(f"正在编辑： {exit.key}")
    menu.open_submenu("commands.building.ExitBuildingMenu", exit, parent_keys=["e"])
    return False

class ExitBuildingMenu(BuildingMenu):

    """
    用于编辑出口的构建菜单。

    """

    def init(self, exit):
        self.add_choice("key", key="k", attr="key", glance="{obj.key}")
        self.add_choice_edit("description", "d")
```

代码可能更容易阅读。但在详细说明之前，先看看它的行为：

```
> @edit here
构建菜单： A beautiful meadow

 [T]itle: A beautiful meadow
 [D]escription:
   这是一个美丽的草地，但太美了。
 [E]xits:
  door
  south
 [Q]uit the menu

> e
-------------------------------------------------------------------------------

房间出口：
 使用 |y@c|n 创建新出口。

现有出口：
  @e door (n) 向 door(#4)
  @e south (s) 向 south(#7)

正在编辑： door

> @e door
构建菜单： door

 [K]ey: door
 [D]escription:
   没有

> k
-------------------------------------------------------------------------------
door(#4) 的键

你可以通过输入它来简单地更改这个值。

使用 @ 返回主菜单。

当前值： door

> north

-------------------------------------------------------------------------------
key for north(#4)

你可以简单通过输入来更改这个值。

使用 @ 返回主菜单。

当前值： north

> @
构建菜单： north

 [K]ey: north
 [D]escription:
   没有

> d
----------行编辑器 [editor]----------------------------------------------------
01| 没有
----------[l:01 w:001 c:0004]------------(:h for help)----------------------------

> :DD
清除了缓冲区中的 1 行。

> 这是北边的出口。太酷了吧？
01| 这是北边的出口。太酷了吧？

> :wq
构建菜单： north
 [K]ey: north
 [D]escription:
   这是北边的出口。太酷了吧？

> @
-------------------------------------------------------------------------------

房间出口：
 使用 |y@c|n 创建新出口。

现有出口：
  @e north (n) 向 north(#4)
  @e south (s) 向 south(#7)

> @
构建菜单： A beautiful meadow

 [T]itle: A beautiful meadow
 [D]escription:
   这是一个美丽的草地，但太美了。
 [E]xits:
  north
  south
 [Q]uit the menu

> q
关闭构建菜单。

> look
A beautiful meadow(#2)
这是一个美丽的草地，但太美了。
出口： north(#4) 和 south(#7)
> @py here.exits[0]
>>> here.exits[0]
north
> @py here.exits[0].db.desc
>>> here.exits[0].db.desc
这是北边的出口。太酷了吧？
```

我们非常简单地创建了两个菜单并将它们连接起来。这需要的回调更少。在 `nomatch_exits` 中我们只需要添加一行：

```python
    menu.open_submenu("commands.building.ExitBuildingMenu", exit, parent_keys=["e"])
```

我们必须在菜单对象上调用 `open_submenu`（如其名，打开一个子菜单），并给出三个参数：

- 创建菜单类的路径。它是通向菜单的 Python 类（请注意其中的点）。
- 将由菜单编辑的对象。在这里它是我们的 `exit`，因此我们将其传递给子菜单。
- 子菜单关闭时要打开的父级的键。基本上，当我们在子菜单的根目录中并按 `@` 时，我们将打开父菜单，带上父键。因此，我们指定 `["e"]`，因为父菜单是“exits”选择。

就这样。新类将自动创建。正如你所看到的，我们还必须创建 `on_nomatch` 回调以打开子菜单，但一旦打开，它在需要时会自动关闭。

### 通用菜单选项

所有菜单类都有一些可以设置的选项。这些选项允许更大的自定义。它们是类属性（见下面的示例），只需在类体中设置即可：

- `keys_go_back`（默认为 `["@"]`）：用于在菜单层次结构中向后返回的键，从选择到根菜单，从子菜单到父菜单。默认情况下，仅使用 `@`。你可以为一个菜单或所有菜单更改这个键。如果您希望有多个返回命令，也可以定义多个。
- `sep_keys`（默认为 `"."`）：这是嵌套键的分隔符。除非你真的需要将点用作键并且需要菜单中有嵌套键，否则无需重新定义它。
- `joker_key`（默认为 `"*"`）：用于嵌套键以指示“任何键”。同样，除非你想使用 `@*@` 作为命令键，并且还需要菜单中有嵌套键，否则你不应该更改它。
- `min_shortcut`（默认为 `1`）：尽管我们在这里没有看到，但可以创建没有为其提供键的菜单选择。如果是这样，菜单系统将尝试“猜测”密钥。此选项允许更改安全原因下任何键的最小长度。

要设置其中一个，只需在你的菜单类中这样做：

```python
class RoomBuildingMenu(BuildingMenu):
    keys_go_back = ["/"]
    min_shortcut = 2
```

## 结论

构建菜单意味着节省时间并创建丰富而又简单的界面。但是它们可能很复杂，学习需要时间，需要阅读源代码才能发现如何做某事。尽管如此，这篇文档（尽管冗长）试图描述这一系统，但在阅读后，你可能仍然会对它有疑问，特别是如果你尝试推动该系统到一个较大程度。请随时阅读此贡献的文档，它旨在详尽且用户友好。


----

<small>此文档页面并非由 `evennia/contrib/base_systems/building_menu/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
