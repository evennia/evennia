"""
The state system allows the player to enter a state where only a special set of commands
are available. This can be used for all sorts of useful things:
  - in-game menus (picking an option from a list)
  - inline text editors (entering text into a buffer)
  - npc conversation (select replies)
  - commands only available while in 'combat mode' etc  
This allows for more power than using rooms to build 'menus'. 

Basically the GLOBAL_STATE_TABLE contains a dict with command tables keyed after the
name of the state. To use, a function must set the 'state' variable on a player object
using the obj.set_state() function. The GLOBAL_STATE_TABLE will then be searched by the
command handler and if the state is defined its command table is used instead
of the normal global command table.

The state system is pluggable, in the same way that commands are added to the global command
table, commands are added to the GLOBAL_STATE_TABLE using add_command supplying in
addition the name of the state. 
"""

from cmdtable import CommandTable
from logger import log_errmsg
import src.helpsys.management.commands.edit_helpfiles as edit_help


class StateTable(object):

    state_table = None

    def __init__(self):
        self.state_table = {}
        self.help_index = StateHelpIndex()
        
    def add_command(self, state_name, command_string, function, priv_tuple=None,
                    extra_vals=None, auto_help=False, staff_help=False, help_global=False,
                    exit_command=True):
        """
        Access function; transparently add commands to a specific command table to
        represent a particular state. This command is similar to the normal
        command_table.add_command() function. See example in gamesrc/commands/examples.

        command_string: (str) command name to run, like look, @list etc
        function: (reference) command function object
        state_name: (str) identifier of the state we tie this to.
        priv_tuple: (tuple) String tuple of permissions required for command.
        extra_vals: (dict) Dictionary to add to the Command object.        
        
        auto_help: (bool) Activate the auto_help system. By default this stores the
               help inside the statetable only (not in the main help database), and so
               the help entries are only available when the player is actually inside
               the state. Note that the auto_help system of state-commands do not
               support <<TOPIC:mytitle>> markup. 
        staff_help: (bool) Help entry is only available for staff players.
        help_global: (bool) Also auto_add the help entry to the main help database. Be
               careful with overwriting same-named help topics if you define special
               versions of commands inside your state. 

        exit_command: (bool) Sets if the default @exit command is added to the state. Only
               one command needs to include this statement in order to add @exit. This is
               usually a good idea to make sure the player is not stuck, but you might want
               to turn this off if you know what you're doing and want to avoid players
               'escaping' the state (like in a combat state or similar), or when
               you need to do some special final cleanup or save operations before
               exiting (like in a text editor). 
        """

        if not state_name:
            log_errmsg("Command %s was not given a state. Not added." % command_string)
            return 

        state_name = state_name.strip()
        if not self.state_table.has_key(state_name):

            #create the state
            self.state_table[state_name] = CommandTable()        
            #always add a help index even though it might not be used.
            self.help_index.add_state(state_name)

            if exit_command:                
                #add the @exit command
                self.state_table[state_name].add_command("@exit",
                                                         cmd_state_exit,
                                                         auto_help=True)            
                if auto_help:
                    #add help for @exit command
                    self.help_index.add_state_help(state_name, "@exit",
                                                   cmd_state_exit.__doc__)        

        #handle auto-help for the state
        if auto_help:            

            #make sure the state's help command is in place           
            self.state_table[state_name].add_command('help',cmd_state_help)

            #add the help text
            helptext = function.__doc__
            self.help_index.add_state_help(state_name,command_string,
                                           helptext,staff_only=staff_help)    
            if not help_global:
                #if we don't want global help access, we need to
                #turn off auto_help before adding the command.
                auto_help = False                
            
        #finally add the new command to the state                        
        self.state_table[state_name].add_command(command_string,
                                                     function, priv_tuple,
                                                     extra_vals,auto_help,
                                                     staff_help)        
            
    def get_cmd_table(self, state_name):
        """
        Return the command table for a particular state.
        """
        if self.state_table.has_key(state_name):
            return self.state_table[state_name]
        else:
            return None
        
                   
