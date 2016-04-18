"""
Command handler

This module contains the infrastructure for accepting commands on the
command line. The processing of a command works as follows:

1. The calling object (caller) is analyzed based on its callertype.
2. Cmdsets are gathered from different sources:
   - channels:  all available channel names are auto-created into a cmdset, to allow
     for giving the channel name and have the following immediately
     sent to the channel. The sending is performed by the CMD_CHANNEL
     system command.
   - object cmdsets: all objects at caller's location are scanned for non-empty
     cmdsets. This includes cmdsets on exits.
   - caller: the caller is searched for its own currently active cmdset.
   - player: lastly the cmdsets defined on caller.player are added.
3. The collected cmdsets are merged together to a combined, current cmdset.
4. If the input string is empty -> check for CMD_NOINPUT command in
   current cmdset or fallback to error message. Exit.
5. The Command Parser is triggered, using the current cmdset to analyze the
   input string for possible command matches.
6. If multiple matches are found -> check for CMD_MULTIMATCH in current
   cmdset, or fallback to error message. Exit.
7. If no match was found -> check for CMD_NOMATCH in current cmdset or
   fallback to error message. Exit.
8. A single match was found. If this is a channel-command (i.e. the
   ommand name is that of a channel), --> check for CMD_CHANNEL in
   current cmdset or use channelhandler default. Exit.
9. At this point we have found a normal command. We assign useful variables to it that
   will be available to the command coder at run-time.
12. We have a unique cmdobject, primed for use. Call all hooks:
   `at_pre_cmd()`, `cmdobj.parse()`, `cmdobj.func()` and finally `at_post_cmd()`.
13. Return deferred that will fire with the return from `cmdobj.func()` (unused by default).
"""

from collections import defaultdict
from weakref import WeakValueDictionary
from traceback import format_exc
from copy import copy
from twisted.internet.defer import inlineCallbacks, returnValue
from django.conf import settings
from evennia.comms.channelhandler import CHANNELHANDLER
from evennia.utils import logger, utils
from evennia.utils.utils import string_suggestions, to_unicode

from django.utils.translation import ugettext as _

_IN_GAME_ERRORS = settings.IN_GAME_ERRORS

__all__ = ("cmdhandler",)
_GA = object.__getattribute__
_CMDSET_MERGE_CACHE = WeakValueDictionary()

# tracks recursive calls by each caller
# to avoid infinite loops (commands calling themselves)
_COMMAND_NESTING = defaultdict(lambda: 0)
_COMMAND_RECURSION_LIMIT = 10

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

# Function for handling multiple command matches.
_SEARCH_AT_RESULT = utils.variable_from_module(*settings.SEARCH_AT_RESULT.rsplit('.', 1))

# Output strings. The first is the IN_GAME_ERRORS return, the second
# is the normal "production message to echo to the player.

_ERROR_UNTRAPPED = (
"""
An untrapped error occurred.
""",
"""
An untrapped error occurred. Please file a bug report detailing the steps to reproduce.
""")

_ERROR_CMDSETS = (
"""
A cmdset merger-error occurred. This is often due to a syntax
error in one of the cmdsets to merge.
""",
"""
A cmdset merger-error occurred. Please file a bug report detailing the
steps to reproduce.
""")

_ERROR_NOCMDSETS = (
"""
No command sets found! This is a critical bug that can have
multiple causes.
""",
"""
No command sets found! This is a sign of a critical bug.  If
disconnecting/reconnecting doesn't" solve the problem, try to contact
the server admin through" some other means for assistance.
""")

_ERROR_CMDHANDLER = (
"""
A command handler bug occurred. If this is not due to a local change,
please file a bug report with the Evennia project, including the
traceback and steps to reproduce.
""",
"""
A command handler bug occurred. Please notify staff - they should
likely file a bug report with the Evennia project.
""")

_ERROR_RECURSION_LIMIT = "Command recursion limit ({recursion_limit}) " \
                         "reached for '{raw_string}' ({cmdclass})."


def _msg_err(receiver, stringtuple):
    """
    Helper function for returning an error to the caller.

    Args:
        receiver (Object): object to get the error message.
        stringtuple (tuple): tuple with two strings - one for the
        _IN_GAME_ERRORS mode (with the traceback) and one with the
        production string (with a timestamp) to be shown to the user.

    """
    string = "{traceback}\n{errmsg}\n(Traceback was logged {timestamp})."
    timestamp = logger.timeformat()
    tracestring = format_exc()
    logger.log_trace()
    if _IN_GAME_ERRORS:
        receiver.msg(string.format(traceback=tracestring,
                                   errmsg=stringtuple[0].strip(),
                                   timestamp=timestamp).strip())
    else:
        receiver.msg(string.format(traceback=tracestring.splitlines()[-1],
                                   errmsg=stringtuple[1].strip(),
                                   timestamp=timestamp).strip())

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

