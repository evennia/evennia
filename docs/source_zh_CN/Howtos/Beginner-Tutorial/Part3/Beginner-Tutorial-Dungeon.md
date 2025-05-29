# 程序生成的地下城

我们在[房间教程](./Beginner-Tutorial-Rooms.md)中讨论的房间都是 _手动_ 生成的。也就是说，人工构建者必须坐下来在游戏中或使用代码手动生成每个房间。

在本节中，我们将探索构成我们游戏地下城的房间的 _程序生成_。程序生成意味着这些房间在玩家探索时会自动且半随机地生成，从而创建出每次都不同的地下城布局。

## 设计概念

这部分描述了程序生成的高层工作原理。在我们开始编写代码之前，理解这一点非常重要。

我们将假设地下城存在于一个 2D 平面上（x,y，没有 z 方向）。我们只使用 N、E、S、W 方位，但没有理由不可以使用 SE、NW 等等，只是这可能会让玩家更难想象。更多的可能方向也更容易导致碰撞和单向出口（见下文）。

这个设计很简单，但通过调整一些设置，它可以产生感觉截然不同的地下城系统。

### 起始房间

所有玩家的目的是要下降到一个井内，井底是一个静态创建的房间，不会改变。

```{code-block}
:caption: 起始房间
            
                 Branch N                
                    ▲                    
                    │                    
           ┌────────┼────────┐           
           │        │n       │           
           │        ▼        │           
           │                 │           
           │                e│           
Branch W ◄─┼─►     up▲     ◄─┼─► Branch E1
           │w                │           
           │                 │           
           │        ▲        │           
           │        │s       │           
           └────────┼────────┘           
                    │                    
                    ▼                    
                 Branch S               
```

选择从这个房间的一个出口（除了通往地面的那个出口）时，魔法便会发生。假设一个玩家向 `east`（东）移动：

- 第一个向东移动的人会生成一个新的“地下城分支”（图中的 Branch E1）。这是与通过任何其他出口时生成的地下城有别的“实例”。
- 一个计时器开始运作。在这个计时器活动期间，所有向东走的人都会进入 Branch E1。这使得玩家可以组队合作，挑战一个分支。
- 当计时器结束后，所有向东走的人将进入一个 _新的_ Branch E2。这是一个与 Branch E1 无重叠的新分支。
- 位于 Branch E1 和 E2 的玩家总是可以向 `west`（西）返回到起始房间，但在计时器结束后，返回现在是单向出口—如果他们这样做，他们将无法返回到他们以前的分支。

### 生成新分支房间

每个地下城分支本身会在一个 (X, Y) 坐标网格上跟踪属于该分支的房间布局。

```{code-block}
:caption: 创建东部分支及其第一个房间
                   ?         
                   ▲         
                   │         
┌─────────┐   ┌────┼────┐    
│         │   │A   │    │    
│         │   │   PC    │    
│  start◄─┼───┼─► is  ──┼──►?
│         │   │   here  │    
│         │   │    │    │    
└─────────┘   └────┼────┘    
                   │         
                   ▼         
```

起始房间总是在坐标 `(0, 0)`。 

只有在实际移动到它时才生成地下城房间。在上面的例子中，玩家以 `east`（东）方向从起始房间移动，启动了一个新的地下城分支。这个分支还在坐标 `(1,0)` 处创建了一个新房间（房间 `A`）。在这种情况下，它（随机）给这个房间配置了三个出口：`north`（北）、`east`（东）和 `south`（南）。
由于这个分支刚刚创建，回到起始房间的出口仍然是双向的。

这个地下城分支在生成新房间时遵循以下程序：

- 它总是创建一个返回到我们来的房间的出口。
- 它检查我们在地下城中目前有多少个未探索的出口。也就是说，有多少个我们尚未走过的出口。这个数字永远不能为零，除非我们想要一个能够“完成”的地下城。在任意时刻允许开放的未探索出口的最大数量是一个我们可以实验的设置。一个小的最大数量会导致线性地下城，而更大的数字会使地下城变得广阔而迷宫般。
- 出口（不返回到我们来的地方的出口）的生成规则如下：
    - 随机创建0到当前房间和分支的允许未探索出口数量之间的数量的出口。
    - 仅在此操作不会导致有至少一个未探索出口在地下城分支的任何地方开放时才创建0个出口（死胡同）。
    - 不 _创建_ 一个指向之前生成房间的出口（所以我们更倾向于产生指向新地方的出口，而不是回到旧地方）。
    - 如果先前创建的出口最终指向新创建的房间，这 _是_ 被允许的，这也是创建单向出口的唯一时机（下面的例子）。所有其他的出口总是双向出口。这也呈现出唯一可以关闭一个地下城的微小机会而无路可走，只能返回开始。
    - 决不能创建返回到起始房间的出口（例如，从另一个方向）。 返回到起始房间的唯一方法是回溯。

在以下例子中，我们假设在任意时间允许打开的未探索出口的最大数量设置为4。

