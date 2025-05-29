# 让对象持久化

现在我们已经了解了一些如何在 Evennia 库中找到东西的知识，让我们来使用它。

在 [Python 类和对象](./Beginner-Tutorial-Python-classes-and-objects.md) 课程中，我们创建了龙 Fluffy、Cuddly 和 Smaug，并让它们飞翔和喷火。到目前为止，我们的龙是短暂的——每当我们 `restart` 服务器或 `quit()` 退出 Python 模式时，它们就消失了。

这是你在 `mygame/typeclasses/monsters.py` 中应该有的代码：

```python
class Monster:
    """
    This is a base class for Monsters.
    """
 
    def __init__(self, key):
        self.key = key 

    def move_around(self):
        print(f"{self.key} is moving!")


class Dragon(Monster):
    """
    This is a dragon-specific monster.
    """

    def move_around(self):
        super().move_around()
        print("The world trembles.")

    def firebreath(self):
        """ 
        Let our dragon breathe fire.
        """
        print(f"{self.key} breathes fire!")
```

## 我们的第一个持久化对象

此时，我们应该足够了解 `mygame/typeclasses/objects.py` 中发生的事情。让我们打开它：

```python
"""
module docstring
"""
from evennia import DefaultObject

class ObjectParent:
    """ 
    class docstring 
    """
    pass

class Object(ObjectParent, DefaultObject):
    """
    class docstring
    """
    pass
```

我们有一个类 `Object`，它继承自 `ObjectParent`（它是空的）和从 Evennia 导入的 `DefaultObject`。`ObjectParent` 作为一个放置代码的地方，你希望所有的 `Objects` 都拥有这些代码。我们现在将重点放在 `Object` 和 `DefaultObject` 上。

类本身并没有做任何事情（它只是 `pass`），但这并不意味着它是无用的。正如我们所见，它继承了其父类的所有功能。实际上，它现在是 `DefaultObject` 的一个_精确副本_。一旦我们知道 `DefaultObject` 上有哪些方法和资源可用，我们就可以添加自己的方法并改变其工作方式！

Evennia 类提供的一个功能，而你在普通 Python 类中没有的，就是_持久性_——它们在服务器重载后仍然存在，因为它们存储在数据库中。

回到 `mygame/typeclasses/monsters.py`。将其更改如下：

```python
from typeclasses.objects import Object

class Monster(Object):
    """
    This is a base class for Monsters.
    """
    def move_around(self):
        print(f"{self.key} is moving!")


class Dragon(Monster):
    """
    This is a dragon-specific Monster.
    """

    def move_around(self):
        super().move_around()
        print("The world trembles.")

    def firebreath(self):
        """ 
        Let our dragon breathe fire.
        """
        print(f"{self.key} breathes fire!")
```

别忘了保存。我们移除了 `Monster.__init__` 并让 `Monster` 继承自 Evennia 的 `Object`（而 `Object` 又继承自 Evennia 的 `DefaultObject`，如我们所见）。这意味着 `Dragon` 也继承自 `DefaultObject`，只是距离更远一些！

### 通过调用类创建新对象

首先像往常一样重载服务器。这次我们需要以稍微不同的方式创建龙：

```{sidebar} 关键字参数

_关键字参数_（如 `db_key="Smaug"`）是一种为函数或方法的输入参数命名的方式。它们使代码更易于阅读，同时也允许为未显式给出的值方便地设置默认值。我们之前在 `.format()` 中看到了它们的用法。

```

```plaintext
> py
> from typeclasses.monsters import Dragon
> smaug = Dragon(db_key="Smaug", db_location=here)
> smaug.save()
> smaug.move_around()
Smaug is moving!
The world trembles.
```

Smaug 的工作原理与之前相同，但我们以不同的方式创建了它：首先我们使用 `Dragon(db_key="Smaug", db_location=here)` 创建对象，然后使用 `smaug.save()` 保存它。

```{sidebar} here
`db_location=here` 中使用的 `here` 是你当前所在位置的快捷方式。这个 `here`（类似于 `me`）_仅_在 `py` 命令中可用；除非你自己定义它，否则不能在其他 Python 代码中使用。
```

```plaintext
> quit()
Python Console is closing.
> look 
```

你现在应该看到 Smaug _在房间里与你同在_。哇！

