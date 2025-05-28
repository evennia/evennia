# 回合制战斗

在本课中，我们将基于[战斗基础](./Beginner-Tutorial-Combat-Base.md)实现一个回合制战斗系统，在这个系统中，你可以在菜单中选择你的动作，如下所示：

```shell
> attack Troll
______________________________________________________________________________

 You (Perfect)  vs  Troll (Perfect)
 Your queued action: [attack] (22s until next round,
 or until all combatants have chosen their next action).
______________________________________________________________________________

 1: attack an enemy
 2: Stunt - gain a later advantage against a target
 3: Stunt - give an enemy disadvantage against yourself or an ally
 4: Use an item on yourself or an ally
 5: Use an item on an enemy
 6: Wield/swap with an item from inventory
 7: flee!
 8: hold, doing nothing

> 4
_______________________________________________________________________________

Select the item
_______________________________________________________________________________

 1: Potion of Strength
 2. Potion of Dexterity
 3. Green Apple
 4. Throwing Daggers
 back
 abort

> 1
_______________________________________________________________________________

Choose an ally to target.
_______________________________________________________________________________

 1: Yourself
 back
 abort

> 1
_______________________________________________________________________________

 You (Perfect)  vs Troll (Perfect)
 Your queued action: [use] (6s until next round,
 or until all combatants have chosen their next action).
_______________________________________________________________________________

 1: attack an enemy
 2: Stunt - gain a later advantage against a target
 3: Stunt - give an enemy disadvantage against yourself or an ally
 4: Use an item on yourself or an ally
 5: Use an item on an enemy
 6: Wield/swap with an item from inventory
 7: flee!
 8: hold, doing nothing

Troll attacks You with Claws: Roll vs armor (12):
 rolled 4 on d20 + strength(+3) vs 12 -> Fail
 Troll missed you.

You use Potion of Strength.
 Renewed strength coarses through your body!
 Potion of Strength was used up.
```

> 请注意，此文档未显示游戏内颜色。此外，如果您对替代方案感兴趣，请参见[上一课](./Beginner-Tutorial-Combat-Twitch.md)，我们在其中实现了基于输入每个动作的直接命令的“twitch”式战斗系统。

“回合制”战斗意味着战斗以较慢的速度“滴答”进行，足够慢以允许参与者在菜单中选择他们的选项（菜单并不是严格必要的，但它也是学习如何制作菜单的好方法）。他们的动作将被排队，并将在回合计时器结束时执行。为了避免不必要的等待，当每个人都做出选择时，我们也将进入下一轮。

回合制系统的优点是它消除了玩家速度的影响；你的战斗能力不取决于你输入命令的速度。在RPG重度游戏中，你还可以允许玩家在战斗回合中进行RP表情，以丰富动作。

使用菜单的优点是你可以直接获得所有可能的动作，这使得它对初学者友好，并且易于知道你可以做什么。对于某些玩家来说，这也意味着写作要少得多，这可能是一个优势。

## 一般原则

```{sidebar}
在`evennia/contrib/tutorials/evadventure/`下可以找到实现的回合制战斗系统示例，在[combat_turnbased.py](evennia.contrib.tutorials.evadventure.combat_turnbased)。
```

以下是回合制战斗处理器的一般原则：

- 回合制版本的CombatHandler将存储在_当前位置_。这意味着每个位置只有一个战斗。其他任何人开始战斗都会加入同一个处理器并被分配到一方进行战斗。
- 处理器将运行一个30秒的中央计时器（在此示例中）。当它触发时，所有排队的动作将被执行。如果每个人都提交了他们的动作，那么当最后一个人提交时，这将立即发生。
- 在战斗中你将无法四处走动——你被困在房间里。逃离战斗是一个需要几回合才能完成的单独动作（我们需要创建这个）。
- 通过`attack <target>`命令开始战斗。之后你将在战斗菜单中，并将使用菜单进行所有后续动作。

## 回合制战斗处理器

> 创建一个新模块`evadventure/combat_turnbased.py`。

```python
# 在 evadventure/combat_turnbased.py 中

from .combat_base import (
   CombatActionAttack,
   CombatActionHold,
   CombatActionStunt,
   CombatActionUseItem,
   CombatActionWield,
   EvAdventureCombatBaseHandler,
)

from .combat_base import EvAdventureCombatBaseHandler

class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

    action_classes = {
        "hold": CombatActionHold,
        "attack": CombatActionAttack,
        "stunt": CombatActionStunt,
        "use": CombatActionUseItem,
        "wield": CombatActionWield,
        "flee": None # 我们很快会添加这个！
    }

    # 如果未选择任何内容，则为后备动作
    fallback_action_dict = AttributeProperty({"key": "hold"}, autocreate=False)

    # 跟踪我们处于哪个回合
    turn = AttributeProperty(0)
    # 谁参与了战斗，以及他们排队的动作
    # 作为{combatant: actiondict, ...}
    combatants = AttributeProperty(dict)

    # 谁对谁有优势。这是一个类似{"combatant": {enemy1: True, enemy2: True}}的结构
    advantage_matrix = AttributeProperty(defaultdict(dict))
    # 劣势的同样
    disadvantage_matrix = AttributeProperty(defaultdict(dict))

    # 你必须逃跑多少回合才能逃脱
    flee_timeout = AttributeProperty(1, autocreate=False)

    # 跟踪谁在逃跑，作为{combatant: turn_they_started_fleeing}
    fleeing_combatants = AttributeProperty(dict)

    # 到目前为止被击败的人的列表
    defeated_combatants = AttributeProperty(list)
```

我们为`"flee"`动作留了一个占位符，因为我们还没有创建它。

由于回合制战斗处理器在所有战斗者之间共享，我们需要在处理器上存储这些战斗者的引用，在`combatants` [属性](Attribute)中。同样，我们必须存储一个_矩阵_，以确定谁对谁有优势/劣势。我们还必须跟踪谁在_逃跑_，特别是他们逃跑了多久，因为他们将在那段时间后离开战斗。

### 获取战斗双方

这两方取决于我们是否在[PvP房间](./Beginner-Tutorial-Rooms.md)：在PvP房间中，其他所有人都是你的敌人。否则，只有战斗中的NPC是你的敌人（假设你与其他玩家组队）。

