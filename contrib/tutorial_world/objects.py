"""
TutorialWorld - basic objects - Griatch 2011

This module holds all "dead" object definitions for
the tutorial world. Object-commands and -cmdsets
are also defined here, together with the object.

Objects:

TutorialObject

Readable
Climbable
Obelisk
LightSource
CrumblingWall
Weapon
WeaponRack

"""

import time, random

from ev import utils, create_object
from ev import Object, Exit, Command, CmdSet, Script

#------------------------------------------------------------
#
# TutorialObject
#
# The TutorialObject is the base class for all items
# in the tutorial. They have an attribute "tutorial_info"
# on them that a global tutorial command can use to extract
# interesting behind-the scenes information about the object.
#
# TutorialObjects may also be "reset". What the reset means
# is up to the object. It can be the resetting of the world
# itself, or the removal of an inventory item from a
# character's inventory when leaving the tutorial, for example.
#
#------------------------------------------------------------


class TutorialObject(Object):
    """
    This is the baseclass for all objects in the tutorial.
    """

    def at_object_creation(self):
        "Called when the object is first created."
        super(TutorialObject, self).at_object_creation()
        self.db.tutorial_info = "No tutorial info is available for this object."
        #self.db.last_reset = time.time()

    def reset(self):
        "Resets the object, whatever that may mean."
        self.location = self.home


#------------------------------------------------------------
#
# Readable - an object one can "read".
#
#------------------------------------------------------------

class CmdRead(Command):
    """
    Usage:
      read [obj]

    Read some text.
    """

    key = "read"
    locks = "cmd:all()"
    help_category = "TutorialWorld"

    def func(self):
        "Implement the read command."
        if self.args:
            obj = self.caller.search(self.args.strip())
        else:
            obj = self.obj
        if not obj:
            return
        # we want an attribute read_text to be defined.
        readtext = obj.db.readable_text
        if readtext:
            string = "You read {C%s{n:\n  %s" % (obj.key, readtext)
        else:
            string = "There is nothing to read on %s." % obj.key
        self.caller.msg(string)

class CmdSetReadable(CmdSet):
    "CmdSet for readables"
    def at_cmdset_creation(self):
        "called when object is created."
        self.add(CmdRead())

class Readable(TutorialObject):
    """
    This object defines some attributes and defines a read method on itself.
    """
    def at_object_creation(self):
        "Called when object is created"
        super(Readable, self).at_object_creation()
        self.db.tutorial_info = "This is an object with a 'read' command defined in a command set on itself."
        self.db.readable_text = "There is no text written on %s." % self.key
        # define a command on the object.
        self.cmdset.add_default(CmdSetReadable, permanent=True)


#------------------------------------------------------------
#
# Climbable object
#
# The climbable object works so that once climbed, it sets
# a flag on the climber to show that it was climbed. A simple
# command 'climb' handles the actual climbing.
#
#------------------------------------------------------------

class CmdClimb(Command):
    """
    Usage:
      climb <object>
    """
    key = "climb"
    locks = "cmd:all()"
    help_category = "TutorialWorld"

    def func(self):
        "Implements function"

        if not self.args:
            self.caller.msg("What do you want to climb?")
            return
        obj = self.caller.search(self.args.strip())
        if not obj:
            return
        if obj != self.obj:
            self.caller.msg("Try as you might, you cannot climb that.")
            return
        ostring = self.obj.db.climb_text
        if not ostring:
            ostring = "You climb %s. Having looked around, you climb down again." % self.obj.name
        self.caller.msg(ostring)
        self.caller.db.last_climbed = self.obj

class CmdSetClimbable(CmdSet):
    "Climbing cmdset"
    def at_cmdset_creation(self):
        "populate set"
        self.add(CmdClimb())


class Climbable(TutorialObject):
    "A climbable object."

    def at_object_creation(self):
        "Called at initial creation only"
        self.cmdset.add_default(CmdSetClimbable, permanent=True)



