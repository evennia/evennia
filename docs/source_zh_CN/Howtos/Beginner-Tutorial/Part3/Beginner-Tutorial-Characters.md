# 玩家角色

在[关于规则和掷骰的前一课](./Beginner-Tutorial-Rules.md)中，我们对“玩家角色”实体做了一些假设：

- 它应该在自身上存储能力值，如`character.strength`、`character.constitution`等。
- 它应该有一个`.heal(amount)`方法。

因此，我们有了一些关于它应该如何表现的指导！角色是一个数据库实体，其值应能够随时间改变。基于Evennia的[DefaultCharacter Typeclass](../../../Components/Typeclasses.md)来实现它是合理的。角色类就像桌面RPG中的“角色纸”，它将包含与该PC相关的所有内容。

## 继承结构

玩家角色（PC）并不是我们世界中唯一的“活物”。我们还有_NPC_（如店主和其他友好角色）以及可以攻击我们的_怪物_（mobs）。

在代码中，我们可以用几种方式来构建这个结构。如果NPC/怪物只是PC的特殊情况，我们可以使用如下的类继承：

```python
from evennia import DefaultCharacter 

class EvAdventureCharacter(DefaultCharacter): 
    # 内容
    
class EvAdventureNPC(EvAdventureCharacter):
    # 更多内容
    
class EvAdventureMob(EvAdventureNPC): 
    # 更多内容
```

我们在`Character`类上放置的所有代码现在将自动继承到`NPC`和`Mob`。

然而，在_Knave_中，NPC，特别是怪物，不使用与PC相同的规则——它们被简化为使用Hit-Die（HD）概念。因此，尽管仍然类似于角色，NPC应该与PC分开，如下所示：

```python
from evennia import DefaultCharacter 

class EvAdventureCharacter(DefaultCharacter): 
    # 内容

class EvAdventureNPC(DefaultCharacter):
    # 单独的内容
    
class EvAdventureMob(EvAdventureNPC):
    # 更多单独的内容
```

然而，有些事情应该是所有“活物”共有的：

- 所有的角色都可以受到伤害。
- 所有的角色都可以死亡。
- 所有的角色都可以治愈。
- 所有的角色都可以持有和失去金币。
- 所有的角色都可以掠夺他们的敌人。
- 所有的角色在被击败时都可以被掠夺。

我们不希望为每个类单独编写这些代码，但我们不再有一个共同的父类来放置它们。因此，我们将使用一个_混入_类的概念：

```python 
from evennia import DefaultCharacter 

class LivingMixin:
    # 所有活物共有的内容

class EvAdventureCharacter(LivingMixin, DefaultCharacter): 
    # 内容

class EvAdventureNPC(LivingMixin, DefaultCharacter):
    # 内容
    
class EvAdventureMob(LivingMixin, EvAdventureNPC):
    # 更多内容
```

```{sidebar}
在[evennia/contrib/tutorials/evadventure/characters.py](../../../api/evennia.contrib.tutorials.evadventure.characters.md)中有一个角色类结构的示例。
```
上面的`LivingMixin`类不能单独工作——它只是为其他类“补丁”了一些所有活物应该能够做的额外功能。这是一个_多重继承_的例子。了解这一点很有用，但不应过度使用多重继承，因为它可能会使代码难以跟踪。

## Living混入类

> 创建一个新模块`mygame/evadventure/characters.py`

让我们为游戏中的所有活物添加一些有用的通用方法。

```python 
# 在 mygame/evadventure/characters.py 中

from .rules import dice 

class LivingMixin:

    # 使怪物容易知道攻击PC
    is_pc = False  

	@property
    def hurt_level(self):
        """
        描述角色受伤程度的字符串。
        """
        percent = max(0, min(100, 100 * (self.hp / self.hp_max)))
        if 95 < percent <= 100:
            return "|g完美|n"
        elif 80 < percent <= 95:
            return "|g擦伤|n"
        elif 60 < percent <= 80:
            return "|G淤青|n"
        elif 45 < percent <= 60:
            return "|y受伤|n"
        elif 30 < percent <= 45:
            return "|y受伤严重|n"
        elif 15 < percent <= 30:
            return "|r重伤|n"
        elif 1 < percent <= 15:
            return "|r几乎撑不住了|n"
        elif percent == 0:
            return "|R倒下了！|n"

    def heal(self, hp): 
        """ 
        治愈hp量的生命值，不允许超过最大hp
         
        """ 
        damage = self.hp_max - self.hp 
        healed = min(damage, hp) 
        self.hp += healed 
        
        self.msg(f"你治愈了 {healed} HP。") 
        
    def at_pay(self, amount):
        """在支付金币时，确保不会扣除超过我们拥有的数量"""
        amount = min(amount, self.coins)
        self.coins -= amount
        return amount
        
    def at_attacked(self, attacker, **kwargs): 
		"""被攻击并开始战斗时调用。"""
		pass
    
    def at_damage(self, damage, attacker=None):
        """被攻击并受到伤害时调用。"""
        self.hp -= damage  
        
    def at_defeat(self): 
        """被击败时调用。默认情况下这意味着死亡。"""
        self.at_death()
        
    def at_death(self):
        """当这个东西死去时调用。"""
        # 对于不同的活物来说，这将意味着不同的事情
        pass 
        
    def at_do_loot(self, looted):
        """掠夺另一个实体时调用""" 
        looted.at_looted(self)
        
    def at_looted(self, looter):
        """被另一个实体掠夺时调用""" 
        
        # 默认偷一些金币 
        max_steal = dice.roll("1d10") 
        stolen = self.at_pay(max_steal)
        looter.coins += stolen

```
这些大多是空的，因为它们在角色和NPC中会表现不同。但将它们放在混入中意味着我们可以期望这些方法对所有活物都可用。

