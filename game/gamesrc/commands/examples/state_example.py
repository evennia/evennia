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
    #display the menu.
    print_menu(source_object)    

#
# Commands only available while in the 'menu' state. Note that
#  these have auto_help, so the __doc__ strings of the functions
#  can be read as help entries when in the menu. 
#
def menu_cmd_option1(command):
    """
    option1
    This selects the first option.
    """
    source_object = command.source_object
    print_menu(source_object, 1)
def menu_cmd_option2(command):
    """
    option2
    This selects the second option. Duh.

    <<TOPIC:About>>
    This is an extra topic to test the auto_help functionality.
    """
    source_object = command.source_object
    print_menu(source_object, 2)
def menu_cmd_clear(command):
    """
    clear
    Clears the options.  
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
        ch = "> option1\n  option2"
    elif choice==2:
        ch = "  option1\n> option2"
    else:
        ch = "  option1\n  option2"
        
    s ="Menu---------\n%s\n  help - get help" % ch
    source_obj.emit_to(s)



#Add the 'entry' command to the normal command table
GLOBAL_CMD_TABLE.add_command("entermenu", cmd_entermenu)

#Add the menu commands to the state table by tying them to the 'menu' state. It is
#important that the name of the state matches what we set the player-object to in
#the 'entry' command. Since auto_help is on, we will have help entries for all commands
#while in the menu.
GLOBAL_STATE_TABLE.add_command(STATENAME, "option1", menu_cmd_option1,auto_help=True)
GLOBAL_STATE_TABLE.add_command(STATENAME, "option2", menu_cmd_option2,auto_help=True)
GLOBAL_STATE_TABLE.add_command(STATENAME, "clear", menu_cmd_clear,auto_help=True)
