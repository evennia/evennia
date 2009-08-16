"""
This is the command processing module. It is instanced once in the main
server module and the handle() function is hit every time a player sends
something.
"""
import time
from traceback import format_exc
from django.contrib.contenttypes.models import ContentType
import defines_global
import cmdtable
import statetable
import logger
import comsys
import alias_mgr

class UnknownCommand(Exception):
    """
    Throw this when a user enters an an invalid command.
    """
    pass

class CommandNotInState(Exception):
    """
    Throw this when a user tries a global command that exists, but
    don't happen to be defined in the current game state. 
    err_string: The error string returned to the user.
    """
    def __init__(self,err_string):
        self.err_string = err_string

class ExitCommandHandler(Exception):
    """
    Thrown when something happens and it's time to exit the command handler.
    """
    pass
    
class Command(object):
    # The source object that the command originated from.
    source_object = None
    # The session that the command originated from (optional)
    session = None
    # The entire raw, un-parsed command.
    raw_input = None
    # Just the root command. IE: if input is "look dog", this is just "look".
    command_string = None
    # A list of switches in the form of strings.
    command_switches = []
    # The un-parsed argument provided. IE: if input is "look dog", this is "dog".
    command_argument = None
    # A reference to the command function looked up in a command table.
    command_function = None
    # An optional dictionary that is passed through the command table as extra_vars.
    extra_vars = None
    
    def parse_command_switches(self):
        """
        Splits any switches out of a command_string into the command_switches
        list, and yanks the switches out of the original command_string.
        """
        splitted_command = self.command_string.split('/')
        self.command_switches = splitted_command[1:]
        self.command_string = splitted_command[0]
    
    def parse_command(self):
        """
        Breaks the command up into the main command string, a list of switches,
        and a string containing the argument provided with the command. More
        specific processing is left up to the individual command functions.
        """
        try:
            """
            Break the command in half into command and argument. If the
            command string can't be parsed, it has no argument and is
            handled by the except ValueError block below.
            """
            # Lop off the return at the end.
            self.raw_input = self.raw_input.strip('\r')
            # Break the command up into the root command and its arguments.
            (self.command_string, self.command_argument) = self.raw_input.split(' ', 1)
            # Yank off trailing and leading spaces.
            self.command_argument = self.command_argument.strip()
            self.command_string = self.command_string.strip()
            """
            This is a really important behavior to note. If the user enters
            anything other than a string with some character in it, the value
            of the argument is None, not an empty string.
            """
            if self.command_string == '':
                self.command_string = None
            if self.command_argument == '':
                self.command_argument = None
                
            if self.command_string == None:
                """
                This prevents any bad stuff from happening as a result of
                trying to further parse a None object.
                """
                return 
        except ValueError:
            """
            No arguments. IE: look, who.
            """
            self.command_string = self.raw_input

        # Parse command_string for switches, regardless of what happens.
        self.parse_command_switches()
    
    def __init__(self, source_object, raw_input, session=None):
        """
        Instantiates the Command object and does some preliminary parsing.
        """
        self.raw_input = raw_input
        self.source_object = source_object
        self.session = session
        # The work starts here.
        self.parse_command()
        
    def arg_has_target(self):
        """
        Returns true if the argument looks to be target-style. IE:
        page blah=hi
        kick ball=north
        """
        return "=" in self.command_argument
    
    def get_arg_targets(self, delim=','):
        """
        Returns a list of targets from the argument. These happen before
        the '=' sign and may be separated by a delimiter.
        """
        # Make sure we even have a target (= sign).
        if not self.arg_has_target():
            return None
        
        target = self.command_argument.split('=', 1)[0]
        return [targ.strip() for targ in target.split(delim)]
    
    def get_arg_target_value(self):
        """
        In a case of something like: page bob=Hello there, the target is "bob",
        while the value is "Hello there". This function returns the portion
        of the command that takes place after the first equal sign.
        """
        # Make sure we even have a target (= sign).
        if not self.arg_has_target():
            return None
        
        return self.command_argument.split('=', 1)[1]

def match_idle(command):
    """
    Matches against the 'idle' command. It doesn't actually do anything, but it
    lets the users get around badly configured NAT timeouts that would cause
    them to drop if they don't send or receive something from the connection
    for a while.
    """
    if command.session and command.command_string != 'idle' \
                       and command.command_string != None:
        # Anything other than an 'idle' command or a blank return
        # updates the public-facing idle time for the session.
        command.session.count_command(silently=False)
    elif command.session:
        # User is hitting IDLE command. Don't update their publicly
        # facing idle time, drop out of command handler immediately.
        command.session.count_command(silently=True)
        raise ExitCommandHandler

        
