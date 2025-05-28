# 代码结构和工具

在本课中，我们将为 _EvAdventure_ 设置文件结构。我们将创建一些在之后会有用的工具，并学习如何编写 _测试_。

## 文件夹结构

```{sidebar} 此布局用于教程！
为了方便教程，我们将 `evadventure` 文件夹独立出来。这样隔离代码可以清晰显示我们所做的更改，并便于您稍后获取所需内容。同时，这也使我们更容易参考 `evennia/contrib/tutorials/evadventure` 中相应的代码。

对于您自己的游戏，建议您直接在游戏目录中进行修改（即，直接添加到 `commands/commands.py` 并修改 `typeclasses/` 模块）。除了 `server/` 文件夹之外，您的游戏目录代码几乎可以自由结构。
```

在 `mygame` 文件夹下创建一个名为 `evadventure` 的新文件夹。在该新文件夹内，再创建一个名为 `tests/` 的文件夹。确保在这两个新文件夹中放入空的 `__init__.py` 文件。这样做可以将这两个新文件夹转变为 Python 可以自动识别导入的包。

```
mygame/
   commands/
   evadventure/         <---
      __init__.py       <---
      tests/            <---
          __init__.py   <---
   __init__.py
   README.md
   server/
   typeclasses/
   web/
   world/
```

在 `mygame` 的任何地方导入此文件夹内的任何内容时，将使用：

```python
# 从 mygame 的任何位置/
from evadventure.yourmodulename import whatever
```

这是使用“绝对路径”的导入方法。

在两个都在 `evadventure/` 内的模块之间，可以使用 “相对” 导入：

```python
# 从 mygame/evadventure 内的一个模块
from .yourmodulename import whatever
```

例如，从 `mygame/evadventure/tests/` 中，您可以使用 `..` 导入上一级：

```python
# 从 mygame/evadventure/tests/
from ..yourmodulename import whatever
```

## 枚举（Enums）

```{sidebar}
完整的枚举模块示例可以在
[evennia/contrib/tutorials/evadventure/enums.py](../../../api/evennia.contrib.tutorials.evadventure.enums.md) 找到。
```

在 `mygame/evadventure/enums.py` 中创建一个新文件。

枚举（enum）是建立 Python 常量的一种方式。例如：

```python
# 在文件 mygame/evadventure/enums.py 中

from enum import Enum

class Ability(Enum):
    STR = "strength"
```

然后可以这样访问枚举：

```python
# 从 mygame/evadventure 的另一个模块中

from .enums import Ability

Ability.STR   # 枚举本身
Ability.STR.value  # 这个字符串 "strength"
```

使用枚举是推荐的做法。通过设置枚举，我们可以确保每次都引用相同的常量或变量。将所有枚举集中在一个地方也意味着我们对所处理的常量有更好的概述。

枚举的替代方案是，随处传递一个名为 `"constitution"` 的字符串。如果您拼写错误为 `“consitution”`，那么您不会立刻知道，因为错误会在字符串未被识别时发生。通过使用枚举，如果您在获取 `Ability.COM` 而不是 `Ability.CON` 时发生拼写错误，Python 会立即引发错误，因为你将不会识别出这个拼写存在错误的枚举。

使用枚举，您还可以进行直接比较，例如：`if ability is Ability.WIS: <do stuff>`。

请注意，`Ability.STR` 枚举没有实际的 _值_，例如，您的力量。`Ability.STR` 只是力量能力的固定标签。

下面是 _Knave_ 所需的 `enum.py` 模块。它涵盖了我们需要跟踪的规则系统的基本方面（查看 _Knave_ 的规则）。如果您以后使用其他规则系统，您很可能会逐渐扩展您的枚举，与您的需求相符。

```python
# mygame/evadventure/enums.py

class Ability(Enum):
    """
    六项基础能力加成及其他能力
    """

    STR = "strength"
    DEX = "dexterity"
    CON = "constitution"
    INT = "intelligence"
    WIS = "wisdom"
    CHA = "charisma"

    ARMOR = "armor"

    CRITICAL_FAILURE = "critical_failure"
    CRITICAL_SUCCESS = "critical_success"

    ALLEGIANCE_HOSTILE = "hostile"
    ALLEGIANCE_NEUTRAL = "neutral"
    ALLEGIANCE_FRIENDLY = "friendly"

ABILITY_REVERSE_MAP = {
    "str": Ability.STR,
    "dex": Ability.DEX,
    "con": Ability.CON,
    "int": Ability.INT,
    "wis": Ability.WIS,
    "cha": Ability.CHA
}
```

