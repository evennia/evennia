"""

Room Typeclasses for the TutorialWorld.

"""

import random
from ev import CmdSet, Script, Command, Room
from ev import utils, create_object, search_object
from contrib.tutorial_world import scripts as tut_scripts
from contrib.tutorial_world.objects import LightSource, TutorialObject

#------------------------------------------------------------
#
# Tutorial room - parent room class
#
# This room is the parent of all rooms in the tutorial.
# It defines a tutorial command on itself (available to
# all who is in a tutorial room).
#
#------------------------------------------------------------

class CmdTutorial(Command):
    """
    Get help during the tutorial

    Usage:
      tutorial [obj]

    This command allows you to get behind-the-scenes info
    about an object or the current location.

    """
    key = "tutorial"
    aliases = ["tut"]
    locks = "cmd:all()"
    help_category = "TutorialWorld"

    def func(self):
        """
        All we do is to scan the current location for an attribute
        called `tutorial_info` and display that.
        """

        caller = self.caller

        if not self.args:
            target = self.obj # this is the room object the command is defined on
        else:
            target = caller.search(self.args.strip())
            if not target:
                return
        helptext = target.db.tutorial_info
        if helptext:
            caller.msg("{G%s{n" % helptext)
        else:
            caller.msg("{RSorry, there is no tutorial help available here.{n")

class TutorialRoomCmdSet(CmdSet):
    "Implements the simple tutorial cmdset"
    key = "tutorial_cmdset"
    def at_cmdset_creation(self):
        "add the tutorial cmd"
        self.add(CmdTutorial())

class TutorialRoom(Room):
    """
    This is the base room type for all rooms in the tutorial world.
    It defines a cmdset on itself for reading tutorial info about the location.
    """
    def at_object_creation(self):
        "Called when room is first created"
        self.db.tutorial_info = "This is a tutorial room. It allows you to use the 'tutorial' command."
        self.cmdset.add_default(TutorialRoomCmdSet)

    def reset(self):
        "Can be called by the tutorial runner."
        pass



#------------------------------------------------------------
#
# Weather room - scripted room
#
# The weather room is called by a script at
# irregular intervals. The script is generally useful
# and so is split out into tutorialworld.scripts.
#
#------------------------------------------------------------


class WeatherRoom(TutorialRoom):
    """
    This should probably better be called a rainy room...

    This sets up an outdoor room typeclass. At irregular intervals,
    the effects of weather will show in the room. Outdoor rooms should
    inherit from this.

    """
    def at_object_creation(self):
        "Called when object is first created."
        super(WeatherRoom, self).at_object_creation()

        # we use the imported IrregularEvent script
        self.scripts.add(tut_scripts.IrregularEvent)
        self.db.tutorial_info = \
            "This room has a Script running that has it echo a weather-related message at irregular intervals."
    def update_irregular(self):
        "create a tuple of possible texts to return."
        strings = (
            "The rain coming down from the iron-grey sky intensifies.",
            "A gush of wind throws the rain right in your face. Despite your cloak you shiver.",
            "The rainfall eases a bit and the sky momentarily brightens.",
            "For a moment it looks like the rain is slowing, then it begins anew with renewed force.",
            "The rain pummels you with large, heavy drops. You hear the rumble of thunder in the distance.",
            "The wind is picking up, howling around you, throwing water droplets in your face. It's cold.",
            "Bright fingers of lightning flash over the sky, moments later followed by a deafening rumble.",
            "It rains so hard you can hardly see your hand in front of you. You'll soon be drenched to the bone.",
            "Lightning strikes in several thundering bolts, striking the trees in the forest to your west.",
            "You hear the distant howl of what sounds like some sort of dog or wolf.",
            "Large clouds rush across the sky, throwing their load of rain over the world.")

        # get a random value so we can select one of the strings above. Send this to the room.
        irand = random.randint(0, 15)
        if irand > 10:
            return # don't return anything, to add more randomness
        self.msg_contents("{w%s{n" % strings[irand])


