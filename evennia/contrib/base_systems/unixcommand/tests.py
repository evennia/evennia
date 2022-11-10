"""
Test of the Unixcommand.

"""

from evennia.commands.default.tests import BaseEvenniaCommandTest

from .unixcommand import UnixCommand


class CmdDummy(UnixCommand):

    """A dummy UnixCommand."""

    key = "dummy"

    def init_parser(self):
        """Fill out options."""
        self.parser.add_argument("nb1", type=int, help="the first number")
        self.parser.add_argument("nb2", type=int, help="the second number")
        self.parser.add_argument("-v", "--verbose", action="store_true")

    def func(self):
        nb1 = self.opts.nb1
        nb2 = self.opts.nb2
        result = nb1 * nb2
        verbose = self.opts.verbose
        if verbose:
            self.msg("{} times {} is {}".format(nb1, nb2, result))
        else:
            self.msg("{} * {} = {}".format(nb1, nb2, result))


class TestUnixCommand(BaseEvenniaCommandTest):
    def test_success(self):
        """See the command parsing succeed."""
        self.call(CmdDummy(), "5 10", "5 * 10 = 50")
        self.call(CmdDummy(), "5 10 -v", "5 times 10 is 50")

    def test_failure(self):
        """If not provided with the right info, should fail."""
        ret = self.call(CmdDummy(), "5")
        lines = ret.splitlines()
        self.assertTrue(any(lin.startswith("usage:") for lin in lines))
        self.assertTrue(any(lin.startswith("dummy: error:") for lin in lines))

        # If we specify an incorrect number as parameter
        ret = self.call(CmdDummy(), "five ten")
        lines = ret.splitlines()
        self.assertTrue(any(lin.startswith("usage:") for lin in lines))
        self.assertTrue(any(lin.startswith("dummy: error:") for lin in lines))
