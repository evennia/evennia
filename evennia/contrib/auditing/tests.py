"""
Module containing the test cases for the Audit system.
"""

from django.conf import settings
from evennia.contrib.auditing.server import AuditedServerSession
from evennia.utils.test_resources import EvenniaTest

class AuditingTest(EvenniaTest):
    def setUp(self):
        # Configure session auditing settings
        settings.AUDIT_CALLBACK = "evennia.contrib.auditing.examples"
        settings.AUDIT_IN = True
        settings.AUDIT_OUT = True
        
        # Configure settings to use custom session
        settings.SERVER_SESSION_CLASS = "evennia.contrib.auditing.server.AuditedServerSession"
        
        super(AuditingTest, self).setUp()
        
    def test_mask(self):
        """
        Make sure the 'mask' function is properly masking potentially sensitive 
        information from strings.
        """
        safe_cmds = (
            'say hello to my little friend',
            '@ccreate channel = for channeling',
            '@create a pretty shirt : evennia.contrib.clothing.Clothing',
            '@charcreate johnnyefhiwuhefwhef',
            'Command "@logout" is not available. Maybe you meant "@color" or "@cboot"?',
        )
        
        for cmd in safe_cmds:
            self.assertEqual(self.session.mask(cmd), cmd)
            
        unsafe_cmds = (
            ('connect johnny password123', 'connect johnny ***********'),
            ('concnct johnny password123', 'concnct *******************'),
            ('create johnny password123', 'create johnny ***********'),
            ('@userpassword johnny = password234', '@userpassword johnny ***********'),
            ('craete johnnypassword123', 'craete *****************'),
            ("Command 'conncect teddy teddy' is not available. Maybe you meant \"@encode\"?", 'Command *************************************************************************************')
        )
        
        for unsafe, safe in unsafe_cmds:
            self.assertEqual(self.session.mask(unsafe), safe)
        
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
        self.assertEqual(log['msg'], 'logged_in')
    