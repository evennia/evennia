# 地图构建器

贡献者：Cloud_Keeper 2016

根据2D ASCII地图的绘图构建游戏地图。

这是一个命令，它需要两个输入：

```
≈≈≈≈≈
≈♣n♣≈   MAP_LEGEND = {("♣", "♠"): build_forest,
≈∩▲∩≈                 ("∩", "n"): build_mountains,
≈♠n♠≈                 ("▲"): build_temple}
≈≈≈≈≈
```

一个表示地图的ASCII字符字符串和一个包含构建指令的函数字典。地图的字符会被迭代并与触发字符列表进行比较。当找到匹配项时，将执行相应的函数，生成用户构建指令所定义的房间、出口和对象。如果字符不匹配提供的触发字符（包括空格），则会被简单跳过，处理流程将继续进行。

例如，上面的地图表示一个寺庙（▲）坐落在山间（n,∩）的森林（♣,♠）上，四周环绕着水（≈）。第一行的每个字符都被迭代，但是由于与我们的 `MAP_LEGEND` 中没有匹配项，因此被跳过。在第二行它找到“♣”，这是一个匹配项，因此将调用 `build_forest` 函数。接着调用 `build_mountains` 函数，直到地图完成。构建指令会接收以下参数：

- `x` - 房间在地图上的x轴位置
- `y` - 房间在地图上的y轴位置
- `caller` - 调用命令的账户
- `iteration` - 当前迭代次数（0, 1或2）
- `room_dict` - 包含房间引用的字典，这些引用是由构建函数返回的，以元组坐标作为键。即 `room_dict[(2, 2)]` 将返回上面的寺庙房间。

构建函数应返回它们创建的房间。默认情况下，这些房间用于在有效相邻房间之间的北、南、东和西方向创建出口。这种行为可以通过使用切换参数来关闭。此外，切换参数允许地图多次迭代。这对于自定义出口生成等情况非常重要。由于出口需要对出口位置和目的地的引用，因此在第一次迭代中，可能会创建一个指向尚未创建的目的地的出口，从而引发错误。通过对地图进行两次迭代，可以在第一次迭代中创建房间，并在第二次迭代中使用依赖于房间的代码。迭代编号和对先前创建房间的引用的字典会传递给构建命令。

然后您在游戏中调用命令，使用 `MAP` 和 `MAP_LEGEND` 变量的路径。您提供的路径是相对于evennia或mygame文件夹的。

参见[文档中的单独教程](./Contrib-Mapbuilder-Tutorial.md)。

## 安装

通过导入并在您的 `default_cmdsets` 模块中包含命令来使用。例如：

```python
    # mygame/commands/default_cmdsets.py

    from evennia.contrib.grid import mapbuilder

    ...

    self.add(mapbuilder.CmdMapBuilder())
```

## 使用：

    mapbuilder[/switch] <path.to.file.MAPNAME> <path.to.file.MAP_LEGEND>

- `one` - 执行构建指令一次，不自动创建出口。
- `two` - 执行构建指令两次，不自动创建出口。

## 示例

    mapbuilder world.gamemap.MAP world.maplegend.MAP_LEGEND
    mapbuilder evennia.contrib.grid.mapbuilder.EXAMPLE1_MAP EXAMPLE1_LEGEND
    mapbuilder/two evennia.contrib.grid.mapbuilder.EXAMPLE2_MAP EXAMPLE2_LEGEND
            (图例路径默认为地图路径)

以下是两个示例，展示了自动出口生成和自定义出口生成的使用。虽然可以在这个模块中使用，并且方便，但以下示例代码应放在 `mymap.py` 中的 `mygame/world`。

### 示例一

