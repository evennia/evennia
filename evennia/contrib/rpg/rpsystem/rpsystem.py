"""
Roleplaying base system for Evennia

Contribution - Griatch, 2015

This module contains the ContribRPObject, ContribRPRoom and
ContribRPCharacter typeclasses.  If you inherit your
objects/rooms/character from these (or make them the defaults) from
these you will get the following features:

- Objects/Rooms will get the ability to have poses and will report
  the poses of items inside them (the latter most useful for Rooms).
- Characters will get poses and also sdescs (short descriptions)
that will be used instead of their keys. They will gain commands
for managing recognition (custom sdesc-replacement), masking
themselves as well as an advanced free-form emote command.

In more detail, This RP base system introduces the following features
to a game, common to many RP-centric games:

- emote system using director stance emoting (names/sdescs).
    This uses a customizable replacement noun (/me, @ etc) to
    represent you in the emote. You can use /sdesc, /nick, /key or
    /alias to reference objects in the room. You can use any
    number of sdesc sub-parts to differentiate a local sdesc, or
    use /1-sdesc etc to differentiate them. The emote also
    identifies nested says and separates case.
- sdesc obscuration of real character names for use in emotes
    and in any referencing such as object.search().  This relies
    on an SdescHandler `sdesc` being set on the Character and
    makes use of a custom Character.get_display_name hook. If
    sdesc is not set, the character's `key` is used instead. This
    is particularly used in the emoting system.
- recog system to assign your own nicknames to characters, can then
    be used for referencing. The user may recog a user and assign
    any personal nick to them. This will be shown in descriptions
    and used to reference them. This is making use of the nick
    functionality of Evennia.
- masks to hide your identity (using a simple lock).
- pose system to set room-persistent poses, visible in room
    descriptions and when looking at the person/object.  This is a
    simple Attribute that modifies how the characters is viewed when
    in a room as sdesc + pose.
- in-emote says, including seamless integration with language
    obscuration routine (such as contrib/rpg/rplanguage.py)

Installation:

Add `RPSystemCmdSet` from this module to your CharacterCmdSet:

```python
# mygame/commands/default_cmdsets.py

# ...

from evennia.contrib.rpg.rpsystem.rpsystem import RPSystemCmdSet  <---

class CharacterCmdSet(default_cmds.CharacterCmdset):
    # ...
    def at_cmdset_creation(self):
        # ...
        self.add(RPSystemCmdSet())  # <---

```

You also need to make your Characters/Objects/Rooms inherit from
the typeclasses in this module:

```python
# in mygame/typeclasses/characters.py

from evennia.contrib.rpg.rpsystem.rpsystem import ContribRPCharacter

class Character(ContribRPCharacter):
    # ...

```

```python
# in mygame/typeclasses/objects.py

from evennia.contrib.rpg.rpsystem.rpsystem import ContribRPObject

class Object(ContribRPObject):
    # ...

```

```python
# in mygame/typeclasses/rooms.py

from evennia.contrib.rpg.rpsystem.rpsystem import ContribRPRoom

class Room(ContribRPRoom):
    # ...

```

Examples:

> look
Tavern
The tavern is full of nice people

*A tall man* is standing by the bar.

Above is an example of a player with an sdesc "a tall man". It is also
an example of a static *pose*: The "standing by the bar" has been set
by the player of the tall man, so that people looking at him can tell
at a glance what is going on.

> emote /me looks at /Tall and says "Hello!"

I see:
    Griatch looks at Tall man and says "Hello".
Tall man (assuming his name is Tom) sees:
    The godlike figure looks at Tom and says "Hello".

Note that by default, the case of the tag matters, so `/tall` will
lead to 'tall man' while `/Tall` will become 'Tall man' and /TALL
becomes /TALL MAN. If you don't want this behavior, you can pass
case_sensitive=False to the `send_emote` function.

Extra Installation Instructions:

1. In typeclasses/character.py:
   Import the `ContribRPCharacter` class:
       `from evennia.contrib.rpg.rpsystem.rpsystem import ContribRPCharacter`
   Inherit ContribRPCharacter:
       Change "class Character(DefaultCharacter):" to
       `class Character(ContribRPCharacter):`
   If you have any overriden calls in `at_object_creation(self)`:
       Add `super().at_object_creation()` as the top line.
2. In `typeclasses/rooms.py`:
       Import the `ContribRPRoom` class:
       `from evennia.contrib.rpg.rpsystem.rpsystem import ContribRPRoom`
   Inherit `ContribRPRoom`:
       Change `class Room(DefaultRoom):` to
       `class Room(ContribRPRoom):`
3. In `typeclasses/objects.py`
       Import the `ContribRPObject` class:
       `from evennia.contrib.rpg.rpsystem.rpsystem import ContribRPObject`
   Inherit `ContribRPObject`:
       Change `class Object(DefaultObject):` to
       `class Object(ContribRPObject):`
4. Reload the server (`reload` or from console: "evennia reload")
5. Force typeclass updates as required. Example for your character:
       `type/reset/force me = typeclasses.characters.Character`

"""
import re
from collections import defaultdict
from string import punctuation

import inflect
from django.conf import settings

from evennia.commands.cmdset import CmdSet
from evennia.commands.command import Command
from evennia.objects.models import ObjectDB
from evennia.objects.objects import DefaultCharacter, DefaultObject
from evennia.utils import ansi, logger
from evennia.utils.utils import (
    iter_to_str,
    lazy_property,
    make_iter,
    variable_from_module,
)

_INFLECT = inflect.engine()

_AT_SEARCH_RESULT = variable_from_module(*settings.SEARCH_AT_RESULT.rsplit(".", 1))
# ------------------------------------------------------------
# Emote parser
# ------------------------------------------------------------

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

_EMOTE_NOMATCH_ERROR = """|RNo match for |r{ref}|R.|n"""

_EMOTE_MULTIMATCH_ERROR = """|RMultiple possibilities for {ref}:
    |r{reflist}|n"""

_RE_FLAGS = re.MULTILINE + re.IGNORECASE + re.UNICODE

