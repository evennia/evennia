"""
Test the main server component

"""

from unittest import TestCase

from django.test import override_settings
from mock import DEFAULT, MagicMock, call, patch


@patch("evennia.server.server.LoopingCall", new=MagicMock())
class TestServer(TestCase):
    """
    Test server module.

    """

    def setUp(self):
        from evennia.server import server

        self.server = server

    def test__server_maintenance_reset(self):
        with patch.multiple(
            "evennia.server.server",
            LoopingCall=DEFAULT,
            Evennia=DEFAULT,
            _FLUSH_CACHE=DEFAULT,
            connection=DEFAULT,
            _IDMAPPER_CACHE_MAXSIZE=1000,
            _MAINTENANCE_COUNT=0,
            ServerConfig=DEFAULT,
        ) as mocks:
            mocks["connection"].close = MagicMock()
            mocks["ServerConfig"].objects.conf = MagicMock(return_value=456)

            # flush cache
            self.server._server_maintenance()
            mocks["ServerConfig"].objects.conf.assert_called_with("runtime", 456)

    def test__server_maintenance_flush(self):
        with patch.multiple(
            "evennia.server.server",
            LoopingCall=DEFAULT,
            Evennia=DEFAULT,
            _FLUSH_CACHE=DEFAULT,
            connection=DEFAULT,
            _IDMAPPER_CACHE_MAXSIZE=1000,
            _MAINTENANCE_COUNT=5 - 1,
            ServerConfig=DEFAULT,
        ) as mocks:
            mocks["connection"].close = MagicMock()
            mocks["ServerConfig"].objects.conf = MagicMock(return_value=100)

            # flush cache
            self.server._server_maintenance()
            mocks["_FLUSH_CACHE"].assert_called_with(1000)

    def test__server_maintenance_close_connection(self):
        with patch.multiple(
            "evennia.server.server",
            LoopingCall=DEFAULT,
            Evennia=DEFAULT,
            _FLUSH_CACHE=DEFAULT,
            connection=DEFAULT,
            _IDMAPPER_CACHE_MAXSIZE=1000,
            _MAINTENANCE_COUNT=(60 * 7) - 1,
            _LAST_SERVER_TIME_SNAPSHOT=0,
            ServerConfig=DEFAULT,
        ) as mocks:
            mocks["connection"].close = MagicMock()
            mocks["ServerConfig"].objects.conf = MagicMock(return_value=100)
            self.server._server_maintenance()
            mocks["connection"].close.assert_called()

    def test__server_maintenance_idle_time(self):
        with patch.multiple(
            "evennia.server.server",
            LoopingCall=DEFAULT,
            Evennia=DEFAULT,
            _FLUSH_CACHE=DEFAULT,
            connection=DEFAULT,
            _IDMAPPER_CACHE_MAXSIZE=1000,
            _MAINTENANCE_COUNT=(3600 * 7) - 1,
            _LAST_SERVER_TIME_SNAPSHOT=0,
            SESSIONS=DEFAULT,
            _IDLE_TIMEOUT=10,
            time=DEFAULT,
            ServerConfig=DEFAULT,
        ) as mocks:
            sess1 = MagicMock()
            sess2 = MagicMock()
            sess3 = MagicMock()
            sess4 = MagicMock()
            sess1.cmd_last = 100  # should time out
            sess2.cmd_last = 999  # should not time out
            sess3.cmd_last = 100  # should not time (due to account)
            sess4.cmd_last = 100  # should time out (due to access)
            sess1.account = None
            sess2.account = None
            sess3.account = MagicMock()
            sess3.account = MagicMock()
            sess4.account.access = MagicMock(return_value=False)

            mocks["time"].time = MagicMock(return_value=1000)

            mocks["ServerConfig"].objects.conf = MagicMock(return_value=100)
            mocks["SESSIONS"].values = MagicMock(return_value=[sess1, sess2, sess3, sess4])
            mocks["SESSIONS"].disconnect = MagicMock()

            self.server._server_maintenance()
            reason = "idle timeout exceeded"
            calls = [call(sess1, reason=reason), call(sess4, reason=reason)]
            mocks["SESSIONS"].disconnect.assert_has_calls(calls, any_order=True)

    def test_evennia_start(self):
        with patch.multiple("evennia.server.server", time=DEFAULT, service=DEFAULT) as mocks:

            mocks["time"].time = MagicMock(return_value=1000)
            evennia = self.server.Evennia(MagicMock())
            self.assertEqual(evennia.start_time, 1000)

    @patch("evennia.objects.models.ObjectDB")
    @patch("evennia.server.server.AccountDB")
    @patch("evennia.server.server.ScriptDB")
    @patch("evennia.comms.models.ChannelDB")
    def test_update_defaults(self, mockchan, mockscript, mockacct, mockobj):
        with patch.multiple("evennia.server.server", ServerConfig=DEFAULT) as mocks:

            mockchan.objects.filter = MagicMock()
            mockscript.objects.filter = MagicMock()
            mockacct.objects.filter = MagicMock()
            mockobj.objects.filter = MagicMock()

            # fake mismatches
            settings_names = (
                "CMDSET_CHARACTER",
                "CMDSET_ACCOUNT",
                "BASE_ACCOUNT_TYPECLASS",
                "BASE_OBJECT_TYPECLASS",
                "BASE_CHARACTER_TYPECLASS",
                "BASE_ROOM_TYPECLASS",
                "BASE_EXIT_TYPECLASS",
                "BASE_SCRIPT_TYPECLASS",
                "BASE_CHANNEL_TYPECLASS",
            )
            fakes = {name: "Dummy.path" for name in settings_names}

            def _mock_conf(key, *args):
                return fakes[key]

            mocks["ServerConfig"].objects.conf = _mock_conf

            evennia = self.server.Evennia(MagicMock())
            evennia.update_defaults()

            mockchan.objects.filter.assert_called()
            mockscript.objects.filter.assert_called()
            mockacct.objects.filter.assert_called()
            mockobj.objects.filter.assert_called()

    def test_initial_setup(self):
        from evennia.utils.create import create_account

        acct = create_account("TestSuperuser", "test@test.com", "testpassword", is_superuser=True)

        with patch.multiple(
            "evennia.server.initial_setup", reset_server=DEFAULT, AccountDB=DEFAULT
        ) as mocks:
            mocks["AccountDB"].objects.get = MagicMock(return_value=acct)
            evennia = self.server.Evennia(MagicMock())
            evennia.run_initial_setup()
        acct.delete()

    def test_initial_setup_retry(self):
        from evennia.utils.create import create_account

        acct = create_account("TestSuperuser2", "test@test.com", "testpassword", is_superuser=True)

        with patch.multiple(
            "evennia.server.initial_setup",
            ServerConfig=DEFAULT,
            reset_server=DEFAULT,
            AccountDB=DEFAULT,
        ) as mocks:
            mocks["AccountDB"].objects.get = MagicMock(return_value=acct)
            # a last_initial_setup_step > 0
            mocks["ServerConfig"].objects.conf = MagicMock(return_value=4)
            evennia = self.server.Evennia(MagicMock())
            evennia.run_initial_setup()
        acct.delete()

    @patch("evennia.server.server.INFO_DICT", {"test": "foo"})
    def test_get_info_dict(self):
        evennia = self.server.Evennia(MagicMock())
        self.assertEqual(evennia.get_info_dict(), {"test": "foo"})