```plaintext
> reload 
> look 
```

_它仍然在那里_……我们刚刚做的是为 Smaug 在数据库中创建了一个新条目。我们给对象命名（key）并将其位置设置为我们当前的位置。

要在代码中使用 Smaug，我们必须首先在数据库中找到它。对于当前位置的对象，我们可以在 `py` 中通过使用 `me.search()` 轻松完成：

```plaintext
> py smaug = me.search("Smaug") ; smaug.firebreath()
Smaug breathes fire!
```

### 使用 create_object 创建

像我们上面那样创建 Smaug 很好，因为它类似于我们之前创建非数据库绑定 Python 实例的方式。但你需要使用 `db_key` 而不是 `key`，并且还需要记得之后调用 `.save()`。Evennia 有一个更常用的辅助函数，称为 `create_object`。让我们这次重新创建 Cuddly：

```plaintext
> py evennia.create_object('typeclasses.monsters.Monster', key="Cuddly", location=here)
> look 
```

砰，Cuddly 现在应该在房间里与你同在，比 Smaug 稍微不那么可怕。你指定了你想要的代码的 Python 路径，然后设置 key 和 location（如果你已经导入了 `Monster` 类，你也可以传递它）。Evennia 为你设置好一切并保存。

如果你想从任何地方（而不仅仅是在同一个房间）找到 Cuddly，可以使用 Evennia 的 `search_object` 函数：

```plaintext
> py cuddly = evennia.search_object("Cuddly")[0] ; cuddly.move_around()
Cuddly is moving!
```

> `[0]` 是因为 `search_object` 总是返回一个包含零个、一个或多个找到的对象的_列表_。`[0]` 表示我们想要这个列表的第一个元素（Python 中的计数总是从 0 开始）。如果有多个 Cuddly，我们可以通过 `[1]` 获取第二个。

### 使用 create 命令创建

最后，你还可以使用我们在几节课前探索过的熟悉的构建器命令创建一个新龙：

```plaintext
> create/drop Fluffy:typeclasses.monsters.Dragon
```

Fluffy 现在在房间里。了解对象是如何创建的后，你会意识到这个命令所做的就是解析你的输入，找出 `/drop` 意味着“将对象的位置设置为调用者的位置”，然后进行一个非常类似于

```plaintext
evennia.create_object("typeclasses.monsters.Dragon", key="Cuddly", location=here)
```

的调用。这就是强大的 `create` 命令的全部内容！其余的只是解析命令以理解用户想要创建什么。

## 类型类

我们上面继承的 `Object`（和 `DefaultObject` 类）就是我们所说的_类型类_。这是 Evennia 的一个概念。类型类的实例在创建时会保存到数据库中，之后你可以通过搜索找到它。

我们使用术语_类型类_或_类型化_来区分这些类型的类和对象与普通 Python 类，它们的实例在重载时会消失。

Evennia 中的类型类数量很少，可以通过记忆来学习：

| Evennia 基础类型类 | mygame.typeclasses 子类 | 描述 |
| ------------------ | ---------------------- | ---- |
| `evennia.DefaultObject` | `typeclasses.objects.Object` | 具有位置的所有事物 |
| `evennia.DefaultCharacter`（`DefaultObject` 的子类） | `typeclasses.characters.Character` | 玩家化身 |
| `evennia.DefaultRoom`（`DefaultObject` 的子类） | `typeclasses.rooms.Room` | 游戏内位置 |
| `evennia.DefaultExit`（`DefaultObject` 的子类） | `typeclasses.exits.Exit` | 房间之间的链接 |
| `evennia.DefaultAccount` | `typeclasses.accounts.Account` | 玩家账户 |
| `evennia.DefaultChannel` | `typeclasses.channels.Channel` | 游戏内通信 |
| `evennia.DefaultScript` | `typeclasses.scripts.Script` | 无位置的实体 |

`mygame/typeclasses/` 下的子类是为了方便你修改和使用的。每个继承自 Evennia 基础类型类的类（无论距离多远）也被视为类型类。

```python
from somewhere import Something 
from evennia import DefaultScript 

class MyOwnClass(Something): 
    # 不继承自 Evennia 核心类型类，所以这只是一个继承自某处的“普通” Python 类
    pass 

class MyOwnClass2(DefaultScript):
    # 继承自 Evennia 核心类型类之一，所以这也被视为“类型类”。
    pass
```

