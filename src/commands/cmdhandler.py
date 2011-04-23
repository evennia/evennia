"""
Command handler

This module contains the infrastructure for accepting commands on the
command line. The process is as follows: 

1) The calling object (caller) inputs a string and triggers the command parsing system.
2) The system checks the state of the caller - loggedin or not
3) Depending on the login/not state, it collects cmdsets from different sources:
     not logged in - uses the single cmdset in settings.CMDSET_UNLOGGEDIN
     normal - gathers command sets from many different sources (shown in dropping priority): 
           channels - all available channel names are auto-created into a cmdset, to allow 
                  for giving the channel name and have the following immediately
                  sent to the channel. The sending is performed by the CMD_CHANNEL
                  system command.
           exits - exits from a room are dynamically made into a cmdset for matching,
                  allowing the player to give just the name and thus traverse the exit.
                  If a match, the traversing is handled by the CMD_EXIT system command.
           object cmdsets - all objects at caller's location are scanned for non-empty
                  cmdsets.
           caller - the caller is searched for its currently active cmdset.
4) All the gathered cmdsets (if more than one) are merged into one using the cmdset priority rules. 
5) If no cmdsets where found, we raise NoCmdSet exception. This should not happen, at least the
   caller should have a default cmdset available at all times. --> Finished 
6) The raw input string is parsed using the parser defined by settings.CMDPARSER. It returns
   a special match object since a command may consist of many space-separated words and we 
   thus have to match them all.
7) If no command was supplied, we search the merged cmdset for system command CMD_NOINPUT 
   and branches to execute that.  --> Finished
8) We match the the match object against the merged cmdset and the eventual priorities given it
   by the parser. The result is a list of command matches tied to their respective match object. 
9) If we found no matches, branch to system command CMD_NOMATCH --> Finished
10) If we were unable to weed out multiple matches, branch CMD_MULTIMATCH --> Finished
11) If we have a single match, we now check user permissions. 
       not permissions: branch to system command CMD_NOPERM --> Finished
12) We analyze the matched command to determine if it is a channel-type command, that is
    a command auto-created to represent a valid comm channel. If so, we see if CMD_CHANNEL is 
    custom-defined in the merged cmdset, or we launch the auto-created command 
    direclty --> Finished
13 We next check if this is an exit-type command, that is, a command auto-created to represent
    an exit from this room. If so we check for custom CMD_EXIT in cmdset or launch
    the auto-generated command directly --> Finished
14) At this point we have found a normal command. We assign useful variables to it, that
    will be available to the command coder at run-time. 

When launching the command (normal, or system command both), two hook functions are called
in sequence, cmd.parse() followed by cmd.func(). It's up to the implementation as to how to
use this to most advantage. 

"""

from traceback import format_exc
from django.conf import settings
from src.comms.channelhandler import CHANNELHANDLER
from src.commands.cmdsethandler import import_cmdset
from src.objects.exithandler import EXITHANDLER
from src.utils import logger, utils 

#This switches the command parser to a user-defined one.
# You have to restart the server for this to take effect. 
COMMAND_PARSER = utils.mod_import(*settings.COMMAND_PARSER.rsplit('.', 1))

# There are a few system-hardcoded command names. These
# allow for custom behaviour when the command handler hits
# special situations -- it then calls a normal Command
# that you can customize! 

CMD_NOINPUT = "__noinput_command"
CMD_NOMATCH = "__nomatch_command"
CMD_MULTIMATCH = "__multimatch_command"
CMD_NOPERM = "__noperm_command"
CMD_CHANNEL = "__send_to_channel"
CMD_EXIT = "__move_to_exit"

class NoCmdSets(Exception):
    "No cmdsets found. Critical error."
    pass 
class ExecSystemCommand(Exception):
    "Run a system command"
    def __init__(self, syscmd, sysarg):
        self.args = (syscmd, sysarg) # needed by exception error handling
        self.syscmd = syscmd
        self.sysarg = sysarg