#------------------------------------------------------------
#
# Obelisk - a unique item
#
# The Obelisk is an object with a modified return_appearance
# method that causes it to look slightly different every
# time one looks at it. Since what you actually see
# is a part of a game puzzle, the act of looking also
# stores a key attribute on the looking object for later
# reference.
#
#------------------------------------------------------------

OBELISK_DESCS = ["You can briefly make out the image of {ba woman with a blue bird{n.",
                 "You for a moment see the visage of {ba woman on a horse{n.",
                 "For the briefest moment you make out an engraving of {ba regal woman wearing a crown{n.",
                 "You think you can see the outline of {ba flaming shield{n in the stone.",
                 "The surface for a moment seems to portray {ba woman fighting a beast{n."]

class Obelisk(TutorialObject):
    """
    This object changes its description randomly.
    """

    def at_object_creation(self):
        "Called when object is created."
        super(Obelisk, self).at_object_creation()
        self.db.tutorial_info = "This object changes its desc randomly, and makes sure to remember which one you saw."
        # make sure this can never be picked up
        self.locks.add("get:false()")

    def return_appearance(self, caller):
        "Overload the default version of this hook."
        clueindex = random.randint(0, len(OBELISK_DESCS)-1)
        # set this description
        string = "The surface of the obelisk seem to waver, shift and writhe under your gaze, with "
        string += "different scenes and structures appearing whenever you look at it. "
        self.db.desc = string + OBELISK_DESCS[clueindex]
        # remember that this was the clue we got.
        caller.db.puzzle_clue = clueindex
        # call the parent function as normal (this will use db.desc we just set)
        return super(Obelisk, self).return_appearance(caller)

#------------------------------------------------------------
#
# LightSource
#
# This object that emits light and can be
# turned on or off. It must be carried to use and has only
# a limited burn-time.
# When burned out, it will remove itself from the carrying
# character's inventory.
#
#------------------------------------------------------------

class StateLightSourceOn(Script):
    """
    This script controls how long the light source is burning. When
    it runs out of fuel, the lightsource goes out.
    """
    def at_script_creation(self):
        "Called at creation of script."
        self.key = "lightsourceBurn"
        self.desc = "Keeps lightsources burning."
        self.start_delay = True # only fire after self.interval s.
        self.repeats = 1 # only run once.
        self.persistent = True  # survive a server reboot.

    def at_start(self):
        "Called at script start - this can also happen if server is restarted."
        self.interval = self.obj.db.burntime
        self.db.script_started = time.time()

    def at_repeat(self):
        # this is only called when torch has burnt out
        self.obj.db.burntime = -1
        self.obj.reset()

    def at_stop(self):
        """
        Since the user may also turn off the light
        prematurely, this hook will store the current
        burntime.
        """
        # calculate remaining burntime, if object is not
        # already deleted (because it burned out)
        if self.obj:
            try:
                time_burnt = time.time() - self.db.script_started
            except TypeError:
                # can happen if script_started is not defined
                time_burnt = self.interval
            burntime = self.interval - time_burnt
            self.obj.db.burntime = burntime

    def is_valid(self):
        "This script is only valid as long as the lightsource burns."
        return self.obj.db.is_active

class CmdLightSourceOn(Command):
    """
    Switches on the lightsource.
    """
    key = "on"
    aliases = ["switch on", "turn on", "light"]
    locks = "cmd:holds()" # only allow if command.obj is carried by caller.
    help_category = "TutorialWorld"

    def func(self):
        "Implements the command"

        if self.obj.db.is_active:
            self.caller.msg("%s is already burning." % self.obj.key)
        else:
            # set lightsource to active
            self.obj.db.is_active = True
            # activate the script to track burn-time.
            self.obj.scripts.add(StateLightSourceOn)
            self.caller.msg("{gYou light {C%s.{n" % self.obj.key)
            self.caller.location.msg_contents("%s lights %s!" % (self.caller, self.obj.key), exclude=[self.caller])
            # we run script validation on the room to make light/dark states tick.
            self.caller.location.scripts.validate()
            # look around
            self.caller.execute_cmd("look")

