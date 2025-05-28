# 使用 Arxcode 游戏目录

> **警告**：Arxcode 是单独维护的。
>
> 尽管 Arxcode 使用 Evennia，但它并不是 Evennia 的一部分；我们提供此文档仅作为对用户的服务。此外，尽管 Arxcode 仍在积极维护（2022），这些指令是基于 *2018 年 8 月 12 日* 发布的 Arx 代码。这些指令可能无法完全开箱即用。

Arx - After the Reckoning 是一个大型且非常受欢迎的 [Evennia](https://www.evennia.com) 基于游戏。Arx 是高度角色扮演的，依赖于游戏大师来推动故事。它在技术上可能最好被描述为“一个 MUSH，但有更多的编码系统”。在 2018 年 8 月，游戏开发者 Tehom 慷慨地在 [github](https://github.com/Arx-Game/arxcode) 上发布了 Arx 的源代码。这是想要获取创意或甚至获取一个可供构建的起始游戏的开发者的财富。

从源代码运行 Arx 并不是太难（当然，您将从一个空数据库开始），但由于 Arx 的某些部分是有机生长的，因此它在所有地方并不遵循标准的 Evennia 模式。本页面涵盖了一种安装和设置的方法，同时使您的新 Arx 基于游戏更好地与基于 Evennia 的标准安装匹配。

## 安装 Evennia

首先，请在您的驱动器上为随后的内容留出一个文件夹/目录。

您需要通过遵循大部分 [Git 安装说明](../Setup/Installation-Git.md) 来开始安装 [Evennia](https://www.evennia.com)。不同之处在于，您应该这样做，而不是从上游 Evennia 克隆：

```
git clone https://github.com/TehomCD/evennia.git
```

这是因为 Arx 使用 TehomCD 的旧 Evennia 0.8 [分支](https://github.com/TehomCD/evennia)，特别是在使用 Python2。这一点在参考更新的 Evennia 文档时非常重要。

如果您是 Evennia 的新手，*强烈建议*您完整运行正常的安装说明——包括初始化和启动一个新的空游戏并连接到它。这样，您可以确保 Evennia 作为基准正常工作。

安装后，您应该有一个 `virtualenv` 正在运行，并且您的文件结构应该在您设定的文件夹中如下所示：

```
muddev/
   vienv/
   evennia/
   mygame/
```

这里的 `mygame` 是您在 Evennia 安装期间通过 `evennia --init` 创建的空游戏。转到该目录并运行 `evennia stop` 以确保您的空游戏未在运行。我们将让 Evennia 运行 Arx，因此原则上可以删除 `mygame`——但拥有一个干净的游戏做对比也是不错的。

## 安装 Arxcode

`cd` 到您目录的根目录并从 github 克隆发布的源代码：

```
git clone https://github.com/Arx-Game/arxcode.git myarx
```

一个名为 `myarx` 的新文件夹将在您已有的文件夹旁出现。如果愿意，可以将其重命名为其他名称。

`cd` 进入 `myarx`。如果您想了解游戏目录的结构，可以在 [这里阅读更多内容](Beginner-Tutorial/Part1/Beginner-Tutorial-Gamedir-Overview.md)。

### 清理设置

Arx 已将 Evennia 的正常设置拆分为 `base_settings.py` 和 `production_settings.py`。它还拥有自己管理设置文件“秘密”部分的解决方案。我们将保留大部分 Arx 的方式，但将删除秘密处理部分，并用标准的 Evennia 方法替换它。

`cd` 进入 `myarx/server/conf/` 并在文本编辑器中打开文件 `settings.py`。顶部部分（在 `"""..."""` 之间）只是帮助文本。擦除其下方的所有内容，并将其改为如下所示（别忘了保存）：

```python
from base_settings import *

TELNET_PORTS = [4000]
SERVERNAME = "MyArx"
GAME_SLOGAN = "The cool game"

try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")
```

> 注意：在 Python 中，缩进和大小写很重要。为你的逻辑 sanity 确保缩进为 4 个空格（不是选项卡）。如果您想获取 Evennia 中 Python 的入门，可以 [查看这里](Beginner-Tutorial/Part1/Beginner-Tutorial-Python-basic-introduction.md)。

这将导入 Arx 的基本设置，并使用 Evennia 默认的 Telnet 端口覆盖它们，并为游戏命名。口号更改了游戏网站标题下显示的子文本。您稍后可以根据自己的喜好进行调整。

接下来，在与 `settings.py` 文件相同的位置创建一个新的空文件 `secret_settings.py`。这可以只包含以下内容：

```python
SECRET_KEY = "sefsefiwwj3 jnwidufhjw4545_oifej whewiu hwejfpoiwjrpw09&4er43233fwefw"
```

用您自己的随机 ASCII 字符替换长随机字符串。秘密密钥不应共享。

接下来，打开 `myarx/server/conf/base_settings.py` 在您的文本编辑器中。我们希望移除/注释所有提到 `decouple` 包的部分，因为 Evennia 不使用它（我们使用 `private_settings.py` 来隐藏不应共享的设置）。

通过在行的开头添加 `#` 来注释掉 `from decouple import config`：`# from decouple import config`。然后在文件中搜索 `config(` 并注释掉所有使用此内容的行。这些中的许多是原始 Arx 运行的服务器环境特定的，因此对我们并不那么相关。

### 安装 Arx 依赖项

Arx 还具有一些比普通 Evennia 更多的依赖项。首先 `cd` 到您的 `myarx` 文件夹的根目录。

> 如果您使用 *Linux* 或 *Mac*：编辑 `myarx/requirements.txt` 并注释掉这一行 `pypiwin32==219`——它仅在 Windows 上需要，在其他平台上会出错。

确保您的 `virtualenv` 是活动的，然后运行：

```
pip install -r requirements.txt
```

所需的 Python 包将为您安装。

### 添加日志/文件夹

Arx 存储库不包含 Evennia 期待存储服务器日志的 `myarx/server/logs/` 文件夹。这很简单：

```
# linux/mac
mkdir server/logs
# windows
mkdir server\logs
```

### 设置数据库并启动

在 `myarx` 文件夹中运行：

```
evennia migrate
```

这将创建数据库并完成所有需要的数据库迁移。

```
evennia start
```

如果一切顺利，Evennia 将启动，运行 Arx！您可以使用 Telnet 客户端连接到 `localhost` （如果您的平台不将 `localhost` 映射到 `127.0.0.1`）的端口 `4000`。或者，您可以使用 web 浏览器访问 `http://localhost:4001` 查看游戏网站并访问网页客户端。

当您登录时，您将收到标准的 Evennia 问候（因为数据库是空的），但您可以尝试 `help` 来查看确实正在运行的是 Arx。

### 额外设置步骤

在通过上面的 `evennia migrate` 步骤创建数据库后，第一次启动 Evennia 时它应该为您创建一些起始对象——您的超级用户帐户，它将提示您输入、一个起始房间（Limbo）和一个角色对象。如果出于某种原因这没有发生，您可能需要按照以下步骤操作。针对超级用户的首次登录，您可能需要运行步骤 7-8 和 10 来创建并连接到您在游戏中的角色。

1. 使用您的超级用户帐户登录游戏网站。
2. 按下 `Admin` 按钮以进入（Django）管理界面。
3. 导航到 `Accounts` 部分。
4. 添加一个新帐户，命名为新工作人员的名字。使用一个占位符密码和虚拟电子邮件地址。
5. 将帐户标记为 `Staff`并应用 `Admin` 权限组（这假设您已经在 Django 中设置了一个 Admin 组）。
6. 添加名为 `player` 和 `developer` 的标签。
7. 使用您的超级用户帐户通过 web 客户端（或第三方 Telnet 客户端）登录游戏。移动到您希望新工作人员角色出现的地方。
8. 在游戏客户端中运行 `@create/drop <staffername>:typeclasses.characters.Character`，其中 `<staffername>` 通常与您在 Admin 中创建的 Staffer 帐户使用的名称相同（如果您正在为超级用户创建角色，请使用您的超级用户帐户名）。这将创建一个新的游戏角色，并将其放置在您当前位置。
9. 让新的管理员玩家登录游戏。
10. 让新管理员操纵角色，使用 `@ic StafferName`。
11. 让新的管理员更改其密码 - `@password <old password> = <new password>`。

现在您有了角色和帐户对象，您可能需要做一些额外的事情，以便某些命令正常工作。您可以在游戏中作为 `ic`（控制您的角色对象）执行这些操作。

```python
py from web.character.models import RosterEntry;RosterEntry.objects.create(player=self.player, character=self)
py from world.dominion.models import PlayerOrNpc, AssetOwner;dompc = PlayerOrNpc.objects.create(player=self.player);AssetOwner.objects.create(player=dompc)
```

这些步骤将为您提供 'RosterEntry'，'PlayerOrNpc' 和 'AssetOwner' 对象。RosterEntry 明确地将角色和帐户对象连接在一起，即使在离线状态下，也包含有关角色当前在游戏中呈现的额外信息（例如，他们所在的“名册”，如果您选择使用活动的角色名册）。PlayerOrNpc 是更多角色扩展，以及对没有游戏内存在、仅由名字表示的 NPC 的支持。这也允许在组织中的成员资格。AssetOwner 持有关于角色或组织的资金和资源的信息。

## 替代 Windows 安装指南

_由 Pax 贡献_

如果出于某种原因您无法使用 Windows 子系统 Linux（这将使用与上述相同的说明），则可以在 Windows 下通过 Anaconda 运行 Evennia/Arx。这个过程有点棘手。

确保您拥有：
* Windows 下的 Git https://git-scm.com/download/win
* Windows 下的 Anaconda https://www.anaconda.com/distribution/
* VC++ 编译器用于 Python 2.7 https://aka.ms/vcpython27

```bash
conda update conda
conda create -n arx python=2.7
source activate arx
```

为事物设置一个方便的存储库位置。

```bash
cd ~
mkdir Source
cd Source
mkdir Arx
cd Arx
```

用您的 github 分支替换以下 SSH git 克隆链接。
如果您不打算更改 Evennia，您可以使用 evennia/evennia.git 存储库而不是分叉的。

```bash
git clone git@github.com:<youruser>/evennia.git
git clone git@github.com:<youruser>/arxcode.git
```

Evennia 是一个软件包，因此我们希望在切换到为 Arxcode 打上标签的分支后安装它及其所有依赖项。

```bash
cd evennia
git checkout tags/v0.7 -b arx-master
pip install -e .
```

Arx 还有一些自己特有的依赖项，因此现在我们将安装它们。由于它不是一个软件包，我们将使用普通的 requirements 文件。

```bash
cd ../arxcode
pip install -r requirements.txt
```

git 仓库不包含空日志目录，如果没有它 Evennia 会不满意，因此仍然在 arxcode 目录中...

```bash
mkdir server/logs
```

现在访问 https://github.com/evennia/evennia/wiki/Arxcode-installing-help 并按照“清理设置”部分中的设置内容进行更改。

然后我们将创建我们的默认数据库...

```bash
../evennia/bin/windows/evennia.bat migrate
```

...并进行第一次运行。您需要 winpty，因为 Windows 默认没有 TTY/PTY，因此用于在首次运行时输入的 Python 控制台输入命令（用于提示）将失败，您将陷入不愉快的地方。以后再运行时，您不需要 winpty。

```bash
winpty ../evennia/bin/windows/evennia.bat start
```

完成后，您应该在 localhost 的 4000 端口上运行 Evennia 服务器运行 Arxcode，并且 web 服务器在 `http://localhost:4001/` 上运行。
