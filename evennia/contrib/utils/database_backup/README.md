# Database Backup Scheduler

Contribution by helpme (2024)

This module schedules backups in-game, which saves a copy of your database to your game's `server/backups` folder. Database backups are *not* automatically uploaded to any cloud service, it is left to you to decide what to do with them (i.e. pushed to git, uploaded to the ether, downloaded to a hard drive).

Backups can take place at any time. Restoring the game world from backup takes place during downtime, as documented below.

Currently, the sqlite3 (the evennia default) and postgresql databases are supported. Others are welcome to add more.

## Installation

This utility adds the `backup` command. The `backup` command can be used to set up a scheduled backup script, or trigger the script to run immediately. The backup script makes a backup of your game world. Import the module into your commands and add it to your command set to make it available.

In `mygame/commands/default_cmdsets.py`:

```python
...
from evennia.contrib.utils.database_backup import DbCmdSet   # <---

class CharacterCmdset(default_cmds.Character_CmdSet):
    ...
    def at_cmdset_creation(self):
        ...
        self.add(DbCmdSet)  # <---

```

Then `reload` to make the `backup` command available.

If you prefer to run the script without the `backup` command, you can manage it as a global script in your settings:

```python
# in mygame/server/conf/settings.py

GLOBAL_SCRIPTS = {
    "backupscript": {
        "typeclass": "evennia.contrib.utils.database_backup.DatabaseBackupScript",
        "repeats": -1,
        "interval": 86400,
        "desc": "Database backup script"
    },
}
```

## Permissions

By default, the backup command is only available to those with Developer permissions and higher. You can change this by overriding the command and setting its locks from "cmd:pperm(Developer)" to the lock of your choice.

## Settings Used

This utility uses the settings.DATABASES dictionary.

## Restoration

Remember to `evennia stop` before restoring your db.

### Restoring sqlite3 (.db3)

* Copy the database backup you want to restore from back into the `server/` directory
* By default (unless you changed the name of the file in `settings DATABASES`), the game data is expected to be located in the sqlite3 file `mygame/server/evennia.db3`. Copy your backup file over this file to recover your backup.

### Restoring postgres (.sql)

* Prepare the following variables
```
export DB_USER=db_user # db_user from your settings.DATABASES
export DB_NAME=db_name # db_name from your settings.DATABASES
export BACKUP_FILE=backup_file_path # the path to the backup file you are restoring from
export PGPASSWORD=db_password # the password to your db

If you prefer not to export your password to an env variable, you can enter it when prompted instead.
```
* Run the following commands
```
# Drop the existing database if it exists
psql -U $DB_USER -c "DROP DATABASE IF EXISTS $DB_NAME;" || exit 1

# Recreate the database
psql -U $DB_USER -c "CREATE DATABASE $DB_NAME;" || exit 1

# Restore the database from the backup file
psql -U $DB_USER -d $DB_NAME -f $BACKUP_FILE || exit 1
```