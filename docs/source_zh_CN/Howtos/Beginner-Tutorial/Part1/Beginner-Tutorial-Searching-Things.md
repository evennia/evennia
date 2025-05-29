# 搜索对象

我们已经学习了如何在Evennia中创建各种实体。但如果创建后无法找到和使用它们，创建就没什么意义了。

```{sidebar} Python代码 vs 使用py命令
这些工具大多用于Python代码中，当你创建游戏时使用。我们给出如何从`py`命令测试的示例，但那只是为了实验，通常不是你编写游戏的方式。
```

为了测试本教程中的示例，让我们在当前房间创建几个可以搜索的对象。

    > create/drop Rose 

## 使用Object.search搜索

`DefaultObject`上有一个`.search`方法，我们在创建命令时已经尝试过。要使用它，你必须已经有一个对象可用，如果使用`py`，可以使用自己：

    py self.search("rose")
    Rose

- 这会按对象的`key`或`alias`搜索。字符串总是大小写不敏感的，所以搜索`"rose"`、`"Rose"`或`"rOsE"`会得到相同结果。
- 默认情况下，它总是在`obj.location.contents`和`obj.contents`中搜索对象(即在obj的物品栏或同一房间中的东西)。
- 它总是返回一个匹配项。如果找到零个或多个匹配项，返回`None`。这与`evennia.search`不同(见下文)，后者总是返回一个列表。
- 在没有匹配或多匹配时，`.search`会自动向`obj`发送错误消息。所以如果结果是`None`，你不必担心报告消息。

换句话说，这个方法为你处理错误消息。一个非常常见的用法是在命令中。你可以把命令放在任何地方，但让我们试试预填充的`mygame/commands/command.py`。

```python
# 例如在mygame/commands/command.py中

from evennia import Command as BaseCommand

class Command(BaseCommand): 
    # ... 

class CmdQuickFind(Command):
    """ 
    在你当前位置查找物品。

    用法: 
        quickfind <查询>
        
	"""

    key = "quickfind"

    def func(self):
        query = self.args
        result = self.caller.search(query)
        if not result:
            return
        self.caller.msg(f"找到{query}的匹配: {result}")
```

如果你想测试这个命令，将其添加到默认命令集(详见[命令教程](./Beginner-Tutorial-Adding-Commands.md))，然后用`reload`重新加载服务器：

```python
# 在mygame/commands/default_cmdsets.py中

# ...

from commands.command import CmdQuickFind    # <-------

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ... 
    def at_cmdset_creation(self): 
        # ... 
        self.add(CmdQuickFind())   # <------

```

记住，`self.caller`是调用命令的对象。这通常是一个角色，继承自`DefaultObject`。所以它有可用的`.search()`方法。

这个简单的小命令接受参数并搜索匹配项。如果找不到，`result`将是`None`。错误已经报告给`self.caller`，所以我们直接`return`中止。

使用`global_search`标志，你可以用`.search`找到任何东西，而不仅是在同一房间的东西：

```python
volcano = self.caller.search("Vesuvio", global_search=True)
```

你可以将匹配限制为特定类型类：

```python
water_glass = self.caller.search("glass", typeclass="typeclasses.objects.WaterGlass")
```

如果只想搜索特定列表中的东西，也可以这样做：

```python
stone = self.caller.search("MyStone", candidates=[obj1, obj2, obj3, obj4])
```

这只有在"MyStone"在房间中(或你的物品栏中)_并且_是提供的四个候选对象之一时才会返回匹配项。这非常强大，以下是如何只在你物品栏中查找东西：

```python
potion = self.caller.search("Healing potion", candidates=self.caller.contents)
```

你也可以关闭自动错误处理：

```python
swords = self.caller.search("Sword", quiet=True)  # 返回一个列表！
```

使用`quiet=True`时，用户不会在零匹配或多匹配错误时收到通知。相反，你需要自己处理。此外，现在返回的是一个零个、一个或多个匹配项的列表！

