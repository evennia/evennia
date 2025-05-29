# OnDemandHandler

此处理程序提供了实现按需状态更改的帮助。按需意味着状态不会被计算，直到玩家 _实际查看_ 它为止。在此之前，什么都不会发生。这是处理系统的最节省计算资源的方式，你应尽可能考虑使用这种系统风格。

例如，考虑一个园艺系统。玩家进入一个房间并种植一颗种子。经过一段时间后，该植物将经历一系列阶段；它将从“幼苗”变为“芽”，再到“开花”，然后“枯萎”，最终“死亡”。

现在，你 _可以_ 使用 `utils.delay` 跟踪每个阶段，或使用 [TickerHandler](./TickerHandler.md) 来定时更新花朵。你甚至可以在花朵上使用 [Script](./Scripts.md)。这将按以下方式工作：

1. 计时器/任务/脚本会自动定期触发，以更新植物的各个阶段。
2. 每当玩家进入房间时，花朵的状态已经更新，他们只需读取状态。

这可以正常工作，但如果没有人回到那个房间，那就是很多没人会看到的更新。虽然对于单个玩家来说可能没什么大不了的，但如果你在数千个房间中都有花朵，并且都在独立生长呢？或者某些更复杂的系统需要在每次状态更改时进行计算。你应该避免在对玩家没有任何额外价值的事情上花费计算资源。

使用按需风格，花朵将按以下方式工作：

1. 当玩家种下种子时，我们记录 _当前时间戳_ ——植物开始生长的时间。我们将其存储在 `OnDemandHandler`（如下）中。
2. 当玩家进入房间和/或查看植物时（或代码系统需要知道植物的状态），_然后_（仅在此时）我们检查 _当前时间_ 以确定花朵现在应该处于的状态（`OnDemandHandler` 为我们进行记录）。关键是 _直到我们检查_，花朵对象完全处于非活动状态，不使用任何计算资源。

## 使用 OnDemandHandler 的开花植物

此处理程序可以在 `evennia.ON_DEMAND_HANDLER` 中找到。它旨在集成到你的其他代码中。以下是一个花朵在 12 小时内经历其生命周期阶段的示例。

```python
# 例如在 mygame/typeclasses/objects.py 中

from evennia import ON_DEMAND_HANDLER 

# ... 

class Flower(Object): 

    def at_object_creation(self):

        minute = 60
        hour = minute * 60

        ON_DEMAND_HANDLER.add(
            self,
            category="plantgrowth"
            stages={
                0: "seedling",
                10 * minute: "sprout",
                5 * hour: "flowering",
                10 * hour: "wilting",
                12 * hour: "dead"
            })

    def at_desc(self, looker):
        """
        每当有人查看此对象时调用
        """ 
        stage = ON_DEMAND_HANDLER.get_state(self, category="plantgrowth")

        match stage: 
            case "seedling": 
                return "没有什么可看的。什么都还没长出来。"
            case "sprout": 
                return "一个小而精致的芽已经冒出来了！"
            case "flowering": 
                return f"一朵美丽的 {self.name}！"
            case "wilting": 
                return f"这朵 {self.name} 曾经有过更好的日子。"
            case "dead": 
                # 它已经死了。停止并删除 
                ON_DEMAND_HANDLER.remove(self, category="plantgrowth")
                self.delete()
```

`get_state(key, category=None, **kwargs)` 方法用于获取当前阶段。`get_dt(key, category=None, **kwargs)` 方法则检索当前经过的时间。

你现在可以创建玫瑰，并且它只会在你实际查看它时才确定其状态。它将在 10 分钟（游戏中的实际时间）内保持幼苗状态，然后发芽。在 12 小时内它将再次死亡。

如果你在游戏中有一个 `harvest` 命令，你也可以让它检查开花阶段，并根据你是否在正确的时间采摘玫瑰给出不同的结果。

按需处理程序的任务在重新加载后仍然有效，并将正确考虑停机时间。

## 更多使用示例

[OnDemandHandler API](evennia.scripts.ondemandhandler.OnDemandHandler) 详细描述了如何使用处理程序。虽然它可以作为 `evennia.ON_DEMAND_HANDLER` 使用，但其代码位于 `evennia.scripts.ondemandhandler.py` 中。

