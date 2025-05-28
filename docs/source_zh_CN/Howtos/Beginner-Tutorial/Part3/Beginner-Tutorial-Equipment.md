# 处理装备

在 _Knave_ 中，你有一定数量的库存“插槽”。这些插槽的数量由 `CON + 10` 决定。所有物品（除了硬币）都有一个 `size`，表示它占用多少插槽。你不能携带超过你拥有的插槽空间的物品。被使用或穿戴的物品也会计入插槽。

我们需要跟踪角色正在使用的物品：他们准备好的武器会影响他们造成的伤害。盾牌、头盔和盔甲会影响他们的防御。

我们在定义对象时已经设置了可能的“穿戴/使用位置”，这些是在[前一节](./Beginner-Tutorial-Objects.md)中定义的 `enums.py` 中：

```python 
# mygame/evadventure/enums.py

# ...

class WieldLocation(Enum):
    
    BACKPACK = "backpack"
    WEAPON_HAND = "weapon_hand"
    SHIELD_HAND = "shield_hand"
    TWO_HANDS = "two_handed_weapons"
    BODY = "body"  # 装甲
    HEAD = "head"  # 头盔
```

基本上，所有武器/盔甲位置都是独占的——每个位置只能放一个物品（或者没有）。`BACKPACK` 是特别的——它可以包含任意数量的物品（最多使用插槽的上限）。

## EquipmentHandler 的实现

> 创建一个新模块 `mygame/evadventure/equipment.py`。

```{sidebar}
如果你想了解更多关于 Evennia 如何使用处理程序的背后原理， 
有一个[专门的教程](../../Tutorial-Persistent-Handler.md)讨论这一原则。
```
在默认的 Evennia 中，你捡起的所有东西都会“在”你的角色对象内（即，具有你的 `.location`）。这叫做你的 _库存_，没有限制。我们将继续在我们捡起物品时“将物品移动到我们身上”，但我们将通过一个 _Equipment handler_ 添加更多功能。

处理程序是（就我们的目的而言）一个坐在另一个实体上的对象，包含执行特定功能的能力（在我们的例子中是管理装备）。

这是我们处理程序的起始代码：

```python 
# 在 mygame/evadventure/equipment.py 中 

from .enums import WieldLocation

class EquipmentHandler: 
    save_attribute = "inventory_slots"
    
    def __init__(self, obj): 
        # 这里的 obj 是我们在其上存储处理程序的角色 
        self.obj = obj 
        self._load() 
        
    def _load(self):
        """从 `self.obj` 的属性中加载我们的数据"""
        self.slots = self.obj.attributes.get(
            self.save_attribute,
            category="inventory",
            default={
                WieldLocation.WEAPON_HAND: None, 
                WieldLocation.SHIELD_HAND: None, 
                WieldLocation.TWO_HANDS: None, 
                WieldLocation.BODY: None,
                WieldLocation.HEAD: None,
                WieldLocation.BACKPACK: []
            } 
        )
    
    def _save(self):
        """将我们的数据保存回同一个属性"""
        self.obj.attributes.add(self.save_attribute, self.slots, category="inventory") 
```

这是一个简洁且功能齐全的小型处理程序。在分析它的工作原理之前，下面是我们如何将其添加到字符中的：

```python
# mygame/evadventure/characters.py

# ... 

from evennia.utils.utils import lazy_property
from .equipment import EquipmentHandler 

# ... 

class EvAdventureCharacter(LivingMixin, DefaultCharacter):
    
    # ... 

    @lazy_property 
    def equipment(self):
        return EquipmentHandler(self)
```

服务器重新加载后，装备处理器现在可以通过字符实例访问：

```python
character.equipment
```

`@lazy_property` 的工作原理是，直到有人实际尝试通过 `character.equipment` 来获取它时，它才会加载处理器。当这一点发生时，我们启动处理器并传入 `self`（字符实例本身）。这就是上面 EquipmentHandler 代码中的 `__init__` 中的 `.obj`。

所以现在我们在角色上有一个处理器，而处理器也具有指向它所在角色的回指。

由于处理器本身只是一个常规的 Python 对象，我们需要使用 `Character` 来存储我们的数据——_Knave_ 的“插槽”。我们必须将其保存到数据库中，因为我们希望服务器在重新加载后仍然记住它们。

