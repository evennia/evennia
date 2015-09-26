"""
RP base system for Evennia

Contribution - Griatch, 2015


This RP base system introduces the following features to a game,
common to many RP-centric games:

    emote system using director stance emoting (names/sdescs instead of
        replacing with you etc)
    sdesc obscuration of real character names for use in emotes
        and in any referencing
    recog system to assign your own nicknames to characters, can then
        be used for referencing
    pose system to set room-persistent poses, visible in room
        descriptions and when looking at the person

Emote system: This uses a customizable replacement noun (/me, @ etc)
    to represent you in the emote. You can use /sdesc, /nick, /key or
    /alias to reference objects in the room.
Sdesc system:
    This relies on an Attribute `sdesc` being set on the Character and
    makes use of a custom Character.get_display_name hook. If sdesc
    is not set, the character's `key` is used instead. This is particularly
    used in the emoting system.
Recog system:
    The user may recog a user and assign any personal nick to them. This
    will be shown in descriptions and used to reference them. This is
    making use of the nick functionality of Evennia.
Pose system:
    This is a simple Attribute that modifies the way the character is
    listed when in a room as sdesc + pose.

Examples:

> look
Tavern
The tavern is full of nice people

You see *a tall man* standing by the bar.

Above is an example of a player with an sdesc "a tall man". It is also
an example of a static *pose*: The "standing by the bar" has been set
by the player of the tall man, so that people looking at him can tell
at a glance what is going on.

> emote /me looks at /tall and says "Hello!"

I see:
    Griatch looks at Tall man and says "Hello".
Tall man (assuming his name is Tom) sees:
    The godlike figure looks at Tom and says "Hello".

"""

import re
import itertools
from copy import copy
from evennia import DefaultObject, DefaultCharacter, DefaultRoom
from evennia import Command, CmdSet
from evennia import ansi
from evennia.utils.utils import lazy_property

#------------------------------------------------------------
# Emote parser
#------------------------------------------------------------

# Settings

# The prefix is the (single-character) symbol used to find the start
# of a object reference, such as /tall (note that
# the system will understand multi-word references like '/a tall man' too).
_PREFIX = "/"

# The num_sep is the (single-character) symbol used to separate the
# sdesc from the number when  trying to separate identical sdescs from
# one another. This is the same syntax used in the rest of Evennia, so
# by default, multiple "tall" can be separated by entering 1-tall,
# 2-tall etc.
_NUM_SEP = "-"

# Texts

_EMOTE_NOMATCH_ERROR = \
"""{{RNo match for {{r{ref}{{R.{{n"""

_EMOTE_MULTIMATCH_ERROR = \
"""{{RMultiple possibilities for {ref}:
    {{r{reflist}{{n"""

_RE_FLAGS = re.MULTILINE + re.IGNORECASE + re.UNICODE

_RE_PREFIX = re.compile(r"^%s" % _PREFIX, re.UNICODE)

# The num_sep is the (single-character) symbol used to separate the
# sdesc from the number when  trying to separate identical sdescs from
# one another. This is the same syntax used in the rest of Evennia, so
# by default, multiple "tall" can be separated by entering 1-tall,
# 2-tall etc.
_NUM_SEP = "-"

# This regex will return groups (num, word), where num is an optional counter to
# separate multimatches from one another and word is the first word in the
# marker. So entering "/tall man" will return groups ("", "tall")
# and "/2-tall man" will return groups ("2", "tall").
_RE_OBJ_REF_START = re.compile(r"%s(?:([0-9]+)%s)*(\w+)" %
                    (_PREFIX, _NUM_SEP), _RE_FLAGS)

# Reference markers are used internally when distributing the emote to
# all that can see it. They are never seen by players and are on the form {#dbref}.
_RE_REF = re.compile(r"\{+\#([0-9]+)\}+")

# This regex is used to quickly reference one self in an emote.
_RE_SELF_REF = re.compile(r"/me|@", _RE_FLAGS)

# regex for non-alphanumberic end of a string
_RE_CHAREND = re.compile(r"\W+$", _RE_FLAGS)

# reference markers for language
_RE_REF_LANG = re.compile(r"\{+\##([0-9]+)\}+")
# language says in the emote are on the form "..." or langname"..." (no spaces).
# this regex returns in groups (langname, say), where langname can be empty.
_RE_LANGUAGE = re.compile(r"(?:(\w+))*(\".+?\")")

