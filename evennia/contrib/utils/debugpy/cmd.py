import sys

from django.conf import settings
from evennia.utils import utils

COMMAND_DEFAULT_CLASS = utils.class_from_module(settings.COMMAND_DEFAULT_CLASS)

ERROR_MSG = "debugpy needed for the debugpy contrib. Admin must install it and reboot."


class CmdDebugPy(COMMAND_DEFAULT_CLASS):
    """
    Launch debugpy debugger and wait for attach on port 5678

    Usage:
      debugpy

    """

    key = "debugpy"
    locks = "cmd:perm(debugpy) or perm(Builder)"

    def func(self):

        try:
            import debugpy
        except ImportError:
            self.caller.msg(ERROR_MSG)
            return

        caller = self.caller
        caller.msg("Waiting for debugger attach...")
        yield 0.1  # make sure msg is sent first
        debugpy.listen(5678)
        debugpy.wait_for_client()
        caller.msg("Debugger attached.")
