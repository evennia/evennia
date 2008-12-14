"""
This is the command processing module. It is instanced once in the main
server module and the handle() function is hit every time a player sends
something.
"""
from traceback import format_exc
import time

from apps.objects.models import Object
import defines_global
import cmdtable
import logger
import comsys
from util import functions_general

class UnknownCommand(Exception):
    """
    Throw this when a user enters an an invalid command.
    """
    pass
    
class Command(object):
    # Reference to the master server object.
    server = None
    # The player session that the command originated from.
    session = None
    # The entire raw, un-parsed command.
    raw_input = None
    # Just the root command. IE: if input is "look dog", this is just "look".
    command_string = None
    # A list of switches in the form of strings.
    command_switches = []
    # The un-parsed argument provided. IE: if input is "look dog", this is "dog".
    command_argument = None
    
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
            (self.command_string, self.command_argument) = self.raw_input.split(' ', 1)
            self.command_argument = self.command_argument.strip()
            if self.command_argument == '':
                self.command_argument = None 
        except ValueError:
            """
            No arguments. IE: look, who.
            """
            self.command_string = self.raw_input
        finally:
            # Parse command_string for switches, regardless of what happens.
            self.parse_command_switches()
    
    def __init__(self, raw_input, server=None, session=None):
        self.server = server
        self.raw_input = raw_input
        self.session = session
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

def match_exits(pobject, searchstr):
    """
    See if we can find an input match to exits.
    """
    exits = pobject.get_location().get_contents(filter_type=defines_global.OTYPE_EXIT)
    return Object.objects.list_search_object_namestr(exits, 
                                                     searchstr, 
                                                     match_type="exact")

def handle(command):
    """
    Use the spliced (list) uinput variable to retrieve the correct
    command, or return an invalid command error.

    We're basically grabbing the player's command by tacking
    their input on to 'cmd_' and looking it up in the GenCommands
    class.
    """
    session = command.session
    server = command.server
    
    try:
        # TODO: Protect against non-standard characters.
        if command.raw_input == '':
            # Nothing sent in of value, ignore it.
            return

        # Now we'll see if the user is using an alias. We do a dictionary lookup,
        # if the key (the player's command_string) doesn't exist on the dict, 
        # just keep the command_string the same. If the key exists, its value
        # replaces the command_string. For example, sa -> say.
        command.command_string = server.cmd_alias_list.get(
                                                command.command_string,
                                                command.command_string)

        # This will hold the reference to the command's function.
        cmd = None

        if session.logged_in:
            # Store the timestamp of the user's last command.
            session.cmd_last = time.time()

            # Lets the users get around badly configured NAT timeouts.
            if command.command_string == 'idle':
                return

            # Increment our user's command counter.
            session.cmd_total += 1
            # Player-visible idle time, not used in idle timeout calcs.
            session.cmd_last_visible = time.time()

            # Just in case. Prevents some really funky-case crashes.
            if len(command.command_string) == 0:
                raise UnknownCommand

            if comsys.plr_has_channel(session, command.command_string, 
                alias_search=True, return_muted=True):
                
                calias = command.command_string
                cname = comsys.plr_cname_from_alias(session, calias)
                
                if command.command_argument == "who":
                    comsys.msg_cwho(session, cname)
                    return
                elif command.command_argument == "on":
                    comsys.plr_chan_on(session, calias)
                    return
                elif command.command_argument == "off":
                    comsys.plr_chan_off(session, calias)
                    return
                elif command.command_argument == "last":
                    comsys.msg_chan_hist(session, cname)
                    return
                    
                second_arg = "%s=%s" % (cname, command.command_argument)
                command.command_string = "@cemit"
                command.command_switches = ["sendername", "quiet"]

            # Get the command's function reference (Or False)
            cmdtuple = cmdtable.GLOBAL_CMD_TABLE.get_command_tuple(command.command_string)
            if cmdtuple:
                # If there is a permissions element to the entry, check perms.
                if cmdtuple[1]:
                    if not session.get_pobject().user_has_perm_list(cmdtuple[1]):
                        session.msg(defines_global.NOPERMS_MSG)
                        return
                # If flow reaches this point, user has perms and command is ready.
                cmd = cmdtuple[0]
                    
        else:
            # Not logged in, look through the unlogged-in command table.
            cmdtuple = cmdtable.GLOBAL_UNCON_CMD_TABLE.get_command_tuple(command.command_string)
            if cmdtuple:
                cmd = cmdtuple[0]

        # Debugging stuff.
        #session.msg("ROOT : %s" % (parsed_input['root_cmd'],))
        #session.msg("SPLIT: %s" % (parsed_input['splitted'],))
        
        if callable(cmd):
            try:
                cmd(command)
            except:
                session.msg("Untrapped error, please file a bug report:\n%s" % (format_exc(),))
                logger.log_errmsg("Untrapped error, evoker %s: %s" %
                    (session, format_exc()))
            return

        if session.logged_in:
            # If we're not logged in, don't check exits.
            pobject = session.get_pobject()
            exit_matches = match_exits(pobject, command.command_string)
            if exit_matches:
                targ_exit = exit_matches[0]
                if targ_exit.get_home():                   
                    # SCRIPT: See if the player can traverse the exit
                    if not targ_exit.scriptlink.default_lock({
                        "pobject": pobject
                    }):
                        session.msg("You can't traverse that exit.")
                    else:
                        pobject.move_to(targ_exit.get_home())
                        session.execute_cmd("look")
                else:
                    session.msg("That exit leads to nowhere.")
                return

        # If we reach this point, we haven't matched anything.     
        raise UnknownCommand

    except UnknownCommand:
        session.msg("Huh?  (Type \"help\" for help.)")

