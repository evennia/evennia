# 改变游戏日历和时间流速

在许多游戏中，*游戏时间*与我们通常所说的*现实时间*并行运行。游戏时间可能以不同的速度运行，使用不同的时间单位名称，甚至可能使用完全自定义的日历。Evennia 提供了基本工具来处理这些情况。以下是如何设置和使用这些功能的教程。

## 使用标准日历的游戏时间

许多游戏让其游戏内时间比现实时间运行得更快或更慢，但仍然使用我们的正常现实世界日历。这对于设定在现代、历史或未来背景下的游戏都很常见。使用标准日历有一些优势：

- 处理重复动作更容易，因为从现实时间体验转换到游戏内感知时间很简单。
- 现实世界日历的复杂性，如闰年和不同长度的月份等，系统会自动处理。

### 为标准日历设置游戏时间

可以通过设置来完成。以下是使用标准日历设置游戏时间的设置：

```python
# 在 mygame/server/conf 文件中的 settings.py 中
# 时间因子决定游戏世界运行得比现实世界快（timefactor>1）还是慢（timefactor<1）。
TIME_FACTOR = 2.0

# 游戏时间的起始点（纪元），以秒为单位。
# 在 Python 中，值为 0 表示 1970 年 1 月 1 日（使用负数表示更早的开始日期）。
TIME_GAME_EPOCH = None
```

默认情况下，游戏时间比现实时间快两倍。你可以将时间因子设置为 1（游戏时间将与现实时间以相同速度运行）或更低（游戏时间将比现实时间慢）。大多数游戏选择让游戏时间运行得更快（有些游戏的时间因子为 60，这意味着游戏时间比现实时间快六十倍，现实时间的一分钟在游戏中相当于一小时）。

纪元是一个稍微复杂的设置。它应该包含一个以秒为单位的数字，表示游戏开始的时间。例如，一个纪元为 0 表示 1970 年 1 月 1 日。如果你想将时间设置在未来，只需找到以秒为单位的起始点。有几种方法可以在 Python 中做到这一点，以下方法将向你展示如何在本地时间中做到这一点：

```python
# 我们正在寻找代表 2020 年 1 月 1 日的秒数
from datetime import datetime
import time
start = datetime(2020, 1, 1)
time.mktime(start.timetuple())
```

这应该返回一个很大的数字——自 1970 年 1 月 1 日以来的秒数。将其直接复制到你的设置中（编辑 `server/conf/settings.py`）：

```python
# 在 mygame/server/conf 文件中的 settings.py 中
TIME_GAME_EPOCH = 1577865600
```

使用 `@reload` 重新加载游戏，然后使用 `@time` 命令。你应该会看到类似这样的输出：

```
+----------------------------+-------------------------------------+
| Server time                |                                     |
+~~~~~~~~~~~~~~~~~~~~~~~~~~~~+~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~+
| Current uptime             | 20 seconds                          |
| Total runtime              | 1 day, 1 hour, 55 minutes           |
| First start                | 2017-02-12 15:47:50.565000          |
| Current time               | 2017-02-13 17:43:10.760000          |
+----------------------------+-------------------------------------+
| In-Game time               | Real time x 2                       |
+~~~~~~~~~~~~~~~~~~~~~~~~~~~~+~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~+
| Epoch (from settings)      | 2020-01-01 00:00:00                 |
| Total time passed:         | 1 day, 17 hours, 34 minutes         |
| Current time               | 2020-01-02 17:34:55.430000          |
+----------------------------+-------------------------------------+
```

最相关的行是游戏时间纪元。你可以看到它显示为 2020-01-01。从这一点开始，游戏时间不断增加。如果你继续输入 `@time`，你会看到游戏时间更新正确，并且默认情况下比现实时间快两倍。

### 时间相关事件

`gametime` 实用程序还可以根据你的游戏时间安排游戏相关事件，并假设使用标准日历。例如，它可以用于每天（游戏内）早上 6:00 显示太阳升起的特定消息。

