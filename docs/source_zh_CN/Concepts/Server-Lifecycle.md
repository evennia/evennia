# Evennia 服务器生命周期

在你的游戏设计中，你可能希望更改 Evennia 在启动或停止时的行为。一个常见的用例是启动一些自定义代码，以便在服务器启动后始终可用。

Evennia 有三个主要生命周期，你可以为这些生命周期添加自定义行为：

- **数据库生命周期**：Evennia 使用数据库。这与您所做的代码更改并行存在。数据库一直存在，直到您选择重置或删除它。这样做不需要重新下载 Evennia。
- **重启生命周期**：从 Evennia 启动到完全关闭，这意味着 Portal 和 Server 都停止。在此周期结束时，所有玩家都将断开连接。
- **重载生命周期**：这是主要的运行时，直到发生“重载”事件。重载会刷新游戏代码，但不会踢出任何玩家。

## 当 Evennia 首次启动时

这是 **数据库生命周期** 的开始，就在数据库首次创建和迁移之后（或在其被删除和重建之后）。请参阅 [选择数据库](../Setup/Choosing-a-Database.md) 以获取有关如何重置数据库的说明，以便在第一次之后重新运行此序列。

按顺序调用的钩子：

1. `evennia.server.initial_setup.handle_setup(last_step=None)`：Evennia 的核心初始化函数。这是创建 #1 角色（与超级用户帐户关联）和 `Limbo` 房间的地方。它调用下面的下一个钩子，并且如果出现问题，它还会在上次失败的步骤重新启动。通常不应重写此函数，除非你 _确实_ 知道自己在做什么。要重写，请将 `settings.INITIAL_SETUP_MODULE` 更改为包含 `handle_setup` 函数的模块。
2. `mygame/server/conf/at_initial_setup.py` 包含一个函数 `at_initial_setup()`，它将在没有参数的情况下被调用。它在上述函数的设置序列中最后被调用。使用此函数添加自定义行为或调整初始化。例如，如果你想更改自动生成的 Limbo 房间，应从这里进行更改。如果你想更改此函数的位置，可以通过更改 `settings.AT_INITIAL_SETUP_HOOK_MODULE` 来实现。

## 当 Evennia 启动和关闭时

这是 **重启生命周期** 的一部分。Evennia 由两个主要进程组成，[Portal 和 Server](../Components/Portal-And-Server.md)。在重启或关闭时，Portal 和 Server 都会关闭，这意味着所有玩家都将断开连接。

每个进程调用位于 `mygame/server/conf/at_server_startstop.py` 中的一系列钩子。你可以使用 `settings.AT_SERVER_STARTSTOP_MODULE` 自定义使用的模块——这甚至可以是一个模块列表，如果是这样，将按顺序从每个模块调用适当命名的函数。

所有钩子都在没有参数的情况下被调用。

> 钩子名称中使用的术语“server”表示整个 Evennia，而不仅仅是 `Server` 组件。

### 服务器冷启动

从零开始启动服务器，在完全停止之后。这是通过终端中的 `evennia start` 完成的。

1. `at_server_init()` - 启动序列中始终首先调用。
2. `at_server_cold_start()` - 仅在冷启动时调用。
3. `at_server_start()` - 启动序列中始终最后调用。

### 服务器冷关闭

关闭所有内容。通过游戏中的 `shutdown` 或终端中的 `evennia stop` 完成。

1. `at_server_cold_stop()` - 仅在冷停止时调用。
2. `at_server_stop()` - 停止序列中始终最后调用。

### 服务器重启

这是通过 `evennia reboot` 完成的，实际上构成了自动冷关闭，随后由 `evennia` 启动器控制的冷启动。对此没有特殊的 `reboot` 钩子，而是看起来像你期望的那样：

1. `at_server_cold_stop()`
2. `at_server_stop()`  （在此之后，`Server` 和 `Portal` 都已关闭）
3. `at_server_init()`  （像冷启动一样）
4. `at_server_cold_start()`
5. `at_server_start()`

## 当 Evennia 重载和重置时

这是 **重载生命周期**。如上所述，Evennia 由两个组件组成，[Portal 和 Server](../Components/Portal-And-Server.md)。在重载期间，仅 `Server` 组件被关闭并重新启动。由于 Portal 保持运行，玩家不会断开连接。

所有钩子都在没有参数的情况下被调用。

### 服务器重载

重载是通过游戏中的 `reload` 命令或终端中的 `evennia reload` 启动的。

1. `at_server_reload_stop()` - 仅在重载停止时调用。
2. `at_server_stop` - 停止序列中始终最后调用。
3. `at_server_init()` - 启动序列中始终首先调用。
4. `at_server_reload_start()` - 仅在重载（重新）启动时调用。
5. `at_server_start()` - 启动序列中始终最后调用。

### 服务器重置

“重置”是一种混合重载状态，其中重载被视为冷关闭，仅用于运行钩子（玩家不会断开连接）。它通过游戏中的 `reset` 或终端中的 `evennia reset` 运行。

1. `at_server_cold_stop()`
2. `at_server_stop()`  （在此之后，只有 `Server` 已关闭）
3. `at_server_init()`  （`Server` 重新启动）
4. `at_server_cold_start()`
5. `at_server_start()`