```{code-block}
:caption: 在东部地下城分支的四个步骤后
                    ?                                 
                   ▲                                 
                   │                                 
┌─────────┐   ┌────┼────┐                            
│         │   │A   │    │                            
│         │   │         │                            
│  start◄─┼───┼─      ──┼─►?                         
│         │   │    ▲    │                            
│         │   │    │    │                            
└─────────┘   └────┼────┘                            
                   │                                 
              ┌────┼────┐   ┌─────────┐   ┌─────────┐
              │B   │    │   │C        │   │D        │
              │    ▼    │   │         │   │   PC    │
          ?◄──┼─      ◄─┼───┼─►     ◄─┼───┼─► is    │
              │         │   │         │   │   here  │
              │         │   │         │   │         │
              └─────────┘   └─────────┘   └─────────┘
```

1. 玩家（PC）从起始房间向 `east`（东）移动。创建了一个新房间 `A`（坐标 `(1, 0)`）。过一段时间，返回到起始房间的出口变成了单向出口。该分支最多可以有4个未探索的出口，并且地下城分支随机从房间 `A` 添加了另外三个出口。
2. 玩家向 `south`（南）移动。创建了一个新房间 `B`（`(1,-1)`），它有两个随机出口，这是调解员此时允许创建的数量（目前有 4 个打开的出口）。它总是创建一个返回到前一个房间（`A`）的出口。
3. 玩家向 `east`（东）移动（坐标 `(2, -1)`）。新房间 `C` 被创建。由于地下城分支已经有 3 个未探索的出口，因此此房间只能添加 1 个出口。
4. 玩家向 `east`（东）移动（`(3, -1)`）。虽然地下城分支仍有创建 1 个出口的预算，但它知道其他地方还有未探索的出口，因此可以随机创建 0 个出口。这是一个死胡同。玩家必须回去探索另一个方向。

让我们改变一下地下城来做另一个示例：

```{code-block}
:caption: 循环
                   ?                   
                   ▲                   
                   │                   
┌─────────┐   ┌────┼────┐              
│         │   │A   │    │              
│         │   │         │              
│  start◄─┼───┼─      ──┼──►?           
│         │   │    ▲    │              
│         │   │    │    │        ?     
└─────────┘   └────┼────┘        ▲     
                   │             │     
              ┌────┼────┐   ┌────┼────┐
              │B   │    │   │C   │    │
              │    ▼    │   │   PC    │
          ?◄──┼─      ◄─┼───┼─► is    │
              │         │   │   here  │
              │         │   │         │
              └─────────┘   └─────────┘
```

在这个例子中，玩家向 `east`（东）、`south`（南）、`east`（东）移动，但是房间 `C` 的出口指向北部，进入一个 `A` 已经有出口指向的坐标。向北移动会出现如下情况：

```{code-block}
:caption: 创建一个单向出口
                   ?                   
                   ▲                   
                   │                   
┌─────────┐   ┌────┼────┐   ┌─────────┐
│         │   │A   │    │   │D   PC   │
│         │   │         │   │    is   │
│  start◄─┼───┼─      ──┼───┼─►  here │
│         │   │    ▲    │   │    ▲    │
│         │   │    │    │   │    │    │
└─────────┘   └────┼────┘   └────┼────┘
                   │             │     
              ┌────┼────┐   ┌────┼────┐
              │B   │    │   │C   │    │
              │    ▼    │   │    ▼    │
          ?◄──┼─      ◄─┼───┼─►       │
              │         │   │         │
              │         │   │         │
              └─────────┘   └─────────┘
```

当玩家向北移动时，房间 `D` 会在 `(2,0)` 处创建。

虽然 `C` 到 `D` 的出口是正常的双向出口，但这从 `A` 到 `D` 创造了一个单向出口。

创建了实际房间的出口会获得双向出口，所以如果玩家从 `C` 返回并通过向 `A` 的出口创建 `D` 房间，那么单向出口将来自 `C`。

> 如果最大允许的开放未探索出口的数量较小，这种情况是可能“完成”地下城的唯一情况（没有更多未探索的出口可跟随）。我们接受这种情况，玩家必须掉头，尝试另一个地下城分支。

```{code-block}
:caption: 永不链接回起始房间
                   ?                   
                   ▲                   
                   │                   
┌─────────┐   ┌────┼────┐   ┌─────────┐
│         │   │A   │    │   │D        │
│         │   │         │   │         │
│  start◄─┼───┼─      ──┼───┼─►       │
│         │   │    ▲    │   │    ▲    │
│         │   │    │    │   │    │    │
└─────────┘   └────┼────┘   └────┼────┘
                   │             │     
┌─────────┐   ┌────┼────┐   ┌────┼────┐
│E        │   │B   │    │   │C   │    │
│  PC     │   │    ▼    │   │    ▼    │
│  is   ◄─┼───┼─►     ◄─┼───┼─►       │
│  here   │   │         │   │         │
│         │   │         │   │         │
└─────────┘   └─────────┘   └─────────┘
```

