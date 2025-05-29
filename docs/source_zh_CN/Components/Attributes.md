# 属性

```{code-block}
:caption: 游戏内
> set obj/myattr = "test"
```
```{code-block} python
:caption: 代码中，使用 .db 包装器
obj.db.foo = [1, 2, 3, "bar"]
value = obj.db.foo
```
```{code-block} python
:caption: 代码中，使用 .attributes 处理器
obj.attributes.add("myattr", 1234, category="bar")
value = attributes.get("myattr", category="bar")
```
```{code-block} python
:caption: 代码中，使用 `AttributeProperty` 在类级别
from evennia import DefaultObject
from evennia import AttributeProperty

class MyObject(DefaultObject):
    foo = AttributeProperty(default=[1, 2, 3, "bar"])
    myattr = AttributeProperty(100, category='bar')
```

**属性**允许您在对象上存储任意数据，并确保数据在服务器重启时得以保存。属性可以存储几乎任何 Python 数据结构和数据类型，如数字、字符串、列表、字典等。您还可以存储（引用）数据库对象，如角色和房间。

## 使用属性

属性通常在代码中处理。所有的 [Typeclass](./Typeclasses.md) 实体（[账户](./Accounts.md)、[对象](./Objects.md)、[脚本](./Scripts.md) 和 [频道](./Channels.md)）都可以（并通常会）有相关的属性。管理属性有三种方式，所有这些可以混合使用。

### 使用 .db

获取/设置属性的最简单方法是使用 `.db` 快捷方式。这允许设置和获取缺少 _类别_ 的属性（类别为 `None`）。

```python
import evennia

obj = evennia.create_object(key="Foo")

obj.db.foo1 = 1234
obj.db.foo2 = [1, 2, 3, 4]
obj.db.weapon = "sword"
obj.db.self_reference = obj   # 存储对对象的引用

# (假设游戏中存在一朵玫瑰)
rose = evennia.search_object(key="rose")[0]  # 返回一个列表，取第一个元素
rose.db.has_thorns = True

# 检索
val1 = obj.db.foo1
val2 = obj.db.foo2
weap = obj.db.weapon
myself = obj.db.self_reference  # 从数据库中检索引用，获得对象

is_ouch = rose.db.has_thorns

# 这将返回 None，而不是 AttributeError！
not_found = obj.db.jiwjpowiwwerw

# 返回对象上的所有属性
obj.db.all

# 删除一个属性
del obj.db.foo2
```

尝试访问一个不存在的属性将永远不会导致 `AttributeError`。相反，您将获得 `None`。特殊的 `.db.all` 将返回附加在对象上的所有属性列表。您可以用自己的属性 `all` 替代它，这将替换默认的 `all` 功能，直到您再次删除它。

### 使用 .attributes

如果您想将属性分组到一个类别中，或者事先不知道属性的名称，可以使用 [AttributeHandler](evennia.typeclasses.attributes.AttributeHandler)，该处理器可以在所有类型类实体上通过 `.attributes` 进行访问。没有额外关键字时，这与使用 `.db` 快捷方式是相同的（`.db` 实际上是在内部使用 `AttributeHandler`）。

```python
is_ouch = rose.attributes.get("has_thorns")

obj.attributes.add("helmet", "Knight's helmet")
helmet = obj.attributes.get("helmet")

# 您可以给出用空格分隔的属性名称（这样做在 .db 中无法实现）
obj.attributes.add("my game log", "long text about ...")
```

使用类别可以在同一对象上对同名属性进行分隔以帮助组织。

```python
# 存储（假设我们之前有 gold_necklace 和 ringmail_armor）
obj.attributes.add("neck", gold_necklace, category="clothing")
obj.attributes.add("neck", ringmail_armor, category="armor")

# 待会检索 - 我们会得到 gold_necklace 和 ringmail_armor
neck_clothing = obj.attributes.get("neck", category="clothing")
neck_armor = obj.attributes.get("neck", category="armor")
```