#-----------------------------------------------------------------------------------
#
# Dark Room - a scripted room
#
# This room limits the movemenets of its denizens unless they carry a and active
# LightSource object (LightSource is defined in tutorialworld.objects.LightSource)
#
#-----------------------------------------------------------------------------------

class CmdLookDark(Command):
    """
    Look around in darkness

    Usage:
      look

    Looks in darkness
    """
    key = "look"
    aliases = ["l", 'feel', 'feel around', 'fiddle']
    locks = "cmd:all()"
    help_category = "TutorialWorld"

    def func(self):
        "Implement the command."
        caller = self.caller
        # we don't have light, grasp around blindly.
        messages = ("It's pitch black. You fumble around but cannot find anything.",
                    "You don't see a thing. You feel around, managing to bump your fingers hard against something. Ouch!",
                    "You don't see a thing! Blindly grasping the air around you, you find nothing.",
                    "It's totally dark here. You almost stumble over some un-evenness in the ground.",
                    "You are completely blind. For a moment you think you hear someone breathing nearby ... \n ... surely you must be mistaken.",
                    "Blind, you think you find some sort of object on the ground, but it turns out to be just a stone.",
                    "Blind, you bump into a wall. The wall seems to be covered with some sort of vegetation, but its too damp to burn.",
                    "You can't see anything, but the air is damp. It feels like you are far underground.")
        irand = random.randint(0, 10)
        if irand < len(messages):
            caller.msg(messages[irand])
        else:
            # check so we don't already carry a lightsource.
            carried_lights = [obj for obj in caller.contents if utils.inherits_from(obj, LightSource)]
            if carried_lights:
                string = "You don't want to stumble around in blindness anymore. You already found what you need. Let's get light already!"
                caller.msg(string)
                return
            #if we are lucky, we find the light source.
            lightsources = [obj for obj in self.obj.contents if utils.inherits_from(obj, LightSource)]
            if lightsources:
                lightsource = lightsources[0]
            else:
                # create the light source from scratch.
                lightsource = create_object(LightSource, key="splinter")
            lightsource.location = caller
            string = "Your fingers bump against a splinter of wood in a corner. It smells of resin and seems dry enough to burn!"
            string += "\nYou pick it up, holding it firmly. Now you just need to {wlight{n it using the flint and steel you carry with you."
            caller.msg(string)

class CmdDarkHelp(Command):
    """
    Help command for the dark state.
    """
    key = "help"
    locks = "cmd:all()"
    help_category = "TutorialWorld"
    def func(self):
        "Implements the help command."
        string = "Can't help you until you find some light! Try feeling around for something to burn."
        string += " You cannot give up even if you don't find anything right away."
        self.caller.msg(string)

# the nomatch system command will give a suitable error when we cannot find the normal commands.
from src.commands.default.syscommands import CMD_NOMATCH
from src.commands.default.general import CmdSay
class CmdDarkNoMatch(Command):
    "This is called when there is no match"
    key = CMD_NOMATCH
    locks = "cmd:all()"
    def func(self):
        "Implements the command."
        self.caller.msg("Until you find some light, there's not much you can do. Try feeling around.")

class DarkCmdSet(CmdSet):
    "Groups the commands."
    key = "darkroom_cmdset"
    mergetype = "Replace" # completely remove all other commands
    def at_cmdset_creation(self):
        "populates the cmdset."
        self.add(CmdTutorial())
        self.add(CmdLookDark())
        self.add(CmdDarkHelp())
        self.add(CmdDarkNoMatch())
        self.add(CmdSay)
#
# Darkness room two-state system
#

