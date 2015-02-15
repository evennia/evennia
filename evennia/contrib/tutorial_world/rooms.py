"""

Room Typeclasses for the TutorialWorld.

This defines special types of Rooms available in the tutorial. To keep
everything in one place we define them together with custom commands
to control them, those commands could also have been in a separate
module (e.g. if they could have been re-used elsewhere.)

"""

import random
from evennia import TICKER_HANDLER
from evennia import CmdSet, Command, DefaultRoom
from evennia import utils, create_object, search_object
from evennia import syscmdkeys, default_cmds
from evennia.contrib.tutorial_world.objects import LightSource, TutorialObject


#------------------------------------------------------------
#
# Tutorial room - parent room class
#
# This room is the parent of all rooms in the tutorial.
# It defines a tutorial command on itself (available to
# all who is in a tutorial room).
#
#------------------------------------------------------------

#
# Special command avaiable in all tutorial rooms
#

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
        All we do is to scan the current location for an Attribute
        called `tutorial_info` and display that.
        """

        caller = self.caller

        if not self.args:
            target = self.obj # this is the room the command is defined on
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
    """
    Implements the simple tutorial cmdset
    """
    key = "tutorial_cmdset"

    def at_cmdset_creation(self):
        "add the tutorial cmd"
        self.add(CmdTutorial())


class TutorialRoom(DefaultRoom):
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
# Weather room - room with a ticker
#
#------------------------------------------------------------

# These are rainy weather strings
WEATHER_STRINGS = (
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

class WeatherRoom(TutorialRoom):
    """
    This should probably better be called a rainy room...

    This sets up an outdoor room typeclass. At irregular intervals,
    the effects of weather will show in the room. Outdoor rooms should
    inherit from this.

    """
    def at_object_creation(self):
        """
        Called when object is first created.
        We set up a ticker to update this room regularly.

        Note that we could in principle also use a Script to manage
        the ticking of the room, the TickerHandler is works fine for
        simple things like this though.
        """
        super(WeatherRoom, self).at_object_creation()
        # subscribe ourselves to a ticker to repeatedly call the hook
        # "update_weather" on this object. The interval is randomized
        # so as to not have all weather rooms update at the same time.
        interval = random.randint(50, 70)
        TICKER_HANDLER.add(self, interval, idstring="tutorial", hook_key="update_weather")
        # this is parsed by the 'tutorial' command on TutorialRooms.
        self.db.tutorial_info = \
            "This room has a Script running that has it echo a weather-related message at irregular intervals."

    def update_weather(self):
        """
        Called by the tickerhandler at regular intervals. Even so, we
        only update 20% of the time, picking a random weather message
        when we do.
        """
        if random.random() < 0.2:
            # only update 20 % of the time
            self.msg_contents("{w%s{n" % random.choice(WEATHER_STRINGS))


#------------------------------------------------------------------------------
#
# Dark Room - a scripted room
#
# This room limits the movemenets of its denizens unless they carry an active
# LightSource object (LightSource is defined in
#                     tutorialworld.objects.LightSource)
#
#------------------------------------------------------------------------------

DARK_MESSAGES = ("It is pitch black. You are likely to be eaten by a grue."
                 "It's pitch black. You fumble around but cannot find anything.",
                 "You don't see a thing. You feel around, managing to bump your fingers hard against something. Ouch!",
                 "You don't see a thing! Blindly grasping the air around you, you find nothing.",
                 "It's totally dark here. You almost stumble over some un-evenness in the ground.",
                 "You are completely blind. For a moment you think you hear someone breathing nearby ... \n ... surely you must be mistaken.",
                 "Blind, you think you find some sort of object on the ground, but it turns out to be just a stone.",
                 "Blind, you bump into a wall. The wall seems to be covered with some sort of vegetation, but its too damp to burn.",
                 "You can't see anything, but the air is damp. It feels like you are far underground.")

ALREADY_LIGHTSOURCE = "You don't want to stumble around in blindness anymore. You already " \
                      "found what you need. Let's get light already!"

FOUND_LIGHTSOURCE = "Your fingers bump against a splinter of wood in a corner. It smells of resin and seems dry enough to burn! " \
                    "You pick it up, holding it firmly. Now you just need to {wlight{n it using the flint and steel you carry with you."

class CmdLookDark(Command):
    """
    Look around in darkness

    Usage:
      look

    Look around in the darkness, trying
    to find something.
    """
    key = "look"
    aliases = ["l", 'feel', 'search', 'feel around', 'fiddle']
    locks = "cmd:all()"
    help_category = "TutorialWorld"

    def func(self):
        """
        Implement the command.

        This works both as a look and a search command; there is a
        random chance of eventually finding a light source.
        """
        caller = self.caller

        if random.random() < 0.8:
            # we don't find anything
            caller.msg(random.choice(DARK_MESSAGES))
        else:
            # we could have found something!
            if any(obj for obj in caller.contents if utils.inherits_from(obj, LightSource)):
                #  we already carry a LightSource object.
                caller.msg(ALREADY_LIGHTSOURCE)
            else:
                # don't have a light source, create a new one.
                create_object(LightSource, key="splinter", location=caller)
                caller.msg(FOUND_LIGHTSOURCE)


class CmdDarkHelp(Command):
    """
    Help command for the dark state.
    """
    key = "help"
    locks = "cmd:all()"
    help_category = "TutorialWorld"

    def func(self):
        """
        Replace the the help command with a not-so-useful help
        """
        string = "Can't help you until you find some light! Try looking/feeling around for something to burn. " \
                 "You shouldn't give up even if you don't find anything right away."
        self.caller.msg(string)


class CmdDarkNoMatch(Command):
    """
    This is a system command. Commands with special keys are used to
    override special sitations in the game. The CMD_NOMATCH is used
    when the given command is not found in the current command set (it
    replaces Evennia's default behavior or offering command
    suggestions)
    """
    key = syscmdkeys.CMD_NOMATCH
    locks = "cmd:all()"

    def func(self):
        "Implements the command."
        self.caller.msg("Until you find some light, there's not much you can do. Try feeling around.")


class DarkCmdSet(CmdSet):
    """
    Groups the commands of the dark room together.  We also import the
    default say command here so that players can still talk in the
    darkness.

    We give the cmdset the mergetype "Replace" to make sure it
    completely replaces whichever command set it is merged onto
    (usually the default cmdset)
    """
    key = "darkroom_cmdset"
    mergetype = "Replace"

    def at_cmdset_creation(self):
        "populate the cmdset."
        self.add(CmdTutorial())
        self.add(CmdLookDark())
        self.add(CmdDarkHelp())
        self.add(CmdDarkNoMatch())
        self.add(default_cmds.CmdSay)


class DarkRoom(TutorialRoom):
    """
    A dark room. This tries to start the DarkState script on all
    objects entering. The script is responsible for making sure it is
    valid (that is, that there is no light source shining in the room).

    The is_lit Attribute is used to define if the room is currently lit
    or not, so as to properly echo state changes.

    Since this room (in the tutorial) is meant as a sort of catch-all,
    we also make sure to heal characters ending up here, since they
    may have been beaten up by the ghostly apparition at this point.

    """
    def at_object_creation(self):
        """
        Called when object is first created.
        """
        super(DarkRoom, self).at_object_creation()
        self.db.tutorial_info = "This is a room with custom command sets on itself."
        # the room starts dark.
        self.db.is_lit = False

    def _carries_light(self, obj):
        """
        Checks if the given object carries anything that gives light.

        Note that we do NOT look for a specific LightSource typeclass,
        but for the Attribute is_giving_light - this makes it easy to
        later add other types of light-giving items.
        """
        return any(obj for obj in obj.contents if obj.db.is_giving_light)

    def _heal(self, character):
        """
        Heal a character.
        """
        health = character.db.health_max or 20
        character.db.health = health

    def check_light_state(self):
        """
        This method checks if there are any light sources in the room.
        If there isn't it makes sure to add the dark cmdset to all
        characters in the room. It is called whenever characters enter
        the room and also by the Light sources when they turn on.
        """
        if any(self._carries_light(obj) for obj in self.contents):
            # people are carrying lights
            if not self.db.is_lit:
                self.db.is_lit = True
                for char in (obj for obj in self.contents if obj.has_player):
                    # this won't do anything if it is already removed
                    char.cmdset.delete(DarkCmdSet)
                    char.msg("The room is lit up.")
        else:
            # noone is carrying light - darken the room
            for char in (obj for obj in self.contents if obj.has_player):
                if self.db.is_lit:
                    self.db.is_lit = False
                    if char.is_superuser:
                        char.msg("You are Superuser, so you are not affected by the dark state.")
                    else:
                        # put players in darkness
                        char.cmdset.add(DarkCmdSet)
                        char.msg("The room is completely dark.")

    def at_object_receive(self, obj, source_location):
        """
        Called when an object enters the room.
        """
        if obj.has_player:
            # a puppeted object, that is, a Character
            self._heal(obj)
            # in case the new guy carries light with them
            self.check_light_state()

    def at_object_leave(self, obj, target_location):
        """
        In case people leave with the light, we make sure to clear the
        DarkCmdSet if necessary.  This also works if they are
        teleported away.
        """
        obj.cmdset.delete(DarkCmdSet)
        self.check_light_state()

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
        # target of successful teleportation. Can be a dbref or a
        # unique room name.
        self.db.success_teleport_to = "treasure room"
        # the target of the failure teleportation.
        self.db.failure_teleport_to = "dark cell"

    def at_object_receive(self, character, source_location):
        """
        This hook is called by the engine whenever the player is moved into
        this room.
        """
        if not character.has_player:
            # only act on player characters.
            return
        #print character.db.puzzle_clue, self.db.puzzle_value
        if character.db.puzzle_clue != self.db.puzzle_value:
            # we didn't pass the puzzle. See if we can teleport.
            teleport_to = self.db.failure_teleport_to  # this is a room name
        else:
            # passed the puzzle
            teleport_to = self.db.success_teleport_to  # this is a room name

        results = search_object(teleport_to)
        if not results or len(results) > 1:
            # we cannot move anywhere since no valid target was found.
            print "no valid teleport target for %s was found." % teleport_to
            return
        if character.player.is_superuser:
            # superusers don't get teleported
            character.msg("Superuser block: You would have been teleported to %s." % results[0])
            return
        # the teleporter room's desc should give the 'teleporting message'.
        character.execute_cmd("look")
        # teleport quietly to the new place
        character.move_to(results[0], quiet=True)


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
    Go eastwards across the bridge.

    Tutorial info:
        This command relies on the caller having two Attributes
        (assigned by the room when entering):
            - east_exit: a unique name or dbref to the room to go to
              when exiting east.
            - west_exit: a unique name or dbref to the room to go to
              when exiting west.
       The room must also have the following property:
           - tutorial_bridge_posistion: the current position on
             on the bridge, 0 - 4.

    """
    key = "east"
    aliases = ["e"]
    locks = "cmd:all()"
    help_category = "TutorialWorld"

    def func(self):
        "move one step eastwards"
        caller = self.caller

        bridge_step = min(5, caller.db.tutorial_bridge_position + 1)

        if bridge_step > 4:
            # we have reached the far east end of the bridge.
            # Move to the east room.
            eexit = search_object(self.obj.db.east_exit)
            if eexit:
                caller.move_to(eexit[0])
            else:
                caller.msg("No east exit was found for this room. Contact an admin.")
            return
        caller.db.tutorial_bridge_position = bridge_step
        # since we are really in one room, we have to notify others
        # in the room when we move.
        caller.location.msg_contents("%s steps eastwards across the bridge." % caller.name, exclude=caller)
        caller.execute_cmd("look")


