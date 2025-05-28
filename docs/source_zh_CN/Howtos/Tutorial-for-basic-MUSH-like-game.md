# MUSH 风格游戏的基本教程

本教程让你在 Evennia 中编码一个小而完整的 MUSH 风格游戏。[MUSH](https://en.wikipedia.org/wiki/MUSH) 是一种以角色扮演为中心的游戏类型，专注于自由形式的叙事。即使你对 MUSH 不感兴趣，这仍然是一个很好的第一款游戏类型，因为它不那么重视代码。你将能够使用相同的原则来构建其他类型的游戏。

本教程从头开始。 如果你已经完成了 [第一步编码](Beginner-Tutorial/Part1/Beginner-Tutorial-Part1-Overview.md) 的教程，你应该对如何做某些步骤已经有了一些想法。

以下是我们将实现的（非常简化和删减的）功能（来源于 MUSH 用户对 Evennia 的功能请求）。在这个系统中，角色应该：

- 拥有一个从 1 到 10 的“力量”分数，表示他们的强度（代表属性系统）。
- 拥有一个命令（例如 `+setpower 4`）来设置自己的力量（代表角色生成代码）。
- 拥有一个命令（例如 `+attack`），允许他们投掷力量并生成一个“战斗分数”，介于 `1` 到 `10*Power` 之间，显示结果并编辑他们的对象以记录此数字（代表 `+actions` 代码）。
- 拥有一个命令，可以显示房间中的每个人及其最近的“战斗分数”投掷（代表战斗代码）。
- 拥有一个命令（例如 `+createNPC Jenkins`）来创建一个具有完整能力的 NPC。
- 拥有一个命令来控制 NPC，例如 `+npc/cmd (name)=(command)`（代表 NPC 控制代码）。

在本教程中，我们假设从空数据库开始，没有任何之前的修改。

## 服务器设置

为了模拟 MUSH，默认的 `MULTISESSION_MODE=0` 就足够了（每个帐户/角色一个唯一会话）。这是一种默认设置，因此你无需更改任何内容。你仍然可以操纵/取消操纵你有权限的对象，但没有现成的角色选择功能。

我们将假设我们的游戏文件夹称为 `mygame`。你应该可以使用默认的 SQLite3 数据库。

## 创建角色

首先要选择我们的角色类如何运作。我们不需要定义一个特殊的 NPC 对象——NPC 毕竟只是一个当前没有帐户控制的角色。

在 `mygame/typeclasses/characters.py` 文件中进行更改：

```python
# mygame/typeclasses/characters.py

from evennia import DefaultCharacter

class Character(DefaultCharacter):
    """
     [...]
    """
    def at_object_creation(self):
        "这是只在对象首次创建时调用。"
        self.db.power = 1
        self.db.combat_score = 1
```

我们定义了两个新的 [属性](../Components/Attributes.md)：`power` 和 `combat_score`，并将它们设置为默认值。如果你已经运行服务器，请确保 `@reload` 服务器（每次更新 Python 代码时都需要重新加载，不用担心，没有帐户会被断开连接）。

请注意，只有 *新* 角色才能看到你的新属性（因为 `at_object_creation` 钩子在对象首次创建时被调用，现有角色不会拥有它）。要更新自己，请运行

```
@typeclass/force self
```

这将重置你的类型类（`/force` 开关是一个安全措施，以防止意外执行），这意味着 `at_object_creation` 会重新运行。

```
examine self
```

在“持久属性”标题下，你现在应该可以看到新属性 `power` 和 `combat_score`。如果没有，首先确保你已经 `@reload` 了新代码，然后查看服务器日志（在终端/控制台中），以检查是否有任何语法错误阻止新代码正确加载。

## 角色生成

在此示例中，我们假设帐户首先连接到一个“角色生成区域”。Evennia 还支持完整的 OOC 菜单驱动角色生成，但对于此示例，一个简单的起始房间就足够了。当在这个房间（或房间）中时，我们允许角色生成命令。实际上，角色生成命令将 *仅* 在这样的房间中可用。

注意，再次这样做是为了便于扩展到完整的游戏系统。在我们简单的示例中，我们可以简单地在账户上设置一个 `is_in_chargen` 标志，并让 `+setpower` 命令进行检查。然而使用这种方法，方便后续添加更多功能。

我们需要以下内容：

- 一个角色生成 [命令](../Components/Commands.md) 用于设置角色的“力量”。
- 一个角色生成 [CmdSet](../Components/Command-Sets.md) 来保存这个命令。我们称之为 `ChargenCmdset`。
- 一个自定义的 `ChargenRoom` 类型，使这个命令集能够在这样的房间中提供给玩家。
- 一个这样的房间来进行测试。

### +setpower 命令

为了本教程，我们将将所有新命令添加到 `mygame/commands/command.py` 中，但如果你希望，你可以将命令拆分到多个模块中。

在本教程中，角色生成将仅包括一个 [命令](../Components/Commands.md)，用于设置角色的“力量”属性。它将使用以下类似 MUSH 的形式调用：

```
+setpower 4
```

打开 `command.py` 文件。它包含基于默认命令和 Evennia 中使用的“MuxCommand”类型的空模板。我们将使用普通的 `Command` 类型，`MuxCommand` 类提供了一些额外功能，例如去除多余的空格，如果需要，请从那里导入。

向 `command.py` 文件末尾添加以下内容：

```python
# end of command.py
from evennia import Command  # 仅为清晰起见；已在上方导入

class CmdSetPower(Command):
    """
    设置角色的力量

    用法：
      +setpower <1-10>

    这将设置当前角色的力量。这只能在角色生成期间使用。
    """

    key = "+setpower"
    help_category = "mush"

    def func(self):
        "执行实际命令"
        errmsg = "你必须提供一个介于 1 和 10 之间的数字。"
        if not self.args:
            self.caller.msg(errmsg)
            return
        try:
            power = int(self.args)
        except ValueError:
            self.caller.msg(errmsg)
            return
        if not (1 <= power <= 10):
            self.caller.msg(errmsg)
            return
        # 此时参数经过测试为有效。让我们设置它。
        self.caller.db.power = power
        self.caller.msg(f"你的力量已设置为 {power}。")
```

这是一个相当简单的命令。我们进行了一些错误检查，然后设置自己的力量。我们使用 `help_category` 为“mush”，以便使所有命令易于查找并在帮助列表中分开。

保存文件。现在，我们将其添加到一个新的 [CmdSet](../Components/Command-Sets.md) 中，以便可以访问（在完整的角色生成系统中，你当然会在这里有多个命令）。

打开 `mygame/commands/default_cmdsets.py`，在顶部导入你的 `command.py` 模块。我们还为下一步导入默认的 `CmdSet` 类：

```python
from evennia import CmdSet
from commands import command
```

接下来，向下滚动并定义一个新的命令集（基于我们刚才在此文件末尾导入的基本 `CmdSet` 类），仅保存我们的角色生成特定命令：

```python
# end of default_cmdsets.py

class ChargenCmdset(CmdSet):
    """
    这个命令集在角色生成区域使用。
    """
    key = "Chargen"
    def at_cmdset_creation(self):
        "这在初始化时被调用"
        self.add(command.CmdSetPower())
```

将来，你可以将任何数量的命令添加到此命令集中，以扩展你希望的角色生成系统。现在，我们需要将该命令集放在某个地方，以便为用户提供访问权限。我们可以直接将其放在角色上，但这样会使其随时可用。将其放在房间上更清晰，因此当玩家在该房间时，才可用。

### 角色生成区域

我们将创建一个简单的房间类型作为所有角色生成区域的模板。接下来编辑 `mygame/typeclasses/rooms.py`：

```python
from commands.default_cmdsets import ChargenCmdset

# ...
# 在 rooms.py 文件末尾

class ChargenRoom(Room):
    """
    这个房间类用于角色生成房间。它使
    ChargenCmdset 可用。
    """
    def at_object_creation(self):
        "这仅在首次创建时调用"
        self.cmdset.add(ChargenCmdset, persistent=True)
```

注意，使用此类型类创建的新房间将始终在自身上启动 `ChargenCmdset`。不要忘记 `persistent=True` 关键字，否则在服务器重新加载后将丢失命令集。有关 [命令集](../Components/Command-Sets.md) 和 [命令](../Components/Commands.md) 的更多信息，请参见各自的链接。

### 测试角色生成

首先，确保你已经 `@reload` 了服务器（或使用终端中的 `evennia reload`），以将新 Python 代码添加到游戏中。检查你的终端并修复您看到的任何错误——错误回溯会准确列出错误所在——查看您已更改文件的行号。

在没有角色生成区域的情况下，我们无法测试。登录游戏（此时你应该使用新的自定义角色类）。让我们挖掘一个角色生成区域进行测试。

```
@dig chargen:rooms.ChargenRoom = chargen,finish
```

如果您阅读 `@dig` 的帮助，您会发现这将创建一个名为 `chargen` 的新房间。冒号后面的部分是你想要使用的类型类的 Python 路径。由于 Evennia 将自动尝试进入游戏目录的 `typeclasses` 文件夹，因此我们只需指定 `rooms.ChargenRoom`，这意味着它将在 `rooms.py` 模块中查找名为 `ChargenRoom` 的类（这就是我们上面创建的）。在名称后面的 `=` 中给出的名称是从当前地点到房间的出口名称。你还可以为每个名称附加别名，例如 `chargen;角色生成`。

因此，总结一下，这将创建一个 `ChargenRoom` 类型的新房间，并打开一个到它的出口 `chargen` 和一个出口回到这里，名称为 `finish`。如果在此阶段看到错误，你必须修复代码中的错误。`@reload` 在修复之间。请勿继续，直到创建似乎正常工作为止。

```
chargen
```

这应该会将你带到角色生成房间。在那里，你应该现在拥有 `+setpower` 命令，因此测试一下。当你离开（通过 `finish` 出口）时，该命令将消失，尝试 `+setpower` 现在应该会给你一个命令未找到错误。使用 `ex me`（作为特权用户）来检查 `Power` [属性](../Components/Attributes.md) 是否已正确设置。

如果事情不工作，请确保你的类型类和命令没有错误，并确保你输入的各种命令集和命令的路径是正确的。检查日志或命令行，寻找回溯和错误。

## 战斗系统

我们将将我们的战斗命令添加到默认命令集中，这意味着它将始终对所有人可用。战斗系统由 `+attack` 命令组成，以确定我们攻击的成功程度。我们还将更改默认的 `look` 命令，以显示当前战斗分数。

### 使用 +attack 命令进行攻击

在这个简单的系统中，攻击意味着投掷一个受 `power` 属性影响的随机“战斗分数”：

```
> +attack
你 +attack 的战斗分数为 12!
```

返回到 `mygame/commands/command.py`，在文件末尾添加命令，如下所示：

```python
import random

# ...

class CmdAttack(Command):
    """
    发起攻击

    用法：
        +attack

    这将根据你的力量计算新的战斗分数。
    你的战斗分数对同一位置的所有人可见。
    """
    key = "+attack"
    help_category = "mush"

    def func(self):
        "计算 1-10*Power 之间的随机分数"
        caller = self.caller
        power = caller.db.power
        if not power:
            # 如果调用者不是我们的自定义角色类型类，这可能会发生
            power = 1
        combat_score = random.randint(1, 10 * power)
        caller.db.combat_score = combat_score

        # 宣布
        message_template = "{attacker} +attack{s} 的战斗分数为 {c_score}!"
        caller.msg(message_template.format(
            attacker="你",
            s="",
            c_score=combat_score,
        ))
        caller.location.msg_contents(message_template.format(
            attacker=caller.key,
            s="s",
            c_score=combat_score,
        ), exclude=caller)
```

我们在这里做的只是使用 Python 内置的 `random.randint()` 函数生成一个“战斗分数”。然后我们存储这个结果并将其回显给所有在场的人。

要让 `+attack` 命令在游戏中可用，请返回到 `mygame/commands/default_cmdsets.py` 并向下滚动到 `CharacterCmdSet` 类。在适当的位置添加此行：

```python
self.add(command.CmdAttack())
```

`@reload` Evennia，`+attack` 命令应对你可用。运行并使用例如 `@ex` 确保 `combat_score` 属性正确保存。

### 让“look”显示战斗分数

玩家应该能够查看房间中的所有当前战斗分数。我们可以通过简单地添加一个名为 `+combatscores` 的第二个命令来实现，但我们将让默认的 `look` 命令为我们做繁重的工作，并将我们的分数显示为其正常输出的一部分，像这样：

```
> look Tom
Tom（战斗分数：3）
这是一个伟大的战士。
```

然而，我们并不需要实际修改 `look` 命令。要理解原因，请查看默认的 `look` 实际定义。它位于 [evennia/commands/default/general.py](evennia.commands.default.general)。

你会发现，实际返回文本是通过 `look` 命令调用一个名为 `return_appearance` 的 *钩子方法* 实现的。所有 `look` 做的就是回显由此钩子返回的内容。因此，我们需要做的是编辑我们自定义的角色类型类，并重载它的 `return_appearance`，以返回我们想要的内容（这就是拥有自定义类型类的实际好处）。

返回到在 `mygame/typeclasses/characters.py` 中的自定义角色类型类。`return_appearance` 的默认实现位于 [evennia.DefaultCharacter](evennia.objects.objects.DefaultCharacter)。

如果你想进行更大的更改，你可以将整个默认内容复制并粘贴到我们重载的方法中。然而在我们的例子中，更改很小：

```python
class Character(DefaultCharacter):
    """
     [...]
    """
    def at_object_creation(self):
        "这是只在对象首次创建时调用。"
        self.db.power = 1
        self.db.combat_score = 1

    def return_appearance(self, looker):
        """
        来自此方法的返回内容是
        观察者在查看该对象时所看到的。
        """
        text = super().return_appearance(looker)
        cscore = f"（战斗分数：{self.db.combat_score}）"
        if "\n" in text:
            # 文本是多行的，在第一行后添加分数
            first_line, rest = text.split("\n", 1)
            text = first_line + cscore + "\n" + rest
        else:
            # 文本只有一行；将分数添加到末尾
            text += cscore
        return text
```

我们所做的只是让默认的 `return_appearance` 自己的工作（`super` 将调用父类的同一方法）。然后我们将这段文本的第一行分出，附上我们的 `combat_score`，并重新组合在一起。

`@reload` 服务器，你应该能够查看其他角色并看到他们当前的战斗分数。

> 注意：更有用的一种方式是重载整个 `Room` 的 `return_appearance`，并修改它们列出内容的方式；这样一来，人们在查看房间时就可以同时看到所有在场角色的战斗分数。我们将此作为练习留给你。

## NPC 系统

这里我们将通过引入一个可以创建 NPC 对象的命令来重用角色类。我们还应该能够设置其力量并指挥它。

定义 NPC 类有几种方法。理论上，我们可以为其创建一个自定义的类型类，并在所有 NPC 上放置一个特定于 NPC 的自定义命令集。这个命令集可以包含所有操作命令。然而，由于我们期望 NPC 操作在用户群体中会是常见的，因此我们将把所有相关 NPC 命令放在默认命令集中，并通过 [权限和锁](../Components/Permissions.md) 限制最终访问。

### 使用 +createNPC 创建 NPC

我们需要一个用于创建 NPC 的命令，这是一个非常简单的命令：

```
> +createnpc Anna
你创建了 NPC 'Anna'。
```

在 `command.py` 的末尾，创建我们的新命令：

```python
from evennia import create_object

class CmdCreateNPC(Command):
    """
    创建一个新的 NPC

    用法：
        +createNPC <name>

    创建一个新的、命名的 NPC。 NPC 将以 1 的力量开始。
    """
    key = "+createnpc"
    aliases = ["+createNPC"]
    locks = "call:not perm(nonpcs)"
    help_category = "mush"

    def func(self):
        "创建对象并命名"
        caller = self.caller
        if not self.args:
            caller.msg("用法：+createNPC <name>")
            return
        if not caller.location:
            # 不允许在 OOC 时创建 NPC
            caller.msg("你必须有一个位置来创建 NPC。")
            return
        # 姓名始终以大写字母开头
        name = self.args.strip().capitalize()
        # 在调用者的位置创建 NPC
        npc = create_object("characters.Character",
                      key=name,
                      location=caller.location,
                      locks=f"edit:id({caller.id}) and perm(Builders);call:false()")
        # 宣布
        message_template = "{creator} 创建了 NPC '{npc}'。"
        caller.msg(message_template.format(
            creator="你",
            npc=name,
        ))
        caller.location.msg_contents(message_template.format(
            creator=caller.key,
            npc=name,
        ), exclude=caller)
```

在这里，我们定义了 `+createnpc`（`+createNPC` 也可以），其可由*未拥有 `nonpcs` “[权限](../Components/Permissions.md)”* 的每个人调用（在 Evennia 中，“权限”也可以用于阻止访问，这取决于我们定义的锁）。我们在调用者的当前位置创建 NPC 对象，使用我们自定义的 `Character` 类型类来做到这一点。

我们在 NPC 上设置了一个额外的锁条件，我们将在稍后用于检查谁可以编辑 NPC——我们允许创建者这样做，以及任何拥有构建者权限（或更高权限）的人。有关锁系统的更多信息，请参见 [锁](../Components/Locks.md)。

请注意，我们只是向对象提供默认权限（通过不指定 `permissions` 关键字来调用 `create_object()`）。在某些游戏中，人们可能希望给 NPC 赋予与创建它们的角色相同的权限，但这样做可能会有安全风险。

像以前一样将此命令添加到你的默认命令集中。`@reload` 并且它将可以进行测试。

### 使用 +editNPC 编辑 NPC

由于我们重用了自定义角色类型类，新的 NPC 已经有了 *力量* 值—默认值为 1。我们如何更改这个？

我们可以选择几种方法。最简单的办法是记住 `power` 属性仅仅是一个简单的 [属性](../Components/Attributes.md)，存储在 NPC 对象上。因此，作为构建者或管理员，我们可以立即使用默认的 `@set` 命令设置它：

```
@set mynpc/power = 6
```

不过，`@set` 命令过于强大，因此仅限于工作人员。我们将添加一个自定义命令，仅更改我们希望玩家能够更改的内容。原则上，我们可以重新设计旧的 `+setpower` 命令，但让我们尝试一些更有用的东西。我们将创建一个 `+editNPC` 命令。

```
> +editNPC Anna/power = 10
将 Anna 的属性 'power' 设置为 10。
```

这是一个稍微复杂一点的命令。它将放在 `command.py` 文件末尾，如前所述。

```python
class CmdEditNPC(Command):
    """
    编辑现有 NPC

    用法：
      +editnpc <name>[/<属性> [= 值]]

    示例：
      +editnpc mynpc/power = 5
      +editnpc mynpc/power    - 显示力量值
      +editnpc mynpc          - 显示所有可编辑的
                                属性和值

    此命令用于编辑现有 NPC。你必须有
    编辑该 NPC 的权限才能使用此命令。
    """
    key = "+editnpc"
    aliases = ["+editNPC"]
    locks = "cmd:not perm(nonpcs)"
    help_category = "mush"

    def parse(self):
        "我们需要在这里进行一些解析"
        args = self.args
        propname, propval = None, None
        if "=" in args:
            args, propval = [part.strip() for part in args.rsplit("=", 1)]
        if "/" in args:
            args, propname = [part.strip() for part in args.rsplit("/", 1)]
        # 存储，以便在 func() 中可以访问
        self.name = args
        self.propname = propname
        # 只有属性名没有属性值是没有意义的
        self.propval = propval if propname else None

    def func(self):
        "进行编辑"

        allowed_propnames = ("power", "attribute1", "attribute2")

        caller = self.caller
        if not self.args or not self.name:
            caller.msg("用法：+editnpc name[/propname][=propval]")
            return
        npc = caller.search(self.name)
        if not npc:
            return
        if not npc.access(caller, "edit"):
            caller.msg("你无法更改此 NPC。")
            return
        if not self.propname:
            # 这意味着我们只是列出了值
            output = f"{npc.key} 的属性："
            for propname in allowed_propnames:
                propvalue = npc.attributes.get(propname, default="N/A")
                output += f"\n {propname} = {propvalue}"
            caller.msg(output)
        elif self.propname not in allowed_propnames:
            caller.msg("你只能更改 %s。" %
                              ", ".join(allowed_propnames))
        elif self.propval:
            # 为新属性值分配
            # 在此示例中，属性都是整数...
            intpropval = int(self.propval)
            npc.attributes.add(self.propname, intpropval)
            caller.msg("将 %s 的属性 '%s' 设置为 %s" %
                         (npc.key, self.propname, self.propval))
        else:
            # 设置了属性名，但没有属性值 - 显示当前值
            caller.msg("%s 的属性 %s = %s" %
                         (npc.key, self.propname,
                          npc.attributes.get(self.propname, default="N/A")))
```

这个命令示例展示了更高级解析的用法，但其余部分主要是错误检查。它在同一房间中搜索给定的 NPC，并检查调用者是否确实具有“编辑”权限，然后才继续。没有适当权限的帐户将无法查看给定 NPC 的属性。对每个游戏来说，这是否适合如此处理由你决定。

像以前一样将此添加到默认命令集中，你应该能够尝试它。

_注意：如果你希望玩家使用这个命令来更改 NPC 的某个属性名称（即 `key` 属性），你需要修改命令，因为 `key` 不是属性（不能通过 `npc.attributes.get` 检索，而是通过 `npc.key` 直接检索）。我们将这作为可选的练习留给你。_

### 让 NPC 做事 - +npc 命令

最后，我们将创建一个命令来指挥我们的 NPC。目前，我们将将此命令限制为仅可由对 NPC 拥有“编辑”权限的人使用。如果任何人可以使用 NPC，则可以进行更改。

由于 NPC 是从我们的角色类型类中继承的，因此可以访问大多数玩家的命令。它没有权限访问基于会话和玩家的命令集（这意味着，除了聊天时不能在频道上发言，但如果你添加了这些命令，他们也可以做到）。因此，`+npc` 命令很简单：

```
+npc Anna = say Hello!
Anna 说：“你好！”
```

再次将其添加到 `command.py` 模块的末尾：

```python
class CmdNPC(Command):
    """
    控制 NPC

    用法：
        +npc <name> = <命令>

    这使得 NPC 作为其自身执行命令。它将以
    自己的权限和访问执行此操作。
    """
    key = "+npc"
    locks = "call:not perm(nonpcs)"
    help_category = "mush"

    def parse(self):
        "简单地分割 = 符号"
        name, cmdname = None, None
        if "=" in self.args:
            name, cmdname = [part.strip()
                             for part in self.args.rsplit("=", 1)]
        self.name, self.cmdname = name, cmdname

    def func(self):
        "运行命令"
        caller = self.caller
        if not self.cmdname:
            caller.msg("用法：+npc <name> = <command>")
            return
        npc = caller.search(self.name)
        if not npc:
            return
        if not npc.access(caller, "edit"):
            caller.msg("你无法命令此 NPC 做任何事情。")
            return
        # 发送命令
        npc.execute_cmd(self.cmdname)
        caller.msg(f"你告诉 {npc.key} 去做 '{self.cmdname}'。")
```

请注意，如果你给出错误命令，你将不会看到任何错误消息，因为该错误将返回给 NPC 对象，而不是返回给你。如果你希望玩家看到这些内容，可以将调用者的会话 ID 传递给 `execute_cmd` 调用，如下所示：

```python
npc.execute_cmd(self.cmdname, sessid=self.caller.sessid)
```

不过，需要记住的是，这是一种非常简单的控制 NPC 的方法。Evennia 支持完整的操纵。一个帐户（假设“操纵”权限设置正确）可以简单地执行 `@ic mynpc` 并能够“作为”该 NPC 玩游戏。这实际上与帐户控制其正常角色时发生的情况是相同的。

## 总结评论

本教程到此为止。看起来文本很多，但你需要编写的代码实际上相对较短。此时你应该拥有游戏的基本框架，并了解到编写游戏涉及的内容。

从这里开始，你可以构建更多的 ChargenRooms 并将其链接到更大的网格。`+setpower` 命令可以基于或伴随许多其他命令，以获得更复杂的角色生成。

简单的“力量”游戏机制应容易扩展为更成熟和有用的东西，战斗分数原则也是如此。`+attack` 可以通过针对特定玩家（或 NPC）并自动比较他们的相关属性来生成结果。

如需进一步学习，你可以查看 [教程世界](Beginner-Tutorial/Part1/Beginner-Tutorial-Tutorial-World.md)。有关更多具体想法，查看 [其他教程和提示](./Howtos-Overview.md) 以及 [Evennia 组件概述](../Components/Components-Overview.md)。
