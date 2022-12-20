"""
Unit testing for the Command system itself.

"""

from django.test import override_settings

from evennia.commands import cmdparser
from evennia.commands.cmdset import CmdSet
from evennia.commands.command import Command
from evennia.utils.test_resources import BaseEvenniaTest, TestCase

# Testing-command sets


class _BaseCmd(Command):
    def __init__(self, cmdset, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.from_cmdset = cmdset


class _CmdA(_BaseCmd):
    key = "A"


class _CmdB(_BaseCmd):
    key = "B"


class _CmdC(_BaseCmd):
    key = "C"


class _CmdD(_BaseCmd):
    key = "D"


class _CmdEe(_BaseCmd):
    key = "E"
    aliases = ["ee"]


class _CmdEf(_BaseCmd):
    key = "E"
    aliases = ["ff"]


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


class _CmdSetEe_Ef(CmdSet):
    key = "Ee_Ef"

    def at_cmdset_creation(self):
        self.add(_CmdEe("Ee"))
        self.add(_CmdEf("Ee"))


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


class TestOptionTransferTrue(TestCase):
    """
    Test cmdset-merge transfer of the cmdset-special options
    (no_exits/channels/objs/duplicates etc)

    cmdset A has all True options

    """

    def setUp(self):
        super().setUp()
        self.cmdset_a = _CmdSetA()
        self.cmdset_b = _CmdSetB()
        self.cmdset_c = _CmdSetC()
        self.cmdset_d = _CmdSetD()
        self.cmdset_a.priority = 0
        self.cmdset_b.priority = 0
        self.cmdset_c.priority = 0
        self.cmdset_d.priority = 0
        self.cmdset_a.no_exits = True
        self.cmdset_a.no_objs = True
        self.cmdset_a.no_channels = True
        self.cmdset_a.duplicates = True

    def test_option_transfer__reverse_sameprio_passthrough(self):
        """
        A has all True options, merges last (normal reverse merge), same prio.
        The options should pass through to F since none of the other cmdsets
        care to change the setting from their default None.

        Since A.duplicates = True, the final result is an union of duplicate
        pairs (8 commands total).

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        cmdset_f = d + c + b + a  # reverse, same-prio
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 8)

    def test_option_transfer__forward_sameprio_passthrough(self):
        """
        A has all True options, merges first (forward merge), same prio. This
        should pass those options through since the other all have options set
        to None. The exception is `duplicates` since that is determined by
        the two last mergers in the chain both being True.

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        cmdset_f = a + b + c + d  # forward, same-prio
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__reverse_highprio_passthrough(self):
        """
        A has all True options, merges last (normal reverse  merge) with the
        highest prio. This should also pass through.
        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = 2
        b.priority = 1
        c.priority = 0
        d.priority = -1
        cmdset_f = d + c + b + a  # reverse, A top priority
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__forward_highprio_passthrough(self):
        """
        A has all True options, merges first (forward merge). This is a bit
        synthetic since it will never happen in practice, but logic should
        still make it pass through.
        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = 2
        b.priority = 1
        c.priority = 0
        d.priority = -1
        cmdset_f = a + b + c + d  # forward, A top priority. This never happens in practice.
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__reverse_lowprio_passthrough(self):
        """
        A has all True options, merges last (normal reverse merge) with the lowest
        prio. This never happens (it would always merge first) but logic should hold
        and pass through since the other cmdsets have None.

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = -1
        b.priority = 0
        c.priority = 1
        d.priority = 2
        cmdset_f = d + c + b + a  # reverse, A low prio. This never happens in practice.
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__forward_lowprio_passthrough(self):
        """
        A has all True options, merges first (forward merge) with lowest prio. This
        is the normal behavior for a low-prio cmdset. Passthrough should happen.
        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = -1
        b.priority = 0
        c.priority = 1
        d.priority = 2
        cmdset_f = a + b + c + d  # forward, A low prio
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__reverse_highprio_block_passthrough(self):
        """
        A has all True options, other cmdsets has False. A merges last with high
        prio. A should retain its option values and override the others

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = 2
        b.priority = 1
        c.priority = 0
        d.priority = -1
        c.no_exits = False
        b.no_objs = False
        d.duplicates = False
        # higher-prio sets will change the option up the chain
        cmdset_f = d + c + b + a  # reverse, high prio
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__forward_highprio_block_passthrough(self):
        """
        A has all True options, other cmdsets has False. A merges last with high
        prio. This situation should never happen, but logic should hold - the highest
        prio's options should survive the merge process.

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = 2
        b.priority = 1
        c.priority = 0
        d.priority = -1
        c.no_exits = False
        b.no_channels = False
        b.no_objs = False
        d.duplicates = False
        # higher-prio sets will change the option up the chain
        cmdset_f = a + b + c + d  # forward, high prio, never happens
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__forward_lowprio_block(self):
        """
        A has all True options, other cmdsets has False. A merges last with low
        prio. This should result in its values being blocked and come out False.

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = -1
        b.priority = 0
        c.priority = 1
        d.priority = 2
        c.no_exits = False
        c.no_channels = False
        b.no_objs = False
        d.duplicates = False
        # higher-prio sets will change the option up the chain
        cmdset_f = a + b + c + d  # forward, A low prio
        self.assertFalse(cmdset_f.no_exits)
        self.assertFalse(cmdset_f.no_objs)
        self.assertFalse(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__forward_lowprio_block_partial(self):
        """
        A has all True options, other cmdsets has False excet C which has a None
        for `no_channels`. A merges last with low
        prio. This should result in its values being blocked and come out False
        except for no_channels which passes through.

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = -1
        b.priority = 0
        c.priority = 1
        d.priority = 2
        c.no_exits = False
        c.no_channels = None  # passthrough
        b.no_objs = False
        d.duplicates = False
        # higher-prio sets will change the option up the chain
        cmdset_f = a + b + c + d  # forward, A low prio
        self.assertFalse(cmdset_f.no_exits)
        self.assertFalse(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__reverse_highprio_sameprio_order_last(self):
        """
        A has all True options and highest prio, D has False and lowest prio,
        others are passthrough. B has the same prio as A, with passthrough.

        Since A is merged last, this should give prio to A's options
        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = 2
        b.priority = 2
        c.priority = 0
        d.priority = -1
        d.no_channels = False
        d.no_exits = False
        d.no_objs = None
        d.duplicates = False
        # higher-prio sets will change the option up the chain
        cmdset_f = d + c + b + a  # reverse, A same prio, merged after b
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 8)

    def test_option_transfer__reverse_highprio_sameprio_order_first(self):
        """
        A has all True options and highest prio, D has False and lowest prio,
        others are passthrough. B has the same prio as A, with passthrough.

        While B, with None-values, is merged after A, A's options should have
        replaced those of D at that point, and since B has passthrough the
        final result should contain A's True options.

        Note that despite A having duplicates=True, there is no duplication in
        the DB + A merger since they have different priorities.

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = 2
        b.priority = 2
        c.priority = 0
        d.priority = -1
        d.no_channels = False
        d.no_exits = False
        d.no_objs = False
        d.duplicates = False
        # higher-prio sets will change the option up the chain
        cmdset_f = d + c + a + b  # reverse, A same prio, merged before b
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__reverse_lowprio_block(self):
        """
        A has all True options, other cmdsets has False. A merges last with low
        prio. This usually doesn't happen- it should merge last. But logic should
        hold and the low-prio cmdset's values should be blocked and come out False.

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = -1
        b.priority = 0
        c.priority = 1
        d.priority = 2
        c.no_exits = False
        d.no_channels = False
        b.no_objs = False
        d.duplicates = False
        # higher-prio sets will change the option up the chain
        cmdset_f = d + c + b + a  # reverse, A low prio, never happens
        self.assertFalse(cmdset_f.no_exits)
        self.assertFalse(cmdset_f.no_objs)
        self.assertFalse(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)


class TestOptionTransferFalse(TestCase):
    """
    Test cmdset-merge transfer of the cmdset-special options
    (no_exits/channels/objs/duplicates etc)

    cmdset A has all False options

    """

    def setUp(self):
        super().setUp()
        self.cmdset_a = _CmdSetA()
        self.cmdset_b = _CmdSetB()
        self.cmdset_c = _CmdSetC()
        self.cmdset_d = _CmdSetD()
        self.cmdset_a.priority = 0
        self.cmdset_b.priority = 0
        self.cmdset_c.priority = 0
        self.cmdset_d.priority = 0
        self.cmdset_a.no_exits = False
        self.cmdset_a.no_objs = False
        self.cmdset_a.no_channels = False
        self.cmdset_a.duplicates = False

    def test_option_transfer__reverse_sameprio_passthrough(self):
        """
        A has all False options, merges last (normal reverse merge), same prio.
        The options should pass through to F since none of the other cmdsets
        care to change the setting from their default None.

        Since A has duplicates=False, the result is a unique union of 4 cmds.
        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        cmdset_f = d + c + b + a  # reverse, same-prio
        self.assertFalse(cmdset_f.no_exits)
        self.assertFalse(cmdset_f.no_objs)
        self.assertFalse(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__forward_sameprio_passthrough(self):
        """
        A has all False options, merges first (forward merge), same prio. This
        should pass those options through since the other all have options set
        to None. The exception is `duplicates` since that is determined by
        the two last mergers in the chain both being .

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        cmdset_f = a + b + c + d  # forward, same-prio
        self.assertFalse(cmdset_f.no_exits)
        self.assertFalse(cmdset_f.no_objs)
        self.assertFalse(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__reverse_highprio_passthrough(self):
        """
        A has all False options, merges last (normal reverse  merge) with the
        highest prio. This should also pass through.
        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = 2
        b.priority = 1
        c.priority = 0
        d.priority = -1
        cmdset_f = d + c + b + a  # reverse, A top priority
        self.assertFalse(cmdset_f.no_exits)
        self.assertFalse(cmdset_f.no_objs)
        self.assertFalse(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__forward_highprio_passthrough(self):
        """
        A has all False options, merges first (forward merge). This is a bit
        synthetic since it will never happen in practice, but logic should
        still make it pass through.
        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = 2
        b.priority = 1
        c.priority = 0
        d.priority = -1
        cmdset_f = a + b + c + d  # forward, A top priority. This never happens in practice.
        self.assertFalse(cmdset_f.no_exits)
        self.assertFalse(cmdset_f.no_objs)
        self.assertFalse(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__reverse_lowprio_passthrough(self):
        """
        A has all False options, merges last (normal reverse merge) with the lowest
        prio. This never happens (it would always merge first) but logic should hold
        and pass through since the other cmdsets have None.

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = -1
        b.priority = 0
        c.priority = 1
        d.priority = 2
        cmdset_f = d + c + b + a  # reverse, A low prio. This never happens in practice.
        self.assertFalse(cmdset_f.no_exits)
        self.assertFalse(cmdset_f.no_objs)
        self.assertFalse(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__forward_lowprio_passthrough(self):
        """
        A has all False options, merges first (forward merge) with lowest prio. This
        is the normal behavior for a low-prio cmdset. Passthrough should happen.
        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = -1
        b.priority = 0
        c.priority = 1
        d.priority = 2
        cmdset_f = a + b + c + d  # forward, A low prio
        self.assertFalse(cmdset_f.no_exits)
        self.assertFalse(cmdset_f.no_objs)
        self.assertFalse(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__reverse_highprio_block_passthrough(self):
        """
        A has all False options, other cmdsets has True. A merges last with high
        prio. A should retain its option values and override the others

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = 2
        b.priority = 1
        c.priority = 0
        d.priority = -1
        c.no_exits = True
        b.no_objs = True
        d.duplicates = True
        # higher-prio sets will change the option up the chain
        cmdset_f = d + c + b + a  # reverse, high prio
        self.assertFalse(cmdset_f.no_exits)
        self.assertFalse(cmdset_f.no_objs)
        self.assertFalse(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__forward_highprio_block_passthrough(self):
        """
        A has all False options, other cmdsets has True. A merges last with high
        prio. This situation should never happen, but logic should hold - the highest
        prio's options should survive the merge process.

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = 2
        b.priority = 1
        c.priority = 0
        d.priority = -1
        c.no_exits = True
        b.no_channels = True
        b.no_objs = True
        d.duplicates = True
        # higher-prio sets will change the option up the chain
        cmdset_f = a + b + c + d  # forward, high prio, never happens
        self.assertFalse(cmdset_f.no_exits)
        self.assertFalse(cmdset_f.no_objs)
        self.assertFalse(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__forward_lowprio_block(self):
        """
        A has all False options, other cmdsets has True. A merges last with low
        prio. This should result in its values being blocked and come out False.

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = -1
        b.priority = 0
        c.priority = 1
        d.priority = 2
        c.no_exits = True
        c.no_channels = True
        b.no_objs = True
        d.duplicates = True
        # higher-prio sets will change the option up the chain
        cmdset_f = a + b + c + d  # forward, A low prio
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__forward_lowprio_block_partial(self):
        """
        A has all False options, other cmdsets has True excet C which has a None
        for `no_channels`. A merges last with low
        prio. This should result in its values being blocked and come out True
        except for no_channels which passes through.

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = -1
        b.priority = 0
        c.priority = 1
        d.priority = 2
        c.no_exits = True
        c.no_channels = None  # passthrough
        b.no_objs = True
        d.duplicates = True
        # higher-prio sets will change the option up the chain
        cmdset_f = a + b + c + d  # forward, A low prio
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertFalse(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__reverse_sameprio_order_last(self):
        """
        A has all False options and highest prio, D has True and lowest prio,
        others are passthrough. B has the same prio as A, with passthrough.

        Since A is merged last, this should give prio to A's False options
        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = 2
        b.priority = 2
        c.priority = 0
        d.priority = -1
        d.no_channels = True
        d.no_exits = True
        d.no_objs = True
        d.duplicates = False
        # higher-prio sets will change the option up the chain
        cmdset_f = d + c + b + a  # reverse, A high prio, merged after b
        self.assertFalse(cmdset_f.no_exits)
        self.assertFalse(cmdset_f.no_objs)
        self.assertFalse(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__reverse_sameprio_order_first(self):
        """
        A has all False options and highest prio, D has True and lowest prio,
        others are passthrough. B has the same prio as A, with passthrough.

        While B, with None-values, is merged after A, A's options should have
        replaced those of D at that point, and since B has passthrough the
        final result should contain A's False options.

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = 2
        b.priority = 2
        c.priority = 0
        d.priority = -1
        d.no_channels = True
        d.no_exits = True
        d.no_objs = True
        d.duplicates = False

        # higher-prio sets will change the option up the chain
        cmdset_f = d + c + a + b  # reverse, A high prio, merged before b
        self.assertFalse(cmdset_f.no_exits)
        self.assertFalse(cmdset_f.no_objs)
        self.assertFalse(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)

    def test_option_transfer__reverse_lowprio_block(self):
        """
        A has all False options, other cmdsets has True. A merges last with low
        prio. This usually doesn't happen- it should merge last. But logic should
        hold and the low-prio cmdset's values should be blocked and come out True.

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = -1
        b.priority = 0
        c.priority = 1
        d.priority = 2
        c.no_exits = True
        d.no_channels = True
        b.no_objs = True
        d.duplicates = True
        # higher-prio sets will change the option up the chain
        cmdset_f = d + c + b + a  # reverse, A low prio, never happens
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)


class TestDuplicateBehavior(TestCase):
    """
    Test behavior of .duplicate option, which is a bit special in that it
    doesn't propagate.

    `A.duplicates=True` for all tests.

    """

    def setUp(self):
        super().setUp()
        self.cmdset_a = _CmdSetA()
        self.cmdset_b = _CmdSetB()
        self.cmdset_c = _CmdSetC()
        self.cmdset_d = _CmdSetD()
        self.cmdset_a.priority = 0
        self.cmdset_b.priority = 0
        self.cmdset_c.priority = 0
        self.cmdset_d.priority = 0
        self.cmdset_a.duplicates = True

    def test_reverse_sameprio_duplicate__implicit(self):
        """
        Test of `duplicates` transfer which does not propagate. Only
        A has duplicates=True.

        D + B = DB (no duplication, DB.duplication=None)
        DB + C = DBC  (no duplication, DBC.duplication=None)
        DBC + A = final (duplication, final.duplication=None)

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        cmdset_f = d + b + c + a  # two last mergers duplicates=True
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 8)

    def test_reverse_sameprio_duplicate__explicit(self):
        """
        Test of `duplicates` transfer, which does not propagate.
        C.duplication=True

        D + B = DB (no duplication, DB.duplication=None)
        DB + C = DBC  (duplication, DBC.duplication=None)
        DBC + A = final (duplication, final.duplication=None)

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        c.duplicates = True
        cmdset_f = d + b + c + a  # two last mergers duplicates=True
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 10)

    def test_forward_sameprio_duplicate(self):
        """
        Test of `duplicates` transfer which does not propagate.
        C.duplication=True, merges later than A

        D + B = DB (no duplication, DB.duplication=None)
        DB + A = DBA (duplication, DBA.duplication=None)
        DBA + C = final (duplication, final.duplication=None)

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        c.duplicates = True
        cmdset_f = d + b + a + c  # two last mergers duplicates=True
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 10)

    def test_reverse_sameprio_duplicate_reverse(self):
        """
        Test of `duplicates` transfer which does not propagate.
        C.duplication=False (explicit), merges before A. This behavior is the
        same as if C.duplication=None, since A merges later and takes
        precedence.

        D + B = DB (no duplication, DB.duplication=None)
        DB + C = DBC  (no duplication, DBC.duplication=None)
        DBC + A = final (duplication, final.duplication=None)

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        c.duplicates = False
        cmdset_f = d + b + c + a  # a merges last, takes precedence
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 8)

    def test_reverse_sameprio_duplicate_forward(self):
        """
        Test of `duplicates` transfer which does not propagate.
        C.duplication=False (explicit), merges after A. This just means
        only A causes duplicates, earlier in the chain.

        D + B = DB (no duplication, DB.duplication=None)
        DB + A = DBA (duplication, DBA.duplication=None)
        DBA + C = final (no duplication, final.duplication=None)

        Note that DBA has 8 cmds due to A merging onto DB with duplication,
        but since C merges onto this with no duplication, the union will hold
        6 commands, since C has two commands that replaces the 4 duplicates
        with uniques copies from C.

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        c.duplicates = False
        cmdset_f = d + b + a + c  # a merges before c
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 6)


class TestOptionTransferReplace(TestCase):
    """
    Test option transfer through more complex merge types.
    """

    def setUp(self):
        super().setUp()
        self.cmdset_a = _CmdSetA()
        self.cmdset_b = _CmdSetB()
        self.cmdset_c = _CmdSetC()
        self.cmdset_d = _CmdSetD()
        self.cmdset_a.priority = 0
        self.cmdset_b.priority = 0
        self.cmdset_c.priority = 0
        self.cmdset_d.priority = 0
        self.cmdset_a.no_exits = True
        self.cmdset_a.no_objs = True
        self.cmdset_a.no_channels = True
        self.cmdset_a.duplicates = True

    def test_option_transfer__replace_reverse_highprio(self):
        """
        A has all options True and highest priority. C has them False and is
        Replace-type.

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.priority = 2
        b.priority = 2
        c.priority = 0
        c.mergetype = "Replace"
        c.no_channels = False
        c.no_exits = False
        c.no_objs = False
        c.duplicates = False
        d.priority = -1

        cmdset_f = d + c + b + a  # reverse, A high prio, C Replace
        self.assertTrue(cmdset_f.no_exits)
        self.assertTrue(cmdset_f.no_objs)
        self.assertTrue(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 7)

    def test_option_transfer__replace_reverse_highprio_from_false(self):
        """
        Inverse of previous test: A has all options False and highest priority.
        C has them True and is Replace-type.

        """
        a, b, c, d = self.cmdset_a, self.cmdset_b, self.cmdset_c, self.cmdset_d
        a.no_exits = False
        a.no_objs = False
        a.no_channels = False
        a.duplicates = False

        a.priority = 2
        b.priority = 2
        c.priority = 0
        c.mergetype = "Replace"
        c.no_channels = True
        c.no_exits = True
        c.no_objs = True
        c.duplicates = True
        d.priority = -1

        cmdset_f = d + c + b + a  # reverse, A high prio, C Replace
        self.assertFalse(cmdset_f.no_exits)
        self.assertFalse(cmdset_f.no_objs)
        self.assertFalse(cmdset_f.no_channels)
        self.assertIsNone(cmdset_f.duplicates)
        self.assertEqual(len(cmdset_f.commands), 4)


# test cmdhandler functions


import sys

from twisted.trial.unittest import TestCase as TwistedTestCase

from evennia.commands import cmdhandler


def _mockdelay(time, func, *args, **kwargs):
    return func(*args, **kwargs)


class TestGetAndMergeCmdSets(TwistedTestCase, BaseEvenniaTest):
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
            self.assertEqual(set(cmd.key for cmd in cmdset.commands), set(pcmds))

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

    def test_command_replace_different_aliases(self):
        cmdset_ee = _CmdSetEe_Ef()
        self.assertEqual(len(cmdset_ee.commands), 1)
        self.assertEqual(cmdset_ee.commands[0].key, "e")


class AccessableCommand(Command):
    def access(*args, **kwargs):
        return True


class _CmdTest1(AccessableCommand):
    key = "test1"
    arg_regex = None


class _CmdTest2(AccessableCommand):
    key = "another command"
    arg_regex = None


class _CmdTest3(AccessableCommand):
    key = "&the third command"
    arg_regex = None


class _CmdTest4(AccessableCommand):
    key = "test2"
    arg_regex = None


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
    def test_num_differentiators(self):
        self.assertEqual(cmdparser.try_num_differentiators("look me"), (None, None))
        self.assertEqual(cmdparser.try_num_differentiators("look me-3"), (3, "look me"))
        self.assertEqual(cmdparser.try_num_differentiators("look me-567"), (567, "look me"))

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


class TestCmdSetNesting(BaseEvenniaTest):
    """
    Test 'nesting' of cmdsets by adding
    """

    def test_nest(self):
        class CmdA(Command):
            key = "a"

            def func(self):
                self.msg(str(self.obj))

        class CmdSetA(CmdSet):
            def at_cmdset_creation(self):
                self.add(CmdA)

        class CmdSetB(CmdSet):
            def at_cmdset_creation(self):
                self.add(CmdSetA)

        cmd = self.char1.cmdset.cmdset_stack[-1].commands[0]
        self.assertEqual(cmd.obj, self.char1)


class TestCmdSet(BaseEvenniaTest):
    """
    General tests for cmdsets
    """

    def test_cmdset_remove_by_key(self):
        test_cmd_set = _CmdSetTest()
        test_cmd_set.remove("another command")

        self.assertNotIn(_CmdTest2, test_cmd_set.commands)

    def test_cmdset_gets_by_key(self):
        test_cmd_set = _CmdSetTest()
        result = test_cmd_set.get("another command")

        self.assertIsInstance(result, _CmdTest2)
