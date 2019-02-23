"""
Test the evennia launcher.

"""

import os
import pickle
from anything import Something
from mock import patch, MagicMock
from twisted.internet import reactor
from twisted.trial.unittest import TestCase as TwistedTestCase
from evennia.server import evennia_launcher
from evennia.server.portal import amp

from twisted.internet.base import DelayedCall
DelayedCall.debug = True

@patch("evennia.server.evennia_launcher.Popen", new=MagicMock())
class TestLauncher(TwistedTestCase):

    def test_is_windows(self):
        self.assertEqual(evennia_launcher._is_windows(), os.name == 'nt')

    def test_file_compact(self):
        self.assertEqual(evennia_launcher._file_names_compact(
            "foo/bar/test1", "foo/bar/test2"),
            "foo/bar/test1 and test2")

        self.assertEqual(evennia_launcher._file_names_compact(
            "foo/test1", "foo/bar/test2"),
            "foo/test1 and foo/bar/test2")

    @patch("evennia.server.evennia_launcher.print")
    def test_print_info(self, mockprint):
        portal_dict = {
            "servername": "testserver",
            "version": "1",
            "telnet": 1234,
            "telnet_ssl": [1234, 2345],
            "ssh": 1234,
            "webserver_proxy": 1234,
            "webclient": 1234,
            "webserver_internal": 1234,
            "amp": 1234
        }
        server_dict = {
            "servername": "testserver",
            "version": "1",
            "webserver": [1234, 1234],
            "amp": 1234,
            "irc_rss": "irc.test",
            "info": "testing mode",
            "errors": ""
        }

        evennia_launcher._print_info(portal_dict, server_dict)
        mockprint.assert_called()

    def test_parse_status(self):
        response = {"status": pickle.dumps(("teststring",))}
        result = evennia_launcher._parse_status(response)
        self.assertEqual(result, ("teststring",))

    @patch("evennia.server.evennia_launcher.os.name", new="posix")
    def test_get_twisted_cmdline(self):
        pcmd, scmd = evennia_launcher._get_twistd_cmdline(False, False)
        self.assertTrue("portal.py" in pcmd[1])
        self.assertTrue("--pidfile" in pcmd[2])
        self.assertTrue("server.py" in scmd[1])
        self.assertTrue("--pidfile" in scmd[2])

        pcmd, scmd = evennia_launcher._get_twistd_cmdline(True, True)
        self.assertTrue("portal.py" in pcmd[1])
        self.assertTrue("--pidfile" in pcmd[2])
        self.assertTrue("--profiler=cprofile" in pcmd[4], "actual: {}".format(pcmd))
        self.assertTrue("--profile=" in pcmd[5])
        self.assertTrue("server.py" in scmd[1])
        self.assertTrue("--pidfile" in scmd[2])
        self.assertTrue("--pidfile" in scmd[2])
        self.assertTrue("--profiler=cprofile" in scmd[4], "actual: {}".format(scmd))
        self.assertTrue("--profile=" in scmd[5])

    @patch("evennia.server.evennia_launcher.os.name", new="nt")
    def test_get_twisted_cmdline_nt(self):
        pcmd, scmd = evennia_launcher._get_twistd_cmdline(False, False)
        self.assertTrue(len(pcmd) == 2, "actual: {}".format(pcmd))
        self.assertTrue(len(scmd) == 2, "actual: {}".format(scmd))

    @patch("evennia.server.evennia_launcher.reactor.stop")
    def test_reactor_stop(self, mockstop):
        evennia_launcher._reactor_stop()
        mockstop.assert_called()

    def _catch_wire_read(self, mocktransport):
        "Parse what was supposed to be sent over the wire"
        arg_list = mocktransport.write.call_args_list

        all_sent = []
        for i, cll in enumerate(arg_list):
            args, kwargs = cll
            raw_inp = args[0]
            all_sent.append(raw_inp)

        return all_sent

    @patch("evennia.server.portal.amp.amp.BinaryBoxProtocol.transport")
    def test_send_instruction_pstatus(self, mocktransport):

        deferred = evennia_launcher.send_instruction(
            evennia_launcher.PSTATUS,
            (),
            callback=MagicMock(),
            errback=MagicMock())

        on_wire = self._catch_wire_read(mocktransport)
        self.assertEqual(on_wire, "")

        return deferred
