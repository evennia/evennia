# 单元测试

*单元测试* 是指在程序的各个组件彼此隔离的情况下进行测试，以确保每个部分在与其他部分结合使用之前能够单独正常工作。广泛的测试有助于避免新更新引发意外的副作用，并减轻代码腐烂的问题（关于单元测试的更全面的维基百科文章可以在[这里](https://en.wikipedia.org/wiki/Unit_test)找到）。

一个典型的单元测试集会调用某个函数或方法，给定输入，查看结果并确保该结果符合预期。与其拥有许多独立的测试程序，Evennia 使用一个中央的 *测试运行器*。这是一个收集 Evennia 源代码中所有可用测试（称为 *测试套件*）并一次性运行它们的程序。错误和回溯会被报告。

默认情况下，Evennia 只测试自身。但您也可以将自己的测试添加到游戏代码中，并让 Evennia 为您运行这些测试。

## 运行 Evennia 测试套件

要运行完整的 Evennia 测试套件，请转到您的游戏文件夹并输入以下命令：

```
evennia test evennia
```

这将使用默认设置运行所有 Evennia 测试。您还可以通过指定库的子包来仅运行一部分测试：

```
evennia test evennia.commands.default
```

将会实例化一个临时数据库来管理测试。如果一切正常，您将看到运行了多少测试以及花费了多长时间。如果出现问题，您将收到错误消息。如果您为 Evennia 做出贡献，这是一个有用的检查，以确保您没有引入意外的错误。

## 运行自定义游戏目录单元测试

如果您为游戏实现了自己的测试，可以从游戏目录运行它们：

```
evennia test --settings settings.py .
```

句号（`.`）表示运行当前目录及所有子目录中找到的所有测试。您也可以指定，比如 `typeclasses` 或 `world`，如果您只想运行这些子目录中的测试。

需要注意的重要一点是，这些测试将使用 _默认的 Evennia 设置_ 运行。要使用您自己的设置文件运行测试，必须使用 `--settings` 选项：

```
evennia test --settings settings.py .
```

Evennia 的 `--settings` 选项接受位于 `mygame/server/conf` 文件夹中的文件名。通常用于在测试和开发中切换设置文件。与 `test` 结合使用时，它会强制 Evennia 使用此设置文件而不是默认文件。

您还可以通过提供路径来测试特定内容：

```
evennia test --settings settings.py world.tests.YourTest
```

## 编写新单元测试

Evennia 的测试套件使用 Django 单元测试系统，而 Django 单元测试系统依赖于 Python 的 *unittest* 模块。

为了让测试运行器找到测试，它们必须放在名为 `test*.py` 的模块中（例如 `test.py`、`tests.py` 等）。这样的测试模块无论在包中的哪个位置都会被找到。查看一些 Evennia 的 `tests.py` 模块以了解它们的样子可能是个好主意。

在模块内部，您需要放置一个从 `unittest.TestCase` 继承的类（继承距离不限）。该类中每个以 `test_` 开头的方法将分别作为单元测试运行。有两个特殊的、可选的方法 `setUp` 和 `tearDown`，如果您定义它们，将分别在 _每个_ 测试之前和之后运行。这对于创建、配置和清理类中每个测试所需的内容非常有用。

要实际测试内容，您可以在类上使用特殊的 `assert...` 方法。最常用的是 `assertEqual`，它确保结果符合预期。

以下是一个示例。假设您将其放在 `mygame/world/tests.py` 中，并想测试 `mygame/world/myfunctions.py` 中的一个函数：

```python
# 在游戏目录中的某个模块 tests.py 中
import unittest

from evennia import create_object
# 我们要测试的函数
from .myfunctions import myfunc


class TestObj(unittest.TestCase):
   """测试函数 myfunc。"""

   def setUp(self):
       """在下面每个 test_ * 方法之前完成"""
       self.obj = create_object("mytestobject")

   def tearDown(self):
       """在下面每个 test_* 方法之后完成"""
       self.obj.delete()

   def test_return_value(self):
       """测试方法。确保返回值符合预期。"""
       actual_return = myfunc(self.obj)
       expected_return = "This is the good object 'mytestobject'."
       # 测试
       self.assertEqual(expected_return, actual_return)

   def test_alternative_call(self):
       """测试方法。使用关键字参数调用。"""
       actual_return = myfunc(self.obj, bad=True)
       expected_return = "This is the baaad object 'mytestobject'."
       # 测试
       self.assertEqual(expected_return, actual_return)
```

要测试此内容，请运行：

```
evennia test --settings settings.py .
```

运行整个测试模块：

```
evennia test --settings settings.py world.tests
```

或特定类：

```
evennia test --settings settings.py world.tests.TestObj
```

您还可以运行特定测试：

```
evennia test --settings settings.py world.tests.TestObj.test_alternative_call
```

您可能还想阅读 [Python unittest 模块的文档](https://docs.python.org/library/unittest.html)。

### 使用 Evennia 测试类

Evennia 提供了许多自定义测试类，帮助测试 Evennia 功能。它们都位于 [evennia.utils.test_resources](evennia.utils.test_resources) 中。

```{important}
请注意，这些基类已经实现了 `setUp` 和 `tearDown`，因此如果您想自己在其中添加内容，应该记得在代码中使用例如 `super().setUp()`。
```

#### 用于测试游戏目录的类

这些类使用您传递给它们的任何设置，并且非常适合测试游戏目录中的代码。

- `EvenniaTest` - 为您的测试设置完整的对象环境。所有创建的实体都可以作为类的属性访问：
  - `.account` - 一个名为 "TestAccount" 的虚拟 [Account](evennia.accounts.accounts.DefaultAccount)。
  - `.account2` - 另一个名为 "TestAccount2" 的 [Account](evennia.accounts.accounts.DefaultAccount)。
  - `.char1` - 一个链接到 `.account` 的 [Character](evennia.objects.objects.DefaultCharacter)，名为 `Char`。它具有“开发者”权限，但不是超级用户。
  - `.char2` - 另一个链接到 `account2` 的 [Character](evennia.objects.objects.DefaultCharacter)，名为 `Char2`。它具有基本权限（玩家）。
  - `.obj1` - 一个常规的 [Object](evennia.objects.objects.DefaultObject)，名为 "Obj"。
  - `.obj2` - 另一个 [Object](evennia.objects.objects.DefaultObject)，名为 "Obj2"。
  - `.room1` - 一个 [Room](evennia.objects.objects.DefaultRoom)，名为 "Room"。两个角色和两个对象都位于此房间内。它的描述为 "room_desc"。
  - `.room2` - 另一个 [Room](evennia.objects.objects.DefaultRoom)，名为 "Room2"。它是空的，没有设置描述。
  - `.exit` - 一个名为 "out" 的出口，从 `.room1` 通向 `.room2`。
  - `.script` - 一个名为 "Script" 的 [Script](evennia.scripts.scripts.DefaultScript)。这是一个没有计时组件的惰性脚本。
  - `.session` - 一个模拟玩家连接到游戏的虚拟 [Session](evennia.server.serversession.ServerSession)。它由 `.account1` 使用，sessid 为 1。
- `EvenniaCommandTest` - 拥有与 `EvenniaTest` 相同的环境，但还添加了一个特殊的 [.call()](evennia.utils.test_resources.EvenniaCommandTestMixin.call) 方法，专门用于测试 Evennia [Commands](../Components/Commands.md)。它允许您将命令实际返回给玩家的内容与预期进行比较。阅读 `call` API 文档以获取更多信息。
- `EvenniaTestCase` - 这与常规的 Python `TestCase` 类相同，只是为了与下面的 `BaseEvenniaTestCase` 保持命名对称。

以下是使用 `EvenniaTest` 的示例：

```python
# 在测试模块中

from evennia.utils.test_resources import EvenniaTest

class TestObject(EvenniaTest):
    """请记住，测试类在 room1 中创建 char1 和 char2 ..."""
    def test_object_search_character(self):
        """检查 char1 是否可以通过名称搜索 char2"""
        self.assertEqual(self.char1.search(self.char2.key), self.char2)

    def test_location_search(self):
        """检查 char1 是否可以通过名称找到当前位置"""
        self.assertEqual(self.char1.search(self.char1.location.key), self.char1.location)
        # ...
```

此示例测试自定义命令。

```python
from evennia.commands.default.tests import EvenniaCommandTest
from commands import command as mycommand


class TestSet(EvenniaCommandTest):
    """通过简单调用测试 look 命令，使用 Char2 作为目标"""

    def test_mycmd_char(self):
        self.call(mycommand.CmdMyLook(), "Char2", "Char2(#7)")

    def test_mycmd_room(self):
        """通过简单调用测试 look 命令，目标为房间"""
        self.call(mycommand.CmdMyLook(), "Room",
                  "Room(#1)\nroom_desc\nExits: out(#3)\n"
                  "You see: Obj(#4), Obj2(#5), Char2(#7)")
```

使用 `.call` 时，您不需要指定整个字符串；您可以只给出它的开头，如果匹配就足够了。使用 `\n` 表示换行符，（这是 `.call` 帮助程序的一个特殊功能），使用 `||` 表示命令中多次使用 `.msg()`。`.call` 帮助程序有很多参数用于模拟不同的命令调用方式，因此请确保[阅读 .call() 的 API 文档](evennia.utils.test_resources.EvenniaCommandTestMixin.call)。

#### 用于测试 Evennia 核心的类

这些类用于测试 Evennia 本身。它们提供与上述类相同的资源，但强制使用 `evennia/settings_default.py` 中的 Evennia 默认设置，忽略游戏目录中的任何设置更改。

- `BaseEvenniaTest` - 所有的默认对象，但强制使用默认设置
- `BaseEvenniaCommandTest` - 用于测试命令，但强制使用默认设置
- `BaseEvenniaTestCase` - 没有默认对象，只有强制使用默认设置

还有两个特殊的“mixin”类。这些类在上述类中使用，但如果您想混合自己的测试类，也可能有用：

- `EvenniaTestMixin` - 一个创建所有测试环境对象的类混合。
- `EvenniaCommandMixin` - 一个添加 `.call()` 命令测试助手的类混合。

如果您想帮助编写 Evennia 的单元测试，请查看 Evennia 的 [coveralls.io 页面](https://coveralls.io/github/evennia/evennia)。在那里，您可以看到哪些模块有任何形式的测试覆盖，哪些没有。所有帮助都受到欢迎！

### 使用自定义模型进行单元测试贡献

如果您要创建一个贡献给 `evennia/contrib` 文件夹的贡献，并使用其[自己的数据库模型](../Concepts/Models.md)，这是一种特殊情况。问题在于 Evennia（和 Django）只会识别 `settings.INSTALLED_APPS` 中的模型。如果用户想要使用您的贡献，他们将需要将您的模型添加到他们的设置文件中。但是由于贡献是可选的，您不能将模型添加到 Evennia 的中央 `settings_default.py` 文件中——这将始终创建您的可选模型，而不管用户是否需要它们。但同时，贡献是 Evennia 分发的一部分，其单元测试应与所有其他 Evennia 测试一起使用 `evennia test evennia` 运行。

解决方法是在测试运行时仅临时将您的模型添加到 `INSTALLED_APPS` 目录中。以下是如何做到这一点的示例。

> 请注意，此解决方案源自 [stackexchange 答案](http://stackoverflow.com/questions/502916/django-how-to-create-a-model-dynamically-just-for-testing#503435)，目前尚未测试！请报告您的发现。

```python
# 文件 contrib/mycontrib/tests.py

from django.conf import settings
import django
from evennia.utils.test_resources import BaseEvenniaTest

OLD_DEFAULT_SETTINGS = settings.INSTALLED_APPS
DEFAULT_SETTINGS = dict(
    INSTALLED_APPS=(
        'contrib.mycontrib.tests',
    ),
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3"
        }
    },
    SILENCED_SYSTEM_CHECKS=["1_7.W001"],
)


class TestMyModel(BaseEvenniaTest):
    def setUp(self):
        if not settings.configured:
            settings.configure(**DEFAULT_SETTINGS)
        django.setup()

        from django.core.management import call_command
        from django.db.models import loading
        loading.cache.loaded = False
        call_command('syncdb', verbosity=0)

    def tearDown(self):
        settings.configure(**OLD_DEFAULT_SETTINGS)
        django.setup()

        from django.core.management import call_command
        from django.db.models import loading
        loading.cache.loaded = False
        call_command('syncdb', verbosity=0)

    # 测试用例在此之后...

    def test_case(self):
# 测试用例在此
```

### 关于加快测试运行器的说明

如果您有大量迁移的自定义模型，创建测试数据库可能需要很长时间。如果您的测试不需要运行迁移，可以使用 django-test-without-migrations 包禁用它们。要安装它，只需：

```
$ pip install django-test-without-migrations
```

然后将其添加到 `server.conf.settings.py` 中的 `INSTALLED_APPS`：

```python
INSTALLED_APPS = (
    # ...
    'test_without_migrations',
)
```

这样做之后，您可以通过添加 `--nomigrations` 参数来运行没有迁移的测试：

```
evennia test --settings settings.py --nomigrations .
```
