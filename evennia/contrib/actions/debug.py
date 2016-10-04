"""
Debug commands that are always preceded by "@@" in-game to distinguish them
from regular player and admin commands.
"""

from evennia import CmdSet
from evennia.commands.command import Command

from evennia.contrib.actions.actions import Action
from evennia.contrib.actions.utils import setup


class ActionDebugCmdSet(CmdSet):
    """CmdSet for debugging commands."""
    key = "debug_cmdset"
    priority = 1

    def at_cmdset_creation(self):
        self.add(CmdDebugActSlow())
        self.add(CmdDebugActFast())
        self.add(CmdDebugActLeftArm())
        self.add(CmdDebugActRightArm())
        self.add(CmdDebugActFriend())
        self.add(CmdDebugActFoe())
        self.add(CmdDebugActSetup())
        self.add(CmdDebugMessages())


class CmdDebugActSlow(Command):
    """
    Allows testing of the start, completion and cancelling of an action
    in real-time and turn-based mode. This action's duration is 30 seconds.
    """
    key = "@@actslow"
    #aliases = [""]
    locks = "cmd:perm(Wizards)"
    help_category = "Debug"

    def func(self):
        DebugActionSlow(self.caller, self.caller.location)


class DebugActionSlow(Action):
    def __init__(self, owner, room):
        duration = 10
        super(DebugActionSlow, self).__init__(
            key="DebugActionSlow",
            desc="performing a slow action",
            owner=owner,
            room=room,
            bodyparts=None,
            target=None,
            data=None,
            cancellable=True,
            invokes_tb=False,
            non_turn=False,
            msg_defaults=False,
            begin_msg="has begun testing.",
            duration=duration,
            )
        

class CmdDebugActFast(Command):
    """
    Allows testing of the start, completion and cancelling of an action
    in real-time and turn-based mode. This action's duration is 10 seconds.
    """
    key = "@@actfast"
    #aliases = [""]
    locks = "cmd:perm(Wizards)"
    help_category = "Debug"

    def func(self):
        DebugActionFast(self.caller, self.caller.location)


class DebugActionFast(Action):
    def __init__(self, owner, room):
        duration = 2
        super(DebugActionFast, self).__init__(
            key="DebugActionFast",
            desc="performing a fast action",
            owner=owner,
            room=room,
            bodyparts=None,
            target=None,
            data=None,
            cancellable=True,
            invokes_tb=False,
            non_turn=False,
            duration=duration,
            )


class CmdDebugActLeftArm(Command):
    """
    Triggers a single action that uses the left arm.
    In conjunction with CmdDebugActRightArm, allows testing of the use of
    bodyparts in the action system, as well as enqueuing and overriding actions.
    """
    key = "@@actlarm"
    locks = "cmd:perm(Wizards)"
    help_category = "Debug"

    def func(self):
        DebugActionLeftArm(self.caller, self.caller.location)


class DebugActionLeftArm(Action):
    def __init__(self, owner, room):
        duration = 7
        super(DebugActionLeftArm, self).__init__(
            key="DebugActionLeftArm",
            desc="performing an action with their left arm",
            owner=owner,
            room=room,
            bodyparts='left arm',
            target=None,
            data=None,
            cancellable=True,
            invokes_tb=False,
            non_turn=False,
            duration=duration,
            )


class CmdDebugActRightArm(Command):
    """
    Triggers a single action that uses the right arm.
    In conjunction with CmdDebugActLeftArm, allows testing of the use of
    bodyparts in the action system, as well as enqueuing and overriding actions.
    """
    key = "@@actrarm"
    locks = "cmd:perm(Wizards)"
    help_category = "Debug"

    def func(self):
        DebugActionRightArm(self.caller, self.caller.location)

class DebugActionRightArm(Action):
    def __init__(self, owner, room):
        duration = 7
        super(DebugActionRightArm, self).__init__(
            key="DebugActionRightArm",
            desc="performing an action with their right arm",
            owner=owner,
            room=room,
            bodyparts='right arm',
            target=None,
            data=None,
            cancellable=True,
            invokes_tb=False,
            non_turn=False,
            duration=duration,
            )


class CmdDebugActFriend(Command):
    """
    Triggers a single action that uses the right arm.
    In conjunction with CmdDebugActLeftArm, allows testing of the use of
    bodyparts in the action system, as well as enqueuing and overriding actions.
    """
    key = "@@actfriend"
    locks = "cmd:perm(Wizards)"
    help_category = "Debug"

    def func(self):
        s = self.args.strip()
        if not s:
            self.caller.msg("Please supply a target.")
            return
        target = self.caller.search(s)
        if not target:
            self.caller.msg("Could not find {0} to target.".format(s))
            return
        DebugActionFriend(self.caller, self.caller.location, target)


class DebugActionFriend(Action):
    def __init__(self, owner, room, target):
        duration = 5
        super(DebugActionFriend, self).__init__(
            key="DebugActionFriend",
            desc="performing a $d good action towards $t",
            owner=owner,
            room=room,
            bodyparts='head',
            target=target,
            reach='contact',
            data="jolly",
            cancellable=True,
            invokes_tb=False,
            non_turn=False,
            duration=duration,
            )


class CmdDebugActFoe(Command):
    """
    Triggers a single action that uses the right arm.
    In conjunction with CmdDebugActLeftArm, allows testing of the use of
    bodyparts in the action system, as well as enqueuing and overriding actions.
    """
    key = "@@actfoe"
    locks = "cmd:perm(Wizards)"
    help_category = "Debug"

    def func(self):
        s = self.args.strip()
        if not s:
            self.caller.msg("Please supply a target.")
            return
        target = self.caller.search(s)
        if not target:
            self.caller.msg("Could not find {0} to target.".format(s))
            return
        DebugActionFoe(self.caller, self.caller.location, target)


class DebugActionFoe(Action):
    def __init__(self, owner, room, target):
        duration = 5
        super(DebugActionFoe, self).__init__(
            key="DebugActionFoe",
            desc="performing a $d hostile action towards $t",
            owner=owner,
            room=room,
            bodyparts=None,
            target=target,
            reach='contact',
            data="diabolically",
            cancellable=True,
            invokes_tb=True,
            non_turn=False,
            duration=duration,
            )


class CmdDebugActSetup(Command):
    """
    Resets the actions system
    """
    key = "@@actsetup"
    #aliases = [""]
    locks = "cmd:perm(wizards)"
    #arg_regex = r"$"
    help_category = "Debug"

    def func(self):
        if self.args.find("over") != -1:
            setup(override=True)
            self.caller.msg("Action system successfully overridden.")
        else:
            setup(override=False)
            self.caller.msg("Action system successfully set up.")


class CmdDebugMessages(Command):
    """
    Enables / disables debug messages

    Usage:
        @@actdebug [<on/off>]

    The use of "@@actdebug" on its own enables debug messages.
    """
    key = "@@actdebug"
    #aliases = [""]
    locks = "cmd:perm(wizards)"
    #arg_regex = r"$"
    help_category = "Debug"

    def func(self):
        if self.args.find("off") != -1:
            self.caller.msg("Debug messages disabled.")
            self.caller.tags.remove("actdebug")
        else: 
            self.caller.msg("Debug messages enabled.")
            self.caller.tags.add("actdebug")


