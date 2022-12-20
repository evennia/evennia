"""
Intro menu / game tutor

Evennia contrib - Griatch 2020

This contrib is an intro-menu for general MUD and evennia usage using the
EvMenu menu-templating system.

EvMenu templating is a way to create a menu using a string-format instead
of creating all nodes manually. Of course, for full functionality one must
still create the goto-callbacks.

"""

from evennia import CmdSet, create_object
from evennia.utils.evmenu import EvMenu, parse_menu_template

# Goto callbacks and helper resources for the menu


def do_nothing(caller, raw_string, **kwargs):
    """
    Re-runs the current node
    """
    return None


def send_testing_tagged(caller, raw_string, **kwargs):
    """
    Test to send a message to a pane tagged with 'testing' in the webclient.

    """
    caller.msg(
        (
            "This is a message tagged with 'testing' and "
            "should appear in the pane you selected!\n "
            f"You wrote: '{raw_string}'",
            {"type": "testing"},
        )
    )
    return None


# Resources for the first help-command demo


class DemoCommandSetHelp(CmdSet):
    """
    Demo the help command
    """

    key = "Help Demo Set"
    priority = 2

    def at_cmdset_creation(self):
        from evennia import default_cmds

        self.add(default_cmds.CmdHelp())
        self.add(default_cmds.CmdChannel())


def goto_command_demo_help(caller, raw_string, **kwargs):
    "Sets things up before going to the help-demo node"
    _maintain_demo_room(caller, delete=True)
    caller.cmdset.remove(DemoCommandSetRoom)
    caller.cmdset.remove(DemoCommandSetComms)
    caller.cmdset.add(DemoCommandSetHelp)  # TODO - make persistent
    return kwargs.get("gotonode") or "command_demo_help"


# Resources for the comms demo


class DemoCommandSetComms(CmdSet):
    """
    Demo communications
    """

    key = "Color Demo Set"
    priority = 2
    no_exits = True
    no_objs = True

    def at_cmdset_creation(self):
        from evennia import default_cmds

        self.add(default_cmds.CmdHelp())
        self.add(default_cmds.CmdSay())
        self.add(default_cmds.CmdPose())
        self.add(default_cmds.CmdPage())
        self.add(default_cmds.CmdColorTest())


def goto_command_demo_comms(caller, raw_string, **kwargs):
    """
    Setup and go to the color demo node.
    """
    caller.cmdset.remove(DemoCommandSetHelp)
    caller.cmdset.remove(DemoCommandSetRoom)
    caller.cmdset.add(DemoCommandSetComms)
    return kwargs.get("gotonode") or "comms_demo_start"


# Resources for the room demo

_ROOM_DESC = """
This is a small and comfortable wood cabin. Bright sunlight is shining in
through the windows.

Use |ylook sign|n or |yl sign|n to examine the wooden sign nailed to the wall.

"""

_SIGN_DESC = """
The small sign reads:

    Good! Now try '|ylook small|n'.

    ... You'll get a multi-match error! There are two things that 'small' could
    refer to here - the 'small wooden sign' or the 'small, cozy cabin' itself.  You will
    get a list of the possibilities.

    You could either tell Evennia which one you wanted by picking a unique part
    of their name (like '|ylook cozy|n') or use the number in the list to pick
    the one you want, like this:

        |ylook small-2|n

    As long as what you write is uniquely identifying you can be lazy and not
    write the full name of the thing you want to look at. Try '|ylook bo|n',
    '|yl co|n' or '|yl sm-1|n'!

    ... Oh, and if you see database-ids like (#1245) by the name of objects,
    it's because you are playing with Builder-privileges or higher. Regular
    players will not see the numbers.

    Next try |ylook door|n.

"""

_DOOR_DESC_OUT = """
This is a solid wooden door leading to the outside of the cabin. Some
text is written on it:

    This is an |wexit|n. An exit is often named by its compass-direction like
    |weast|n, |wwest|n, |wnorthwest|n and so on, but it could be named
    anything, like this door. To use the exit, you just write its name. So by
    writing |ydoor|n you will leave the cabin.

"""