class CmdLightSourceOff(Command):
    """
    Switch off the lightsource.
    """
    key = "off"
    aliases = ["switch off", "turn off", "dowse"]
    locks = "cmd:holds()" # only allow if command.obj is carried by caller.
    help_category = "TutorialWorld"

    def func(self):
        "Implements the command "

        if not self.obj.db.is_active:
            self.caller.msg("%s is not burning." % self.obj.key)
        else:
            # set lightsource to inactive
            self.obj.db.is_active = False
            # validating the scripts will kill it now that is_active=False.
            self.obj.scripts.validate()
            self.caller.msg("{GYou dowse {C%s.{n" % self.obj.key)
            self.caller.location.msg_contents("%s dowses %s." % (self.caller, self.obj.key), exclude=[self.caller])
            self.caller.location.scripts.validate()
            self.caller.execute_cmd("look")
            # we run script validation on the room to make light/dark states tick.


class CmdSetLightSource(CmdSet):
    "CmdSet for the lightsource commands"
    key = "lightsource_cmdset"
    def at_cmdset_creation(self):
        "called at cmdset creation"
        self.add(CmdLightSourceOn())
        self.add(CmdLightSourceOff())

class LightSource(TutorialObject):
    """
    This implements a light source object.

    When burned out, lightsource will be moved to its home - which by default is the
    location it was first created at.
    """
    def at_object_creation(self):
        "Called when object is first created."
        super(LightSource, self).at_object_creation()
        self.db.tutorial_info = "This object can be turned on off and has a timed script controlling it."
        self.db.is_active = False
        self.db.burntime = 60*3 # 3 minutes
        self.db.desc = "A splinter of wood with remnants of resin on it, enough for burning."
        # add commands
        self.cmdset.add_default(CmdSetLightSource, permanent=True)

    def reset(self):
        """
        Can be called by tutorial world runner, or by the script when the lightsource
        has burned out.
        """
        if self.db.burntime <= 0:
            # light burned out. Since the lightsources's "location" should be
            # a character, notify them this way.
            try:
                loc = self.location.location
            except AttributeError:
                loc = self.location
            loc.msg_contents("{c%s{n {Rburns out.{n" % self.key)
        self.db.is_active = False
        try:
            # validate in holders current room, if possible
            self.location.location.scripts.validate()
        except AttributeError:
            # maybe it was dropped, try validating at current location.
            try:
                self.location.scripts.validate()
            except AttributeError,e:
                pass
        self.delete()

#------------------------------------------------------------
#
# Crumbling wall - unique exit
#
# This implements a simple puzzle exit that needs to be
# accessed with commands before one can get to traverse it.
#
# The puzzle is currently simply to move roots (that have
# presumably covered the wall) aside until a button for a
# secret door is revealed. The original position of the
# roots blocks the button, so they have to be moved to a certain
# position - when they have, the "press button" command
# is made available and the Exit is made traversable.
#
#------------------------------------------------------------

# There are four roots - two horizontal and two vertically
# running roots. Each can have three positions: top/middle/bottom
# and left/middle/right respectively. There can be any number of
# roots hanging through the middle position, but only one each
# along the sides. The goal is to make the center position clear.
# (yes, it's really as simple as it sounds, just move the roots
# to each side to "win". This is just a tutorial, remember?)

