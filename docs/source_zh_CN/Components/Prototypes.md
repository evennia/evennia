# 生成器与原型

```shell
> spawn goblin

Spawned Goblin Grunt(#45)
```

*生成器* 是一个用于从称为 *原型* 的基础模板定义和创建单个对象的系统。它仅用于游戏内的 [Objects](./Objects.md)，不适用于其他类型的实体。

在 Evennia 中创建自定义对象的常规方法是制作一个 [Typeclass](./Typeclasses.md)。如果你还没有了解过 Typeclass，可以将其视为在后台保存到数据库的普通 Python 类。假设你想创建一个“哥布林”敌人。常见的方法是首先创建一个 `Mobile` 类型类，包含游戏中所有移动对象的通用功能，如通用 AI、战斗代码和各种移动方法。然后创建一个 `Goblin` 子类继承自 `Mobile`。`Goblin` 类添加了哥布林特有的东西，比如基于团队的 AI（因为哥布林在团队中更聪明）、恐慌能力、挖金能力等。

但现在是时候实际开始创建一些哥布林并将它们放入世界中了。如果我们希望这些哥布林看起来不完全一样怎么办？也许我们想要灰皮肤和绿皮肤的哥布林，或者一些可以施法或使用不同武器的哥布林？我们 *可以* 创建 `Goblin` 的子类，比如 `GreySkinnedGoblin` 和 `GoblinWieldingClub`。但这似乎有点过于繁琐（并且为每个小东西编写大量 Python 代码）。当想要组合它们时，使用类也可能变得不切实际——如果我们想要一个灰皮肤的哥布林萨满祭司手持长矛——设置一个相互继承的类网络，使用多重继承可能会很棘手。

这就是 *原型* 的用途。它是一个描述对象这些每个实例更改的 Python 字典。原型的另一个优点是允许游戏内的构建者在不访问 Python 后端的情况下自定义对象。Evennia 还允许保存和搜索原型，以便其他构建者可以在以后找到并使用（和调整）它们。拥有一个有趣的原型库是构建者的一个很好的资源。OLC 系统允许使用菜单系统创建、保存、加载和操作原型。

*生成器* 获取一个原型并使用它创建（生成）新的自定义对象。

## 使用原型

### 使用 OLC

输入 `olc` 命令或 `spawn/olc` 进入原型向导。这是一个用于创建、加载、保存和操作原型的菜单系统。它旨在供游戏内构建者使用，并将更好地理解原型的一般概念。在菜单的每个节点上使用 `help` 获取更多信息。以下是有关原型如何工作以及如何使用它们的更多详细信息。

### 原型

原型字典可以由 OLC 为你创建（见上文），也可以在 Python 模块中手动编写（然后由 `spawn` 命令/OLC 引用），或者在运行时创建并手动加载到生成器函数或 `spawn` 命令中。

该字典定义了对象的所有可能的数据库属性。它有一组固定的允许键。在准备将原型存储在数据库中时（或使用 OLC 时），其中一些键是必需的。当仅将一次性原型字典传递给生成器时，系统会更宽松，并将对未明确提供的键使用默认值。

以字典形式，原型可以看起来像这样：

```python
{
   "prototype_key": "house",
   "key": "Large house",
   "typeclass": "typeclasses.rooms.house.House"
}
```

如果你想在游戏中将其加载到生成器中，可以将所有内容放在一行上：

```shell
spawn {"prototype_key"="house", "key": "Large house", ...}
```

