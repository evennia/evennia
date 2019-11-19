"""
Test initial startup procedure

"""

from mock import MagicMock, patch
from django.conf import settings
from django.test import TestCase

from evennia.server import initial_setup


class TestInitialSetup(TestCase):
    @patch("evennia.server.initial_setup.AccountDB")
    def test_get_god_account(self, mocked_accountdb):
        mocked_accountdb.objects.get = MagicMock(return_value=1)
        self.assertEqual(initial_setup.get_god_account(), 1)
        mocked_accountdb.objects.get.assert_called_with(id=1)
