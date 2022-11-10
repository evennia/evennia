"""
Slow exit tests.

"""

from mock import Mock, patch

from evennia.commands.default.tests import BaseEvenniaCommandTest
from evennia.utils.create import create_object

from . import slow_exit

slow_exit.MOVE_DELAY = {"stroll": 0, "walk": 0, "run": 0, "sprint": 0}


def _cancellable_mockdelay(time, callback, *args, **kwargs):
    callback(*args, **kwargs)
    return Mock()


class TestSlowExit(BaseEvenniaCommandTest):
    @patch("evennia.utils.delay", _cancellable_mockdelay)
    def test_exit(self):
        exi = create_object(
            slow_exit.SlowExit, key="slowexit", location=self.room1, destination=self.room2
        )
        exi.at_traverse(self.char1, self.room2)
        self.call(slow_exit.CmdSetSpeed(), "walk", "You are now walking.")
        self.call(slow_exit.CmdStop(), "", "You stop moving.")