一旦我们创建了更多的游戏内容，我们需要记住实际调用这些钩子方法，以便它们发挥作用。例如，一旦我们实现了战斗，我们必须记住调用`at_attacked`以及涉及受伤、被击败或死亡的其他方法。

## 角色类

我们现在开始根据_Knave_的需求制作基本的角色类。

```python
# 在 mygame/evadventure/characters.py 中

from evennia import DefaultCharacter, AttributeProperty
from .rules import dice 

class LivingMixin:
    # ... 


class EvAdventureCharacter(LivingMixin, DefaultCharacter):
    """ 
    用于EvAdventure的角色。 
    """
    is_pc = True 

    strength = AttributeProperty(1) 
    dexterity = AttributeProperty(1)
    constitution = AttributeProperty(1)
    intelligence = AttributeProperty(1)
    wisdom = AttributeProperty(1)
    charisma = AttributeProperty(1)
    
    hp = AttributeProperty(8) 
    hp_max = AttributeProperty(8)
    
    level = AttributeProperty(1)
    xp = AttributeProperty(0)
    coins = AttributeProperty(0)

    def at_defeat(self):
        """角色在死亡表上掷骰子"""
        if self.location.allow_death:
            # 这允许房间进行非致命战斗
            dice.roll_death(self)
        else:
            self.location.msg_contents(
                "$You() $conj(collapse) in a heap, alive but beaten.",
                from_obj=self)
            self.heal(self.hp_max)
            
    def at_death(self):
        """我们在死亡表上掷出了“死”。"""
        self.location.msg_contents(
            "$You() collapse in a heap, embraced by death.",
            from_obj=self) 
        # TODO - 返回到角色生成以创建新角色！            
```

我们在这里对我们的房间做了一个假设——它们有一个属性`.allow_death`。我们需要记下以后实际在房间中添加这样的属性！

在我们的`Character`类中，我们实现了我们希望从_Knave_规则集中模拟的所有属性。`AttributeProperty`是一种以字段方式添加属性的方法；这些将在每个角色上以多种方式访问：

- 作为`character.strength`
- 作为`character.db.strength`
- 作为`character.attributes.get("strength")`

参见[Attributes](../../../Components/Attributes.md)以了解属性的工作原理。

与基础_Knave_不同，我们将`coins`存储为一个单独的属性，而不是作为库存中的物品，这使得以后处理以物易物和交易更加容易。

我们实现了玩家角色版本的`at_defeat`和`at_death`。我们还利用了`LivingMixin`类中的`.heal()`。

### Funcparser内联

上面`at_defeat`方法中的这段代码值得额外解释：

```python
self.location.msg_contents(
    "$You() $conj(collapse) in a heap, alive but beaten.",
    from_obj=self)
```

记住，`self`是这里的角色实例。因此`self.location.msg_contents`意味着“向我当前所在位置中的所有事物发送消息”。换句话说，向与角色在同一地方的每个人发送消息。

`$You() $conj(collapse)`是[FuncParser内联](../../../Components/FuncParser.md)。这些是在字符串中执行的函数。结果字符串可能会因不同的观众而异。`$You()`内联函数将使用`from_obj`来确定“你”是谁，并显示你的名字或“你”。`$conj()`（动词变位器）将调整（英语）动词以匹配。

- 你将看到：“你倒在一堆，活着但被打败。”
- 房间里的其他人将看到：“托马斯倒在一堆，活着但被打败。”

注意`$conj()`选择了“collapse/collapses”以使句子语法正确。

### 回溯

我们首次使用`rules.dice`掷骰子在死亡表上！正如你可能记得的，在上一课中，我们不知道在这个表上掷出“死”时该怎么办。现在我们知道了——我们应该在角色上调用`at_death`。所以让我们在我们之前有TODO的地方添加这个：