```{sidebar} 为什么要发明“类型类”这个名称？
我们将“常规类”与“类型类”分开，因为虽然类型类的行为_几乎_像普通 Python 类，[但有一些不同之处](../../../Components/Typeclasses.md)。我们现在会略过这些差异，但当你想做更高级的事情时，它们值得一读。
```

注意 `mygame/typeclasses/` 中的类_没有相互继承_。例如，`Character` 继承自 `evennia.DefaultCharacter` 而不是 `typeclasses.objects.Object`。所以如果你更改 `Object`，你不会对 `Character` 类产生任何影响。如果你想要那样，你可以轻松地更改子类以那种方式继承；Evennia 并不在意。

正如我们在 `Dragon` 示例中看到的，你不_必须_直接修改这些模块。你可以创建自己的模块并导入基础类。

### 检查对象

当你执行

```plaintext
> create/drop giantess:typeclasses.monsters.Monster
You create a new Monster: giantess.
```

或

```plaintext
> py evennia.create_object("typeclasses.monsters.Monster", key="Giantess", location=here)
```

你正在指定要用哪个类型类来构建 Giantess。让我们检查结果：

```plaintext
> examine giantess
-------------------------------------------------------------------------------
Name/key: Giantess (#14)
Typeclass: Monster (typeclasses.monsters.Monster)
Location: Limbo (#2)
Home: Limbo (#2)
Permissions: <None>
Locks: call:true(); control:id(1) or perm(Admin); delete:id(1) or perm(Admin);
   drop:holds(); edit:perm(Admin); examine:perm(Builder); get:all();
   puppet:pperm(Developer); tell:perm(Admin); view:all()
Persistent attributes:
 desc = You see nothing special. 
-------------------------------------------------------------------------------
```

我们在 [关于游戏内建造的课程](./Beginner-Tutorial-Building-Quickstart.md) 中简要使用了 `examine` 命令。现在这些行可能对我们更有用：
- **Name/key** - 此事物的名称。值 `(#14)` 可能与你的不同。这是数据库中该实体的唯一“主键”或 _dbref_。
- **Typeclass**: 这显示了我们指定的类型类以及其路径。
- **Location**: 我们在 Limbo。如果你移动到其他地方，你会看到相应的变化。Limbo 的 `#dbref` 也会显示。
- **Home**: 所有具有位置的对象（继承自 `DefaultObject`）必须有一个家庭位置。如果当前的位置被删除，这是一个备份位置。
- **Permissions**: _权限_ 类似于 _锁_ 的反面——它们就像解锁访问其他事物的钥匙。巨人没有这样的钥匙（也许幸运的是）。[权限](../../../Components/Permissions.md) 有更多信息。
- **Locks**: 锁是 _权限_ 的反面——指定其他对象必须满足什么条件才能访问 `giantess` 对象。这使用一个非常灵活的小型语言。例如，行 `examine:perm(Builders)` 被读取为“只有具有 _Builder_ 权限或更高权限的人才能 _examine_ 此对象”。由于我们是超级用户，我们可以轻松通过（甚至绕过）这些锁。有关更多信息，请参阅 [Locks](../../../Components/Locks.md) 文档。
- **Persistent attributes**: 这允许在类型化实体上存储任意的持久数据。我们将在下一节中介绍这些。

注意 **Typeclass** 行如何准确描述在哪里可以找到此对象的代码？这对于理解 Evennia 中的任何对象如何工作非常有用。

### 默认类型类

如果我们创建一个对象而_不_指定其类型类，会发生什么？

```plaintext
> create/drop box 
You create a new Object: box.
```

或

```plaintext
> py create.create_object(None, key="box", location=here)
```

现在检查它：

```plaintext
> examine box  
```

你会发现 **Typeclass** 行现在显示

```plaintext
Typeclass: Object (typeclasses.objects.Object) 
```

所以当你没有指定类型类时，Evennia 使用了一个默认值，更具体地说是 `mygame/typeclasses/objects.py` 中的（到目前为止）空的 `Object` 类。这通常是你想要的，特别是因为你可以根据需要调整该类。

但 Evennia 知道回退到这个类的原因不是硬编码的——这是一个设置。默认值在 [evennia/settings_default.py](../../../Setup/Settings-Default.md) 中，名称为 `BASE_OBJECT_TYPECLASS`，设置为 `typeclasses.objects.Object`。

