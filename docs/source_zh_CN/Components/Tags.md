# 标签

_标签_ 是可以“附加”到对象上的简短文本标签，用于组织、分组和快速了解其属性，类似于将标签附加到行李上。

```plaintext
:caption: 在游戏中
> tag obj = tagname
```

```python
:caption: 在代码中，使用 .tags（TagHandler）

obj.tags.add("mytag", category="foo")
obj.tags.get("mytag", category="foo")
```

```python
:caption: 在代码中，使用 TagProperty 或 TagCategoryProperty

from evennia import DefaultObject
from evennia import TagProperty, TagCategoryProperty

class Sword(DefaultObject): 
    # 属性名称是标签键，类别作为参数
    can_be_wielded = TagProperty(category='combat')
    has_sharp_edge = TagProperty(category='combat')

    # 属性名称是类别，标签键是参数
    damage_type = TagCategoryProperty("piercing", "slashing")
    crafting_element = TagCategoryProperty("blade", "hilt", "pommel") 
```

在游戏中，标签由默认的 `tag` 命令控制：

```plaintext
> tag Chair = furniture
> tag Chair = furniture
> tag Table = furniture

> tag/search furniture 
Chair, Sofa, Table
```

一个 Evennia 实体可以被任意数量的标签标记。标签比 [Attributes](./Attributes.md) 更高效，因为在数据库端，标签在所有具有该特定标签的对象之间是 _共享_ 的。标签本身不携带值；而是检查标签本身的存在——给定对象要么有给定标签，要么没有。

在代码中，你可以使用类型类实体上的 `TagHandler`（`.tags`）来管理标签。你还可以通过 `TagProperty`（每行一个标签，一个类别）或 `TagCategoryProperty`（每行一个类别，多个标签）在类级别上分配标签。这两者都在底层使用 `TagHandler`，它们只是定义类时添加标签的便捷方式。

在上面的例子中，标签告诉我们 `Sword` 是锋利的并且可以被挥舞。如果这就是它们的全部功能，它们可能只是一个普通的 Python 标志。当标签变得重要时，是因为有很多对象具有不同的标签组合。也许你有一个魔法咒语，可以使城堡中所有锋利的物体变钝——无论是剑、匕首、矛还是厨房刀！你可以抓取所有带有 `has_sharp_edge` 标签的对象。另一个例子是影响所有标记为 `outdoors` 的房间的天气脚本，或者查找所有带有 `belongs_to_fighter_guild` 标签的角色。

在 Evennia 中，标签在技术上也用于实现 `别名`（对象的替代名称）和 `权限`（简单字符串用于 [锁](./Locks.md) 检查）。

## 使用标签

### 搜索标签

使用标签的常见方法（设置后）是查找所有带有特定标签组合的对象：

```python
objs = evennia.search_tag(key=("foo", "bar"), category='mycategory')
```

如上所示，你也可以拥有没有类别的标签（类别为 `None`）。

```python
import evennia

# 所有方法返回查询集

# 搜索对象
objs = evennia.search_tag("furniture")
objs2 = evennia.search_tag("furniture", category="luxurious")
dungeon = evennia.search_tag("dungeon#01")
forest_rooms = evennia.search_tag(category="forest")
forest_meadows = evennia.search_tag("meadow", category="forest")
magic_meadows = evennia.search_tag("meadow", category="magical")

# 搜索脚本
weather = evennia.search_tag_script("weather")
climates = evennia.search_tag_script(category="climate")

# 搜索账户
accounts = evennia.search_tag_account("guestaccount")
```

> 请注意，仅搜索“furniture”将只返回带有“furniture”标签且类别为 `None` 的对象。我们必须明确给出类别才能获得“豪华”家具。