def get_and_merge_cmdsets(caller):
    """
    Gather all relevant cmdsets and merge them. Note 
    that this is only relevant for logged-in callers.
    """
    # The calling object's cmdset 
    try:
        caller_cmdset = caller.cmdset.current
    except AttributeError:
        caller_cmdset = None

    # All surrounding cmdsets
    channel_cmdset = None
    exit_cmdset = None
    local_objects_cmdsets = [None] 
    
    # Player object's commandsets 
    try:
        player_cmdset = caller.player.cmdset.current
    except AttributeError:
        player_cmdset = None 
    
    if not caller_cmdset.no_channels:
        # Make cmdsets out of all valid channels
        channel_cmdset = CHANNELHANDLER.get_cmdset(caller)
    if not caller_cmdset.no_exits:
        # Make cmdsets out of all valid exits in the room
        exit_cmdset = EXITHANDLER.get_cmdset(caller)
    location = None
    if hasattr(caller, "location"):
        location = caller.location 
    if location and not caller_cmdset.no_objs:
        # Gather all cmdsets stored on objects in the room and
        # also in the caller's inventory
        local_objlist = location.contents + caller.contents
        local_objects_cmdsets = [obj.cmdset.current
                                 for obj in local_objlist
                                 if obj.locks.check(caller, 'call', no_superuser_bypass=True)]

    # Merge all command sets into one
    # (the order matters, the higher-prio cmdsets are merged last)
    cmdset = caller_cmdset
    for obj_cmdset in [obj_cmdset for obj_cmdset in local_objects_cmdsets if obj_cmdset]:
        # Here only, object cmdsets are merged with duplicates=True
        # (or we would never be able to differentiate between objects)
        try:
            old_duplicate_flag = obj_cmdset.duplicates
            obj_cmdset.duplicates = True
            cmdset = obj_cmdset + cmdset
            obj_cmdset.duplicates = old_duplicate_flag
        except TypeError:
            pass
    # Exits and channels automatically has duplicates=True.
    try:
        cmdset = exit_cmdset + cmdset
    except TypeError:
        pass
    try:
        cmdset = channel_cmdset + cmdset
    except TypeError:
        pass
    # finally merge on the player cmdset. This should have a low priority
    try:
        cmdset = player_cmdset + cmdset
    except TypeError:
        pass

    return cmdset

def match_command(cmd_candidates, cmdset, logged_caller=None):
    """
    Try to match the command against one of the
    cmd_candidates. 

    logged_caller - a logged-in object, if any.

    """
    
    # Searching possible command matches in the given cmdset
    matches = []
    prev_found_cmds = [] # to avoid aliases clashing with themselves
    for cmd_candidate in cmd_candidates:
        cmdmatches = list(set([cmd for cmd in cmdset
                               if cmd == cmd_candidate.cmdname and 
                               cmd not in prev_found_cmds]))
        matches.extend([(cmd_candidate, cmd) for cmd in cmdmatches])
        prev_found_cmds.extend(cmdmatches)

    if not matches or len(matches) == 1:        
        return matches

    # Do our damndest to resolve multiple matches ...
    
    # At this point we might still have several cmd candidates,
    # each with a cmd match. We try to use candidate priority to 
    # separate them (for example this will give precedences to 
    # multi-word matches rather than one-word ones).                  

    top_ranked = []
    top_priority = None
    for match in matches:
        prio = match[0].priority
        if top_priority == None or prio > top_priority:
            top_ranked = [match]
            top_priority = prio
        elif top_priority == prio:
            top_ranked.append(match)            
            
    matches = top_ranked
    if not matches or len(matches) == 1:       
        return matches

    # Still multiplies. At this point we should have sorted out
    # all candidate multiples; the multiple comes from one candidate
    # matching more than one command. 

    # Check if player supplied
    # an obj name on the command line (e.g. 'clock's open' would
    # with the default parser tell us we want the open command
    # associated with the clock and not, say, the open command on 
    # the door in the same location). It's up to the cmdparser to
    # interpret and store this reference in candidate.obj_key if given. 

    if logged_caller:
        try:
            local_objlist = logged_caller.location.contents            
            top_ranked = []
            candidate = matches[0][0] # all candidates should be the same
            top_ranked.extend([(candidate, obj.cmdset.current.get(candidate.cmdname))
                               for obj in local_objlist
                               if candidate.obj_key == obj.name
                               and any(cmd == candidate.cmdname 
                                       for cmd in obj.cmdset.current)])
            if top_ranked:
                matches = top_ranked
        except Exception:
            logger.log_trace()
        if not matches or len(matches) == 1:            
            return matches 

    # We should still have only one candidate type, but matching 
    # several same-named commands.

    # Maybe the player tried to supply a separator in the form
    # of a number (e.g. 1-door, 2-door for two different door exits)? If so,
    # we pick the Nth-1 multiple as our result. It is up to the cmdparser
    # to read and store this number in candidate.obj_key if given. 

    candidate = matches[0][0] # all candidates should be the same
    if candidate.obj_key and candidate.obj_key.isdigit():
        num = int(candidate.obj_key) - 1
        if 0 <= num < len(matches):            
            matches = [matches[num]]
            
    # regardless what we have at this point, we have to be content    
    return matches

