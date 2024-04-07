"""
Test the main server component

"""

from unittest import TestCase

from django.test import override_settings
from mock import DEFAULT, MagicMock, call, patch

import evennia


@patch("evennia.server.service.LoopingCall", new=MagicMock())
class TestServer(TestCase):
    """
    Test server module.

    """

    def setUp(self):
        # Running this first line ensures that the EVENNIA_SERVICE is instantiated.
        from evennia.server import server

        self.server = evennia.EVENNIA_SERVER_SERVICE

    @override_settings(IDMAPPER_CACHE_MAXSIZE=1000)
    def test__server_maintenance_reset(self):
        with (
            patch.object(self.server, "_flush_cache", new=MagicMock()) as mockflush,
            patch.object(evennia, "ServerConfig", new=MagicMock()) as mockconf,
            patch.multiple(
                "evennia.server.service",
                LoopingCall=DEFAULT,
                connection=DEFAULT,
            ) as mocks,
        ):
            self.server.maintenance_count = 0

            mocks["connection"].close = MagicMock()
            mockconf.objects.conf = MagicMock(return_value=456)

            # flush cache
            self.server.server_maintenance()
            mockconf.objects.conf.assert_called_with("runtime", 456)

    @override_settings(IDMAPPER_CACHE_MAXSIZE=1000)
    def test__server_maintenance_flush(self):
        with (
            patch.multiple(
                "evennia.server.service",
                LoopingCall=DEFAULT,
                connection=DEFAULT,
            ) as mocks,
            patch.object(evennia, "ServerConfig", new=MagicMock()) as mockconf,
            patch.object(self.server, "_flush_cache", new=MagicMock()) as mockflush,
        ):
            mocks["connection"].close = MagicMock()
            mockconf.objects.conf = MagicMock(return_value=100)
            self.server.maintenance_count = 5 - 1
            # flush cache
            self.server.server_maintenance()
            self.server._flush_cache.assert_called_with(1000)

    @override_settings(IDMAPPER_CACHE_MAXSIZE=1000)
    def test__server_maintenance_close_connection(self):
        with (
            patch.multiple(
                "evennia.server.service",
                LoopingCall=DEFAULT,
                connection=DEFAULT,
            ) as mocks,
            patch.object(evennia, "ServerConfig", new=MagicMock()) as mockconf,
        ):
            self.server._flush_cache = MagicMock()
            self.server.maintenance_count = (60 * 7) - 1
            self.server._last_server_time_snapshot = 0
            mocks["connection"].close = MagicMock()
            mockconf.objects.conf = MagicMock(return_value=100)
            self.server.server_maintenance()
            mocks["connection"].close.assert_called()

    @override_settings(IDLE_TIMEOUT=10)
    def test__server_maintenance_idle_time(self):
        with (
            patch.multiple(
                "evennia.server.service",
                LoopingCall=DEFAULT,
                connection=DEFAULT,
                time=DEFAULT,
            ) as mocks,
            patch.object(evennia, "ServerConfig", new=MagicMock()) as mockconf,
            patch.object(evennia, "SESSION_HANDLER", new=MagicMock()) as mocksess,
        ):
            self.server.maintenance_count = (3600 * 7) - 1
            self.server._last_server_time_snapshot = 0
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

            mockconf.objects.conf = MagicMock(return_value=100)
            mocksess.values = MagicMock(return_value=[sess1, sess2, sess3, sess4])
            mocksess.disconnect = MagicMock()

            self.server.server_maintenance()
            reason = "idle timeout exceeded"
            calls = [call(sess1, reason=reason), call(sess4, reason=reason)]
            mocksess.disconnect.assert_has_calls(calls, any_order=True)

    def test_update_defaults(self):
        with (
            patch.object(evennia, "ObjectDB", new=MagicMock()) as mockobj,
            patch.object(evennia, "AccountDB", new=MagicMock()) as mockacc,
            patch.object(evennia, "ScriptDB", new=MagicMock()) as mockscr,
            patch.object(evennia, "ChannelDB", new=MagicMock()) as mockchan,
            patch.object(evennia, "ServerConfig", new=MagicMock()) as mockconf,
        ):
            for m in (mockscr, mockobj, mockacc, mockchan):
                m.objects.filter = MagicMock()

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

            mockconf.objects.conf = _mock_conf

            self.server.update_defaults()

            for m in (mockscr, mockobj, mockacc, mockchan):
                m.objects.filter.assert_called()

    @override_settings(TEST_ENVIRONMENT=True)
    def test_initial_setup(self):
        from evennia.utils.create import create_account

        acct = create_account("TestSuperuser", "test@test.com", "testpassword", is_superuser=True)

        with patch.multiple(
            "evennia.server.initial_setup", reset_server=DEFAULT, AccountDB=DEFAULT
        ) as mocks:
            mocks["AccountDB"].objects.get = MagicMock(return_value=acct)
            self.server.run_initial_setup()
        acct.delete()

    @override_settings(TEST_ENVIRONMENT=True)
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
            self.server.run_initial_setup()
        acct.delete()

    def test_get_info_dict(self):
        with patch.object(self.server, "get_info_dict", return_value={"test": "foo"}) as mocks:
            self.assertEqual(self.server.get_info_dict(), {"test": "foo"})


class TestInitHooks(TestCase):
    def setUp(self):
        from evennia.server import server
        from evennia.utils import create

        self.server = evennia.EVENNIA_SERVER_SERVICE

        self.obj1 = create.object(key="HookTestObj1")
        self.obj2 = create.object(key="HookTestObj2")
        self.acct1 = create.account("HookAcct1", "hooktest1@test.com", "testpasswd")
        self.acct2 = create.account("HookAcct2", "hooktest2@test.com", "testpasswd")
        self.chan1 = create.channel("Channel1")
        self.chan2 = create.channel("Channel2")
        self.script1 = create.script(key="script1")
        self.script2 = create.script(key="script2")

        self.objects = [
            self.obj1,
            self.obj2,
            self.acct1,
            self.acct2,
            self.chan1,
            self.chan2,
            self.script1,
            self.script2,
        ]

        for obj in self.objects:
            obj.at_init = MagicMock()

    def tearDown(self):
        for obj in self.objects:
            obj.delete()

    @override_settings(TEST_ENVIRONMENT=True)
    def test_run_init_hooks(self):
        with (
            patch.object(self.server, "at_server_reload_start", new=MagicMock()) as reload,
            patch.object(self.server, "at_server_cold_start", new=MagicMock()) as cold,
        ):
            self.server.run_init_hooks("reload")
            self.server.run_init_hooks("reset")
            self.server.run_init_hooks("shutdown")

            for obj in self.objects:
                obj.at_init.assert_called()

            for hook in (reload, cold):
                hook.assert_called()
