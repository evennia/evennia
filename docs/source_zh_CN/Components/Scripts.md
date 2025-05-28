# 脚本

[脚本 API 参考](evennia.scripts.scripts)

*脚本* 是角色外的 [对象](./Objects.md) 的兄弟。脚本的灵活性极高，以至于“脚本”这个名字有些局限——但我们总得给它们起个名字。根据用途不同，其他可能的名字有 `OOBObjects`、`StorageContainers` 或 `TimerObjects`。

如果你曾考虑创建一个 `None` 位置的 [对象](./Objects.md) 来存储一些游戏数据，你实际上应该使用脚本。

- 脚本是完整的 [Typeclassed](./Typeclasses.md) 实体——它们有 [属性](./Attributes.md)，并可以以相同的方式进行修改。但它们没有 _游戏内存在_，因此没有像 [对象](./Objects.md) 那样的位置或命令执行，也没有像 [账户](./Accounts.md) 那样与特定玩家/会话的连接。这意味着它们非常适合作为游戏 _系统_ 的数据库存储后端：存储当前经济状态、谁参与了当前战斗、跟踪正在进行的交易等。它们是持久系统处理器的绝佳选择。
- 脚本有一个可选的 _计时器组件_。这意味着你可以设置脚本在特定间隔内触发 `at_repeat` 钩子。计时器可以根据需要独立于脚本的其他部分进行控制。此组件是可选的，并且可以与 Evennia 中的其他计时功能互补，例如 [evennia.utils.delay](evennia.utils.utils.delay) 和 [evennia.utils.repeat](evennia.utils.utils.repeat)。
- 脚本可以通过例如 `obj.scripts.add/remove` 附加到对象和账户。在脚本中，你可以通过 `self.obj` 或 `self.account` 访问对象/账户。这可以用于动态扩展其他类型类，也可以使用计时器组件以各种方式影响父对象。出于历史原因，没有附加到对象的脚本被称为 _全局_ 脚本。

```{versionchanged} 1.0
在以前的 Evennia 版本中，停止脚本的计时器也意味着删除脚本对象。
从这个版本开始，计时器可以单独启动/停止，必须显式调用 `.delete()` 来删除脚本。
```

## 使用脚本

在默认的 cmdset 中有两个主要命令控制脚本：

`addscript` 命令用于将脚本附加到现有对象：

```
> addscript obj = bodyfunctions.BodyFunctions
```

`scripts` 命令用于查看所有脚本并对其执行操作：

```
> scripts
> scripts/stop bodyfunctions.BodyFunctions
> scripts/start #244
> scripts/pause #11
> scripts/delete #566
```

```{versionchanged} 1.0
`addscript` 命令以前只是 `script`，这很容易与 `scripts` 混淆。
```

### 代码示例

以下是一些在代码中使用脚本的示例（更多详细信息将在后续部分中介绍）。

创建一个新脚本：

```python
new_script = evennia.create_script(key="myscript", typeclass=...)
```

创建带有计时器组件的脚本：

```python
# 注意，这将调用 `timed_script.at_repeat`，默认情况下为空
timed_script = evennia.create_script(key="Timed script",
                                     interval=34,  # 秒，<=0 表示关闭
                                     start_delay=True,  # 在首次调用前等待间隔
                                     autostart=True)  # 启动计时器（否则需要 .start()）

# 操作脚本的计时器
timed_script.stop()
timed_script.start()
timed_script.pause()
timed_script.unpause()
```

将脚本附加到另一个对象：

```python
myobj.scripts.add(new_script)
myobj.scripts.add(evennia.DefaultScript)
all_scripts_on_obj = myobj.scripts.all()
```

以各种方式搜索/查找脚本：

```python
# 常规搜索（这始终是一个列表，即使只有一个匹配项）
list_of_myscripts = evennia.search_script("myscript")

# 通过 Evennia 的 GLOBAL_SCRIPTS 容器搜索（仅基于脚本的 key）
from evennia import GLOBAL_SCRIPTS

myscript = GLOBAL_SCRIPTS.myscript
GLOBAL_SCRIPTS.get("Timed script").db.foo = "bar"
```

删除脚本（这也将停止其计时器）：

