"""
A more sophisticated nested menu module. This could easily be adapted for anything
 from character creation to npc quest dialogues. 

Default functionality:
 - Multiple-choice options, numbered 1-10
 - Any level of option nesting and structure
 - Run arbitrary command in each menu node (character attributes, anybody?)
 - Menu history; allows you to step back all the way to the beginning.
 - Exit function

Note that this makes full use of expanded attributes, by saving a list of objects
in a temporary attribute. So if you haven't updated/reinitialized the database
after revision 626 you should do that or this menu will not work. 

This can be used as a template for any menu. Copy this to a new module (activate in
settings.py if necessary), then change STATENAME and adjust the cmd_update() to look
the way you want. Decide if you want back-stepping functionality and be able to
exit the menu at any time (deactivate those commands if so). Finally define the menu
itself by interconnecting Node objects. 
"""

from src.cmdtable import GLOBAL_CMD_TABLE
from src.statetable import GLOBAL_STATE_TABLE

STATENAME = 'nestedmenu'

#temporary attribute
NODELIST = '_menu_node_history'

#
# Defining the menu tree
#

class Node(object):
    """
    This holds one single point in the menu tree.
    """
    def __init__(self,header, text="", func=None):
        self.header = header
        self.text = text
        self.func = func
        self.choices = []
#
# functions to be run at particular nodes
#
def node_func(command):
    "function to be called at a node"
    source_object = command.source_object
    source_object.emit_to("This is the node function being called!")
def endmenu(command):
    "Exit the menu."
    cmd_exit_menu(command)
    
#
# The menu tree 
#

#available nodes
START = Node("Start menu", text="Welcome to the menu.")
secondnode = Node("Second menu")
thirdnode = Node("Third menu")
fourthnode = Node("Fourth menu", text="This is an extra text.")
fifthnode = Node("Fifth menu", func=node_func)
endnode = Node("Endpoint", text="Goodbye.", func=endmenu)

#linking the nodes together
START.choices = [secondnode,thirdnode]
secondnode.choices = [fourthnode, fifthnode]
thirdnode.choices = [secondnode, fifthnode]
fourthnode.choices = [fifthnode, thirdnode]
fifthnode.choices = [START, endnode]

#
# Menu mechanics
#

# Menu entry command
def cmd_entermenu(command):
    "entry command"
    source_object = command.source_object
    source_object.set_state(STATENAME)
    #assumes a node START has been defined as the initial one.
    source_object.set_attribute(NODELIST, [START]) 
    cmd_update(command)    

def cmd_update(command):
    """Runs the current node in the tree and displays
    its contents."""
    source_object = command.source_object
    node = source_object.get_attribute_value(NODELIST)[-1]
            
    s = "\n\r%s%s\n\r%s" % ('%ch%cw',node.header,'%cn')
    if node.text:
        s += node.text + '\n\r'

    if node.choices:         
        for i,ch in enumerate(node.choices):
            s += "  %s%i %s%s\n\r" % ('%ch%cw', i+1, '%cn%cy', ch.header)
    s += "    (back)"
    source_object.emit_to(s)
    
    if callable(node.func):
        node.func(command)
        
def cmd_exit_menu(command):
    "helper command"
    source_object = command.source_object
    source_object.clear_attribute(NODELIST)    
    source_object.clear_state()
    source_object.execute_cmd('look')

def cmd_prev(command):
    source_object = command.source_object
    prevlist = source_object.get_attribute_value(NODELIST)    
    exiting = False
    try:
        prevlist.pop()        
        if not prevlist: exiting = True
    except IndexError:        
        exiting = True
    if exiting:
        cmd_exit_menu(command)
        return    
    source_object.set_attribute(NODELIST,prevlist)
    cmd_update(command)

def cmd_help(command):
    source_object = command.source_object        
    s = \
    """
    %sMenu help
    %s1-10       - Select an option
    l,look     - redraw the menu
    b,back     - back to previous
    exit       - leave menu""" % ('%ch%cw', '%cn%cy')
    source_object.emit_to(s)

def option(function):
    "Option Decorator"
    def retfunc(command):
        val = function()
        source_object = command.source_object    
        nodelist = source_object.get_attribute_value(NODELIST)
        choices = nodelist[-1].choices
        try:
            choicenode = choices[val-1]
        except IndexError:
            source_object.emit_to("Not a valid option.")
            return
        nodelist.append(choicenode)
        source_object.set_attribute(NODELIST, nodelist)
        cmd_update(command)
    return retfunc

@option
def cmd_option1():
    return 1
@option
def cmd_option2():
    return 2
@option
def cmd_option3():
    return 3
@option
def cmd_option4():
    return 4
@option
def cmd_option5():
    return 5
@option
def cmd_option6():
    return 6
@option
def cmd_option7():
    return 7
@option
def cmd_option8():
    return 8
@option
def cmd_option9():
    return 9
@option
def cmd_option10():
    return 10
           
#entry command
GLOBAL_CMD_TABLE.add_command("enter_nested", cmd_entermenu)

#create the state
GLOBAL_STATE_TABLE.add_state(STATENAME)

#menu commands
GLOBAL_STATE_TABLE.add_command(STATENAME, '1', cmd_option1)
GLOBAL_STATE_TABLE.add_command(STATENAME, '2', cmd_option2)
GLOBAL_STATE_TABLE.add_command(STATENAME, '3', cmd_option3)
GLOBAL_STATE_TABLE.add_command(STATENAME, '4', cmd_option4)
GLOBAL_STATE_TABLE.add_command(STATENAME, '5', cmd_option5)
GLOBAL_STATE_TABLE.add_command(STATENAME, '6', cmd_option6)
GLOBAL_STATE_TABLE.add_command(STATENAME, '7', cmd_option7)
GLOBAL_STATE_TABLE.add_command(STATENAME, '8', cmd_option8)
GLOBAL_STATE_TABLE.add_command(STATENAME, '9', cmd_option9)
GLOBAL_STATE_TABLE.add_command(STATENAME, '10',cmd_option10)
GLOBAL_STATE_TABLE.add_command(STATENAME, 'l', cmd_update)
GLOBAL_STATE_TABLE.add_command(STATENAME, 'look', cmd_update)
GLOBAL_STATE_TABLE.add_command(STATENAME, 'h', cmd_help)
GLOBAL_STATE_TABLE.add_command(STATENAME, 'help', cmd_help)

GLOBAL_STATE_TABLE.add_command(STATENAME, 'b', cmd_prev)
GLOBAL_STATE_TABLE.add_command(STATENAME, 'back', cmd_prev)
GLOBAL_STATE_TABLE.add_command(STATENAME, 'exit', cmd_exit_menu)