def format_multimatches(caller, matches):
    """
    Format multiple command matches to a useful error.
    """
    string = "There where multiple matches:"
    for num, match in enumerate(matches): 
        # each match is a tuple (candidate, cmd)
        candidate, cmd = match        

        is_channel = hasattr(cmd, "is_channel") and cmd.is_channel
        if is_channel:
            is_channel = " (channel)"
        else:
            is_channel = ""
        is_exit = hasattr(cmd, "is_exit") and cmd.is_exit 
        if is_exit and cmd.destination:
            is_exit =  " (exit to %s)" % cmd.destination
        else:
            is_exit = ""

        id1 = ""
        id2 = ""
        if not (is_channel or is_exit) and (hasattr(cmd, 'obj') and cmd.obj != caller):
            # the command is defined on some other object
            id1 = "%s-" % cmd.obj.name
            id2 = " (%s-%s)" % (num + 1, candidate.cmdname)
        else:
            id1 = "%s-" % (num + 1)
            id2 = ""
        string += "\n  %s%s%s%s%s" % (id1, candidate.cmdname, id2, is_channel, is_exit)
    return string

# Main command-handler function 

def cmdhandler(caller, raw_string, unloggedin=False, testing=False):
    """
    This is the main function to handle any string sent to the engine.    
    
    caller - calling object
    raw_string - the command string given on the command line
    unloggedin - if caller is an authenticated user or not
    testing - if we should actually execute the command or not. 
              if True, the command instance will be returned instead.
    """    
    try: # catch bugs in cmdhandler itself
        try: # catch special-type commands

            if unloggedin: 
                # not logged in, so it's just one cmdset we are interested in
                cmdset = import_cmdset(settings.CMDSET_UNLOGGEDIN, caller)
            else:                
                # We are logged in, collect all relevant cmdsets and merge
                cmdset = get_and_merge_cmdsets(caller)

            #print cmdset
            if not cmdset:
                # this is bad and shouldn't happen. 
                raise NoCmdSets

            raw_string = raw_string.strip()
            if not raw_string:
                # Empty input. Test for system command instead.
                syscmd = cmdset.get(CMD_NOINPUT)
                sysarg = ""
                raise ExecSystemCommand(syscmd, sysarg)

            # Parse the input string into command candidates
            cmd_candidates = COMMAND_PARSER(raw_string)            
            
            #string ="Command candidates"
            #for cand in cmd_candidates:
            #    string += "\n %s || %s" % (cand.cmdname, cand.args)                
            #caller.msg(string)

            # Try to produce a unique match between the merged 
            # cmdset and the candidates.
            if unloggedin:
                matches = match_command(cmd_candidates, cmdset)
            else:
                matches = match_command(cmd_candidates, cmdset, caller)
    
            #print "matches: ", matches

            # Deal with matches
            if not matches:
                # No commands match our entered command
                syscmd = cmdset.get(CMD_NOMATCH)
                if syscmd: 
                    sysarg = raw_string
                else:
                    sysarg = "Huh? (Type \"help\" for help)"
                raise ExecSystemCommand(syscmd, sysarg)

            if len(matches) > 1:
                # We have a multiple-match
                syscmd = cmdset.get(CMD_MULTIMATCH)
                sysarg = "There where multiple matches."
                if syscmd:
                    syscmd.matches = matches
                else:
                    sysarg = format_multimatches(caller, matches)
                raise ExecSystemCommand(syscmd, sysarg)
            
            # At this point, we have a unique command match. 
            cmd_candidate, cmd = matches[0]

            # Check so we have permission to use this command.
            if not cmd.access(caller):                
                cmd = cmdset.get(CMD_NOPERM)
                if cmd:
                    sysarg = raw_string
                else:
                    sysarg = "Huh? (type 'help' for help)"
                raise ExecSystemCommand(cmd, sysarg)

            # Check if this is a Channel match.
            if hasattr(cmd, 'is_channel') and cmd.is_channel:
                # even if a user-defined syscmd is not defined, the 
                # found cmd is already a system command in its own right. 
                syscmd = cmdset.get(CMD_CHANNEL)                
                if syscmd:
                    # replace system command with custom version
                    cmd = syscmd           
                sysarg = "%s:%s" % (cmd_candidate.cmdname,
                                    cmd_candidate.args)
                raise ExecSystemCommand(cmd, sysarg)

            # Check if this is an Exit match.
            if hasattr(cmd, 'is_exit') and cmd.is_exit:
                # even if a user-defined syscmd is not defined, the 
                # found cmd is already a system command in its own right. 
                syscmd = cmdset.get(CMD_EXIT)
                if syscmd:
                    # replace system command with custom version
                    cmd = syscmd
                sysarg = raw_string 
                raise ExecSystemCommand(cmd, sysarg)

            # A normal command.

            # Assign useful variables to the instance
            cmd.caller = caller 
            cmd.cmdstring = cmd_candidate.cmdname
            cmd.args = cmd_candidate.args
            cmd.cmdset = cmdset

            if hasattr(cmd, 'obj') and hasattr(cmd.obj, 'scripts'):
                # cmd.obj are automatically made available.
                # we make sure to validate its scripts. 
                cmd.obj.scripts.validate()
            
            if testing:
                # only return the command instance
                return cmd

            # pre-command hook
            cmd.at_pre_cmd()

            # Parse and execute        
            cmd.parse()
            cmd.func()

            # post-command hook
            cmd.at_post_cmd()
            # Done! 

        except ExecSystemCommand, exc:             
            # Not a normal command: run a system command, if available,
            # or fall back to a return string.            
            syscmd = exc.syscmd
            sysarg = exc.sysarg
            if syscmd:
                syscmd.caller = caller
                syscmd.cmdstring = syscmd.key
                syscmd.args = sysarg
                syscmd.cmdset = cmdset

                if hasattr(cmd, 'obj') and hasattr(cmd.obj, 'scripts'):
                    # cmd.obj is automatically made available.
                    # we make sure to validate its scripts. 
                    cmd.obj.scripts.validate()
                    
                if testing:
                    # only return the command instance
                    return syscmd

                # parse and run the command
                syscmd.parse()
                syscmd.func()
            elif sysarg:
                caller.msg(exc.sysarg)

        except NoCmdSets:
            # Critical error.
            string = "No command sets found! This is a sign of a critical bug.\n"
            string += "The error was logged.\n" 
            string += "If logging out/in doesn't solve the problem, try to "
            string += "contact the server admin through some other means "
            string += "for assistance."
            caller.msg(string)
            logger.log_errmsg("No cmdsets found: %s" % caller)
                
        except Exception:
            # We should not end up here. If we do, it's a programming bug.
            string = "%s\nAbove traceback is from an untrapped error." 
            string += " Please file a bug report."
            logger.log_trace(string)
            caller.msg(string % format_exc())

    except Exception:            
        # This catches exceptions in cmdhandler exceptions themselves
        string = "%s\nAbove traceback is from a Command handler bug."
        string += " Please contact an admin."
        logger.log_trace(string)
        caller.msg(string % format_exc())

#----------------------------------------------------- end cmdhandler