在上面的代码中，`Ability` 类包含了一些角色表的基本属性。

`ABILITY_REVERSE_MAP` 是一个方便的映射，将字符串转换为枚举。此映射的最常见使用场景是在命令中；玩家对枚举一无所知，他们只能发送字符串。因此，我们只会收到字符串 `"cha"`。使用 `ABILITY_REVERSE_MAP`，我们可以方便地将这个输入转换为 `Ability.CHA` 枚举，然后在代码中传递。

```python
ability = ABILITY_REVERSE_MAP.get(user_input)
```

## 工具模块

> 创建一个新模块 `mygame/evadventure/utils.py`

```{sidebar}
工具模块的示例见
[evennia/contrib/tutorials/evadventure/utils.py](../../../api/evennia.contrib.tutorials.evadventure.utils.md)
```

工具模块用于包含我们可能从各种其他模块中反复调用的通用函数。在本教程示例中，我们只创建一个工具：一个生成对象任何传入对象的漂亮展示的函数。

看起来可以是这样的：

```python
# 在 mygame/evadventure/utils.py 中

_OBJ_STATS = """
|c{key}|n
Value: ~|y{value}|n coins{carried}

{desc}

Slots: |w{size}|n, Used from: |w{use_slot_name}|n
Quality: |w{quality}|n, Uses: |w{uses}|n
Attacks using |w{attack_type_name}|n against |w{defense_type_name}|n
Damage roll: |w{damage_roll}|n
""".strip()


def get_obj_stats(obj, owner=None):
    """
    获取对象的统计信息字符串。

    参数：
        obj (Object): 要获取统计信息的对象。
        owner (Object): 当前拥有/携带 `obj` 的对象（如果有的话）。可以用于显示例如它们正在携带的位置。
    返回：
        str: 有关对象的漂亮信息字符串。

    """
    return _OBJ_STATS.format(
        key=obj.key,
        value=10,
        carried="[Not carried]",
        desc=obj.db.desc,
        size=1,
        quality=3,
        uses="infinite",
        use_slot_name="backpack",
        attack_type_name="strength",
        defense_type_name="armor",
        damage_roll="1d6"
    )
```

在这些教程课程中，我们主要使用过的 `""" ... """` 多行字符串通常用作函数帮助字符串，但 Python 中的三重引号字符串也用于任何多行字符串。

在上面的代码中，我们设置了一个字符串模板 (`_OBJ_STATS`)，其占位符 (`{...}`) 用于显示每个统计信息元素的位置。在 `_OBJ_STATS.format(...)` 调用中，我们动态填充这些占位符，使用传入 `get_obj_stats` 的对象数据。

如果您将 “破损的剑” 传递给 `get_obj_stats`，那么您将获得如下的输出（注意这些文档没有显示文本颜色）：

```
Chipped Sword
Value: ~10 coins [wielded in Weapon hand]

A simple sword used by mercenaries all over
the world.

Slots: 1, Used from: weapon hand
Quality: 3, Uses: None
Attacks using strength against armor.
Damage roll: 1d6
```

我们将稍后用这个功能让玩家检查任何对象，而不必为每种对象类型创建新的工具。

仔细研究 `_OBJ_STATS` 模板字符串，以便理解它的功能。`|c`、`|y`、`|w` 和 `|n` 标记是 [Evennia 颜色标记](../../../Concepts/Colors.md)，用于将文本设置为青色、黄色、白色和中性色，分别。

一些统计信息元素在上面的代码中很容易识别。例如，`obj.key` 是对象的名称，而 `obj.db.desc` 将保存对象的描述——这也是 Evennia 的默认工作原理。

到目前为止，在我们的教程中，我们尚未确定如何获取 `size`、`damage_roll` 或 `attack_type_name` 等其它属性。鉴于我们当前的目的，我们将这些值设置为固定的虚拟值，以使其能够工作！在我们将来有更多代码到位时需要回过头去重新访问它们。

## 测试

