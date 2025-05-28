# 新模型

*注意：这是一个高级主题。*

Evennia 提供了许多方便的方法来存储对象数据，比如通过属性或脚本。这对于大多数用例已经足够了。但是，如果你打算构建一个大型的独立系统，试图将你的存储需求挤入这些方法中可能会比你预期的更复杂。例如，存储公会数据以便公会成员能够更改、跟踪整个游戏经济系统中的资金流动，或实现其他需要快速访问自定义数据的自定义游戏系统。

虽然 [标签](../Components/Tags.md) 或 [脚本](../Components/Scripts.md) 可以处理许多情况，但有时通过添加自己的数据库模型可能会更容易处理。

## 数据库表概述

SQL 类型的数据库（Evennia 支持的类型）基本上是高度优化的系统，用于检索存储在表中的文本。一个表可能看起来像这样：

```
     id | db_key    | db_typeclass_path          | db_permissions  ...
    ------------------------------------------------------------------
     1  |  Griatch  | evennia.DefaultCharacter   | Developers       ...
     2  |  Rock     | evennia.DefaultObject      | None            ...
```

在你的数据库中，每行会更长。每一列被称为“字段”，每一行是一个单独的对象。你可以自己检查一下。如果你使用的是默认的 sqlite3 数据库，进入你的游戏文件夹并运行：

     evennia dbshell

你将进入数据库 shell。在那里，试试：

     sqlite> .help       # 查看帮助

     sqlite> .tables     # 查看所有表

     # 显示 objects_objectdb 表的字段名称
     sqlite> .schema objects_objectdb

     # 显示 objects_objectdb 表的第一行
     sqlite> select * from objects_objectdb limit 1;

     sqlite> .exit

