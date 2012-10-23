"""
The default command parser. Use your own by assigning
settings.ALTERNATE_PARSER to a Python path to a module containing the
replacing cmdparser function. The replacement parser must
return a CommandCandidates object.
"""

from src.utils.logger import log_trace
from django.utils.translation import ugettext as _

def cmdparser(raw_string, cmdset, caller, match_index=None):
    """
    This function is called by the cmdhandler once it has
    gathered all valid cmdsets for the calling player. raw_string
    is the unparsed text entered by the caller.

    The cmdparser understand the following command combinations (where
    [] marks optional parts.

    [cmdname[ cmdname2 cmdname3 ...] [the rest]

    A command may consist of any number of space-separated words of any
    length, and contain any character.

    The parser makes use of the cmdset to find command candidates. The
    parser return a list of matches. Each match is a tuple with its
    first three elements being the parsed cmdname (lower case),
    the remaining arguments, and the matched cmdobject from the cmdset.
    """

    def create_match(cmdname, string, cmdobj):
        """
        Evaluates the quality of a match by counting how many chars of cmdname
        matches string (counting from beginning of string). We also calculate
        a ratio from 0-1 describing how much cmdname matches string.
        We return a tuple (cmdname, count, ratio, args, cmdobj).

        """
        cmdlen, strlen = len(cmdname), len(string)
        mratio = 1 - (strlen - cmdlen) / (1.0 * strlen)
        args = string[cmdlen:]
        return (cmdname, args, cmdobj, cmdlen, mratio)

    if not raw_string:
        return None

    matches = []

    # match everything that begins with a matching cmdname.
    l_raw_string = raw_string.lower()
    for cmd in cmdset:
        try:
            matches.extend([create_match(cmdname, raw_string, cmd)
                            for cmdname in [cmd.key] + cmd.aliases
                            if cmdname and l_raw_string.startswith(cmdname.lower())
                            and (not cmd.arg_regex or
                                 cmd.arg_regex.match(l_raw_string[len(cmdname):]))])
        except Exception:
            log_trace("cmdhandler error. raw_input:%s" % raw_string)

    if not matches:
        # no matches found.
        if '-' in raw_string:
            # This could be due to the user trying to identify the
            # command with a #num-<command> style syntax.
            mindex, new_raw_string = raw_string.split("-", 1)
            if mindex.isdigit():
                mindex = int(mindex) - 1
                # feed result back to parser iteratively
                return cmdparser(new_raw_string, cmdset, caller, match_index=mindex)

    # only select command matches we are actually allowed to call.
    matches = [match for match in matches if match[2].access(caller, 'cmd')]

    if len(matches) > 1:
        # See if it helps to analyze the match with preserved case but only if
        # it leaves at least one match.
        trimmed = [match for match in matches if raw_string.startswith(match[0])]
        if trimmed:
            matches = trimmed

    if len(matches) > 1:
        # we still have multiple matches. Sort them by count quality.
        matches = sorted(matches, key=lambda m: m[3])
        # only pick the matches with highest count quality
        quality = [mat[3] for mat in matches]
        matches = matches[-quality.count(quality[-1]):]

    if len(matches) > 1:
        # still multiple matches. Fall back to ratio-based quality.
        matches = sorted(matches, key=lambda m: m[4])
        # only pick the highest rated ratio match
        quality = [mat[4] for mat in matches]
        matches = matches[-quality.count(quality[-1]):]

    if len(matches) > 1 and match_index != None and 0 <= match_index < len(matches):
        # We couldn't separate match by quality, but we have an index argument to
        # tell us which match to use.
        matches = [matches[match_index]]

    # no matter what we have at this point, we have to return it.
    return matches



#------------------------------------------------------------
# Search parsers and support methods
#------------------------------------------------------------
#
# Default functions for formatting and processing searches.
#
# This is in its own module due to them being possible to
# replace from the settings file by setting the variables
#
# SEARCH_AT_RESULTERROR_HANDLER
# SEARCH_MULTIMATCH_PARSER
#
# The the replacing modules must have the same inputs and outputs as
# those in this module.
#

