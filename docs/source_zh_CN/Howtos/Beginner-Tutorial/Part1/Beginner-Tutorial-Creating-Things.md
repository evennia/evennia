# 创建事物

我们已经创建了一些东西——例如龙。然而，在 Evennia 中还有许多不同的事物可以创建。在 [Typeclasses 教程](./Beginner-Tutorial-Learning-Typeclasses.md)中，我们提到 Evennia 开箱即用地提供了 7 个默认 Typeclasses：

| Evennia 基础类型类 | mygame.typeclasses 子类 | 描述 |  
| --------------- |  --------------| ------------- | 
| `evennia.DefaultObject` | `typeclasses.objects.Object` | 具有位置的所有事物 |
| `evennia.DefaultCharacter` (为 `DefaultObject` 的子类) | `typeclasses.characters.Character` | 玩家化身 |
| `evennia.DefaultRoom` (为 `DefaultObject` 的子类) | `typeclasses.rooms.Room` | 游戏内位置 | 
| `evennia.DefaultExit` (为 `DefaultObject` 的子类) | `typeclasses.exits.Exit` | 房间之间的链接 | 
| `evennia.DefaultAccount` | `typeclasses.accounts.Account` | 玩家账户 | 
| `evennia.DefaultChannel` | `typeclasses.channels.Channel` | 游戏内通信 | 
|  `evennia.DefaultScript` | `typeclasses.scripts.Script` | 无位置的实体 | 

给定一个导入的 Typeclass，有四种方法可以创建它的实例：

1. 首先，您可以直接调用类，然后 `.save()` 它：

    ```python
    obj = SomeTypeClass(db_key=...)
    obj.save()
    ```

   这种方法的缺点是需要进行两次操作；您还必须导入类并传递实际的数据库字段名称，例如 `db_key` 而不是 `key` 作为关键字参数。这与“普通”Python 类的工作方式最接近，但不推荐使用。

2. 其次，您可以使用 Evennia 的创建助手：

    ```python
    obj = evennia.create_object(SomeTypeClass, key=...)
    ```

   如果您尝试在 Python 中创建事物，这是推荐的方法。第一个参数可以是类 _或_ typeclass 的 Python 路径，例如 `"path.to.SomeTypeClass"`。它也可以是 `None`，在这种情况下将使用 Evennia 默认值。虽然所有创建方法都可在 `evennia` 上使用，但它们实际上是在 [evennia/utils/create.py](../../../api/evennia.utils.create.md) 中实现的。每个不同的基类都有自己的创建函数，例如 `create_account` 和 `create_script` 等。

3. 第三，您可以在 Typeclass 本身上使用 `.create` 方法：

    ```python
    obj, err = SomeTypeClass.create(key=...)
    ```

    由于 `.create` 是 typeclass 上的方法，如果您想自定义创建过程以适应您的自定义 typeclasses，这种形式很有用。请注意，它返回 _两个_ 值 - `obj` 是新对象或 `None`，在这种情况下 `err` 应该是一个错误字符串列表，详细说明出了什么问题。

4. 最后，您可以使用游戏内命令创建对象，例如：

    ```
    create obj:path.to.SomeTypeClass
    ```

   作为开发人员，通常最好使用其他方法，但命令通常是让没有 Python 访问权限的普通玩家或构建者帮助构建游戏世界的唯一方法。

## 创建对象

[Object](../../../Components/Objects.md) 是最常见的创建类型之一。这些是从 `DefaultObject` 继承的实体。它们在游戏世界中存在，包括房间、角色、出口、武器、花盆和城堡。

```python
> py
> import evennia 
> rose = evennia.create_object(key="rose")
```

由于我们没有将 `typeclass` 指定为第一个参数，因此将使用 `settings.BASE_OBJECT_TYPECLASS`（开箱即用的 `typeclasses.objects.Object`）提供的默认值。

`create_object` 有[很多选项](evennia.utils.create.create_object)。代码中的更详细示例：

```python 
from evennia import create_object, search_object

meadow = search_object("Meadow")[0]

lasgun = create_object("typeclasses.objects.guns.LasGun", 
                       key="lasgun", 
                       location=meadow,
                       attributes=[("desc", "A fearsome Lasgun.")])
```

在这里，我们设置了武器的位置，并给它一个 [Attribute](../../../Components/Attributes.md) `desc`，这是 `look` 命令在查看此物品和其他物品时使用的内容。

## 创建房间、角色和出口

