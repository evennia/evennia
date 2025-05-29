# Python类和对象入门

我们已经学习了如何在游戏服务器内外运行一些简单的Python代码，也了解了游戏目录的结构。现在我们将开始实际使用它。

## 导入模块

在[前几课](./Beginner-Tutorial-Python-basic-introduction.md#importing-code-from-other-modules)中，我们已经学习了如何将资源导入代码。现在我们将更深入一些。

没有人会用一个庞大的文件来编写像在线游戏这样的大型项目。相反，代码会被拆分到不同的文件(模块)中，每个模块专注于不同的目的。这不仅使代码更清晰、更有组织、更易于理解，还能提高代码的可重用性——你只需导入需要的资源，确保只获取所需内容。这使得定位错误和识别代码质量更容易。

> Evennia本身也以同样的方式使用你的代码——你只需告诉它特定类型代码的位置，它就会导入并使用它(通常代替其默认值)。

这是一个熟悉的例子：

    > py import world.test ; world.test.hello_world(me)
    Hello World!

在这个例子中，硬盘上的文件结构如下：

```
mygame/
    world/
        test.py    <- 这个文件中有一个hello_world函数
```

如果你遵循了之前的教程课程，`mygame/world/test.py`文件应该如下所示(如果没有，请修改)：

```python
def hello_world(who):
    who.msg("Hello World!")
```

```{sidebar} Python中的空格很重要！
- 缩进在Python中很重要
- 大小写也很重要
- 使用4个空格缩进，而不是制表符
- 空行没问题
- `#`后的内容是注释，Python会忽略
```

重申一下，_python路径_描述了Python资源之间的关系，包括Python模块之间和内部(即以.py结尾的文件)。路径使用`.`并总是跳过`.py`文件扩展名。此外，Evennia已经知道从`mygame/`开始查找Python资源，所以这部分不应包含在路径中。

    import world.test

`import` Python指令加载`world.test`使其可用。现在你可以"进入"这个模块获取想要的函数：

    world.test.hello_world(me)

像这样使用`import`意味着每次想获取函数时都必须指定完整的`world.test`。这里有一个替代方案：

    from world.test import hello_world

`from ... import ...`非常常见，特别是当你想获取路径较长的内容时。它直接导入`hello_world`，所以你可以立即使用它！

     > py from world.test import hello_world ; hello_world(me)
     Hello World!

假设你的`test.py`模块有一堆有趣的函数。你可以逐个导入它们：

    from world.test import hello_world, my_func, awesome_func

如果有_很多_函数，你可以只导入`test`并在需要时从中获取函数(而不必每次都给出完整的`world.test`)：

    > from world import test ; test.hello_world(me)
    Hello World!

你也可以_重命名_导入的内容。例如，如果导入到的模块已经有一个`hello_world`函数，但我们还想使用`world/test.py`中的那个：

    from world.test import hello_world as test_hello_world

`from ... import ... as ...`形式会重命名导入。

    > from world.test import hello_world as hw ; hw(me)
    Hello World!

> 除非是为了避免上述的名称冲突，否则应避免重命名——你希望代码尽可能易于阅读，而重命名增加了潜在的混淆层。

在[Python基础介绍](./Beginner-Tutorial-Python-basic-introduction.md)中，我们学习了如何打开游戏内的多行解释器。

    > py
    Evennia Interactive Python mode
    Python 3.7.1 (default, Oct 22 2018, 11:21:55)
    [GCC 8.2.0] on Linux
    [py mode - quit() to exit]

现在你只需导入一次就可以重复使用导入的函数。

    > from world.test import hello_world
    > hello_world(me)
    Hello World!
    > hello_world(me)
    Hello World!
    > hello_world(me)
    Hello World!
    > quit()
    Closing the Python console.

```{sidebar} py的替代方案
如果发现在`py`命令中输入多行很麻烦(传统的MUD客户端对此相当有限)，你也可以`cd`到`mygame`文件夹并运行`evennia shell`。你将进入一个Python shell，其中Evennia可用。如果安装`pip install ipython`，你将获得一个更现代的Python shell使用。这在游戏外工作，但`print`会以相同方式显示。
```

编写模块代码时也是如此——在大多数Python模块中，你会看到顶部有一堆导入，这些资源随后被该模块中的所有代码使用。

## 关于类和对象

现在我们已经了解了导入，让我们来看一个真正的Evennia模块并尝试理解它。

在你选择的文本编辑器中打开`mygame/typeclasses/scripts.py`。

```python
# mygame/typeclasses/script.py
"""
模块文档字符串
"""
from evennia import DefaultScript

class Script(DefaultScript):
    """
    类文档字符串
    """
    pass
```

```{sidebar} 文档字符串 vs 注释
文档字符串与注释(由`#`创建)不同。Python不会忽略文档字符串，而是它所记录内容(本例中的模块和类)的组成部分。例如，我们阅读文档字符串作为[API文档](../../../Evennia-API.md)的帮助文本；我们不能用注释做到这一点。
```

实际文件要长得多，但我们可以忽略多行字符串(`""" ... """`)。这些作为模块(顶部)和下面`class`的_文档字符串_。

在模块文档字符串下面我们有_导入_。这里我们从核心`evennia`库本身导入资源。我们稍后会深入探讨，现在只需将其视为黑盒。

名为`Script`的`class`从`DefaultScript`_继承_。如你所见，`Script`几乎是空的。所有有用的代码实际上都在`DefaultScript`中(`Script`_继承_了这些代码，除非它用自己的同名代码_覆盖_它)。

我们需要稍微绕道来理解什么是'类'、'对象'或'实例'。这些是在高效使用Evennia之前需要理解的基本概念。
```{sidebar} OOP
类、对象、实例和继承是Python的基础。这些和一些其他概念通常被归类为面向对象编程(OOP)。
```

### 类和实例

'类'可以看作是对象'类型'的'模板'。类描述了该类的每个对象的基本功能。例如，我们可以有一个`Monster`类，它具有从一个房间移动到另一个房间的资源。

新建一个文件`mygame/typeclasses/monsters.py`。添加以下简单类：

```python
class Monster:

    key = "Monster"

    def move_around(self):
        print(f"{self.key} is moving!")
```

上面我们定义了一个`Monster`类，有一个变量`key`(即名称)和一个_方法_。方法类似于函数，但它"位于"类上。它还总是至少有一个参数(几乎总是写作`self`，尽管原则上你可以使用其他名称)，这是对自身的引用。所以当我们打印`self.key`时，我们指的是类上的`key`。

```{sidebar} 术语
- `class`是描述某物'类型'的代码模板
- `object`是`class`的`instance`。就像用模具铸造锡兵一样，一个类可以被_实例化_为任意数量的对象实例。每个实例不必相同(就像每个锡兵可以被涂成不同颜色)。
```

类只是一个模板。在使用之前，我们必须创建类的_实例_。如果`Monster`是一个类，那么实例就是`Fluffy`，一个特定的龙个体。你通过_调用_类来实例化，就像调用函数一样：

    fluffy = Monster()

让我们在游戏中试试(我们使用`py`多行模式，这样更容易)：

    > py
    > from typeclasses.monsters import Monster
    > fluffy = Monster()
    > fluffy.move_around()
    Monster is moving!

我们创建了一个`Monster`的_实例_，存储在变量`fluffy`中。然后我们调用`fluffy`上的`move_around`方法来获取打印输出。

> 注意我们_没有_像`fluffy.move_around(self)`这样调用方法。虽然在定义方法时`self`必须存在，但在调用方法时我们_从不_显式添加它(Python会在幕后自动为我们添加正确的`self`)。

让我们创建Fluffy的兄弟Cuddly：

    > cuddly = Monster()
    > cuddly.move_around()
    Monster is moving!

现在我们有两个怪物，它们会一直存在，直到我们调用`quit()`退出这个Python实例。我们可以让它们移动任意多次。但无论我们创建多少怪物，它们都会显示相同的打印输出，因为`key`始终固定为"Monster"。

让我们让类更灵活一些：

```python
class Monster:

    def __init__(self, key):
        self.key = key

    def move_around(self):
        print(f"{self.key} is moving!")
```

`__init__`是Python识别的一个特殊方法。如果提供，它会处理实例化新Monster时的额外参数。我们让它添加一个参数`key`，存储在`self`上。

现在，为了让Evennia看到这个代码更改，我们需要重新加载服务器。你可以这样做：

    > quit()
    Python Console is closing.
    > reload

或者你可以使用单独的终端从游戏外部重启：
```{sidebar} 关于重新加载
使用python模式重新加载会有点烦人，因为你需要在每次重新加载后重做所有事情。只需记住，在常规开发中你不会以这种方式工作。游戏内的python模式适用于快速修复和实验，但实际代码通常是在外部的python模块中编写的。
```

    $ evennia reload   (或 restart)

无论哪种方式，你都需要再次进入`py`：

    > py
    > from typeclasses.monsters import Monster
    fluffy = Monster("Fluffy")
    fluffy.move_around()
    Fluffy is moving!

现在我们向类传递了`"Fluffy"`作为参数。这进入了`__init__`并设置了`self.key`，我们稍后用它来打印正确的名字！

### 对象有什么好处？

到目前为止，我们看到类所做的只是表现得像我们最初的`hello_world`函数，但更复杂。我们本可以只做一个函数：

```python
     def monster_move_around(key):
        print(f"{key} is moving!")
```

函数和类的实例(对象)之间的区别在于对象保持_状态_。一旦你调用了函数，它就会忘记你上次调用它时的一切。而另一方面，对象会记住变化：

    > fluffy.key = "Fluffy, the red dragon"
    > fluffy.move_around()
    Fluffy, the red dragon is moving!

`fluffy`对象的`key`被更改，只要它存在就会保持。这使得对象对于表示和记住数据集合非常有用——其中一些数据又可以是其他对象。一些例子：

- 具有所有属性的玩家角色
- 具有HP的怪物
- 装有若干金币的箱子
- 内有其他对象的房间
- 政党的当前政策立场
- 解决挑战或掷骰子的规则方法
- 复杂经济模拟的多维数据点
- 还有更多！

### 类可以有子类

类可以相互_继承_。"子"类将从其"父"类继承所有内容。但如果子类添加了与父类同名的内容，它将_覆盖_从父类获得的内容。

让我们用另一个类扩展`mygame/typeclasses/monsters.py`：

```python
class Monster:
    """
    这是Monster的基类。
    """

    def __init__(self, key):
        self.key = key

    def move_around(self):
        print(f"{self.key} is moving!")


class Dragon(Monster):
    """
    这是一个龙怪物。
    """

    def move_around(self):
        print(f"{self.key} flies through the air high above!")

    def firebreath(self):
        """
        让我们的龙喷火。
        """
        print(f"{self.key} breathes fire!")
```

我们添加了一些文档字符串以提高清晰度。添加文档字符串总是一个好主意；你也可以为方法添加文档字符串，如新的`firebreath`方法所示。

我们创建了新类`Dragon`，但我们也通过添加括号中的父类指定`Monster`是`Dragon`的_父类_。`class Classname(Parent)`是这样做的方式。

```{sidebar} 多重继承
可以为一个类添加更多逗号分隔的父类。我们在本课最后展示了这种"多重继承"的示例。在知道自己在做什么之前，通常应该避免自己设置多重继承。单一父类几乎可以满足你需要的所有情况。
```

让我们试试新类。首先`reload`服务器，然后：

    > py
    > from typeclasses.monsters import Dragon
    > smaug = Dragon("Smaug")
    > smaug.move_around()
    Smaug flies through the air high above!
    > smaug.firebreath()
    Smaug breathes fire!

因为我们没有(重新)在`Dragon`中实现`__init__`，所以我们从`Monster`中获取了它。我们确实在`Dragon`中实现了自己的`move_around`，所以它_覆盖_了`Monster`中的那个。而`firebreath`只对`Dragon`可用。在`Monster`上有这个方法没有多大意义，因为不是每个怪物都能喷火。

即使你正在覆盖某些内容，也可以强制一个类使用父类的资源。这是通过`super()`方法完成的。如下修改你的`Dragon`类：

```python
# ...

class Dragon(Monster):

    def move_around(self):
        super().move_around()
        print("The world trembles.")

    # ...
```

> 保留`Monster`和`firebreath`方法。上面的`# ...`表示其余代码未更改。

`super().move_around()`行意味着我们正在调用类父类上的`move_around()`。所以在这种情况下，我们将在做自己的事情之前先调用`Monster.move_around`。

要查看，`reload`服务器然后：

    > py
    > from typeclasses.monsters import Dragon
    > smaug = Dragon("Smaug")
    > smaug.move_around()
    Smaug is moving!
    The world trembles.

我们可以看到`Monster.move_around()`首先被调用并打印"Smaug is moving!"，然后是`Dragon`类中关于世界颤抖的额外内容。

继承是一个强大的概念。它允许你组织和重用代码，同时只添加你想改变的特殊内容。Evennia经常使用这一点。

### 多重继承一瞥

在你选择的文本编辑器中打开`mygame/typeclasses/objects.py`。

```python
"""
模块文档字符串
"""
from evennia import DefaultObject

class ObjectParent:
    """
    类文档字符串 
    """

class Object(ObjectParent, DefaultObject):
    """
    类文档字符串
    """
    pass
```

在这个模块中，我们有一个名为`ObjectParent`的空`class`。它不做任何事情，它的唯一代码(除了文档字符串)是`pass`，意思是，嗯，跳过并不做任何事情。由于它也没有从任何东西_继承_，它只是一个空容器。

名为`Object`的`class`从`ObjectParent`和`DefaultObject`_继承_。通常一个类只有一个父类，但这里有两个。我们已经了解到，除非子类覆盖它，否则子类会从父类继承所有内容。当有多个父类("多重继承")时，继承从左到右发生。

所以如果`obj`是`Object`的一个实例，我们尝试访问`obj.foo`，Python会首先检查`Object`类是否有属性/方法`foo`。接下来它会检查`ObjectParent`是否有。最后，它会检查`DefaultObject`。如果都没有，你会得到一个错误。

为什么Evennia要设置一个像这样的空父类？为了回答这个问题，让我们看看另一个模块`mygame/typeclasses/rooms.py`：

```python
"""
...
"""

from evennia.objects.objects import DefaultRoom

from .objects import ObjectParent

class Room(ObjectParent, DefaultRoom):
    """
	...
    """
    pass
```

这里我们看到`Room`从相同的`ObjectParent`(从`objects.py`导入)和来自`evennia`库的`DefaultRoom`父类继承。你会发现`Character`和`Exit`也是如此。这些都是"游戏内对象"的例子，所以它们很可能有很多共同点。`ObjectParent`的存在为你提供了一种(可选的)方式来添加_应该对所有游戏实体相同_的代码。只需将该代码放入`ObjectParent`，所有对象、角色、房间和出口都会自动拥有它！

我们将在[下一课](./Beginner-Tutorial-Learning-Typeclasses.md)中回到`objects.py`模块。

## 总结

我们从类创建了第一批龙。我们学习了如何将类_实例化_为_对象_。我们看到了一些_继承_的例子，并测试了用子类中的方法_覆盖_父类中的方法。我们还有效地使用了`super()`。

到目前为止，我们使用了相当原始的Python。在接下来的课程中，我们将开始研究Evennia提供的额外内容。但首先我们需要学习到哪里找到所有东西。