class CmdShiftRoot(Command):
    """
    Shifts roots around.

    shift blue root left/right
    shift red root left/right
    shift yellow root up/down
    shift green root up/down

    """
    key = "shift"
    aliases = ["move"]
    # the locattr() lock looks for the attribute is_dark on the current room.
    locks = "cmd:not locattr(is_dark)"
    help_category = "TutorialWorld"

    def parse(self):
        "custom parser; split input by spaces"
        self.arglist = self.args.strip().split()

    def func(self):
        """
        Implement the command.
          blue/red - vertical roots
          yellow/green - horizontal roots
        """

        if not self.arglist:
            self.caller.msg("What do you want to move, and in what direction?")
            return
        if "root" in self.arglist:
            self.arglist.remove("root")
        # we accept arguments on the form <color> <direction>
        if not len(self.arglist) > 1:
            self.caller.msg("You must define which colour of root you want to move, and in which direction.")
            return
        color = self.arglist[0].lower()
        direction = self.arglist[1].lower()
        # get current root positions dict
        root_pos = self.obj.db.root_pos

        if not color in root_pos:
            self.caller.msg("No such root to move.")
            return

        # first, vertical roots (red/blue) - can be moved left/right
        if color == "red":
            if direction == "left":
                root_pos[color] = max(-1, root_pos[color] - 1)
                self.caller.msg("You shift the reddish root to the left.")
                if root_pos[color] != 0 and root_pos[color] == root_pos["blue"]:
                    root_pos["blue"] += 1
                    self.caller.msg("The root with blue flowers gets in the way and is pushed to the right.")
            elif direction == "right":
                root_pos[color] = min(1, root_pos[color] + 1)
                self.caller.msg("You shove the reddish root to the right.")
                if root_pos[color] != 0 and root_pos[color] == root_pos["blue"]:
                    root_pos["blue"] -= 1
                    self.caller.msg("The root with blue flowers gets in the way and is pushed to the left.")
            else:
                self.caller.msg("You cannot move the root in that direction.")
        elif color == "blue":
            if direction == "left":
                root_pos[color] = max(-1, root_pos[color] - 1)
                self.caller.msg("You shift the root with small blue flowers to the left.")
                if root_pos[color] != 0 and root_pos[color] == root_pos["red"]:
                    root_pos["red"] += 1
                    self.caller.msg("The reddish root is to big to fit as well, so that one falls away to the left.")
            elif direction == "right":
                root_pos[color] = min(1, root_pos[color] + 1)
                self.caller.msg("You shove the root adorned with small blue flowers to the right.")
                if root_pos[color] != 0 and root_pos[color] == root_pos["red"]:
                    root_pos["red"] -= 1
                    self.caller.msg("The thick reddish root gets in the way and is pushed back to the left.")
            else:
                self.caller.msg("You cannot move the root in that direction.")
        # now the horizontal roots (yellow/green). They can be moved up/down
        elif color == "yellow":
            if direction == "up":
                root_pos[color] = max(-1, root_pos[color] - 1)
                self.caller.msg("You shift the root with small yellow flowers upwards.")
                if root_pos[color] != 0 and root_pos[color] == root_pos["green"]:
                    root_pos["green"] += 1
                    self.caller.msg("The green weedy root falls down.")
            elif direction == "down":
                root_pos[color] = min(1, root_pos[color] +1)
                self.caller.msg("You shove the root adorned with small yellow flowers downwards.")
                if root_pos[color] != 0 and root_pos[color] == root_pos["green"]:
                    root_pos["green"] -= 1
                    self.caller.msg("The weedy green root is shifted upwards to make room.")
            else:
                self.caller.msg("You cannot move the root in that direction.")
        elif color == "green":
            if direction == "up":
                root_pos[color] = max(-1, root_pos[color] - 1)
                self.caller.msg("You shift the weedy green root upwards.")
                if root_pos[color] != 0 and root_pos[color] == root_pos["yellow"]:
                    root_pos["yellow"] += 1
                    self.caller.msg("The root with yellow flowers falls down.")
            elif direction == "down":
                root_pos[color] = min(1, root_pos[color] + 1)
                self.caller.msg("You shove the weedy green root downwards.")
                if root_pos[color] != 0 and root_pos[color] == root_pos["yellow"]:
                    root_pos["yellow"] -= 1
                    self.caller.msg("The root with yellow flowers gets in the way and is pushed upwards.")
            else:
                self.caller.msg("You cannot move the root in that direction.")
        # store new position
        self.obj.db.root_pos = root_pos
        # check victory condition
        if root_pos.values().count(0) == 0: # no roots in middle position
            self.caller.db.crumbling_wall_found_button = True
            self.caller.msg("Holding aside the root you think you notice something behind it ...")

