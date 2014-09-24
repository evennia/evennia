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

from weakref import WeakValueDictionary
from copy import copy
from traceback import format_exc
from twisted.internet.defer import inlineCallbacks, returnValue
from django.conf import settings
from src.comms.channelhandler import CHANNELHANDLER
from src.utils import logger, utils
from src.commands.cmdparser import at_multimatch_cmd
from src.utils.utils import string_suggestions, to_unicode

from django.utils.translation import ugettext as _

__all__ = ("cmdhandler",)
_GA = object.__getattribute__
_CMDSET_MERGE_CACHE = WeakValueDictionary()

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
        self.args = (syscmd, sysarg)  # needed by exception error handling
        self.syscmd = syscmd
        self.sysarg = sysarg

# Helper function


@inlineCallbacks
def get_and_merge_cmdsets(caller, session, player, obj,
                          callertype, sessid=None):
    """
    Gather all relevant cmdsets and merge them.

    callertype is one of "session", "player" or "object" dependin
    on which level the cmdhandler is invoked. Session includes the
    cmdsets available to Session, Player and its eventual puppeted Object.
    Player-level include cmdsets on Player and Object, while calling
    the handler on an Object only includes cmdsets on itself.

    The cdmsets are merged in order generality, so that the Object's
    cmdset is merged last (and will thus take precedence over
    same-named and same-prio commands on Player and Session).

    Note that this function returns a deferred!
    """
    local_obj_cmdsets = [None]

    @inlineCallbacks
    def _get_channel_cmdsets(player, player_cmdset):
        "Channel-cmdsets"
        # Create cmdset for all player's available channels
        channel_cmdset = None
        if not player_cmdset.no_channels:
            channel_cmdset = yield CHANNELHANDLER.get_cmdset(player)
        returnValue(channel_cmdset)

    @inlineCallbacks
    def _get_local_obj_cmdsets(obj, obj_cmdset):
        "Object-level cmdsets"
        # Gather cmdsets from location, objects in location or carried
        local_obj_cmdsets = [None]
        try:
            location = obj.location
        except Exception:
            location = None
        if location and not obj_cmdset.no_objs:
            # Gather all cmdsets stored on objects in the room and
            # also in the caller's inventory and the location itself
            local_objlist = yield (location.contents_get(exclude=obj.dbobj) +
                                   obj.contents +
                                   [location])
            for lobj in local_objlist:
                try:
                    # call hook in case we need to do dynamic changing to cmdset
                    _GA(lobj, "at_cmdset_get")()
                except Exception:
                    logger.log_trace()
            # the call-type lock is checked here, it makes sure a player
            # is not seeing e.g. the commands on a fellow player (which is why
            # the no_superuser_bypass must be True)
            local_obj_cmdsets = \
                yield [lobj.cmdset.current for lobj in local_objlist
                   if (lobj.cmdset.current and
                   lobj.locks.check(caller, 'call', no_superuser_bypass=True))]
            for cset in local_obj_cmdsets:
                #This is necessary for object sets, or we won't be able to
                # separate the command sets from each other in a busy room.
                cset.old_duplicates = cset.duplicates
                cset.duplicates = True
        returnValue(local_obj_cmdsets)

    @inlineCallbacks
    def _get_cmdset(obj):
        "Get cmdset, triggering all hooks"
        try:
            yield obj.at_cmdset_get()
        except Exception:
            logger.log_trace()
        try:
            returnValue(obj.cmdset.current)
        except AttributeError:
            returnValue(None)

    if callertype == "session":
        # we are calling the command from the session level
        report_to = session
        session_cmdset = yield _get_cmdset(session)
        cmdsets = [session_cmdset]
        if player:  # this automatically implies logged-in
            player_cmdset = yield _get_cmdset(player)
            channel_cmdset = yield _get_channel_cmdsets(player, player_cmdset)
            cmdsets.extend([player_cmdset, channel_cmdset])
            if obj:
                obj_cmdset = yield _get_cmdset(obj)
                local_obj_cmdsets = yield _get_local_obj_cmdsets(obj, obj_cmdset)
                cmdsets.extend([obj_cmdset] + local_obj_cmdsets)
    elif callertype == "player":
        # we are calling the command from the player level
        report_to = player
        player_cmdset = yield _get_cmdset(player)
        channel_cmdset = yield _get_channel_cmdsets(player, player_cmdset)
        cmdsets = [player_cmdset, channel_cmdset]
        if obj:
            obj_cmdset = yield _get_cmdset(obj)
            local_obj_cmdsets = yield _get_local_obj_cmdsets(obj, obj_cmdset)
            cmdsets.extend([obj_cmdset] + local_obj_cmdsets)
    elif callertype == "object":
        # we are calling the command from the object level
        report_to = obj
        obj_cmdset = yield _get_cmdset(obj)
        local_obj_cmdsets = yield _get_local_obj_cmdsets(obj, obj_cmdset)
        cmdsets = [obj_cmdset] + local_obj_cmdsets
    else:
        raise Exception("get_and_merge_cmdsets: callertype %s is not valid." % callertype)
    #cmdsets = yield [caller_cmdset] + [player_cmdset] +
    #          [channel_cmdset] + local_obj_cmdsets

    # weed out all non-found sets
    cmdsets = yield [cmdset for cmdset in cmdsets
                     if cmdset and cmdset.key != "_EMPTY_CMDSET"]
    # report cmdset errors to user (these should already have been logged)
    yield [report_to.msg(cmdset.errmessage) for cmdset in cmdsets
           if cmdset.key == "_CMDSET_ERROR"]

    if cmdsets:
        # faster to do tuple on list than to build tuple directly
        mergehash = tuple([id(cmdset) for cmdset in cmdsets])
        if mergehash in _CMDSET_MERGE_CACHE:
            # cached merge exist; use that
            cmdset = _CMDSET_MERGE_CACHE[mergehash]
        else:
            # we group and merge all same-prio cmdsets separately (this avoids
            # order-dependent clashes in certain cases, such as
            # when duplicates=True)
            tempmergers = {}
            for cmdset in cmdsets:
                prio = cmdset.priority
                #print cmdset.key, prio
                if prio in tempmergers:
                    # merge same-prio cmdset together separately
                    tempmergers[prio] = yield cmdset + tempmergers[prio]
                else:
                    tempmergers[prio] = cmdset

            # sort cmdsets after reverse priority (highest prio are merged in last)
            cmdsets = yield sorted(tempmergers.values(), key=lambda x: x.priority)

            # Merge all command sets into one, beginning with the lowest-prio one
            cmdset = cmdsets[0]
            for merging_cmdset in cmdsets[1:]:
                #print "<%s(%s,%s)> onto <%s(%s,%s)>" % (merging_cmdset.key, merging_cmdset.priority, merging_cmdset.mergetype,
                #                                        cmdset.key, cmdset.priority, cmdset.mergetype)
                cmdset = yield merging_cmdset + cmdset
            # store the full sets for diagnosis
            cmdset.merged_from = cmdsets
            # cache
            _CMDSET_MERGE_CACHE[mergehash] = cmdset
    else:
        cmdset = None

    for cset in (cset for cset in local_obj_cmdsets if cset):
        cset.duplicates = cset.old_duplicates
    #print "merged set:", cmdset.key
    returnValue(cmdset)