```python
# 在 evadventure/combat_turnbased.py 中

# ...

class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

    # ...

    def get_sides(self, combatant):
           """
           从提供的战斗者的角度获取此战斗的两个“方面”的列表。
           """
           if self.obj.allow_pvp:
               # 在pvp中，其他所有人都是敌人
               allies = [combatant]
               enemies = [comb for comb in self.combatants if comb != combatant]
           else:
               # 否则，敌人/盟友取决于战斗者是谁
               pcs = [comb for comb in self.combatants if inherits_from(comb, EvAdventureCharacter)]
               npcs = [comb for comb in self.combatants if comb not in pcs]
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

请注意，由于`EvadventureCombatBaseHandler`（我们的回合制处理器基于它）是一个[脚本](../../../Components/Scripts.md)，它提供了许多有用的功能。例如，`self.obj`是此脚本“坐在”其上的实体。由于我们计划将此处理器放在当前位置，因此`self.obj`将是该房间。

我们在这里所做的只是检查它是否是PvP房间，并使用此信息来确定谁是盟友或敌人。请注意，`combatant`不包含在返回的`allies`中——我们需要记住这一点。

### 跟踪优势/劣势

```python
# 在 evadventure/combat_turnbased.py 中

# ...

class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

    # ...

    def give_advantage(self, combatant, target):
        self.advantage_matrix[combatant][target] = True

    def give_disadvantage(self, combatant, target, **kwargs):
        self.disadvantage_matrix[combatant][target] = True

    def has_advantage(self, combatant, target, **kwargs):
        return (
            target in self.fleeing_combatants
            or bool(self.advantage_matrix[combatant].pop(target, False))
        )
    def has_disadvantage(self, combatant, target):
        return bool(self.disadvantage_matrix[combatant].pop(target, False))
```

我们使用`advantage/disadvantage_matrix`属性来跟踪谁对谁有优势。

```{sidebar} .pop()
Python `.pop()`方法存在于列表和字典以及其他一些可迭代对象上。它从容器中“弹出”并返回一个元素。对于列表，可以按索引弹出或弹出最后一个元素。对于字典（如这里），必须给定一个特定的键来弹出。如果不提供默认值作为第二个元素，则如果尝试弹出的键未找到，将引发错误。
```

在`has dis/advantage`方法中，我们从矩阵中`pop`目标，这将导致值为`True`或`False`（如果目标不在矩阵中，我们给`pop`的默认值）。这意味着一旦获得优势，就只能使用一次。

我们还认为每个人对逃跑的战斗者都有优势。

### 添加和移除战斗者

由于战斗处理器是共享的，我们必须能够轻松地添加和移除战斗者。这与基础处理器相比是新的。

```python
# 在 evadventure/combat_turnbased.py 中

# ...

class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

    # ...

    def add_combatant(self, combatant):
        """
        向战斗中添加一个新的战斗者。可以安全地多次调用。
        """
        if combatant not in self.combatants:
            self.combatants[combatant] = self.fallback_action_dict
            return True
        return False

    def remove_combatant(self, combatant):
        """
        从战斗中移除一个战斗者。
        """
        self.combatants.pop(combatant, None)
        # 清理菜单（如果存在）
        # TODO!
```

我们只是用后备动作字典添加战斗者。我们从`add_combatant`返回一个`bool`，以便调用函数知道他们是否真的被重新添加（如果他们是新的，我们可能想要进行一些额外的设置）。

目前我们只是`pop`战斗者，但将来我们需要在战斗结束时对菜单进行一些额外的清理（我们会做到这一点）。

### 逃跑动作

由于你不能只是移动离开房间以逃离回合制战斗，我们需要添加一个新的`CombatAction`子类，就像我们在[基础战斗课程](./Beginner-Tutorial-Combat-Base.md#actions)中创建的那些一样。

```python
# 在 evadventure/combat_turnbased.py 中

from .combat_base import CombatAction

# ...

class CombatActionFlee(CombatAction):
    """
    开始（或继续）逃离/脱离战斗。

    action_dict = {
           "key": "flee",
        }
    """

    def execute(self):
        combathandler = self.combathandler

        if self.combatant not in combathandler.fleeing_combatants:
            # 我们记录开始逃跑的回合
            combathandler.fleeing_combatants[self.combatant] = self.combathandler.turn

        # 显示成功逃跑还需要多少回合
        current_turn = combathandler.turn
        started_fleeing = combathandler.fleeing_combatants[self.combatant]
        flee_timeout = combathandler.flee_timeout
        time_left = flee_timeout - (current_turn - started_fleeing) - 1

        if time_left > 0:
            self.msg(
                "$You() $conj(retreat), being exposed to attack while doing so (will escape in "
                f"{time_left} $pluralize(turn, {time_left}))."
            )


class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

    action_classes = {
        "hold": CombatActionHold,
        "attack": CombatActionAttack,
        "stunt": CombatActionStunt,
        "use": CombatActionUseItem,
        "wield": CombatActionWield,
        "flee": CombatActionFlee # < ---- 添加！
    }

    # ...
```

我们创建了一个动作来利用我们在战斗处理器中设置的`fleeing_combatants`字典。此字典存储逃跑的战斗者以及其逃跑开始的`turn`。如果多次执行`flee`动作，我们将只显示还剩多少回合。

最后，我们确保将新的`CombatActionFlee`添加到战斗处理器的`action_classes`注册表中。

### 队列动作

```python
# 在 evadventure/combat_turnbased.py 中

# ...

class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

    # ...

    def queue_action(self, combatant, action_dict):
        self.combatants[combatant] = action_dict

        # 跟踪谁在本回合插入了动作（非持久性）
        did_action = set(self.ndb.did_action or set())
        did_action.add(combatant)
        if len(did_action) >= len(self.combatants):
            # 每个人都插入了一个动作。立即开始下一回合！
            self.force_repeat()

```

要排队一个动作，我们只需将其`action_dict`与战斗者一起存储在`combatants`属性中。

我们使用Python `set()`来跟踪谁在本回合排队了一个动作。如果所有战斗者在本回合输入了一个新动作（或更新的动作），我们使用`.force_repeat()`方法，该方法在所有[脚本](../../../Components/Scripts.md)上可用。当调用此方法时，下一轮将立即触发，而不是等到超时。

### 执行动作并进行回合

```{code-block} python
:linenos:
:emphasize-lines: 13,16,17,22,43,49

