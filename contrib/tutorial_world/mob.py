"""
This module implements a simple mobile object with
a very rudimentary AI as well as an aggressive enemy
object based on that mobile class.

"""

import random, time
from django.conf import settings

from ev import search_object, utils, Script
from contrib.tutorial_world import objects as tut_objects
from contrib.tutorial_world import scripts as tut_scripts

BASE_CHARACTER_TYPECLASS = settings.BASE_CHARACTER_TYPECLASS

#------------------------------------------------------------
#
# Mob - mobile object
#
# This object utilizes exits and moves about randomly from
# room to room.
#
#------------------------------------------------------------

class Mob(tut_objects.TutorialObject):
    """
    This type of mobile will roam from exit to exit at
    random intervals. Simply lock exits against the is_mob attribute
    to block them from the mob (lockstring = "traverse:not attr(is_mob)").
    """
    def at_object_creation(self):
        "This is called when the object is first created."
        self.db.tutorial_info = "This is a moving object. It moves randomly from room to room."

        self.scripts.add(tut_scripts.IrregularEvent)
        # this is a good attribute for exits to look for, to block
        # a mob from entering certain exits.
        self.db.is_mob = True
        self.db.last_location = None
        # only when True will the mob move.
        self.db.roam_mode = True

    def announce_move_from(self, destination):
        "Called just before moving"
        self.location.msg_contents("With a cold breeze, %s drifts in the direction of %s." % (self.key, destination.key))

    def announce_move_to(self, source_location):
        "Called just after arriving"
        self.location.msg_contents("With a wailing sound, %s appears from the %s." % (self.key, source_location.key))

    def update_irregular(self):
        "Called at irregular intervals. Moves the mob."
        if self.roam_mode:
            exits = [ex for ex in self.location.exits if ex.access(self, "traverse")]
            if exits:
                # Try to make it so the mob doesn't backtrack.
                new_exits = [ex for ex in exits if ex.destination != self.db.last_location]
                if new_exits:
                    exits = new_exits
                self.db.last_location = self.location
                # execute_cmd() allows the mob to respect exit and exit-command locks,
                # but may pose a problem if there is more than one exit with the same name.
                # - see Enemy example for another way to move
                self.execute_cmd("%s" % exits[random.randint(0, len(exits) - 1)].key)


#------------------------------------------------------------
#
# Enemy - mobile attacking object
#
# An enemy is a mobile that is aggressive against players
# in its vicinity. An enemy will try to attack characters
# in the same location. It will also pursue enemies through
# exits if possible.
#
# An enemy needs to have a Weapon object in order to
# attack.
#
# This particular tutorial enemy is a ghostly apparition that can only
# be hurt by magical weapons. It will also not truly "die", but only
# teleport to another room. Players defeated by the apparition will
# conversely just be teleported to a holding room.
#
#------------------------------------------------------------

class AttackTimer(Script):
    """
    This script is what makes an eneny "tick".
    """
    def at_script_creation(self):
        "This sets up the script"
        self.key = "AttackTimer"
        self.desc = "Drives an Enemy's combat."
        self.interval = random.randint(2, 3) # how fast the Enemy acts
        self.start_delay = True # wait self.interval before first call
        self.persistent = True

    def at_repeat(self):
        "Called every self.interval seconds."
        if self.obj.db.inactive:
            return
        #print "attack timer: at_repeat", self.dbobj.id, self.ndb.twisted_task, id(self.ndb.twisted_task)
        if self.obj.db.roam_mode:
            self.obj.roam()
            #return
        elif self.obj.db.battle_mode:
            #print "attack"
            self.obj.attack()
            return
        elif self.obj.db.pursue_mode:
            #print "pursue"
            self.obj.pursue()
            #return
        else:
            #dead mode. Wait for respawn.
            if not self.obj.db.dead_at:
                self.obj.db.dead_at = time.time()
            if (time.time() - self.obj.db.dead_at) > self.obj.db.dead_timer:
                self.obj.reset()

