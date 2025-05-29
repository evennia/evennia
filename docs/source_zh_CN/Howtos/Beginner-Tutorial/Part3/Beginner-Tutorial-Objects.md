# 游戏内对象和物品

在上一节中，我们定义了游戏中的“角色”。在继续之前，我们还需要了解“物品”或“对象”是什么。

查看 _Knave_ 的物品列表，我们可以得到关于需要跟踪的内容的一些想法：

- `size` - 这是物品在角色库存中占用的“插槽”数量。
- `value` - 如果我们想出售或购买物品的基本价值。
- `inventory_use_slot` - 某些物品可以被穿戴或使用。例如，头盔需要佩戴在头上，盾牌需要在盾手。某些物品根本不能以这种方式使用，只能放在背包中。
- `obj_type` - 该物品的“类型”。

## 新枚举

我们在[工具教程](./Beginner-Tutorial-Utilities.md)中为能力添加了一些枚举。在继续之前，让我们为使用槽和对象类型扩展枚举。

```python
# mygame/evadventure/enums.py

class WieldLocation(Enum):
    BACKPACK = "backpack"
    WEAPON_HAND = "weapon_hand"
    SHIELD_HAND = "shield_hand"
    TWO_HANDS = "two_handed_weapons"
    BODY = "body"  # 盔甲
    HEAD = "head"  # 头盔

class ObjType(Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    SHIELD = "shield"
    HELMET = "helmet"
    CONSUMABLE = "consumable"
    GEAR = "gear"
    MAGIC = "magic"
    QUEST = "quest"
    TREASURE = "treasure"
```

一旦我们有了这些枚举，就可以用来引用事物。

## 基本对象

> 创建新模块 `mygame/evadventure/objects.py`

```{sidebar}
请查看 [evennia/contrib/tutorials/evadventure/objects.py](../../../api/evennia.contrib.tutorials.evadventure.objects.md) 获取实现完整对象集的示例。
```

我们将基于 Evennia 的标准 `DefaultObject` 创建一个基础 `EvAdventureObject` 类。然后，我们将添加子类，以表示相关的类型：

```python
# mygame/evadventure/objects.py

from evennia import AttributeProperty, DefaultObject 
from evennia.utils.utils import make_iter
from .utils import get_obj_stats 
from .enums import WieldLocation, ObjType

class EvAdventureObject(DefaultObject): 
    """ 
    EvAdventure 对象的基础类。 
    """ 
    inventory_use_slot = WieldLocation.BACKPACK
    size = AttributeProperty(1, autocreate=False)
    value = AttributeProperty(0, autocreate=False)

    # 这可以是单一类型或多个类型的列表（对于能够充当多个角色的对象）。这用于在创建时标记该对象。
    obj_type = ObjType.GEAR

    # 默认的 Evennia hooks

    def at_object_creation(self): 
        """当该对象首次创建时调用。我们将 .obj_type 属性转换为数据库标记。"""
        
        for obj_type in make_iter(self.obj_type):
            self.tags.add(self.obj_type.value, category="obj_type")

    def get_display_header(self, looker, **kwargs):
        """描述顶部""" 
        return "" 

    def get_display_desc(self, looker, **kwargs):
        """主要展示 - 显示对象统计数据""" 
        return get_obj_stats(self, owner=looker)

    # 自定义 EvAdventure 方法

    def has_obj_type(self, objtype): 
        """检查对象是否为某种类型""" 
        return objtype.value in make_iter(self.obj_type)

    def at_pre_use(self, *args, **kwargs): 
        """使用前调用。如果返回 False，则无法使用""" 
        return True 

    def use(self, *args, **kwargs): 
        """使用此对象，无论其含义是什么""" 
        pass 

    def post_use(self, *args, **kwargs): 
        """使用后总是调用。""" 
        pass

    def get_help(self):
        """获取该物品的任何帮助文本"""
        return "该物品没有帮助说明"
```

### 使用属性与否

理论上，`size` 和 `value` 不会改变，可以简单地设置为类上的常规 Python 属性：

```python
class EvAdventureObject(DefaultObject):
    inventory_use_slot = WieldLocation.BACKPACK 
    size = 1 
    value = 0 
```

