"""
Test the evennia launcher.

"""

import os
import pickle
from anything import Something
from mock import patch, MagicMock, create_autospec
from twisted.internet import reactor
from twisted.trial.unittest import TestCase as TwistedTestCase
from evennia.server import evennia_launcher
from evennia.server.portal import amp

from twisted.internet.base import DelayedCall

DelayedCall.debug = True


@patch("evennia.server.evennia_launcher.Popen", new=MagicMock())
class TestLauncher(TwistedTestCase):
    def test_is_windows(self):
        self.assertEqual(evennia_launcher._is_windows(), os.name == "nt")

    def test_file_compact(self):
        self.assertEqual(
            evennia_launcher._file_names_compact("foo/bar/test1", "foo/bar/test2"),
            "foo/bar/test1 and test2",
        )

        self.assertEqual(
            evennia_launcher._file_names_compact("foo/test1", "foo/bar/test2"),
            "foo/test1 and foo/bar/test2",
        )

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
            "amp": 1234,
        }
        server_dict = {
            "servername": "testserver",
            "version": "1",
            "webserver": [1234, 1234],
            "amp": 1234,
            "irc_rss": "irc.test",
            "info": "testing mode",
            "errors": "",
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

    # @patch("evennia.server.portal.amp.amp.BinaryBoxProtocol.transport")
    # def test_send_instruction_pstatus(self, mocktransport):

    #     deferred = evennia_launcher.send_instruction(
    #         evennia_launcher.PSTATUS,
    #         (),
    #         callback=MagicMock(),
    #         errback=MagicMock())

    #     on_wire = self._catch_wire_read(mocktransport)
    #     self.assertEqual(on_wire, "")

    #     return deferred

    def _msend_status_ok(operation, arguments, callback=None, errback=None):
        callback({"status": pickle.dumps((True, True, 2, 24, "info1", "info2"))})

    def _msend_status_err(operation, arguments, callback=None, errback=None):
        errback({"status": pickle.dumps((False, False, 3, 25, "info3", "info4"))})

    @patch("evennia.server.evennia_launcher.send_instruction", _msend_status_ok)
    @patch("evennia.server.evennia_launcher.NO_REACTOR_STOP", True)
    @patch("evennia.server.evennia_launcher.get_pid", MagicMock(return_value=100))
    @patch("evennia.server.evennia_launcher.print")
    def test_query_status_run(self, mprint):
        evennia_launcher.query_status()
        mprint.assert_called_with("Portal: RUNNING (pid 100)\nServer: RUNNING (pid 100)")

    @patch("evennia.server.evennia_launcher.send_instruction", _msend_status_err)
    @patch("evennia.server.evennia_launcher.NO_REACTOR_STOP", True)
    @patch("evennia.server.evennia_launcher.print")
    def test_query_status_not_run(self, mprint):
        evennia_launcher.query_status()
        mprint.assert_called_with("Portal: NOT RUNNING\nServer: NOT RUNNING")

    @patch("evennia.server.evennia_launcher.send_instruction", _msend_status_ok)
    @patch("evennia.server.evennia_launcher.NO_REACTOR_STOP", True)
    def test_query_status_callback(self):
        mprint = MagicMock()

        def testcall(response):
            resp = pickle.loads(response["status"])
            mprint(resp)

        evennia_launcher.query_status(callback=testcall)
        mprint.assert_called_with((True, True, 2, 24, "info1", "info2"))

    @patch("evennia.server.evennia_launcher.AMP_CONNECTION")
    @patch("evennia.server.evennia_launcher.print")
    def test_wait_for_status_reply(self, mprint, aconn):
        aconn.wait_for_status = MagicMock()

        def test():
            pass

        evennia_launcher.wait_for_status_reply(test)
        aconn.wait_for_status.assert_called_with(test)

    @patch("evennia.server.evennia_launcher.AMP_CONNECTION", None)
    @patch("evennia.server.evennia_launcher.print")
    def test_wait_for_status_reply_fail(self, mprint):
        evennia_launcher.wait_for_status_reply(None)
        mprint.assert_called_with("No Evennia connection established.")

    @patch("evennia.server.evennia_launcher.send_instruction", _msend_status_ok)
    @patch("evennia.server.evennia_launcher.reactor.callLater")
    def test_wait_for_status(self, mcalllater):
        mcall = MagicMock()
        merr = MagicMock()
        evennia_launcher.wait_for_status(
            portal_running=True, server_running=True, callback=mcall, errback=merr
        )

        mcall.assert_called_with(True, True)
        merr.assert_not_called()

    @patch("evennia.server.evennia_launcher.send_instruction", _msend_status_err)
    @patch("evennia.server.evennia_launcher.reactor.callLater")
    def test_wait_for_status_fail(self, mcalllater):
        mcall = MagicMock()
        merr = MagicMock()
        evennia_launcher.wait_for_status(
            portal_running=True, server_running=True, callback=mcall, errback=merr
        )

        mcall.assert_not_called()
        merr.assert_not_called()
        mcalllater.assert_called()
