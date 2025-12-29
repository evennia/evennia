from django.conf import settings

from evennia.comms.models import ChannelDB
from evennia import CmdSet, DefaultScript
from evennia.commands.default.muxcommand import MuxCommand
from evennia.utils.create import create_script
from evennia.utils import logger, search

import datetime
import os
import shutil
import subprocess
import sqlite3

_MUDINFO_CHANNEL = None
BACKUP_FOLDER = "server/backups"
DATETIME_FORMAT_STR = "%Y-%m-%d.%H_%M_%S"
DEFAULT_INTERVAL = 86400


class DatabaseBackupScript(DefaultScript):
    """
    The global script to backup the server on a schedule.

    It will be automatically created the first time the `backup` command is used.
    """

    def at_script_creation(self):
        super().at_script_creation()
        self.key = "db_backup_script"
        self.desc = "Database backups"
        self.persistent = True

    def log(self, message):
        global _MUDINFO_CHANNEL
        if not _MUDINFO_CHANNEL and settings.CHANNEL_MUDINFO:
            channels = search.search_channel(settings.CHANNEL_MUDINFO["key"])
            if channels:
                _MUDINFO_CHANNEL = channels[0]

        if _MUDINFO_CHANNEL:
            _MUDINFO_CHANNEL.msg(message)
        logger.log_sec(message)

    def backup_postgres(self, db_name, db_user, output_file_path):
        """
        Run `pg_dump` on the postgreSQL database and save the output.
        """

        output_file_path += ".sql"
        subprocess.run(
            ["pg_dump", "-U", db_user, "-F", "p", db_name],
            stdout=open(output_file_path, "w"),
            check=True,
        )
        self.log(f"|wpostgresql db backed up in: {BACKUP_FOLDER}|n")

    def backup_sqlite3(self, db_name, output_file_path):
        """
        Copy the sqlite3 db.
        """

        output_file_path += ".db3"
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        shutil.copy(db_name, output_file_path)

        # Check the integrity of the copied db
        con = sqlite3.connect(output_file_path)
        cur = con.cursor()
        try:
            cur.execute("PRAGMA integrity_check")
        except sqlite3.DatabaseError:
            self.log(f"|rsqlite3 db backup to {BACKUP_FOLDER} failed: integrity check failed|n")
            con.close()
            return
        self.log(f"|wsqlite3 db backed up in: {BACKUP_FOLDER}|n")

    def at_repeat(self):
        databases = settings.DATABASES
        db = databases["default"]
        engine = db.get("ENGINE")
        db_name = db.get("NAME")
        db_user = db.get("USER")

        try:
            # Create the output folder if it doesn't exist
            os.makedirs(BACKUP_FOLDER, exist_ok=True)
            output_file = datetime.datetime.now().replace(microsecond=0).isoformat()
            output_file_path = os.path.join(BACKUP_FOLDER, output_file)

            if "postgres" in engine:
                self.backup_postgres(db_name, db_user, output_file_path)
            elif "sqlite3" in engine:
                self.backup_sqlite3(db_name, output_file_path)

        except Exception as e:
            logger.log_err("Backup failed: {}".format(e))


class CmdBackup(MuxCommand):
    """
    Backup your database to the server/backups folder in your game directory.

    Usage:
      backup [interval in seconds] - Schedule a backup. The default interval is one day.
      backup/stop  - Stop the backup script (equivalent to scripts/delete #id)
      backup/force - Trigger a backup manually
    """

    key = "backup"
    aliases = "backups"
    locks = "cmd:pperm(Developer)"

    def get_latest_backup(self):
        """
        Returns:
            str: Name of the most recent backup
        """
        try:
            files = os.listdir(BACKUP_FOLDER)
            paths = [os.path.join(BACKUP_FOLDER, basename) for basename in files]
            last_backup = max(paths, key=os.path.getctime)
            return last_backup
        except Exception:
            return ""

    def create_script(self, interval):
        """Create new script. Deletes old script if it exists."""
        script = search.search_script("db_backup_script")
        if script:
            script[0].delete()
        create_script(DatabaseBackupScript, interval=interval)
        self.caller.msg(f"You have scheduled backups to run every {interval} seconds.")

    def get_script(self):
        """
        Returns:
            script: Existing script
        """
        script = search.search_script("db_backup_script")
        if script:
            return script[0]

    def func(self):
        """
        Database backup functionality
        """
        caller = self.caller
        args = self.args.strip()
        interval = int(args) if args.isnumeric() else DEFAULT_INTERVAL

        script = self.get_script()

        # Kill existing backup script
        if "stop" in self.switches:
            if not script:
                caller.msg("No existing db backup script to delete.")
                return
            script.delete()
            caller.msg("DB backup script deleted.")
            return

        # Create new backup script
        if not script:
            self.create_script(interval)
            return

        # Change backup script's interval (if the provided interval is different)
        original_interval = script.interval
        if args and original_interval != interval:
            self.create_script(interval)
            return

        if "force" in self.switches:
            # Manually trigger the backup
            script.at_repeat()
            return

        if self.get_latest_backup():
            caller.msg(f"Most recent database backup: {self.get_latest_backup()}.")
        else:
            caller.msg(f"No database backups found in {BACKUP_FOLDER}")

        caller.msg(
            f"Countdown till next scheduled backup: |x{datetime.timedelta(seconds=script.time_until_next_repeat())}|n. Use |wbackup/force|n to manually backup the database."
        )


class DbCmdSet(CmdSet):
    """
    Database backup command
    """

    def at_cmdset_creation(self):
        self.add(CmdBackup)