## 主要搜索函数

Evennia的基本搜索工具是`evennia.search_*`函数，如`evennia.search_object`。这些通常在你的代码中使用，但你也可以在游戏中使用`py`尝试它们：

     > py evennia.search_object("rose")
     <Queryset [Rose]>

```{sidebar} 查询集

从主要搜索函数返回的实际上是一个`queryset`。它们可以像列表一样处理，但不能原地修改。我们将在[下一课](./Beginner-Tutorial-Django-queries.md)讨论查询集
```

这会基于`key`或`alias`搜索对象。我们在上一节讨论的`.search`方法实际上包装了`evennia.search_object`并以各种方式处理其输出。以下是相同的Python代码示例，例如作为命令或编码系统的一部分：

```python
import evennia 

roses = evennia.search_object("rose")
accts = evennia.search_account("YourName")
```

上面我们首先找到玫瑰，然后是一个账户。你可以用`py`尝试两者：

    > py evennia.search_object("rose")[0]
    Rose
    > py evennia.search_account("YourName")[0]
    <Player: YourName>

`search_object/account`返回所有匹配项。我们使用`[0]`只获取查询集的第一个匹配项，这里分别给了我们玫瑰和你的账户。注意，如果找不到任何匹配项，像这样使用`[0]`会导致错误，所以它主要用于调试。

在其他情况下，零个或多个匹配项是问题的标志，你需要自己处理这种情况。这对于仅用`py`测试来说太详细了，但如果你想制作自己的搜索方法，这很有用：

```python
    the_one_ring = evennia.search_object("The one Ring")
    if not the_one_ring:
        # 处理根本找不到戒指的情况
    elif len(the_one_ring) > 1:
        # 处理找到多个戒指的情况
    else:
        # 好的 - 只找到一个戒指
        the_one_ring = the_one_ring[0]
```

所有主要资源都有等效的搜索函数。你可以在API首页的[搜索函数部分](../../../Evennia-API.md)找到它们的列表。

## 理解对象关系

在搜索时理解对象之间的关系很重要。

让我们考虑一个`chest`里面有一个`coin`。箱子放在一个`dungeon`房间里。地下室里还有一个`door`(一个通向外的出口)。

```
┌───────────────────────┐
│dungeon                │
│    ┌─────────┐        │
│    │chest    │ ┌────┐ │
│    │  ┌────┐ │ │door│ │
│    │  │coin│ │ └────┘ │
│    │  └────┘ │        │
│    │         │        │
│    └─────────┘        │
│                       │
└───────────────────────┘
```

如果你可以访问任何游戏中的对象，你可以通过使用其`.location`和`.contents`属性找到相关对象。

- `coin.location`是`chest`。
- `chest.location`是`dungeon`。
- `door.location`是`dungeon`。
- `room.location`是`None`，因为它不在其他东西里面。

可以用这个来查找什么在什么里面。例如，`coin.location.location`是`dungeon`。

- `room.contents`是`[chest, door]`
- `chest.contents`是`[coin]`
- `coin.contents`是`[]`，空列表，因为硬币里面没有东西。
- `door.contents`也是`[]`。

一个方便的助手是`.contents_get` - 这允许限制返回的内容：

- `room.contents_get(exclude=chest)` - 这返回房间里除箱子外的所有东西(也许它被隐藏了？)

查找出口有一个特殊属性：

- `room.exits`是`[door]`
- `coin.exits`是`[]`，因为它没有出口(所有其他对象也是如此)

有一个`.destination`属性仅用于出口：

- `door.destination`是`outside`(或门通向的任何地方)
- `room.destination`是`None`(所有其他非出口对象也是如此)

## 可以搜索什么

这些是可以搜索的主要数据库实体：

- [对象](../../../Components/Objects.md)
- [账户](../../../Components/Accounts.md)
- [脚本](../../../Components/Scripts.md),
- [频道](../../../Components/Channels.md) 
- [消息](../../../Components/Msg.md)   (默认由`page`命令使用)
- [帮助条目](../../../Components/Help-System.md) (手动创建的帮助条目)