# the emote parser works in two steps:
#  1) convert the incoming emote into an intermediary
#     form with all object references mapped to ids.
#  2) for every person seeing the emote, parse this
#     intermediary form into the one valid for that char.

class EmoteError(Exception):
    pass


class SdescError(Exception):
    pass


class RecogError(Exception):
    pass


class LanguageError(Exception):
    pass


def _dummy_process(text, *args, **kwargs):
    "Pass-through processor"
    return text


# emoting mechanisms


def ordered_permutation_regex(sentence):
    """
    Builds a regex that matches 'ordered permutations' of a sentence's
    words.

    Args:
        sentence (str): The sentence to build a match pattern to

    Returns:
        regex (re object): Compiled regex object represented the
            possible ordered permutations of the sentence, from longest to
            shortest.
    Example:
         The sdesc_regex for an sdesc of " very tall man" will
         result in the following allowed permutations,
         regex-matched in inverse order of length (case-insensitive):
         "the very tall man", "the very tall", "very tall man",
         "very tall", "the very", "tall man", "the", "very", "tall",
         and "man".
         We also add regex to make sure it also accepts num-specifiers,
         like /2-tall.

    """
    # escape {#nnn} markers from sentence, replace with nnn
    sentence = _RE_REF.sub(r"\1", sentence)
    # escape {##nnn} markers, replace with nnn
    sentence = _RE_REF_LANG.sub(r"\1", sentence)
    # escape self-ref marker from sentence
    sentence = _RE_SELF_REF.sub(r"", sentence)

    # ordered permutation algorithm
    words = sentence.split()
    combinations = itertools.product((True, False), repeat=len(words))
    solution = []
    for combination in combinations:
        comb = []
        for iword, word in enumerate(words):
            if combination[iword]:
                comb.append(word)
            elif comb:
                break
        if comb:
            solution.append(_PREFIX + r"[0-9]*%s*" % _NUM_SEP + " ".join(comb))

    # compile into a match regex, first matching the longest down to the shortest components
    regex = r"|".join(sorted(set(solution), key=lambda o:len(o), reverse=True))
    return regex


def parse_language(speaker, emote):
    """
    Parse the emote for language. This is
    used with a plugin for handling languages.

    Args:
        speaker (Object): The object speaking.
        emote (str): An emote possibly containing
            language references.

    Returns:
        (emote, mapping) (tuple): A tuple where the
            `emote` is the emote string with all says
            (including quotes) replaced with reference
            markers on the form {##n} where n is a running
            number. The `mapping` is a dictionary between
            the markers and a tuple (langname, saytext), where
            langname can be None.
    Raises:
        LanguageError: If an invalid language was specified.

    Notes:
        Note that no errors are raised if the wrong language identifier
        is given.
        This data, together with the identity of the speaker, is
        intended to be used by the "listener" later, since with this
        information the language skill of the speaker can be offset to
        the language skill of the listener to determine how much
        information is actually conveyed.

    """
    # escape mapping syntax on the form {##id} if it exists already in emote,
    # if so it is replaced with just "id".
    emote = _RE_REF_LANG.sub(r"\1", emote)

    errors = []
    mapping = {}
    for imatch, say_match in enumerate(reversed(list(_RE_LANGUAGE.finditer(emote)))):
        # process matches backwards to be able to replace
        # in-place without messing up indexes for future matches
        # note that saytext includes surrounding "...".
        langname, saytext = say_match.groups()
        istart, iend = say_match.start(), say_match.end()
        # the key is simply the running match in the emote
        key = "##%i" % imatch
        # replace say with ref markers in emote
        emote = emote[:istart] + "{%s}" % key + emote[iend:]
        mapping[key] = (langname, saytext)

    if errors:
        # catch errors and report
        raise LanguageError("\n".join(errors))

    # at this point all says have been replaced with {##nn} markers
    # and mapping maps 1:1 to this.
    return emote, mapping


