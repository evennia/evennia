# XYZ网格

贡献者：Griatch 2021

将Evennia的游戏世界放置在一个xy（z代表不同地图）坐标网格上。通过绘制和解析2D ASCII 地图，包括传送、地图转换和特殊标记，外部创建和维护网格，以帮助寻路。支持每个地图的非常快速的最短路由寻路。还包括一个快速查看功能，可以查看离当前地点仅限数量的步骤（在游戏中显示网格作为更新地图时非常有用）。

网格管理是在游戏外使用新的evennia-launcher选项完成的。

## 示例

<script id="asciicast-Zz36JuVAiPF0fSUR09Ii7lcxc" src="https://asciinema.org/a/Zz36JuVAiPF0fSUR09Ii7lcxc.js" async></script>

```
#-#-#-#   #
|  /      d
#-#       |   #
   \      u   |\
o---#-----#---+-#-#
|         ^   |/
|         |   #
v         |    \
#-#-#-#-#-# #---#
    |x|x|     /
    #-#-#    #-
```

```
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                                     #---#
                                    /
                                   @-
-~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
地下入口
向东，一个狭窄的开口通向黑暗。
出口：东北和东边

```

## 安装

1. XYZGrid需要`scipy`库。最简单的方法是通过以下方式获取Evennia的“额外”依赖项：

       pip install evennia[extra]

   如果您使用`git`安装，您也可以

       (cd到evennia/文件夹)
       pip install --upgrade -e .[extra]

   这将安装Evennia的所有可选要求。
2. 在`mygame/commands.default_cmds.py`中导入并[添加] `evennia.contrib.grid.xyzgrid.commands.XYZGridCmdSet`到`CharacterCmdset`命令集中。重新加载服务器。这使得`map`、`goto/path`和修改后的`teleport`与`open`命令在游戏中可用。

[add]: ../Components/Command-Sets

3. 编辑`mygame/server/conf/settings.py`并添加

       EXTRA_LAUNCHER_COMMANDS['xyzgrid'] = 'evennia.contrib.grid.xyzgrid.launchcmd.xyzcommand'
       PROTOTYPE_MODULES += ['evennia.contrib.grid.xyzgrid.prototypes']

   这将使您能够在命令行中输入 `evennia xyzgrid <option>`。它还会使`xyz_room`和`xyz_exit`原型可以用于生成网格时作为原型父级。

4. 运行`evennia xyzgrid help`以获取可用选项。

5. （可选）：默认情况下，xyzgrid只会生成基于模块的[原型]。这是一个优化，通常是合理的，因为网格完全在游戏外定义。如果您希望也使用游戏中（db-）创建的原型，请在设置中添加`XYZGRID_USE_DB_PROTOTYPES = True`。

[prototypes]: ../Components/Prototypes

## 概述

该网格组件由多个部分组成。

1. `XYMap` - 此类解析带有特殊_Map字符串_和_Map图例_的模块为一个Python对象。它具有用于寻路和视觉范围处理的助手。
2. `XYZGrid` - 这是一个单例[脚本](../Components/Scripts.md)，存储游戏中的所有`XYMaps`。它是管理游戏“网格”的中心点。
3. `XYZRoom`和`XYZExit`是自定义类型类，使用[标签](../Components/Tags.md)来知道它们位于哪个X，Y，Z坐标。`XYZGrid` 在被用于生成这些数据库实体之前是抽象的，这些实体在游戏中是可以实际交互的。`XYZRoom`类型类使用其`return_appearance`钩子来显示游戏中的地图。
4. 为与XYZ感知位置交互添加了自定义_命令_。
5. 使用新的自定义_启动命令_ `evennia xyzgrid <options>` 可以从终端管理网格（不需要游戏登录）。

我们将通过一个例子来开始探索这些组件。

## 第一个例子用法

安装后，请从您的命令行中执行以下操作（即`evennia`命令可用的地方）：

    $ evennia xyzgrid init

使用`evennia xyzgrid help`查看所有选项）
这将创建一个新的`XYZGrid` [脚本](../Components/Scripts.md)，如果尚不存在的话。`evennia xyzgrid`是仅为此贡献添加的自定义启动选项。

xyzgrid贡献提供了一个完整的网格示例。让我们添加它：

    $ evennia xyzgrid add evennia.contrib.grid.xyzgrid.example

现在您可以列出网格上的地图：

    $ evennia xyzgrid list

您会发现新增了两张新地图。您可以使用`show`子命令找到有关每个地图的更多额外信息：

    $ evennia xyzgrid show "the large tree"
    $ evennia xyzgrid show "the small cave"

如果您想查看网格的代码，打开 [evennia/contrib/grid/xyzgrid/example.py](evennia.contrib.grid.xyzgrid.example)。
（稍后我们会在更详细的部分解释细节）。

到目前为止，网格是“抽象”的，并且没有实际的游戏内存在。让我们从中生成实际的房间/出口。这将需要一些时间。

    $ evennia xyzgrid spawn

这将使用每个地图的_map图例_存储的原型，使用该原型构建XYZ感知房间。它还会解析所有链接，以便在位置之间生成适当的出口。如果您修改网格的布局/原型，则应重新运行此命令。多次运行是安全的。

    $ evennia reload

（或如果服务器没有运行则`evennia start`）。在每次生成操作后，这一点非常重要，因为`evennia xyzgrid`在常规evennia进程之外运行。重新加载确保所有缓存都已刷新。

现在您可以登录服务器。一些新命令应该可供您使用。

    teleport (3,0,the large tree)

`teleport`命令现在接受一个可选的（X，Y，Z）坐标。传送到房间名称或`#dbref`仍然以相同的方式工作。这将使您传送到网格上。您应该会看到地图显示。尝试四处走动。

    map

这个新的仅限构建者的命令显示当前地图的完整形式（还显示通常对用户不可见的“隐形”标记）。

    teleport (3, 0)

一旦您位于网格房间中，您可以在不指定Z坐标/地图名称的情况下传送到同一地图上的另一个网格房间。

您可以使用`open`使出口返回到“非网格”，但请记住，您不能以基本方向使用此方法 - 如果这样做，`evennia xyzgrid spawn`在下一次运行时可能会删除它。

    open To limbo;limbo = #2
    limbo

您已经回到了Limbo（它不知晓任何XYZ坐标）。但是，您可以将一个永久链接返回到网格地图：

    open To grid;grid = (3,0,the large tree)
    grid

