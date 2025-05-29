# 游戏内房间

一个 _房间_ 描述了游戏世界中的一个特定位置。作为一个抽象概念，它可以代表任何方便组合在一起的游戏内容区域。在本课程中，我们还将创建一个小型的游戏内自动地图。

在 EvAdventure 中，我们将有两种主要类型的房间：
- 正常的地面房间。基于固定的地图，这些房间将一次性创建，然后不会改变。本课程将涵盖这些房间。
- 地下城房间 - 这些将是 _程序生成_ 的房间，根据玩家探索地下世界的情况动态创建。作为正常房间的子类，我们将其涉及到 [地下城生成课程](./Beginner-Tutorial-Dungeon.md)。

## 基础房间

> 创建一个新的模块 `evadventure/rooms.py`。

```python
# 在 evadventure/rooms.py 中

from evennia import AttributeProperty, DefaultRoom

class EvAdventureRoom(DefaultRoom):
    """
    支持一些 EvAdventure 特定功能的简单房间。
    """
 
    allow_combat = AttributeProperty(False, autocreate=False)
    allow_pvp = AttributeProperty(False, autocreate=False)
    allow_death = AttributeProperty(False, autocreate=False)
```

我们的 `EvAdventureRoom` 非常简单。我们使用 Evennia 的 `DefaultRoom` 作为基础，仅添加三个额外的属性来定义：

- 是否允许在房间内开始战斗。
- 如果允许战斗，是否允许 PvP（玩家对玩家）战斗。
- 如果允许战斗，任何一方是否会因此死亡。

稍后我们必须确保我们的战斗系统尊重这些值。

## PvP 房间

这是一个允许非致命 PvP（比武）的房间：

```python
# 在 evadventure/rooms.py 中

# ... 

class EvAdventurePvPRoom(EvAdventureRoom):
    """
    可以发生 PvP 的房间，但无人会死亡。
    """
    
    allow_combat = AttributeProperty(True, autocreate=False)
    allow_pvp = AttributeProperty(True, autocreate=False)
    
    def get_display_footer(self, looker, **kwargs):
        """
        自定义描述的页脚。
        """
        return "|y这里允许非致命 PvP 战斗！|n"
```