_DOOR_DESC_IN = """
This is a solid wooden door leading to the inside of the cabin. On
are some carved text:

    This exit leads back into the cabin. An exit is just like any object,
    so while has a name, it can also have aliases. To get back inside
    you can both write |ydoor|n but also |yin|n.

"""

_MEADOW_DESC = """
This is a lush meadow, just outside a cozy cabin. It's surrounded
by trees and sunlight filters down from a clear blue sky.

There is a |wstone|n here. Try looking at it!

"""

_STONE_DESC = """
This is a fist-sized stone covered in runes:

    To pick me up, use

    |yget stone|n

    You can see what you carry with the |yinventory|n (|yi|n).

    To drop me again, just write

    |ydrop stone|n

    Use |ynext|n when you are done exploring and want to
    continue with the tutorial.

"""


def _maintain_demo_room(caller, delete=False):
    """
    Handle the creation/cleanup of demo assets. We store them
    on the character and clean them when leaving the menu later.
    """
    # this is a tuple (room, obj)
    roomdata = caller.db.tutorial_world_demo_room_data

    if delete:
        if roomdata:
            # we delete directly for simplicity. We need to delete
            # in specific order to avoid deleting rooms moves
            # its contents to their default home-location
            prev_loc, room1, sign, room2, stone, door_out, door_in = roomdata
            caller.location = prev_loc
            sign.delete()
            stone.delete()
            door_out.delete()
            door_in.delete()
            room1.delete()
            room2.delete()
            del caller.db.tutorial_world_demo_room_data
    elif not roomdata:
        # create and describe the cabin and box
        room1 = create_object("evennia.objects.objects.DefaultRoom", key="A small, cozy cabin")
        room1.db.desc = _ROOM_DESC.lstrip()
        sign = create_object(
            "evennia.objects.objects.DefaultObject", key="small wooden sign", location=room1
        )
        sign.db.desc = _SIGN_DESC.strip()
        sign.locks.add("get:false()")
        sign.db.get_err_msg = "The sign is nailed to the wall. It's not budging."

        # create and describe the meadow and stone
        room2 = create_object("evennia.objects.objects.DefaultRoom", key="A lush summer meadow")
        room2.db.desc = _MEADOW_DESC.lstrip()
        stone = create_object(
            "evennia.objects.objects.DefaultObject", key="carved stone", location=room2
        )
        stone.db.desc = _STONE_DESC.strip()

        # make the linking exits
        door_out = create_object(
            "evennia.objects.objects.DefaultExit",
            key="Door",
            location=room1,
            destination=room2,
            locks=["get:false()"],
        )
        door_out.db.desc = _DOOR_DESC_OUT.strip()
        door_in = create_object(
            "evennia.objects.objects.DefaultExit",
            key="entrance to the cabin",
            aliases=["door", "in", "entrance"],
            location=room2,
            destination=room1,
            locks=["get:false()"],
        )
        door_in.db.desc = _DOOR_DESC_IN.strip()

        # store references for easy removal later
        caller.db.tutorial_world_demo_room_data = (
            caller.location,
            room1,
            sign,
            room2,
            stone,
            door_out,
            door_in,
        )
        # move caller into room
        caller.location = room1


class DemoCommandSetRoom(CmdSet):
    """
    Demo some general in-game commands command.
    """

    key = "Room Demo Set"
    priority = 2
    no_exits = False
    no_objs = False

    def at_cmdset_creation(self):
        from evennia import default_cmds

        self.add(default_cmds.CmdHelp())
        self.add(default_cmds.CmdLook())
        self.add(default_cmds.CmdGet())
        self.add(default_cmds.CmdDrop())
        self.add(default_cmds.CmdInventory())
        self.add(default_cmds.CmdExamine())
        self.add(default_cmds.CmdPy())