```{sidebar} 更改内容

虽然根据你的喜好更改文件夹是很诱人的，但这可能会使跟随教程变得更困难，并可能在你向他人寻求帮助时产生困惑。所以除非你真的知道自己在做什么，否则不要过度更改。
```

因此，如果你希望创建命令和方法默认使用其他类，你可以在 `mygame/server/conf/settings.py` 中添加自己的 `BASE_OBJECT_TYPECLASS` 行。对于所有其他类型类，如角色、房间和账户，情况也是如此。这样，如果你愿意，可以大大改变游戏目录的布局。你只需告诉 Evennia 每个东西在哪里。

## 修改我们自己

让我们尝试稍微修改一下自己。打开 `mygame/typeclasses/characters.py`。

```python
"""
(module docstring)
"""
from evennia import DefaultCharacter
from .objects import ObjectParent

class Character(ObjectParent, DefaultCharacter):
    """
    (class docstring)
    """
    pass
```

这看起来很熟悉——一个空类继承自 Evennia 基础类型类 `ObjectParent`。`ObjectParent`（默认情况下为空）也在这里，用于添加所有类型对象共享的任何功能。正如你所料，这也是创建角色时默认使用的类型类。你可以验证一下：

```plaintext
> examine me
------------------------------------------------------------------------------
Name/key: YourName (#1)
Session id(s): #1
Account: YourName
Account Perms: <Superuser> (quelled)
Typeclass: Character (typeclasses.characters.Character)
Location: Limbo (#2)
Home: Limbo (#2)
Permissions: developer, player
Locks:      boot:false(); call:false(); control:perm(Developer); delete:false();
      drop:holds(); edit:false(); examine:perm(Developer); get:false();
      msg:all(); puppet:false(); tell:perm(Admin); view:all()
Stored Cmdset(s):
 commands.default_cmdsets.CharacterCmdSet [DefaultCharacter] (Union, prio 0)
Merged Cmdset(s):
   ...
Commands available to YourName (result of Merged CmdSets):
   ...
Persistent attributes:
 desc = This is User #1.
 prelogout_location = Limbo
Non-Persistent attributes:
 last_cmd = None
------------------------------------------------------------------------------
```

是的，`examine` 命令理解 `me`。这次你得到了更长的输出。你比一个简单的对象有更多的东西。这里有一些值得注意的新字段：

- **Session id(s)**: 这标识了_会话_（即与玩家游戏客户端的单个连接）。
- **Account** 显示了与此角色和会话关联的 `Account` 对象。
- **Stored/Merged Cmdsets** 和 **Commands available** 与存储在你身上的_命令_有关。我们将在[下一课](./Beginner-Tutorial-Adding-Commands.md)中介绍它们。现在知道这些构成了在给定时刻可用的所有命令就足够了。
- **Non-Persistent attributes** 是仅临时存储的属性，并将在下次重载时消失。

查看 **Typeclass** 字段，你会发现它指向 `typeclasses.character.Character`，正如预期的那样。所以如果我们修改这个类，我们也会修改我们自己。

### 在我们自己身上添加一个方法

让我们先尝试一些简单的事情。回到 `mygame/typeclasses/characters.py`：

```python
# in mygame/typeclasses/characters.py

# ...

class Character(ObjectParent, DefaultCharacter):
    """
    (class docstring)
    """

    strength = 10
    dexterity = 12
    intelligence = 15

    def get_stats(self):
        """
        Get the main stats of this character
        """
        return self.strength, self.dexterity, self.intelligence
```

```plaintext
> reload 
> py self.get_stats()
(10, 12, 15)
```

```{sidebar} 元组和列表

- `list` 写作 `[a, b, c, d, ...]`。它可以在创建后修改。
- `tuple` 写作 `(a, b, c, ...)`。一旦创建就无法修改。
```

我们创建了一个新方法，给它一个文档字符串，并让它返回我们设置的角色扮演值。它以一个_元组_ `(10, 12, 15)` 的形式返回。要获取特定值，你可以指定你想要的值的_索引_，从零开始：

```plaintext
> py stats = self.get_stats() ; print(f"Strength is {stats[0]}.")
Strength is 10.
```

