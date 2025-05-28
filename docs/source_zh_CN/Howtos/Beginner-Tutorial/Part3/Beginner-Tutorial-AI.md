# NPC和怪物AI

```{sidebar} 人工智能听起来很复杂
"人工智能"这个词听起来很吓人。它让人联想到超级计算机、机器学习、神经网络和大型语言模型。但对于我们的使用场景，只需要几个if语句就可以实现看起来相当“智能”的效果。
```
游戏中并不是每个实体都由玩家控制。NPC和敌人需要由计算机控制——也就是说，我们需要给它们人工智能（AI）。

对于我们的游戏，我们将实现一种称为“状态机”的AI类型。这意味着实体（如NPC或怪物）始终处于某个“状态”。状态的例子可以是“闲置”、“漫游”或“攻击”。
在固定的时间间隔内，AI实体将由Evennia“触发”。这个“触发”开始于一个评估过程，该过程决定实体是否应该切换到另一个状态，或者停留在当前状态并执行一个（或多个）动作。

```{sidebar} 怪物和NPC
“怪物”是“移动”的缩写，是一个常见的MUD术语，指的是可以在房间之间移动的实体。这个术语通常用于攻击性敌人。怪物也是一个“NPC”（非玩家角色），但后者通常用于更和平的实体，如店主和任务发布者。
```

例如，如果一个处于“漫游”状态的怪物遇到一个玩家角色，它可能会切换到“攻击”状态。在战斗中，它可以在不同的战斗动作之间移动，如果它在战斗中幸存下来，它会回到“漫游”状态。

AI可以在不同的时间尺度上“触发”，这取决于你的游戏如何工作。例如，当怪物在移动时，它们可能每20秒自动从一个房间移动到另一个房间。但一旦进入回合制战斗（如果你使用的话），AI将仅在每个回合“触发”。

## 我们的需求

```{sidebar} 店主和任务发布者
在我们的游戏中，NPC店主和任务发布者将被假定始终处于“闲置”状态——与他们交谈或从他们那里购物的功能将在未来的课程中探索。
```

对于这个教程游戏，我们需要AI实体能够处于以下状态：

- _闲置_ - 什么也不做，只是站着。
- _漫游_ - 从一个房间移动到另一个房间。重要的是，我们需要添加限制AI可以漫游的能力。例如，如果我们有非战斗区域，我们希望能够[锁定](../../../Components/Locks.md)所有通往这些区域的出口，以防止攻击性怪物进入。
- _战斗_ - 发起并与玩家角色进行战斗。该状态将利用[战斗教程](./Beginner-Tutorial-Combat-Base.md)来随机选择战斗动作（适当地基于回合或触发）。
- _逃跑_ - 这类似于_漫游_，但AI将尽量避免进入有玩家角色的房间。

我们将这样组织AI代码：
- `AIHandler` 将作为一个处理器存储在AI实体上，名为`.ai`。它负责存储AI的状态。要“触发”AI，我们运行`.ai.run()`。我们将AI以这种方式运行的频率留给其他游戏系统。
- NPC/怪物类上的`.ai_<state_name>`方法 - 当调用`ai.run()`方法时，它负责找到一个与其当前状态命名相似的方法（例如，如果我们处于_战斗_状态，则为`.ai_combat`）。拥有这样的方法使得添加新状态变得容易——只需添加一个适当命名的新方法，AI现在就知道如何处理该状态！

## AIHandler

```{{sidebar}}
你可以在`evennia/contrib/tutorials`中找到一个实现的AIHandler，在[evadventure/tests/test_ai.py](evennia.contrib.tutorials.evadventure.ai)中。
```
这是管理AI状态的核心逻辑。创建一个新文件`evadventure/ai.py`。

> 创建一个新文件`evadventure/ai.py`。

```{code-block} python
:linenos: 
:emphasize-lines: 10,11-13,16,23
# 在 evadventure/ai.py 中

from evennia.logger import log_trace

class AIHandler:
    attribute_name = "ai_state"
    attribute_category = "ai_state"

    def __init__(self, obj):
        self.obj = obj
        self.ai_state = obj.attributes.get(self.attribute_name,
                                           category=self.attribute_category,
                                           default="idle")
    def set_state(self, state):
        self.ai_state = state
        self.obj.attributes.add(self.attribute_name, state, category=self.attribute_category)

    def get_state(self):
        return self.ai_state

    def run(self):
        try:
            state = self.get_state()
            getattr(self.obj, f"ai_{state}")()
        except Exception:
            log_trace(f"AI error in {self.obj.name} (running state: {state})")


```