```python
from django.conf import settings
from evennia.utils import utils

# mapbuilder evennia.contrib.grid.mapbuilder.EXAMPLE1_MAP EXAMPLE1_LEGEND

# -*- coding: utf-8 -*-

# 添加构建指令所需的导入。
from evennia import create_object
from typeclasses import rooms, exits
from random import randint
import random


# 一张包含寺庙（▲）的地图，周围环绕着山（n,∩）的森林（♣,♠），位于水（≈）的岛上。
EXAMPLE1_MAP = '''
≈≈≈≈≈
≈♣n♣≈
≈∩▲∩≈
≈♠n♠≈
≈≈≈≈≈
'''

def example1_build_forest(x, y, **kwargs):
    '''构建指令的简单示例。确保其中包含**kwargs，并且返回房间的实例以供出口生成。'''

    # 创建房间并提供基本描述。
    room = create_object(rooms.Room, key="forest" + str(x) + str(y))
    room.db.desc = "基础森林房间。"

    # 向账户发送消息
    kwargs["caller"].msg(room.key + " " + room.dbref)

    # 这通常是必需的。
    return room


def example1_build_mountains(x, y, **kwargs):
    '''一个稍微复杂的房间'''

    # 创建房间。
    room = create_object(rooms.Room, key="mountains" + str(x) + str(y))

    # 通过从列表中随机选择条目来生成描述。
    room_desc = [
        "山延绵不绝，望不到边",
        "你的道路被陡峭的悬崖包围",
        "你以前是否见过那块岩石?",
    ]
    room.db.desc = random.choice(room_desc)

    # 创建随机数量的对象以填充房间。
    for i in range(randint(0, 3)):
        rock = create_object(key="岩石", location=room)
        rock.db.desc = "一块普通的石头。"

    # 向账户发送消息
    kwargs["caller"].msg(room.key + " " + room.dbref)

    # 这通常是必需的。
    return room


def example1_build_temple(x, y, **kwargs):
    '''一个独特的房间，不需要像之前那么一般化'''

    # 创建房间。
    room = create_object(rooms.Room, key="temple" + str(x) + str(y))

    # 设置描述。
    room.db.desc = (
        "在外观上是一座宏伟古老的寺庙，你竟然发现自己身处于"
        "Evennia客栈！这里是一个大房间，四周布满桌子。"
        "酒吧的桌子延伸在东墙上，各种桶和瓶子排满了货架。"
        "酒保似乎正忙于分发啤酒，与顾客交谈，顾客们是一群吵闹又愉快的人，"
        "使得声音水平几乎达到雷鸣般的程度。这是这片可怕沼泽中难得的欢声笑语。"
    )

    # 向账户发送消息
    kwargs["caller"].msg(room.key + " " + room.dbref)

    # 这通常是必需的。
    return room


# 在图例字典中包括您的触发字符和构建函数。
EXAMPLE1_LEGEND = {
    ("♣", "♠"): example1_build_forest,
    ("∩", "n"): example1_build_mountains,
    ("▲"): example1_build_temple,
}
```

### 示例二

```python
# @mapbuilder/two evennia.contrib.grid.mapbuilder.EXAMPLE2_MAP EXAMPLE2_LEGEND

# -*- coding: utf-8 -*-

# 添加构建指令所需的导入。
# from evennia import create_object
# from typeclasses import rooms, exits
# from evennia.utils import utils
# from random import randint
# import random

# 这是与示例1相同的布局，但包括了出口的字符。
# 我们可以使用这些字符来确定哪些房间应连接在一起。
EXAMPLE2_MAP = '''
≈ ≈ ≈ ≈ ≈

≈ ♣-♣-♣ ≈
  |   |
≈ ♣ ♣ ♣ ≈
  | | |
≈ ♣-♣-♣ ≈

≈ ≈ ≈ ≈ ≈
'''

def example2_build_forest(x, y, **kwargs):
    '''基础房间'''
    # 如果不是第一次迭代 - 什么都不做。
    if kwargs["iteration"] > 0:
        return None

    room = create_object(rooms.Room, key="forest" + str(x) + str(y))
    room.db.desc = "基础森林房间。"

    kwargs["caller"].msg(room.key + " " + room.dbref)

    return room

def example2_build_verticle_exit(x, y, **kwargs):
    '''创建两个出口，分别连接南北两个房间。'''
    # 如果是在第一次迭代 - 什么都不做。
    if kwargs["iteration"] == 0:
        return

    north_room = kwargs["room_dict"][(x, y - 1)]
    south_room = kwargs["room_dict"][(x, y + 1)]

    # 在房间内创建出口
    create_object(
        exits.Exit, key="south", aliases=["s"], location=north_room, destination=south_room
    )

    create_object(
        exits.Exit, key="north", aliases=["n"], location=south_room, destination=north_room
    )

    kwargs["caller"].msg("连接： " + north_room.key + " & " + south_room.key)


def example2_build_horizontal_exit(x, y, **kwargs):
    '''创建两个出口，分别连接东西两个房间。'''
    # 如果是在第一次迭代 - 什么都不做。
    if kwargs["iteration"] == 0:
        return

    west_room = kwargs["room_dict"][(x - 1, y)]
    east_room = kwargs["room_dict"][(x + 1, y)]

    create_object(exits.Exit, key="east", aliases=["e"], location=west_room, destination=east_room)

    create_object(exits.Exit, key="west", aliases=["w"], location=east_room, destination=west_room)

    kwargs["caller"].msg("连接： " + west_room.key + " & " + east_room.key)


# 在图例字典中包括您的触发字符和构建函数。
EXAMPLE2_LEGEND = {
    ("♣", "♠"): example2_build_forest,
    ("|"): example2_build_verticle_exit,
    ("-"): example2_build_horizontal_exit,
}
```

```{toctree}
:hidden:
Contrib-Mapbuilder-Tutorial
```