class CmdPressButton(Command):
    """
    Presses a button.
    """
    key = "press"
    aliases = ["press button", "button", "push", "push button"]
    locks = "cmd:attr(crumbling_wall_found_button) and not locattr(is_dark)" # only accessible if the button was found and there is light.
    help_category = "TutorialWorld"

    def func(self):
        "Implements the command"

        if self.caller.db.crumbling_wall_found_exit:
            # we already pushed the button
            self.caller.msg("The button folded away when the secret passage opened. You cannot push it again.")
            return

        # pushing the button
        string = "You move your fingers over the suspicious depression, then gives it a "
        string += "decisive push. First nothing happens, then there is a rumble and a hidden "
        string += "{wpassage{n opens, dust and pebbles rumbling as part of the wall moves aside."

        # we are done - this will make the exit traversable!
        self.caller.db.crumbling_wall_found_exit = True
        # this will make it into a proper exit
        eloc = self.caller.search(self.obj.db.destination, global_search=True)
        if not eloc:
            self.caller.msg("The exit leads nowhere, there's just more stone behind it ...")
            return
        self.obj.destination = eloc
        self.caller.msg(string)

class CmdSetCrumblingWall(CmdSet):
    "Group the commands for crumblingWall"
    key = "crumblingwall_cmdset"
    def at_cmdset_creation(self):
        "called when object is first created."
        self.add(CmdShiftRoot())
        self.add(CmdPressButton())

class CrumblingWall(TutorialObject, Exit):
    """
    The CrumblingWall can be examined in various
    ways, but only if a lit light source is in the room. The traversal
    itself is blocked by a traverse: lock on the exit that only
    allows passage if a certain attribute is set on the trying
    player.

    Important attribute
     destination - this property must be set to make this a valid exit
                   whenever the button is pushed (this hides it as an exit
                   until it actually is)
    """
    def at_object_creation(self):
        "called when the object is first created."
        super(CrumblingWall, self).at_object_creation()

        self.aliases = ["secret passage", "passage", "crack", "opening", "secret door"]
        # this is assigned first when pushing button, so assign this at creation time!
        self.db.destination = 2
        # locks on the object directly transfer to the exit "command"
        self.locks.add("cmd:not locattr(is_dark)")

        self.db.tutorial_info = "This is an Exit with a conditional traverse-lock. Try to shift the roots around."
        # the lock is important for this exit; we only allow passage if we "found exit".
        self.locks.add("traverse:attr(crumbling_wall_found_exit)")
        # set cmdset
        self.cmdset.add(CmdSetCrumblingWall, permanent=True)

        # starting root positions. H1/H2 are the horizontally hanging roots, V1/V2 the
        # vertically hanging ones. Each can have three positions: (-1, 0, 1) where
        # 0 means the middle position. yellow/green are horizontal roots and red/blue vertical.
        # all may have value 0, but never any other identical value.
        self.db.root_pos = {"yellow":0, "green":0, "red":0, "blue":0}

    def _translate_position(self, root, ipos):
        "Translates the position into words"
        rootnames = {"red": "The {rreddish{n vertical-hanging root ",
                     "blue": "The thick vertical root with {bblue{n flowers ",
                     "yellow": "The thin horizontal-hanging root with {yyellow{n flowers ",
                     "green": "The weedy {ggreen{n horizontal root "}
        vpos = {-1: "hangs far to the {wleft{n on the wall.",
                 0: "hangs straight down the {wmiddle{n of the wall.",
                 1: "hangs far to the {wright{n of the wall."}
        hpos = {-1: "covers the {wupper{n part of the wall.",
                 0: "passes right over the {wmiddle{n of the wall.",
                 1: "nearly touches the floor, near the {wbottom{n of the wall."}

        if root in ("yellow", "green"):
            string = rootnames[root] + hpos[ipos]
        else:
            string = rootnames[root] + vpos[ipos]
        return string

    def return_appearance(self, caller):
        "This is called when someone looks at the wall. We need to echo the current root positions."
        if caller.db.crumbling_wall_found_button:
            string = "Having moved all the roots aside, you find that the center of the wall, "
            string += "previously hidden by the vegetation, hid a curious square depression. It was maybe once "
            string += "concealed and made to look a part of the wall, but with the crumbling of stone around it,"
            string += "it's now easily identifiable as some sort of button."
        else:
            string =  "The wall is old and covered with roots that here and there have permeated the stone. "
            string += "The roots (or whatever they are - some of them are covered in small non-descript flowers) "
            string += "crisscross the wall, making it hard to clearly see its stony surface.\n"
            for key, pos in self.db.root_pos.items():
                string += "\n" + self._translate_position(key, pos)
        self.db.desc = string
        # call the parent to continue execution (will use desc we just set)
        return super(CrumblingWall, self).return_appearance(caller)

    def at_after_traverse(self, traverser, source_location):
        "This is called after we traversed this exit. Cleans up and resets the puzzle."
        del traverser.db.crumbling_wall_found_button
        del traverser.db.crumbling_wall_found_exit
        self.reset()

    def at_failed_traverse(self, traverser):
        "This is called if the player fails to pass the Exit."
        traverser.msg("No matter how you try, you cannot force yourself through %s." % self.key)

    def reset(self):
        "Called by tutorial world runner, or whenever someone successfully traversed the Exit."
        self.location.msg_contents("The secret door closes abruptly, roots falling back into place.")
        for obj in self.location.contents:
            # clear eventual puzzle-solved attribues on everyone that didn't get out in time. They
            # have to try again.
            del obj.db.crumbling_wall_found_exit

        # Reset the roots with some random starting positions for the roots:
        start_pos = [{"yellow":1, "green":0, "red":0, "blue":0},
                     {"yellow":0, "green":0, "red":0, "blue":0},
                     {"yellow":0, "green":1, "red":-1, "blue":0},
                     {"yellow":1, "green":0, "red":0, "blue":0},
                     {"yellow":0, "green":0, "red":0, "blue":1}]
        self.db.root_pos = start_pos[random.randint(0, 4)]
        self.destination = None