AIHandler是一个[对象处理器](../../Tutorial-Persistent-Handler.md)的示例。这是一种将所有功能组合在一起的设计风格。稍微展望一下，这个处理器将被添加到对象中，如下所示：
```{sidebar} lazy_property
这是一个Evennia [@decorator](https://realpython.com/primer-on-python-decorators/)装饰器，它使得处理器不会在有人第一次尝试访问`obj.ai`之前初始化。在后续调用中，将返回已经初始化的处理器。当你有很多对象时，这是一种非常有用的性能优化，对处理器的功能也很重要。
```

```python
# 只是一个示例，暂时不要放在任何地方

from evennia.utils import lazy_property
from evadventure.ai import AIHandler 

class MyMob(SomeParent): 

    @lazy_property
    def ai(self): 
        return AIHandler(self)
```

简而言之，访问`.ai`属性将初始化`AIHandler`的一个实例，我们将`self`（当前对象）传递给它。在`AIHandler.__init__`中，我们接受这个输入并将其存储为`self.obj`（**第10-13行**）。这样，处理器可以通过访问`self.obj`始终对其“坐在”的实体进行操作。`lazy_property`确保这种初始化每次服务器重载只发生一次。

更多关键功能：

- **第11行**：我们通过访问`self.obj.attributes.get()`重新加载AI状态。这会加载一个具有给定名称和类别的数据库[属性](../../../Components/Attributes.md)。如果尚未保存，则返回“idle”。请注意，我们必须访问`self.obj`（NPC/怪物）因为那是唯一可以访问数据库的东西。
- **第16行**：在`set_state`方法中，我们强制处理器切换到给定状态。当我们这样做时，我们确保将其保存到数据库中，以便其状态在重载时得以保留。但我们也将其存储在`self.ai_state`中，因此我们不需要在每次获取时访问数据库。
- **第23行**：`getattr`函数是一个内置的Python函数，用于获取对象上的命名属性。这使我们能够根据当前状态调用在NPC/怪物上定义的方法`ai_<statename>`。我们必须将此调用包装在`try...except`块中，以正确处理AI方法中的错误。Evennia的`log_trace`将确保记录错误，包括其用于调试的回溯。

### AI处理器上的更多助手

在AIHandler上放置一些助手也很方便。这使得它们可以从`ai_<state>`方法中轻松调用，例如`self.ai.get_targets()`。

```{code-block} python
:linenos:
:emphasize-lines: 41,42,47,49
# 在 evadventure/ai.py 中

# ... 
import random

class AIHandler:

    # ...

    def get_targets(self):
        """
        获取NPC可以攻击的潜在目标列表。

        """
        return [obj for obj in self.obj.location.contents if hasattr(obj, "is_pc") and obj.is_pc]

    def get_traversable_exits(self, exclude_destination=None):
        """
        获取NPC可以穿越的出口列表。可选择排除某个目的地。
        
        参数：
            exclude_destination (Object, optional): 排除具有此目的地的出口。

        """
        return [
            exi
            for exi in self.obj.location.exits
            if exi.destination != exclude_destination and exi.access(self, "traverse")
        ]
    
    def random_probability(self, probabilities):
        """
        给定一个概率字典，返回所选概率的键。

        参数：
            probabilities (dict): 一个概率字典，其中键是动作，值是该动作的概率。

        """
        # 从高到低排序概率，确保将其标准化为0..1
        prob_total = sum(probabilities.values())
        sorted_probs = sorted(
            ((key, prob / prob_total) for key, prob in probabilities.items()),
            key=lambda x: x[1],
            reverse=True,
        )
        rand = random.random()
        total = 0
        for key, prob in sorted_probs:
            total += prob
            if rand <= total:
                return key
```

