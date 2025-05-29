# 在 Android 上安装

本页面描述了如何在 Android 手机上安装并运行 Evennia 服务器。此过程需要从 Google Play 商店安装大量第三方程序，因此在开始之前，请确保你对此没有异议。

```{warning}
在 Android 上的安装是实验性的，未在较新版本的 Android 上测试。请报告你的发现。
```

## 安装 Termux

首先需要安装一个终端模拟器，以便运行“完整”的 Linux 版本。请注意，Android 本质上是运行在 Linux 之上的，因此如果你的手机已经 root，可以跳过这一步。不过，安装 Evennia 并不需要 root 权限。

假设我们没有 root 权限，我们将安装 [Termux](https://play.google.com/store/apps/details?id=com.termux&hl=en)。Termux 提供了一个 Linux 基础安装，包括 apt 和 Python，并在一个可写目录下提供它们。它还为我们提供了一个可以输入命令的终端。默认情况下，Android 不允许你访问根文件夹，因此 Termux 将其安装目录伪装为根目录。

Termux 在首次启动时会为我们设置一个基础系统，但我们需要为 Evennia 安装一些先决条件。在 Termux 中运行的命令如下所示：

```
$ cat file.txt
```

`$` 符号是你的提示符——运行命令时不要包括它。

## 先决条件

为了安装 Evennia 所需的一些库，即 Pillow 和 Twisted，我们首先需要安装它们依赖的一些包。在 Termux 中运行以下命令：

```
$ pkg install -y clang git zlib ndk-sysroot libjpeg-turbo libcrypt python
```

Termux 自带 Python 3，完美。Python 3 内置了 venv（虚拟环境）和 pip（Python 的模块安装器）。

因此，让我们设置虚拟环境。这可以将我们安装的 Python 包与系统版本分开。

```
$ cd
$ python3 -m venv evenv
```

这将创建一个名为 `evenv` 的新文件夹，包含新的 Python 可执行文件。接下来，让我们激活新的虚拟环境。每次你想在 Evennia 上工作时，你需要运行以下命令：

```
$ source evenv/bin/activate
```

你的提示符将更改为如下所示：

```
(evenv) $
```

更新 venv 中的更新器和安装器：pip、setuptools 和 wheel。

```
python3 -m pip install --upgrade pip setuptools wheel
```

### 安装 Evennia

现在我们已经准备好下载并安装 Evennia 本身。

神秘的咒语：

```
export LDFLAGS="-L/data/data/com.termux/files/usr/lib/"
export CFLAGS="-I/data/data/com.termux/files/usr/include/"
```

（这些告诉 C 编译器 clang 在构建 Pillow 时在哪里找到 zlib 的部分）

以可编辑源代码的方式安装最新的 Evennia：

```
(evenv) $ pip install --upgrade -e 'git+https://github.com/evennia/evennia#egg=evennia'
```

这一步可能需要相当长的时间——我们正在下载 Evennia 并安装它，构建 Evennia 运行所需的所有依赖项。如果在此步骤中遇到问题，请参阅[故障排除](./Installation-Android.md#troubleshooting)。

你可以使用 `cd $VIRTUAL_ENV/src/evennia` 进入 Evennia 安装目录。`git grep (something)` 和 `git diff` 可能会很有用。

### 最后步骤

此时，Evennia 已安装在你的手机上！你现在可以继续原始的[快速设置](./Installation.md)说明，我们在此重复以便清晰。

要开始一个新游戏：

```
(evenv) $ evennia --init mygame
(evenv) $ ls
mygame evenv
```

首次启动游戏：

```
(evenv) $ cd mygame
(evenv) $ evennia migrate
(evenv) $ evennia start
```

你的游戏现在应该正在运行！在浏览器中打开 http://localhost:4001 或将 telnet 客户端指向 localhost:4000 并使用你创建的用户登录。

## 运行 Evennia

当你希望运行 Evennia 时，进入 Termux 控制台，并确保你已激活虚拟环境并位于游戏目录中。然后你可以像往常一样运行 `evennia start`。

```
$ cd ~ && source evenv/bin/activate
(evenv) $ cd mygame
(evenv) $ evennia start
```

你可能希望查看[Linux 指南](./Installation-Git.md#linux-install)以获取更多信息。

## 注意事项

- Android 的 os 模块不支持某些功能——特别是 getloadavg。因此，在游戏中运行命令 @server 会引发异常。目前对此问题尚无解决方案。
- 正如你可能预期的那样，性能并不理想。
- Android 对内存管理相当积极，如果你的手机负载过重，你可能会发现服务器进程被终止。Termux 似乎会保持一个通知以防止这种情况。

## 故障排除

随着时间的推移和错误的报告，本节将不断补充。

无论如何，一些步骤可以尝试：

- 确保你的包是最新的，尝试运行 `pkg update && pkg upgrade -y`
- 确保你已安装 clang 包。如果没有，尝试 `pkg install clang -y`
- 确保你在正确的目录中。`cd ~/mygame`
- 确保你已激活虚拟环境。输入 `cd && source evenv/bin/activate`
- 查看 shell 是否可以启动：`cd ~/mygame ; evennia shell`
- 查看 ~/mygame/server/logs/ 中的日志文件。