# 在 evadventure/combat_turnbased.py 中

import random

# ...

class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

    # ...

    def execute_next_action(self, combatant):
        # 获取下一个字典并旋转队列
        action_dict = self.combatants.get(combatant, self.fallback_action_dict)

        # 使用动作字典从动作类中选择并创建一个动作
        action_class = self.action_classes[action_dict["key"]]
        action = action_class(self, combatant, action_dict)

        action.execute()
        action.post_execute()

        if action_dict.get("repeat", False):
            # 再次排队动作*而不更新*.ndb.did_action列表*（否则
            # 如果每个人都使用重复动作，我们总是会自动结束回合
            # 并且在下一轮之前没有时间更改它）
            self.combatants[combatant] = action_dict
        else:
            # 如果不是重复，则设置后备动作
            self.combatants[combatant] = self.fallback_action_dict


   def at_repeat(self):
        """
        每次脚本重复时调用此方法
        （每`interval`秒）。执行完整的战斗回合，以随机顺序执行每个人的动作。
        """
        self.turn += 1
        # 随机回合顺序
        combatants = list(self.combatants.keys())
        random.shuffle(combatants)  # 就地洗牌

        # 执行每个人的下一个排队战斗动作
        for combatant in combatants:
            self.execute_next_action(combatant)

        self.ndb.did_action = set()

        # 检查一方是否赢得了战斗
        self.check_stop_combat()

```

我们的动作执行由两个部分组成——`execute_next_action`（在父类中定义供我们实现）和`at_repeat`方法，这是[脚本](../../../Components/Scripts.md)的一部分。

对于`execute_next_action`：

- **第13行**：我们从`combatants`属性中获取`action_dict`。如果没有排队的动作，则返回`fallback_action_dict`（默认为`hold`）。
- **第16行**：我们使用`action_dict`的`key`（可能是"attack"、"use"、"wield"等）从`action_classes`字典中获取匹配动作的类。
- **第17行**：在此处实例化动作类，并准备好执行。然后在接下来的几行中执行此操作。
- **第22行**：我们在此引入一个新的可选`action-dict`，即布尔值`repeat`键。这允许我们重新排队动作。如果没有，将使用后备动作。

`at_repeat`每`interval`秒重复调用一次脚本触发。这是我们用来跟踪每轮结束的方式。

- **第43行**：在此示例中，我们的动作之间没有内部顺序。因此，我们只是随机化它们触发的顺序。
- **第49行**：此`set`在`queue_action`方法中被分配，以便知道何时每个人都提交了一个新动作。我们必须确保在下一轮之前在这里取消设置它。

### 检查和停止战斗

```{code-block} python
:linenos:
:emphasize-lines: 28,41,49,60

# 在 evadventure/combat_turnbased.py 中

import random
from evennia.utils.utils import list_to_string

# ...

class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

    # ...

     def stop_combat(self):
        """
        立即停止战斗。

        """
        for combatant in self.combatants:
            self.remove_combatant(combatant)
        self.stop()
        self.delete()

    def check_stop_combat(self):
        """检查是否是停止战斗的时候"""

        # 检查是否有人被击败
        for combatant in list(self.combatants.keys()):
            if combatant.hp <= 0:
                # PC在此处掷骰子，NPC死亡。
                # 即使PC幸存，他们
                # 仍然退出战斗。
                combatant.at_defeat()
                self.combatants.pop(combatant)
                self.defeated_combatants.append(combatant)
                self.msg("|r$You() $conj(fall) to the ground, defeated.|n", combatant=combatant)
            else:
                self.combatants[combatant] = self.fallback_action_dict

        # 检查是否有人成功逃跑
        flee_timeout = self.flee_timeout
        for combatant, started_fleeing in self.fleeing_combatants.items():
            if self.turn - started_fleeing >= flee_timeout - 1:
                # 如果他们仍然活着/逃跑并且已经逃跑足够长时间，则逃脱
                self.msg("|y$You() successfully $conj(flee) from combat.|n", combatant=combatant)
                self.remove_combatant(combatant)

        # 检查一方是否赢得了战斗
        if not self.combatants:
            # 没有人留在战斗中 - 也许他们互相杀死或全部逃跑
            surviving_combatant = None
            allies, enemies = (), ()
        else:
            # 抓住一个随机幸存者并检查他们是否有任何活着的敌人。
            surviving_combatant = random.choice(list(self.combatants.keys()))
            allies, enemies = self.get_sides(surviving_combatant)

        if not enemies:
            # 如果没有敌人可战斗
            still_standing = list_to_string(f"$You({comb.key})" for comb in allies)
            knocked_out = list_to_string(comb for comb in self.defeated_combatants if comb.hp > 0)
            killed = list_to_string(comb for comb in self.defeated_combatants if comb.hp <= 0)

            if still_standing:
                txt = [f"The combat is over. {still_standing} are still standing."]
            else:
                txt = ["The combat is over. No-one stands as the victor."]
            if knocked_out:
                txt.append(f"{knocked_out} were taken down, but will live.")
            if killed:
                txt.append(f"{killed} were killed.")
            self.msg(txt)
            self.stop_combat()
