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

from copy import copy
from traceback import format_exc
from twisted.internet.defer import inlineCallbacks, returnValue
from django.conf import settings
from src.comms.channelhandler import CHANNELHANDLER
from src.utils import logger, utils
from src.commands.cmdset import CmdSet
from src.commands.cmdparser import at_multimatch_cmd
from src.utils.utils import string_suggestions

from django.utils.translation import ugettext as _

__all__ = ("cmdhandler",)

# This decides which command parser is to be used.
# You have to restart the server for changes to take effect.
_COMMAND_PARSER = utils.variable_from_module(*settings.COMMAND_PARSER.rsplit('.', 1))

# System command names - import these variables rather than trying to
# remember the actual string constants. If not defined, Evennia
# hard-coded defaults are used instead.

# command to call if user just presses <return> with no input
CMD_NOINPUT = "__noinput_command"
# command to call if no command match was found
CMD_NOMATCH = "__nomatch_command"
# command to call if multiple command matches were found
CMD_MULTIMATCH = "__multimatch_command"
# command to call if found command is the name of a channel
CMD_CHANNEL = "__send_to_channel_command"
# command to call as the very first one when the user connects.
# (is expected to display the login screen)
CMD_LOGINSTART = "__unloggedin_look_command"

# custom Exceptions

class NoCmdSets(Exception):
    "No cmdsets found. Critical error."
    pass
class ExecSystemCommand(Exception):
    "Run a system command"
    def __init__(self, syscmd, sysarg):
        self.args = (syscmd, sysarg) # needed by exception error handling
        self.syscmd = syscmd
        self.sysarg = sysarg

# Helper function

