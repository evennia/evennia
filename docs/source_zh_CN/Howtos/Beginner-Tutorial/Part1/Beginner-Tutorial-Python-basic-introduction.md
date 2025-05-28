# Python与Evennia入门指南

是时候开始接触一些编码了！Evennia是使用[Python](https://python.org)编写和扩展的。Python是一种成熟且专业的编程语言，开发效率非常高。

虽然Python被广泛认为易于学习，但本教程只能涵盖基础知识。我们会尽量讲解最重要的部分，但您可能还需要自行补充学习。幸运的是，网上有大量免费的Python学习资源。可以参考我们的[链接章节](../../../Links.md)获取一些示例。

> 如果您是经验丰富的开发者，可能会觉得这些内容很基础，但建议至少阅读前几节，了解如何在Evennia中运行Python。

如果您正在体验教程世界，请确保恢复超级用户权限：

       unquell

## Evennia的Hello World

`py`命令(或别名`!`)允许超级用户在游戏中执行原始Python代码，非常适合快速测试。在游戏输入行中输入：

    > py print("Hello World!")

```{sidebar} 命令输入

以`>`开头的行表示在游戏中输入的指令，下面的行是该指令的预期输出。
```

您将看到：

    > print("Hello world!")
    Hello World!

`print(...)`是Python中基本的文本输出*函数*。我们将"Hello World"作为单个*参数*传递给这个函数。如果传递多个参数，需要用逗号分隔。

引号`"..."`表示您输入的是*字符串*(即文本)。也可以使用单引号`'...'` - Python都接受。

> 第三种输入Python字符串的方式是使用三引号(`"""..."""`或`'''...'''`)，用于跨多行的长字符串。但在`py`命令中直接插入代码时，我们只能使用单行。

## 制作一些文本"图形"

在制作文本游戏时，您会大量处理文本。即使偶尔有按钮或图形元素，通常流程也是用户输入文本命令并获取文本反馈。如上所示，在Python中一段文本称为*字符串*，用单引号或双引号括起来。

字符串可以相加：

    > py print("这是一个" + "重大改变。")
    这是一个重大改变。

字符串乘以数字会重复该字符串：

    > py print("|" + "-" * 40 + "|")
    |----------------------------------------|

或

    > py print("A" + "a" * 5 + "rgh!")
    Aaaaaargh!

### .format()

```{sidebar} 函数与方法
- 函数：通过零个或多个`参数`调用的独立操作，如`print()`
- 方法：位于对象上的函数，通过`.`运算符访问，如`obj.msg()`或这里的`<string>.format()`
```

虽然组合字符串很有用，但更强大的是能够就地修改字符串内容。Python有几种方式可以实现，这里展示其中两种。第一种是使用字符串的`.format`*方法*：

    > py print("这是一个{}主意！".format("好"))
    这是一个好主意！

方法可以看作对象上的资源。方法知道它所属的对象，因此可以以各种方式影响它。您通过句点`.`访问它。这里，字符串有一个`format(...)`资源来修改它。具体来说，它用传递给format的值替换字符串中的`{}`标记。可以多次这样做：

    > py print("这是{}和{} {}主意！".format("第一个", "第二个", "绝妙"))
    这是第一个和第二个绝妙主意！

> 注意结尾的双括号 - 第一个关闭`format(...`方法，最外层的关闭`print(...`。不关闭会导致可怕的`SyntaxError`。我们将在下一节讨论错误。

这里我们传递了三个逗号分隔的字符串作为*参数*给字符串的`format`方法。它们按给定顺序替换了`{}`标记。

输入不一定非是字符串：

    > py print("力量: {}, 敏捷: {}, 智力: {}".format(12, 14, 8))
    力量: 12, 敏捷: 14, 智力: 8

要在同一行分隔两个Python指令，使用分号`;`。试试：

    > py a = "超赞酱料" ; print("这是{}！".format(a))
    这是超赞酱料！

```{warning} MUD客户端与分号

有些MUD客户端使用分号`;`将客户端输入分成多个发送。如果是这样，上面会出错。大多数客户端允许使用"逐字"模式或重新映射为其他分隔符。如果仍有问题，请使用Evennia网页客户端。
```

这里我们*赋值*字符串`"超赞酱料"`给一个名为`a`的*变量*。在下一个语句中，Python记住了`a`是什么，我们将其传递给`format()`获取输出。如果在中间更改`a`的值，将打印新值。

再次展示属性示例，将属性移到变量中(这里只是设置，但在真实游戏中可能会随时间变化或受环境影响)：

    > py 力量, 敏捷, 智力 = 13, 14, 8 ; print("力量: {}, 敏捷: {}, 智力: {}".format(力量, 敏捷, 智力))
    力量: 13, 敏捷: 14, 智力: 8

关键是即使属性值变化，print()语句也不会改变 - 它只是漂亮地打印给定的任何内容。

也可以使用命名标记：

     > py print("力量: {stren}, 智力: {intel}, 力量再次: {stren}".format(dext=10, intel=18, stren=9))
     力量: 9, 智力: 18, 力量再次: 9

添加的`key=value`对称为`format()`方法的*关键字参数*。每个命名参数将匹配字符串中的`{key}`。使用关键字时，添加顺序无关紧要。字符串中没有`{dext}`但有两次`{stren}`，这完全没问题。

### f-字符串

使用`.format()`很强大(还有[更多功能](https://www.w3schools.com/python/ref_string_format.asp))。但*f-字符串*更方便。f-字符串看起来像普通字符串...只是前面有个`f`：

    f"这是一个f-字符串。"

单独的f-字符串就像任何其他字符串。但让我们用f-字符串重做之前的例子：

    > py a = "超赞酱料" ; print(f"这是{a}！")
    这是超赞酱料！

我们使用`{a}`直接将变量`a`插入f-字符串。需要记住的括号更少，可以说也更易读！

    > py 力量, 敏捷, 智力 = 13, 14, 8 ; print(f"力量: {力量}, 敏捷: {敏捷}, 智力: {智力}")
    力量: 13, 敏捷: 14, 智力: 8

在现代Python代码中，f-字符串比`.format()`更常用，但阅读代码时需要了解两者。

当我们创建命令并需要解析和理解玩家输入时，将探索更复杂的字符串概念。

### 彩色文本

Python本身不支持彩色文本，这是Evennia的功能。Evennia支持传统MUD的标准配色方案。

    > py print("|r这是红色文本！|n 这是正常颜色。")

开头的`|r`将使输出变为亮红色。`|R`是深红色。`|n`恢复正常文本颜色。也可以使用0-5的RGB值(Xterm256颜色)：

    > py print("|043这是蓝绿色。|[530|003 现在是橙色背景上的深蓝色文本。")

> 如果看不到预期颜色，您的客户端或终端可能不支持Xterm256(或根本不支持颜色)。请使用Evennia网页客户端。

使用命令`color ansi`或`color xterm`查看可用颜色。尽情尝试！更多信息请参阅[颜色文档](../../../Concepts/Colors.md)。

## 从其他模块导入代码

如前所述，我们使用`.format`格式化字符串，使用`me.msg`访问`me`上的`msg`方法。这种使用句点字符的方式可用于访问各种资源，包括其他Python模块中的资源。

保持游戏运行，然后打开您选择的文本编辑器。如果游戏文件夹名为`mygame`，在子文件夹`mygame/world`中创建新文本文件`test.py`。文件结构应如下：

```
mygame/
    world/
        test.py
```

暂时只在`test.py`中添加一行：

```python
print("Hello World!")
```

```{sidebar} Python模块

这是带有`.py`扩展名的文本文件。模块包含Python源代码，在Python中可以通过其python路径导入访问其内容。
```

别忘了*保存*文件。我们刚创建了第一个Python*模块*！
要在游戏中使用，必须*导入*它。试试：

    > py import world.test
    Hello World

如果出错(下面将介绍如何处理错误)，确保文本与上面完全一致，然后在游戏中运行`reload`命令使更改生效。

...如您所见，导入`world.test`实际上意味着导入`world/test.py`。将句点`.`视为替换路径中的`/`(Windows中是`\`)。

`test.py`的`.py`扩展名不包含在这个"Python路径"中，但*只有*带有该扩展名的文件才能这样导入。`mygame`在哪里？答案是Evennia已经告诉Python您的`mygame`文件夹是一个很好的导入查找位置。所以我们不应在路径中包含`mygame` - Evennia已为我们处理。

导入模块时，其顶层代码会立即执行。这里会立即打印"Hello World"。

现在尝试再次运行：

    > py import world.test

这次或以后都不会看到输出！这不是bug。而是因为Python导入的工作方式 - 它会存储所有导入的模块并避免重复导入。所以`print`只会在模块首次导入时运行一次。

试试：

    > reload

然后

    > py import world.test
    Hello World!

现在又看到了。`reload`清除了服务器内存中的导入内容，所以必须重新导入。每次想要显示hello-world时都必须这样做，这不太实用。

> 我们将在[后续课程](./Beginner-Tutorial-Python-classes-and-objects.md#importing-things)中回到更高级的导入方式 - 这是一个重要主题。但现在，让我们继续解决这个特定问题。

### 第一个自定义函数

我们希望随时打印hello-world消息，而不仅是在服务器重载后一次。将`mygame/world/test.py`改为：

```python
def hello_world():
    print("Hello World!")
```

```{sidebar}
如果您来自Javascript或C等其他语言，可能熟悉变量和函数名称混合大小写，如`helloWorld()`。虽然可以这样命名，但会与其他Python代码冲突 - Python标准是对所有变量和方法使用小写和下划线`_`。
```

随着转向多行Python代码，有一些重要事项需记住：

- Python中大小写敏感。必须是`def`而非`DEF`，`hello_world()`与`Hello_World()`不同。
- Python中缩进很重要。第二行必须缩进，否则不是有效代码。还应使用一致的缩进长度。为了您的理智，*强烈*建议设置编辑器在按TAB键时总是缩进*4个空格*(**不是**单个制表符)。

关于这个函数。第1行：

- `def`是"define"的缩写，定义*函数*(或对象上的*方法*)。这是[Python保留关键字](https://docs.python.org/2.5/ref/keywords.html)；尽量不要在其他地方使用这些词。
- 函数名不能有空格，但其他方面几乎可以任意命名。我们称它为`hello_world`。Evennia遵循[Python标准命名风格](../../../Coding/Evennia-Code-Style.md)，使用小写字母和下划线。建议您也这样做。
- 行尾的冒号(`:`)表示函数头已完成。

第2行：

- 缩进标记函数实际操作代码的开始(函数*体*)。如果希望更多行属于此函数，这些行都必须至少以此缩进级别开始。

现在试试。首先`reload`游戏以获取更新的Python模块，然后导入它。

    > reload
    > py import world.test

没发生任何事！这是因为模块中的函数仅通过导入不会执行任何操作(这正是我们想要的)。只有在*调用*时才会执行。所以需要先导入模块，然后访问其中的函数：

    > py import world.test ; world.test.hello_world()
    Hello world!

出现了"Hello World"！如前所述，使用分号将多个Python语句放在一行。也请注意之前关于MUD客户端使用`;`的警告。

发生了什么？首先照常导入`world.test`。但这次模块的"顶层"只定义了函数，并未实际执行函数体。

通过在`hello_world`函数后添加`()`，我们*调用*了它。即执行函数体并打印文本。现在可以多次重复，无需在中间`reload`：

    > py import world.test ; world.test.hello_world()
    Hello world!
    > py import world.test ; world.test.hello_world()
    Hello world!

## 向他人发送文本

`print`是标准Python结构。我们可以在`py`命令中使用它，因为可以看到输出。非常适合调试和快速测试。但如果需要向实际玩家发送文本，`print`不行，因为它不知道发送给*谁*。试试：

    > py me.msg("Hello world!")
    Hello world!

看起来与`print`结果相同，但现在实际上是向特定*对象*`me`发送消息。`me`是'我们'的快捷方式，即运行`py`命令的人。它不是特殊的Python东西，而是Evennia为了方便在`py`命令中提供的(`self`是其别名)。

`me`是*对象实例*的例子。对象在Python和Evennia中是基础。`me`对象还包含许多有用的资源来操作该对象。我们通过'`.`'访问这些资源。

其中一个资源是`msg`，类似于`print`，但将文本发送给它所属的对象。例如，如果有对象`you`，执行`you.msg(...)`会向对象`you`发送消息。

目前，`print`和`me.msg`行为相同，但请记住`print`主要用于调试，而`.msg()`将来对您更有用。

## 解析Python错误

让我们在刚创建的函数中尝试这个新文本发送功能。回到`test.py`文件，将函数替换为：

```python
def hello_world():
    me.msg("Hello World!")
```

保存文件并`reload`服务器告诉Evennia重新导入新代码，然后像之前一样运行：

     > py import world.test ; world.test.hello_world()

不行 - 这次出现*错误*！

```python
File "./world/test.py", line 2, in hello_world
    me.msg("Hello World!")
NameError: name 'me' is not defined
```

```{sidebar} 日志中的错误

在常规使用中，回溯通常出现在日志而非游戏中。使用`evennia --log`在终端查看日志。如果预期错误但没看到，请确保回滚。使用`Ctrl-C`(Mac上是`Cmd-C`)退出日志查看。
```

这称为*回溯*。Python的错误非常友好，大多数时候会准确告诉您问题及位置。学会解析回溯很重要，这样才能修复代码。

回溯应*从下往上*阅读：

- (第3行) `NameError`类型错误是问题...
- (第3行) ...更具体地说是因为变量`me`未定义。
- (第2行) 这发生在`me.msg("Hello world!")`行...
- (第1行) ...即文件`./world/test.py`的第`2`行。

本例中回溯很短。上面可能有更多行，追踪不同模块如何互相调用直到问题行。有时这些信息很有用，但从底部开始总是好的起点。

这里的`NameError`是因为模块是独立的。它对导入环境一无所知。它知道`print`是什么，因为那是特殊的[Python保留关键字](https://docs.python.org/2.5/ref/keywords.html)。但`me`*不是*这样的保留字(如前所述，只是Evennia为了方便在`py`命令中添加的)。对模块来说，`me`是一个陌生的名字，不知从哪冒出来的。因此出现`NameError`。

## 向函数传递参数

我们知道在运行`py`命令时`me`存在，因为可以无问题地执行`py me.msg("Hello World!")`。所以让我们将`me`*传递*给函数，让它知道应该是什么。回到`test.py`，改为：

```python
def hello_world(who):
    who.msg("Hello World!")
```
我们为函数添加了一个*参数*。可以任意命名。无论`who`是什么，我们都将调用其`.msg()`方法。

照常`reload`服务器确保新代码可用。

    > py import world.test ; world.test.hello_world(me)
    Hello World!

现在工作了。我们将`me`*传递*给函数。它在函数内重命名为`who`，现在函数正常工作并按预期打印。注意`hello_world`函数不关心您传递什么，只要它有`.msg()`方法。因此可以重复使用此函数处理其他合适目标。

> **额外练习**：尝试将其他内容传递给`hello_world`。例如传递数字`5`或字符串`"foo"`。会得到错误，提示它们没有`msg`属性。它们不关心`me`本身不是字符串或数字。如果熟悉其他语言(尤其是C/Java)，可能想在发送前*验证*`who`确保类型正确。这在Python中通常不推荐。Python哲学是[处理](https://docs.python.org/2/tutorial/errors.html)发生的错误，而不是添加大量代码防止错误发生。参见[鸭子类型](https://en.wikipedia.org/wiki/Duck_typing)和*Leap before you Look*概念。

## 寻找其他发送对象

让我们通过寻找其他发送对象来结束第一个Python`py`速成课程。

在Evennia的`contrib/`文件夹(`evennia/contrib/tutorial_examples/mirror.py`)中有一个方便的小对象叫`TutorialMirror`。镜子会将它收到的任何内容回显到所在房间。

在游戏命令行中，创建一个镜子：

    > create/drop mirror:contrib.tutorials.mirror.TutorialMirror

```{sidebar} 创建对象

`create`命令首次用于在[构建物品](./Beginner-Tutorial-Building-Quickstart.md)教程中创建箱子。现在应能识别它使用"python-path"告诉Evennia从哪里加载镜像代码。
```

镜子应出现在您的位置。

    > look mirror
    mirror shows your reflection:
    This is User #1

您看到的实际上是游戏中的自己的化身，与`py`命令中的`me`相同。

现在目标是实现`mirror.msg("Mirror Mirror on the wall")`的等效操作。但首先想到的不会工作：

    > py mirror.msg("Mirror, Mirror on the wall ...")
    NameError: name 'mirror' is not defined.

这不奇怪：Python对"mirrors"或位置等一无所知。我们使用的`me`如前所述，只是Evennia开发者为方便`py`命令提供的。他们不可能预测您想与镜子对话。

相反，我们需要先*搜索*`mirror`对象才能发送。确保与镜子在同一位置并尝试：

    > py me.search("mirror")
    mirror

`me.search("name")`默认会搜索并*返回*与`me`对象在同一位置中给定名称的对象。如果找不到，会看到错误。

```{sidebar} 函数返回

像`print`这样的函数只打印参数，但函数/方法*返回*某种结果非常常见。将函数视为机器 - 放入一些东西，出来一个可用的结果。对于`me.search`，它将执行数据库搜索并吐出找到的对象。
```

    > py me.search("dummy")
    Could not find 'dummy'.

通常希望在同一位置找到东西，但随着继续，我们会发现Evennia提供了丰富的工具来标记、搜索和查找游戏中的所有内容。

现在知道如何找到'mirror'对象，只需用它替代`me`！

    > py mirror = self.search("mirror") ; mirror.msg("Mirror, Mirror on the wall ...")
    mirror echoes back to you:
    "Mirror, Mirror on the wall ..."

镜子对测试很有用，因为它的`.msg`方法只是将发送给它的任何内容回显到房间。更常见的是与玩家角色对话，在这种情况下，您发送的文本会出现在他们的游戏客户端中。

## 多行py

到目前为止，我们以单行模式使用`py`，用`;`分隔多个输入。这在快速测试时非常方便。但也可以在Evennia中启动完整的多行Python交互解释器。

    > py
    Evennia Interactive Python mode
    Python 3.11.0 (default, Nov 22 2022, 11:21:55)
    [GCC 8.2.0] on Linux
    [py mode - quit() to exit]

(输出的详细信息因Python版本和操作系统而异)。您现在处于python解释器模式。意味着从现在插入的*所有*内容都将成为Python代码行(您不能再查看或执行其他命令)。

    > print("Hello World")

    >>> print("Hello World")
    Hello World
    [py mode - quit() to exit]

注意现在不需要在前面加`py`。系统还会回显您的输入(这是`>>>`之后的部分)。为简洁起见，本教程将关闭回显。先退出`py`，然后使用`/noecho`标志重新启动。

    > quit()
    Closing the Python console.
    > py/noecho
    Evennia Interactive Python mode (no echoing of prompts)
    Python 3.11.0 (default, Nov 22 2022, 11:21:56)
    [GCC 8.2.0] on Linux
    [py mode - quit() to exit]

```{sidebar} 交互式py

- 以`py`开始。
- 使用`py/noecho`如果不想每行都回显输入。
- *所有*输入将被解释为Python代码。
- 用`quit()`退出。
```

现在可以输入多行Python代码：

    > a = "Test"
    > print(f"This is a {a}.")
    This is a Test.

让我们尝试定义一个函数：

    > def hello_world(who, txt):
    ...
    >     who.msg(txt)
    ...
    >
    [py mode - quit() to exit]

上面一些重要事项：

- 用`def`定义函数意味着我们开始一个新的代码块。Python通过缩进标记块内容。所以下一行必须手动缩进(4个空格是个好标准)，以便Python知道它是函数体的一部分。
- 我们扩展`hello_world`函数，添加另一个参数`txt`。这允许我们发送任何文本，而不只是重复"Hello World"。
- 告诉`py`不再向函数体添加行，我们以空输入结束。当正常提示返回时，我们知道已完成。

现在定义了一个新函数。试试：

    > hello_world(me, "Hello world to me!")
    Hello world to me!

`me`仍然可用，所以我们将其作为`who`参数传递，以及稍长的字符串。让我们结合搜索镜子。

    > mirror = me.search("mirror")
    > hello_world(mirror, "Mirror, Mirror on the wall ...")
    mirror echoes back to you:
    "Mirror, Mirror on the wall ..."

用以下方式退出`py`模式：

    > quit()
    Closing the Python console.

## 其他测试Python代码的方式

`py`命令在游戏中实验Python非常强大。非常适合快速测试。但仍受限于通过telnet或webclient工作，这些接口本身不了解Python。

在游戏外，转到运行Evennia的终端(或任何`evennia`命令可用的终端)。

- `cd`到游戏目录。
- `evennia shell`

打开Python shell。这与游戏中的`py`类似，只是默认没有`me`可用。如果需要`me`，必须先找到自己：

    > import evennia
    > me = evennia.search_object("YourChar")[0]

这里我们直接导入`evennia`，使用其搜索功能之一。后面将介绍更高级的搜索，现在只需将"YourChar"替换为您自己的角色名。

> 结尾的`[0]`是因为`.search_object`返回对象列表，我们想要第一个(计数从0开始)。

使用`Ctrl-D`(Mac上是`Cmd-D`)或`quit()`退出Python控制台。

## ipython

默认Python shell相当有限且丑陋。*强烈*建议安装`ipython`。这是一个更美观的第三方Python解释器，具有颜色和许多可用性改进。

    pip install ipython

如果安装了`ipython`，`evennia shell`会自动使用它。

    evennia shell
    ...
    IPython 7.4.0 -- An enhanced Interactive Python. Type '?' for help
    In [1]: 现在有Tab补全：

    > import evennia
    > evennia.<TAB>

即输入`evennia.`然后按TAB键 - 将获得`evennia`对象上所有可用资源的列表。这对探索Evennia提供的功能非常有用。例如，用箭头键滚动到`search_object()`填充它。

    > evennia.search_object?

添加`?`并按回车将获得`.search_object`的完整文档。使用`??`如果想查看整个源代码。

与普通python解释器一样，使用`Ctrl-D`/`Cmd-D`或`quit()`退出ipython。

```{important} 持久代码

`py`和`python`/`ipython`的共同点是编写的代码不持久 - 关闭解释器后会消失(但ipython会记住输入历史)。要创建持久的Python代码，需要将其保存在Python模块中，就像我们对`world/test.py`所做的那样。
```

## 结论

这涵盖了相当多的基本Python用法。我们打印和格式化字符串，定义了第一个函数，修复了错误，甚至搜索并与镜子对话！能够在游戏内外访问python是测试和调试的重要技能，但在实践中，您将在Python模块中编写大部分代码。

为此，我们还在`mygame/`游戏目录中创建了第一个新的Python模块，然后导入并使用它。现在让我们看看`mygame/`文件夹中的其他内容...