# go back across the bridge
class CmdWest(Command):
    """
    Go westwards across the bridge.

    Tutorial info:
       This command relies on the caller having two Attributes
       (assigned by the room when entering):
           - east_exit: a unique name or dbref to the room to go to
             when exiting east.
           - west_exit: a unique name or dbref to the room to go to
             when exiting west.
       The room must also have the following property:
           - tutorial_bridge_posistion: the current position on
             on the bridge, 0 - 4.

    """
    key = "west"
    aliases = ["w"]
    locks = "cmd:all()"
    help_category = "TutorialWorld"

    def func(self):
        "move one step westwards"
        caller = self.caller

        bridge_step = max(-1, caller.db.tutorial_bridge_position - 1)

        if bridge_step < 0:
            # we have reached the far west end of the bridge.
            # Move to the west room.
            wexit = search_object(self.obj.db.west_exit)
            if wexit:
                caller.move_to(wexit[0])
            else:
                caller.msg("No west exit was found for this room. Contact an admin.")
            return
        caller.db.tutorial_bridge_position = bridge_step
        # since we are really in one room, we have to notify others
        # in the room when we move.
        caller.location.msg_contents("%s steps westwards across the bridge." % caller.name, exclude=caller)
        caller.execute_cmd("look")


BRIDGE_POS_MESSAGES = ("You are standing {wvery close to the the bridge's western foundation{n. If you go west you will be back on solid ground ...",
                       "The bridge slopes precariously where it extends eastwards towards the lowest point - the center point of the hang bridge.",
                       "You are {whalfways{n out on the unstable bridge.",
                       "The bridge slopes precariously where it extends westwards towards the lowest point - the center point of the hang bridge.",
                       "You are standing {wvery close to the bridge's eastern foundation{n. If you go east you will be back on solid ground ...")
