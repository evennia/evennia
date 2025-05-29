# 创建一个移动的火车

> TODO: 这应更新以适应最新的 Evennia 使用。

车辆是你可以进入并在你的游戏世界中移动的对象。在这里，我们将解释如何创建一个火车，但这同样适用于创建其他类型的车辆（汽车、飞机、船只、宇宙飞船、潜水艇，等等）。

Evennia 中的对象有一个有趣的属性：你可以将任何对象放入另一个对象中。这在房间中是最明显的：Evennia 中的房间就像任何其他游戏对象（不过房间通常不会在其他任何东西里面）。

我们的火车将类似于一个对象，其他对象可以进入。然后我们简单地移动火车，这样就能带着所有在里面的角色移动。

## 创建我们的火车对象

我们需要做的第一步是创建火车对象，包括一个新的类型类。为此，在 `mygame/typeclasses/train.py` 中创建一个新文件，包含以下内容：

```python
# 在 mygame/typeclasses/train.py 中

from evennia import DefaultObject

class TrainObject(DefaultObject):

    def at_object_creation(self):
        # 以后我们将在这里添加代码。
        pass
```

现在我们可以在游戏中创建我们的火车：

```plaintext
create/drop train:train.TrainObject
```

现在这只是一个不做任何事情的对象……但我们已经可以强制进入它和返回（假设我们在虚无中创建它）。

```plaintext
tel train 
tel limbo
```

## 进入和离开火车

使用如上所示的 `tel` 命令显然不是我们想要的。`@tel` 是一个管理员命令，因此普通玩家将无法进入火车！

