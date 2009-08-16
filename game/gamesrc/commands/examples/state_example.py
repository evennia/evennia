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
        
    s ="%sMenu: \n%s\n  %shelp" % ('%ch%cr',ch,'%cn%cy')
    source_obj.emit_to(s)

#Add the 'entry' command to the normal command table
GLOBAL_CMD_TABLE.add_command("entermenu", cmd_entermenu)

#create the state.
GLOBAL_STATE_TABLE.add_state(STATENAME)

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

#the test command @test_state
def cmd_test_state(command):
    "testing the new state system"
    source_object = command.source_object
    args = command.command_argument
    if not args:
        source_object.emit_to("Usage: @test_state [1..6]")
        return    
    arg = args.strip()
    if arg=='1':
        state = TSTATE1
    elif arg=='2':
        state = TSTATE2
    elif arg=='3':
        state = TSTATE3
    elif arg=='4':
        state = TSTATE4
    elif arg=='5':
        state = TSTATE5
    elif arg=='6':
        state = TSTATE6
    else:
        source_object.emit_to("Usage: @test_state [1..6]")
        return 
    #set the state
    source_object.set_state(state)
    source_object.emit_to("Now in state '%s' ..." % state)

#a simple command to include in all states.
def cmd_instate_cmd(command):
    "test command in state"
    command.source_object.emit_to("This command works!")

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
GLOBAL_STATE_TABLE.add_command(TSTATE1,'test',cmd_instate_cmd)
GLOBAL_STATE_TABLE.add_command(TSTATE2,'test',cmd_instate_cmd)
GLOBAL_STATE_TABLE.add_command(TSTATE3,'test',cmd_instate_cmd)
GLOBAL_STATE_TABLE.add_command(TSTATE4,'test',cmd_instate_cmd)
GLOBAL_STATE_TABLE.add_command(TSTATE5,'test',cmd_instate_cmd)
GLOBAL_STATE_TABLE.add_command(TSTATE6,'test',cmd_instate_cmd)

#create the entry function for testing all states
GLOBAL_CMD_TABLE.add_command('@test_state',cmd_test_state)


