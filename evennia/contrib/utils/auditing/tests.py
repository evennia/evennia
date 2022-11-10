"""
Module containing the test cases for the Audit system.

"""

import re

from anything import Anything
from django.test import override_settings
from mock import patch

from evennia.server.sessionhandler import SESSIONS
from evennia.utils.test_resources import BaseEvenniaTest

from .server import AuditedServerSession


@override_settings(AUDIT_MASKS=[])
class AuditingTest(BaseEvenniaTest):
    @patch("evennia.server.sessionhandler._ServerSession", AuditedServerSession)
    def setup_session(self):
        """Overrides default one in EvenniaTest"""
        dummysession = AuditedServerSession()
        dummysession.init_session("telnet", ("localhost", "testmode"), SESSIONS)
        dummysession.sessid = 1
        SESSIONS.portal_connect(
            dummysession.get_sync_data()
        )  # note that this creates a new Session!
        session = SESSIONS.session_from_sessid(1)  # the real session
        SESSIONS.login(session, self.account, testmode=True)
        self.session = session

    @patch(
        "evennia.contrib.utils.auditing.server.AUDIT_CALLBACK",
        "evennia.contrib.utils.auditing.outputs.to_syslog",
    )
    @patch("evennia.contrib.utils.auditing.server.AUDIT_IN", True)
    @patch("evennia.contrib.utils.auditing.server.AUDIT_OUT", True)
    def test_mask(self):
        """
        Make sure the 'mask' function is properly masking potentially sensitive
        information from strings.
        """
        safe_cmds = (
            "/say hello to my little friend",
            "@ccreate channel = for channeling",
            "@create/drop some stuff",
            "@create rock",
            "@create a pretty shirt : evennia.contrib.game_systems.clothing.Clothing",
            "@charcreate johnnyefhiwuhefwhef",
            'Command "@logout" is not available. Maybe you meant "@color" or "@cboot"?',
            '/me says, "what is the password?"',
            "say the password is plugh",
            # Unfortunately given the syntax, there is no way to discern the
            # latter of these as sensitive
            "@create pretty sunset" "@create johnny password123",
            '{"text": "Command \'do stuff\' is not available. Type "help" for help."}',
        )

        for cmd in safe_cmds:
            self.assertEqual(self.session.mask(cmd), cmd)

        unsafe_cmds = (
            (
                "something - new password set to 'asdfghjk'.",
                "something - new password set to '********'.",
            ),
            (
                "someone has changed your password to 'something'.",
                "someone has changed your password to '*********'.",
            ),
            ("connect johnny password123", "connect johnny ***********"),
            ("concnct johnny password123", "concnct johnny ***********"),
            ("concnct johnnypassword123", "concnct *****************"),
            ('connect "johnny five" "password 123"', 'connect "johnny five" **************'),
            ('connect johnny "password 123"', "connect johnny **************"),
            ("create johnny password123", "create johnny ***********"),
            ("@password password1234 = password2345", "@password ***************************"),
            ("@password password1234 password2345", "@password *************************"),
            ("@passwd password1234 = password2345", "@passwd ***************************"),
            ("@userpassword johnny = password234", "@userpassword johnny = ***********"),
            ("craete johnnypassword123", "craete *****************"),
            (
                "Command 'conncect teddy teddy' is not available. Maybe you meant \"@encode\"?",
                "Command 'conncect ******** ********' is not available. Maybe you meant \"@encode\"?",
            ),
            (
                "{'text': u'Command \\'conncect jsis dfiidf\\' is not available. Type \"help\" for help.'}",
                "{'text': u'Command \\'conncect jsis ********\\' is not available. Type \"help\" for help.'}",
            ),
        )

        for index, (unsafe, safe) in enumerate(unsafe_cmds):
            self.assertEqual(re.sub(" <Masked: .+>", "", self.session.mask(unsafe)).strip(), safe)

        # Make sure scrubbing is not being abused to evade monitoring
        secrets = [
            "say password password password; ive got a secret that i cant explain",
            "whisper johnny = password\n let's lynch the landlord",
            "say connect johnny password1234|the secret life of arabia",
            "@password eval(\"__import__('os').system('clear')\", {'__builtins__':{}})",
        ]
        for secret in secrets:
            self.assertEqual(self.session.mask(secret), secret)

    @patch(
        "evennia.contrib.utils.auditing.server.AUDIT_CALLBACK",
        "evennia.contrib.utils.auditing.outputs.to_syslog",
    )
    @patch("evennia.contrib.utils.auditing.server.AUDIT_IN", True)
    @patch("evennia.contrib.utils.auditing.server.AUDIT_OUT", True)
    def test_audit(self):
        """
        Make sure the 'audit' function is returning a dictionary based on values
        parsed from the Session object.
        """
        log = self.session.audit(src="client", text=[["hello"]])
        obj = {
            k: v for k, v in log.items() if k in ("direction", "protocol", "application", "text")
        }
        self.assertEqual(
            obj,
            {
                "direction": "RCV",
                "protocol": "telnet",
                "application": Anything,  # this will change if running tests from the game dir
                "text": "hello",
            },
        )

        # Make sure OOB data is being recorded
        log = self.session.audit(
            src="client", text="connect johnny password123", prompt="hp=20|st=10|ma=15", pane=2
        )
        self.assertEqual(log["text"], "connect johnny ***********")
        self.assertEqual(log["data"]["prompt"], "hp=20|st=10|ma=15")
        self.assertEqual(log["data"]["pane"], 2)
