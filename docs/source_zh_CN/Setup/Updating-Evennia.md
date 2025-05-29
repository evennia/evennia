# 更新 Evennia

当 Evennia 更新到新版本时，通常会在 [讨论论坛](github:discussions) 和 [开发博客](https://www.evennia.com/devblog/index.html) 上宣布。你也可以在 [GitHub](github:) 或通过我们的其他 [链接页面](../Links.md) 查看更改。

## 如果你通过 `pip` 安装

如果你按照[常规安装说明](./Installation.md)操作，以下是升级步骤：

1. 阅读 [changelog](../Coding/Changelog.md) 以了解更改内容，以及是否需要对游戏代码进行修改。
2. 如果使用 [virtualenv](#Installation-Git#virtualenv)，确保它是激活的。
3. `cd` 到你的游戏目录（例如 `mygame`）
4. `evennia stop`
5. `pip install --upgrade evennia`
6. `cd` 到你的游戏目录
7. `evennia migrate` - 这通常是安全的，但可以跳过，除非发布公告/changelog 特别要求。_忽略_ 关于运行 `makemigrations` 的警告，不应执行此操作！
8. `evennia start`

## 如果你通过 `git` 安装

这适用于你按照 [git 安装说明](./Installation-Git.md) 操作的情况。在 Evennia 1.0 之前，这是唯一的安装方式。

开发通常在 `main` 分支（最新稳定版）或 `develop`（实验版）进行。具体哪个分支为活跃的“最新”版本取决于时间点——发布后，`main` 会有更多更新，接近新发布时，`develop` 通常变化更快。

1. 阅读 [changelog](../Coding/Changelog.md) 以了解更改内容，以及是否需要对游戏代码进行修改。
2. 如果使用 [virtualenv](#Installation-Git#virtualenv)，确保它是激活的。
3. `cd` 到你的游戏目录（例如 `mygame`）
4. `evennia stop`
5. `cd` 到你在 git 安装过程中克隆的 `evennia` 仓库文件夹。
6. `git pull`
7. `pip install --upgrade -e .`  （记住末尾的 `.`！）
8. `cd` 回到你的游戏目录
9. `evennia migrate` - 这通常是安全的，但可以跳过，除非发布公告/changelog 特别要求。_忽略_ 关于运行 `makemigrations` 的警告，不应执行此操作！
10. `evennia start`

## 如果你通过 `docker` 安装

如果你按照 [docker 安装说明](./Installation-Docker.md) 操作，你需要为你想要的分支拉取最新的 docker 镜像：

- `docker pull evennia/evennia`  （`main` 分支）
- `docker pull evennia/evennia:develop`  （实验 `develop` 分支）

然后重启你的容器。

## 重置数据库

如果你想从头开始，不需要重新下载 Evennia。你只需清空数据库。

首先：

1. `cd` 到你的游戏目录（例如 `mygame`）
2. `evennia stop`

### SQLite3（默认）

```{sidebar} 提示
创建超级用户后，复制 `evennia.db3` 文件。当你想重置时（只要没有运行新的迁移），可以停止 evennia 并将该文件复制回 `evennia.db3`。这样你就不需要每次都运行相同的迁移和创建超级用户！
```

3. 删除文件 `mygame/server/evennia.db3`
4. `evennia migrate`
5. `evennia start`

### PostgreSQL

3. `evennia dbshell`  （打开 psql 客户端界面）
    ```
    psql> DROP DATABASE evennia;
    psql> exit
    ```
4. 你现在应该按照 [PostgreSQL 安装说明](./Choosing-a-Database.md#postgresql) 创建一个新的 evennia 数据库。
5. `evennia migrate`
6. `evennia start`

### MySQL/MariaDB

3. `evennia dbshell` （打开 mysql 客户端界面）
   ```
   mysql> DROP DATABASE evennia;
   mysql> exit
   ```
4. 你现在应该按照 [MySQL 安装说明](./Choosing-a-Database.md#mysql-mariadb) 创建一个新的 evennia 数据库。
5. `evennia migrate`
6. `evennia start`

### 什么是数据库迁移？

如果 Evennia 更新修改了数据库 *架构*（即数据在数据库中的存储方式），你必须相应地更新现有数据库以匹配更改。如果不这样做，更新后的 Evennia 会抱怨无法正确读取数据库。随着 Evennia 的成熟，架构更改应该会越来越少，但仍可能偶尔发生。

一种处理方法是手动将更改应用到数据库，使用数据库的命令行。这通常意味着添加/删除新表或字段，以及可能转换现有数据以匹配新 Evennia 版本的期望。显然，这很快就会变得繁琐且容易出错。如果你的数据库尚未包含任何关键内容，可能最简单的方法是重置并重新开始，而不是费心转换。

这时就需要 *迁移*。迁移会跟踪数据库架构的更改并自动为你应用它们。基本上，每当架构更改时，我们会随源代码分发小文件，称为“迁移”。这些文件准确地告诉系统如何实现更改，这样你就不必手动操作。当添加迁移时，我们会在 Evennia 的邮件列表和提交信息中告知你——然后你只需运行 `evennia migrate` 即可保持最新。
