# 启动、停止、重载

你可以从游戏文件夹（这里称为 `mygame/`）使用 `evennia` 程序来控制 Evennia。如果命令行中没有 `evennia` 程序，你必须先按照[安装](./Installation.md)页面的说明安装 Evennia。

```{sidebar} 找不到 evennia？
如果你尝试 `evennia` 命令并收到错误，提示命令不可用，请确保你的 [virtualenv](./Installation-Git.md#virtualenv) 已激活。在 Windows 上，你可能需要先运行 `py -m evennia` 一次。
```

下面描述了各种管理选项。运行

```
evennia -h
```

可以获得简要帮助，运行

```
evennia menu
```

可以获得带选项的菜单。

## 启动 Evennia

Evennia 由两个组件组成：[Portal 和 Server](../Components/Portal-And-Server.md)。简单来说，*Server* 负责运行 MUD。它处理所有游戏相关的事情，但不关心玩家如何连接，只关心他们是否连接。*Portal* 是玩家连接的网关。它了解 telnet、ssh、webclient 协议等，但对游戏知之甚少。两者都是游戏正常运行所必需的。

```
evennia start
```

上述命令将启动 Portal，Portal 随后会启动 Server。命令将打印进程摘要，除非出现错误，否则你将看不到进一步的输出。两个组件将记录到 `mygame/server/logs/` 中的日志文件。为了方便起见，你可以通过在命令中附加 `-l` 来直接在终端中查看这些日志：

```
evennia -l
```

将开始跟踪已运行服务器的日志。启动 Evennia 时，你还可以这样做

```
evennia start -l
```

> 要停止查看日志文件，请按 `Ctrl-C`（在 Mac 上为 `Cmd-C`）。

## 重载

*重载*操作意味着 Portal 将告诉 Server 关闭，然后重新启动。所有人都会收到消息，游戏将暂时暂停，因为服务器重新启动。由于他们连接到 *Portal*，他们的连接不会丢失。

重载是最接近“热重启”的操作。它重新初始化 Evennia 的所有代码，但不会终止“持久”[脚本](../Components/Scripts.md)。它还会调用所有对象上的 `at_server_reload()` 钩子，以便你可以保存可能的临时属性。

在游戏中使用 `reload` 命令。你也可以从游戏外部重载服务器：

```
evennia reload
```

有时从“外部”重载是必要的，特别是在你添加了某种阻止游戏内输入的错误时。

## 停止

完全关闭会完全关闭 Evennia，包括 Server 和 Portal。所有账户将被踢出，系统将被保存并干净地关闭。

在游戏中，你可以使用 `shutdown` 命令启动关闭。从命令行执行

```
evennia stop
```

你将看到 Server 和 Portal 都关闭的消息。所有账户将看到关闭消息，然后被断开连接。

## 前台模式

通常，Evennia 作为“守护进程”在后台运行。如果你愿意，可以以*交互*模式启动任一进程（但不是两个）。这意味着它们将直接记录到终端（而不是记录到我们然后回显到终端的日志文件），你可以用 `Ctrl-C` 终止进程（而不仅仅是日志文件视图）。

```
evennia istart
```

将以交互模式启动/重启 *Server*。如果你想运行[调试器](../Coding/Debugging.md)，这是必需的。下次你 `evennia reload` 服务器时，它将返回正常模式。

```
evennia ipstart
```

将以交互模式启动 *Portal*。

如果你在前台模式下使用 `Ctrl-C`/`Cmd-C`，组件将停止。你需要运行 `evennia start` 来重新启动游戏。

## 重置

*重置*相当于“冷重启”——服务器将关闭并重新启动，但会表现得像完全关闭一样。与“真正的”关闭不同，重置期间不会断开任何账户连接。然而，重置会清除所有非持久性脚本，并调用 `at_server_shutdown()` 钩子。对于开发期间清理不安全脚本来说，这是一个很好的方法。

在游戏中使用 `reset` 命令。从终端：

```
evennia reset
```

## 重启

这将关闭*服务器和门户*，这意味着所有连接的玩家将失去连接。只能从终端启动：

```
evennia reboot
```

这与执行以下两个命令相同：

```
evennia stop
evennia start
```

## 状态和信息

要检查基本的 Evennia 设置，例如哪些端口和服务处于活动状态，这将重复启动服务器时给出的初始返回：

```
evennia info
```

你还可以使用此命令从两个组件中获取更简洁的运行状态

```
evennia status
```

这对于自动化检查以确保游戏正在运行并响应很有用。

## 杀死进程（仅限 Linux/Mac）

在极端情况下，如果服务器进程锁定且不响应命令，你可以发送 kill 信号以强制它们关闭。要仅杀死服务器：

```
evennia skill
```

要同时杀死服务器和门户：

```
evennia kill
```

请注意，此功能在 Windows 上不受支持。

## Django 选项

`evennia` 程序还将传递 `django-admin` 使用的选项。这些选项以各种方式操作数据库。

```bash
evennia migrate # 迁移数据库
evennia shell   # 启动一个交互式、支持 django 的 python shell
evennia dbshell # 启动数据库 shell
```

有关（许多）更多选项，请参阅 [django-admin 文档](https://docs.djangoproject.com/en/4.1/ref/django-admin/#usage)。

## Evennia 进程的高级处理

如果你需要手动管理 Evennia 的进程（或在任务管理器程序中查看它们，例如 Linux 的 `top` 或更高级的 `htop`），你会发现以下进程与 Evennia 相关：

- 1 x `twistd ... evennia/server/portal/portal.py` - 这是 Portal 进程。
- 3 x `twistd ... server.py` - 其中一个进程管理 Evennia 的 Server 组件，主要游戏。其他进程（名称相同但进程 ID 不同）处理 Evennia 的内部 Web 服务器线程。你可以查看 `mygame/server/server.pid` 来确定哪个是主进程。

### 实时开发中的语法错误

在开发过程中，你通常会修改代码，然后重载服务器以查看更改。这是通过 Evennia 从磁盘重新导入自定义模块来完成的。通常，模块中的错误只会让你在游戏中、日志中或命令行中看到回溯。然而，对于一些非常严重的语法错误，你的模块甚至可能无法被识别为有效的 Python。Evennia 可能因此无法正确重启。

在游戏中，你会看到有关服务器重启的文本，后面跟着一个不断增长的“...”。通常这只会持续很短的时间（最多几秒钟）。如果似乎持续很久，这意味着 Portal 仍在运行（你仍然连接到游戏），但 Evennia 的 Server 组件未能重新启动（即，它保持在关闭状态）。查看你的日志文件或终端以查看问题所在——你通常会看到一个清晰的回溯，显示出了什么问题。

修复你的错误，然后运行

```
evennia start
```

假设错误已修复，这将手动启动服务器（而不重启 Portal）。在游戏中，你现在应该会收到服务器已成功重启的消息。
