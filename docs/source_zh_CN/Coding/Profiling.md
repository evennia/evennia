# 性能分析

```{important}
这是一个高级主题，主要面向服务器开发人员。
```

有时候，确定某段代码的效率或考虑是否可以进一步加速是很有用的。测试 Python 和运行服务器的性能有多种方法。

在深入研究这一部分之前，请记住 Donald Knuth 的[箴言](https://en.wikipedia.org/wiki/Program_optimization#When_to_optimize)：

> *[...]大约 97% 的时间：过早优化是万恶之源*。

也就是说，在实际确定需要优化之前，不要开始尝试优化代码。这意味着在考虑优化之前，您的代码必须能够正常工作。优化通常会使代码变得更复杂且更难阅读。考虑可读性和可维护性，您可能会发现速度上的小增益并不值得。

## 简单的计时测试

Python 的 `timeit` 模块非常适合测试小型代码片段。例如，为了测试使用 `for` 循环还是列表推导式更快，可以使用以下代码：

```python
import timeit
# 进行 1000000 次 for 循环的时间
timeit.timeit("for i in range(100):\n    a.append(i)", setup="a = []")
<<< 10.70982813835144
# 进行 1000000 次列表推导式的时间
timeit.timeit("a = [i for i in range(100)]")
<<<  5.358283996582031
```

`setup` 关键字用于设置不应包含在时间测量中的内容，例如第一个调用中的 `a = []`。

默认情况下，`timeit` 函数将重新运行给定测试 1000000 次，并返回执行这些测试的*总时间*（而不是每次测试的平均时间）。提示是不要使用此默认值来测试包含数据库写入的内容——对于这些内容，您可能希望使用较低的重复次数（例如 100 或 1000），使用 `number=100` 关键字。

在上面的示例中，我们看到对于这个调用次数，使用列表推导式比使用 `.append()` 构建列表快大约两倍。

## 使用 cProfile

Python 自带一个名为 cProfile 的分析器（这是针对 cPython 的，目前尚未对 `pypy` 进行测试）。由于 Evennia 的进程处理方式，使用正常方式启动分析器（`python -m cProfile evennia.py`）没有意义。相反，您可以通过启动器启动分析器：

```
evennia --profiler start
```

这将启动 Evennia，服务器组件在 cProfile 下以守护进程模式运行。您也可以尝试使用 `--profile` 和 `portal` 参数来分析 Portal（然后需要[单独启动服务器](../Setup/Running-Evennia.md)）。

请注意，分析器运行时，您的进程将比平时使用更多内存。内存使用量甚至可能随着时间推移而增加。因此，不要让它持续运行，而是要仔细监控（例如在 Linux 上使用 `top` 命令或在 Windows 上使用任务管理器的内存显示）。

运行服务器一段时间后，您需要停止它以便分析器给出报告。*不要*从任务管理器中杀死程序或通过发送 kill 信号来停止它——这很可能会干扰分析器。相反，可以使用 `evennia.py stop` 或（可能更好）在游戏内部使用 `@shutdown`。

服务器完全关闭后（这可能比平时慢得多），您会发现分析器创建了一个新文件 `mygame/server/logs/server.prof`。

### 分析性能数据

`server.prof` 文件是一个二进制文件。有很多方法可以分析和显示其内容，这些方法仅在 Linux 上进行了测试（如果您是 Windows/Mac 用户，请告诉我们哪些方法有效）。

您可以在 evennia shell 中使用 Python 的内置 `pstats` 模块查看配置文件文件的内容（建议您先在虚拟环境中使用 `pip install ipython` 安装 `ipython`，以获得更漂亮的输出）：

```
evennia shell
```

然后在 shell 中输入：

```python
import pstats
from pstats import SortKey

p = pstats.Stats('server/log/server.prof')
p.strip_dirs().sort_stats(-1).print_stats()
```

有关更多信息，请参阅 [Python 性能分析文档](https://docs.python.org/3/library/profile.html#instant-user-s-manual)。

您还可以通过多种方式可视化数据。
- [Runsnake](https://pypi.org/project/RunSnakeRun/) 可视化配置文件以提供良好的概览。使用 `pip install runsnakerun` 安装。请注意，这可能需要 C 编译器，并且安装速度可能较慢。
- 要获取更详细的使用时间列表，可以使用 [KCachegrind](http://kcachegrind.sourceforge.net/html/Home.html)。要使 KCachegrind 与 Python 配置文件一起工作，您还需要包装脚本 [pyprof2calltree](https://pypi.python.org/pypi/pyprof2calltree/)。您可以通过 `pip` 获取 `pyprof2calltree`，而 KCacheGrind 需要通过包管理器或其主页获取。

如何分析和解释性能数据并不是一个简单的问题，取决于您进行性能分析的目的。Evennia 作为一个异步服务器，也可能会混淆性能分析。如果您需要帮助，请在邮件列表中询问，并准备好提供您的 `server.prof` 文件以供比较，以及获取该文件时的确切条件。

## Dummyrunner

在没有玩家的情况下测试“实际”游戏性能是困难的。为此，Evennia 提供了 *Dummyrunner* 系统。Dummyrunner 是一个压力测试系统：一个单独的程序，它使用模拟玩家（也称为“机器人”或“假人”）登录到您的游戏。一旦连接，这些假人将从可能的动作列表中半随机地执行各种任务。使用 `Ctrl-C` 停止 Dummyrunner。

```{warning}

    您不应在生产数据库上运行 Dummyrunner。它将生成许多对象，还需要在一般权限下运行。

这是使用 Dummyrunner 的推荐过程：
```

1. 使用 `evennia stop` 完全停止服务器。
2. 在 `mygame/server/conf/settings.py` 文件的_末尾_添加以下行：

    ```python
    from evennia.server.profiling.settings_mixin import *
    ```

   这将覆盖您的设置并禁用 Evennia 的速率限制器和 DoS 保护，否则会阻止来自一个 IP 的大量连接客户端。特别是，它还将更改为不同的（更快的）密码哈希算法。
3. （推荐）构建一个新数据库。如果您使用默认的 Sqlite3 并希望保留现有数据库，只需将 `mygame/server/evennia.db3` 重命名为 `mygame/server/evennia.db3_backup`，然后运行 `evennia migrate` 和 `evennia start`，按常规方式创建一个新的超级用户。
4. （推荐）以超级用户身份登录游戏。这只是为了让您可以手动检查响应。如果您保留了旧数据库，由于密码哈希算法已更改，您将_无法_使用_现有_用户连接！
5. 从终端启动 Dummyrunner，使用 10 个假用户：

    ```
    evennia --dummyrunner 10
    ```

   使用 `Ctrl-C`（或 `Cmd-C`）停止它。

如果您想查看假人实际在做什么，可以使用单个假人运行：

```
evennia --dummyrunner 1
```

假人的输入/输出将被打印。默认情况下，运行器使用 'looker' 配置文件，该配置文件只是一遍又一遍地登录并发送 'look' 命令。要更改设置，请将文件 `evennia/server/profiling/dummyrunner_settings.py` 复制到您的 `mygame/server/conf/` 目录，然后在设置文件中添加此行以在新位置使用它：

```python
DUMMYRUNNER_SETTINGS_MODULE = "server/conf/dummyrunner_settings.py"
```

Dummyrunner 设置文件本身是一个 Python 代码模块——它定义了假人可用的动作。这些只是命令字符串（如 "look here"）的元组，供假人发送到服务器，并附带它们发生的概率。Dummyrunner 寻找一个全局变量 `ACTIONS`，它是一个元组列表，其中前两个元素定义了登录/退出服务器的命令。

下面是一个简化的最小设置（默认设置文件添加了更多功能和信息）：

```python
# minimal dummyrunner setup file

# Time between each dummyrunner "tick", in seconds. Each dummy will be called
# with this frequency.
TIMESTEP = 1

# Chance of a dummy actually performing an action on a given tick. This
# spreads out usage randomly, like it would be in reality.
CHANCE_OF_ACTION = 0.5

# Chance of a currently unlogged-in dummy performing its login action every
# tick. This emulates not all accounts logging in at exactly the same time.
CHANCE_OF_LOGIN = 0.01

# Which telnet port to connect to. If set to None, uses the first default
# telnet port of the running server.
TELNET_PORT = None

# actions

def c_login(client):
    name = f"Character-{client.gid}"
    pwd = f"23fwsf23sdfw23wef23"
    return (
        f"create {name} {pwd}"
        f"connect {name} {pwd}"
    )

def c_logout(client):
    return ("quit", )

def c_look(client):
    return ("look here", "look me")

# this is read by dummyrunner.
ACTIONS = (
    c_login,
    c_logout,
    (1.0, c_look)   # (probability, command-generator)
)
```

在默认文件的底部，有一些默认配置文件，您可以通过将 `PROFILE` 变量设置为其中一个选项来测试。

### Dummyrunner 提示

- 不要一开始就使用太多假人。Dummyrunner 对服务器的压力比“真实”用户通常要大。开始时使用 10-100 个。
- 压力测试可能很有趣，但也要考虑对您的游戏来说“现实”的用户数量。
- 注意 Dummyrunner 输出中所有假人发送到服务器的命令/秒数量。这通常比您期望从相同数量的用户中看到的要高得多。
- 默认设置设置了一个“延迟”测量，以测量往返消息时间。每 30 秒更新一次平均值。值得在一个终端中为少量假人运行此程序，然后通过在另一个终端中启动另一个 Dummyrunner 来添加更多假人——第一个将充当不同负载下延迟变化的测量工具。还可以通过在游戏中手动输入命令来验证延迟时间。
- 使用 `top/htop`（Linux）检查服务器的 CPU 使用情况。在游戏中，使用 `server` 命令。
- 您可以使用 `--profiler start` 运行服务器，以便与假人一起测试。请注意，分析器本身会影响服务器性能，尤其是内存消耗。
- 总的来说，Dummyrunner 系统是测试一般性能的一个不错的工具；但当然很难真正模拟人类用户行为。为此，需要进行实际的游戏测试。
