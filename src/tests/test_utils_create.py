import unittest

class TestHandleDbref(unittest.TestCase):
    def test_handle_dbref(self):
        # self.assertEqual(expected, handle_dbref(inp, objclass, raise_errors))
        assert True # TODO: implement your test here

class TestCreateObject(unittest.TestCase):
    def test_create_object(self):
        # self.assertEqual(expected, create_object(typeclass, key, location, home, permissions, locks, aliases, destination, report_to, nohome))
        assert True # TODO: implement your test here

class TestCreateScript(unittest.TestCase):
    def test_create_script(self):
        # self.assertEqual(expected, create_script(typeclass, key, obj, player, locks, interval, start_delay, repeats, persistent, autostart, report_to))
        assert True # TODO: implement your test here

class TestCreateHelpEntry(unittest.TestCase):
    def test_create_help_entry(self):
        # self.assertEqual(expected, create_help_entry(key, entrytext, category, locks))
        assert True # TODO: implement your test here

class TestCreateMessage(unittest.TestCase):
    def test_create_message(self):
        # self.assertEqual(expected, create_message(senderobj, message, channels, receivers, locks, header))
        assert True # TODO: implement your test here

class TestCreateChannel(unittest.TestCase):
    def test_create_channel(self):
        # self.assertEqual(expected, create_channel(key, aliases, desc, locks, keep_log, typeclass))
        assert True # TODO: implement your test here

class TestCreateTag(unittest.TestCase):
    def test_create_tag(self):
        # self.assertEqual(expected, create_tag(self, key, category, data))
        assert True # TODO: implement your test here

class TestCreatePlayer(unittest.TestCase):
    def test_create_player(self):
        # self.assertEqual(expected, create_player(key, email, password, typeclass, is_superuser, locks, permissions, report_to))
        assert True # TODO: implement your test here

if __name__ == '__main__':
    unittest.main()