```

`check_stop_combat`在回合结束时调用。我们想要确定谁死了以及是否有一方赢了。

- **第28-38行**：我们遍历所有战斗者，确定他们是否没有HP。如果是这样，我们触发相关的钩子并将它们添加到`defeated_combatants`属性中。
- **第38行**：对于所有幸存的战斗者，我们确保给他们`fallback_action_dict`。
- **第41-46行**：`fleeing_combatant`属性是一个形式为`{fleeing_combatant: turn_number}`的字典，跟踪他们首次开始逃跑的时间。我们将其与当前回合数和`flee_timeout`进行比较，以查看他们是否现在逃跑并应被允许从战斗中移除。
- **第49-56行**：从这里开始，我们确定冲突的一方是否击败了另一方。
- **第60行**：`list_to_string` Evennia实用工具将一个条目列表（如`["a", "b", "c"`）转换为一个漂亮的字符串`"a, b and c"`。我们使用它来向战斗者展示一些漂亮的结束消息。

### 开始战斗

由于我们使用[脚本](../../../Components/Scripts.md)的计时器组件来滴答我们的战斗，我们还需要一个助手方法来“启动”它。

```python
from evennia.utils.utils import list_to_string

# 在 evadventure/combat_turnbased.py 中

# ...

class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

    # ...

    def start_combat(self, **kwargs):
        """
        这实际上开始了战斗。可以安全地多次运行此命令
        因为它只会在尚未运行时开始战斗。

        """
        if not self.is_active:
            self.start(**kwargs)

```

`start(**kwargs)`方法是脚本上的一个方法，并将使其开始每`interval`秒调用`at_repeat`方法。我们将在`kwargs`中传递该`interval`（例如，我们稍后将执行`combathandler.start_combat(interval=30)`）。

## 使用EvMenu进行战斗菜单

_EvMenu_用于在Evennia中创建游戏内菜单。我们已经在[角色生成课程](./Beginner-Tutorial-Chargen.md)中使用了一个简单的EvMenu。这次我们需要更高级一点。虽然[EvMenu文档](../../../Components/EvMenu.md)详细描述了其功能，但我们将在这里快速概述一下它的工作原理。

EvMenu由_节点_组成，这些节点是以下形式的常规函数（这里稍作简化，还有更多选项）：

```python
def node_somenodename(caller, raw_string, **kwargs):

    text = "some text to show in the node"
    options = [
        {
           "key": "Option 1", # 跳过此选项以获得一个数字
           "desc": "Describing what happens when choosing this option."
           "goto": "name of the node to go to"  # 或(callable, {kwargs}})返回该名称
        },
        # 其他选项在这里
    ]
    return text, options
```

基本上，每个节点都接受`caller`（使用菜单的人）、`raw_string`（上一个节点输入的空字符串或用户输入的内容）和`**kwargs`（可用于从一个节点传递到另一个节点的数据）作为参数。它返回`text`和`options`。

`text`是用户进入此菜单部分时将看到的内容，例如“选择你想攻击的人！”。`options`是描述每个选项的字典列表。它们将显示为节点文本下方的多选列表（请参见本课程页面顶部的示例）。

稍后创建EvMenu时，我们将创建一个_节点索引_——一个唯一名称与这些“节点函数”之间的映射。像这样：

```python
# EvMenu节点索引示例
    {
      "start": node_combat_main,
      "node1": node_func1,
      "node2": node_func2,
      "some name": node_somenodename,
      "end": node_abort_menu,
    }
```

每个`option`字典都有一个键`"goto"`，用于确定玩家选择该选项时应跳转到哪个节点。在菜单中，每个节点都需要使用这些名称引用（如`"start"`、`"node1"`等）。

每个选项的`"goto"`值可以直接指定名称（如`"node1"`）_或_可以作为元组`(callable, {keywords})`给出。此`callable`将被_调用_，并且应返回要使用的下一个节点名称（如`"node1"`）。

`callable`（通常称为“goto callable”）看起来非常类似于节点函数：

```python
def _goto_when_choosing_option1(caller, raw_string, **kwargs):
    # 执行确定下一个节点所需的操作
    return nodename  # 也可以是nodename, dict
```

```{sidebar} 将节点函数与goto callable分开
为了使节点函数与goto callable明确分开，Evennia文档始终在节点函数前加上`node_`，在菜单goto函数前加上下划线`_`（这也使goto函数在Python术语中是“私有的”）。
```

在这里，`caller`仍然是使用菜单的人，`raw_string`是你输入以选择此选项的实际字符串。`**kwargs`是你添加到`(callable, {keywords})`元组中的关键字。

goto callable必须返回下一个节点的名称。可选地，你可以返回`nodename, {kwargs}`。如果这样做，下一节点将获得这些kwargs作为传入的`**kwargs`。通过这种方式，你可以将信息从一个节点传递到下一个节点。一个特殊功能是，如果`nodename`作为`None`返回，则_当前_节点将被_重新运行_。

这是一个（有些牵强的）示例，说明goto callable和节点函数如何结合在一起：

```
# goto callable
def _my_goto_callable(caller, raw_string, **kwargs):
    info_number = kwargs["info_number"]
    if info_number > 0:
        return "node1"
    else:
        return "node2", {"info_number": info_number}  # 在“node2”下次运行时将作为**kwargs传递


# 节点函数
def node_somenodename(caller, raw_string, **kwargs):
    text = "Some node text"
    options = [
        {
            "desc": "Option one",
            "goto": (_my_goto_callable, {"info_number", 1})
        },
        {
            "desc": "Option two",
            "goto": (_my_goto_callable, {"info_number", -1})
        },
    ]
```

## 回合制战斗菜单

我们的战斗菜单将非常简单。我们将有一个中心菜单节点，其中包含指示战斗的所有不同动作的选项。当在菜单中选择一个动作时，玩家应该被问到一系列问题，每个问题都指定该动作所需的信息。最后一步是将这些信息构建为一个可以与combathandler排队的`action-dict`。

为了理解这个过程，以下是动作选择的工作方式（从左到右阅读）：

| 在基础节点中 | 第一步 | 第二步 | 第三步 | 第四步 |
| --- | --- | --- | --- | --- |
| 选择`attack` | 选择`target` | 排队动作字典 | - | - |
| 选择`stunt - give advantage` | 选择`Ability`| 选择`allied recipient` | 选择`enemy target` | 排队动作字典 |
| 选择`stunt - give disadvantage` | 选择`Ability` | 选择`enemy recipient` | 选择`allied target` | 排队动作字典 |
| 选择`use item on yourself or ally` | 从库存中选择`item` | 选择`allied target` | 排队动作字典 | - |
| 选择`use item on enemy` | 从库存中选择`item` | 选择`enemy target` | 排队动作字典 | - |
| 选择`wield/swap item from inventory` | 从库存中选择`item` | 排队动作字典 | - | - |
| 选择`flee` | 排队动作字典 | - | - | - |
| 选择`hold, doing nothing` | 排队动作字典 | - | - | - |

查看上表，我们可以看到我们有_很多_重用。选择盟友/敌人/目标/接收者/物品代表可以由不同动作共享的节点。

这些动作中的每一个也遵循一个线性序列，就像你在某些软件中看到的逐步“向导”一样。我们希望能够在每个序列中前后移动，如果你在途中改变主意，也可以中止动作。

在排队动作后，我们应该始终返回到基础节点，在那里我们将等待直到回合结束并执行所有动作。

我们将创建一些助手，以使我们的特定菜单易于使用。

### 节点索引

这些是我们菜单所需的节点：

```python
# 尚未在任何地方编码，仅供参考
node_index = {
    # 节点名称                # callable   # （未来的callable）
    "node_choose_enemy_target": None, # node_choose_enemy_target,
    "node_choose_allied_target": None, # node_choose_allied_target,
    "node_choose_enemy_recipient": None, # node_choose_enemy_recipient,
    "node_choose_allied_recipient": None, # node_choose_allied_recipient,
    "node_choose_ability": None, # node_choose_ability,
    "node_choose_use_item": None, # node_choose_use_item,
    "node_choose_wield_item": None, # node_choose_wield_item,
    "node_combat": None, # node_combat,
}
```

所有callable都留作`None`，因为我们还没有创建它们。但记下预期的名称是好的，因为我们需要它们来从一个节点跳转到另一个节点。重要的是要注意`node_combat`将是我们应该一次又一次返回的基础节点。

### 获取或设置战斗处理器

```python
# 在 evadventure/combat_turnbased.py 中

from evennia import EvMenu

# ...

def _get_combathandler(caller, turn_timeout=30, flee_time=3, combathandler_key="combathandler"):
    return EvAdventureTurnbasedCombatHandler.get_or_create_combathandler(
        caller.location,
        interval=turn_timeout,
        attributes=[("flee_time", flee_time)],
        key=combathandler_key,
    )
```

我们添加这个只是为了在稍后调用时不必写太多。我们传递`caller.location`，这就是在当前位置检索/创建战斗处理器的方式。`interval`是战斗处理器（这是一个[脚本](../../../Components/Scripts.md)）将调用其`at_repeat`方法的频率。我们同时设置`flee_time`属性。

### 排队动作

这是我们的第一个“goto函数”。这将被调用以实际将我们完成的动作字典排队到战斗处理器中。完成后，它应返回到基础`node_combat`。

```python
# 在 evadventure/combat_turnbased.py 中

# ...

def _queue_action(caller, raw_string, **kwargs):
    action_dict = kwargs["action_dict"]
    _get_combathandler(caller).queue_action(caller, action_dict)
    return "node_combat"
```

我们在这里做了一个假设——`kwargs`包含`action_dict`键，并且动作字典已准备好使用。

由于这是一个goto callable，我们必须返回下一个要跳转的节点。由于这是最后一步，我们将始终返回到`node_combat`基础节点，因此这是我们返回的内容。

### 重新运行节点

goto callable的一个特殊功能是能够通过返回`None`重新运行相同的节点。

```python
# 在 evadventure/combat_turnbased.py 中

# ...

def _rerun_current_node(caller, raw_string, **kwargs):
    return None, kwargs
```

在选项中使用此功能将重新运行当前节点，但会保留传入的`kwargs`。

### 逐步完成向导

我们的菜单非常对称——你选择一个选项，然后你将只选择一系列选项，然后返回。因此，我们将制作另一个goto函数，以帮助我们轻松完成此操作。为了理解这一点，让我们首先展示我们计划如何使用它：

```python
# 在基础战斗节点函数中（仅作为示例显示）

options = [
    # ...
    "desc": "use an item on an enemy",
    "goto": (
       _step_wizard,
       {
           "steps": ["node_choose_use_item", "node_choose_enemy_target"],
           "action_dict": {"key": "use", "item": None, "target": None},
       }
    )
]
```

当用户选择在敌人身上使用物品时，我们将使用两个关键字`steps`和`action_dict`调用`_step_wizard`。第一个是我们需要引导玩家完成以构建我们的动作字典的_序列_。

后者是`action_dict`本身。每个节点将逐步填充此字典中的`None`位置，直到我们拥有一个完整的字典并可以将其发送到我们之前定义的[`_queue_action`](#queue-an-action) goto函数。

此外，我们希望能够像这样“返回”到上一个节点：

```python
# 在其他节点中（仅作为示例显示）

def some_node(caller, raw_string, **kwargs):

    # ...

    options = [
        # ...
        {
            "key": "back",
            "goto": ( _step_wizard, {**kwargs, **{"step": "back"}})
        },
    ]

    # ...
```

请注意这里使用的`**`。`{**dict1, **dict2}`是一种强大的单行语法，用于将两个字典合并为一个。这保留了（并传递了）传入的`kwargs`，并仅向其中添加了一个新键"step"。最终效果类似于我们在单独的行中执行`kwargs["step"] = "back"`（除了使用`**`方法时，我们最终得到一个_新_的`dict`）。

所以让我们实现一个`_step_wizard` goto函数来处理这个！

```python
# 在 evadventure/combat_turnbased.py 中

# ...

def _step_wizard(caller, raw_string, **kwargs):

    # 获取步骤并计算它们
    steps = kwargs.get("steps", [])
    nsteps = len(steps)

    # 跟踪我们处于哪个步骤
    istep = kwargs.get("istep", -1)

    # 检查我们是否正在后退（默认是前进）
    step_direction = kwargs.get("step", "forward")

    if step_direction == "back":
        # 在向导中后退一步
        if istep <= 0:
            # 回到起点
            return "node_combat"
        istep = kwargs["istep"] = istep - 1
        return steps[istep], kwargs
    else:
        # 在向导中前进一步
        if istep >= nsteps - 1:
            # 我们已经在向导的末尾 - 排队动作！
            return _queue_action(caller, raw_string, **kwargs)
        else:
            # 前进一步
            istep = kwargs["istep"] = istep + 1
            return steps[istep], kwargs

```

这取决于通过`**kwargs`传递`steps`、`step`和`istep`。如果`step`是"back"，我们将在`steps`序列中后退，否则前进。我们增加/减少`istep`键值以跟踪我们的位置。

如果我们到达末尾，我们直接调用我们的`_queue_action`助手函数。如果我们回到开头，我们返回到基础节点。

我们将制作一个最终的助手函数，以快速将`back`（和`abort`）选项添加到需要它的节点：

```python
# 在 evadventure/combat_turnbased.py 中

# ...

_get_default_wizard_options(caller, **kwargs):
    return [
        {
            "key": "back",
            "goto": (_step_wizard, {**kwargs, **{"step": "back"}})
        },
        {
            "key": "abort",
            "goto": "node_combat"
        },
        {
            "key": "_default",
            "goto": (_rerun_current_node, kwargs),
        },
    ]
```

这不是一个goto函数，它只是一个助手，我们将调用它以快速将这些额外选项添加到节点的选项列表中，而不必一遍又一遍地输入。

正如我们之前所见，`back`选项将使用`_step_wizard`在向导中后退。`abort`选项将简单地跳回主节点，中止向导。

`_default`选项是特殊的。此选项键告诉EvMenu：“如果没有其他选项匹配，请使用此选项”。也就是说，如果他们输入空输入或垃圾输入，我们将重新显示节点。我们确保传递`kwargs`，以便我们不会丢失我们在向导中的位置信息。

最后，我们准备好编写我们的菜单节点了！

### 选择目标和接收者

这些节点的工作原理相同：它们应该提供一个合适的目标/接收者列表供选择，然后将结果放入动作字典中作为`target`或`recipient`键。

```{code-block} python
:linenos:
:emphasize-lines: 11,13,15,18,23

# 在 evadventure/combat_turnbased.py 中

# ...

def node_choose_enemy_target(caller, raw_string, **kwargs):

    text = "Choose an enemy to target"

    action_dict = kwargs["action_dict"]
    combathandler = _get_combathandler(caller)
    _, enemies = combathandler.get_sides(caller)

    options = [
        {
            "desc": target.get_display_name(caller),
            "goto": (
                _step_wizard,
                {**kwargs, **{"action_dict": {**action_dict, **{"target": target}}}},
            )
        }
        for target in enemies
    ]
    options.extend(_get_default_wizard_options(caller, **kwargs))
    return text, options


def node_choose_enemy_recipient(caller, raw_string, **kwargs):
     # 几乎相同，只是存储"recipient"


def node_choose_allied_target(caller, raw_string, **kwargs):
     # 几乎相同，只是使用allies + yourself


def node_choose_allied_recipient(caller, raw_string, **kwargs):
     # 几乎相同，只是使用allies + yourself并存储"recipient"

```

- **第11行**：在这里，我们使用`combathandler.get_sides(caller)`从`caller`（使用菜单的人）的角度获取“enemies”。
- **第13-31行**：这是一个循环，遍历我们找到的所有敌人。
    - **第15行**：我们使用`target.get_display_name(caller)`。此方法（Evennia `Objects`上的默认方法）允许目标在知道是谁在询问的情况下返回名称。这就是管理员看到`Name (#5)`而普通用户只看到`Name`的原因。如果你对此不感兴趣，你可以在这里直接使用`target.key`。
    - **第18行**：这行看起来很复杂，但请记住，`{**dict1, **dict2}`是一种将两个字典合并为一个字典的单行方法。这是在三步中完成的：
        - 首先，我们将`action_dict`与一个字典`{"target": target}`合并。这与执行`action_dict["target"] = target`的效果相同，除了我们创建了一个新的字典作为合并结果。
        - 接下来，我们将这个新合并的字典创建为一个新的字典`{"action_dict": new_action_dict}`。
        - 最后，我们将其与现有的`kwargs`字典合并。结果是一个新的字典，现在具有更新的`"action_dict"`键，指向一个设置了`target`的动作字典。
- **第23行**：我们使用默认的向导选项（`back`、`abort`）扩展`options`列表。由于我们为此创建了一个助手函数，因此这只需一行。

创建其他三个所需的节点`node_choose_enemy_recipient`、`node_choose_allied_target`和`node_choose_allied_recipient`遵循相同的模式；它们只是使用`combathandler.get_sides()`的`allies`或`enemies`返回值。然后在`action_dict`中设置`target`或`recipient`字段。我们将这些留给读者实现。

### 选择能力

对于特技，我们需要能够选择你想要增强/阻止的_Knave_能力（STR、DEX等）。

```python
# 在 evadventure/combat_turnbased.py 中

from .enums import Ability

# ...

def node_choose_ability(caller, raw_string, **kwargs):
    text = "Choose the ability to apply"
    action_dict = kwargs["action_dict"]

    options = [
        {
            "desc": abi.value,
            "goto": (
                _step_wizard,
                {
                    **kwargs,
                    **{
                        "action_dict": {**action_dict, **{"stunt_type": abi, "defense_type": abi}},
                    },
                },
            ),
        }
        for abi in (
            Ability.STR,
            Ability.DEX,
            Ability.CON,
            Ability.INT,
            Ability.INT,
            Ability.WIS,
            Ability.CHA,
        )
    ]
    options.extend(_get_default_wizard_options(caller, **kwargs))
    return text, options

```

原理与目标/接收者设置节点相同，只是我们提供了一个能力列表供选择。我们根据特技动作的需要更新`action_dict`中的`stunt_type`和`defense_type`键。

### 选择要使用或装备的物品

```python
# 在 evadventure/combat_turnbased.py 中

# ...

def node_choose_use_item(caller, raw_string, **kwargs):
    text = "Select the item"
    action_dict = kwargs["action_dict"]

    options = [
        {
            "desc": item.get_display_name(caller),
            "goto": (
                _step_wizard,
                {**kwargs, **{"action_dict": {**action_dict, **{"item": item}}}},
            ),
        }
        for item in caller.equipment.get_usable_objects_from_backpack()
    ]
    if not options:
        text = "There are no usable items in your inventory!"

    options.extend(_get_default_wizard_options(caller, **kwargs))
    return text, options


def node_choose_wield_item(caller, raw_string, **kwargs):
     # 相同，但使用caller.equipment.get_wieldable_objects_from_backpack()

```

我们的[装备处理器](./Beginner-Tutorial-Equipment.md)具有非常有用的帮助方法`.get_usable_objects_from_backpack`。我们只需调用此方法即可获取我们想要选择的所有物品的列表。否则，此节点现在应该看起来很熟悉。

`node_choose_wield_item`非常相似，只是使用`caller.equipment.get_wieldable_objects_from_backpack()`。我们将其实现留给读者。

### 主菜单节点

这将所有内容结合在一起。

```python
# 在 evadventure/combat_turnbased.py 中

# ...

def node_combat(caller, raw_string, **kwargs):
    """基础战斗菜单"""

    combathandler = _get_combathandler(caller)

    text = combathandler.get_combat_summary(caller)
    options = [
        {
            "desc": "attack an enemy",
            "goto": (
                _step_wizard,
                {
                    "steps": ["node_choose_enemy_target"],
                    "action_dict": {"key": "attack", "target": None, "repeat": True},
                },
            ),
        },
        {
            "desc": "Stunt - gain a later advantage against a target",
            "goto": (
                _step_wizard,
                {
                    "steps": [
                        "node_choose_ability",
                        "node_choose_enemy_target",
                        "node_choose_allied_recipient",
                    ],
                    "action_dict": {"key": "stunt", "advantage": True},
                },
            ),
        },
        {
            "desc": "Stunt - give an enemy disadvantage against yourself or an ally",
            "goto": (
                _step_wizard,
                {
                    "steps": [
                        "node_choose_ability",
                        "node_choose_enemy_recipient",
                        "node_choose_allied_target",
                    ],
                    "action_dict": {"key": "stunt", "advantage": False},
                },
            ),
        },
        {
            "desc": "Use an item on yourself or an ally",
            "goto": (
                _step_wizard,
                {
                    "steps": ["node_choose_use_item", "node_choose_allied_target"],
                    "action_dict": {"key": "use", "item": None, "target": None},
                },
            ),
        },
        {
            "desc": "Use an item on an enemy",
            "goto": (
                _step_wizard,
                {
                    "steps": ["node_choose_use_item", "node_choose_enemy_target"],
                    "action_dict": {"key": "use", "item": None, "target": None},
                },
            ),
        },
        {
            "desc": "Wield/swap with an item from inventory",
            "goto": (
                _step_wizard,
                {
                    "steps": ["node_choose_wield_item"],
                    "action_dict": {"key": "wield", "item": None},
                },
            ),
        },
        {
            "desc": "flee!",
            "goto": (_queue_action, {"action_dict": {"key": "flee", "repeat": True}}),
        },
        {
            "desc": "hold, doing nothing",
            "goto": (_queue_action, {"action_dict": {"key": "hold"}}),
        },
        {
            "key": "_default",
            "goto": "node_combat",
        },
    ]

    return text, options
```

这为每个动作选择启动了`_step_wizard`。它还为每个动作布局了`action_dict`，为将由以下节点设置的字段保留`None`值。

注意我们如何将`"repeat"`键添加到某些动作中。让它们自动重复意味着玩家不必每次都输入相同的动作。

## 攻击命令

我们只需要一个命令来运行回合制战斗系统。这是`attack`命令。一旦你使用它一次，你将进入菜单。

```python
# 在 evadventure/combat_turnbased.py 中

from evennia import Command, CmdSet, EvMenu

# ...

class CmdTurnAttack(Command):
    """
    开始或加入战斗。

    用法：
      attack [<target>]

    """

    key = "attack"
    aliases = ["hit", "turnbased combat"]

    turn_timeout = 30  # 秒
    flee_time = 3  # 回合

    def parse(self):
        super().parse()
        self.args = self.args.strip()

    def func(self):
        if not self.args:
            self.msg("你在攻击什么？")
            return

        target = self.caller.search(self.args)
        if not target:
            return

        if not hasattr(target, "hp"):
            self.msg("你不能攻击那个。")
            return

        elif target.hp <= 0:
            self.msg(f"{target.get_display_name(self.caller)}已经倒下。")
            return

        if target.is_pc and not target.location.allow_pvp:
            self.msg("这里不允许PvP战斗！")
            return

        combathandler = _get_combathandler(
            self.caller, self.turn_timeout, self.flee_time)

        # 将战斗者添加到combathandler。可以安全地一遍又一遍地完成
        combathandler.add_combatant(self.caller)
        combathandler.queue_action(self.caller, {"key": "attack", "target": target})
        combathandler.add_combatant(target)
        target.msg("|r你被{self.caller.get_display_name(self.caller)}攻击了！|n")
        combathandler.start_combat()

        # 构建并启动菜单
        EvMenu(
            self.caller,
            {
                "node_choose_enemy_target": node_choose_enemy_target,
                "node_choose_allied_target": node_choose_allied_target,
                "node_choose_enemy_recipient": node_choose_enemy_recipient,
                "node_choose_allied_recipient": node_choose_allied_recipient,
                "node_choose_ability": node_choose_ability,
                "node_choose_use_item": node_choose_use_item,
                "node_choose_wield_item": node_choose_wield_item,
                "node_combat": node_combat,
            },
            startnode="node_combat",
            combathandler=combathandler,
            auto_look=False,
            # cmdset_mergetype="Union",
            persistent=True,
        )


class TurnCombatCmdSet(CmdSet):
    """
    回合制战斗的CmdSet。
    """

    def at_cmdset_creation(self):
        self.add(CmdTurnAttack())
```

`attack target`命令将确定目标是否有生命值（只有有生命值的东西可以被攻击）以及房间是否允许战斗。如果目标是pc，它将检查是否允许PvP。

然后，它继续启动一个新的命令处理器或重用一个新的命令处理器，同时将攻击者和目标添加到其中。如果目标已经在战斗中，这不会做任何事情（与`.start_combat()`调用相同）。

当我们创建`EvMenu`时，我们将其传递给我们之前讨论的“菜单索引”，现在每个插槽中都有实际的节点函数。我们使菜单持久化，以便在重新加载时仍然存在。

要使命令可用，请将`TurnCombatCmdSet`添加到角色的默认cmdset中。

## 确保菜单停止

战斗可能由于多种原因而结束。当这种情况发生时，我们必须确保清理菜单，以便恢复正常操作。我们将在战斗处理器的`remove_combatant`方法中添加这一点（我们之前在那里留下了一个TODO）：

```python

# 在 evadventure/combat_turnbased.py 中

# ...

class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

    # ...
    def remove_combatant(self, combatant):
        """
        从战斗中移除一个战斗者。
        """
        self.combatants.pop(combatant, None)
        # 清理菜单（如果存在）
        if combatant.ndb._evmenu:                   # <--- 新增
            combatant.ndb._evmenu.close_menu()      #     ''

```

当evmenu处于活动状态时，它可以通过`.ndb._evmenu`在其用户上获得（参见EvMenu文档）。当我们从战斗中移除时，我们使用它来获取evmenu并调用其`close_menu()`方法以关闭菜单。

我们的回合制战斗系统完成了！

## 测试

```{sidebar}
请参见`evennia/contrib/tutorials`中的示例测试，在[evadventure/tests/test_combat.py](evennia.contrib.tutorials.evadventure.tests.test_combat)中
```

对回合制战斗处理器进行单元测试很简单，你可以按照早期课程的过程测试处理器上的每个方法是否返回你期望的模拟输入。

对菜单进行单元测试更加复杂。你可以在[evennia.utils.tests.test_evmenu](github:main/evennia/utils/testss/test_evmenu.py)中找到示例。

## 小型战斗测试

对代码进行单元测试不足以查看战斗是否有效。我们还需要进行一个小的“功能”测试，以查看它在实践中的效果。

这是我们进行最小测试所需的：

- 一个启用战斗的房间。
- 一个可以攻击的NPC（它还不会做任何反击，因为我们还没有添加任何AI）
- 一把我们可以`wield`的武器。
- 我们可以`use`的物品（如药水）。

```{sidebar}
你可以在`evennia/contrib/tutorials/evadventure/`中找到示例战斗批处理代码脚本，在[batchscripts/turnbased_combat_demo.py](github:evennia/contrib/tutorials/evadventure/batchscripts/turnbased_combat_demo.py)中
```

在[快速战斗课程](./Beginner-Tutorial-Combat-Twitch.md)中，我们使用了一个[批处理命令脚本](../../../Components/Batch-Command-Processor.md)在游戏中创建测试环境。这在游戏中按顺序运行Evennia命令。为了演示目的，我们将改用[批处理代码脚本](../../../Components/Batch-Code-Processor.md)，它以可重复的方式运行原始Python代码。批处理代码脚本比批处理命令脚本灵活得多。

> 创建一个新的子文件夹`evadventure/batchscripts/`（如果它尚不存在）

> 创建一个新的Python模块`evadventure/batchscripts/combat_demo.py`

批处理代码文件是一个有效的Python模块。唯一的区别是它有一个`# HEADER`块和一个或多个`# CODE`部分。当处理器运行时，`# HEADER`部分将添加到每个`# CODE`部分的顶部，然后在隔离的代码块中执行该代码块。由于你可以从游戏中运行文件（包括在不重新加载服务器的情况下刷新它），这使得能够按需运行较长的Python代码。

```python
# Evadventure（回合制）战斗演示 - 使用批处理代码文件。
#
# 设置一个战斗区域以测试回合制战斗。
#
# 首先添加到mygame/server/conf/settings.py：
#
#    BASE_BATCHPROCESS_PATHS += ["evadventure.batchscripts"]
#
# 从游戏中运行`batchcode turnbased_combat_demo`
#

# HEADER

from evennia import DefaultExit, create_object, search_object
from evennia.contrib.tutorials.evadventure.characters import EvAdventureCharacter
from evennia.contrib.tutorials.evadventure.combat_turnbased import TurnCombatCmdSet
from evennia.contrib.tutorials.evadventure.npcs import EvAdventureNPC
from evennia.contrib.tutorials.evadventure.rooms import EvAdventureRoom

# CODE

# 将玩家转换为EvadventureCharacter
player = caller  # caller由批处理代码运行器注入，它是运行此脚本的人 # E: undefined name 'caller'
player.swap_typeclass(EvAdventureCharacter)

# 添加回合制cmdset
player.cmdset.add(TurnCombatCmdSet, persistent=True)

# 创建一个武器和一个可以使用的物品
create_object(
    "contrib.tutorials.evadventure.objects.EvAdventureWeapon",
    key="Sword",
    location=player,
    attributes=[("desc", "A sword.")],
)

create_object(
    "contrib.tutorials.evadventure.objects.EvAdventureConsumable",
    key="Potion",
    location=player,
    attributes=[("desc", "A potion.")],
)

# 从limbo开始
limbo = search_object("#2")[0]

arena = create_object(EvAdventureRoom, key="Arena", attributes=[("desc", "A large arena.")])

# 创建出口
arena_exit = create_object(DefaultExit, key="Arena", location=limbo, destination=arena)
back_exit = create_object(DefaultExit, key="Back", location=arena, destination=limbo)

# 创建NPC假人
create_object(
    EvAdventureNPC,
    key="Dummy",
    location=arena,
    attributes=[("desc", "A training dummy."), ("hp", 1000), ("hp_max", 1000)],
)

```

如果在IDE中编辑此文件，你可能会在`player = caller`行上出现错误。这是因为`caller`在此文件中未定义。相反，`caller`（运行脚本的人）由`batchcode`运行器注入。

但除了`# HEADER`和`# CODE`特殊之外，这只是一些正常的Evennia api调用。

使用开发者/超级用户帐户登录游戏并运行

    > batchcmd evadventure.batchscripts.turnbased_combat_demo

这应该将你放置在竞技场中，那里有假人（如果没有，请检查输出中的错误！使用`objects`和`delete`命令列出和删除对象，如果需要重新开始。）

你现在可以尝试`attack dummy`，应该能够对假人进行攻击（降低其健康以测试摧毁它）。如果你需要修复某些东西，请使用`q`退出菜单并获得对`reload`命令的访问权限（对于最终战斗，你可以通过在创建`EvMenu`时传递`auto_quit=False`来禁用此功能）。

## 结论

到目前为止，我们已经涵盖了一些关于如何实现快速和回合制战斗系统的想法。在此过程中，你接触了许多概念，如类、脚本和处理器、命令、EvMenus等。

在我们的战斗系统实际可用之前，我们需要让我们的敌人进行反击。我们将在下一步中解决这个问题。
