"""
The default command parser. Use your own by assigning
`settings.COMMAND_PARSER` to a Python path to a module containing the
replacing cmdparser function. The replacement parser must accept the
same inputs as the default one.

"""
from __future__ import division

import re
from django.conf import settings
from evennia.utils.logger import log_trace

_MULTIMATCH_SEPARATOR = settings.SEARCH_MULTIMATCH_SEPARATOR
_MULTIMATCH_REGEX = re.compile(r"([0-9]+)%s(.*)" % _MULTIMATCH_SEPARATOR, re.I + re.U)

def cmdparser(raw_string, cmdset, caller, match_index=None):
    """
    This function is called by the cmdhandler once it has
    gathered and merged all valid cmdsets valid for this particular parsing.

    Args:
        raw_string (str): The unparsed text entered by the caller.
        cmdset (CmdSet): The merged, currently valid cmdset
        caller (Session, Player or Object): The caller triggering this parsing.
        match_index (int, optional): Index to pick a given match in a
            list of same-named command matches. If this is given, it suggests
            this is not the first time this function was called: normally
            the first run resulted in a multimatch, and the index is given
            to select between the results for the second run.

    Notes:
        The cmdparser understand the following command combinations (where
        [] marks optional parts.

        ```
        [cmdname[ cmdname2 cmdname3 ...] [the rest]
        ```

        A command may consist of any number of space-separated words of any
        length, and contain any character. It may also be empty.

        The parser makes use of the cmdset to find command candidates. The
        parser return a list of matches. Each match is a tuple with its
        first three elements being the parsed cmdname (lower case),
        the remaining arguments, and the matched cmdobject from the cmdset.

    """

    def create_match(cmdname, string, cmdobj):
        """
        Builds a command match by splitting the incoming string and
        evaluating the quality of the match.

        Args:
            cmdname (str): Name of command to check for.
            string (str): The string to match against.
            cmdobj (str): The full Command instance.

        Returns:
            match (tuple): This is on the form (cmdname, args, cmdobj, cmdlen, mratio), where
                `cmdname` is the command's name and `args` the rest of the incoming string,
                without said command name. `cmdobj` is the Command instance, the cmdlen is
                the same as len(cmdname) and mratio is a measure of how big a part of the
                full input string the cmdname takes up - an exact match would be 1.0.

        """
        cmdlen, strlen = len(unicode(cmdname)), len(unicode(string))
        mratio = 1 - (strlen - cmdlen) / (1.0 * strlen)
        args = string[cmdlen:]
        return (cmdname, args, cmdobj, cmdlen, mratio)

    if not raw_string:
        return []

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
        # no matches found
        num_ref_match = _MULTIMATCH_REGEX.match(raw_string)
        if num_ref_match:
            # the user might be trying to identify the command
            # with a #num-command style syntax.
            mindex, new_raw_string = num_ref_match.groups()
            return cmdparser(new_raw_string, cmdset,
                                 caller, match_index=int(mindex))

    # only select command matches we are actually allowed to call.
    matches = [match for match in matches if match[2].access(caller, 'cmd')]

    if len(matches) > 1:
        # See if it helps to analyze the match with preserved case but only if
        # it leaves at least one match.
        trimmed = [match for match in matches
                     if raw_string.startswith(match[0])]
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

    if len(matches) > 1 and match_index != None and 0 < match_index <= len(matches):
        # We couldn't separate match by quality, but we have an
        # index argument to tell us which match to use.
        matches = [matches[match_index-1]]

    # no matter what we have at this point, we have to return it.
    return matches

