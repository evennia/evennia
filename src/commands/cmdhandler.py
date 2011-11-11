"""
Command handler

This module contains the infrastructure for accepting commands on the
command line. The process is as follows: 

1) The calling object (caller) inputs a string and triggers the command parsing system.
2) The system checks the state of the caller - loggedin or not
3) If no command string was supplied, we search the merged cmdset for system command CMD_NOINPUT 
   and branches to execute that.  --> Finished
4) Cmdsets are gathered from different sources (in order of dropping priority):     
           channels - all available channel names are auto-created into a cmdset, to allow 
                  for giving the channel name and have the following immediately
                  sent to the channel. The sending is performed by the CMD_CHANNEL
                  system command.
           object cmdsets - all objects at caller's location are scanned for non-empty
                  cmdsets. This includes cmdsets on exits. 
           caller - the caller is searched for its own currently active cmdset.
           player - lastly the cmdsets defined on caller.player are added. 
5) All the gathered cmdsets (if more than one) are merged into one using the cmdset priority rules. 
6) If merged cmdset is empty, raise NoCmdSet exception (this should not happen, at least the
   player should have a default cmdset available at all times). --> Finished 
7) The raw input string is parsed using the parser defined by settings.COMMAND_PARSER. It 
   uses the available commands from the merged cmdset to know which commands to look for and
   returns one or many matches.  
8)   If match list is empty, branch to system command CMD_NOMATCH --> Finished
9)   If match list has more than one element, branch to system command CMD_MULTIMATCH --> Finished
10) A single match was found. If this is a channel-command (i.e. the command name is that of a channel),
    branch to CMD_CHANNEL --> Finished 
11) At this point we have found a normal command. We assign useful variables to it that
    will be available to the command coder at run-time. 
12) We have a unique cmdobject, primed for use. Call all hooks: 
    at_pre_cmd(), cmdobj.parse(), cmdobj.func() and finally at_post_cmd().  


"""

from traceback import format_exc
from django.conf import settings
from src.comms.channelhandler import CHANNELHANDLER
from src.commands.cmdsethandler import import_cmdset
from src.utils import logger, utils 
from src.commands.cmdparser import at_multimatch_cmd

#This switches the command parser to a user-defined one.
# You have to restart the server for this to take effect. 
COMMAND_PARSER = utils.mod_import(*settings.COMMAND_PARSER.rsplit('.', 1))

# There are a few system-hardcoded command names. These
# allow for custom behaviour when the command handler hits
# special situations -- it then calls a normal Command
# that you can customize! 
# Import these variables and use them rather than trying
# to remember the actual string constants. 

