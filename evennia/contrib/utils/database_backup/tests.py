"""
Tests for database backups.
"""

import evennia.contrib.utils.database_backup.database_backup as backup
from evennia.commands.default.tests import BaseEvenniaCommandTest
from unittest.mock import patch

EXCEPTION_STR = "failed"


class TestDatabaseBackupScript(BaseEvenniaCommandTest):
    mocked_db_setting_postgres = patch(
        "django.conf.settings.DATABASES",
        {
            "default": {
                "ENGINE": "django.db.backends.postgresql_psycopg2",
                "NAME": "fake_name",
                "USER": "fake_user",
            }
        },
    )

    def setUp(self):
        super().setUp()

    @patch("shutil.copy")
    @patch("evennia.utils.logger.log_sec")
    def test_sqlite_success(self, mock_logger, mock_copy):
        mock_copy.return_value.returncode = 0
        self.call(
            backup.CmdBackup(),
            "300",
            "You have scheduled backups to run every 300 seconds.",
            caller=self.char1,
        )

        mock_logger.assert_called_with(f"|wsqlite3 db backed up in: {backup.BACKUP_FOLDER}|n")

        self.call(
            backup.CmdBackup(),
            "/stop",
            "DB backup script deleted.",
            caller=self.char1,
        )

    @patch("shutil.copy")
    @patch("evennia.utils.logger.log_err")
    def test_sqlite_failure(self, mock_logger, mock_copy):
        mock_copy.return_value.returncode = 1
        mock_copy.side_effect = Exception(EXCEPTION_STR)

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