_RE_PREFIX = re.compile(rf"^{_PREFIX}", re.UNICODE)

# This regex will return groups (num, word), where num is an optional counter to
# separate multimatches from one another and word is the first word in the
# marker. So entering "/tall man" will return groups ("", "tall")
# and "/2-tall man" will return groups ("2", "tall").
_RE_OBJ_REF_START = re.compile(rf"{_PREFIX}(?:([0-9]+){_NUM_SEP})*(\w+)", _RE_FLAGS)

_RE_LEFT_BRACKETS = re.compile(r"\{+", _RE_FLAGS)
_RE_RIGHT_BRACKETS = re.compile(r"\}+", _RE_FLAGS)
# Reference markers are used internally when distributing the emote to
# all that can see it. They are never seen by players and are on the form {#dbref<char>}
# with the <char> indicating case of the original reference query (like ^ for uppercase)
_RE_REF = re.compile(r"\{+\#([0-9]+[\^\~tv]{0,1})\}+")

# This regex is used to quickly reference one self in an emote.
_RE_SELF_REF = re.compile(r"(/me|@)(?=\W+)", _RE_FLAGS)

# regex for non-alphanumberic end of a string
_RE_CHAREND = re.compile(r"\W+$", _RE_FLAGS)

# reference markers for language
_RE_REF_LANG = re.compile(r"\{+\##([0-9]+)\}+")
# language says in the emote are on the form "..." or langname"..." (no spaces).
# this regex returns in groups (langname, say), where langname can be empty.
_RE_LANGUAGE = re.compile(r"(?:\((\w+)\))*(\".+?\")")


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


def _get_case_ref(string):
    """
    Helper function which parses capitalization and
    returns the appropriate case-ref character for emotes.
    """
    # default to retaining the original case
    case = "~"
    # internal flags for the case used for the original /query
    # - t for titled input (like /Name)
    # - ^ for all upercase input (like /NAME)
    # - v for lower-case input (like /name)
    # - ~ for mixed case input (like /nAmE)
    if string.istitle():
        case = "t"
    elif string.isupper():
        case = "^"
    elif string.islower():
        case = "v"

    return case


# emoting mechanisms
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
        evennia.contrib.rpg.rpsystem.LanguageError: If an invalid language was
        specified.

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
        key = f"##{imatch}"
        # replace say with ref markers in emote
        emote = "{start}{{{key}}}{end}".format(start=emote[:istart], key=key, end=emote[iend:])
        mapping[key] = (langname, saytext)

    if errors:
        # catch errors and report
        raise LanguageError("\n".join(errors))

    # at this point all says have been replaced with {##nn} markers
    # and mapping maps 1:1 to this.
    return emote, mapping


