# 从ASCII地图创建房间

本教程描述了如何基于预先绘制的地图创建一个游戏内的地图显示。它与[地图构建器贡献](./Contrib-Mapbuilder.md)相配合。并且它还详细说明了如何使用[批处理代码处理器](../Components/Batch-Code-Processor.md)进行高级构建。

Evennia不要求其房间以“逻辑”的方式定位。你的出口可以命名为任何东西。你可以制作一个“西边”的出口，通向一个描述为位于遥远北部的房间。你可以让房间相互嵌套，出口回到同一个房间，或者描述在现实世界中不可能的空间几何体。

尽管如此，大多数游戏*确实*会以逻辑的方式组织他们的房间，至少是为了保持玩家的理智。当他们这样做时，游戏就变得可以映射。本教程将提供一个简单但灵活的游戏内地图系统的示例，以进一步帮助玩家导航。我们将：

为了简化开发和错误检查，我们将把工作分解为小步骤，每个步骤都建立在之前的基础上。为此，我们将广泛使用[批处理代码处理器](Batch-Code-Processor)，因此您可能希望提前了解一下。

1. **规划地图** - 在这里，我们将设计一个小示例地图以供后面的教程使用。
2. **制作地图对象** - 这将展示如何制作一个角色可以拾取并查看的静态游戏内“地图”对象。
3. **构建地图区域** - 在这里，我们将按照之前设计的地图实际创建小的示例区域。
4. **地图代码** - 这将把地图链接到位置，使我们的输出看起来像这样：

    ```
    crossroads(#3)
    ↑╚∞╝↑
    ≈↑│↑∩  两条道路的交汇处。北侧高耸着一座宏伟的城堡。
    O─O─O  南侧可以看到篝火的微光。东边是
    ≈↑│↑∩  广阔的山脉，西边可以听到海浪的声音。
    ↑▲O▲↑
    
    出口: north(#8), east(#9), south(#10), west(#11)
    ```

我们将假设您的游戏文件夹命名为 `mygame`，并且您没有修改默认命令。我们也不会在地图中使用[颜色](../Concepts/Colors.md)，因为它们在文档wiki中无法显示。

## 规划地图

