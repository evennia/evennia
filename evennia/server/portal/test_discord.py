"""Tests for Discord gateway reconnection and intentional disconnection."""

import json
from unittest import TestCase, skipIf
from unittest.mock import Mock, patch

from twisted.internet.task import Clock

from evennia.server.portal.portalsessionhandler import PortalSessionHandler

try:
    from evennia.server.portal.discord import (
        OP_INVALID_SESSION,
        OP_RECONNECT,
        DiscordWebsocketServerFactory,
    )
except ModuleNotFoundError as err:
    if err.name != "OpenSSL":
        raise
    DiscordWebsocketServerFactory = None


@skipIf(
    DiscordWebsocketServerFactory is None,
    "Discord tests require the optional pyopenssl dependency.",
)
class TestDiscordReconnect(TestCase):
    """Exercise the real factory retry loop without a database or network."""

    def setUp(self):
        """Create a connected bot with a deterministic reconnect clock."""
        portal = patch("evennia.EVENNIA_PORTAL_SERVICE")
        portal.start()
        self.addCleanup(portal.stop)
        self.sessions = PortalSessionHandler()
        self.factory = DiscordWebsocketServerFactory(self.sessions, uid=1)
        self.factory.clock = Clock()
        self.factory.jitter = 0
        self.factory.connector = Mock()
        self.client = self.factory.buildProtocol(None)
        self.client.sessid = 1
        self.client.sendClose = Mock()
        self.factory.bot = self.client
        self.sessions[1] = self.client

    def close_connection(self):
        """Deliver the protocol and factory callbacks for a closed transport."""
        self.client.onClose(False)
        self.factory.clientConnectionLost(self.factory.connector, None)

    def test_server_disconnect_stops_reconnecting(self):
        """A duplicate login rejected by the Server must stay disconnected."""
        reason = "Logged in from elsewhere. Disconnecting."
        self.sessions.server_disconnect(self.client, reason)
        self.close_connection()
        self.factory.clock.advance(120)

        self.client.sendClose.assert_called_once_with(self.client.CLOSE_STATUS_CODE_NORMAL, reason)
        self.factory.connector.connect.assert_not_called()
        self.assertNotIn(1, self.sessions)
        self.assertFalse(self.factory.clock.getDelayedCalls())

    def test_disconnect_cancels_pending_retry(self):
        """An explicit disconnect also cancels a retry already waiting to run."""
        self.close_connection()
        self.assertEqual(len(self.factory.clock.getDelayedCalls()), 1)

        self.client.disconnect()
        self.factory.clock.advance(120)

        self.factory.connector.connect.assert_not_called()
        self.assertFalse(self.factory.clock.getDelayedCalls())

    def test_connection_loss_reconnects(self):
        """An ordinary network failure still retries through the same factory."""
        self.close_connection()
        self.factory.clock.advance(120)

        self.factory.connector.connect.assert_called_once_with()
        self.assertNotIn(1, self.sessions)

    def test_gateway_requests_reconnect(self):
        """Discord reconnect and invalid-session messages keep retries enabled."""
        for opcode in (OP_RECONNECT, OP_INVALID_SESSION):
            with self.subTest(opcode=opcode):
                self.factory.connector.reset_mock()
                self.client.sendClose.reset_mock()
                self.sessions[1] = self.client
                self.client.onMessage(json.dumps({"op": opcode, "d": False}).encode(), False)
                self.close_connection()
                self.factory.clock.advance(120)

                self.factory.connector.connect.assert_called_once_with()
                self.assertNotIn(1, self.sessions)

    def test_missing_heartbeat_reconnects(self):
        """A missed heartbeat acknowledgement still initiates reconnection."""
        self.client.pending_heartbeat = True
        self.client.doHeartbeat()
        self.close_connection()
        self.factory.clock.advance(120)

        self.factory.connector.connect.assert_called_once_with()
        self.assertNotIn(1, self.sessions)