def parse_sdescs_and_recogs(sender, candidates, string, search_mode=False):
    """
    Read a textraw emote and parse it into an intermediary
    format for distributing to all observers.

    Args:
        sender (Object): The object sending the emote. This object's
            recog data will be considered in the parsing.
        candidates (iterable): A list of objects valid for referencing
            in the emote.
    string (str): The string (like an emote) we want to analyze for keywords.
    search_mode (bool, optional): If `True`, the "emote" is a query string
        we want to analyze. If so, the return value is changed.

    Returns:
        (emote, mapping) (tuple): If `search_mode` is `False`
            (default), a tuple where the emote is the emote string, with
            all references replaced with internal-representation {#dbref}
            markers and mapping is a dictionary `{"#dbref":"sdesc", ...}`
            if `map_obj` is `False` (default) and `{"#dbref":obj,...}`
            otherwise.
        result (list): If `search_mode` is `True` we are
            performing a search query on `string`, looking for a specific
            object. A list with zero, one or more matches.

    Raises:
        EmoteException: For various ref-matching errors.

    Notes:
        The parser analyzes and should understand the following
        _PREFIX-tagged structures in the emote:
        - self-reference (/me)
        - recogs (any part of it) stored on emoter, matching obj in `candidates`.
        - sdesc (any part of it) from any obj in `candidates`.
        - N-sdesc, N-recog separating multi-matches (1-tall, 2-tall)
        - says, "..." are

    """
    # Load all candidate regex tuples [(regex, obj, sdesc/recog),...]
    candidate_regexes = \
            [(_RE_SELF_REF, sender, sender.sdesc.get())] + \
                        [sender.recog.get_regex_tuple(obj)
            for obj in candidates if hasattr(obj, "recog")] + \
                        [obj.sdesc.get_regex_tuple()
            for obj in candidates if hasattr(obj, "sdesc")]
    # filter out non-found data
    candidate_regexes = [tup for tup in candidate_regexes if tup]

    # escape mapping syntax on the form {#id} if it exists already in emote,
    # if so it is replaced with just "id".
    string = _RE_REF.sub(r"\1", string)

    # we now loop over all references and analyze them
    mapping = {}
    errors = []
    obj = None
    nmatches = 0
    for marker_match in reversed(list(_RE_OBJ_REF_START.finditer(string))):
        # we scan backwards so we can replace in-situ without messing
        # up later occurrences. Given a marker match, query from
        # start index forward for all candidates.

        # first see if there is a number given (e.g. 1-tall)
        num_identifier, _ = marker_match.groups("") # return "" if no match, rather than None
        istart0 = marker_match.start()
        # +1 for _NUM_SEP, if defined
        istart = istart0 #+ (len(num_identifier) + 1 if num_identifier else 0)

        #print "candidates:", [tup[2] for tup in candidate_regexes]
        # loop over all candidate regexes and match against the string following the match
        matches = ((reg.match(string[istart:]), obj, text) for reg, obj, text in candidate_regexes)

        # score matches by how long part of the string was matched
        matches = [(match.end() if match else -1, obj, text) for match, obj, text in matches]
        maxscore = max(score for score, obj, text in matches)

        # we have a valid maxscore, extract all matches with this value
        bestmatches = [(obj, text) for score, obj, text in matches if maxscore == score != -1]
        nmatches = len(bestmatches)

        if not nmatches:
            # no matches
            obj = None
            nmatches = 0
        elif nmatches == 1:
            # an exact match.
            obj = bestmatches[0][0]
            nmatches = 1
        elif all(bestmatches[0][0].id == obj.id for obj, text in bestmatches):
            # multi-match but all reference the same obj (could happen
            # with clashing recogs/sdescs)
            obj = bestmatches[0][0]
            nmatches = 1
        else:
            # multi-match.
            # was a numerical identifier given to help us separate the multi-match?
            inum = min(max(0, int(num_identifier) - 1), nmatches-1) if num_identifier else None
            if inum is not None:
                # A valid inum is given. Use this to separate data
                obj = bestmatches[inum][0]
                nmatches = 1
            else:
                # no identifier given - a real multimatch
                obj = bestmatches

        if search_mode:
            # single-object search
            break
        elif nmatches == 0:
            errors.append(_EMOTE_NOMATCH_ERROR.format(ref=marker_match.group()))
        elif nmatches == 1:
            key = "#%i" % obj.id
            string = string[:istart0] + "{%s}" % key + string[istart + maxscore:]
            mapping[key] = obj if search_mode else (obj.sdesc.get() or obj.key)
        else:
            refname = marker_match.group()
            reflist = ["%s%s%s (%s%s)" % (inum+1, _NUM_SEP,
                    _RE_PREFIX.sub("", refname), text,
                    " (%s)" % sender.key if sender == obj else "")
                    for inum, (obj, text) in enumerate(bestmatches) if score == maxscore]
            errors.append(_EMOTE_MULTIMATCH_ERROR.format(
                          ref=marker_match.group(), reflist="\n    ".join(reflist)))
    if search_mode:
        # return list of object(s) matching
        if nmatches == 0:
            return []
        elif nmatches == 1:
            return [obj]
        else:
            return [tup[0] for tup in obj]

    if errors:
        # make sure to not let errors through.
        raise EmoteError("\n".join(errors))

    # at this point all references have been replaced with {#xxx} markers and the mapping contains
    # a 1:1 mapping between those inline markers and objects.
    return string, mapping


