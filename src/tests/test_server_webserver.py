import unittest

class TestHTTPChannelWithXForwardedFor(unittest.TestCase):
    def test_allHeadersReceived(self):
        # h_ttp_channel_with_x_forwarded_for = HTTPChannelWithXForwardedFor()
        # self.assertEqual(expected, h_ttp_channel_with_x_forwarded_for.allHeadersReceived())
        assert True # TODO: implement your test here

class TestEvenniaReverseProxyResource(unittest.TestCase):
    def test_getChild(self):
        # evennia_reverse_proxy_resource = EvenniaReverseProxyResource()
        # self.assertEqual(expected, evennia_reverse_proxy_resource.getChild(path, request))
        assert True # TODO: implement your test here

    def test_render(self):
        # evennia_reverse_proxy_resource = EvenniaReverseProxyResource()
        # self.assertEqual(expected, evennia_reverse_proxy_resource.render(request))
        assert True # TODO: implement your test here

class TestDjangoWebRoot(unittest.TestCase):
    def test___init__(self):
        # django_web_root = DjangoWebRoot(pool)
        assert True # TODO: implement your test here

    def test_getChild(self):
        # django_web_root = DjangoWebRoot(pool)
        # self.assertEqual(expected, django_web_root.getChild(path, request))
        assert True # TODO: implement your test here

class TestWSGIWebServer(unittest.TestCase):
    def test___init__(self):
        # w_sgi_web_server = WSGIWebServer(pool, *args, **kwargs)
        assert True # TODO: implement your test here

    def test_startService(self):
        # w_sgi_web_server = WSGIWebServer(pool, *args, **kwargs)
        # self.assertEqual(expected, w_sgi_web_server.startService())
        assert True # TODO: implement your test here

    def test_stopService(self):
        # w_sgi_web_server = WSGIWebServer(pool, *args, **kwargs)
        # self.assertEqual(expected, w_sgi_web_server.stopService())
        assert True # TODO: implement your test here

if __name__ == '__main__':
    unittest.main()