```python 
# mygame/evadventure/rules.py 

class EvAdventureRollEngine:
    
    # ... 

    def roll_death(self, character): 
        ability_name = self.roll_random_table("1d8", death_table)

        if ability_name == "dead":
            # 杀死角色！
            character.at_death()  # <------ TODO 没有了
        else: 
            # ... 
                        
            if current_ability < -10: 
                # 杀死角色！
                character.at_death()  # <------- TODO 没有了
            else:
                # ... 
```

## 将角色与Evennia连接

你可以在游戏中使用`type`命令轻松创建一个`EvAdventureCharacter`：

    type self = evadventure.characters.EvAdventureCharacter

现在你可以使用`examine self`检查你的类型是否已更新。

如果你希望_所有_新角色都是这种类型，你需要告诉Evennia。Evennia使用全局设置`BASE_CHARACTER_TYPECLASS`来知道在创建角色时（例如登录时）使用哪种类型类。这默认为`typeclasses.characters.Character`（即`mygame/typeclasses/characters.py`中的`Character`类）。

因此，有两种方法可以将你的新角色类编织到Evennia中：

1. 更改`mygame/server/conf/settings.py`并添加`BASE_CHARACTER_TYPECLASS = "evadventure.characters.EvAdventureCharacter"`。
2. 或者，更改`typeclasses.characters.Character`以继承自`EvAdventureCharacter`。

你必须始终重新加载服务器以使此类更改生效。

```{important}
在本教程中，我们在文件夹`mygame/evadventure/`中进行所有更改。这意味着我们可以隔离我们的代码，但这意味着我们需要做一些额外的步骤将角色（和其他对象）与Evennia连接起来。对于你自己的游戏，直接编辑`mygame/typeclasses/characters.py`也是完全可以的。
```

## 单元测试

> 创建一个新模块`mygame/evadventure/tests/test_characters.py`

对于测试，我们只需创建一个新的EvAdventure角色，并检查调用其上的方法不会出错。

```python
# mygame/evadventure/tests/test_characters.py 

from evennia.utils import create
from evennia.utils.test_resources import BaseEvenniaTest 

from ..characters import EvAdventureCharacter 

class TestCharacters(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        self.character = create.create_object(EvAdventureCharacter, key="testchar")

    def test_heal(self):
        self.character.hp = 0 
        self.character.hp_max = 8 
        
        self.character.heal(1)
        self.assertEqual(self.character.hp, 1)
        # 确保我们不能治愈超过最大值
        self.character.heal(100)
        self.assertEqual(self.character.hp, 8)
        
    def test_at_pay(self):
        self.character.coins = 100 
        
        result = self.character.at_pay(60)
        self.assertEqual(result, 60) 
        self.assertEqual(self.character.coins, 40)
        
        # 不能得到超过我们拥有的金币
        result = self.character.at_pay(100)
        self.assertEqual(result, 40)
        self.assertEqual(self.character.coins, 0)
        
    # 测试其他方法 ...

```
如果你遵循了之前的课程，这些测试应该看起来很熟悉。考虑添加其他方法的测试作为练习。有关详细信息，请参阅以前的课程。

要运行测试，你可以执行：

     evennia test --settings settings.py .evadventure.tests.test_characters


## 关于种族和职业

_Knave_没有任何D&D风格的_职业_（如盗贼、战士等）。它也不涉及_种族_（如矮人、精灵等）。这使得教程更短，但你可能会问自己如何添加这些功能。

在我们为_Knave_勾勒出的框架中，这将是简单的——你可以在角色上添加一个属性作为种族/职业：

```python
# mygame/evadventure/characters.py

from evennia import DefaultCharacter, AttributeProperty
# ... 

class EvAdventureCharacter(LivingMixin, DefaultCharacter):
    
    # ... 

    charclass = AttributeProperty("Fighter")
    charrace = AttributeProperty("Human")

```
我们使用`charclass`而不是`class`，因为`class`是一个保留的Python关键字。将`race`命名为`charrace`以匹配风格。

然后我们需要扩展我们的[规则模块](./Beginner-Tutorial-Rules.md)（以及后来的[角色生成](./Beginner-Tutorial-Chargen.md)）以检查和包含这些职业的含义。

## 总结

有了`EvAdventureCharacter`类，我们对在_Knave_下我们的PC将会是什么样子有了更好的理解。

目前，我们只有一些零散的代码，并没有在游戏中测试这些代码。但如果你愿意，你现在可以将自己切换到`EvAdventureCharacter`。登录你的游戏并运行命令：

    type self = evadventure.characters.EvAdventureCharacter 

如果一切顺利，`ex self`现在将显示你的类型类为`EvAdventureCharacter`。用以下命令检查你的力量：

    py self.strength = 3

```{important}
在执行`ex self`时，你暂时不会看到所有的能力列出。这是因为使用`AttributeProperty`添加的属性在至少访问过一次之前是不可用的。所以一旦你设置（或查看）上面的`.strength`，从那时起`examine`中将显示`strength`。
```
