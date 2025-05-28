# Evennia for Diku Users

Evennia 对于习惯于 Diku 类型 MUD 代码的用户来说有一定的学习曲线。虽然如果你已经熟悉 C 编程，使用 Python 编程会很容易，但是主要的挑战在于摆脱旧的 C 编程习惯。尝试以 C 的方式编写 Python 不仅会使代码看起来丑陋，还会导致代码不够优化且更难维护。阅读 Evennia 示例代码是理解不同问题的处理方式的好方法。

总体而言，Python 提供了丰富的资源库、安全的内存管理和优秀的错误处理。虽然 Python 代码的运行速度不如原始 C 代码快，但对于基于文本的游戏来说，这一差异并不太重要。Python 的主要优势在于极快的开发周期以及创建游戏系统的简单性。用 C 实现同样的功能可能需要更多的代码，并且更难以稳定和维护。

## 核心区别

- 如前所述，Evennia 和 Diku 派生的代码库之间的主要区别在于，Evennia 完全用 Python 编写。由于 Python 是一种解释性语言，所以没有编译阶段。它通过服务器在运行时加载 Python 模块进行修改和扩展。它还可以在 Python 运行的所有计算机平台上运行（几乎是任何地方）。
- 原始的 Diku 类型引擎将数据保存在自定义的 *平面文件* 存储解决方案中。相比之下，Evennia 将所有游戏数据存储在一种支持的 SQL 数据库中。虽然平面文件的实现更简单，但它们通常缺乏许多预期的安全特性和有效提取存储数据子集的方式。例如，如果服务器在写入平面文件时断电，它可能会损坏并丢失数据。而一个合理的数据库解决方案不会受到这个影响——在任何时候数据都不会处于不可恢复的状态。数据库也针对高效查询大量数据集进行了高度优化。

## 一些熟悉的事物

Diku 通常通过以下方式表示角色对象：

`struct char ch*` ，然后可以通过 `ch->` 访问所有与角色相关的字段。在 Evennia 中，必须注意你正在使用的对象，以及在通过后台处理访问另一个对象时，确保你访问的是正确的对象。在 Diku C 中，访问角色对象通常通过如下方式完成：

```c
/* 创建角色和房间结构的指针 */

void(struct char ch*, struct room room*){
    int dam;
    if (ROOM_FLAGGED(room, ROOM_LAVA)){
        dam = 100;
        ch->damage_taken = dam;
    }
}
```

下面是通过 `from evennia import Command` 在 Evennia 中创建命令的示例，调用命令的字符对象由一个类属性表示为 `self.caller`。在这个例子中，`self.caller` 实质上是调用该命令的 "对象"，但大多数时候它是一个账户对象。为了更贴近 Diku 的感觉，可以创建一个变量，它表示账户对象，如下所示：

```python
# mygame/commands/command.py

from evennia import Command

class CmdMyCmd(Command):
    """
    这是一个 Evennia 命令对象
    """

    [...]

    def func(self):
        ch = self.caller
        # 然后可以通过熟悉的 ch 直接访问账户对象。
        ch.msg("...")
        account_name = ch.name
        race = ch.db.race
```

如上所述，必须小心你正在处理的具体对象。如果专注于一个房间对象且需要访问账户对象：

```python
# mygame/typeclasses/room.py

from evennia import DefaultRoom

class MyRoom(DefaultRoom):
    [...]

    def is_account_object(self, object):
        # 测试对象是否为账户
        [...]

    def myMethod(self):
        # self.caller 是没有意义的，因为 self 指的是 'DefaultRoom' 对象，
        # 你必须先找到角色对象：
        for ch in self.contents:
            if self.is_account_object(ch):
                # 现在你可以通过 ch 访问账户对象：
                account_name = ch.name
                race = ch.db.race
```

## 在 Evennia 中模拟 Diku/ROM 的外观和感觉

为了在 Evennia 上模拟 Diku Mud，需要提前进行一些工作。如果有什么事情是所有编码者和构建者都记得的，那就是 VNUM 的存在。本质上，所有数据都保存在平面文件中，并通过 VNUM 索引以便于访问。Evennia 能够模拟 VNUM，以对房间/生物/物品/触发器/区域等进行分类以适应 VNUM 范围。

Evennia 有一种叫做脚本的对象。正如定义的那样，它们是在 mud 中存在的“游戏外”实例，但从未直接与之交互。脚本可用于定时器、怪物 AI，甚至独立的数据库。

由于其结构优良，所有生物、房间、区域、触发器等数据都可以保存在独立创建的全局脚本中。

以下是来自 Diku 派生平面文件的示例生物文件。

```text
#0
mob0~
mob0~
mob0
~
   Mob0
~
10 0 0 0 0 0 0 0 0 E
1 20 9 0d0+10 1d2+0
10 100
8 8 0
E
#1
Puff dragon fractal~
Puff~
Puff the Fractal Dragon is here, contemplating a higher reality.
~
   Is that some type of differential curve involving some strange, and unknown
calculus that she seems to be made out of?
~
516106 0 0 0 2128 0 0 0 1000 E
34 9 -10 6d6+340 5d5+5
340 115600
8 8 2
BareHandAttack: 12
E
T 95
```
每一行表示 MUD 读取并进行处理的内容。这些内容并不容易读取，但我们可以尝试将其模拟为一个字典，以便存储在 Evennia 创建的数据库脚本中。

首先，让我们创建一个全局脚本，它完全不执行任何操作，也不附加到任何内容上。你可以通过 @py 命令直接在游戏中创建它，或在其他文件中创建它，以进行一些检查和判断，以防这个脚本需要重新创建。可以这样完成：

```python
from evennia import create_script

mob_db = create_script("typeclasses.scripts.DefaultScript", key="mobdb",
                       persistent=True, obj=None)
mob_db.db.vnums = {}
```
通过创建一个简单的脚本对象并将其 'vnums' 属性分配为字典类型来完成。接下来，我们需要创建生物布局。

```python
# vnum : mob_data

mob_vnum_1 = {
            'key' : 'puff',
            'sdesc' : 'puff the fractal dragon',
            'ldesc' : 'Puff the Fractal Dragon is here, ' \
                      'contemplating a higher reality.',
            'ddesc' : ' Is that some type of differential curve ' \
                      'involving some strange, and unknown calculus ' \
                      'that she seems to be made out of?',
            [...]
        }

# 然后将其保存到数据中，假设你已将脚本对象存储在变量中。
mob_db.db.vnums[1] = mob_vnum_1
```

这只是一个“原始人”示例，但它传达了该概念。你可以在 `mob_db.vnums` 中使用键作为生物的 vnum，而其余部分则包含数据。

这样更容易阅读和编辑。如果你打算采取这种方法，必须记住，默认情况下，Evennia 在使用 `look` 命令时“查看”不同的属性。例如，如果你创建了此生物的实例并使其 `self.key = 1`，默认情况下，Evennia 将会说：

`Here is : 1`

你必须重构所有默认命令，以便 MUD 查看在生物上定义的其他属性。
