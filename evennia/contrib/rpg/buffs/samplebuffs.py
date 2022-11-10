import random

from .buff import BaseBuff, Mod


class Exploit(BaseBuff):
    key = "exploit"
    name = "Exploit"
    flavor = "You are learning your opponent's weaknesses."

    duration = -1
    maxstacks = 20

    triggers = ["hit"]

    stack_msg = {
        1: "You begin to notice flaws in your opponent's defense.",
        10: "You've begun to match the battle's rhythm.",
        20: "You've found a gap in the guard!",
    }

    def conditional(self, *args, **kwargs):
        if self.handler.get_by_type(Exploited):
            return False
        return True

    def at_trigger(self, trigger: str, *args, **kwargs):
        chance = self.stacks / 20
        roll = random.random()

        if chance > roll:
            self.handler.add(Exploited)
            self.owner.msg("An opportunity presents itself!")
        elif chance < roll:
            self.handler.add(Exploit)

        if self.stacks in self.stack_msg:
            self.owner.msg(self.stack_msg[self.stacks])


class Exploited(BaseBuff):
    key = "exploited"
    name = "Exploited"
    flavor = "You have sensed your target's vulnerability, and are poised to strike."

    duration = 30

    mods = [Mod("damage", "add", 100)]

    def at_post_check(self, *args, **kwargs):
        self.owner.msg("You ruthlessly exploit your target's weakness!")
        self.remove(quiet=True)

    def at_remove(self, *args, **kwargs):
        self.owner.msg("You have waited too long; the opportunity passes.")


class Leeching(BaseBuff):
    key = "leeching"
    name = "Leeching"
    flavor = "Attacking this target fills you with vigor."

    duration = 30

    triggers = ["taken_damage"]

    def at_trigger(self, trigger: str, attacker=None, damage=None, *args, **kwargs):
        if not attacker or not damage:
            return
        attacker.msg("You have been healed for {heal} life!".format(heal=damage * 0.1))


class Poison(BaseBuff):
    key = "poison"
    name = "Poison"
    flavor = "A poison wracks this body with painful spasms."

    duration = 120

    maxstacks = 5
    tickrate = 5
    dmg = 5

    playtime = True

    def at_pause(self, *args, **kwargs):
        self.owner.db.prelogout_location.msg_contents(
            "{actor} stops twitching, their flesh a deathly pallor.".format(actor=self.owner)
        )

    def at_unpause(self, *args, **kwargs):
        self.owner.location.msg_contents(
            "{actor} begins to twitch again, their cheeks flushing red with blood.".format(
                actor=self.owner
            )
        )

    def at_tick(self, initial=True, *args, **kwargs):
        _dmg = self.dmg * self.stacks
        if not initial:
            self.owner.location.msg_contents(
                "Poison courses through {actor}'s body, dealing {damage} damage.".format(
                    actor=self.owner, damage=_dmg
                )
            )


class Sated(BaseBuff):
    key = "sated"
    name = "Sated"
    flavor = "You have eaten a great meal!"

    duration = 180
    maxstacks = 3

    mods = [Mod("mood", "add", 15)]


class StatBuff(BaseBuff):
    """Customize the stat this buff affects by feeding a list in the order [stat, mod, base, perstack] to the cache argument when added"""

    key = "statbuff"
    name = "statbuff"
    flavor = "This buff affects the following stats: {stats}"

    maxstacks = 0
    refresh = True
    unique = False

    cache = {"modgen": ["foo", "add", 0, 0]}

    def __init__(self, handler, buffkey, cache={}) -> None:
        super().__init__(handler, buffkey, cache)
        # Finds our "modgen" cache value, which we pass on application
        modgen = list(self.cache.get("modgen"))
        if modgen:
            self.mods = [Mod(*modgen)]
        msg = ""
        _msg = [mod.stat for mod in self.mods]
        for stat in _msg:
            msg += stat
        self.flavor = self.flavor.format(stats=msg)