class ErrorReported(Exception):
    "Re-raised when a subsructure already reported the error"

# Helper function

@inlineCallbacks
def get_and_merge_cmdsets(caller, session, player, obj, callertype):
    """
    Gather all relevant cmdsets and merge them.

    Args:
        caller (Session, Player or Object): The entity executing the command. Which
            type of object this is depends on the current game state; for example
            when the user is not logged in, this will be a Session, when being OOC
            it will be a Player and when puppeting an object this will (often) be
            a Character Object. In the end it depends on where the cmdset is stored.
        session (Session or None): The Session associated with caller, if any.
        player (Player or None): The calling Player associated with caller, if any.
        obj (Object or None): The Object associated with caller, if any.
        callertype (str): This identifies caller as either "player", "object" or "session"
            to avoid having to do this check internally.

    Returns:
        cmdset (Deferred): This deferred fires with the merged cmdset
        result once merger finishes.

    Notes:
        The cdmsets are merged in order or generality, so that the
        Object's cmdset is merged last (and will thus take precedence
        over same-named and same-prio commands on Player and Session).

    """
    try:
        local_obj_cmdsets = [None]

        @inlineCallbacks
        def _get_channel_cmdsets(player, player_cmdset):
            """
            Helper-method; Get channel-cmdsets
            """
            # Create cmdset for all player's available channels
            try:
                channel_cmdset = None
                if not player_cmdset.no_channels:
                    channel_cmdset = yield CHANNELHANDLER.get_cmdset(player)
                returnValue(channel_cmdset)
            except Exception:
                _msg_err(caller, _ERROR_CMDSETS)
                raise ErrorReported

        @inlineCallbacks
        def _get_local_obj_cmdsets(obj, obj_cmdset):
            """
            Helper-method; Get Object-level cmdsets
            """
            # Gather cmdsets from location, objects in location or carried
            try:
                local_obj_cmdsets = [None]
                try:
                    location = obj.location
                except Exception:
                    location = None
                if location and not obj_cmdset.no_objs:
                    # Gather all cmdsets stored on objects in the room and
                    # also in the caller's inventory and the location itself
                    local_objlist = yield (location.contents_get(exclude=obj) +
                                           obj.contents_get() + [location])
                    local_objlist = [o for o in local_objlist if not o._is_deleted]
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
                           lobj.access(caller, access_type='call', no_superuser_bypass=True))]
                    for cset in local_obj_cmdsets:
                        #This is necessary for object sets, or we won't be able to
                        # separate the command sets from each other in a busy room. We
                        # only keep the setting if duplicates were set to False/True
                        # explicitly.
                        cset.old_duplicates = cset.duplicates
                        cset.duplicates = True if cset.duplicates is None else cset.duplicates
                returnValue(local_obj_cmdsets)
            except Exception:
                _msg_err(caller, _ERROR_CMDSETS)
                raise ErrorReported


        @inlineCallbacks
        def _get_cmdset(obj):
            """
            Helper method; Get cmdset while making sure to trigger all
            hooks safely.
            """
            try:
                yield obj.at_cmdset_get()
            except Exception:
                _msg_err(caller, _ERROR_CMDSETS)
                raise ErrorReported
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
                    cmdset = yield merging_cmdset + cmdset
                # store the full sets for diagnosis
                cmdset.merged_from = cmdsets
                # cache
                _CMDSET_MERGE_CACHE[mergehash] = cmdset
        else:
            cmdset = None

        for cset in (cset for cset in local_obj_cmdsets if cset):
            cset.duplicates = cset.old_duplicates
        returnValue(cmdset)
    except ErrorReported:
        raise
    except Exception:
        _msg_err(caller, _ERROR_CMDSETS)
        raise ErrorReported

# Main command-handler function