def at_search_result(msg_obj, ostring, results, global_search=False,
                     nofound_string=None, multimatch_string=None):
    """
    Called by search methods after a result of any type has been found.

    Takes a search result (a list) and
    formats eventual errors.

    msg_obj - object to receive feedback.
    ostring - original search string
    results - list of found matches (0, 1 or more)
    global_search - if this was a global_search or not
            (if it is, there might be an idea of supplying
            dbrefs instead of only numbers)
    nofound_string - optional custom string for not-found error message.
    multimatch_string - optional custom string for multimatch error header

    Multiple matches are returned to the searching object
    as
     1-object
     2-object
     3-object
       etc

    """
    string = ""
    if not results:
        # no results.
        if nofound_string:
            # custom return string
            string = nofound_string
        else:
            string = _("Could not find '%s'." % ostring)
        results = None

    elif len(results) > 1:
        # we have more than one match. We will display a
        # list of the form 1-objname, 2-objname etc.

        # check if the msg_object may se dbrefs
        show_dbref = global_search

        if multimatch_string:
            # custom header
            string = multimatch_string
        else:
            string = "More than one match for '%s'" % ostring
            string += " (please narrow target):"
            string = _(string)

        for num, result in enumerate(results):
            invtext = ""
            dbreftext = ""
            if hasattr(result, _("location")) and result.location == msg_obj:
                invtext = _(" (carried)")
            if show_dbref:
                dbreftext = "(#%i)" % result.dbid
            string += "\n %i-%s%s%s" % (num+1, result.name,
                                        dbreftext, invtext)
        results = None
    else:
        # we have exactly one match.
        results = results[0]

    if string:
        msg_obj.msg(string.strip())
    return results

def at_multimatch_input(ostring):
    """
    Parse number-identifiers.

    This parser will be called by the engine when a user supplies
    a search term. The search term must be analyzed to determine
    if the user wants to differentiate between multiple matches
    (usually found during a previous search).

    This method should separate out any identifiers from the search
    string used to differentiate between same-named objects. The
    result should be a tuple (index, search_string) where the index
    gives which match among multiple matches should be used (1 being
    the lowest number, rather than 0 as in Python).

    This parser version will identify search strings on the following
    forms

      2-object

    This will be parsed to (2, "object") and, if applicable, will tell
    the engine to pick the second from a list of same-named matches of
    objects called "object".

    Ex for use in a game session:

     > look
    You see: ball, ball, ball and ball.
     > get ball
    There where multiple matches for ball:
        1-ball
        2-ball
        3-ball
        4-ball
     > get 3-ball
     You get the ball.

    """

    if not isinstance(ostring, basestring):
        return (None, ostring)
    if not '-' in ostring:
        return (None, ostring)
    try:
        index  = ostring.find('-')
        number = int(ostring[:index])-1
        return (number, ostring[index+1:])
    except ValueError:
        #not a number; this is not an identifier.
        return (None, ostring)
    except IndexError:
        return (None, ostring)


def at_multimatch_cmd(caller, matches):
    """
    Format multiple command matches to a useful error.
    """
    string = "There where multiple matches:"
    for num, match in enumerate(matches):
        # each match is a tuple (candidate, cmd)
        cmdname, arg, cmd, dum, dum = match

        is_channel = hasattr(cmd, "is_channel") and cmd.is_channel
        if is_channel:
            is_channel = _(" (channel)")
        else:
            is_channel = ""
        if cmd.is_exit and cmd.destination:
            is_exit =  _(" (exit to %s)") % cmd.destination
        else:
            is_exit = ""

        id1 = ""
        id2 = ""
        if not (is_channel or is_exit) and (hasattr(cmd, 'obj') and cmd.obj != caller):
            # the command is defined on some other object
            id1 = "%s-%s" % (num + 1, cmdname)
            id2 = " (%s)" % (cmd.obj.key)
        else:
            id1 = "%s-%s" % (num + 1, cmdname)
            id2 = ""
        string += "\n  %s%s%s%s" % (id1, id2, is_channel, is_exit)
    return string