```python
from evennia import ON_DEMAND_HANDLER 

ON_DEMAND_HANDLER.add("key", category=None, stages=None)
time_passed = ON_DEMAND_HANDLER.get_dt("key", category=None)
current_state = ON_DEMAND_HANDLER.get_stage("key", category=None)

# 移除内容 
ON_DEMAND_HANDLER.remove("key", category=None)
ON_DEMAND_HANDLER.clear(category="category")  # 清除所有具有该类别的内容
```

```{sidebar} 并非所有阶段都会触发！
这很重要。如果没有人检查花朵，直到它已经枯萎，它将简单地 _跳过_ 所有先前的阶段，直接进入“枯萎”阶段。因此，不要为某个阶段编写假设先前阶段已经对对象进行了特定更改的代码——这些更改可能没有发生，因为这些阶段可能已被完全跳过！
```

- `key` 可以是字符串，也可以是 typeclassed 对象（将使用其字符串表示形式，通常包括其 `#dbref`）。你还可以传递一个 `callable`——这将被调用而不带参数，并期望返回一个用于 `key` 的字符串。最后，你还可以传递 [OnDemandTask](evennia.scripts.ondemandhandler.OnDemandTask) 实体——这些是处理程序在后台用于表示每个任务的对象。
- `category` 允许你进一步分类你的按需处理程序任务，以确保它们是唯一的。由于处理程序是全局的，你需要确保 `key` + `category` 是唯一的。虽然 `category` 是可选的，但如果你使用它，你还必须使用它来检索你的状态。
- `stages` 是一个 `dict` `{dt: statename}` 或 `{dt: (statename, callable)}`，表示从 _任务开始_ 到该阶段开始所需的时间（以秒为单位）。在上面的花朵示例中，直到 `wilting` 状态开始才经过 10 小时。如果包含一个可调用对象，它将在第一次达到该阶段时触发。此可调用对象将当前的 `OnDemandTask` 和 `**kwargs` 作为参数；关键字是从 `get_stages/dt` 方法传递的。[参见下文](#stage-callables) 了解有关允许的可调用对象的信息。拥有 `stages` 是可选的——有时你只想知道经过了多少时间。
- `.get_dt()` - 获取自任务开始以来的当前时间（以秒为单位）。这是一个 `float`。
- `.get_stage()` - 获取当前状态名称，例如“flowering”或“seedling”。如果你没有指定任何 `stages`，这将返回 `None`，你需要自己解释 `dt` 以确定你所处的状态。

在后台，处理程序使用 [OnDemandTask](evennia.scripts.ondemandhandler.OnDemandTask) 对象。有时直接创建任务并将其批量传递给处理程序是很实用的：

```python
from evennia import ON_DEMAND_HANDLER, OnDemandTask 

task1 = OnDemandTask("key1", {0: "state1", 100: ("state2", my_callable)})
task2 = OnDemandTask("key2", category="state-category")

# 批量启动按需任务
ON_DEMAND_HANDLER.batch_add(task1, task2)

# 稍后获取任务 
task1 = ON_DEMAND_HANDLER.get("key1")
task2 = ON_DEMAND_HANDLER.get("key1", category="state-category")

# 批量停用你可用的任务
ON_DEMAND_HANDLER.batch_remove(task1, task2)
```

### 阶段可调用对象

如果你将一个或多个 `stages` 字典键定义为 `{dt: (statename, callable)}`，则该可调用对象将在第一次检查该阶段时被调用。此“阶段可调用对象”有一些要求：

- 阶段可调用对象必须 [可以被 pickle](https://docs.python.org/3/library/pickle.html#pickle-picklable)，因为它将被保存到数据库中。这基本上意味着你的可调用对象需要是一个独立的函数或一个用 `@staticmethod` 装饰的方法。你将无法直接从这样的函数或方法访问对象实例作为 `self`——你需要显式传递它。
- 可调用对象必须始终将 `task` 作为其第一个元素。这是触发此可调用对象的 `OnDemandTask` 对象。
- 它可以选择性地接受 `**kwargs`。这将从你调用 `get_dt` 或 `get_stages` 时传递下来。

以下是一个示例：

```python
from evennia DefaultObject, ON_DEMAND_HANDLER

def mycallable(task, **kwargs)
    # 此函数在类之外，可以很好地被 pickle
    obj = kwargs.get("obj")
    # 对对象执行某些操作

class SomeObject(DefaultObject):

    def at_object_creation(self):
        ON_DEMAND_HANDLER.add(
            "key1", 
            stages={0: "new", 10: ("old", mycallable)}
        )

    def do_something(self):
        # 将 obj=self 传入处理程序；如果我们处于“old”阶段，将传入 mycallable。
        state = ON_DEMAND_HANDLER.get_state("key1", obj=self)
```

在上面，`obj=self` 将在我们达到“old”状态时传入 `mycallable`。如果我们不在“old”阶段，额外的 kwargs 将无处可去。这样可以让函数意识到调用它的对象，同时仍然可以被 pickle。你也可以通过这种方式将任何其他信息传递给可调用对象。

> 如果你不想处理可调用对象的复杂性，你也可以只读取当前阶段，并在处理程序之外执行所有逻辑。这通常更容易阅读和维护。

### 重复循环

通常，当一系列 `stages` 循环完毕后，任务将无限期地停留在最后一个阶段。

`evennia.OnDemandTask.stagefunc_loop` 是一个包含的静态方法阶段可调用对象，你可以用来使任务循环。以下是如何使用它的示例：

```python
from evennia import ON_DEMAND_HANDLER, OnDemandTask 

ON_DEMAND_HANDLER.add(
    "trap_state", 
    stages={
        0: "harmless",
        50: "solvable",
        100: "primed",
        200: "deadly",
        250: ("_reset", OnDemandTask.stagefunc_loop)
    }
)
```

这是一个陷阱状态，根据时间循环其状态。请注意，循环帮助器可调用对象将 _立即_ 将循环重置回第一个阶段，因此最后一个阶段对玩家/游戏系统将不可见。因此，最好（如果可选）将其命名为 `_*`，以记住这是一个“虚拟”阶段。在上面的示例中，“deadly”状态将直接循环到“harmless”。

`OnDemandTask` 任务实例有一个 `.iterations` 变量，每次循环时都会增加 1。

如果状态长时间未被检查，循环函数将正确更新任务上本应使用的 `.iterations` 属性，并找出当前在循环中的位置。

### 来回弹跳

`evennia.OnDemandTask.stagefunc_bounce` 是一个包含的静态方法可调用对象，你可以用来“弹跳”阶段序列。也就是说，它将循环到循环的末尾，然后反向并以相反的顺序循环序列，保持每个阶段之间的时间间隔相同。

要使其无限期重复，你需要在列表的两端放置这些可调用对象：

```python 
from evennia import ON_DEMAND_HANDLER, OnDemandTask 

ON_DEMAND_HANDLER.add(
    "cycling reactor",
    "nuclear",
    stages={
        0: ("cold", OnDemandTask.stagefunc_bounce),
        150: "luke warm",
        300: "warm", 
        450: "hot"
        600: ("HOT!", OnDemandTask.stagefunc_bounce)    
    }
)
```

这将循环

```
cold -> luke warm -> warm -> hot -> HOT!
```

然后反向返回（一次又一次）：

```
HOT! -> hot -> warm -> luke warm -> cold
```

与 `stagefunc_loop` 可调用对象不同，弹跳可调用对象 _将_ 在第一个和最后一个阶段可见，直到它更改为序列中的下一个阶段。`OnDemandTask` 实例有一个 `.iterations` 属性，每次序列反转时都会增加 1。

如果状态长时间未被检查，弹跳函数将正确更新 `.iterations` 属性到在那段时间内本应完成的迭代次数，并找出当前在循环中的位置。

## 什么时候不适合按需处理？

如果你用心去做，你可能可以让游戏的大部分内容按需进行。玩家不会察觉。

只有一种情况按需处理不起作用，那就是如果玩家应该在 _没有提供任何输入_ 的情况下被告知某些事情。

如果玩家必须运行 `check health` 命令来查看他们的健康状况，这可以按需进行。同样，提示可以设置为每次移动时更新。但如果你希望一个空闲的玩家突然收到一条消息说“你感到饿了”或者看到某个 HP 计量器在站立不动时也在增加，那么某种计时器/滴答器将是必要的，以推动事情的发展。

然而请记住，在文本媒介中（尤其是传统的逐行 MUD 客户端），你能向玩家推送的垃圾信息是有限的，过多的信息会让他们感到不知所措。