这样的问题是，如果我们想创建一个 `size 3` 和 `value 20` 的新对象，我们必须为它创建一个新类。我们不能随意更改，因为改变将仅在内存中进行，并在下次服务器重新加载时丢失。

由于我们使用了 `AttributeProperties`，我们可以在创建对象时（或稍后）将 `size` 和 `value` 设置为我们想要的任何值，并且这些属性将永久记住我们对该对象的更改。

为了提高效率，我们使用了 `autocreate=False`。通常，当您使用定义的 `AttributeProperties` 创建新对象时，会同时立即创建一个匹配的 `Attribute`。因此，通常情况下，对象将与两个属性 `size` 和 `value` 一起创建。使用 `autocreate=False`，不会创建任何属性，_除非更改了默认值_。也就是说，只要你的对象的 `size=1`，根本不会创建数据库 `Attribute`。这样可以节省创建大量对象时的时间和资源。

缺点是，由于没有创建属性，因此你无法使用 `obj.db.size` 或 `obj.attributes.get("size")` 引用它，_除非你更改了它的默认值_。你也不能查询出所有 `size=1` 的对象，因为大多数对象尚未在数据库中拥有 `size` 属性。

在我们的案例中，我们将仅将这些属性作为 `obj.size` 等来引用，并且不需要查找特定大小的所有对象。因此，我们认为这样是安全的。

### 在 `at_object_creation` 中创建标签

`at_object_creation` 是 Evennia 在每个子类化 `DefaultObject` 的对象首次创建时调用的方法。

我们在这里做一个巧妙的事情，将我们的 `.obj_type` 转换为一个或多个 [标签](../../../Components/Tags.md)。以这种方式标记对象意味着以后可以通过 Evennia 的搜索功能有效地查找所有给定类型（或多种类型）的对象：

```python
from .enums import ObjType 
from evennia.utils import search 

# 获取游戏中的所有盾牌
all_shields = search.search_object_by_tag(ObjType.SHIELD.value, category="obj_type")
```

我们允许 `.obj_type` 作为单个值或多个值给出。我们使用 `make_iter` 来确保我们不会在任何情况下出现问题。这意味着您可以拥有一个同时也是魔法的盾牌。

## 其他对象类型

某些其他对象类型现在非常简单。

```python
# mygame/evadventure/objects.py 

from evennia import AttributeProperty, DefaultObject
from .enums import ObjType 

class EvAdventureObject(DefaultObject): 
    # ... 
    
class EvAdventureQuestObject(EvAdventureObject):
    """任务对象通常不应可以出售或交易。"""
    obj_type = ObjType.QUEST
 
class EvAdventureTreasure(EvAdventureObject):
    """宝藏通常只是为了出售以获得金币"""
    obj_type = ObjType.TREASURE
    value = AttributeProperty(100, autocreate=False)
```

## 消耗品 

“消耗品”是具有一定数量“使用次数”的物品。使用完毕后，便无法再次使用。例如，健康药水。

```python
# mygame/evadventure/objects.py 

# ... 

class EvAdventureConsumable(EvAdventureObject): 
    """可以消耗的物品""" 
    
    obj_type = ObjType.CONSUMABLE
    value = AttributeProperty(0.25, autocreate=False)
    uses = AttributeProperty(1, autocreate=False)
    
    def at_pre_use(self, user, target=None, *args, **kwargs):
        """使用前调用。如果返回 False，则中止使用。"""
        if target and user.location != target.location:
            user.msg("您离目标太远了！")
            return False
        
        if self.uses <= 0:
            user.msg(f"|w{self.key} 已用完。|n")
            return False

    def use(self, user, *args, **kwargs):
        """使用物品时调用""" 
        pass
    
    def at_post_use(self, user, *args, **kwargs):
        """使用后调用""" 
        # 减少一次使用，若用尽则删除物品。
        self.uses -= 1
        if self.uses <= 0: 
            user.msg(f"{self.key} 已用完。")
            self.delete()
```

