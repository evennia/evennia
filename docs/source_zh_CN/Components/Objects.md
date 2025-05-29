# Objects

**消息路径：**
```
┌──────┐ │   ┌───────┐    ┌───────┐   ┌──────┐
│Client├─┼──►│Session├───►│Account├──►│Object│
└──────┘ │   └───────┘    └───────┘   └──────┘
                                         ^
```

在 Evennia 中，所有游戏内的对象，无论是角色、椅子、怪物、房间还是手榴弹，都统称为 Evennia *Object*。Object 通常是你可以在游戏世界中查看和交互的东西。当消息从客户端传递时，Object 级别是最后一站。

Objects 是 Evennia 的核心，可能是你花费最多时间处理的部分。Objects 是 [Typeclassed](./Typeclasses.md) 实体。

从定义上讲，Evennia Object 是一个 Python 类，其父类之一是 [evennia.objects.objects.DefaultObject](evennia.objects.objects.DefaultObject)。Evennia 定义了 `DefaultObject` 的几个子类：

- `Object` - 基础的游戏实体。位于 `mygame/typeclasses/objects.py`。直接继承自 `DefaultObject`。
- [Characters](./Characters.md) - 正常的游戏角色，由玩家控制。位于 `mygame/typeclasses/characters.py`。继承自 `DefaultCharacter`，而 `DefaultCharacter` 是 `DefaultObject` 的子类。
- [Rooms](./Rooms.md) - 游戏世界中的位置。位于 `mygame/typeclasses/rooms.py`。继承自 `DefaultRoom`，而 `DefaultRoom` 是 `DefaultObject` 的子类。
- [Exits](./Exits.md) - 表示到另一个位置的单向连接。位于 `mygame/typeclasses/exits.py`（继承自 `DefaultExit`，而 `DefaultExit` 是 `DefaultObject` 的子类）。

## Object

**继承树：**
```
┌─────────────┐
│DefaultObject│
└──────▲──────┘
       │       ┌────────────┐
       │ ┌─────►ObjectParent│
       │ │     └────────────┘
     ┌─┴─┴──┐
     │Object│
     └──────┘
```

> 关于 `ObjectParent` 的解释，请参见下一节。

`Object` 类用于创建既不是角色、房间也不是出口的事物的基础——从武器和盔甲、设备到房屋都可以通过扩展 Object 类来表示。根据你的游戏，这也适用于 NPC 和怪物（在某些游戏中，你可能希望将 NPC 视为未被操控的 [Character](./Characters.md)）。

你不应该将 Objects 用于游戏 _系统_。不要使用“不可见”的 Object 来跟踪天气、战斗、经济或公会会员资格——这是 [Scripts](./Scripts.md) 的用途。

## ObjectParent - 添加通用功能

`Object`、`Character`、`Room` 和 `Exit` 类都继承自 `mygame.typeclasses.objects.ObjectParent`。

`ObjectParent` 是一个空的“mixin”类。你可以向这个类添加希望 _所有_ 游戏实体都具有的内容。

以下是一个示例：

```python
# 在 mygame/typeclasses/objects.py 中
# ...

from evennia.objects.objects import DefaultObject 

class ObjectParent:
    def at_pre_get(self, getter, **kwargs):
       # 默认情况下，使所有实体不可拾取
      return False
```

现在，所有的 `Object`、`Exit`、`Room` 和 `Character` 默认都不能通过 `get` 命令拾取。

## 使用 DefaultObject 的子类

此功能由 `DefaultObject` 的所有子类共享。你可以通过修改游戏目录中的某个 typeclass 或进一步继承它们来轻松添加自己的游戏行为。

你可以直接在相关模块中放置新的 typeclass，或者以其他方式组织代码。这里我们假设创建一个新的模块 `mygame/typeclasses/flowers.py`：

```python
# mygame/typeclasses/flowers.py

from typeclasses.objects import Object

class Rose(Object):
    """
    这将创建一个简单的玫瑰对象
    """    
    def at_object_creation(self):
        "这仅在对象首次创建时调用"
        # 为对象添加一个持久属性 'desc'（一个简单的示例）。
        self.db.desc = "这是一朵带刺的美丽玫瑰。"     
```

现在你只需使用 `create` 命令指向类 *Rose* 来创建一个新的玫瑰：

```
create/drop MyRose:flowers.Rose
```

`create` 命令实际上*执行*的是使用 [evennia.create_object](evennia.utils.create.create_object) 函数。你可以在代码中自己做同样的事情：

```python
from evennia import create_object
new_rose = create_object("typeclasses.flowers.Rose", key="MyRose")
```

（`create` 命令会自动附加 typeclass 的最可能路径，如果你手动输入调用，则必须提供类的完整路径。`create.create_object` 函数功能强大，应该用于所有编码对象的创建（因此这是你在定义自己的构建命令时使用的）。 

这个特定的 Rose 类实际上并没有做太多，它只是确保属性 `desc`（这是 `look` 命令查找的内容）被预设，这几乎没有意义，因为你通常希望在构建时更改它（使用 `desc` 命令或使用 [Spawner](./Prototypes.md)）。

### Object 的属性和函数

除了分配给所有 [typeclassed](./Typeclasses.md) 对象的属性（请参阅该页面以获取这些属性的列表）之外，Object 还具有以下自定义属性：