使用 [出口](../Components/Objects.md#exits) 进入和离开火车也不是个好主意——出口（至少默认情况下）也是对象。它们指向特定的目标。如果我们在这个房间中放置一个出口指向火车，火车移动时它会仍留在这里（仍然像个魔法传送门一样指向火车！）。同样，如果我们在火车里放一个出口对象，它将始终指向这个房间，无论火车移动到何处。

当然，可以定义自定义出口类型来随火车移动或正确地改变它们的目标——但这看起来似乎是一个很麻烦的解决方案。

我们将要做的是创建一些新的 [命令](../Components/Commands.md)：一个用于进入火车，另一个用于离开它。这些将存储在 *火车对象上*，因此将对在里面或在火车同一房间的所有人可用。

让我们创建一个新的命令模块 `mygame/commands/train.py`：

```python
# mygame/commands/train.py

from evennia import Command, CmdSet

class CmdEnterTrain(Command):
    """
    进入火车
    
    用法:
      enter train

    这将对在同一位置的玩家可用
    允许他们登车。 
    """

    key = "enter train"

    def func(self):
        train = self.obj
        self.caller.msg("You board the train.")
        self.caller.move_to(train, move_type="board")


class CmdLeaveTrain(Command):
    """
    离开火车 
 
    用法:
      leave train

    这将对在 
    火车内部的每个人可用。它允许他们
    返回到火车当前的位置。 
    """

    key = "leave train"

    def func(self):
        train = self.obj
        parent = train.location
        self.caller.move_to(parent, move_type="disembark")


class CmdSetTrain(CmdSet):

    def at_cmdset_creation(self):
        self.add(CmdEnterTrain())
        self.add(CmdLeaveTrain())
```

请注意，虽然这看起来是很多文本，但大部分行都被文档占用了。

这些命令的工作方式相当简单：`CmdEnterTrain` 将玩家的位置移动到火车内部，而 `CmdLeaveTrain` 反之：将玩家移回火车的当前位置（返回到外面）。我们将它们堆叠在一个 [命令集](../Components/Command-Sets.md) `CmdSetTrain` 中，以便可以使用。

要使这些命令有效，我们需要将此命令集添加到我们的火车类型类中：

```python
# 文件 mygame/typeclasses/train.py

from commands.train import CmdSetTrain
from typeclasses.objects import Object

class TrainObject(Object):

    def at_object_creation(self):        
        self.cmdset.add_default(CmdSetTrain)
```

如果我们现在 `reload` 我们的游戏并重置我们的火车，这些命令应该可以正常工作，我们现在可以进入和离开火车：

```plaintext
reload
typeclass/force/reset train = train.TrainObject
enter train
leave train
```

注意使用 `typeclass` 命令时的开关：`/force` 选项是必要的，以将我们的对象分配为我们已经拥有的同一类型类。`/reset` 会重新触发类型类的 `at_object_creation()` 钩子（否则只在首次创建实例时调用）。
正如上面所示，当在我们的火车上调用该钩子时，新的命令集将被加载。

## 锁定命令

如果你玩了一段时间，你可能已经发现你可以在火车外部使用 `leave train`，在火车内部使用 `enter train`。这没有任何意义……所以让我们去修复它。我们需要告诉 Evennia，你不能在已经在里面时进入火车，或者在外面时离开火车。一种解决方案是使用 [锁](../Components/Locks.md)：我们将锁定命令，使其只能在玩家处于正确的位置时调用。

由于我们未在命令上设置 `lock` 属性，它默认是 `cmd:all()`。这意味着，只要他们在同一房间 _或_ 在火车内部，所有人都可以使用该命令。

首先，我们需要创建一个新的锁函数。Evennia 已经内置了很多锁函数，但没有一个可以用于锁定命令的特定情况。你可以在 `mygame/server/conf/lockfuncs.py` 中创建一个新条目：

```python
# 文件 mygame/server/conf/lockfuncs.py

def cmdinside(accessing_obj, accessed_obj, *args, **kwargs):
    """
    用法: cmdinside() 
    用于锁定命令，仅在访问的对象
    上定义，并且访问对象在里面的情况
    才允许访问。     
    """
    return accessed_obj.obj == accessing_obj.location
```

如果你不知道，Evennia 默认配置为将该模块中的所有函数用作锁函数（有一个设置变量指向它）。

我们新的锁函数 `cmdinside` 将用于命令。`accessed_obj` 是命令对象（在我们的例子中是 `CmdEnterTrain` 和 `CmdLeaveTrain`）——每个命令都有一个 `obj` 属性：这是命令“所在”的对象。由于我们已将这些命令添加到我们的火车对象，因此 `.obj` 属性将设置为火车对象。相反，`accessing_obj` 是调用该命令的对象：在我们的情况下是尝试进入或离开火车的角色。

这个函数做的就是检查玩家的位置是否与火车对象相同。如果相同，则表示玩家在火车里面。否则表示玩家在其他地方，检查将失败。

接下来的步骤是实际使用这个新锁函数来创建类型为 `cmd` 的锁：

```python
# 文件 commands/train.py
...
class CmdEnterTrain(Command):
    key = "enter train"
    locks = "cmd:not cmdinside()"
    # ...

class CmdLeaveTrain(Command):
    key = "leave train"
    locks = "cmd:cmdinside()"
    # ...
```

请注意，我们在这里使用 `not`，这样我们就可以使用相同的 `cmdinside` 来检查我们是否在里面和外面，而不必创建两个单独的锁函数。在 `@reload` 之后，我们的命令应该被适当地锁定，您应该只能在正确的位置使用它们。

> 注意：如果你以超级用户（用户 `#1`）身份登录，那么这个锁将不起作用：超级用户忽略锁函数。要使用此功能，你需要先 `@quell`。

## 使我们的火车移动

现在我们可以正确进入和离开火车，接下来就该让它移动了。我们需要考虑不同的事情：

* 谁可以控制你的车辆？第一个进入它的玩家，只有拥有某种“驾驶”技能的玩家，自动？
* 它应该到哪里去？玩家可以驾驶车辆去其他地方，还是它总是遵循同一路线？

对于我们的示例火车，我们将选择通过预定义路线（轨道）的自动移动。火车将在路线的起点和终点稍作停留，以便玩家能够上下车。

去创建一些房间作为我们的火车。使用 `xe` 命令列出沿途的房间 ID。

```plaintext
> dig/tel South station
> ex              # 记下车站的 id
> tunnel/tel n = Following a railroad
> ex              # 记下轨道的 id
> tunnel/tel n = Following a railroad
> ...
> tunnel/tel n = North Station
```

将火车放到轨道上：

```plaintext
tel south station
tel train = here
```

接下来我们将告诉火车如何移动和选择哪条路径。

```python
# 文件类型类 train.py

from evennia import DefaultObject, search_object

from commands.train import CmdSetTrain

class TrainObject(DefaultObject):

    def at_object_creation(self):
        self.cmdset.add_default(CmdSetTrain)
        self.db.driving = False
        # 我们火车行驶的方向（1为前进，-1为后退）
        self.db.direction = 1
        # 我们火车将经过的房间（根据你的游戏进行更改）
        self.db.rooms = ["#2", "#47", "#50", "#53", "#56", "#59"]

    def start_driving(self):
        self.db.driving = True

    def stop_driving(self):
        self.db.driving = False

    def goto_next_room(self):
        currentroom = self.location.dbref
        idx = self.db.rooms.index(currentroom) + self.db.direction

        if idx < 0 or idx >= len(self.db.rooms):
            # 我们到达了路径的尽头
            self.stop_driving()
            # 反转火车的方向
            self.db.direction *= -1
        else:
            roomref = self.db.rooms[idx]
            room = search_object(roomref)[0]
            self.move_to(room)
            self.msg_contents(f"The train is moving forward to {room.name}.")
```

在这里我们添加了很多代码。由于我们更改了 `at_object_creation` 以添加变量，因此我们需要像之前那样重置我们的火车对象（使用 `@typeclass/force/reset` 命令）。

我们现在跟踪几个不同的事情：火车是移动还是静止，火车朝哪个方向前进，以及火车将经过哪些房间。

我们还添加了一些方法：一个开始移动火车，另一个停止，第三个则实际上将火车移动到列表中的下一个房间。或者在到达最后一站时让其停止行驶。

让我们试试，通过 `py` 调用新的火车功能：

```plaintext
> reload
> typeclass/force/reset train = train.TrainObject
> enter train
> py here.goto_next_room()
```

你应该看到火车沿着铁轨向前移动一步。

## 添加脚本

如果我们想全权控制火车，我们现在可以仅仅添加一个命令，在需要时让它沿着轨道前进。但我们希望火车能够自动移动，而不必手动调用 `goto_next_room` 方法。

为此，我们将创建两个 [脚本](../Components/Scripts.md)：一个脚本在火车停靠在站台时运行，负责在一段时间后再次启动火车。另一个脚本将处理行驶。

让我们在 `mygame/typeclasses/trainscript.py` 中创建一个新文件：

```python
# 文件 mygame/typeclasses/trainscript.py

from evennia import DefaultScript

class TrainStoppedScript(DefaultScript):

    def at_script_creation(self):
        self.key = "trainstopped"
        self.interval = 30
        self.persistent = True
        self.repeats = 1
        self.start_delay = True

    def at_repeat(self):
        self.obj.start_driving()        

    def at_stop(self):
        self.obj.scripts.add(TrainDrivingScript)


class TrainDrivingScript(DefaultScript):

    def at_script_creation(self):
        self.key = "traindriving"
        self.interval = 1
        self.persistent = True

    def is_valid(self):
        return self.obj.db.driving

    def at_repeat(self):
        if not self.obj.db.driving:
            self.stop()
        else:
            self.obj.goto_next_room()

    def at_stop(self):
        self.obj.scripts.add(TrainStoppedScript)
```

这些脚本作为状态系统工作：当火车停止时，它等待 30 秒，然后再次启动。当火车移动时，它每秒移动到下一个房间。火车始终处于这两个状态之一——两个脚本在完成后管理添加另一个脚本。

最后一步是将停止状态脚本链接到我们的火车，重新加载游戏并再次重置我们的火车，这样我们就可以随意骑乘了！

```python
# 文件 mygame/typeclasses/train.py

from typeclasses.trainscript import TrainStoppedScript

class TrainObject(DefaultObject):

    def at_object_creation(self):
        # ...
        self.scripts.add(TrainStoppedScript)
```

现在，只需执行以下操作：

```plaintext
> reload
> typeclass/force/reset train = train.TrainObject
> enter train

# 输出:
< The train is moving forward to Following a railroad.
< The train is moving forward to Following a railroad.
< The train is moving forward to Following a railroad.
...
< The train is moving forward to Following a railroad.
< The train is moving forward to North station.

leave train
```

我们的火车将在每个末端站停留 30 秒，然后转身返回另一端。

## 扩展功能

这列火车非常基础，仍然存在一些缺陷。还有一些事情需要完成：

* 让它看起来像一列火车。
* 确保在行驶过程中无法上下车。这可以通过让进入/离开命令检查火车是否在移动来实现，然后才允许调用者继续操作。
* 添加车长命令，能够覆盖自动启动/停止。
* 允许在起点和终点站之间停靠更多站。
* 创建一条铁路轨道，而不是在火车对象中硬编码房间。这可以是一个自定义 [出口](../Components/Objects.md#exits)，仅火车可通过。火车将跟随轨道。有些轨道部分可以拆分到两个不同的房间，玩家可以切换要前往的房间。
* 创建另一种类型的车辆！
