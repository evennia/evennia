# 安装指南

```{important}
如果你正在从旧版本的 Evennia 转换现有游戏，你需要进行升级。
```

安装 Evennia 最快的方法是使用 Python 自带的 `pip` 安装程序（继续阅读）。你也可以从 [GitHub 克隆 Evennia](./Installation-Git.md) 或使用 [Docker](./Installation-Docker.md)。一些用户还尝试过在 [Android 上安装 Evennia](./Installation-Android.md)。

如果你正在转换现有游戏，请遵循[升级说明](./Installation-Upgrade.md)。

## 系统要求

```{sidebar} 独立开发
安装 Evennia 不会让任何东西在线可见。除了安装和更新，你可以在没有互联网连接的情况下开发你的游戏。
```
- Evennia 需要 [Python](https://www.python.org/downloads/) 3.10, 3.11 或 3.12（推荐）。任何支持 Python 的操作系统都应该可以运行。
  - _Windows_：在安装程序中，确保选择 `add python to path`。如果你安装了多个版本的 Python，请使用 `py` 命令而不是 `python`，以便 Windows 自动使用最新版本。
- 不要以管理员或超级用户身份安装 Evennia。
- 如果遇到问题，请参阅[安装故障排除](./Installation-Troubleshooting.md)。

## 使用 `pip` 安装

```{important}
建议你设置一个轻量级的 Python virtualenv 来安装 Evennia。使用 virtualenv 是 Python 的标准实践，可以让你在与其他程序隔离的环境中安装所需的内容。virtualenv 系统是 Python 的一部分，会让你的生活更轻松！
```

建议你首先[设置一个轻量级的 Python virtualenv](./Installation-Git.md#virtualenv)。

Evennia 的管理是在终端（Windows 上的控制台/命令提示符）中进行的。一旦安装了 Python，并在使用 virtualenv 的情况下激活它后，用以下命令安装 Evennia：

```
pip install evennia
```

可选：如果你使用的 [contrib](../Contribs/Contribs-Overview.md) 提醒你需要额外的包，可以用以下命令安装所有额外的依赖：

```
pip install evennia[extra]
```

以后要更新 Evennia，请执行以下操作：

```
pip install --upgrade evennia
```

```{note} **仅限 Windows 用户 -** 
你现在必须运行 `python -m evennia` 一次。这应该会永久地使 `evennia` 命令在你的环境中可用。
```

安装完成后，确保 `evennia` 命令可用。使用 `evennia -h` 查看使用帮助。如果你使用 virtualenv，请确保在以后需要使用 `evennia` 命令时它是激活的。

## 初始化新游戏

我们将创建一个新的“游戏目录”来创建你的游戏。在此以及 Evennia 文档的其余部分，我们将这个游戏目录称为 `mygame`，但你当然可以为你的游戏命名为任何你喜欢的名称。要在当前位置创建新的 `mygame` 文件夹或你选择的其他名称：

```{sidebar} 游戏目录 vs 游戏名称
你创建的游戏目录不必与游戏名称匹配。你可以通过编辑 `mygame/server/conf/settings.py` 来更改游戏名称。
```

```
evennia --init mygame
```

生成的文件夹包含启动 Evennia 服务器所需的所有空模板和默认设置。

## 启动新游戏

首先，创建默认数据库（Sqlite3）：

```
cd mygame
evennia migrate
```

生成的数据库文件创建在 `mygame/server/evennia.db3` 中。如果你想从一个新的数据库开始，只需删除此文件并重新运行 `evennia migrate` 命令。

接下来，启动 Evennia 服务器：

```
evennia start
```

当被提示时，输入游戏内“god”或“superuser”的用户名和密码。提供电子邮件地址是可选的。

> 你也可以[自动化](./Installation-Non-Interactive.md)创建超级用户。

如果一切顺利，你的新 Evennia 服务器现在应该已经启动并运行！要玩你的新游戏（虽然是空的），可以将传统的 MUD/telnet 客户端指向 `localhost:4000` 或将网页浏览器指向 [http://localhost:4001](http://localhost:4001)。你可以注册一个新账户或使用你创建的超级用户账户登录。

## 重启和停止

你可以通过以下命令重启服务器（不会断开玩家连接）：

```
evennia restart
```

要进行完整的停止和重启（会断开玩家连接），请使用：

```
evennia reboot
```

要完全停止服务器（使用 `evennia start` 重新启动），请执行：

```
evennia stop
```

有关详细信息，请参阅[服务器启动-停止-重载](./Running-Evennia.md)文档页面。

## 查看服务器日志

日志文件位于 `mygame/server/logs`。你可以通过以下命令实时跟踪日志：

```
evennia --log
```

或简单地：

```
evennia -l
```

按 `Ctrl-C`（Mac 上是 `Cmd-C`）停止查看实时日志。

你也可以通过在启动服务器时添加 `-l/--log` 来立即开始查看实时日志：

```
evennia start -l
```

## 服务器配置

你的服务器配置文件是 `mygame/server/conf/settings.py`。默认情况下是空的。仅复制和粘贴你想要/需要的设置从[默认设置文件](./Settings-Default.md)到你的服务器的 `settings.py`。在此时配置服务器之前，请参阅[设置](./Settings.md)文档以获取更多信息。

## 注册到 Evennia 游戏索引（可选）

为了让世界知道你正在开发一个基于 Evennia 的新游戏，你可以通过以下命令将你的服务器注册到 _Evennia 游戏索引_：

```
evennia connections
```

然后，只需按照提示进行操作。你不必开放给玩家就可以这样做&mdash;只需将你的游戏标记为关闭和“预 alpha”。

请查看[此处](./Evennia-Game-Index.md)以获取更多说明，并在此之前[查看索引](http:games.evennia.com)，以确保你没有选择已经被占用的游戏名称&mdash;请友好对待！

## 下一步

你已经准备好了！

接下来，为什么不前往[入门教程](../Howtos/Beginner-Tutorial/Beginner-Tutorial-Overview.md)学习如何开始制作你的新游戏呢？
