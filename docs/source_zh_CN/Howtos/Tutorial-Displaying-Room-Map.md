# 显示房间的动态地图

```{sidebar}
另见 [Mapbuilder](../Contribs/Contrib-Mapbuilder.md) 和 [XYZGrid](../Contribs/Contrib-XYZGrid.md) 贡献，它们提供了创建和显示房间地图的替代方法。 [初学者教程中实现 Evadventure 房间的课程](https://www.evennia.com/docs/latest/Howtos/Beginner-Tutorial/Part3/Beginner-Tutorial-Rooms.html#adding-a-room-map) 还解释了如何添加（更简单的）自动地图。
```
在 MUD 中，显示游戏内地图以帮助导航是一个常见的需求。

```
森林小径

         [.]   [.]
[.][.][@][.][.][.]
         [.]   [.][.][.]

树木在狭窄的森林小径上高耸。
出口：东，西
```

## 房间的网格

本教程需要至少两个要求：

1. 你的 MUD 的结构必须遵循逻辑布局。Evennia 支持你的世界布局为“逻辑上”不可能的布局，房间互相循环或出口通向地图的另一侧。出口也可以命名为任何内容，从“跳出窗户”到“进入第五维”。本教程假定你只能朝四个基本方向移动（北、东、西和南）。
2. 房间必须连接并互相链接，以便正确生成地图。原版 Evennia 附带了一个管理员命令 [tunnel](evennia.commands.default.building.CmdTunnel)，允许用户以基本方向创建房间，但需要额外工作以确保房间连接。例如，如果你执行 `tunnel east` 然后立即执行 `tunnel west`，你会发现你创建了两个完全独立的房间。因此，如果你想创建一个“逻辑”布局，必须小心。在本教程中，我们假设你有这样一个房间网格，我们可以从中生成地图。

## 概念

在进入代码之前，了解并概念化如何实现这一点是有益的。这个想法类似于一条虫子，从你的当前位置开始。它选择一个方向并“爬行”出去，同时映射它的路线。一旦它走过预设的距离，它就会停止并在另一个方向重新开始。一个重要的注意事项是，我们希望有一个易于调用且不太复杂的系统。因此，我们将把整个代码封装到一个自定义 Python 类中（而不是类型类，因为这不使用 Evennia 本身的核心对象）。我们要创建的东西在你输入 'look' 时显示如下：

```
走廊

      [.]   [.]
      [@][.][.][.][.]
      [.]   [.]   [.]

被遗忘的回声在空旷的走廊中回荡。
出口：北，东，南
```

你当前的位置用 `[@]` 表示，而 `[.]` 是“虫子”自离开当前位置以来所看到的其他房间。

## 设置地图显示

首先，我们必须定义用于显示地图的组件。为了让“虫子”知道在地图上绘制哪个符号，我们将让它检查每个房间上名为 `sector_type` 的属性。在本教程中，我们理解两种符号——一个是普通房间，一个是与我们所在的房间。我们还定义了一个未设置属性的房间的回退符号——这样地图即使没有正确配置房间也能正常工作。假设你的游戏文件夹命名为 `mygame`，我们将在 `mygame/world/map.py` 中创建以下代码：

```python
# 在 mygame/world/map.py 中

# 符号通过房间上的属性 "sector_type" 被标识
# 键 None 和 "you" 必须始终存在。
SYMBOLS = { None : ' . ', # 对于没有 sector_type 属性的房间
            'you' : '[@]',
            'SECT_INSIDE': '[.]' }
```

由于尝试访问未设置的属性返回 `None`，这意味着没有 `sector_type` 属性的房间显示为 ` . `。接下来，我们开始构建自定义类 `Map`。它将包含我们所需的所有方法。

```python
# 在 mygame/world/map.py 中

class Map(object):

    def __init__(self, caller, max_width=9, max_length=9):
        self.caller = caller
        self.max_width = max_width
        self.max_length = max_length
        self.worm_has_mapped = {}
        self.curX = None
        self.curY = None
```

- `self.caller` 通常是你的角色对象，即使用地图的对象。
- `self.max_width/length` 决定将生成的地图的最大宽度和长度。请注意，将这些变量设置为 *奇数* 是重要的，以确保显示区域有一个中心点。
- `self.worm_has_mapped` 基于上述虫子类比。这个字典将存储“虫子”映射的所有房间及其在网格中的相对位置。这个变量是最重要的，因为它充当检查器和地址簿，能够告诉我们虫子到过哪里以及迄今为止映射了什么。
- `self.curX/Y` 是表示虫子在网格上当前位置的坐标。