def parse_sdescs_and_recogs(
    sender, candidates, string, search_mode=False, case_sensitive=True, fallback=None
):
    """
    Read a raw emote and parse it into an intermediary
    format for distributing to all observers.

    Args:
        sender (Object): The object sending the emote. This object's
            recog data will be considered in the parsing.
        candidates (iterable): A list of objects valid for referencing
            in the emote.
    string (str): The string (like an emote) we want to analyze for keywords.
    search_mode (bool, optional): If `True`, the "emote" is a query string
        we want to analyze. If so, the return value is changed.
    case_sensitive (bool, optional): If set, the case of /refs matter, so that
        /tall will come out as 'tall man' while /Tall will become 'Tall man'.
        This allows for more grammatically correct emotes at the cost of being
        a little more to learn for players. If disabled, the original sdesc case
        is always kept and are inserted as-is.
    fallback (string, optional): If set, any references that don't match a target
        will be replaced with the fallback string. If `None` (default), the
        parsing will fail and give a warning about the missing reference.

    Returns:
        (emote, mapping) (tuple): If `search_mode` is `False`
            (default), a tuple where the emote is the emote string, with
            all references replaced with internal-representation {#dbref}
            markers and mapping is a dictionary `{"#dbref":obj, ...}`.
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
    # build a list of candidates with all possible referrable names
    # include 'me' keyword for self-ref
    candidate_map = []
    for obj in candidates:
        # check if sender has any recogs for obj and add
        if hasattr(sender, "recog"):
            if recog := sender.recog.get(obj):
                candidate_map.append((obj, recog))
        # check if obj has an sdesc and add
        if hasattr(obj, "sdesc"):
            candidate_map.append((obj, obj.sdesc.get()))
        # if no sdesc, include key plus aliases instead
        else:
            candidate_map.append((obj, obj.key))
        candidate_map.extend([(obj, alias) for alias in obj.aliases.all()])

    # escape mapping syntax on the form {#id} if it exists already in emote,
    # if so it is replaced with just "id".
    string = _RE_REF.sub(r"\1", string)
    # escape loose { } brackets since this will clash with formatting
    string = _RE_LEFT_BRACKETS.sub("{{", string)
    string = _RE_RIGHT_BRACKETS.sub("}}", string)

    # we now loop over all references and analyze them
    mapping = {}
    errors = []
    obj = None
    nmatches = 0
    # first, find and replace any self-refs
    for self_match in list(_RE_SELF_REF.finditer(string)):
        matched = self_match.group()
        case = _get_case_ref(matched.lstrip(_PREFIX)) if case_sensitive else ""
        key = f"#{sender.id}{case}"
        # replaced with ref
        string = _RE_SELF_REF.sub(f"{{{key}}}", string, count=1)
        mapping[key] = sender

    for marker_match in reversed(list(_RE_OBJ_REF_START.finditer(string))):
        # we scan backwards so we can replace in-situ without messing
        # up later occurrences. Given a marker match, query from
        # start index forward for all candidates.

        # first see if there is a number given (e.g. 1-tall)
        num_identifier, _ = marker_match.groups("")  # return "" if no match, rather than None
        match_index = marker_match.start()
        # split the emote string at the reference marker, to process everything after it
        head = string[:match_index]
        tail = string[match_index + 1 :]

        if search_mode:
            # match the candidates against the whole search string after the marker
            rquery = "".join(
                [
                    r"\b(" + re.escape(word.strip(punctuation)) + r").*"
                    for word in iter(tail.split())
                ]
            )
            matches = (
                (re.search(rquery, text, _RE_FLAGS), obj, text) for obj, text in candidate_map
            )
            # filter out any non-matching candidates
            bestmatches = [(obj, match.group()) for match, obj, text in matches if match]

        else:
            # to find the longest match, we start from the marker and lengthen the
            # match query one word at a time.
            word_list = []
            bestmatches = []
            # preserve punctuation when splitting
            tail = re.split("(\W)", tail)
            iend = 0
            for i, item in enumerate(tail):
                # don't add non-word characters to the search query
                if not item.isalpha():
                    continue
                word_list.append(item)
                rquery = "".join([r"\b(" + re.escape(word) + r").*" for word in word_list])
                # match candidates against the current set of words
                matches = (
                    (re.search(rquery, text, _RE_FLAGS), obj, text) for obj, text in candidate_map
                )
                matches = [(obj, match.group()) for match, obj, text in matches if match]
                if len(matches) == 0:
                    # no matches at this length, keep previous iteration as best
                    break
                # since this is the longest match so far, set latest match set as best matches
                bestmatches = matches
                # save current index as end point of matched text
                iend = i

            # save search string
            matched_text = "".join(tail[1:iend])
            # recombine remainder of emote back into a string
            tail = "".join(tail[iend + 1 :])

        nmatches = len(bestmatches)

        if not nmatches:
            # no matches
            obj = None
            nmatches = 0
        elif nmatches == 1:
            # an exact match.
            obj, match_str = bestmatches[0]
        elif all(bestmatches[0][0].id == obj.id for obj, text in bestmatches):
            # multi-match but all matches actually reference the same
            # obj (could happen with clashing recogs + sdescs)
            obj, match_str = bestmatches[0]
            nmatches = 1
        else:
            # multi-match.
            # was a numerical identifier given to help us separate the multi-match?
            inum = min(max(0, int(num_identifier) - 1), nmatches - 1) if num_identifier else None
            if inum is not None:
                # A valid inum is given. Use this to separate data.
                obj, match_str = bestmatches[inum]
                nmatches = 1
            else:
                # no identifier given - a real multimatch.
                obj = bestmatches

        if search_mode:
            # single-object search mode. Don't continue loop.
            break
        elif nmatches == 0:
            if fallback:
                # replace unmatched reference with the fallback string
                string = f"{head}{fallback}{tail}"
            else:
                errors.append(_EMOTE_NOMATCH_ERROR.format(ref=marker_match.group()))
        elif nmatches == 1:
            # a unique match - parse into intermediary representation
            case = _get_case_ref(marker_match.group()) if case_sensitive else ""
            # recombine emote with matched text replaced by ref
            key = f"#{obj.id}{case}"
            string = f"{head}{{{key}}}{tail}"
            mapping[key] = obj

        else:
            # multimatch error
            refname = marker_match.group()
            reflist = [
                "{num}{sep}{name} ({text}{key})".format(
                    num=inum + 1,
                    sep=_NUM_SEP,
                    name=_RE_PREFIX.sub("", refname),
                    text=text,
                    key=f" ({sender.key})" if sender == ob else "",
                )
                for inum, (ob, text) in enumerate(obj)
            ]
            errors.append(
                _EMOTE_MULTIMATCH_ERROR.format(
                    ref=marker_match.group(), reflist="\n    ".join(reflist)
                )
            )
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


def send_emote(sender, receivers, emote, msg_type="pose", anonymous_add="first", **kwargs):
    """
    Main access function for distribute an emote.

    Args:
        sender (Object): The one sending the emote.
        receivers (iterable): Receivers of the emote. These
            will also form the basis for which sdescs are
            'valid' to use in the emote.
        emote (str): The raw emote string as input by emoter.
        msg_type (str): The type of emote this is. "say" or "pose"
            for example. This is arbitrary and used for generating
            extra data for .msg(text) tuple.
        anonymous_add (str or None, optional): If `sender` is not
            self-referencing in the emote, this will auto-add
            `sender`'s data to the emote. Possible values are
            - None: No auto-add at anonymous emote
            - 'last': Add sender to the end of emote as [sender]
            - 'first': Prepend sender to start of emote.
    Kwargs:
        case_sensitive (bool): Defaults to True, but can be unset
            here. When enabled, /tall will lead to a lowercase
            'tall man' while /Tall will lead to 'Tall man' and
            /TALL will lead to 'TALL MAN'. If disabled, the sdesc's
            case will always be used, regardless of the /ref case used.
        any: Other kwargs will be passed on into the receiver's process_sdesc and
            process_recog methods, and can thus be used to customize those.

    """
    case_sensitive = kwargs.pop("case_sensitive", True)
    fallback = kwargs.pop("fallback", None)
    try:
        emote, obj_mapping = parse_sdescs_and_recogs(
            sender, receivers, emote, case_sensitive=case_sensitive, fallback=fallback
        )
        emote, language_mapping = parse_language(sender, emote)
    except (EmoteError, LanguageError) as err:
        # handle all error messages, don't hide actual coding errors
        sender.msg(str(err))
        return

    skey = f"#{sender.id}"

    # we escape the object mappings since we'll do the language ones first
    # (the text could have nested object mappings).
    emote = _RE_REF.sub(r"{{#\1}}", emote)
    # if anonymous_add is passed as a kwarg, collect and remove it from kwargs
    if "anonymous_add" in kwargs:
        anonymous_add = kwargs.pop("anonymous_add")
    # make sure to catch all possible self-refs
    self_refs = [f"{skey}{ref}" for ref in ("t", "^", "v", "~", "")]
    if anonymous_add and not any(1 for tag in obj_mapping if tag in self_refs):
        # no self-reference in the emote - add it
        if anonymous_add == "first":
            # add case flag for initial caps
            skey += "t"
            # don't put a space after the self-ref if it's a possessive emote
            femote = "{key}{emote}" if emote.startswith("'") else "{key} {emote}"
        else:
            # add it to the end
            femote = "{emote} [{key}]"
        emote = femote.format(key="{{" + skey + "}}", emote=emote)
        obj_mapping[skey] = sender

    # broadcast emote to everyone
    for receiver in receivers:
        # first handle the language mapping, which always produce different keys ##nn
        if hasattr(receiver, "process_language") and callable(receiver.process_language):
            receiver_lang_mapping = {
                key: receiver.process_language(saytext, sender, langname)
                for key, (langname, saytext) in language_mapping.items()
            }
        else:
            receiver_lang_mapping = {
                key: saytext for key, (langname, saytext) in language_mapping.items()
            }
        # map the language {##num} markers. This will convert the escaped sdesc markers on
        # the form {{#num}} to {#num} markers ready to sdesc-map in the next step.
        sendemote = emote.format_map(receiver_lang_mapping)

        # map the ref keys to sdescs
        receiver_sdesc_mapping = dict(
            (
                ref,
                obj.get_display_name(receiver, ref=ref, noid=True),
            )
            for ref, obj in obj_mapping.items()
        )

        # do the template replacement of the sdesc/recog {#num} markers
        receiver.msg(
            text=(sendemote.format_map(receiver_sdesc_mapping), {"type": msg_type}),
            from_obj=sender,
            **kwargs,
        )


# ------------------------------------------------------------
# Handlers for sdesc and recog
# ------------------------------------------------------------


class SdescHandler:
    """
    This Handler wraps all operations with sdescs. We
    need to use this since we do a lot preparations on
    sdescs when updating them, in order for them to be
    efficient to search for and query.

    The handler stores data in the following Attributes

        _sdesc   - a string
        _regex  - an empty dictionary

    """

    def __init__(self, obj):
        """
        Initialize the handler

        Args:
            obj (Object): The entity on which this handler is stored.

        """
        self.obj = obj
        self.sdesc = ""
        self._cache()

    def _cache(self):
        """
        Cache data from storage
        """
        self.sdesc = self.obj.attributes.get("_sdesc", default=self.obj.key)

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
            SdescError: If the sdesc is empty, can not be set or is
            longer than `max_length`.

        """
        # strip emote components from sdesc
        sdesc = _RE_REF.sub(
            r"\1",
            _RE_REF_LANG.sub(
                r"\1",
                _RE_SELF_REF.sub(r"", _RE_LANGUAGE.sub(r"", _RE_OBJ_REF_START.sub(r"", sdesc))),
            ),
        )

        # make an sdesc clean of ANSI codes
        cleaned_sdesc = ansi.strip_ansi(sdesc)

        if not cleaned_sdesc:
            raise SdescError("Short desc cannot be empty.")

        if len(cleaned_sdesc) > max_length:
            raise SdescError(
                "Short desc can max be {} chars long (was {} chars).".format(
                    max_length, len(cleaned_sdesc)
                )
            )

        # store to attributes
        self.obj.attributes.add("_sdesc", sdesc)
        # local caching
        self.sdesc = sdesc

        return sdesc

    def get(self):
        """
        Simple getter. The sdesc should never be allowed to
        be empty, but if it is we must fall back to the key.

        """
        return self.sdesc or self.obj.key


