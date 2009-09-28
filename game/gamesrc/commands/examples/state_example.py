"""
Example of using the state system. The Event system allows a player object to be
'trapped' in a special environment where different commands are available than normal.
This is very useful in order to implement anything from menus to npc-conversational
choices and inline text-editors. 

This example uses the State system to create a simple menu. 

To test out this example, add this module to the CUSTOM_COMMAND_MODULES tuple in
your game/settings.py as 'game.gamesrc.commands.examples.state_example' (see ./example.py
for another example). You need to restart the Evennia server before new files are
recognized. 

Next enter the mud and give the command
> entermenu

Note that the help entries added to the state system with the auto_help flag are NOT
part of the normal help database, they are stored with the state and only accessible
from inside it (unless you also set the 'global_help' flag in the add_command(), in
which case it is also added to the global help system). If you want to describe the
state itself in more detail you should add that to the main help index manually. 

To further test the state system, try the command 
> enterstate
"""

#This is the normal command table, accessible by default
from src.cmdtable import GLOBAL_CMD_TABLE

#The statetable contains sets of cmdtables that is made available
#only when we are in a particular state, overriding the GLOBAL_CMD_TABLE
from src.statetable import GLOBAL_STATE_TABLE

#
# Implementing a simple 'menu' state
#

#the name of our state, to make sure it's the same everywhere
STATENAME = 'menu'

#
# 'entry' command
#    
def cmd_entermenu(command):
    """
    This is the 'entry' command that takes the player from the normal    
    gameplay mode into the 'menu' state. In order to do this, it
    must be added to the GLOBAL_CMD_TABLE like any command.
    """
    #get the player object calling the command    
    source_object = command.source_object    
    #this is important: we use the set_state() command
    #to shift the player into a state named 'menu'. Other useful
    #access functions on source_object are get_state()
    # and clear_state(), the latter returns the player to
    # the normal mode of gameplay. 
    source_object.set_state(STATENAME)
    #show the menu.
    s = """
     Welcome to the Demo menu!
     In this demo all you can do is select one of the two options so it changes colour.
     This is just intended to show off the possibility of the state system. More
     interesting things should of course happen in a real menu. Use @exit to
     leave the menu."""  
    source_object.emit_to(s)
    source_object.execute_cmd('menu')

#
# Commands only available while in the 'menu' state. Note that
#  these have auto_help, so the __doc__ strings of the functions
#  can be read as help entries when in the menu. 
#
def menu_cmd_option1(command):
    """
    option1
    This command, obviously,  selects the first option.
    """
    source_object = command.source_object
    print_menu(source_object, 1)
def menu_cmd_option2(command):
    """
    option2
    This command selects the second option. Duh.
    """
    source_object = command.source_object
    print_menu(source_object, 2)
def menu_cmd_menu(command):
    """
    menu
    Clears the options and redraws the menu.  
    <<TOPIC:autohelp>>    
    This is an extra topic to test the auto-help functionality. The state-help
    system supports nested ('related') topics just like the normal help index does.
    """
    source_object = command.source_object
    print_menu(source_object)

#
# helper function
#
def print_menu(source_obj,choice=None):
    """
    Utility function to print the menu. More interesting things
    would happen here in a real menu. 
    """
    
    if choice==1:
        ch = "%s> option1\n  %soption2" % ('%ch%cy','%cn%cy') #ansi colouring; see src.ansi
    elif choice==2:
        ch = "  %soption1\n%s> option2" % ('%cn%cy','%ch%cy')
    else:
        ch = "  %soption1\n  option2" % ('%cn%cy')
      
    s ="\n%sMenu: \n%s\n  %shelp" % ('%ch%cr',ch,'%cn%cy')
    source_obj.emit_to(s)

#Add the 'entry' command to the normal command table
GLOBAL_CMD_TABLE.add_command("entermenu", cmd_entermenu)

#create the state.
GLOBAL_STATE_TABLE.add_state(STATENAME,exit_command=True)

#Add the menu commands to the state table by tying them to the 'menu' state. It is
#important that the name of the state matches what we set the player-object to in
#the 'entry' command. Since auto_help is on, we will have help entries for all commands
#while in the menu.
GLOBAL_STATE_TABLE.add_command(STATENAME, "option1", menu_cmd_option1,auto_help=True)
GLOBAL_STATE_TABLE.add_command(STATENAME, "option2", menu_cmd_option2,auto_help=True)
GLOBAL_STATE_TABLE.add_command(STATENAME, "menu", menu_cmd_menu,auto_help=True)




