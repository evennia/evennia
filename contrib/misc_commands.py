"""
Evennia misc commands

Contribution - Griatch 2011

This module offers some miscellaneous commands that may be useful
depending on the game you run or the style of administration you
prefer. Alternatively they can be looked at for inspiration.

To make available in the game, make sure to follow the instructions
in game/gamesrc/commands/examples.py (copy the template up one level
and re-point the relevant settings to this new module - if you already
have such a module, you can of course use that).  Next import this module into
this custom module and add the command class(es) you want to the default
command set. You need to reload the server to make them recognized.
"""

from django.conf import settings
from src.commands.default.muxcommand import MuxCommand

PERMISSION_HIERARCHY = settings.PERMISSION_HIERARCHY
PERMISSION_HIERARCHY_LOWER = [perm.lower() for perm in PERMISSION_HIERARCHY]

class CmdQuell(MuxPlayerCommand):
    """
    Quelling permissions

    Usage:
      quell
      unquell
      quell/permlevel <command>

    Normally the permission level of the Player is used when puppeting a
    Character/Object to determine access. Giving this command without
    arguments will instead switch the lock system to make use of the
    puppeted Object's permissions instead. Note that this only works DOWNWARDS -
    a Player cannot use a higher-permission Character to escalate their Player
    permissions for example. Use the unquell command to revert this state.

    Note that the superuser character is unaffected by full quelling. Use a separate
    admin account for testing.

    When given an argument, the argument is considered a command to execute with
    a different (lower) permission level than they currently have. This is useful
    for quick testing. If no permlevel switch is given, the command will be
    executed using the lowest permission level available in settings.PERMISSION_HIERARCHY.

    Quelling singular commands will work also for the superuser.

    """

    key = "quell"
    locks = "cmd:perm(all)"
    help_category = "General"

    def func(self):
        "Perform the command"

        player = self.caller

        if not self.args:
            # try to fully quell player permissions
            if self.cmdstring == 'unquell':
                if player.get_attribute('_quell'):
                    self.msg("You are not currently quelling you Player permissions.")
                else:
                    player.del_attribute('_quell')
                    self.msg("You are now using your Player permissions normally.")
                return
            else:
                if player.is_superuser:
                    self.msg("Superusers cannot be quelled.")
                    return
                if player.get_attribute('_quell'):
                    self.msg("You are already quelling your Player permissions.")
                    return
                player.set_attribute('_quell', True)
                self.msg("You quell your Player permissions.")
                return

        cmd = self.lhs
        perm = self.switches and self.switches[0] or None

        if not PERMISSION_HIERARCHY:
            self.caller.msg("settings.PERMISSION_HIERARCHY is not defined. Add a hierarchy to use this command.")
            return
        if perm:
            if not perm.lower() in PERMISSION_HIERARCHY_LOWER:
                self.caller.msg("Unknown permission. Permission hierarchy is: [%s]" % ", ".join(PERMISSION_HIERARCHY))
                return
            if not self.caller.locks.check_lockstring(self.caller, "dummy:perm(%s)" % perm):
                self.caller.msg("You cannot use a permission higher than the one you have.")
                return
        else:
            perm = PERMISSION_HIERARCHY_LOWER[0]

        # replace permission
        oldperm = self.caller.permissions
        old_superuser = self.caller.player.user.is_superuser
        newperm = [perm] + [perm for perm in oldperm if perm not in PERMISSION_HIERARCHY_LOWER]
        self.caller.permissions = newperm
        self.caller.player.user.is_superuser = False
        self.caller.player.user.save()

        def callback(ret):
            self.caller.msg(ret)
        def errback(err):
            self.caller.msg(err)

        # this returns a deferred, so we need to assign callbacks
        self.caller.execute_cmd(cmd).addCallbacks(callback, errback)

        self.caller.permissions = oldperm
        self.caller.player.user.is_superuser = old_superuser
        self.caller.player.user.save()
        return
