"""

Room Typeclasses for the TutorialWorld.

This defines special types of Rooms available in the tutorial. To keep
everything in one place we define them together with the custom
commands needed to control them. Those commands could also have been
in a separate module (e.g. if they could have been re-used elsewhere.)

"""


import random

# the system error-handling module is defined in the settings. We load the
# given setting here using utils.object_from_module. This way we can use
# it regardless of if we change settings later.
from django.conf import settings

from evennia import (
    TICKER_HANDLER,
    CmdSet,
    Command,
    DefaultExit,
    DefaultRoom,
    create_object,
    default_cmds,
    search_object,
    syscmdkeys,
    utils,
)

from .objects import LightSource

_SEARCH_AT_RESULT = utils.object_from_module(settings.SEARCH_AT_RESULT)

# -------------------------------------------------------------
#
# Tutorial room - parent room class
#
# This room is the parent of all rooms in the tutorial.
# It defines a tutorial command on itself (available to
# all those who are in a tutorial room).
#
# -------------------------------------------------------------

#
# Special command available in all tutorial rooms


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
            target = self.obj  # this is the room the command is defined on
        else:
            target = caller.search(self.args.strip())
            if not target:
                return
        helptext = target.db.tutorial_info or ""

        if helptext:
            helptext = f" |G{helptext}|n"
        else:
            helptext = " |RSorry, there is no tutorial help available here.|n"
        helptext += "\n\n (Write 'give up' if you want to abandon your quest.)"
        caller.msg(helptext)


# for the @detail command we inherit from MuxCommand, since
# we want to make use of MuxCommand's pre-parsing of '=' in the
# argument.
class CmdTutorialSetDetail(default_cmds.MuxCommand):
    """
    sets a detail on a room

    Usage:
        @detail <key> = <description>
        @detail <key>;<alias>;... = description

    Example:
        @detail walls = The walls are covered in ...
        @detail castle;ruin;tower = The distant ruin ...

    This sets a "detail" on the object this command is defined on
    (TutorialRoom for this tutorial). This detail can be accessed with
    the TutorialRoomLook command sitting on TutorialRoom objects (details
    are set as a simple dictionary on the room). This is a Builder command.

    We custom parse the key for the ;-separator in order to create
    multiple aliases to the detail all at once.
    """

    key = "@detail"
    locks = "cmd:perm(Builder)"
    help_category = "TutorialWorld"

    def func(self):
        """
        All this does is to check if the object has
        the set_detail method and uses it.
        """
        if not self.args or not self.rhs:
            self.caller.msg("Usage: @detail key = description")
            return
        if not hasattr(self.obj, "set_detail"):
            self.caller.msg("Details cannot be set on %s." % self.obj)
            return
        for key in self.lhs.split(";"):
            # loop over all aliases, if any (if not, this will just be
            # the one key to loop over)
            self.obj.set_detail(key, self.rhs)
        self.caller.msg("Detail set: '%s': '%s'" % (self.lhs, self.rhs))


