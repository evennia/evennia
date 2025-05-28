# Typeclasses

*Typeclasses* 是 Evennia 数据存储的核心。它允许 Evennia 通过 Python 类表示任意数量的不同游戏实体，而无需为每种新类型修改数据库模式。

在 Evennia 中，最重要的游戏实体 [Accounts](./Accounts.md)、[Objects](./Objects.md)、[Scripts](./Scripts.md) 和 [Channels](./Channels.md) 都是继承自 `evennia.typeclasses.models.TypedObject` 的 Python 类。在文档中，我们称这些对象为“typeclassed”或“是一个 typeclass”。

以下是 Evennia 中 typeclasses 的继承结构：

```
                                  ┌───────────┐
                                  │TypedObject│
                                  └─────▲─────┘
               ┌───────────────┬────────┴──────┬────────────────┐
          ┌────┴────┐     ┌────┴───┐      ┌────┴────┐      ┌────┴───┐
1:        │AccountDB│     │ScriptDB│      │ChannelDB│      │ObjectDB│
          └────▲────┘     └────▲───┘      └────▲────┘      └────▲───┘
       ┌───────┴──────┐ ┌──────┴──────┐ ┌──────┴───────┐ ┌──────┴──────┐
2:     │DefaultAccount│ │DefaultScript│ │DefaultChannel│ │DefaultObject│
       └───────▲──────┘ └──────▲──────┘ └──────▲───────┘ └──────▲──────┘
               │               │               │                │  Evennia
       ────────┼───────────────┼───────────────┼────────────────┼─────────
               │               │               │                │  Gamedir
           ┌───┴───┐       ┌───┴──┐        ┌───┴───┐   ┌──────┐ │
3:         │Account│       │Script│        │Channel│   │Object├─┤
           └───────┘       └──────┘        └───────┘   └──────┘ │
                                                    ┌─────────┐ │
                                                    │Character├─┤
                                                    └─────────┘ │
                                                         ┌────┐ │
                                                         │Room├─┤
                                                         └────┘ │
                                                         ┌────┐ │
                                                         │Exit├─┘
                                                         └────┘
```

