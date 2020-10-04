"""
Intro menu / game tutor

Evennia contrib - Griatch 2020

This contrib is an intro-menu for general MUD and evennia usage using the
EvMenu menu-templating system.

EvMenu templating is a way to create a menu using a string-format instead
of creating all nodes manually. Of course, for full functionality one must
still create the goto-callbacks.

"""

from evennia import create_object
from evennia import CmdSet
from evennia.utils.evmenu import parse_menu_template, EvMenu

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

Use |ylook box|n or |yl box|n to examine the box in this room.
"""

_BOX_DESC = """
The box is made of wood. On it, letters are engraved, reading:

    Good! Now try '|ylook small|n'.

    You'll get an error! There are two things that 'small' could refer to here
    - the 'small box' or the 'small, cozy cabin' itself.  You will get a list of the
    possibilities.

    You could either tell Evennia which one you wanted by picking a unique part
    of their name (like '|ylook cozy|n') or use the number in the list to pick
    the one you want, like this:

        |ylook 2-small|n

    As long as what you write is uniquely identifying you can be lazy and not
    write the full name of the thing you want to look at. Try '|ylook bo|n',
    '|yl co|n' or '|yl 1-sm|n'!

    ... Oh, and if you see database-ids like (#1245) by the name of objects,
    it's because you are playing with Builder-privileges or higher. Regular
    players will not see the numbers.

    Next look at the |wdoor|n.

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

There is a |wstone|n here. Try looking at it.

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
            prev_loc, room1, box, room2, stone, door_out, door_in = roomdata
            caller.location = prev_loc
            box.delete()
            stone.delete()
            door_out.delete()
            door_in.delete()
            room1.delete()
            room2.delete()
            del caller.db.tutorial_world_demo_room_data
    elif not roomdata:
        # create and describe the cabin and box
        room1 = create_object("evennia.objects.objects.DefaultRoom", key="A small, cozy cabin")
        room1.db.desc = _ROOM_DESC.strip()
        box = create_object(
            "evennia.objects.objects.DefaultObject", key="small wooden box", location=room1
        )
        box.db.desc = _BOX_DESC.strip()

        # create and describe the meadow and stone
        room2 = create_object("evennia.objects.objects.DefaultRoom", key="A lush summer meadow")
        room2.db.desc = _MEADOW_DESC.strip()
        stone = create_object(
            "evennia.objects.objects.DefaultObject", key="carved stone", location=room2
        )
        stone.db.desc = _STONE_DESC.strip()

        # make the linking exits
        door_out = create_object(
            "evennia.objects.objects.DefaultExit", key="Door", location=room1, destination=room2
        )
        door_out.db.desc = _DOOR_DESC_OUT.strip()
        door_in = create_object(
            "evennia.objects.objects.DefaultExit",
            key="entrance to the cabin",
            aliases=["door", "in", "entrance"],
            location=room2,
            destination=room1,
        )
        door_in.db.desc = _DOOR_DESC_IN.strip()

        # store references for easy removal later
        caller.db.tutorial_world_demo_room_data = (
            caller.location,
            room1,
            box,
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
    caller.cmdset.add(DemoCommandSetRoom)  # TODO - make persistent
    return "command_demo_room"


# register all callables that can be used in the menu template

GOTO_CALLABLES = {
    "send_testing_tagged": send_testing_tagged,
    "do_nothing": do_nothing,
    "goto_command_demo_help": goto_command_demo_help,
    "goto_command_demo_comms": goto_command_demo_comms,
    "goto_command_demo_room": goto_command_demo_room,
}


# Main menu definition

MENU_TEMPLATE = """

## NODE start

Welcome to the |cEvennia|n intro! From this menu you can learn some more about
the system and also the basics of how to play a text-based game. You can exit
this menu at any time by using "q" or "quit".

For (a lot) more help, check out the documentation at http://www.evennia.com.

Write |wnext|n to continue or select a number to jump to that lesson.

## OPTIONS

    1 (next);1;next;n: About Evennia -> about_evennia
    2: What is a MUD/MU*? -> about_muds
    3: Using the webclient -> using webclient
    4: The help command -> goto_command_demo_help()
    5: Communicating with others -> goto_command_demo_help(gotonode='talk on channels')
    6: Using colors -> goto_command_demo_comms(gotonode='testing_colors')
    7: Moving and exploring -> goto_command_demo_room()

# ---------------------------------------------------------------------------------

## NODE about_evennia

Evennia is a game engine for creating multiplayer online text-games.

## OPTIONS

    back;b: Start -> start
    next;n: About MUDs -> about_muds
    >: about_muds

# ---------------------------------------------------------------------------------

## NODE about_muds

The term MUD stands for Multi-user-Dungeon or -Dimension. These are the precursor
to graphical MMORPG-style games like World of Warcraft.


## OPTIONS

    back;b: About Evennia -> about_evennia
    next;n: Using the webclient -> using webclient
    back to start;start;t: start
    >: using webclient

# ---------------------------------------------------------------------------------

## NODE using webclient

|rNote: This is only relevant if you use Evennia's HTML5 web client. If you use a
third-party (telnet) mud-client, you can skip this section.|n

Evennia's web client is (when you install the server locally) found by pointing
your web browser to
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

    back;b: About MUDs -> about_muds
    extra: Customizing the webclient -> customizing the webclient
    next;n: Playing the game -> goto_command_demo_help()
    back to start;start: start
    >: goto_command_demo_help()

# ---------------------------------------------------------------------------------

# this is a dead-end 'leaf' of the menu

## NODE customizing the webclient

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

# ---------------------------------------------------------------------------------

# we get here via goto_command_demo_help()

## NODE command_demo_help

Evennia has about 90 default commands. They include useful administration/building
commands and a few limited "in-game" commands to serve as examples. They are intended
to be changed, extended and modified as you please.

First to try is |yhelp|n. This lists all commands |wcurrently|n available to you.

Use |yhelp <topic>|n to get specific help. Try |yhelp help|n to get help on using
the help command. For your game you could add help about your game, lore, rules etc
as well.

At the moment you only have |whelp|n and some |wChannel Names|n (the '<menu commands>'
is just a placeholder to indicate you are using this menu).

We'll add more commands as we get to them in this tutorial - but we'll only
cover a small handful. Once you exit you'll find a lot more! Now let's try
those channels ...

## OPTIONS

    back;b: Using the webclient -> using webclient
    next;n: Talk on Channels -> talk on channels
    back to start;start: start
    >: talk on channels

# ---------------------------------------------------------------------------------

## NODE talk on channels

|wChannels|n are like in-game chatrooms. The |wChannel Names|n help-category
holds the names of the channels available to you right now. One such channel is
|wpublic|n. Use |yhelp public|n to see how to use it. Try it:

    |ypublic Hello World!|n

This will send a message to the |wpublic|n channel where everyone on that
channel can see it. If someone else is on your server, you may get a reply!

Evennia can link its in-game channels to external chat networks. This allows
you to talk with people not actually logged into the game. For
example, the online Evennia-demo links its |wpublic|n channel to the #evennia
IRC support channel.

## OPTIONS

    back;b: Finding help -> goto_command_demo_help()
    next;n: Talk to people in-game -> goto_command_demo_comms()
    back to start;start: start

# ---------------------------------------------------------------------------------

# we get here via goto_command_demo_comms()

## NODE comms_demo_start

You can also chat with people inside the game. If you try |yhelp|n now you'll
find you have a few more commands available for trying this out.

    |ysay Hello there!|n
    |y"Hello there!|n

|wsay|n is used to talk to people in the same location you are. Everyone in the
room will see what you have to say. A single quote |y"|n is a  convenient shortcut.

    |ypose smiles|n
    |y:smiles|n

|wpose|n (or |wemote|n) describes what you do to those nearby. This is a very simple
command by default, but it can be extended to much more complex parsing in order to
include other people/objects in the emote, reference things by a short-description etc.

## OPTIONS

    next;n: Paging people -> paging_people
    back;b: Talk on Channels -> talk on channels
    back to start;start: start

# ---------------------------------------------------------------------------------

## NODE paging_people

Halfway between talking on a |wChannel|n and chatting in your current location
with |wsay|n and |wpose|n, you can also |wpage|n people. This is like a private
message only they can see.

    |ypage <name> = Hello there!
    page <name1>, <name2> = Hello both of you!|n

If you are alone on the server, put your own name as |w<name>|n to test it and
page yourself. Write just |ypage|n to see your latest pages. This will also show
you if anyone paged you while you were offline.

(By the way - do you think that the use of |y=|n above is strange? This is a
MUSH/MUX-style of syntax.  If you don't like it, you can change it for your own
game by simply changing how the |wpose|n command parses its input.)


## OPTIONS

    next;n: Using colors -> testing_colors
    back;b: Talk to people in-game -> comms_demo_start
    back to start;start: start

# ---------------------------------------------------------------------------------

## NODE testing_colors

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
    back;b: Paging people -> paging_people
    back to start;start: start

# ---------------------------------------------------------------------------------

# we get here via goto_command_demo_room()

## NODE command_demo_room

For exploring the game, a very important command is '|ylook|n'. It's also
abbreviated '|yl|n' since it's used so much. Looking displays/redisplays your
current location. You can also use it to look closer at items in the world. So
far in this tutorial, using 'look' would just redisplay the menu.

Try |ylook|n now. You have been quietly transported to a sunny cabin to look
around in. Explore a little and use |ynext|n when you are done.

## OPTIONS

    back;b: Channel commands -> talk on channels
    next;n: end
    back to start;start: start

# ---------------------------------------------------------------------------------

## NODE end

Thank you for going through the tutorial!


"""


class TutorialEvMenu(EvMenu):
    def close_menu(self):
        """Custom cleanup actions when closing menu"""
        self.caller.cmdset.remove(DemoCommandSetHelp)
        self.caller.cmdset.remove(DemoCommandSetRoom)
        self.caller.cmdset.remove(DemoCommandSetComms)
        _maintain_demo_room(self.caller, delete=True)
        super().close_menu()


def testmenu(caller):
    menutree = parse_menu_template(caller, MENU_TEMPLATE, GOTO_CALLABLES)
    # we'll use a custom EvMenu child later
    TutorialEvMenu(caller, menutree)