@inlineCallbacks
def get_and_merge_cmdsets(caller):
    """
    Gather all relevant cmdsets and merge them. Note
    that this is only relevant for logged-in callers.

    Note that this function returns a deferred!
    """
    # The calling object's cmdset
    try:
        yield caller.at_cmdset_get()
    except Exception:
        logger.log_trace()
    try:
        caller_cmdset = caller.cmdset.current
    except AttributeError:
        caller_cmdset = None

    # Create cmdset for all player's available channels
    channel_cmdset = None
    if not caller_cmdset.no_channels:
        channel_cmdset = yield CHANNELHANDLER.get_cmdset(caller)

    # Gather cmdsets from location, objects in location or carried
    local_objects_cmdsets = [None]
    try:
        location = caller.location
    except Exception:
        location = None
    if location and not caller_cmdset.no_objs:
        # Gather all cmdsets stored on objects in the room and
        # also in the caller's inventory and the location itself
        local_objlist = yield location.contents_get(exclude=caller.dbobj) + caller.contents + [location]
        for obj in local_objlist:
            try:
                # call hook in case we need to do dynamic changing to cmdset
                yield obj.at_cmdset_get()
            except Exception:
                logger.log_trace()
        # the call-type lock is checked here, it makes sure a player is not seeing e.g. the commands
        # on a fellow player (which is why the no_superuser_bypass must be True)
        local_objects_cmdsets = yield [obj.cmdset.current for obj in local_objlist
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

    cmdsets = yield [caller_cmdset] + [player_cmdset] + [channel_cmdset] + local_objects_cmdsets
    # weed out all non-found sets
    cmdsets = yield [cmdset for cmdset in cmdsets if cmdset]
    # report cmdset errors to user (these should already have been logged)
    yield [caller.msg(cmdset.message) for cmdset in cmdsets if cmdset.key == "_CMDSET_ERROR"]
    # sort cmdsets after reverse priority (highest prio are merged in last)
    yield cmdsets.sort(key=lambda x: x.priority)
    #cmdsets = yield sorted(cmdsets, key=lambda x: x.priority)

    if cmdsets:
        # Merge all command sets into one, beginning with the lowest-prio one
        cmdset = cmdsets.pop(0)
        for merging_cmdset in cmdsets:
            #print "<%s(%s,%s)> onto <%s(%s,%s)>" % (merging_cmdset.key, merging_cmdset.priority, merging_cmdset.mergetype,
            #                                        cmdset.key, cmdset.priority, cmdset.mergetype)
            cmdset = yield merging_cmdset + cmdset
    else:
        cmdset = None

    for cset in (cset for cset in local_objects_cmdsets if cset):
        cset.duplicates = cset.old_duplicates
    returnValue(cmdset)


# Main command-handler function

@inlineCallbacks
def cmdhandler(caller, raw_string, testing=False):
    """
    This is the main function to handle any string sent to the engine.

    caller - calling object
    raw_string - the command string given on the command line
    testing - if we should actually execute the command or not.
              if True, the command instance will be returned instead.

    Note that this function returns a deferred!
    """
    try: # catch bugs in cmdhandler itself
        try: # catch special-type commands

            cmdset = yield get_and_merge_cmdsets(caller)
            if not cmdset:
                # this is bad and shouldn't happen.
                raise NoCmdSets
            unformatted_raw_string = raw_string
            raw_string = raw_string.strip()
            if not raw_string:
                # Empty input. Test for system command instead.
                syscmd = yield cmdset.get(CMD_NOINPUT)
                sysarg = ""
                raise ExecSystemCommand(syscmd, sysarg)
            # Parse the input string and match to available cmdset.
            # This also checks for permissions, so all commands in match
            # are commands the caller is allowed to call.
            matches = yield _COMMAND_PARSER(raw_string, cmdset, caller)

            # Deal with matches

            if len(matches) > 1:
                # We have a multiple-match
                syscmd = yield cmdset.get(CMD_MULTIMATCH)
                sysarg = _("There were multiple matches.")
                if syscmd:
                    syscmd.matches = matches
                else:
                    sysarg = yield at_multimatch_cmd(caller, matches)
                raise ExecSystemCommand(syscmd, sysarg)

            if len(matches) == 1:
                # We have a unique command match.
                match = matches[0]
                cmdname, args, cmd = match[0], match[1], match[2]

                # check if we allow this type of command
                if cmdset.no_channels and hasattr(cmd, "is_channel") and cmd.is_channel:
                    matches = []
                if cmdset.no_exits and hasattr(cmd, "is_exit") and cmd.is_exit:
                    matches = []

            if not matches:
                # No commands match our entered command
                syscmd = yield cmdset.get(CMD_NOMATCH)
                if syscmd:
                    sysarg = raw_string
                else:
                    sysarg = _("Command '%s' is not available.") % raw_string
                    suggestions = string_suggestions(raw_string, cmdset.get_all_cmd_keys_and_aliases(caller), cutoff=0.7, maxnum=3)
                    if suggestions:
                        sysarg += _(" Maybe you meant %s?") % utils.list_to_string(suggestions, _('or'), addquote=True)
                    else:
                        sysarg += _(" Type \"help\" for help.")
                raise ExecSystemCommand(syscmd, sysarg)


            # Check if this is a Channel match.
            if hasattr(cmd, 'is_channel') and cmd.is_channel:
                # even if a user-defined syscmd is not defined, the
                # found cmd is already a system command in its own right.
                syscmd = yield cmdset.get(CMD_CHANNEL)
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
            cmd.raw_string = unformatted_raw_string

            if hasattr(cmd, 'obj') and hasattr(cmd.obj, 'scripts'):
                # cmd.obj are automatically made available.
                # we make sure to validate its scripts.
                yield cmd.obj.scripts.validate()

            if testing:
                # only return the command instance
                returnValue(cmd)

            # pre-command hook
            yield cmd.at_pre_cmd()

            # Parse and execute
            yield cmd.parse()
            # (return value is normally None)
            ret = yield cmd.func()

            # post-command hook
            yield cmd.at_post_cmd()

            if cmd.save_for_next:
                # store a reference to this command, possibly
                # accessible by the next command.
                caller.ndb.last_cmd = yield copy(cmd)
            else:
                caller.ndb.last_cmd = None
            # Done! This returns a deferred. By default, Evennia does
            # not use this at all.
            returnValue(ret)

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
                syscmd.raw_string = unformatted_raw_string

                if hasattr(syscmd, 'obj') and hasattr(syscmd.obj, 'scripts'):
                    # cmd.obj is automatically made available.
                    # we make sure to validate its scripts.
                    yield syscmd.obj.scripts.validate()

                if testing:
                    # only return the command instance
                    returnValue(syscmd)

                # parse and run the command
                yield syscmd.parse()
                yield syscmd.func()
            elif sysarg:
                # return system arg
                caller.msg(exc.sysarg)

        except NoCmdSets:
            # Critical error.
            string = "No command sets found! This is a sign of a critical bug.\n"
            string += "The error was logged.\n"
            string += "If logging out/in doesn't solve the problem, try to "
            string += "contact the server admin through some other means "
            string += "for assistance."
            caller.msg(_(string))
            logger.log_errmsg("No cmdsets found: %s" % caller)

        except Exception:
            # We should not end up here. If we do, it's a programming bug.
            string = "%s\nAbove traceback is from an untrapped error."
            string += " Please file a bug report."
            logger.log_trace(_(string))
            caller.msg(string % format_exc())

    except Exception:
        # This catches exceptions in cmdhandler exceptions themselves
        string = "%s\nAbove traceback is from a Command handler bug."
        string += " Please contact an admin and/or file a bug report."
        logger.log_trace(_(string))
        caller.msg(string % format_exc())
