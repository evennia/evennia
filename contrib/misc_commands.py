"""
Evennia misc commands 

Contribution - Griatch 2011

This module offers some miscellaneous commands that may be useful
depending on the game you run or the style of administration you
prefer. Alternatively they can be looked at for inspiration.

To make available in the game, import this module to 
game.gamesrc.commands.basecmdset.py (or your own equivalent) and add
the command class(es) you want to the default command set. You need to 
reload the server to make them recognized. 
"""

from django.conf import settings 
from src.commands.default.muxcommand import MuxCommand 

PERMISSION_HIERARCHY = settings.PERMISSION_HIERARCHY
PERMISSION_HIERARCHY_LOWER = [perm.lower() for perm in PERMISSION_HIERARCHY]

class CmdQuell(MuxCommand):
    """
    Quelling permissions

    Usage: 
      quell <command> [=permission level] 

    This is an admin command that allows to execute another command as
    another (lower) permission level than what you currently
    have. This is useful for testing. Also superuser flag will be
    deactivated by this command. If no permission level is given,
    the command will be executed as the lowest level available in
    settings.PERMISSION_HIERARCHY.       
    """

    key = "quell"
    locks = "cmd:perm(all)"
    help_category = "General"

    def func(self):
        "Perform the command"

        if not self.args:
            self.caller.msg("Usage: quell <command> [=permission level]")
            return 

        cmd = self.lhs
        perm = self.rhs
        
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

        try:
            ret = self.caller.execute_cmd(cmd)
        except Exception, e:
            self.caller.msg(str(e))
            
        self.caller.permissions = oldperm
        self.caller.player.user.is_superuser = old_superuser 
        self.caller.player.user.save() 
        return ret