这就是将非网格和网格位置连接在一起的方式。您可以通过这种方式将房屋“嵌入”到网格中。

`(3,0,the large tree)`是“地下入口”。如果您向东走，您将进入“the small cave”地图。这是一个有限可见的小地下城。再回到外面（回到“the large tree”地图）。

    path view

这将找出到“一个令人惊叹的视野”房间的最短路径，位于大树的高处。如果您的客户端中有颜色，您应该会看到路径的起点以黄色可视化。

    goto view

这将开始自动行走您到视野。在此过程中，您将向上移动到树上，并穿越地图内的传送门。单独使用`goto`以中止自动行走。

当您完成探索后，请再次打开终端（在游戏外），并删除所有内容：

    $ evennia xyzgrid delete

您将被要求确认删除网格和卸载XYZGrid脚本。然后重新加载服务器。如果您在已删除的地图上，您将被移回您的主位置。

## 定义XYMap

为了将模块传递给`evennia xyzgrid add <module>`，模块必须包含以下变量之一：

- `XYMAP_DATA` - 包含完整定义XYMap的字典
- `XYMAP_DATA_LIST` - `XYMAP_DATA`字典的列表。如果存在，它将优先。这允许在一个模块中存储多个地图。

`XYMAP_DATA`字典具有以下格式：

```
XYMAP_DATA = {
    "zcoord": <str>,
    "map": <str>,
    "legend": <dict, optional>,
    "prototypes": <dict, optional>,
    "options": <dict, optional>
}
```

- `"zcoord"`（字符串）：地图的Z坐标/地图名称。
- `"map"`（字符串）：描述地图拓扑的_Map字符串_。
- `"legend"`（字典，可选）：将地图上的每个符号映射到Python代码。可以省略此字典或仅部分填充 - 没有指定的任何符号将使用贡献的默认图例。
- `"prototypes"`（字典，可选）：这是一个将地图坐标映射到自定义原型覆盖的字典。用于将地图生成实际的房间/出口时。
- `"options"`（字典，可选）：这些将传递到房间的`return_appearance`钩子，并允许自定义地图的显示方式、寻路方式等。

以下是整个设置的最小示例：

```
# 在，比如说，一个模块gamedir/world/mymap.py

MAPSTR = r"""

+ 0 1 2

2 #-#-#
     /
1 #-#
  |  \
0 #---#

+ 0 1 2

# 仅使用默认值
LEGEND = {}

# 仅调整一个房间。`xyz_room/exit`父级可在安装期间通过将xyzgrid原型添加到设置中获得。 
# ‘*’是通配符，并允许在此地图上提供默认值。
PROTOTYPES = {
    (0, 0): {
        "prototype_parent": "xyz_room",
        "key": "一个美好的空地",
        "desc": "阳光透过树枝洒落在地上。",
    },
    (0, 0, 'e'): {
        "prototype_parent": "xyz_exit",
        "desc": "穿过树丛的小径",
    },
    ('*', '*'): {
        "prototype_parent": "xyz_room",
        "key": "在一片阳光明媚的森林中",
        "desc": "周围都是绿色。",
    },
    ('*', '*', '*'): {
        "prototype_parent": "xyz_exit",
        "desc": "小径继续深入森林。",
    },
}

# 为这个地图收集所有信息
XYMAP_DATA = {
    "zcoord": "mymap",  # 重要！
    "map": MAPSTR,
    "legend": LEGEND,
    "prototypes": PROTOTYPES,
    "options": {}
}

# 如果模块中只有一个地图，这可以跳过
XYMAP_DATA_LIST = [
    XYMAP_DATA
]
```

上面的地图将通过以下方式添加到网格中：

    $ evennia xyzgrid add world.mymap

在以下部分中，我们将逐一讨论每个组件。

### Z坐标

网格上的每个XYMap都有一个Z坐标，通常可以被视为地图的名称。Z坐标可以是字符串或整数，必须在整个网格中唯一。它作为键“zcoord”添加到`XYMAP_DATA`中。

大多数用户只想将每个地图视为一个位置，并将“Z坐标”命名为`进斗室`、`冰女皇的宫殿`或`黑港`。但是，您也可以将其命名为 -1、0、1、2、3，如果您愿意。

> 请注意，Z坐标是*不区分大小写* 的搜索

寻路仅在每个XYMap内发生（上下通常通过横向移动到XY平面的新区域“伪造”）。

#### 一个真实的3D地图

即使对于最狂热的科幻太空游戏，也建议坚持2D移动。让玩家可视化3D体积已经足够困难了。在文本中，更加困难。

不过，如果您想设置真正的X、Y、Z 3D坐标系统（您可以从每个点向上/向下移动），您也可以做到这一点。

此贡献提供了一个示例命令`commands.CmdFlyAndDive`，为玩家提供了使用`fly`和`dive`直接在Z坐标之间上下移动的能力。只需将其（或其cmdset `commands.XYZGridFlyDiveCmdSet`）添加到您的角色命令集中，然后重新加载即可试用。

对于飞行/潜水工作，您需要将网格构建为XY网格地图的“堆栈”，并以其Z坐标作为整数命名。飞行/潜水操作仅在上下方确实存在匹配房间时有效。

> 请注意，由于寻路仅在每个XYMap内有效，玩家将无法将飞行/潜水纳入他们的自动行走 - 这始终是手动操作。

作为示例，假设坐标 `(1, 1, -3)` 是通往地面的深井底部（在0级）

```
LEVEL_MINUS_3 = r"""
+ 0 1

1   #
    |
0 #-#

+ 0 1
"""

LEVEL_MINUS_2 = r"""
+ 0 1

1   #

0

+ 0 1
"""

LEVEL_MINUS_1 = r"""
+ 0 1

1   #

0

+ 0 1
"""

LEVEL_0 = r"""
+ 0 1

1 #-#
  |x|
0 #-#

+ 0 1
"""

XYMAP_DATA_LIST = [
    {"zcoord": -3, "map": LEVEL_MINUS_3},
    {"zcoord": -2, "map": LEVEL_MINUS_2},
    {"zcoord": -1, "map": LEVEL_MINUS_1},
    {"zcoord": 0, "map": LEVEL_0},
]
```

在此示例中，如果我们到达井底 `(1, 1, -3)` 我们将`fly`直接向上三层，直至到达 `(1, 1, 0)`，在某种开放场地的角落。

我们可以从 `(1, 1, 0)` 潜水下去。在默认实现中，您必须潜水三次才能到达底部。如果您愿意，您可以调整命令，使其自动降落到底部并造成伤害等。