#------------------------------------------------------------
#
# Weapon - object type
#
# A weapon is necessary in order to fight in the tutorial
# world. A weapon (which here is assumed to be a bladed
# melee weapon for close combat) has three commands,
# stab, slash and defend. Weapons also have a property "magic"
# to determine if they are usable against certain enemies.
#
# Since Characters don't have special skills in the tutorial,
# we let the weapon itself determine how easy/hard it is
# to hit with it, and how much damage it can do.
#
#------------------------------------------------------------

class CmdAttack(Command):
    """
    Attack the enemy. Commands:

      stab <enemy>
      slash <enemy>
      parry

    stab - (thrust) makes a lot of damage but is harder to hit with.
    slash - is easier to land, but does not make as much damage.
    parry - forgoes your attack but will make you harder to hit on next enemy attack.

    """

    # this is an example of implementing many commands as a single command class,
    # using the given command alias to separate between them.

    key = "attack"
    aliases = ["hit","kill", "fight", "thrust", "pierce", "stab", "slash", "chop", "parry", "defend"]
    locks = "cmd:all()"
    help_category = "TutorialWorld"

    def func(self):
        "Implements the stab"

        cmdstring = self.cmdstring


        if cmdstring in ("attack", "fight"):
            string = "How do you want to fight? Choose one of 'stab', 'slash' or 'defend'."
            self.caller.msg(string)
            return

        # parry mode
        if cmdstring in ("parry", "defend"):
            string = "You raise your weapon in a defensive pose, ready to block the next enemy attack."
            self.caller.msg(string)
            self.caller.db.combat_parry_mode = True
            self.caller.location.msg_contents("%s takes a defensive stance" % self.caller, exclude=[self.caller])
            return

        if not self.args:
            self.caller.msg("Who do you attack?")
            return
        target = self.caller.search(self.args.strip())
        if not target:
            return

        string = ""
        tstring = ""
        ostring = ""
        if cmdstring in ("thrust", "pierce", "stab"):
            hit = float(self.obj.db.hit) * 0.7 # modified due to stab
            damage = self.obj.db.damage * 2 # modified due to stab
            string = "You stab with %s. " % self.obj.key
            tstring = "%s stabs at you with %s. " % (self.caller.key, self.obj.key)
            ostring = "%s stabs at %s with %s. " % (self.caller.key, target.key, self.obj.key)
            self.caller.db.combat_parry_mode = False
        elif cmdstring in ("slash", "chop"):
            hit = float(self.obj.db.hit)  # un modified due to slash
            damage = self.obj.db.damage # un modified due to slash
            string = "You slash with %s. " % self.obj.key
            tstring = "%s slash at you with %s. " % (self.caller.key, self.obj.key)
            ostring = "%s slash at %s with %s. " % (self.caller.key, target.key, self.obj.key)
            self.caller.db.combat_parry_mode = False
        else:
            self.caller.msg("You fumble with your weapon, unsure of whether to stab, slash or parry ...")
            self.caller.location.msg_contents("%s fumbles with their weapon." % self.obj.key)
            self.caller.db.combat_parry_mode = False
            return

        if target.db.combat_parry_mode:
            # target is defensive; even harder to hit!
            target.msg("{GYou defend, trying to avoid the attack.{n")
            hit *= 0.5

        if random.random() <= hit:
            self.caller.msg(string + "{gIt's a hit!{n")
            target.msg(tstring + "{rIt's a hit!{n")
            self.caller.location.msg_contents(ostring + "It's a hit!", exclude=[target,self.caller])

            # call enemy hook
            if hasattr(target, "at_hit"):
                # should return True if target is defeated, False otherwise.
                return target.at_hit(self.obj, self.caller, damage)
            elif target.db.health:
                target.db.health -= damage
            else:
                # sorry, impossible to fight this enemy ...
                self.caller.msg("The enemy seems unaffacted.")
                return False
        else:
            self.caller.msg(string + "{rYou miss.{n")
            target.msg(tstring + "{gThey miss you.{n")
            self.caller.location.msg_contents(ostring + "They miss.", exclude=[target, self.caller])