class CmdTutorialLook(default_cmds.CmdLook):
    """
    looks at the room and on details

    Usage:
        look <obj>
        look <room detail>
        look *<account>

    Observes your location, details at your location or objects
    in your vicinity.

    Tutorial: This is a child of the default Look command, that also
    allows us to look at "details" in the room.  These details are
    things to examine and offers some extra description without
    actually having to be actual database objects. It uses the
    return_detail() hook on TutorialRooms for this.
    """

    # we don't need to specify key/locks etc, this is already
    # set by the parent.
    help_category = "TutorialWorld"

    def func(self):
        """
        Handle the looking. This is a copy of the default look
        code except for adding in the details.
        """
        caller = self.caller
        args = self.args
        if args:
            # we use quiet=True to turn off automatic error reporting.
            # This tells search that we want to handle error messages
            # ourself. This also means the search function will always
            # return a list (with 0, 1 or more elements) rather than
            # result/None.
            looking_at_obj = caller.search(
                args,
                # note: excludes room/room aliases
                candidates=caller.location.contents + caller.contents,
                use_nicks=True,
                quiet=True,
            )
            if len(looking_at_obj) != 1:
                # no target found or more than one target found (multimatch)
                # look for a detail that may match
                detail = self.obj.return_detail(args)
                if detail:
                    self.caller.msg(detail)
                    return
                else:
                    # no detail found, delegate our result to the normal
                    # error message handler.
                    _SEARCH_AT_RESULT(looking_at_obj, caller, args)
                    return
            else:
                # we found a match, extract it from the list and carry on
                # normally with the look handling.
                looking_at_obj = looking_at_obj[0]

        else:
            looking_at_obj = caller.location
            if not looking_at_obj:
                caller.msg("You have no location to look at!")
                return

        if not hasattr(looking_at_obj, "return_appearance"):
            # this is likely due to us having an account instead
            looking_at_obj = looking_at_obj.character
        if not looking_at_obj.access(caller, "view"):
            caller.msg("Could not find '%s'." % args)
            return
        # get object's appearance
        caller.msg(looking_at_obj.return_appearance(caller))
        # the object's at_desc() method.
        looking_at_obj.at_desc(looker=caller)
        return


class CmdTutorialGiveUp(default_cmds.MuxCommand):
    """
    Give up the tutorial-world quest and return to Limbo, the start room of the
    server.

    """

    key = "give up"
    aliases = ["abort"]

    def func(self):
        outro_room = OutroRoom.objects.all()
        if outro_room:
            outro_room = outro_room[0]
        else:
            self.caller.msg(
                "That didn't work (seems like a bug). "
                "Try to use the |wteleport|n command instead."
            )
            return

        self.caller.move_to(outro_room, move_type="teleport")


class TutorialRoomCmdSet(CmdSet):
    """
    Implements the simple tutorial cmdset. This will overload the look
    command in the default CharacterCmdSet since it has a higher
    priority (ChracterCmdSet has prio 0)
    """

    key = "tutorial_cmdset"
    priority = 1

    def at_cmdset_creation(self):
        """add the tutorial-room commands"""
        self.add(CmdTutorial())
        self.add(CmdTutorialSetDetail())
        self.add(CmdTutorialLook())
        self.add(CmdTutorialGiveUp())


class TutorialRoom(DefaultRoom):
    """
    This is the base room type for all rooms in the tutorial world.
    It defines a cmdset on itself for reading tutorial info about the location.
    """

    def at_object_creation(self):
        """Called when room is first created"""
        self.db.tutorial_info = (
            "This is a tutorial room. It allows you to use the 'tutorial' command."
        )
        self.cmdset.add_default(TutorialRoomCmdSet)

    def at_object_receive(self, new_arrival, source_location, move_type="move", **kwargs):
        """
        When an object enter a tutorial room we tell other objects in
        the room about it by trying to call a hook on them. The Mob object
        uses this to cheaply get notified of enemies without having
        to constantly scan for them.

        Args:
            new_arrival (Object): the object that just entered this room.
            source_location (Object): the previous location of new_arrival.

        """
        if new_arrival.has_account and not new_arrival.is_superuser:
            # this is a character
            for obj in self.contents_get(exclude=new_arrival):
                if hasattr(obj, "at_new_arrival"):
                    obj.at_new_arrival(new_arrival)

    def return_detail(self, detailkey):
        """
        This looks for an Attribute "obj_details" and possibly
        returns the value of it.

        Args:
            detailkey (str): The detail being looked at. This is
                case-insensitive.

        """
        details = self.db.details
        if details:
            return details.get(detailkey.lower(), None)

    def set_detail(self, detailkey, description):
        """
        This sets a new detail, using an Attribute "details".

        Args:
            detailkey (str): The detail identifier to add (for
                aliases you need to add multiple keys to the
                same description). Case-insensitive.
            description (str): The text to return when looking
                at the given detailkey.

        """
        if self.db.details:
            self.db.details[detailkey.lower()] = description
        else:
            self.db.details = {detailkey.lower(): description}


