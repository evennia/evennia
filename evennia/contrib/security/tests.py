from django.http.request import HttpRequest
from evennia.utils.test_resources import EvenniaTest

from mock import MagicMock
import mock

class TestConnectionWrappers(EvenniaTest):
    
    def setUp(self):
        super(TestConnectionWrappers, self).setUp()
        
        # first, create a mock
        self.geoip = MagicMock()
        self.pyasn = MagicMock()

        modules = {
            "geoip2.database.Reader": self.geoip,
            "pyasn.pyasn": self.pyasn,
        }

        # we use the mock dict patcher directly (not as a context manager or decorator), so we must
        # start it manually to apply it (.start is an alias for .__enter__ for the patcher)
        self.module_patcher = mock.patch.dict('sys.modules', modules)
        self.module_patcher.start()

        # now we are safe to import the geoip/pyasn reader when not installed
        from evennia.contrib.security.wrappers import SessionWrapper, RequestWrapper
        self.sessionwrapper_class = SessionWrapper
        self.requestwrapper_class = RequestWrapper
        
        # Set session address to something foreign
        self.session.address = '208.80.152.201'
        self.session.protocol_key = 'webclient/ajax'
        
        # Create a HttpRequest object
        request = HttpRequest()
        request.META['HTTP_X_FORWARDED_FOR'] = '208.80.152.201,208.80.152.201'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 (Compatible)'
        self.request = request
    
    def test_session_wrapper_mandatory(self):
        conn = self.sessionwrapper_class(self.session)
        
        # Confirm can get IP
        self.assertEqual(conn.ip, self.session.address)
        
        # Confirm can get protocol
        self.assertEqual(conn.protocol, self.session.protocol_key)
        
    def test_request_wrapper_mandatory(self):
        conn = self.requestwrapper_class(self.request)
        
        # Confirm can get IP
        self.assertEqual(conn.ip, self.request.META['HTTP_X_FORWARDED_FOR'].split(',')[0])
        
        # Confirm can get protocol
        self.assertEqual(conn.protocol, 'http', conn.protocol)
        
        # Confirm can get useragent
        self.assertEqual(conn.useragent, self.request.META['HTTP_USER_AGENT'], conn.useragent)
        
    def test_session_wrapper_optional(self):
        conn = self.sessionwrapper_class(self.session)
        
        self.assertFalse(conn.isp)
        self.assertFalse(conn.iso)
        self.assertEqual(conn.cidr, conn.ip + '/32')
        
        conn._geoip['isp'] = 'Comcast'
        conn._geoip['country_code'] = 'US'
        conn._geoip['cidr'] = '0.0.0.0/0'
        
        # Confirm can access properties
        self.assertTrue(conn.isp)
        self.assertTrue(conn.iso)
        self.assertTrue(conn.cidr)
        
    def test_request_wrapper_optional(self):
        conn = self.requestwrapper_class(self.request)
        
        self.assertFalse(conn.isp)
        self.assertFalse(conn.iso)
        self.assertEqual(conn.cidr, conn.ip + '/32')
        
        conn._geoip['isp'] = 'Comcast'
        conn._geoip['country_code'] = 'US'
        conn._geoip['cidr'] = '0.0.0.0/0'
        
        # Confirm can access properties
        self.assertTrue(conn.isp)
        self.assertTrue(conn.iso)
        self.assertTrue(conn.cidr)