使用 `schedule()` 函数来实现。这将创建一个具有一些附加功能的 [script](../Components/Scripts.md)，以确保脚本始终在游戏时间与给定参数匹配时执行。

`schedule` 函数接受以下参数：

- *callback*，时间到时要调用的函数。
- 关键字 `repeat`（默认值为 `False`），指示此函数是否应重复调用。
- 其他关键字参数 `sec`、`min`、`hour`、`day`、`month` 和 `year` 用于描述要安排的时间。如果未给出参数，则假定为此特定单位的当前时间值。

以下是每天让太阳升起的简短示例：

```python
# 在 mygame/world/ 文件中的 ingame_time.py 中

from evennia.utils import gametime
from typeclasses.rooms import Room

def at_sunrise():
    """当太阳升起时，在每个房间显示一条消息。"""
    # 浏览所有房间
    for room in Room.objects.all():
        room.msg_contents("The sun rises from the eastern horizon.")

def start_sunrise_event():
    """安排每天早上 6 点发生的日出事件。"""
    script = gametime.schedule(at_sunrise, repeat=True, hour=6, min=0, sec=0)
    script.key = "at sunrise"
```

如果你想测试此函数，可以轻松执行以下操作：

```
@py from world import ingame_time; ingame_time.start_sunrise_event()
```

脚本将被静默创建。`at_sunrise` 函数现在将在每个游戏内天的早上 6 点被调用。你可以使用 `@scripts` 命令查看它。你可以使用 `@scripts/stop` 停止它。如果我们没有设置 `repeat`，太阳只会升起一次，然后再也不会升起。

我们在这里使用了 `@py` 命令：没有什么可以阻止你将系统添加到你的游戏代码中。请记住，要小心不要在启动时添加每个事件，否则当太阳升起时会有很多重叠的事件被安排。

当 `repeat` 设置为 `True` 时，`schedule` 函数将与更高的、未指定的单位一起使用。在我们的示例中，我们指定了小时、分钟和秒。我们没有指定的更高单位是天：`schedule` 假定我们的意思是“在指定时间每天运行回调”。因此，你可以有一个每小时在 HH:30 运行的事件，或者每月在第 3 天运行的事件。

> 对于每月或每年重复的脚本要谨慎：由于现实生活日历的变化，你需要小心在月底或年底安排事件。例如，如果你设置一个脚本在每月的 31 日运行，它将在一月份运行，但在二月、四月等月份找不到这样的日子。同样，闰年可能会改变一年的天数。

### 使用自定义日历的游戏时间

在某些情况下，如果你想在一个虚构的宇宙中设置你的游戏，使用自定义日历来处理游戏时间是必要的。例如，你可能想要创建托尔金描述的夏尔日历，其中有 12 个月，每个月有 30 天。这将只有 360 天（假设霍比特人并不喜欢遵循天文日历的麻烦）。另一个例子是在一个不同的太阳系中创建一个行星，比如说，天有 29 小时长，月只有 18 天。

Evennia 通过一个可选的 *contrib* 模块 `custom_gametime` 来处理自定义日历。与上面描述的正常 `gametime` 模块不同，它默认不激活。

### 设置自定义日历

在托尔金书中描述的夏尔日历的第一个例子中，我们实际上不需要星期的概念……但我们需要每个月有 30 天，而不是 28 天。

自定义日历通过在设置文件中添加 `TIME_UNITS` 设置来定义。它是一个字典，包含单位名称作为键，单位中秒数（我们最小的单位）作为值。其键必须从以下选项中选择：“sec”、“min”、“hour”、“day”、“week”、“month”和“year”，但你不必全部包含。以下是夏尔日历的配置：

```python
# 在 mygame/server/conf 文件中的 settings.py 中
TIME_UNITS = {"sec": 1,
              "min": 60,
              "hour": 60 * 60,
              "day": 60 * 60 * 24,
              "month": 60 * 60 * 24 * 30,
              "year": 60 * 60 * 24 * 30 * 12 }
```