def send_emote(sender, receivers, emote, anonymous_add="first"):
    """
    Main access function for distribute an emote.

    Args:
        sender (Object): The one sending the emote.
        receivers (iterable): Receivers of the emote. These
            will also form the basis for which sdescs are
            'valid' to use in the emote.
        emote (str): The raw emote string as input by emoter.
        anonymous_add (str or None, optional): If `sender` is not
            self-referencing in the emote, this will auto-add
            `sender`'s data to the emote. Possible values are
            - None: No auto-add at anonymous emote
            - 'last': Add sender to the end of emote as [sender]
            - 'first': Prepend sender to start of emote.

    """
    try:
        emote, sdesc_mapping = parse_sdescs_and_recogs(sender, receivers, emote)
        emote, language_mapping = parse_language(sender, emote)
    except (EmoteError, LanguageError) as err:
        # handle all error messages, don't hide actual coding errors
        sender.msg(err.message)
        return

    if anonymous_add and not "#%i" % sender.id in sdesc_mapping:
        # no self-reference in the emote - add to the end
        key = "#%i" % sender.id
        sdesc_mapping[key] = sender.sdesc.get() or sender.key
        if anonymous_add == 'first':
            possessive = "" if emote.startswith('\'') else " "
            emote = "%s%s%s" % ("{%s}" % key, possessive, emote)
        else:
            emote = "%s [%s]" % (emote, "{%s}" % key)

    # broadcast emote to everyone
    for receiver in receivers:
        # we make a temporary copy that we can modify
        mapping = copy(sdesc_mapping)
        # overload mapping with receiver's recogs (which is on the same form)
        try:
            mapping.update(receiver.recog.ref2recog)
        except AttributeError:
            pass
        # handle the language mapping, which always produce different keys ##nn
        try:
            process_language = receiver.process_language
        except AttributeError:
            process_language = _dummy_process
        for key, (langname, saytext) in language_mapping.iteritems():
            # color says
            mapping[key] = process_language(saytext, sender, langname)
        # make sure receiver always sees their real name
        rkey = "#%i" % receiver.id
        if rkey in mapping:
            mapping[rkey] = receiver.key

        # add color to sdesc strings
        try:
            process_sdesc = receiver.process_sdesc
        except AttributeError:
            process_sdesc = _dummy_process

        mapping  = dict((key, process_sdesc(val, receiver))
                         for key, val in mapping.iteritems())

        # do the template replacement
        receiver.msg(emote.format(**mapping))


#------------------------------------------------------------
# RP Commands
#------------------------------------------------------------


class RPCommand(Command):
    "simple parent"
    def parse(self):
        "strip extra whitespace"
        self.args = self.args.strip()


class CmdEmote(RPCommand):  # replaces the main emote
    """
    Emote an action, allowing dynamic replacement of
    text in the emote.

    Usage:
      emote text

    Example:
      emote /me looks around.
      emote With a flurry /me attacks /tall man with his sword.
      emote "Hello", /me says.

    Describes an event in the world. This allows the use of /ref
    markers to replace with the short descriptions or recognized
    strings of objects in the same room. These will be translated to
    emotes to match each person seeing it. Use "..." for saying
    things and langcode"..." without spaces to say something in
    a different language.

    """
    key = "emote"
    aliases = [":"]
    locks = "cmd:all()"

    def func(self):
        "Perform the emote."
        if not self.args:
            self.caller.msg("What do you want to do?")
        else:
            # we also include ourselves here.
            emote = self.args
            targets = self.caller.location.contents
            if not emote.endswith((".", "!")):
                emote = "%s." % emote
            send_emote(self.caller, targets, emote, anonymous_add='first')


class CmdSdesc(RPCommand): # set/look at own sdesc
    """
    Assign yourself a short description (sdesc).

    Usage:
      sdesc <short description>

    Assigns a short description to yourself.

    """
    key = "sdesc"
    locks = "cmd:all()"

    def func(self):
        "Assign the sdesc"
        caller = self.caller
        if not self.args:
            caller.msg("Usage: sdesc <sdesc-text>")
            return
        else:
            # strip non-alfanum chars from end of sdesc
            sdesc = _RE_CHAREND.sub("", self.args)
            sdesc = caller.sdesc.add(sdesc)
            caller.msg("Your sdesc was set to '%s'." % sdesc)


