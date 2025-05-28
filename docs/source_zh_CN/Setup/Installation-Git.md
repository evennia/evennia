# 使用 GIT 安装

通过源代码安装并运行 Evennia。如果你想为 Evennia 做贡献或更轻松地探索代码，这是必需的。有关库的快速安装，请参阅基本[安装说明](./Installation.md)。如果遇到问题，请参阅[故障排除](./Installation-Troubleshooting.md)。

```{important}
如果你要从以前的版本转换现有游戏，请[参见此处](./Installation-Upgrade.md)。
```

## 概述

对于心急的人。如果某一步出现问题，你应该查看更详细的说明。

1. 安装 Python 和 GIT。启动控制台/终端。
2. `cd` 到你想进行开发的地方（例如 Linux 上的 `/home/anna/muddev/` 文件夹或 Windows 上的个人用户目录中的文件夹）。
3. `git clone https://github.com/evennia/evennia.git`（会创建一个新的 `evennia` 文件夹）
4. `python3.11 -m venv evenv`（会创建一个新的 `evenv` 文件夹）
5. `source evenv/bin/activate`（Linux, Mac），`evenv\Scripts\activate`（Windows）
6. `pip install -e evennia`
7. `evennia --init mygame`
8. `cd mygame`
9. `evennia migrate`
10. `evennia start`（确保在询问时创建超级用户）

现在 Evennia 应该正在运行，你可以通过将网页浏览器指向 `http://localhost:4001` 或将 MUD telnet 客户端指向 `localhost:4000`（如果你的操作系统不识别 `localhost`，请使用 `127.0.0.1`）来连接到它。

## 虚拟环境

