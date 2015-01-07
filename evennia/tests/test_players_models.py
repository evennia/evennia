import unittest

class TestPlayerDB(unittest.TestCase):
    def test___init__(self):
        # player_d_b = PlayerDB(*args, **kwargs)
        assert True # TODO: implement your test here

    def test___str__(self):
        # player_d_b = PlayerDB(*args, **kwargs)
        # self.assertEqual(expected, player_d_b.__str__())
        assert True # TODO: implement your test here

    def test___unicode__(self):
        # player_d_b = PlayerDB(*args, **kwargs)
        # self.assertEqual(expected, player_d_b.__unicode__())
        assert True # TODO: implement your test here

    def test_cmdset_storage_del(self):
        # player_d_b = PlayerDB(*args, **kwargs)
        # self.assertEqual(expected, player_d_b.cmdset_storage_del())
        assert True # TODO: implement your test here

    def test_cmdset_storage_get(self):
        # player_d_b = PlayerDB(*args, **kwargs)
        # self.assertEqual(expected, player_d_b.cmdset_storage_get())
        assert True # TODO: implement your test here

    def test_cmdset_storage_set(self):
        # player_d_b = PlayerDB(*args, **kwargs)
        # self.assertEqual(expected, player_d_b.cmdset_storage_set(value))
        assert True # TODO: implement your test here

    def test_delete(self):
        # player_d_b = PlayerDB(*args, **kwargs)
        # self.assertEqual(expected, player_d_b.delete(*args, **kwargs))
        assert True # TODO: implement your test here

    def test_disconnect_session_from_player(self):
        # player_d_b = PlayerDB(*args, **kwargs)
        # self.assertEqual(expected, player_d_b.disconnect_session_from_player(sessid))
        assert True # TODO: implement your test here

    def test_execute_cmd(self):
        # player_d_b = PlayerDB(*args, **kwargs)
        # self.assertEqual(expected, player_d_b.execute_cmd(raw_string, sessid))
        assert True # TODO: implement your test here

    def test_get_all_puppets(self):
        # player_d_b = PlayerDB(*args, **kwargs)
        # self.assertEqual(expected, player_d_b.get_all_puppets(return_dbobj))
        assert True # TODO: implement your test here

    def test_get_all_sessions(self):
        # player_d_b = PlayerDB(*args, **kwargs)
        # self.assertEqual(expected, player_d_b.get_all_sessions())
        assert True # TODO: implement your test here

    def test_get_puppet(self):
        # player_d_b = PlayerDB(*args, **kwargs)
        # self.assertEqual(expected, player_d_b.get_puppet(sessid, return_dbobj))
        assert True # TODO: implement your test here

    def test_get_session(self):
        # player_d_b = PlayerDB(*args, **kwargs)
        # self.assertEqual(expected, player_d_b.get_session(sessid))
        assert True # TODO: implement your test here

    def test_msg(self):
        # player_d_b = PlayerDB(*args, **kwargs)
        # self.assertEqual(expected, player_d_b.msg(text, from_obj, sessid, **kwargs))
        assert True # TODO: implement your test here

    def test_puppet_object(self):
        # player_d_b = PlayerDB(*args, **kwargs)
        # self.assertEqual(expected, player_d_b.puppet_object(sessid, obj, normal_mode))
        assert True # TODO: implement your test here

    def test_search(self):
        # player_d_b = PlayerDB(*args, **kwargs)
        # self.assertEqual(expected, player_d_b.search(ostring, return_puppet, return_character, **kwargs))
        assert True # TODO: implement your test here

    def test_unpuppet_all(self):
        # player_d_b = PlayerDB(*args, **kwargs)
        # self.assertEqual(expected, player_d_b.unpuppet_all())
        assert True # TODO: implement your test here

    def test_unpuppet_object(self):
        # player_d_b = PlayerDB(*args, **kwargs)
        # self.assertEqual(expected, player_d_b.unpuppet_object(sessid))
        assert True # TODO: implement your test here

if __name__ == '__main__':
    unittest.main()