def match_alias(command):
    """
    Checks to see if the entered command matches an alias. If so, replaces
    the command_string with the correct command.

    We do a dictionary lookup. If the key (the player's command_string) doesn't 
    exist on the dict, just keep the command_string the same. If the key exists, 
    its value replaces the command_string. For example, sa -> say.
    """
    # See if there's an entry in the global alias table.
    command.command_string = alias_mgr.CMD_ALIAS_LIST.get(
                                            command.command_string,
                                            command.command_string)
    
    def get_aliased_message():
        """
        Convenience sub-function to combine the lopped off command string
        and arguments for posing, saying, and nospace posing aliases.
        """
        if not command.command_argument:
            return command.command_string[1:]
        else:
            return "%s %s" % (command.command_string[1:], 
                              command.command_argument)
        
    # Match against the single-character aliases of MUX/MUSH-dom.
    first_char = command.command_string[0]
    # Shortened say alias.
    if first_char == '"':
        command.command_argument = get_aliased_message()
        command.command_string = "say"
    # Shortened pose alias.
    elif first_char == ':':
        command.command_argument = get_aliased_message()
        command.command_string = "pose"
#        command.command_string = "emote"
    # Pose without space alias.
    elif first_char == ';':
        command.command_argument = get_aliased_message()
        command.command_string = "pose"
        command.command_switches.insert(0, "nospace")
    
def match_channel(command):
    """
    Match against a comsys channel or comsys command. If the player is talking
    over a channel, replace command_string with @cemit. If they're entering
    a channel manipulation command, perform the operation and kill the things
    immediately with a True value sent back to the command handler.
    
    This only works with PLAYER objects at this point in time.
    """
    if command.session and comsys.plr_has_channel(command.session, 
        command.command_string, alias_search=True, return_muted=True):
        
        calias = command.command_string
        cname = comsys.plr_cname_from_alias(command.session, calias)
        
        if command.command_argument == "who":
            comsys.msg_cwho(command.source_object, cname)
            raise ExitCommandHandler
        elif command.command_argument == "on":
            comsys.plr_chan_on(command.session, calias)
            raise ExitCommandHandler
        elif command.command_argument == "off":
            comsys.plr_chan_off(command.session, calias)
            raise ExitCommandHandler
        elif command.command_argument == "last":
            comsys.msg_chan_hist(command.source_object, cname)
            raise ExitCommandHandler
            
        second_arg = "%s=%s" % (cname, command.command_argument)
        command.command_string = "@cemit"
        command.command_switches = ["sendername", "quiet"]
        command.command_argument = second_arg
        return True

def match_exits(command,test=False):
    """
    See if we can find an input match to exits.
    command - the command we are testing for.
              if a match, move obj and exit
    test    - just return Truee if it is an exit command,
              do not move the object there.              
    """
    # If we're not logged in, don't check exits.
    source_object = command.source_object
    location = source_object.get_location()
    
    if location == None:
        logger.log_errmsg("cmdhandler.match_exits(): Object '%s' has no location." % 
                          source_object)
        return
    
    exits = location.get_contents(filter_type=defines_global.OTYPE_EXIT)
    Object = ContentType.objects.get(app_label="objects", 
                                     model="object").model_class()
    exit_matches = Object.objects.list_search_object_namestr(exits, 
                                                     command.command_string, 
                                                     match_type="exact")
    if exit_matches:
        if test:
            return True
        
        # Only interested in the first match.
        targ_exit = exit_matches[0]
        # An exit's home is its destination. If the exit has a None home value,
        # it's not traversible.
        if targ_exit.get_home():                   
            # SCRIPT: See if the player can traverse the exit
            if not targ_exit.scriptlink.default_lock(source_object):
                source_object.emit_to("You can't traverse that exit.")
            else:
                source_object.move_to(targ_exit.get_home())
        else:
            source_object.emit_to("That exit leads nowhere.")
        # We found a match, kill the command handler.
        raise ExitCommandHandler
    
               
def command_table_lookup(command, command_table, eval_perms=True,test=False):
    """
    Performs a command table lookup on the specified command table. Also
    evaluates the permissions tuple.
    The test flag only checks without manipulating the command
    """
    # Get the command's function reference (Or False)
    cmdtuple = command_table.get_command_tuple(command.command_string)
    if cmdtuple:
        if test:
            return True
        # If there is a permissions element to the entry, check perms.
        if eval_perms and cmdtuple[1]:
            if not command.source_object.has_perm_list(cmdtuple[1]):
                command.source_object.emit_to(defines_global.NOPERMS_MSG)
                raise ExitCommandHandler
        # If flow reaches this point, user has perms and command is ready.
        command.command_function = cmdtuple[0]
        command.extra_vars = cmdtuple[2]
        return True

        
