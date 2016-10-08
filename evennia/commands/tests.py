"""
Unit testing for the Command system itself.

"""

from evennia.utils.test_resources import EvenniaTest, SESSIONS
from evennia.commands.cmdset import CmdSet
from evennia.commands.command import Command


# Testing-command sets

class _CmdA(Command):
    key = "A"
    def __init__(self, cmdset, *args, **kwargs):
        super(_CmdA, self).__init__(*args, **kwargs)
        self.from_cmdset = cmdset
class _CmdB(Command):
    key = "B"
    def __init__(self, cmdset, *args, **kwargs):
        super(_CmdB, self).__init__(*args, **kwargs)
        self.from_cmdset = cmdset
class _CmdC(Command):
    key = "C"
    def __init__(self, cmdset, *args, **kwargs):
        super(_CmdC, self).__init__(*args, **kwargs)
        self.from_cmdset = cmdset
class _CmdD(Command):
    key = "D"
    def __init__(self, cmdset, *args, **kwargs):
        super(_CmdD, self).__init__(*args, **kwargs)
        self.from_cmdset = cmdset

class _CmdSetA(CmdSet):
    key = "A"
    def  at_cmdset_creation(self):
        self.add(_CmdA("A"))
        self.add(_CmdB("A"))
        self.add(_CmdC("A"))
        self.add(_CmdD("A"))
class _CmdSetB(CmdSet):
    key = "B"
    def  at_cmdset_creation(self):
        self.add(_CmdA("B"))
        self.add(_CmdB("B"))
        self.add(_CmdC("B"))
class _CmdSetC(CmdSet):
    key = "C"
    def  at_cmdset_creation(self):
        self.add(_CmdA("C"))
        self.add(_CmdB("C"))
class _CmdSetD(CmdSet):
    key = "D"
    def  at_cmdset_creation(self):
        self.add(_CmdA("D"))
        self.add(_CmdB("D"))
        self.add(_CmdC("D"))
        self.add(_CmdD("D"))

# testing Command Sets

class TestCmdSetMergers(EvenniaTest):
    "Test merging of cmdsets"
    def setUp(self):
        super(TestCmdSetMergers, self).setUp()
        self.cmdset_a = _CmdSetA()
        self.cmdset_b = _CmdSetB()
        self.cmdset_c = _CmdSetC()
        self.cmdset_d = _CmdSetD()

    def test_order(self):
        "Merge in reverse- and forward orders, same priorities"
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        cmdset_f = d + c + b + a # merge in reverse order of priority
        self.assertEqual(cmdset_f.priority, 0)
        self.assertEqual(cmdset_f.mergetype, "Union")
        self.assertEqual(len(cmdset_f.commands), 4)
        self.assertTrue(all(True for cmd in cmdset_f.commands if cmd.from_cmdset == "A"))
        cmdset_f = a + b + c + d # merge in order of priority
        self.assertEqual(cmdset_f.priority, 0)
        self.assertEqual(cmdset_f.mergetype, "Union")
        self.assertEqual(len(cmdset_f.commands), 4) # duplicates setting from A transfers
        self.assertTrue(all(True for cmd in cmdset_f.commands if cmd.from_cmdset == "D"))

    def test_priority_order(self):
        "Merge in reverse- and forward order with well-defined prioritities"
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = 2
        b.priority = 1
        c.priority = 0
        d.priority = -1
        cmdset_f = d + c + b + a # merge in reverse order of priority
        self.assertEqual(cmdset_f.priority, 2)
        self.assertEqual(cmdset_f.mergetype, "Union")
        self.assertEqual(len(cmdset_f.commands), 4)
        self.assertTrue(all(True for cmd in cmdset_f.commands if cmd.from_cmdset == "A"))
        cmdset_f = a + b + c + d # merge in order of priority
        self.assertEqual(cmdset_f.priority, 2)
        self.assertEqual(cmdset_f.mergetype, "Union")
        self.assertEqual(len(cmdset_f.commands), 4)
        self.assertTrue(all(True for cmd in cmdset_f.commands if cmd.from_cmdset == "A"))

    def test_option_transfer(self):
        "Test transfer of cmdset options"
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.no_exits = True
        a.no_objs = True
        a.no_channels = True
        a.duplicates = True
        cmdset_f = d + c + b + a # reverse, same-prio
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertTrue(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 8)
        cmdset_f = a + b + c + d # forward, same-prio
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertTrue(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)
        a.priority = 2
        b.priority = 1
        c.priority = 0
        d.priority = -1
        cmdset_f = d + c + b + a # reverse, A top priority
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertTrue(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)
        cmdset_f = a + b + c + d # forward, A top priority
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertTrue(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)
        a.priority = -1
        b.priority = 0
        c.priority = 1
        d.priority = 2
        cmdset_f = d + c + b + a # reverse, A low prio
        self.assertFalse(cmdset_f.no_exits)
        self.assertFalse(cmdset_f.no_objs)
        self.assertFalse(cmdset_f.no_channels)
        self.assertFalse(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)
        cmdset_f = a + b + c + d # forward, A low prio
        self.assertFalse(cmdset_f.no_exits)
        self.assertFalse(cmdset_f.no_objs)
        self.assertFalse(cmdset_f.no_channels)
        self.assertFalse(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)
        a.priority = 0
        b.priority = 0
        c.priority = 0
        d.priority = 0
        c.duplicates = True
        cmdset_f = d + b + c + a # two last mergers duplicates=True
        self.assertEqual(len(cmdset_f.commands), 10)