在进行任何形式的映射之前，我们需要创建一个空的显示区域，并使用以下方法对其进行一些基本检查。

```python
# 在 mygame/world/map.py 中

class Map(object):
    # [... 继续]

    def create_grid(self):
        # 此方法简单地创建一个空网格/显示区域
        # 使用 __init__(self) 中指定的变量：
        board = []
        for row in range(self.max_width):
            board.append([])
            for column in range(self.max_length):
                board[row].append('   ')
        return board

    def check_grid(self):
        # 此方法简单地检查网格以确保
        # max_l 和 max_w 都是奇数。
        return True if self.max_length % 2 != 0 or self.max_width % 2 != 0\
            else False
```

在我们将虫子放在路上之前，我们需要了解一些计算机科学的基础知识，称为“图遍历”。伪代码中我们试图实现的是：

```python
# 伪代码

def draw_room_on_map(room, max_distance):
    self.draw(room)

    if max_distance == 0:
        return

    for exit in room.exits:
        if self.has_drawn(exit.destination):
            # 如果我们已经访问过目标，则跳过绘制
            continue
        else:
            # 第一次到这里！
            self.draw_room_on_map(exit.destination, max_distance - 1)
```

Python 的美妙之处在于我们实际的代码与这个伪代码示例几乎没有差别。

- `max_distance` 是一个变量，指示我们的虫子将映射距离你当前位置多少房间。显然，数字越大，如果你周围有许多房间，它所需的时间就越长。

第一个难点是使用什么值作为“max_distance”。虫子没有理由走得比你实际显示的更远。例如，如果你的当前位置位于大小为 `max_length = max_width = 9` 的显示区域的中心，则虫子只需要向任何方向走 `4` 个单位：

```
[.][.][.][.][@][.][.][.][.]
 4  3  2  1  0  1  2  3  4
```

`max_distance` 可以基于显示区域的大小动态设置。当你的宽度/长度变化时，它变成一个简单的代数线性关系，即 `max_distance = (min(max_width, max_length) - 1) / 2`。

## 构建映射器

现在我们可以开始填充我们的 Map 对象，添加一些方法。我们仍然缺少一些非常重要的方法：

* `self.draw(self, room)` - 负责将房间实际绘制到网格上。
* `self.has_drawn(self, room)` - 检查房间是否已被映射且虫子已经到过这里。
* `self.median(self, number)` - 一个简单的工具方法，用于找到从 `0` 到 `n` 的中位数（中点）。
* `self.update_pos(self, room, exit_name)` - 通过相应地重新分配 `self.curX/Y` 来更新虫子的物理位置。
* `self.start_loc_on_grid(self)` - 表示你在网格中位置的初步绘制。
* `self.show_map` - 在所有工作完成后将地图转换为可读字符串。
* `self.draw_room_on_map(self, room, max_distance)` - 将所有内容串联在一起的主要方法。

现在我们知道需要哪些方法，下面让我们完善初始的 `__init__(self)`，以便传入一些条件语句并设置它开始构建显示。

```python
# mygame/world/map.py

class Map(object):

    def __init__(self, caller, max_width=9, max_length=9):
        self.caller = caller
        self.max_width = max_width
        self.max_length = max_length
        self.worm_has_mapped = {}
        self.curX = None
        self.curY = None

        if self.check_grid():
            # 我们必须将网格存储到一个变量中
            self.grid = self.create_grid()
            # 我们使用代数关系
            self.draw_room_on_map(caller.location,
                                  ((min(max_width, max_length) - 1) / 2))
```

在这里，我们检查网格的参数是否正确，然后创建一个空白画布并将初始位置映射为第一个房间！

如上所述，`self.draw_room_on_map()` 的代码与伪代码的差别不大。该方法如下所示：

```python
# 在 mygame/world/map.py 中，Map 类里

def draw_room_on_map(self, room, max_distance):
    self.draw(room)

    if max_distance == 0:
        return

    for exit in room.exits:
        if exit.name not in ("north", "east", "west", "south"):
            # 我们只在基本方向上绘制。如果有人想尝试一下，绘制上下方向将是一个有趣的学习项目。
            continue
        if self.has_drawn(exit.destination):
            # 我们已经到达了目的地，跳过。
            continue

        self.update_pos(room, exit.name.lower())
        self.draw_room_on_map(exit.destination, max_distance - 1)
```