- `aliases` - 一个处理程序，允许你添加和删除此对象的别名。使用 `aliases.add()` 添加新别名，使用 `aliases.remove()` 删除别名。
- `location` - 引用当前包含此对象的对象。
- `home` 是备份位置。主要动机是如果对象的 `location` 被销毁，将对象移动到一个安全的地方。所有对象通常都应该有一个 home 位置以确保安全。
- `destination` - 这保存了一个引用，指向此对象以某种方式链接到的另一个对象。它的主要用途是用于 [Exits](./Exits.md)，否则通常未设置。
- `nicks` - 与别名不同，[Nick](./Nicks.md) 为真实名称、单词或序列提供了一个方便的昵称替换，仅对该对象有效。这主要在对象用作游戏角色时有意义——它可以存储更简短的缩写，例如快速引用游戏命令或其他角色。使用 `nicks.add(alias, realname)` 添加新昵称。
- `account` - 这保存了一个引用，指向控制此对象的连接 [Account](./Accounts.md)（如果有）。请注意，即使控制账户*不*在线，也会设置此项——要测试账户是否在线，请使用 `has_account` 属性。
- `sessions` - 如果 `account` 字段已设置*且账户在线*，这将是一个包含所有活动会话（服务器连接）的列表，以便通过它们进行联系（如果设置中允许多个连接，则可能会有多个）。
- `has_account` - 用于检查当前是否有*在线*账户连接到此对象的简写。
- `contents` - 返回一个列表，引用所有“在”此对象内部的对象（即，将此对象设置为其 `location` 的对象）。
- `exits` - 返回此对象内部的所有*Exits*对象，即已设置 `destination` 属性的对象。
- `appearance_template` - 这有助于格式化对象在被查看时的外观（参见下一节）。
- `cmdset` - 这是一个处理程序，存储对象上定义的所有 [command sets](./Command-Sets.md)（如果有）。
- `scripts` - 这是一个管理附加到对象的 [Scripts](./Scripts.md) 的处理程序（如果有）。

Object 还具有许多有用的实用函数。请参阅 `src/objects/objects.py` 中的函数头以获取其参数和更多详细信息。

- `msg()` - 此函数用于从服务器向连接到此对象的账户发送消息。
- `msg_contents()` - 在此对象内的所有对象上调用 `msg`。
- `search()` - 这是一个方便的简写，用于在给定位置或全局搜索特定对象。它主要在定义命令时有用（在这种情况下，执行命令的对象称为 `caller`，可以使用 `caller.search()` 查找房间中的对象以进行操作）。
- `execute_cmd()` - 让对象执行给定的字符串，就像在命令行中给定一样。
- `move_to` - 将此对象完全移动到新位置。这是主要的移动方法，将调用所有相关钩子，进行所有检查等。
- `clear_exits()` - 将删除所有*到*和*从*此对象的 [Exits](./Exits.md)。
- `clear_contents()` - 这不会删除任何内容，而是将所有内容（不包括 Exits）移动到其指定的 `Home` 位置。
- `delete()` - 删除此对象，首先调用 `clear_exits()` 和 `clear_contents()`。
- `return_appearance` 是让对象可视化描述其自身的主要钩子。

Object Typeclass 定义了许多*钩子方法*，除了 `at_object_creation`。Evennia 在各个点调用这些钩子。当实现自定义对象时，你将从基础父类继承并用自己的自定义代码重载这些钩子。有关所有可用钩子的更新列表，请参阅 `evennia.objects.objects` 或 [DefaultObject 的 API](evennia.objects.objects.DefaultObject)。

## 更改对象的外观

当你输入 `look <obj>` 时，会发生以下事件序列：

1. 命令检查命令的 `caller`（观察者）是否通过目标 `obj` 的 `view` [lock](./Locks.md)。如果没有，他们将找不到任何可以查看的内容（这就是你如何使对象不可见的方式）。
2. `look` 命令调用 `caller.at_look(obj)`——即调用“观察者”（命令的调用者）的 `at_look` 钩子来对目标对象执行查看。命令将回显此钩子返回的内容。
3. `caller.at_look` 调用并返回 `obj.return_apperance(looker, **kwargs)` 的结果。这里 `looker` 是命令的 `caller`。换句话说，我们要求 `obj` 向 `looker` 描述自己。
4. `obj.return_appearance` 使用其 `.appearance_template` 属性并调用一系列辅助钩子来填充此模板。默认情况下模板如下所示：

```python
appearance_template = """
{header}
|c{name}|n
{desc}
{exits}{characters}{things}
{footer}
"""
```

5. 模板的每个字段由匹配的辅助方法填充（及其默认返回值）：
    - `name` -> `obj.get_display_name(looker, **kwargs)` - 返回 `obj.name`。
    - `desc` -> `obj.get_display_desc(looker, **kwargs)` - 返回 `obj.db.desc`。
    - `header` -> `obj.get_display_header(looker, **kwargs)` - 默认情况下为空。
    - `footer` -> `obj.get_display_footer(looker, **kwargs)` - 默认情况下为空。
    - `exits` -> `obj.get_display_exits(looker, **kwargs)` - 在此对象内部找到的 `DefaultExit` 继承对象的列表（通常仅在 `obj` 是 `Room` 时存在）。
    - `characters` -> `obj.get_display_characters(looker, **kwargs)` - 此对象内部的 `DefaultCharacter` 继承实体的列表。
    - `things` -> `obj.get_display_things(looker, **kwargs)` - `obj` 内所有其他对象的列表。
6. `obj.format_appearance(string, looker, **kwargs)` 是填充模板字符串经过的最后一步。这可以用于最终调整，例如去除空格。此方法的返回值是用户将看到的内容。

由于这些钩子（以及模板本身）可以在子类中重写，因此你可以广泛自定义外观。你还可以根据观察者的不同让对象看起来不同。额外的 `**kwargs` 默认情况下未使用，但如果需要，可以用于向系统传递额外数据（如光照条件等）。