class CmdPose(Command): # set current pose and default pose
    """
    Set a static pose

    Usage:
        pose <pose>
        pose default <pose>
        pose reset
        pose obj = <pose>
        pose default obj = <pose>
        pose reset obj =

    Examples:
        pose leans against the tree
        pose is talking to the barkeep.
        pose box = is sitting on the floor.

    Set a static pose. This is the end of a full sentence that
    starts with your sdesc. If no full stop is given, it will
    be added automatically. The default pose is the pose you
    get when using pose reset.

    """
    key = "pose"

    def parse(self):
        """
        Extract the "default" alternative to the pose.
        """
        args = self.args.strip()
        default = args.startswith("default")
        reset = args.startswith("reset")
        if default:
            args = re.sub(r"^default", "", args)
        if reset:
            args = re.sub(r"^reset", "", args)
        target = None
        if "=" in args:
            target, args = [part.strip() for part in args.split("=", 1)]

        self.target = target
        self.reset = reset
        self.default = default
        self.args = args.strip()

    def func(self):
        "Create the pose"
        caller = self.caller
        pose = self.args
        target = self.target
        if not pose and not self.reset:
            caller.msg("Usage: pose <pose-text> OR pose obj = <pose-text>")
            return

        if not pose.endswith("."):
            pose = "%s." % pose
        if target:
            # affect something else
            target = caller.search(target)
            if not target:
                return
            if not target.access(caller, "edit"):
                caller.msg("You can't pose that.")
                return
        else:
            target = caller

        if not target.attributes.has("pose"):
            caller.msg("%s cannot be posed." % target.key)
            return

        target_name = target.sdesc.get() if hasattr(target, "sdesc") else target.key
        # set the pose
        if self.reset:
            pose = target.db.pose_default
            target.db.pose = pose
        elif self.default:
            target.db.pose_default = pose
            caller.msg("Default pose is now '%s %s'." % (target_name, pose))
            return
        else:
            # set the pose. We do one-time ref->sdesc mapping here.
            parsed, mapping = parse_sdescs_and_recogs(caller, caller.location.contents, pose)
            print mapping
            mapping = dict((ref, obj.sdesc.get() if hasattr(obj, "sdesc") else obj.key)
                            for ref, obj in mapping.iteritems())
            parsed = parsed.format(**mapping)
            target.db.pose = parsed
        caller.msg("Pose will read '%s %s'." % (target_name, pose))


class CmdRecog(Command): # assign personal alias to object in room
    """
    Recognize another person in the same room.

    Usage:
      recog sdesc as alias

    Example:
        recog tall man as Griatch

    This will assign a personal alias for a person.

    """
    key = "recog"
    aliases = ["recognize"]

    def parse(self):
        "Parse for the sdesc as alias structure"
        if "as" in self.args:
            self.sdesc, self.alias = [part.strip() for part in self.args.split(" as ", 2)]
        else:
            self.sdesc = self.alias = None

    def func(self):
        "Assign the recog"
        caller = self.caller
        if not all((self.args, self.sdesc, self.alias)):
            caller.msg("Usage: recog <sdesc> as <alias>")
            return
        sdesc = self.sdesc
        alias = self.alias
        prefixed_sdesc = sdesc if sdesc.startswith(_PREFIX) else _PREFIX + sdesc
        candidates = caller.location.contents
        matches = parse_sdescs_and_recogs(caller, candidates, prefixed_sdesc, search_mode=True)
        nmatches = len(matches)
        # handle 0, 1 and >1 matches
        if nmatches == 0:
            caller.msg(_EMOTE_NOMATCH_ERROR.format(ref=sdesc))
        elif nmatches > 1:
            reflist = ["%s%s%s (%s%s)" % (inum+1, _NUM_SEP,
                _RE_PREFIX.sub("", sdesc), caller.recog.get(obj),
                " (%s)" % caller.key if caller == obj else "")
                    for inum, obj in enumerate(matches)]
            caller.msg(_EMOTE_MULTIMATCH_ERROR.format(ref=sdesc,reflist="\n    ".join(reflist)))
        else:
            # we have all we need, add the recog alias
            obj = matches[0]
            sdesc = obj.sdesc.get() if hasattr(obj, "sdesc") else obj.key
            alias = caller.recog.add(obj, alias)
            caller.msg("You will now remember {w%s{n as {w%s{n." % (sdesc, alias))