class DarkState(Script):
    """
    The darkness state is a script that keeps tabs on when
    a player in the room carries an active light source. It places
    a new, very restrictive cmdset (DarkCmdSet) on all the players
    in the room whenever there is no light in it. Upon turning on
    a light, the state switches off and moves to LightState.
    """
    def at_script_creation(self):
        "This setups the script"
        self.key = "tutorial_darkness_state"
        self.desc = "A dark room"
        self.persistent = True
    def at_start(self):
        "called when the script is first starting up."
        for char in [char for char in self.obj.contents if char.has_player]:
            if char.is_superuser:
                char.msg("You are Superuser, so you are not affected by the dark state.")
            else:
                char.cmdset.add(DarkCmdSet)
            char.msg("The room is pitch dark! You are likely to be eaten by a Grue.")
    def is_valid(self):
        "is valid only as long as noone in the room has lit the lantern."
        return not self.obj.is_lit()
    def at_stop(self):
        "Someone turned on a light. This state dies. Switch to LightState."
        for char in [char for char in self.obj.contents if char.has_player]:
            char.cmdset.delete(DarkCmdSet)
        self.obj.db.is_dark = False
        self.obj.scripts.add(LightState)

class LightState(Script):
    """
    This is the counterpart to the Darkness state. It is active when the lantern is on.
    """
    def at_script_creation(self):
        "Called when script is first created."
        self.key = "tutorial_light_state"
        self.desc = "A room lit up"
        self.persistent = True
    def is_valid(self):
        "This state is only valid as long as there is an active light source in the room."
        return self.obj.is_lit()
    def at_stop(self):
        "Light disappears. This state dies. Return to DarknessState."
        self.obj.db.is_dark = True
        self.obj.scripts.add(DarkState)

class DarkRoom(TutorialRoom):
    """
    A dark room. This tries to start the DarkState script on all
    objects entering. The script is responsible for making sure it is
    valid (that is, that there is no light source shining in the room).
    """
    def is_lit(self):
        """
        Helper method to check if the room is lit up. It checks all
        characters in room to see if they carry an active object of
        type LightSource.
        """
        return any([any([True for obj in char.contents
                         if utils.inherits_from(obj, LightSource) and obj.db.is_active])
                    for char in self.contents if char.has_player])

    def at_object_creation(self):
        "Called when object is first created."
        super(DarkRoom, self).at_object_creation()
        self.db.tutorial_info = "This is a room with custom command sets on itself."
        # this variable is set by the scripts. It makes for an easy flag to look for
        # by other game elements (such as the crumbling wall in the tutorial)
        self.db.is_dark = True
        # the room starts dark.
        self.scripts.add(DarkState)

    def at_object_receive(self, character, source_location):
        "Called when an object enters the room. We crank the wheels to make sure scripts are synced."
        if character.has_player:
            if not self.is_lit() and not character.is_superuser:
                character.cmdset.add(DarkCmdSet)
            if character.db.health and character.db.health <= 0:
                # heal character coming here from being defeated by mob.
                health = character.db.health_max
                if not health:
                    health = 20
                character.db.health = health
        self.scripts.validate()

    def at_object_leave(self, character, target_location):
        "In case people leave with the light, we make sure to update the states accordingly."
        character.cmdset.delete(DarkCmdSet) # in case we are teleported away
        self.scripts.validate()

#------------------------------------------------------------
#
# Teleport room - puzzle room
#
# This is a sort of puzzle room that requires a certain
# attribute on the entering character to be the same as
# an attribute of the room. If not, the character will
# be teleported away to a target location. This is used
# by the Obelisk - grave chamber puzzle, where one must
# have looked at the obelisk to get an attribute set on
# oneself, and then pick the grave chamber with the
# matching imagery for this attribute.
#
#------------------------------------------------------------