#-----------------------testing the depth of the state system
# This is a test suite that shows off all the features of the state system.
# It sets up a test command @test_state that takes an argument 1-6 for moving into states
# with different characteristics. Note that the only difference as to how the
# various states are created lies in the options given to the add_state() function.
# Use @exit to leave any state. 
#
#  All states includes a small test function named "test". 
#  1: A very limited state; only contains the "test" command. 
#  2: All global commands are included (so this should be the same as normal operation,
#     except you cannot traverse exits and use object-based cmds)
#  3: Only the global commands "get" and "inventory" are included into the state.
#  4: All global commands /except/ "get" and "inventory" are available
#  5: All global commands availabe + ability to traverse exits (not use object-based cmds).
#  6: Only the "test" command, but ability to both traverse exits and use object-based cmds. 
#
# Examples of in-game use: 
# 1: was used for the menu system above.
# 2: could be used in order to stop someone from moving despite exits being open (tied up?)
# 3: someone incapacitated or blinded might get only limited commands available
# 4: in e.g. a combat state, things like crafting should not be possible
# 5: Pretty much default operation, maybe limiting the use of magical weapons in a room etc?
# 6: A state of panic? You can move, but not take in your surroundings?
#   ... the possibilities are endless. 

#defining the test-state names so they are the same everywhere
TSTATE1 = 'no_globals'
TSTATE2 = 'all_globals'
TSTATE3 = 'include_some_globals'
TSTATE4 = 'exclude_some_globals'
TSTATE5 = 'global_allow_exits'
TSTATE6 = 'noglobal_allow_exits_obj_cmds'

#
#the test command @test_state
#
def cmd_test_state(command):
    "testing the new state system"
    source_object = command.source_object
    args = command.command_argument
    if not args:
        source_object.emit_to("Usage: enterstate 1 - 6")
        return    
    s = "\n Entering state ... \nThis state includes the commands 'test', 'help', '@exit' and "
    arg = args.strip()
    if arg=='1':
        s += "no global commands at all. With some more state commands, this state would work well for e.g. a combat state or a menu where the player don't need access to the normal command definitions. Take a special look at the help command, which is in fact a state-only version of the normal help." 
        state = TSTATE1
    elif arg=='2':
        s += "all global commands. You should be able to do everything as normal, but not move around."
        state = TSTATE2
    elif arg=='3':
        s += "the global commands 'inv' and 'get' only."
        state = TSTATE3
    elif arg=='4':
        s += "all global commands *except* 'inv' and 'get' (try using them). This allows you to disable commands that should not be possible at a certain time (like starting to craft while in a fight or something)."
        state = TSTATE4
    elif arg=='5':
        s += "all global commands as well as the ability to traverse exits. You do not have the ability to use commands defined on objects though."
        state = TSTATE5
    elif arg=='6':
        s += "no globals at all, but you have the ability to both use exits and commands on items. This would maybe be interesting for a 'total darkness' state or maybe a 'panic' state where you can move around but cannot actually take in your surroundings."
        state = TSTATE6
    else:
        source_object.emit_to("Usage: enterstate 1 - 6")
        return 
    #set the state
    source_object.set_state(state)
    source_object.emit_to("%s\n (Now in state %s: '%s' ... use @exit to leave the state.)" % (s,arg,state))

#a simple command to include in all states.
def cmd_instate_cmd(command):
    """
    This is the help text for the test command (created with the auto_help sytem).
    This is a state-only command that does not exist outside this state. Since this state
    is completely isolated from the normal gameplay, commands can also
    harmlessly redefine any normal command - so if there was a normal command named
    'test', it would remain unchanged when we leave the state.
    """
    command.source_object.emit_to("This state command works!")

#define some global commands to filter for
cmdfilter = ['get','inventory']
    
#1: A simple, basic state
GLOBAL_STATE_TABLE.add_state(TSTATE1,exit_command=True)
#2: Include all normal commands in the state
GLOBAL_STATE_TABLE.add_state(TSTATE2,exit_command=True,global_cmds='all')
#3: Include only the two global commands in cmdfilter
GLOBAL_STATE_TABLE.add_state(TSTATE3,exit_command=True,
                             global_cmds='include',global_filter=cmdfilter)
#4: Include all global commands except the ones in cmdfilter
GLOBAL_STATE_TABLE.add_state(TSTATE4,exit_command=True,
                             global_cmds='exclude',global_filter=cmdfilter)
#5: Include all global commands + ability to traverse exits
GLOBAL_STATE_TABLE.add_state(TSTATE5,exit_command=True,
                             global_cmds='all',
                             allow_exits=True)
#6: No global commands, allow exits and commands defined on objects.
GLOBAL_STATE_TABLE.add_state(TSTATE6,exit_command=True,
                             allow_exits=True,allow_obj_cmds=True)

#append the "test" function to all states
GLOBAL_STATE_TABLE.add_command(TSTATE1,'test',cmd_instate_cmd,auto_help=True)
GLOBAL_STATE_TABLE.add_command(TSTATE2,'test',cmd_instate_cmd)
GLOBAL_STATE_TABLE.add_command(TSTATE3,'test',cmd_instate_cmd)
GLOBAL_STATE_TABLE.add_command(TSTATE4,'test',cmd_instate_cmd)
GLOBAL_STATE_TABLE.add_command(TSTATE5,'test',cmd_instate_cmd)
GLOBAL_STATE_TABLE.add_command(TSTATE6,'test',cmd_instate_cmd)

#create the entry function for testing all states
GLOBAL_CMD_TABLE.add_command('enterstate',cmd_test_state)


