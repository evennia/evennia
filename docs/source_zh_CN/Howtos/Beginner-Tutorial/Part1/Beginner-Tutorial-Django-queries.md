# 高级搜索 - Django 数据库查询

```{important} 进阶课程！

一旦您开始在 Evennia 中进行更高级的操作，学习 Django 的查询语言将非常有用。但这并不是开箱即用的必需知识，第一次阅读可能会有些不知所措。所以，如果您是 Python 和 Evennia 的新手，可以随意浏览本课程，并在您获得更多经验后再回头参考。
```

在上一课中我们使用的搜索函数和方法对于大多数情况已经足够。但有时您需要更具体：

- 您想找到所有 `Characters` ...
- ... 位于标记为 `moonlit` 的房间中 ...
- ... _并且_ 具有属性 `lycanthropy` 且级别等于 2 ...
- ... 因为他们应该立即变成狼人！

原则上，您可以通过现有的搜索函数结合大量循环和 if 语句来实现这一点。但对于像这样非标准的情况，直接查询数据库会更高效。

Evennia 使用 [Django](https://www.djangoproject.com/) 来处理其与数据库的连接。[django queryset](https://docs.djangoproject.com/en/3.0/ref/models/querysets/) 代表一个数据库查询。可以将多个 queryset 组合在一起以构建更复杂的查询。只有当您尝试使用 queryset 的结果时，它才会实际调用数据库。

构建 queryset 的常用方法是通过获取其 `.objects` 资源来定义要搜索的实体类，然后调用各种方法。我们之前见过这样的变体：

```python
all_weapons = Weapon.objects.all()
```

这现在是一个代表所有 `Weapon` 实例的 queryset。如果 `Weapon` 有一个子类 `Cannon`，而我们只想要大炮，我们会这样做：

```python
all_cannons = Cannon.objects.all()
```

请注意，`Weapon` 和 `Cannon` 是 _不同的_ 类型类。这意味着您在 `all_cannons` 中找不到任何 `Weapon` 类型类的结果。反之亦然，您在 `all_weapons` 中找不到任何 `Cannon` 类型类的结果。这可能不是您所期望的。

如果您想获取所有类型类为 `Weapon` _以及_ `Weapon` 的所有子类（如 `Cannon`）的实体，您需要使用 `_family` 类型的查询：

```{sidebar} _family

`all_family` 和 `filter_family`（以及用于获取一个结果的 `get_family`）是 Evennia 特有的。它们不是常规 Django 的一部分。
```

```python
really_all_weapons = Weapon.objects.all_family()
```

这个结果现在包含了 `Weapon` 和 `Cannon` 实例（以及任何其他类型类在任何距离上继承自 `Weapon` 的实体，如 `Musket` 或 `Sword`）。

要根据其他标准限制您的搜索，而不是 Typeclass，您需要使用 `.filter`（或 `.filter_family`）：

```python
roses = Flower.objects.filter(db_key="rose")
```

这是一个代表所有 `db_key` 等于 `"rose"` 的花的 queryset。由于这是一个 queryset，您可以继续添加条件；这将作为 `AND` 条件。

```python
local_roses = roses.filter(db_location=myroom)
```

我们也可以在一条语句中写出：

```python
local_roses = Flower.objects.filter(db_key="rose", db_location=myroom)
```

我们还可以从结果中 `.exclude` 某些内容：

```python
local_non_red_roses = local_roses.exclude(db_key="red_rose")
```

重要的是要注意，我们还没有调用数据库！直到我们真正尝试检查结果时，数据库才会被调用。这里，当我们尝试遍历它时，数据库被调用（因为现在我们需要实际从中获取结果以便能够循环）：

```python
for rose in local_non_red_roses:
    print(rose)
```

从现在开始，queryset 被 _评估_，我们不能再继续添加更多查询到它——如果我们想找到其他结果，我们需要创建一个新的 queryset。评估 queryset 的其他方法是打印它、用 `list()` 将其转换为列表以及尝试访问其结果。

```{sidebar} 数据库字段
每个数据库表只有几个字段。对于 `DefaultObject`，最常见的是 `db_key`、`db_location` 和 `db_destination`。访问它们时，通常只需访问 `obj.key`、`obj.location` 和 `obj.destination`。在数据库查询中使用它们时，您只需记住 `db_`。对象描述 `obj.db.desc` 不是这样的硬编码字段，而是附加到对象的众多属性之一。
```

注意我们如何使用 `db_key` 和 `db_location`。这是这些数据库字段的实际名称。按照惯例，Evennia 在每个数据库字段前使用 `db_`。当您使用普通的 Evennia 搜索助手和对象时，您可以跳过 `db_`，但在这里我们直接调用数据库，需要使用“真实”的名称。

以下是与 `objects` 管理器一起使用的最常用方法：

- `filter` - 根据搜索条件查询对象列表。如果未找到，则返回空 queryset。
- `get` - 查询单个匹配项 - 如果未找到或找到多个，则引发异常。
- `all` - 获取特定类型的所有实例。
- `filter_family` - 类似于 `filter`，但也搜索所有子类。
- `get_family` - 类似于 `get`，但也搜索所有子类。
- `all_family` - 类似于 `all`，但也返回所有子类的实体。

> 所有 Evennia 搜索函数都在底层使用 querysets。`evennia.search_*` 函数实际上返回 querysets（到目前为止，我们只是将它们视为列表）。这意味着原则上您可以在 `evennia.search_object` 的结果上添加 `.filter` 查询以进一步细化搜索。

## Queryset 字段查找

上面我们找到了 `db_key` 为 `"rose"` 的玫瑰。这是一个 _精确_ 匹配，_区分大小写_，所以它不会找到 `"Rose"`。

```python
# 这是区分大小写的，与 = 相同
roses = Flower.objects.filter(db_key__exact="rose"

# i 表示不区分大小写
roses = Flower.objects.filter(db_key__iexact="rose")
```

Django 字段查询语言使用 `__` 类似于 Python 使用 `.` 来访问资源。这是因为 `.` 在函数关键字中不被允许。

```python
roses = Flower.objects.filter(db_key__icontains="rose")
```

这将找到名称包含字符串 `"rose"` 的所有花，如 `"roses"`、`"wild rose"` 等。开头的 `i` 使搜索不区分大小写。其他有用的变体包括 `__istartswith` 和 `__iendswith`。您还可以使用 `__gt`、`__ge` 进行“大于”/“大于或等于”比较（`__lt` 和 `__le` 也相同）。还有 `__in`：

```python
swords = Weapons.objects.filter(db_key__in=("rapier", "two-hander", "shortsword"))
```

还可以使用 `__` 来访问外部对象，如 Tags。例如，假设这是我们识别法师的方式：

```python
char.tags.add("mage", category="profession")
```

在这种情况下，我们已经有一个 Evennia 助手来进行此搜索：

```python
mages = evennia.search_tags("mage", category="profession")
```

如果您只想查找吸血鬼法师，这就是查询的样子：

```{sidebar} 断行代码
在 Python 中，您可以用 `(...)` 包裹代码以将其分成多行。这样做不会影响功能，但可以使其更易于阅读。
```

```python
sparkly_mages = (
    Vampire.objects.filter(									   
        db_tags__db_key="mage", 
        db_tags__db_category="profession")
)
```

这会查看 `Vampire` 上的 `db_tags` 字段，并根据每个标签的 `db_key` 和 `db_category` 的值进行过滤。

有关更多字段查找，请参阅 [django 文档](https://docs.djangoproject.com/en/3.0/ref/models/querysets/#field-lookups)。

## 让我们找到那个狼人...

让我们看看我们是否可以为我们在本课开始时提到的月光下的狼人制作一个查询。

首先，我们让自己和我们当前的位置符合条件，以便进行测试：

```python
> py here.tags.add("moonlit")
> py me.db.lycanthropy = 2
```

这是一个更复杂查询的示例。我们将其视为可能性的示例。

```{code-block} python
:linenos:
:emphasize-lines: 4,6,7,8

from typeclasses.characters import Character

will_transform = (
    Character.objects
    .filter(
        db_location__db_tags__db_key__iexact="moonlit",
        db_attributes__db_key__iexact="lycanthropy",
        db_attributes__db_value=2
    )
)
```

```{sidebar} 属性与数据库字段
不要将数据库字段与您通过 `obj.db.attr = 'foo'` 或 `obj.attributes.add()` 设置的 [Attributes](../../../Components/Attributes.md) 混淆。属性是*链接*到对象的自定义数据库实体。它们不是像 `db_key` 或 `db_location` 那样在该对象上的独立字段。

虽然属性的 `db_key` 只是一个普通字符串，但它们的 `db_value` 实际上是一个序列化的数据。这意味着无法使用附加运算符来查询它。因此，如果您使用例如 `db_attributes__db_value__iexact=2`，您将收到错误。虽然属性非常灵活，但这是它们的缺点 - 它们存储的值无法通过高级查询方法直接查询，除了找到精确匹配。
```

- **第 4 行** 我们想找到 `Character`，所以我们访问 `Character` 类型类上的 `.objects`。
- 我们开始过滤...
- **第 6 行**：...通过访问 `db_location` 字段（通常这是一个房间）
- ...并在该位置，我们获取 `db_tags` 的值（这是一个 _多对多_ 数据库字段，我们可以将其视为一个对象；它引用位置上的所有标签）
- ...并从那些 `Tags` 中，我们寻找 `db_key` 为 "moonlit" 的 `Tags`（不区分大小写）。
- **第 7 行**：...我们还只想要具有 `Attributes` 的 `Characters`，其 `db_key` 恰好为 `"lycanthropy"`
- **第 8 行**：...同时 `Attribute` 的 `db_value` 为 2。

运行此查询会使我们新获得的狼人角色出现在 `will_transform` 中，因此我们知道要将其转换。成功！

```{important}
您不能像其他数据类型那样自由查询属性 `db_value`。这是因为属性可以存储任何 Python 实体，并且实际上在数据库端存储为 _字符串_。因此，虽然在上面的示例中可以使用 `db_value=2`，但无法使用 `dbvalue__eq=2` 或 `__lt=2`。有关处理属性的更多信息，请参阅 [Attributes](../../../Components/Attributes.md#querying-by-attribute)。
```

## 使用 OR 或 NOT 的查询

到目前为止的所有示例都使用了 `AND` 关系。`.filter` 的参数通过 `AND` 添加在一起（“我们希望标签房间为 "moonlit" _并且_ 狼人症大于 2”）。

对于使用 `OR` 和 `NOT` 的查询，我们需要 Django 的 [Q 对象](https://docs.djangoproject.com/en/4.1/topics/db/queries/#complex-lookups-with-q-objects)。它直接从 Django 导入：

```python
from django.db.models import Q
```

`Q` 是一个对象，使用与 `.filter` 相同的参数创建，例如：

```python
Q(db_key="foo")
```

然后，您可以将此 `Q` 实例用作 `filter` 中的参数：

```python
q1 = Q(db_key="foo")
Character.objects.filter(q1)
# 这与以下相同
Character.objects.filter(db_key="foo")
```

`Q` 的有用之处在于，这些对象可以使用特殊符号（位运算符）链接在一起：`|` 表示 `OR`，`&` 表示 `AND`。前面的波浪号 `~` 否定 `Q` 中的表达式，因此起到 `NOT` 的作用。

```python
q1 = Q(db_key="Dalton")
q2 = Q(db_location=prison)
Character.objects.filter(q1 | ~q2)
```

将获取所有名称为 "Dalton" _或_ 不在监狱中的角色。结果是 Daltons 和非囚犯的混合。

让我们扩展我们原来的狼人查询。我们不仅想找到所有在月光下房间中具有特定 `lycanthropy` 级别的角色——我们决定如果他们 _新被咬_，他们也应该变形，_无论_ 他们的狼人症级别如何（这样更有戏剧性！）。

假设被咬意味着您将被分配一个标签 `recently_bitten`。

这就是我们更改查询的方式：

```python
from django.db.models import Q

will_transform = (
    Character.objects
    .filter(
        Q(db_location__db_tags__db_key__iexact="moonlit")
        & (
          Q(db_attributes__db_key="lycanthropy",
            db_attributes__db_value=2)
          | Q(db_tags__db_key__iexact="recently_bitten")
        ))
    .distinct()
)
```

这非常紧凑。如果这样写，可能更容易看出发生了什么：

```python
from django.db.models import Q

q_moonlit = Q(db_location__db_tags__db_key__iexact="moonlit")
q_lycanthropic = Q(db_attributes__db_key="lycanthropy", db_attributes__db_value=2)
q_recently_bitten = Q(db_tags__db_key__iexact="recently_bitten")

will_transform = (
    Character.objects
    .filter(q_moonlit & (q_lycanthropic | q_recently_bitten))
    .distinct()
)
```

```{sidebar} SQL

这些 Python 结构在内部转换为 SQL，即数据库的本机语言。如果您熟悉 SQL，这些是通过 `LEFT OUTER JOIN` 连接的多对多表，这可能导致多个合并行将同一对象与不同关系组合在一起。

```

这读作“查找所有在月光下房间中的角色，这些角色要么具有等于 2 的 `lycanthropy` 属性，要么具有 `recently_bitten` 标签”。通过这样的 OR 查询，可以通过不同的路径找到同一个角色，因此我们在末尾添加 `.distinct()`。这确保结果中每个角色只有一个实例。

## 注解

如果我们想根据对象上某个字段不易表示的条件进行过滤怎么办？一个例子是想找到只包含 _五个或更多对象_ 的房间。

我们*可以*这样做（不要这样做！）：

```python
from typeclasses.rooms import Room

all_rooms = Rooms.objects.all()

rooms_with_five_objects = []
for room in all_rooms:
    if len(room.contents) >= 5:
        rooms_with_five_objects.append(room)
```

```{sidebar} list.append, extend 和 .pop

使用 `mylist.append(obj)` 向列表添加新项目。使用 `mylist.extend(another_list))` 或 `list1 + list2` 将两个列表合并在一起。使用 `mylist.pop()` 从末尾删除一个项目，或使用 `.pop(0)` 从列表开头删除。请记住，Python 中的所有索引都从 `0` 开始。
```

上面我们获取 _所有_ 房间，然后使用 `list.append()` 不断向一个不断增长的列表中添加合适的房间。这不是一个好主意，一旦您的数据库增长，这将是计算密集型的。直接查询数据库要好得多。

_注解_ 允许您在查询中设置一个“变量”，然后可以从查询的其他部分访问它。让我们直接在数据库中进行与之前相同的示例：

```{code-block} python
:linenos:
:emphasize-lines: 6,8

from typeclasses.rooms import Room
from django.db.models import Count

rooms = (
    Room.objects
    .annotate(
        num_objects=Count('locations_set'))
    .filter(num_objects__gte=5)
)
```

```{sidebar} locations_set
注意在 `Count` 中使用 `locations_set`。`*s_set` 是 Django 自动创建的反向引用。在这种情况下，它允许您找到所有 *以当前对象为位置* 的对象。
```

`Count` 是一个 Django 类，用于计算数据库中的事物数量。

- **第 6-7 行**：在这里，我们首先创建一个类型为 `Count` 的注解 `num_objects`。它在数据库中创建一个函数，用于计算数据库内部的结果数量。注解意味着现在 `num_objects` 可以在查询的其他部分使用。
- **第 8 行** 我们根据此注解进行过滤，使用名称 `num_objects` 作为我们可以过滤的内容。我们使用 `num_objects__gte=5`，这意味着 `num_objects` 应大于或等于 5。

注解可能有点难以理解，但比在 Python 中遍历所有对象要高效得多。

## F-objects

如果我们想在查询中比较两个动态参数怎么办？例如，如果我们只想要库存比标签多的对象（虽然这是个愚蠢的例子，但...）？

这可以通过 Django 的 [F 对象](https://docs.djangoproject.com/en/4.1/ref/models/expressions/#f-expressions) 实现。所谓的 F 表达式允许您进行查询，查看数据库中每个对象的值。

```python
from django.db.models import Count, F
from typeclasses.rooms import Room

result = (
    Room.objects
    .annotate(
        num_objects=Count('locations_set'),
        num_tags=Count('db_tags'))
    .filter(num_objects__gt=F('num_tags'))
)
```

在这里，我们使用 `.annotate` 创建了两个查询中的“变量” `num_objects` 和 `num_tags`。然后我们直接在过滤器中使用这些结果。使用 `F()` 允许在过滤条件的右侧动态计算，完全在数据库内进行。

## 分组并仅返回某些属性

假设您使用标签标记某人属于一个组织。现在您想要制作一个列表，并需要一次性获取每个组织的成员数量。

`.annotate`、`.values_list` 和 `.order_by` queryset 方法对此非常有用。通常，当您运行 `.filter` 时，返回的是一堆完整的类型类实例，如玫瑰或剑。使用 `.values_list`，您可以选择只返回对象上的某些属性。`.order_by` 方法最终允许根据某个标准对结果进行排序：

```{code-block} python 
:linenos:
:emphasize-lines: 6,7,8,9 

from django.db.models import Count
from typeclasses.rooms import Room

result = (
    Character.objects
    .filter(db_tags__db_category="organization")
    .annotate(tagcount=Count('id'))
    .order_by('-tagcount'))
    .values_list('db_tags__db_key', "tagcount")
```

在这里，我们获取所有的角色，他们...
- **第 6 行**：...有一个类别为 "organization" 的标签
- **第 7 行**：...在此过程中，我们计算每个组织中找到的不同角色（每个 `id` 是唯一的）数量，并使用 `.annotate` 和 `Count` 将其存储在一个“变量” `tagcount` 中
- **第 8 行**：...我们使用此计数按 `tagcount` 的降序对结果进行排序（降序是因为有一个减号，默认是升序，但我们希望最受欢迎的组织排在第一位）。
- **第 9 行**：...最后，我们确保只返回我们想要的属性，即组织标签的名称以及我们为该组织找到的匹配数量。为此，我们在 queryset 上使用 `values_list` 方法。这将立即评估 queryset。

结果将是一个按匹配数量降序排列的元组列表，格式如下：

```
[
 ('Griatch's poets society', 3872),
 ("Chainsol's Ainneve Testers", 2076),
 ("Blaufeuer's Whitespace Fixers", 1903),
 ("Volund's Bikeshed Design Crew", 1764),
 ("Tehom's Glorious Misanthropes", 1763)
]
```

## 结论

在本课中，我们涵盖了很多内容，并涉及了几个更复杂的主题。知道如何使用 Django 进行查询是一项强大的技能。