```python
new_script.delete()
timed_script.delete()
```

### 定义新脚本

脚本定义为一个类，并以与其他 [类型类化](./Typeclasses.md) 实体相同的方式创建。父类是 `evennia.DefaultScript`。

#### 简单存储脚本

在 `mygame/typeclasses/scripts.py` 中已经设置了一个空的 `Script` 类。你可以将其用作自己的脚本的基础。

```python
# 在 mygame/typeclasses/scripts.py 中

from evennia import DefaultScript

class Script(DefaultScript):
    # 所有脚本的公共部分在此处

class MyScript(Script):
    def at_script_creation(self):
        """首次创建脚本时调用"""
        self.key = "myscript"
        self.db.foo = "bar"
```

创建后，这个简单的脚本可以作为全局存储：

```python
evennia.create_script('typeclasses.scripts.MyScript')

# 从其他地方

myscript = evennia.search_script("myscript").first()
bar = myscript.db.foo
myscript.db.something_else = 1000
```

请注意，如果你给 `create_script` 提供关键字参数，你可以覆盖在 `at_script_creation` 中设置的值：

```python
evennia.create_script('typeclasses.scripts.MyScript', key="another name",
                      attributes=[("foo", "bar-alternative")])
```

有关创建和查找脚本的更多选项，请参阅 [create_script](evennia.utils.create.create_script) 和 [search_script](evennia.utils.search.search_script) API 文档。

#### 定时脚本

可以在脚本上设置多个属性来控制其计时器组件。

```python
# 在 mygame/typeclasses/scripts.py 中

class TimerScript(Script):

    def at_script_creation(self):
        self.key = "myscript"
        self.desc = "An example script"
        self.interval = 60  # 每分钟重复一次

    def at_repeat(self):
        # 每分钟执行的操作
```

此示例将在每分钟调用 `at_repeat`。`create_script` 函数默认有一个 `autostart=True` 关键字，这意味着脚本的计时器组件将自动启动。否则必须单独调用 `.start()`。

支持的属性有：

- `key` (str)：脚本的名称。这使得以后更容易搜索它。如果它是附加到另一个对象的脚本，也可以获取该对象的所有脚本并通过这种方式获取脚本。
- `desc` (str)：注意，不是 `.db.desc`！这是脚本上的一个数据库字段，用于在脚本列表中显示以帮助识别作用。
- `interval` (int)：计时器每次“滴答”的时间间隔（以秒为单位）。请注意，在文本游戏中使用亚秒级计时器通常是不好的做法——玩家无法欣赏这种精度（如果打印出来，只会刷屏）。对于计算，你几乎总是可以按需进行，或者以更慢的间隔进行，而玩家不会察觉。
- `start_delay` (bool)：计时器是否应立即启动，或先等待 `interval` 秒。
- `repeats` (int)：如果 >0，计时器将仅运行此次数，然后停止。否则，重复次数为无限。如果设置为 1，脚本将模拟 `delay` 操作。
- `persistent` (bool)：默认为 `True`，表示计时器将在服务器重载/重启后继续存在。如果不是，重载后计时器将以停止状态返回。设置为 `False` 不会删除脚本对象本身（使用 `.delete()` 来实现）。

计时器组件通过脚本类上的方法进行控制：

- `.at_repeat()` - 当计时器处于活动状态时，每 `interval` 秒调用此方法。
- `.is_valid()` - 计时器在 `at_repeat()` 之前调用此方法。如果返回 `False`，计时器将立即停止。
- `.start()` - 启动/更新计时器。如果给定关键字参数，可以用于动态更改 `interval`、`start_delay` 等。这将调用 `.at_start()` 钩子。假设计时器先前未停止，这也将在服务器重载后调用。
- `.update()` - `.start` 的旧别名。
- `.stop()`  - 停止并重置计时器。这将调用 `.at_stop()` 钩子。
- `.pause()` - 暂停计时器，存储其当前位置。这将调用 `.at_pause(manual_pause=True)` 钩子。这也将在服务器重载/重启时调用，此时 `manual_pause` 将为 `False`。
- `.unpause()` - 取消暂停先前暂停的脚本。这将调用 `at_start` 钩子。
- `.time_until_next_repeat()` - 获取计时器下次触发的时间。
- `.remaining_repeats()` - 获取剩余的重复次数，或 `None` 如果重复次数为无限。
- `.reset_callcount()` - 这将重置重复计数器，从0开始。仅在 `repeats>0` 时有用。
- `.force_repeat()` - 提前强制立即调用 `at_repeat`。这样做会重置倒计时，因此下次调用将在 `interval` 秒后再次发生。

