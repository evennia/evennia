# TickerHandler

在动态 MUD 中实现“tickers”或称“心跳”是一种方法。Ticker 是一个定时器，会在给定的时间间隔触发（“tick”）。Tick 会触发各种游戏系统的更新。

在其他 MUD 代码库中，tickers 非常常见，甚至是不可避免的。某些代码库甚至硬编码地依赖于全局“tick”的概念。而 Evennia 没有这样的概念——是否使用 tickers 完全取决于你的游戏需求和要求。“ticker 配方”只是推动齿轮运转的一种方式。

管理时间流动的最细粒度的方法是使用 [utils.delay](evennia.utils.utils.delay)（使用 [TaskHandler](evennia.scripts.taskhandler.TaskHandler)）。另一种方法是使用 [Scripts](./Scripts.md) 的时间重复功能。这些工具在单个对象上操作。

然而，许多类型的操作（天气是经典示例）是在多个对象上以相同方式在常规间隔进行的，为此，为每个这样的对象设置单独的延迟/脚本效率不高。

解决方法是使用具有“订阅模型”的 ticker——让对象注册以在相同间隔触发，当不再需要更新时取消订阅。这意味着时间保持机制只为所有对象设置一次，使订阅/取消订阅更快。

Evennia 提供了一种优化的订阅模型实现——*TickerHandler*。这是一个可以从 [evennia.TICKER_HANDLER](evennia.utils.tickerhandler.TickerHandler) 访问的全局单例处理程序。你可以将任何 *callable*（函数或更常见的，数据库对象上的方法）分配给此处理程序。TickerHandler 将在你指定的间隔调用此 callable，并使用你在添加时提供的参数。这将持续到 callable 从 ticker 取消订阅。处理程序在重启后仍然存在，并且在资源使用上进行了高度优化。

## 使用方法

以下是导入 `TICKER_HANDLER` 并使用它的示例：

```python
# 我们假设 obj 在自身上定义了一个钩子 "at_tick"
from evennia import TICKER_HANDLER as tickerhandler    

tickerhandler.add(20, obj.at_tick)
```

就是这样——从现在开始，`obj.at_tick()` 将每 20 秒被调用一次。

```{important}
你提供给 `TickerHandler.add` 的所有内容最终都需要被 pickled 以保存到数据库中——即使你使用 `persistent=False`。大多数情况下，处理程序将正确存储数据库对象，但对 TickerHandler 可以存储的内容的限制与 [Attributes](./Attributes.md) 相同。
```

你也可以导入一个函数并对其进行 tick：

```python
from evennia import TICKER_HANDLER as tickerhandler
from mymodule import myfunc

tickerhandler.add(30, myfunc)
```

移除（停止）ticker 的操作如预期：

```python
tickerhandler.remove(20, obj.at_tick)
tickerhandler.remove(30, myfunc) 
```

请注意，你还必须提供 `interval` 以识别要移除的订阅。这是因为 TickerHandler 维护了一组 tickers，并且给定的 callable 可以订阅在任意数量的不同间隔被 tick。

`tickerhandler.add` 方法的完整定义是：

```python
tickerhandler.add(interval, callback, 
                  idstring="", persistent=True, *args, **kwargs)
```

这里的 `*args` 和 `**kwargs` 将在每个 `interval` 秒传递给 `callback`。如果 `persistent` 为 `False`，则在 _服务器关闭_ 时此订阅将被清除（它仍然可以在正常重载中存活）。

Tickers 通过对 callable 本身、ticker 间隔、`persistent` 标志和 `idstring`（如果未显式给出则为空字符串）进行键控来识别和存储。

由于参数不包含在 ticker 的识别中，因此 `idstring` 必须用于在相同间隔多次触发特定回调但使用不同参数：

```python
tickerhandler.add(10, obj.update, "ticker1", True, 1, 2, 3)
tickerhandler.add(10, obj.update, "ticker2", True, 4, 5)
```

> 请注意，当我们想要在 ticker 处理程序中向回调发送参数时，我们需要在之前指定 `idstring` 和 `persistent`，除非我们以关键字形式调用参数，这通常更具可读性：

```python
tickerhandler.add(10, obj.update, caller=self, value=118)
```

如果你以完全相同的 callback、interval 和 idstring 组合添加一个 ticker，它将覆盖现有的 ticker。这种识别对于以后移除（停止）订阅也是至关重要的：

```python
tickerhandler.remove(10, obj.update, idstring="ticker1")
tickerhandler.remove(10, obj.update, idstring="ticker2")
```

`callable` 可以是任何形式，只要它接受你在 `TickerHandler.add` 中给定的参数。

在测试时，你可以使用 `tickerhandler.clear()` 停止整个游戏中的所有 tickers。你还可以使用 `tickerhandler.all()` 查看当前订阅的对象。

有关使用 TickerHandler 的示例，请参阅 [Weather Tutorial](../Howtos/Tutorial-Weather-Effects.md)。

### 何时*不*使用 TickerHandler

使用 TickerHandler 可能听起来很有用，但重要的是要考虑何时不使用它。即使你习惯于在其他代码库中习惯性地依赖 tickers 来处理所有事情，也要停下来思考你真正需要它的地方。关键点是：

> 你*永远不应该*使用 ticker 来捕捉*变化*。

想一想——你可能需要每秒运行一次 ticker 才能足够快地对变化做出反应。很可能在给定时刻没有任何变化。因此你是在进行无意义的调用（因为跳过调用与进行调用的结果相同）。确保没有变化可能甚至在计算上是昂贵的，这取决于系统的复杂性。更不用说你可能需要在 *数据库中的每个对象* 上运行检查。每秒一次。只是为了维持现状……

与其反复检查以防万一发生变化，不如考虑一种更积极的方法。你能否实现一个不常变化的系统，让它*自己*报告状态变化？如果你能“按需”做事，这几乎总是更便宜/更高效。Evennia 本身使用钩子方法正是出于这个原因。

因此，如果你考虑一个会非常频繁触发但你预计 99% 的时间都没有效果的 ticker，请考虑以其他方式处理这些事情。自我报告的按需解决方案通常对于快速更新的属性也更便宜。还要记住，某些事情可能不需要更新，直到有人实际检查或使用它们——在那一刻之前发生的任何临时变化都是计算时间的无谓浪费。

需要 ticker 的主要原因是当你希望在没有其他输入的情况下同时对多个对象进行操作时。
