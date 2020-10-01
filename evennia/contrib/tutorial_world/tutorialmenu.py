"""
Game tutor

Evennia contrib - Griatch 2020

This contrib is a tutorial menu using the EvMenu menu-templating system.

"""

from evennia import create_object
from evennia import CmdSet
from evennia.utils.evmenu import parse_menu_template, EvMenu

# goto callables


def do_nothing(caller, raw_string, **kwargs):
    return None

def send_testing_tagged(caller, raw_string, **kwargs):
    caller.msg(("This is a message tagged with 'testing' and "
                "should appear in the pane you selected!\n "
                f"You wrote: '{raw_string}'", {"type": "testing"}))
    return None

def send_string(caller, raw_string, **kwargs):
    caller.msg(raw_string)
    return None


# resources for the look-demo

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

    Write |ynext|n to leave the cabin and continue with the tutorial.
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
            prev_loc, room, obj = roomdata
            caller.location = prev_loc
            obj.delete()
            room.delete()
            del caller.db.tutorial_world_demo_room_data
    elif not roomdata:
        room = create_object("evennia.objects.objects.DefaultRoom",
                             key="A small, cozy cabin")
        room.db.desc = _ROOM_DESC.strip()
        obj = create_object("evennia.objects.objects.DefaultObject",
                            key="A small wooden box")
        obj.db.desc = _BOX_DESC.strip()
        obj.location = room
        # move caller into room and store
        caller.db.tutorial_world_demo_room_data = (caller.location, room, obj)
        caller.location = room

class DemoCommandSet1(CmdSet):
    """
    Demo the `look` command.
    """
    key = "cmd_demo_cmdset_1"
    priority = 2

    def at_cmdset_creation(self):
        from evennia import default_cmds
        self.add(default_cmds.CmdLook())

def goto_command_demo_1(caller, raw_string, **kwargs):
    """Generate a little room environment for testing out some commands."""
    _maintain_demo_room(caller)
    caller.cmdset.add(DemoCommandSet1)  # TODO - make persistent
    return "command_demo_1"

# resources for the general command demo

class DemoCommandSet2(CmdSet):
    """
    Demo other commands.
    """
    key = "cmd_demo_cmdset_2"
    priority = 2

    def at_cmdset_creation(self):
        from evennia import default_cmds
        self.add(default_cmds.CmdHelp())


def goto_command_demo_2(caller, raw_string, **kwargs):
    _maintain_demo_room(caller, delete=True)
    caller.cmdset.remove(DemoCommandSet1)
    caller.cmdset.add(DemoCommandSet2)  # TODO - make persistent
    return "command_demo_2"


def command_passthrough(caller, raw_string, **kwargs):
    cmd = kwargs.get("cmd")
    on_success = kwargs.get('on_success')
    if cmd:
        caller.execute_cmd(cmd)
    else:
        caller.execute_cmd(raw_string)
    return on_success


MENU_TEMPLATE = """

## NODE start

Welcome to |cEvennia|n! From this menu you can learn some more about the system and
also the basics of how to play a text-based game. You can exit this menu at
any time by using "q" or "quit".

Select an option you want to learn more about below.

## OPTIONS

    1: About evennia -> about_evennia
    2: What is a MUD/MU*? -> about_muds
    3: Using the webclient -> using webclient
    4: Using commands -> goto_command_demo_1()

# ---------------------------------------------------------------------------------

## NODE about_evennia

Evennia is a game engine for creating multiplayer online text-games.

## OPTIONS

    back: start
    next: about MUDs -> about_muds
    >: about_muds

# ---------------------------------------------------------------------------------

## NODE about_muds

The term MUD stands for Multi-user-Dungeon or -Dimension. These are the precursor
to graphical MMORPG-style games like World of Warcraft.


## OPTIONS

    back: about_evennia
    next: using the webclient -> using webclient
    back to top: start
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

    back: about_muds
    extra: more details about customizing the webclient -> customizing the webclient
    next: general command tutorial -> goto_command_demo_1()
    back to top: start
    >: back

# ---------------------------------------------------------------------------------

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

    back: using webclient
    next: general command input -> goto_command_demo_1()
    back to top: start
    > test *: send tagged message to new pane -> send_testing_tagged()

# ---------------------------------------------------------------------------------

# we get here via goto_command_demo_1()

## NODE command_demo_1

Evennia has about 90 default commands. They include useful administration/building
commands and a few limited "in-game" commands to serve as examples. They are intended
to be changed, extended and modified as you please.

The most important and common command you have is '|ylook|n'. It's also
abbreviated '|yl|n' since it's used so much. It displays/redisplays your current
location.

Try |ylook|n now. You have been transported to a sunny cabin to look around in.

## OPTIONS

    back: using webclient
    next: help on help -> goto_command_demo_2()
    back to top: start


# ---------------------------------------------------------------------------------

# we get here via goto_command_demo_2()

## NODE command_demo_2

Evennia commands can change meaning depending on context. We left the sunny
cabin now and if you try |ylook|n again you will just re-display this menu
(try it!). Instead you have some other commands available to try out.

First is |yhelp|n. This lists all commands |wcurrently|n available to you. In
the future you could also add your own topics about your game, world, rules etc.

Only a few commands are made available while in this tutorial. Once you exit
you'll find a lot more!

(ignore the the <menu commands>, it's just indicating that you have the ability
to use the default functionality of this tutorial menu, like choosing options).

Use |yhelp help|n to see how to use the help command. Most often you'll just do

    help <topic>

In the coming pages we'll test out these available commands.

## OPTIONS

    back: back to the cabin -> goto_command_demo_1()
    next: talk on channels -> talk on channels
    back to top: start

# ---------------------------------------------------------------------------------

## NODE talk on channels

|wChannels|n are like in-game chatrooms. The |wChannel names|n help-category
holds the names of the channels available to you right now. One such channel is
|wpublic|n. Use |yhelp public|n to see how to use it. Try it:

    |ypublic Hello World!|n

This will send a message to the |wpublic|n channel where everyone on that
channel can see it. If someone else is on your server, you may get a reply!

Evennia can link its in-game channels to external chat networks. This allows
you to talk with people not actually logged into the game. For
example, the online Evennia-demo links its |wpublic|n channel to the #evennia
IRC support channel, which in turn links to a Discord channel!

## OPTIONS

    back: help on help -> goto_command_demo_2()
    next: end
    back to top: start

# ---------------------------------------------------------------------------------

## NODE end

Thankyou for going through the tutorial!


"""


GOTO_CALLABLES = {
    "command_passthrough": command_passthrough,
    "send_testing_tagged": send_testing_tagged,
    "do_nothing": do_nothing,
    "send_string": send_string,
    "goto_command_demo_1": goto_command_demo_1,
    "goto_command_demo_2": goto_command_demo_2,
}

class TutorialEvMenu(EvMenu):
    def close_menu(self):
        """Custom cleanup actions when closing menu"""
        _maintain_demo_room(self.caller, delete=True)
        super().close_menu()


def testmenu(caller):
    menutree = parse_menu_template(caller, MENU_TEMPLATE, GOTO_CALLABLES)
    # we'll use a custom EvMenu child later
    TutorialEvMenu(caller, menutree)
