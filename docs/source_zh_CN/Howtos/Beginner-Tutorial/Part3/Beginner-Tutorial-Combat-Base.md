# 战斗基础框架

战斗是许多游戏的核心。具体的运作方式非常依赖于游戏本身。在本课中，我们将构建一个框架来实现两种常见的风格：

- “Twitch-based”战斗（[具体课程在这里](./Beginner-Tutorial-Combat-Twitch.md)）意味着你通过输入命令来执行战斗动作，并在一些延迟后（可能取决于你的技能等）动作发生。之所以称为“twitch”，是因为动作通常发生得足够快，以至于改变策略可能涉及快速思考和“快速反应”。 
- “Turn-based”战斗（[具体课程在这里](./Beginner-Tutorial-Combat-Turnbased.md)）意味着玩家在明确的回合中输入动作。输入/排队动作的超时时间通常比twitch-based风格长得多。一旦每个人都做出了选择（或达到了超时），所有人的动作都会同时发生，然后下一回合开始。这种战斗风格对玩家的反应要求较低。

我们将设计一个支持这两种风格的基础战斗系统。

- 我们需要一个`CombatHandler`来跟踪战斗的进展。这将是一个[脚本](../../../Components/Scripts.md)。它的具体工作方式（以及存储位置）在Twitch和Turnbased战斗之间会有所不同。我们将在本课中创建其通用框架。
- 战斗分为_动作_。我们希望能够轻松扩展我们的战斗以实现更多可能的动作。动作需要Python代码来展示执行动作时实际发生的事情。我们将在`Action`类中定义此类代码。
- 我们还需要一种方法来描述给定动作的_特定实例_。也就是说，当我们执行“攻击”动作时，我们至少需要知道谁正在被攻击。为此，我们将使用Python `dict`，我们将其称为`action_dicts`。

## CombatHandler

> 创建一个新模块`evadventure/combat_base.py`

```{sidebar}
在`evennia/contrib/tutorials/evadventure/`下，[combat_base.py](evennia.contrib.tutorials.evadventure.combat_base)中可以找到基础战斗模块的完整实现。
```

我们的“战斗处理器”将处理战斗相关的管理。它需要是_持久的_（即使我们重新加载服务器，你的战斗也应该继续进行）。

创建CombatHandler有点像鸡生蛋的问题——它的工作方式取决于动作和动作字典的样子。但没有CombatHandler，很难知道如何设计动作和动作字典。因此，我们将从其一般结构开始，并在本课中填写细节。

下面，带有`pass`的方法将在本课中填写，而那些引发`NotImplementedError`的方法将在后续的Twitch/Turnbased战斗课程中实现。

```python
# 在 evadventure/combat_base.py 中

from evennia import DefaultScript


class CombatFailure(RuntimeError):
    """如果战斗中发生错误"""
    pass


class EvAdventureCombatBaseHandler(DefaultScript):
    """
    这应该在战斗开始时创建。它“滴答”战斗并跟踪所有方面。
    
    """
    # 所有类型战斗的通用部分

    action_classes = {}          # 稍后填写
    fallback_action_dict = {}

    @classmethod
    def get_or_create_combathandler(cls, obj, **kwargs):
        """ 获取或创建`obj`上的战斗处理器。"""
        pass

    def msg(self, message, combatant=None, broadcast=True, location=True):
        """
        向所有战斗者发送消息。
        
        """
        pass  # TODO
     
    def get_combat_summary(self, combatant):
        """
        从战斗者的角度获取格式良好的“战斗报告”。
        
        """
        pass  # TODO

    # 由Twitch和Turnbased战斗分别实现

    def get_sides(self, combatant):
        """
        获取战斗双方的存活者，作为一个元组`([盟友], [敌人])`，从`combatant`的角度看
        （`allies`列表中不包括自己）。
        
        """
        raise NotImplementedError

    def give_advantage(self, recipient, target):
        """
        给接收者对目标的优势。
        
        """
        raise NotImplementedError

    def give_disadvantage(self, recipient, target):
        """
        给接收者对目标的劣势。

        """
        raise NotImplementedError

    def has_advantage(self, combatant, target):
        """
        战斗者是否对目标有优势？
        
        """
        raise NotImplementedError

    def has_disadvantage(self, combatant, target):
        """
        战斗者是否对目标有劣势？
        
        """
        raise NotImplementedError

    def queue_action(self, combatant, action_dict):
        """
        通过提供动作字典为战斗者排队动作。
        
        """
        raise NotImplementedError

    def execute_next_action(self, combatant):
        """
        执行战斗者的下一个动作。
        
        """
        raise NotImplementedError

    def start_combat(self):
        """
        开始战斗。
        
        """
        raise NotImplementedError
    
    def check_stop_combat(self):
        """
        检查战斗是否结束以及是否应停止。
         
        """
        raise NotImplementedError
        
    def stop_combat(self):
        """
        停止战斗并进行清理。
        
        """
        raise NotImplementedError
```