BRIDGE_MOODS = ("The bridge sways in the wind.", "The hanging bridge creaks dangerously.",
                "You clasp the ropes firmly as the bridge sways and creaks under you.",
                "From the castle you hear a distant howling sound, like that of a large dog or other beast.",
                "The bridge creaks under your feet. Those planks does not seem very sturdy.",
                "Far below you the ocean roars and throws its waves against the cliff, as if trying its best to reach you.",
                "Parts of the bridge come loose behind you, falling into the chasm far below!",
                "A gust of wind causes the bridge to sway precariously.",
                "Under your feet a plank comes loose, tumbling down. For a moment you dangle over the abyss ...",
                "The section of rope you hold onto crumble in your hands, parts of it breaking apart. You sway trying to regain balance.")

FALL_MESSAGE = "Suddenly the plank you stand on gives way under your feet! You fall!" \
               "\nYou try to grab hold of an adjoining plank, but all you manage to do is to " \
               "divert your fall westwards, towards the cliff face. This is going to hurt ... " \
               "\n ... The world goes dark ...\n\n" \

class CmdLookBridge(Command):
    """
    looks around at the bridge.

    Tutorial info:
        This command assumes that the room has an Attribute
        "fall_exit", a unique name or dbref to the place they end upp
        if they fall off the bridge.
    """
    key = 'look'
    aliases = ["l"]
    locks = "cmd:all()"
    help_category = "TutorialWorld"

    def func(self):
        "Looking around, including a chance to fall."
        caller = self.caller
        bridge_position = self.caller.db.tutorial_bridge_position
        # this command is defined on the room, so we get it through self.obj
        location = self.obj
        # randomize the look-echo
        message = "{c%s{n\n%s\n%s" % (location.key,
                                      BRIDGE_POS_MESSAGES[bridge_position],
                                      random.choice(BRIDGE_MOODS))

        chars = [obj for obj in self.obj.get_contents(exclude=caller) if obj.has_player]
        if chars:
            # we create the You see: message manually here
            message += "\n You see: %s" % ", ".join("{c%s{n" % char.key for char in chars)
        self.caller.msg(message)

        # there is a chance that we fall if we are on the western or central
        # part of the bridge.
        if bridge_position < 3 and random.random() < 0.05 and not self.caller.is_superuser:
            # we fall 5% of time.
            fall_exit = search_object(self.obj.db.fall_exit)
            if fall_exit:
                self.caller.msg("{r%s{n" % FALL_MESSAGE)
                self.caller.move_to(fall_exit, quiet=True)
                # inform others on the bridge
                self.obj.msg_contents("A plank gives way under %s's feet and " \
                                      "they fall from the bridge!" % self.caller.key)


