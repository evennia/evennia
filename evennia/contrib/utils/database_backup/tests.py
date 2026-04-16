"""
Tests for database backups.
"""

import evennia.contrib.utils.database_backup.database_backup as backup
from evennia.commands.default.tests import BaseEvenniaCommandTest
from unittest.mock import patch
from evennia.utils import search
import subprocess, os, tempfile, sqlite3

EXCEPTION_STR = "failed"


class TestDatabaseBackupScript(BaseEvenniaCommandTest):
    mocked_db_setting_postgres = patch(
        "django.conf.settings.DATABASES",
        {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": "fake_name",
                "USER": "fake_user",
            }
        },
    )
    mocked_db_setting_sqlite = patch(
        "django.conf.settings.DATABASES",
        {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": "fake_name",
            }
        },
    )
    mocked_db_setting_unsupported = patch(
        "django.conf.settings.DATABASES",
        {
            "default": {
                "ENGINE": "django.db.backends.oracle",
                "NAME": "fake_name",
                "USER": "fake_user",
            }
        },
    )

    def setUp(self):
        super().setUp()
        self._tmp_dir = tempfile.TemporaryDirectory()
        self._backup_folder_patch = patch.object(backup, "BACKUP_FOLDER", self._tmp_dir.name)
        self._backup_folder_patch.start()

    def tearDown(self):
        super().tearDown()
        script = search.search_script("db_backup_script")
        if script:
            script[0].delete()
        self._backup_folder_patch.stop()
        self._tmp_dir.cleanup()

    @mocked_db_setting_sqlite
    @patch("sqlite3.connect")
    @patch("evennia.utils.logger.log_sec")
    def test_sqlite_success(self, mock_logger, mock_connect):
        self.call(
            backup.CmdBackup(),
            "300",
            "You have scheduled backups to run every 300 seconds.",
            caller=self.char1,
        )
        self.call(backup.CmdBackup(), "/force", "", caller=self.char1)
        mock_logger.assert_called_with(f"|wsqlite3 db backed up in: {backup.BACKUP_FOLDER}|n")
        self.call(
            backup.CmdBackup(),
            "/stop",
            "DB backup script deleted.",
            caller=self.char1,
        )

    @mocked_db_setting_sqlite
    @patch("sqlite3.connect")
    @patch("evennia.utils.logger.log_err")
    def test_sqlite_failure(self, mock_logger, mock_connect):
        mock_connect.side_effect = Exception(EXCEPTION_STR)
        self.call(
            backup.CmdBackup(),
            "",
            "You have scheduled backups to run every 86400 seconds.",
            caller=self.char1,
        )
        mock_logger.assert_called_with(f"Backup failed: {EXCEPTION_STR}")

    @mocked_db_setting_postgres
    @patch("subprocess.run")
    @patch("evennia.utils.logger.log_sec")
    def test_postgres_success(self, mock_logger, mock_run):
        mock_run.return_value.returncode = 0

        self.call(
            backup.CmdBackup(),
            "",
            "You have scheduled backups to run every 86400 seconds.",
            caller=self.char1,
        )
        mock_logger.assert_called_with(f"|wpostgresql db backed up in: {backup.BACKUP_FOLDER}|n")

    @mocked_db_setting_postgres
    @patch("subprocess.run")
    @patch("evennia.utils.logger.log_err")
    def test_postgres_failure(self, mock_logger, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.side_effect = Exception(EXCEPTION_STR)

        self.call(
            backup.CmdBackup(),
            "",
            "You have scheduled backups to run every 86400 seconds.",
            caller=self.char1,
        )
        mock_logger.assert_called_with(f"Backup failed: {EXCEPTION_STR}")

    @mocked_db_setting_sqlite
    @patch("sqlite3.connect")
    @patch("shutil.copy")
    @patch("evennia.utils.logger.log_sec")
    def test_sqlite_force_no_existing_script(self, mock_logger, mock_copy, mock_connect):
        """backup/force should create the script if it doesn't exist, then run it."""
        mock_cursor = mock_connect.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = ("ok",)
        self.call(
            backup.CmdBackup(),
            "/force",
            "You have scheduled backups to run every 86400 seconds.",
            caller=self.char1,
        )
        mock_logger.assert_called_with(f"|wsqlite3 db backed up in: {backup.BACKUP_FOLDER}|n")

    @mocked_db_setting_unsupported
    def test_unsupported_engine(self):
        """Unsupported DB engine should message the caller and not attempt a backup."""
        self.call(
            backup.CmdBackup(),
            "/force",
            "Database backup failed: unsupported engine 'django.db.backends.oracle'. Contrib supports postgres and sqlite3.",
            caller=self.char1,
        )

    @mocked_db_setting_postgres
    @patch("subprocess.run")
    @patch("evennia.utils.logger.log_err")
    def test_postgres_failure_cleans_up(self, mock_logger, mock_run):
        """A failed pg_dump should not leave a partial .sql file behind."""
        self.call(
            backup.CmdBackup(),
            "",
            "You have scheduled backups to run every 86400 seconds.",
            caller=self.char1,
        )
        mock_run.side_effect = subprocess.CalledProcessError(1, "pg_dump")
        self.call(backup.CmdBackup(), "/force", "", caller=self.char1)
        sql_files = (
            [f for f in os.listdir(backup.BACKUP_FOLDER) if f.endswith(".sql")]
            if os.path.exists(backup.BACKUP_FOLDER)
            else []
        )
        self.assertEqual(sql_files, [])

    @mocked_db_setting_sqlite
    @patch("os.remove")
    @patch("sqlite3.connect")
    @patch("evennia.utils.logger.log_sec")
    def test_sqlite_corrupt_backup_cleans_up(self, mock_logger, mock_connect, mock_remove):
        """A corrupt sqlite backup should be deleted and log a failure."""
        self.call(
            backup.CmdBackup(),
            "",
            "You have scheduled backups to run every 86400 seconds.",
            caller=self.char1,
        )
        mock_connect.return_value.backup.side_effect = sqlite3.DatabaseError("corrupt")
        self.call(backup.CmdBackup(), "/force", "", caller=self.char1)
        mock_remove.assert_called_once()
        mock_logger.assert_called_with(f"|rsqlite3 db backup to {backup.BACKUP_FOLDER} failed|n")