战斗处理器是一个[脚本](../../../Components/Scripts.md)。脚本是类型化的实体，这意味着它们持久地存储在数据库中。脚本可以选择性地存储在其他对象上（例如角色或房间上）或是“全局的”而没有任何此类连接。虽然脚本有一个可选的计时器组件，但默认情况下它不活跃，脚本通常仅用作简单存储。由于脚本没有游戏内的存在，它们非常适合存储各种“系统”的数据，包括我们的战斗。

让我们实现我们需要的通用方法。

### CombatHandler.get_or_create_combathandler

一个用于快速获取正在进行的战斗和战斗者的战斗处理器的辅助方法。

我们期望在一个对象上创建脚本（具体是哪个我们还不知道，但我们期望它是一个类型化的实体）。

```python
# 在 evadventure/combat_base.py 中

from evennia import create_script

# ...

class EvAdventureCombatBaseHandler(DefaultScript):

    # ...

    @classmethod
    def get_or_create_combathandler(cls, obj, **kwargs):
        """
        获取或创建`obj`上的战斗处理器。
    
        参数：
            obj (any): 存储此脚本的类型化实体。
        关键字参数：
            combathandler_key (str): 脚本的标识符。默认为'combathandler'。
            **kwargs: 如果创建脚本则传递的额外参数。
    
        """
        if not obj:
            raise CombatFailure("没有地方进行战斗，无法开始战斗！")
    
        combathandler_key = kwargs.pop("key", "combathandler")
        combathandler = obj.ndb.combathandler
        if not combathandler or not combathandler.id:
            combathandler = obj.scripts.get(combathandler_key).first()
            if not combathandler:
                # 必须从头创建
                persistent = kwargs.pop("persistent", True)
                combathandler = create_script(
                    cls,
                    key=combathandler_key,
                    obj=obj,
                    persistent=persistent,
                    **kwargs,
                )
            obj.ndb.combathandler = combathandler
        return combathandler

    # ...
```

这个辅助方法使用`obj.scripts.get()`来查找战斗脚本是否已经存在于提供的`obj`上。如果没有，它将使用Evennia的[create_script](evennia.utils.create.create_script)函数创建它。为了提高速度，我们将处理器缓存为`obj.ndb.combathandler`。`.ndb.`（非数据库）表示处理器仅在内存中缓存。

```{sidebar} 检查.id（或.pk）
从缓存中获取它时，我们确保还检查我们获得的combathandler是否具有不为`None`的数据库`.id`（我们也可以检查`.pk`，表示“主键”）。如果它为`None`，这意味着数据库实体已被删除，我们只是从内存中获得了其缓存的python表示——我们需要重新创建它。
```