在这里，玩家从房间 `B` 向 `west`（西）移动，创建了房间 `E`（坐标 `(0, -1)`）。

地下城分支不会创建一个返回到起始房间的链接，但它 _可以_ 创建最多两个新出口 `west` 和/或 `south`。由于房间 `A` 中仍然有一个未探索的出口向 `north`，因此该分支也允许随机分配 0 个出口，正是它在这里所做的。

玩家需要回溯并从 `A` 向 `north`（北）移动来继续探索这个地下城分支。

### 让地下城更具危险性

地下城如果没有危险那就不会有趣！需要有怪物可供击杀、难题待解以及宝藏可获得。

当玩家首次进入房间时，该房间被标记为 `未清理`。在房间未清理时，玩家 _无法_ 使用该房间出路中的任何未探索出口。他们 _仍然_ 可以退回至他们来的地方，除非他们被困住而无法战斗，在这种情况下，他们必须首先逃离。

一旦玩家克服了房间的挑战（并可能获得一些奖励），它将变为 `清理`。如果房间是空的或者没有阻挡玩家的挑战（如用于其他地方难题的书面提示），房间可以自动清理。

### 难度提升

```{sidebar} 风险与奖励
地下城深度/难度的概念与有限资源很好地结合在一起。如果治疗受限于可以携带的内容，这使得玩家必须决定是否想要冒险深入探索或带着当前的战利品撤退回地面以恢复。
```

