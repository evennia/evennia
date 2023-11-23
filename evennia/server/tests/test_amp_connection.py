"""
Test AMP client

"""

import pickle
from unittest import TestCase
from unittest.mock import MagicMock, patch

from model_mommy import mommy
from twisted.internet.base import DelayedCall
from twisted.trial.unittest import TestCase as TwistedTestCase

import evennia
from evennia.server import amp_client, server, serversession, session
from evennia.server.portal import amp, amp_server, portal
from evennia.server.portal.portalsessionhandler import PortalSessionHandler
from evennia.server.portal.service import EvenniaPortalService
from evennia.server.service import EvenniaServerService
from evennia.server.sessionhandler import ServerSessionHandler
from evennia.utils import create

DelayedCall.debug = True


# @patch("evennia.server.initial_setup.get_god_account",
#        MagicMock(return_value=create.account("TestAMPAccount", "test@test.com", "testpassword")))
class _TestAMP(TwistedTestCase):
    def setUp(self):
        super().setUp()
        self.account = mommy.make("accounts.AccountDB", id=1)
        self.server = EvenniaServerService()
        evennia.SERVER_SESSION_HANDLER = ServerSessionHandler()
        evennia.SERVER_SESSION_HANDLER.data_in = MagicMock()
        evennia.SERVER_SESSION_HANDLER.data_out = MagicMock()
        self.amp_client_factory = amp_client.AMPClientFactory(self.server)
        self.amp_client = self.amp_client_factory.buildProtocol("127.0.0.1")
        self.session = MagicMock()  # serversession.ServerSession()
        self.session.sessid = 1
        evennia.SERVER_SESSION_HANDLER[1] = self.session

        self.portal = EvenniaPortalService()
        self.portalsession = session.Session()
        self.portalsession.sessid = 1
        evennia.PORTAL_SESSION_HANDLER = PortalSessionHandler()
        evennia.PORTAL_SESSION_HANDLER[1] = self.portalsession
        evennia.PORTAL_SESSION_HANDLER.data_in = MagicMock()
        evennia.PORTAL_SESSION_HANDLER.data_out = MagicMock()
        self.amp_server_factory = amp_server.AMPServerFactory(self.portal)
        self.amp_server = self.amp_server_factory.buildProtocol("127.0.0.1")

    def tearDown(self):
        self.account.delete()
        super().tearDown()

    def _connect_client(self, mocktransport):
        "Setup client to send data for testing"
        mocktransport.write = MagicMock()
        self.amp_client.makeConnection(mocktransport)
        mocktransport.write.reset_mock()

    def _connect_server(self, mocktransport):
        "Setup server to send data for testing"
        mocktransport.write = MagicMock()
        self.amp_server.makeConnection(mocktransport)
        mocktransport.write.reset_mock()

    def _catch_wire_read(self, mocktransport):
        "Parse what was supposed to be sent over the wire"
        arg_list = mocktransport.write.call_args_list

        all_sent = []
        for i, cll in enumerate(arg_list):
            args, kwargs = cll
            raw_inp = args[0]
            all_sent.append(raw_inp)

        return all_sent


@patch("evennia.server.service.LoopingCall", MagicMock())
@patch("evennia.server.portal.amp.amp.BinaryBoxProtocol.transport")
class TestAMPClientSend(_TestAMP):
    """Test amp client sending data"""

    def test_msgserver2portal(self, mocktransport):
        self._connect_client(mocktransport)
        self.amp_client.send_MsgServer2Portal(self.session, text={"foo": "bar"})
        wire_data = self._catch_wire_read(mocktransport)[0]

        self._connect_server(mocktransport)
        self.amp_server.dataReceived(wire_data)
        evennia.PORTAL_SESSION_HANDLER.data_out.assert_called_with(
            self.portalsession, text={"foo": "bar"}
        )

    def test_adminserver2portal(self, mocktransport):
        self._connect_client(mocktransport)

        self.amp_client.send_AdminServer2Portal(
            self.session, operation=amp.PSYNC, info_dict={}, spid=None
        )
        wire_data = self._catch_wire_read(mocktransport)[0]

        self._connect_server(mocktransport)
        self.amp_server.data_in = MagicMock()
        self.amp_server.dataReceived(wire_data)
        self.amp_server.data_in.assert_called()


@patch("evennia.server.portal.amp.amp.BinaryBoxProtocol.transport")
class TestAMPClientRecv(_TestAMP):
    """Test amp client sending data"""

    def test_msgportal2server(self, mocktransport):
        self._connect_server(mocktransport)
        self.amp_server.send_MsgPortal2Server(self.session, text={"foo": "bar"})
        wire_data = self._catch_wire_read(mocktransport)[0]

        self._connect_client(mocktransport)
        self.amp_client.dataReceived(wire_data)
        evennia.SERVER_SESSION_HANDLER.data_in.assert_called_with(self.session, text={"foo": "bar"})

    def test_adminportal2server(self, mocktransport):
        self._connect_server(mocktransport)

        self.amp_server.send_AdminPortal2Server(self.session, operation=amp.PDISCONNALL)
        wire_data = self._catch_wire_read(mocktransport)[0]

        self._connect_client(mocktransport)
        evennia.SERVER_SESSION_HANDLER.portal_disconnect_all = MagicMock()
        self.amp_client.dataReceived(wire_data)
        evennia.SERVER_SESSION_HANDLER.portal_disconnect_all.assert_called()
