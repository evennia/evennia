import unittest

class TestBotStarter(unittest.TestCase):
    def test_at_repeat(self):
        # bot_starter = BotStarter()
        # self.assertEqual(expected, bot_starter.at_repeat())
        assert True # TODO: implement your test here

    def test_at_script_creation(self):
        # bot_starter = BotStarter()
        # self.assertEqual(expected, bot_starter.at_script_creation())
        assert True # TODO: implement your test here

    def test_at_server_reload(self):
        # bot_starter = BotStarter()
        # self.assertEqual(expected, bot_starter.at_server_reload())
        assert True # TODO: implement your test here

    def test_at_server_shutdown(self):
        # bot_starter = BotStarter()
        # self.assertEqual(expected, bot_starter.at_server_shutdown())
        assert True # TODO: implement your test here

    def test_at_start(self):
        # bot_starter = BotStarter()
        # self.assertEqual(expected, bot_starter.at_start())
        assert True # TODO: implement your test here

class TestCmdBotListen(unittest.TestCase):
    def test_func(self):
        # cmd_bot_listen = CmdBotListen()
        # self.assertEqual(expected, cmd_bot_listen.func())
        assert True # TODO: implement your test here

class TestBotCmdSet(unittest.TestCase):
    def test_at_cmdset_creation(self):
        # bot_cmd_set = BotCmdSet()
        # self.assertEqual(expected, bot_cmd_set.at_cmdset_creation())
        assert True # TODO: implement your test here

class TestBot(unittest.TestCase):
    def test_basetype_setup(self):
        # bot = Bot()
        # self.assertEqual(expected, bot.basetype_setup())
        assert True # TODO: implement your test here

    def test_execute_cmd(self):
        # bot = Bot()
        # self.assertEqual(expected, bot.execute_cmd(raw_string, sessid))
        assert True # TODO: implement your test here

    def test_msg(self):
        # bot = Bot()
        # self.assertEqual(expected, bot.msg(text, from_obj, sessid, **kwargs))
        assert True # TODO: implement your test here

    def test_start(self):
        # bot = Bot()
        # self.assertEqual(expected, bot.start(**kwargs))
        assert True # TODO: implement your test here

class TestIRCBot(unittest.TestCase):
    def test_execute_cmd(self):
        # i_rc_bot = IRCBot()
        # self.assertEqual(expected, i_rc_bot.execute_cmd(text, sessid))
        assert True # TODO: implement your test here

    def test_msg(self):
        # i_rc_bot = IRCBot()
        # self.assertEqual(expected, i_rc_bot.msg(text, **kwargs))
        assert True # TODO: implement your test here

    def test_start(self):
        # i_rc_bot = IRCBot()
        # self.assertEqual(expected, i_rc_bot.start(ev_channel, irc_botname, irc_channel, irc_network, irc_port))
        assert True # TODO: implement your test here

class TestRSSBot(unittest.TestCase):
    def test_execute_cmd(self):
        # r_ss_bot = RSSBot()
        # self.assertEqual(expected, r_ss_bot.execute_cmd(text, sessid))
        assert True # TODO: implement your test here

    def test_start(self):
        # r_ss_bot = RSSBot()
        # self.assertEqual(expected, r_ss_bot.start(ev_channel, rss_url, rss_rate))
        assert True # TODO: implement your test here

class TestIMC2Bot(unittest.TestCase):
    def test_execute_cmd(self):
        # i_m_c2_bot = IMC2Bot()
        # self.assertEqual(expected, i_m_c2_bot.execute_cmd(text, sessid))
        assert True # TODO: implement your test here

    def test_msg(self):
        # i_m_c2_bot = IMC2Bot()
        # self.assertEqual(expected, i_m_c2_bot.msg(text, **kwargs))
        assert True # TODO: implement your test here

    def test_start(self):
        # i_m_c2_bot = IMC2Bot()
        # self.assertEqual(expected, i_m_c2_bot.start(ev_channel, imc2_network, imc2_mudname, imc2_port, imc2_client_pwd, imc2_server_pwd))
        assert True # TODO: implement your test here

if __name__ == '__main__':
    unittest.main()
