# 快速战斗

在本课中，我们将在[上一课](./Beginner-Tutorial-Combat-Base.md)设计的基本战斗框架上构建一个“快速”战斗系统。

```shell
> attack troll 
  You attack the Troll! 

The Troll roars!

You attack the Troll with Sword: Roll vs armor(11):
 rolled 3 on d20 + strength(+1) vs 11 -> Fail
 
Troll attacks you with Terrible claws: Roll vs armor(12): 
 rolled 13 on d20 + strength(+3) vs 12 -> Success
 Troll hits you for 5 damage! 
 
You attack the Troll with Sword: Roll vs armor(11):
 rolled 14 on d20 + strength(+1) vs 11 -> Success
 You hit the Troll for 2 damage!
 
> look 
  A dark cave 
  
  Water is dripping from the ceiling. 
  
  Exits: south and west 
  Enemies: The Troll 
  --------- Combat Status ----------
  You (Wounded)  vs  Troll (Scraped)

> use potion 
  You prepare to use a healing potion! 
  
Troll attacks you with Terrible claws: Roll vs armor(12): 
 rolled 2 on d20 + strength(+3) vs 12 -> Fail
 
You use a healing potion. 
 You heal 4 damage. 
 
Troll attacks you with Terrible claws: Roll vs armor(12): 
 rolled 8 on d20 + strength(+3) vs 12 -> Fail
 
You attack the troll with Sword: Roll vs armor(11):
 rolled 20 on d20 + strength(+1) vs 11 -> Success (critical success)
 You critically hit the Troll for 8 damage! 
 The Troll falls to the ground, dead. 
 
The battle is over. You are still standing. 
```

> 请注意，此文档未显示游戏内颜色。如果您对替代方案感兴趣，请参见[下一课](./Beginner-Tutorial-Combat-Turnbased.md)，我们将在其中制作一个基于菜单的回合制系统。