我们无法从任何其他XY位置上下飞行/潜水，因为在相邻的Z坐标没有开放的房间。

### 地图字符串

创建新地图从一个_Map字符串_ 开始。这允许您“绘制”地图，描述房间在X、Y坐标系统中的位置。
它被添加到 `XYMAP_DATA` 中，键为'地图'。

```
MAPSTR = r"""

+ 0 1 2

2 #-#-#
     /
1 #-#
  |  \
0 #---#

+ 0 1 2

"""

```

在坐标轴上，只有两个`+`是重要的 - 数字是_可选_的，因此这等价于：

```
MAPSTR = r"""

+

  #-#-#
     /
  #-#
  | \
  #---#

+

"""
```
> 即使是可选的，强烈建议您在坐标轴中添加数字 - 如果仅为了您自己的 sanity。

坐标区域从强制的`+`标志（标记地图区域的边角）_右侧两个空格_和_上方/下方两个空格_开始。原点`(0,0)`位于左下角（因此X坐标向右增加，Y坐标向上增加）。地图的高度/宽度没有限制，但将大型世界拆分为多个地图可以使管理更容易。

网格中位置很重要。完整的坐标放置在所有轴上的每个_第二个_空间之间。在这些“完整”坐标之间是`.5`坐标。请注意，在游戏中没有_任何_ `.5`坐标；它们仅用于地图字符串中，以留出空间以描述房间/节点之间的链接方式。

    + 0 1 2 3 4 5

    4           E
       B
    3

    2         D

    1    C

    0 A

    + 0 1 2 3 4 5

- `A`位于原点 `(0, 0)`（一个“完整”的坐标）
- `B`位于 `(0.5, 3.5)`
- `C`位于 `(1.5, 1)`
- `D`位于 `(4, 2)`（一个“完整”的坐标）。
- `E`是地图的右上角，位于 `(5, 4)`（一个“完整”的坐标）。

地图字符串由两类主要实体组成 - _节点_和_链接_。
- _节点_ 通常代表游戏中的一个_房间_（但不总是）。节点必须_总是_放置在一个“完整”的坐标上。
- _链接_ 描述两个节点之间的连接。在游戏中，链接通常代表_出口_。链接可以放置在坐标空间的任何位置（在完整坐标和0.5坐标之间）。多个链接通常是_链式_连接，但链必须始终在两侧的节点结束。

> 尽管链接链可以由多个步骤组成，例如`#-----#`，在游戏中它仍将只表示一个“步骤”（例如，您只需一次向“东”移动即可从最左侧移动到最右侧的节点/房间）。

### 地图图例

可能有许多不同类型的 _节点_和 _链接_。而地图字符串描述它们的位置，_地图图例_将地图上的每个符号连接到Python代码。

```

LEGEND = {
    '#': xymap_legend.MapNode,
    '-': xymap_legende.EWMapLink
}

# 作为'legend'添加到XYMAP_DATA字典中：LEGEND如下

```