# Main command-handler function

@inlineCallbacks
def cmdhandler(called_by, raw_string, _testing=False, callertype="session", sessid=None, **kwargs):
    """
    This is the main function to handle any string sent to the engine.

    called_by - object on which this was called from. This is either a Session, a Player or an Object.
    raw_string - the command string given on the command line
    _testing - if we should actually execute the command or not.
              if True, the command instance will be returned instead.
    callertype - this is one of "session", "player" or "object", in decending
                 order. So when the Session is the caller, it will merge its
                 own cmdset into cmdsets from both Player and eventual puppeted
                 Object (and cmdsets in its room etc). A Player will only
                 include its own cmdset and the Objects and so on. Merge order
                 is the same order, so that Object cmdsets are merged in last,
                 giving them precendence for same-name and same-prio commands.
    sessid - Relevant if callertype is "player" - the session id will help
             retrieve the correct cmdsets from puppeted objects.
    **kwargs - other keyword arguments will be assigned as named variables on the
               retrieved command object *before* it is executed. This is unuesed
               in default Evennia but may be used by code to set custom flags or
               special operating conditions for a command as it executes.

    Note that this function returns a deferred!
    """

    raw_string = to_unicode(raw_string, force_string=True)

    session, player, obj = None, None, None
    if callertype == "session":
        session = called_by
        player = session.player
        if player:
            obj = yield _GA(player.dbobj, "get_puppet")(session.sessid)
    elif callertype == "player":
        player = called_by
        if sessid:
            obj = yield _GA(player.dbobj, "get_puppet")(sessid)
    elif callertype == "object":
        obj = called_by
    else:
        raise RuntimeError("cmdhandler: callertype %s is not valid." % callertype)

    # the caller will be the one to receive messages and excert its permissions.
    # we assign the caller with preference 'bottom up'
    caller = obj or player or session

    try:  # catch bugs in cmdhandler itself
        try:  # catch special-type commands

            cmdset = yield get_and_merge_cmdsets(caller, session, player, obj,
                                                  callertype, sessid)
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
                    # use custom CMD_MULTIMATCH
                    syscmd.matches = matches
                else:
                    # fall back to default error handling
                    sysarg = yield at_multimatch_cmd(caller, matches)
                raise ExecSystemCommand(syscmd, sysarg)

            if len(matches) == 1:
                # We have a unique command match. But it may still be invalid.
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
                    # use custom CMD_NOMATH command
                    sysarg = raw_string
                else:
                    # fallback to default error text
                    sysarg = _("Command '%s' is not available.") % raw_string
                    suggestions = string_suggestions(raw_string,
                                    cmdset.get_all_cmd_keys_and_aliases(caller),
                                    cutoff=0.7, maxnum=3)
                    if suggestions:
                        sysarg += _(" Maybe you meant %s?") % utils.list_to_string(suggestions, _('or'), addquote=True)
                    else:
                        sysarg += _(" Type \"help\" for help.")
                raise ExecSystemCommand(syscmd, sysarg)

            # Check if this is a Channel-cmd match.
            if hasattr(cmd, 'is_channel') and cmd.is_channel:
                # even if a user-defined syscmd is not defined, the
                # found cmd is already a system command in its own right.
                syscmd = yield cmdset.get(CMD_CHANNEL)
                if syscmd:
                    # replace system command with custom version
                    cmd = syscmd
                cmd.sessid = session.sessid if session else None
                sysarg = "%s:%s" % (cmdname, args)
                raise ExecSystemCommand(cmd, sysarg)

            # A normal command.

            # Assign useful variables to the instance
            cmd.caller = caller
            cmd.cmdstring = cmdname
            cmd.args = args
            cmd.cmdset = cmdset
            cmd.sessid = session.sessid if session else sessid
            cmd.session = session
            cmd.player = player
            cmd.raw_string = unformatted_raw_string
            #cmd.obj  # set via on-object cmdset handler for each command,
                      # since this may be different for every command when
                      # merging multuple cmdsets

            if hasattr(cmd, 'obj') and hasattr(cmd.obj, 'scripts'):
                # cmd.obj is automatically made available by the cmdhandler.
                # we make sure to validate its scripts.
                yield cmd.obj.scripts.validate()

            if _testing:
                # only return the command instance
                returnValue(cmd)

            # assign custom kwargs to found cmd object
            for key, val in kwargs.items():
                setattr(cmd, key, val)

            # pre-command hook
            abort = yield cmd.at_pre_cmd()
            if abort:
                # abort sequence
                returnValue(abort)

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
                syscmd.sessid = session.sessid if session else None
                syscmd.raw_string = unformatted_raw_string

                if hasattr(syscmd, 'obj') and hasattr(syscmd.obj, 'scripts'):
                    # cmd.obj is automatically made available.
                    # we make sure to validate its scripts.
                    yield syscmd.obj.scripts.validate()

                if _testing:
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
