"""
Module containing the test cases for the Audit system.
"""

from django.conf import settings
from evennia.contrib.auditing.server import AuditedServerSession
from evennia.utils.test_resources import EvenniaTest
import re

# Configure session auditing settings
settings.AUDIT_CALLBACK = "evennia.contrib.auditing.outputs.to_syslog"
settings.AUDIT_IN = True
settings.AUDIT_OUT = True

# Configure settings to use custom session
settings.SERVER_SESSION_CLASS = "evennia.contrib.auditing.server.AuditedServerSession"

class AuditingTest(EvenniaTest):

    def test_mask(self):
        """
        Make sure the 'mask' function is properly masking potentially sensitive 
        information from strings.
        """
        safe_cmds = (
            '/say hello to my little friend',
            '@ccreate channel = for channeling',
            '@create/drop some stuff',
            '@create rock',
            '@create a pretty shirt : evennia.contrib.clothing.Clothing',
            '@charcreate johnnyefhiwuhefwhef',
            'Command "@logout" is not available. Maybe you meant "@color" or "@cboot"?',
            '/me says, "what is the password?"',
            'say the password is plugh',
            # Unfortunately given the syntax, there is no way to discern the
            # latter of these as sensitive
            '@create pretty sunset'
            '@create johnny password123',
        )
        
        for cmd in safe_cmds:
            self.assertEqual(self.session.mask(cmd), cmd)
            
        unsafe_cmds = (
            ('connect johnny password123', 'connect johnny ***********'),
            ('concnct johnny password123', 'concnct johnny ***********'),
            ('concnct johnnypassword123', 'concnct *****************'),
            ('connect "johnny five" "password 123"', 'connect "johnny five" **************'),
            ('connect johnny "password 123"', 'connect johnny **************'),
            ('create johnny password123', 'create johnny ***********'),
            ('@password password1234 = password2345', '@password ***************************'),
            ('@password password1234 password2345', '@password *************************'),
            ('@passwd password1234 = password2345', '@passwd ***************************'),
            ('@userpassword johnny = password234', '@userpassword johnny = ***********'),
            ('craete johnnypassword123', 'craete *****************'),
            ("Command 'conncect teddy teddy' is not available. Maybe you meant \"@encode\"?", 'Command \'conncect ***** *****\' is not available. Maybe you meant "@encode"?'),
            ("{'text': u'Command \\'conncect jsis dfiidf\\' is not available. Type \"help\" for help.'}", "{'text': u'Command \\'conncect jsis ******\\' is not available. Type \"help\" for help.'}")
        )
        
        for index, (unsafe, safe) in enumerate(unsafe_cmds):
            self.assertEqual(re.sub('<Masked: .+>', '', self.session.mask(unsafe)).strip(), safe)
            
        # Make sure scrubbing is not being abused to evade monitoring
        secrets = [
            'say password password password; ive got a secret that i cant explain',
            'whisper johnny = password let\'s lynch the landlord',
            'say connect johnny password1234 secret life of arabia',
            "@password;eval(\"__import__('os').system('clear')\", {'__builtins__':{}})"
        ]
        for secret in secrets:
            self.assertEqual(self.session.mask(secret), secret)
        
    def test_audit(self):
        """
        Make sure the 'audit' function is returning a dictionary based on values
        parsed from the Session object.
        """
        log = self.session.audit(src='client', text=[['hello']])
        obj = {k:v for k,v in log.iteritems() if k in ('direction', 'protocol', 'application', 'msg')}
        self.assertEqual(obj, {
            'direction': 'RCV',
            'protocol': 'telnet',
            'application': 'Evennia',
            'msg': 'hello'
        })
        
        # Make sure auditor is breaking down responses without actual text
        log = self.session.audit(**{'logged_in': {}, 'src': 'server'})
        self.assertEqual(log['msg'], "{'logged_in': {}}")
    