class TestInitHooks(TestCase):
    def setUp(self):

        from evennia.server import server
        from evennia.utils import create

        self.server = server

        self.obj1 = create.object(key="HookTestObj1")
        self.obj2 = create.object(key="HookTestObj2")
        self.acct1 = create.account("HookAcct1", "hooktest1@test.com", "testpasswd")
        self.acct2 = create.account("HookAcct2", "hooktest2@test.com", "testpasswd")
        self.chan1 = create.channel("Channel1")
        self.chan2 = create.channel("Channel2")
        self.script1 = create.script(key="script1")
        self.script2 = create.script(key="script2")

        self.obj1.at_init = MagicMock()
        self.obj2.at_init = MagicMock()
        self.acct1.at_init = MagicMock()
        self.acct2.at_init = MagicMock()
        self.chan1.at_init = MagicMock()
        self.chan2.at_init = MagicMock()
        self.script1.at_init = MagicMock()
        self.script2.at_init = MagicMock()

    def tearDown(self):
        self.obj1.delete()
        self.obj2.delete()
        self.acct1.delete()
        self.acct2.delete()
        self.chan1.delete()
        self.chan2.delete()
        self.script1.delete()
        self.script2.delete()

    @override_settings(_TEST_ENVIRONMENT=True)
    def test_run_init_hooks(self):

        evennia = self.server.Evennia(MagicMock())

        evennia.at_server_reload_start = MagicMock()
        evennia.at_server_cold_start = MagicMock()

        evennia.run_init_hooks("reload")
        evennia.run_init_hooks("reset")
        evennia.run_init_hooks("shutdown")

        self.acct1.at_init.assert_called()
        self.acct2.at_init.assert_called()
        self.obj1.at_init.assert_called()
        self.obj2.at_init.assert_called()
        self.chan1.at_init.assert_called()
        self.chan2.at_init.assert_called()
        self.script1.at_init.assert_called()
        self.script2.at_init.assert_called()

        evennia.at_server_reload_start.assert_called()
        evennia.at_server_cold_start.assert_called()