class TeleportRoom(TutorialRoom):
    """
    Teleporter - puzzle room.

    Important attributes (set at creation):
      puzzle_key    - which attr to look for on character
      puzzle_value  - what char.db.puzzle_key must be set to
      teleport_to   - where to teleport to in case of failure to match

    """
    def at_object_creation(self):
        "Called at first creation"
        super(TeleportRoom, self).at_object_creation()
        # what character.db.puzzle_clue must be set to, to avoid teleportation.
        self.db.puzzle_value = 1
        # the target of the success teleportation. Can be a dbref or a unique room name.
        self.db.success_teleport_to = "treasure room"
        # the target of the failure teleportation.
        self.db.failure_teleport_to = "dark cell"

    def at_object_receive(self, character, source_location):
        "This hook is called by the engine whenever the player is moved into this room."
        if not character.has_player:
            # only act on player characters.
            return
        #print character.db.puzzle_clue, self.db.puzzle_value
        if character.db.puzzle_clue != self.db.puzzle_value:
            # we didn't pass the puzzle. See if we can teleport.
            teleport_to = self.db.failure_teleport_to # this is a room name
        else:
            # passed the puzzle
            teleport_to = self.db.success_teleport_to # this is a room name

        results = search_object(teleport_to)
        if not results or len(results) > 1:
            # we cannot move anywhere since no valid target was found.
            print "no valid teleport target for %s was found." % teleport_to
            return
        if character.player.is_superuser:
            # superusers don't get teleported
            character.msg("Superuser block: You would have been teleported to %s." % results[0])
            return
        # teleport
        character.execute_cmd("look")
        character.location = results[0] # stealth move
        character.location.at_object_receive(character, self)

#------------------------------------------------------------
#
# Bridge - unique room
#
# Defines a special west-eastward "bridge"-room, a large room it takes
# several steps to cross. It is complete with custom commands and a
# chance of falling off the bridge. This room has no regular exits,
# instead the exiting are handled by custom commands set on the player
# upon first entering the room.
#
# Since one can enter the bridge room from both ends, it is
# divided into five steps:
#       westroom <- 0 1 2 3 4 -> eastroom
#
#------------------------------------------------------------


class CmdEast(Command):
    """
    Try to cross the bridge eastwards.
    """
    key = "east"
    aliases = ["e"]
    locks = "cmd:all()"
    help_category = "TutorialWorld"

    def func(self):
        "move forward"
        caller = self.caller

        bridge_step = min(5, caller.db.tutorial_bridge_position + 1)

        if bridge_step > 4:
            # we have reached the far east end of the bridge. Move to the east room.
            eexit = search_object(self.obj.db.east_exit)
            if eexit:
                caller.move_to(eexit[0])
            else:
                caller.msg("No east exit was found for this room. Contact an admin.")
            return
        caller.db.tutorial_bridge_position = bridge_step
        caller.location.msg_contents("%s steps eastwards across the bridge." % caller.name, exclude=caller)
        caller.execute_cmd("look")

# go back across the bridge
class CmdWest(Command):
    """
    Go back across the bridge westwards.
    """
    key = "west"
    aliases = ["w"]
    locks = "cmd:all()"
    help_category = "TutorialWorld"

    def func(self):
        "move forward"
        caller = self.caller

        bridge_step = max(-1, caller.db.tutorial_bridge_position - 1)

        if bridge_step < 0:
            # we have reached the far west end of the bridge. Move to the west room.
            wexit = search_object(self.obj.db.west_exit)
            if wexit:
                caller.move_to(wexit[0])
            else:
                caller.msg("No west exit was found for this room. Contact an admin.")
            return
        caller.db.tutorial_bridge_position = bridge_step
        caller.location.msg_contents("%s steps westwartswards across the bridge." % caller.name, exclude=caller)
        caller.execute_cmd("look")