`get_display_footer` 的返回值将在 [主要房间描述的后面](../../../Components/Objects.md#changing-an-objects-appearance) 显示，表明该房间是比武房间。这意味着当一个玩家 HP 降到 0 时，他们将输掉战斗，但没有死亡的风险（而在比武期间，武器通常会磨损）。

## 添加房间地图

我们希望有一个动态的地图，可以随时可视化你可以使用的出口。房间的显示如下：

```shell
  o o o
   \|/
  o-@-o
    | 
    o
十字路口
一个许多道路交汇的地方。 
出口：北、东北、南、西和西北
```

> 文档未显示 ANSI 颜色。

让我们扩展基础 `EvAdventureRoom` 以包含地图。

```{code-block} python
:linenos: 
:emphasize-lines: 12,19,51,52,58,67

# 在 evadventure/rooms.py 中

# ...

from copy import deepcopy
from evennia import DefaultCharacter
from evennia.utils.utils import inherits_from

CHAR_SYMBOL = "|w@|n"
CHAR_ALT_SYMBOL = "|w>|n"
ROOM_SYMBOL = "|bo|n"
LINK_COLOR = "|B"

_MAP_GRID = [
    [" ", " ", " ", " ", " "],
    [" ", " ", " ", " ", " "],
    [" ", " ", "@", " ", " "],
    [" ", " ", " ", " ", " "],
    [" ", " ", " ", " ", " "],
]
_EXIT_GRID_SHIFT = {
    "north": (0, 1, "||"),
    "east": (1, 0, "-"),
    "south": (0, -1, "||"),
    "west": (-1, 0, "-"),
    "northeast": (1, 1, "/"),
    "southeast": (1, -1, "\\"),
    "southwest": (-1, -1, "/"),
    "northwest": (-1, 1, "\\"),
}

class EvAdventureRoom(DefaultRoom): 

    # ...

    def format_appearance(self, appearance, looker, **kwargs):
        """不对外观字符串进行左侧去除"""
        return appearance.rstrip()
 
    def get_display_header(self, looker, **kwargs):
        """
        显示当前位置的迷你地图。
        """
        # 确保不向辅助功能用户显示地图。
        # 为了优化，我们也不向 NPC/怪物显示它
        if not inherits_from(looker, DefaultCharacter) or (
            looker.account and looker.account.uses_screenreader()
        ):
            return ""
 
        # 构建地图
        map_grid = deepcopy(_MAP_GRID)
        dx0, dy0 = 2, 2
        map_grid[dy0][dx0] = CHAR_SYMBOL
        for exi in self.exits:
            dx, dy, symbol = _EXIT_GRID_SHIFT.get(exi.key, (None, None, None))
            if symbol is None:
                # 我们有一个非主要方向要走 - 予以指明
                map_grid[dy0][dx0] = CHAR_ALT_SYMBOL
                continue
            map_grid[dy0 + dy][dx0 + dx] = f"{LINK_COLOR}{symbol}|n"
            if exi.destination != self:
                map_grid[dy0 + dy + dy][dx0 + dx + dx] = ROOM_SYMBOL
 
        # 注意，在网格上，dy 实际上是向 *下* 的 (origo 在左上角)，
        # 因此我们需要在最后反转顺序以进行镜像处理
        return "  " + "\n  ".join("".join(line) for line in reversed(map_grid))
```

`get_display_header` 返回的字符串将出现在 [房间描述的最上方](../../../Components/Objects.md#changing-an-objects-description)，这是显示地图的好地方！

- **第 12 行**：地图本身由 2D 矩阵 `_MAP_GRID` 组成。这是一个由 Python 列表描述的 2D 区域。要查找列表中的给定位置，您首先需要找出哪个嵌套列表要使用，然后使用该列表中的哪个元素。索引从 0 开始。因此，要绘制最南部房间的 `o` 符号，您需要在 `_MAP_GRID[4][2]` 上进行操作。
- **第 19 行**：`_EXIT_GRID_SHIFT` 指示每个主要出口的方向以及在该点要绘制的地图符号。因此，`"east": (1, 0, "-")` 意味着东出口将在 x 方向上向右绘制一个步骤，并使用符号 "-"。对于像 `|` 和 "\\" 这样的符号，我们需要使用双符号转义，因为这些会被解释为其他格式的一部分。
- **第 51 行**：我们通过对 `_MAP_GRID` 进行 `deepcopy` 来开始。这是为了确保我们不修改原始值，而始终有一个空模板可供使用。
- **第 52 行**：我们使用 `@` 表示玩家的位置（在坐标 `(2, 2)`）。然后，我们根据房间中的实际出口使用它们的名称来确定要从中心绘制的符号。
- **第 58 行**：我们希望能够有条件地出入网格。因此，如果一个房间有一个非主要出口（如“返回”或上下），我们将通过在当前房间显示 `>` 符号而不是 `@` 来指明这个情况。
- **第 67 行**：一旦我们在网格中放置完所有出口和房间符号，就将它们合并到一个单独的字符串中。最后，我们使用 Python 的标准 [join](https://www.w3schools.com/python/ref_string_join.asp) 将网格转换为一个单字符串。在这样做时，我们必须将网格翻转过来（反转最外层的列表）。这为什么这么做？如果你考虑一下 MUD 游戏是如何显示数据的 - 通过打印在底部然后向上滚动 - 你会意识到 Evennia 必须先发送地图的顶部，然后在最后发送底部，以便正确显示给用户。

## 为房间增添生机

通常情况下，房间在您不做任何事情时是静态的。但是，如果您在一个被描述为热闹市场的房间里，那偶尔收到一些随机消息会不会很不错？

    "你听到一个商人叫卖他的货物。"
    "音乐的声音从开着的酒吧门传来。"
    "商业的声音以稳步的节奏起伏。"

下面是如何实现这一点的示例：

```{code-block} python 
:linenos:
:emphasize-lines: 22,25

# 在 evadventure/rooms.py 中 

# ... 

from random import choice, random
from evennia import TICKER_HANDLER

# ... 

class EchoingRoom(EvAdventureRoom):
    """一个随机向房间内所有人回显消息的房间"""

    echoes = AttributeProperty(list, autocreate=False)
    echo_rate = AttributeProperty(60 * 2, autocreate=False)
    echo_chance = AttributeProperty(0.1, autocreate=False)

    def send_echo(self): 
        if self.echoes and random() < self.echo_chance: 
            self.msg_contents(choice(self.echoes))

    def start_echo(self): 
        TICKER_HANDLER.add(self.echo_rate, self.send_echo)

    def stop_echo(self): 
        TICKER_HANDLER.remove(self.echo_rate, self.send_echo)
```

[TickerHandler](../../../Components/TickerHandler.md) 充当“请按时给我 - 订阅服务”。在 **第 22 行** 中，我们告诉处理器添加我们的 `.send_echo` 方法，并请求 TickerHandler 每 `.echo_rate` 秒调用该方法。

当 `.send_echo` 方法被调用时，它将使用 `random.random()` 来检查我们是否应该 _实际_ 做任何事情。在我们的示例中，我们只有 10% 的概率显示一条消息。在这种情况下，我们使用 Python 的 `random.choice()` 从 `.echoes` 列表中随机选取一条文本字符串并发送给这个房间内的所有人。

下面是在游戏中使用此房间的方法：

    > dig market:evadventure.rooms.EchoingRoom = market,back 
    > market 
    > set here/echoes = ["你听到一个商人叫卖", "你听到硬币的叮当声"]
    > py here.start_echo() 

如果你等一段时间，你最终会看到其中一个回声出现在房间里。如果你想停止，可以使用 `py here.stop_echo()`。

能够随意启用/禁用回声是一个好主意，毕竟如果它们出现得太频繁，你会惊讶于它们会多么烦人。

在这个示例中，我们不得不借助 `py` 来激活/停用回声，但你很容易可以实现小型实用命令 [`startecho`](../Part1/Beginner-Tutorial-Adding-Commands.md) 和 `stopecho` 来为你处理这一点。我们将这留作额外练习。

## 测试

> 创建一个新的模块 `evadventure/tests/test_rooms.py`。

```{sidebar} 
您可以在教程文件夹中找到一个现成的测试模块 [here](evennia.contrib.tutorials.evadventure.tests.test_rooms)。
```
我们新房间的主要测试内容是地图。以下是测试的基本原则：

```python
# 在 evadventure/tests/test_rooms.py 中

from evennia import DefaultExit, create_object
from evennia.utils.test_resources import EvenniaTestCase
from ..characters import EvAdventureCharacter 
from ..rooms import EvAdventureRoom

class EvAdventureRoomTest(EvenniaTestCase): 

    def test_map(self): 
        center_room = create_object(EvAdventureRoom, key="room_center")
        
        n_room = create_object(EvAdventureRoom, key="room_n")
        create_object(DefaultExit, 
                      key="north", location=center_room, destination=n_room)
        ne_room = create_object(EvAdventureRoom, key="room=ne")
        create_object(DefaultExit,
                      key="northeast", location=center_room, destination=ne_room)
        # ... 其他主要方向的房间
        
        char = create_object(EvAdventureCharacter, 
                             key="TestChar", location=center_room)					        
        desc = center_room.return_appearance(char)

        # 在这里将我们获得的描述与预期的描述进行比较
```

我们创建了一堆房间，将它们链接到一个中心房间，然后确保该房间的地图外观符合我们的预期。

## 结论  

在本课程中，我们操控了字符串并制作了一个地图。更改对象的描述是改变基于文本的游戏“图形”的重要部分，因此查看 [构成对象描述的各个部分](../../../Components/Objects.md#changing-an-objects-description) 是很好的附加阅读材料。
