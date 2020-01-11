"""
Module containing the test cases for the Audit system.
"""

from anything import Anything
from django.test import override_settings
from django.conf import settings
from evennia.utils.test_resources import EvenniaTest
import re

# Configure session auditing settings - TODO: This is bad practice that leaks over to other tests
settings.AUDIT_CALLBACK = "evennia.security.contrib.auditing.outputs.to_syslog"
settings.AUDIT_IN = True
settings.AUDIT_OUT = True
settings.AUDIT_ALLOW_SPARSE = True

# Configure settings to use custom session - TODO: This is bad practice, changing global settings
settings.SERVER_SESSION_CLASS = "evennia.contrib.security.auditing.server.AuditedServerSession"


class AuditingTest(EvenniaTest):
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
            "@create a pretty shirt : evennia.contrib.clothing.Clothing",
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