class Enemy(Mob):
    """
    This is a ghostly enemy with health (hit points). Their chance to hit, damage etc is
    determined by the weapon they are wielding, same as characters.

    An enemy can be in four modes:
       roam (inherited from Mob) - where it just moves around randomly
       battle - where it stands in one place and attacks players
       pursue - where it follows a player, trying to enter combat again
       dead - passive and invisible until it is respawned

    Upon creation, the following attributes describe the enemy's actions
      desc - description
      full_health - integer number > 0
      defeat_location - unique name or #dbref to the location the player is taken when defeated. If not given, will remain in room.
      defeat_text - text to show player when they are defeated (just before being whisped away to defeat_location)
      defeat_text_room - text to show other players in room when a player is defeated
      win_text - text to show player when defeating the enemy
      win_text_room - text to show room when a player defeates the enemy
      respawn_text - text to echo to room when the mob is reset/respawn in that room.

    """
    def at_object_creation(self):
        "Called at object creation."
        super(Enemy, self).at_object_creation()

        self.db.tutorial_info = "This moving object will attack players in the same room."

        # state machine modes
        self.db.roam_mode = True
        self.db.battle_mode = False
        self.db.pursue_mode = False
        self.db.dead_mode = False
        # health (change this at creation time)
        self.db.full_health = 20
        self.db.health = 20
        self.db.dead_at = time.time()
        self.db.dead_timer = 100 # how long to stay dead
        self.db.inactive = True # this is used during creation to make sure the mob doesn't move away
        # store the last player to hit
        self.db.last_attacker = None
        # where to take defeated enemies
        self.db.defeat_location = "darkcell"
        self.scripts.add(AttackTimer)

    def update_irregular(self):
        "the irregular event is inherited from Mob class"
        strings = self.db.irregular_echoes
        if strings:
            self.location.msg_contents(strings[random.randint(0, len(strings) - 1)])

    def roam(self):
        "Called by Attack timer. Will move randomly as long as exits are open."

        # in this mode, the mob is healed.
        self.db.health = self.db.full_health
        players = [obj for obj in self.location.contents
                   if utils.inherits_from(obj, BASE_CHARACTER_TYPECLASS) and not obj.is_superuser]
        if players:
            # we found players in the room. Attack.
            self.db.roam_mode = False
            self.db.pursue_mode = False
            self.db.battle_mode = True

        elif random.random() < 0.2:
            # no players to attack, move about randomly.
            exits = [ex.destination for ex in self.location.exits if ex.access(self, "traverse")]
            if exits:
                # Try to make it so the mob doesn't backtrack.
                new_exits = [ex for ex in exits if ex.destination != self.db.last_location]
                if new_exits:
                    exits = new_exits
                self.db.last_location = self.location
                # locks should be checked here
                self.move_to(exits[random.randint(0, len(exits) - 1)])
            else:
                # no exits - a dead end room. Respawn back to start.
                self.move_to(self.home)

    def attack(self):
        """
        This is the main mode of combat. It will try to hit players in
        the location. If players are defeated, it will whisp them off
        to the defeat location.
        """
        last_attacker = self.db.last_attacker
        players = [obj for obj in self.location.contents
                   if utils.inherits_from(obj, BASE_CHARACTER_TYPECLASS) and not obj.is_superuser]
        if players:

            # find a target
            if last_attacker in players:
                # prefer to attack the player last attacking.
                target = last_attacker
            else:
                # otherwise attack a random player in location
                target = players[random.randint(0, len(players) - 1)]

            # try to use the weapon in hand
            attack_cmds = ("thrust", "pierce", "stab", "slash", "chop")
            cmd = attack_cmds[random.randint(0, len(attack_cmds) - 1)]
            self.execute_cmd("%s %s" % (cmd, target))

            # analyze result.
            if target.db.health <= 0:
                # we reduced enemy to 0 health. Whisp them off to the prison room.
                tloc = search_object(self.db.defeat_location)
                tstring = self.db.defeat_text
                if not tstring:
                    tstring = "You feel your conciousness slip away ... you fall to the ground as "
                    tstring += "the misty apparition envelopes you ...\n The world goes black ...\n"
                target.msg(tstring)
                ostring = self.db.defeat_text_room
                if tloc:
                    if not ostring:
                        ostring = "\n%s envelops the fallen ... and then their body is suddenly gone!" % self.key
                        # silently move the player to defeat location (we need to call hook manually)
                    target.location = tloc[0]
                    tloc[0].at_object_receive(target, self.location)
                elif not ostring:
                    ostring = "%s falls to the ground!" % target.key
                self.location.msg_contents(ostring, exclude=[target])
        else:
            # no players found, this could mean they have fled. Switch to pursue mode.
            self.battle_mode = False
            self.roam_mode = False
            self.pursue_mode = True

    def pursue(self):
        """
        In pursue mode, the enemy tries to find players in adjoining rooms, preferably
        those that previously attacked it.
        """
        last_attacker = self.db.last_attacker
        players = [obj for obj in self.location.contents if utils.inherits_from(obj, BASE_CHARACTER_TYPECLASS) and not obj.is_superuser]
        if players:
            # we found players in the room. Maybe we caught up with some, or some walked in on us
            # before we had time to pursue them. Switch to battle mode.
            self.battle_mode = True
            self.roam_mode = False
            self.pursue_mode = False
        else:
            # find all possible destinations.
            destinations = [ex.destination for ex in self.location.exits if ex.access(self, "traverse")]
            # find all players in the possible destinations. OBS-we cannot just use the player's
            # current position to move the Enemy; this might have changed when the move is performed,
            # causing the enemy to teleport out of bounds.
            players = {}
            for dest in destinations:
                for obj in [o for o in dest.contents if utils.inherits_from(o, BASE_CHARACTER_TYPECLASS)]:
                    players[obj] = dest
            if players:
                # we found targets. Move to intercept.
                if last_attacker in players:
                    # preferably the one that last attacked us
                    self.move_to(players[last_attacker])
                else:
                    # otherwise randomly.
                    key = players.keys()[random.randint(0, len(players) - 1)]
                    self.move_to(players[key])
            else:
                # we found no players nearby. Return to roam mode.
                self.battle_mode = False
                self.roam_mode = True
                self.pursue_mode = False

    def at_hit(self, weapon, attacker, damage):
        """
        Called when this object is hit by an enemy's weapon
        Should return True if enemy is defeated, False otherwise.

        In the case of players attacking, we handle all the events
        and information from here, so the return value is not used.
        """

        self.db.last_attacker = attacker
        if not self.db.battle_mode:
            # we were attacked, so switch to battle mode.
            self.db.roam_mode = False
            self.db.pursue_mode = False
            self.db.battle_mode = True
            #self.scripts.add(AttackTimer)

        if not weapon.db.magic:
            # In the tutorial, the enemy is a ghostly apparition, so
            # only magical weapons can harm it.
            string = self.db.weapon_ineffective_text
            if not string:
                string = "Your weapon just passes through your enemy, causing no effect!"
            attacker.msg(string)
            return
        else:
            # an actual hit
            health = float(self.db.health)
            health -= damage
            self.db.health = health
            if health <= 0:
                string = self.db.win_text
                if not string:
                    string = "After your last hit, %s folds in on itself, it seems to fade away into nothingness. " % self.key
                    string += "In a moment there is nothing left but the echoes of its screams. But you have a "
                    string += "feeling it is only temporarily weakened. "
                    string += "You fear it's only a matter of time before it materializes somewhere again."
                attacker.msg(string)
                string = self.db.win_text_room
                if not string:
                    string = "After %s's last hit, %s folds in on itself, it seems to fade away into nothingness. " % (attacker.name, self.key)
                    string += "In a moment there is nothing left but the echoes of its screams. But you have a "
                    string += "feeling it is only temporarily weakened. "
                    string += "You fear it's only a matter of time before it materializes somewhere again."
                self.location.msg_contents(string, exclude=[attacker])

                # put enemy in dead mode and hide it from view. AttackTimer will bring it back later.
                self.db.dead_at = time.time()
                self.db.roam_mode = False
                self.db.pursue_mode = False
                self.db.battle_mode = False
                self.db.dead_mode = True
                self.location = None
            else:
                self.location.msg_contents("%s wails, shudders and writhes." % self.key)
        return False

    def reset(self):
        "If the mob was 'dead', respawn it to its home position and reset all modes and damage."
        if self.db.dead_mode:
            self.db.health = self.db.full_health
            self.db.roam_mode = True
            self.db.pursue_mode = False
            self.db.battle_mode = False
            self.db.dead_mode = False
            self.location = self.home
            string = self.db.respawn_text
            if not string:
                string = "%s fades into existence from out of thin air. It's looking pissed." % self.key
                self.location.msg_contents(string)