def goto_command_demo_room(caller, raw_string, **kwargs):
    """
    Setup and go to the demo-room node. Generates a little 2-room environment
    for testing out some commands.
    """
    _maintain_demo_room(caller)
    caller.cmdset.remove(DemoCommandSetHelp)
    caller.cmdset.remove(DemoCommandSetComms)
    caller.cmdset.add(DemoCommandSetRoom)
    return "command_demo_room"


def goto_cleanup_cmdsets(caller, raw_strings, **kwargs):
    """
    Cleanup all cmdsets.
    """
    caller.cmdset.remove(DemoCommandSetHelp)
    caller.cmdset.remove(DemoCommandSetComms)
    caller.cmdset.remove(DemoCommandSetRoom)
    return kwargs.get("gotonode")


# register all callables that can be used in the menu template

GOTO_CALLABLES = {
    "send_testing_tagged": send_testing_tagged,
    "do_nothing": do_nothing,
    "goto_command_demo_help": goto_command_demo_help,
    "goto_command_demo_comms": goto_command_demo_comms,
    "goto_command_demo_room": goto_command_demo_room,
    "goto_cleanup_cmdsets": goto_cleanup_cmdsets,
}


# Main menu definition

MENU_TEMPLATE = """

## NODE start

|g** Evennia introduction wizard **|n

If you feel lost you can learn some of the basics of how to play a text-based
game here. You can also learn a little about the system and how to find more
help. You can exit this tutorial-wizard at any time by entering '|yq|n' or '|yquit|n'.

Press |y<return>|n or write |ynext|n to step forward. Or select a number to jump to.

## OPTIONS

    1 (next);1;next;n: What is a MUD/MU*? -> about_muds
    2: About Evennia -> about_evennia
    3: Using the webclient -> using webclient
    4: The help command -> goto_command_demo_help()
    5: Communicating with others -> goto_command_demo_help(gotonode='talk on channels')
    6: Using colors -> goto_command_demo_comms(gotonode='testing_colors')
    7: Moving and exploring -> goto_command_demo_room()
    8: Conclusions & next steps-> conclusions
    >: about_muds

# ---------------------------------------------------------------------------------

## NODE about_muds

|g** About MUDs **|n

The term '|wMUD|n' stands for Multi-user-Dungeon or -Dimension. A MUD is
primarily played by inserting text |wcommands|n and getting text back.

MUDS were the |wprecursors|n to graphical MMORPG-style games like World of
Warcraft. While not as mainstream as they once were, comparing a text-game to a
graphical game is like comparing a book to a movie - it's just a different
experience altogether.

MUDs are |wdifferent|n from Interactive Fiction (IF) in that they are multiplayer
and usually have a consistent game world with many stories and protagonists
acting at the same time.

Like there are many different styles of graphical MMOs, there are |wmany
variations|n of MUDs: They can be slow-paced or fast. They can cover fantasy,
sci-fi, horror or other genres. They can allow PvP or not and be casual or
hardcore, strategic, tactical, turn-based or play in real-time.

Whereas 'MUD' is arguably the most well-known term, there are other terms
centered around particular game engines - such as MUSH, MOO, MUX, MUCK, LPMuds,
ROMs, Diku and others. Many people that played MUDs in the past used one of
these existing families of text game-servers, whether they knew it or not.

|cEvennia|n is a newer text game engine designed to emulate almost any existing
gaming style you like and possibly any new ones you can come up with!

## OPTIONS

    next;n: About Evennia -> about_evennia
    back to start;back;start;t: start
    >: about_evennia

# ---------------------------------------------------------------------------------

## NODE about_evennia

|g** About Evennia **|n

|cEvennia|n is a Python game engine for creating multiplayer online text-games
(aka MUDs, MUSHes, MUX, MOOs...). It is open-source and |wfree to use|n, also for
commercial projects (BSD license).

Out of the box, Evennia provides a |wworking, if empty game|n. Whereas you can play
via traditional telnet MUD-clients, the server runs your game's website and
offers a |wHTML5 webclient|n so that people can play your game in their browser
without downloading anything extra.

Evennia deliberately |wdoes not|n hard-code any game-specific things like
combat-systems, races, skills, etc. They would not match what just you wanted
anyway! Whereas we do have optional contribs with many examples, most of our
users use them as inspiration to make their own thing.

Evennia is developed entirely in |wPython|n, using modern developer practices.
The advantage of text is that even a solo developer or small team can
realistically make a competitive multiplayer game (as compared to a graphical
MMORPG which is one of the most expensive game types in existence to develop).
Many also use Evennia as a |wfun way to learn Python|n!

## OPTIONS

    next;n: Using the webclient -> using webclient
    back;b: About MUDs -> about_muds
    >: using webclient

# ---------------------------------------------------------------------------------

## NODE using webclient

|g** Using the Webclient **|n

|RNote: This is only relevant if you use Evennia's HTML5 web client. If you use a
third-party (telnet) mud-client, you can skip this section.|n

Evennia's web client is (for a local install) found by pointing your browser to

    |yhttp://localhost:4001/webclient|n

For a live example, the public Evennia demo can be found at

    |yhttps://demo.evennia.com/webclient|n

The web client starts out having two panes - the input-pane for entering commands
and the main window.

- Use |y<Return>|n (or click the arrow on the right) to send your input.
- Use |yCtrl + <up/down-arrow>|n to step back and forth in your command-history.
- Use |yCtrl + <Return>|n to add a new line to your input without sending.
(Cmd instead of Ctrl-key on Macs)

There is also some |wextra|n info to learn about customizing the webclient.

## OPTIONS

    extra: Customizing the webclient -> customizing the webclient
    next;n: Playing the game -> goto_command_demo_help()
    back;b: About Evennia -> about_evennia
    back to start;start: start
    >: goto_command_demo_help()

# ---------------------------------------------------------------------------------

# this is a dead-end 'leaf' of the menu

## NODE customizing the webclient

|g** Extra hints on customizing the Webclient **|n

|y1)|n The panes of the webclient can be resized and you can create additional panes.

- Press the little  plus (|w+|n) sign in the top left and a new tab will appear.
- Click and drag the tab and pull it far to the right and release when it creates two
  panes next to each other.

|y2)|n You can have certain server output only appear in certain panes.

- In your new rightmost pane, click the diamond (⯁) symbol at the top.
- Unselect everything and make sure to select "testing".
- Click the diamond again so the menu closes.
- Next, write "|ytest Hello world!|n". A test-text should appear in your rightmost pane!

|y3)|n You can customize general webclient settings by pressing the cogwheel in the upper
left corner. It allows to change things like font and if the client should play sound.

The "message routing" allows for rerouting text matching a certain regular expression (regex)
to a web client pane with a specific tag that you set yourself.

|y4)|n Close the right-hand pane with the |wX|n in the rop right corner.

## OPTIONS

    back;b: using webclient
    > test *: send tagged message to new pane -> send_testing_tagged()
    >: using webclient

# ---------------------------------------------------------------------------------

# we get here via goto_command_demo_help()

## NODE command_demo_help

|g** Playing the game **|n

Evennia has about |w90 default commands|n. They include useful administration/building
commands and a few limited "in-game" commands to serve as examples. They are intended
to be changed, extended and modified as you please.

First to try is |yhelp|n. This lists all commands |wcurrently|n available to you.

Use |yhelp <topic>|n to get specific help. Try |yhelp help|n to get help on using
the help command. For your game you could add help about your game, lore, rules etc
as well.

At the moment you probably only have |whelp|n and a |wchannel|n command
(the '<menu commands>' is just a placeholder to indicate you are using this menu).

We'll add more commands as we get to them in this tutorial - but we'll only
cover a small handful. Once you exit you'll find a lot more! Now let's try
those channels ...

## OPTIONS

    next;n: Talk on Channels -> talk on channels
    back;b: Using the webclient -> goto_cleanup_cmdsets(gotonode='using webclient')
    back to start;start: start
    >: talk on channels

# ---------------------------------------------------------------------------------

## NODE talk on channels

|g** Talk on Channels **|n

|wChannels|n are like in-game chatrooms. The |wChannel Names|n help-category
holds the names of the channels available to you right now. One such channel is
|wpublic|n. Use |yhelp public|n to see how to use it. Try it:

    |ypublic Hello World!|n

This will send a message to the |wpublic|n channel where everyone on that
channel can see it. If someone else is on your server, you may get a reply!

Evennia can link its in-game channels to external chat networks. This allows
you to talk with people not actually logged into the game.

## OPTIONS

    next;n: Talk to people in-game -> goto_command_demo_comms()
    back;b: Finding help -> goto_command_demo_help()
    back to start;start: start
    >: goto_command_demo_comms()

# ---------------------------------------------------------------------------------

# we get here via goto_command_demo_comms()

## NODE comms_demo_start

|g** Talk to people in-game **|n

You can also chat with people inside the game. If you try |yhelp|n now you'll
find you have a few more commands available for trying this out.

    |ysay Hello there!|n
    |y'Hello there!|n

|wsay|n is used to talk to people in the same location you are. Everyone in the
room will see what you have to say. A single quote |y'|n is a  convenient shortcut.

    |ypose smiles|n
    |y:smiles|n

|wpose|n (or |wemote|n) describes what you do to those nearby. This is a very simple
command by default, but it can be extended to much more complex parsing in order to
include other people/objects in the emote, reference things by a short-description etc.

## OPTIONS

    next;n: Paging people -> paging_people
    back;b: Talk on Channels -> goto_command_demo_help(gotonode='talk on channels')
    back to start;start: start
    >: paging_people

# ---------------------------------------------------------------------------------

## NODE paging_people

|g** Paging people **|n

Halfway between talking on a |wChannel|n and chatting in your current location
with |wsay|n and |wpose|n, you can also send private messages with |wpage|n:

    |ypage <name> Hello there!|n

Put your own name as |y<name>|n to page yourself as a test. Write just |ypage|n
to see your latest pages. This will also show you if anyone paged you while you
were offline.

## OPTIONS

    next;n: Using colors -> testing_colors
    back;b: Talk to people in-game -> comms_demo_start
    back to start;start: start
    >: testing_colors

# ---------------------------------------------------------------------------------

## NODE testing_colors

|g** U|rs|yi|gn|wg |c|yc|wo|rl|bo|gr|cs |g**|n

You can add color in your text by the help of tags. However, remember that not
everyone will see your colors - it depends on their client (and some use
screenreaders). Using color can also make text harder to read. So use it
sparingly.

To start coloring something |rred|n, add a ||r (red) marker and then
end with ||n (to go back to neutral/no-color):

    |ysay This is a ||rred||n text!
    say This is a ||Rdark red||n text!|n

You can also change the background:

    |ysay This is a ||[x||bblue text on a light-grey background!|n

There are 16 base colors and as many background colors (called ANSI colors). Some
clients also supports so-called Xterm256 which gives a total of 256 colors. These are
given as |w||rgb|n, where r, g, b are the components of red, green and blue from 0-5:

    |ysay This is ||050solid green!|n
    |ysay This is ||520an orange color!|n
    |ysay This is ||[005||555white on bright blue background!|n

If you don't see the expected colors from the above examples, it's because your
client does not support it - try out the Evennia webclient instead. To see all
color codes printed, try

    |ycolor ansi
    |ycolor xterm

## OPTIONS

    next;n: Moving and Exploring -> goto_command_demo_room()
    back;b: Paging people -> goto_command_demo_comms(gotonode='paging_people')
    back to start;start: start
    >: goto_command_demo_room()

# ---------------------------------------------------------------------------------

# we get here via goto_command_demo_room()

## NODE command_demo_room

|gMoving and Exploring|n

For exploring the game, a very important command is '|ylook|n'. It's also
abbreviated '|yl|n' since it's used so much. Looking displays/redisplays your
current location. You can also use it to look closer at items in the world. So
far in this tutorial, using 'look' would just redisplay the menu.

Try |ylook|n now. You have been quietly transported to a sunny cabin to look
around in. Explore a little and use |ynext|n when you are done.

## OPTIONS

    next;n: Conclusions -> conclusions
    back;b: Channel commands -> goto_command_demo_comms(gotonode='testing_colors')
    back to start;start: start
    >: conclusions

# ---------------------------------------------------------------------------------

## NODE conclusions

|gConclusions|n

That concludes this little quick-intro to using the base game commands of
Evennia. With this you should be able to continue exploring and also find help
if you get stuck!

Write |ynext|n to end this wizard. If you want there is also some |wextra|n info
for where to go beyond that.

## OPTIONS

    extra: Where to go next -> post scriptum
    next;next;n: End -> end
    back;b: Moving and Exploring -> goto_command_demo_room()
    back to start;start: start
    >: end

# ---------------------------------------------------------------------------------

## NODE post scriptum

|gWhere to next?|n

After playing through the tutorial-world quest, if you aim to make a game with
Evennia you are wise to take a look at the |wEvennia documentation|n at

    |yhttps://www.evennia.com/docs/latest|n

- You can start by trying to build some stuff by following the |wBuilder quick-start|n:

    |yhttps://www.evennia.com/docs/latest/Building-Quickstart|n

- The tutorial-world may or may not be your cup of tea, but it does show off
  several |wuseful tools|n of Evennia. You may want to check out how it works:

    |yhttps://www.evennia.com/docs/latest/Howtos/Beginner-Tutorial/Part1/Tutorial-World|n

- You can then continue looking through the |wTutorials|n and pick one that
  fits your level of understanding.

    |yhttps://www.evennia.com/docs/latest/Howtos/Howtos-Overview|n

- Make sure to |wjoin our forum|n and connect to our |wsupport chat|n! The
  Evennia community is very active and friendly and no question is too simple.
  You will often quickly get help. You can everything you need linked from

    |yhttps://www.evennia.com|n

# ---------------------------------------------------------------------------------

## OPTIONS

back: conclusions
>: conclusions


## NODE end

|gGood luck!|n

"""


