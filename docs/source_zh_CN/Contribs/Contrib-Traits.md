# 特质

由 Griatch 于 2020 年贡献，基于 Whitenoise 和 Ainneve 的贡献代码，2014 年

`Trait` 代表一个（通常是）角色上的可修改属性。它们可以用于表示从属性（力量、敏捷等）到技能（狩猎 10、剑术 14 等）以及动态变化的事物（如 HP、XP 等）。特质与普通属性的不同之处在于，它们跟踪其变化并限制在特定的数值范围内。可以轻松地对它们进行加减运算，甚至可以以特定的速率动态变化（例如中毒或治疗）。

特质在底层使用 Evennia 属性，使其具有持久性（即使服务器重载/重启也能保留）。

## 安装

特质总是添加到类型类中，例如角色类。

有两种方法可以在类型类上设置特质。第一种方法是在类上设置 `TraitHandler` 作为属性 `.traits`，然后可以通过 `.traits.strength` 访问特质。另一种方法使用 `TraitProperty`，使特质可以直接通过 `.strength` 访问。这种解决方案也使用 `TraitHandler`，但不需要显式定义它。如果愿意，可以结合两种风格。

### 使用 TraitHandler 的特质

以下是将 TraitHandler 添加到角色类的示例：

```python
# mygame/typeclasses/objects.py

from evennia import DefaultCharacter
from evennia.utils import lazy_property
from evennia.contrib.rpg.traits import TraitHandler

# ...

class Character(DefaultCharacter):
    ...
    @lazy_property
    def traits(self):
        # 这将处理程序添加为 .traits
        return TraitHandler(self)

    def at_object_creation(self):
        # （或在你想要的地方）
        self.traits.add("str", "Strength", trait_type="static", base=10, mod=2)
        self.traits.add("hp", "Health", trait_type="gauge", min=0, max=100)
        self.traits.add("hunting", "Hunting Skill", trait_type="counter",
                        base=10, mod=1, min=0, max=100)
```

添加特质时，您需要提供属性的名称（`hunting`）以及更易于理解的名称（"Hunting Skill"）。后者将在打印特质等时显示。`trait_type` 很重要，它指定了特质的类型（见下文）。

### TraitProperties

使用 `TraitProperties` 可以直接在类上访问特质，类似于 Django 模型字段。缺点是必须确保特质的名称不会与类上的其他属性/方法冲突。

```python
# mygame/typeclasses/objects.py

from evennia import DefaultObject
from evennia.utils import lazy_property
from evennia.contrib.rpg.traits import TraitProperty

# ...

class Object(DefaultObject):
    ...
    strength = TraitProperty("Strength", trait_type="static", base=10, mod=2)
    health = TraitProperty("Health", trait_type="gauge", min=0, base=100, mod=2)
    hunting = TraitProperty("Hunting Skill", trait_type="counter", base=10, mod=1, min=0, max=100)
```

> 请注意，属性名称将成为特质的名称，您不需要单独提供 `trait_key`。

> `.traits` TraitHandler 仍将被创建（它在底层使用）。但它只有在 TraitProperty 至少被访问过一次后才会被创建，因此如果混合使用两种风格要小心。如果想确保 `.traits` 始终可用，请像之前那样手动添加 `TraitHandler`——`TraitProperty` 默认会使用相同的处理程序（`.traits`）。

## 使用特质

特质是在 traithandler 中添加的实体（如果使用 `TraitProperty`，处理程序只是底层创建的），之后可以作为处理程序上的属性访问（类似于在 Evennia 中使用 `.db.attrname` 访问属性）。

所有特质都有一个只读字段 `.value`。这仅用于读取结果，不能直接操作它（如果尝试，它将保持不变）。`.value` 是基于组合字段（如 `.base` 和 `.mod`）计算的——可用字段及其相互关系取决于特质类型。

```python
> obj.traits.strength.value
12  # base + mod

> obj.traits.strength.base += 5
obj.traits.strength.value
17

> obj.traits.hp.value
102  # base + mod

> obj.traits.hp.base -= 200
> obj.traits.hp.value
0  # 最小值为 0

> obj.traits.hp.reset()
> obj.traits.hp.value
100

# 也可以像字典一样访问属性
> obj.traits.hp["value"]
100

# 可以持久存储任意数据以便于引用
> obj.traits.hp.effect = "poisoned!"
> obj.traits.hp.effect
"poisoned!"

# 使用 TraitProperties:

> obj.hunting.value
12

> obj.strength.value += 5
> obj.strength.value
17
```

### 关联特质

从特质可以通过 `.traithandler` 访问其自己的 Traithandler。还可以使用 `Trait.get_trait("traitname")` 方法在同一处理程序中找到另一个特质。

```python
> obj.strength.get_trait("hp").value
100
```

对于默认特质类型，这不是特别有用——它们都是独立运行的。但如果创建自己的特质类，可以使用它来创建相互依赖的特质。

