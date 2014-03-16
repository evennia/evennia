import unittest

class TestExtendedLoopingCall(unittest.TestCase):
    def test___call__(self):
        # extended_looping_call = ExtendedLoopingCall()
        # self.assertEqual(expected, extended_looping_call.__call__())
        assert True # TODO: implement your test here

    def test_force_repeat(self):
        # extended_looping_call = ExtendedLoopingCall()
        # self.assertEqual(expected, extended_looping_call.force_repeat())
        assert True # TODO: implement your test here

    def test_next_call_time(self):
        # extended_looping_call = ExtendedLoopingCall()
        # self.assertEqual(expected, extended_looping_call.next_call_time())
        assert True # TODO: implement your test here

    def test_start(self):
        # extended_looping_call = ExtendedLoopingCall()
        # self.assertEqual(expected, extended_looping_call.start(interval, now, start_delay, count_start))
        assert True # TODO: implement your test here

class TestScriptBase(unittest.TestCase):
    def test___eq__(self):
        # script_base = ScriptBase()
        # self.assertEqual(expected, script_base.__eq__(other))
        assert True # TODO: implement your test here

    def test_at_init(self):
        # script_base = ScriptBase()
        # self.assertEqual(expected, script_base.at_init())
        assert True # TODO: implement your test here

    def test_at_repeat(self):
        # script_base = ScriptBase()
        # self.assertEqual(expected, script_base.at_repeat())
        assert True # TODO: implement your test here

    def test_at_script_creation(self):
        # script_base = ScriptBase()
        # self.assertEqual(expected, script_base.at_script_creation())
        assert True # TODO: implement your test here

    def test_at_start(self):
        # script_base = ScriptBase()
        # self.assertEqual(expected, script_base.at_start())
        assert True # TODO: implement your test here

    def test_at_stop(self):
        # script_base = ScriptBase()
        # self.assertEqual(expected, script_base.at_stop())
        assert True # TODO: implement your test here

    def test_force_repeat(self):
        # script_base = ScriptBase()
        # self.assertEqual(expected, script_base.force_repeat())
        assert True # TODO: implement your test here

    def test_is_valid(self):
        # script_base = ScriptBase()
        # self.assertEqual(expected, script_base.is_valid())
        assert True # TODO: implement your test here

    def test_pause(self):
        # script_base = ScriptBase()
        # self.assertEqual(expected, script_base.pause())
        assert True # TODO: implement your test here

    def test_remaining_repeats(self):
        # script_base = ScriptBase()
        # self.assertEqual(expected, script_base.remaining_repeats())
        assert True # TODO: implement your test here

    def test_start(self):
        # script_base = ScriptBase()
        # self.assertEqual(expected, script_base.start(force_restart))
        assert True # TODO: implement your test here

    def test_stop(self):
        # script_base = ScriptBase()
        # self.assertEqual(expected, script_base.stop(kill))
        assert True # TODO: implement your test here

    def test_time_until_next_repeat(self):
        # script_base = ScriptBase()
        # self.assertEqual(expected, script_base.time_until_next_repeat())
        assert True # TODO: implement your test here

    def test_unpause(self):
        # script_base = ScriptBase()
        # self.assertEqual(expected, script_base.unpause())
        assert True # TODO: implement your test here

class TestScript(unittest.TestCase):
    def test___init__(self):
        # script = Script(dbobj)
        assert True # TODO: implement your test here

    def test_at_repeat(self):
        # script = Script(dbobj)
        # self.assertEqual(expected, script.at_repeat())
        assert True # TODO: implement your test here

    def test_at_script_creation(self):
        # script = Script(dbobj)
        # self.assertEqual(expected, script.at_script_creation())
        assert True # TODO: implement your test here

    def test_at_server_reload(self):
        # script = Script(dbobj)
        # self.assertEqual(expected, script.at_server_reload())
        assert True # TODO: implement your test here

    def test_at_server_shutdown(self):
        # script = Script(dbobj)
        # self.assertEqual(expected, script.at_server_shutdown())
        assert True # TODO: implement your test here

    def test_at_start(self):
        # script = Script(dbobj)
        # self.assertEqual(expected, script.at_start())
        assert True # TODO: implement your test here

    def test_at_stop(self):
        # script = Script(dbobj)
        # self.assertEqual(expected, script.at_stop())
        assert True # TODO: implement your test here

    def test_is_valid(self):
        # script = Script(dbobj)
        # self.assertEqual(expected, script.is_valid())
        assert True # TODO: implement your test here

class TestDoNothing(unittest.TestCase):
    def test_at_script_creation(self):
        # do_nothing = DoNothing()
        # self.assertEqual(expected, do_nothing.at_script_creation())
        assert True # TODO: implement your test here

class TestStore(unittest.TestCase):
    def test_at_script_creation(self):
        # store = Store()
        # self.assertEqual(expected, store.at_script_creation())
        assert True # TODO: implement your test here

class TestCheckSessions(unittest.TestCase):
    def test_at_repeat(self):
        # check_sessions = CheckSessions()
        # self.assertEqual(expected, check_sessions.at_repeat())
        assert True # TODO: implement your test here

    def test_at_script_creation(self):
        # check_sessions = CheckSessions()
        # self.assertEqual(expected, check_sessions.at_script_creation())
        assert True # TODO: implement your test here

class TestValidateScripts(unittest.TestCase):
    def test_at_repeat(self):
        # validate_scripts = ValidateScripts()
        # self.assertEqual(expected, validate_scripts.at_repeat())
        assert True # TODO: implement your test here

    def test_at_script_creation(self):
        # validate_scripts = ValidateScripts()
        # self.assertEqual(expected, validate_scripts.at_script_creation())
        assert True # TODO: implement your test here

class TestValidateChannelHandler(unittest.TestCase):
    def test_at_repeat(self):
        # validate_channel_handler = ValidateChannelHandler()
        # self.assertEqual(expected, validate_channel_handler.at_repeat())
        assert True # TODO: implement your test here

    def test_at_script_creation(self):
        # validate_channel_handler = ValidateChannelHandler()
        # self.assertEqual(expected, validate_channel_handler.at_script_creation())
        assert True # TODO: implement your test here

if __name__ == '__main__':
    unittest.main()