“地下城”的“难度”通过玩家的“深度”来衡量。这个深度是玩家到达的 _径向距离_ 从起始房间，使用悠久的[勾股定理](https://en.wikipedia.org/wiki/Pythagorean_theorem) 来计算：

    depth = int(math.sqrt(x**2 + y**2))

因此，如果你在房间 `(1, 1)`，难度为 1。而在房间坐标 `(4,-5)`，难度为 6。增加深度应导致更具挑战性的挑战，但也伴随更大的奖励。

## 开始实现

现在让我们实现这个设计！

```{sidebar}
你还可以在 `evennia/contrib/tutorials` 中找到地下城生成器的代码示例，在 [evadventure/dungeon.py](evennia.contrib.tutorials.evadventure.dungeon) 中。
```
> 创建一个新模块 `evadventure/dungeon.py`。

## 基本地下城房间

这是设计的基本元素。因此，我们将在这里开始。

回到[房间教程](./Beginner-Tutorial-Rooms.md)，我们创建了一个基本的 `EvAdventureRoom` 类型类。
我们将对其进行扩展以适应地下城房间。

```{code-block} python
:linenos: 
:emphasize-lines: 13-14,29,32,36, 38
# 在 evadventure/dungeon.py 中 

from evennia import AttributeProperty
from .rooms import EvAdventureRoom 


class EvAdventureDungeonRoom(EvAdventureRoom):
    """
    危险的地下城房间。

    """

    allow_combat = AttributeProperty(True, autocreate=False)
    allow_death = AttributeProperty(True, autocreate=False)

    # 地下城生成属性；在房间创建时设置
    dungeon_branch = AttributeProperty(None, autocreate=False)
    xy_coords = AttributeProperty(None, autocreate=False)

    def at_object_creation(self):
        """
        设置房间的 `not_clear` 标签。这个标签在房间“清理”时会被移除，
        对每个房间来说“清理”意味着不同的东西。

        我们将其放在这里而不是在房间创建代码中，以便于覆盖（例如，我们可能希望一个空房间自动清理）。

        """
        self.tags.add("not_clear", category="dungeon_room")
    
    def clear_room(self):
        self.tags.remove("not_clear", category="dungeon_room")
    
    @property
    def is_room_clear(self):
        return not bool(self.tags.get("not_clear", category="dungeon_room"))

    def get_display_footer(self, looker, **kwargs):
        """
        作为房间描述的一部分显示该房间是否“已清理”。

        """
        if self.is_room_clear:
            return ""
        else:
            return "|r前方的道路被阻挡了！|n"
```

```{sidebar} 存储房间类型类
对于本教程，我们将所有地下城相关代码保留在一个模块中。不过也有人可以认为它们应该与其他房间一起放在 `evadventure/rooms.py` 中。这只是你想如何组织的事情。欢迎根据自己的游戏进行组织。
```

- **第 14-15 行**：地下城房间是危险的，因此与基础的 EvAdventure 房间不同，我们允许在其中进行战斗和死亡。
- **第 17 行**：我们存储对地下城分支的引用，以便在房间创建时访问。如果我们希望在创建房间时了解有关地下城分支的内容，这可能会很相关。
- **第 18 行**：xy 坐标将作为元组 `(x,y)` 存储在房间上。

所有其他功能均旨在管理房间的“清理”状态。

- **第 29 行**：当我们创建房间时，Evennia 将始终调用其 `at_object_creation` 钩子。我们确保在其上添加一个 [标签](../../../Components/Tags.md) `not_clear`（类别为“dungeon_room”，以避免与其他系统发生冲突）。
- **第 32 行**：我们将使用 `.clear_room()` 方法在房间的挑战克服后移除该标签。
- **第 36 行**：`.is_room_clear` 是一个方便的属性，用于检查标签。这隐藏了标签，以便我们不需要担心如何跟踪清理房间的状态。
- **第 38 行**：`get_display_footer` 是一个标准的 Evennia 钩子，用于自定义房间的底部显示。 

## 地下城出口

地下城出口与其他出口不同，因为我们希望穿越它们的行为在对面创建房间。

```python
# 在 evadventure/dungeon.py 中 

# ...

from evennia import DefaultExit

# ... 

class EvAdventureDungeonExit(DefaultExit):
    """
    地下城出口。此出口不会在穿越之前创建目标房间。

    """

    def at_object_creation(self):
        """
        我们希望在房间未清理之前阻止前进。

        """
        self.locks.add("traverse:not objloctag(not_clear, dungeon_room)")

    def at_traverse(self, traversing_object, target_location, **kwargs):
        pass  # 待实现！

    def at_failed_traverse(self, traversing_object, **kwargs):
        """
        当穿越失败时被调用。

        """
        traversing_object.msg("你不能通过这个方向！")

```

目前，我们尚未为创建分支中新的房间编写代码，因此我们暂时将 `at_traverse` 方法留空。这个钩子是 Evennia 在穿越出口时调用的。

在 `at_object_creation` 方法中，我们确保添加一个 [锁](../../../Components/Locks.md)，类型是“traverse”，它将限制谁可以通过此出口。我们用 objlocktag 锁功能对其进行锁定。这会检查被访问的对象（这个出口）的位置（该地下城房间）是否带有来自库的“not_clear”标签，同时在类别“dungeon_room”中。如果有，则退出 _失败_。换句话说，房间未被清理时，这种类型的出口将不允许任何人通过。

`at_failed_traverse` 钩子让我们在出现问题时自定义错误消息。

## 地下城分支和坐标网格

地下城分支负责一个地下城的结构实例。

### 网格坐标和出口映射

在我们开始之前，我们需要为网格建立一些常量—我们将把房间放置在该 xy 平面上。 

```python
# 在 evadventure/dungeon.py 中 

# ... 

# 基本方向
_AVAILABLE_DIRECTIONS = [
    "north",
    "east",
    "south",
    "west",
]

_EXIT_ALIASES = {
    "north": ("n",),
    "east": ("e",),
    "south": ("s",),
    "west": ("w",),
}
# 查找反向基准方向
_EXIT_REVERSE_MAPPING = {
    "north": "south",
    "east": "west",
    "south": "north",
    "west": "east",
}

# 通过移动方向如何转变 xy 坐标
_EXIT_GRID_SHIFT = {
    "north": (0, 1),
    "east": (1, 0),
    "south": (0, -1),
    "west": (-1, 0),
}
```

在本教程中，我们只允许 NESW 移动。如果你想，也可以很容易地添加 NE、SE、SW、NW 等方向。我们为出口别名创建了映射（这里只有一个，但每个方向也可以有多个别名）。我们还确定了“反向”方向，以便将在程序中轻松创建“返回出口”。

`_EXIT_GRID_SHIFT` 映射指示在特定方向上移动时 (x,y) 坐标的变化方式。因此，如果你位于 `(4,2)` 并向 `south`（南）移动，你将到达 `(4,1)`。

#### 地下城分支脚本的基础结构

我们将此组件基于 Evennia [脚本](../../../Components/Scripts.md)—它们可以被视作在世界中没有物理存在的游戏实体。脚本也具有时间记录属性。

```{code-block} 
:linenos: 
:emphasize-lines: 
# 在 evadventure/dungeon.py 中 

from evennia.utils import create
from evennia import DefaultScript

# ... 

class EvAdventureDungeonBranch(DefaultScript):
    """
    为每个地下城“实例”创建了一个脚本。该分支负责确定
    当角色进入地下城内的出口时应该创建什么。

    """
    # 这决定了地下城的分支程度
    max_unexplored_exits = 2
    max_new_exits_per_room = 2

    rooms = AttributeProperty(list())
    unvisited_exits = AttributeProperty(list())

    last_updated = AttributeProperty(datetime.utcnow())

    # 房间生成函数；从分支首次创建的相同名称的值复制
    room_generator = AttributeProperty(None, autocreate=False)

    # (x,y)：分支使用的房间坐标
    xy_grid = AttributeProperty(dict())
    start_room = AttributeProperty(None, autocreate=False)


    def register_exit_traversed(self, exit):
        """
        告诉系统给定的出口已被穿越。
        这使我们能够跟踪未访问路径的数量，以免其呈指数增长。

        """
        if exit.id in self.unvisited_exits:
            self.unvisited_exits.remove(exit.id)

    def create_out_exit(self, location, exit_direction="north"):
        """
        从房间创建输出出口。目标房间尚未创建。

        """
        out_exit = create.create_object(
            EvAdventureDungeonExit,
            key=exit_direction,
            location=location,
            aliases=_EXIT_ALIASES[exit_direction],
        )
        self.unvisited_exits.append(out_exit.id)
        
    def delete(self):
        """
        清理地下城分支。

        """
        pass  # 待实现
        
    def new_room(self, from_exit):
        """
        创建一个新的地下城房间，通往提供的出口。

        参数：
            from_exit (Exit): 通往此新房间的出口。

        """
        pass  # 待实现
```

这设置了分支所需的有用属性，并勾勒出一些我们将在下面实现的方法。

分支有几个主要任务：
- 跟踪有多少个未探索的出口可用（确保不超过最大允许数量）。当角色通过这些出口时，我们必须相应更新。
- 在未探索出口被穿越时创建新房间。该房间也可能有外部出口。我们还必须跟踪这些房间和出口，以便在清理时删除它们。
- 该分支也必须能够删除自己，清理所有资源和房间。

由于 `register_exit_traversed` 和 `create_out_exit` 是直接的，我们立即实现它们。创建出口的唯一额外部分是确保标记新出口为“未访问”，以便分支能够跟踪它。

### 关于房间生成器的说明

`EvAdventureDungeonBranch` 的 `room_generator` 属性特别注意。它将指向一个函数。我们将其制作成插件，因为生成房间是我们可能希望在创建游戏内容时大量定制的工作—这里将生成我们的挑战、房间描述等。

很明显，房间生成器必须与地下城分支、当前的预期难度（在我们的情况下是深度）和要在其上创建房间的 xy 坐标相关联。

以下是一个非常基本的房间生成器示例，仅将深度映射到不同的房间描述： 

```
# 在 evadventure/dungeon.py 中（也可以放置在游戏内容文件中）

# ... 

def room_generator(dungeon_branch, depth, coords):
    """
    插件房间生成器

    这个默认生成器返回相同的空房间，但具有不同的描述。

    参数：
        dungeon_branch (EvAdventureDungeonBranch): 当前地下城分支。
        depth (int): 此新房间放置的地下城的“深度”（离起始房间的径向距离）。
        coords (tuple): 要创建的新房间的 `(x,y)` 坐标。

    """
    room_typeclass = EvAdventureDungeonRoom

    # 深度与房间名称和描述的简单映射
    name_depth_map = {
        1: ("水浸通道", "这个土墙通道滴着水。"),
        2: ("有根的通道", "树根穿过土墙。"),
        3: ("坚硬的粘土通道", "这个通道的墙壁是坚硬的粘土。"),
        4: ("带石块的粘土", "这个通道有粘土与嵌入的石块。"),
        5: ("石头通道", "墙壁是崩溃的石头，树根穿过它。"),
        6: ("石厅", "墙壁是用粗糙的石头切割而成。"),
        7: ("石室", "一个用粗重石块建造的石室。"),
        8: ("花岗岩走廊", "墙壁是由优质的花岗岩块造的。"),
        9: ("大理石通道", "墙壁是光滑而闪亮的大理石。"),
        10: ("装饰房间", "大理石墙壁上有挂毯和家具。"),
    }
    key, desc = name_depth_map.get(depth, ("黑暗的房间", "这里非常黑暗。"))

    new_room = create.create_object(
        room_typeclass,
        key=key,
        attributes=(
            ("desc", desc),
            ("xy_coords", coords),
            ("dungeon_branch", dungeon_branch),
        ),
    )
    return new_room

```

这个函数可以包含 _很多_ 逻辑—根据深度、坐标或随机机会，我们可以生成各种不同的房间，并将其填充各种怪物、难题等。由于我们可以访问地下城分支对象，我们甚至可以在其他房间中更改内容，以实现非常复杂的交互（多房间难题，听起来怎么样？）。

这将在[第4部分](../Part4/Beginner-Tutorial-Part4-Overview.md)中使用，我们将在其中利用我们所创建的工具来真正构建游戏世界。

### 删除地下城分支

我们希望能够清理分支。这有很多原因：
- 当每个玩家离开分支后，他们就无法返回，因此所有数据现在都只占用空间。
- 分支并非打算永久存在。所以如果玩家只是停止探索并在分支中长时间呆着，我们应该有办法强制他们返回。

为了安全清理这个地下城内的角色，我们做了一些假设：
- 当创建地下城分支时，我们给其脚本一个唯一标识符（例如，某个时间涉及的内容）。
- 当开始地下城分支时，我们给角色标记该分支的唯一标识符。
- 同样，当我们在该分支中创建房间时，给它们打上该分支的标识符标签。

通过做到这一点，可以很简单地找到所有在该分支中的角色和房间，以便执行这个清理操作。

```python
# 在 evadventure/dungeon.py 中 

from evennia import search

# ... 

class EvAdventureDungeonBranch(DefaultScript):

    # ...

    def delete(self):
        """
        清理地下城分支，安全地移除玩家。

        """
        # 首先，将所有角色安全地移回起始房间
        characters = search.search_object_by_tag(self.key, category="dungeon_character")
        start_room = self.start_room
        for character in characters:
            start_room.msg_contents(
                "突然有人踉跄地从黑暗出口中走出，满身灰尘！"
            )
            character.location = start_room
            character.msg(
                "|r经过一段时间的沉默，房间突然摇晃，然后坍塌！"
                "一切都变黑了 ...|n\n\n然后你意识到你回到起始地点。"
            )
            character.tags.remove(self.key, category="dungeon_character")
        # 然后删除地下城中所有房间（这也将删除出口）
        rooms = search.search_object_by_tag(self.key, category="dungeon_room")
        for room in rooms:
            room.delete()
        # 最后删除分支本身
        super().delete()

    # ...

```

`evennia.search.search_object_by_tag` 是 Evennia 内置实用程序，用于查找带有特定标签+类别组合的对象。

1. 首先，我们获取角色并将它们移动到起始房间，并提供相关消息。
2. 然后，我们获取所有房间并删除它们（出口将自动删除）。
3. 最后，我们删除分支本身。 

### 创建新地下城房间

这是地下城分支的核心任务。这是我们创造新房间的地方，我们还需要创建返回的出口以及（随机）生成前往地下城其他部分的出口。 

```{code-block}
:linenos: 
:emphasize-lines: 20,23,31,37,44,58,67,72,77
# 在 evadventure/dungeon.py 中 

from datetime import datetime
from random import shuffle

# ... 

class EvAdventureDungeonBranch(DefaultScript):

    # ...

    def new_room(self, from_exit):
        """
        创建一个新的地下城房间，通往提供的出口。

        参数：
            from_exit (Exit): 通往此新房间的出口。

        """
        self.last_updated = datetime.utcnow()
        # 确定旧房间的坐标并确定，
        # 新房间的坐标是什么
        source_location = from_exit.location
        x, y = source_location.attributes.get("xy_coords", default=(0, 0))
        dx, dy = _EXIT_GRID_SHIFT.get(from_exit.key, (0, 1))
        new_x, new_y = (x + dx, y + dy)

        # 地下城的深度作为当前难度水平的量度。 这是径向
        # 从 (0, 0)（入口）计算的距离。该分支还跟踪已达到的最高
        # 深度。
        depth = int(sqrt(new_x**2 + new_y**2))

        new_room = self.room_generator(self, depth, (new_x, new_y))

        self.xy_grid[(new_x, new_y)] = new_room

        # 始终创建返回到我们来的房间的出口
        back_exit_key = _EXIT_REVERSE_MAPPING.get(from_exit.key, "back")
        create.create_object(
            EvAdventureDungeonExit,
            key=back_exit_key,
            aliases=_EXIT_ALIASES.get(back_exit_key, ()),
            location=new_room,
            destination=from_exit.location,
            attributes=(
                (
                    "desc",
                    "一条黑暗通道。",
                ),
            ),
            # 我们默认允许回溯（也用于逃避）
            locks=("traverse: true()",),
        )

        # 确定此处应有的其他出口，如果有的话
        n_unexplored = len(self.unvisited_exits)

        if n_unexplored < self.max_unexplored_exits:
            # 我们有一个未探索出口的预算
            n_exits = min(self.max_new_exits_per_room, self.max_unexplored_exits)
            if n_exits > 1:
                n_exits = randint(1, n_exits)
            available_directions = [
                direction for direction in _AVAILABLE_DIRECTIONS if direction != back_exit_key
            ]
            # 随机化出口顺序
            shuffle(available_directions)
            for _ in range(n_exits):
                while available_directions:
                    # 获取随机方向并检查是否没有房间已存在
                    direction = available_directions.pop(0)
                    dx, dy = _EXIT_GRID_SHIFT[direction]
                    target_coord = (new_x + dx, new_y + dy)
                    if target_coord not in self.xy_grid and target_coord != (0, 0):
                        # 该方向没有房间（且不能返回起始房间）- 创建出口
                        self.create_out_exit(new_room, direction)
                        # 我们创建此目的以避免其他房间链接到此处，但不创建实际房间
                        self.xy_grid[target_coord] = None
                        break

        return new_room
```

有很多内容需要解析！ 

- **第 17 行**：我们将“最后更新时间”存储为当前 UTC 时间戳。正如我们在上面的删除部分讨论的那样，我们需要知道分支“闲置”了多长时间，帮助跟踪这一点。
- **第 20 行**：输入 `from_exit` 是一个出口对象（可能是 `EvAdventureDungeonExit`）。它位于“源”位置（我们开始移动的地方）。接下来的几行中，我们确定源位置的坐标以及移动至建议方向时将要到达的坐标。
- **第 28 行**：勾股定理！
- **第 30 行**：在这里，我们调用 `room_generator` 插件函数来获取新房间。
- **第 34 行**：我们始终创建一个返回出口，指向我们来的地方。
- **第 44 行**：我们可以将 `destination` 字段留空，但 Evennia 假设出口在显示房间等内容时必须设置 `destination` 字段。因此，为了避免更改房间的显示内容，这个值应设置为 _某个东西_。由于我们不想立即创建实际目的地，因此我们将其指向当前房间。也就是说，如果你可以通过这个出口的话，你将回到同一地方。我们将在下面用于标识未被探索的出口。
- **第 55 行**：我们只在“未探索”出口预算允许时创建新出口。
- **第 64 行**：在上一行中，我们创建了一个所有可能出口方向的新列表（排除必需的返回出口）。然后我们随机打乱这个列表的顺序。
- **第 69 行**：在这个循环中，我们从随机化列表中弹出第一个元素（所以这是一个随机方向）。在接下来的行中，我们检查该方向没有指向已存在的地下城房间，也不返回起始房间。如果一切正常，我们 Call 的出口创建方法在 **第 74 行**。

最终结果是一个新房间，至少有一个返回出口和 0 个或更多未探索的出口。

## 回到地下城出口类

现在我们有了工具，可以回到 `EvAdventureDungeonExit` 类，实现 `at_traverse` 方法。

```python
# 在 evadventure/dungeon.py 中 

# ... 

class EvAdventureDungeonExit(DefaultExit):

# ...
    def at_traverse(self, traversing_object, target_location, **kwargs):
        """
        在穿越时调用。如果目标位置尚未创建，将指向我们自己。
        它检查当前位置以获取正在使用的地下城分支。

        """
        dungeon_branch = self.location.db.dungeon_branch
        if target_location == self.location:
            # 目的地指向自己 - 创建新房间
            self.destination = target_location = dungeon_branch.new_room(
                self
            )
            dungeon_branch.register_exit_traversed(self)

        super().at_traverse(traversing_object, target_location, **kwargs)

```

我们获取 `EvAdventureDungeonBranch` 实例，检查当前出口是否指回当前房间。如果你阅读了上一节的第 44 行，你会注意到这是找到此出口是否未被探索的方式！

如果是，我们调用地下城分支的 `new_room` 来生成一个新房间，并将此出口的 `destination` 更改为该房间。我们还确保调用 `.register_exit_traversed`，以显示此出口现在是“已探索”。

我们还必须调用父类的 `at_traverse`，使用 `super()`，因为这正是将玩家移动到新创建的位置。

## 起始房间出口 

我们现在拥有了运行程序生成的地下城分支所需的所有部分。缺少的是起始房间，所有分支都从中产生。

如设计中所述，房间的出口将生成新分支，但在一段时间内，玩家都应该进入同一个分支。因此，我们需要一个特殊类型的出口，用于通往起始房间的出口。

```{code-block} python
:linenos:
:emphasize-lines: 12,19,22,32
# 在 evennia/dungeon.py 中

# ... 

class EvAdventureDungeonStartRoomExit(DefaultExit):

    def reset_exit(self):
        """
        刷新出口，以便下次穿越时创建一个新地下城分支。

        """
        self.destination = self.location

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """
        当穿越时，如果尚未分配分支，则创建一个新分支。

        """
        if target_location == self.location:
            # 为这个地下城分支制作一个全局分支脚本
            self.location.room_generator
            dungeon_branch = create.create_script(
                EvAdventureDungeonBranch,
                key=f"dungeon_branch_{self.key}_{datetime.utcnow()}",
                attributes=(
                    ("start_room", self.location),
                    ("room_generator", self.location.room_generator),
                ),
            )
            self.destination = target_location = dungeon_branch.new_room(self)
            # 进入时标记字符，以便我们稍后找到他们
            traversing_object.tags.add(dungeon_branch.key, category="dungeon_character")

        super().at_traverse(traversing_object, target_location, **kwargs)
```

这个出口具备创建新地下城分支所需的一切。

- **第 12 行**：它将出口与它连接的内容断开，并将其重新连接回当前房间（形成一个循环且无用的出口）。
- **第 19 行**：当有人穿越这个出口时，`at_traverse` 被调用。我们检测到上述特殊条件（目标等于当前位置）来确定此出口当前没有指向任何地方，我们应该创建一个新分支。
- **第 22 行**：我们创建了一个新的 `EvAdventureDungeonBranch`，并确保给它一个基于当前时间的唯一 `key`。我们还确保设置其起始属性。
- **第 32 行**：当玩家穿越这个出口时，角色会被标记为该地下城分支的适当标签。稍后可以用于删除机制。

## 实用脚本

在我们创建起始房间之前，我们需要两个最后的实用工具：

- 用于定期重置通往起始房间的出口（使它们创建新分支）。
- 用于清理老旧/闲置地下城分支的重复任务。

这两个脚本都将被期望在起始房间内创建，因此 `self.obj` 将是起始房间。

```python
# 在 evadventure/dungeon.py 中

from evennia.utils.utils import inherits_from

# ... 

class EvAdventureStartRoomResetter(DefaultScript):
    """
    简单的定时器脚本。引入在每个间隔时间内循环该房间出口的机会。

    """

    def at_script_creation(self):
        self.key = "evadventure_dungeon_startroom_resetter"

    def at_repeat(self):
        """
        每次脚本重复时调用。

        """
        room = self.obj
        for exi in room.exits:
            if inherits_from(exi, EvAdventureDungeonStartRoomExit) and random() < 0.5:
                exi.reset_exit()
```

这个脚本很简单—它遍历所有起始房间出口，并在 50% 的时间重置每个出口。

```python
# 在 evadventure/dungeon.py 中

# ... 

class EvAdventureDungeonBranchDeleter(DefaultScript):
    """
    清理脚本。经过一段时间，地下城分支会“坍塌”，迫使所有在其中的玩家回到起始房间。

    """

    # 在创建时设置的属性
    branch_max_life = AttributeProperty(0, autocreate=False)

    def at_script_creation(self):
        self.key = "evadventure_dungeon_branch_deleter"

    def at_repeat(self):
        """
        遍历所有地下城分支，查找哪些已经过期。

        """
        max_dt = timedelta(seconds=self.branch_max_life)
        max_allowed_date = datetime.utcnow() - max_dt

        for branch in EvAdventureDungeonBranch.objects.all():
            if branch.last_updated < max_allowed_date:
                # 分支太旧；告诉它自行清理并删除自己
                branch.delete()

```

此脚本检查所有分支，查看自上次更新以来（即，在其内部创建新房间）应该经过多久。如果时间太长，该分支将被删除（这将把所有玩家送回起始房间）。

## 起始房间

最后，我们需要一个起始房间的类。此房间需要手动创建，之后分支应该自动生成。

```python
# 在 evadventure/dungeon.py 中

# ... 

class EvAdventureDungeonStartRoom(EvAdventureDungeonRoom):

    recycle_time = 60 * 5  # 5 分钟
    branch_check_time = 60 * 60  # 1 小时
    branch_max_life = 60 * 60 * 24 * 7  # 1 周

    # 允许自定义房间生成器函数
    room_generator = AttributeProperty(lambda: room_generator, autocreate=False)

    def get_display_footer(self, looker, **kwargs):
        return (
            "|y你感觉到如果你想组成队伍，"
            "你必须都从这里选择相同的道路... 否则你们会很快分开。|n"
        )

    def at_object_creation(self):
        # 想在创建时设置脚本间隔时间，因此我们使用 create_script 以 obj=self
        # 而不是 self.scripts.add() 在这里
        create.create_script(
            EvAdventureStartRoomResetter, obj=self, interval=self.recycle_time, autostart=True
        )
        create.create_script(
            EvAdventureDungeonBranchDeleter,
            obj=self,
            interval=self.branch_check_time,
            autostart=True,
            attributes=(("branch_max_life", self.branch_max_life),),
        )

    def at_object_receive(self, obj, source_location, **kwargs):
        """
        确保在离开地下城分支时清除角色的地下城分支标签。

        """
        obj.tags.remove(category="dungeon_character")



```

这个房间需要做的就是设置我们创建的脚本，并确保在任何对象从该房间返回时清除任何地下城标签。所有其他操作则由出口和地下城分支处理。

## 测试 

```{sidebar}
在 `evennia/contrib/tutorials/` 中可找到单元测试文件示例，在 [evadventure/tests/test_dungeon.py](evennia.contrib.tutorials.evadventure.tests.test_dungeon) 中。
```

> 创建 `evadventure/tests/test_dungeon.py`。

测试程序地下城最好与单元测试和手动测试一起进行。

要手动测试，只需在游戏中执行：

```shell
> dig well:evadventure.dungeon.EvAdventureDungeonStartRoom = down,up
> down 
> create/drop north;n:evadventure.dungeon.EvAdventureDungeonStartRoomExit
> create/drop east;e:evadventure.dungeon.EvAdventureDungeonStartRoomExit
> create/drop south;s:evadventure.dungeon.EvAdventureDungeonStartRoomExit
> create/drop west;w:evadventure.dungeon.EvAdventureDungeonStartRoomExit
```
    
你现在应该能够通过某个出口走出去，开始探索地下城！ 一旦一切正常，这尤其有用。

要单元测试，你可以在代码中创建一个起始房间和出口，然后模拟角色穿越出口，确保结果符合预期。我们将这留给读者自行练习。

## 结论 

这只是稍微扫过程序生成的可能性，但通过相对简单的手段，可以为玩家创建一个无限延展的地下城进行探索。

值得注意的是，这仅涉及如何程序生成地下城的结构。它还尚未填充大量 _内容_。我们将在[第4部分](../Part4/Beginner-Tutorial-Part4-Overview.md)中回到这一点，届时将使用我们创建的代码来创建游戏内容。
