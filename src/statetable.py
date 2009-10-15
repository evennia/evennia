"""
State table 

The state system allows the player to enter states/modes where only a
special set of commands are available. This can be used for all sorts
of useful things: - in-game menus (picking an option from a list, much
more powerful than using 'rooms') - inline text editors (entering text
into a buffer) - npc conversation (select replies) - only allowing
certain commands in special situations (e.g. special attack commands
when in 'combat' mode) - adding special commands to the normal set
(e.g. a 'howl' command when in 'werewolf' state) - deactivating
certain commands (e.g. removing the 'say' command in said 'werewolf'
state ...)

Basically the GLOBAL_STATE_TABLE contains a dict with command tables
keyed after the name of the state. To use, a function must set the
'state' variable on a player object using the obj.set_state()
function. The GLOBAL_STATE_TABLE will then be searched by the command
handler and if the state is defined its command table is used instead
of the normal global command table.

The state system is pluggable, in the same way that commands are added
to the global command table, commands are added to the
GLOBAL_STATE_TABLE using add_command supplying in addition the name of
the state. The main difference is that new states must first be
created using the GLOBAL_STATE_TABLE.add_state() command. See examples
in game/gamesrc.
"""

from django.conf import settings
from cmdtable import CommandTable, GLOBAL_CMD_TABLE
from logger import log_errmsg
from src import defines_global
from  src.helpsys import helpsystem
from src.helpsys.models import HelpEntry

class StateTable(object):
    """
    This implements a variant of the command table handling states.
    """
    state_table = None

    def __init__(self):        
        self.state_table = {} #of the form {statename:CommandTable, ...}
        self.help_index = StateHelpIndex() 
        self.state_flags = {}
        
    def add_state(self, state_name,
                  global_cmds=None, global_filter=None,
                  allow_exits=False, allow_obj_cmds=False,
                  help_command=True, exit_command=False):
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

        #store special state flags
        self.state_flags[state_name] = {}
        self.state_flags[state_name]['globals'] = global_cmds
        self.state_flags[state_name]['exits'] = allow_exits
        self.state_flags[state_name]['obj_cmds'] = allow_obj_cmds
            
        if global_cmds == 'all':
            # we include all global commands
            func = lambda c: True
        elif global_cmds == 'include':
            # selective global inclusion
            func = lambda c: c in global_filter                    
            if not 'help' in global_filter:
                global_filter.append('help')
        elif global_cmds == 'exclude':
            # selective global exclusion
            func = lambda c: c not in global_filter
        else:
            # no global commands
            func = lambda c: False

        # add copies of the global command defs to the state's command table.
        for cmd in filter(func, GLOBAL_CMD_TABLE.ctable.keys()): 
            self.state_table[state_name].ctable[cmd] = \
                                GLOBAL_CMD_TABLE.get_command_tuple(cmd)
            
        # create a stand-alone state-based help index
        self.help_index.add_state(state_name)

        # if the auto-help command is not wanted, just make a custom command
        # overwriting this default 'help' command. Keeps 'info' as a way to have
        # both a custom help command and state auto-help; replace this too
        # to completely hide auto-help functionality in the state.
        self.add_command(state_name, 'help', cmd_state_help)
        self.add_command(state_name, 'info', cmd_state_help)
        
        if exit_command:                
            #add the @exit command
            self.state_table[state_name].add_command("@exit",
                                                     cmd_state_exit)
            self.help_index.add_state_help(state_name,
                                           "@exit",
                                           "General",
                                           cmd_state_exit.__doc__)
            
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
            self.help_index.del_state_help(state_name, command_string)
        except KeyError:
            pass
        
    def add_command(self, state_name, command_string, function, priv_tuple=None,
                    extra_vals=None, help_category="", priv_help_tuple=None):
        """
        Transparently add commands to a specific state.
        This command is similar to the normal
        command_table.add_command() function. See example in gamesrc/commands/examples.

        state_name: (str) identifier of the state we tie this to.
        command_string: (str) command name to run, like look, @list etc
        function: (reference) command function object
        priv_tuple: (tuple) String tuple of permissions required for command.
        extra_vals: (dict) Dictionary to add to the Command object.        

        Auto-help functionality: (only used if settings.HELP_AUTO_ENABLED=True) 
        help_category (str): An overall help category where auto-help will place 
                             the help entry. If not given, 'General' is assumed.
        priv_help_tuple (tuple) String tuple of permissions required to view this
                                help entry. If nothing is given, priv_tuple is used. 
        """

        if state_name not in self.state_table.keys():
            log_errmsg("State %s is not a valid state for command %s. Not added." % \
                       (state_name, command_string))
            return 

        state_name = state_name.strip()

        # handle the creation of an auto-help entry in the
        # stand-alone help index

        topicstr = command_string
        if not help_category:
            help_category = state_name
        help_category = help_category.capitalize()            

        self.help_index.add_state_help(state_name,
                                       topicstr,
                                       help_category,
                                       function.__doc__,
                                       priv_help_tuple)    
                
        # finally add the new command to the state's command table

        self.state_table[state_name].add_command(command_string,
                                                 function,
                                                 priv_tuple,
                                                 extra_vals,
                                                 help_category,
                                                 priv_help_tuple,
                                                 auto_help_override=False)        
            
    def get_cmd_table(self, state_name):
        """
        Return the command table for a particular state.
        """
        if self.state_table.has_key(state_name):
            return self.state_table[state_name]
        else:
            return None

    def get_exec_rights(self, state_name):
        """
        Used by the cmdhandler. Accesses the relevant state flags
        concerned with execution access for a particular state.        
        """
        if self.state_flags.has_key(state_name):
            return self.state_flags[state_name]['exits'], \
                   self.state_flags[state_name]['obj_cmds']                  
        else:
            return False, False, False
                           