大多数时候你可能会花时间搜索对象和偶尔的账户。

大多数搜索方法可以直接从`evennia`获得。但也有许多有用的搜索助手通过`evennia.search`找到。

那么要找到一个实体，可以搜索什么？

### 按key搜索

`key`是实体的名称。搜索这个总是大小写不敏感的。

### 按别名搜索

对象和账户可以有任意数量的别名。搜索`key`时也会搜索这些，你不能轻易地只搜索别名。让我们用默认的`alias`命令给我们的玫瑰添加一个别名：

    > alias rose = flower

或者你可以手动实现相同的事情(这是`alias`命令自动为你做的)：

    > py self.search("rose").aliases.add("flower")

如果上面的例子`rose`有一个`key` `"Rose"`，现在也可以通过搜索它的别名`flower`找到它。

    > py self.search("flower")
    Rose 

> 所有默认命令使用相同的搜索功能，所以你现在也可以`look flower`来查看玫瑰。

### 按位置搜索

只有对象(继承自`evennia.DefaultObject`的东西)有`.location`属性。

`Object.search`方法会自动将搜索限制在对象的位置内，所以假设你和玫瑰在同一房间，这会工作：

    > py self.search("rose")
    Rose

让我们创建另一个位置并移动到它 - 你将不再找到玫瑰：

    > tunnel n = kitchen
    north 
    > py self.search("rose")
    Could not find "rose"

然而，使用`search_object`会找到玫瑰，无论它在哪里：

     > py evennia.search_object("rose") 
     <QuerySet [Rose]> 

`evennia.search_object`方法没有`location`参数。相反，你通过将其`candidates`关键字设置为当前位置的`.contents`来限制搜索。这与位置搜索相同，因为它只接受房间中的匹配项。在这个例子中，我们将(正确地)发现玫瑰不在房间里。

    > py evennia.search_object("rose", candidate=here.contents)
    <QuerySet []>

一般来说，`Object.search`是执行同一位置东西的非常常见搜索的快捷方式，而`search_object`可以找到任何地方的对象。

### 按标签搜索

将[标签](../../../Components/Tags.md)想象成机场在你飞行时放在行李上的标签。乘坐同一航班的每个人都会得到一个标签，将它们分组，以便机场知道什么应该上哪架飞机。Evennia中的实体可以以相同的方式分组。每个对象可以附加任意数量的标签。

回到你的`rose`的位置，让我们创建更多植物：

    > create/drop Daffodil
    > create/drop Tulip
    > create/drop Cactus

然后让我们添加"thorny"和"flowers"标签，根据它们是否是花和/或有刺来分组：

    py self.search("rose").tags.add("flowers")
	py self.search("rose").tags.add("thorny")
    py self.search("daffodil").tags.add("flowers")
    py self.search("tulip").tags.add("flowers")
    py self.search("cactus").tags.add("flowers")
    py self.search("cactus").tags.add("thorny")	

你现在可以使用`search_tag`函数找到所有花：

    py evennia.search_tag("flowers")
    <QuerySet [Rose, Daffodil, Tulip, Cactus]>
    py evennia.search_tag("thorny")
    <QuerySet [Rose, Cactus]>

标签也可以有类别。默认情况下这个类别是`None`，这被认为是一个自己的类别。以下是在普通Python代码中使用类别的示例(如果你想先创建对象，也可以用`py`试试)：

    silmarillion.tags.add("fantasy", category="books")
    ice_and_fire.tags.add("fantasy", category="books")
    mona_lisa_overdrive.tags.add("cyberpunk", category="books")

注意，如果你用类别指定标签，搜索时_必须_也包含其类别，否则将搜索`None`的标签类别。

    all_fantasy_books = evennia.search_tag("fantasy")  # 没有匹配项！
    all_fantasy_books = evennia.search_tag("fantasy", category="books")

