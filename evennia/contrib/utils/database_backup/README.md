# Database Backup Scheduler

Contribution by helpme (2024)

This module helps backup and restore your game world from database, as well as scheduling backups in-game. Backups are saved in your game's `server` folder. Database backups are *not* automatically uploaded to any cloud service, it is left to you to decide what to do with them (i.e. pushed to git, uploaded to a cloud service, downloaded to hard drive).

Backups can take place at any time, while restoring the game world from backup has to take place outside of game commands, during downtime, as documented below.

Currently, the sqlite3 (the evennia default) and postgresql databases are supported. Others are welcome to add more.

## Installation

This utility adds the `backup` command. Import the module into your commands and add it to your command set to make it available.

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

## Permissions

By default, the backup command is only available to those with Developer permissions and higher. You can change this by overriding the command and setting its locks from "cmd:pperm(Developer)" to the lock of your choice.

## Settings Used

This utility uses the settings.DATABASES dictionary.

## Restoration

Remember to `evennia stop` before restoring your db.

### Restoring sqlite3 (.db3)

* Copy the database backup you want to restore from back into the `server/` directory
* Rename the database backup to `evennia.db3` if you have not modified `settings.DATABASES`, otherwise whatever name is in your `settings.DATABASES` dictionary.

### Restoring postgres (.sql)

* Prepare the following variables
```
export DB_USER=db_user from your settings.DATABASES
export DB_NAME=db_name from your settings.DATABASES
export BACKUP_FILE=the path to the backup file you are restoring from
export PGPASSWORD=your db password

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