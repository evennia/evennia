# 规则与掷骰

在 _EvAdventure_ 中，我们决定使用 [Knave](https://www.drivethrurpg.com/product/250888/Knave) RPG 规则集。虽然这是商业产品，但根据创作共享 4.0 许可证发布，意味着可以出于任何目的共享和改编 _Knave_，甚至是商业用途。如果您不想购买但仍然想要跟随，可以在 [这里找到一个免费的粉丝版](http://abominablefancy.blogspot.com/2018/10/knaves-fancypants.html)。

## _Knave_ 规则摘要

Knave 受早期《龙与地下城》的启发，规则非常简单。

- 它使用六个能力加值：
  - _力量_ (STR)
  - _敏捷_ (DEX)
  - _体质_ (CON)
  - _智力_ (INT)
  - _智慧_ (WIS)
  - _魅力_ (CHA)  
  这些能力的评分范围从 `+1` 到 `+10`。
  
- 强制使用二十面骰 (`1d20`) 掷骰，通常会加上适当的能力加值。
- 如果你是 _优势_ 掷骰，掷 `2d20` 并选择最高值。如果你是 _劣势_ 掷骰，掷 `2d20` 并选择最低值。
- 掷出自然的 `1` 是 _危急失败_。自然的 `20` 是 _关键成功_。在战斗中掷出这样的点数意味着你的武器或护具会失去质量，最终摧毁它们。
- _豁免检定_（尝试超越环境）意味着掷骰以超过 `15`（始终如此）。所以如果你正在举起一块重石，并且有 `STR +2`，你会掷 `1d20 + 2`，希望结果高于 `15`。
- _对抗豁免检定_意味着要超越敌人的适当能力“防御”，这始终是他们的 `能力加值 + 10`。所以如果你有 `STR +1`，而你在和一个有 `STR +2` 的人摔跤，你掷 `1d20 + 1`，并希望掷出高于 `2 + 10 = 12` 的结果。
- 一个特殊的加值是 `护甲`，`+1` 表示未穿护甲，额外护甲由装备提供。近战攻击测试 `STR` 对抗护甲防御值，而远程攻击使用 `WIS` 对抗护甲。
- _Knave_ 没有技能或职业。每个人都可以使用所有物品，使用魔法意味着手中有一个特殊的“符文石”；每个石头每天可以施放一次法术。
- 角色有 `CON + 10` 的携带'槽'。大多数普通物品占用一个槽，盔甲和大型武器占用两个或三个。
- 恢复是随机的，在吃东西和睡觉后恢复 `1d8 + CON` HP。
- 怪物的难度是通过它们的 `1d8` HP 列出；这称为它们的“击中骰”或 HD。如果需要测试能力，怪物在每项能力中都有 HD 的加值。
- 怪物有一个 _士气评分_。当事情变得糟糕时，它们有机会在掷出 `2d6` 超过其士气评分时感到恐慌而逃跑。
- 在 _Knave_ 中，所有角色均大多随机生成。HP 是 `<level>d8`，但我们给每个新角色设置最大 HP 开局。
- _Knave_ 还拥有随机表，比如起始装备和在 HP 为 0 时是否死亡。死亡（如果发生的话）是永久性的。

## 创建规则模块

> 创建一个新模块 `mygame/evadventure/rules.py`

```{sidebar}
完整版本的规则模块可以在 [evennia/contrib/tutorials/evadventure/rules.py](../../../api/evennia.contrib.tutorials.evadventure.rules.md) 中找到。
```

大多数 RPG 有三大类规则：

- 角色生成规则，通常仅在角色创建时使用
- 常规游戏规则 - 掷骰和解决游戏场景
- 角色提升 - 获得和消费经验以提升角色

我们希望我们的 `rules` 模块涵盖尽可能多的方面，以便我们不必查阅规则书。

## 掷骰

我们将首先制作一个掷骰器。让我们将所有掷骰逻辑组合在一个像这样的结构中（尚未实现的代码）：

```python 
class EvAdventureRollEngine:

   def roll(...):
       # 获取某种类型和数量骰子的结果
       
   def roll_with_advantage_or_disadvantage(...)
       # 获取正常 d20 掷骰的结果，带有优势/劣势（或不带）
       
   def saving_throw(...):
       # 针对特定目标数值进行豁免检定
       
   def opposed_saving_throw(...):
       # 针对目标的防御进行对抗豁免检定

   def roll_random_table(...):
       # 针对随机表进行掷骰（稍后加载）
  
   def morale_check(...):
       # 对目标进行 2d6 士气检定
      
   def heal_from_rest(...):
       # 在休息时恢复 1d8，但不超过最大值。
       
   def roll_death(...):
       # 在 HP 降到 0 时掷骰确定惩罚。 
       
dice = EvAdventureRollEngine() 
```
```{sidebar}
这将所有与骰子相关的代码组合到一个“容器”中，便于导入。但是这更多是个人品味。你 _也可以_ 根据需要将类方法拆分为模块的顶层常规函数。
```

这种结构（称为 _单例_）使我们将所有掷骰逻辑边集中在一个类中，然后在模块底部将其初始化为变量 `dice`。这意味着我们可以在其他模块中这样做：

```python
    from .rules import dice 

    dice.roll("1d8")
```

### 通用掷骰器

我们想能够执行 `roll("1d20")` 并从掷骰中返回一个随机结果。

```python
# 在 mygame/evadventure/rules.py 

from random import randint

class EvAdventureRollEngine:
    
    def roll(self, roll_string):
        """ 
        掷 XdY 骰子，其中 X 是骰子数量 
        Y 是每个骰子的面数。
        
        参数:
            roll_string (str): 形式为 XdY 的掷骰字符串。
        返回:
            int: 掷骰的结果。 
            
        """ 
        
        # 在 'd' 上分割 XdY 输入，一次性分割
        number, diesize = roll_string.split("d", 1)     
        
        # 从字符串转换为整数
        number = int(number) 
        diesize = int(diesize)
            
        # 执行掷骰
        return sum(randint(1, diesize) for _ in range(number))
```

```{sidebar}
在本教程中，我们选择不使用任何贡献模块，因此我们创建自己的掷骰器。但通常你可以使用 [dice](../../../Contribs/Contrib-Dice.md) 贡献模块来处理这一点。我们将在接下来的说明中指出可能有帮助的贡献模块。
```

`randint` 标准 Python 库模块在特定范围内生成随机整数。行

```python 
sum(randint(1, diesize) for _ in range(number))
```
的工作原理如下：

- 针对某个 `number` 次 ... 
- ... 创建一个介于 `1` 和 `diesize` 之间的随机整数 ...
- ... 并将所有这些整数的总和计算出来。

你可以以更不紧凑的方式写同样的东西：

```python 
rolls = []
for _ in range(number): 
   random_result = randint(1, diesize)
   rolls.append(random_result)
return sum(rolls)
```

```{sidebar}
注意 `range` 生成的值是 `0...number-1`。我们在 `for` 循环中使用 `_` 来表示我们并不真正关心这个值 - 我们只想重复循环一定次数。
```

我们不期望最终用户调用此方法；如果真的如此，我们需要进行更多的输入验证 - 我们必须确保 `number` 或 `diesize` 是有效的输入，而不是疯狂的大，以免循环无限进行下去！

### 使用优势掷骰

现在我们有了通用掷骰器，我们可以开始使用它进行更复杂的掷骰。

```python
# 在 mygame/evadventure/rules.py 

# ... 

class EvAdventureRollEngine:

    def roll(roll_string):
        # ... 
    
    def roll_with_advantage_or_disadvantage(self, advantage=False, disadvantage=False):
        
        if not (advantage or disadvantage) or (advantage and disadvantage):
            # 正常掷骰 - 优势/劣势未设定或相互抵消 
            return self.roll("1d20")
        elif advantage:
             # 两次 d20 掷骰中较高的
             return max(self.roll("1d20"), self.roll("1d20"))
        else:
             # 劣势 - 两次 d20 掷骰中较低的 
             return min(self.roll("1d20"), self.roll("1d20"))
```

`min()` 和 `max()` 函数是用来获取两个参数中最大/最小值的标准 Python 函数。

### 豁免检定

我们希望豁免检定能够自己判断是否成功。这意味着它需要知道能力加值（如 STR `+1`）。如果我们能仅通过将执行豁免检定的实体传递给这个方法，告诉他们需要什么类型的掷骰，并让它自行解决，那会很方便：

```python 
result, quality = dice.saving_throw(character, Ability.STR)
```
返回将是一个布尔值 `True/False`，表示是否通过，以及一个 `quality` 值，告知我们是完美失败/成功。

为了让这个豁免检定方法更智能，我们需要再次思考希望如何存储角色数据。

对于我们的目的，使用 [属性](../../../Components/Attributes.md) 来存储能力分数似乎合乎逻辑。为了方便，我们将其命名为与之前课程中设置的 [枚举值](./Beginner-Tutorial-Utilities.md#enums) 相同。因此，如果我们有一个枚举 `STR = "strength"`，我们希望将该能力存储为角色的属性 `strength`。

根据属性文档，我们可以使用 `AttributeProperty`，使属性可通过 `character.strength` 访问，这就是我们将要做的。

简而言之，我们将创建豁免检定方法，假设我们能够通过 `character.strength`、`character.constitution`、`character.charisma` 等等来获得相关的能力值。

```python 
# 在 mygame/evadventure/rules.py 
# ...
from .enums import Ability

class EvAdventureRollEngine: 

    def roll(...)
        # ...
   
    def roll_with_advantage_or_disadvantage(...)
        # ...
       
    def saving_throw(self, character, bonus_type=Ability.STR, target=15, 
                     advantage=False, disadvantage=False):
        """ 
        进行豁免检定，尝试超越一个目标。
       
        参数:
           character (Character): 一个角色（假设拥有以属性形式存储的能力加值）。
           bonus_type (Ability): 一个有效能力加值枚举。
           target (int): 目标数字。Knave 中始终为 15。
           advantage (bool): 如果角色在此掷骰上有优势。
           disadvantage (bool): 如果角色在此掷骰上有劣势。
          
        返回:
            tuple: 一个元组 (bool, Ability)，指示是否成功并且质量为 None 或 Ability.CRITICAL_FAILURE/SUCCESS之一
               
        """
                    
        # 掷骰 
        dice_roll = self.roll_with_advantage_or_disadvantage(advantage, disadvantage)
       
        # 确定我们是否有关键失败/成功
        quality = None
        if dice_roll == 1:
            quality = Ability.CRITICAL_FAILURE
        elif dice_roll == 20:
            quality = Ability.CRITICAL_SUCCESS 

        # 确定加值
        bonus = getattr(character, bonus_type.value, 1) 

        # 返回一个元组 (bool, quality)
        return (dice_roll + bonus) > target, quality
```

`getattr(obj, attrname, default)` 函数是一个非常有用的 Python 工具，用于从对象获取属性，并在未定义该属性时获取默认值。

### 对抗豁免检定

利用我们已经创建的基础，这个方法很简单。记住你必须超越的防御总是相关的加值 + 10。在 _Knave_ 中，因此，如果敌人的防御是 `STR +3`，你必须掷出高于 `13` 的结果。

```python
# 在 mygame/evadventure/rules.py 

from .enums import Ability

class EvAdventureRollEngine:
    
    def roll(...):
        # ... 

    def roll_with_advantage_or_disadvantage(...):
        # ... 

    def saving_throw(...):
        # ... 

    def opposed_saving_throw(self, attacker, defender, 
                             attack_type=Ability.STR, defense_type=Ability.ARMOR,
                             advantage=False, disadvantage=False):
        defender_defense = getattr(defender, defense_type.value, 1) + 10 
        result, quality = self.saving_throw(attacker, bonus_type=attack_type,
                                            target=defender_defense, 
                                            advantage=advantage, disadvantage=disadvantage)
        
        return result, quality 
```

### 士气检定

我们将假设 `morale` 值可以直接从生物体获取，作为 `monster.morale`，- 我们稍后需要记住这样做！

在 _Knave_ 中，生物体进行 `2d6` 的掷骰，如果结果等于或小于其士气，则不会逃跑或投降。标准士气值为 9。

```python 
# 在 mygame/evadventure/rules.py 

class EvAdventureRollEngine:

    # ...
    
    def morale_check(self, defender): 
        return self.roll("2d6") <= getattr(defender, "morale", 9)
    
```

### 治疗检定

为了能够处理治疗，我们需要对游戏实体的健康存储方式做出一些假设。我们需要 `hp_max`（可用 HP 的总量）和 `hp`（当前健康值）。我们假设这些将作为 `obj.hp` 和 `obj.hp_max` 可访问。

根据规则，角色在消耗配给，并有整夜的睡眠后，会恢复 `1d8 + CON` HP。

```python 
# 在 mygame/evadventure/rules.py 

from .enums import Ability

class EvAdventureRollEngine: 

    # ... 
    
    def heal_from_rest(self, character): 
        """ 
        一晚休息恢复 1d8 + CON HP  
        
        """
        con_bonus = getattr(character, Ability.CON.value, 1)
        character.heal(self.roll("1d8") + con_bonus)
```

我们在这里做另一个假设 - `character.heal()` 是可执行的。我们告诉这个函数角色应该恢复多少健康，它会处理这一过程，确保不会恢复超过其最大 HP 的值。

> 了解可用的角色内容和需要的规则掷骰有点像“鸡和蛋”的问题。我们将确保在下一课程中实现匹配的 _Character_ 类。

### 在表上掷骰

我们偶尔需要在一个“表”上掷骰 - 一系列选择。我们需要支持两种主要表类型：

简单的每行一个元素的表（每个结果的几率相同）：

| 结果 |
|:----:|
| item1  |
| item2  | 
| item3  | 
| item4  |

这将简单地表示为一个普通的列表：

```python
["item1", "item2", "item3", "item4"]
```

每个项目的范围（每个结果几率各不相同）：

| 范围 | 结果 | 
|:----:|:----:|
|  1-5  | item1  |
| 6-15  | item2  |
| 16-19 | item3  |
|  20   | item4  |

这将表示为一个元组列表： 

```python
[("1-5", "item1"), ("6-15", "item2"), ("16-19", "item4"), ("20", "item5")]
```

我们还需要知道为获得表的结果而掷的骰子（这可能并不总是显而易见的，在某些游戏中，可能会请求更低的骰子来仅获得早期表结果等）。

```python
# 在 mygame/evadventure/rules.py 

from random import randint, choice

class EvAdventureRollEngine:
    
    # ... 

    def roll_random_table(self, dieroll, table_choices): 
        """ 
        参数: 
             dieroll (str): 一个骰子掷骰字符串，如 "1d20"。
             table_choices (iterable): 一个简单元素列表或元组列表。
        返回: 
            Any: 从给定选择列表中随机结果。
            
        引发:
            RuntimeError: 如果掷骰结果在表之外。
            
        """
        roll_result = self.roll(dieroll) 
        
        if isinstance(table_choices[0], (tuple, list)):
            # 第一个元素是元组/列表；按 [("1-5", "item"),...] 形式对待
            for (valrange, choice) in table_choices:
                minval, *maxval = valrange.split("-", 1)
                minval = abs(int(minval))
                maxval = abs(int(maxval[0]) if maxval else minval)
                
                if minval <= roll_result <= maxval:
                    return choice 
                
            # 如果达到这里，意味着我们设定了一个产生超出表界限的掷骰 - 抛出错误
            raise RuntimeError("roll_random_table: Invalid die roll")
        else:
            # 简单的普通列表
            roll_result = max(1, min(len(table_choices), roll_result))
            return table_choices[roll_result - 1]
```

确保你理解这段代码的作用。

这可能会令人困惑：
```python
minval, *maxval = valrange.split("-", 1)
minval = abs(int(minval))
maxval = abs(int(maxval[0]) if maxval else minval)
```

如果 `valrange` 是字符串 `1-5`，那么 `valrange.split("-", 1)` 将会生成元组 `("1", "5")`。但如果字符串实际上是 `"20"`（对于 RPG 表中的单个条目来说是可能的），这将导致错误，因为它只会分割出一个元素 - 而我们期望两个。

通过使用 `*maxval`（带有 `*`），`maxval` 被告知期望 _0 或多个_ 元素在元组中。因此 `1-5` 的结果将是 `("1", ("5",))`，而 `20` 的结果将变为 `("20", ())`。在这一行：

```python
maxval = abs(int(maxval[0]) if maxval else minval)
```

我们检查 `maxval` 是否实际上有一个值 `("5",)`，或者是空的 `()`。结果是 `maxval` 要么是 `"5"`，要么是 `minval` 的值。

### 死亡检定

虽然原版 Knave 建议 HP 降到 0 意味着立刻死亡，但我们将利用 Knave 的“美化版”可选规则的“死亡表”，使其变得稍微不那么惩罚性。我们还将将 `2` 的结果更改为“死亡”，因为我们在本教程中没有模拟“肢体残缺”：

| 掷骰 | 结果 | -1d4 能力损失 | 
|:----:|:----:|:-------------:|
| 1-2  |   死亡   |          -   |           
| 3    | 虚弱     |         STR   | 
| 4    | 不稳     |         DEX   | 
| 5    | 疲弱     |         CON   | 
| 6    | 混乱     |         INT   | 
| 7    | 不安     |         WIS   | 
| 8    | 面部畸形 |         CHA   |

所有非死亡值映射到某项六项能力中的 1d4 损失（但你会恢复 HP）。我们需要根据上述表进行映射。一个能力加值不能低于 -10，如果你低于这个值，你也会死亡。

```python 
# 在 mygame/evadventure/rules.py 

death_table = (
    ("1-2", "dead"),
    ("3", "strength"),
    ("4", "dexterity"),
    ("5", "constitution"),
    ("6", "intelligence"),
    ("7", "wisdom"),
    ("8", "charisma"),
)
    
    
class EvAdventureRollEngine:
    
    # ... 

    def roll_random_table(...)
        # ... 
        
    def roll_death(self, character): 
        ability_name = self.roll_random_table("1d8", death_table)

        if ability_name == "dead":
            # TODO - 杀死角色！ 
            pass 
        else: 
            loss = self.roll("1d4")
            
            current_ability = getattr(character, ability_name)
            current_ability -= loss
            
            if current_ability < -10: 
                # TODO - 杀死角色！
                pass 
            else:
                # 恢复 1d4 健康，但造成 1d4 能力损失
                self.heal(character, self.roll("1d4"))
                setattr(character, ability_name, current_ability)
                
                character.msg(
                    "你在与死亡的较量中幸存下来，尽管你恢复了一些健康，"
                    f"但永久失去了 {loss} {ability_name}。"
                )
                
dice = EvAdventureRollEngine()
```

在这里，我们根据规则在“死亡表”上掷骰以查看会发生什么。如果他们幸存下来，我们给角色发送一条消息，让他们知道事情的经过。

我们目前还不清楚“杀死角色”的具体含义，因此将其标记为 `TODO`，等待在以后的课程中处理。我们只知道在这里需要 _做点什么_ 来结束角色的生命！

## 测试

> 创建一个新模块 `mygame/evadventure/tests/test_rules.py`

测试 `rules` 模块也将展示一些在测试时非常有用的工具。

```python 
# 在 mygame/evadventure/tests/test_rules.py 

from unittest.mock import patch 
from evennia.utils.test_resources import BaseEvenniaTest
from .. import rules 

class TestEvAdventureRuleEngine(BaseEvenniaTest):
   
    def setUp(self):
        """在每个测试方法执行前调用"""
        super().setUp()
        self.roll_engine = rules.EvAdventureRollEngine()
    
    @patch("evadventure.rules.randint")
    def test_roll(self, mock_randint):
        mock_randint.return_value = 4 
        self.assertEqual(self.roll_engine.roll("1d6"), 4)     
        self.assertEqual(self.roll_engine.roll("2d6"), 2 * 4)     
        
    # 其他规则方法的测试 ...
```

如前所述，运行特定的测试使用命令：

```shell
evennia test --settings settings.py evadventure.tests.test_rules
```

### 模拟与修补

```{sidebar}
在 [evennia/contrib/tutorials/evadventure/tests/test_rules.py](../../../api/evennia.contrib.tutorials.evadventure.tests.test_rules.md) 中有一个完整的规则测试示例。
```

`setUp` 方法是测试类的特殊方法。在每个测试方法运行之前，它将执行。我们使用 `super().setUp()` 确保父类的此方法版本总是执行。然后我们创建一个新的 `EvAdventureRollEngine` 实例进行测试。

在我们的测试中，我们从 `unittest.mock` 库引入 `patch`。这是一个非常有用的测试工具。通常，我们在 `rules` 中导入的 `randint` 将返回一个随机值。由于每次测试的值都不同，这很难进行测试。

通过使用 `@patch`（这称为 _装饰器_），我们暂时将 `rules.randint` 替换为一个“模拟” - 一个虚假的实体。这个模拟会被传递给测试方法。然后我们在这个 `mock_randint` 上设置 `.return_value = 4`。

为模拟添加 `return_value` 意味着每次调用该模拟时，它将返回 4。在测试期间，我们现在可以检查 `self.assertEqual`，确保我们的 `roll` 方法始终返回一个结果，就像随机结果是 4 一样。

还有很多资源可以帮助理解 mock 的使用，可以参考 [这篇文章](https://realpython.com/python-mock-library/) 获得进一步帮助。

> `EvAdventureRollEngine` 有很多方法需要测试。我们将这视为额外的练习！

## 小结

这结束了 _Knave_ 的所有核心规则机制 - 游戏进行中的规则。我们注意到，我们即将需要确定我们的 _Character_ 实际如何存储数据。所以我们将在下一个课程中解决这个问题。