```{sidebar} 锁定出口
“traverse”锁是Evennia在允许某物通过出口之前检查的默认锁类型。由于只有PC具有`is_pc`属性，我们可以锁定出口以仅允许具有该属性的实体通过。

在游戏中：

    lock north = traverse:attr(is_pc, True)

或者在代码中：

    exit_obj.locks.add(
        "traverse:attr(is_pc, True)")

有关Evennia锁的更多信息，请参见[锁](../../../Components/Locks.md)。
```
- `get_targets`检查与当前对象在同一位置的其他对象是否具有`is_pc`属性。为了简单起见，我们假设怪物只会攻击玩家角色（没有怪物内斗！）。
- `get_traversable_exits`获取当前位置的所有有效出口，排除具有提供的目的地或未通过“traverse”访问检查的出口。
- `get_random_probability`接收一个字典`{action: probability, ...}`。这将随机选择一个动作，但概率越高，被选中的可能性就越大。我们将在稍后的战斗状态中使用它，以允许不同的战斗者更有可能执行不同的战斗动作。此算法使用了一些有用的Python工具：
    - **第41行**：记住`probabilities`是一个字典`{key: value, ...}`，其中值是概率。因此`probabilities.values()`为我们提供了一个仅包含概率的列表。在它们上运行`sum()`可以得到这些概率的总和。我们需要它来将所有概率标准化为0到1.0。
    - **第42-46行**：在这里，我们创建一个新的元组迭代器`(key, prob/prob_total)`。我们使用Python的`sorted`助手对它们进行排序。`key=lambda x: x[1]`表示我们根据每个元组的第二个元素（概率）进行排序。`reverse=True`表示我们将从最高概率到最低概率进行排序。
    - **第47行**：`random.random()`调用生成一个0到1之间的随机值。
    - **第49行**：由于概率从高到低排序，我们遍历它们，直到找到第一个符合随机值的概率——这就是我们要找的动作/键。
    - 举个例子，如果你有一个`probability`输入为`{"attack": 0.5, "defend": 0.1, "idle": 0.4}`，这将变成一个排序后的迭代器`(("attack", 0.5), ("idle", 0.4), ("defend": 0.1))`，如果`random.random()`返回0.65，结果将是“idle”。如果`random.random()`返回`0.90`，结果将是“defend”。也就是说，这个AI实体将有50%的时间攻击，40%的时间闲置，10%的时间防御。

## 向实体添加AI

我们需要做的就是在游戏实体上添加AI支持，添加AI处理器和一系列`.ai_statename()`方法到该对象的类型类。

我们已经在[NPC教程](Beginner-Tutorial_NPCs)中草绘了NPC和怪物类型类。打开`evadventure/npcs.py`并扩展目前为空的`EvAdventureMob`类。

```python
# 在 evadventure/npcs.py 中

# ... 

from evennia.utils import lazy_property 
from .ai import AIHandler

# ... 

class EvAdventureMob(EvAdventureNPC):

    @lazy_property
    def ai(self): 
        return AIHandler(self)

    def ai_idle(self): 
        pass 

    def ai_roam(self): 
        pass 

    def ai_roam(self): 
        pass 

    def ai_combat(self): 
        pass 

    def ai_flee(self):
        pass

```

所有剩余的逻辑都将进入每个状态方法中。

### 闲置状态

在闲置状态下，怪物什么也不做，所以我们只需将`ai_idle`方法保持原样——只需一个空的`pass`。这意味着它也不会攻击同一房间的玩家角色——但如果玩家角色攻击它，我们必须确保强制它进入战斗状态（否则它将毫无防备）。

### 漫游状态

在这个状态下，怪物应该从一个房间移动到另一个房间，直到找到玩家角色进行攻击。

```python
# 在 evadventure/npcs.py 中

# ... 

import random

class EvAdventureMob(EvAdventureNPC): 

    # ... 

    def ai_roam(self):
        """
        漫游，随机移动到一个新房间。如果找到目标，则切换到战斗状态。

        """
        if targets := self.ai.get_targets():
            self.ai.set_state("combat")
            self.execute_cmd(f"attack {random.choice(targets).key}")
        else:
            exits = self.ai.get_traversable_exits()
            if exits:
                exi = random.choice(exits)
                self.execute_cmd(f"{exi.key}")
```

每次AI被触发时，这个方法将被调用。它将首先检查房间中是否有任何有效目标（使用我们在`AIHandler`上创建的`get_targets()`助手）。如果有，我们切换到`combat`状态，并立即调用`attack`命令以发起/加入战斗（参见[战斗教程](./Beginner-Tutorial-Combat-Base.md)）。

如果没有找到目标，我们获取可穿越出口的列表（未通过“traverse”锁检查的出口已从此列表中排除）。使用Python的内置`random.choice`函数，我们从该列表中随机选择一个出口，并通过其名称移动。

### 逃跑状态

逃跑类似于_漫游_，但AI永远不会尝试攻击任何东西，并将确保不返回它来的路。

```python
# 在 evadventure/npcs.py 中

# ... 

class EvAdventureMob(EvAdventureNPC):

    # ... 

    def ai_flee(self):
        """
        从当前房间逃跑，避免返回到我们来的房间。如果没有找到出口，则切换到漫游状态。

        """
        current_room = self.location
        past_room = self.attributes.get("past_room", category="ai_state", default=None)
        exits = self.ai.get_traversable_exits(exclude_destination=past_room)
        if exits:
            self.attributes.set("past_room", current_room, category="ai_state")
            exi = random.choice(exits)
            self.execute_cmd(f"{exi.key}")
        else:
            # 如果在死胡同，漫游将允许退回
            self.ai.set_state("roam")

```