在 `at_pre_use` 中，我们检查是否指定了目标（治疗某人或向敌人投掷火弹？），确保我们在同一位置。我们还确保我们还有 `uses` 剩余。在 `at_post_use` 中，我们确保勾选使用次数。

每个消耗品的具体作用会有所不同——我们稍后将需要实现该类的子类，重写 `at_use` 方法以实现不同效果。

## 武器

所有武器需要能够描述在战斗中表现如何的属性。使用武器意味着攻击，所以我们可以让武器本身处理所有与执行攻击相关的逻辑。将攻击代码放在武器上还意味着，如果将来我们想让武器在攻击时做某些特殊的事情（例如，吸血剑在伤害敌人时会治愈攻击者），那么我们可以很容易地在相关的武器子类中添加这一点，而无需修改其他代码。

```python
# mygame/evadventure/objects.py 

from .enums import WieldLocation, ObjType, Ability

# ... 

class EvAdventureWeapon(EvAdventureObject): 
    """所有武器的基类"""

    obj_type = ObjType.WEAPON 
    inventory_use_slot = AttributeProperty(WieldLocation.WEAPON_HAND, autocreate=False)
    quality = AttributeProperty(3, autocreate=False)
    
    attack_type = AttributeProperty(Ability.STR, autocreate=False)
    defense_type = AttributeProperty(Ability.ARMOR, autocreate=False)
    
    damage_roll = AttributeProperty("1d6", autocreate=False)

    def at_pre_use(self, user, target=None, *args, **kwargs):
        if target and user.location != target.location:
            # 我们假设武器只能在与目标同一位置使用
            user.msg("您离目标太远了！")
            return False

        if self.quality is not None and self.quality <= 0:
            user.msg(f"{self.get_display_name(user)} 已损坏，无法使用！")
            return False
        return super().at_pre_use(user, target=target, *args, **kwargs)

    def use(self, attacker, target, *args, advantage=False, disadvantage=False, **kwargs):
        """当武器被使用时，攻击对手"""

        location = attacker.location

        is_hit, quality, txt = rules.dice.opposed_saving_throw(
            attacker,
            target,
            attack_type=self.attack_type,
            defense_type=self.defense_type,
            advantage=advantage,
            disadvantage=disadvantage,
        )
        location.msg_contents(
            f"$You() $conj(attack) $you({target.key}) with {self.key}: {txt}",
            from_obj=attacker,
            mapping={target.key: target},
        )
        if is_hit:
            # 敌人被击中，计算伤害
            dmg = rules.dice.roll(self.damage_roll)

            if quality is Ability.CRITICAL_SUCCESS:
                # 对于关键成功，双倍伤害
                dmg += rules.dice.roll(self.damage_roll)
                message = (
                    f" $You() |ycritically|n $conj(hit) $you({target.key}) for |r{dmg}|n damage!"
                )
            else:
                message = f" $You() $conj(hit) $you({target.key}) for |r{dmg}|n damage!"

            location.msg_contents(message, from_obj=attacker, mapping={target.key: target})
            # 调用钩子
            target.at_damage(dmg, attacker=attacker)

        else:
            # 未击中
            message = f" $You() $conj(miss) $you({target.key})。"
            if quality is Ability.CRITICAL_FAILURE:
                message += ".. 这是一个 |rcritical miss!|n，损坏了武器。"
                if self.quality is not None:
                    self.quality -= 1
                location.msg_contents(message, from_obj=attacker, mapping={target.key: target})

    def at_post_use(self, user, *args, **kwargs):
        if self.quality is not None and self.quality <= 0:
            user.msg(f"|r{self.get_display_name(user)} 折断，无法再使用！")
```

在 EvAdventure 中，我们假设所有武器（包括弓等）都在与目标同一位置使用。武器还有一个 `quality` 属性，在用户掷出关键失败时会磨损。一旦质量降至 0，武器便报废，需要修理。

`quality` 是我们在 _Knave_ 中需要跟踪的东西。当在攻击中出现关键失败时，武器的质量会下降。当它达到 0 时，它将断裂。我们假设 `quality` 为 `None` 意味着质量不适用（也就是说，该物品是不可破坏的），因此在检查时我们必须考虑。