class TutorialStartExit(DefaultExit):
    """
    This is like a normal exit except it makes the `intro` command available
    on itself. We put it on the exit in order to provide this command to the
    Limbo room without modifying Limbo itself - deleting the tutorial exit
    will also  clean up the intro command.

    """

    def at_object_creation(self):
        self.cmdset.add(CmdSetEvenniaIntro, persistent=True)


# -------------------------------------------------------------
#
# Weather room - room with a ticker
#
# -------------------------------------------------------------

# These are rainy weather strings
WEATHER_STRINGS = (
    "The rain coming down from the iron-grey sky intensifies.",
    "A gust of wind throws the rain right in your face. Despite your cloak you shiver.",
    "The rainfall eases a bit and the sky momentarily brightens.",
    "For a moment it looks like the rain is slowing, then it begins anew with renewed force.",
    "The rain pummels you with large, heavy drops. You hear the rumble of thunder in the distance.",
    "The wind is picking up, howling around you, throwing water droplets in your face. It's cold.",
    "Bright fingers of lightning flash over the sky, moments later followed by a deafening rumble.",
    "It rains so hard you can hardly see your hand in front of you. You'll soon be drenched to the bone.",
    "Lightning strikes in several thundering bolts, striking the trees in the forest to your west.",
    "You hear the distant howl of what sounds like some sort of dog or wolf.",
    "Large clouds rush across the sky, throwing their load of rain over the world.",
)


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
        the ticking of the room; the TickerHandler works fine for
        simple things like this though.
        """
        super().at_object_creation()
        # subscribe ourselves to a ticker to repeatedly call the hook
        # "update_weather" on this object. The interval is randomized
        # so as to not have all weather rooms update at the same time.
        self.db.interval = random.randint(50, 70)
        TICKER_HANDLER.add(
            interval=self.db.interval, callback=self.update_weather, idstring="tutorial"
        )
        # this is parsed by the 'tutorial' command on TutorialRooms.
        self.db.tutorial_info = "This room has a Script running that has it echo a weather-related message at irregular intervals."

    def update_weather(self, *args, **kwargs):
        """
        Called by the tickerhandler at regular intervals. Even so, we
        only update 20% of the time, picking a random weather message
        when we do. The tickerhandler requires that this hook accepts
        any arguments and keyword arguments (hence the *args, **kwargs
        even though we don't actually use them in this example)
        """
        if random.random() < 0.2:
            # only update 20 % of the time
            self.msg_contents("|w%s|n" % random.choice(WEATHER_STRINGS))


SUPERUSER_WARNING = (
    "\nWARNING: You are playing as a superuser ({name}). Use the {quell} command to\n"
    "play without superuser privileges (many functions and puzzles ignore the \n"
    "presence of a superuser, making this mode useful for exploring things behind \n"
    "the scenes later).\n"
)

# ------------------------------------------------------------
#
# Intro Room - unique room
#
# This room marks the start of the tutorial. It sets up properties on
# the player char that is needed for the tutorial.
#
# -------------------------------------------------------------


class CmdEvenniaIntro(Command):
    """
    Start the Evennia intro wizard.

    Usage:
        intro

    """

    key = "intro"

    def func(self):
        from .intro_menu import init_menu

        # quell also superusers
        if self.caller.account:
            self.caller.msg("Auto-quelling permissions while in intro ...")
            self.caller.account.execute_cmd("quell")
        init_menu(self.caller)


class CmdSetEvenniaIntro(CmdSet):
    key = "Evennia Intro StartSet"

    def at_cmdset_creation(self):
        self.add(CmdEvenniaIntro())


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
        super().at_object_creation()
        self.db.tutorial_info = (
            "The first room of the tutorial. "
            "This assigns the health Attribute to "
            "the account."
        )

    def at_object_receive(self, character, source_location, move_type="move", **kwargs):
        """
        Assign properties on characters
        """

        # setup character for the tutorial
        health = self.db.char_health or 20

        if character.has_account:
            character.db.health = health
            character.db.health_max = health

        if character.is_superuser:
            string = "-" * 78 + SUPERUSER_WARNING + "-" * 78
            character.msg("|r%s|n" % string.format(name=character.key, quell="|wquell|r"))
        else:
            # quell user
            if character.account:
                character.account.execute_cmd("quell")
                character.msg("(Auto-quelling while in tutorial-world)")


# -------------------------------------------------------------
#
# Bridge - unique room
#
# Defines a special west-eastward "bridge"-room, a large room that takes
# several steps to cross. It is complete with custom commands and a
# chance of falling off the bridge. This room has no regular exits,
# instead the exitings are handled by custom commands set on the account
# upon first entering the room.
#
# Since one can enter the bridge room from both ends, it is
# divided into five steps:
#       westroom <- 0 1 2 3 4 -> eastroom
#
# -------------------------------------------------------------


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
       The room must also have the following Attributes
           - tutorial_bridge_posistion: the current position on
             on the bridge, 0 - 4.

    """

    key = "east"
    aliases = ["e"]
    locks = "cmd:all()"
    help_category = "TutorialWorld"

    def func(self):
        """move one step eastwards"""
        caller = self.caller

        bridge_step = min(5, caller.db.tutorial_bridge_position + 1)

        if bridge_step > 4:
            # we have reached the far east end of the bridge.
            # Move to the east room.
            eexit = search_object(self.obj.db.east_exit)
            if eexit:
                caller.move_to(eexit[0], move_type="traverse")
            else:
                caller.msg("No east exit was found for this room. Contact an admin.")
            return
        caller.db.tutorial_bridge_position = bridge_step
        # since we are really in one room, we have to notify others
        # in the room when we move.
        caller.location.msg_contents(
            "%s steps eastwards across the bridge." % caller.name, exclude=caller
        )
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
        """move one step westwards"""
        caller = self.caller

        bridge_step = max(-1, caller.db.tutorial_bridge_position - 1)

        if bridge_step < 0:
            # we have reached the far west end of the bridge.
            # Move to the west room.
            wexit = search_object(self.obj.db.west_exit)
            if wexit:
                caller.move_to(wexit[0], move_type="traverse")
            else:
                caller.msg("No west exit was found for this room. Contact an admin.")
            return
        caller.db.tutorial_bridge_position = bridge_step
        # since we are really in one room, we have to notify others
        # in the room when we move.
        caller.location.msg_contents(
            "%s steps westwards across the bridge." % caller.name, exclude=caller
        )
        caller.execute_cmd("look")


BRIDGE_POS_MESSAGES = (
    "You are standing |wvery close to the the bridge's western foundation|n."
    " If you go west you will be back on solid ground ...",
    "The bridge slopes precariously where it extends eastwards"
    " towards the lowest point - the center point of the hang bridge.",
    "You are |whalfways|n out on the unstable bridge.",
    "The bridge slopes precariously where it extends westwards"
    " towards the lowest point - the center point of the hang bridge.",
    "You are standing |wvery close to the bridge's eastern foundation|n."
    " If you go east you will be back on solid ground ...",
)
BRIDGE_MOODS = (
    "The bridge sways in the wind.",
    "The hanging bridge creaks dangerously.",
    "You clasp the ropes firmly as the bridge sways and creaks under you.",
    "From the castle you hear a distant howling sound, like that of a large dog or other beast.",
    "The bridge creaks under your feet. Those planks does not seem very sturdy.",
    "Far below you the ocean roars and throws its waves against the cliff,"
    " as if trying its best to reach you.",
    "Parts of the bridge come loose behind you, falling into the chasm far below!",
    "A gust of wind causes the bridge to sway precariously.",
    "Under your feet a plank comes loose, tumbling down. For a moment you dangle over the abyss ...",
    "The section of rope you hold onto crumble in your hands,"
    " parts of it breaking apart. You sway trying to regain balance.",
)

FALL_MESSAGE = (
    "Suddenly the plank you stand on gives way under your feet! You fall!"
    "\nYou try to grab hold of an adjoining plank, but all you manage to do is to "
    "divert your fall westwards, towards the cliff face. This is going to hurt ... "
    "\n ... The world goes dark ...\n\n"
)


class CmdLookBridge(Command):
    """
    looks around at the bridge.

    Tutorial info:
        This command assumes that the room has an Attribute
        "fall_exit", a unique name or dbref to the place they end upp
        if they fall off the bridge.
    """

    key = "look"
    aliases = ["l"]
    locks = "cmd:all()"
    help_category = "TutorialWorld"

    def func(self):
        """Looking around, including a chance to fall."""
        caller = self.caller
        bridge_position = self.caller.db.tutorial_bridge_position
        # this command is defined on the room, so we get it through self.obj
        location = self.obj
        # randomize the look-echo
        message = "|c%s|n\n%s\n%s" % (
            location.key,
            BRIDGE_POS_MESSAGES[bridge_position],
            random.choice(BRIDGE_MOODS),
        )

        chars = [obj for obj in self.obj.contents_get(exclude=caller) if obj.has_account]
        if chars:
            # we create the You see: message manually here
            message += "\n You see: %s" % ", ".join("|c%s|n" % char.key for char in chars)
        self.caller.msg(message)

        # there is a chance that we fall if we are on the western or central
        # part of the bridge.
        if bridge_position < 3 and random.random() < 0.05 and not self.caller.is_superuser:
            # we fall 5% of time.
            fall_exit = search_object(self.obj.db.fall_exit)
            if fall_exit:
                self.caller.msg("|r%s|n" % FALL_MESSAGE)
                self.caller.move_to(fall_exit[0], quiet=True, move_type="fall")
                # inform others on the bridge
                self.obj.msg_contents(
                    "A plank gives way under %s's feet and "
                    "they fall from the bridge!" % self.caller.key
                )


# custom help command
class CmdBridgeHelp(Command):
    """
    Overwritten help command while on the bridge.
    """

    key = "help"
    aliases = ["h", "?"]
    locks = "cmd:all()"
    help_category = "Tutorial world"

    def func(self):
        """Implements the command."""
        string = (
            "You are trying hard not to fall off the bridge ..."
            "\n\nWhat you can do is trying to cross the bridge |weast|n"
            " or try to get back to the mainland |wwest|n)."
        )
        self.caller.msg(string)


class BridgeCmdSet(CmdSet):
    """This groups the bridge commands. We will store it on the room."""

    key = "Bridge commands"
    priority = 2  # this gives it precedence over the normal look/help commands.

    def at_cmdset_creation(self):
        """Called at first cmdset creation"""
        self.add(CmdTutorial())
        self.add(CmdEast())
        self.add(CmdWest())
        self.add(CmdLookBridge())
        self.add(CmdBridgeHelp())


BRIDGE_WEATHER = (
    "The rain intensifies, making the planks of the bridge even more slippery.",
    "A gust of wind throws the rain right in your face.",
    "The rainfall eases a bit and the sky momentarily brightens.",
    "The bridge shakes under the thunder of a closeby thunder strike.",
    "The rain pummels you with large, heavy drops. You hear the distinct howl of a large hound in the distance.",
    "The wind is picking up, howling around you and causing the bridge to sway from side to side.",
    "Some sort of large bird sweeps by overhead, giving off an eery screech. Soon it has disappeared in the gloom.",
    "The bridge sways from side to side in the wind.",
    "Below you a particularly large wave crashes into the rocks.",
    "From the ruin you hear a distant, otherwordly howl. Or maybe it was just the wind.",
)


class BridgeRoom(WeatherRoom):
    """
    The bridge room implements an unsafe bridge. It also enters the player into
    a state where they get new commands so as to try to cross the bridge.

     We want this to result in the account getting a special set of
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
        """Setups the room"""
        # this will start the weather room's ticker and tell
        # it to call update_weather regularly.
        super().at_object_creation()
        # this identifies the exits from the room (should be the command
        # needed to leave through that exit). These are defaults, but you
        # could of course also change them after the room has been created.
        self.db.west_exit = "cliff"
        self.db.east_exit = "gate"
        self.db.fall_exit = "cliffledge"
        # add the cmdset on the room.
        self.cmdset.add(BridgeCmdSet, persistent=True)
        # since the default Character's at_look() will access the room's
        # return_description (this skips the cmdset) when
        # first entering it, we need to explicitly turn off the room
        # as a normal view target - once inside, our own look will
        # handle all return messages.
        self.locks.add("view:false()")

    def update_weather(self, *args, **kwargs):
        """
        This is called at irregular intervals and makes the passage
        over the bridge a little more interesting.
        """
        if random.random() < 80:
            # send a message most of the time
            self.msg_contents("|w%s|n" % random.choice(BRIDGE_WEATHER))

    def at_object_receive(self, character, source_location, move_type="move", **kwargs):
        """
        This hook is called by the engine whenever the player is moved
        into this room.
        """
        if character.has_account:
            # we only run this if the entered object is indeed a player object.
            # check so our east/west exits are correctly defined.
            wexit = search_object(self.db.west_exit)
            eexit = search_object(self.db.east_exit)
            fexit = search_object(self.db.fall_exit)
            if not (wexit and eexit and fexit):
                character.msg(
                    "The bridge's exits are not properly configured. "
                    "Contact an admin. Forcing west-end placement."
                )
                character.db.tutorial_bridge_position = 0
                return
            if source_location == eexit[0]:
                # we assume we enter from the same room we will exit to
                character.db.tutorial_bridge_position = 4
            else:
                # if not from the east, then from the west!
                character.db.tutorial_bridge_position = 0
            character.execute_cmd("look")

    def at_object_leave(self, character, target_location, move_type="move", **kwargs):
        """
        This is triggered when the player leaves the bridge room.
        """
        if character.has_account:
            # clean up the position attribute
            del character.db.tutorial_bridge_position


# -------------------------------------------------------------------------------
#
# Dark Room - a room with states
#
# This room limits the movemenets of its denizens unless they carry an active
# LightSource object (LightSource is defined in
#                     tutorialworld.objects.LightSource)
#
# -------------------------------------------------------------------------------


DARK_MESSAGES = (
    "It is pitch black. You are likely to be eaten by a grue.",
    "It's pitch black. You fumble around but cannot find anything.",
    "You don't see a thing. You feel around, managing to bump your fingers hard against something. Ouch!",
    "You don't see a thing! Blindly grasping the air around you, you find nothing.",
    "It's totally dark here. You almost stumble over some un-evenness in the ground.",
    "You are completely blind. For a moment you think you hear someone breathing nearby ... "
    "\n ... surely you must be mistaken.",
    "Blind, you think you find some sort of object on the ground, but it turns out to be just a stone.",
    "Blind, you bump into a wall. The wall seems to be covered with some sort of vegetation,"
    " but its too damp to burn.",
    "You can't see anything, but the air is damp. It feels like you are far underground.",
)

ALREADY_LIGHTSOURCE = (
    "You don't want to stumble around in blindness anymore. You already "
    "found what you need. Let's get light already!"
)

FOUND_LIGHTSOURCE = (
    "Your fingers bump against a splinter of wood in a corner."
    " It smells of resin and seems dry enough to burn! "
    "You pick it up, holding it firmly. Now you just need to"
    " |wlight|n it using the flint and steel you carry with you."
)


class CmdLookDark(Command):
    """
    Look around in darkness

    Usage:
      look

    Look around in the darkness, trying
    to find something.
    """

    key = "look"
    aliases = ["l", "feel", "search", "feel around", "fiddle"]
    locks = "cmd:all()"
    help_category = "TutorialWorld"

    def func(self):
        """
        Implement the command.

        This works both as a look and a search command; there is a
        random chance of eventually finding a light source.
        """
        caller = self.caller

        # count how many searches we've done
        nr_searches = caller.ndb.dark_searches
        if nr_searches is None:
            nr_searches = 0
            caller.ndb.dark_searches = nr_searches

        if nr_searches < 4 and random.random() < 0.90:
            # we don't find anything
            caller.msg(random.choice(DARK_MESSAGES))
            caller.ndb.dark_searches += 1
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
        string = (
            "Can't help you until you find some light! Try looking/feeling around for something to burn. "
            "You shouldn't give up even if you don't find anything right away."
        )
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
        """Implements the command."""
        self.caller.msg(
            "Until you find some light, there's not much you can do. "
            "Try feeling around, maybe you'll find something helpful!"
        )


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
    priority = 2

    def at_cmdset_creation(self):
        """populate the cmdset."""
        self.add(CmdTutorial())
        self.add(CmdLookDark())
        self.add(CmdDarkHelp())
        self.add(CmdDarkNoMatch())
        self.add(default_cmds.CmdSay())
        self.add(default_cmds.CmdQuit())
        self.add(default_cmds.CmdHome())


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
        super().at_object_creation()
        self.db.tutorial_info = "This is a room with custom command sets on itself."
        # the room starts dark.
        self.db.is_lit = False
        self.cmdset.add(DarkCmdSet, persistent=True)

    def at_init(self):
        """
        Called when room is first recached (such as after a reload)
        """
        self.check_light_state()

    def _carries_light(self, obj):
        """
        Checks if the given object carries anything that gives light.

        Note that we do NOT look for a specific LightSource typeclass,
        but for the Attribute is_giving_light - this makes it easy to
        later add other types of light-giving items. We also accept
        if there is a light-giving object in the room overall (like if
        a splinter was dropped in the room)
        """
        return (
            obj.is_superuser
            or obj.db.is_giving_light
            or any(o for o in obj.contents if o.db.is_giving_light)
        )

    def _heal(self, character):
        """
        Heal a character.
        """
        health = character.db.health_max or 20
        character.db.health = health

    def check_light_state(self, exclude=None):
        """
        This method checks if there are any light sources in the room.
        If there isn't it makes sure to add the dark cmdset to all
        characters in the room. It is called whenever characters enter
        the room and also by the Light sources when they turn on.

        Args:
            exclude (Object): An object to not include in the light check.
        """
        if any(self._carries_light(obj) for obj in self.contents if obj != exclude):
            self.locks.add("view:all()")
            self.cmdset.remove(DarkCmdSet)
            self.db.is_lit = True
            for char in (obj for obj in self.contents if obj.has_account):
                # this won't do anything if it is already removed
                char.msg("The room is lit up.")
        else:
            # noone is carrying light - darken the room
            self.db.is_lit = False
            self.locks.add("view:false()")
            self.cmdset.add(DarkCmdSet, persistent=True)
            for char in (obj for obj in self.contents if obj.has_account):
                if char.is_superuser:
                    char.msg("You are Superuser, so you are not affected by the dark state.")
                else:
                    # put players in darkness
                    char.msg("The room is completely dark.")

    def at_object_receive(self, obj, source_location, move_type="move", **kwargs):
        """
        Called when an object enters the room.
        """
        if obj.has_account:
            # a puppeted object, that is, a Character
            self._heal(obj)
            # in case the new guy carries light with them
            self.check_light_state()

    def at_object_leave(self, obj, target_location, move_type="move", **kwargs):
        """
        In case people leave with the light, we make sure to clear the
        DarkCmdSet if necessary.  This also works if they are
        teleported away.
        """
        # since this hook is called while the object is still in the room,
        # we exclude it from the light check, to ignore any light sources
        # it may be carrying.
        self.check_light_state(exclude=obj)


# -------------------------------------------------------------
#
# Teleport room - puzzles solution
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
# -------------------------------------------------------------


class TeleportRoom(TutorialRoom):
    """
    Teleporter - puzzle room.

    Important attributes (set at creation):
      puzzle_key    - which attr to look for on character
      puzzle_value  - what char.db.puzzle_key must be set to
      success_teleport_to -  where to teleport in case if success
      success_teleport_msg - message to echo while teleporting to success
      failure_teleport_to - where to teleport to in case of failure
      failure_teleport_msg - message to echo while teleporting to failure

    """

    def at_object_creation(self):
        """Called at first creation"""
        super().at_object_creation()
        # what character.db.puzzle_clue must be set to, to avoid teleportation.
        self.db.puzzle_value = 1
        # target of successful teleportation. Can be a dbref or a
        # unique room name.
        self.db.success_teleport_msg = "You are successful!"
        self.db.success_teleport_to = "treasure room"
        # the target of the failure teleportation.
        self.db.failure_teleport_msg = "You fail!"
        self.db.failure_teleport_to = "dark cell"

    def at_object_receive(self, character, source_location, move_type="move", **kwargs):
        """
        This hook is called by the engine whenever the player is moved into
        this room.
        """
        if not character.has_account:
            # only act on player characters.
            return
        # determine if the puzzle is a success or not
        is_success = str(character.db.puzzle_clue) == str(self.db.puzzle_value)
        teleport_to = self.db.success_teleport_to if is_success else self.db.failure_teleport_to
        # note that this returns a list
        results = search_object(teleport_to)
        if not results or len(results) > 1:
            # we cannot move anywhere since no valid target was found.
            character.msg("no valid teleport target for %s was found." % teleport_to)
            return
        if character.is_superuser:
            # superusers don't get teleported
            character.msg("Superuser block: You would have been teleported to %s." % results[0])
            return
        # perform the teleport
        if is_success:
            character.msg(self.db.success_teleport_msg)
        else:
            character.msg(self.db.failure_teleport_msg)
        # teleport quietly to the new place
        character.move_to(results[0], quiet=True, move_hooks=False, move_type="teleport")
        # we have to call this manually since we turn off move_hooks
        # - this is necessary to make the target dark room aware of an
        # already carried light.
        results[0].at_object_receive(character, self)


# -------------------------------------------------------------
#
# Outro room - unique exit room
#
# Cleans up the character from all tutorial-related properties.
#
# -------------------------------------------------------------


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
        super().at_object_creation()
        self.db.tutorial_info = (
            "The last room of the tutorial. "
            "This cleans up all temporary Attributes "
            "the tutorial may have assigned to the "
            "character."
        )

    def at_object_receive(self, character, source_location, move_type="move", **kwargs):
        """
        Do cleanup.
        """
        if character.has_account:
            del character.db.health_max
            del character.db.health
            del character.db.last_climbed
            del character.db.puzzle_clue
            del character.db.combat_parry_mode
            del character.db.tutorial_bridge_position
            for obj in character.contents:
                if obj.typeclass_path.startswith("evennia.contrib.tutorials.tutorial_world"):
                    obj.delete()
            character.tags.clear(category="tutorial_world")

    def at_object_leave(self, character, destination, move_type="move", **kwargs):
        if character.account:
            character.account.execute_cmd("unquell")