- **Level 1** 是“数据库模型”层。这描述了数据库表和字段（技术上是一个 [Django 模型](https://docs.djangoproject.com/en/4.1/topics/db/models/)）。
- **Level 2** 是我们在数据库之上找到 Evennia 的各种游戏实体的默认实现的地方。这些类定义了 Evennia 在各种情况下调用的所有钩子方法。`DefaultObject` 有点特殊，因为它是 `DefaultCharacter`、`DefaultRoom` 和 `DefaultExit` 的父类。它们都被分组在第 2 层，因为它们都是构建的默认值。
- **Level 3** 最后包含在你的游戏目录中创建的空模板类。这是你可以根据需要修改和调整的级别，重载默认值以适应你的游戏。模板直接继承自其默认值，因此 `Object` 继承自 `DefaultObject`，`Room` 继承自 `DefaultRoom`。

> 此图未包括 `Object`、`Character`、`Room` 和 `Exit` 的 `ObjectParent` 混入。这为这些类建立了一个共同的父类，用于共享属性。更多细节请参见 [Objects](./Objects.md)。

使用 `typeclass/list` 命令可以提供 Evennia 所知道的所有 typeclasses 的列表。这对于了解可用内容很有用。但请注意，如果你添加了一个包含类的新模块但没有从任何地方导入该模块，`typeclass/list` 将找不到它。要让 Evennia 知道它，你必须从某处导入该模块。

## typeclasses 和类的区别

所有继承自上表中类的 Evennia 类共享一个重要特性和两个重要限制。这就是为什么我们不简单地称它们为“类”而是“typeclasses”。

1. Typeclass 可以将自身保存到数据库中。这意味着类上的某些属性（实际上并不多）实际上代表数据库字段，并且只能保存非常特定的数据类型。
2. 由于其与数据库的连接，typeclass 的名称必须在整个服务器命名空间中*唯一*。也就是说，任何地方都不能定义两个同名的类。因此，下面的代码将给出错误（因为 `DefaultObject` 现在在此模块和默认库中都被全局找到）：

    ```python
    from evennia import DefaultObject as BaseObject
    class DefaultObject(BaseObject):
         pass
    ```

3. Typeclass 的 `__init__` 方法通常不应被重载。这主要是因为 `__init__` 方法的调用方式不可预测。相反，Evennia 建议你使用 `at_*_creation` 钩子（例如 `at_object_creation` 对于 Objects）来设置 typeclass 第一次保存到数据库时的内容，或者使用每次对象缓存到内存时调用的 `at_init` 钩子。如果你知道自己在做什么并想使用 `__init__`，它*必须*同时接受任意关键字参数并使用 `super` 调用其父类：

    ```python
    def __init__(self, **kwargs):
        # my content
        super().__init__(**kwargs)
        # my content
    ```

除此之外，typeclass 的工作方式与任何普通 Python 类一样，你可以将其视为这样。

## 使用 typeclasses

### 创建新 typeclass

使用 Typeclasses 很容易。你可以使用现有的 typeclass 或创建一个新的 Python 类继承自现有的 typeclass。以下是创建新类型 Object 的示例：

```python
from evennia import DefaultObject

class Furniture(DefaultObject):
    # 这定义了“furniture”是什么，比如
    # 存储谁坐在上面或其他东西。
    pass
```

你现在可以通过两种方式创建一个新的 `Furniture` 对象。第一种（通常不是最方便的）方法是创建类的实例，然后手动将其保存到数据库：

```python
chair = Furniture(db_key="Chair")
chair.save()
```

要使用此方法，你必须将数据库字段名称作为关键字传递给调用。哪些可用取决于你正在创建的实体，但在 Evennia 中都以 `db_*` 开头。如果你之前了解 Django，这是一种你可能熟悉的方法。

建议你使用 `create_*` 函数来创建 typeclassed 实体：

```python
from evennia import create_object

chair = create_object(Furniture, key="Chair")
# 或者（如果你的 typeclass 在模块 furniture.py 中）
chair = create_object("furniture.Furniture", key="Chair")
```

`create_object`（`create_account`、`create_script` 等）将 typeclass 作为其第一个参数；这可以是实际类或在游戏目录下找到的 typeclass 的 Python 路径。因此，如果你的 `Furniture` typeclass 位于 `mygame/typeclasses/furniture.py` 中，你可以将其指向 `typeclasses.furniture.Furniture`。由于 Evennia 本身将在 `mygame/typeclasses` 中查找，你可以进一步缩短到 `furniture.Furniture`。create-functions 接受许多额外的关键字，允许你一次性设置 [Attributes](./Attributes.md) 和 [Tags](./Tags.md) 等。这些关键字不使用 `db_*` 前缀。这也会自动将新实例保存到数据库，因此你不需要显式调用 `save()`。

数据库字段的一个示例是 `db_key`。这存储了你正在修改的实体的“名称”，因此只能保存字符串。这是确保更新 `db_key` 的一种方法：

```python
chair.db_key = "Table"
chair.save()

print(chair.db_key)
<<< Table
```

也就是说，我们将 chair 对象更改为具有 `db_key` "Table"，然后将其保存到数据库。然而，你几乎不会这样做；Evennia 为所有数据库字段定义了属性包装器。这些名称与字段相同，但没有 `db_` 部分：

```python
chair.key = "Table"

print(chair.key)
<<< Table
```

`key` 包装器不仅更短，而且会确保为你保存字段，并通过在底层使用 sql 更新机制更有效地执行此操作。因此，虽然知道字段名为 `db_key` 是有益的，但你应该尽量使用 `key`。

每个 typeclass 实体都有一些与该类型相关的唯一字段。但它们也共享以下字段（不带 `db_` 的包装器名称）：

- `key` (str): 实体的主要标识符，如 "Rose"、"myscript" 或 "Paul"。`name` 是一个别名。
- `date_created` (datetime): 创建此对象的时间戳。
- `typeclass_path` (str): 指向此（类型）类位置的 Python 路径

有一个特殊字段不使用 `db_` 前缀（由 Django 定义）：

- `id` (int): 对象的数据库 id（数据库引用）。这是一个不断增加的唯一整数。它还可以通过 `dbid`（数据库 ID）或 `pk`（主键）访问。`dbref` 属性返回字符串形式的 "#id"。

typeclassed 实体有几个常见的处理程序：

- `tags` - 处理标签的 [TagHandler](./Tags.md)。使用 `tags.add()` 、`tags.get()` 等。
- `locks` - 管理访问限制的 [LockHandler](./Locks.md)。使用 `locks.add()`、`locks.get()` 等。
- `attributes` - 管理对象上的属性的 [AttributeHandler](./Attributes.md)。使用 `attributes.add()` 等。
- `db` (DataBase) - AttributeHandler 的快捷属性；允许 `obj.db.attrname = value`
- `nattributes` - 不在数据库中保存的属性的 [Non-persistent AttributeHandler](./Attributes.md)。
- `ndb` (NotDataBase) - 非持久性 AttributeHandler 的快捷属性。允许 `obj.ndb.attrname = value`

然后，每个 typeclassed 实体用它们自己的属性扩展此列表。有关更多信息，请转到 [Objects](./Objects.md)、[Scripts](./Scripts.md)、[Accounts](./Accounts.md) 和 [Channels](./Channels.md) 的各个页面。还建议你使用 [Evennia 的平面 API](../Evennia-API.md) 探索它们可用的属性和方法。

### 重载钩子

自定义 typeclasses 的方法通常是重载它们上的*钩子方法*。钩子是在各种情况下 Evennia 调用的方法。一个示例是 `Objects` 的 `at_object_creation` 钩子，它只在此对象第一次保存到数据库时被调用。其他示例包括 Accounts 的 `at_login` 钩子和 Scripts 的 `at_repeat` 钩子。

### 查询 typeclasses

大多数时候，你通过使用便捷方法（如 [Commands](./Commands.md) 的 `caller.search()`）或搜索函数（如 `evennia.search_objects`）在数据库中搜索对象。

然而，你也可以使用 [Django 的查询语言](https://docs.djangoproject.com/en/4.1/topics/db/queries/)直接查询它们。这利用了一个位于所有 typeclasses 上的*数据库管理器*，名为 `objects`。此管理器包含允许针对特定对象类型进行数据库搜索的方法（这也是 Django 的常规工作方式）。使用 Django 查询时，你需要使用完整的字段名（如 `db_key`）进行搜索：

```python
matches = Furniture.objects.get(db_key="Chair")
```

重要的是，这将*仅*在数据库中找到直接继承自 `Furniture` 的对象。如果有一个名为 `Sitables` 的 `Furniture` 子类，你将无法通过此查询找到任何派生自 `Sitables` 的椅子（这不是 Django 功能，而是 Evennia 的特性）。为了从子类中找到对象，Evennia 提供了 `get_family` 和 `filter_family` 查询方法：

```python
# 搜索所有家具及其子类，其名称以 "Chair" 开头
matches = Furniture.objects.filter_family(db_key__startswith="Chair")
```

为了确保搜索所有 `Scripts` *无论* typeclass，你需要从数据库模型本身进行查询。因此，对于 Objects，这将是上图中的 `ObjectDB`。以下是 Scripts 的示例：

```python
from evennia import ScriptDB
matches = ScriptDB.objects.filter(db_key__contains="Combat")
```

从数据库模型父类进行查询时，你不需要使用 `filter_family` 或 `get_family` - 你将始终查询数据库模型上的所有子类。

### 更新现有 typeclass 实例

如果你已经创建了 Typeclasses 的实例，你可以随时修改*Python 代码*——由于 Python 继承的工作方式，你的更改将在重新加载服务器后自动应用于所有子类。然而，数据库保存的数据，如 `db_*` 字段、[Attributes](./Attributes.md)、[Tags](./Tags.md) 等，并未嵌入到类中，因此不会自动更新。这需要你自己管理，通过搜索所有相关对象并更新或添加数据：

```python
# 为所有现有家具添加一个价值属性
for obj in Furniture.objects.all():
    # 这将遍历所有 Furniture 实例
    obj.db.worth = 100
```

一个常见的用例是将所有属性放在实体的 `at_*_creation` 钩子中，例如 `Objects` 的 `at_object_creation`。这在每次创建对象时调用——并且仅在那时调用。这通常是你想要的，但这意味着如果你稍后更改 `at_object_creation` 的内容，已经存在的对象将不会更新。你可以通过类似上面的方式（手动设置每个属性）或如下所示修复此问题：

```python
# 仅在那些没有新属性的对象上重新运行 at_object_creation
for obj in Furniture.objects.all():
    if not obj.db.worth:
        obj.at_object_creation()
```

以上示例可以在 `evennia shell` 创建的命令提示符中运行。你也可以在游戏中使用 `@py` 运行所有这些代码。然而，这需要你将代码（包括导入）作为一个单行使用 `;` 和 [列表推导式](http://www.secnetix.de/olli/Python/list_comprehensions.hawk)，如下所示（忽略换行，这只是为了在 wiki 中的可读性）：

```
py from typeclasses.furniture import Furniture;
[obj.at_object_creation() for obj in Furniture.objects.all() if not obj.db.worth]
```

建议你在开始构建之前正确规划游戏，以避免不必要地对对象进行追溯更新。

### 切换 typeclass

如果你想切换一个已经存在的 typeclass，有两种方法可以做到：在游戏中和通过代码。从游戏内部，你可以使用默认的 `@typeclass` 命令：

```
typeclass objname = path.to.new.typeclass
```

此命令有两个重要的开关：
- `/reset` - 这将清除对象上的所有现有属性并重新运行创建钩子（如 Objects 的 `at_object_creation`）。这确保你获得一个纯粹属于此新类的对象。
- `/force` - 如果你要将类更改为对象已经拥有的*相同*类，则需要此选项——这是一个安全检查，以避免用户错误。这通常与 `/reset` 一起使用，以在现有类上重新运行创建钩子。

在代码中，你可以使用所有 typeclassed 实体上可用的 `swap_typeclass` 方法：

```python
obj_to_change.swap_typeclass(new_typeclass_path, clean_attributes=False,
                   run_start_hooks="all", no_default=True, clean_cmdsets=False)
```

此方法的参数在 [API 文档中描述](github:evennia.typeclasses.models#typedobjectswap_typeclass)。

## typeclasses 实际上是如何工作的

*这是一个高级部分。*

从技术上讲，typeclasses 是 [Django 代理模型](https://docs.djangoproject.com/en/4.1/topics/db/models/#proxy-models)。在 typeclass 系统中，唯一“真实”的数据库模型（即在数据库中由实际表表示）是 `AccountDB`、`ObjectDB`、`ScriptDB` 和 `ChannelDB`（还有 [Attributes](./Attributes.md) 和 [Tags](./Tags.md)，但它们本身不是 typeclasses）。它们的所有子类都是“代理”，通过 Python 代码扩展它们而不实际修改数据库布局。

Evennia 在多种方式上修改了 Django 的代理模型，以使它们无需任何样板代码即可工作（例如，你无需在模型 `Meta` 子类中设置 Django 的“代理”属性，Evennia 使用元类为你处理此问题）。Evennia 还确保你可以查询子类，并修补 Django 以允许从同一基类进行多重继承。

### 注意事项

Evennia 使用 *idmapper* 将其 typeclasses（Django 代理模型）缓存到内存中。idmapper 允许像对象处理程序和属性这样的东西存储在 typeclass 实例上，并且只要服务器正在运行就不会丢失（它们只会在服务器重载时被清除）。Django 默认情况下不是这样工作的；默认情况下，每次你在数据库中搜索对象时，你都会得到该对象的*不同*实例，并且你在其上存储的任何不在数据库中的内容都会丢失。底线是 Evennia 的 Typeclass 实例在内存中存在的时间比普通 Django 模型实例长得多。

这有一个需要考虑的注意事项，与[创建你自己的模型](New-Models)有关：Django 缓存对 typeclasses 的外部关系，这意味着如果你通过其他方式更改外部关系中的对象而不是通过该关系，看到关系的对象可能不会可靠地更新，但仍会看到其旧的缓存版本。由于 typeclasses 在内存中停留的时间较长，这种关系的陈旧缓存可能比 Django 中常见的更明显。有关示例和解决方案，请参阅 [已关闭的问题 #1098 及其评论](https://github.com/evennia/evennia/issues/1098)。

## 我会耗尽 dbrefs 吗？

Evennia 不会重用其 `#dbrefs`。这意味着新对象获得一个不断增加的 `#dbref`，即使你删除了旧对象。这有技术和安全原因。但你可能会想这是否意味着你必须担心大型游戏最终会“耗尽” dbref 整数。

答案很简单：**不会**。

例如，默认 sqlite3 数据库的最大 dbref 值是 `2**64`。如果你*每秒钟创建 10,000 个新对象，每分钟的每一天都这样做，大约需要 **6000 万年** 才会耗尽 dbref 数字*。这只是一个 140 TB 的数据库，仅用于存储 dbrefs，没有其他数据。

如果到那时你仍在使用 Evennia 并且有此顾虑，请联系我们，我们可以讨论届时添加 dbref 重用。
