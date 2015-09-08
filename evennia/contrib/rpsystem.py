"""
RP base system for Evennia

Contrib by Griatch, 2015


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
from re import match as re_match
import itertools
from copy import copy
from evennia import DefaultObject, DefaultCharacter
from evennia import Command

#------------------------------------------------------------
# Emote parser
#------------------------------------------------------------

# Texts

_EMOTE_NOMATCH_ERROR = \
"""{{RNo match for {{r{ref}{{R.{{n"""

_EMOTE_MULTIMATCH_ERROR = \
"""{{RMultiple possibilities for {ref}:
    {{r{reflist}{{n"""

_LANGUAGE_NOMATCH_ERROR = \
"""{{RNo language named {{r{langname}{{n"""

_RE_FLAGS = re.MULTILINE + re.IGNORECASE + re.UNICODE

# The prefix is the (single-character) symbol used to find the start
# of a object reference, such as /tall (note that
# the system will understand multi-word references).
_PREFIX = "/"
_RE_PREFIX = re.compile(r"^/", re.UNICODE)

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

# reference markers for language
_RE_REF_LANG = re.compile(r"\{+\##([0-9]+)\}+")
# language says in the emote are on the form "..." or langname"..." (no spaces).
# this regex returns in groups (langname, say), where langname can be empty.
_RE_LANGUAGE = re.compile(r"(?:(\w+))*(\".+?\")")


#TODO
# make this into a pluggable language module for handling
# language errors and translations.

_LANGUAGE_MODULE = None # load code here
#TODO function determining if a given langname exists. Note that
# langname can be None if not specified explicitly.
_LANGUAGE_AVAILABLE = lambda langname: True
#TODO function to translate a string in a given language
_LANGUAGE_TRANSLATE = lambda speaker, listener, language, text: text
#TODO list available languages
_LANGUAGE_LIST = lambda: []


# the emote parser works in two steps:
#  1) convert the incoming emote into an intermediary
#     form with all object references mapped to ids.
#  2) for every person seeing the emote, parse this
#     intermediary form into the one valid for that char.

class EmoteError(Exception):
    pass


class SdescError(Exception):
    pass


class LanguageError(Exception):
    pass


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

    """
    # escape {#nnn} markers from sentence, replace with nnn
    sentence = _RE_REF.sub("\1", sentence)
    # escape self-ref marker from sentence
    sentence = _RE_SELF_REF.sub("", sentence)

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
            solution.append(_PREFIX + " ".join(comb))

    # compile into a match regex, first matching the longest down to the shortest components
    regex = r"|".join(sorted(set(solution), key=lambda o:len(o), reverse=True))#, re.MULTILINE + re.IGNORECASE + re.UNICODE
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
    emote = _RE_REF_LANG.sub("\1", emote)

    errors = []
    mapping = {}
    for imatch, say_match in enumerate(reversed(list(_RE_LANGUAGE.finditer(emote)))):
        # process matches backwards to be able to replace
        # in-place without messing up indexes for future matches
        # note that saytext includes surrounding "...".
        langname, saytext = say_match.group()
        if not _LANGUAGE_AVAILABLE(langname):
            errors.append(_LANGUAGE_NOMATCH_ERROR.format(langname=langname))
            continue

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


def parse_sdescs_and_recogs(sender, candidates, emote):
    """
    Read a textraw emote and parse it into an intermediary
    format for distributing to all observers.

    Args:
        sender (Object): The object sending the emote. This object's
            recog data will be considered in the parsing.
        candidates (iterable): A list of objects valid for referencing
            in the emote.
    emote (str): The incoming emote from the caller.

    Returns:
        (emote, mapping) (tuple): A tuple where the emote is
            the emote string, with all references replaced with
            internal-representation {#dbref} markers and mapping
            is a dictionary {"#dbref":obj,...}

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

    # escape mapping syntax on the form {#id} if it exists already in emote,
    # if so it is replaced with just "id".
    emote = _RE_REF.sub("\1", emote)

    # build all candidate regex tuples
    candidate_regexes = [
            (recog_regex, obj, sdesc) for obj, (recog_regex, sdesc)
            in sender.db.recog_objmap.items() if obj in candidates] + \
            [obj.db.sdesc_regex_tuple for obj in candidates]
    # pre-compile the regexes while filtering empty tuples
    print candidate_regexes
    candidate_regexes = [(re.compile(tup[0], _RE_FLAGS), tup[1], tup[2])
                         for tup in candidate_regexes if tup]

    # handle self-reference first
    mapping = {}
    if _RE_SELF_REF.search(emote):
        key = "#%i" % sender.id
        emote = _RE_SELF_REF.sub("{%s}" % key, emote)
        mapping[key] = sender.db.sdesc or sender.key

    # we now loop over all references and analyze them
    errors = []
    for marker_match in reversed(list(_RE_OBJ_REF_START.finditer(emote))):
        # we scan backwards so we can replace in-situ without messing
        # up later occurrences. Given a marker match, query from
        # start index forward for all candidates.

        # first see if there is a number given (e.g. 1-tall)
        num_identifier, _ = marker_match.groups("") # return "" if no match, rather than None
        istart0 = marker_match.start()
        # +1 for _NUM_SEP, if defined
        istart = istart0 + (len(num_identifier) + 1 if num_identifier else 0)

        print "marker match:", marker_match.group(), istart0, istart, emote[istart:]
        #print "candidates:", [tup[2] for tup in candidate_regexes]
        # loop over all candidate regexes and match against the string following the match
        matches = ((reg.match(emote[istart:]), obj, text) for reg, obj, text in candidate_regexes)

        # score matches by how long part of the string was matched
        matches = [(match.end() if match else -1, obj, text) for match, obj, text in matches]
        print "matches:", istart, matches
        maxscore = max(score for score, obj, text in matches)

        # analyze result
        if maxscore == -1:
            # No matches
            errors.append(_EMOTE_NOMATCH_ERROR.format(ref=marker_match.group()))
            continue

        # we have a valid maxscore, extract all matches with this value
        bestmatches = [(obj, text) for score, obj, text in matches if maxscore == score]
        nmatches = len(bestmatches)
        print "nmatches:", nmatches, bestmatches

        if nmatches == 1:
            # an exact match.
            obj = bestmatches[0][0]
        if nmatches:
            # several matches have the same score.
            inum = max(0, int(num_identifier) - 1) if num_identifier else None
            if all(bestmatches[0][0].id == obj.id for obj, text in bestmatches):
                # multi-matches all references the same obj (could happen with clashing recogs/sdescs)
                obj = bestmatches[0][0]
            else:
                # was a numerical identifier given to help us separate the multi-match?
                if inum is None or inum > nmatches:
                    # no match or invalid match id given
                    refname = marker_match.group()
                    reflist = ["%s%s%s (%s)" % (inum+1, _NUM_SEP, _RE_PREFIX.sub("", refname), text)
                            for inum, (obj, text) in enumerate(bestmatches) if score == maxscore]
                    errors.append(_EMOTE_MULTIMATCH_ERROR.format(
                                  ref=marker_match.group(), reflist="\n    ".join(reflist)))
                    continue
                else:
                    # A valid inum is given. Use this to separate data
                    obj = bestmatches[inum][0]

        # if we get to this point we have identifed a local object tied to this sdesc or recog marker.
        # we replace it with the interal representation on the form {#dbref}.
        print "replace emote:", istart, maxscore, emote, emote[istart + maxscore:]
        key = "#%i" % obj.id
        emote = emote[:istart0] + "{%s}" % key + emote[istart + maxscore:]
        mapping[key] = obj.db.sdesc or obj.key

    if errors:
        # make sure to not let errors through.
        raise EmoteError("\n".join(errors))

    # at this point all references have been replaced with {#xxx} markers and the mapping contains
    # a 1:1 mapping between those inline markers and objects.
    return emote, mapping


def receive_emote(sender, receiver, emote, sdesc_mapping, language_mapping):
    """
    Receive a pre-parsed emote.

    Args:
        sender (Object): The object sending the emote.
        receiver (Object): The object receiving (seeing) the emote.
        emote (str): A pre-parsed emote string created with
            `parse_emote`, with {#dbref} and {##nn} references for
            objects and languages respectively.
        sdesc_mapping (dict): A mapping between "#dbref" keys and
            objects.
        language_mapping (dict): A mapping "##dbref" and (langname, saytext).

    Returns:
        finished_emote (str): The finished and ready-to-send emote
            string, customized for receiver.

    Notes:
        This function will translage all text back based both on sdesc
        and recog mappings, but will give presedence to recog mappings.
    """
    # we make a local copy that we can modify
    mapping = copy(sdesc_mapping)
    # overload mapping with receiver's recogs (which is on the same form)
    if receiver.db.recog_refmap:
        mapping.update(receiver.db.recog_refmap)
    # handle the language mapping, which always produce different keys ##nn
    for key, (langname, saytext) in language_mapping.iteritems():
        mapping[key] = _LANGUAGE_TRANSLATE(sender, receiver, langname, saytext)
    # make sure receiver always sees their real name
    rkey = "#%i" % receiver.id
    if rkey in mapping:
        mapping[rkey] = receiver.key

    #TODO - color handling
    mapping  = dict((key, "{b%s{n" % val) for key, val in mapping.iteritems())
    receiver.msg(emote.format(**mapping))


def send_emote(sender, receivers, emote, no_anonymous=True):
    """
    Main access function for distribute an emote.

    Args:
        sender (Object): The one sending the emote.
        receivers (iterable): Receivers of the emote. These
            will also form the basis for which sdescs are
            'valid' to use in the emote.
        emote (str): The raw emote string as input by emoter.
        no_anonymous (bool, optional): Do not allow anonynous
            emotes, that is, emotes without sender self-referencing,
            but add an extra reference to the end of the emote
            if so.

    """
    print "receivers:", receivers
    try:
        emote, sdesc_mapping = parse_sdescs_and_recogs(sender, receivers, emote)
        emote, language_mapping = parse_language(sender, emote)
    except (EmoteError, LanguageError) as err:
        # handle all error messages, don't hide actual coding errors
        sender.msg(err.message)
        return

    if no_anonymous and not "#%i" % sender.id in sdesc_mapping:
        # no self-reference in the emote - add to the end
        key = "#%i" % sender.id
        emote = "%s [%s]" % (emote, "{%s}" % key)
        sdesc_mapping[key] = sender.db.sdesc or sender.key

    # broadcast emote
    for receiver in receivers:
        receive_emote(sender, receiver, emote, sdesc_mapping, language_mapping)


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
            targets = self.caller.location.contents
            send_emote(self.caller, targets, self.args, no_anonymous=True)


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
            sdesc = caller.set_sdesc(self.args)
            caller.msg("Your sdesc was set to '%s'." % sdesc)


class CmdPose(Command): # set current pose and default pose
    """
    Set a static pose

    Usage:
        pose <pose>
        pose default <pose>

    Examples:
        pose leans against the tree
        pose is talking to the barkeep.

    Set a static pose. This is the end of a full sentence that
    starts with your sdesc. If no full stop is given, it will
    be added automatically. The default pose means

    """
    key = "pose"

    def parse(self):
        """
        Extract the "default" alternative to the pose.
        """
        args = self.args.strip()
        default = args.startswith("default")
        if default:
            args = args.strip("default ")
        self.default = default
        self.args = args.strip()

    def func(self):
        "Create the pose"
        caller = self.caller
        pose = self.args
        if not pose:
            caller.msg("Usage: pose <pose-text> OR pose default <pose-text>")
        else:
            if not pose.endswith("."):
                pose = "%s." % pose
            if self.default:
                caller.db.pose_default = pose
            else:
                caller.db.pose = pose
            caller.msg("Your pose is now '%s %s'." % pose)


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
        self.sdesc, self.alias = [part.strip() for part in self.args.split(" as ", 2)]

    def func(self):
        "Assign the recog"
        caller = self.caller
        if not all(self.args, self.sdesc, self.alias):
            caller.msg("Usage: recog <sdesc> as <alias>")
        sdesc = self.sdesc
        if not sdesc.startswith("/"):
            # we make use of the emote parse mapper so
            # we need to prep the sdesc a little
            sdesc = "/%s" % sdesc
        candidates = caller.location.contents
        try:
            _, mapping = parse_sdescs_and_recogs(candidates, sdesc)

        except EmoteError as err:
            # errors are handled already here
            caller.msg(err.message)
            return
        obj = mapping.values()[0]
        # we have all we need, add the recog alias
        alias = caller.set_recog(obj, self.alias)
        caller.msg("You will now remember {w%s{n as {w%s{n." % (sdesc, alias))


class CmdLanguage(Command): # list available languages
    """
    List the available languages.

    Usages:
      languages

    This will display a list of all languages available
    and the short names needed to speak a given language in
    an emote.

    """
    key = "language"

    def func(self):
        "simple list"
        self.caller.msg("Languages available: %s" % ", ".join(_LANGUAGE_LIST))


#------------------------------------------------------------
# RP Object typeclass
#------------------------------------------------------------

class RPObject(DefaultObject):
    """
    This class is meant as a mix-in or parent for characters in an
    rp-heavy game. It implements the base functionality for sdescs,
    name replacement and look extensions.
    """

    def at_object_creation(self):
        """
        Called at initial creation.
        """
        super(RPObject, self).at_object_creation

        # emoting/recog data
        self.db.pose = ""
        self.db.pose_default = "is here."

        self.db.sdesc = None
        self.db.sdesc_regex_tuple = None
        self.set_sdesc("A normal person")
        self.db.recog_refmap = {}
        self.db.recog_objmap = {}

    def set_sdesc(self, sdesc):
        """
        Assign a new sdesc to this character. It's important
        to use this in order to set up all mappings.

        Args:
            sdesc (str): The short description to set.

        Returns:
            sdesc (str): The (possibly cleaned up) sdesc actually set.

        """
        # strip emote components from sdesc
        sdesc = _RE_REF.sub("\1",
                _RE_REF_LANG.sub("\1",
                _RE_SELF_REF.sub("",
                _RE_LANGUAGE.sub("",
                _RE_OBJ_REF_START.sub("", sdesc)))))

        self.db.sdesc = sdesc
        self.db.sdesc_regex_tuple = (ordered_permutation_regex(sdesc), self, sdesc)
        return sdesc

    def set_recog(self, obj, recog):
        """
        Assign a custom recog (nick) to the given sdesc. This
        requires that the sdesc exists in the same room as us.

        Args:
            obj (Object): The object ot associate with the recog string. This
                is usually determined from the sdesc in the room by a call to
                parse_sdescs_and_recogs, but can also be given, say as part
                of changing an existing recog value.given, say as part
            recog (str): The replacement string to use for this sdesc.

        Returns:
            recog (str): The (possibly cleaned up) recog string actually set.

        """
        # strip emote components from recog
        recog = _RE_REF.sub("\1",
                _RE_REF_LANG.sub("\1",
                _RE_SELF_REF.sub("",
                _RE_LANGUAGE.sub("",
                _RE_OBJ_REF_START.sub("", recog)))))

        # mapping #dbref:obj
        self.db.recog_refmap.update("{#%i}" % obj.id, recog)
        # mapping obj:(regex, recog)
        self.db.recog_objmap[obj] = (ordered_permutation_regex(recog), recog)

    def get_recog(self, obj):
        """
        Get recog replacement string, if one exists.

        Args:
            obj (Object): The object, whose sdesc to replace
        Returns:
            recog (str): The replacement string to use.

        """
        return self.db.recog_objmap.get(obj, (None, None))[1]

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

        """
        idstr = " (#%s)" % self.id if self.access(looker, access_type='control') else ""
        try:
            recog = looker.get_recog(self)
        except AttributeError:
            recog = None
        sdesc = recog or self.db.sdesc or self.key
        pose = " %s" % self.db.pose or "" if kwargs.get("pose", False) else ""
        return "%s%s%s" % (sdesc, pose, idstr)

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
                users.append("{c%s{n" % key)
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
            string += "\n{wYou see:{n " + "\n ".join(users + things)
        return string


class RPCharacter(DefaultCharacter, RPObject):
    """
    This is a character aware of RP systems.
    """
    def at_object_creation(self):
        super(RPCharacter, self).at_object_creation()