> 请注意，命令行中给出的原型字典必须是有效的 Python 结构——因此你需要在字符串等周围加上引号。出于安全原因，从游戏中插入的字典不能包含任何其他高级 Python 功能，例如可执行代码、`lambda` 等。如果构建者应该能够使用此类功能，则需要通过 [$protfuncs](Spawner-and- Prototypes#protfuncs) 提供它们，嵌入可运行的函数，你可以在运行前完全控制检查和验证它们。

### 原型键

所有以 `prototype_` 开头的键用于记录。

- `prototype_key` - 原型的“名称”，用于在生成和继承时引用原型。如果在模块中定义原型并且未设置此项，它将自动设置为模块中原型变量的名称。
- `prototype_parent` - 如果给出，这应该是系统中存储的另一个原型或模块中可用的原型的 `prototype_key`。这使得这个原型可以从父级继承键，并且只覆盖所需的内容。对于多重左-右继承，给出一个元组 `(parent1, parent2, ...)`。如果未给出此项，通常应定义 `typeclass`（见下文）。
- `prototype_desc` - 这是可选的，用于在游戏内列表中列出原型时。
- `protototype_tags` - 这是可选的，允许为原型标记以便以后更容易找到它。
- `prototype_locks` - 支持两种锁类型：`edit` 和 `spawn`。第一个锁限制通过 OLC 加载时对原型的复制和编辑。第二个锁决定谁可以使用原型创建新对象。

其余键决定要从此原型生成的对象的实际方面：

- `key` - 主要对象标识符。默认为 "Spawned Object *X*"，其中 *X* 是一个随机整数。
- `typeclass` - 要使用的类型类的完整 python 路径（从你的游戏目录开始）。如果未设置，则应定义 `prototype_parent`，并在父链中的某处定义 `typeclass`。当仅为生成而创建一次性原型字典时，可以省略此项——将使用 `settings.BASE_OBJECT_TYPECLASS`。
- `location` - 这应该是一个 `#dbref`。
- `home` - 一个有效的 `#dbref`。默认为 `location` 或 `settings.DEFAULT_HOME`（如果位置不存在）。
- `destination` - 一个有效的 `#dbref`。仅由出口使用。
- `permissions` - 权限字符串列表，如 `["Accounts", "may_use_red_door"]`
- `locks` - 一个 [lock-string](./Locks.md)，如 `"edit:all();control:perm(Builder)"`
- `aliases` - 用作别名的字符串列表
- `tags` - 列表 [Tags](./Tags.md)。这些以元组 `(tag, category, data)` 的形式给出。
- `attrs` - [Attributes](./Attributes.md) 列表。这些以元组 `(attrname, value, category, lockstring)` 的形式给出。
- 任何其他关键字都被解释为无类别的 [Attributes](./Attributes.md) 及其值。这对于简单的属性很方便——使用 `attrs` 可以完全控制属性。

#### 关于原型继承的更多信息

- 可以通过定义一个 `prototype_parent` 指向另一个原型的 `prototype_key` 来继承原型。如果是 `prototype_keys` 的列表，将从左到右逐步遍历，优先考虑列表中第一个而不是后面出现的那些。也就是说，如果你的继承是 `prototype_parent = ('A', 'B,' 'C')`，并且所有父级都包含冲突的键，那么将应用 `A` 的键。
- 所有以 `prototype_*` 开头的原型键都是每个原型唯一的。它们 _从不_ 从父级继承到子级。
- 原型字段 `'attr': [(key, value, category, lockstring),...]` 和 `'tags': [(key, category, data), ...]` 以 _互补_ 的方式继承。这意味着只有冲突的键+类别匹配项会被替换，而不是整个列表。请记住，类别 `None` 也被视为有效类别！
- 将属性添加为简单的 `key:value` 将在后台转换为属性元组 `(key, value, None, '')`，并可能替换父级中的属性（如果它具有相同的键和 `None` 类别）。
- 所有其他键（`permissions`、`destination`、`aliases` 等）如果给定，将完全 _被子级的值替换_。为了保留父级的值，子级不得定义这些键。

### 原型值

原型支持多种不同类型的值。

它可以是硬编码值：

```python
{"key": "An ugly goblin", ...}
```

它也可以是一个 *可调用对象*。每当使用原型生成新对象时，此可调用对象将被调用而不带参数：

```python
{"key": _get_a_random_goblin_name, ...}
```

通过使用 Python `lambda`，可以包装可调用对象以便在原型中立即设置：

```python
{"key": lambda: random.choice(("Urfgar", "Rick the smelly", "Blargh the foul", ...)), ...}
```

#### Protfuncs

最后，值可以是 *原型函数* (*Protfunc*)。这些看起来像嵌入在字符串中的简单函数调用，并且在前面有一个 `$`，例如

```python
{"key": "$choice(Urfgar, Rick the smelly, Blargh the foul)",
 "attrs": {"desc": "This is a large $red(and very red) demon. "
                   "He has $randint(2,5) skulls in a chain around his neck."}
```

> 如果你想转义一个原型函数并让它按原样显示，请使用 `$$funcname()`。

在生成时，原型函数的位置将被该原型函数被调用的结果替换（这始终是一个字符串）。原型函数是一个 [FuncParser 函数](./FuncParser.md)，每次使用原型生成新对象时运行。有关更多信息，请参见 FuncParse。

以下是如何定义原型函数（与其他 funcparser 函数相同）。

```python
# 这是一个愚蠢的例子，你可以直接用 |r 为文本着色！
def red(*args, **kwargs):
   """
   用法: $red(<text>)
   返回你输入的相同文本，但为红色。
   """
   if not args or len(args) > 1:
      raise ValueError("必须有一个参数，即要着色为红色的文本！")
   return f"|r{args[0]}|n"
```

> 请注意，我们必须确保验证输入并在失败时引发 `ValueError`。

解析器将始终包含以下保留的 `kwargs`：
- `session` - 当前执行生成的 [Session](evennia.server.ServerSession)。
- `prototype` - 此函数所属的原型字典。此项旨在仅用于 _只读_。请注意从函数内部修改这样的可变结构——这样做可能会导致非常难以发现的错误。
- `current_key` - 执行此原型函数的 `prototype` 字典的当前键。

要使此原型函数对游戏中的构建者可用，请将其添加到新模块中，并将该模块的路径添加到 `settings.PROT_FUNC_MODULES`：

```python
# 在 mygame/server/conf/settings.py 中

PROT_FUNC_MODULES += ["world.myprotfuncs"]
```

你添加模块中的所有 *全局可调用对象* 都将被视为新的原型函数。要避免这种情况（例如，拥有不作为原型函数的辅助函数），请将你的函数命名为以 `_` 开头的名称。

默认情况下，开箱即用的原型函数在 `evennia/prototypes/profuncs.py` 中定义。要覆盖可用的原型函数，只需在自己的原型函数模块中添加同名函数。

| 原型函数 | 描述 |
| --- | --- |
| `$random()` | 返回范围 `[0, 1)` 内的随机值 |
| `$randint(start, end)` | 返回范围 [start, end] 内的随机值 |
| `$left_justify(<text>)` | 左对齐文本 |
| `$right_justify(<text>)` | 将文本右对齐到屏幕宽度 |
| `$center_justify(<text>)` | 将文本居中对齐到屏幕宽度 |
| `$full_justify(<text>)` | 通过添加空格将文本展开到屏幕宽度 |
| `$protkey(<name>)` | 返回此原型中另一个键的值（自引用） |
| `$add(<value1>, <value2>)` | 返回 value1 + value2。也可以是列表、字典等 |
| `$sub(<value1>, <value2>)` | 返回 value1 - value2 |
| `$mult(<value1>, <value2>)` | 返回 value1 * value2 |
| `$div(<value1>, <value2>)` | 返回 value2 / value1 |
| `$toint(<value>)` | 返回转换为整数的值（如果无法转换，则返回值） |
| `$eval(<code>)` | 返回 [literal-eval](https://docs.python.org/2/library/ast.html#ast.literal_eval) 的代码字符串的结果。仅限简单的 python 表达式。 |
| `$obj(<query>)` | 返回通过键、标签或 #dbref 全局搜索的对象 #dbref。如果找到多个，则出错。 |
| `$objlist(<query>)` | 类似于 `$obj`，但始终返回零个、一个或多个结果的列表。 |
| `$dbref(dbref)` | 如果参数的格式为 #dbref（例如 #1234），则返回参数，否则出错。 |

对于有 Python 访问权限的开发人员，在原型中使用原型函数通常没有用。传递真实的 Python 函数更加强大和灵活。它们的主要用途是允许游戏中的构建者为其原型进行有限的编码/脚本编写，而无需直接访问原始 Python。

## 数据库原型

作为 [Scripts](./Scripts.md) 存储在数据库中。这些有时被称为 *数据库原型*。这是游戏内构建者修改和添加原型的唯一方法。它们的优点是可以轻松地在构建者之间修改和共享，但你需要使用游戏内工具来处理它们。

## 基于模块的原型

这些原型在 `settings.PROTOTYPE_MODULES` 中定义为分配给全局变量的字典。它们只能从游戏外部修改，因此它们在游戏内是“只读”的，不能被修改（但可以将它们的副本制成数据库原型）。这些是 Evennia 0.8 之前唯一可用的原型。基于模块的原型可以为开发人员提供只读的“起始”或“基础”原型，以便构建，或者如果他们只是更喜欢在外部代码编辑器中离线工作。

默认情况下，`mygame/world/prototypes.py` 已为你设置好以添加你自己的原型。*此模块中的所有全局字典* 将被 Evennia 视为原型。你也可以告诉 Evennia 在更多模块中查找原型：

```python
# 在 mygame/server/conf.py 中

PROTOTYPE_MODULES += ["world.myownprototypes", "combat.prototypes"]
```

以下是一个在模块中定义的原型示例：

```python
# 在 Evennia 查找原型的模块中，
# （如 mygame/world/prototypes.py）

ORC_SHAMAN = {"key": "Orc shaman",
              "typeclass": "typeclasses.monsters.Orc",
              "weapon": "wooden staff",
              "health": 20}
```

> 请注意，在上面的示例中，`"ORC_SHAMAN"` 将成为此原型的 `prototype_key`。这是唯一可以在原型中跳过 `prototype_key` 的情况。但是，如果显式给出了 `prototype_key`，则会优先考虑。这是一种遗留行为，建议始终添加 `prototype_key` 以保持一致性。

## 生成

生成器可以通过仅限构建者的 `@spawn` 命令从游戏内部使用。假设系统中有可用的“goblin”类型类（无论是作为数据库原型还是从模块读取），你可以生成一个新的哥布林：

```shell
spawn goblin
```

你还可以将原型直接指定为有效的 Python 字典：

```shell
spawn {"prototype_key": "shaman", \
       "key": "Orc shaman", \
       "prototype_parent": "goblin", \
       "weapon": "wooden staff", \
       "health": 20}
```

> 注意：`spawn` 命令对原型字典的要求比此处显示的更宽松。因此，如果你只是在测试一个一次性原型，可以跳过 `prototype_key`。会使用一个随机哈希以满足验证。你还可以跳过 `prototype_parent/typeclass`——然后将使用 `settings.BASE_OBJECT_TYPECLASS` 中给出的类型类。

### 使用 evennia.prototypes.spawner()

在代码中，你可以通过调用直接访问生成器机制：

```python
new_objects = evennia.prototypes.spawner.spawn(*prototypes)
```

所有参数都是原型字典。该函数将返回一个与创建的对象匹配的列表。示例：

```python
obj1, obj2 = evennia.prototypes.spawner.spawn({"key": "Obj1", "desc": "A test"},
                                              {"key": "Obj2", "desc": "Another test"})
```

> 提示：与使用 `spawn` 时一样，当从这样的一次性原型字典生成时，可以跳过其他必需的键，如 `prototype_key` 或 `typeclass`/`prototype_parent`。将使用默认值。

请注意，当使用 `evennia.prototypes.spawner.spawn()` 时，不会自动设置 `location`，你必须在原型字典中显式指定 `location`。如果你提供的原型使用 `prototype_parent` 关键字，生成器将从 `settings.PROTOTYPE_MODULES` 中的模块以及保存到数据库中的原型中读取原型，以确定可用父级的主体。`spawn` 命令接受许多可选关键字，你可以在 [API 文档](https://www.evennia.com/docs/latest/api/evennia.prototypes.spawner.html#evennia.prototypes.spawner.spawn) 中找到其定义。