### 脚本计时器与 delay/repeat

如果唯一目标是获得重复/延迟效果，通常应优先考虑 [evennia.utils.delay](evennia.utils.utils.delay) 和 [evennia.utils.repeat](evennia.utils.utils.repeat) 函数。脚本在动态创建/删除时要“重”得多。实际上，对于制作单个延迟调用（`script.repeats==1`），`utils.delay` 调用可能始终是更好的选择。

对于重复任务，`utils.repeat` 优化用于快速重复大量对象。它在底层使用 TickerHandler。其基于订阅的模型使得启动/停止对象的重复操作非常高效。其副作用是，所有设置为在给定间隔滴答的对象将 _同时_ 执行。这在游戏中可能会显得奇怪，具体取决于情况。相比之下，脚本使用自己的滴答器，将独立于所有其他脚本的滴答器操作。

还值得注意的是，一旦脚本对象 _已经创建_，启动/停止/暂停/取消暂停计时器的开销非常小。脚本的暂停/取消暂停和更新方法还提供比使用 `utils.delays/repeat` 更精细的控制。

### 附加到另一个对象的脚本

脚本可以附加到 [账户](./Accounts.md) 或（更常见）[对象](./Objects.md)。
如果是这样，“父对象”将作为 `.obj` 或 `.account` 提供给脚本。

```python
# mygame/typeclasses/scripts.py
# Script 类定义在此模块的顶部

import random

class Weather(Script):
    """
    一个计时器脚本，显示天气信息。旨在附加到房间。
    """
    def at_script_creation(self):
        self.key = "weather_script"
        self.desc = "Gives random weather messages."
        self.interval = 60 * 5  # 每 5 分钟

    def at_repeat(self):
        "每 self.interval 秒调用一次。"
        rand = random.random()
        if rand < 0.5:
            weather = "A faint breeze is felt."
        elif rand < 0.7:
            weather = "Clouds sweep across the sky."
        else:
            weather = "There is a light drizzle of rain."
        # 将此消息发送给附加此脚本的对象中的所有人（可能是一个房间）
        self.obj.msg_contents(weather)
```

如果附加到一个房间，此脚本将在每 5 分钟随机向房间中的所有人报告一些天气。

```python
myroom.scripts.add(scripts.Weather)
```

> 请注意，游戏目录中的 `typeclasses` 已添加到设置 `TYPECLASS_PATHS` 中。
> 因此我们不需要给出完整路径（`typeclasses.scripts.Weather`），只需 `scripts.Weather`。

你也可以在创建脚本时将其附加：

```python
create_script('typeclasses.weather.Weather', obj=myroom)
```

### 其他脚本方法

脚本具有类型类化对象的所有属性，例如 `db` 和 `ndb`（参见 [类型类](./Typeclasses.md)）。设置 `key` 对于管理脚本（按名称删除等）很有用。这些通常在脚本的类型类中设置，但也可以作为关键字参数传递给 `evennia.create_script`。

- `at_script_creation()` - 仅调用一次 - 脚本首次创建时。
- `at_server_reload()` - 每当服务器热重启时（例如使用 `reload` 命令）调用。这是保存你可能希望在重载后保留的非持久性数据的好地方。
- `at_server_shutdown()` - 当系统重置或系统关闭时调用。
- `at_server_start()` - 当服务器返回（从重载/关闭/重启）时调用。它可以用于初始化和缓存非持久性数据，以便在启动脚本功能时使用。
- `at_repeat()`
- `at_start()`
- `at_pause()`
- `at_stop()`
- `delete()` - 与其他类型类化实体相同，这将删除脚本。值得注意的是，这也将停止计时器（如果运行），导致调用 `at_stop` 钩子。