如果不指定类别，则属性的 `category` 将为 `None`，因此也可以通过 `.db` 找到。`None` 被视为其自身的类别，因此不会将 `None` 类别的属性与具有类别的属性混合在一起。

以下是 `AttributeHandler` 的方法。有关更多详细信息，请参阅 [AttributeHandler API](evennia.typeclasses.attributes.AttributeHandler)。

- `has(...)` - 检查对象是否具有此键的属性。这相当于 `obj.db.attrname`，但您也可以检查特定的 `category`。
- `get(...)` - 检索给定的属性。您还可以提供一个 `default` 值以返回如果该属性未定义时（而不是 None）。通过将 `accessing_object` 提供给调用，可以确保在修改任何内容之前检查权限。`raise_exception` 关键字允许您在访问不存在的属性时引发 `AttributeError`。`strattr` 关键字告诉系统将属性存储为原始字符串而不是进行序列化。尽管这是一个优化，但通常不应使用，除非该属性用于某个特定的有限目的。
- `add(...)` - 将新属性添加到对象。可以在此处提供可选的 [锁字符串](./Locks.md) 以限制未来的访问，该调用本身也可以根据锁进行检查。
- `remove(...)` - 删除给定的属性。可以选择性地在执行删除之前检查权限。
- `clear(...)` - 从对象上移除所有属性。
- `all(category=None)` - 返回附加到此对象的所有属性（特定类别）。

示例：

```python
try:
    # 如果属性 foo 不存在，则引发错误
    val = obj.attributes.get("foo", raise_exception=True)
except AttributeError:
    # ...

# 如果 foo2 不存在，则返回默认值
val2 = obj.attributes.get("foo2", default=[1, 2, 3, "bar"])

# 如果存在则删除 foo（如果未设置将悄然失败，除非
# raise_exception 被设置）
obj.attributes.remove("foo")

# 查看对象上的所有衣物
all_clothes = obj.attributes.all(category="clothes")
```

### 使用 AttributeProperty

设置属性的第三种方式是使用 `AttributeProperty`。这是在类型类的 _类级别_ 上进行的，允许您将属性视为 Django 数据库字段。与使用 `.db` 和 `.attributes` 不同，`AttributeProperty` 不能动态创建，必须在类代码中赋值。

```python
# mygame/typeclasses/characters.py

from evennia import DefaultCharacter
from evennia.typeclasses.attributes import AttributeProperty

class Character(DefaultCharacter):

    strength = AttributeProperty(10, category='stat')
    constitution = AttributeProperty(11, category='stat')
    agility = AttributeProperty(12, category='stat')
    magic = AttributeProperty(13, category='stat')

    sleepy = AttributeProperty(False, autocreate=False)
    poisoned = AttributeProperty(False, autocreate=False)

    def at_object_creation(self):
        # ...
```

当类的新实例被创建时，将使用给定的值和类别创建新的 `Attributes`。

通过以这种方式设置 `AttributeProperty`，可以像常规属性一样访问所创建对象的基础属性：

```python
char = create_object(Character)

char.strength   # 返回 10
char.agility = 15  # 分配一个新值（类别保持为 'stat'）

char.db.magic  # 返回 None (错误的类别)
char.attributes.get("agility", category="stat")  # 返回 15

char.db.sleepy # 返回 None 因为 autocreate=False (见下文)
```

```{warning}
请小心不要将 AttributeProperty 分配给类上已经存在的属性和方法的名称，如 'key' 或 'at_object_creation'。这可能会导致非常混淆的错误。
```

`autocreate=False`（默认是 `True`）用于 `sleepy` 和 `poisoned`，值得更详细解释。当设置为 `False` 时，除非显式设置，否则将 _不_ 会为这些属性自动创建。

不创建属性的好处是， `AttributeProperty` 中给定的默认值在未更改时不需要进行数据库访问。这也意味着，如果您想稍后更改默认值，所有先前创建的实体将继承新的默认值。

缺点是，没有数据库的存在，您无法通过 `.db` 和 `.attributes.get`（或通过其他方式在数据库中查询）找到属性：

