# 安装故障排除

如果你遇到的问题不在这里列出，[请报告](https://github.com/evennia/evennia/issues/new/choose)以便修复或找到解决方法！

服务器日志位于 `mygame/server/logs/`。要在终端中轻松查看服务器日志，你可以运行 `evennia -l`，或使用 `evennia start -l` 或 `evennia reload -l` 启动/重载服务器。

## 检查你的要求

任何支持 Python3.10+ 的系统都应该可以运行。
- Linux/Unix
- Windows (Win7, Win8, Win10, Win11)
- Mac OSX (建议 >10.5)

- [Python](https://www.python.org) (测试过 3.10, 3.11 和 3.12，推荐 3.12)
- [Twisted](https://twistedmatrix.com) (v23.10+)
  - [ZopeInterface](https://www.zope.org/Products/ZopeInterface) (v3.0+) - 通常包含在 Twisted 包中
  - Linux/Mac 用户可能需要 `gcc` 和 `python-dev` 包或等效包。
  - Windows 用户需要 [MS Visual C++](https://aka.ms/vs/16/release/vs_buildtools.exe) 和 *可能* 需要 [pypiwin32](https://pypi.python.org/pypi/pypiwin32)。
- [Django](https://www.djangoproject.com) (v4.2+)，请注意最新的开发版本通常未经 Evennia 测试。
- [GIT](https://git-scm.com/) - 如果你想安装源代码，这个版本控制软件是必需的（但也有助于跟踪你自己的代码）
  - Mac 用户可以使用 [git-osx-installer](https://code.google.com/p/git-osx-installer/) 或 [MacPorts 版本](https://git-scm.com/book/en/Getting-Started-Installing-Git#Installing-on-Mac)。

## 位置混淆（GIT 安装）

在进行 [Git 安装](./Installation-Git.md) 时，有些人可能会混淆并将 Evennia 安装在错误的位置。按照说明（并使用 virtualenv）后，文件夹结构应如下所示：

```
muddev/
    evenv/
    evennia/
    mygame/
```

Evennia 的库代码位于 `evennia/evennia/`（两层下）。你不应该更改这个；所有工作都应在 `mygame/` 中进行。你的设置文件是 `mygame/server/conf/settings.py`，而父设置文件是 `evennia/evennia/settings_default.py`。

## Virtualenv 设置失败

在执行 `python3.x -m venv evenv`（其中 x 是 python3 版本）步骤时，一些用户报告收到错误；类似于：

```
Error: Command '['evenv', '-Im', 'ensurepip', '--upgrade', '--default-pip']' 
returned non-zero exit status 1
```

你可以通过安装 `python3.11-venv`（或更高版本）包（或适用于你的操作系统的等效包）来解决此问题。或者，你可以这样引导它：

```
python3.x -m --without-pip evenv
```

这应该可以在没有 `pip` 的情况下设置 virtualenv。激活新的 virtualenv，然后从中安装 pip（激活 virtualenv 后，你不需要指定 python 版本）：

```
python -m ensurepip --upgrade
```

如果失败，可以尝试一个更糟糕的替代方法：

```
curl https://bootstrap.pypa.io/get-pip.py | python3.x    (仅限 linux/unix/WSL)
```

无论哪种方式，你现在应该可以继续安装。

## 找不到 Localhost

如果在尝试连接到本地游戏时 `localhost` 不起作用，请尝试 `127.0.0.1`，这与 `localhost` 是相同的。

## Linux 故障排除

- 如果在安装 Evennia 时出现错误（尤其是提到无法包含 `Python.h` 的行），请尝试 `sudo apt-get install python3-setuptools python3-dev`。安装后，再次运行 `pip install -e evennia`。
- 在进行 [git 安装](./Installation-Git.md) 时，一些未更新的 Linux 发行版可能会出现关于 `setuptools` 版本过旧或缺少 `functools` 的错误。如果是这样，请使用 `pip install --upgrade pip wheel setuptools` 更新你的环境。然后再尝试 `pip install -e evennia`。
- 一位用户报告在 Ubuntu 16 上安装 Twisted 时出现了一个罕见的问题；`Command "python setup.py egg_info" failed with error code 1 in /tmp/pip-build-vnIFTg/twisted/` 并伴有 `distutils.errors.DistutilsError: Could not find suitable distribution for Requirement.parse('incremental>=16.10.1')` 等错误。似乎可以通过简单地更新 Ubuntu 来解决此问题，使用 `sudo apt-get update && sudo apt-get dist-upgrade`。
- Fedora 用户（尤其是 Fedora 24）报告了一个 `gcc` 错误，称目录 `/usr/lib/rpm/redhat/redhat-hardened-cc1` 缺失，尽管 `gcc` 本身已安装。[确认的解决方法](https://gist.github.com/yograterol/99c8e123afecc828cb8c) 似乎是安装 `redhat-rpm-config` 包，例如使用 `sudo dnf install redhat-rpm-config`。
- 一些尝试在 NTFS 文件系统上设置 virtualenv 的用户发现由于不支持符号链接而失败。答案是不使用 NTFS（说真的，为什么要这样对自己？）

## Mac 故障排除

- 一些 Mac 用户报告无法连接到 `localhost`（即你的计算机）。如果是这样，请尝试连接到 `127.0.0.1`，这与 `localhost` 是相同的。从 mud 客户端使用端口 4000，从 web 浏览器使用端口 4001。
- 如果在启动 Evennia 或查看日志时出现 `MemoryError`，这可能是由于 sqlite 版本问题。[我们论坛上的一位用户](https://github.com/evennia/evennia/discussions/2637) 找到了一个有效的解决方案。[这里](https://github.com/evennia/evennia/issues/2854) 是另一种解决方法。[另一位用户](https://github.com/evennia/evennia/issues/3704) 还撰写了关于此问题的详细总结，并附有故障排除说明。

## Windows 故障排除

- 如果你使用 `pip install evennia` 安装后发现 `evennia` 命令不可用，运行 `py -m evennia` 一次。这应该会将 evennia 二进制文件添加到你的环境中。如果失败，请确保你正在使用 [virtualenv](./Installation-Git.md#virtualenv)。最坏的情况下，你可以在使用 `evennia` 命令的地方继续使用 `py -m evennia`。
- 如果在安装后直接尝试运行 `evennia` 程序时收到 `command not found`，请尝试关闭 Windows 控制台并重新启动（如果使用 virtualenv，请记得重新激活它！）。有时 Windows 没有正确更新其环境，`evennia` 只会在新控制台中可用。
- 如果你安装了 Python 但 `python` 命令不可用（即使在新控制台中），那么你可能错过了将 Python 安装到路径中。在 Windows Python 安装程序中，你会看到一个选项列表，列出了要安装的内容。大多数或所有选项都是预选的，除了这个选项，你甚至可能需要向下滚动才能看到它。重新安装 Python 并确保选中它。从 [Python 主页](https://www.python.org/downloads/windows/) 安装 Python。你需要是 Windows 管理员才能安装软件包。
- 如果你的 MUD 客户端无法连接到 `localhost:4000`，请尝试等效的 `127.0.0.1:4000`。Windows 上的一些 MUD 客户端似乎不理解 `localhost` 的别名。
- 一些 Windows 用户在安装 Twisted 'wheel' 时遇到错误。Wheel 是一个预编译的 Python 二进制包。此错误的常见原因是你使用的是 32 位版本的 Python，但 Twisted 尚未上传最新的 32 位 wheel。最简单的解决方法是安装稍旧的 Twisted 版本。因此，如果版本 `22.1` 失败，请使用 `pip install twisted==22.0` 手动安装 `22.0`。或者，你可以检查你使用的是 64 位版本的 Python，并卸载任何 32 位版本。如果是这样，你必须 `deactivate` virtualenv，删除 `evenv` 文件夹，并使用新的 Python 重新创建它。
- 如果你进行了 git 安装，并且你的服务器无法启动，出现类似 `AttributeError: module 'evennia' has no attribute '_init'` 的错误消息，这可能是一个 python 路径问题。在终端中，cd 到 `(你的 python 目录)\site-packages` 并运行命令 `echo "C:\absolute\path\to\evennia" > local-vendors.pth`。在你喜欢的 IDE 中打开创建的文件，并确保它以 *UTF-8* 编码保存，而不是 *UTF-8 with BOM*。
- 一些用户报告在 Windows WSL 和杀毒软件在 Evennia 开发期间出现问题。超时错误和无法运行 `evennia connections` 可能是由于杀毒软件干扰。尝试禁用或更改杀毒软件设置。