使用 `self.obj.attributes.add()` 和 `.get()` 方法，我们将数据保存到具有特殊命名的 [Attribute](../../../Components/Attributes.md) 中。由于我们使用了 `category`，因此与其他属性发生冲突的可能性很小。

我们的存储结构是一个 `dict`，其中的键基于我们可用的 `WieldLocation` 枚举，每个位置只能有一个物品，除了 `WieldLocation.BACKPACK` 位置，这里是一个列表。

## 连接 EquipmentHandler

每当一个物体从一个位置移动到另一个位置时，Evennia 会在移动的对象、源位置和目的地上调用一组 _hooks_（方法）。所有移动的事物都是如此——无论是角色在房间之间移动还是物品从你的手中掉落到地面。

我们需要将新的 `EquipmentHandler` 绑定到这个系统中。通过阅读[对象页面](../../../Components/Objects.md)或查看 [DefaultObject.move_to](evennia.objects.objects.DefaultObject.move_to) 的文档，我们将找到 Evennia 将会调用的 hooks。这里的 `self` 是移动的对象，从 `source_location` 到 `destination`：

1. `self.at_pre_move(destination)` （如果返回 False，则中止）
2. `source_location.at_pre_object_leave(self, destination)` （如果返回 False，则中止）
3. `destination.at_pre_object_receive(self, source_location)` （如果返回 False，则中止）
4. `source_location.at_object_leave(self, destination)`
5. `self.announce_move_from(destination)`
6. （这里发生移动）
7. `self.announce_move_to(source_location)`
8. `destination.at_object_receive(self, source_location)`
9. `self.at_post_move(source_location)`

所有这些 hooks 都可以被重写以自定义移动行为。在这种情况下，我们有兴趣控制物品如何“进入”和“离开”我们的角色——在角色“内部”的东西就等同于他们“携带”它。我们有三个好的钩子可以使用。 

- `.at_pre_object_receive` - 用于检查你是否可以捡起某物，或者如果你的装备空间已满。
- `.at_object_receive` - 用于将项目添加到 EquipmentHandler 中。
- `.at_object_leave` - 用于从 EquipmentHandler 中移除物品。

你也可以想象使用 `.at_pre_object_leave` 来限制放置（被诅咒的？）物品，但我们将跳过这部分以简化教程。

```python 
# mygame/evadventure/characters.py 

# ... 

class EvAdventureCharacter(LivingMixin, DefaultCharacter): 

    # ... 
    
    def at_pre_object_receive(self, moved_object, source_location, **kwargs): 
        """在 Evennia 将对象放入此角色之前调用（也就是说，
        如果他们捡起某样东西）。如果返回 False，则移动被中止。
        
        """ 
        return self.equipment.validate_slot_usage(moved_object)
    
    def at_object_receive(self, moved_object, source_location, **kwargs): 
        """ 
        当对象“到达”角色时由 Evennia 调用。
        
        """
        self.equipment.add(moved_object)

    def at_object_leave(self, moved_object, destination, **kwargs):
        """ 
        当对象离开角色时由 Evennia 调用。 
        
        """
        self.equipment.remove(moved_object)
```

在上面，我们假设 `EquipmentHandler`（`self.equipment`）具有方法 `.validate_slot_usage`、`.add` 和 `.remove`。但我们还没有实际添加这些方法——我们只是给出了几个合理的名称！在我们可以使用这些方法之前，我们需要实际添加它们。 

当你执行诸如 `create/drop monster:NPC` 的操作时，NPC 会短暂地出现在你的库存中，然后再被放下。因此，NPC 不是可以装备的有效物品，EquipmentHandler 会对此抱怨并引发 `EquipmentError`（我们在下面定义这个错误）。所以我们需要 

## 扩展 EquipmentHandler

### `.validate_slot_usage`