“快速”战斗指的是一种没有明确的“回合”划分的战斗系统（与[回合制战斗](./Beginner-Tutorial-Combat-Turnbased.md)相对）。它受到了旧[DikuMUD](https://en.wikipedia.org/wiki/DikuMUD)代码库中战斗方式的启发，但更加灵活。

```{sidebar} 与DIKU战斗的区别
在DIKU中，战斗中的所有动作都发生在一个_全局_的“滴答”上，例如3秒。在我们的系统中，每个战斗者都有自己的“滴答”，彼此完全独立。现在，在Evadventure中，每个战斗者将以相同的速度滴答，因此模仿DIKU……但他们不必这样做。
```

基本上，用户输入一个动作，经过一段时间后，该动作将被执行（通常是攻击）。如果他们不做任何事情，攻击将一遍又一遍地重复（结果随机）直到敌人或你被击败。

你可以通过执行其他动作（如喝药水或施法）来改变策略。你也可以简单地移动到另一个房间以“逃离”战斗（但敌人当然可能会跟随你）。

## 一般原则

```{sidebar}
在`evennia/contrib/tutorials`中可以找到实现的快速战斗系统示例，在[evadventure/combat_twitch.py](evennia.contrib.tutorials.evadventure.combat_twitch)。
```

以下是基于Twitch的战斗处理器的一般设计：

- 快速版本的CombatHandler将在战斗开始时存储在每个战斗者上。当战斗结束或他们离开战斗所在的房间时，处理器将被删除。
- 处理器将独立排队每个动作，启动计时器直到它们触发。
- 所有输入都通过Evennia [Commands](../../../Components/Commands.md)处理。

## 快速战斗处理器

> 创建一个新模块`evadventure/combat_twitch.py`。

我们将利用之前创建的_战斗动作_、_动作字典_和父类`EvAdventureCombatBaseHandler`。

```python
# 在 evadventure/combat_twitch.py 中

from .combat_base import (
   CombatActionAttack,
   CombatActionHold,
   CombatActionStunt,
   CombatActionUseItem,
   CombatActionWield,
   EvAdventureCombatBaseHandler,
)

from .combat_base import EvAdventureCombatBaseHandler

class EvAdventureCombatTwitchHandler(EvAdventureCombatBaseHandler):
    """
    当战斗开始时，这将在战斗者上创建。它仅跟踪战斗者的战斗方面，并处理下一个动作何时发生。
    """
 
    def msg(self, message, broadcast=True):
        """参见EvAdventureCombatBaseHandler.msg"""
        super().msg(message, combatant=self.obj, 
                    broadcast=broadcast, location=self.obj.location)
```

我们为我们的快速战斗创建了`EvAdventureCombatBaseHandler`的子类。父类是一个[脚本](../../../Components/Scripts.md)，当脚本“坐在”对象上时，该对象可以在脚本上通过`self.obj`访问。由于此处理器旨在“坐在”战斗者上，因此`self.obj`就是战斗者，`self.obj.location`是战斗者所在的当前房间。通过使用`super()`，我们可以重用父类的`msg()`方法，并添加这些快速特定的细节。

### 获取战斗双方

```python
# 在 evadventure/combat_twitch.py 中

from evennia.utils import inherits_from

# ...

class EvAdventureCombatTwitchHandler(EvAdventureCombatBaseHandler):

    # ...

    def get_sides(self, combatant):
         """
         从提供的战斗者的角度获取此战斗的两个“方面”的列表。双方不需要平衡。
 
         Args:
             combatant (Character or NPC): 作为方面基础的战斗者。
             
         Returns:
             tuple: 从`combatant`的角度返回一个列表元组`(allies, enemies)`。请注意，战斗者本身不包含在其中任何一个中。

        """
        # 通过查找他们的combathandlers获取参与战斗的所有实体
        combatants = [
            comb
            for comb in self.obj.location.contents
            if hasattr(comb, "scripts") and comb.scripts.has(self.key)
        ]
        location = self.obj.location

        if hasattr(location, "allow_pvp") and location.allow_pvp:
            # 在pvp中，其他所有人都是敌人
            allies = [combatant]
            enemies = [comb for comb in combatants if comb != combatant]
        else:
            # 否则，敌人/盟友取决于战斗者是谁
            pcs = [comb for comb in combatants if inherits_from(comb, EvAdventureCharacter)]
            npcs = [comb for comb in combatants if comb not in pcs]
            if combatant in pcs:
                # 战斗者是PC，因此NPC都是敌人
                allies = pcs
                enemies = npcs
            else:
                # 战斗者是NPC，因此PC都是敌人
                allies = npcs
                enemies = pcs
        return allies, enemies
```

接下来，我们添加我们自己的`get_sides()`方法实现。这从提供的`combatant`的角度展示了战斗双方。在快速战斗中，有一些事情可以识别战斗者：

- 他们在同一个位置
- 他们每个人都有一个`EvAdventureCombatTwitchHandler`脚本在自己身上运行

```{sidebar} inherits_from
由于`inherits_from`在你的类从父类继承时_任何_距离都为True，因此如果你将NPC类更改为也继承自我们的Character类，则此特定检查将不起作用。在这种情况下，我们必须想出其他方法来比较这两种实体类型。
```

在PvP开放房间中，每个人都是敌人。否则，我们通过查看他们是否继承自`EvAdventureCharacter`（我们的PC类）来区分PC和NPC——如果你是PC，那么NPC是你的敌人，反之亦然。[inherits_from](evennia.utils.utils.inherits_from)对于进行这些检查非常有用——即使你从`EvAdventureCharacter`继承_任何_距离，它也会通过。

请注意，`allies`不包括`combatant`本身，因此如果你正在与一个孤独的敌人战斗，此方法的返回值将是`([], [enemy_obj])`。

### 跟踪优势/劣势

```python
# 在 evadventure/combat_twitch.py 中

from evennia import AttributeProperty

# ...

class EvAdventureCombatTwitchHandler(EvAdventureCombatBaseHandler):

    self.advantage_against = AttributeProperty(dict) 
    self.disadvantage_against = AttributeProperty(dict)

    # ...

    def give_advantage(self, recipient, target):
        """让接收者对目标获得优势。"""
        self.advantage_against[target] = True

    def give_disadvantage(self, recipient, target):
        """让受影响的一方对目标获得劣势。"""
        self.disadvantage_against[target] = True

    def has_advantage(self, combatant, target):
        """检查战斗者是否对目标有优势。"""
        return self.advantage_against.get(target, False)

    def has_disadvantage(self, combatant, target):
        """检查战斗者是否对目标有劣势。"""
        return self.disadvantage_against.get(target, False)
```

如上一课所示，动作调用这些方法来存储给定战斗者具有优势的事实。

在这种快速战斗情况下，获得优势的一方始终是定义了combathandler的一方，因此我们实际上不需要使用`recipient/combatant`参数（它始终是`self.obj`）——只有`target`是重要的。

我们创建了两个新的属性来将关系存储为字典。

### 排队动作

```{code-block} python
:linenos:
:emphasize-lines: 17,26,30,43,44, 48, 49
# 在 evadventure/combat_twitch.py 中

from evennia.utils import repeat, unrepeat
from .combat_base import (
    CombatActionAttack,
    CombatActionHold,
    CombatActionStunt,
    CombatActionUseItem,
    CombatActionWield,
    EvAdventureCombatBaseHandler,
)

# ...

class EvAdventureCombatTwitchHandler(EvAdventureCombatBaseHandler):

    action_classes = {
         "hold": CombatActionHold,
         "attack": CombatActionAttack,
         "stunt": CombatActionStunt,
         "use": CombatActionUseItem,
         "wield": CombatActionWield,
     }

    action_dict = AttributeProperty(dict, autocreate=False)
    current_ticker_ref = AttributeProperty(None, autocreate=False)

    # ...

    def queue_action(self, action_dict, combatant=None):
        """
        安排下一个动作的触发时间。

        Args:
            action_dict (dict): 要初始化的新动作字典。
            combatant (optional): 未使用。

        """
        if action_dict["key"] not in self.action_classes:
            self.obj.msg("这是一个未知的动作！")
            return

        # 存储动作字典并安排其在dt时间内运行
        self.action_dict = action_dict
        dt = action_dict.get("dt", 0)

        if self.current_ticker_ref:
            # 我们已经有一个当前的ticker在运行 - 终止它
            unrepeat(self.current_ticker_ref)
        if dt <= 0:
            # 无重复
            self.current_ticker_ref = None
        else:
            # 始终安排任务重复，稍后取消
            # 否则。我们存储tickerhandler的引用以确保
            # 我们可以稍后删除它
            self.current_ticker_ref = repeat(
                dt, self.execute_next_action, id_string="combat")

```

- **第30行**：`queue_action`方法接受一个“动作字典”，表示战斗者接下来要执行的动作。它必须是`action_classes`属性中添加到处理器中的键动作之一（**第17行**）。我们不使用`combatant`关键字参数，因为我们已经知道战斗者是`self.obj`。
- **第43行**：我们只需将给定的动作字典存储在处理器上的`action_dict`属性中。简单而有效！
- **第44行**：当你输入例如`attack`时，你期望在这种类型的战斗中，即使你没有输入任何其他内容，也会看到`attack`命令自动重复。为此，我们在动作字典中查找一个新键，指示此动作应以某个速率（以秒为单位的`dt`）_重复_。我们通过简单地假设它为零来使其与所有动作字典兼容。

 [evennia.utils.utils.repeat](evennia.utils.utils.repeat)和[evennia.utils.utils.unrepeat](evennia.utils.utils.unrepeat)是[TickerHandler](../../../Components/TickerHandler.md)的便捷快捷方式。你告诉`repeat`以某个速率调用给定的方法/函数。你得到的回是一个引用，以便你可以稍后使用它来“取消重复”（停止重复）。我们确保将此引用存储在`current_ticket_ref`属性中（**第26行**）。

- **第48行**：每当我们排队一个新动作（它可能会替换现有的动作）时，我们必须确保终止（取消重复）任何正在进行的旧重复。否则，我们会得到旧动作一遍又一遍地触发，并且新动作与它们一起启动。
- **第49行**：如果设置了`dt`，我们调用`repeat`以在给定速率下设置新的重复动作。我们存储此新引用。经过`dt`秒后，`.execute_next_action`方法将触发（我们将在下一节中创建它）。

### 执行动作

```{code-block} python
:linenos:
:emphasize-lines: 5,15,16,18,22,27

# 在 evadventure/combat_twitch.py 中

class EvAdventureCombatTwitchHandler(EvAdventureCombatBaseHandler):

    fallback_action_dict = AttributeProperty({"key": "hold", "dt": 0})

    # ...

    def execute_next_action(self):
            """
            由命令在延迟后触发
            """
            combatant = self.obj
            action_dict = self.action_dict
            action_class = self.action_classes[action_dict["key"]]
            action = action_class(self, combatant, action_dict)
    
            if action.can_use():
                action.execute()
                action.post_execute()
    
            if not action_dict.get("repeat", True):
                # 不是重复动作，使用后备动作（通常是原始攻击）
                self.action_dict = self.fallback_action_dict
                self.queue_action(self.fallback_action_dict)
    
            self.check_stop_combat()
```

这是在`queue_action`中的`dt`秒后调用的方法。

- **第5行**：我们定义了一个“后备动作”。这在一次性动作（不应重复的动作）完成后使用。
- **第15行**：我们从`action-dict`中获取`'key'`，并使用`action_classes`映射获取动作类（例如，我们在[这里](./Beginner-Tutorial-Combat-Base.md#attack-action)定义的`ActionAttack`）。
- **第16行**：在这里，我们使用实际的当前数据初始化动作类——战斗者和`action_dict`。这会调用类上的`__init__`方法，并使动作准备好使用。
```{sidebar} 新动作字典键
总结一下，对于快速战斗使用，我们现在在动作字典中引入了两个新键：
- `dt`：从排队动作到触发动作的等待时间（以秒为单位）。
- `repeat`：布尔值，确定动作在触发后是否应自动排队。
```
- **第18行**：在这里，我们运行动作的使用方法——在这里执行动作。我们让动作本身处理所有逻辑。
- **第22行**：我们检查动作字典上的另一个可选标志：`repeat`。除非设置，否则我们使用**第5行**中定义的后备动作。许多动作不应重复——例如，一遍又一遍地执行`wield`同一武器是没有意义的。
- **第27行**：重要的是我们知道如何停止战斗。我们将在接下来编写此方法。

### 检查和停止战斗

```{code-block} python
:linenos:
:emphasize-lines: 12,18,19

# 在 evadventure/combat_twitch.py 中

class EvAdventureCombatTwitchHandler(EvAdventureCombatBaseHandler):

    # ...

    def check_stop_combat(self):
        """
        检查战斗是否结束。
        """

        allies, enemies = self.get_sides(self.obj)

        location = self.obj.location

        # 只保留仍然活着且仍在同一房间的战斗者
        allies = [comb for comb in allies if comb.hp > 0 and comb.location == location]
        enemies = [comb for comb in enemies if comb.hp > 0 and comb.location == location]

        if not allies and not enemies:
            self.msg("战斗结束。没有人站着。", broadcast=False)
            self.stop_combat()
            return
        if not allies:
            self.msg("战斗结束。你输了。", broadcast=False)
            self.stop_combat()
        if not enemies:
            self.msg("战斗结束。你赢了！", broadcast=False)
            self.stop_combat()

    def stop_combat(self):
        pass  # 我们将最后完成这个
```

我们必须确保检查战斗是否结束。

- **第12行**：使用我们的`.get_sides()`方法，我们可以轻松获取冲突的双方。
- **第18, 19行**：我们获取仍然活着且仍在同一房间的所有人。后一个条件在我们从战斗中移动走时很重要——你不能从另一个房间击中敌人。

在`stop_method`中，我们需要进行一堆清理。在我们编写命令之前，我们将暂时不实现这一点。继续阅读。

## 命令

我们希望每个动作都映射到一个[命令](../../../Components/Commands.md)——玩家可以传递给游戏的实际输入。

### 基础战斗类

我们应该尝试找到我们需要的命令之间的相似之处，并将它们分组到一个父类中。当命令触发时，它将在自身上按顺序触发以下方法：

1. `cmd.at_pre_command()`
2. `cmd.parse()`
3. `cmd.func()`
4. `cmd.at_post_command()`

我们将为我们的父类重写前两个。

```{code-block} python
:linenos:
:emphasize-lines: 23,49

# 在 evadventure/combat_twitch.py 中

from evennia import Command
from evennia import InterruptCommand

# ...

# 在战斗处理器类之后

class _BaseTwitchCombatCommand(Command):
    """
    所有快速战斗命令的父类。

    """

    def at_pre_command(self):
        """
        在解析之前调用。

        """
        if not self.caller.location or not self.caller.location.allow_combat:
            self.msg("这里不能战斗！")
            raise InterruptCommand()

    def parse(self):
        """
        处理大多数支持的战斗语法的解析（除了特技）。

        <action> [<target>|<item>]
        或
        <action> <item> [on] <target>

        使用“on”来区分名称/物品名称中是否有空格。

        """
        self.args = args = self.args.strip()
        self.lhs, self.rhs = "", ""

        if not args:
            return

        if " on " in args:
            lhs, rhs = args.split(" on ", 1)
        else:
            lhs, *rhs = args.split(None, 1)
            rhs = " ".join(rhs)
        self.lhs, self.rhs = lhs.strip(), rhs.strip()

    def get_or_create_combathandler(self, target=None, combathandler_name="combathandler"):
        """
        获取或创建分配给此战斗者的combathandler。

        """
        if target:
            # 添加/检查目标的combathandler
            if target.hp_max is None:
                self.msg("你不能攻击那个！")
                raise InterruptCommand()

            EvAdventureCombatTwitchHandler.get_or_create_combathandler(target)
        return EvAdventureCombatTwitchHandler.get_or_create_combathandler(self.caller)
```

- **第23行**：如果当前位置不允许战斗，所有战斗命令应立即退出。要在命令到达`.func()`之前停止命令，我们必须引发`InterruptCommand()`。
- **第49行**：为获取命令处理器添加一个助手方法很方便，因为我们所有的命令都将使用它。它反过来调用我们从`EvAdventureCombatTwitchHandler`的父类继承的类方法`get_or_create_combathandler`。

### 战斗中的查看命令

```python
# 在 evadventure/combat_twitch.py 中

from evennia import default_cmds
from evennia.utils import pad

# ...

class CmdLook(default_cmds.CmdLook, _BaseTwitchCombatCommand):
    def func(self):
        # 获取常规查看，然后是战斗摘要
        super().func()
        if not self.args:
            combathandler = self.get_or_create_combathandler()
            txt = str(combathandler.get_combat_summary(self.caller))
            maxwidth = max(display_len(line) for line in txt.strip().split("\n"))
            self.msg(f"|r{pad(' Combat Status ', width=maxwidth, fillchar='-')}|n\n{txt}")
```

在战斗中，我们希望能够执行`look`并获得正常的查看，但在末尾附加额外的`combat summary`（形式为`Me (Hurt) vs Troll (Perfect)`）。

最后一行使用Evennia的`utils.pad`函数在两侧用线条包围文本"Combat Status"。

结果将是查看命令输出，紧接着是

```shell
--------- Combat Status ----------
You (Wounded)  vs  Troll (Scraped)
```

### 保持命令

```python
class CmdHold(_BaseTwitchCombatCommand):
    """
    保持住你的攻击，不做任何事情。

    用法：
        hold

    """

    key = "hold"

    def func(self):
        combathandler = self.get_or_create_combathandler()
        combathandler.queue_action({"key": "hold"})
        combathandler.msg("$You() $conj(hold) back, doing nothing.", self.caller)
```

“什么都不做”命令展示了所有后续命令的基本原理：

1. 获取combathandler（如果已经存在，将被创建或加载）。
2. 通过将其动作字典传递给`combathandler.queue_action`方法来排队动作。
3. 确认给调用者他们现在排队了这个动作。

### 攻击命令

```python
# 在 evadventure/combat_twitch.py 中

# ...

class CmdAttack(_BaseTwitchCombatCommand):
    """
    攻击目标。将继续攻击目标直到战斗结束或采取其他战斗动作。

    用法：
        attack/hit <target>

    """

    key = "attack"
    aliases = ["hit"]
    help_category = "combat"

    def func(self):
        target = self.caller.search(self.lhs)
        if not target:
            return

        combathandler = self.get_or_create_combathandler(target)
        combathandler.queue_action(
            {"key": "attack", 
             "target": target, 
             "dt": 3, 
             "repeat": True}
        )
        combathandler.msg(f"$You() $conj(attack) $You({target.key})!", self.caller)
```

`attack`命令变得相当简单，因为我们在combathandler和`ActionAttack`类中完成了所有繁重的工作。请注意，我们在这里将`dt`设置为固定的`3`，但在更复杂的系统中，可以想象你的技能、武器和环境会影响你的攻击需要多长时间。

```python
# 在 evadventure/combat_twitch.py 中

from .enums import ABILITY_REVERSE_MAP

# ...

class CmdStunt(_BaseTwitchCombatCommand):
    """
    执行战斗特技，增强盟友对目标的优势，或阻止敌人，使他们对盟友产生劣势。

    用法：
        boost [ability] <recipient> <target>
        foil [ability] <recipient> <target>
        boost [ability] <target>       (same as boost me <target>)
        foil [ability] <target>        (same as foil <target> me)

    Example:
        boost STR me Goblin
        boost DEX Goblin
        foil STR Goblin me
        foil INT Goblin
        boost INT Wizard Goblin

    """

    key = "stunt"
    aliases = (
        "boost",
        "foil",
    )
    help_category = "combat"

    def parse(self):
        args = self.args

        if not args or " " not in args:
            self.msg("Usage: <ability> <recipient> <target>")
            raise InterruptCommand()

        advantage = self.cmdname != "foil"

        # 从输入中提取数据

        stunt_type, recipient, target = None, None, None

        stunt_type, *args = args.split(None, 1)
        if stunt_type:
            stunt_type = stunt_type.strip().lower()

        args = args[0] if args else ""

        recipient, *args = args.split(None, 1)
        target = args[0] if args else None

        # 验证输入并尝试猜测如果没有给出

        # ability是必需的
        if not stunt_type or stunt_type not in ABILITY_REVERSE_MAP:
            self.msg(
                f"'{stunt_type}' is not a valid ability. Pick one of"
                f" {', '.join(ABILITY_REVERSE_MAP.keys())}."
            )
            raise InterruptCommand()

        if not recipient:
            self.msg("Must give at least a recipient or target.")
            raise InterruptCommand()

        if not target:
            # 类似于`boost str target`
            target = recipient if advantage else "me"
            recipient = "me" if advantage else recipient
        # 如果我们此时仍然有None，我们无法继续
        if None in (stunt_type, recipient, target):
            self.msg("Both ability, recipient and  target of stunt must be given.")
            raise InterruptCommand()

        # 保存我们找到的内容，以便可以从func()中访问
        self.advantage = advantage
        self.stunt_type = ABILITY_REVERSE_MAP[stunt_type]
        self.recipient = recipient.strip()
        self.target = target.strip()

    def func(self):
        target = self.caller.search(self.target)
        if not target:
            return
        recipient = self.caller.search(self.recipient)
        if not recipient:
            return

        combathandler = self.get_or_create_combathandler(target)

        combathandler.queue_action(
            {
                "key": "stunt",
                "recipient": recipient,
                "target": target,
                "advantage": self.advantage,
                "stunt_type": self.stunt_type,
                "defense_type": self.stunt_type,
                "dt": 3,
            },
        )
        combathandler.msg("$You() prepare a stunt!", self.caller)
```

这看起来更长，但这只是因为特技命令应该理解许多不同的输入结构，具体取决于你是试图创造优势还是劣势，以及盟友或敌人是否应该接收特技效果。

请注意，`enums.ABILITY_REVERSE_MAP`（在[实用工具课程](./Beginner-Tutorial-Utilities.md)中创建）对于将你的输入'`str`'转换为动作字典所需的`Ability.STR`非常有用。

一旦我们理清了字符串解析，`func`就很简单——我们找到目标和接收者，并使用它们构建需要排队的动作字典。

### 使用物品

```python
# 在 evadventure/combat_twitch.py 中

# ...

class CmdUseItem(_BaseTwitchCombatCommand):
    """
    在战斗中使用物品。物品必须在你的库存中才能使用。

    用法：
        use <item>
        use <item> [on] <target>

    Examples:
        use potion
        use throwing knife on goblin
        use bomb goblin

    """

    key = "use"
    help_category = "combat"

    def parse(self):
        super().parse()

        if not self.args:
            self.msg("你想使用什么？")
            raise InterruptCommand()

        self.item = self.lhs
        self.target = self.rhs or "me"

    def func(self):
        item = self.caller.search(
            self.item,
            candidates=self.caller.equipment.get_usable_objects_from_backpack()
        )
        if not item:
            self.msg("(你必须携带物品才能使用。)")
            return
        if self.target:
            target = self.caller.search(self.target)
            if not target:
                return

        combathandler = self.get_or_create_combathandler(self.target)
        combathandler.queue_action(
            {"key": "use", 
             "item": item, 
             "target": target, 
             "dt": 3}
        )
        combathandler.msg(
            f"$You() prepare to use {item.get_display_name(self.caller)}!", self.caller
        )
```

要使用物品，我们需要确保我们携带它。幸运的是，我们在[装备课程](./Beginner-Tutorial-Equipment.md)中的工作为我们提供了可以用来搜索合适对象的简单方法。

### 装备新武器和装备

```python
# 在 evadventure/combat_twitch.py 中

# ...

class CmdWield(_BaseTwitchCombatCommand):
    """
    装备武器或法术符文。你将装备物品，交换你之前装备的任何其他物品。

    用法：
      wield <weapon or spell>

    Examples:
      wield sword
      wield shield
      wield fireball

    请注意，装备盾牌不会替换你手中的剑，而装备双手武器（或法术符文）将占用两只手并交换你携带的物品。

    """

    key = "wield"
    help_category = "combat"

    def parse(self):
        if not self.args:
            self.msg("你想装备什么？")
            raise InterruptCommand()
        super().parse()

    def func(self):
        item = self.caller.search(
            self.args, candidates=self.caller.equipment.get_wieldable_objects_from_backpack()
        )
        if not item:
            self.msg("(你必须携带物品才能装备。)")
            return
        combathandler = self.get_or_create_combathandler()
        combathandler.queue_action({"key": "wield", "item": item, "dt": 3})
        combathandler.msg(f"$You() reach for {item.get_display_name(self.caller)}!", self.caller)
```

装备命令遵循与其他命令相同的模式。

## 将命令分组以供使用

要使这些命令可用，我们必须将它们添加到[命令集](../../../Components/Command-Sets.md)。

```python
# 在 evadventure/combat_twitch.py 中

from evennia import CmdSet

# ...

# 在命令之后

class TwitchCombatCmdSet(CmdSet):
    """
    添加到角色，以便能够以快速风格攻击其他人。
    """

    def at_cmdset_creation(self):
        self.add(CmdAttack())
        self.add(CmdHold())
        self.add(CmdStunt())
        self.add(CmdUseItem())
        self.add(CmdWield())


class TwitchLookCmdSet(CmdSet):
    """
    这将在战斗中动态添加/移除。
    """

    def at_cmdset_creation(self):
        self.add(CmdLook())
```

第一个cmdset，`TwitchCombatCmdSet`旨在添加到角色中。我们可以通过将cmdset添加到默认角色cmdset中来永久执行此操作（如[初学者命令课程](../Part1/Beginner-Tutorial-Adding-Commands.md)中所述）。在下面的测试部分中，我们将以另一种方式进行。

那`TwitchLookCmdSet`呢？我们不能将其永久添加到角色中，因为我们只希望在战斗中操作此特定版本的`look`。

我们必须确保在战斗开始和结束时添加和清理它。

### 战斗启动和清理

```{code-block} python
:linenos:
:emphasize-lines: 9,13,14,15,16

# 在 evadventure/combat_twitch.py 中

# ...

class EvAdventureCombatTwitchHandler(EvAdventureCombatBaseHandler):

    # ...

    def at_init(self): 
        self.obj.cmdset.add(TwitchLookCmdSet, persistent=False)

    def stop_combat(self): 
        self.queue_action({"key": "hold", "dt": 0})  # 确保ticker被终止
        del self.obj.ndb.combathandler
        self.obj.cmdset.remove(TwitchLookCmdSet)
        self.delete()
```

现在我们有了查看命令集，我们可以完成快速战斗处理器。

- **第9行**：`at_init`方法是所有类型化实体（包括`Scripts`，这就是我们的战斗处理器）的标准Evennia方法。与`at_object_creation`（仅在对象首次创建时触发）不同，`at_init`将在每次对象加载到内存中时调用（通常在你执行服务器`reload`之后）。所以我们在这里添加`TwitchLookCmdSet`。我们这样做是非持久性的，因为我们不希望每次重新加载时都会添加越来越多的cmdsets。
- **第13行**：通过排队一个`dt`为`0`的保持动作，我们确保终止正在进行的`repeat`动作。如果不这样做，它仍然会在稍后触发——并发现战斗处理器已消失。
- **第14行**：如果查看我们定义的`get_or_create_combathandler`类方法（我们在战斗中使用它来获取/创建combathandler），你会看到它将处理器缓存为对象上的`.ndb.combathandler`。所以我们在这里删除那个缓存的引用以确保它消失。
- **第15行**：我们从自己身上移除查看cmdset（记住`self.obj`是你，现在刚刚完成战斗的战斗者）。
- **第16行**：我们删除战斗处理器本身。

## 单元测试

```{sidebar}
有关单元测试的示例，请参见`evennia/contrib/tutorials`中的[evadventure/tests/test_combat.py](evennia.contrib.tutorials.evadventure.tests.test_combat)，这是一个完整的战斗测试套件的示例。
```

> 创建`evadventure/tests/test_combat.py`（如果尚未创建）。

快速命令处理器和命令都可以并且应该进行单元测试。通过Evennia的特殊`EvenniaCommandTestMixin`类，命令测试变得更加容易。这使得`.call`方法可用，并且可以轻松检查命令是否返回你期望的结果。

这是一个示例：

```python
# 在 evadventure/tests/test_combat.py 中

from unittest.mock import Mock, patch
from evennia.utils.test_resources import EvenniaCommandTestMixin

from .. import combat_twitch

# ...

class TestEvAdventureTwitchCombat(EvenniaCommandTestMixin)

    def setUp(self): 
        self.combathandler = (
                combat_twitch.EvAdventureCombatTwitchHandler.get_or_create_combathandler(
            self.char1, key="combathandler") 
        )
   
    @patch("evadventure.combat_twitch.unrepeat", new=Mock())
    @patch("evadventure.combat_twitch.repeat", new=Mock())
    def test_hold_command(self): 
        self.call(combat_twitch, CmdHold(), "", "You hold back, doing nothing")
        self.assertEqual(self.combathandler.action_dict, {"key": "hold"})
```

`EvenniaCommandTestMixin`有一些默认对象，包括我们在这里使用的`self.char1`。

两个`@patch`行是Python [装饰器](https://realpython.com/primer-on-python-decorators/)，用于“补丁”`test_hold_command`方法。它们的作用基本上是说“在下面的方法中，每当任何代码尝试访问`evadventure.combat_twitch.un/repeat`时，只需返回一个Mock对象即可”。

我们这样做是为了在单元测试中避免创建计时器——这些计时器将在测试完成后完成（包括删除其对象），因此会失败。

在测试中，我们使用`self.call()`方法显式触发命令（没有参数）并检查输出是否符合我们的预期。最后，我们检查combathandler是否正确设置，是否在其自身上存储了动作字典。

## 小型战斗测试

```{sidebar}
你可以在`evennia/contrib/tutorials/evadventure`中找到示例批处理命令脚本，在[batchscripts/twitch_combat_demo.ev](github:evennia/contrib/tutorials/evadventure/batchscripts/twitch_combat_demo.ev)中
```

显示代码的各个部分可以正常工作（单元测试）不足以确保你的战斗系统实际工作。我们需要测试所有部分_一起_。这通常称为_功能测试_。虽然功能测试也可以自动化，但能够实际看到我们的代码在运行不是很有趣吗？

这是我们进行最小测试所需的：

- 一个启用战斗的房间。
- 一个可以攻击的NPC（它还不会做任何反击，因为我们还没有添加任何AI）
- 一把我们可以`wield`的武器
- 我们可以`use`的物品（如药水）。

虽然你可以在游戏中手动创建这些，但创建一个[批处理命令脚本](../../../Components/Batch-Command-Processor.md)来设置你的测试环境可能很方便。

> 创建一个新的子文件夹`evadventure/batchscripts/`（如果尚未存在）

> 创建一个新文件`evadventure/combat_demo.ev`（注意，是`.ev`而不是`.py`！）

批处理命令文件是一个包含正常游戏内命令的文本文件，每行一个，命令行之间用以`#`开头的行分隔（这些在所有命令行之间是必需的）。它看起来是这样的：

```
# Evadventure combat demo 

# start from limbo

tel #2

# turn ourselves into a evadventure-character

type self = evadventure.characters.EvAdventureCharacter

# assign us the twitch combat cmdset (requires superuser/developer perms)

py self.cmdset.add("evadventure.combat_twitch.TwitchCombatCmdSet", persistent=True)

# Create a weapon in our inventory (using all defaults)

create sword:evadventure.objects.EvAdventureWeapon

# create a consumable to use

create potion:evadventure.objects.EvAdventureConsumable

# dig a combat arena

dig arena:evadventure.rooms.EvAdventureRoom = arena,back

# go to arena

arena

# allow combat in this room

set here/allow_combat = True

# create a dummy enemy to hit on

create/drop dummy puppet;dummy:evadventure.npcs.EvAdventureNPC

# describe the dummy

desc dummy = This is is an ugly training dummy made out of hay and wood.

# make the dummy crazy tough

set dummy/hp_max = 1000

# 

set dummy/hp = 1000
```

使用开发者/超级用户帐户登录游戏并运行

    > batchcmd evadventure.batchscripts.twitch_combat_demo 
    
这应该将你放置在竞技场中，那里有假人（如果没有，请检查输出中的错误！使用`objects`和`delete`命令列出和删除对象，如果需要重新开始。）

你现在可以尝试`attack dummy`，应该能够对假人进行攻击（降低其健康以测试摧毁它）。使用`back`来“逃离”战斗。

## 结论

这是一节大课！即使我们的战斗系统并不复杂，但仍有许多活动部件需要注意。

此外，虽然相对简单，但此系统也有很大的发展空间。你可以轻松地从中扩展或将其用作自己游戏的灵感。

接下来，我们将尝试在回合制框架内实现相同的目标！