### 属性

那么当我们增加力量时会发生什么？这是一种方法：

```plaintext
> py self.strength = self.strength + 1
> py self.strength
11
```

这里我们将力量设置为其先前值加 1。使用 Python 的 `+=` 运算符可以更简洁地写：

```plaintext
> py self.strength += 1
> py self.strength
12     
> py self.get_stats()
(12, 12, 15)
```

这看起来是正确的！尝试更改敏捷和智力的值；它工作正常。然而：

```plaintext
> reload 
> py self.get_stats()
(10, 12, 15)
```

重载后我们所有的更改都被遗忘了。当我们这样更改属性时，它只在内存中更改，而不在数据库中（我们也没有修改 Python 模块的代码）。所以当我们重载时，加载的是“新鲜”的 `Character` 类，它仍然具有我们在其中编写的原始统计数据。

原则上我们可以更改 Python 代码。但我们不想每次都手动这样做。更重要的是，由于我们在类中硬编码了统计数据，现在游戏中的_每个_角色实例都将具有完全相同的 `str`、`dex` 和 `int`！这显然不是我们想要的。

Evennia 为此提供了一种特殊的持久化属性，称为 `Attribute`。重新设计你的 `mygame/typeclasses/characters.py` 如下：

```python
# in mygame/typeclasses/characters.py

# ...

class Character(ObjectParent, DefaultCharacter):
    """
    (class docstring)
    """

    def get_stats(self):
        """
        Get the main stats of this character
        """
        return self.db.strength, self.db.dexterity, self.db.intelligence
```

```{sidebar} 属性名中的空格？

如果你想在属性名中使用空格怎么办？或者你想动态分配属性名？那么你可以使用 `.attributes.add(name, value)`，例如 `self.attributes.add("emotional intelligence", 10)`。你可以通过 `self.attributes.get("emotional intelligence")` 重新读取它。

```

我们移除了硬编码的统计数据，并为每个统计数据添加了 `.db`。`.db` 处理程序将统计数据变成 Evennia 的 [Attribute](../../../Components/Attributes.md)。

```plaintext
> reload 
> py self.get_stats()
(None, None, None) 
```

由于我们移除了硬编码的值，Evennia 还不知道它们应该是什么。所以我们得到的只是 `None`，这是一个 Python 保留字，用于表示无值。这与普通的 Python 属性不同：

```plaintext
> py me.strength
AttributeError: 'Character' object has no attribute 'strength'
> py me.db.strength
(nothing will be displayed, because it's None)
```

尝试获取一个未知的普通 Python 属性会导致错误。获取一个未知的 Evennia `Attribute` 永远不会导致错误，只会返回 `None`。这通常非常实用。

接下来，让我们测试分配这些属性

```plaintext
> py me.db.strength, me.db.dexterity, me.db.intelligence = 10, 12, 15
> py me.get_stats()
(10, 12, 15)
> reload 
> py me.get_stats()
(10, 12, 15)
```

现在我们将属性设置为正确的值，并且它们在服务器重载后仍然存在！让我们修改力量：

```plaintext
> py self.db.strength += 2 
> py self.get_stats()
(12, 12, 15)
> reload 
> py self.get_stats()
(12, 12, 15)
```

现在我们的更改在重载后仍然存在，因为 Evennia 自动为我们保存了属性到数据库。

### 设置新角色的属性

事情看起来更好了，但有一件事仍然很奇怪——统计数据以 `None` 开始，我们必须手动将它们设置为合理的值。在以后的课程中，我们将更详细地研究角色创建。现在，让我们为每个新角色提供一些随机的初始统计数据。

我们希望这些统计数据只在对象首次创建时设置。对于角色，此方法称为 `at_object_creation`。

```python
# in mygame/typeclasses/characters.py

# ...
import random 

class Character(ObjectParent, DefaultCharacter):
    """
    (class docstring)
    """

    def at_object_creation(self):       
        self.db.strength = random.randint(3, 18)
        self.db.dexterity = random.randint(3, 18)
        self.db.intelligence = random.randint(3, 18)
    
    def get_stats(self):
        """
        Get the main stats of this character
        """
        return self.db.strength, self.db.dexterity, self.db.intelligence
```