图例是可选的，任何未在您的图例中明确给出的符号将回退到其在默认图例中的值[如下所述](#default-legend)。

- [MapNode](evennia.contrib.grid.xyzgrid.xymap_legend.MapNode) 是所有节点的基类。
- [MapLink](evennia.contrib.grid.xyzgrid.xymap_legend.MapLink) 是所有链接的基类。

当解析_地图字符串_时，找到的每个符号都会在图例中查找，并初始化为相应的MapNode/Link实例。

#### 重要的节点/链接属性

如果您想自定义地图，这些是相关的。该贡献已经提供了一整套地图元素，使用这些属性进行了不同方式的描述（在下一节中描述）。

一些有用的属性：[MapNode](evennia.contrib.grid.xyzgrid.xymap_legend.MapNode)类（见类文档以获取钩子方法）：

- `symbol`（字符串） - 从地图中解析为此节点的字符。默认情况下为`'#'`，_必须_是单个字符（除了必须转义使用的`\`）。运行时将根据图例字典中使用的符号替换此值。
- `display_symbol`（字符串或`None`） - 这是用于在游戏中可视化此节点的内容。此符号必须仍仅具有1的视觉大小，但是您可以使用一些花哨的Unicode字符（但要注意不同客户端的编码），或通常在其周围添加颜色标签。此类的`.get_display_symbol`可以自定义以动态生成；默认情况下，它仅返回`.display_symbol`。如果设置为`None`（默认），则使用`symbol`。
- `interrupt_path`（布尔值）：如果设置，则最短路径算法通常会包括此节点，但自动步进器在达到该节点时会停止，即使尚未到达目标。这对于标记沿路径的“兴趣点”或标记您在未指定地图上无法继续的地方很有用（例如守卫或锁门等）。
- `prototype`（字典） - 在游戏网格上重现此地图组件要使用的默认`prototype`字典。如果没有为此坐标单独覆盖，则使用此值。如果没有给出，在此坐标上将不会生成任何内容（“虚拟”节点在多种原因上都有用，主要是地图转换）。

一些有用的属性：[MapLink](evennia.contrib.grid.xyzgrid.xymap_legend.MapLink)类（参考类文档以获取钩子方法）：

- `symbol`（字符串） - 从地图解析为此节点的字符。必须是单个字符，除了`\`。此值在运行时会被图例字典中使用的符号替换。
- `display_symbol`（字符串或 None）  - 这是稍后可视化此节点的内容。此符号必须仍仅具有1的视觉大小，但您可以使用一些花哨的Unicode字符（但要注意不同客户端的编码），或通常在其周围添加颜色标签。要进一步自定义，可以使用`.get_display_symbol`。
- `default_weight`（整数） - 此链接覆盖的每个链接方向都可以有自己的权重（用于寻路）。如果在特定链接方向中未指定权重，则使用此值。此值必须≥1，如果链接应该不太受偏爱的，可以大于1。
- `directions`（字典） - 这指定从哪个链接边缘到哪个其他链接边缘连接；将连接链接的西南边缘与其东边缘写为`{'sw': 'e'}`，表示“从西南连接到东”。这仅接受基于基本方向的运动（而不是上下）。请注意，如果您希望该链接双向连接，则也必须添加反向（东到西南）。
- `weights（字典）`将链接的起始方向映射到权重。因此，对于 `{'sw': 'e'}`链接，权重将作为 `{'sw': 2}`给出。如果未给出，链接将使用 `default_weight`。
- `average_long_link_weights`（布尔值）：这仅适用于节点的*第一个*链接。当追踪到另一个节点的链接时，可能涉及多个链接，每个链接都有一个权重。因此，对于带有默认权重的链接链，`#---#`总重量为3。通过此设置（默认），权重将为（1+1+1）/3 = 1。也就是说，对于均匀加权的链接，链接链的长度并不重要（通常是最有意义的）。
- `direction_aliases`（字典）：在寻路时显示一个方向时，可能希望显示与基于卡迪尔方向的地图上不同的“方向”。例如，'上'可能在地图上可视化为' n'移动，但在此链接上找到的路径应显示为'u'。在这种情况下，别名将是`{'n': 'u'}`。
- `multilink`（布尔值）：如果设置，可以从所有方向接受此链接。它通常会使用自定义的`.get_direction`方法来根据周围的拓扑确定这些方向。此设置在存在多个多链接时是必要的，以避免无限循环。
- `interrupt_path`（布尔值）：如果设置，最短路径解决方案会像往常一样包括此链接，但自动步进器将停止而未实际穿过此链接移动。
- `prototype`（字典） - 在游戏网格上重现此地图组件要使用的默认`prototype`字典。这仅与节点的*第一个*链接相关（链接的后续部分仅用于确定链接的目标）。可以在每个方向上覆盖此值。
- `spawn_aliases`（字典）：对于从此链接生成实际出口时使用的映射 `{direction: (key, alias, alias, ...),}`。如果未给出，将使用一组合理的默认值（`n=(north, n)` 等）。如果您使用任何自定义方向而不是基本方向+上下，则这是必需的。出口的键（对于自动行走有用）通常通过调用`node.get_exit_spawn_name(direction)`获取。

以下是一个例子，改变地图节点的显示为红色（可能是岩浆地图？）：

```
from evennia.contrib.grid.xyzgrid import xymap_legend

class RedMapNode(xymap_legend.MapNode):
    display_symbol = "|r#|n"


LEGEND = {
   '#': RedMapNode
}

```

#### 默认图例

以下是默认地图图例。`symbol`是应放入地图字符串中的内容。它必须始终是单个字符。`display-symbol`是在游戏中向玩家展示地图时实际可视化的内容。这可能有颜色等。所有类均可在`evennia.contrib.grid.xyzgrid.xymap_legend`中找到，类名已纳入以便于了解需要覆盖的内容。

```{eval-rst}
=============  ==============  ====  ===================  =========================================
符号         显示符号      类型  类                  描述
=============  ==============  ====  ===================  =========================================
#              #               节点  `BasicMapNode`       基本节点/房间。
T                              节点  `MapTransitionNode`  连接地图之间的链接的过渡目标
                                                          （见下文）
I (字母I)     #               节点  `InterruptMapNode`   兴趣点，自动步行总是会在此处停止（见下文）。
\|             \|              链接  `NSMapLink`          南北双向
\-             \-              链接  `EWMapLink`          东西双向
/              /               链接  `NESWMapLink`        东北-西南双向
\\             \\              链接  `SENWMapLink`        西北双向
u              u               链接  `UpMapLink`          向上，单向或双向（见下文）
d              d               链接  `DownMapLink`        向下，单向或双向（见下文）
x              x               链接  `CrossMapLink`       SW-NE和SE-NW双向
\+             \+              链接  `PlusMapLink`        交叉南北和东西双向
v              v               链接  `NSOneWayMapLink`    南北单向
^              ^               链接  `SNOneWayMapLink`    南北单向
<              <               链接  `EWOneWayMapLink`    东西单向
>              >               链接  `WEOneWayMapLink`    西东单向
o              o               链接  `RouterMapLink`      路由链接，用于创建链接'膝'和
                                                          非正交交叉（见下文）
b              (多变)        链接  `BlockedMapLink`     阻止寻路者使用此链接。
                                                          会表现为逻辑上放置的普通链接（见下文）。
i              (多变)        链接  `InterruptMapLink`   中断链接；自动步骤将永远不会穿过此链接（
                                                          必须手动移动，见下文)
t                              链接  `TeleporterMapLink`  跨地图的传送门；将传送到
                                                          相同符号的传送门。
                                                          （见下文）
=============  ==============  ====  ===================  =========================================

```

#### 地图节点

基本地图节点（`#`）通常表示游戏世界中的一个“房间”。链接可以从8个基本方向中的任何一个连接到节点，但由于节点_只能_存在于完整坐标上，因此它们永远不能直接彼此相邻。

```
    \|/
    -#-
    /|\

    ##     无效！

所有链接或链接链_必须_在两侧以节点结束。



    #-#-----#
    
    #-#-----  无效！

#### 单向链接

`>`,`<`, `v`, `^`用于表示单向链接。这些指示符应在链接链的_第一个_或_最后一个_位置（将它们视为箭头）：

    #----->#
    #>-----#

这两个是等效的，但第一个显然更易于阅读。由于在最右侧节点上，解析器立即看到该方向的链接是不可通行的，这样也可以加快解析速度。

> 请注意不存在` \ `和`/`方向的单向等效物。这并不是因为无法做到，而是因为没有明显的ASCII字符来表示对角箭头。如果您需要它们，很容易为现有的单向地图图例创建子类，以添加斜向移动的单向版本。

#### 上下链接

像`u`和`d`这样的链接没有明确指出它们连接的方向（与例如 `|` 和 `-`不同）。

因此，放置它们（以及许多类似类型的地图元素）需要确保视觉上明确。例如，多个链接不能连接到上下链接（因为不清楚究竟是哪一个链接到哪一个），并且如果相邻于一个节点，链接将优先连接到节点。以下是一些示例：

        #
        u    - 上下两方向的移动将使您到达另一个节点（双向）
        #

        #
        |    - 从下方节点向上是一条单向路径，向南返回
        u
        #

        #
        ^    - 真实的单向上移动，结合单向“ n”链接
        u
        #

        #
        d    - 单向上，单向下（标准的上下行为）
        u
        #

        #u#
        u    - 无效，因为左上节点有两个“上”方向可去
        #

        #     |
        u# 或 u-   - 无效，因为上面u的方向不明确
        #     |

#### 中断节点

中断节点（`I`, `InterruptMapNode`）是像任何其他节点一样的节点，只是它被视为“兴趣点”，并且`goto`命令的自动步行将始终在该位置停止。

```
    #-#-I-#-#
```

因此，从左到右自动行走时，自动步行将正确绘制到结束房间的路径，但将始终在`I`节点停止。如果用户_从_`I`房间开始，他们将不受打扰地远离那里（因此您可以手动再次运行`goto`以恢复自动步行）。

此房间的使用是预计未包括在地图中的阻塞点。例如，可能在此房间有一名守卫，除非您出示正确的文件，否则他们会逮捕您 - 尝试自动走过他们是很糟糕的！

默认情况下，此节点对玩家看起来就像一个普通的`#`。

#### 中断链接

中断链接（`i`, `InterruptMapLink`）相当于`InterruptMapNode`，但它适用于链接。尽管寻路算法会正确追踪到另一侧的路径，但自动步进器永远不会穿过中断链接 - 您必须“手动”做到这一点。与上下链接类似，InterruptMapLink必须放置在其方向明确的地方（优先连接到附近的节点）。

```
    #-#-#i#-#
```

从左到右进行寻路时，寻路器将找到终点房间，但在自动步行时，它总是会在直接左侧的节点停止在`i`链接处。重新运行`goto`将没有用。

这对于自动处理游戏中不属于地图的阻塞内容非常有用。一个例子是锁门 - 而不是让自动步进器尝试走过门口（失败），它应该停止并让用户手动跨过阈值，才能继续进行。

与中断节点一样，中断链接对用户显示为预期的链接（因此在上面的示例中，它将显示为 `-`）。

#### 阻塞链接

阻塞者（`b`, `BlockedMapLink`）指示寻路者不应使用的路径。尽管在游戏中会将其视为普通出口，但寻路器将将其视为不可通过。

```
    #-#-#b#-#
```

因为寻路器将把 `b`（阻塞）视为没有链接 (技术上它将链接的`weight`设置为一个非常高的数字)，因此自动步进器无法从左到右自动行走。玩家需要自动走到阻止的直接左侧，手动跨过阻止，然后再继续。

这对于实际的阻止（也许房间里充满了瓦砾？）很有用，并且为了避免玩家自动走入隐藏区域或找到迷宫的出口等。只需将迷宫的出口隐藏在一个阻止后，`goto exit`将不起作用（诚然，有人可能想在这种地图上完全关闭寻路）。

#### 路由链接

路由器（`o`, `RouterMapLink`）允许通过创建一个“膝”来以角度连接节点。


    #----o
    |     \
    #-#-#  o
           |
         #-o


在上面，您可以在左上房间和最底部房间之间向东移动。记住，链接的长度没有关系，因此在游戏中这将仅为一步（在两个房间中均为一步出口“东”）。

路由器可以连接多个连接，只要“输入”和“输出”链接之间数量相同。如果有疑问，系统将假设链接将继续指向路由器对面的输出链接。


          /
        -o    - 这没问题，只能有一条路径，西北-东南

         |
        -o-   - 等同于'+'：一条南北和一条东西链接交叉
         |

        \|/
        -o-   - 所有链接直接通过
        /|\

        -o-   - 东西链接直接通过，其他链接朝西南
        /|

        -o    - 无效；无法知道哪个输入链接到哪个输出
        /|


#### 传送链接

传送链接（`TeleportMapLink`）总是成对出现，使用相同地图符号（默认是`'t'`）。当进入一个链接时，移动会继续通过匹配的传送链接出去。组成对的传送链接必须位于同一XYMap上，并且两侧必须连接/链到一个节点（就像所有链接一样）。只能有一个链接（或节点）连接到传送链接。

跨过传送也会正常工作。

    #-t     t-#

从最左侧节点向东移动将使您出现在最右侧节点，反之亦然（将两个`t`视为在同一位置）。

传送动作总是双向的，但您可以使用单向链接来创建单向传送的效果：

    #-t    t>#

在此示例中，您可以跨过传送门向东，但是由于传送链接的隐藏在一条单向出口后，不能向西。

    #-t#     (无效!)

上面的无效，因为只有一个链接/节点可以连接到传送门。

您可以在同一地图上使用多个传送门，方法是在地图图例中为每对分配不同的（未使用）唯一符号：

```python
# 在您的地图定义模块中

from evennia.contrib.grid.xyzgrid import xymap_legend

MAPSTR = r"""

+ 0 1 2 3 4

2 t q #   q
  | v/ \  |
1 #-#-p #-#
  |       |
0 #-t p>#-#

+ 0 1 2 3 4

"""

LEGEND = {
    't': xymap_legend.TeleporterMapLink,
    'p': xymap_legend.TeleporterMapLink,
    'q': xymap_legend.TeleportermapLink,
}


```

#### 地图过渡节点

地图过渡（`MapTransitionNode`）在XYMaps之间进行传送（Z坐标过渡）。例如，从“地下城”地图走到“城堡”地图。与其他节点不同，MapTransitionNode从不生成实际的房间（它没有原型）。它仅保留指向另一个地图上某个位置的XYZ坐标。指向该节点的链接将使用这些坐标制作指向那里的出口。唯一一个链接可以指向此类型的节点。

与`TeleporterMapLink`不同，另一张地图上不需要有匹配的`MapTransitionNode` - 该过渡可以选择将玩家发送到另一张地图上_任何_有效坐标。

每个MapTransitionNode都具有一个属性`target_map_xyz`，该属性保存向这个节点移动时玩家应该到达的XYZ坐标。每次过渡必须在子类中自定义。

如果有多个过渡，则应添加不同地图图例符号的分离过渡类：

```python
# 在您的地图定义模块中（假设这就是mapB）

from evennia.contrib.grid.xyzgrid import xymap_legend

MAPSTR = r"""

+ 0 1 2

2   #-C
    |
1 #-#-#
     \
0 A-#-#

+ 0 1 2


"""

class TransitionToMapA(xymap_legend.MapTransitionNode):
    """转换到MapA"""
    target_map_xyz = (1, 4, "mapA")

class TransitionToMapC(xymap_legend.MapTransitionNode):
    """转换到MapB"""
    target_map_xyz = (12, 14, "mapC")

LEGEND = {
    'A': TransitionToMapA
    'C': TransitionToMapC

}

XYMAP_DATA = {
    # ...
    "map": MAPSTR,
    "legend": LEGEND
    # ...
}

```

向西移动`(1,0)`将使您到达MapA的`(1,4)`，向东移动`(1,2)`将使您到达MapC的`(12,14)`（假设这些地图存在）。

地图过渡总是单向的，并且可以指向另一张地图的_任何_现有节点坐标：

    map1     map2

    #-T      #-#---#-#-#-#

一名玩家向东进入`T`，可能会想在map2的第四个`#`处结束（即使这样做在视觉上不够合理）。
将无法从map1返回。

要创建双向过渡的效果，可以在另一张地图上设置一个镜像过渡节点：

    citymap    dungeonmap

    #-T        T-#

上述每张地图的过渡节点具有`target_map_xyz`指向另一张地图的`#`节点坐标（_未指向另一个“T”，该“T”未生成，从而使出口寻找不到目标！）。结果是可以东行进入地下城，然后立即向西返回城镇，跨过地图边界。

### 原型

[原型](../Components/Prototypes.md)是描述如何生成对象新实例的字典。上述每个_节点_和_链接_都有默认原型，使得`evennia xyzgrid spawn`命令可以将它们转换为 [XYZRoom](evennia.contrib.grid.xyzgrid.xyzroom.XYZRoom) 或 [XYZExit](evennia.contrib.grid.xyzgrid.xyzroom.XYZRoom) 。

默认原型在`evennia.contrib.grid.xyzgrid.prototypes`中找到（在安装此贡献时已添加），其 `prototype_key`s 为 `"xyz_room"` 和 `"xyz_exit"` - 使用这些作为`prototype_parent`来添加您自己的自定义原型。

`XYMap-data`字典的`"prototypes"`键允许您自定义每个XYMap中使用的原型。坐标给定为`(X, Y)`用于节点/房间，`(X, Y, direction)`用于链接/出口，其中方向为 "n"、"ne"、"e"、"se"、"s"、"sw"、"w"、"nw"、"u" 或 "d"。对于出口，建议_不_设置`key`，因为这是由网格生成器自动生成的以符合预期（“north”并带别名“n”）。

特殊坐标是`*`。这作为该坐标的通配符，可以用于该坐标的“默认”原型。

```python

MAPSTR = r"""

+ 0 1

1 #-#
   \
0 #-#

+ 0 1


"""


PROTOTYPES = {
    (0,0): {
	"prototype_parent": "xyz_room",
	"key": "隧道的尽头",
	"desc": "这是黑暗隧道的尽头。空气中弥漫着污水的味道。"
    },
    (0,0, 'e') : {
	"prototype_parent": "xyz_exit",
	"desc": "隧道向东继续通向黑暗"
    },
    (1,1): {
	"prototype_parent": "xyz_room",
	"key": "隧道的另一端",
	"desc": 黑暗隧道的另一端。这里的空气感觉更好。"
    }
    # 默认项
    ('*', '*'): {
    	"prototype_parent": "xyz_room",
	"key": "一条黑暗的隧道",
	"desc": "这里很黑。"
    },
    ('*', '*', '*'): {
	"prototype_parent": "xyz_exit",
	"desc": "隧道延伸进黑暗中。"
    }
}

XYMAP_DATA = {
    # ...
    "map": MAPSTR,
    "prototypes": PROTOTYPES
    # ...
}

```

生成上述地图时，地图左下角和右上角的房间将获得自定义描述和名称，而其他房间将具有默认值。地图底部左侧的一个出口（从房间往东的出口）将拥有自定义描述。

> 如果您习惯使用原型，您可能会注意到上述原型中我们没有添加`prototype_key`。这通常要求为每个原型添加。这是为了便利 - 如果您不添加`prototype_key`，网格将自动为您生成它 - 基于当前XYZ (+方向) 的哈希来生成。

如果您发现自己在已经生成网格/地图后更改原型，可以再次运行`evennia xyzgrid spawn`；更改将被识别并应用于现有对象。

#### 扩展基本原型

默认原型在`evennia.contrib.grid.xyzgrid.prototypes`中找到，可作为原型父级包含在地图中。难道不希望能够更改这些并使更改应用于整个网格吗？可以通过在`mygame/server/conf/settings.py`中添加以下内容来实现：

    XYZROOM_PROTOTYPE_OVERRIDE = {"typeclass": "myxyzroom.MyXYZRoom"}
    XYZEXIT_PROTOTYPE_OVERRIDE = {...}

> 如果您在原型中覆盖类型类，所用的类型类**必须**继承自`XYZRoom`和/或`XYZExit`。`BASE_ROOM_TYPECLASS`和`BASE_EXIT_TYPECLASS`设置不会有帮助 - 这些在非xyzgrid房间/出口中仍然是有用的。

只需添加您想要更改的内容 - 这些字典将_扩展_默认父级原型，而不是替换它们。只要您将地图的原型定义为使用`prototype_parent` 为`"xyz_room"`和/或`"xyz_exit"`，您的更改将得到应用。在进行此类更改后，您可能需要重新生成网格并重新加载服务器。

### 选项

`XYMAP_DATA`字典的最后一个元素是`"options"`，例如

```
XYMAP_DATA = {
    # ...
    "options": {
	"map_visual_range": 2
    }
}

```

`options`字典作为`**kwargs`传递给`XYZRoom.return_appearance`，以在游戏中可视化地图。它允许不同地图在显示上表现出不同的特性（请注意，尽管这些选项很方便，但当然也可以通过继承`XYZRoom`完全覆盖`return_appearance`）。

默认可视化如下：

```
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                                     #---#
                                    /
                                   @-
-~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
地下入口
向东，一个狭窄的开口通向黑暗。
出口：东北和东边
```

- `map_display`（布尔值）：这将完全关闭该地图的显示。
- `map_character_symbol`（字符串）：用于显示地图上“您”的符号。它可以有颜色，但应仅占一个字符空间。默认情况下为绿色 `@`。
- `map_visual_range`（整数）：这是您从当前位置可以看到的距离。
- `map_mode`（字符串）：这是“node”或“scan”，影响视觉范围的计算方式。
  在“node”模式下，范围显示距离您能看到多少个_节点_。在“scan”模式中，您可以选择看到多少个_屏幕上的字符_在您的人物附近。
  为了可视化，假设这是完整的地图（其中`@`是角色位置）：

      #----------------#
      |                |
      |                |
      # @------------#-#
      |                |
      #----------------#

  这是玩家在'节点'模式下看到的，将`map_visual_range=2`设置为：

      @------------#-#

  ...而在'扫描'模式下：

      |
      |
      # @--
      |
      #----

  `node`模式的优势在于只显示连接的链接，并且在导航时非常有效，但根据地图，可能会包含相对较远的节点视图。`scan`模式可能意外地显示地图的未连接部分（参见上面的示例），但限制范围可以作为隐藏信息的一种方式。

  当玩家在'节点'模式下看到时，将`map_visual_range=1`：

      @------------#

  ...而在'扫描'模式下：

      @-

  例如，可以在户外/城镇地图使用'节点'模式，而在探索地下城时使用'scan'模式。

- `map_align`（字符串）：可以为'r'、'c'或'l'之一。这将使地图相对于房间文本进行偏移。默认情况下居中。
- `map_target_path_style`: 可视化目标路径的方式。这是一个字符串，采用`{display_symbol}`格式化标签。它将用路径中每个地图元素的`display_symbol`替换此格式。默认设置为`"|y{display_symbol}|n"`，即，路径为黄色。
- `map_fill_all`（布尔值）：地图区域是否应填充整个客户端宽度（默认设置），或更改为始终仅与房间描述一样宽。请注意，在后一种情况下，如果描述的宽度变化很大，则地图可能会在客户端窗口中“跳动”。
- `map_separator_char`（字符串）：用于地图与房间描述之间分隔线的字符。默认为 `"|x~|n"` - 波浪状的深灰色线条。

对已生成地图的选项进行更改无需重新生成地图，但您_确实_需要重新加载服务器！

### 关于寻路器

新的`goto`命令示范了_寻路器_的使用。这是一个计算任意大小和复杂度的XY地图节点（房间）之间最短路线的算法。如果玩家知道该位置的名称，它允许他们快速移动到该位置。关于它的一些细节：

- 寻路器解析节点和链接以构建一个从每个节点到_所有_其他节点的移动距离矩阵。使用[迪杰斯特拉算法](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm)解决该路径。
- 对于非常大的地图，寻路器的矩阵构建可能会花费大量时间。因此，它们以pickle格式的二进制文件缓存在`mygame/server/.cache/` 中，并且仅在地图更改时重建。它们是安全的删除（您还可以使用`evennia xyzgrid initpath`来强制创建/重建缓存文件）。
- 一旦缓存，寻路器便很快（查找500步最短路径需耗时不到0.1s，涉及20,000个节点/房间）。
- 重要的是要记住，寻路器仅在_一个_ XYMap内工作。它不会找到跨地图过渡的路径。如果这点很重要，可以考虑将游戏的所有区域视为一个XYMap。这可能没问题，但会使添加/删除新地图变得更困难。
- 寻路器实际上会对每个链接的“权重”进行求和，以确定哪个路线是“最便宜的”（最短的）路径。默认情况下，除阻塞链接外的每个链接的成本为1（因此，成本等于在节点之间移动的步骤数）。但是，单独的链接可以更改为较高/较低的权重（必须`>=1`）。较高的权重意味着寻路器使用该路径的可能性较小（这也可能对用户视觉上造成困惑，因此请小心使用）。
- 寻路器将对长链接链的权重进行平均。由于所有链接默认都具有相同的权重（=1），这意味着`#-#`的移动成本与`#----#`相同，尽管它在视觉上“更短”。此行为可以通过使用使用`average_long_link_weights = False`的链接进行更改。

## XYZGrid

`XYZGrid`是一个[全局脚本](../Components/Scripts.md)，在网格上保存所有`XYMap`对象。应始终创建一个XYZGrid。

要在代码中访问网格，有几种方法：

- 您可以像搜索其他脚本一样搜索网格。它名为“XYZGrid”。

    grid = evennia.search_script("XYZGrid")[0]

  （`search_script`始终返回一个列表）
- 您可以通过`evennia.contrib.grid.xyzgrid.xyzgrid.get_xyzgrid`获取它。

    from evennia.contrib.grid.xyzgrid.xyzgrid import get_xyzgrid
    grid = get_xyzgrid()

  这将*始终*返回一个网格，如果一个尚不存在，则创建一个空网格。因此，这也是推荐在代码中生成一个新网格的方式。
- 您可以从已存在的XYZRoom/Exit中获取，通过访问它们的 `.xyzgrid` 属性。

    grid = self.caller.location.xyzgrid  # 如果当前在网格房间内

网格类的许多工具涉及加载/添加和删除地图，您期望使用`evennia xyzgrid`命令来执行此操作。但还有几种通常有用的方法：

- `.get_room(xyz)` - 获取特定坐标`(X, Y, Z)`的房间。此方法仅在地图实际上已经生成之后才能工作。例如，`.get_room((0,4,"the dark castle))`。使用`'*'`作为通配符，因此，`.get_room(('*','*',"the dark castle))`将为您获得在黑暗城堡地图上生成的所有房间。
- `.get_exit(xyz, name)` - 获取特定出口，例如，`.get_exit((0,4,"the dark castle", "north")`。您也可以使用`'*'`作为通配符。

还可以直接访问 `XYZGrid` 上特定解析的 `XYMap` 对象：

- `.grid` - 这是所有XYMaps的实际（缓存）存储，格式为 `{zcoord: XYMap, ...}`
- `.get_map(zcoord)` - 获取特定的XYMap。
- `.all_maps()` - 获取所有XYMaps的列表。

除非您想对地图的工作方式进行重大更改（或学习其功能），否则您可能永远不需要修改`XYZMap`对象本身。不过，您可能想要了解如何调用寻路器：

- `xymap.get_shortest_path(start_xy, end_xy)`
- `xymap.get_visual_range(xy, dist=2, **kwargs)`

请参阅[XYMap](xymap)文档以获取详细信息。

## XYZRoom和XYZExit

这些是位于`evennia.contrib.xyzgrid.xyzroom`中的自定义[类型类](../Components/Typeclasses.md)。它们扩展了基本`DefaultRoom`和`DefaultExit`，以便识别其X、Y和Z坐标。

```{warning}

    您通常**不应该**手动创建 XYZRooms/Exits。它们旨在根据网格的布局进行创建/删除。因此，要添加一个新房间，请在地图中添加一个新节点。删除它时，只需删除它。然后重新运行 **evennia xyzgrid spawn**。手动创建的 XYZRooms/Exits 与系统混合在一起，可能会导致它们被删除或系统混淆。

    如果您**仍然**希望手动创建 XYZRoom/Exits（不要说我们没有警告您！），则应使用它们的 `XYZRoom.create()` 和 `XYZExit.create()` 方法。这确保它们使用的 XYZ 是唯一的。

```

`XYZRoom`和`XYZExit`上有用（附加）属性：

- `xyz` 实体的 `(X, Y, Z)` 坐标，例如`(23, 1, "greenforest")`
- `xyzmap` 此节点所属的 `XYMap`。
- `get_display_name(looker)` - 此次已被修改以显示实体的坐标，以及如果您具有建造者或更高特权的话，会显示`#dbref`。
- `return_appearance(looker, **kwargs)` - 这已广泛修改为`XYZRoom`，以显示地图。提供在 `XYMAP_DATA` 中的选项将作为 `**kwargs` 出现在此方法中，如果您覆盖此方法，可以深入自定义地图的显示。
- `xyz_destination`（仅针对 `XYZExits`） - 这表明出口的目的地的xyz坐标。

坐标存储为[标签](../Components/Tags.md)，其中房间和出口标记类别为`room_x_coordinate`、`room_y_coordinate`和`room_z_coordinate`，同时出口使用相同的标签类别，还附带其目的地的标签类别，标记为 `exit_dest_x_coordinate`、`exit_dest_y_coordinate` 和 `exit_dest_z_coordinate`。

为了便于按坐标查询数据库，每种类型类都提供了自定义管理器方法。过滤方法允许使用`'*'`作为通配符。

```python

# 查找foo地图中所有房间的列表
rooms = XYZRoom.objects.filter_xyz(('*', '*', 'foo'))

# 查找foo地图上名称为“Tunnel”的所有房间的列表
rooms = XYZRoom.objects.filter_xyz(('*', '*', 'foo'), db_key="Tunnel")

# 查找foo地图第一列中的所有房间
rooms = XYZRoom.objects.filter_xyz((0, '*', 'foo'))

# 查找给定坐标下的确切房间（不允许使用通配符）
room = XYZRoom.objects.get_xyz((13, 2, foo))

# 找到特定房间中的所有出口
exits = XYZExit.objects.filter_xyz((10, 4, foo))

# 查找指向特定目的地的所有出口（来自所有地图）
exits = XYZExit.objects.filter_xyz_exit(xyz_destination=(13,5,'bar'))

# 查找从某个房间到另一个地图上的任何地方的出口
exits = XYZExit.objects.filter_xyz_exit(xyz=(1, 5, 'foo'), xyz_destination=('*', '*', 'bar'))

# 查找指向特定目的地的确切出口（不允许使用通配符）
exit = XYZExit.objects.get_xyz_exit(xyz=(0, 12, 'foo'), xyz_destination=(5, 2, 'foo'))

```

您可以通过让网格生成您自己的子类，来自定义XYZRoom/Exit。要这样做，您需要覆盖用于在网格上生成房间的原型。最简单的方法是修改设置中基本原型父级的内容（请参阅上述[XYZRoom和XYZExit](#xyzroom和xyzexit)部分）。

## 使用网格

使用网格的工作流程通常如下：

1. 准备一个模块，其中包含组成`XYMAP_DATA`的_Map字符串_、_地图图例_、_原型_和_选项_的字典。如果通过添加多个 `XYMAP_DATA`到`XYMAP_DATA_LIST`中，一个模块可包含多个地图。
2. 如果您的地图包含`TransitionMapNodes`，则目标地图必须也添加，或者已经存在于网格中。如果没有，您现在应该跳过该节点（否则在生成时将面临错误，因为出口目的地不存在）。
3. 运行`evennia xyzgrid add <module>`，将地图注册到网格中。如果没有网格，则将创建它。修复解析器报告的任何错误。
4. 使用`evennia xyzgrid show <zcoord>`检查解析后的地图，并确保它们看起来正常。
5. 运行`evennia xyzgrid spawn`以生成/更新实际的`XYZRoom`和`XYZExit`。
6. 如果您想，您现在可以通过常规构建命令手动调整网格。您在网格原型中未指定的任何内容都可以在您的游戏中本地修改 - 只要整个房间/出口未被删除，它们将不会受到`evennia xyzgrid spawn`的影响。您还可以挖掘/打开进入网格中“嵌入”的其他房间的出口。这些出口的名称不得与网格方向之一（北、东北等，或上下）重复，否则网格将在下次运行`evennia xyzgrid spawn`时删除它。
7. 如果您想添加新的网格房间/出口，您始终应通过修改_地图字符串_并随后重新运行`evennia xyzgrid spawn`来应用更改。

## 详细信息

Evennia的默认房间为非欧几里得的 - 它们可以通过任何类型的出口彼此连接，而不必在位置关系上明确。这提供了最大的灵活性，但许多游戏希望使用基本的移动（北、东等）以及功能，例如在两点之间找到最短路径。

此贡献强制每个房间存在于一个三维XYZ网格中，并且实现非常高效的寻路，同时提供工具以显示您当前的视距和许多相关功能。

网格的房间完全由外部控制，使用字符串和字典定义的python模块的地图。可以将网格与非网格房间结合使用，并且您可以在游戏中随意装饰网格房间，但不能在不编辑游戏外的地图文件的情况下生成新的网格房间。

## 安装

1. 如果您尚未安装额外的贡献需求，可以通过运行`pip install evennia[extra]`来完成，或者如果您使用`git`安装，请在`evennia/`存储库文件夹中执行`pip install --upgrade -e .[extra]`。
2. 在`mygame/commands.default_cmds.py`中导入并添加 `evennia.contrib.grid.xyzgrid.commands.XYZGridCmdSet`到`CharacterCmdset`命令集中。重新加载服务器。这使得`map`、`goto/path`和修改后的`teleport`与`open`命令在游戏中可用。
3. 编辑`mygame/server/conf/settings.py`并设置

        EXTRA_LAUNCHER_COMMANDS['xyzgrid'] = 'evennia.contrib.grid.xyzgrid.launchcmd.xyzcommand'

4. 运行新安装的`evennia xyzgrid help`，以获取有关如何生成网格的说明。

## 示例用法

安装后，请执行以下操作（在能够使用`evennia`命令的命令行中）安装示例网格：

    evennia xyzgrid init
    evennia xyzgrid add evennia.contrib.grid.xyzgrid.example
    evennia xyzgrid list
    evennia xyzgrid show "the large tree"
    evennia xyzgrid show "the small cave"
    evennia xyzgrid spawn
    evennia reload

（记得在生成操作后重新加载服务器）。

现在您可以登录服务器并执行`teleport (3,0,the large tree)`以传送到地图。

您可以使用`open togrid = (3, 0, the large tree)`从您的当前位置打开一个永久的（单向）出口到网格。要回到非网格位置，只需站在网格房间并打开一个新出口：
`open tolimbo = #2`。

尝试`goto view`去到顶端，尝试`goto dungeon`去到地下城入口，位于树底部。