此外，脚本支持 [属性](./Attributes.md)、[标签](./Tags.md) 和 [锁](./Locks.md) 等，如其他类型类化实体。

另请参阅上面控制 [定时脚本](#timed-script) 的方法。

### 处理脚本错误

在执行中的定时脚本内的错误有时可能相当简短，或者指向难以解释的执行机制的部分。使调试脚本更容易的一种方法是导入 Evennia 的本地记录器，并将你的函数包装在 try/catch 块中。Evennia 的记录器可以向你显示脚本中发生回溯的位置。

```python
from evennia.utils import logger

class Weather(Script):

    # [...]

    def at_repeat(self):

        try:
            # [...]
        except Exception:
            logger.log_trace()
```

## 使用 GLOBAL_SCRIPTS

没有附加到其他实体的脚本通常称为 _全局_ 脚本，因为它可以从任何地方访问。这意味着需要搜索它们才能使用。

Evennia 提供了一个方便的“容器” `evennia.GLOBAL_SCRIPTS` 来帮助组织你的全局脚本。你只需要脚本的 `key`。

```python
from evennia import GLOBAL_SCRIPTS

# 作为容器上的属性访问，名称与 key 相同
my_script = GLOBAL_SCRIPTS.my_script
# 如果名称中有空格或名称是动态确定的，需要这样
another_script = GLOBAL_SCRIPTS.get("another script")
# 获取所有全局脚本（这返回一个 Django 查询集）
all_scripts = GLOBAL_SCRIPTS.all()
# 你可以直接对脚本进行操作
GLOBAL_SCRIPTS.weather.db.current_weather = "Cloudy"
```

```{warning}
请注意，全局脚本根据其 `key` 作为属性出现在 `GLOBAL_SCRIPTS` 上。如果你创建了两个具有相同 `key` 的全局脚本（即使具有不同的类型类），`GLOBAL_SCRIPTS` 容器将只返回其中一个（哪个取决于数据库中的顺序）。最好组织你的脚本以避免这种情况。否则，使用 `evennia.search_script` 来准确获取你想要的脚本。
```

有两种方法可以使脚本作为 `GLOBAL_SCRIPTS` 上的属性出现：

1. 使用 `create_script` 手动创建一个具有 `key` 的新全局脚本。
2. 在 `GLOBAL_SCRIPTS` 设置变量中定义脚本的属性。这告诉 Evennia 它应该检查是否存在具有该 `key` 的脚本，如果不存在，则为你创建它。这对于必须始终存在和/或应在服务器重启时自动创建的脚本非常有用。如果使用此方法，必须确保所有脚本键在全局范围内是唯一的。

以下是如何在设置中告诉 Evennia 管理脚本：

```python
# 在 mygame/server/conf/settings.py 中

GLOBAL_SCRIPTS = {
    "my_script": {
        "typeclass": "typeclasses.scripts.Weather",
        "repeats": -1,
        "interval": 50,
        "desc": "Weather script"
    },
    "storagescript": {}
}
```

上面我们分别添加了两个键为 `myscript` 和 `storagescript` 的脚本。以下字典可以为空 - 然后将使用 `settings.BASE_SCRIPT_TYPECLASS`。在底层，提供的字典（连同 `key`）将自动传递给 `create_script`，因此此处支持所有 [与 create_script 相同的关键字参数](evennia.utils.create.create_script)。
```{warning}
在设置 Evennia 以这种方式管理脚本之前，请确保你的脚本类型类没有任何关键错误（单独测试它）。如果有，你将在日志中看到错误，并且你的脚本将暂时回退为 `DefaultScript` 类型。
```

此外，以这种方式定义的脚本在你尝试访问时 *保证* 存在：

```python
from evennia import GLOBAL_SCRIPTS
# 删除脚本
GLOBAL_SCRIPTS.storagescript.delete()
# 现在运行 `scripts` 命令将不显示 storagescript
# 但下面它会自动重新创建！
storage = GLOBAL_SCRIPTS.storagescript
```

也就是说，如果脚本被删除，下次你从 `GLOBAL_SCRIPTS` 获取它时，Evennia 将使用设置中的信息为你动态重新创建它。