`get_or_create_combathandler`被装饰为一个[classmethod](https://docs.python.org/3/library/functions.html#classmethod)，这意味着它应该直接在处理器类上使用（而不是在该类的_实例_上）。这很有意义，因为此方法实际上应该返回新的实例。

作为类方法，我们需要直接在类上调用它，如下所示：

```python
combathandler = EvAdventureCombatBaseHandler.get_or_create_combathandler(combatant)
```

结果将是一个新的处理器_或_已经定义的处理器。

### CombatHandler.msg

```python
# 在 evadventure/combat_base.py 中

# ...

class EvAdventureCombatBaseHandler(DefaultScript):
    # ...

    def msg(self, message, combatant=None, broadcast=True, location=None):
        """
        向战斗者发送消息的中心位置。这允许在一个地方添加任何战斗特定的文本装饰。

        参数：
            message (str): 要发送的消息。
            combatant (Object): 消息中的“你”，如果有的话。
            broadcast (bool): 如果为`False`，则必须包含`combatant`，并且将是唯一看到消息的人。如果为`True`，则发送给位置中的所有人。
            location (Object, optional): 如果给定，则使用此作为发送广播消息的位置。如果没有，则使用`self.obj`作为该位置。

        注意：
            如果给定`combatant`，则使用`$You/you()`标记创建一个根据看到它的人不同而看起来不同的消息。使用`$You(combatant_key)`来指代其他战斗者。

        """
        if not location:
            location = self.obj

        location_objs = location.contents

        exclude = []
        if not broadcast and combatant:
            exclude = [obj for obj in location_objs if obj is not combatant]

        location.msg_contents(
            message,
            exclude=exclude,
            from_obj=combatant,
            mapping={locobj.key: locobj for locobj in location_objs},
        )

    # ...
```

```{sidebar}
脚本的`self.obj`属性是脚本“坐在”其上的实体。如果设置在角色上，`self.obj`将是该角色。如果在房间上，它将是该房间。对于全局脚本，`self.obj`为`None`。
```

我们在[对象课程的武器类](./Beginner-Tutorial-Objects.md#weapons)中见过`location.msg_contents()`方法。它的目的是获取一个形如`"$You() do stuff against $you(key)"`的字符串，并确保所有方面看到适合他们的字符串。我们的`msg()`方法默认会将消息广播给房间中的所有人。

你可以这样使用它：

```python
combathandler.msg(
    f"$You() $conj(throw) {item.key} at $you({target.key}).",
    combatant=combatant,
    location=combatant.location
)
```

如果战斗者是`Trickster`，`item.key`是“a colorful ball”且`target.key`是“Goblin”，那么

战斗者将看到：

```
You throw a colorful ball at Goblin.
```

Goblin看到：

```
Trickster throws a colorful ball at you.
```

房间中的其他人看到：

```
Trickster throws a colorful ball at Goblin.
```

### Combathandler.get_combat_summary

我们希望能够显示当前战斗的漂亮总结：

```shell
                                        Goblin shaman (Perfect)
        Gregor (Hurt)                   Goblin brawler(Hurt)
        Bob (Perfect)         vs        Goblin grunt 1 (Hurt)
                                        Goblin grunt 2 (Perfect)
                                        Goblin grunt 3 (Wounded)
```

```{code-block} python
:linenos:
:emphasize-lines: 15,17,21,22,28,41

# 在 evadventure/combat_base.py 中

# ...

from evennia import EvTable

# ...

class EvAdventureCombatBaseHandler(DefaultScript):

    # ...

    def get_combat_summary(self, combatant):

        allies, enemies = self.get_sides(combatant)
        nallies, nenemies = len(allies), len(enemies)

        # 准备颜色和受伤级别
        allies = [f"{ally} ({ally.hurt_level})" for ally in allies]
        enemies = [f"{enemy} ({enemy.hurt_level})" for enemy in enemies]

        # 带有“vs”的中间列
        vs_column = ["" for _ in range(max(nallies, nenemies))]
        vs_column[len(vs_column) // 2] = "|wvs|n"

        # 两个盟友/敌人列应垂直居中
        diff = abs(nallies - nenemies)
        top_empty = diff // 2
        bot_empty = diff - top_empty
        topfill = ["" for _ in range(top_empty)]
        botfill = ["" for _ in range(bot_empty)]

        if nallies >= nenemies:
            enemies = topfill + enemies + botfill
        else:
            allies = topfill + allies + botfill

        # 制作一个三列的表
        return evtable.EvTable(
            table=[
                evtable.EvColumn(*allies, align="l"),
                evtable.EvColumn(*vs_column, align="c"),
                evtable.EvColumn(*enemies, align="r"),
            ],
            border=None,
            maxwidth=78,
        )

    # ...
```

这可能看起来很复杂，但复杂性仅在于如何组织三列，特别是如何调整`vs`两侧的两边大致垂直对齐。

- **第15行**：我们利用`self.get_sides(combatant)`方法，虽然我们还没有实现它。这是因为回合制和twitch-based战斗将需要不同的方法来找出双方。`allies`和`enemies`是列表。
- **第17行**：`combatant`不在`allies`列表中（这是我们定义`get_sides`的方式），所以我们将其插入列表顶部（这样他们会首先显示在左侧）。
- **第21和22行**：我们利用所有生物的`.hurt_level`值（参见[角色课程的LivingMixin](./Beginner-Tutorial-Characters.md)）。
- **第28-39行**：通过在内容上方和下方添加空行来确定如何垂直居中两侧。
- **第41行**：[Evtable](../../../Components/EvTable.md)是一个Evennia实用工具，用于制作文本表格。一旦我们对列满意，我们将它们提供给表并让Evennia完成其余工作。值得探索`EvTable`，因为它可以帮助你创建各种漂亮的布局。

## 动作

在EvAdventure中，我们将仅支持一些常见的战斗动作，映射到_Knave_中使用的等效掷骰和检查。我们将设计我们的战斗框架，以便以后可以轻松扩展其他动作。

- `hold` - 最简单的动作。你只是靠在后面，什么也不做。
- `attack` - 你使用当前装备的武器攻击给定的`target`。这将成为对目标ARMOR的STR或WIS掷骰。
- `stunt` - 你进行“特技”，在角色扮演术语中，这意味着你绊倒对手、嘲讽或以其他方式试图在不伤害他们的情况下获得上风。你可以这样做以在下一次行动中为自己（或盟友）对`target`提供_优势_。你还可以在他们的下一次行动中为`target`提供_劣势_。
- `use item` - 你使用你库存中的`Consumable`。当用于自己时，通常是治疗药水。如果用于敌人，可能是火焰炸弹或酸瓶。
- `wield` - 你装备一个物品。根据装备的物品不同，它将以不同的方式装备：头盔将放在头上，盔甲放在胸部。剑将用一只手装备，盾牌用另一只手。双手斧将占用两只手。这样做会将之前的物品移到背包中。
- `flee` - 你逃跑/脱离。这一动作仅适用于回合制战斗（在twitch-based战斗中，你只需移动到另一个房间即可逃跑）。因此，我们将在[回合制战斗课程](./Beginner-Tutorial-Combat-Turnbased.md)中定义此动作。

## 动作字典

为了传递攻击的细节（上面的第二点），我们将使用一个`dict`。`dict`简单且易于保存在`Attribute`中。我们将其称为`action_dict`，以下是我们对每个动作的需求。

> 你不需要在任何地方输入这些内容，这里列出的是供参考。我们将在调用`combathandler.queue_action(combatant, action_dict)`时使用这些字典。

```python
hold_action_dict = {
    "key": "hold"
}
attack_action_dict = {
    "key": "attack",
    "target": <Character/NPC>
}
stunt_action_dict = {
    "key": "stunt",
    "recipient": <Character/NPC>, # 谁获得优势/劣势
    "target": <Character/NPC>,  # 接收者对谁获得优势/劣势
    "advantage": bool,  # 授予优势还是劣势？
    "stunt_type": Ability,   # 用于挑战的能力
    "defense_type": Ability, # 如果我们试图给予劣势，接收者用来防御的能力
}
use_item_action_dict = {
    "key": "use",
    "item": <Object>
    "target": <Character/NPC/None> # 如果对其他人使用物品
}
wield_action_dict = {
    "key": "wield",
    "item": <Object>
}

# 仅用于回合制战斗，因此其动作将在那里定义
flee_action_dict = {
    "key": "flee"
}
```

除了`stunt`动作，这些字典都很简单。`key`标识要执行的动作，其他字段标识解决每个动作所需的最小内容。

我们尚未编写设置这些字典的代码，但我们将假设我们知道谁在执行每个动作。因此，如果`Beowulf`攻击`Grendel`，Beowulf本身不会包含在攻击字典中：

```python
attack_action_dict = {
    "key": "attack",
    "target": Grendel
}
```

让我们更详细地解释最长的动作字典`Stunt`动作字典。在这个例子中，`Trickster`正在执行一个_特技_，以帮助他的朋友`Paladin`在`Goblin`上获得INT-_优势_（也许圣骑士正在准备施法）。由于`Trickster`正在执行动作，他不会出现在字典中：

```python
stunt_action_dict = {
    "key": "stunt",
    "recipient": Paladin,
    "target": Goblin,
    "advantage": True,
    "stunt_type": Ability.INT,
    "defense_type": Ability.INT,
}
```

```{sidebar}
在EvAdventure中，我们将始终设置`stunt_type == defense_type`以简化。但你也可以考虑混合使用，以便你可以使用DEX迷惑某人并给他们INT劣势，例如。
```

这应该导致`Trickster`和`Goblin`之间基于INT vs INT的检查（也许Trickster试图通过一些巧妙的文字游戏来迷惑Goblin）。如果`Trickster`获胜，`Paladin`在`Paladin`的下一次行动中对Goblin获得优势。

## 动作类

一旦我们的`action_dict`确定了我们应该使用的特定动作，我们需要一些东西来读取这些键/值并实际_执行_动作。

```python
# 在 evadventure/combat_base.py 中

class CombatAction:

    def __init__(self, combathandler, combatant, action_dict):
        self.combathandler = combathandler
        self.combatant = combatant

        for key, val in action_dict.items():
            if key.startswith("_"):
                setattr(self, key, val)
```

我们将在每次发生动作时创建此类的新实例。因此，我们存储了一些每个动作都需要的关键内容——我们需要对公共`combathandler`的引用（我们将在下一节中设计），以及对`combatant`的引用（执行此动作的人）。`action_dict`是一个与我们要执行的动作匹配的字典。

Python标准函数`setattr`将`action_dict`的键/值分配为此动作的属性。这在其他方法中使用非常方便。因此，对于`stunt`动作，其他方法可以直接访问`self.key`、`self.recipient`、`self.target`等。

```python
# 在 evadventure/combat_base.py 中

class CombatAction:

    # ...

    def msg(self, message, broadcast=True):
        "向战斗中的其他人发送消息"
        self.combathandler.msg(message, combatant=self.combatant, broadcast=broadcast)

    def can_use(self):
        """如果战斗者现在不能使用此动作，则返回False"""
        return True

    def execute(self):
        """执行实际动作"""
        pass

    def post_execute(self):
        """在`execute`之后调用"""
        pass
```

在战斗中向每个人发送消息是_非常_常见的——你需要告诉人们他们正在被攻击，如果他们受伤等等。因此，在动作上有一个`msg`助手方法是很方便的。我们将所有复杂性卸载到combathandler.msg()方法中。

`can_use`、`execute`和`post_execute`应该都被调用，并且我们应该确保`combathandler`像这样调用它们：

```python
if action.can_use():
    action.execute()
    action.post_execute()
```

### Hold Action

```python
# 在 evadventure/combat_base.py 中

# ...

class CombatActionHold(CombatAction):
    """
    什么也不做的动作
    
    action_dict = {
        "key": "hold"
    }
    
    """
```

Hold动作什么也不做，但无论如何有一个单独的类会更清晰。我们使用文档字符串来指定其动作字典的样子。

### Attack Action

```python
# 在 evadventure/combat_base.py 中

# ...

class CombatActionAttack(CombatAction):
     """
     使用已装备武器的常规攻击。
 
     action-dict = {
             "key": "attack",
             "target": Character/Object
         }
 
     """
 
     def execute(self):
         attacker = self.combatant
         weapon = attacker.weapon
         target = self.target
 
         if weapon.at_pre_use(attacker, target):
             weapon.use(
                 attacker, target, advantage=self.combathandler.has_advantage(attacker, target)
             )
             weapon.at_post_use(attacker, target)
```

参考我们[设计Evadventure武器](./Beginner-Tutorial-Objects.md#weapons)的方式，以了解这里发生了什么——大部分工作由武器类完成——我们只需插入相关参数。

### Stunt Action

```python
# 在 evadventure/combat_base.py 中

# ...

class CombatActionStunt(CombatAction):
    """
    执行一个特技，使受益者（可以是自己）在他们对目标的下一次行动中获得优势。每当执行一个特技会对另一个人产生负面影响时（给予他们对盟友的劣势，或对他们授予优势），我们需要先进行检查。如果给予盟友或自己优势，我们不进行检查。

    action_dict = {
           "key": "stunt",
           "recipient": Character/NPC,
           "target": Character/NPC,
           "advantage": bool,  # 如果为False，则为劣势
           "stunt_type": Ability,  # 用于执行此特技的能力（如STR、DEX等）。
           "defense_type": Ability, # 用于防御此特技负面效果的能力。
        }

    """

    def execute(self):
        combathandler = self.combathandler
        attacker = self.combatant
        recipient = self.recipient  # 接收特技效果的人
        target = self.target  # 被特技影响的人（可以与接收者/战斗者相同）
        txt = ""

        if recipient == target:
            # 授予另一个实体对自己的优势/劣势
            defender = recipient
        else:
            # 接收者与目标不同；谁将防御取决于要给予的劣势或优势。
            defender = target if self.advantage else recipient

        # 尝试给予接收者对目标的优势。目标对调用者进行防御
        is_success, _, txt = rules.dice.opposed_saving_throw(
            attacker,
            defender,
            attack_type=self.stunt_type,
            defense_type=self.defense_type,
            advantage=combathandler.has_advantage(attacker, defender),
            disadvantage=combathandler.has_disadvantage(attacker, defender),
        )

        self.msg(f"$You() $conj(attempt) stunt on $You({defender.key}). {txt}")

        # 处理结果
        if is_success:
            if self.advantage:
                combathandler.give_advantage(recipient, target)
            else:
                combathandler.give_disadvantage(recipient, target)
            if recipient == self.combatant:
                self.msg(
                    f"$You() $conj(gain) {'advantage' if self.advantage else 'disadvantage'} "
                    f"against $You({target.key})!"
                )
            else:
                self.msg(
                    f"$You() $conj(cause) $You({recipient.key}) "
                    f"to gain {'advantage' if self.advantage else 'disadvantage'} "
                    f"against $You({target.key})!"
                )
            self.msg(
                "|yHaving succeeded, you hold back to plan your next move.|n [hold]",
                broadcast=False,
            )
        else:
            self.msg(f"$You({defender.key}) $conj(resist)! $You() $conj(fail) the stunt.")
```

这里的主要动作是调用`rules.dice.opposed_saving_throw`来确定特技是否成功。在那之后，大多数行是关于确定谁应该获得优势/劣势以及向受影响方传达结果。

请注意，我们在这里大量使用了`combathandler`上的助手方法，即使是那些尚未实现的方法。只要我们将`action_dict`传递给`combathandler`，动作实际上并不关心接下来会发生什么。

在我们成功执行特技之后，我们排队`combathandler.fallback_action_dict`。这是因为特技旨在是一次性的事情，如果我们重复动作，反复执行特技将没有意义。

### Use Item Action

```python
# 在 evadventure/combat_base.py 中

# ...

class CombatActionUseItem(CombatAction):
    """
    在战斗中使用物品。这是为一次性或有限使用的物品设计的（因此像卷轴和药水这样的东西，而不是剑和盾牌）。如果这是某种武器或法术符文，我们参考物品来确定用于攻击/防御掷骰的内容。

    action_dict = {
            "key": "use",
            "item": Object
            "target": Character/NPC/Object/None
        }

    """

    def execute(self):
        item = self.item
        user = self.combatant
        target = self.target

        if item.at_pre_use(user, target):
            item.use(
                user,
                target,
                advantage=self.combathandler.has_advantage(user, target),
                disadvantage=self.combathandler.has_disadvantage(user, target),
            )
            item.at_post_use(user, target)
```

请参见[对象课程中的消耗品](./Beginner-Tutorial-Objects.md)，以了解消耗品的工作原理。与武器一样，我们将所有逻辑卸载到我们使用的物品上。

### Wield Action

```python
# 在 evadventure/combat_base.py 中

# ...

class CombatActionWield(CombatAction):
    """
    从你的库存中装备新武器（或法术）。这将替换你当前装备的物品（如果有的话）。

    action_dict = {
            "key": "wield",
            "item": Object
        }

    """

    def execute(self):
        self.combatant.equipment.move(self.item)
```

我们依赖于我们创建的[装备处理器](./Beginner-Tutorial-Equipment.md)来为我们处理物品的交换。由于不断交换没有意义，我们在此之后排队后备动作。

## 测试

> 创建一个模块`evadventure/tests/test_combat.py`。

```{sidebar}
在`evennia/contrib/tutorials/evadventure/`下，[tests/test_combat.py](evennia.contrib.tutorials.evadventure.tests.test_combat)中可以找到现成的战斗单元测试。
```

对战斗基础类进行单元测试似乎是不可能的，因为我们尚未实现大部分内容。然而，通过使用[Mocks](https://docs.python.org/3/library/unittest.mock.html)可以走得很远。Mock的想法是你用一个虚拟对象（“mock”）_替换_一段代码，该对象可以被调用以返回一些特定值。

例如，考虑以下对`CombatHandler.get_combat_summary`的测试。我们不能直接调用它，因为它内部调用`.get_sides`，这将引发`NotImplementedError`。

```{code-block} python
:linenos:
:emphasize-lines: 25,32

# 在 evadventure/tests/test_combat.py 中

from unittest.mock import Mock

from evennia.utils.test_resources import EvenniaTestCase
from evennia import create_object
from .. import combat_base
from ..rooms import EvAdventureRoom
from ..characters import EvAdventureCharacter


class TestEvAdventureCombatBaseHandler(EvenniaTestCase):

    def setUp(self):

        self.location = create_object(EvAdventureRoom, key="testroom")
        self.combatant = create_object(EvAdventureCharacter, key="testchar")
        self.target = create_object(EvAdventureMob, key="testmonster")

        self.combathandler = combat_base.get_combat_summary(self.location)

    def test_get_combat_summary(self):

        # 从战斗者的角度进行测试
        self.combathandler.get_sides = Mock(return_value=([], [self.target]))
        result = str(self.combathandler.get_combat_summary(self.combatant))
        self.assertEqual(
            result,
            " testchar (Perfect)  vs  testmonster (Perfect)"
        )
        # 从怪物的角度进行测试
        self.combathandler.get_sides = Mock(return_value=([], [self.combatant]))
        result = str(self.combathandler.get_combat_summary(self.target))
        self.assertEqual(
            result,
            " testmonster (Perfect)  vs  testchar (Perfect)"
        )
```

有趣的地方是我们应用mock的地方：

- **第25行**和**第32行**：虽然`get_sides`尚未实现，但我们知道它_应该_返回什么——一个列表的元组。因此，为了测试的目的，我们用一个mock替换`get_sides`方法，当调用时将返回一些有用的东西。

通过这种方法，即使系统尚未“完整”，也可以完全测试它。

## 结论

我们为我们的战斗系统提供了核心功能！在接下来的两节课中，我们将利用这些构建块来创建两种风格的战斗。