我们将每个我们想要的单位作为键。值表示该单位中的秒数。小时设置为 60 * 60（即每小时 3600 秒）。请注意，在此配置中我们没有指定周单位：相反，我们直接从天跳到月。

为了使此设置正常工作，请记住所有单位必须是前一个单位的倍数。如果你创建“天”，它需要是小时的倍数。

因此，对于我们的示例，我们的设置可能如下所示：

```python
# 在 mygame/server/conf 文件中的 settings.py 中
# 时间因子
TIME_FACTOR = 4

# 游戏时间纪元
TIME_GAME_EPOCH = 0

# 单位
TIME_UNITS = {
        "sec": 1,
        "min": 60,
        "hour": 60 * 60,
        "day": 60 * 60 * 24,
        "month": 60 * 60 * 24 * 30,
        "year": 60 * 60 * 24 * 30 * 12,
}
```

请注意，我们设置了一个时间纪元为 0。使用自定义日历，我们将自己设计一个漂亮的时间显示。在我们的例子中，游戏时间从第 0 年，第 1 月，第 1 天和午夜开始。

> 年、小时、分钟和秒从 0 开始，月、周和天从 1 开始，这使它们的行为与标准时间一致。

请注意，虽然我们在设置中使用“月”、“周”等术语，但你的游戏中可能不使用这些术语，而是称它们为“周期”、“月亮”、“沙漏”等。这只是你以不同方式显示它们的问题。请参见下一节。

#### 显示当前游戏时间的命令

如前所述，`@time` 命令是用于标准日历的，而不是自定义日历。我们可以轻松创建一个新命令。我们将其称为 `time`，这在其他 MU* 上很常见。以下是我们如何编写它的示例（在示例中，你可以在 `commands` 目录中创建一个文件 `gametime.py` 并将此代码粘贴到其中）：

```python
# 在 mygame/commands/ 文件中的 gametime.py 中

from evennia.contrib.base_systems import custom_gametime

from commands.command import Command

class CmdTime(Command):
    """
    显示时间。

    语法：
        time
    """

    key = "time"
    locks = "cmd:all()"

    def func(self):
        """执行 time 命令。"""
        # 获取绝对游戏时间
        year, month, day, hour, mins, secs = custom_gametime.custom_gametime(absolute=True)
        time_string = f"We are in year {year}, day {day}, month {month}."
        time_string += f"\nIt's {hour:02}:{mins:02}:{secs:02}."
        self.msg(time_string)
```

不要忘记在你的 CharacterCmdSet 中添加它以查看此命令：

```python
# 在 mygame/commands/default_cmdset.py 中

from commands.gametime import CmdTime   # <-- 添加

# ...

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    `CharacterCmdSet` 包含一般的游戏内命令，如 `look`、`get` 等，可用于游戏内的 Character 对象。
    当一个 Account 操控一个 Character 时，它会与 `AccountCmdSet` 合并。
    """
    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        填充命令集
        """
        super().at_cmdset_creation()
        # ...
        self.add(CmdTime())   # <- 添加
```

使用 `@reload` 命令重新加载你的游戏。你现在应该能看到 `time` 命令。如果你输入它，你可能会看到类似这样的输出：

```
We are in year 0, day 0, month 0.
It's 00:52:17.
```

如果你愿意，可以用月份的名称甚至是天数来更漂亮地显示它。如果在你的游戏中“月”被称为“月亮”，这就是你添加它的地方。

## 自定义游戏时间中的时间相关事件

`custom_gametime` 模块还可以根据你的游戏时间（和自定义日历）安排游戏相关事件。它可以用于每天早上 6:00 显示太阳升起的特定消息。例如，`custom_gametime.schedule` 函数的工作方式与上面描述的默认函数相同。
