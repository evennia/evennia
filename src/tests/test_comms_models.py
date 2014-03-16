import unittest

class TestMsg(unittest.TestCase):
    def test___init__(self):
        # msg = Msg(*args, **kwargs)
        assert True # TODO: implement your test here

    def test___str__(self):
        # msg = Msg(*args, **kwargs)
        # self.assertEqual(expected, msg.__str__())
        assert True # TODO: implement your test here

    def test_remove_receiver(self):
        # msg = Msg(*args, **kwargs)
        # self.assertEqual(expected, msg.remove_receiver(obj))
        assert True # TODO: implement your test here

    def test_remove_sender(self):
        # msg = Msg(*args, **kwargs)
        # self.assertEqual(expected, msg.remove_sender(value))
        assert True # TODO: implement your test here

class TestTempMsg(unittest.TestCase):
    def test___init__(self):
        # temp_msg = TempMsg(senders, receivers, channels, message, header, type, lockstring, hide_from)
        assert True # TODO: implement your test here

    def test___str__(self):
        # temp_msg = TempMsg(senders, receivers, channels, message, header, type, lockstring, hide_from)
        # self.assertEqual(expected, temp_msg.__str__())
        assert True # TODO: implement your test here

    def test_access(self):
        # temp_msg = TempMsg(senders, receivers, channels, message, header, type, lockstring, hide_from)
        # self.assertEqual(expected, temp_msg.access(accessing_obj, access_type, default))
        assert True # TODO: implement your test here

    def test_remove_receiver(self):
        # temp_msg = TempMsg(senders, receivers, channels, message, header, type, lockstring, hide_from)
        # self.assertEqual(expected, temp_msg.remove_receiver(obj))
        assert True # TODO: implement your test here

    def test_remove_sender(self):
        # temp_msg = TempMsg(senders, receivers, channels, message, header, type, lockstring, hide_from)
        # self.assertEqual(expected, temp_msg.remove_sender(obj))
        assert True # TODO: implement your test here

class TestChannelDB(unittest.TestCase):
    def test___init__(self):
        # channel_d_b = ChannelDB(*args, **kwargs)
        assert True # TODO: implement your test here

    def test___str__(self):
        # channel_d_b = ChannelDB(*args, **kwargs)
        # self.assertEqual(expected, channel_d_b.__str__())
        assert True # TODO: implement your test here

    def test_access(self):
        # channel_d_b = ChannelDB(*args, **kwargs)
        # self.assertEqual(expected, channel_d_b.access(accessing_obj, access_type, default))
        assert True # TODO: implement your test here

    def test_connect(self):
        # channel_d_b = ChannelDB(*args, **kwargs)
        # self.assertEqual(expected, channel_d_b.connect(player))
        assert True # TODO: implement your test here

    def test_delete(self):
        # channel_d_b = ChannelDB(*args, **kwargs)
        # self.assertEqual(expected, channel_d_b.delete())
        assert True # TODO: implement your test here

    def test_disconnect(self):
        # channel_d_b = ChannelDB(*args, **kwargs)
        # self.assertEqual(expected, channel_d_b.disconnect(player))
        assert True # TODO: implement your test here

    def test_has_connection(self):
        # channel_d_b = ChannelDB(*args, **kwargs)
        # self.assertEqual(expected, channel_d_b.has_connection(player))
        assert True # TODO: implement your test here

if __name__ == '__main__':
    unittest.main()