CMD_NOINPUT = "__noinput_command"
CMD_NOMATCH = "__nomatch_command"
CMD_MULTIMATCH = "__multimatch_command"
CMD_CHANNEL = "__send_to_channel_command"
# this is the name of the command the engine calls when the player
# connects. It is expected to show the login screen.
CMD_LOGINSTART = "__unloggedin_look_command" 


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
        caller.at_cmdset_get()
    except Exception:
        logger.log_trace()
    try:
        caller_cmdset = caller.cmdset.current
    except AttributeError:
        caller_cmdset = None
        
    # Create cmdset for all player's available channels
    channel_cmdset = None
    if not caller_cmdset.no_channels:
        channel_cmdset = CHANNELHANDLER.get_cmdset(caller)

    # Gather cmdsets from location, objects in location or carried        
    local_objects_cmdsets = [None] 
    location = None
    if hasattr(caller, "location"):
        location = caller.location 
    if location and not caller_cmdset.no_objs:
        # Gather all cmdsets stored on objects in the room and
        # also in the caller's inventory and the location itself
        local_objlist = location.contents_get(exclude=caller.dbobj) + caller.contents + [location]
        for obj in local_objlist:
            try:
                # call hook in case we need to do dynamic changing to cmdset
                obj.at_cmdset_get()
            except Exception:
                logger.log_trace()
        local_objects_cmdsets = [obj.cmdset.current for obj in local_objlist
                                 if (obj.cmdset.current and obj.locks.check(caller, 'call', no_superuser_bypass=True))]
        for cset in local_objects_cmdsets:
            #This is necessary for object sets, or we won't be able to separate 
            #the command sets from each other in a busy room.
            cset.old_duplicates = cset.duplicates
            cset.duplicates = True

    # Player object's commandsets 
    try:
        player_cmdset = caller.player.cmdset.current
    except AttributeError:
        player_cmdset = None

    cmdsets = [caller_cmdset] + [player_cmdset] + [channel_cmdset] + local_objects_cmdsets
    # weed out all non-found sets 
    cmdsets = [cmdset for cmdset in cmdsets if cmdset]
    # sort cmdsets after reverse priority (highest prio are merged in last)
    cmdsets = sorted(cmdsets, key=lambda x: x.priority)

    if cmdsets:
        # Merge all command sets into one, beginning with the lowest-prio one
        cmdset = cmdsets.pop(0)
        for merging_cmdset in cmdsets:
            #print "<%s(%s,%s)> onto <%s(%s,%s)>" % (merging_cmdset.key, merging_cmdset.priority, merging_cmdset.mergetype, 
            #                                        cmdset.key, cmdset.priority, cmdset.mergetype)        
            cmdset = merging_cmdset + cmdset 
    else:
        cmdset = None

    for cset in (cset for cset in local_objects_cmdsets if cset):
        cset.duplicates = cset.old_duplicates

    return cmdset 


# Main command-handler function 

def cmdhandler(caller, raw_string, testing=False):
    """
    This is the main function to handle any string sent to the engine.    
    
    caller - calling object
    raw_string - the command string given on the command line
    testing - if we should actually execute the command or not. 
              if True, the command instance will be returned instead.
    """    
    try: # catch bugs in cmdhandler itself
        try: # catch special-type commands

            cmdset = get_and_merge_cmdsets(caller)

            # print cmdset
            if not cmdset:
                # this is bad and shouldn't happen. 
                raise NoCmdSets

            raw_string = raw_string.strip()
            if not raw_string:
                # Empty input. Test for system command instead.
                syscmd = cmdset.get(CMD_NOINPUT)
                sysarg = ""
                raise ExecSystemCommand(syscmd, sysarg)
            # Parse the input string and match to available cmdset.
            # This also checks for permissions, so all commands in match
            # are commands the caller is allowed to call.
            matches = COMMAND_PARSER(raw_string, cmdset, caller)
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
                    sysarg = at_multimatch_cmd(caller, matches)
                raise ExecSystemCommand(syscmd, sysarg)
            
            # At this point, we have a unique command match. 
            match = matches[0]
            cmdname, args, cmd = match[0], match[1], match[2]

            # Check if this is a Channel match.
            if hasattr(cmd, 'is_channel') and cmd.is_channel:
                # even if a user-defined syscmd is not defined, the 
                # found cmd is already a system command in its own right. 
                syscmd = cmdset.get(CMD_CHANNEL)                
                if syscmd:
                    # replace system command with custom version
                    cmd = syscmd           
                sysarg = "%s:%s" % (cmdname, args)
                raise ExecSystemCommand(cmd, sysarg)

            # A normal command.

            # Assign useful variables to the instance
            cmd.caller = caller 
            cmd.cmdstring = cmdname
            cmd.args = args
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
            # (return value is normally None)
            ret = cmd.func()

            # post-command hook
            cmd.at_post_cmd()
            # Done! By default, Evennia does not use this return at all
            return ret 

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

                if hasattr(syscmd, 'obj') and hasattr(syscmd.obj, 'scripts'):
                    # cmd.obj is automatically made available.
                    # we make sure to validate its scripts. 
                    syscmd.obj.scripts.validate()
                    
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
