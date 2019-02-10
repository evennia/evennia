"""
Test the main server component

"""

from unittest import TestCase
from mock import MagicMock, patch, DEFAULT, call
from evennia.utils.test_resources import unload_module


@patch("evennia.server.server.LoopingCall", new=MagicMock())
class TestServer(TestCase):
    """
    Test server module.

    """

    def setUp(self):
        from evennia.server import server
        self.server = server

    def test__server_maintenance_flush(self):
        with patch.multiple("evennia.server.server",
                            LoopingCall=DEFAULT,
                            Evennia=DEFAULT,
                            _FLUSH_CACHE=DEFAULT,
                            connection=DEFAULT,
                            _IDMAPPER_CACHE_MAXSIZE=1000,
                            _MAINTENANCE_COUNT=600 - 1,
                            ServerConfig=DEFAULT) as mocks:
            mocks['connection'].close = MagicMock()
            mocks['ServerConfig'].objects.conf = MagicMock(return_value=100)

            # flush cache
            self.server._server_maintenance()
            mocks['_FLUSH_CACHE'].assert_called_with(1000)

    def test__server_maintenance_validate_scripts(self):
        with patch.multiple("evennia.server.server",
                            LoopingCall=DEFAULT,
                            Evennia=DEFAULT,
                            _FLUSH_CACHE=DEFAULT,
                            connection=DEFAULT,
                            _IDMAPPER_CACHE_MAXSIZE=1000,
                            _MAINTENANCE_COUNT=3600 - 1,
                            ServerConfig=DEFAULT) as mocks:
            mocks['connection'].close = MagicMock()
            mocks['ServerConfig'].objects.conf = MagicMock(return_value=100)
            with patch("evennia.server.server.evennia.ScriptDB.objects.validate") as mock:
                self.server._server_maintenance()
                mocks['_FLUSH_CACHE'].assert_called_with(1000)
                mock.assert_called()

    def test__server_maintenance_channel_handler_update(self):
        with patch.multiple("evennia.server.server",
                            LoopingCall=DEFAULT,
                            Evennia=DEFAULT,
                            _FLUSH_CACHE=DEFAULT,
                            connection=DEFAULT,
                            _IDMAPPER_CACHE_MAXSIZE=1000,
                            _MAINTENANCE_COUNT=3700 - 1,
                            ServerConfig=DEFAULT) as mocks:
            mocks['connection'].close = MagicMock()
            mocks['ServerConfig'].objects.conf = MagicMock(return_value=100)
            with patch("evennia.server.server.evennia.CHANNEL_HANDLER.update") as mock:
                self.server._server_maintenance()
                mock.assert_called()

    def test__server_maintenance_close_connection(self):
        with patch.multiple("evennia.server.server",
                            LoopingCall=DEFAULT,
                            Evennia=DEFAULT,
                            _FLUSH_CACHE=DEFAULT,
                            connection=DEFAULT,
                            _IDMAPPER_CACHE_MAXSIZE=1000,
                            _MAINTENANCE_COUNT=(3600 * 7) - 1,
                            ServerConfig=DEFAULT) as mocks:
            mocks['connection'].close = MagicMock()
            mocks['ServerConfig'].objects.conf = MagicMock(return_value=100)
            self.server._server_maintenance()
            mocks['connection'].close.assert_called()

    def test__server_maintenance_idle_time(self):
        with patch.multiple("evennia.server.server",
                            LoopingCall=DEFAULT,
                            Evennia=DEFAULT,
                            _FLUSH_CACHE=DEFAULT,
                            connection=DEFAULT,
                            _IDMAPPER_CACHE_MAXSIZE=1000,
                            _MAINTENANCE_COUNT=(3600 * 7) - 1,
                            SESSIONS=DEFAULT,
                            _IDLE_TIMEOUT=10,
                            time=DEFAULT,
                            ServerConfig=DEFAULT) as mocks:
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

            mocks['time'].time = MagicMock(return_value=1000)

            mocks['ServerConfig'].objects.conf = MagicMock(return_value=100)
            mocks["SESSIONS"].values = MagicMock(return_value=[sess1, sess2, sess3, sess4])
            mocks["SESSIONS"].disconnect = MagicMock()

            self.server._server_maintenance()
            reason = "idle timeout exceeded"
            calls = [call(sess1, reason=reason), call(sess4, reason=reason)]
            mocks["SESSIONS"].disconnect.assert_has_calls(calls, any_order=True)

    def test_evennia_start(self):
        with patch.multiple("evennia.server.server",
                            time=DEFAULT,
                            service=DEFAULT) as mocks:

            mocks['time'].time = MagicMock(return_value=1000)
            evennia = self.server.Evennia(MagicMock())
            self.assertEqual(evennia.start_time, 1000)

    def test_update_defaults(self):
        evennia = self.server.Evennia(MagicMock())
        evennia.update_defaults()

    def test_initial_setup(self):
        from evennia.utils.create import create_account

        acct = create_account("TestSuperuser", "test@test.com", "testpassword",
                              is_superuser=True)

        with patch.multiple("evennia.server.initial_setup",
                            reset_server=DEFAULT,
                            AccountDB=DEFAULT) as mocks:
            mocks['AccountDB'].objects.get = MagicMock(return_value=acct)
            evennia = self.server.Evennia(MagicMock())
            evennia.run_initial_setup()