@inlineCallbacks
def cmdhandler(called_by, raw_string, _testing=False, callertype="session", session=None, **kwargs):
    """
    This is the main mechanism that handles any string sent to the engine.

    Args:
        called_by (Session, Player or Object): Object from which this
            command was called. which this was called from.  What this is
            depends on the game state.
        raw_string (str): The command string as given on the command line.
        _testing (bool, optional): Used for debug purposes and decides if we
            should actually execute the command or not. If True, the
            command instance will be returned.
        callertype (str, optional): One of "session", "player" or
            "object". These are treated in decending order, so when the
            Session is the caller, it will merge its own cmdset into
            cmdsets from both Player and eventual puppeted Object (and
            cmdsets in its room etc). A Player will only include its own
            cmdset and the Objects and so on. Merge order is the same
            order, so that Object cmdsets are merged in last, giving them
            precendence for same-name and same-prio commands.
        session (Session, optional): Relevant if callertype is "player" - the session will help
            retrieve the correct cmdsets from puppeted objects.

    Kwargs:
        kwargs (any): other keyword arguments will be assigned as named variables on the
            retrieved command object *before* it is executed. This is unused
            in default Evennia but may be used by code to set custom flags or
            special operating conditions for a command as it executes.

    Returns:
        deferred (Deferred): This deferred is fired with the return
        value of the command's `func` method.  This is not used in
        default Evennia.

    """

    @inlineCallbacks
    def _run_command(cmd, cmdname, args):
        """
        Helper function: This initializes and runs the Command
        instance once the parser has identified it as either a normal
        command or one of the system commands.

        Args:
            cmd (Command): command object
            cmdname (str): name of command
            args (str): extra text entered after the identified command

        Returns:
            deferred (Deferred): this will fire with the return of the
                command's `func` method.

        Raises:
            RuntimeError: If command recursion limit was reached.

        """
        global _COMMAND_NESTING
        try:
            # Assign useful variables to the instance
            cmd.caller = caller
            cmd.cmdstring = cmdname
            cmd.args = args
            cmd.cmdset = cmdset
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

            _COMMAND_NESTING[called_by] += 1
            if _COMMAND_NESTING[called_by] > _COMMAND_RECURSION_LIMIT:
                err = _ERROR_RECURSION_LIMIT.format(recursion_limit=_COMMAND_RECURSION_LIMIT,
                                                    raw_string=unformatted_raw_string,
                                                    cmdclass=cmd.__class__)
                raise RuntimeError(err)

            # pre-command hook
            abort = yield cmd.at_pre_cmd()
            if abort:
                # abort sequence
                returnValue(abort)

            # Parse and execute
            yield cmd.parse()

            # main command code
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
            _COMMAND_NESTING[called_by] -= 1

            # return result to the deferred
            returnValue(ret)

        except Exception:
            _msg_err(caller, _ERROR_UNTRAPPED)
            raise ErrorReported

    raw_string = to_unicode(raw_string, force_string=True)

    session, player, obj = session, None, None
    if callertype == "session":
        session = called_by
        player = session.player
        obj = session.puppet
    elif callertype == "player":
        player = called_by
        if session:
            obj = yield session.puppet
    elif callertype == "object":
        obj = called_by
    else:
        raise RuntimeError("cmdhandler: callertype %s is not valid." % callertype)
    # the caller will be the one to receive messages and excert its permissions.
    # we assign the caller with preference 'bottom up'
    caller = obj or player or session
    # The error_to is the default recipient for errors. Tries to make sure a player
    # does not get spammed for errors while preserving character mirroring.
    error_to = obj or session or player

    try:  # catch bugs in cmdhandler itself
        try:  # catch special-type commands

            cmdset = yield get_and_merge_cmdsets(caller, session, player, obj,
                                                  callertype)
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
                    sysarg = yield _SEARCH_AT_RESULT([match[2] for match in matches], caller, query=match[0])
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
                    # use custom CMD_NOMATCH command
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
                cmd.session = session
                sysarg = "%s:%s" % (cmdname, args)
                raise ExecSystemCommand(cmd, sysarg)

            # A normal command.
            ret = yield _run_command(cmd, cmdname, args)
            returnValue(ret)

        except ErrorReported:
            # this error was already reported, so we
            # catch it here and don't pass it on.
            pass

        except ExecSystemCommand as exc:
            # Not a normal command: run a system command, if available,
            # or fall back to a return string.
            syscmd = exc.syscmd
            sysarg = exc.sysarg

            if syscmd:
                ret = yield _run_command(syscmd, syscmd.key, sysarg)
                returnValue(ret)
            elif sysarg:
                # return system arg
                error_to.msg(exc.sysarg)

        except NoCmdSets:
            # Critical error.
            logger.log_err("No cmdsets found: %s" % caller)
            error_to.msg(_ERROR_NOCMDSETS)

        except Exception:
            # We should not end up here. If we do, it's a programming bug.
            _msg_err(error_to, _ERROR_UNTRAPPED)

    except Exception:
        # This catches exceptions in cmdhandler exceptions themselves
        _msg_err(error_to, _ERROR_CMDHANDLER)
