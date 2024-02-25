from evennia.contrib.base_systems.godotwebsocket.webclient import start_plugin_services
from evennia.server.portal.amp_server import AMPServerFactory

try:
    from django.utils.unittest import TestCase
except ImportError:
    from django.test import TestCase

try:
    from django.utils import unittest
except ImportError:
    import unittest

import json

import mock
from django.test import override_settings
from mock import MagicMock, Mock
from twisted.internet.base import DelayedCall
from twisted.test import proto_helpers

import evennia
from evennia.server.portal.portalsessionhandler import PortalSessionHandler
from evennia.server.portal.service import EvenniaPortalService
from evennia.utils.test_resources import BaseEvenniaTest


class TestGodotWebSocketClient(BaseEvenniaTest):
    @override_settings(
        GODOT_CLIENT_WEBSOCKET_CLIENT_INTERFACE="127.0.0.1", GODOT_CLIENT_WEBSOCKET_PORT="8988"
    )
    def setUp(self):
        super().setUp()
        self.portal = EvenniaPortalService()
        evennia.EVENNIA_PORTAL_SERVICE = self.portal
        self.amp_server_factory = AMPServerFactory(self.portal)
        self.amp_server = self.amp_server_factory.buildProtocol("127.0.0.1")
        start_plugin_services(self.portal)
        godot_ws_service = next(
            srv for srv in self.portal.services if srv.name.startswith("GodotWebSocket")
        )

        factory = godot_ws_service.args[1]
        self.proto = factory.protocol()
        self.proto.factory = factory

        evennia.PORTAL_SESSION_HANDLER = PortalSessionHandler()
        self.proto.factory.sessionhandler = evennia.PORTAL_SESSION_HANDLER
        self.proto.sessionhandler = evennia.PORTAL_SESSION_HANDLER
        self.proto.sessionhandler.portal = Mock()
        self.proto.transport = proto_helpers.StringTransport()
        # self.proto.transport = proto_helpers.FakeDatagramTransport()
        self.proto.transport.client = ["localhost"]
        self.proto.transport.setTcpKeepAlive = Mock()
        self.proto.state = MagicMock()
        self.addCleanup(self.proto.factory.sessionhandler.disconnect_all)
        DelayedCall.debug = True

    @mock.patch("evennia.server.portal.portalsessionhandler.reactor", new=MagicMock())
    def test_data_in(self):
        self.proto.sessionhandler.data_in = MagicMock()
        self.proto.onOpen()
        msg = json.dumps(["logged_in", (), {}]).encode()
        self.proto.onMessage(msg, isBinary=False)
        self.proto.sessionhandler.data_in.assert_called_with(self.proto, logged_in=[[], {}])
        msg = json.dumps(["text", ("|rRed Text|n",), {}]).encode()
        self.proto.onMessage(msg, isBinary=False)
        self.proto.sessionhandler.data_in.assert_called_with(
            self.proto, text=[["|rRed Text|n"], {}]
        )

    @mock.patch("evennia.server.portal.portalsessionhandler.reactor", new=MagicMock())
    def test_data_out(self):
        self.proto.onOpen()
        self.proto.sendLine = MagicMock()
        self.proto.sessionhandler.data_out(self.proto, text=[["|rRed Text|n"], {}])
        self.proto.sendLine.assert_called_with(
            json.dumps(["text", ["[color=#ff0000]Red Text[/color]"], {}])
        )
