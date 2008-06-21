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

def match_exits(pobject, searchstr):
    """
    See if we can find an input match to exits.
    """
    exits = pobject.get_location().get_contents(filter_type=4)
    return Object.objects.list_search_object_namestr(exits, searchstr, match_type="exact")

def parse_command(command_string):
    """
    Tries to handle the most common command strings and returns a dictionary with various data.
    Common command types:
    - Complex:
        @pemit[/option] <target>[/option]=<data>
    - Simple:
        look
        look <target>

    I'm not married to either of these terms, but I couldn't think of anything better.  If you can, lets change it :)

    The only cases that I haven't handled is if someone enters something like:
        @pemit <target> <target>/<switch>=<data>
            - Ends up considering both targets as one with a space between them, and the switch as a switch.
        @pemit <target>/<switch> <target>=<data>
            - Ends up considering the first target a target, and the second target as part of the switch.


    """
    # Each of the bits of data starts off as None, except for the raw, original
    # command
    parsed_command = dict(
            raw_command=command_string,
            data=None,
            original_command=None,
            original_targets=None,
            base_command=None,
            command_switches=None,
            targets=None,
            target_switches=None
            )
    try:
        # If we make it past this next statement, then this is what we 
        # consider a complex command
        (command_parts, data) = command_string.split('=', 1)
        parsed_command['data'] = data
        # First we deal with the command part of the command and break it
        # down into the base command, along with switches
        # If we make it past the next statement, then they must have
        # entered a command like:
        #      p =<data>
        # So we should probably just let it get caught by the ValueError
        # again and consider it a simple command
        (total_command, total_targets) = command_parts.split(' ', 1)
        parsed_command['original_command'] = total_command
        parsed_command['original_targets'] = total_targets
        split_command = total_command.split('/')
        parsed_command['base_command'] = split_command[0]
        parsed_command['command_switches'] = split_command[1:]
        # Now we move onto the target data
        try:
            # Look for switches- if they give target switches, then we don't
            # accept multiple targets
            (target, switch_string) = total_targets.split('/', 1)
            parsed_command['targets'] = [target]
            parsed_command['target_switches'] = switch_string.split('/')
        except ValueError:
            # Alright, no switches, so lets consider multiple targets
            parsed_command['targets'] = total_targets.split()
    except ValueError:
        # Ok, couldn't find an =, so not a complex command
        try:
            (command, data) = command_string.split(' ', 1)
            parsed_command['base_command'] = command
            parsed_command['data'] = data
        except ValueError:
            # No arguments
            # ie:
            #    - look
            parsed_command['base_command'] = command_string
    return parsed_command

def handle(cdat):
    """
    Use the spliced (list) uinput variable to retrieve the correct
    command, or return an invalid command error.

    We're basically grabbing the player's command by tacking
    their input on to 'cmd_' and looking it up in the GenCommands
    class.
    """
    session = cdat['session']
    server = cdat['server']
    
    try:
        # TODO: Protect against non-standard characters.
        if cdat['uinput'] == '':
            return

        parsed_input = {}
        parsed_input['parsed_command'] = parse_command(cdat['uinput'])

        # First we split the input up by spaces.
        parsed_input['splitted'] = cdat['uinput'].split()
        # Now we find the root command chunk (with switches attached).
        parsed_input['root_chunk'] = parsed_input['splitted'][0].split('/')
        # And now for the actual root command. It's the first entry in root_chunk.
        parsed_input['root_cmd'] = parsed_input['root_chunk'][0].lower()
        # Keep around the full, raw input in case a command needs it
        cdat['raw_input'] = cdat['uinput']

        # Now we'll see if the user is using an alias. We do a dictionary lookup,
        # if the key (the player's root command) doesn't exist on the dict, we
        # don't replace the existing root_cmd. If the key exists, its value
        # replaces the previously splitted root_cmd. For example, sa -> say.
        alias_list = server.cmd_alias_list
        parsed_input['root_cmd'] = alias_list.get(parsed_input['root_cmd'],parsed_input['root_cmd'])

        # This will hold the reference to the command's function.
        cmd = None

        if session.logged_in:
            # Store the timestamp of the user's last command.
            session.cmd_last = time.time()

            # Lets the users get around badly configured NAT timeouts.
            if parsed_input['root_cmd'] == 'idle':
                return

            # Increment our user's command counter.
            session.cmd_total += 1
            # Player-visible idle time, not used in idle timeout calcs.
            session.cmd_last_visible = time.time()

            # Just in case. Prevents some really funky-case crashes.
            if len(parsed_input['root_cmd']) == 0:
                raise UnknownCommand

            # Shortened say alias.
            if parsed_input['root_cmd'][0] == '"':
                parsed_input['splitted'].insert(0, "say")
                parsed_input['splitted'][1] = parsed_input['splitted'][1][1:]
                parsed_input['root_cmd'] = 'say'
            # Shortened pose alias.
            elif parsed_input['root_cmd'][0] == ':':
                parsed_input['splitted'].insert(0, "pose")
                parsed_input['splitted'][1] = parsed_input['splitted'][1][1:]
                parsed_input['root_cmd'] = 'pose'
            # Pose without space alias.
            elif parsed_input['root_cmd'][0] == ';':
                parsed_input['splitted'].insert(0, "pose/nospace")
                parsed_input['root_chunk'] = ['pose', 'nospace']
                parsed_input['splitted'][1] = parsed_input['splitted'][1][1:]
                parsed_input['root_cmd'] = 'pose'
            # Channel alias match.
            elif comsys.plr_has_channel(session, 
                parsed_input['root_cmd'], 
                alias_search=True, 
                return_muted=True):
                
                calias = parsed_input['root_cmd']
                cname = comsys.plr_cname_from_alias(session, calias)
                cmessage = ' '.join(parsed_input['splitted'][1:])
                
                if cmessage == "who":
                    comsys.msg_cwho(session, cname)
                    return
                elif cmessage == "on":
                    comsys.plr_chan_on(session, calias)
                    return
                elif cmessage == "off":
                    comsys.plr_chan_off(session, calias)
                    return
                elif cmessage == "last":
                    comsys.msg_chan_hist(session, cname)
                    return
                    
                second_arg = "%s=%s" % (cname, cmessage)
                parsed_input['splitted'] = ["@cemit/sendername", second_arg]
                parsed_input['root_chunk'] = ['@cemit', 'sendername', 'quiet']
                parsed_input['root_cmd'] = '@cemit'

            # Get the command's function reference (Or False)
            cmdtuple = cmdtable.return_cmdtuple(parsed_input['root_cmd'])
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
            cmdtuple = cmdtable.return_cmdtuple(parsed_input['root_cmd'], unlogged_cmd=True)
            if cmdtuple:
                cmd = cmdtuple[0]

        # Debugging stuff.
        #session.msg("ROOT : %s" % (parsed_input['root_cmd'],))
        #session.msg("SPLIT: %s" % (parsed_input['splitted'],))
        
        if callable(cmd):
            cdat['uinput'] = parsed_input
            try:
                cmd(cdat)
            except:
                session.msg("Untrapped error, please file a bug report:\n%s" % (format_exc(),))
                logger.log_errmsg("Untrapped error, evoker %s: %s" %
                    (session, format_exc()))
            return

        if session.logged_in:
            # If we're not logged in, don't check exits.
            pobject = session.get_pobject()
            exit_matches = match_exits(pobject, ' '.join(parsed_input['splitted']))
            if exit_matches:
                targ_exit = exit_matches[0]
                if targ_exit.get_home():
                    cdat['uinput'] = parsed_input
                    
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

