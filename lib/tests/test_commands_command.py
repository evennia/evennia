import unittest

class TestCommandMeta(unittest.TestCase):
    def test___init__(self):
        # command_meta = CommandMeta(*args, **kwargs)
        assert True # TODO: implement your test here

class TestCommand(unittest.TestCase):
    def test___contains__(self):
        # command = Command(**kwargs)
        # self.assertEqual(expected, command.__contains__(query))
        assert True # TODO: implement your test here

    def test___eq__(self):
        # command = Command(**kwargs)
        # self.assertEqual(expected, command.__eq__(cmd))
        assert True # TODO: implement your test here

    def test___init__(self):
        # command = Command(**kwargs)
        assert True # TODO: implement your test here

    def test___ne__(self):
        # command = Command(**kwargs)
        # self.assertEqual(expected, command.__ne__(cmd))
        assert True # TODO: implement your test here

    def test___str__(self):
        # command = Command(**kwargs)
        # self.assertEqual(expected, command.__str__())
        assert True # TODO: implement your test here

    def test_access(self):
        # command = Command(**kwargs)
        # self.assertEqual(expected, command.access(srcobj, access_type, default))
        assert True # TODO: implement your test here

    def test_at_post_cmd(self):
        # command = Command(**kwargs)
        # self.assertEqual(expected, command.at_post_cmd())
        assert True # TODO: implement your test here

    def test_at_pre_cmd(self):
        # command = Command(**kwargs)
        # self.assertEqual(expected, command.at_pre_cmd())
        assert True # TODO: implement your test here

    def test_func(self):
        # command = Command(**kwargs)
        # self.assertEqual(expected, command.func())
        assert True # TODO: implement your test here

    def test_match(self):
        # command = Command(**kwargs)
        # self.assertEqual(expected, command.match(cmdname))
        assert True # TODO: implement your test here

    def test_msg(self):
        # command = Command(**kwargs)
        # self.assertEqual(expected, command.msg(msg, to_obj, from_obj, sessid, all_sessions, **kwargs))
        assert True # TODO: implement your test here

    def test_parse(self):
        # command = Command(**kwargs)
        # self.assertEqual(expected, command.parse())
        assert True # TODO: implement your test here

if __name__ == '__main__':
    unittest.main()