class CmdLookBridge(Command):
    """
    looks around at the bridge.
    """
    key = 'look'
    aliases = ["l"]
    locks = "cmd:all()"
    help_category = "TutorialWorld"

    def func(self):
        "Looking around, including a chance to fall."
        bridge_position = self.caller.db.tutorial_bridge_position


        messages =("You are standing {wvery close to the the bridge's western foundation{n. If you go west you will be back on solid ground ...",
                   "The bridge slopes precariously where it extends eastwards towards the lowest point - the center point of the hang bridge.",
                   "You are {whalfways{n out on the unstable bridge.",
                   "The bridge slopes precariously where it extends westwards towards the lowest point - the center point of the hang bridge.",
                   "You are standing {wvery close to the bridge's eastern foundation{n. If you go east you will be back on solid ground ...")
        moods = ("The bridge sways in the wind.", "The hanging bridge creaks dangerously.",
                 "You clasp the ropes firmly as the bridge sways and creaks under you.",
                 "From the castle you hear a distant howling sound, like that of a large dog or other beast.",
                 "The bridge creaks under your feet. Those planks does not seem very sturdy.",
                 "Far below you the ocean roars and throws its waves against the cliff, as if trying its best to reach you.",
                 "Parts of the bridge come loose behind you, falling into the chasm far below!",
                 "A gust of wind causes the bridge to sway precariously.",
                 "Under your feet a plank comes loose, tumbling down. For a moment you dangle over the abyss ...",
                 "The section of rope you hold onto crumble in your hands, parts of it breaking apart. You sway trying to regain balance.")
        message = "{c%s{n\n" % self.obj.key + messages[bridge_position] + "\n" + moods[random.randint(0, len(moods) - 1)]
        chars = [obj for obj in self.obj.contents if obj != self.caller and obj.has_player]
        if chars:
            message += "\n You see: %s" % ", ".join("{c%s{n" % char.key for char in chars)

        self.caller.msg(message)

        # there is a chance that we fall if we are on the western or central part of the bridge.
        if bridge_position < 3 and random.random() < 0.05 and not self.caller.is_superuser:
            # we fall on 5% of the times.
            fexit = search_object(self.obj.db.fall_exit)
            if fexit:
                string = "\n Suddenly the plank you stand on gives way under your feet! You fall!"
                string += "\n You try to grab hold of an adjoining plank, but all you manage to do is to "
                string += "divert your fall westwards, towards the cliff face. This is going to hurt ... "
                string += "\n ... The world goes dark ...\n"
                # note that we move silently so as to not call look hooks (this is a little trick to leave
                # the player with the "world goes dark ..." message, giving them ample time to read it. They
                # have to manually call look to find out their new location). Thus we also call the
                # at_object_leave hook manually (otherwise this is done by move_to()).
                self.caller.msg("{r%s{n" % string)
                self.obj.at_object_leave(self.caller, fexit)
                self.caller.location = fexit[0] # stealth move, without any other hook calls.
                self.obj.msg_contents("A plank gives way under %s's feet and they fall from the bridge!" % self.caller.key)

# custom help command
class CmdBridgeHelp(Command):
    """
    Overwritten help command
    """
    key = "help"
    aliases = ["h"]
    locks = "cmd:all()"
    help_category = "Tutorial world"

    def func(self):
        "Implements the command."
        string = "You are trying hard not to fall off the bridge ..."
        string += "\n\nWhat you can do is trying to cross the bridge {weast{n "
        string += "or try to get back to the mainland {wwest{n)."
        self.caller.msg(string)

class BridgeCmdSet(CmdSet):
    "This groups the bridge commands. We will store it on the room."
    key = "Bridge commands"
    priority = 1 # this gives it precedence over the normal look/help commands.
    def at_cmdset_creation(self):
        self.add(CmdTutorial())
        self.add(CmdEast())
        self.add(CmdWest())
        self.add(CmdLookBridge())
        self.add(CmdBridgeHelp())