我们导入了一个新模块 `random`。这是 Python 标准库的一部分。我们使用 `random.randint` 为每个统计数据设置一个从 3 到 18 的随机值。简单，但对于一些经典 RPG 来说，这就是你所需要的！

```plaintext
> reload 
> py self.get_stats()
(12, 12, 15)
```

```{sidebar} __init__ 与 at_object_creation

对于 `Monster` 类，我们使用 `__init__` 来设置类。我们不能对类型类使用它，因为它会被调用多次，至少在每次重载后会被调用，可能更多，具体取决于缓存。即使你熟悉 Python，也要避免对类型类使用 `__init__`，结果不会是你期望的。

```

嗯，这与我们之前设置的值相同。它们不是随机的。原因当然是，正如所说，`at_object_creation` 只运行_一次_，即角色首次创建时。我们的角色对象早已创建，因此不会再次调用。

不过，手动运行它很简单：

```plaintext
> py self.at_object_creation()
> py self.get_stats()
(5, 4, 8)
```

运气不佳，这个例子中我们的运气不佳；也许你会更好。Evennia 有一个辅助命令 `update`，它会重新运行创建钩子，并清除 `at_object_creation` 未重新创建的任何其他属性：

```plaintext
> update self
> py self.get_stats()
(8, 16, 14)
```

### 在循环中更新所有角色

```{sidebar} AttributeProperties 
还有另一种在类上定义属性的方法，称为 [AttributeProperties](../../../Components/Attributes.md#using-attributeproperty)。它们可以使在类型类上维护静态默认属性值更容易。我们将在本教程系列的后面部分展示它们。
```

不用说，明智的做法是在创建大量对象（在本例中为角色）之前，对你想要放入 `at_object_creation` 钩子的内容有一个感觉。

幸运的是，你只需要更新对象一次，并且不需要手动重新运行每个人的 `at_object_creation` 方法。为此，我们将尝试 Python _循环_。让我们进入多行 Python 模式：

```plaintext
> py
> for a in [1, 2, "foo"]:   
>     print(a)
1
2
foo
```

Python _for 循环_ 允许我们遍历某个东西。上面，我们创建了一个包含两个数字和一个字符串的_列表_。在循环的每次迭代中，变量 `a` 依次成为一个元素，我们打印它。

对于我们的列表，我们想要遍历所有角色，并想要在每个角色上调用 `.at_object_creation`。这是如何做到的（仍在 Python 多行模式下）：

```plaintext
> from typeclasses.characters import Character
> for char in Character.objects.all():
>     char.at_object_creation()
```

```{sidebar} 数据库查询

`Character.objects.all()` 是一个用 Python 表达的数据库查询示例。这将在底层转换为数据库查询。此语法是 [Django 查询语言](https://docs.djangoproject.com/en/4.1/topics/db/queries/) 的一部分。你不需要了解 Django 才能使用 Evennia，但如果你需要更具体的数据库查询，这始终可用。我们将在以后的课程中回到数据库查询。
```

我们导入了 `Character` 类，然后使用 `.objects.all()` 获取所有 `Character` 实例。简化来说，`.objects` 是一个资源，可以用来_查询_所有 `Characters`。使用 `.all()` 获取我们然后立即遍历的所有角色列表。砰，我们刚刚更新了所有角色，包括我们自己：

```plaintext
> quit()
Closing the Python console.
> py self.get_stats()
(3, 18, 10)
```

## 额外奖励

这个原则对其他类型类也是一样的。所以使用本课中探索的工具，尝试扩展默认房间，添加一个 `is_dark` 标志。它可以是 `True` 或 `False`。让所有新房间以 `is_dark = False` 开始，并确保一旦更改，它可以在重载后保留。如果你之前创建了任何其他房间，请确保它们也获得了新标志！

## 结论

在本课中，我们通过让它们的类继承自 Evennia 的一个类型类 `Object` 来创建数据库持久化的龙。我们探索了 Evennia 在我们没有明确指定路径时查找类型类的位置。然后我们通过 `Character` 类修改了我们自己，给我们一些简单的 RPG 统计数据。这导致了需要使用 Evennia 的 _属性_，通过 `.db` 设置，并使用 for 循环更新我们自己。

类型类是 Evennia 的一个基本部分，我们将在本教程的过程中看到更多它们的用途。但现在关于它们的内容已经足够了。是时候采取一些行动了。让我们学习 _命令_。
