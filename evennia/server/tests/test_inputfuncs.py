"""
Tests for server input functions.
"""

import pickle

import evennia
from evennia.server import inputfuncs
from evennia.utils.test_resources import BaseEvenniaTest


class TestMonitoredInputfunc(BaseEvenniaTest):
    """
    Regressions for monitor/monitored inputfunc handling.
    """

    def test_monitored_payload_is_pickleable(self):
        """
        The monitored payload sent over AMP must not include raw Session objects.
        """

        self.session.puppet = self.char1
        inputfuncs.monitor(self.session, name="location")
        inputfuncs.monitored(self.session)

        sent_session = evennia.SESSION_HANDLER.data_out.call_args.args[0]
        sent_kwargs = evennia.SESSION_HANDLER.data_out.call_args.kwargs
        monitors = sent_kwargs["monitored"][0]
        monitor_kwargs = monitors[0][4]

        self.assertEqual(sent_session, self.session)
        self.assertIn("session", monitor_kwargs)
        self.assertIsInstance(monitor_kwargs["session"], str)
        pickle.dumps((self.session.sessid, sent_kwargs), pickle.HIGHEST_PROTOCOL)
