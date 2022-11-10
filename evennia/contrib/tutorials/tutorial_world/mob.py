"""
This module implements a simple mobile object with
a very rudimentary AI as well as an aggressive enemy
object based on that mobile class.

"""

import random

from evennia import TICKER_HANDLER, CmdSet, Command, logger, search_object

from . import objects as tut_objects


class CmdMobOnOff(Command):
    """
    Activates/deactivates Mob

    Usage:
        mobon <mob>
        moboff <mob>

    This turns the mob from active (alive) mode
    to inactive (dead) mode. It is used during
    building to  activate the mob once it's
    prepared.
    """

    key = "mobon"
    aliases = "moboff"
    locks = "cmd:superuser()"

    def func(self):
        """
        Uses the mob's set_alive/set_dead methods
        to turn on/off the mob."
        """
        if not self.args:
            self.caller.msg("Usage: mobon||moboff <mob>")
            return
        mob = self.caller.search(self.args)
        if not mob:
            return
        if self.cmdstring == "mobon":
            mob.set_alive()
        else:
            mob.set_dead()


class MobCmdSet(CmdSet):
    """
    Holds the admin command controlling the mob
    """

    def at_cmdset_creation(self):
        self.add(CmdMobOnOff())


class Mob(tut_objects.TutorialObject):
    """
    This is a state-machine AI mobile. It has several states which are
    controlled from setting various Attributes. All default to True:

        patrolling: if set, the mob will move randomly
            from room to room, but preferring to not return
            the way it came. If unset, the mob will remain
            stationary (idling) until attacked.
        aggressive: if set, will attack Characters in
            the same room using whatever Weapon it
            carries (see tutorial_world.objects.TutorialWeapon).
            if unset, the mob will never engage in combat
            no matter what.
        hunting: if set, the mob will pursue enemies trying
            to flee from it, so it can enter combat. If unset,
            it will return to patrolling/idling if fled from.
        immortal: If set, the mob cannot take any damage.
        irregular_echoes: list of strings the mob generates at irregular intervals.
        desc_alive: the physical description while alive
        desc_dead: the physical descripion while dead
        send_defeated_to: unique key/alias for location to send defeated enemies to
        defeat_msg: message to echo to defeated opponent
        defeat_msg_room: message to echo to room. Accepts %s as the name of the defeated.
        hit_msg: message to echo when this mob is hit. Accepts %s for the mob's key.
        weapon_ineffective_msg: message to echo for useless attacks
        death_msg: message to echo to room when this mob dies.
        patrolling_pace: how many seconds per tick, when patrolling
        aggressive_pace:   -"-         attacking
        hunting_pace:      -"-         hunting
        death_pace:        -"-         returning to life when dead

        field 'home' - the home location should set to someplace inside
           the patrolling area. The mob will use this if it should
           happen to roam into a room with no exits.

    """

    def at_init(self):
        """
        When initialized from cache (after a server reboot), set up
        the AI state.
        """
        # The AI state machine (not persistent).
        self.ndb.is_patrolling = self.db.patrolling and not self.db.is_dead
        self.ndb.is_attacking = False
        self.ndb.is_hunting = False
        self.ndb.is_immortal = self.db.immortal or self.db.is_dead

    def at_object_creation(self):
        """
        Called the first time the object is created.
        We set up the base properties and flags here.
        """
        self.cmdset.add(MobCmdSet, persistent=True)
        # Main AI flags. We start in dead mode so we don't have to
        # chase the mob around when building.
        self.db.patrolling = True
        self.db.aggressive = True
        self.db.immortal = False
        # db-store if it is dead or not
        self.db.is_dead = True
        # specifies how much damage we divide away from non-magic weapons
        self.db.damage_resistance = 100.0
        # pace (number of seconds between ticks) for
        # the respective modes.
        self.db.patrolling_pace = 6
        self.db.aggressive_pace = 2
        self.db.hunting_pace = 1
        self.db.death_pace = 100  # stay dead for 100 seconds

        # we store the call to the tickerhandler
        # so we can easily deactivate the last
        # ticker subscription when we switch.
        # since we will use the same idstring
        # throughout we only need to save the
        # previous interval we used.
        self.db.last_ticker_interval = None

        # store two separate descriptions, one for alive and
        # one for dead (corpse)
        self.db.desc_alive = "This is a moving object."
        self.db.desc_dead = "A dead body."

        # health stats
        self.db.full_health = 20
        self.db.health = 20

        # when this mob defeats someone, we move the character off to
        # some other place (Dark Cell in the tutorial).
        self.db.send_defeated_to = "dark cell"
        # text to echo to the defeated foe.
        self.db.defeat_msg = "You fall to the ground."
        self.db.defeat_msg_room = "%s falls to the ground."
        self.db.weapon_ineffective_msg = (
            "Your weapon just passes through your enemy, causing almost no effect!"
        )

        self.db.death_msg = "After the last hit %s evaporates." % self.key
        self.db.hit_msg = "%s wails, shudders and writhes." % self.key
        self.db.irregular_msgs = ["the enemy looks about.", "the enemy changes stance."]

        self.db.tutorial_info = "This is an object with simple state AI, using a ticker to move."

    def _set_ticker(self, interval, hook_key, stop=False):
        """
        Set how often the given hook key should
        be "ticked".

        Args:
            interval (int or None): The number of seconds
                between ticks
            hook_key (str or None): The name of the method
                (on this mob) to call every interval
                seconds.
            stop (bool, optional): Just stop the
                last ticker without starting a new one.
                With this set, the interval and hook_key
                arguments are unused.

        In order to only have one ticker
        running at a time, we make sure to store the
        previous ticker subscription so that we can
        easily find and stop it before setting a
        new one. The tickerhandler is persistent so
        we need to remember this across reloads.

        """
        idstring = "tutorial_mob"  # this doesn't change
        last_interval = self.db.last_ticker_interval
        last_hook_key = self.db.last_hook_key
        if last_interval and last_hook_key:
            # we have a previous subscription, kill this first.
            TICKER_HANDLER.remove(
                interval=last_interval, callback=getattr(self, last_hook_key), idstring=idstring
            )
        self.db.last_ticker_interval = interval
        self.db.last_hook_key = hook_key
        if not stop:
            # set the new ticker
            TICKER_HANDLER.add(
                interval=interval, callback=getattr(self, hook_key), idstring=idstring
            )

    def _find_target(self, location):
        """
        Scan the given location for suitable targets (this is defined
        as Characters) to attack.  Will ignore superusers.

        Args:
            location (Object): the room to scan.

        Returns:
            The first suitable target found.

        """
        targets = [
            obj
            for obj in location.contents_get(exclude=self)
            if obj.has_account and not obj.is_superuser
        ]
        return targets[0] if targets else None

    def set_alive(self, *args, **kwargs):
        """
        Set the mob to "alive" mode. This effectively
        resurrects it from the dead state.
        """
        self.db.health = self.db.full_health
        self.db.is_dead = False
        self.db.desc = self.db.desc_alive
        self.ndb.is_immortal = self.db.immortal
        self.ndb.is_patrolling = self.db.patrolling
        if not self.location:
            self.move_to(self.home)
        if self.db.patrolling:
            self.start_patrolling()

    def set_dead(self):
        """
        Set the mob to "dead" mode. This turns it off
        and makes sure it can take no more damage.
        It also starts a ticker for when it will return.
        """
        self.db.is_dead = True
        self.location = None
        self.ndb.is_patrolling = False
        self.ndb.is_attacking = False
        self.ndb.is_hunting = False
        self.ndb.is_immortal = True
        # we shall return after some time
        self._set_ticker(self.db.death_pace, "set_alive")

    def start_idle(self):
        """
        Starts just standing around. This will kill
        the ticker and do nothing more.
        """
        self._set_ticker(None, None, stop=True)

    def start_patrolling(self):
        """
        Start the patrolling state by
        registering us with the ticker-handler
        at a leasurely pace.
        """
        if not self.db.patrolling:
            self.start_idle()
            return
        self._set_ticker(self.db.patrolling_pace, "do_patrol")
        self.ndb.is_patrolling = True
        self.ndb.is_hunting = False
        self.ndb.is_attacking = False
        # for the tutorial, we also heal the mob in this mode
        self.db.health = self.db.full_health

    def start_hunting(self):
        """
        Start the hunting state
        """
        if not self.db.hunting:
            self.start_patrolling()
            return
        self._set_ticker(self.db.hunting_pace, "do_hunt")
        self.ndb.is_patrolling = False
        self.ndb.is_hunting = True
        self.ndb.is_attacking = False

    def start_attacking(self):
        """
        Start the attacking state
        """
        if not self.db.aggressive:
            self.start_hunting()
            return
        self._set_ticker(self.db.aggressive_pace, "do_attack")
        self.ndb.is_patrolling = False
        self.ndb.is_hunting = False
        self.ndb.is_attacking = True

    def do_patrol(self, *args, **kwargs):
        """
        Called repeatedly during patrolling mode.  In this mode, the
        mob scans its surroundings and randomly chooses a viable exit.
        One should lock exits with the traverse:has_account() lock in
        order to block the mob from moving outside its area while
        allowing account-controlled characters to move normally.
        """
        if random.random() < 0.01 and self.db.irregular_msgs:
            self.location.msg_contents(random.choice(self.db.irregular_msgs))
        if self.db.aggressive:
            # first check if there are any targets in the room.
            target = self._find_target(self.location)
            if target:
                self.start_attacking()
                return
        # no target found, look for an exit.
        exits = [exi for exi in self.location.exits if exi.access(self, "traverse")]
        if exits:
            # randomly pick an exit
            exit = random.choice(exits)
            # move there.
            self.move_to(exit.destination)
        else:
            # no exits! teleport to home to get away.
            self.move_to(self.home)

    def do_hunting(self, *args, **kwargs):
        """
        Called regularly when in hunting mode. In hunting mode the mob
        scans adjacent rooms for enemies and moves towards them to
        attack if possible.
        """
        if random.random() < 0.01 and self.db.irregular_msgs:
            self.location.msg_contents(random.choice(self.db.irregular_msgs))
        if self.db.aggressive:
            # first check if there are any targets in the room.
            target = self._find_target(self.location)
            if target:
                self.start_attacking()
                return
        # no targets found, scan surrounding rooms
        exits = [exi for exi in self.location.exits if exi.access(self, "traverse")]
        if exits:
            # scan the exits destination for targets
            for exit in exits:
                target = self._find_target(exit.destination)
                if target:
                    # a target found. Move there.
                    self.move_to(exit.destination)
                    return
            # if we get to this point we lost our
            # prey. Resume patrolling.
            self.start_patrolling()
        else:
            # no exits! teleport to home to get away.
            self.move_to(self.home)

    def do_attack(self, *args, **kwargs):
        """
        Called regularly when in attacking mode. In attacking mode
        the mob will bring its weapons to bear on any targets
        in the room.
        """
        if random.random() < 0.01 and self.db.irregular_msgs:
            self.location.msg_contents(random.choice(self.db.irregular_msgs))
        # first make sure we have a target
        target = self._find_target(self.location)
        if not target:
            # no target, start looking for one
            self.start_hunting()
            return

        # we use the same attack commands as defined in
        # tutorial_world.objects.TutorialWeapon, assuming that
        # the mob is given a Weapon to attack with.
        attack_cmd = random.choice(("thrust", "pierce", "stab", "slash", "chop"))
        self.execute_cmd("%s %s" % (attack_cmd, target))

        # analyze the current state
        if target.db.health <= 0:
            # we reduced the target to <= 0 health. Move them to the
            # defeated room
            target.msg(self.db.defeat_msg)
            self.location.msg_contents(self.db.defeat_msg_room % target.key, exclude=target)
            send_defeated_to = search_object(self.db.send_defeated_to)
            if send_defeated_to:
                target.move_to(send_defeated_to[0], quiet=True)
            else:
                logger.log_err(
                    "Mob: mob.db.send_defeated_to not found: %s" % self.db.send_defeated_to
                )

    # response methods - called by other objects

    def at_hit(self, weapon, attacker, damage):
        """
        Someone landed a hit on us. Check our status
        and start attacking if not already doing so.
        """
        if self.db.health is None:
            # health not set - this can't be damaged.
            attacker.msg(self.db.weapon_ineffective_msg)
            return

        if not self.ndb.is_immortal:
            if not weapon.db.magic:
                # not a magic weapon - divide away magic resistance
                damage /= self.db.damage_resistance
                attacker.msg(self.db.weapon_ineffective_msg)
            else:
                self.location.msg_contents(self.db.hit_msg)
            self.db.health -= damage

        # analyze the result
        if self.db.health <= 0:
            # we are dead!
            attacker.msg(self.db.death_msg)
            self.set_dead()
        else:
            # still alive, start attack if not already attacking
            if self.db.aggressive and not self.ndb.is_attacking:
                self.start_attacking()

    def at_new_arrival(self, new_character):
        """
        This is triggered whenever a new character enters the room.
        This is called by the TutorialRoom the mob stands in and
        allows it to be aware of changes immediately without needing
        to poll for them all the time. For example, the mob can react
        right away, also when patrolling on a very slow ticker.
        """
        # the room actually already checked all we need, so
        # we know it is a valid target.
        if self.db.aggressive and not self.ndb.is_attacking:
            self.start_attacking()