Evennia 提供了丰富的功能来帮助您测试代码。单元测试允许您设置自动测试代码的功能。完成测试之后，您可以反复运行它，以确保以后对代码所做的更改不会由于引入错误而导致功能失常。

> 创建一个新模块 `mygame/evadventure/tests/test_utils.py`

您如何知道自己在上面的代码中是否存在拼写错误？您可以通过重新加载 Evennia 服务器并在游戏中输入以下 Python 命令进行 _手动_ 测试：

```python
py from evadventure.utils import get_obj_stats;print(get_obj_stats(self))
```

这样做将输出一段关于自己的漂亮字符串！如果这可以成功，太好了！但是，当您以后更改代码时需要记住每次都手动重新运行此测试。

```{sidebar}
在 [evennia/contrib/tutorials/evadventure/tests/test_utils.py](evennia.contrib.tutorials.evadventure.tests.test_utils) 中是测试模块的示例。要深入了解 Evennia 中的单元测试，请参考 [单元测试](../../../Coding/Unit-Testing.md) 文档。
```

在本教程的特定情况下，我们期待在 `get_obj_stats` 代码变得更加完整并返回更相关的数据时，需要更新测试。

下面是测试 `get_obj_stats` 的模块：

```python
# mygame/evadventure/tests/test_utils.py

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from .. import utils

class TestUtils(EvenniaTest):
    def test_get_obj_stats(self):
        # 创建一个简单的对象进行测试
        obj = create.create_object(
            key="testobj",
            attributes=(("desc", "A test object"),)
        )
        # 将其传递至函数进行处理
        result = utils.get_obj_stats(obj)
        # 检查结果是否如我们预期的一样
        self.assertEqual(
            result,
            """
|ctestobj|n
Value: ~|y10|n coins[Not carried]

A test object

Slots: |w1|n, Used from: |wbackpack|n
Quality: |w3|n, Uses: |winfinite|n
Attacks using |wstrength|n against |warmor|n
Damage roll: |w1d6|n
""".strip()
        )
```

在上面的代码中，我们创建了一个名为 `TestUtils` 的新测试类，它继承于 `EvenniaTest`。正是这种继承使它成为一个测试类。

```{important}
掌握如何有效测试代码对于游戏开发者至关重要。因此，我们将在每个后续实现课程的结尾包含 *测试* 部分。
```

我们可以在这个类中有任意数量的方法。要让 Evennia 自动识别其中一个方法包含要测试的代码，它的名称 _必须_ 以 `test_` 前缀开头。在这里，我们的一个方法命名为 `test_get_obj_stats`。

在 `test_get_obj_stats` 方法中，我们创建一个虚拟的 `obj`，并将其分配一个 `key` 为 "testobj"。注意，我们在 `create_object` 调用中通过将属性作为元组 `(name, value)` 直接添加了 `desc` 属性！

然后，我们可以将这个虚拟对象传递通过 `get_obj_stats` 函数，并获取结果。

`assertEqual` 方法适用于所有测试类，它检查 `result` 是否与我们指定的字符串相等。如果它们相同，测试 _通过_；如果不相同，测试 _失败_，我们需要调查出了什么问题。

### 运行测试

要运行我们的工具模块测试，我们需要在 `mygame` 文件夹中执行以下命令：

```bash
evennia test --settings settings.py evadventure.tests
```

上面的命令将运行所有在 `mygame/evadventure/tests` 文件夹中找到的 `evadventure` 测试。要单独运行我们的工具测试，可以指定测试：

```bash
evennia test --settings settings.py evadventure.tests.test_utils
```

如果一切顺利，以上的工具测试将以 `OK` 结尾，表明我们的代码已通过测试。

但是，如果我们的返回字符串与预期不完全匹配，测试就会失败。我们需要开始检查和排查代码中存在的问题。

> 提示：上面的示例单元测试代码中包含一个故意的大小写错误。查看输出以解释故意错误，尝试修复它！

## 总结

理解如何在 Python 中在模块之间导入代码非常重要。如果导入 Python 模块仍然让您感到困惑，值得花时间阅读更多相关内容。

尽管如此，许多新手在处理这些概念时会感到困惑。在本课程中，通过创建文件夹结构、两个小模块，甚至编写我们第一个单元测试，您已经开始了一个良好的开端！
