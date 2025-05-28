# 升级现有安装

如果你已经在使用旧版本的 Evennia 并且有代码，这部分内容与你相关。如果你是新手，或者代码不多，可能更容易按照[安装说明](./Installation.md)重新开始，并手动复制内容。

## 从 Evennia v0.9.5 升级到 1.0+

### 升级 Evennia 库

在 1.0 之前，所有的 Evennia 安装都是 [Git 安装](./Installation-Git.md)。这些说明假设你已经克隆了 `evennia` 仓库，并使用了 virtualenv（最佳实践）。

- 确保通过在游戏目录中运行 `evennia stop` 完全停止 Evennia 0.9.5。
- 使用 `deactivate` 退出你当前激活的 virtualenv。
- 删除旧的 virtualenv `evenv` 文件夹，或者重命名它（以防你想继续使用 0.9.5 一段时间）。
- `cd` 到你的 `evennia/` 根目录（你应该看到 `docs/` 和 `bin/` 目录以及嵌套的 `evennia/` 文件夹）。
- `git pull`
- `git checkout main`（而不是 `0.9.5` 使用的 `master`）

从这里开始，按照 [Git 安装](./Installation-Git.md) 的步骤进行，但跳过克隆 Evennia（因为你已经有仓库了）。注意，如果你不需要或不想使用 git 跟踪最新变化，也不想为 Evennia 本身做贡献，你也可以按照正常的 [pip 安装](./Installation.md)。

### 升级你的游戏目录

如果你不需要保留现有游戏目录中的任何内容，可以按照正常的[安装说明](./Installation.md)开始一个新目录。如果你想保留/转换现有的游戏目录，请继续以下步骤。

- 首先，备份你现有的游戏目录！如果你使用版本控制，请确保提交当前状态。
- `cd` 到你现有的基于 0.9.5 的游戏文件夹（如 `mygame`）。
- 如果你更改了 `mygame/web`，请将文件夹重命名为 `web_0.9.5`。如果你没有更改任何内容（或没有需要保留的内容），可以完全删除它。
- 将 `evennia/evennia/game_template/web` 复制到 `mygame/`（例如使用 `cp -Rf` 或文件管理器）。这个新的 `web` 文件夹替换旧的，具有非常不同的结构。
- 可能需要替换/注释掉对已弃用的 [`django.conf.urls`](https://docs.djangoproject.com/en/4.1/ref/urls/#url) 的导入和调用。新的调用方式[在这里](https://docs.djangoproject.com/en/4.0/ref/urls/#django.urls.re_path)。
- 运行 `evennia migrate` - 注意这里看到一些警告是正常的，即使系统要求你也不要运行 `makemigrations`。
- 运行 `evennia start`

如果你在游戏目录中做了大量工作，可能需要对代码进行一些（希望是小的）更改，以便它能在 Evennia 1.0 中启动。以下是一些重要的注意事项：

- `evennia/contrib/` 文件夹的结构已更改 - 现在有了分类的子文件夹，因此你需要更新导入。
- 任何 `web` 的更改需要手动从备份中移回到 `web/` 的新结构中。
- 查看 [Evennia 1.0 更新日志](../Coding/Changelog.md) 了解所有更改。