`Characters`、`Rooms` 和 `Exits` 都是 `DefaultObject` 的子类。因此，例如没有单独的 `create_character`，您只需使用指向 `Character` typeclass 的 `create_object` 创建角色。

### 在代码中链接出口和房间

`Exit` 是房间之间的单向链接。例如，`east` 可以是 `Forest` 房间和 `Meadow` 房间之间的 `Exit`。

```
Meadow -> east -> Forest 
```

`east` 出口的 `key` 为 `east`，`location` 为 `Meadow`，`destination` 为 `Forest`。如果您想从 Forest 返回到 Meadow，您需要创建一个新的 `Exit`，例如 `west`，其中 `location` 是 `Forest`，`destination` 是 `Meadow`。

```
Meadow -> east -> Forest 
Forest -> west -> Meadow
```

在游戏中，您可以使用 `tunnel` 和 `dig` 命令做到这一点，但如果您想在代码中设置这些链接，可以这样做：

```python
from evennia import create_object 
from mygame.typeclasses import rooms, exits 

# rooms
meadow = create_object(rooms.Room, key="Meadow")
forest = create_object(rooms.Room, key="Forest")

# exits 
create_object(exits.Exit, key="east", location=meadow, destination=forest)
create_object(exits.Exit, key="west", location=forest, destination=meadow)
```

## 创建账户

[Account](../../../Components/Accounts.md) 是一个角色外（OOC）实体，在游戏世界中不存在。
您可以在 `typeclasses/accounts.py` 中找到 Accounts 的父类。

通常，您希望在用户进行身份验证时创建账户。默认情况下，这发生在 `UnloggedInCmdSet` 中的 `create account` 和 `login` 默认命令中。这意味着自定义只需要替换这些命令即可！

所以通常您会修改这些命令，而不是从头开始制作。但是这里是原理：

```python 
from evennia import create_account 

new_account = create_account(
            accountname, email, password, 
            permissions=["Player"], 
            typeclass="typeclasses.accounts.MyAccount"
 )
```

输入通常是通过命令从玩家那里获取的。必须提供 `email`，但如果不使用它，可以为 `None`。`accountname` 必须在服务器上全局唯一。`password` 在数据库中加密存储。如果未给出 `typeclass`，将使用 `settings.BASE_ACCOUNT_TYPECLASS`（`typeclasses.accounts.Account`）。

## 创建频道

[Channel](../../../Components/Channels.md) 就像一个交换机，用于在用户之间发送游戏内消息；就像 IRC 或 Discord 频道，但在游戏内。

用户通过 `channel` 命令与频道交互：

```
channel/all 
channel/create channelname 
channel/who channelname 
channel/sub channel name 
...
(see 'help channel')
```

如果存在一个名为 `myguild` 的频道，用户只需写下频道名称即可向其发送消息：

```
> myguild Hello! I have some questions ... 
```

创建频道遵循熟悉的语法：

```python 
from evennia import create_channel

new_channel = create_channel(channelname)
```

服务器还可以通过设置 `DEFAULT_CHANNELS` 自动创建频道。有关详细信息，请参阅 [Channels 文档](../../../Components/Channels.md)。

## 创建脚本

[Script](../../../Components/Scripts.md) 是一个没有游戏内位置的实体。它可以用于存储任意数据，通常用于需要持久存储但无法在游戏中“查看”的游戏系统。示例包括经济系统、天气和战斗处理程序。

脚本是多用途的，具体取决于它们的功能，给定脚本可以是“全局”的，也可以附加到另一个对象（如房间或角色）上。

```python 
from evennia import create_script, search_object 
# global script 
new_script = create_script("typeclasses.scripts.MyScript", key="myscript")

# on-object script 
meadow = search_object("Meadow")[0]
new_script = create_script("typeclasses.scripts.MyScripts", 
                           key="myscript2", obj=meadow)
```

创建全局脚本的一种方便方法是在 `GLOBAL_SCRIPTS` 设置中定义它们；Evennia 将确保初始化它们。脚本还具有可选的“计时器”组件。有关更多信息，请参阅专用的 [Script](../../../Components/Scripts.md) 文档。

## 结论

任何游戏都需要数据的持久存储。这是关于如何创建每种默认类型的类型类实体的快速概述。如果您制作自己的类型类（作为默认类型类的子类），您可以以相同的方式创建它们。

接下来，我们将学习如何通过在数据库中 _搜索_ 它们来再次找到它们。
