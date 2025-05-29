# 建造一个巨型机甲

让我们在 Evennia 中创建一个功能性的巨型机甲。每个人都喜欢巨型机甲，对吧？作为具有构建权限的角色（或超级用户）开始游戏。

```plaintext
create/drop Giant Mech ; mech
```

砰，我们创建了一个巨型机甲对象并将其放入房间。我们还给它一个别名 *mech*。让我们描述一下它。

```plaintext
desc mech = This is a huge mech. It has missiles and stuff.
```

接下来，我们定义谁可以“操控”机甲对象。

```plaintext
lock mech = puppet:all()
```

这将允许所有人控制机甲。更多机甲归人民！（请注意，虽然 Evennia 的默认命令可能看起来略似 MUX 风格，你可以将语法更改为你喜欢的任何接口样式。）

在我们继续之前，让我们稍作岔路。Evennia 对其对象非常灵活，更加灵活的是对这些对象使用和添加命令。以下是一些值得铭记的基本原则，供本文接下来的部分参考：

- [帐户](../Components/Accounts.md) 代表真实登录的人，没有游戏世界的存在。
- 任何 [对象](../Components/Objects.md) 都可以被帐户操控（如果拥有适当权限）。
- [角色](../Components/Objects.md#characters)、[房间](../Components/Objects.md#rooms) 和 [出口](../Components/Objects.md#exits) 都是普通对象的子类。
- 任何对象都可以在另一个对象内部（除非会造成循环）。
- 任何对象都可以存储自定义命令集。这些命令可以：
  - 对操控者（帐户）可用,
  - 对与对象在同一位置的任何玩家可用,
  - 对“内部”的任何人可用。
  - 帐户也可以在自身上存储命令。帐户命令总是可用，除非在被操控对象上显式覆盖。

在 Evennia 中，使用 `ic` 命令将允许你操控给定的对象（假设你有操控访问权限）。正如上面所提到的，标准的角色类实际上就像任何对象一样：它在登录时被自动操控，并仅包含包含正常游戏命令的命令集，如观察、背包、获取等。

```plaintext
ic mech
```

你刚刚跳出了你的角色，现在你控制的是机甲！如果人们在游戏中查看你，他们将看到一个机甲。此时的问题是，该机甲对象没有自己的命令。通常的命令如观察、背包和获取都在角色对象上，记得吗？所以目前机甲不过是个“人形”。

```plaintext
ic <Your old Character>
```

你刚刚跳回到操控你正常的、平凡的角色。万事如意。

> `ic` 命令从何而来？如果机甲没有命令呢？答案是它来自帐户的命令集。这一点很重要。如果没有帐户拥有 `ic` 命令，我们将无法再次跳出机甲。

## 让机甲能够开火

让我们让机甲更加有趣。在我们喜欢的文本编辑器中，我们将创建一些新的适合机甲的命令。在 Evennia 中，命令被定义为 Python 类。

```python
# 在新的文件 mygame/commands/mechcommands.py 中

from evennia import Command

class CmdShoot(Command):
    """
    开火机甲的炮

    用法:
      shoot [target]

    这将发射你的机甲主炮。如果没有
    给定目标，你将向天空开火。
    """
    key = "shoot"
    aliases = ["fire", "fire!"]

    def func(self):
        "这实际上是开火的实现"

        caller = self.caller
        location = caller.location

        if not self.args:
            # 命令未给定参数 - 向天空开火
            message = "BOOM! The mech fires its gun in the air!"
            location.msg_contents(message)
            return

        # 我们有参数，搜索目标
        target = caller.search(self.args.strip())
        if target:
            location.msg_contents(
                f"BOOM! The mech fires its gun at {target.key}"
            )

class CmdLaunch(Command):
    # 自己实现'launch'命令，作为练习！
    # （它与上面的'shoot'命令非常相似）。

```

这将作为普通的 Python 模块保存（假设我们将其命名为 `mechcommands.py`），保存在 Evennia 查找此类模块的位置（`mygame/commands/`）。当玩家给出命令“shoot”、“fire”或甚至带有感叹号的“fire！”时，命令将被触发。机甲可以向天空开火或瞄准目标打开。在实际游戏中，炮可能会给出命中机会并造成伤害，但现在这就足够了。

我们还为发射导弹创建了第二个命令（`CmdLaunch`）。为了节省空间，我们这里不详细描述，它的实现相似，只是返回有关导弹发射的文本并具有不同的 `key` 和 `aliases`。我们将此留给你进行练习。你可以让它打印 `"WOOSH! The mech launches missiles against <target>!`。

现在我们将命令放入命令集中。一个 [命令集](../Components/Command-Sets.md)（CmdSet）是一个容器，可以容纳任意数量的命令。我们将把命令集存储在机甲上。

```python
# 在同一个文件 mygame/commands/mechcommands.py 中

from evennia import CmdSet
from evennia import default_cmds

class MechCmdSet(CmdSet):
    """
    这允许机甲做机甲的事情。
    """
    key = "mechcmdset"

    def at_cmdset_creation(self):
        "在命令集首次创建时调用"
        self.add(CmdShoot())
        self.add(CmdLaunch())
```

这仅仅是将我们想要的所有命令分组。我们添加了新的开火和发射命令。现在，让我们回到游戏中进行测试。我们将手动将新的 CmdSet 附加到机甲上。

```plaintext
py self.search("mech").cmdset.add("commands.mechcommands.MechCmdSet")
```

这是一个小 Python 代码片段，搜索我们当前所在位置的机甲并将我们新的 MechCmdSet 附加到它上。我们添加的实际上是 cmdset 类的 Python 路径。Evennia 会在后台导入并初始化它。

```plaintext
ic mech
```

我们又回到了机甲上！现在让我们进行一些射击！

```plaintext
fire!
BOOM! The mech fires its gun in the air!
```

好了，一个功能齐全的机甲到位。尝试你自己的 `launch` 命令，看看它是否也能正常工作。我们不仅可以像机甲一样四处移动——由于 CharacterCmdSet 被包含在我们的 MechCmdSet 中，机甲还可以做任何角色可以做的事情，比如四处查看、捡起东西和拥有背包。现在我们可以朝目标射击或尝试导弹发射命令。拥有自己的机甲后，你还需要什么？

> 你会发现，机甲的命令只需与其在同一位置时可用（不仅在操控它时）。我们将在下一部分通过添加 *lock* 来解决这个问题。

## 创建一支机甲军队

到目前为止，我们只做了一个普通对象，描述它并将一些命令放在上面。这对于测试来说是不错的。由于我们添加了它，MechCmdSet 在重新加载服务器时确实会消失。现在，我们希望将机甲真正变成一种“类型”，这样我们就可以在不进行额外步骤的情况下创建机甲。为此，我们需要创建一个新的类型类。

一个 [类型类](../Components/Typeclasses.md) 是一个近乎正常的 Python 类，它在后台将其存在存储到数据库中。类型类是在普通的 Python 源文件中创建的：

```python
# 在新的文件 mygame/typeclasses/mech.py 中

from typeclasses.objects import Object
from commands.mechcommands import MechCmdSet
from evennia import default_cmds

class Mech(Object):
    """
    这个类型类描述了一种装备武器的机甲。
    """
    def at_object_creation(self):
        "这仅在对象首次创建时调用"
        self.cmdset.add_default(default_cmds.CharacterCmdSet)
        self.cmdset.add(MechCmdSet, persistent=True)
        self.locks.add("puppet:all();call:false()")
        self.db.desc = "This is a huge mech. It has missiles and stuff."
```

为了方便起见，我们在此处包含默认 `CharacterCmdSet` 的完整内容。这将使机甲可以使用角色的正常命令。我们还添加了之前的机甲命令，确保它们在数据库中持久保存。锁定指定任何人都可以操控机甲，并且没有人可以“调用”机甲的命令——你必须操控它才能开火。

就这样。创建这种类型的对象时，它们将始终启动机甲的命令集和正确的锁定。我们设置了一个默认描述，但你可能会通过 `desc` 的功能在构建机甲时对其个性化。

回到游戏中，只需退出旧的机甲（`@ic` 回到你的旧角色），然后执行：

```plaintext
create/drop The Bigger Mech ; bigmech : mech.Mech
```

我们创建一个新的更大的机甲，别名为 bigmech。注意我们在末尾提供了类型类的 Python 路径——这告诉 Evennia 根据该类创建新对象（我们不必在游戏目录中提供完整路径 `typeclasses.mech.Mech`，因为 Evennia 知道要在 `typeclasses` 文件夹中查找）。一个崭新的机甲将在房间中出现！只需使用

```plaintext
ic bigmech
```

来进行测试驾驶。

### 未来的机甲

让你直接操控机甲对象只是 Evennia 中实现巨大机甲的一种方式。

例如，你可以将机甲视作一个“载具”，你以正常角色的身份“进入”它（因为任何对象都可以在另一个里面移动）。在这种情况下，机甲对象的“内部”可以是“驾驶舱”。驾驶舱将存储 `MechCommandSet`，而只有当你进入时，所有开火功能才会向你提供。

你可以添加更多命令到机甲中并移除其他命令。也许机甲毕竟不应该像角色一样工作。

也许它每次在房间间移动时都会发出响亮的噪声。也许它在不压坏东西的情况下无法捡起。也许它需要燃料、弹药和维修。也许你会锁定，让它只能被情绪化的青少年操控。

当然，你还可以在机甲上安装更多武器，甚至让它飞！