class RPSystemCmdSet(CmdSet):
    """
    Mix-in for adding rp-commands to default cmdset.
    """
    def at_cmdset_creation(self):
        self.add(CmdEmote())
        self.add(CmdSdesc())
        self.add(CmdPose())
        self.add(CmdRecog())


#------------------------------------------------------------
# Handlers for sdesc and recog
#------------------------------------------------------------

class SdescHandler(object):
    """
    This Handler wraps all operations with sdescs. We
    need to use this since we do a lot preparations on
    sdescs when updating them, in order for them to be
    efficient to search for and query.
    """
    def __init__(self, obj):
        """
        Initialize the handler

        Args:
            obj (Object): The entity on which this handler is stored.

        """
        self.obj = obj
        self.sdesc = ""
        self.sdesc_regex = ""
        self._cache()

    def _cache(self):
        """
        Cache data from storage

        """
        self.sdesc = self.obj.attributes.get("_sdesc", default="")
        sdesc_regex = self.obj.attributes.get("_sdesc_regex", default="")
        self.sdesc_regex = re.compile(sdesc_regex, _RE_FLAGS)

    def add(self, sdesc, max_length=60):
        """
        Add a new sdesc to object, replacing the old one.

        Args:
            sdesc (str): The sdesc to set. This may be stripped
                of control sequences before setting.
            max_length (int, optional): The max limit of the sdesc.

        Returns:
            sdesc (str): The actually set sdesc.

        Raises:
            SdescError: If the sdesc can not be set or is longer than
            `max_length`.

        """
        # strip emote components from sdesc
        sdesc = _RE_REF.sub(r"\1",
                _RE_REF_LANG.sub(r"\1",
                _RE_SELF_REF.sub(r"",
                _RE_LANGUAGE.sub(r"",
                _RE_OBJ_REF_START.sub(r"", sdesc)))))

        # make an sdesc clean of ANSI codes
        cleaned_sdesc = ansi.strip_ansi(sdesc)
        if len(cleaned_sdesc) > max_length:
            raise SdescError("Too long sdesc")

        # store to attributes
        sdesc_regex = ordered_permutation_regex(cleaned_sdesc)
        self.obj.attributes.add("_sdesc", sdesc)
        self.obj.attributes.add("_sdesc_regex", sdesc_regex)
        # local caching
        self.sdesc = sdesc
        self.sdesc_regex = re.compile(sdesc_regex, _RE_FLAGS)

        return sdesc

    def get(self):
        """
        Simple getter.

        """
        return self.sdesc

    def get_regex_tuple(self):
        """
        Return data for sdesc/recog handling

        Returns:
            tup (tuple): tuple (sdesc_regex, obj, sdesc)

        """
        return self.sdesc_regex, self.obj, self.sdesc


