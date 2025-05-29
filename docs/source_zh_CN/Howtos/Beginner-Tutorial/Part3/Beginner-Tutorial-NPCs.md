# 非玩家角色 (NPCs)

```{sidebar} vNPCs
通常你应该避免创建数百个 NPC 对象来填充你“繁忙的城镇”——在文本游戏中，过多的 NPC 会使屏幕充斥信息，惹恼玩家。由于这是一个文本游戏，你通常可以通过使用 _vNPCs_（虚拟 NPC）来解决这个问题。vNPC 仅以文本形式描述——房间可以描述为一条热闹的街道，农民可以被描述为互相高声呼喊。使用房间描述来实现这一点效果良好，但关于[EvAdventure 房间](./Beginner-Tutorial-Rooms.md)的教程中，有一节提到[为房间增加生命](./Beginner-Tutorial-Rooms.md#adding-life-to-a-room)，可以用来让 vNPC 在背景中显得忙碌。
```

_Non-Player-Characters_，或 NPC，是指所有_不_由玩家控制的活动代理。NPC 可以是商人、任务给予者、怪物和首领。它们也可以是“调味”的角色——镇上居民在做家务，农民在耕作——目的是让世界感觉“更有生命”。

在本课中，我们将根据 _Knave_ 规则集创建 _EvAdventure_ NPC 的基础类。根据 _Knave_ 规则，NPC 的某些简化属性与我们之前设计的 [PC 角色](./Beginner-Tutorial-Characters.md) 相比更为简单。

## NPC 基类

```{sidebar}
请查看 [evennia/contrib/tutorials/evadventure/npcs.py](evennia.contrib.tutorials.evadventure.npcs) 获取现成的 NPC 模块示例。
```
> 创建新模块 `evadventure/npcs.py`。

```python
# in evadventure/npcs.py 

from evennia import DefaultCharacter, AttributeProperty
from .characters import LivingMixin
from .enums import Ability
from .objects import get_bare_hands

class EvAdventureNPC(LivingMixin, DefaultCharacter): 
    """NPC 的基类""" 

    is_pc = False
    hit_dice = AttributeProperty(default=1, autocreate=False)
    armor = AttributeProperty(default=1, autocreate=False)  # +10 来计算防御
    hp_multiplier = AttributeProperty(default=4, autocreate=False)  # Knave 默认值为 4
    hp = AttributeProperty(default=None, autocreate=False)  # 内部跟踪，使用 .hp 属性
    morale = AttributeProperty(default=9, autocreate=False)
    allegiance = AttributeProperty(default=Ability.ALLEGIANCE_HOSTILE, autocreate=False)

    weapon = AttributeProperty(default=get_bare_hands, autocreate=False)  # 代替装备系统
    coins = AttributeProperty(default=1, autocreate=False)  # 硬币掉落
 
    is_idle = AttributeProperty(default=False, autocreate=False)
    
    @property
    def strength(self):
        return self.hit_dice
        
    @property
    def dexterity(self):
        return self.hit_dice
 
    @property
    def constitution(self):
        return self.hit_dice
 
    @property
    def intelligence(self):
        return self.hit_dice
 
    @property
    def wisdom(self):
        return self.hit_dice
 
    @property
    def charisma(self):
        return self.hit_dice
 
    @property
    def hp_max(self):
        return self.hit_dice * self.hp_multiplier
    
    def at_object_creation(self):
        """
        初始时具有最大生命值。
        """
        self.hp = self.hp_max
        self.tags.add("npcs", category="group")


class EvAdventureMob(EvAdventureNPC): 
    """
    Mob(ile) NPC 用于作为敌人。
    """
```

- **第 9 行**：通过使用 _多重继承_，我们使用了[在角色课程中](./Beginner-Tutorial-Characters.md)创建的 `LivingMixin`。这包含了许多有用的方法，例如显示“受伤程度”、治愈方法、被攻击时调用的 hooks 等。我们可以在即将到来的 NPC 子类中重用所有这些方法。
- **第 12 行**：`is_pc` 是一种快速方便的方式来检查这个角色是否是玩家角色。我们将在接下来的[基础战斗课程](./Beginner-Tutorial-Combat-Base.md)中使用它。
- **第 13 行**：NPC 被简化为所有属性都仅基于 `Hit dice` 数字（见 **第 25-51 行**）。我们将 `armor` 和 `weapon` 作为类的直接 [Attributes](../../../Components/Attributes.md) 存储，而不是实施完整的装备系统。
- **第 17、18 行**：`morale` 和 `allegiance` 是 _Knave_ 属性，用于确定 NPC 在战斗情况下逃跑的可能性以及他们是敌对还是友好的。
- **第 19 行**：`is_idle` 属性是一个有用的属性。它应该在所有 NPC 中可用，并将用于完全禁用 AI。
- **第 59 行**：我们确保对 NPC 进行标记。我们可能希望稍后将不同的 NPC 分组，例如让所有带有相同标签的 NPC 在其中一个 NPC 被攻击时做出反应。

我们创建了一个空的子类 `EvAdventureMob`。Mob（短语为“mobile”）是 MUD 游戏中用于那些能够自己移动的 NPC 的常见术语。我们将在未来的课程中使用该类来表示游戏中的敌人。[关于添加 AI 的课程](Beginner-Tutoroal-AI)。

## 测试

> 创建新模块 `evadventure/tests/test_npcs.py`

现在尚无太多可测试的内容，但我们将在同一模块中测试 NPC 的其他方面，因此现在让我们创建它。

```python
# in evadventure/tests/test_npcs.py

from evennia import create_object                                           
from evennia.utils.test_resources import EvenniaTest                        
                                                                            
from .. import npcs                                                         
                                                                            
class TestNPCBase(EvenniaTest):                                             
    """测试 NPC 基类""" 
    
    def test_npc_base(self):
        npc = create_object(
            npcs.EvAdventureNPC,
            key="TestNPC",
            attributes=[("hit_dice", 4)],  # 设置 hit_dice 为 4
        )
        
        self.assertEqual(npc.hp_multiplier, 4)
        self.assertEqual(npc.hp, 16)
        self.assertEqual(npc.strength, 4)
        self.assertEqual(npc.charisma, 4)
```

这里没有什么特别的注意事项。请注意，`create_object` 辅助函数将 `attributes` 作为关键字参数。 这是一个元组列表，我们用来设置 Attribute 的不同值而不是默认值。我们随后检查几个属性，以确保它们返回我们所期望的值。

## 结论

在 _Knave_ 中，NPC 是玩家角色的简化版本。在其他游戏和规则系统中，它们可能几乎相同。

有了 NPC 类，我们已经有能力创建一个“测试靶子”。由于它尚未具有 AI，它不会反击，但在我们即将到来的课程中，它将足够用于测试战斗。