“虫子”的第一件事就是在 `self.draw` 中绘制你当前的位置。让我们定义这个方法...

```python
# 在 mygame/world/map.py 中，Map 类里

def draw(self, room):
    # 首先在地图上绘制初始的角色位置！
    if room == self.caller.location:
        self.start_loc_on_grid()
        self.worm_has_mapped[room] = [self.curX, self.curY]
    else:
        # 映射所有其他房间
        self.worm_has_mapped[room] = [self.curX, self.curY]
        # 将使用 sector_type 属性或未设置时为 None。
        self.grid[self.curX][self.curY] = SYMBOLS[room.db.sector_type]
```

在 `self.start_loc_on_grid()` 中：

```python
def median(self, num):
    lst = sorted(range(0, num))
    n = len(lst)
    m = n - 1
    return (lst[n // 2] + lst[m // 2]) / 2.0

def start_loc_on_grid(self):
    x = self.median(self.max_width)
    y = self.median(self.max_length)
    # x 和 y 默认是浮点数，不能用浮点数索引列表
    x, y = int(x), int(y)

    self.grid[x][y] = SYMBOLS['you']
    self.curX, self.curY = x, y  # 更新虫子当前的位置
```

系统绘制了当前地图之后，它检查 `max_distance` 是否为 `0`（因为这是初始启动阶段，所以不是）。现在我们在获取每个房间的出口后处理迭代。它首先检查虫子所在的房间是否已经被映射... 让我们定义这个方法：

```python
def has_drawn(self, room):
    return True if room in self.worm_has_mapped.keys() else False
```

如果 `has_drawn` 返回 `False`，这意味着虫子找到一个尚未映射的房间。然后，它将“移动”到那里。`self.curX/Y` 有点滞后，因此我们必须确保跟踪虫子的位置；我们在下面的 `self.update_pos()` 方法中做到这一点。

```python
def update_pos(self, room, exit_name):
    # 这确保了坐标保持最新
    # 以至于虫子当前所处的位置。
    self.curX, self.curY = \
        self.worm_has_mapped[room][0], self.worm_has_mapped[room][1]

    # 现在我们必须根据它找到的哪条“出口”实际移动指针
    if exit_name == 'east':
        self.curY += 1
    elif exit_name == 'west':
        self.curY -= 1
    elif exit_name == 'north':
        self.curX -= 1
    elif exit_name == 'south':
        self.curX += 1
```

系统更新虫子的位置后，将新房间再次传回原始 `draw_room_on_map()` 中，并再次开始这个过程...

这就是整个过程。最后一个方法是将所有内容组合在一起，并使用 `self.show_map()` 方法创建一个漂亮的文本字符串。

```python
def show_map(self):
    map_string = ""
    for row in self.grid:
        map_string += " ".join(row)
        map_string += "\n"

    return map_string
```

## 使用地图

为了激活地图，我们将其存储在房间类型类中。如果我们将其放在 `return_appearance` 中，那么每次我们查看房间时就会获得地图。

> `return_appearance` 是所有对象上可用的默认 Evennia 钩子；例如，它由 `look` 命令调用，以获取某物（在这种情况下是房间）的描述。

```python
# 在 mygame/typeclasses/rooms.py 中

from evennia import DefaultRoom
from world.map import Map

class Room(DefaultRoom):

    def return_appearance(self, looker):
        # [...]
        string = f"{Map(looker).show_map()}\n"
        # 添加所有正常的内容，如房间描述，
        # 内容、出口等。
        string += "\n" + super().return_appearance(looker)
        return string
```

显然，这种生成地图的方法没有考虑任何隐藏的门或出口等... 但希望它作为一个良好的基础出发点。如之前所提到的，在实现这一点之前，确保房间有一个坚实的基础非常重要。你可以通过使用 @tunnel 在原版 Evennia 上尝试这项功能，基本上你可以创建一个长而直的、非循环的房间，这将显示在你的游戏地图上。

上述示例将在房间描述上方显示地图。你还可以使用 [EvTable](github:evennia.utils.evtable) 将描述和地图并排放置。你还可以添加一个 [Command](../Components/Commands.md)，它可以显示更大的半径，也许还有图例和其他功能。