攻击/防御类型跟踪我们如何使用武器解决攻击，例如 `roll + STR vs ARMOR + 10`。

在 `use` 方法中，我们使用了之前[创建的](./Beginner-Tutorial-Rules.md) `rules` 模块来执行解决攻击所需的所有掷骰。

这段代码需要一些额外的解释：
```python
location.msg_contents(
    f"$You() $conj(attack) $you({target.key}) with {self.key}: {txt}",
    from_obj=attacker,
    mapping={target.key: target},
)
```
`location.msg_contents` 会向 `location` 中的所有人发送消息。因为人们通常会注意到你向某人挥剑，这样做是有道理的。然而，这条消息应该根据谁看到而看起来_不同_。

我应该看到： 

    你用剑攻击格伦德尔：<掷骰结果> 

其他人应该看到 

    贝奥武夫攻击格伦德尔：<掷骰结果>  

而格伦德尔应该看到 

    贝奥武夫用剑攻击你：<掷骰结果>

我们向 `msg_contents` 提供以下字符串： 
```python 
f"$You() $conj(attack) $you({target.key}) with {self.key}: {txt}"
```

`{...}` 是我们之前使用过的常规 f-string 格式化标记。`$func(...)` 片段是 [Evennia FuncParser](../../../Components/FuncParser.md) 函数调用。 FuncParser 调用被作为函数执行，结果替代它们在字符串中的位置。当这个字符串被 Evennia 解析时，发生以下情况：

首先，f-string 标记被替换，因此我们得到：
```python 
"$You() $cobj(attack) $you(Grendel) with sword: \n rolled 8 on d20 ..."
```

接下来，调用 FuncParser 函数：
 - `$You()` 根据字符串发送对象的不同返回 `You` 或者相应的名字。它使用 `from_obj=` kwarg 来知道这一点。由于 `msg_contents=attacker`，例如在本例中这将变为 `You` 或 `Beowulf`。 
 - `$you(Grendel)` 查找 `msg_contents` 的 `mapping=` kwarg，以确定谁应该被称呼。如果将被替换为显示名称或小写的 `you`。我们添加了 `mapping={target.key: target}` - 也就是 `{"Grendel": <grendel_obj>}`。所以这将变为 `you` 或者 `Grendel` ，具体取决于谁看到字符串。 
 - `$conj(attack)` 根据观看者决定动词的形式。结果将是 `You attack ...` 或者 `Beowulf attacks`（注意额外的 `s`）。 

一些 FuncParser 调用将所有这些视角压缩成一条字符串！ 

## 魔法 

在 _Knave_ 中，任何人都可以使用魔法，只要他们同时双手握住一个符文石（我们对法术书的称呼）。每个休息期间只能使用一次符文石。因此，符文石是一个同时也是“消耗品”的“魔法武器”的例子。

```python 
# mygame/evadventure/objects.py 

# ... 
class EvAdventureConsumable(EvAdventureObject): 
    # ... 

class EvAdventureWeapon(EvAdventureObject): 
    # ... 

class EvAdventureRuneStone(EvAdventureWeapon, EvAdventureConsumable): 
    """所有魔法符文石的基础类"""
    
    obj_type = (ObjType.WEAPON, ObjType.MAGIC)
    inventory_use_slot = WieldLocation.TWO_HANDS  # 使用魔法时始终双手
    quality = AttributeProperty(3, autocreate=False)

    attack_type = AttributeProperty(Ability.INT, autocreate=False)
    defense_type = AttributeProperty(Ability.DEX, autocreate=False)
    
    damage_roll = AttributeProperty("1d8", autocreate=False)

    def at_post_use(self, user, *args, **kwargs):
        """使用/施放法术后调用""" 
        self.uses -= 1 
        # 我们不在这里删除符文石，但它必须在下次休息时重置。
        
    def refresh(self):
        """刷新符文石（通常在休息后）"""
        self.uses = 1
```

我们将符文石混合成武器和消耗品。请注意，我们不需要再次添加 `.uses`，这是从 `EvAdventureConsumable` 父类继承的。`at_pre_use` 和 `use` 方法也被继承了；我们仅重写 `at_post_use`，因为我们不希望符文石在用尽时被删除。

