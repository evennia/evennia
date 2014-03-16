import unittest

class TestGetRestartMode(unittest.TestCase):
    def test_get_restart_mode(self):
        # self.assertEqual(expected, get_restart_mode(restart_file))
        assert True # TODO: implement your test here

class TestAmpServerFactory(unittest.TestCase):
    def test___init__(self):
        # amp_server_factory = AmpServerFactory(server)
        assert True # TODO: implement your test here

    def test_buildProtocol(self):
        # amp_server_factory = AmpServerFactory(server)
        # self.assertEqual(expected, amp_server_factory.buildProtocol(addr))
        assert True # TODO: implement your test here

class TestAmpClientFactory(unittest.TestCase):
    def test___init__(self):
        # amp_client_factory = AmpClientFactory(portal)
        assert True # TODO: implement your test here

    def test_buildProtocol(self):
        # amp_client_factory = AmpClientFactory(portal)
        # self.assertEqual(expected, amp_client_factory.buildProtocol(addr))
        assert True # TODO: implement your test here

    def test_clientConnectionFailed(self):
        # amp_client_factory = AmpClientFactory(portal)
        # self.assertEqual(expected, amp_client_factory.clientConnectionFailed(connector, reason))
        assert True # TODO: implement your test here

    def test_clientConnectionLost(self):
        # amp_client_factory = AmpClientFactory(portal)
        # self.assertEqual(expected, amp_client_factory.clientConnectionLost(connector, reason))
        assert True # TODO: implement your test here

    def test_startedConnecting(self):
        # amp_client_factory = AmpClientFactory(portal)
        # self.assertEqual(expected, amp_client_factory.startedConnecting(connector))
        assert True # TODO: implement your test here

class TestDumps(unittest.TestCase):
    def test_dumps(self):
        # self.assertEqual(expected, dumps(data))
        assert True # TODO: implement your test here

class TestLoads(unittest.TestCase):
    def test_loads(self):
        # self.assertEqual(expected, loads(data))
        assert True # TODO: implement your test here

class TestAMPProtocol(unittest.TestCase):
    def test_amp_function_call(self):
        # a_mp_protocol = AMPProtocol()
        # self.assertEqual(expected, a_mp_protocol.amp_function_call(module, function, args, **kwargs))
        assert True # TODO: implement your test here

    def test_amp_msg_portal2server(self):
        # a_mp_protocol = AMPProtocol()
        # self.assertEqual(expected, a_mp_protocol.amp_msg_portal2server(sessid, ipart, nparts, msg, data))
        assert True # TODO: implement your test here

    def test_amp_msg_server2portal(self):
        # a_mp_protocol = AMPProtocol()
        # self.assertEqual(expected, a_mp_protocol.amp_msg_server2portal(sessid, ipart, nparts, msg, data))
        assert True # TODO: implement your test here

    def test_amp_portal_admin(self):
        # a_mp_protocol = AMPProtocol()
        # self.assertEqual(expected, a_mp_protocol.amp_portal_admin(sessid, ipart, nparts, operation, data))
        assert True # TODO: implement your test here

    def test_amp_server_admin(self):
        # a_mp_protocol = AMPProtocol()
        # self.assertEqual(expected, a_mp_protocol.amp_server_admin(sessid, ipart, nparts, operation, data))
        assert True # TODO: implement your test here

    def test_call_remote_FunctionCall(self):
        # a_mp_protocol = AMPProtocol()
        # self.assertEqual(expected, a_mp_protocol.call_remote_FunctionCall(modulepath, functionname, *args, **kwargs))
        assert True # TODO: implement your test here

    def test_call_remote_MsgPortal2Server(self):
        # a_mp_protocol = AMPProtocol()
        # self.assertEqual(expected, a_mp_protocol.call_remote_MsgPortal2Server(sessid, msg, data))
        assert True # TODO: implement your test here

    def test_call_remote_MsgServer2Portal(self):
        # a_mp_protocol = AMPProtocol()
        # self.assertEqual(expected, a_mp_protocol.call_remote_MsgServer2Portal(sessid, msg, data))
        assert True # TODO: implement your test here

    def test_call_remote_PortalAdmin(self):
        # a_mp_protocol = AMPProtocol()
        # self.assertEqual(expected, a_mp_protocol.call_remote_PortalAdmin(sessid, operation, data))
        assert True # TODO: implement your test here

    def test_call_remote_ServerAdmin(self):
        # a_mp_protocol = AMPProtocol()
        # self.assertEqual(expected, a_mp_protocol.call_remote_ServerAdmin(sessid, operation, data))
        assert True # TODO: implement your test here

    def test_connectionMade(self):
        # a_mp_protocol = AMPProtocol()
        # self.assertEqual(expected, a_mp_protocol.connectionMade())
        assert True # TODO: implement your test here

    def test_errback(self):
        # a_mp_protocol = AMPProtocol()
        # self.assertEqual(expected, a_mp_protocol.errback(e, info))
        assert True # TODO: implement your test here

    def test_safe_recv(self):
        # a_mp_protocol = AMPProtocol()
        # self.assertEqual(expected, a_mp_protocol.safe_recv(command, sessid, ipart, nparts, **kwargs))
        assert True # TODO: implement your test here

    def test_safe_send(self):
        # a_mp_protocol = AMPProtocol()
        # self.assertEqual(expected, a_mp_protocol.safe_send(command, sessid, **kwargs))
        assert True # TODO: implement your test here

if __name__ == '__main__':
    unittest.main()