以下是整个 `map.py` 供你参考。你需要更新你的 `Room` 类型类（见上）以实际调用它。请记得，要看到不同位置的符号，你还需要将 `sector_type` 属性设置为房间的 `SYMBOLS` 字典中的一个键。因此，在这个示例中，要使某个房间被映射为 `[.]`，你应将房间的 `sector_type` 设置为 `"SECT_INSIDE"`。你可以尝试使用 `@set here/sector_type = "SECT_INSIDE"`。如果你希望所有新房间都有给定的区域符号，你可以更改下面 `SYMBOLS` 字典中的默认值，或者你可以在房间的 `at_object_creation` 方法中添加该属性。

```python
# mygame/world/map.py

# 这些是通过房间上的属性 sector_type 设置的键。
# 键 None 和 "you" 必须始终存在。
SYMBOLS = { None : ' . ',  # 对于没有 sector_type 属性的房间
            'you' : '[@]',
            'SECT_INSIDE': '[.]' }

class Map(object):

    def __init__(self, caller, max_width=9, max_length=9):
        self.caller = caller
        self.max_width = max_width
        self.max_length = max_length
        self.worm_has_mapped = {}
        self.curX = None
        self.curY = None

        if self.check_grid():
            # 我们实际上需要将网格存储到一个变量中
            self.grid = self.create_grid()
            self.draw_room_on_map(caller.location,
                                 ((min(max_width, max_length) - 1) / 2))

    def update_pos(self, room, exit_name):
        # 这确保指针变量始终
        # 保持最新，以至于虫子当前所处的位置。
        self.curX, self.curY = \
           self.worm_has_mapped[room][0], self.worm_has_mapped[room][1]

        # 现在我们必须根据找到的“出口”实际移动指针变量
        if exit_name == 'east':
            self.curY += 1
        elif exit_name == 'west':
            self.curY -= 1
        elif exit_name == 'north':
            self.curX -= 1
        elif exit_name == 'south':
            self.curX += 1

    def draw_room_on_map(self, room, max_distance):
        self.draw(room)

        if max_distance == 0:
            return

        for exit in room.exits:
            if exit.name not in ("north", "east", "west", "south"):
                # 我们只在基本方向上绘制。如果有人想尝试一下，绘制上下方向将是一个有趣的学习项目。
                continue
            if self.has_drawn(exit.destination):
                # 我们已经到达了目的地，跳过。
                continue

            self.update_pos(room, exit.name.lower())
            self.draw_room_on_map(exit.destination, max_distance - 1)

    def draw(self, room):
        # 首先在地图上绘制初始的角色位置！
        if room == self.caller.location:
            self.start_loc_on_grid()
            self.worm_has_mapped[room] = [self.curX, self.curY]
        else:
            # 映射所有其他房间
            self.worm_has_mapped[room] = [self.curX, self.curY]
            # 将使用 sector_type 属性或未设置时为 None。
            self.grid[self.curX][self.curY] = SYMBOLS[room.db.sector_type]

    def median(self, num):
        lst = sorted(range(0, num))
        n = len(lst)
        m = n - 1
        return (lst[n // 2] + lst[m // 2]) / 2.0

    def start_loc_on_grid(self):
        x = self.median(self.max_width)
        y = self.median(self.max_length)
        # x 和 y 默认是浮点数，不能用浮点数索引列表
        x, y = int(x), int(y)

        self.grid[x][y] = SYMBOLS['you']
        self.curX, self.curY = x, y # 更新虫子当前的位置


    def has_drawn(self, room):
        return True if room in self.worm_has_mapped.keys() else False


    def create_grid(self):
        # 此方法简单地创建一个空网格
        # 使用 __init__(self) 中指定的变量：
        board = []
        for row in range(self.max_width):
            board.append([])
            for column in range(self.max_length):
                board[row].append('   ')
        return board

    def check_grid(self):
        # 此方法简单地检查网格以确保
        # max_l 和 max_w 都是奇数
        return True if self.max_length % 2 != 0 or \
                    self.max_width % 2 != 0 else False

    def show_map(self):
        map_string = ""
        for row in self.grid:
            map_string += " ".join(row)
            map_string += "\n"

        return map_string
```

## 最后的评论

动态地图可以扩展到更多功能。例如，它可以标记出口，或者允许 NE、SE 等方向。它还可以为不同的地形类型使用颜色。人们还可以研究上下方向，并找出如何以良好的方式呈现。
