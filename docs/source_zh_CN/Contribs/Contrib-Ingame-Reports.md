# 游戏内报告系统

由 InspectorCaracal 贡献，2024

这个贡献提供了一个游戏内报告系统，默认处理错误报告、玩家报告和创意提交。它还支持添加您自己的报告类型，或删除任何默认的报告类型。

每种类型的报告都有自己的命令用于提交新报告，并提供了一个管理员命令用于通过菜单管理报告。

## 安装

要安装报告贡献，只需将提供的 cmdset 添加到您的默认 AccountCmdSet：

```python
# 在 commands/default_cmdset.py 中

from evennia.contrib.base_systems.ingame_reports import ReportsCmdSet

class AccountCmdSet(default_cmds.AccountCmdSet):
    # ...

    def at_cmdset_creation(self):
        # ...
        self.add(ReportsCmdSet)
```

该贡献还有两个可选设置：`INGAME_REPORT_TYPES` 和 `INGAME_REPORT_STATUS_TAGS`。

`INGAME_REPORT_TYPES` 设置在“添加新类型的报告”部分中详细介绍。

`INGAME_REPORT_STATUS_TAGS` 设置在“管理报告”部分中介绍。

## 用法

默认情况下，以下报告类型可用：

* 错误：报告游戏过程中遇到的错误。
* 创意：提交游戏改进建议。
* 玩家：报告不当的玩家行为。

玩家可以通过每种报告类型的命令提交新报告，工作人员可以使用报告管理命令和菜单进行管理。

### 提交报告

玩家可以使用以下命令提交报告：

* `bug <text>` - 提交错误报告。可以选择包含目标 - `bug <target> = <text>` - 使开发者/构建者更容易追踪问题。
* `report <player> = <text>` - 报告玩家的不当或违规行为。*需要*提供目标 - 默认在账户中搜索。
* `idea <text>` - 提交一般建议，无需目标。它还有一个别名 `ideas`，允许您查看所有提交的创意。

### 管理报告

`manage reports` 命令允许工作人员通过启动管理菜单来查看和管理各种类型的报告。

此命令将根据可用的报告类型动态添加别名，每个命令字符串启动该特定报告类型的菜单。别名基于模式 `manage <report type>s` 构建 - 默认情况下，这意味着它使 `manage bugs`、`manage players` 和 `manage ideas` 可用，以及默认的 `manage reports`，例如 `manage bugs` 将启动 `bug` 类型报告的管理菜单。

除了查看现有报告外，菜单还允许您更改任何给定报告的状态。默认情况下，贡献包括两个不同的状态标签：`in progress` 和 `closed`。

> 注意：报告创建时没有状态标签，这被视为“开放”

如果您想为您的报告设置不同的状态集，可以将 `INGAME_REPORT_STATUS_TAGS` 定义为您的状态列表。

**示例**

```python
# 在 server/conf/settings.py 中

# 这将允许状态为 'in progress'、'rejected' 和 'completed'，而不使用贡献默认的 'closed'
INGAME_REPORT_STATUS_TAGS = ('in progress', 'rejected', 'completed')
```

### 添加新类型的报告

该贡献旨在使向系统添加新类型的报告尽可能简单，只需两个步骤：

1. 更新您的设置文件以包含 `INGAME_REPORT_TYPES` 设置。
2. 创建并添加新的 `ReportCmd` 到您的命令集中。

#### 更新您的设置

贡献可选地在您的 `settings.py` 中引用 `INGAME_REPORT_TYPES` 以查看哪些类型的报告可以管理。如果您想更改可用的报告类型，您需要定义此设置。

```python
# 在 server/conf/settings.py 中

# 这将包括贡献的报告类型以及自定义的 'complaint' 报告类型
INGAME_REPORT_TYPES = ('bugs', 'ideas', 'players', 'complaints')
```

您还可以使用此设置删除任何贡献的报告类型 - 贡献将在构建其 cmdset 时尊重此设置，无需额外步骤。

```python
# 在 server/conf/settings.py 中

# 这重新定义了设置以不包括 'ideas'，因此创意命令和报告将不可用
INGAME_REPORT_TYPES = ('bugs', 'players')
```

#### 创建新的 ReportCmd

`ReportCmdBase` 是一个父命令类，带有提交报告的主要功能。创建新的报告命令就像继承此类并定义几个类属性一样简单。

* `key` - 与其他命令相同，设置命令的可用键。如果未明确设置，它也充当报告类型。
* `report_type` - 此命令所针对的报告类型（例如 `player`）。如果您希望使用与键不同的字符串，则只需设置它。
* `report_locks` - 您希望应用于创建的报告的锁。默认为 `"read:pperm(Admin)"`
* `success_msg` - 提交此类型报告后发送给玩家的字符串。默认为 `"Your report has been filed."`
* `require_target`: 如果您的报告类型需要目标（例如玩家报告），请设置为 `True`。

> 注意：贡献自己的命令 - `CmdBug`、`CmdIdea` 和 `CmdReport` - 实现方式相同，因此您可以查看它们作为示例。

示例：

```python
from evennia.contrib.base_systems.ingame_reports.reports import ReportCmdBase

class CmdCustomReport(ReportCmdBase):
    """
    提交自定义报告

    用法:
        customreport <message>

    这是一个自定义报告类型。
    """

    key = "customreport"
    report_type = "custom"
    success_message = "You have successfully filed a custom report."
```

将此新命令添加到您的默认 cmdset 以启用提交您的新报告类型。


----

<small>此文档页面并非由 `evennia/contrib/base_systems/ingame_reports/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
