"""
This module implements a simple mobile object with
a very rudimentary AI as well as an aggressive enemy
object based on that mobile class.

"""

import random

from evennia import TICKER_HANDLER
from evennia import search_object
from evennia.contrib.tutorial_world import objects as tut_objects


class Mob(tut_objects.TutorialObject):
    """
    This is a state-machine AI mobile. It has several states which
    are controlled from setting various Attributes:

        patrolling: if set, the mob will move randomly
            from room to room, but preferring to not return
            the way it came. If unset, the mob will remain
            stationary (idling) until attacked.
        aggressive: if set, will attack Characters in
            the same room using whatever Weapon it
            carries (see tutorial_world.objects.Weapon).
            if unset, the mob will never engage in combat
            no matter what.
        hunting: if set, the mob will pursue enemies trying
            to flee from it, so it can enter combat. If unset,
            it will return to patrolling/idling if fled from.
        immortal: If set, the mob cannot take any damage.
    It also has several states,
        is_patrolling - set when the mob is patrolling.
        is_attacking - set when the mob is in combat
        is_hunting - set when the mob is pursuing an enemy.
        is_immortal - is currently immortal
        is_dead: if set, the Mob is set to immortal, non-patrolling
                   and non-aggressive mode. Its description is
                   turned into that of a corpse-description.
    Other important properties:
        home - the home location should set to someplace inside
        the patrolling area. The mob will use this if it should
        happen to roam into a room with no exits.

    """
    def __init__(self):
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
        # Main AI flags. We start in dead mode so we don't have to
        # chase the mob around when building.
        self.db.patrolling = False
        self.db.aggressive = False
        self.db.immortal = True
        # db-store if it is dead or not
        self.db.is_dead = True
        # specifies how much damage we remove from non-magic weapons
        self.db.magic_resistance = 0.01
        # pace (number of seconds between ticks) for
        # the respective modes.
        self.db.patrolling_pace = 6
        self.db.aggressive_pace = 2
        self.db.hunting_pace = 1

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
        self.db.weapon_ineffective_text = "Your weapon just passes through your enemy, causing almost no effect!"

        self.db.death_msg = "After the last hit %s evaporates." % self.key
        self.db.hit_msg = "%s wails, shudders and writhes." % self.key

        self.db.tutorial_info = "This is an object with simple state AI, using a ticker to move."

    def _set_ticker(self, interval, hook_key, stop=False):
        """
        Set how often the given hook key should
        be "ticked".

        Args:
            interval (int): The number of seconds
                between ticks
            hook_key (str): The name of the method
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
        we need to remmeber this across reloads.

        """
        idstring = "tutorial_mob" # this doesn't change
        last_interval = self.db.last_ticker_interval
        if last_interval:
             # we have a previous subscription, kill this first.
            TICKER_HANDLER.remove(self, last_interval, idstring)
        if not stop:
            # set the new ticker
            TICKER_HANDLER.add(self, interval, idstring, hook_key)

    def _find_target(self, location):
        """
        Scan the given location for suitable targets (this is defined
        as Characters) to attack.  Will ignore superusers.

        Args:
            location (Object): the room to scan.

        Returns:
            The first suitable target found.

        """
        targets = [obj for obj in location.contents_get(exclude=self)
                    if obj.has_player and not obj.is_superuser]
        return targets[0] if targets else None

    def set_alive(self):
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
        """
        self.db.is_dead = True
        self.location = None
        self.ndb.is_patrolling = False
        self.ndb.is_attacking = False
        self.ndb.is_hunting = False
        self.ndb.is_immortal = True

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
        self._set_ticker(self.db.attacking_pace, "do_attack")
        self.ndb.is_patrolling = False
        self.ndb.is_hunting = False
        self.ndb.is_attacking = True

    def do_patrol(self):
        """
        Called repeatedly during patrolling mode.  In this mode, the
        mob scans its surroundings and randomly chooses a viable exit.
        One should lock exits with the traverse:has_player() lock in
        order to block the mob from moving outside its area while
        allowing player-controlled characters to move normally.
        """
        if self.db.aggressive:
            # first check if there are any targets in the room.
            target = self._find_target(self.location)
            if target:
                self.start_attacking()
                return
        # no target found, look for an exit.
        exits = self.location.exits
        last_location = self.ndb.last_location
        if exits:
            # randomly pick an exit
            exit = random.choice(self.location.exits)
            if len(exits) > 1 and exit.destination == last_location:
                # don't go back the same way we came if we
                # can avoid it.
                return
            # check if we may actually exit this way,
            # otherwise wait for next tick to try again.
            if exit.access(self, "traverse"):
                self.move_to(exit.destination)
        else:
            # no exits! teleport to home to get away.
            self.move_to(self.home)

    def do_hunting(self):
        """
        Called regularly when in hunting mode. In hunting mode the mob
        scans adjacent rooms for enemies and moves towards them to
        attack if possible.
        """
        if self.db.aggressive:
            # first check if there are any targets in the room.
            target = self._find_target(self.location)
            if target:
                self.start_attacking()
                return
        # no targets found, scan surrounding rooms
        exits = [exi for exi in self.location.exits
                 if exi.access(self, "traverse")]
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

    def do_attacking(self):
        """
        Called regularly when in attacking mode. In attacking mode
        the mob will bring its weapons to bear on any targets
        in the room.
        """
        # first make sure we have a target
        target = self._find_target(self.location)
        if not target:
            # no target, start looking for one
            self.start_hunting()
            return

        # we use the same attack commands as defined in
        # tutorial_world.objects.Weapon, assuming that
        # the mob is given a Weapon to attack with.
        attack_cmd = random.choice(("thrust", "pierce", "stab", "slash", "chop"))
        self.execute_cmd("%s %s" % (attack_cmd, target))

        # analyze the current state
        if target.db.health <= 0:
            # we reduced the target to <= 0 health. Move them to the
            # defeated room
            target.msg(self.db.defeat_msg)
            self.location.msg_contents(self.db.defeat_msg_room, exclude=target)
            defeat_location = search_object(self.db.defeat_location)
            if defeat_location:
                target.move_to(defeat_location, quiet=True)

    # response methods - called by other objects

    def at_hit(self, weapon, attacker, damage):
        """
        Someone landed a hit on us. Check our status
        and start attacking if not already doing so.
        """
        if not self.db.immortal:
            if not weapon.db.magic:
                damage = self.db.damage_resistance * damage
                attacker.msg(self.db.weapon_ineffective_text)
                self.db.health -= damage

        # analyze the result
        if self.db.health <= 0:
            # we are dead!
            attacker.msg(self.db.death_msg)
            self.set_dead()
        else:
            # still alive, start attack if not already attacking
            attacker.msg(self.db.hit_msg)
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

#
##------------------------------------------------------------
##
## Mob - mobile object
##
## This object utilizes exits and moves about randomly from
## room to room.
##
##------------------------------------------------------------
#
#class Mob(tut_objects.TutorialObject):
#    """
#    This type of mobile will roam from exit to exit at
#    random intervals. Simply lock exits against the is_mob attribute
#    to block them from the mob (lockstring = "traverse:not attr(is_mob)").
#    """
#    def at_object_creation(self):
#        "This is called when the object is first created."
#        self.db.tutorial_info = "This is a moving object. It moves randomly from room to room."
#
#        self.scripts.add(tut_scripts.IrregularEvent)
#        # this is a good attribute for exits to look for, to block
#        # a mob from entering certain exits.
#        self.db.is_mob = True
#        self.db.last_location = None
#        # only when True will the mob move.
#        self.db.roam_mode = True
#        #
#        self.db.move_from
#        self.location.msg_contents("With a cold breeze, %s drifts in the direction of %s." % (self.key, destination.key))
#
#    def announce_move_from(self, destination):
#        "Called just before moving"
#        self.location.msg_contents("With a cold breeze, %s drifts in the direction of %s." % (self.key, destination.key))
#
#    def announce_move_to(self, source_location):
#        "Called just after arriving"
#        self.location.msg_contents("With a wailing sound, %s appears from the %s." % (self.key, source_location.key))
#
#    def update_irregular(self):
#        "Called at irregular intervals. Moves the mob."
#        if self.roam_mode:
#            exits = [ex for ex in self.location.exits
#                                    if ex.access(self, "traverse")]
#            if exits:
#                # Try to make it so the mob doesn't backtrack.
#                new_exits = [ex for ex in exits
#                                     if ex.destination != self.db.last_location]
#                if new_exits:
#                    exits = new_exits
#                self.db.last_location = self.location
#                # execute_cmd() allows the mob to respect exit and
#                # exit-command locks, but may pose a problem if there is more
#                # than one exit with the same name.
#                # - see Enemy example for another way to move
#                self.execute_cmd("%s" % exits[random.randint(0, len(exits) - 1)].key)
#
#
#
##------------------------------------------------------------
##
## Enemy - mobile attacking object
##
## An enemy is a mobile that is aggressive against players
## in its vicinity. An enemy will try to attack characters
## in the same location. It will also pursue enemies through
## exits if possible.
##
## An enemy needs to have a Weapon object in order to
## attack.
##
## This particular tutorial enemy is a ghostly apparition that can only
## be hurt by magical weapons. It will also not truly "die", but only
## teleport to another room. Players defeated by the apparition will
## conversely just be teleported to a holding room.
##
##------------------------------------------------------------
#
#class AttackTimer(DefaultScript):
#    """
#    This script is what makes an eneny "tick".
#    """
#    def at_script_creation(self):
#        "This sets up the script"
#        self.key = "AttackTimer"
#        self.desc = "Drives an Enemy's combat."
#        self.interval = random.randint(2, 3) # how fast the Enemy acts
#        self.start_delay = True # wait self.interval before first call
#        self.persistent = True
#
#    def at_repeat(self):
#        "Called every self.interval seconds."
#        if self.obj.db.inactive:
#            return
#        # id(self.ndb.twisted_task)
#        if self.obj.db.roam_mode:
#            self.obj.roam()
#            #return
#        elif self.obj.db.battle_mode:
#            #print "attack"
#            self.obj.attack()
#            return
#        elif self.obj.db.pursue_mode:
#            #print "pursue"
#            self.obj.pursue()
#            #return
#        else:
#            #dead mode. Wait for respawn.
#            if not self.obj.db.dead_at:
#                self.obj.db.dead_at = time.time()
#            if (time.time() - self.obj.db.dead_at) > self.obj.db.dead_timer:
#                self.obj.reset()
#
#
#class Enemy(Mob):
#    """
#    This is a ghostly enemy with health (hit points). Their chance to hit,
#    damage etc is determined by the weapon they are wielding, same as
#    characters.
#
#    An enemy can be in four modes:
#       roam (inherited from Mob) - where it just moves around randomly
#       battle - where it stands in one place and attacks players
#       pursue - where it follows a player, trying to enter combat again
#       dead - passive and invisible until it is respawned
#
#    Upon creation, the following attributes describe the enemy's actions
#      desc - description
#      full_health - integer number > 0
#      defeat_location - unique name or #dbref to the location the player is
#                        taken when defeated. If not given, will remain in room.
#      defeat_text - text to show player when they are defeated (just before
#                    being whisped away to defeat_location)
#      defeat_text_room - text to show other players in room when a player
#                         is defeated
#      win_text - text to show player when defeating the enemy
#      win_text_room - text to show room when a player defeates the enemy
#      respawn_text - text to echo to room when the mob is reset/respawn in
#                     that room.
#
#    """
#    def at_object_creation(self):
#        "Called at object creation."
#        super(Enemy, self).at_object_creation()
#
#        self.db.tutorial_info = "This moving object will attack players in the same room."
#
#        # state machine modes
#        self.db.roam_mode = True
#        self.db.battle_mode = False
#        self.db.pursue_mode = False
#        self.db.dead_mode = False
#        # health (change this at creation time)
#        self.db.full_health = 20
#        self.db.health = 20
#        self.db.dead_at = time.time()
#        self.db.dead_timer = 100 # how long to stay dead
#        # this is used during creation to make sure the mob doesn't move away
#        self.db.inactive = True
#        # store the last player to hit
#        self.db.last_attacker = None
#        # where to take defeated enemies
#        self.db.defeat_location = "darkcell"
#        self.scripts.add(AttackTimer)
#
#    def update_irregular(self):
#        "the irregular event is inherited from Mob class"
#        strings = self.db.irregular_echoes
#        if strings:
#            self.location.msg_contents(strings[random.randint(0, len(strings) - 1)])
#
#    def roam(self):
#        "Called by Attack timer. Will move randomly as long as exits are open."
#
#        # in this mode, the mob is healed.
#        self.db.health = self.db.full_health
#        players = [obj for obj in self.location.contents
#                   if utils.inherits_from(obj, BASE_CHARACTER_TYPECLASS) and not obj.is_superuser]
#        if players:
#            # we found players in the room. Attack.
#            self.db.roam_mode = False
#            self.db.pursue_mode = False
#            self.db.battle_mode = True
#
#        elif random.random() < 0.2:
#            # no players to attack, move about randomly.
#            exits = [ex.destination for ex in self.location.exits
#                                                if ex.access(self, "traverse")]
#            if exits:
#                # Try to make it so the mob doesn't backtrack.
#                new_exits = [ex for ex in exits
#                                    if ex.destination != self.db.last_location]
#                if new_exits:
#                    exits = new_exits
#                self.db.last_location = self.location
#                # locks should be checked here
#                self.move_to(exits[random.randint(0, len(exits) - 1)])
#            else:
#                # no exits - a dead end room. Respawn back to start.
#                self.move_to(self.home)
#
#    def attack(self):
#        """
#        This is the main mode of combat. It will try to hit players in
#        the location. If players are defeated, it will whisp them off
#        to the defeat location.
#        """
#        last_attacker = self.db.last_attacker
#        players = [obj for obj in self.location.contents
#                   if utils.inherits_from(obj, BASE_CHARACTER_TYPECLASS) and not obj.is_superuser]
#        if players:
#
#            # find a target
#            if last_attacker in players:
#                # prefer to attack the player last attacking.
#                target = last_attacker
#            else:
#                # otherwise attack a random player in location
#                target = players[random.randint(0, len(players) - 1)]
#
#            # try to use the weapon in hand
#            attack_cmds = ("thrust", "pierce", "stab", "slash", "chop")
#            cmd = attack_cmds[random.randint(0, len(attack_cmds) - 1)]
#            self.execute_cmd("%s %s" % (cmd, target))
#
#            # analyze result.
#            if target.db.health <= 0:
#                # we reduced enemy to 0 health. Whisp them off to
#                # the prison room.
#                tloc = search_object(self.db.defeat_location)
#                tstring = self.db.defeat_text
#                if not tstring:
#                    tstring = "You feel your conciousness slip away ... you fall to the ground as "
#                    tstring += "the misty apparition envelopes you ...\n The world goes black ...\n"
#                target.msg(tstring)
#                ostring = self.db.defeat_text_room
#                if tloc:
#                    if not ostring:
#                        ostring = "\n%s envelops the fallen ... and then their body is suddenly gone!" % self.key
#                        # silently move the player to defeat location
#                        # (we need to call hook manually)
#                    target.location = tloc[0]
#                    tloc[0].at_object_receive(target, self.location)
#                elif not ostring:
#                    ostring = "%s falls to the ground!" % target.key
#                self.location.msg_contents(ostring, exclude=[target])
#                # Pursue any stragglers after the battle
#                self.battle_mode = False
#                self.roam_mode = False
#                self.pursue_mode = True
#        else:
#            # no players found, this could mean they have fled.
#            # Switch to pursue mode.
#            self.battle_mode = False
#            self.roam_mode = False
#            self.pursue_mode = True
#
#    def pursue(self):
#        """
#        In pursue mode, the enemy tries to find players in adjoining rooms, preferably
#        those that previously attacked it.
#        """
#        last_attacker = self.db.last_attacker
#        players = [obj for obj in self.location.contents if utils.inherits_from(obj, BASE_CHARACTER_TYPECLASS) and not obj.is_superuser]
#        if players:
#            # we found players in the room. Maybe we caught up with some,
#            # or some walked in on us before we had time to pursue them.
#            # Switch to battle mode.
#            self.battle_mode = True
#            self.roam_mode = False
#            self.pursue_mode = False
#        else:
#            # find all possible destinations.
#            destinations = [ex.destination for ex in self.location.exits
#                                                if ex.access(self, "traverse")]
#            # find all players in the possible destinations. OBS-we cannot
#            # just use the player's current position to move the Enemy; this
#            # might have changed when the move is performed, causing the enemy
#            # to teleport out of bounds.
#            players = {}
#            for dest in destinations:
#                for obj in [o for o in dest.contents
#                           if utils.inherits_from(o, BASE_CHARACTER_TYPECLASS)]:
#                    players[obj] = dest
#            if players:
#                # we found targets. Move to intercept.
#                if last_attacker in players:
#                    # preferably the one that last attacked us
#                    self.move_to(players[last_attacker])
#                else:
#                    # otherwise randomly.
#                    key = players.keys()[random.randint(0, len(players) - 1)]
#                    self.move_to(players[key])
#            else:
#                # we found no players nearby. Return to roam mode.
#                self.battle_mode = False
#                self.roam_mode = True
#                self.pursue_mode = False
#
#    def at_hit(self, weapon, attacker, damage):
#        """
#        Called when this object is hit by an enemy's weapon
#        Should return True if enemy is defeated, False otherwise.
#
#        In the case of players attacking, we handle all the events
#        and information from here, so the return value is not used.
#        """
#
#        self.db.last_attacker = attacker
#        if not self.db.battle_mode:
#            # we were attacked, so switch to battle mode.
#            self.db.roam_mode = False
#            self.db.pursue_mode = False
#            self.db.battle_mode = True
#            #self.scripts.add(AttackTimer)
#
#        if not weapon.db.magic:
#            # In the tutorial, the enemy is a ghostly apparition, so
#            # only magical weapons can harm it.
#            string = self.db.weapon_ineffective_text
#            if not string:
#                string = "Your weapon just passes through your enemy, causing no effect!"
#            attacker.msg(string)
#            return
#        else:
#            # an actual hit
#            health = float(self.db.health)
#            health -= damage
#            self.db.health = health
#            if health <= 0:
#                string = self.db.win_text
#                if not string:
#                    string = "After your last hit, %s folds in on itself, it seems to fade away into nothingness. " % self.key
#                    string += "In a moment there is nothing left but the echoes of its screams. But you have a "
#                    string += "feeling it is only temporarily weakened. "
#                    string += "You fear it's only a matter of time before it materializes somewhere again."
#                attacker.msg(string)
#                string = self.db.win_text_room
#                if not string:
#                    string = "After %s's last hit, %s folds in on itself, it seems to fade away into nothingness. " % (attacker.name, self.key)
#                    string += "In a moment there is nothing left but the echoes of its screams. But you have a "
#                    string += "feeling it is only temporarily weakened. "
#                    string += "You fear it's only a matter of time before it materializes somewhere again."
#                self.location.msg_contents(string, exclude=[attacker])
#
#                # put mob in dead mode and hide it from view.
#                # AttackTimer will bring it back later.
#                self.db.dead_at = time.time()
#                self.db.roam_mode = False
#                self.db.pursue_mode = False
#                self.db.battle_mode = False
#                self.db.dead_mode = True
#                self.location = None
#            else:
#                self.location.msg_contents("%s wails, shudders and writhes." % self.key)
#        return False
#
#    def reset(self):
#        """
#        If the mob was 'dead', respawn it to its home position and reset
#        all modes and damage."""
#        if self.db.dead_mode:
#            self.db.health = self.db.full_health
#            self.db.roam_mode = True
#            self.db.pursue_mode = False
#            self.db.battle_mode = False
#            self.db.dead_mode = False
#            self.location = self.home
#            string = self.db.respawn_text
#            if not string:
#                string = "%s fades into existence from out of thin air. It's looking pissed." % self.key
#                self.location.msg_contents(string)