```python
char.sleepy   # 返回 False，没有数据库访问

char.db.sleepy   # 返回 None - 没有属性存在
char.attributes.get("sleepy")  # 返回 None

char.sleepy = True  # 现在创建了一个属性
char.db.sleepy   # 现在返回 True!
char.attributes.get("sleepy")  # 现在返回 True

char.sleepy  # 现在返回 True，涉及数据库访问
```

您可以通过执行 `del char.strength` 将值重置为默认值（在 `AttributeProperty` 中定义的值）。

有关如何使用特定选项创建的更多详细信息，请参见 [AttributeProperty API](evennia.typeclasses.attributes.AttributeProperty)。

```{warning}
虽然 `AttributeProperty` 在底层使用 `AttributeHandler`（`.attributes`），但反向 _不_ 成立。`AttributeProperty` 具有辅助方法，如 `at_get` 和 `at_set`。这些方法仅在您通过属性访问时会被调用。

也就是说，如果您执行 `obj.yourattribute = 1`，则会调用 `AttributeProperty.at_set`。但如果您执行 `obj.db.yourattribute = 1`，虽然会导致相同的属性被保存，但这 "绕过" 了 `AttributeProperty` 而直接使用 `AttributeHandler`。因此在这种情况下，`AttributeProperty.at_set` 将 _不会_ 被调用。如果您在 `at_get` 中添加了某些特殊功能，这可能会导致困惑。

为了避免混淆，您应该在访问属性时保持一致 - 如果您使用 `AttributeProperty` 来定义属性，则在之后也使用它来访问和修改属性。
```

### 属性的信息

一个 `Attribute` 对象存储在数据库中。它具有以下属性：