让我们从实现我们上面所提到的第一个方法 `validate_slot_usage` 开始：
```python 
# mygame/evadventure/equipment.py 

from .enums import WieldLocation, Ability

class EquipmentError(TypeError):
    """所有类型的装备错误"""
    pass

class EquipmentHandler: 

    # ... 
    
    @property
    def max_slots(self):
        """基于 CON 防御的最大插槽数量（CON + 10）""" 
        return getattr(self.obj, Ability.CON.value, 1) + 10
        
    def count_slots(self):
        """计算当前的插槽使用情况""" 
        slots = self.slots
        wield_usage = sum(
            getattr(slotobj, "size", 0) or 0
            for slot, slotobj in slots.items()
            if slot is not WieldLocation.BACKPACK
        )
        backpack_usage = sum(
            getattr(slotobj, "size", 0) or 0 for slotobj in slots[WieldLocation.BACKPACK]
        )
        return wield_usage + backpack_usage
    
    def validate_slot_usage(self, obj):
          """
          检查 obj 是否可以适合装备中，基于其大小。
          
          """
          if not inherits_from(obj, EvAdventureObject):
              # 在切换非 evadventure 对象时
              raise EquipmentError(f"{obj.key} 不是可以装备的物品。")
  
         size = obj.size
         max_slots = self.max_slots
         current_slot_usage = self.count_slots()
         return current_slot_usage + size <= max_slots

```

```{sidebar}
`@property` 装饰器将方法转换为属性，因此你不需要“调用”它。
也就是说，你可以访问 `.max_slots` 而不是 `.max_slots()`。在这种情况下，这只需少输入一些。
```

我们添加了两个辅助函数——`max_slots` _属性_ 和 `count_slots`，它是用于计算当前使用插槽数量的方法。让我们找出它们的工作原理。

### `.max_slots`

对于 `max_slots`，请记住处理程序中的 `.obj` 是我们将此处理程序放置到的 `EvAdventureCharacter` 的回指。`getattr` 是一个用于检索对象上命名属性的 Python 方法。`Enum` 的 `Ability.CON.value` 是字符串 `Constitution`（如果你不记得，可以查阅[第一次实用程序与枚举教程](./Beginner-Tutorial-Utilities.md)）。

所以为了更清楚， 

```python 
getattr(self.obj, Ability.CON.value) + 10
```
等同于写:

```python 
getattr(your_character, "Constitution") + 10 
```

这与执行以下操作相同：

```python 
your_character.Constitution + 10 
```

在我们的代码中，我们写了 `getattr(self.obj, Ability.CON.value, 1)` - 这个额外的 `1` 意味着如果在 `self.obj` 上不存在属性 "Constitution"，我们就不会出现错误，而是返回 1。


### `.count_slots`