class RecogHandler(object):
    """
    This handler manages the recognition mapping
    of an Object.

    """
    def __init__(self, obj):
        """
        Initialize the handler

        Args:
            obj (Object): The entity on which this handler is stored.

        """
        self.obj = obj
        # mappings
        self.ref2recog = {}
        self.obj2regex = {}
        self.obj2recog = {}

    def _cache(self):
        """
        Load data to handler cache
        """
        self.ref2recog = self.obj.attributes.get("_recog_ref2recog", default={})
        obj2regex = self.obj.attributes.get("_recog_obj2regex", default={})
        obj2recog = self.obj.attributes.get("_recog_obj2recog", default={})
        self.obj2regex = dict((obj, re.compile(regex, _RE_FLAGS))
                            for obj, regex in obj2regex.items() if obj)
        self.obj2recog = dict((obj, recog)
                            for obj, recog in obj2recog.items() if obj)

    def add(self, obj, recog, max_length=60):
        """
        Assign a custom recog (nick) to the given object.

        Args:
            obj (Object): The object ot associate with the recog
                string. This is usually determined from the sdesc in the
                room by a call to parse_sdescs_and_recogs, but can also be
                given.
            recog (str): The replacement string to use with this object.
            max_length (int, optional): The max length of the recog string.

        Returns:
            recog (str): The (possibly cleaned up) recog string actually set.

        Raises:
            SdescError: When recog could not be set or sdesc longer
                than `max_length`.

        """
        # strip emote components from recog
        recog = _RE_REF.sub(r"\1",
                _RE_REF_LANG.sub(r"\1",
                _RE_SELF_REF.sub(r"",
                _RE_LANGUAGE.sub(r"",
                _RE_OBJ_REF_START.sub(r"", recog)))))

        # make an recog clean of ANSI codes
        cleaned_recog = ansi.strip_ansi(recog)
        if len(cleaned_recog) > max_length:
            raise RecogError("Too long recog")

        # mapping #dbref:obj
        key = "#%i" % obj.id
        self.obj.db._recog_ref2recog[key] = recog
        self.obj.db._recog_obj2recog[obj] = recog
        regex = ordered_permutation_regex(cleaned_recog)
        self.obj.db._recog_obj2regex[obj] = regex
        # local caching
        self.ref2recog[key] = recog
        self.obj2recog[obj] = recog
        self.obj2regex[obj] = re.compile(regex, _RE_FLAGS)
        return recog

    def get(self, obj):
        """
        Get recog replacement string, if one exists, otherwise
        get sdesc and as a last resort, the object's key.

        Args:
            obj (Object): The object, whose sdesc to replace
        Returns:
            recog (str): The replacement string to use.
        """
        return self.obj2recog.get(obj, obj.sdesc.get()
                    if hasattr(obj, "sdesc") else obj.key)

    def remove(self, obj):
        """
        Clear recog for a given object.

        Args:
            obj (Object): The object for which to remove recog.
        """
        if obj in self.obj2recog:
            del self.obj.db._recog_obj2recog[obj]
            del self.obj.db._recog_obj2regex[obj]
            del self.obj.db._recog_ref2recog["#%i" % obj.id]
        self._cache()

    def get_regex_tuple(self, obj):
        """
        Returns:
            rec (tuple): Tuple (recog_regex, obj, recog)
        """
        if obj in self.obj2recog:
            return self.obj2regex[obj], obj, self.obj2regex[obj]
        return None


#------------------------------------------------------------
# RP typeclasses
#------------------------------------------------------------

class ContribRPObject(DefaultObject):
    """
    This class is meant as a mix-in or parent for objects in an
    rp-heavy game. It implements the base functionality for poses.
    """

    def at_object_creation(self):
        """
        Called at initial creation.
        """
        super(ContribRPObject, self).at_object_creation

        # emoting/recog data
        self.db.pose = ""
        self.db.pose_default = "is here."


    def search(self, searchdata, **kwargs):
        """
        This version of search will pre-parse searchdata for eventual
        matches against recogs and sdescs of candidates in the same
        location.

        Args:
            searchdata (str): Search string.

        Notes:
            Recog/sdesc matching is always turned off if the keyword
            `global_search` is set or `candidates` are given.

        """
        if (isinstance(searchdata, basestring) and not
                (kwargs.get("global_search") or
                 kwargs.get("candidates"))):
            # searchdata is a string; common self-references
            if searchdata.lower() in ("here", ):
                return [self.location] if "quiet" in kwargs else self.location
            if searchdata.lower() in ("me", "self",):
                return [self] if "quiet" in kwargs else self
            if searchdata.lower() == self.key.lower():
                return [self] if "quiet" in kwargs else self

            # sdesc/recog matching
            candidates = self.location.contents
            matches = parse_sdescs_and_recogs(self, candidates,
                        _PREFIX + searchdata, search_mode=True)
            nmatches = len(matches)
            if nmatches == 1:
                return matches[0]
            elif nmatches > 1:
                # multimatch
                reflist = ["%s%s%s (%s%s)" % (inum+1, _NUM_SEP, searchdata, self.recog.get(obj),
                        " (%s)" % self.key if self == obj else "")
                        for inum, obj in enumerate(matches)]
                self.msg(_EMOTE_MULTIMATCH_ERROR.format(ref=searchdata,reflist="\n    ".join(reflist)))
                return

            if not self.locks.check_lockstring(self, "perm(Builders)"):
                # we block lookup unless we have access to continue
                if "nofound_string" in kwargs:
                    self.msg(kwargs["nofound_string"])
                else:
                    self.msg("There is nothing here called '%s'." % searchdata)
                return
        # fall back to normal search
        return super(ContribRPObject, self).search(searchdata, **kwargs)


    def get_display_name(self, looker, **kwargs):
        """
        Displays the name of the object in a viewer-aware manner.

        Args:
            looker (TypedObject): The object or player that is looking
                at/getting inforamtion for this object.

        Kwargs:
            pose (bool): Include the pose (if available) in the return.

        Returns:
            name (str): A string of the sdesc containing the name of the object,
            if this is defined.
                including the DBREF if this user is privileged to control
                said object.

        Notes:
            The RPObject version doesn't add color to its display.

        """
        idstr = "(#%s)" % self.id if self.access(looker, access_type='control') else ""
        try:
            recog = looker.recog.get(self)
        except AttributeError:
            recog = None
        sdesc = recog or (hasattr(self, "sdesc") and self.sdesc.get()) or self.key
        pose = " %s" % ((self.db.pose or "") if kwargs.get("pose", False) else "")
        return "%s%s%s" % (sdesc, idstr, pose)

    def return_appearance(self, looker):
        """
        This formats a description. It is the hook a 'look' command
        should call.

        Args:
            looker (Object): Object doing the looking.
        """
        if not looker:
            return
        # get and identify all objects
        visible = (con for con in self.contents if con != looker and
                                                    con.access(looker, "view"))
        exits, users, things = [], [], []
        for con in visible:
            key = con.get_display_name(looker, pose=True)
            if con.destination:
                exits.append(key)
            elif con.has_player:
                users.append(key)
            else:
                things.append(key)
        # get description, build string
        string = "{c%s{n\n" % self.get_display_name(looker, pose=True)
        desc = self.db.desc
        if desc:
            string += "%s" % desc
        if exits:
            string += "\n{wExits:{n " + ", ".join(exits)
        if users or things:
            string += "\n " + "\n ".join(users + things)
        return string