让我们开始有趣的部分！MUD中的地图有许多不同的[形状和大小](http://journal.imaginary-realities.com/volume-05/issue-01/modern-interface-modern-mud/index.html)。有些地图只显示通过线连接的盒子，有的则有复杂的外部图形。

我们的地图将是游戏内的文本，但这并不意味着我们限制使用普通字母！如果你曾经在Microsoft Word中选择过[Windings字体](https://en.wikipedia.org/wiki/Wingdings)，你会发现有许多其他字符可供使用。当使用Evennia创建游戏时，你可以访问[UTF-8字符编码](https://en.wikipedia.org/wiki/UTF-8)，这让你可以使用[成千上万的字母、数字和几何形状](https://mcdlr.com/utf-8/#1)。

在这个练习中，我们从[Dwarf Fortress](https://dwarffortresswiki.org/index.php/Character_table)的特殊字符集中复制并粘贴，创造出一个希望可以令人愉悦且易于理解的景观：

```
≈≈↑↑↑↑↑∩∩
≈≈↑╔═╗↑∩∩   角色可以访问的地方用“O”表示。
≈≈↑║O║↑∩∩   在顶部是角色可以访问的城堡。
≈≈↑╚∞╝↑∩∩   右边是一个小屋，左边是沙滩。
≈≈≈↑│↑∩∩∩   最下面是一个有帐篷的营地。
≈≈O─O─O⌂∩   中间是起始位置，一个十字路口
≈≈≈↑│↑∩∩∩   连接着四个其他区域。
≈≈↑▲O▲↑∩∩   
≈≈↑↑▲↑↑∩∩
≈≈↑↑↑↑↑∩∩
```

在创建游戏地图时，有许多考虑因素，具体取决于您打算实施的玩法风格和要求。这里我们将展示一个5x5的字符区域地图，这意味着必须考虑到每个可访问位置周围的2个字符。此阶段的良好规划可以解决许多潜在问题。

## 创建地图对象

在本节中，我们将尝试创建一个实际的地图对象，角色可以拾取并查看它。

Evennia提供了一系列默认命令，用于[创建游戏内的对象和房间](../Howtos/Beginner-Tutorial/Part1/Beginner-Tutorial-Building-Quickstart.md)。虽然非常方便，但这些命令是为了做非常具体、受限的事情，因此不会提供太多的灵活性进行实验（一个高级例外是[FuncParser](../Components/FuncParser.md)）。此外，在游戏客户端中反复输入冗长的描述和属性可能会变得乏味，尤其是在测试时，您可能会想不断删除和重新创建事物。

为了克服这一点，Evennia提供了[批处理处理器](../Components/Batch-Processors.md)，作为在游戏外创建的输入文件来使用。在本教程中，我们将使用可用的两种批处理处理器中的更强大的一种，即通过`@batchcode`命令调用的[批处理代码处理器](../Components/Batch-Code-Processor.md)。这是一个非常强大的工具。它允许您创建Python文件作为整个游戏世界的蓝图。这些文件可以直接使用Evennia的Python API。Batchcode允许在您喜欢的文本编辑器中轻松编辑和创建，避免了在游戏内逐行手动构建世界的麻烦。

> 重要警告：`@batchcode`的功能仅与`@py`命令媲美。Batchcode是如此强大，以至于应该仅限于[超级用户](../Concepts/Building-Permissions.md)。在让其他人（例如`开发者`级别的工作人员）在其自己的服务器上运行`@batchcode`之前，请仔细考虑 - 确保您可以接受他们运行*任意Python代码*。

虽然这是一个简单的示例，但地图对象是一个很好的方式来尝试`@batchcode`。转到`mygame/world`并在那创建一个名为`batchcode_map.py`的新文件：

```Python
# mygame/world/batchcode_map.py

from evennia import create_object
from evennia import DefaultObject

# 我们使用 create_object 函数将一个名为“地图”的 DefaultObject 实例化
# 创建在你所站立的位置。

map = create_object(DefaultObject, key="Map", location=caller.location)

# 然后直接访问其描述并设置为我们的地图。

map.db.desc = """
≈≈↑↑↑↑↑∩∩
≈≈↑╔═╗↑∩∩
≈≈↑║O║↑∩∩
≈≈↑╚∞╝↑∩∩
≈≈≈↑│↑∩∩∩
≈≈O─O─O⌂∩
≈≈≈↑│↑∩∩∩
≈≈↑▲O▲↑∩∩
≈≈↑↑▲↑↑∩∩
≈≈↑↑↑↑↑∩∩
"""

# 这个消息让我们知道我们的地图已成功创建。
caller.msg("一张地图凭空而现，落在地上。")
```

以超级用户身份登录到您的游戏项目，并运行命令 

```
@batchcode batchcode_map
```

这将加载您的 `batchcode_map.py` 文件并执行代码（Evennia会自动查找您的 `world/` 文件夹，因此您无需指定）。

一个新的地图对象应该出现在地面上。您可以通过`look map`查看地图。让我们用`get map`命令把它拿走，以防迷路！

## 构建地图区域

我们刚刚使用批处理代码创建了一个对我们的冒险有用的对象。但是地图上的位置实际上还不存在——我们所有的地图都没有地方可去！让我们利用批处理代码根据我们的地图构建一个游戏区域。我们有五个区域的轮廓：一个城堡，一个小屋，一个营地，一个海滨沙滩和连接它们的十字路口。为此，在`mygame/world`中为此创建一个新的批处理代码文件，将其命名为`batchcode_world.py`。

```Python
# mygame/world/batchcode_world.py

from evennia import create_object, search_object
from typeclasses import rooms, exits

# 我们首先创建我们的房间，以便稍后进行详细说明。

centre = create_object(rooms.Room, key="crossroads")
north = create_object(rooms.Room, key="castle")
east = create_object(rooms.Room, key="cottage")
south = create_object(rooms.Room, key="camp")
west = create_object(rooms.Room, key="coast")

# 这是我们设置十字路口的地方。
# 房间描述是我们通过“查看”命令看到的内容。

centre.db.desc = """
两条道路的交汇处。一盏灯笼暗淡地照亮了孤独的十字路口。
北面高耸着一座宏伟的城堡。南边可以看到篝火的微光。
东边是一片山脉，西边则是开阔大海的低沉咆哮声。
"""

# 在这里我们为中心"十字路口"位置创建出口，前往
# 北、东、南和西的目的地。我们可以通过输入出口的键，例如“北”或别名，例如“n”来使用出口。

centre_north = create_object(exits.Exit, key="north", 
                            aliases=["n"], location=centre, destination=north)
centre_east = create_object(exits.Exit, key="east", 
                            aliases=["e"], location=centre, destination=east)
centre_south = create_object(exits.Exit, key="south", 
                            aliases=["s"], location=centre, destination=south)
centre_west = create_object(exits.Exit, key="west", 
                            aliases=["w"], location=centre, destination=west)

# 现在我们对将要实现的其他房间重复此操作。
# 在这里我们设置北侧的城堡。

north.db.desc = "你被令人印象深刻的城堡包围。 " \
                "也许这些塔楼中有一位公主。"
north_south = create_object(exits.Exit, key="south", 
                            aliases=["s"], location=north, destination=centre)

# 这是我们设置东边小屋的地方。

east.db.desc = "一间舒适的小屋，位于东面绵延的山脉之间，" \
               "远望无际。"
east_west = create_object(exits.Exit, key="west", 
                            aliases=["w"], location=east, destination=centre)

# 这是我们设置南边营地的地方。

south.db.desc = "环绕着空地的是一些" \
                "部落帐篷，中央有一堆熊熊燃烧的篝火。"
south_north = create_object(exits.Exit, key="north", 
                            aliases=["n"], location=south, destination=centre)

# 这是我们设置西侧海岸的地方。

west.db.desc = "黑暗的森林停滞在沙滩边。 " \
               "冲击的海浪声让灵魂宁静。"
west_east = create_object(exits.Exit, key="east", 
                            aliases=["e"], location=west, destination=centre)

# 最后，让我们从默认的Limbo房间创建一个通往我们世界的入口。

limbo = search_object('Limbo')[0]
limbo_exit = create_object(exits.Exit, key="enter world", 
                            aliases=["enter"], location=limbo, destination=centre)
```

使用`@batchcode batchcode_world`应用这段新批处理代码。如果代码没有错误，我们现在有一个可供探索的小世界。记住，如果迷路，可以查看我们创建的地图！

## 游戏内小地图

现在我们有了一个景观以及匹配的地图，但我们真正想要的是在进入房间或使用 `look` 命令时显示的小地图。

我们*可以*手动将地图的一部分输入到每个房间的描述中，就像我们之前的地图对象描述那样。但是一些MUD拥有数万间房间！此外，如果我们更改地图，可能需要手动更改许多房间描述以匹配更改。因此，我们将制作一个中央模块来保存我们的地图。房间在创建时将引用此中央位置，地图更改将在下次运行批处理代码时生效。

为了制作小地图，我们需要能够将完整地图切分为部分。为此，我们需要将其放入一个便于处理的格式。幸运的是，Python允许我们将字符串视为字符列表，从而轻松提取所需的字符。

在 `mygame/world/map_module.py` 文件中：

```Python
# 我们将在这里将地图放入一个字符串中。
world_map = """\
≈≈↑↑↑↑↑∩∩
≈≈↑╔═╗↑∩∩
≈≈↑║O║↑∩∩
≈≈↑╚∞╝↑∩∩
≈≈≈↑│↑∩∩∩
≈≈O─O─O⌂∩
≈≈≈↑│↑∩∩∩
≈≈↑▲O▲↑∩∩
≈≈↑↑▲↑↑∩∩
≈≈↑↑↑↑↑∩∩
"""

# 此代码将我们的地图字符串转换为行列表。由于Python
# 允许我们将字符串视为字符列表，因此我们可以通过
# world_map[5][5] 来访问这些字符，其中world_map[row][column]表示行和列。
world_map = world_map.split('\n')

def return_map():
    """
    此函数返回整个地图
    """
    map = ""
    
    #对于地图中的每一行，将其添加到地图中
    for valuey in world_map:
        map += valuey
        map += "\n"
    
    return map

def return_minimap(x, y, radius=2):
    """
    此函数仅返回地图的一部分，
    返回以(x,y)为中心的半径为2的所有字符。
    """
    map = ""
    
    # 对于我们需要的每一行，添加所需的字符。
    for valuey in world_map[y-radius:y+radius+1]:
        for valuex in valuey[x-radius:x+radius+1]:
            map += valuex
        map += "\n"
    
    return map
```

设置好我们的地图模块后，让我们用对地图模块的引用替换`mygame/world/batchcode_map.py`中的硬编码地图。确保导入我们的地图模块！

```python
# mygame/world/batchcode_map.py

from evennia import create_object
from evennia import DefaultObject
from world import map_module

map = create_object(DefaultObject, key="Map", location=caller.location)

map.db.desc = map_module.return_map()

caller.msg("一张地图凭空而现，落在地上。")
```

以超级用户身份登录Evennia并运行此批处理代码。如果一切顺利，我们的新地图应该与旧地图完全相同——您可以使用`@delete`命令删除旧的地图（用数字指定要删除的地图）。

接下来，让我们关注游戏的房间。我们将使用上面创建的 `return_minimap` 方法在房间描述中包含一个小地图。这有点复杂。

单独使用时，我们只能选择将地图放在描述*上方*，使用 `room.db.desc = map_string + description_string`，或将其放在*下方*，通过反转二者的顺序。两个选项都不是特别令人满意——我们希望将地图和文本放在一起！为此解决方案，我们将探索与Evennia一同提供的工具。在 `evennia\evennia\utils` 中有一个模块叫做[EvTable](https://github.com/evennia/evennia/blob/master/evennia/utils/evtable.py)。这是一个高级ASCII表创建器，可以在游戏中使用。我们将通过创建一个包含1行和两列（一个用于我们的地图，一个用于我们的文本）的基本表，同时隐藏边框来使用它。打开批处理文件，再次更新：

```python
# mygame\world\batchcode_world.py

# 添加到导入中
from evennia.utils import evtable
from world import map_module

# [...]

# 用以下代码替换描述。

# 十字路口。
# 我们传递想在表中显示的内容，EvTable会处理其余部分。
# 传递两个参数将创建两列，但我们可以添加更多列。
# 我们还指定没有边框。
centre.db.desc = evtable.EvTable(map_module.return_minimap(4, 5), 
                 "两条道路的交汇处。一盏灯笼暗淡地照亮了孤独的十字路口。"
                 "北面高耸着一座宏伟的城堡。南边可以看到篝火的微光。"
                 "东边是一片山脉，西边则是开阔大海的低沉咆哮声。", 
                 border=None)
# EvTable 允许格式化单独的列和单元格。我们在这里使用它
# 设置我们描述的最大宽度，同时让地图填充需要的空间。 
centre.db.desc.reformat_column(1, width=70)

# [...]

# 北方城堡。
north.db.desc = evtable.EvTable(map_module.return_minimap(4, 2), 
                "你被令人印象深刻的城堡包围。这里的塔楼中也许有公主。", 
                border=None)
north.db.desc.reformat_column(1, width=70)   

# [...]

# 东方小屋。
east.db.desc = evtable.EvTable(map_module.return_minimap(6, 5), 
               "一间舒适的小屋，位于东面绵延的山脉间，" 
               "望无际。", 
               border=None)
east.db.desc.reformat_column(1, width=70)

# [...]

# 南方营地。
south.db.desc = evtable.EvTable(map_module.return_minimap(4, 7), 
                "环绕着空地的是一些部落帐篷，" 
                "中央有一堆熊熊燃烧的篝火。", 
                border=None)
south.db.desc.reformat_column(1, width=70)

# [...]

# 西方海岸。
west.db.desc = evtable.EvTable(map_module.return_minimap(2, 5), 
               "黑暗的森林停滞在沙滩边，" 
               "冲击的海浪声让灵魂宁静。", 
               border=None)
west.db.desc.reformat_column(1, width=70)
```

在运行我们新的批处理代码之前，如果您和我一样，您可能会有将近100个地图和3-4个不同版本的房间扩展自limbo。让我们清空所有内容，从头开始。在命令提示符中运行 `evennia flush` 可以清除数据库并重新开始。它不会重置DBREF值，因此如果您处在#100处，它将从该值开始。同时，您可以导航到`mygame/server`并删除`evennia.db3`文件。之后在命令提示符中使用 `evennia migrate` 创建一个全新的数据库。

登录到Evennia并运行 `@batchcode batchcode_world`，您将拥有一个可以探索的小世界。

## 结论

现在您应该拥有一个已绘制的小世界，并对批处理代码、EvTable以及如何轻松向Evennia添加新游戏定义功能有所了解。

您可以轻松地从本教程构建，通过扩展地图并创建更多房间进行探索。为什么不通过尝试其他教程来为您的游戏添加更多功能呢：[为您的世界添加天气](Weather-Tutorial)、[让您的世界充满NPC](../Howtos/Tutorial-NPC-Reacting.md)或[实现战斗系统](../Howtos/Turn-based-Combat-System.md)。