例如，可以设想创建一个特质，该特质是两个其他特质值的总和，并由第三个特质的值限制。这种复杂的交互在 RPG 规则系统中很常见，但定义上是特定于游戏的。

请参阅有关[创建自己的特质类](#expanding-with-your-own-traits)部分的示例。

## 特质类型

所有默认特质都有一个只读的 `.value` 属性，显示特质的相关或“当前”值。这具体意味着什么取决于特质的类型。

如果两个特质的类型兼容，特质也可以组合进行算术运算。

```python
> trait1 + trait2
54

> trait1.value
3

> trait1 + 2
> trait1.value
5
```

两个数值特质也可以进行比较（大于等），这在各种规则解析中很有用。

```python
if trait1 > trait2:
    # 执行操作
```

### Trait

任何类型的单个值。

这是“基本”特质，如果想从头开始发明特质类型，可以从中继承（大多数情况下，可能会从一些更高级的特质类型类继承）。

与其他特质类型不同，基本 `Trait` 的单个 `.value` 属性可以编辑。该值可以保存任何可以存储在属性中的数据。如果是整数/浮点数，可以进行算术运算，否则它就像一个高级属性。

```python
> obj.traits.add("mytrait", "My Trait", trait_type="trait", value=30)
> obj.traits.mytrait.value
30

> obj.traits.mytrait.value = "stringvalue"
> obj.traits.mytrait.value
"stringvalue"
```

### 静态特质

`value = base + mod`

静态特质具有一个 `base` 值和一个可选的 `mod`-ifier。静态特质的典型用途是力量统计或技能值。也就是说，变化缓慢或根本不变的东西，可以在原地修改。

```python
> obj.traits.add("str", "Strength", trait_type="static", base=10, mod=2)
> obj.traits.mytrait.value

12  # base + mod
> obj.traits.mytrait.base += 2
> obj.traits.mytrait.mod += 1
> obj.traits.mytrait.value
15

> obj.traits.mytrait.mod = 0
> obj.traits.mytrait.value
12
```

### 计数器

```
min/unset     base    base+mod                       max/unset
|--------------|--------|---------X--------X------------|
                              current    value
                                         = current
                                         + mod
```

计数器描述了一个可以从基值移动的值。`.current` 属性通常是被修改的对象。它从 `.base` 开始。还可以添加一个修饰符，该修饰符将同时添加到基值和当前值（形成 `.value`）。范围的最小值/最大值是可选的，设置为 None 的边界将移除它。建议将计数器特质用于跟踪技能值。

```python
> obj.traits.add("hunting", "Hunting Skill", trait_type="counter",
                   base=10, mod=1, min=0, max=100)
> obj.traits.hunting.value
11  # current 从 base + mod 开始

> obj.traits.hunting.current += 10
> obj.traits.hunting.value
21

# 删除 current 重置回 base+mod
> del obj.traits.hunting.current
> obj.traits.hunting.value
11
> obj.traits.hunting.max = None  # 移除上限

# 对于 TraitProperties，将 traits.add() 的 args/kwargs 传递给
# TraitProperty 构造函数即可。
```

计数器有一些额外的属性：

#### .descs

`descs` 属性是一个字典 `{upper_bound:text_description}`。这允许轻松存储当前值在区间中的更易于理解的描述。以下是技能值在 0 到 10 之间的示例：

```python
{0: "unskilled", 1: "neophyte", 5: "trained", 7: "expert", 9: "master"}
```

键必须从最小到最大提供。任何低于最低和高于最高描述的值将被视为包含在最接近的描述槽中。通过调用计数器上的 `.desc()`，将获得与当前 `value` 匹配的文本。

```python
# （也可以将 descs= 传递给 traits.add()）
> obj.traits.hunting.descs = {
    0: "unskilled", 10: "neophyte", 50: "trained", 70: "expert", 90: "master"}
> obj.traits.hunting.value
11

> obj.traits.hunting.desc()
"neophyte"
> obj.traits.hunting.current += 60
> obj.traits.hunting.value
71

> obj.traits.hunting.desc()
"expert"
```

#### .rate

`rate` 属性默认为 0。如果设置为不同于 0 的值，则允许特质动态更改值。这可以用于例如一个属性暂时降低但在一段时间后逐渐（或突然）恢复。速率以每秒 `.value` 的变化量给出，这仍将受到 min/max 边界的限制（如果设置了这些边界）。

还可以设置 `.ratetarget`，以便自动更改在此处停止（而不是在 min/max 边界处）。这允许值返回到先前的值。

```python
> obj.traits.hunting.value
71

> obj.traits.hunting.ratetarget = 71
# 由于某种原因降低狩猎技能
> obj.traits.hunting.current -= 30
> obj.traits.hunting.value
41

> obj.traits.hunting.rate = 1  # 每秒增加 1
# 等待 5 秒
> obj.traits.hunting.value
46

# 等待 8 秒
> obj.traits.hunting.value
54

# 等待 100 秒
> obj.traits.hunting.value
71  # 我们在 ratetarget 停止

> obj.traits.hunting.rate = 0  # 禁用自动更改
```

请注意，当检索 `current` 时，即使 `rate` 是非整数值，结果也将始终与 `.base` 类型相同。因此，如果 `base` 是 `int`（默认），则 `current` 值也将四舍五入到最接近的整数。如果想查看确切的 `current` 值，请将 `base` 设置为浮点数——然后需要在结果上自己使用 `round()`。

#### .percent()

如果定义了 min 和 max，特质的 `.percent()` 方法将返回值的百分比。

```python
> obj.traits.hunting.percent()
"71.0%"

> obj.traits.hunting.percent(formatting=None)
71.0
```

### 仪表

这模拟了一个[燃料]仪表，从基值+mod 值开始清空。

```
min/0                                            max=base+mod
 |-----------------------X---------------------------|
                       value
                      = current
```

`.current` 值将从满量表开始。`.max` 属性是只读的，由 `.base` + `.mod` 设置。因此，与 `Counter` 相反，`.mod` 修饰符仅适用于仪表的最大值，而不适用于当前值。最小边界默认为 0（如果未显式设置）。

此特质适用于显示常见的可消耗资源，如健康、耐力等。

```python
> obj.traits.add("hp", "Health", trait_type="gauge", base=100)
> obj.traits.hp.value  # （或 .current）
100

> obj.traits.hp.mod = 10
> obj.traits.hp.value
110

> obj.traits.hp.current -= 30
> obj.traits.hp.value
80
```

仪表特质是计数器的子类，因此可以在适当的地方访问相同的方法和属性。因此，仪表也可以有一个 `.descs` 字典来描述区间的文本，并可以使用 `.percent()` 来获取它的填充百分比等。

`.rate` 对于仪表特别相关——从毒药慢慢消耗你的健康到休息逐渐增加它，这都是有用的。

## 扩展自己的特质

特质是一个从 `evennia.contrib.rpg.traits.Trait`（或从现有的特质类之一）继承的类。

```python
# 在一个文件中，例如 'mygame/world/traits.py'

from evennia.contrib.rpg.traits import StaticTrait

class RageTrait(StaticTrait):

    trait_type = "rage"
    default_keys = {
        "rage": 0
    }

    def berserk(self):
        self.mod = 100

    def sedate(self):
        self.mod = 0
```

以上是一个示例自定义特质类“rage”，它在自身上存储一个属性“rage”，默认值为 0。这具有特质的所有功能——例如，如果对 `rage` 属性执行 del 操作，它将被重置为默认值（0）。上面我们还添加了一些辅助方法。

要将自定义 RageTrait 添加到 Evennia，请将以下内容添加到设置文件中（假设类位于 mygame/world/traits.py 中）：

```python
TRAIT_CLASS_PATHS = ["world.traits.RageTrait"]
```

重新加载服务器，现在应该可以使用特质了：

```python
> obj.traits.add("mood", "A dark mood", rage=30, trait_type='rage')
> obj.traits.mood.rage
30
```

请记住，可以使用 `.get_trait("name")` 访问同一处理程序上的其他特质。假设愤怒修饰符实际上受角色当前 STR 值的 3 倍限制，最大为 100：

```python
class RageTrait(StaticTrait):
    #...
    def berserk(self):
        self.mod = min(100, self.get_trait("STR").value * 3)
```

# 作为 TraitProperty

```python
class Character(DefaultCharacter):
    rage = TraitProperty("A dark mood", rage=30, trait_type='rage')
```

## 添加额外的 TraitHandlers

有时，顶级分类特质更容易，例如统计、技能或其他想要独立处理的特质类别。以下是对象类型类上的示例，扩展了第一个安装示例：

```python
# mygame/typeclasses/objects.py

from evennia import DefaultCharacter
from evennia.utils import lazy_property
from evennia.contrib.rpg.traits import TraitHandler

# ...

class Character(DefaultCharacter):
    ...
    @lazy_property
    def traits(self):
        # 这将处理程序添加为 .traits
        return TraitHandler(self)

    @lazy_property
    def stats(self):
        # 这将处理程序添加为 .stats
        return TraitHandler(self, db_attribute_key="stats")

    @lazy_property
    def skills(self):
        # 这将处理程序添加为 .skills
        return TraitHandler(self, db_attribute_key="skills")

    def at_object_creation(self):
        # （或在你想要的地方）
        self.stats.add("str", "Strength", trait_type="static", base=10, mod=2)
        self.traits.add("hp", "Health", trait_type="gauge", min=0, max=100)
        self.skills.add("hunting", "Hunting Skill", trait_type="counter",
                        base=10, mod=1, min=0, max=100)
```

> 请记住，`.get_traits()` 方法仅适用于访问同一 TraitHandler 中的特质。


----

<small>此文档页面并非由 `evennia/contrib/rpg/traits/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