class CmdSetWeapon(CmdSet):
    "Holds the attack command."
    def at_cmdset_creation(self):
        "called at first object creation."
        self.add(CmdAttack())

class Weapon(TutorialObject):
    """
    This defines a bladed weapon.

    Important attributes (set at creation):
      hit - chance to hit (0-1)
      parry - chance to parry (0-1)
      damage - base damage given (modified by hit success and type of attack) (0-10)

    """
    def at_object_creation(self):
        "Called at first creation of the object"
        super(Weapon, self).at_object_creation()
        self.db.hit = 0.4    # hit chance
        self.db.parry = 0.8  # parry chance
        self.damage = 8.0
        self.magic = False
        self.cmdset.add_default(CmdSetWeapon, permanent=True)

    def reset(self):
        "When reset, the weapon is simply deleted, unless it has a place to return to."
        if self.location.has_player and self.home == self.location:
            self.location.msg_contents("%s suddenly and magically fades into nothingness, as if it was never there ..." % self.key)
            self.delete()
        else:
            self.location = self.home

#------------------------------------------------------------
#
# Weapon rack - spawns weapons
#
#------------------------------------------------------------

class CmdGetWeapon(Command):
    """
    Usage:
      get weapon

    This will try to obtain a weapon from the container.
    """
    key = "get"
    aliases = "get weapon"
    locks = "cmd:all()"
    help_cateogory = "TutorialWorld"

    def func(self):
        "Implement the command"

        rack_id = self.obj.db.rack_id
        if self.caller.get_attribute(rack_id):
            # we don't allow a player to take more than one weapon from rack.
            self.caller.msg("%s has no more to offer you." % self.obj.name)
        else:
            dmg, name, aliases, desc, magic = self.obj.randomize_type()
            new_weapon = create_object(Weapon, key=name, aliases=aliases,location=self.caller, home=self.caller)
            new_weapon.db.rack_id = rack_id
            new_weapon.db.damage = dmg
            new_weapon.db.desc = desc
            new_weapon.db.magic = magic
            ostring = self.obj.db.get_text
            if not ostring:
                ostring = "You pick up %s."
            if '%s' in ostring:
                self.caller.msg(ostring % name)
            else:
                self.caller.msg(ostring)
            # tag the caller so they cannot keep taking objects from the rack.
            self.caller.set_attribute(rack_id, True)