我们添加了一个方便的方法 `refresh` - 我们应该在角色休息时调用此方法，以重新激活符文石。

符文石_的确_能做什么，将在此基础类的子类的 `at_use` 方法中实现。由于 _Knave_ 中的魔法通常是相当自定义的，因此这将导致大量的自定义代码。

## 盔甲 

盔甲、盾牌和头盔提高角色的 `ARMOR` 属性。在 _Knave_ 中，存储的是盔甲的防御值（11-20）。相反，我们将存储“盔甲加成”（1-10）。如我们所知，防御总是 `bonus + 10`，因此结果是相同的——这意味着我们可以将 `Ability.ARMOR` 作为任何其他防御能力使用，而不必担心特殊情况。

```python 
# mygame/evadventure/objects.py 

# ... 

class EvAdventureArmor(EvAdventureObject): 
    obj_type = ObjType.ARMOR
    inventory_use_slot = WieldLocation.BODY 

    armor = AttributeProperty(1, autocreate=False)
    quality = AttributeProperty(3, autocreate=False)

class EvAdventureShield(EvAdventureArmor):
    obj_type = ObjType.SHIELD
    inventory_use_slot = WieldLocation.SHIELD_HAND 

class EvAdventureHelmet(EvAdventureArmor): 
    obj_type = ObjType.HELMET
    inventory_use_slot = WieldLocation.HEAD
``` 

## 你的双手

当我们没有武器时，我们将用双手战斗。

我们将在即将到来的 [装备教程 lesson](./Beginner-Tutorial-Equipment.md) 中使用此类来表示当你双手“空无一物”时的状态。这样，我们就不需要添加任何特殊情况。

```python
# mygame/evadventure/objects.py

from evennia import search_object, create_object

_BARE_HANDS = None 

# ... 

class WeaponBareHands(EvAdventureWeapon):
    obj_type = ObjType.WEAPON
    inventory_use_slot = WieldLocation.WEAPON_HAND
    attack_type = Ability.STR
    defense_type = Ability.ARMOR
    damage_roll = "1d4"
    quality = None  # 假设拳头是不可摧毁的...

def get_bare_hands(): 
    """获取空手""" 
    global _BARE_HANDS
    if not _BARE_HANDS: 
        _BARE_HANDS = search_object("Bare hands", typeclass=WeaponBareHands).first()
    if not _BARE_HANDS:
        _BARE_HANDS = create_object(WeaponBareHands, key="Bare hands")
    return _BARE_HANDS
```

```{sidebar}
创建一个在任何地方都可以使用的单个实例被称为创建一个 _Singleton_。
```
由于每个人的空手是相同的（在我们的游戏中），我们创建了一个共享的 `Bare hands` 武器对象。我们通过 `search_object` 查找该对象（`.first()` 意味着即使我们意外创建了多个手，也会抓取第一个，具体信息请见 [Django 查询教程](../Part1/Beginner-Tutorial-Django-queries.md)）。如果找不到，则创建它。

通过使用 `global` Python 关键字，我们在模块级属性 `_BARE_HANDS` 中缓存了获取/创建空手对象。因此，这充当了一个缓存，以便不必频繁地搜索数据库。

从现在开始，其他模块可以简单地导入并运行此函数来获取空手。

## 测试和额外积分 

记得在前面的 [工具教程](./Beginner-Tutorial-Utilities.md) 中提到的 `get_obj_stats` 函数吗？ 由于我们当时还不知道如何在游戏中存储对象的属性，所以我们不得不使用虚拟值。

好吧，我们刚刚找到了我们需要的一切！您可以返回并更新 `get_obj_stats`，以正确读取传入对象的数据。

当您更改此函数时，您还必须更新相关的单元测试——因此，您现有的测试将成为测试新对象的好办法！添加更多测试，显示将不同对象类型传递给 `get_obj_stats` 的输出。

试一试。如果需要帮助，完成的工具示例可在 [evennia/contrib/tutorials/evadventure/utils.py](get_obj_stats) 中找到。