在这个辅助方法中，我们使用了两种 Python 工具——`sum()` 函数和 [列表推导](https://www.w3schools.com/python/python_lists_comprehension.asp)。前者简单地将任何可迭代对象的值相加。后者是一种更有效的创建列表的方式：

```python 
new_list = [item for item in some_iterable if condition]
all_above_5 = [num for num in range(10) if num > 5]  # [6, 7, 8, 9]
all_below_5 = [num for num in range(10) if num < 5]  # [0, 1, 2, 3, 4]
```

为了更容易理解，尝试将上面的最后一行视为“对于范围 0-9 中的每个数字，选择所有小于 5 的数字并将它们制作成列表”。你也可以将这种推导直接嵌入函数调用中，如 `sum()`，而无需使用 `[]` 括起来。

在 `count_slots` 中，我们有这段代码：

```python 
wield_usage = sum(
    getattr(slotobj, "size", 0)
    for slot, slotobj in slots.items()
    if slot is not WieldLocation.BACKPACK
)
```

我们应该能够跟踪所有内容，除了 `slots.items()`。由于 `slots` 是一个 `dict`，我们可以使用 `.items()` 获取 `(key, value)` 对的序列。我们将其存储在 `slot` 和 `slotobj` 中。因此，上述内容可以理解为：“对 `slots` 中的每一对 `slot` 和 `slotobj`，检查它是哪个插槽位置。如果它 _不是_ 背包，则获取其大小并将其添加到列表中。对所有这些大小求和”。

一种更不紧凑但可能更易理解的写法是：

```python 
backpack_item_sizes = [] 
for slot, slotobj in slots.items(): 
    if slot is not WieldLocation.BACKPACK:
       size = getattr(slotobj, "size", 0) 
       backpack_item_sizes.append(size)
wield_usage = sum(backpack_item_sizes)
```

对于实际上在 BACKPACK 插槽中的物品也是如此。总的尺寸被加在一起。

### 验证插槽

有了这些辅助方法，`validate_slot_usage` 现在变得简单。我们使用 `max_slots` 查看我们可以携带多少。然后我们获取当前使用的插槽数量（使用 `count_slots`）并查看我们新的 `obj` 的大小是否超出了我们的容量。

## `.add` 和 `.remove`

我们将使 `.add` 方法将物品放入 `BACKPACK` 位置，并使 `remove` 方法从任何地方（即使是手中）将其删除。

```python 
# mygame/evadventure/equipment.py 

from .enums import WieldLocation, Ability

# ... 

class EquipmentHandler: 

    # ... 
     
    def add(self, obj):
        """
        将物品放入背包中。
        """
        if self.validate_slot_usage(obj):
	        self.slots[WieldLocation.BACKPACK].append(obj)
	        self._save()

    def remove(self, obj_or_slot):
        """
        从一个插槽中移除特定物品或物品。

        返回从库存中移除的 0 个、1 个或多个物品的列表。
        """
        slots = self.slots
        ret = []
        if isinstance(obj_or_slot, WieldLocation):
            # 一个插槽；如果这失败，obj_or_slot 必须是物品
            if obj_or_slot is WieldLocation.BACKPACK:
                # 清空整个背包
                ret.extend(slots[obj_or_slot])
                slots[obj_or_slot] = []
            else:
                ret.append(slots[obj_or_slot])
                slots[obj_or_slot] = None
        elif obj_or_slot in self.slots.values():
            # 物品在使用/穿戴槽
            for slot, objslot in slots.items():
                if objslot is obj_or_slot:
                    slots[slot] = None
                    ret.append(objslot)
        elif obj_or_slot in slots[WieldLocation.BACKPACK]:  # 物品在背包槽中
            try:
                slots[WieldLocation.BACKPACK].remove(obj_or_slot)
                ret.append(obj_or_slot)
            except ValueError:
                pass
        if ret:
            self._save()
        return ret
```

在 `.add` 中，我们利用 `validate_slot_usage` 进行双重检查，以确保我们确实可以装下该物品，然后将其添加到背包中。

在 `.remove` 中，我们允许通过 `WieldLocation` 或显式指出要移除的对象来清空。注意，首先的 `if` 语句检查 `obj_or_slot` 是否是一个插槽。所以如果失败，那么其他的 `elif` 语句可以安全地假设它必须是一个对象！

任何被移除的物体都将被返回。如果我们给了 `BACKPACK` 作为插槽，我们将清空背包并返回其内部所有的物品。

每当我们更改装备配置时，我们必须确保 `_save()` 结果，否则在服务器重新加载后它将丢失。

## 移动物品

借助 `.remove()` 和 `.add()`，我们可以将物品放入 `BACKPACK` 装备位置并将其取出。我们还需要从背包中抓取物品并使用或穿戴它。我们在 `EquipmentHandler` 中添加一个 `.move` 方法来实现这一点：

```python 
# mygame/evadventure/equipment.py 

from .enums import WieldLocation, Ability

# ... 

class EquipmentHandler: 

    # ... 
    
    def move(self, obj): 
         """将物体从背包移动到其预期的 `inventory_use_slot`。""" 
         
        # 确保首先从装备/背包中移除，以避免双重添加
        self.remove(obj) 
        if not self.validate_slot_usage(obj):
            return

        slots = self.slots
        use_slot = getattr(obj, "inventory_use_slot", WieldLocation.BACKPACK)

        to_backpack = []
        if use_slot is WieldLocation.TWO_HANDS:
            # 双手武器不能与单手使用的物品或盾牌共存
            to_backpack = [slots[WieldLocation.WEAPON_HAND], slots[WieldLocation.SHIELD_HAND]]
            slots[WieldLocation.WEAPON_HAND] = slots[WieldLocation.SHIELD_HAND] = None
            slots[use_slot] = obj
        elif use_slot in (WieldLocation.WEAPON_HAND, WieldLocation.SHIELD_HAND):
            # 如果添加单手武器或盾，则不能使用双手武器
            to_backpack = [slots[WieldLocation.TWO_HANDS]]
            slots[WieldLocation.TWO_HANDS] = None
            slots[use_slot] = obj
        elif use_slot is WieldLocation.BACKPACK:
            # 它属于背包，所以回到背包
            to_backpack = [obj]
        else:
            # 对于其他（身体、头部），只需替换掉之前的物品
            to_backpack = [slots[use_slot]]
            slots[use_slot] = obj
       
        for to_backpack_obj in to_backpack:
            # 将物品放入背包
            if to_backpack_obj:
                slots[WieldLocation.BACKPACK].append(to_backpack_obj)
       
        # 存储新状态
        self._save() 
``` 

在这里，我们记得每个 `EvAdventureObject` 具有一个 `inventory_use_slot` 属性，告诉我们它将放置的位置。因此，我们只需将对象移动到该插槽，替换之前位于该位置的物品。任何被替换的物品都会回到背包中，只要它确实是一个物品，而不是 `None`，在将物品移动到空槽的情况下。

## 获取所有物品

为了可视化我们的库存，我们需要一些方法来获取我们所携带的所有物品。 

```python 
# mygame/evadventure/equipment.py 

from .enums import WieldLocation, Ability

# ... 

class EquipmentHandler: 

    # ... 

    def all(self):
        """
        获取库存中所有物品，无论其位置是什么。
        """
        slots = self.slots
        lst = [
            (slots[WieldLocation.WEAPON_HAND], WieldLocation.WEAPON_HAND),
            (slots[WieldLocation.SHIELD_HAND], WieldLocation.SHIELD_HAND),
            (slots[WieldLocation.TWO_HANDS], WieldLocation.TWO_HANDS),
            (slots[WieldLocation.BODY], WieldLocation.BODY),
            (slots[WieldLocation.HEAD], WieldLocation.HEAD),
        ] + [(item, WieldLocation.BACKPACK) for item in slots[WieldLocation.BACKPACK]]
        return lst
```

在这里，我们获取所有装备位置，并将它们的内容合并到一个包含元组的列表中 
`[(item, WieldLocation), ...]`。这方便显示。

## 武器和盔甲

让 `EquipmentHandler` 轻松告诉你当前正在使用的武器及所有穿戴装备提供的 _防护_ 级别是很方便的。否则你必须每次都查找哪个物品位于哪个装备插槽，并手动加总盔甲插槽。 

```python 
# mygame/evadventure/equipment.py 

from .enums import WieldLocation, Ability
from .objects import get_bare_hand

# ... 

class EquipmentHandler: 

    # ... 
    
    @property
    def armor(self):
        slots = self.slots
        return sum(
            (
                # 装甲通过其防护值列出，因此我们从中减去 10
                # （在 Knave 中 11 是没有盔甲的基础值）
                getattr(slots[WieldLocation.BODY], "armor", 1),
                # 盾牌和头盔通过其盔甲加成列出
                getattr(slots[WieldLocation.SHIELD_HAND], "armor", 0),
                getattr(slots[WieldLocation.HEAD], "armor", 0),
            )
        )

    @property
    def weapon(self):
        # 首先检查双手武器，然后是单手武器；这两者
        # 不应该同时出现（在 `move` 方法中检查）。
        slots = self.slots
        weapon = slots[WieldLocation.TWO_HANDS]
        if not weapon:
            weapon = slots[WieldLocation.WEAPON_HAND]
        # 如果我们仍然没有武器，则返回 None
        if not weapon:
            weapon = get_bare_hand()
        return weapon
```

在 `.armor()` 方法中，我们在每个相关的装备插槽（身体、盾牌、头部）中取出物品（如果有），并获取它们的 `armor` 属性。然后再将它们全部相加使用 `sum()`。

在 `.weapon()` 方法中，我们简单地检查可能的武器插槽（单手或双手）是否有物品。如果没有，我们就回退到在[对象教程](./Beginner-Tutorial-Objects.md#your-bare-hands)中创建的“光秃的手”对象。

### 修复角色类

因此，我们添加了我们的装备处理器，它可以验证我们放入的内容。然而，这在游戏中创建 NPC 等物品时会导致问题，例如使用如下操作

```shell
create/drop monster:evadventure.npcs.EvAdventureNPC
```

问题在于，当 NPC 创建时，它会短暂地出现在你的库存中，然后被放下，因此在这期间代码会在你身上执行（假设你是 `EvAdventureCharacter`）：

```python
# mygame/evadventure/characters.py
# ... 

class EvAdventureCharacter(LivingMixin, DefaultCharacter): 

    # ... 

    def at_object_receive(self, moved_object, source_location, **kwargs): 
        """ 
        当对象“到达”角色时由 Evennia 调用。
        
        """
        self.equipment.add(moved_object)
```

这意味着 EquipmentHandler 会检查 NPC，并且由于它不是有效的装备物品，会引发 `EquipmentError`，导致创建失败。由于我们希望能够轻松创建 NPC 等对象，我们将使用 `try...except` 语句处理此错误，如下所示：

```python
# mygame/evadventure/characters.py
# ... 
from evennia import logger 
from .equipment import EquipmentError

class EvAdventureCharacter(LivingMixin, DefaultCharacter): 

    # ... 

    def at_object_receive(self, moved_object, source_location, **kwargs): 
        """ 
        当对象“到达”角色时由 Evennia 调用。
        
        """
        try:
            self.equipment.add(moved_object)
        except EquipmentError:
            logger.log_trace()
```

使用 Evennia 的 `logger.log_trace()` 我们捕捉错误并将其记录到服务器日志中。这允许你查看这里是否存在真正的错误，但一旦功能正常，如果这些错误信息变得冗余，你也可以用 `pass` 替换 `logger.log_trace()` 中的这一行，以隐藏这些错误。 

## 额外功分

这涵盖了装备处理程序的基本功能。还有其他有用的方法可以添加：

- 给定一个物品，找出它当前所在的装备插槽
- 制作一个字符串表示当前装备
- 获取背包中的所有物品（仅此而已）
- 从背包中获取所有可装备的物品（武器、盾牌） 
- 从背包中获取所有可用物品（使用位置为 `BACKPACK` 的物品）

尝试添加这些功能。完整示例可在[evennia/contrib/tutorials/evadventure/equipment.py](../../../api/evennia.contrib.tutorials.evadventure.equipment.md)中找到。

## 单元测试

> 创建一个新模块 `mygame/evadventure/tests/test_equipment.py`。

```{sidebar}
请参阅 [evennia/contrib/tutorials/evadventure/tests/test_equipment.py](../../../api/evennia.contrib.tutorials.evadventure.tests.test_equipment.md) 
以获取完整的测试示例。
```

要测试 `EquipmentHandler`，最简单的方法是创建一个 `EvAdventureCharacter`（到现在为止，它应该可以通过 `.equipment` 使用 EquipmentHandler）和一些测试对象；然后测试将这些对象传入处理程序的方法。

```python 
# mygame/evadventure/tests/test_equipment.py 

from evennia.utils import create 
from evennia.utils.test_resources import BaseEvenniaTest 

from ..objects import EvAdventureObject, EvAdventureHelmet, EvAdventureWeapon
from ..enums import WieldLocation
from ..characters import EvAdventureCharacter

class TestEquipment(BaseEvenniaTest): 
    
    def setUp(self): 
        self.character = create.create_object(EvAdventureCharacter, key='testchar')
        self.helmet = create.create_object(EvAdventureHelmet, key="helmet") 
        self.weapon = create.create_object(EvAdventureWeapon, key="weapon") 
         
    def test_add_remove(self): 
        self.character.equipment.add(self.helmet)
        self.assertEqual(
            self.character.equipment.slots[WieldLocation.BACKPACK],
            [self.helmet]
        )
        self.character.equipment.remove(self.helmet)
        self.assertEqual(self.character.equipment.slots[WieldLocation.BACKPACK], []) 
        
    # ... 
```

## 总结 

_处理程序_ 是用于将功能组合在一起的有用工具。在我们花时间创建 `EquipmentHandler` 之后，我们就不需要再担心物品插槽的问题了——处理程序会为我们“处理”所有细节。只要我们调用它的方法，细节就可以被遗忘。

我们还学习了如何使用 _hooks_ 将 _Knave_ 的自定义装备处理绑定到 Evennia。

通过 `Characters`、`Objects`，现在的 `Equipment` 到位后，我们应该能继续进行角色生成——玩家将能够创建自己的角色！