class CmdSetWeaponRack(CmdSet):
    "group the rack cmd"
    key = "weaponrack_cmdset"
    mergemode = "Replace"
    def at_cmdset_creation(self):
        self.add(CmdGetWeapon())

class WeaponRack(TutorialObject):
    """
    This will spawn a new weapon for the player unless the player already has one from this rack.

    attribute to set at creation:
    min_dmg  - the minimum damage of objects from this rack
    max_dmg - the maximum damage of objects from this rack
    magic - if weapons should be magical (have the magic flag set)
    get_text - the echo text to return when getting the weapon. Give '%s' to include the name of the weapon.
    """
    def at_object_creation(self):
        "called at creation"
        self.cmdset.add_default(CmdSetWeaponRack, permanent=True)
        self.db.rack_id = "weaponrack_1"
        self.db.min_dmg = 1.0
        self.db.max_dmg = 4.0
        self.db.magic = False

    def randomize_type(self):
        """
        this returns a random weapon
        """
        min_dmg = float(self.db.min_dmg)
        max_dmg = float(self.db.max_dmg)
        magic = bool(self.db.magic)
        dmg = min_dmg + random.random()*(max_dmg - min_dmg)
        aliases = [self.db.rack_id, "weapon"]
        if dmg < 1.5:
            name = "Knife"
            desc = "A rusty kitchen knife. Better than nothing."
        elif dmg < 2.0:
            name = "Rusty dagger"
            desc = "A double-edged dagger with nicked edge. It has a wooden handle."
        elif dmg < 3.0:
            name = "Sword"
            desc = "A rusty shortsword. It has leather wrapped around the handle."
        elif dmg < 4.0:
            name = "Club"
            desc = "A heavy wooden club with some rusty spikes in it."
        elif dmg < 5.0:
            name = "Ornate Longsword"
            aliases.extend(["longsword","ornate"])
            desc = "A fine longsword."
        elif dmg < 6.0:
            name = "Runeaxe"
            aliases.extend(["rune","axe"])
            desc = "A single-bladed axe, heavy but yet easy to use."
        elif dmg < 7.0:
            name = "Broadsword named Thruning"
            aliases.extend(["thruning","broadsword"])
            desc = "This heavy bladed weapon is marked with the name 'Thruning'. It is very powerful in skilled hands."
        elif dmg < 8.0:
            name = "Silver Warhammer"
            aliases.append("warhammer")
            desc = "A heavy war hammer with silver ornaments. This huge weapon causes massive damage."
        elif dmg < 9.0:
            name = "Slayer Waraxe"
            aliases.extend(["waraxe","slayer"])
            desc = "A huge double-bladed axe marked with the runes for 'Slayer'. It has more runic inscriptions on its head, which you cannot decipher."
        elif dmg < 10.0:
            name = "The Ghostblade"
            aliases.append("ghostblade")
            desc =  "This massive sword is large as you are tall. Its metal shine with a bluish glow."
        else:
            name = "The Hawkblade"
            aliases.append("hawkblade")
            desc = "White surges of magical power runs up and down this runic blade. The hawks depicted on its hilt almost seems to have a life of their own."
        if dmg < 9 and magic:
            desc += "\nThe metal seems to glow faintly, as if imbued with more power than what is immediately apparent."
        return dmg, name, aliases, desc, magic