使用任何 `search_tag` 变体都将返回 [Django 查询集](https://docs.djangoproject.com/en/4.1/ref/models/querysets/)，即使你只有一个匹配项。你可以将查询集视为列表并对其进行迭代，或者继续使用它们构建搜索查询。

请记住，搜索时未设置类别意味着将其设置为 `None`——这并不意味着类别未定义，而是 `None` 被视为默认的未命名类别。

```python
import evennia 

myobj1.tags.add("foo")  # 暗示类别=None
myobj2.tags.add("foo", category="bar")

# 这将返回一个仅包含 myobj1 的查询集
objs = evennia.search_tag("foo")

# 这将返回一个仅包含 myobj2 的查询集
objs = evennia.search_tag("foo", category="bar")
# 或
objs = evennia.search_tag(category="bar")
```

游戏中还有一个命令用于处理分配和使用（[对象-](./Objects.md)）标签：

```plaintext
tag/search furniture
```

### TagHandler

这是当你已经有条目时处理标签的主要方式。此处理程序位于所有类型类实体上，作为 `.tags`，你可以使用 `.tags.add()`、`.tags.remove()` 和 `.tags.has()` 来管理对象上的标签。[请参阅 API 文档](evennia.typeclasses.tags.TagHandler)以获取更多有用的方法。

TagHandler 可以在任何基本的 *类型化* 对象上找到，即 [Objects](./Objects.md)、[Accounts](./Accounts.md)、[Scripts](./Scripts.md) 和 [Channels](./Channels.md)（以及它们的子类）。以下是一些使用示例：

```python
mychair.tags.add("furniture")
mychair.tags.add("furniture", category="luxurious")
myroom.tags.add("dungeon#01")
myscript.tags.add("weather", category="climate")
myaccount.tags.add("guestaccount")

mychair.tags.all()  # 返回标签列表
mychair.tags.remove("furniture") 
mychair.tags.clear()    
```

添加新标签将创建一个新标签或重用已存在的标签。请注意，有 _两个_ "furniture" 标签，一个类别为 `None`，一个类别为 "luxurious"。

使用 `remove` 时，`Tag` 不会被删除，而只是与标记对象断开连接。这使得操作非常快速。`clear` 方法从对象中删除（断开）所有标签。

### TagProperty

这是在创建新类时用作属性的：

```python
from evennia import TagProperty 
from typeclasses import Object 

class MyClass(Object):
    mytag = TagProperty(tagcategory)
```

这将在数据库中创建一个名为 `mytag` 且类别为 `tagcategory` 的标签。你可以通过 `obj.mytag` 找到它，但更有用的是你可以通过数据库中的常规标签搜索方法找到它。

请注意，如果你使用 `obj.tags.remove("mytag", "tagcategory")` 删除此标签，则下次访问此属性时，该标签将 _重新添加_ 到对象中！

### TagCategoryProperty

这是 `TagProperty` 的逆：

```python
from evennia import TagCategoryProperty 
from typeclasses import Object 

class MyClass(Object): 
    tagcategory = TagCategoryProperty(tagkey1, tagkey2)
```

上面的例子意味着你将有两个标签（`tagkey1` 和 `tagkey2`），每个标签都有 `tagcategory` 类别，分配给此对象。

请注意，与 `TagProperty` 的工作方式类似，如果你使用 `TagHandler` 从对象中删除这些标签（`obj.tags.remove("tagkey1", "tagcategory")`），则下次访问该属性时，这些标签将 _重新添加_。

然而，反向操作并不成立：如果你通过 `TagHandler` 向对象添加了同一类别的新标签，则该属性将在返回的标签列表中包含该标签。

如果你想将属性中的标签与数据库中的标签重新同步，可以对其使用 `del` 操作——下次访问该属性时，它将仅显示你在其中指定的默认键。以下是它的工作原理：

```python
>>> obj.tagcategory 
["tagkey1", "tagkey2"]

# 在属性外部删除默认标签之一
>>> obj.tags.remove("tagkey1", "tagcategory")
>>> obj.tagcategory 
["tagkey1", "tagkey2"]   # 缺失的标签会自动创建！

# 从属性外部添加新标签
>>> obj.tags.add("tagkey3", "tagcategory")
>>> obj.tagcategory 
["tagkey1", "tagkey2", "tagkey3"]  # 包含新标签！

# 将属性与数据库同步
>>> del obj.tagcategory 
>>> obj.tagcategory 
["tagkey1", "tagkey2"]   # 属性/数据库现在同步
```

## 标签（以及别名和权限）的属性

标签是 *唯一* 的。这意味着只有一个具有给定键和类别的标签对象。

```{important}
未指定类别（默认）会将标签的类别设置为 `None`，这也被视为唯一的键 + 类别组合。你不能使用 `TagCategoryProperty` 设置类别为 `None` 的标签，因为属性名称不能为 `None`。请使用 `TagHandler`（或 `TagProperty`）来实现。
```

当标签分配给游戏实体时，这些实体实际上共享同一个标签。这意味着标签不适合存储关于单个对象的信息——请改用 [Attribute](./Attributes.md) 来实现。标签比属性更有限，但这也使它们在数据库中查找非常快速——这就是其意义所在。

标签在数据库中具有以下属性：

- **key** - 标签的名称。这是查找标签时要搜索的主要属性。
- **category** - 此类别允许仅检索用于不同目的的特定标签子集。例如，你可以有一个“区域”类别的标签，另一个“户外位置”类别的标签。如果未给出，类别将为 `None`，这也被视为一个单独的默认类别。
- **data** - 这是一个可选的文本字段，用于存储有关标签的信息。请记住，标签在实体之间共享，因此此字段不能保存任何特定于对象的信息。通常，它用于保存标签所标记的实体组的信息——可能用于上下文帮助，如工具提示。默认情况下不使用它。

还有两个特殊属性。通常不需要更改或设置这些属性，它们由 Evennia 内部使用，用于实现 `Tag` 对象的各种其他用途：

- **model** - 这保存了该标签处理的模型对象的 *自然键* 描述，格式为 *application.modelclass*，例如 `objects.objectdb`。它由每种实体类型的 TagHandler 用于在后台正确存储数据。
- **tagtype** - 这是标签内置子类（即 *别名* 和 *权限*）的“顶级类别”。使用此特殊字段的 TagHandler 特别旨在释放 *category* 属性以供你随意使用。

## 别名和权限

别名和权限是使用普通 TagHandler 实现的，它们只是保存具有不同 `tagtype` 的标签。这些处理程序在所有对象上命名为 `aliases` 和 `permissions`。它们的用法与上面的标签相同：

```python
boy.aliases.add("rascal")
boy.permissions.add("Builders")
boy.permissions.remove("Builders")

all_aliases = boy.aliases.all()
```

等等。类似于游戏中的 `tag` 工作方式，还有用于分配权限的 `perm` 命令和用于别名的 `@alias` 命令。
