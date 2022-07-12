"""
nextEvAdventure commands and cmdsets.

"""

from evennia import Command, default_cmds

from .combat_turnbased import CombatFailure, join_combat


class EvAdventureCommand(Command):
    """
    Base EvAdventure command. This is on the form

        command <args>

    where whitespace around the argument(s) are stripped.

    """

    def parse(self):
        self.args = self.args.strip()


class CmdAttackTurnBased(EvAdventureCommand):
    """
    Attack a target or join an existing combat.

    Usage:
      attack <target>
      attack <target>, <target>, ...

    If the target is involved in combat already, you'll join combat with
    the first target you specify. Attacking multiple will draw them all into
    combat.

    This will start/join turn-based, combat, where you have a limited
    time to decide on your next action from a menu of options.

    """

    key = "attack"
    aliases = ("hit",)

    def parse(self):
        super().parse()
        self.targets = [name.strip() for name in self.args.split(",")]

    def func(self):

        # find if

        target_objs = []
        for target in self.targets:
            target_obj = self.caller.search(target)
            if not target_obj:
                # show a warning but don't abort
                continue
            target_objs.append(target_obj)

        if target_objs:
            try:
                join_combat(self.caller, *target_objs, session=self.session)
            except CombatFailure as err:
                self.caller.msg(f"|r{err}|n")
        else:
            self.caller.msg("|rFound noone to attack.|n")
