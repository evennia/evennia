"""
The default command parser. Use your own by assigning
`settings.COMMAND_PARSER` to a Python path to a module containing the
replacing cmdparser function. The replacement parser must accept the
same inputs as the default one.

"""


import re

from django.conf import settings

from evennia.utils.logger import log_trace

_MULTIMATCH_REGEX = re.compile(settings.SEARCH_MULTIMATCH_REGEX, re.I + re.U)
_CMD_IGNORE_PREFIXES = settings.CMD_IGNORE_PREFIXES


def create_match(cmdname, string, cmdobj, raw_cmdname):
    """
    Builds a command match by splitting the incoming string and
    evaluating the quality of the match.

    Args:
        cmdname (str): Name of command to check for.
        string (str): The string to match against.
        cmdobj (str): The full Command instance.
        raw_cmdname (str, optional): If CMD_IGNORE_PREFIX is set and the cmdname starts with
            one of the prefixes to ignore, this contains the raw, unstripped cmdname,
            otherwise it is None.

    Returns:
        match (tuple): This is on the form (cmdname, args, cmdobj, cmdlen, mratio, raw_cmdname),
            where `cmdname` is the command's name and `args` is the rest of the incoming
            string, without said command name. `cmdobj` is
            the Command instance, the cmdlen is the same as len(cmdname) and mratio
            is a measure of how big a part of the full input string the cmdname
            takes up - an exact match would be 1.0. Finally, the `raw_cmdname` is
            the cmdname unmodified by eventual prefix-stripping.

    """
    cmdlen, strlen = len(str(cmdname)), len(str(string))
    mratio = 1 - (strlen - cmdlen) / (1.0 * strlen)
    args = string[cmdlen:]
    return (cmdname, args, cmdobj, cmdlen, mratio, raw_cmdname)


def build_matches(raw_string, cmdset, include_prefixes=False):
    """
    Build match tuples by matching raw_string against available commands.

    Args:
        raw_string (str): Input string that can look in any way; the only assumption is
            that the sought command's name/alias must be *first* in the string.
        cmdset (CmdSet): The current cmdset to pick Commands from.
        include_prefixes (bool): If set, include prefixes like @, ! etc (specified in settings)
            in the match, otherwise strip them before matching.

    Returns:
        matches (list) A list of match tuples created by `cmdparser.create_match`.

    """
    matches = []
    try:
        orig_string = raw_string
        if not include_prefixes and len(raw_string) > 1:
            raw_string = raw_string.lstrip(_CMD_IGNORE_PREFIXES)
        search_string = raw_string.lower()
        for cmd in cmdset:
            cmdname, raw_cmdname = cmd.match(search_string, include_prefixes=include_prefixes)
            if cmdname:
                matches.append(create_match(cmdname, raw_string, cmd, raw_cmdname))
    except Exception:
        log_trace("cmdhandler error. raw_input:%s" % raw_string)
    return matches


def try_num_differentiators(raw_string):
    """
    Test if user tried to separate multi-matches with a number separator
    (default 1-name, 2-name etc). This is usually called last, if no other
    match was found.

    Args:
        raw_string (str): The user input to parse.

    Returns:
        mindex, new_raw_string (tuple): If a multimatch-separator was detected,
            this is stripped out as an integer to separate between the matches. The
            new_raw_string is the result of stripping out that identifier. If no
            such form was found, returns (None, None).

    Example:
        In the default configuration, entering 2-ball (e.g. in a room will more
        than one 'ball' object), will lead to a multimatch and this function
        will parse `"2-ball"` and return `(2, "ball")`.

    """
    # no matches found
    num_ref_match = _MULTIMATCH_REGEX.match(raw_string)
    if num_ref_match:
        # the user might be trying to identify the command
        # with a #num-command style syntax. We expect the regex to
        # contain the groups "number" and "name".
        mindex, new_raw_string = (
            num_ref_match.group("number"),
            num_ref_match.group("name") + num_ref_match.group("args"),
        )
        return int(mindex), new_raw_string
    else:
        return None, None


def cmdparser(raw_string, cmdset, caller, match_index=None):
    """
    This function is called by the cmdhandler once it has
    gathered and merged all valid cmdsets valid for this particular parsing.

    Args:
        raw_string (str): The unparsed text entered by the caller.
        cmdset (CmdSet): The merged, currently valid cmdset
        caller (Session, Account or Object): The caller triggering this parsing.
        match_index (int, optional): Index to pick a given match in a
            list of same-named command matches. If this is given, it suggests
            this is not the first time this function was called: normally
            the first run resulted in a multimatch, and the index is given
            to select between the results for the second run.

    Returns:
        matches (list): This is a list of match-tuples as returned by `create_match`.
            If no matches were found, this is an empty list.

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
    if not raw_string:
        return []

    # find matches, first using the full name
    matches = build_matches(raw_string, cmdset, include_prefixes=True)

    if not matches or len(matches) > 1:
        # no single match, try parsing for optional numerical tags like 1-cmd
        # or cmd-2, cmd.2 etc
        match_index, new_raw_string = try_num_differentiators(raw_string)
        if match_index is not None:
            matches.extend(build_matches(new_raw_string, cmdset, include_prefixes=True))

    if not matches and _CMD_IGNORE_PREFIXES:
        # still no match. Try to strip prefixes
        raw_string = raw_string.lstrip(_CMD_IGNORE_PREFIXES) if len(raw_string) > 1 else raw_string
        matches = build_matches(raw_string, cmdset, include_prefixes=False)

    # only select command matches we are actually allowed to call.
    matches = [match for match in matches if match[2].access(caller, "cmd")]

    # try to bring the number of matches down to 1
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
        matches = matches[-quality.count(quality[-1]) :]

    if len(matches) > 1:
        # still multiple matches. Fall back to ratio-based quality.
        matches = sorted(matches, key=lambda m: m[4])
        # only pick the highest rated ratio match
        quality = [mat[4] for mat in matches]
        matches = matches[-quality.count(quality[-1]) :]

    if len(matches) > 1 and match_index is not None:
        # We couldn't separate match by quality, but we have an
        # index argument to tell us which match to use.
        if 0 < match_index <= len(matches):
            matches = [matches[match_index - 1]]
        else:
            # we tried to give an index outside of the range - this means
            # a no-match
            matches = []

    # no matter what we have at this point, we have to return it.
    return matches
