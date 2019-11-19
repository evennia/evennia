"""
Unit testing for the Command system itself.

"""

from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest, TestCase
from evennia.commands.cmdset import CmdSet
from evennia.commands.command import Command
from evennia.commands import cmdparser


# Testing-command sets


class _CmdA(Command):
    key = "A"

    def __init__(self, cmdset, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.from_cmdset = cmdset


class _CmdB(Command):
    key = "B"

    def __init__(self, cmdset, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.from_cmdset = cmdset


class _CmdC(Command):
    key = "C"

    def __init__(self, cmdset, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.from_cmdset = cmdset


class _CmdD(Command):
    key = "D"

    def __init__(self, cmdset, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.from_cmdset = cmdset


class _CmdSetA(CmdSet):
    key = "A"

    def at_cmdset_creation(self):
        self.add(_CmdA("A"))
        self.add(_CmdB("A"))
        self.add(_CmdC("A"))
        self.add(_CmdD("A"))


class _CmdSetB(CmdSet):
    key = "B"

    def at_cmdset_creation(self):
        self.add(_CmdA("B"))
        self.add(_CmdB("B"))
        self.add(_CmdC("B"))


class _CmdSetC(CmdSet):
    key = "C"

    def at_cmdset_creation(self):
        self.add(_CmdA("C"))
        self.add(_CmdB("C"))


class _CmdSetD(CmdSet):
    key = "D"

    def at_cmdset_creation(self):
        self.add(_CmdA("D"))
        self.add(_CmdB("D"))
        self.add(_CmdC("D"))
        self.add(_CmdD("D"))


# testing Command Sets


class TestCmdSetMergers(TestCase):
    "Test merging of cmdsets"

    def setUp(self):
        super().setUp()
        self.cmdset_a = _CmdSetA()
        self.cmdset_b = _CmdSetB()
        self.cmdset_c = _CmdSetC()
        self.cmdset_d = _CmdSetD()

    def test_union(self):
        a, c = self.cmdset_a, self.cmdset_c
        cmdset_f = a + c  # same-prio
        self.assertEqual(len(cmdset_f.commands), 4)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "A"), 2)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "C"), 2)
        cmdset_f = c + a  # same-prio, inverse order
        self.assertEqual(len(cmdset_f.commands), 4)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "A"), 4)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "C"), 0)
        a.priority = 1
        cmdset_f = a + c  # high prio A
        self.assertEqual(len(cmdset_f.commands), 4)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "A"), 4)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "C"), 0)

    def test_intersect(self):
        a, c = self.cmdset_a, self.cmdset_c
        a.mergetype = "Intersect"
        cmdset_f = a + c  # same-prio - c's Union kicks in
        self.assertEqual(len(cmdset_f.commands), 4)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "A"), 2)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "C"), 2)
        cmdset_f = c + a  # same-prio - a's Intersect kicks in
        self.assertEqual(len(cmdset_f.commands), 2)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "A"), 2)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "C"), 0)
        a.priority = 1
        cmdset_f = a + c  # high prio A, intersect kicks in
        self.assertEqual(len(cmdset_f.commands), 2)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "A"), 2)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "C"), 0)

    def test_replace(self):
        a, c = self.cmdset_a, self.cmdset_c
        c.mergetype = "Replace"
        cmdset_f = a + c  # same-prio. C's Replace kicks in
        self.assertEqual(len(cmdset_f.commands), 2)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "A"), 0)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "C"), 2)
        cmdset_f = c + a  # same-prio. A's Union kicks in
        self.assertEqual(len(cmdset_f.commands), 4)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "A"), 4)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "C"), 0)
        c.priority = 1
        cmdset_f = c + a  # c higher prio. C's Replace kicks in
        self.assertEqual(len(cmdset_f.commands), 2)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "A"), 0)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "C"), 2)

    def test_remove(self):
        a, c = self.cmdset_a, self.cmdset_c
        c.mergetype = "Remove"
        cmdset_f = a + c  # same-prio. C's Remove kicks in
        self.assertEqual(len(cmdset_f.commands), 2)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "A"), 2)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "C"), 0)
        cmdset_f = c + a  # same-prio. A's Union kicks in
        self.assertEqual(len(cmdset_f.commands), 4)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "A"), 4)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "C"), 0)
        c.priority = 1
        cmdset_f = c + a  # c higher prio. C's Remove kicks in
        self.assertEqual(len(cmdset_f.commands), 2)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "A"), 2)
        self.assertEqual(sum(1 for cmd in cmdset_f.commands if cmd.from_cmdset == "C"), 0)

    def test_order(self):
        "Merge in reverse- and forward orders, same priorities"
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        cmdset_f = d + c + b + a  # merge in reverse order of priority
        self.assertEqual(cmdset_f.priority, 0)
        self.assertEqual(cmdset_f.mergetype, "Union")
        self.assertEqual(len(cmdset_f.commands), 4)
        self.assertTrue(all(True for cmd in cmdset_f.commands if cmd.from_cmdset == "A"))
        cmdset_f = a + b + c + d  # merge in order of priority
        self.assertEqual(cmdset_f.priority, 0)
        self.assertEqual(cmdset_f.mergetype, "Union")
        self.assertEqual(len(cmdset_f.commands), 4)  # duplicates setting from A transfers
        self.assertTrue(all(True for cmd in cmdset_f.commands if cmd.from_cmdset == "D"))

    def test_priority_order(self):
        "Merge in reverse- and forward order with well-defined prioritities"
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = 2
        b.priority = 1
        c.priority = 0
        d.priority = -1
        cmdset_f = d + c + b + a  # merge in reverse order of priority
        self.assertEqual(cmdset_f.priority, 2)
        self.assertEqual(cmdset_f.mergetype, "Union")
        self.assertEqual(len(cmdset_f.commands), 4)
        self.assertTrue(all(True for cmd in cmdset_f.commands if cmd.from_cmdset == "A"))
        cmdset_f = a + b + c + d  # merge in order of priority
        self.assertEqual(cmdset_f.priority, 2)
        self.assertEqual(cmdset_f.mergetype, "Union")
        self.assertEqual(len(cmdset_f.commands), 4)
        self.assertTrue(all(True for cmd in cmdset_f.commands if cmd.from_cmdset == "A"))

    def test_option_transfer(self):
        "Test transfer of cmdset options"
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        # the options should pass through since none of the other cmdsets care
        # to change the setting from None.
        a.no_exits = True
        a.no_objs = True
        a.no_channels = True
        a.duplicates = True
        cmdset_f = d + c + b + a  # reverse, same-prio
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertTrue(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 8)
        cmdset_f = a + b + c + d  # forward, same-prio
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertFalse(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)
        a.priority = 2
        b.priority = 1
        c.priority = 0
        d.priority = -1
        cmdset_f = d + c + b + a  # reverse, A top priority
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertTrue(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)
        cmdset_f = a + b + c + d  # forward, A top priority. This never happens in practice.
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertTrue(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)
        a.priority = -1
        b.priority = 0
        c.priority = 1
        d.priority = 2
        cmdset_f = d + c + b + a  # reverse, A low prio. This never happens in practice.
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertFalse(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)
        cmdset_f = a + b + c + d  # forward, A low prio
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertFalse(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)
        c.no_exits = False
        b.no_objs = False
        d.duplicates = False
        # higher-prio sets will change the option up the chain
        cmdset_f = a + b + c + d  # forward, A low prio
        self.assertFalse(cmdset_f.no_exits)
        self.assertFalse(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertFalse(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)
        a.priority = 0
        b.priority = 0
        c.priority = 0
        d.priority = 0
        c.duplicates = True
        cmdset_f = d + b + c + a  # two last mergers duplicates=True
        self.assertEqual(len(cmdset_f.commands), 10)


# test cmdhandler functions


import sys
from evennia.commands import cmdhandler
from twisted.trial.unittest import TestCase as TwistedTestCase


def _mockdelay(time, func, *args, **kwargs):
    return func(*args, **kwargs)


class TestGetAndMergeCmdSets(TwistedTestCase, EvenniaTest):
    "Test the cmdhandler.get_and_merge_cmdsets function."

    def setUp(self):
        self.patch(sys.modules["evennia.server.sessionhandler"], "delay", _mockdelay)
        super().setUp()
        self.cmdset_a = _CmdSetA()
        self.cmdset_b = _CmdSetB()
        self.cmdset_c = _CmdSetC()
        self.cmdset_d = _CmdSetD()

    def set_cmdsets(self, obj, *args):
        "Set cmdets on obj in the order given in *args"
        for cmdset in args:
            obj.cmdset.add(cmdset)

    def test_from_session(self):
        a = self.cmdset_a
        a.no_channels = True
        self.set_cmdsets(self.session, a)
        deferred = cmdhandler.get_and_merge_cmdsets(
            self.session, self.session, None, None, "session", ""
        )

        def _callback(cmdset):
            self.assertEqual(cmdset.key, "A")

        deferred.addCallback(_callback)
        return deferred

    def test_from_account(self):
        from evennia.commands.default.cmdset_account import AccountCmdSet

        a = self.cmdset_a
        a.no_channels = True
        self.set_cmdsets(self.account, a)
        deferred = cmdhandler.get_and_merge_cmdsets(
            self.account, None, self.account, None, "account", ""
        )
        # get_and_merge_cmdsets converts  to lower-case internally.

        def _callback(cmdset):
            pcmdset = AccountCmdSet()
            pcmdset.at_cmdset_creation()
            pcmds = [cmd.key for cmd in pcmdset.commands] + ["a", "b", "c", "d"]
            self.assertTrue(all(cmd.key in pcmds for cmd in cmdset.commands))

        # _callback = lambda cmdset: self.assertEqual(sum(1 for cmd in cmdset.commands if cmd.key in ("a", "b", "c", "d")), 4)
        deferred.addCallback(_callback)
        return deferred

    def test_from_object(self):
        self.set_cmdsets(self.obj1, self.cmdset_a)
        deferred = cmdhandler.get_and_merge_cmdsets(self.obj1, None, None, self.obj1, "object", "")
        # get_and_merge_cmdsets converts  to lower-case internally.

        def _callback(cmdset):
            return self.assertEqual(
                sum(1 for cmd in cmdset.commands if cmd.key in ("a", "b", "c", "d")), 4
            )

        deferred.addCallback(_callback)
        return deferred

    def test_multimerge(self):
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.no_exits = True
        a.no_channels = True
        self.set_cmdsets(self.obj1, a, b, c, d)

        deferred = cmdhandler.get_and_merge_cmdsets(self.obj1, None, None, self.obj1, "object", "")

        def _callback(cmdset):
            self.assertTrue(cmdset.no_exits)
            self.assertTrue(cmdset.no_channels)
            self.assertEqual(cmdset.key, "D")

        deferred.addCallback(_callback)
        return deferred

    def test_autocmdsets(self):
        import evennia
        from evennia.commands.default.cmdset_account import AccountCmdSet
        from evennia.comms.channelhandler import CHANNEL_HANDLER

        testchannel = evennia.create_channel("channeltest", locks="listen:all();send:all()")
        CHANNEL_HANDLER.add(testchannel)
        CHANNEL_HANDLER.update()
        self.assertTrue(testchannel.connect(self.account))
        self.assertTrue(testchannel.has_connection(self.account))
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        self.set_cmdsets(self.account, a, b, c, d)
        deferred = cmdhandler.get_and_merge_cmdsets(
            self.session, self.session, self.account, self.char1, "session", ""
        )

        def _callback(cmdset):
            pcmdset = AccountCmdSet()
            pcmdset.at_cmdset_creation()
            pcmds = [cmd.key for cmd in pcmdset.commands] + ["a", "b", "c", "d"] + ["out"]
            self.assertTrue(
                all(cmd.key or hasattr(cmd, "is_channel") in pcmds for cmd in cmdset.commands)
            )
            self.assertTrue(any(hasattr(cmd, "is_channel") for cmd in cmdset.commands))

        deferred.addCallback(_callback)
        return deferred

    def test_duplicates(self):
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.no_exits = True
        a.no_channels = True
        b.duplicates = True
        d.duplicates = True
        self.set_cmdsets(self.obj1, a, b, c, d)
        deferred = cmdhandler.get_and_merge_cmdsets(self.obj1, None, None, self.obj1, "object", "")

        def _callback(cmdset):
            self.assertEqual(len(cmdset.commands), 9)

        deferred.addCallback(_callback)
        return deferred


class AccessableCommand(Command):
    def access(*args, **kwargs):
        return True


class _CmdTest1(AccessableCommand):
    key = "test1"


class _CmdTest2(AccessableCommand):
    key = "another command"


class _CmdTest3(AccessableCommand):
    key = "&the third command"


class _CmdTest4(AccessableCommand):
    key = "test2"


class _CmdSetTest(CmdSet):
    key = "test_cmdset"

    def at_cmdset_creation(self):
        self.add(_CmdTest1)
        self.add(_CmdTest2)
        self.add(_CmdTest3)


class TestCmdParser(TestCase):
    def test_create_match(self):
        class DummyCmd:
            pass

        dummy = DummyCmd()

        self.assertEqual(
            cmdparser.create_match("look at", "look at target", dummy, "look"),
            ("look at", " target", dummy, 7, 0.5, "look"),
        )

    @override_settings(CMD_IGNORE_PREFIXES="@&/+")
    def test_build_matches(self):
        a_cmdset = _CmdSetTest()
        bcmd = [cmd for cmd in a_cmdset.commands if cmd.key == "test1"][0]

        # normal parsing
        self.assertEqual(
            cmdparser.build_matches("test1 rock", a_cmdset, include_prefixes=False),
            [("test1", " rock", bcmd, 5, 0.5, "test1")],
        )

        # test prefix exclusion
        bcmd = [cmd for cmd in a_cmdset.commands if cmd.key == "another command"][0]
        self.assertEqual(
            cmdparser.build_matches(
                "@another command smiles to me  ", a_cmdset, include_prefixes=False
            ),
            [("another command", " smiles to me  ", bcmd, 15, 0.5, "another command")],
        )
        # test prefix exclusion on the cmd class
        bcmd = [cmd for cmd in a_cmdset.commands if cmd.key == "&the third command"][0]
        self.assertEqual(
            cmdparser.build_matches("the third command", a_cmdset, include_prefixes=False),
            [("the third command", "", bcmd, 17, 1.0, "&the third command")],
        )

    @override_settings(SEARCH_MULTIMATCH_REGEX=r"(?P<number>[0-9]+)-(?P<name>.*)")
    def test_num_prefixes(self):
        self.assertEqual(cmdparser.try_num_prefixes("look me"), (None, None))
        self.assertEqual(cmdparser.try_num_prefixes("3-look me"), ("3", "look me"))
        self.assertEqual(cmdparser.try_num_prefixes("567-look me"), ("567", "look me"))

    @override_settings(
        SEARCH_MULTIMATCH_REGEX=r"(?P<number>[0-9]+)-(?P<name>.*)", CMD_IGNORE_PREFIXES="@&/+"
    )
    def test_cmdparser(self):
        a_cmdset = _CmdSetTest()
        bcmd = [cmd for cmd in a_cmdset.commands if cmd.key == "test1"][0]

        self.assertEqual(
            cmdparser.cmdparser("test1hello", a_cmdset, None),
            [("test1", "hello", bcmd, 5, 0.5, "test1")],
        )