# -------------------------------------------------------------------------------------------
#
# EvMenu implementation and access function
#
# -------------------------------------------------------------------------------------------


class TutorialEvMenu(EvMenu):
    """
    Custom EvMenu for displaying the intro-menu
    """

    def close_menu(self):
        """Custom cleanup actions when closing menu"""
        self.caller.cmdset.remove(DemoCommandSetHelp)
        self.caller.cmdset.remove(DemoCommandSetRoom)
        self.caller.cmdset.remove(DemoCommandSetComms)
        _maintain_demo_room(self.caller, delete=True)
        super().close_menu()
        if self.caller.account:
            self.caller.msg("Restoring permissions ...")
            self.caller.account.execute_cmd("unquell")

    def options_formatter(self, optionslist):

        navigation_keys = ("next", "back", "back to start")

        other = []
        navigation = []
        for key, desc in optionslist:
            if key in navigation_keys:
                desc = f" ({desc})" if desc else ""
                navigation.append(f"|lc{key}|lt|w{key}|n|le{desc}")
            else:
                other.append((key, desc))
        navigation = (
            (" " + " |W|||n ".join(navigation) + " |W|||n " + "|wQ|Wuit|n") if navigation else ""
        )
        other = super().options_formatter(other)
        sep = "\n\n" if navigation and other else ""

        return f"{navigation}{sep}{other}"


def init_menu(caller):
    """
    Call to initialize the menu.

    """
    menutree = parse_menu_template(caller, MENU_TEMPLATE, GOTO_CALLABLES)
    TutorialEvMenu(caller, menutree)