class ContribRPRoom(ContribRPObject):
    """
    Dummy inheritance for rooms.
    """
    pass


class ContribRPCharacter(DefaultCharacter, ContribRPObject):
    """
    This is a character class that has poses, sdesc and recog.
    """
    # Handlers
    @lazy_property
    def sdesc(self):
        return SdescHandler(self)

    @lazy_property
    def recog(self):
        return RecogHandler(self)

    def get_display_name(self, looker, **kwargs):
        """
        Displays the name of the object in a viewer-aware manner.

        Args:
            looker (TypedObject): The object or player that is looking
                at/getting inforamtion for this object.

        Kwargs:
            pose (bool): Include the pose (if available) in the return.

        Returns:
            name (str): A string of the sdesc containing the name of the object,
            if this is defined.
                including the DBREF if this user is privileged to control
                said object.

        Notes:
            The RPCharacter version of this method colors its display to make
            characters stand out from other objects.

        """
        idstr = "(#%s)" % self.id if self.access(looker, access_type='control') else ""
        try:
            recog = looker.recog.get(self)
        except AttributeError:
            recog = None
        sdesc = recog or (hasattr(self, "sdesc") and self.sdesc.get()) or self.key
        print "get_display_name:", self,sdesc, self.db.pose
        pose = " %s" % self.db.pose or "" if kwargs.get("pose", False) else ""
        return "{c%s{n%s%s" % (sdesc, idstr, pose)

    def at_object_creation(self):
        """
        Called at initial creation.
        """
        super(ContribRPCharacter, self).at_object_creation()

        self.db._sdesc = ""
        self.db._sdesc_regex = ""

        self.db._recog_ref2recog = {}
        self.db._recog_obj2regex = {}
        self.db._recog_obj2recog = {}

        self.cmdset.add(RPSystemCmdSet, permanent=True)
        # initializing sdesc
        self.sdesc.add("A normal person")

    def process_sdesc(self, sdesc, obj, **kwargs):
        """
        Allows to customize how your sdesc is displayed (primarily by
        changing colors).

        Args:
            sdesc (str): The sdesc to display.
            obj (Object): The object to which the adjoining sdesc
                belongs (can be yourself).

        Returns:
            sdesc (str): The processed sdesc ready
                for display.

        """
        return "{b%s{n" % sdesc

    def process_language(self, text, speaker, language, **kwargs):
        """
        Allows to process the spoken text, for example
        by obfuscating language based on your and the
        speaker's language skills. Also a good place to
        put coloring.

        Args:
            text (str): The text to process.
            speaker (Object): The object delivering the text.
            language (str): An identifier string for the language.

        Return:
            text (str): The optionally processed text.

        Notes:
            This is designed to work together with a string obfuscator
            such as the `obfuscate_language` or `obfuscate_whisper` in
            the evennia.contrib.rplanguage module.

        """
        return "{w%s{n" % text

        #from evennia.contrib import rplanguage
        #return "{w%s{n" % rplanguage.obfuscate_language(text, level=1.0)