class StateHelpIndex(object):
    """
    Handles the dynamic state help system. 
    """
    help_index = None
    def __init__(self):
        self.help_index = {}
        self.identifier = '<<TOPIC:'

    def add_state(self,state_name):
        "Create a new state"
        self.help_index[state_name] = {}

    def add_state_help(self, state,command,text,staff_only=False):
        """Store help for a command under a certain state.
        Supports <<TOPIC:MyTopic>> and <<TOPIC:STAFF:MyTopic>> markup."""
        if self.help_index.has_key(state):

            text = text.rstrip()
            if self.identifier in text:
                topic_dict, staff_dict = edit_help.handle_help_markup(command, text, staff_only,
                                                                      identifier=self.identifier)
                for topic, text in topic_dict.items():
                    entry = edit_help.format_footer(topic,text,topic_dict,staff_dict)
                    if entry:                        
                        self.help_index[state][topic] = (staff_only, entry)
            else:
                self.help_index[state][command] = (staff_only, text)

    def del_state_help(self, state, topic):
        """Manually delete an help topic from state help system. Note that this is
        only going to last until the next @reload unless you also turn off auto_help
        for the relevant topic."""
        if self.help_index.has_key(state) and self.help_index[state].has_key(topic):
            del self.help_index[state][topic]
            return True
        else: 
            return False
        
    def get_state_help(self,caller, state, command):
        "get help for a particular command within a state"
        if self.help_index.has_key(state) and self.help_index[state].has_key(command):
            help_tuple = self.help_index[state][command]
            if caller.is_staff() or not help_tuple[0]:
                return help_tuple[1]            
            return None
        else:
            return None
        
    def get_state_index(self,caller, state):
        "list all help topics for a state"
        if self.help_index.has_key(state):                        
            if caller.is_staff():
                index = self.help_index[state].keys()
            else:
                index = []
                for key, tup in self.help_index[state].items():
                    if not tup[0]:
                        index.append(key)
            return sorted(index)
        else:
            return None

#default commands available for all special states

def cmd_state_exit(command):
    """@exit (when in a state)

    This command only works when inside a special game 'state' (like a menu or
    editor or similar place where you have fewer commands available than normal).

    It aborts what you were doing and force-exits back to the normal mode of
    gameplay. Some states might deactivate the @exit command for various reasons.
    In those cases, read the help when in the state to learn more."""

    source_object = command.source_object
    source_object.clear_state()
    source_object.emit_to("... Exited.")
    source_object.execute_cmd('look')        
    
def cmd_state_help(command):
    """
    help <topic> (while in a state)

    In-state help system. This is NOT tied to the normal help
    system and is not stored in the database. It is intended as a quick
    reference for users when in the state; if you want a detailed description
    of the state itself, you should probably add it to the main help system
    so the user can read it at any time.
    If you don't want to use the auto-system, turn off auto_help
    for all commands in the state. You could then for example make a custom help command
    that displays just a short help summary page instead.
    """

    source_object = command.source_object
    state = source_object.get_state()
    args = command.command_argument
    switches = command.command_switches

    help_index = GLOBAL_STATE_TABLE.help_index

    if not args:
        index = help_index.get_state_index(source_object, state)        
        if not index:
            source_object.emit_to("There is no help available here.")
            return        
        s = "Help topics for %s:\n\r" % state        
        for i in index:
            s += "    %s\n\r" % i
        s = s[:-2]
        source_object.emit_to(s)
        return
    else:
        args = args.strip()

        if 'del' in switches:
            if not source_object.is_staff():
                source_object.emit_to("Only staff can delete help topics.")
                return
            if help_index.del_state_help(state,args):
                source_object.emit_to("Topic %s deleted." % args)
            else:
                source_object.emit_to("Topic %s not found." % args)
            return
        
        help = help_index.get_state_help(source_object, state, args)
        if help:
            source_object.emit_to("%s" % help)
        else:
            source_object.emit_to("No help available on %s." % args) 


GLOBAL_STATE_TABLE = StateTable()