# custom help command
class CmdBridgeHelp(Command):
    """
    Overwritten help command while on the bridge.
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
        "Called at first cmdset creation"
        self.add(CmdTutorial())
        self.add(CmdEast())
        self.add(CmdWest())
        self.add(CmdLookBridge())
        self.add(CmdBridgeHelp())

BRIDGE_WEATHER = (
        "The rain intensifies, making the planks of the bridge even more slippery.",
        "A gush of wind throws the rain right in your face.",
        "The rainfall eases a bit and the sky momentarily brightens.",
        "The bridge shakes under the thunder of a closeby thunder strike.",
        "The rain pummels you with large, heavy drops. You hear the distinct howl of a large hound in the distance.",
        "The wind is picking up, howling around you and causing the bridge to sway from side to side.",
        "Some sort of large bird sweeps by overhead, giving off an eery screech. Soon it has disappeared in the gloom.",
        "The bridge sways from side to side in the wind.",
        "Below you a particularly large wave crashes into the rocks.",
        "From the ruin you hear a distant, otherwordly howl. Or maybe it was just the wind.")

class BridgeRoom(WeatherRoom):
    """
    The bridge room implements an unsafe bridge. It also enters the player into
    a state where they get new commands so as to try to cross the bridge.

     We want this to result in the player getting a special set of
     commands related to crossing the bridge. The result is that it
     will take several steps to cross it, despite it being represented
     by only a single room.

     We divide the bridge into steps:

        self.db.west_exit     -   -  |  -   -     self.db.east_exit
                              0   1  2  3   4

     The position is handled by a variable stored on the character
     when entering and giving special move commands will
     increase/decrease the counter until the bridge is crossed.

     We also has self.db.fall_exit, which points to a gathering
     location to end up if we happen to fall off the bridge (used by
     the CmdLookBridge command).

    """
    def at_object_creation(self):
        "Setups the room"
        # this will start the weather room's ticker and tell
        # it to call update_weather regularly.
        super(BridgeRoom, self).at_object_creation()
        # this identifies the exits from the room (should be the command
        # needed to leave through that exit). These are defaults, but you
        # could of course also change them after the room has been created.
        self.db.west_exit = "cliff"
        self.db.east_exit = "gate"
        self.db.fall_exit = "cliffledge"
        # add the cmdset on the room.
        self.cmdset.add_default(BridgeCmdSet)
        # information for those using the tutorial command
        self.db.tutorial_info = \
            "The bridge seems large but is actually only a " \
            "single room that assigns custom west/east commands " \
            "and a counter to determine how far across you are."

    def update_weather(self):
        """
        This is called at irregular intervals and makes the passage
        over the bridge a little more interesting.
        """
        if random.random() < 80:
            # send a message most of the time
            self.msg_contents("{w%s{n" % random.choice(BRIDGE_WEATHER))

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
            if not (wexit and eexit and fexit):
                character.msg("The bridge's exits are not properly configured. "\
                              "Contact an admin. Forcing west-end placement.")
                character.db.tutorial_bridge_position = 0
                return
            if source_location == eexit[0]:
                # we assume we enter from the same room we will exit to
                character.db.tutorial_bridge_position = 4
            else:
                # if not from the east, then from the west!
                character.db.tutorial_bridge_position = 0

    def at_object_leave(self, character, target_location):
        """
        This is triggered when the player leaves the bridge room.
        """
        if character.has_player:
            # clean up the position attribute
            del character.db.tutorial_bridge_position

SUPERUSER_WARNING = "\nWARNING: You are playing as a superuser ({name}). Use the {quell} command to\n" \
                    "play without superuser privileges (many functions and puzzles ignore the \n" \
                    "presence of a superuser, making this mode useful for exploring things behind \n" \
                    "the scenes later).\n" \

#-----------------------------------------------------------
#
# Intro Room - unique room
#
# This room marks the start of the tutorial. It sets up properties on
# the player char that is needed for the tutorial.
#
#------------------------------------------------------------

class IntroRoom(TutorialRoom):
    """
    Intro room

    properties to customize:
     char_health - integer > 0 (default 20)
    """
    def at_object_creation(self):
        """
        Called when the room is first created.
        """
        super(IntroRoom, self).at_object_creation()
        self.db_tutorial_info = "The first room of the tutorial. " \
                                "This assigns the health Attribute to "\
                                "the player."

    def at_object_receive(self, character, source_location):
        """
        Assign properties on characters
        """

        # setup character for the tutorial
        health = self.db.char_health or 20

        if character.has_player:
            character.db.health = health
            character.db.health_max = health

        if character.is_superuser:
            string = "-"*78 + SUPERUSER_WARNING + "-"*78
            character.msg("{r%s{n" % string.format(name=character.key, quell="{w@quell{r"))


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

    Called when exiting the tutorial, cleans the
    character of tutorial-related attributes.

    """

    def at_object_creation(self):
        """
        Called when the room is first created.
        """
        super(IntroRoom, self).at_object_creation()
        self.db_tutorial_info = "The last room of the tutorial. " \
                                "This cleans up all temporary Attributes " \
                                "the tutorial may have assigned to the "\
                                "character."

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
            for tut_obj in [obj for obj in character.contents
                                  if utils.inherits_from(obj, TutorialObject)]:
                tut_obj.reset()