class BridgeRoom(TutorialRoom):
    """
    The bridge room implements an unsafe bridge. It also enters the player into a
    state where they get new commands so as to try to cross the bridge.

     We want this to result in the player getting a special set of
        commands related to crossing the bridge. The result is that it will take several
        steps to cross it, despite it being represented by only a single room.

        We divide the bridge into steps:

        self.db.west_exit     -   -  |  -   -     self.db.east_exit
                              0   1  2  3   4

        The position is handled by a variable stored on the player when entering and giving
        special move commands will increase/decrease the counter until the bridge is crossed.

    """
    def at_object_creation(self):
        "Setups the room"
        super(BridgeRoom, self).at_object_creation()

        # at irregular intervals, this will call self.update_irregular()
        self.scripts.add(tut_scripts.IrregularEvent)
        # this identifies the exits from the room (should be the command
        # needed to leave through that exit). These are defaults, but you
        # could of course also change them after the room has been created.
        self.db.west_exit = "cliff"
        self.db.east_exit = "gate"
        self.db.fall_exit = "cliffledge"
        # add the cmdset on the room.
        self.cmdset.add_default(BridgeCmdSet)

        self.db.tutorial_info = \
            """The bridge seem large but is actually only a single room that assigns custom west/east commands."""

    def update_irregular(self):
        """
        This is called at irregular intervals and makes the passage
        over the bridge a little more interesting.
        """
        strings = (
            "The rain intensifies, making the planks of the bridge even more slippery.",
            "A gush of wind throws the rain right in your face.",
            "The rainfall eases a bit and the sky momentarily brightens.",
            "The bridge shakes under the thunder of a closeby thunder strike.",
            "The rain pummels you with large, heavy drops. You hear the distinct howl of a large hound in the distance.",
            "The wind is picking up, howling around you and causing the bridge to sway from side to side.",
            "Some sort of large bird sweeps by overhead, giving off an eery screech. Soon it has disappeared in the gloom.",
            "The bridge sways from side to side in the wind.")
        self.msg_contents("{w%s{n" % strings[random.randint(0, 7)])

    def at_object_receive(self, character, source_location):
        """
        This hook is called by the engine whenever the player is moved
        into this room.
        """
        if character.has_player:
            # we only run this if the entered object is indeed a player object.
            # check so our east/west exits are correctly defined.
            wexit = search_object(self.db.west_exit)
            eexit = search_object(self.db.east_exit)
            fexit = search_object(self.db.fall_exit)
            if not wexit or not eexit or not fexit:
                character.msg("The bridge's exits are not properly configured. Contact an admin. Forcing west-end placement.")
                character.db.tutorial_bridge_position = 0
                return
            if source_location == eexit[0]:
                character.db.tutorial_bridge_position = 4
            else:
                character.db.tutorial_bridge_position = 0

    def at_object_leave(self, character, target_location):
        """
        This is triggered when the player leaves the bridge room.
        """
        if character.has_player:
            # clean up the position attribute
            del character.db.tutorial_bridge_position


#-----------------------------------------------------------
#
# Intro Room - unique room
#
# This room marks the start of the tutorial. It sets up properties on the player char
# that is needed for the tutorial.
#
#------------------------------------------------------------

class IntroRoom(TutorialRoom):
    """
    Intro room

    properties to customize:
     char_health - integer > 0 (default 20)
    """

    def at_object_receive(self, character, source_location):
        """
        Assign properties on characters
        """

        # setup
        health = self.db.char_health
        if not health:
            health = 20

        if character.has_player:
            character.db.health = health
            character.db.health_max = health

        if character.is_superuser:
            string = "-"*78
            string += "\nWARNING: YOU ARE PLAYING AS A SUPERUSER (%s). TO EXPLORE NORMALLY YOU NEED " % character.key
            string += "\nTO CREATE AND LOG IN AS A REGULAR USER INSTEAD. IF YOU CONTINUE, KNOW THAT "
            string += "\nMANY FUNCTIONS AND PUZZLES WILL IGNORE THE PRESENCE OF A SUPERUSER.\n"
            string += "-"*78
            character.msg("{r%s{n" % string)

#------------------------------------------------------------
#
# Outro room - unique room
#
# Cleans up the character from all tutorial-related properties.
#
#------------------------------------------------------------

class OutroRoom(TutorialRoom):
    """
    Outro room.

    One can set an attribute list "wracklist" with weapon-rack ids
        in order to clear all weapon rack ids from the character.

    """

    def at_object_receive(self, character, source_location):
        """
        Do cleanup.
        """
        if character.has_player:
            if self.db.wracklist:
                for wrackid in self.db.wracklist:
                    character.del_attribute(wrackid)
            del character.db.health_max
            del character.db.health
            del character.db.last_climbed
            del character.db.puzzle_clue
            del character.db.combat_parry_mode
            del character.db.tutorial_bridge_position
            for tut_obj in [obj for obj in character.contents if utils.inherits_from(obj, TutorialObject)]:
                tut_obj.reset()