class StateHelpIndex(object):
    """
    Handles the dynamic state help system. This is
    a non-db based help system intended for the special
    commands associated with a state.

    The system gives preference to help matches within
    the state, but defers to the normal, global help
    system when it fails to find a help entry match.
    """
    help_index = None
    def __init__(self):
        self.help_index = {}

    def add_state(self, state_name):
        "Create a new state"
        self.help_index[state_name] = {}

    def has_state(self, state_name):
        "Checks if we have this state"
        return self.help_index.has_key(state_name)

    def add_state_help(self, state, topicstr, help_category,
                       help_text, priv_help_tuple=()):
        """
        Store help for a command under a certain state.
        Supports [[Title, category, (priv_tuple)]] markup
        """
        
        if not self.help_index.has_key(state):
            return 
        # produce nicely formatted help entries, taking markup
        # into account.
        topics = helpsystem.edithelp.format_help_entry(topicstr,
                                                       help_category,
                                                       help_text,
                                                       priv_help_tuple)         
        # store in state's dict-based database
        for topic in topics:
            self.help_index[state][topic[0]] = topic
       
    def get_state_help(self, caller, state, command):
        """
        Get help for a particular command within a state.
        """
        if self.help_index.has_key(state) and \
               self.help_index[state].has_key(command):
            # this is a state help entry.
            help_tuple = self.help_index[state][command]
            # check permissions
            if help_tuple and help_tuple[2]:
                if help_tuple[3] and not caller.has_perm_list(help_tuple[3]):
                    return None
                return help_tuple[2]
            else:
                return None

        
    def get_state_index(self, state):
        "list all help topics for a state"
        if self.help_index.has_key(state):                        
            tuples = self.help_index[state].items()
            items  = [tup[0] for tup in tuples]            
            table = helpsystem.viewhelp.make_table(items, 6)            
            return table 

# default commands available for all special states. These
# are added to states during the state initialization if
# the proper flags are set. 

def cmd_state_exit(command):
    """
    @exit - exit from a state

    Usage:
      @exit 

    This command only works when inside certain special game 'states'
    (like a menu or editor or similar situations).

    It aborts what you were doing and force-exits back to the normal
    mode of gameplay. Some states might deactivate the @exit command
    for various reasons.
    """
    source_object = command.source_object
    source_object.clear_state()
    source_object.emit_to("... Exited.")
    source_object.execute_cmd('look')        
    

    ## In-state help system. This is NOT tied to the normal help
    ## system and is not stored in the database. It is intended as a quick
    ## reference for users when in the state; if you want a detailed description
    ## of the state itself, you should probably add it to the main help system
    ## so the user can read it at any time.
    ## If you don't want to use the auto-system, turn off auto_help
    ## for all commands in the state. You could then for example make a custom help command
    ## that displays just a short help summary page instead.

    ## Note that at this time we are not displaying categories in the state help system;
    ## (although they are stored). Instead the state itself is treated as a
    ## category in itself.

def cmd_state_help(command):
    """
    help - view help database

    Usage:
      help <topic>

    Shows the available help on <topic>. Use without a topic
    to get the index. 
    """

    source_object = command.source_object
    args = command.command_argument
    switches = command.command_switches

    help_index = GLOBAL_STATE_TABLE.help_index
    state = source_object.get_state()
    
    if not args:
        # first show the normal help index
        source_object.execute_cmd("help", ignore_state=True)

        text = help_index.get_state_index(state)        
        if text:
            # Try to list the state-specific help entries after the main list
            string = "\n%s%s%s\n\r\n\r%s" % ("---", " Help topics for %s: " % \
                                             state.capitalize(), "-"*(30-len(state)), text)                
            source_object.emit_to(string)
        return

    # try to first find a matching state help topic, then defer to global help
    topicstr = args.strip()
    helptext = help_index.get_state_help(source_object, state, topicstr)
    if helptext:
        source_object.emit_to("\n%s" % helptext)
    else:
        source_object.execute_cmd("help %s" % topicstr, ignore_state=True)

#import this instance into your modules
GLOBAL_STATE_TABLE = StateTable()