我们将`past_room`存储在自己身上的一个属性“past_room”中，并确保在尝试找到随机出口时排除它。

如果我们最终进入死胡同，我们切换到_漫游_模式，以便它可以退回（并且也开始再次攻击东西）。因此，这种效果是怪物将尽可能远地逃跑，直到“平静下来”。

### 战斗状态

在战斗状态下，怪物将使用我们设计的战斗系统之一（无论是[快速战斗](./Beginner-Tutorial-Combat-Twitch.md)还是[回合制战斗](./Beginner-Tutorial-Combat-Turnbased.md)）。这意味着每次AI被触发时，而我们处于战斗状态，实体需要执行一个可用的战斗动作，_保持_，_攻击_，_做特技_，_使用物品_或_逃跑_。

```{code-block} python
:linenos: 
:emphasize-lines: 7,22,24,25
# 在 evadventure/npcs.py 中

# ... 

class EvAdventureMob(EvAdventureNPC): 

    combat_probabilities = {
        "hold": 0.0,
        "attack": 0.85,
        "stunt": 0.05,
        "item": 0.0,
        "flee": 0.05,
    }

    # ... 

    def ai_combat(self):
        """
        管理怪物的战斗/战斗状态。

        """
        if combathandler := self.nbd.combathandler:
            # 已经在战斗中
            allies, enemies = combathandler.get_sides(self)
            action = self.ai.random_probability(self.combat_probabilities)

            match action:
                case "hold":
                    combathandler.queue_action({"key": "hold"})
                case "combat":
                    combathandler.queue_action({"key": "attack", "target": random.choice(enemies)})
                case "stunt":
                    # 选择一个随机盟友来帮助
                    combathandler.queue_action(
                        {
                            "key": "stunt",
                            "recipient": random.choice(allies),
                            "advantage": True,
                            "stunt": Ability.STR,
                            "defense": Ability.DEX,
                        }
                    )
                case "item":
                    # 对随机盟友使用随机物品
                    target = random.choice(allies)
                    valid_items = [item for item in self.contents if item.at_pre_use(self, target)]
                    combathandler.queue_action(
                        {"key": "item", "item": random.choice(valid_items), "target": target}
                    )
                case "flee":
                    self.ai.set_state("flee")

        elif not (targets := self.ai.get_targets()):
            self.ai.set_state("roam")
        else:
            target = random.choice(targets)
            self.execute_cmd(f"attack {target.key}")

```

- **第7-13行**：此字典描述了怪物执行给定战斗动作的可能性。通过只修改这个字典，我们可以轻松创建行为非常不同的怪物，比如更频繁地使用物品或更倾向于逃跑。你也可以完全关闭某些动作——默认情况下，这个怪物从不“保持”或“使用物品”。
- **第22行**：如果我们在战斗中，`CombadHandler`应该在我们身上初始化，作为`self.ndb.combathandler`可用（参见[基础战斗教程](./Beginner-Tutorial-Combat-Base.md)）。
- **第24行**：`combathandler.get_sides()`为传递给它的对象生成盟友和敌人。
- **第25行**：现在我们之前在本课程中创建的`random_probability`方法变得很方便！

此方法的其余部分只是获取随机选择的动作，并执行所需的操作以将其排队为`CombatHandler`的新动作。为了简单起见，我们只使用特技来增强我们的盟友，而不是阻碍我们的敌人。

最后，如果我们当前不在战斗中，并且附近没有敌人，我们切换到漫游——否则我们开始另一场战斗！

## 单元测试

```{{sidebar}}
在[evennia/contrib/tutorials/tests/test_ai.py](evennia.contrib.tutorials.evadventure.tests.test_ai)中找到AI测试的示例。
```
> 创建一个新文件`evadventure/tests/test_ai.py`。

如果你已经跟随之前的课程，测试AI处理器和怪物是很简单的。创建一个`EvAdventureMob`并测试调用其上的各种与ai相关的方法和处理器是否按预期工作。一个复杂之处是模拟`random`的输出，以便你总是得到相同的随机结果进行比较。我们将AI测试的实现留给读者作为额外的练习。

## 结论

你可以轻松扩展这个简单的系统，使怪物更“聪明”。例如，怪物可以在战斗中考虑更多因素，而不是仅仅随机决定采取哪种行动——也许一些支持怪物可以使用特技为他们的重击手铺平道路，或者在受伤严重时使用治疗药水。

添加一个“追踪”状态也很简单，在这个状态下，怪物会在移动到相邻房间之前检查目标。

虽然实现一个功能齐全的游戏AI系统不需要高级数学或机器学习技术，但如果你真的想要的话，当然可以添加各种高级功能！
