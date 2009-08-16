"""
The state system allows the player to enter states/modes where only a special set of commands
are available. This can be used for all sorts of useful things:
  - in-game menus (picking an option from a list, much more powerful than using 'rooms')
  - inline text editors (entering text into a buffer)
  - npc conversation (select replies)
  - only allowing certain commands in special situations (e.g. special attack commands
    when in 'combat' mode)    
  - adding special commands to the normal set (e.g. a 'howl' command when in 'werewolf' state)
  - deactivating certain commands (e.g. removing the 'say' command in said 'werewolf' state ...) 

Basically the GLOBAL_STATE_TABLE contains a dict with command tables keyed after the
name of the state. To use, a function must set the 'state' variable on a player object
using the obj.set_state() function. The GLOBAL_STATE_TABLE will then be searched by the
command handler and if the state is defined its command table is used instead
of the normal global command table.

The state system is pluggable, in the same way that commands are added to the global command
table, commands are added to the GLOBAL_STATE_TABLE using add_command supplying in
addition the name of the state. The main difference is that new states must first be created
using the GLOBAL_STATE_TABLE.add_state() command. See examples in game/gamesrc.
"""

from cmdtable import CommandTable, GLOBAL_CMD_TABLE
from logger import log_errmsg
import src.helpsys.management.commands.edit_helpfiles as edit_help