Evennia 使用 [Django](https://docs.djangoproject.com)，它抽象了数据库 SQL 操作，允许你完全在 Python 中搜索和操作数据库。每个数据库表在 Django 中由一个类表示，通常称为*模型*，因为它描述了表的外观。在 Evennia 中，对象、脚本、频道等都是我们扩展和构建的 Django 模型的例子。

## 添加新的数据库表

以下是如何添加自己的数据库表/模型：

1. 在 Django 的术语中，我们将创建一个新的“应用程序”——一个主 Evennia 程序下的子系统。在这个例子中，我们将其称为“myapp”。运行以下命令（在此之前，你需要有一个正在运行的 Evennia，所以确保你已经完成了 [快速开始](Setup-Quickstart) 中的步骤）：

        evennia startapp myapp
        mv myapp world  (Linux)
        move myapp world   (Windows)

2. 一个新的文件夹 `myapp` 被创建。“myapp”也将成为从现在起的名称（“应用标签”）。我们将其移动到 `world/` 子文件夹中，但如果放在 `mygame` 的根目录下更有意义，你也可以这样做。
3. `myapp` 文件夹包含了一些空的默认文件。我们现在感兴趣的是 `models.py`。在 `models.py` 中你定义你的模型。每个模型将是数据库中的一个表。参见下一节，在添加你想要的模型之前不要继续。
4. 你现在需要告诉 Evennia 你的应用程序的模型应该是数据库方案的一部分。在你的 `mygame/server/conf/settings.py` 文件中添加这一行（确保使用你放置 `myapp` 的路径，并且不要忘记元组末尾的逗号）：

    ```python
    INSTALLED_APPS = INSTALLED_APPS + ("world.myapp", )
    ```

5. 从 `mygame/` 运行

        evennia makemigrations myapp
        evennia migrate myapp

这将把你的新数据库表添加到数据库中。如果你已经将你的游戏置于版本控制之下（如果没有，[你应该这样做](../Coding/Version-Control.md)），不要忘记 `git add myapp/*` 来将所有项目添加到版本控制中。

## 定义你的模型

Django *模型* 是数据库表的 Python 表示。它可以像其他 Python 类一样处理。它在自身上定义 *字段*，这些字段是特殊类型的对象。这些字段成为数据库表的“列”。最后，你创建模型的新实例以向数据库添加新行。

我们不会在这里描述 Django 模型的所有方面，关于这个主题我们参考广泛的 [Django 文档](https://docs.djangoproject.com/en/4.1/topics/db/models/)。以下是一个（非常）简短的例子：

```python
from django.db import models

class MyDataStore(models.Model):
    "用于存储一些数据的简单模型"
    db_key = models.CharField(max_length=80, db_index=True)
    db_category = models.CharField(max_length=80, null=True, blank=True)
    db_text = models.TextField(null=True, blank=True)
    # 如果我们想要能够将其存储在 Evennia 属性中，我们需要这个字段！
    db_date_created = models.DateTimeField('创建日期', editable=False,
                                            auto_now_add=True, db_index=True)
```

我们创建了四个字段：两个有限长度的字符字段和一个没有最大长度的文本字段。最后我们创建了一个字段，包含我们创建此对象时的当前时间。

> 如果你希望能够在 Evennia [属性](../Components/Attributes.md) 中存储自定义模型的实例，那么 `db_date_created` 字段（使用这个确切的名称）是*必需的*。它将在创建时自动设置，之后不能更改。拥有这个字段将允许你执行例如 `obj.db.myinstance = mydatastore`。如果你知道你永远不会在属性中存储你的模型实例，那么 `db_date_created` 字段是可选的。

你不*必须*以 `db_` 开始字段名称，这是 Evennia 的惯例。尽管如此，建议你使用 `db_`，部分原因是为了清晰和与 Evennia 的一致性（如果你想分享你的代码），部分原因是为了以后你决定使用 Evennia 的 `SharedMemoryModel` 父类。

字段关键字 `db_index` 为此字段创建一个*数据库索引*，这允许更快的查找，因此建议将其放在你知道经常在查询中使用的字段上。`null=True` 和 `blank=True` 关键字意味着这些字段可以留空或设置为空字符串，而不会引起数据库的抱怨。还有许多其他字段类型和定义它们的关键字，参见 Django 文档以获取更多信息。

类似于使用 [django-admin](https://docs.djangoproject.com/en/4.1/howto/legacy-databases/)，你可以执行 `evennia inspectdb` 以获取现有数据库的模型信息的自动列表。与任何模型生成工具一样，你应该仅将其用作模型的起点。

## 引用现有模型和类型类

你可能希望使用 `ForeignKey` 或 `ManyToManyField` 来将你的新模型与现有模型关联。

为此，我们需要指定我们希望存储的根对象类型的应用程序路径作为字符串（我们必须使用字符串而不是类直接引用，否则你会遇到模型尚未初始化的问题）。

- `"objects.ObjectDB"` 用于所有 [对象](../Components/Objects.md)（如出口、房间、角色等）
- `"accounts.AccountDB"` 用于 [账户](../Components/Accounts.md)。
- `"scripts.ScriptDB"` 用于 [脚本](../Components/Scripts.md)。
- `"comms.ChannelDB"` 用于 [频道](../Components/Channels.md)。
- `"comms.Msg"` 用于 [消息](../Components/Msg.md) 对象。
- `"help.HelpEntry"` 用于 [帮助条目](../Components/Help-System.md)。

以下是一个例子：

```python
from django.db import models

class MySpecial(models.Model):
    db_character = models.ForeignKey("objects.ObjectDB")
    db_items = models.ManyToManyField("objects.ObjectDB")
    db_account = models.ForeignKey("accounts.AccountDB")
```

这可能看起来不太直观，但这将正确工作：

```python
myspecial.db_character = my_character  # 一个角色实例
my_character = myspecial.db_character  # 仍然是一个角色
```

这之所以有效，是因为当 `.db_character` 字段被加载到 Python 中时，实体本身知道它应该是一个 `Character` 并加载自己到那个形式。

这种方法的缺点是数据库不会*强制*你在关系中存储的对象类型。这是我们为类型类系统的许多其他优势所付出的代价。

虽然 `db_character` 字段在你尝试存储一个 `Account` 时会失败，但它会欣然接受任何继承自 `ObjectDB` 的类型类实例，如房间、出口或其他非角色对象。验证你存储的内容是否符合预期是你的责任。

## 创建新模型实例

要在你的表中创建新行，你需要实例化模型，然后调用其 `save()` 方法：

```python
from evennia.myapp import MyDataStore

new_datastore = MyDataStore(db_key="LargeSword",
                            db_category="weapons",
                            db_text="This is a huge weapon!")
# 这是创建数据库行所必需的！
new_datastore.save()
```

注意，模型的 `db_date_created` 字段未指定。其标志 `auto_now_add=True` 确保在对象创建时将其设置为当前日期（创建后也不能进一步更改）。

当你用一些新字段值更新现有对象时，请记住你必须在之后保存对象，否则数据库不会更新：

```python
my_datastore.db_key = "Larger Sword"
my_datastore.save()
```

Evennia 的普通模型不需要显式保存，因为它们基于 `SharedMemoryModel` 而不是原始的 Django 模型。这将在下一节中介绍。

## 使用 `SharedMemoryModel` 父类

Evennia 大多数模型不是基于原始的 `django.db.models.Model`，而是基于 Evennia 基础模型 `evennia.utils.idmapper.models.SharedMemoryModel`。这主要有两个原因：

1. 更容易更新字段而无需显式调用 `save()`
2. 对象内存持久性和数据库缓存

第一个（也是最不重要的）点意味着只要你将字段命名为 `db_*`，Evennia 就会自动为它们创建字段包装器。这发生在模型的 [元类](http://en.wikibooks.org/wiki/Python_Programming/Metaclasses) 中，因此没有速度损失。包装器的名称将与字段名称相同，减去 `db_` 前缀。因此，`db_key` 字段将有一个名为 `key` 的包装器属性。然后你可以这样做：

```python
my_datastore.key = "Larger Sword"
```

并且不必在之后显式调用 `save()`。保存也在底层以更有效的方式进行，仅更新字段而不是使用 Django 优化更新整个模型。请注意，如果你手动将属性或方法 `key` 添加到模型中，这将被使用而不是自动包装器，并允许你根据需要完全自定义访问。

要解释第二个也是更重要的点，请考虑以下使用默认 Django 模型父类的示例：

```python
shield = MyDataStore.objects.get(db_key="SmallShield")
shield.cracked = True # 其中 cracked 不是数据库字段
```

然后在另一个函数中你这样做：

```python
shield = MyDataStore.objects.get(db_key="SmallShield")
print(shield.cracked)  # 错误！
```

最后一个打印语句的结果是*未定义的*！它可能*可能*随机工作，但很可能你会因为找不到 `cracked` 属性而得到一个 `AttributeError`。原因是 `cracked` 不代表数据库中的实际字段。它只是运行时添加的，因此 Django 不关心它。当你稍后检索你的盾牌匹配时，没有*保证*你会得到定义 `cracked` 的*相同 Python 实例*的模型，即使你搜索的是相同的数据库对象。

Evennia 强烈依赖于模型处理程序和其他动态创建的属性。因此，与其使用普通的 Django 模型，Evennia 使用 `SharedMemoryModel`，它利用了一种称为 *idmapper* 的东西。idmapper 缓存模型实例，以便我们在第一次查找给定对象后总是得到*相同的*实例。使用 idmapper，上述示例将正常工作，你可以随时检索你的 `cracked` 属性——直到你重启时所有非持久性数据消失。

使用 idmapper 对每个对象来说既更直观也更高效；这导致从磁盘读取的次数大大减少。缺点是这个系统总体上更耗费内存。因此，如果你知道你*永远*不需要向运行实例添加新属性，或者知道你将一直创建新对象但很少再次访问它们（如日志系统），那么你可能最好制作“普通” Django 模型，而不是使用 `SharedMemoryModel` 及其 idmapper。

要使用 idmapper 和字段包装器功能，你只需让你的模型类继承自 `evennia.utils.idmapper.models.SharedMemoryModel`，而不是默认的 `django.db.models.Model`：

```python
from evennia.utils.idmapper.models import SharedMemoryModel

class MyDataStore(SharedMemoryModel):
    # 其余与之前相同，但 db_* 很重要；这些稍后将可设置为 .key, .category, .text ...
    db_key = models.CharField(max_length=80, db_index=True)
    db_category = models.CharField(max_length=80, null=True, blank=True)
    db_text = models.TextField(null=True, blank=True)
    db_date_created = models.DateTimeField('创建日期', editable=False,
                                            auto_now_add=True, db_index=True)
```

## 搜索你的模型

要搜索你的新自定义数据库表，你需要使用其数据库*管理器*来构建*查询*。请注意，即使你使用了上一节中描述的 `SharedMemoryModel`，你也必须在查询中使用实际的*字段名称*，而不是包装器名称（所以是 `db_key` 而不仅仅是 `key`）。

```python
from world.myapp import MyDataStore

# 获取完全匹配给定键的所有数据存储对象
matches = MyDataStore.objects.filter(db_key="Larger Sword")
# 获取具有包含“sword”的键和类别为“weapons”的所有数据存储对象（都忽略大小写）
matches2 = MyDataStore.objects.filter(db_key__icontains="sword",
                                      db_category__iequals="weapons")
# 显示匹配的数据（例如在命令中）
for match in matches2:
    self.caller.msg(match.db_text)
```

有关查询数据库的更多信息，请参阅 [Django 查询的初学者教程课程](../Howtos/Beginner-Tutorial/Part1/Beginner-Tutorial-Django-queries.md)。