def match_neighbor_ctables(command,test=False):
    """
    Looks through the command tables of neighboring objects for command
    matches.
    test mode just checks if the command is a match, without manipulating
      any commands. 
    """
    source_object = command.source_object
    if source_object.location != None:
        neighbors = source_object.location.get_contents()
        for neighbor in neighbors:
            if command_table_lookup(command,
                                    neighbor.scriptlink.command_table, test=test):
                # If there was a command match, set the scripted_obj attribute
                # for the script parent to pick up.
                if test:
                    return True
                command.scripted_obj = neighbor
                return True
    else:
        #no matches
        return False

def handle(command):
    """
    Use the spliced (list) uinput variable to retrieve the correct
    command, or return an invalid command error.

    We're basically grabbing the player's command by tacking
    their input on to 'cmd_' and looking it up in the GenCommands
    class.
    """
    try:
        # TODO: Protect against non-standard characters.
        if not command.command_string:
            # Nothing sent in of value, ignore it.
            raise ExitCommandHandler

        state = None #no state by default
        
        if command.session and not command.session.logged_in:
            # Not logged in, look through the unlogged-in command table.
            command_table_lookup(command, cmdtable.GLOBAL_UNCON_CMD_TABLE,eval_perms=False)
        else:
            # User is logged in. 
            # Match against the 'idle' command.            
            match_idle(command)
            # See if this is an aliased command.
            match_alias(command)

            state = command.source_object.get_state()
            state_cmd_table = statetable.GLOBAL_STATE_TABLE.get_cmd_table(state)

            if state and state_cmd_table:            
                # Caller is in a special state.                

                state_allow_exits, state_allow_obj_cmds = \
                        statetable.GLOBAL_STATE_TABLE.get_state_flags(state)    

                state_lookup = True
                if match_channel(command):
                    command_table_lookup(command, cmdtable.GLOBAL_CMD_TABLE)
                    state_lookup = False
                # See if the user is trying to traverse an exit.                
                if state_allow_exits:
                    match_exits(command)                         
                # check if this is a command defined on a nearby object.
                if state_allow_obj_cmds and match_neighbor_ctables(command):
                    state_lookup = False
                #if nothing has happened to change our mind, search the state table.    
                if state_lookup:                    
                    command_table_lookup(command, state_cmd_table)
            else:
                # Not in a state. Normal operation.
                state = None #make sure, in case the object had a malformed statename.

                # Check if the user is using a channel command.                    
                match_channel(command)
                # See if the user is trying to traverse an exit.                
                match_exits(command)
                # check if this is a command defined on a nearby object 
                if not match_neighbor_ctables(command):
                    command_table_lookup(command, cmdtable.GLOBAL_CMD_TABLE)
                                        
        
        """
        By this point, we assume that the user has entered a command and not
        something like a channel or exit. Make sure that the command's
        function reference is value and try to run it.
        """
        if callable(command.command_function):
            try:
                # Move to the command function, passing the command object.
                command.command_function(command)
            except:
                """
                This is a crude way of trapping command-related exceptions
                and showing them to the user and server log. Once the
                codebase stabilizes, we will probably want something more
                useful or give them the option to hide exception values.
                """
                if command.source_object:
                    command.source_object.emit_to("Untrapped error, please file a bug report:\n%s" % 
                        (format_exc(),))
                    logger.log_errmsg("Untrapped error, evoker %s: %s" %
                        (command.source_object, format_exc()))
                # Prevent things from falling through to UnknownCommand.
                raise ExitCommandHandler
        else:
            # If we reach this point, we haven't matched anything.     

            if state: 
                # if we are in a state, it could be that the command exists, but
                # it is temporarily not available. If so, we want a different error message.
                if match_exits(command,test=True):
                    raise CommandNotInState("Movement is not possible right now.")
                if match_neighbor_ctables(command,test=True):
                    raise CommandNotInState("You can not do that at the moment.")
                if command_table_lookup(command,cmdtable.GLOBAL_CMD_TABLE,test=True):
                    raise CommandNotInState("This command is not available right now.")
            raise UnknownCommand

    except ExitCommandHandler:
        # When this is thrown, just get out and do nothing. It doesn't mean
        # something bad has happened.
        pass
    except CommandNotInState, e:
        # The command exists, but not in the current state
        if command.source_object != None:
            # The logged-in error message
            command.source_object.emit_to(e.err_string)
        elif command.session != None:
            # States are not available before login, so this should never
            # be reached. But better safe than sorry. 
            command.session.msg("%s %s" % (e.err_string," (Type \"help\" for help.)"))
        else:            
            pass    
    except UnknownCommand:
        # Default fall-through. No valid command match.
        if command.source_object != None:
            # A typical logged in or object-based error message.            
            command.source_object.emit_to("Huh?  (Type \"help\" for help.)")
        elif command.session != None:
            # This is hit when invalid commands are sent at the login screen
            # primarily. Also protect against bad things in odd cases.
            command.session.msg("Huh?  (Type \"help\" for help.)")
        else:
            # We should never get to this point, but if we do, don't freak out.
            pass