class StateTable(object):

    state_table = None

    def __init__(self):        
        self.state_table = {} #of the form {statename:CommandTable, ...}
        self.help_index = StateHelpIndex() 
        self.state_flags = {}
        
    def add_state(self, state_name,
                  global_cmds=None, global_filter=[],
                  allow_exits=False, allow_obj_cmds=False,
                  exit_command=False):
        """
        Creates a new game state. Each state has its own unique set of commands and
        can change how the game works. 

        state_name (str) : name of the state. If state already exists,
                           it will be overwritten.
        global_cmds(None or str): A flag to control imports of global commands into the state.
                      None   - Do not include any global commands in this state (default).
                      'all'     - Include all global commands from GLOBAL_CMD_TABLE,
                                  without using the global_filter argument at all. 
                      'include' - Include only global commands from GLOBAL_CMD_TABLE
                                  that are listed in global_filter. OBS:the global
                                  'help' command will always automatically be included. 
                      'exclude' - Include all global commands from GLOBAL_CMD_TABLE
                                  /except/ those listed in global_filter.
        global_filter (list): This should be a list of command strings (like
                      ['look', '@create',...]). Depending on the global_cmds setting, this
                      list is used to control which global commands are imported from
                      GLOBAL_CMD_TABLE into this state.
        allow_exits (bool): Evennia works so that an exit might have any name. A user
                      may just write e.g. 'outside' and if there is an exit in the room
                      named 'outside' the engine interprets this as a command for
                      traversing this exit. Normally a state disables this check, so
                      a user may not traverse exits while in the state. This switch turns
                      the check back on and allows users to move around also
                      while in the state. Observe that to make this work well you will
                      have to have at least a 'look' command defined in your state
                      (since this is called whenever you enter a new room).
        allow_obj_cmds (bool): Any object in a room can have its own command table assigned
                      to it (such as the ability to 'play' on a flute). Normally these
                      commands are not accessible while in a state. This switch
                      allows the interpreter to also search objects for commands and will
                      use them before using any same-named state commands. 
        exit_command(bool): Adds a special '@exit' command that immediately quits the
                      state. This is useful for testing. Many states might however require
                      special conditions or clean-up operations before allowing a player
                      to exit (e.g. combat states and text editors), in which case this
                      feature should be turned off and handled by custom exit commands.
        """
        
        state_name = state_name.strip()
        #create state
        self.state_table[state_name] = CommandTable()        
    
        if global_cmds != None:            
            if global_cmds == 'all':
                f = lambda c: True
            elif global_cmds == 'include':
                f = lambda c: c in global_filter                    
                if not 'help' in global_filter:
                    global_filter.append('help')
            elif global_cmds == 'exclude':
                f = lambda c: c not in global_filter
            else:
                log_errmsg("ERROR: in statetable, state %s: Unknown global_cmds flag '%s'." %
                           (state_name, global_cmds))
                return            
            for cmd in filter(f,GLOBAL_CMD_TABLE.ctable.keys()): 
                self.state_table[state_name].ctable[cmd] = \
                                 GLOBAL_CMD_TABLE.get_command_tuple(cmd)
            if exit_command:
                #if we import global commands, we use the normal help index; thus add
                #help for @exit to the global index. 
                self.state_table[state_name].add_command("@exit",
                                                         cmd_state_exit,
                                                         auto_help=True)
        else:
            #when no global cmds are imported, we create a small custom
            #state-based help index instead
            self.help_index.add_state(state_name)
            self.add_command(state_name,'help',cmd_state_help)

            if exit_command:                
                #add the @exit command
                self.state_table[state_name].add_command("@exit",
                                                         cmd_state_exit)
                self.help_index.add_state_help(state_name, "@exit",
                                               cmd_state_exit.__doc__)        
        #store special state flags
        self.state_flags[state_name] = {}
        self.state_flags[state_name]['exits'] = allow_exits
        self.state_flags[state_name]['obj_cmds'] = allow_obj_cmds

    def del_state(self, state_name):
        """
        Permanently deletes a state from the state table. Make sure no users are in
        the state upon calling this command. Note that setting an object to a
        non-existing state name is harmless, if the state does not exist the
        interpreter ignores it and assumes normal operation.
        Auto-created global help entries will have to be deleted manually.  
        """
        if self.state_table.has_key(state_name):
            del self.state_table[state_name]
        
                
    def del_command(self, state_name, command_string):
        """
        Deactivate a command within a state. This is mostly useful for states that
        also includes the full global command table, allowing for deactivating individual
        commands dynamically.
        
        state_name (str) : name of the state to delete a command from
        command_string (str) : command name to deactivate, e.g. @edit, look etc 
        """

        if not self.state_table[state_name].has_key():
            return
        try:
            del self.state_table[state_name].ctable[command_string]
            err = self.help_index.del_state_help(state_name,command_string)
        except KeyError:
            pass
        
    def add_command(self, state_name, command_string, function, priv_tuple=None,
                    extra_vals=None, auto_help=False, staff_help=False):
        """
        Transparently add commands to a specific state.
        This command is similar to the normal
        command_table.add_command() function. See example in gamesrc/commands/examples.

        state_name: (str) identifier of the state we tie this to.
        command_string: (str) command name to run, like look, @list etc
        function: (reference) command function object
        priv_tuple: (tuple) String tuple of permissions required for command.
        extra_vals: (dict) Dictionary to add to the Command object.        
        auto_help: (bool) Activate the auto_help system. By default this stores the
               help inside the statetable only (not in the main help database), and so
               the help entries are only available when the player is actually inside
               the state. Note that the auto_help system of state-commands do not
               support <<TOPIC:mytitle>> markup. 
        staff_help: (bool) Help entry is only available for staff players.
        """

        if state_name not in self.state_table.keys():
            log_errmsg("State %s is not a valid state for command %s. Not added." % \
                       (state_name, command_string))
            return 

        state_name = state_name.strip()
        #handle auto-help for the state commands
        if auto_help:            
            if self.help_index.has_state(state_name):                
                #add the help text to state help index only, don't add
                #it to the global help index
                self.help_index.add_state_help(state_name,command_string,
                                               function.__doc__,
                                               staff_help=staff_help)    
                auto_help = False

        #finally add the new command to the state's command table                        
        self.state_table[state_name].add_command(command_string,
                                                 function, priv_tuple,
                                                 extra_vals,auto_help=auto_help,
                                                 staff_help=staff_help)        
            
    def get_cmd_table(self, state_name):
        """
        Return the command table for a particular state.
        """
        if self.state_table.has_key(state_name):
            return self.state_table[state_name]
        else:
            return None

    def get_state_flags(self, state_name):
        """
        Return the state flags for a particular state.        
        """
        if self.state_flags.has_key(state_name):
            return self.state_flags[state_name]['exits'],\
                   self.state_flags[state_name]['obj_cmds']
        else:
            return False, False
        
                   
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

    def has_state(self,state_name):
        return self.help_index.has_key(state_name)

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
        """Manually delete a help topic from state help system. Note that this is
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

    This command only works when inside certain special game 'states' (like a menu or
    editor or similar situations).

    It aborts what you were doing and force-exits back to the normal mode of
    gameplay. Some states might deactivate the @exit command for various reasons."""

    source_object = command.source_object
    source_object.clear_state()
    source_object.emit_to("... Exited.")
    source_object.execute_cmd('look')        
    

def cmd_state_help(command):
    """
    help <topic> (while in a special state)

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

#import this into modules
GLOBAL_STATE_TABLE = StateTable()