class RecogHandler:
    """
    This handler manages the recognition mapping
    of an Object.

    The handler stores data in Attributes as dictionaries of
    the following names:

        _recog_ref2recog
        _recog_obj2recog

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
        self.obj2recog = {}
        self._cache()

    def _cache(self):
        """
        Load data to handler cache
        """
        self.ref2recog = self.obj.attributes.get("_recog_ref2recog", default={})
        obj2recog = self.obj.attributes.get("_recog_obj2recog", default={})
        self.obj2recog = dict((obj, recog) for obj, recog in obj2recog.items() if obj)

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
        if not obj.access(self.obj, "enable_recog", default=True):
            raise SdescError("This person is unrecognizeable.")

        # strip emote components from recog
        recog = _RE_REF.sub(
            r"\1",
            _RE_REF_LANG.sub(
                r"\1",
                _RE_SELF_REF.sub(r"", _RE_LANGUAGE.sub(r"", _RE_OBJ_REF_START.sub(r"", recog))),
            ),
        )

        # make an recog clean of ANSI codes
        cleaned_recog = ansi.strip_ansi(recog)

        if not cleaned_recog:
            raise SdescError("Recog string cannot be empty.")

        if len(cleaned_recog) > max_length:
            raise RecogError(
                "Recog string cannot be longer than {} chars (was {} chars)".format(
                    max_length, len(cleaned_recog)
                )
            )

        # mapping #dbref:obj
        key = f"#{obj.id}"
        self.obj.attributes.get("_recog_ref2recog", default={})[key] = recog
        self.obj.attributes.get("_recog_obj2recog", default={})[obj] = recog
        # local caching
        self.ref2recog[key] = recog
        self.obj2recog[obj] = recog
        return recog

    def get(self, obj):
        """
        Get recog replacement string, if one exists.

        Args:
            obj (Object): The object, whose sdesc to replace
        Returns:
            recog (str or None): The replacement string to use, or
                None if there is no recog for this object.

        Notes:
            This method will respect a "enable_recog" lock set on
            `obj` (True by default) in order to turn off recog
            mechanism. This is useful for adding masks/hoods etc.
        """
        if obj.access(self.obj, "enable_recog", default=True):
            # check an eventual recog_masked lock on the object
            # to avoid revealing masked characters. If lock
            # does not exist, pass automatically.
            return self.obj2recog.get(obj, None)
        else:
            # recog_mask lock not passed, disable recog
            return None

    def all(self):
        """
        Get a mapping of the recogs stored in handler.

        Returns:
            recogs (dict): A mapping of {recog: obj} stored in handler.

        """
        return {self.obj2recog[obj]: obj for obj in self.obj2recog.keys()}

    def remove(self, obj):
        """
        Clear recog for a given object.

        Args:
            obj (Object): The object for which to remove recog.
        """
        if obj in self.obj2recog:
            del self.obj.db._recog_obj2recog[obj]
            del self.obj.db._recog_ref2recog[f"#{obj.id}"]
        self._cache()


# ------------------------------------------------------------
# RP Commands
# ------------------------------------------------------------


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
    arg_regex = ""

    def func(self):
        "Perform the emote."
        if not self.args:
            self.caller.msg("What do you want to do?")
        else:
            # we also include ourselves here.
            emote = self.args
            targets = self.caller.location.contents
            if not emote.endswith((".", "?", "!", '"')):  # If emote is not punctuated or speech,
                emote += "."  # add a full-stop for good measure.
            send_emote(self.caller, targets, emote, anonymous_add="first")


class CmdSay(RPCommand):  # replaces standard say
    """
    speak as your character

    Usage:
      say <message>

    Talk to those in your current location.
    """

    key = "say"
    aliases = ['"', "'"]
    locks = "cmd:all()"
    arg_regex = ""

    def func(self):
        "Run the say command"

        caller = self.caller

        if not self.args:
            caller.msg("Say what?")
            return

        # calling the speech modifying hook
        speech = caller.at_pre_say(self.args)
        targets = self.caller.location.contents
        send_emote(self.caller, targets, speech, msg_type="say", anonymous_add=None)


class CmdSdesc(RPCommand):  # set/look at own sdesc
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
            try:
                sdesc = caller.sdesc.add(sdesc)
            except SdescError as err:
                caller.msg(err)
                return
            except AttributeError:
                caller.msg(f"Cannot set sdesc on {caller.key}.")
                return
            caller.msg(f"{caller.key}'s sdesc was set to '{sdesc}'.")


class CmdPose(RPCommand):  # set current pose and default pose
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

    Set a static pose. This is the end of a full sentence that starts
    with your sdesc. If no full stop is given, it will be added
    automatically. The default pose is the pose you get when using
    pose reset. Note that you can use sdescs/recogs to reference
    people in your pose, but these always appear as that person's
    sdesc in the emote, regardless of who is seeing it.

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

        if not pose.endswith((".", "?", "!", '"')):
            pose += "."
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

        target_name = target.sdesc.get() if hasattr(target, "sdesc") else target.key
        if not target.attributes.has("pose"):
            caller.msg(f"{target_name} cannot be posed.")
            return

        # set the pose
        if self.reset:
            pose = target.db.pose_default
            target.db.pose = pose
        elif self.default:
            target.db.pose_default = pose
            caller.msg(f"Default pose is now '{target_name} {pose}'.")
            return
        else:
            # set the pose. We do one-time ref->sdesc mapping here.
            parsed, mapping = parse_sdescs_and_recogs(caller, caller.location.contents, pose)
            mapping = dict(
                (ref, obj.sdesc.get() if hasattr(obj, "sdesc") else obj.key)
                for ref, obj in mapping.items()
            )
            pose = parsed.format_map(mapping)

            if len(target_name) + len(pose) > 60:
                caller.msg(f"'{pose}' is too long.")
                return

            target.db.pose = pose

        caller.msg(f"Pose will read '{target_name} {pose}'.")


class CmdRecog(RPCommand):  # assign personal alias to object in room
    """
    Recognize another person in the same room.

    Usage:
      recog
      recog sdesc as alias
      forget alias

    Example:
        recog tall man as Griatch
        forget griatch

    This will assign a personal alias for a person, or forget said alias.
    Using the command without arguments will list all current recogs.

    """

    key = "recog"
    aliases = ["recognize", "forget"]

    def parse(self):
        "Parse for the sdesc as alias structure"
        self.sdesc, self.alias = "", ""
        if " as " in self.args:
            self.sdesc, self.alias = [part.strip() for part in self.args.split(" as ", 2)]
        elif self.args:
            # try to split by space instead
            try:
                self.sdesc, self.alias = [part.strip() for part in self.args.split(None, 1)]
            except ValueError:
                self.sdesc, self.alias = self.args.strip(), ""

    def func(self):
        "Assign the recog"
        caller = self.caller
        alias = self.alias.rstrip(".?!")
        sdesc = self.sdesc

        recog_mode = self.cmdstring != "forget" and alias and sdesc
        forget_mode = self.cmdstring == "forget" and sdesc
        list_mode = not self.args

        if not (recog_mode or forget_mode or list_mode):
            caller.msg("Usage: recog, recog <sdesc> as <alias> or forget <alias>")
            return

        if list_mode:
            # list all previously set recogs
            all_recogs = caller.recog.all()
            if not all_recogs:
                caller.msg(
                    "You recognize no-one. (Use 'recog <sdesc> as <alias>' to recognize people."
                )
            else:
                # note that we don't skip those failing enable_recog lock here,
                # because that would actually reveal more than we want.
                lst = "\n".join(
                    " {}  ({})".format(key, obj.sdesc.get() if hasattr(obj, "sdesc") else obj.key)
                    for key, obj in all_recogs.items()
                )
                caller.msg(
                    "Currently recognized (use 'recog <sdesc> as <alias>' to add "
                    f"new and 'forget <alias>' to remove):\n{lst}"
                )
            return

        prefixed_sdesc = sdesc if sdesc.startswith(_PREFIX) else _PREFIX + sdesc
        candidates = caller.location.contents
        matches = parse_sdescs_and_recogs(caller, candidates, prefixed_sdesc, search_mode=True)
        nmatches = len(matches)
        # handle 0 and >1 matches
        if nmatches == 0:
            caller.msg(_EMOTE_NOMATCH_ERROR.format(ref=sdesc))
        elif nmatches > 1:
            reflist = [
                "{num}{sep}{sdesc} ({recog}{key})".format(
                    num=inum + 1,
                    sep=_NUM_SEP,
                    sdesc=_RE_PREFIX.sub("", sdesc),
                    recog=caller.recog.get(obj) or "no recog",
                    key=f" ({caller.key})" if caller == obj else "",
                )
                for inum, obj in enumerate(matches)
            ]
            caller.msg(_EMOTE_MULTIMATCH_ERROR.format(ref=sdesc, reflist="\n    ".join(reflist)))

        else:
            # one single match
            obj = matches[0]
            if not obj.access(self.obj, "enable_recog", default=True):
                # don't apply recog if object doesn't allow it (e.g. by being masked).
                caller.msg("It's impossible to recognize them.")
                return
            if forget_mode:
                # remove existing recog
                caller.recog.remove(obj)
                caller.msg(
                    "You will now know them only as '{}'.".format(
                        obj.get_display_name(caller, noid=True)
                    )
                )
            else:
                # set recog
                sdesc = obj.sdesc.get() if hasattr(obj, "sdesc") else obj.key
                try:
                    alias = caller.recog.add(obj, alias)
                except RecogError as err:
                    caller.msg(err)
                    return
                caller.msg("You will now remember |w{}|n as |w{}|n.".format(sdesc, alias))


class CmdMask(RPCommand):
    """
    Wear a mask

    Usage:
        mask <new sdesc>
        unmask

    This will put on a mask to hide your identity. When wearing
    a mask, your sdesc will be replaced by the sdesc you pick and
    people's recognitions of you will be disabled.

    """

    key = "mask"
    aliases = ["unmask"]

    def func(self):
        caller = self.caller
        if self.cmdstring == "mask":
            # wear a mask
            if not self.args:
                caller.msg("Usage: (un)mask sdesc")
                return
            if caller.db.unmasked_sdesc:
                caller.msg("You are already wearing a mask.")
                return
            sdesc = _RE_CHAREND.sub("", self.args)
            sdesc = f"{sdesc} |H[masked]|n"
            if len(sdesc) > 60:
                caller.msg("Your masked sdesc is too long.")
                return
            caller.db.unmasked_sdesc = caller.sdesc.get()
            caller.locks.add("enable_recog:false()")
            caller.sdesc.add(sdesc)
            caller.msg(f"You wear a mask as '{sdesc}'.")
        else:
            # unmask
            old_sdesc = caller.db.unmasked_sdesc
            if not old_sdesc:
                caller.msg("You are not wearing a mask.")
                return
            del caller.db.unmasked_sdesc
            caller.locks.remove("enable_recog")
            caller.sdesc.add(old_sdesc)
            caller.msg(f"You remove your mask and are again '{old_sdesc}'.")


class RPSystemCmdSet(CmdSet):
    """
    Mix-in for adding rp-commands to default cmdset.
    """

    def at_cmdset_creation(self):
        self.add(CmdEmote())
        self.add(CmdSay())
        self.add(CmdSdesc())
        self.add(CmdPose())
        self.add(CmdRecog())
        self.add(CmdMask())


# ------------------------------------------------------------
# RP typeclasses
# ------------------------------------------------------------


class ContribRPObject(DefaultObject):
    """
    This class is meant as a mix-in or parent for objects in an
    rp-heavy game. It implements the base functionality for poses.
    """

    @lazy_property
    def sdesc(self):
        return SdescHandler(self)

    def at_object_creation(self):
        """
        Called at initial creation.
        """
        super().at_object_creation()

        # emoting/recog data
        self.db.pose = ""
        self.db.pose_default = "is here."
        self.db._sdesc = ""

    def search(
        self,
        searchdata,
        global_search=False,
        use_nicks=True,
        typeclass=None,
        location=None,
        attribute_name=None,
        quiet=False,
        exact=False,
        candidates=None,
        nofound_string=None,
        multimatch_string=None,
        use_dbref=None,
    ):
        """
        Returns an Object matching a search string/condition, taking
        sdescs into account.

        Perform a standard object search in the database, handling
        multiple results and lack thereof gracefully. By default, only
        objects in the current `location` of `self` or its inventory are searched for.

        Args:
            searchdata (str or obj): Primary search criterion. Will be matched
                against `object.key` (with `object.aliases` second) unless
                the keyword attribute_name specifies otherwise.
                **Special strings:**
                - `#<num>`: search by unique dbref. This is always
                   a global search.
                - `me,self`: self-reference to this object
                - `<num>-<string>` - can be used to differentiate
                   between multiple same-named matches
            global_search (bool): Search all objects globally. This is overruled
                by `location` keyword.
            use_nicks (bool): Use nickname-replace (nicktype "object") on `searchdata`.
            typeclass (str or Typeclass, or list of either): Limit search only
                to `Objects` with this typeclass. May be a list of typeclasses
                for a broader search.
            location (Object or list): Specify a location or multiple locations
                to search. Note that this is used to query the *contents* of a
                location and will not match for the location itself -
                if you want that, don't set this or use `candidates` to specify
                exactly which objects should be searched.
            attribute_name (str): Define which property to search. If set, no
                key+alias search will be performed. This can be used
                to search database fields (db_ will be automatically
                appended), and if that fails, it will try to return
                objects having Attributes with this name and value
                equal to searchdata. A special use is to search for
                "key" here if you want to do a key-search without
                including aliases.
            quiet (bool): don't display default error messages - this tells the
                search method that the user wants to handle all errors
                themselves. It also changes the return value type, see
                below.
            exact (bool): if unset (default) - prefers to match to beginning of
                string rather than not matching at all. If set, requires
                exact matching of entire string.
            candidates (list of objects): this is an optional custom list of objects
                to search (filter) between. It is ignored if `global_search`
                is given. If not set, this list will automatically be defined
                to include the location, the contents of location and the
                caller's contents (inventory).
            nofound_string (str):  optional custom string for not-found error message.
            multimatch_string (str): optional custom string for multimatch error header.
            use_dbref (bool or None): If None, only turn off use_dbref if we are of a lower
                permission than Builder. Otherwise, honor the True/False value.

        Returns:
            match (Object, None or list): will return an Object/None if `quiet=False`,
                otherwise it will return a list of 0, 1 or more matches.

        Notes:
            To find Accounts, use eg. `evennia.account_search`. If
            `quiet=False`, error messages will be handled by
            `settings.SEARCH_AT_RESULT` and echoed automatically (on
            error, return will be `None`). If `quiet=True`, the error
            messaging is assumed to be handled by the caller.

        """
        is_string = isinstance(searchdata, str)

        if is_string:
            # searchdata is a string; wrap some common self-references
            if searchdata.lower() in ("here",):
                return [self.location] if quiet else self.location
            if searchdata.lower() in ("me", "self"):
                return [self] if quiet else self

        if use_nicks:
            # do nick-replacement on search
            searchdata = self.nicks.nickreplace(
                searchdata, categories=("object", "account"), include_account=True
            )

        if global_search or (
            is_string
            and searchdata.startswith("#")
            and len(searchdata) > 1
            and searchdata[1:].isdigit()
        ):
            # only allow exact matching if searching the entire database
            # or unique #dbrefs
            exact = True
        elif candidates is None:
            # no custom candidates given - get them automatically
            if location:
                # location(s) were given
                candidates = []
                for obj in make_iter(location):
                    candidates.extend(obj.contents)
            else:
                # local search. Candidates are taken from
                # self.contents, self.location and
                # self.location.contents
                location = self.location
                candidates = self.contents
                if location:
                    candidates = candidates + [location] + location.contents
                else:
                    # normally we don't need this since we are
                    # included in location.contents
                    candidates.append(self)

        # the sdesc-related substitution
        is_builder = self.locks.check_lockstring(self, "perm(Builder)")
        use_dbref = is_builder if use_dbref is None else use_dbref

        def search_obj(string):
            "helper wrapper for searching"
            return ObjectDB.objects.object_search(
                string,
                attribute_name=attribute_name,
                typeclass=typeclass,
                candidates=candidates,
                exact=exact,
                use_dbref=use_dbref,
            )

        if candidates:
            candidates = parse_sdescs_and_recogs(
                self, candidates, _PREFIX + searchdata, search_mode=True
            )
            results = []
            for candidate in candidates:
                # we search by candidate keys here; this allows full error
                # management and use of all kwargs - we will use searchdata
                # in eventual error reporting later (not their keys). Doing
                # it like this e.g. allows for use of the typeclass kwarg
                # limiter.
                results.extend([obj for obj in search_obj(candidate.key) if obj not in results])

            if not results and is_builder:
                # builders get a chance to search only by key+alias
                results = search_obj(searchdata)
        else:
            # global searches / #drefs end up here. Global searches are
            # only done in code, so is controlled, #dbrefs are turned off
            # for non-Builders.
            results = search_obj(searchdata)

        if quiet:
            return results
        return _AT_SEARCH_RESULT(
            results,
            self,
            query=searchdata,
            nofound_string=nofound_string,
            multimatch_string=multimatch_string,
        )

    def get_posed_sdesc(self, sdesc, **kwargs):
        """
        Displays the object with its current pose string.

        Returns:
            pose (str): A string containing the object's sdesc and
                current or default pose.
        """

        # get the current pose, or default if no pose is set
        pose = self.db.pose or self.db.pose_default

        # return formatted string, or sdesc as fallback
        return f"{sdesc} {pose}" if pose else sdesc

    def get_display_name(self, looker, **kwargs):
        """
        Displays the name of the object in a viewer-aware manner.

        Args:
            looker (TypedObject): The object or account that is looking
                at/getting inforamtion for this object.

        Keyword Args:
            pose (bool): Include the pose (if available) in the return.
            ref (str): The reference marker found in string to replace.
                This is on the form #{num}{case}, like '#12^', where
                the number is a processing location in the string and the
                case symbol indicates the case of the original tag input
                - `t` - input was Titled, like /Tall
                - `^` - input was all uppercase, like /TALL
                - `v` - input was all lowercase, like /tall
                - `~` - input case should be kept, or was mixed-case
            noid (bool): Don't show DBREF even if viewer has control access.

        Returns:
            name (str): A string of the sdesc containing the name of the object,
                if this is defined. By default, included the DBREF if this user
                is privileged to control said object.

        """
        ref = kwargs.get("ref", "~")

        if looker == self:
            # always show your own key
            sdesc = self.key
        else:
            try:
                # get the sdesc looker should see
                sdesc = looker.get_sdesc(self, ref=ref)
            except AttributeError:
                # use own sdesc as a fallback
                sdesc = self.sdesc.get()

        # add dbref is looker has control access and `noid` is not set
        if self.access(looker, access_type="control") and not kwargs.get("noid", False):
            sdesc = f"{sdesc}(#{self.id})"

        return self.get_posed_sdesc(sdesc) if kwargs.get("pose", False) else sdesc

    def get_display_characters(self, looker, pose=True, **kwargs):
        """
        Get the ‘characters’ component of the object description. Called by return_appearance.
        """

        def _filter_visible(obj_list):
            return (obj for obj in obj_list if obj != looker and obj.access(looker, "view"))

        characters = _filter_visible(self.contents_get(content_type="character"))
        character_names = "\n".join(
            char.get_display_name(looker, pose=pose, **kwargs) for char in characters
        )

        return f"\n{character_names}" if character_names else ""

    def get_display_things(self, looker, pose=True, **kwargs):
        """
        Get the 'things' component of the object description. Called by `return_appearance`.

        Args:
            looker (Object): Object doing the looking.
            **kwargs: Arbitrary data for use when overriding.
        Returns:
            str: The things display data.

        """
        if not pose:
            # if poses aren't included, we can use the core version instead
            return super().get_display_things(looker, **kwargs)

        def _filter_visible(obj_list):
            return [obj for obj in obj_list if obj != looker and obj.access(looker, "view")]

        # sort and handle same-named things
        things = _filter_visible(self.contents_get(content_type="object"))

        posed_things = defaultdict(list)
        for thing in things:
            pose = thing.db.pose or thing.db.pose_default
            if not pose:
                pose = ""
            posed_things[pose].append(thing)

        display_strings = []

        for pose, thinglist in posed_things.items():
            grouped_things = defaultdict(list)
            for thing in thinglist:
                grouped_things[thing.get_display_name(looker, pose=False, **kwargs)].append(thing)

            thing_names = []
            for thingname, samethings in sorted(grouped_things.items()):
                nthings = len(samethings)
                thing = samethings[0]
                singular, plural = thing.get_numbered_name(nthings, looker, key=thingname)
                thing_names.append(singular if nthings == 1 else plural)
            thing_names = iter_to_str(thing_names)

            if pose:
                pose = _INFLECT.plural(pose) if nthings != 1 else pose
            grouped_names = f"{thing_names} {pose}"
            grouped_names = grouped_names[0].upper() + grouped_names[1:]
            display_strings.append(grouped_names)

        if not display_strings:
            return ""

        return "\n" + "\n".join(display_strings)


class ContribRPRoom(ContribRPObject):
    """
    Dummy inheritance for rooms.
    """

    pass


class ContribRPCharacter(DefaultCharacter, ContribRPObject):
    """
    This is a character class that has poses, sdesc and recog.
    """

    @lazy_property
    def recog(self):
        return RecogHandler(self)

    def get_display_name(self, looker, **kwargs):
        """
        Displays the name of the object in a viewer-aware manner.

        Args:
            looker (TypedObject): The object or account that is looking
                at/getting inforamtion for this object.

        Keyword Args:
            pose (bool): Include the pose (if available) in the return.
            ref (str): The reference marker found in string to replace.
                This is on the form #{num}{case}, like '#12^', where
                the number is a processing location in the string and the
                case symbol indicates the case of the original tag input
                - `t` - input was Titled, like /Tall
                - `^` - input was all uppercase, like /TALL
                - `v` - input was all lowercase, like /tall
                - `~` - input case should be kept, or was mixed-case
            noid (bool): Don't show DBREF even if viewer has control access.

        Returns:
            name (str): A string of the sdesc containing the name of the object,
                if this is defined. By default, included the DBREF if this user
                is privileged to control said object.

        Notes:
            The RPCharacter version adds additional processing to sdescs to make
            characters stand out from other objects.

        """
        ref = kwargs.get("ref", "~")

        if looker == self:
            # process your key as recog since you recognize yourself
            sdesc = self.process_recog(self.key, self)
        else:
            try:
                # get the sdesc looker should see, with formatting
                sdesc = looker.get_sdesc(self, process=True, ref=ref)
            except AttributeError:
                # use own sdesc as a fallback
                sdesc = self.sdesc.get()

        # add dbref is looker has control access and `noid` is not set
        if self.access(looker, access_type="control") and not kwargs.get("noid", False):
            sdesc = f"{sdesc}(#{self.id})"

        return self.get_posed_sdesc(sdesc) if kwargs.get("pose", False) else sdesc

    def at_object_creation(self):
        """
        Called at initial creation.
        """
        super().at_object_creation()

        self.db._sdesc = ""

        self.db._recog_ref2recog = {}
        self.db._recog_obj2recog = {}

        self.cmdset.add(RPSystemCmdSet, persistent=True)
        # initializing sdesc
        self.sdesc.add("A normal person")

    def at_pre_say(self, message, **kwargs):
        """
        Called before the object says or whispers anything, return modified message.

        Args:
            message (str): The suggested say/whisper text spoken by self.
        Keyword Args:
            whisper (bool): If True, this is a whisper rather than a say.

        """
        if kwargs.get("whisper"):
            return f'/Me whispers "{message}"'
        return f'/Me says, "{message}"'

    def get_sdesc(self, obj, process=False, **kwargs):
        """
        Single method to handle getting recogs with sdesc fallback in an
        aware manner, to allow separate processing of recogs from sdescs.
        Gets the sdesc or recog for obj from the view of self.

        Args:
            obj (Object): the object whose sdesc or recog is being gotten
        Keyword Args:
            process (bool): If True, the sdesc/recog is run through the
                appropriate process method for self - .process_sdesc or
                .process_recog
        """
        # always see own key
        if obj == self:
            recog = self.key
            sdesc = self.key
        else:
            # first check if we have a recog for this object
            recog = self.recog.get(obj)
            # set sdesc to recog, using sdesc as a fallback, or the object's key if no sdesc
            sdesc = recog or (hasattr(obj, "sdesc") and obj.sdesc.get()) or obj.key

        if process:
            # process the sdesc as a recog if a recog was found, else as an sdesc
            sdesc = (self.process_recog if recog else self.process_sdesc)(sdesc, obj, **kwargs)

        return sdesc

    def process_sdesc(self, sdesc, obj, **kwargs):
        """
        Allows to customize how your sdesc is displayed (primarily by
        changing colors).

        Args:
            sdesc (str): The sdesc to display.
            obj (Object): The object to which the adjoining sdesc
                belongs. If this object is equal to yourself, then
                you are viewing yourself (and sdesc is your key).
                This is not used by default.

        Kwargs:
            ref (str): The reference marker found in string to replace.
                This is on the form #{num}{case}, like '#12^', where
                the number is a processing location in the string and the
                case symbol indicates the case of the original tag input
                - `t` - input was Titled, like /Tall
                - `^` - input was all uppercase, like /TALL
                - `v` - input was all lowercase, like /tall
                - `~` - input case should be kept, or was mixed-case

        Returns:
            sdesc (str): The processed sdesc ready
                for display.

        """
        if not sdesc:
            return ""

        ref = kwargs.get("ref", "~")  # ~ to keep sdesc unchanged
        if "t" in ref:
            # we only want to capitalize the first letter if there are many words
            sdesc = sdesc.lower()
            sdesc = sdesc[0].upper() + sdesc[1:] if len(sdesc) > 1 else sdesc.upper()
        elif "^" in ref:
            sdesc = sdesc.upper()
        elif "v" in ref:
            sdesc = sdesc.lower()
        return f"|b{sdesc}|n"

    def process_recog(self, recog, obj, **kwargs):
        """
        Allows to customize how a recog string is displayed.

        Args:
            recog (str): The recog string. It has already been
                translated from the original sdesc at this point.
            obj (Object): The object the recog:ed string belongs to.
                This is not used by default.

        Returns:
            recog (str): The modified recog string.

        """
        if not recog:
            return ""

        return f"|m{recog}|n"

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
            the evennia.contrib.rpg.rplanguage module.

        """
        return "{label}|w{text}|n".format(label=f"|W({language})" if language else "", text=text)
