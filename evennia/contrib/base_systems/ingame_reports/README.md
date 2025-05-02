# In-Game Reporting System

Contrib by InspectorCaracal, 2024

This contrib provides an in-game reports system, handling bug reports, player reports, and idea submissions by default. It also supports adding your own types of reports, or removing any of the default report types.

Each type of report has its own command for submitting new reports, and an admin command is also provided for managing the reports through a menu.

## Installation

To install the reports contrib, just add the provided cmdset to your default AccountCmdSet:

```python
# in commands/default_cmdset.py

from evennia.contrib.base_systems.ingame_reports import ReportsCmdSet

class AccountCmdSet(default_cmds.AccountCmdSet):
    # ...

    def at_cmdset_creation(self):
        # ...
        self.add(ReportsCmdSet)
```

The contrib also has two optional settings: `INGAME_REPORT_TYPES` and `INGAME_REPORT_STATUS_TAGS`.

The `INGAME_REPORT_TYPES` setting is covered in detail in the section "Adding new types of reports".

The `INGAME_REPORT_STATUS_TAGS` setting is covered in the section "Managing reports".

## Usage

By default, the following report types are available:

* Bugs: Report bugs encountered during gameplay.
* Ideas: Submit suggestions for game improvement.
* Players: Report inappropriate player behavior.

Players can submit new reports through the command for each report type, and staff are given access to a report-management command and menu.

### Submitting reports

Players can submit reports using the following commands:

* `bug <text>` - Files a bug report. An optional target can be included - `bug <target> = <text>` - making it easier for devs/builders to track down issues.
* `report <player> = <text>` - Reports a player for inappropriate or rule-breaking behavior. *Requires* a target to be provided - it searches among accounts by default.
* `idea <text>` - Submits a general suggestion, with no target. It also has an alias of `ideas` which allows you to view all of your submitted ideas.

### Managing reports

The `manage reports` command allows staff to review and manage the various types of reports by launching a management menu.

This command will dynamically add aliases to itself based on the types of reports available, with each command string launching a menu for that particular report type. The aliases are built on the pattern `manage <report type>s` - by default, this means it makes `manage bugs`, `manage players`, and `manage ideas` available along with the default `manage reports`, and that e.g. `manage bugs` will launch the management menu for `bug`-type reports.

Aside from reading over existing reports, the menu allows you to change the status of any given report. By default, the contrib includes two different status tags: `in progress` and `closed`.

> Note: A report is created with no status tags, which is considered "open"

If you want a different set of statuses for your reports, you can define the `INGAME_REPORT_STATUS_TAGS` to your list of statuses.

**Example**

```python
# in server/conf/settings.py

# this will allow for the statuses of 'in progress', 'rejected', and 'completed', without the contrib-default of 'closed'
INGAME_REPORT_STATUS_TAGS = ('in progress', 'rejected', 'completed')
```

### Adding new types of reports

The contrib is designed to make adding new types of reports to the system as simple as possible, requiring only two steps:

1. Update your settings file to include an `INGAME_REPORT_TYPES` setting.
2. Create and add a new `ReportCmd` to your command set.

#### Update your settings

The contrib optionally references `INGAME_REPORT_TYPES` in your `settings.py` to see which types of reports can be managed. If you want to change the available report types, you'll need to define this setting.

```python
# in server/conf/settings.py

# this will include the contrib's report types as well as a custom 'complaint' report type
INGAME_REPORT_TYPES = ('bugs', 'ideas', 'players', 'complaints')
```

You can also use this setting to remove any of the contrib's report types - the contrib will respect this setting when building its cmdset with no additional steps.

```python
# in server/conf/settings.py

# this redefines the setting to not include 'ideas', so the ideas command and reports won't be available
INGAME_REPORT_TYPES = ('bugs', 'players')
```

#### Create a new ReportCmd

`ReportCmdBase` is a parent command class which comes with the main functionality for submitting reports. Creating a new reporting command is as simple as inheriting from this class and defining a couple of class attributes.

* `key` - This is the same as for any other command, setting the command's usable key. It also acts as the report type if that isn't explicitly set.
* `report_type` - The type of report this command is for (e.g. `player`). You only need to set it if you want a different string from the key.
* `report_locks` - The locks you want applied to the created reports. Defaults to `"read:pperm(Admin)"`
* `success_msg` - The string which is sent to players after submitting a report of this type. Defaults to `"Your report has been filed."`
* `require_target`: Set to `True` if your report type requires a target (e.g. player reports).

> Note: The contrib's own commands - `CmdBug`, `CmdIdea`, and `CmdReport` - are implemented the same way, so you can review them as examples.

Example:

```python
from evennia.contrib.base_systems.ingame_reports.reports import ReportCmdBase

class CmdCustomReport(ReportCmdBase):
    """
    file a custom report

    Usage:
        customreport <message>

    This is a custom report type.
    """

    key = "customreport"
    report_type = "custom"
    success_message = "You have successfully filed a custom report."
```

Add this new command to your default cmdset to enable filing your new report type.