Python [虚拟环境](https://docs.python.org/3/library/venv.html)允许你在一个独立的文件夹中安装 Evennia 及其所有依赖项，与系统的其他部分分开。这也意味着你可以在没有任何额外权限的情况下安装——所有内容都存储在你的驱动器上的一个文件夹中。

使用虚拟环境是可选的，但强烈推荐。这不仅是常见的 Python 实践，它还会让你的生活更轻松，并避免与其他可能安装的 Python 程序发生冲突。

Python 原生支持虚拟环境：

```{sidebar} 在 Windows 上使用 py
如果你在 Windows 上安装了旧版本的 Python，你应该在这里使用 `py` 而不是 `python`。`py` 启动器会自动选择你安装的最新 Python 版本。
```

```bash
python3.11 -m venv evenv   (Linux/Mac)
python -m venv evenv       (Windows)
```

这将在当前目录中创建一个新的 `evenv` 文件夹。
激活它：

```
source evenv/bin/activate (Linux, Mac)

evenv\Scripts\activate    (Windows Console)

.\evenv\scripts\activate  (Windows PS Shell, 
                           Git Bash 等)
```

提示符旁边应该出现文本 `(evenv)`，表示虚拟环境已启用。你*不需要*实际在 `evenv` 文件夹中或附近才能激活环境。

```{important}
请记住，每次启动新终端/控制台（或重新启动计算机）时，你都需要这样（重新）激活虚拟环境。在此之前，`evennia` 命令将不可用。
```

## Linux 安装

对于 Debian 衍生系统（如 Ubuntu、Mint 等），启动终端并安装所需软件：

```bash
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv python3.11-dev gcc
```

确保在此步骤后*不要*以 `root` 身份运行，以 `root` 身份运行存在安全风险。现在创建一个文件夹来进行所有 Evennia 开发：

```bash
mkdir muddev
cd muddev
```

接下来我们获取 Evennia 本身：

```
git clone https://github.com/evennia/evennia.git
```

一个新的 `evennia` 文件夹将出现，其中包含 Evennia 库。但这仅包含源代码，尚未*安装*。

此时，初始化和激活[虚拟环境](#virtualenv)是可选的，但推荐这样做。

接下来，安装 Evennia（系统范围内，或进入活动的虚拟环境）。确保你位于 mud 目录树的顶部（这样你就可以看到 `evennia/` 文件夹，可能还有 `evenv` 虚拟环境文件夹），然后执行：

```{sidebar} 
`-e` 表示我们以可编辑模式安装 evennia。如果你想开发 Evennia 本身，这意味着你对代码的更改会立即反映在正在运行的服务器上（每次更改时不必重新安装）。
```

```
pip install -e evennia
```

测试你是否可以运行 `evennia` 命令。

接下来，你可以继续按照常规[安装说明](./Installation.md)初始化游戏。

## Mac 安装

Evennia 服务器是一个终端程序。从*应用程序->实用工具->终端*打开终端。如果你不确定它的工作原理，[这里是 Mac 终端的介绍](https://blog.teamtreehouse.com/introduction-to-the-mac-os-x-command-line)。

* Python 应该已经安装，但你必须确保它的版本足够高——选择 3.11。（[这里](https://docs.python-guide.org/en/latest/starting/install/osx/)讨论了如何升级它）。
* GIT 可以通过 [git-osx-installer](https://code.google.com/p/git-osx-installer/) 或通过 MacPorts [如这里所述](https://git-scm.com/book/en/Getting-Started-Installing-Git#Installing-on-Mac) 获取。
* 如果你在安装 `Twisted` 时遇到问题，可能需要安装 `gcc` 和 Python 头文件。

在此之后，你不需要 `sudo` 或任何更高权限来安装任何东西。

现在创建一个文件夹来进行所有 Evennia 开发：

```
mkdir muddev
cd muddev
```

接下来我们获取 Evennia 本身：

```
git clone https://github.com/evennia/evennia.git
```

一个新的 `evennia` 文件夹将出现，其中包含 Evennia 库。但这仅包含源代码，尚未*安装*。

此时，初始化和激活[虚拟环境](#virtualenv)是可选的，但推荐这样做。

接下来，安装 Evennia（系统范围内，或进入活动的虚拟环境）。确保你位于 mud 目录树的顶部（这样你就可以看到 `evennia/`，可能还有 `evenv` 虚拟环境文件夹），然后执行：

```
pip install --upgrade pip   # 旧版本的 pip 可能在 Mac 上有问题。
pip install --upgrade setuptools   # 同样关于 Mac 问题。
pip install -e evennia
```

测试你是否可以运行 `evennia` 命令。

接下来，你可以继续按照常规[安装说明](./Installation.md)初始化游戏。

## Windows 安装

> 如果你运行的是 Windows10+，考虑使用 _Windows Subsystem for Linux_ > ([WSL](https://en.wikipedia.org/wiki/Windows_Subsystem_for_Linux))。只需使用 Ubuntu 映像设置 WSL，然后按照上面的 Linux 安装说明进行操作。

Evennia 服务器本身是一个命令行程序。在 Windows 启动菜单中，启动*所有程序 -> 附件 -> 命令提示符*，你将获得 Windows 命令行界面。如果你不熟悉它，这里是[许多教程之一](https://www.bleepingcomputer.com/tutorials/windows-command-prompt-introduction/)。

* 从 [Python 主页](https://www.python.org/downloads/windows/) 安装 Python。你需要是 Windows 管理员才能安装软件包。获取 Python **3.11**，64 位版本。使用默认设置；确保安装了 `py` 启动器。
* 你还需要获取 [GIT](https://git-scm.com/downloads) 并安装它。你可以使用默认安装选项，但当你被要求“调整你的 PATH 环境”时，你应该选择第二个选项“从 Windows 命令提示符使用 Git”，这会给你更多的自由来决定在哪里使用程序。
* 如果你运行 Python 3.11：你还必须安装 [Windows SDK](https://aka.ms/vs/16/release/vs_buildtools.exe)。下载并运行链接的安装程序。点击顶部的 `Individual Components` 选项卡。搜索并勾选最新的 `Windows 10 SDK`（适用于较旧和较新的 Windows 版本）。点击 `Install`。如果你后来由于未能构建“Twisted wheels”而在安装 Evennia 时遇到问题，这是你缺少的东西。如果遇到问题，暂时使用 Python 3.10（2022 年）
* 你*可能*需要 [pypiwin32](https://pypi.python.org/pypi/pypiwin32) Python 头文件。仅在遇到问题时安装这些。

你可以在任何地方安装 Evennia。`cd` 到该位置并为所有 Evennia 开发创建一个新文件夹（我们称之为 `muddev`）。

```
mkdir muddev
cd muddev
```

> 如果 `cd` 不工作，你可以使用 `pushd` 来强制更改目录。

接下来我们获取 Evennia 本身：

```
git clone https://github.com/evennia/evennia.git
```

一个新的 `evennia` 文件夹将出现，其中包含 Evennia 库。但这仅包含源代码，尚未*安装*。

此时，初始化和激活[虚拟环境](#virtualenv)是可选的，但推荐这样做。

接下来，安装 Evennia（系统范围内，或进入虚拟环境）。确保你位于 mud 目录树的顶部（这样你在运行 `dir` 命令时可以看到 `evennia`，可能还有 `evenv` 虚拟环境文件夹）。然后执行：

```
pip install -e evennia
```

测试在虚拟环境（evenv）激活时，你是否可以在任何地方运行 `evennia` 命令。

接下来，你可以继续按照常规[安装说明](./Installation.md)初始化游戏。
