"""
Game tutor

Evennia contrib - Griatch 2020

This contrib is a tutorial menu using the EvMenu menu-templating system.

"""

from evennia.utils.evmenu import parse_menu_template, EvMenu

# goto callables

def command_passthrough(caller, raw_string, **kwargs):
    cmd = kwargs.get("cmd")
    on_success = kwargs.get('on_success')
    if cmd:
        caller.execute_cmd(cmd)
    else:
        caller.execute_cmd(raw_string)
    return on_success

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
    4: Command input -> command_input

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

Evennia supports traditional telnet clients but also offers a HTML5 web client. It
is found (on a default install) by pointing your web browser to
    |yhttp:localhost:4001/webclient|n
For a live example, the public Evennia demo can be found at
    |yhttps://demo.evennia.com/webclient|n

The web client start out having two panes. The bottom one is where you insert commands
and the top one is where you see returns from the server. 

- Use |y<Return>|n (or click the arrow on the right) to send your input.
- Use |yCtrl + <up-arrow>|n to step back and repeat a command you entered previously.
- Use |yCtrl + <Return>|n to add a new line to your input without sending.

If you want there is some |wextra|n info to learn about customizing the webclient.

## OPTIONS
    
    back: about_muds
    extra: learn more about customizing the webclient -> customizing the webclient
    next: general command input -> command_input
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
    next: general command input -> command_input
    back to top: start
    > test *: send tagged message to new pane -> send_testing_tagged()

# ---------------------------------------------------------------------------------

## NODE command_input

The first thing to learn is to use the |yhelp|n command. 

## OPTIONS 

    back: using webclient
    next: (end) -> end
    back to top: start
    > h|help: command_passthrough(cmd=help)
    
# ---------------------------------------------------------------------------------

## NODE end

Thankyou for going through the tutorial!


"""


GOTO_CALLABLES = {
    "command_passthrough": command_passthrough,
    "send_testing_tagged": send_testing_tagged,
    "do_nothing": do_nothing,
    "send_string": send_string,
}

def testmenu(caller):
    menutree = parse_menu_template(caller, MENU_TEMPLATE, GOTO_CALLABLES)
    # we'll use a custom EvMenu child later
    EvMenu(caller, menutree)