- `key` - 属性的名称。当执行例如 `obj.db.attrname = value` 时，此属性被设置为 `attrname`。
- `value` - 这是属性的值。这个值可以是任何可以被序列化的对象——对象、列表、数字或任何其他类型（更多信息见 [这一节](./Attributes.md#what-types-of-data-can-i-save-in-an-attribute)）。在示例 `obj.db.attrname = value` 中， `value` 被存储在这里。
- `category` - 这是一个可选属性，对于大多数属性，设置为 None。设置这个可以将属性用于不同的功能。通常情况下不需要，除非您希望将属性用于非常不同的功能（[昵称](./Nicks.md) 是以这种方式使用属性的一个例子）。要修改此属性，您需要使用 [Attribute Handler](#attributes)。
- `strvalue` - 这是一个单独的值字段，仅接受字符串。这严重限制了可以存储的数据，但允许更简单的数据库查找。除了在将属性复用于其他目的时（[昵称](./Nicks.md) 用到）外，通常不使用此属性。它只能通过 [Attribute Handler](#attributes) 访问。

还有两个特殊属性：

- `attrtype` - 这是 Evennia 内部用于区分 [昵称](./Nicks.md) 和属性（昵称在幕后使用属性）。
- `model` - 这是描述与该属性关联的模型的 *自然键*，形式为 *appname.modelclass*，如 `objects.objectdb`。它被属性和昵称处理器用于快速在数据库中排序匹配。通常不需要修改这个值和 `attrtype`。

非数据库属性不存储在数据库中，且没有 `category`、`strvalue`、`attrtype` 或 `model` 的等价物。

### 在游戏中管理属性

属性主要由代码使用。但也可以允许构建者在游戏中使用属性来“调整旋钮”。例如，构建者可能希望手动调整敌方 NPC 的 “level” 属性以降低其难度。

通过这种方式设置属性时，您受到限制 - 因为给玩家（甚至构建者）存储任意 Python 对象的能力将是一个严重的安全问题。

在游戏中，您可以这样设置属性：

```
set myobj/foo = "bar"
```

要查看，请执行：

```
set myobj/foo
```

或通过以下命令一起查看所有对象信息：

```
examine myobj
```

第一个 `set` 示例将在对象 `myobj` 上存储一个新属性 `foo`，并将其值设为 "bar"。您可以通过这种方式存储数字、布尔值、字符串、元组、列表和字典。但是，如果您存储列表/元组/字典，它们必须是有效的 Python 结构，并且 _只能_ 包含字符串或数字。如果您尝试插入不支持的结构，则输入将被转换为字符串。

```
set myobj/mybool = True
set myobj/mybool = True
set myobj/mytuple = (1, 2, 3, "foo")
set myobj/mylist = ["foo", "bar", 2]
set myobj/mydict = {"a": 1, "b": 2, 3: 4}
set mypobj/mystring = [1, 2, foo]   # foo 是无效的 Python（没有引号）
```

对于最后一行，您将收到警告，值将作为字符串 `"[1, 2, foo]"` 保存。

### 锁定和检查属性

虽然 `set` 命令受限于构建者，但单个属性通常不受限。您可能希望锁定某些敏感属性，特别是对于允许玩家构建的游戏。您可以通过向属性添加 [锁字符串](./Locks.md) 来增加这样的限制。一个 NAttribute 没有锁。

相关的锁类型是：

- `attrread` - 限制谁可以读取属性的值
- `attredit` - 限制谁可以设置/更改此属性

您必须使用 `AttributeHandler` 将锁字符串分配给属性：

```python
lockstring = "attread:all();attredit:perm(Admins)"
obj.attributes.add("myattr", "bar", lockstring=lockstring)
```

如果您已经有一个属性并希望现场添加锁定，您可以使 `AttributeHandler` 返回该属性对象本身（而不是其值），然后直接向其分配锁：

```python
lockstring = "attread:all();attredit:perm(Admins)"
obj.attributes.get("myattr", return_obj=True).locks.add(lockstring)
```

注意 `return_obj` 关键字，确保返回属性对象以便可以访问其 LockHandler。

锁定是无效的，如果没有检查它—而并非所有 Evennia 默认都不检查属性的锁。在执行 `get` 调用时，确保包括 `accessing_obj` 并设置 `default_access=False` 以检查提供的 `lockstring`。

```python
# 在某个命令代码中，我们想限制
# 在对象上设置给定属性名称的功能。
attr = obj.attributes.get(attrname,
                          return_obj=True,
                          accessing_obj=caller,
                          default=None,
                          default_access=False)
if not attr:
    caller.msg("您无法编辑该属性！")
    return
# 在此编辑属性
```

相同的关键字可以用于 `obj.attributes.set()` 和 `obj.attributes.remove()`，这些将检查 `attredit` 锁类型。

## 根据属性查询

虽然您可以使用 `obj.attributes.get` 处理程序获取属性，但您还可以通过每个类型类实体上的 `db_attributes` 许多对多字段根据它们的属性查找对象：

```python
# 根据分配的属性查找对象（不管值如何）
objs = evennia.ObjectDB.objects.filter(db_attributes__db_key="foo")
# 查找具有特定值分配给它们的属性的对象
objs = evennia.ObjectDB.objects.filter(db_attributes__db_key="foo", db_attributes__db_value="bar")
```

```{important}
在内部，属性值被存储为 _序列化字符串_（见下一节）。查询时，您的搜索字符串被转换为相同的格式并以该形式匹配。虽然这意味着属性可以存储任意的 Python 结构，但缺点是您无法对它们进行更高级的数据库比较。例如，`db_attributes__db__value__lt=4` 或 `__gt=0` 将不起作用，因为在字符串之间执行小于和大于的比较是不符合您的要求的。
```

## 我可以在属性中保存什么类型的数据？

数据库对 Python 对象一无所知，因此 Evennia 必须在将属性值存储到数据库之前对其进行 *序列化*。这使用 Python 的 [pickle](https://docs.python.org/library/pickle.html) 模块完成。

> 唯一的例外是，如果您使用 `AttributeHandler` 的 `strattr` 关键字将其保存到属性的 `strvalue` 字段。在这种情况下，您只能保存 *字符串*，并且不会进行序列化）。

### 存储单个对象

单个对象是指不是可迭代的任何对象，如数字、字符串或没有 `__iter__` 方法的自定义类实例。

* 您通常可以存储任何可 _序列化_ 的非可迭代 Python 实体。
* 单个数据库对象/类型类可以存储，尽管它们通常无法被序列化。Evennia 将使用其类名、数据库 ID 和精确到微秒的创建日期将其转换为内部表示。在检索时，将使用此信息从数据库中重新提取对象实例。
* 如果您将数据库对象作为自定义类的属性“隐藏”，Evennia 将无法找到它以进行序列化。为此您需要提供帮助（见下文）。

```{code-block} python
:caption: 有效的赋值例子

# 有效的单值属性数据示例：
obj.db.test1 = 23
obj.db.test1 = False
# 一个数据库对象（将以内部表示存储）
obj.db.test2 = myobj
```

如前所述，Evennia 将无法自动序列化“隐藏”在对象上随机属性中的 db 对象。这会导致在保存属性时抛出错误。

```{code-block} python
:caption: 无效的“隐藏”db对象
# 存储无效的 “隐藏” db 对象的属性示例
class Container:
    def __init__(self, mydbobj):
        # Evennia 无法知道这是一个数据库对象！
        self.mydbobj = mydbobj

# 假设 myobj 是一个 db 对象
container = Container(myobj)
obj.db.mydata = container  # 将引发错误！
```

通过为要保存的对象添加两个方法 `__serialize_dbobjs__` 和 `__deserialize_dbobjs__`，您可以在 Evennia 的主序列化器工作之前，预序列化和后反序列化所有“隐藏”的对象。在这些方法中，使用 Evennia 的 [evennia.utils.dbserialize.dbserialize](evennia.utils.dbserialize.dbserialize) 和 [dbunserialize](evennia.utils.dbserialize.dbunserialize) 函数安全地序列化要存储的 db 对象。

```{code-block} python
:caption: 修复无效的“隐藏”db对象以便于属性存储

from evennia.utils import dbserialize  # 重要

class Container:
    def __init__(self, mydbobj):
        # 一个“隐藏”的 db 对象
        self.mydbobj = mydbobj

    def __serialize_dbobjs__(self):
        """此方法在序列化之前被调用，允许
        我们自定义处理这些“隐藏的” db 对象"""
        self.mydbobj = dbserialize.dbserialize(self.mydbobj)

    def __deserialize_dbobjs__(self):
        """此方法在反序列化之后被调用，允许您
        恢复您之前序列化的 “隐藏” db 对象"""
        if isinstance(self.mydbobj, bytes):
            # 在尝试反序列化之前确保检查它是否为字节
            self.mydbobj = dbserialize.dbunserialize(self.mydbobj)

# 假设 myobj 是一个 db 对象
container = Container(myobj)
obj.db.mydata = container  # 现在可以正常工作！
```

> 注意 `__deserialize_dbobjs__` 中的额外检查，以确保您要反序列化的内容是一个 `bytes` 对象。这是因为在某些情况下，属性的缓存会再次进行反序列化处理，而数据已经被反序列化。如果您在日志中看到的错误是 `无法为存储取消序列化数据: ...`，则可能是因为您忘记了添加此检查。

### 存储多个对象

这意味着将对象存储在某种集合中，是可以在循环中迭代的示例 *可迭代对象*，属性保存支持以下迭代对象：

* [元组](https://docs.python.org/3/library/functions.html#tuple)，如 `(1,2,"test", <dbobj>)`。
* [列表](https://docs.python.org/3/tutorial/datastructures.html#more-on-lists)，如 `[1,2,"test", <dbobj>]`。
* [字典](https://docs.python.org/3/tutorial/datastructures.html#dictionaries)，如 `{1:2, "test":<dbobj>]`。
* [集合](https://docs.python.org/2/tutorial/datastructures.html#sets)，如 `{1,2,"test",<dbobj>}`。
* [collections.OrderedDict](https://docs.python.org/3/library/collections.html#collections.OrderedDict)，如 `OrderedDict((1,2), ("test", <dbobj>))`。
* [collections.Deque](https://docs.python.org/3/library/collections.html#collections.deque)，如 `deque((1,2,"test",<dbobj>))`。
* [collections.DefaultDict](https://docs.python.org/3/library/collections.html#collections.defaultdict) 如 `defaultdict(list)`。
* 以上任意组合的 *嵌套*，如字典中的列表或每个包含字典的元组的 OrderedDict 等。
* 所有其他可迭代的对象（即带有 `__iter__` 方法的实体）将被转换为 *列表*。因为您可以使用上述任意组合，这通常不是很大的限制。

所有在 [单个对象](./Attributes.md#storing-single-objects) 部分列出的实体都可以存储在可迭代对象中。

> 如前所述，数据库实体（即类型类）是无法序列化的。因此，在存储可迭代对象时，Evennia 必须递归遍历可迭代对象及其所有嵌套子可迭代对象，以找到可能的数据库对象进行转换。这个过程非常快速，但为了效率，您可能希望避免使用嵌套结构太深的情况。

```python
# 存储的有效可迭代对象示例
obj.db.test3 = [obj1, 45, obj2, 67]
# 一个字典
obj.db.test4 = {'str':34, 'dex':56, 'agi':22, 'int':77}
# 混合字典/列表
obj.db.test5 = {'members': [obj1,obj2,obj3], 'enemies':[obj4,obj5]}
# 一个包含列表的元组
obj.db.test6 = (1, 3, 4, 8, ["test", "test2"], 9)
# 一个集合
obj.db.test7 = set([1, 2, 3, 4, 5])
# 原位操作
obj.db.test8 = [1, 2, {"test":1}]
obj.db.test8[0] = 4
obj.db.test8[2]["test"] = 5
# test8 现在是 [4,2,{"test":5}]
```

请注意，如果您制作了一些高级可迭代对象，并以某种方式存储数据库对象，以至于未通过迭代返回它，您就创建了一个“隐藏”的数据库对象。请参阅 [上一节](#storing-single-objects) 了解如何安全地告诉 Evennia 如何序列化这样的隐藏对象。

### 检索可变对象

Evennia 存储属性的方式的副作用是 *可变* 迭代对象（可以在创建后就地修改的迭代对象，诸如列表）由称为 `_SaverList`、`_SaverDict` 等的自定义对象处理。这些 `_Saver...` 类行为与普通变量相同，唯一不同的是它们知道数据库，并在赋值给它们时保存到数据库。这使您可以执行 `self.db.mylist[7] = val` 并确保列表的新版本被保存。否则，您必须将列表加载到临时变量中，更改它，然后将其重新分配给属性以使其保存。

不过，有一点重要的是要记住。如果您将可变的迭代对象提取到另一个变量，例如 `mylist2 = obj.db.mylist`，您的新变量（`mylist2`）仍然是 `_SaverList`。这意味着它将在更新时继续保存到数据库！

```python
obj.db.mylist = [1, 2, 3, 4]
mylist = obj.db.mylist

mylist[3] = 5  # 这也将更新数据库

print(mylist)  # 现在是 [1, 2, 3, 5]
print(obj.db.mylist)  # 现在也是 [1, 2, 3, 5]
```

当您将可变属性数据提取到变量（如 `mylist`）时，请将其视为获取变量的 _快照_。如果您更新快照，它将保存到数据库，但该更改 _不会传播到您之前可能做过的其他快照_。

```python
obj.db.mylist = [1, 2, 3, 4]
mylist1 = obj.db.mylist
mylist2 = obj.db.mylist
mylist1[3] = 5

print(mylist1)  # 现在是 [1, 2, 3, 5]
print(obj.db.mylist)  # 也更新为 [1, 2, 3, 5]

print(mylist2)  # 仍然是 [1, 2, 3, 4] ！
```

```{sidebar}
请记住，本节的复杂性仅与 *可变* 迭代对象有关 - 任何可以就地更新的对象，如列表和字典。 [不可变](https://en.wikipedia.org/wiki/Immutable) 对象（字符串、数字、元组等）在一开始就与数据库断开连接。
```

为了避免与可变属性产生混淆，只处理一个变量（快照），根据需要将结果保存回来。

您还可以选择使用 `.deserialize()` 方法“断开”属性与数据库的整个连接：

```python
obj.db.mylist = [1, 2, 3, 4, {1: 2}]
mylist = obj.db.mylist.deserialize()
```

这一操作的结果将是一个仅由常规 Python 可变对象（`list` 而不是 `_SaverList`，`dict` 而不是 `_SaverDict` 等）组成的结构。如果您更新它，您需要将其显式保存回属性以便保存。

## 内存属性（NAttributes）

_NAttributes_（即非数据库属性）在大多数方面模仿属性，但它们是 **非持久的** - 它们 _不会_ 在服务器重启时存活。

- 使用 `.db` 而是使用 `.ndb`。
- 使用 `.attributes` 而是使用 `.nattributes`。
- 使用 `AttributeProperty` 而不是 `NAttributeProperty`。

```python
rose.ndb.has_thorns = True
is_ouch = rose.ndb.has_thorns

rose.nattributes.add("has_thorns", True)
is_ouch = rose.nattributes.get("has_thorns")
```

`Attributes` 和 `NAttributes` 之间的差异：

- `NAttribute` 在服务器重启时总是被清除。
- 它们仅存在于内存中，根本不涉及数据库，使其比 `Attribute` 更快访问和编辑。
- `NAttribute` 可以存储 _任何_ Python 结构（和数据库对象），没有限制。然而，如果您删除之前存储在 `NAttribute` 中的数据库对象，`NAttribute` 将不知道这一点，可能会给您返回没有匹配数据库条目的 Python 对象。相比之下，`Attribute` 始终会检查这一点。如果这是一个问题，请使用 `Attribute`，或在保存之前检查对象的 `.pk` 属性是否不为 None。
- 它们不能使用标准的 `set` 命令设置（但可以通过 `examine` 可见）。

使用 `ndb` 存储临时数据相比于简单地直接在对象上存储变量，有一些重要的原因：
[]()
- NAttributes 由 Evennia 跟踪，在服务器可能执行的各种缓存清理操作中不会被清除。因此，使用它们可以确保在服务器运行时至少保持可用。
- 这是一种一致的风格 - `.db/.attributes` 和 `.ndb/.nattributes` 使得代码清晰，容易区分数据的持久性（或非持久性）。

### 持久与非持久

因此，*持久* 数据意味着您的数据将幸存于服务器重启，而 *非持久* 数据则不会 ...

...那您为什么要使用非持久数据呢？答案是，您不必。大多数情况下，您确实希望保存尽可能多的东西。但非持久数据在某些情况下潜在地有用。

- 您担心数据库性能。由于 Evennia 非常积极地缓存属性，因此除非您非常频繁地读取和写入属性（例如，每秒多次），否则这不是一个问题。从已缓存的属性中的读取速度与读取任何 Python 属性一样快。但即使如此，这通常也不是值得担心的事情：除了 Evennia 自身的缓存，现代数据库系统也非常有效地缓存数据以提高速度。如果可能，我们的默认数据库甚至在 RAM 中完全运行，从而减轻了在高负载期间对磁盘写入的需求。
- 使用非持久数据的更有效原因是如果您 *想* 在注销时丢失状态。也许您存储的是在服务器启动时重新初始化的可丢弃数据。也许您在执行可能对角色对象造成有害影响的脚本时进行测试（如 buggy [Scripts](./Scripts.md)）。使用非持久存储，您可以确保无论发生什么糟糕的事情，服务器重启都可以清理。
- `NAttribute` 对它们可以存储的内容没有任何限制，因为它们不需要担心被保存到数据库 - 它们非常适合临时存储。
- 您希望实现一个完全或部分 *非持久的世界*。我们无权反对您的宏伟设想！
