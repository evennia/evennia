"""
This is the command processing module. It is instanced once in the main
server module and the handle() function is hit every time a player sends
something.
"""
#import time
from traceback import format_exc
from django.conf import settings
#from django.contrib.contenttypes.models import ContentType
from objects.models import Object
import defines_global
import cmdtable
import statetable
import logger
import comsys
import alias_mgr

COMMAND_MAXLEN = settings.COMMAND_MAXLEN

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
    # list of tuples for possible multi-space commands and their arguments
    command_alternatives = None
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

        The command can come in two forms:
         command/switches arg
         command_with_spaces arg  

        The first form is the normal one, used for administration and other commands
        that benefit from the use of switches and options. The drawback is that it
        can only consist of one single word (no spaces).
        The second form, which does not accept switches, allows for longer command
        names (e.g. 'press button' instead of pressbutton) and is mainly useful for
        object-based commands for roleplay, puzzles etc. 
        """
        if not self.raw_input:
            return 
        
        # add a space after the raw input; this cause split() to always
        # create a list with at least two entries. 
        raw = "%s " % self.raw_input        
        cmd_words = raw.split(' ')
        try:
            if '/' in cmd_words[0]:
                # if we have switches we directly go for the first command form.
                command_string, command_argument = \
                                (inp.strip() for inp in raw.split(' ', 1))
                if command_argument:
                    self.command_argument = command_argument
                if command_string:
                    # we have a valid command, store and parse switches.
                    self.command_string = command_string            
                    self.parse_command_switches()
            else:
                # no switches - we need to save a list of all possible command
                # names up to the max-length allowed.
                command_maxlen = min(COMMAND_MAXLEN, len(cmd_words))
                command_alternatives = []
                for spacecount in reversed(range(command_maxlen)):
                    # store all space-separated possible command names
                    # as tuples (commandname, args). They are stored with
                    # the longest possible name first. 
                    try:
                        command_alternatives.append( (" ".join([w.strip()
                                                                for w in cmd_words[:spacecount+1]]).strip(),
                                                      " ".join(cmd_words[spacecount+1:]).strip()) )
                    except IndexError:
                        continue 
                if command_alternatives:
                    # store alternatives. Store the one-word command
                    # as the default command name.
                    one_word_command = command_alternatives.pop()
                    self.command_string = one_word_command[0]
                    self.command_argument = one_word_command[1]
                    self.command_alternatives = command_alternatives 
        except IndexError:
            # this SHOULD only happen if raw_input is malformed
            # (like containing only control characters).
            pass
        

    def __init__(self, source_object, raw_input, session=None):
        """
        Instantiates the Command object and does some preliminary parsing.
        """
        # If we get a unicode string with un-recognizable characters, replace
        # them instead of throwing errors.
        self.raw_input = raw_input 
        if not isinstance(raw_input, unicode):
            self.raw_input = unicode(raw_input, errors='replace')           
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
    # Run aliasing on alternative command names (for commands with
    # spaces in them)
    if command.command_alternatives:
        command_alternatives = []
        for command_alternative in command.command_alternatives:
            # create correct command_alternative tuples for storage
            command_alternatives.append( (alias_mgr.CMD_ALIAS_LIST.get(
                                               command_alternative[0],
                                               command_alternative[0]),
                                          command_alternative[1]) )
        command.command_alternatives = command_alternatives
    
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
        if not command.command_argument:
            command.source_object.emit_to("What do you want to say?")
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
    # get all exits at location
    exits = location.get_contents(filter_type=defines_global.OTYPE_EXIT)
    
    # /not sure why this was done this way when one can import Object. 
    # Object = ContentType.objects.get(app_label="objects", 
    #                                 model="object").model_class()

    exit_matches = None 
    if command.command_alternatives:
        # we have command alternatives (due to spaces in command definition).
        # if so we replace the command_string appropriately.
        for cmd_alternative in command.command_alternatives:
            # the alternatives are ordered longest -> shortest.
            exit_matches = Object.objects.list_search_object_namestr(exits, 
                                                                     cmd_alternative[0],
                                                                     match_type="exact")
            if exit_matches:
                command.command_string = cmd_alternative[0]
                command.command_argument = cmd_alternative[1]
                break        
    if not exit_matches:
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
                lock_msg = targ_exit.get_attribute_value("lock_msg")
                if lock_msg:
                    source_object.emit_to(lock_msg)
                else:                    
                    source_object.emit_to("You can't traverse that exit.")
            else:
                source_object.move_to(targ_exit.get_home())
        else:
            source_object.emit_to("That exit leads nowhere.")
        # We found a match, kill the command handler.
        raise ExitCommandHandler
    
               
def command_table_lookup(command, command_table, eval_perms=True,
                         test=False, neighbor=None):
    """
    Performs a command table lookup on the specified command table. Also
    evaluates the permissions tuple.
    The test flag only checks without manipulating the command
    neighbor (object) If this is supplied, we are looking at a object table and
                      must check for locks.

    In the case of one-word commands with switches, this is a
    quick look-up. For non-switch commands the command might
    however consist of several words separated by spaces up to
    a certain max number of words. We don't know beforehand if one
    of these match an entry in this particular command table. We search
    them in order longest to shortest before deferring to the normal,
    one-word assumption. 
    """
    cmdtuple = None
    if command.command_alternatives:
        #print "alternatives:",command.command_alternatives
        #print command_table.ctable
        # we have command alternatives (due to spaces in command definition)
        for cmd_alternative in command.command_alternatives:
            # the alternatives are ordered longest -> shortest.
            cmdtuple = command_table.get_command_tuple(cmd_alternative[0])
            if cmdtuple:
                # we have a match, so this is the 'right' command to use
                # with this particular command table.
                command.command_string = cmd_alternative[0]
                command.command_argument = cmd_alternative[1]
                break 
    if not cmdtuple:
        # None of the alternatives match, go with the default one-word name
        cmdtuple = command_table.get_command_tuple(command.command_string)
    
    if cmdtuple:
        # if we get here we have found a command match in the table
        if test:
            # Check if this is just a test. 
            return True
        # Check uselocks
        if neighbor and not neighbor.scriptlink.use_lock(command.source_object):
            # send an locked error message only if lock_desc is defined
            lock_msg = neighbor.get_attribute_value("use_lock_msg")
            if lock_msg:
                command.source_object.emit_to(lock_msg)
                raise ExitCommandHandler
            return False
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
    location = source_object.get_location()
    if location:
        # get all objects, including the current room
        neighbors = location.get_contents()  + [location] + source_object.get_contents()
        for neighbor in neighbors:
            #print "neighbor:", neighbor 
            obj_cmdtable = neighbor.get_cmdtable()
            if obj_cmdtable and command_table_lookup(command, obj_cmdtable,
                                                 test=test,
                                                 neighbor=neighbor):

                # If there was a command match, set the scripted_obj attribute
                # for the script parent to pick up.
                if test:
                    return True
                command.scripted_obj = neighbor
                return True            
    # No matches
    return False

def handle(command, ignore_state=False):
    """
    Use the spliced (list) uinput variable to retrieve the correct
    command, or return an invalid command error.

    We're basically grabbing the player's command by tacking
    their input on to 'cmd_' and looking it up in the GenCommands
    class.

    ignore_state : ignore eventual statetable lookups completely.
    """
    try:
        # TODO: Protect against non-standard characters.
        if not command.command_string:
            # Nothing sent in of value, ignore it.
            raise ExitCommandHandler

        # No state by default.
        state = None 
        
        if command.session and not command.session.logged_in:
            # Not logged in, look through the unlogged-in command table.
            command_table_lookup(command, cmdtable.GLOBAL_UNCON_CMD_TABLE,
                                 eval_perms=False)
        else:
            # User is logged in. 
            # Match against the 'idle' command.            
            match_idle(command)
            # See if this is an aliased command.
            match_alias(command)

            state = command.source_object.get_state()
            state_cmd_table = statetable.GLOBAL_STATE_TABLE.get_cmd_table(state)

            if state and state_cmd_table and not ignore_state:            
                # Caller is in a special state.

                state_allow_exits, state_allow_obj_cmds = \
                        statetable.GLOBAL_STATE_TABLE.get_exec_rights(state)    

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
                state = None # make sure, in case the object had a malformed statename.
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
