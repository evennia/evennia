# 游戏内 Git 集成

由 helpme 贡献于 2022 年

这是一个模块，用于在游戏中集成精简版的 git，允许开发者查看 git 状态、更改分支，以及拉取本地 mygame 仓库和 Evennia 核心的更新代码。在成功拉取或检出后，git 命令将重载游戏：某些更改可能需要手动重启，以影响持久化脚本等。

一旦设置好此模块，集成远程更改只需在游戏中输入以下命令：

```
git pull
```

要使用的仓库，无论是本地 mygame 仓库、Evennia 核心，还是两者都需要是 git 目录，命令才能生效。如果您只对获取上游 Evennia 更改感兴趣，则只需要 Evennia 仓库是一个 git 仓库。[在这里开始使用版本控制。](https://www.evennia.com/docs/1.0-dev/Coding/Version-Control.html)

## 依赖

此包需要依赖 "gitpython"，一个用于与 git 仓库交互的 Python 库。安装它最简单的方法是安装 Evennia 的额外需求：

```
pip install evennia[extra]
```

如果您使用 `git` 安装，您也可以这样做：

- `cd` 到 Evennia 仓库的根目录。
- `pip install --upgrade -e .[extra]`

## 安装

此工具添加了一组简单的 'git' 命令。将模块导入到您的命令中，并将其添加到您的命令集以使其可用。

具体来说，在 `mygame/commands/default_cmdsets.py` 中：

```python
...
from evennia.contrib.utils.git_integration import GitCmdSet   # <---

class CharacterCmdset(default_cmds.Character_CmdSet):
    ...
    def at_cmdset_creation(self):
        ...
        self.add(GitCmdSet)  # <---

```

然后 `reload` 以使 git 命令可用。

## 用法

此工具仅在您要操作的目录是 git 目录时有效。如果不是，您将被提示使用以下命令在终端中将目录初始化为 git 仓库：

```
git init
git remote add origin 'link to your repository'
```

默认情况下，git 命令仅对具有开发者权限及以上的用户可用。您可以通过重写命令并将其锁定从 "cmd:pperm(Developer)" 更改为您选择的锁定来更改此设置。

支持的命令有：
* git status: 查看您的 git 仓库概况、本地更改的文件以及当前提交。
* git branch: 查看可供检出的分支。
* git checkout 'branch': 检出一个分支。
* git pull: 从当前分支拉取最新代码。

* 所有这些命令也可以用于 'evennia'，以实现与您的 Evennia 目录相关的相同功能。所以：
* git evennia status
* git evennia branch
* git evennia checkout 'branch'
* git evennia pull: 拉取最新的 Evennia 代码。

## 使用的设置

该工具使用 settings.py 中现有的 GAME_DIR 和 EVENNIA_DIR 设置。如果您有标准的目录设置，您不需要更改这些设置，它们应该已经存在，无需您进行任何设置。