只有上面第二行返回两本奇幻书。

    all_books = evennia.search_tag(category="books")

这会获取所有三本书。

### 按属性搜索

我们还可以按与实体关联的[属性](../../../Components/Attributes.md)搜索。

例如，假设我们的植物有一个'growth state'，随着它生长而更新：

    > py self.search("rose").db.growth_state = "blooming"
    > py self.search("daffodil").db.growth_state = "withering"

现在我们可以找到具有给定生长状态的东西：

    > py evennia.search_object("withering", attribute_name="growth_state")
    <QuerySet [Rose]> 

> 按属性搜索可以非常实用。但如果你想分组实体或经常搜索，使用标签和按标签搜索更快且更节省资源。

### 按类型类搜索

有时按它们具有的类型类限制搜索很有用。

假设你例如有两种花，`CursedFlower`和`BlessedFlower`定义在`mygame/typeclasses.flowers.py`下。每个类包含分别授予诅咒和祝福的自定义代码。你可能有两个`rose`对象，玩家不知道哪个是坏的或好的。为了在搜索中分开它们，你可以确保获取正确的一个(在Python代码中)：

```python
cursed_roses = evennia.search_object("rose", typeclass="typeclasses.flowers.CursedFlower")
```

如果你例如已经导入了`BlessedRose`类，你也可以直接传递它：

```python
from typeclasses.flowers import BlessedFlower
blessed_roses = evennia.search_object("rose", typeclass=BlessedFlower)
```

一个常见的用例是找到给定类型类的_所有_物品，不管它们叫什么。为此，你不使用`search_object`，而是直接用类型类搜索：

```python
from typeclasses.objects.flowers import Rose
all_roses = Rose.objects.all()
```

这最后一种搜索方式是Django_查询_的简单形式。这是一种使用Python表达SQL查询的方式。详见[下一课](./Beginner-Tutorial-Django-queries.md)，我们将更详细地探讨这种搜索方式。

### 按dbref搜索

```{sidebar} 会用完dbref吗？

由于dbref不会重复使用，你需要担心数据库id将来会'用完'吗？[不，原因在此](../../../Components/Typeclasses.md#will-i-run-out-of-dbrefs)。
```
数据库id或`#dbref`在每个数据库表中是唯一且不重复使用的。在搜索方法中，你可以用dbref替换`key`的搜索。这必须写成字符串`#dbref`：

    the_answer = self.caller.search("#42")
    eightball = evennia.search_object("#8")

由于`#dbref`总是唯一的，这个搜索总是全局的。

```{warning} 依赖#dbrefs

在遗留代码库中，你可能习惯于大量依赖#dbrefs来查找和跟踪东西。通过#dbref查找某些东西可能很实用 - 如果偶尔使用。但在Evennia中*依赖*硬编码的#dbrefs被认为是**不良实践**。特别是期望最终用户知道它们。它使你的代码脆弱且难以维护，同时将你的代码绑定到数据库的确切布局。在99%的使用情况下，你应该组织你的代码，以便传递实际对象并通过key/tags/attribute搜索。
```

## 总结

知道如何找到东西很重要，本节的工具将很好地为你服务。这些工具将满足你大多数常规需求。

但并不总是如此。如果我们回到之前箱子里的硬币的例子，你可以_可以_使用以下方法动态找出房间里是否有装有硬币的箱子：

```python 
from evennia import search_object

# 我们假设每个只有一个匹配
dungeons = search_object("dungeon", typeclass="typeclasses.rooms.Room")
chests = search_object("chest", location=dungeons[0])
# 找出箱子里有多少硬币
coins = search_object("coin", candidates=chests[0].contents)
```

这会工作，但效率很低，脆弱且需要大量输入。这种事情最好通过*直接查询数据库*来完成。我们将在下一课中讨论这一点。在那里，我们将深入探讨使用Django数据库查询和查询集的更复杂搜索。
