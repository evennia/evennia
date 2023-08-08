
# ------------------------------------------------------------
#
# EvString - ANSI-aware string class
#
# ------------------------------------------------------------


import functools
from textwrap import TextWrapper
from django.conf import settings
from evennia.server.portal.mxp import mxp_parse
from evennia.utils import logger
from evennia.utils.ansi import ANSI_PARSER
from evennia.utils.text2html import HTML_PARSER
from evennia.utils.utils import display_len, is_iter, to_str

import re

MXP_ENABLED = settings.MXP_ENABLED

_RE_HEX = re.compile(r'(?<!\|)\|#([0-9a-f]{6})', re.I)
_RE_HEX_BG = re.compile(r'(?<!\|)\|\[#([0-9a-f]{6})', re.I)
_RE_XTERM = re.compile(r'(?<!\|)\|([0-5][0-5][0-5]|\=[a-z])')
_RE_XTERM_BG = re.compile(r'(?<!\|)\|\[([0-5][0-5][0-5]|\=[a-z])')
_GREYS = "abcdefghijklmnopqrstuvwxyz"
# "ansi" styles and hex
_RE_STYLES = re.compile(r'(?<!\|)\|\[?([rRgGbBcCyYwWxXmMu\*\>\_n]|#[0-9a-f]{6})|\=[a-z]')

_RE_MXP = re.compile(r"(?<!\|)\|l[uc](.*?)\|lt(.*?)\|le", re.DOTALL)
_RE_LINE = re.compile(r'^(-+|_+)$', re.MULTILINE)

def strip_markup(text, mxp=MXP_ENABLED):
    """
    Removes all Evennia markup codes from the text.
    """
    text = _RE_STYLES.sub('', text)
    if mxp:
        text = _RE_MXP.sub('', text)
    return text


# translate hex tags to XTERM tags
def hex_to_xterm(message):
    """
    Converts all hex tags to xterm-format tags.
    
    Args:
      message (str): the text to parse for tags

    Returns:
      str: the text with converted tags
    """
    def split_hex(text):
      return ( int(text[i:i+2],16) for i in range(0,6,2) )
      
    def grey_int(num):
      return round( max((num-8),0)/10 )

    def hue_int(num):
      return round(max((num-45),0)/40)
    
    
    for match in reversed(list(_RE_HEX.finditer(message))):
      start, end = match.span()
      tag = match.group(1)
      r, g, b = split_hex(tag)

      if r == g and g == b:
        # greyscale
        i = grey_int(r)
        message = message[:start] + "|=" + _GREYS[i] + message[end:]
      
      else:
        xtag = "|{}{}{}".format( hue_int(r), hue_int(g), hue_int(b) )
        message = message[:start] + xtag + message[end:]

    for match in reversed(list(_RE_HEX_BG.finditer(message))):
      start, end = match.span()
      tag = match.group(1)
      r, g, b = split_hex(tag)

      if r == g and g == b:
        # greyscale
        i = grey_int(r)
        message = message[:start] + "|[=" + _GREYS[i] + message[end:]
      
      else:
        xtag = "|[{}{}{}".format( hue_int(r), hue_int(g), hue_int(b) )
        message = message[:start] + xtag + message[end:]

    return message


def _query_super(func_name):
    """
    Have the string class handle this with the cleaned string instead
    of EvString.

    """

    def wrapped(self, *args, **kwargs):
        return getattr(self.clean(), func_name)(*args, **kwargs)

    return wrapped


def _transform(func_name):
    """
    Some string functions, like those manipulating capital letters,
    return a string the same length as the original. This function
    allows us to do the same, replacing all the non-coded characters
    with the resulting string.

    """

    def wrapped(self, *args, **kwargs):
        replacement_string = _query_super(func_name)(self, *args, **kwargs)
        to_string = []
        char_counter = 0
        for index in range(0, len(self._raw_string)):
            if index in self._code_indexes:
                to_string.append(self._raw_string[index])
            elif index in self._char_indexes:
                to_string.append(replacement_string[char_counter])
                char_counter += 1
        return EvString(
            "".join(to_string),
            decoded=True,
            code_indexes=self._code_indexes,
            char_indexes=self._char_indexes,
            clean_string=replacement_string,
        )

    return wrapped


def _on_raw(func_name):
    """
    Like query_super, but makes the operation run on the raw string.

    """

    def wrapped(self, *args, **kwargs):
        args = list(args)
        try:
            string = args.pop(0)
            if hasattr(string, "_raw_string"):
                args.insert(0, string.raw())
            else:
                args.insert(0, string)
        except IndexError:
            # just skip out if there are no more strings
            pass
        result = getattr(self._raw_string, func_name)(*args, **kwargs)
        if isinstance(result, str):
            return EvString(result, decoded=True)
        return result

    return wrapped


class EvStringMeta(type):
    """
    Many functions on EvString are just light wrappers around the string
    base class. We apply them here, as part of the classes construction.

    """

    def __init__(cls, *args, **kwargs):
        for func_name in [
            "count",
            "startswith",
            "endswith",
            "find",
            "index",
            "isalnum",
            "isalpha",
            "isdigit",
            "islower",
            "isspace",
            "istitle",
            "isupper",
            "rfind",
            "rindex",
            "__len__",
        ]:
            setattr(cls, func_name, _query_super(func_name))
        for func_name in ["__mod__", "expandtabs", "decode", "replace", "format", "encode"]:
            setattr(cls, func_name, _on_raw(func_name))
        for func_name in ["capitalize", "translate", "lower", "upper", "swapcase"]:
            setattr(cls, func_name, _transform(func_name))
        super().__init__(*args, **kwargs)


def _spacing_preflight(func):
    """
    This wrapper function is used to do some preflight checks on
    functions used for padding EvStrings.

    """

    @functools.wraps(func)
    def wrapped(self, width=78, fillchar=None):
        if fillchar is None:
            fillchar = " "
        if (len(fillchar) != 1) or (not isinstance(fillchar, str)):
            raise TypeError("must be char, not %s" % type(fillchar))
        if not isinstance(width, int):
            raise TypeError("integer argument expected, got %s" % type(width))
        _difference = width - len(self)
        if _difference <= 0:
            return self
        return func(self, width, fillchar, _difference)

    return wrapped

# 
def _to_evstring(obj):
    """
    convert to ANSIString.

    Args:
        obj (str): Convert incoming text to markup-aware EvStrings.
    """
    if is_iter(obj):
        return [_to_evstring(o) for o in obj]
    else:
        return EvString(obj)

class EvTextWrapper(TextWrapper):
    """
    This is a wrapper work class for handling strings with markup tags
    in it.  It overloads the standard library `TextWrapper` class.

    """

    def _munge_whitespace(self, text):
        """_munge_whitespace(text : string) -> string

        Munge whitespace in text: expand tabs and convert all other
        whitespace characters to spaces.  Eg. " foo\tbar\n\nbaz"
        becomes " foo    bar  baz".
        """
        return text

    # TODO: Ignore expand_tabs/replace_whitespace until ANSIString handles them.
    # - don't remove this code. /Griatch
    #        if self.expand_tabs:
    #            text = text.expandtabs()
    #        if self.replace_whitespace:
    #            if isinstance(text, str):
    #                text = text.translate(self.whitespace_trans)
    #        return text

    def _split(self, text):
        """_split(text : string) -> [string]

        Split the text to wrap into indivisible chunks.  Chunks are
        not quite the same as words; see _wrap_chunks() for full
        details.  As an example, the text
          Look, goof-ball -- use the -b option!
        breaks into the following chunks:
          'Look,', ' ', 'goof-', 'ball', ' ', '--', ' ',
          'use', ' ', 'the', ' ', '-b', ' ', 'option!'
        if break_on_hyphens is True, or in:
          'Look,', ' ', 'goof-ball', ' ', '--', ' ',
          'use', ' ', 'the', ' ', '-b', ' ', option!'
        otherwise.
        """
        # NOTE-PYTHON3: The following code only roughly approximates what this
        #               function used to do. Regex splitting on ANSIStrings is
        #               dropping ANSI codes, so we're using ANSIString.split
        #               for the time being.
        #
        #               A less hackier solution would be appreciated.
        text = EvString(text)


        chunks = [chunk + " " for chunk in chunks if chunk]  # remove empty chunks

        if len(chunks) > 1:
            chunks[-1] = chunks[-1][0:-1]

        return chunks

    def _wrap_chunks(self, chunks):
        """_wrap_chunks(chunks : [string]) -> [string]

        Wrap a sequence of text chunks and return a list of lines of
        length 'self.width' or less.  (If 'break_long_words' is false,
        some lines may be longer than this.)  Chunks correspond roughly
        to words and the whitespace between them: each chunk is
        indivisible (modulo 'break_long_words'), but a line break can
        come between any two chunks.  Chunks should not have internal
        whitespace; ie. a chunk is either all whitespace or a "word".
        Whitespace chunks will be removed from the beginning and end of
        lines, but apart from that whitespace is preserved.
        """
        lines = []
        if self.width <= 0:
            raise ValueError("invalid width %r (must be > 0)" % self.width)

        # Arrange in reverse order so items can be efficiently popped
        # from a stack of chucks.
        chunks.reverse()

        while chunks:

            # Start the list of chunks that will make up the current line.
            # cur_len is just the length of all the chunks in cur_line.
            cur_line = []
            cur_len = 0

            # Figure out which static string will prefix this line.
            if lines:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent

            # Maximum width for this line.
            width = self.width - display_len(indent)

            # First chunk on line is whitespace -- drop it, unless this
            # is the very beginning of the text (ie. no lines started yet).
            if self.drop_whitespace and chunks[-1].strip() == "" and lines:
                del chunks[-1]

            while chunks:
                ln = display_len(chunks[-1])

                # Can at least squeeze this chunk onto the current line.
                if cur_len + ln <= width:
                    cur_line.append(chunks.pop())
                    cur_len += ln

                # Nope, this line is full.
                else:
                    break

            # The current line is full, and the next chunk is too big to
            # fit on *any* line (not just this one).
            if chunks and display_len(chunks[-1]) > width:
                self._handle_long_word(chunks, cur_line, cur_len, width)

            # If the last chunk on this line is all whitespace, drop it.
            if self.drop_whitespace and cur_line and cur_line[-1].strip() == "":
                del cur_line[-1]

            # Convert current line back to a string and store it in list
            # of all lines (return value).
            if cur_line:
                ln = ""
                for w in cur_line:  # ANSI fix
                    ln += w  #
                lines.append(indent + ln)
        return lines


class EvString(str, metaclass=EvStringMeta):
    """
    Unicode-like object that is aware of Evennia format codes.

    This class can be used nearly identically to strings, in that it will
    report string length, handle slices, etc, much like a string object
    would. The methods should be used identically as string methods are.

    There is at least one exception to this (and there may be more, though
    they have not come up yet). When using ''.join() or u''.join() on an
    EvString, color information will get lost. You must use
    EvString('').join() to preserve color information.

    This implementation isn't perfectly clean, as it doesn't really have an
    understanding of what the codes mean in order to eliminate
    redundant characters-- though cleaning up the strings might end up being
    inefficient and slow without some C code when dealing with larger values.
    Such enhancements could be made as an enhancement to ANSI_PARSER
    if needed, however.

    EvString implements protocol-specific parsing methods. *TODO*

    """

    # A compiled Regex for the format mini-language:
    # https://docs.python.org/3/library/string.html#formatspec
    re_format = re.compile(
        r"(?i)(?P<just>(?P<fill>.)?(?P<align>\<|\>|\=|\^))?(?P<sign>\+|\-| )?(?P<alt>\#)?"
        r"(?P<zero>0)?(?P<width>\d+)?(?P<grouping>\_|\,)?(?:\.(?P<precision>\d+))?"
        r"(?P<type>b|c|d|e|E|f|F|g|G|n|o|s|x|X|%)?"
    )

    def __new__(cls, *args, **kwargs):
        """
        (this docstring is largely irrelevant for my target functionality: revisit)
        When creating a new EvString, you may use a custom parser that has
        the same attributes as the standard one, and you may declare the
        string to be handled as already decoded. It is important not to double
        decode strings, as escapes can only be respected once.

        Internally, EvString can also passes itself precached code/character
        indexes and clean strings to avoid doing extra work when combining
        EvStrings.

        """
        string = args[0]
        if not isinstance(string, str):
            string = to_str(string)
        ansi_parser = kwargs.get("ansi", ANSI_PARSER)
        html_parser = kwargs.get("html", HTML_PARSER)
        # decoded = kwargs.get("decoded", False) or hasattr(string, "_raw_string")
        code_indexes = kwargs.pop("code_indexes", None)
        char_indexes = kwargs.pop("char_indexes", None)
        clean_string = kwargs.pop("clean_string", None)
        # All True, or All False, not just one.
        checks = [x is None for x in [code_indexes, char_indexes, clean_string]]
        if not len(set(checks)) == 1:
            raise ValueError(
                "You must specify code_indexes, char_indexes, "
                "and clean_string together, or not at all."
            )
        # if not all(checks):
        #     decoded = True
        # if not decoded:
        #     # Completely new ANSI String
        #     clean_string = parser.parse_ansi(string, strip_ansi=True, mxp=MXP_ENABLED)
        #     string = parser.parse_ansi(string, xterm256=True, mxp=MXP_ENABLED)
        if clean_string is not None:
            # We have an explicit clean string.
            pass
        elif hasattr(string, "_clean_string"):
            # It's already an EvString
            clean_string = string._clean_string
            code_indexes = string._code_indexes
            char_indexes = string._char_indexes
            string = string._raw_string
        else:
            # It's a string that has been pre-ansi decoded.
            clean_string = strip_markup(string)

        ev_string = super().__new__(EvString, to_str(clean_string))
        ev_string._raw_string = string
        ev_string._clean_string = clean_string
        ev_string._code_indexes = code_indexes
        ev_string._char_indexes = char_indexes
        # TODO: support handling arbitrary parsers
        ev_string._ansi_parser = ansi_parser
        ev_string._html_parser = html_parser
        return ev_string

    def __str__(self):
        return self._raw_string

    def __format__(self, format_spec):
        """
        This magic method covers EvString's behavior within a str.format() or f-string.

        Current features supported: fill, align, width.

        Args:
            format_spec (str): The format specification passed by f-string or str.format(). This is
            a string such as "0<30" which would mean "left justify to 30, filling with zeros".
            The full specification can be found at
            https://docs.python.org/3/library/string.html#formatspec

        Returns:
            ansi_str (str): The formatted EvString's .raw() form, for display.

        """
        # This calls the compiled regex stored on EvString's class to analyze the format spec.
        # It returns a dictionary.
        format_data = self.re_format.match(format_spec).groupdict()
        clean = self.clean()
        base_output = EvString(self.raw())
        align = format_data.get("align", "<")
        fill = format_data.get("fill", " ")

        # Need to coerce width into an integer. We can be certain that it's numeric thanks to regex.
        width = format_data.get("width", None)
        if width is None:
            width = len(clean)
        else:
            width = int(width)

        if align == "<":
            base_output = self.ljust(width, fill)
        elif align == ">":
            base_output = self.rjust(width, fill)
        elif align == "^":
            base_output = self.center(width, fill)
        elif align == "=":
            pass

        # Return the raw string with ANSI markup, ready to be displayed.
        return base_output.raw()

    def __repr__(self):
        """
        Let's make the repr the command that would actually be used to
        construct this object, for convenience and reference.

        """
        return "EvString(%s, decoded=True)" % repr(self._raw_string)

    def __init__(self, *_, **kwargs):
        """
        When the EvString is first initialized, a few internal variables
        have to be set.

        The first is the parser. It is possible to replace Evennia's standard
        ANSI parser with one of your own syntax if you wish, so long as it
        implements the same interface.

        The second is the _raw_string. This is the original "dumb" string
        with ansi escapes that EvString represents.

        The third thing to set is the _clean_string. This is a string that is
        devoid of all ANSI Escapes.

        Finally, _code_indexes and _char_indexes are defined. These are lookup
        tables for which characters in the raw string are related to ANSI
        escapes, and which are for the readable text.

        """
        super().__init__()
        if self._code_indexes is None:
            self._code_indexes, self._char_indexes = self._get_indexes()

    @staticmethod
    def _shifter(iterable, offset):
        """
        Takes a list of integers, and produces a new one incrementing all
        by a number.

        """
        if not offset:
            return iterable
        return [i + offset for i in iterable]

    @classmethod
    def _adder(cls, first, second):
        """
        Joins two EvStrings, preserving calculated info.

        """

        raw_string = first._raw_string + second._raw_string
        clean_string = first._clean_string + second._clean_string
        code_indexes = first._code_indexes[:]
        char_indexes = first._char_indexes[:]
        code_indexes.extend(cls._shifter(second._code_indexes, len(first._raw_string)))
        char_indexes.extend(cls._shifter(second._char_indexes, len(first._raw_string)))
        # TODO: which parsers should be used, first or second?
        return EvString(
            raw_string,
            code_indexes=code_indexes,
            char_indexes=char_indexes,
            clean_string=clean_string,
        )

    def __add__(self, other):
        """
        We have to be careful when adding two strings not to reprocess things
        that don't need to be reprocessed, lest we end up with escapes being
        interpreted literally.

        """
        if not isinstance(other, str):
            return NotImplemented
        if not isinstance(other, EvString):
            other = EvString(other)
        return self._adder(self, other)

    def __radd__(self, other):
        """
        Likewise, if we're on the other end.

        """
        if not isinstance(other, str):
            return NotImplemented
        if not isinstance(other, EvString):
            other = EvString(other)
        return self._adder(other, self)

    def __getslice__(self, i, j):
        """
        This function is deprecated, so we just make it call the proper
        function.

        """
        return self.__getitem__(slice(i, j))

    def _slice(self, slc):
        """
        This function takes a slice() object.

        Slices have to be handled specially. Not only are they able to specify
        a start and end with [x:y], but many forget that they can also specify
        an interval with [x:y:z]. As a result, not only do we have to track
        the ANSI Escapes that have played before the start of the slice, we
        must also replay any in these intervals, should they exist.

        Thankfully, slicing the _char_indexes table gives us the actual
        indexes that need slicing in the raw string. We can check between
        those indexes to figure out what escape characters need to be
        replayed.

        """
        char_indexes = self._char_indexes
        slice_indexes = char_indexes[slc]
        # If it's the end of the string, we need to append final color codes.
        if not slice_indexes:
            # if we find no characters it may be because we are just outside
            # of the interval, using an open-ended slice. We must replay all
            # of the escape characters until/after this point.
            if char_indexes:
                if slc.start is None and slc.stop is None:
                    # a [:] slice of only escape characters
                    return EvString(self._raw_string[slc])
                if slc.start is None:
                    # this is a [:x] slice
                    return EvString(self._raw_string[: char_indexes[0]])
                if slc.stop is None:
                    # a [x:] slice
                    return EvString(self._raw_string[char_indexes[-1] + 1 :])
            return EvString("")
        try:
            string = self[slc.start or 0]._raw_string
        except IndexError:
            return EvString("")
        last_mark = slice_indexes[0]
        # Check between the slice intervals for escape sequences.
        i = None
        for i in slice_indexes[1:]:
            for index in range(last_mark, i):
                if index in self._code_indexes:
                    string += self._raw_string[index]
            last_mark = i
            try:
                string += self._raw_string[i]
            except IndexError:
                # raw_string not long enough
                pass
        if i is not None:
            append_tail = self._get_interleving(char_indexes.index(i) + 1)
        else:
            append_tail = ""
        return EvString(string + append_tail, decoded=True)

    def __getitem__(self, item):
        """
        Gateway for slices and getting specific indexes in the EvString. If
        this is a regexable EvString, it will get the data from the raw
        string instead, bypassing EvString's intelligent escape skipping,
        for reasons explained in the __new__ method's docstring.

        """
        if isinstance(item, slice):
            # Slices must be handled specially.
            return self._slice(item)
        try:
            self._char_indexes[item]
        except IndexError:
            raise IndexError("EvString Index out of range")
        # Get character codes after the index as well.
        if self._char_indexes[-1] == self._char_indexes[item]:
            append_tail = self._get_interleving(item + 1)
        else:
            append_tail = ""
        item = self._char_indexes[item]

        clean = self._raw_string[item]
        result = ""
        # Get the character they're after, and replay all escape sequences
        # previous to it.
        for index in range(0, item + 1):
            if index in self._code_indexes:
                result += self._raw_string[index]
        return EvString(result + clean + append_tail, decoded=True)

    def clean(self):
        """
        Return a string object *without* the Evennia markup.

        Returns:
            clean_string (str): A unicode object with no Evennia markup.

        """
        return self._clean_string

    def raw(self):
        """
        Return a string object with the markup codes.

        Returns:
            raw (str): A unicode object *with* Evennia markup.

        """
        return self._raw_string
    
    def ansi(self, xterm256=True, mxp=MXP_ENABLED):
        """
        Returns a string object with Evennia markup converted to ANSI
        """
        if self._ansi_parser:
            text = self._ansi_parser.parse_markup(self._raw_string, xterm256=xterm256, mxp=mxp)
            return mxp_parse(text) if mxp else text
        else:
            # should we raise an error?
            return self._clean_string

    def html(self):
        """
        Returns a string object with Evennia markup converted to ANSI
        """
        if self._html_parser:
            return self._html_parser.parse_markup(self._raw_string)
        else:
            # should we raise an error?
            return self._clean_string

    def partition(self, sep, reverse=False):
        """
        Splits once into three sections (with the separator being the middle section)

        We use the same techniques we used in split() to make sure each are
        colored.

        Args:
            sep (str): The separator to split the string on.
            reverse (boolean): Whether to split the string on the last
                occurrence of the separator rather than the first.

        Returns:
            EvString: The part of the string before the separator
            EvString: The separator itself
            EvString: The part of the string after the separator.

        """
        if hasattr(sep, "_clean_string"):
            sep = sep.clean()
        if reverse:
            parent_result = self._clean_string.rpartition(sep)
        else:
            parent_result = self._clean_string.partition(sep)
        current_index = 0
        result = tuple()
        for section in parent_result:
            result += (self[current_index : current_index + len(section)],)
            current_index += len(section)
        return result

    def _get_indexes(self):
        """
        Two tables need to be made, one which contains the indexes of all
        readable characters, and one which contains the indexes of all ANSI
        escapes. It's important to remember that ANSI escapes require more
        that one character at a time, though no readable character needs more
        than one character, since the string base class abstracts that away
        from us. However, several readable characters can be placed in a row.

        We must use regexes here to figure out where all the escape sequences
        are hiding in the string. Then we use the ranges of their starts and
        ends to create a final, comprehensive list of all indexes which are
        dedicated to code, and all dedicated to text.

        It's possible that only one of these tables is actually needed, the
        other assumed to be what isn't in the first.

        """

        code_indexes = []
        for match in _RE_STYLES.finditer(self._raw_string):
            code_indexes.extend(list(range(match.start(), match.end())))
        if not code_indexes:
            # Plain string, no ANSI codes.
            return code_indexes, list(range(0, len(self._raw_string)))
        # all indexes not occupied by ansi codes are normal characters
        char_indexes = [i for i in range(len(self._raw_string)) if i not in code_indexes]
        return code_indexes, char_indexes

    def _get_interleving(self, index):
        """
        Get the code characters from the given slice end to the next
        character.

        """
        try:
            index = self._char_indexes[index - 1]
        except IndexError:
            return ""
        s = ""
        while True:
            index += 1
            if index in self._char_indexes:
                break
            elif index in self._code_indexes:
                s += self._raw_string[index]
            else:
                break
        return s

    def __mul__(self, other):
        """
        Multiplication method. Implemented for performance reasons.

        """
        if not isinstance(other, int):
            return NotImplemented
        raw_string = self._raw_string * other
        clean_string = self._clean_string * other
        code_indexes = self._code_indexes[:]
        char_indexes = self._char_indexes[:]
        for i in range(other):
            code_indexes.extend(self._shifter(self._code_indexes, i * len(self._raw_string)))
            char_indexes.extend(self._shifter(self._char_indexes, i * len(self._raw_string)))
        return EvString(
            raw_string,
            code_indexes=code_indexes,
            char_indexes=char_indexes,
            clean_string=clean_string,
        )

    def __rmul__(self, other):
        return self.__mul__(other)

    def split(self, by=None, maxsplit=-1):
        """
        Splits a string based on a separator.

        Stolen from PyPy's pure Python string implementation, tweaked for
        EvString.

        PyPy is distributed under the MIT licence.
        http://opensource.org/licenses/MIT

        Args:
            by (str): A string to search for which will be used to split
                the string. For instance, ',' for 'Hello,world' would
                result in ['Hello', 'world']
            maxsplit (int): The maximum number of times to split the string.
                For example, a maxsplit of 2 with a by of ',' on the string
                'Hello,world,test,string' would result in
                ['Hello', 'world', 'test,string']
        Returns:
            result (list of EvStrings): A list of EvStrings derived from
                this string.

        """
        drop_spaces = by is None
        if drop_spaces:
            by = " "

        bylen = len(by)
        if bylen == 0:
            raise ValueError("empty separator")

        res = []
        start = 0
        while maxsplit != 0:
            next = self._clean_string.find(by, start)
            if next < 0:
                break
            # Get character codes after the index as well.
            res.append(self[start:next])
            start = next + bylen
            maxsplit -= 1  # NB. if it's already < 0, it stays < 0

        res.append(self[start : len(self)])
        if drop_spaces:
            return [part for part in res if part != ""]
        return res

    def rsplit(self, by=None, maxsplit=-1):
        """
        Like split, but starts from the end of the string rather than the
        beginning.

        Stolen from PyPy's pure Python string implementation, tweaked for
        EvString.

        PyPy is distributed under the MIT licence.
        http://opensource.org/licenses/MIT

        Args:
            by (str): A string to search for which will be used to split
                the string. For instance, ',' for 'Hello,world' would
                result in ['Hello', 'world']
            maxsplit (int): The maximum number of times to split the string.
                For example, a maxsplit of 2 with a by of ',' on the string
                'Hello,world,test,string' would result in
                ['Hello,world', 'test', 'string']
        Returns:
            result (list of EvStrings): A list of EvStrings derived from
                this string.

        """
        res = []
        end = len(self)
        drop_spaces = by is None
        if drop_spaces:
            by = " "
        bylen = len(by)
        if bylen == 0:
            raise ValueError("empty separator")

        while maxsplit != 0:
            next = self._clean_string.rfind(by, 0, end)
            if next < 0:
                break
            # Get character codes after the index as well.
            res.append(self[next + bylen : end])
            end = next
            maxsplit -= 1  # NB. if it's already < 0, it stays < 0

        res.append(self[:end])
        res.reverse()
        if drop_spaces:
            return [part for part in res if part != ""]
        return res

    def strip(self, chars=None):
        """
        Strip from both ends, taking ANSI markers into account.

        Args:
            chars (str, optional): A string containing individual characters
                to strip off of both ends of the string. By default, any blank
                spaces are trimmed.
        Returns:
            result (EvString): A new EvString with the ends trimmed of the
                relevant characters.

        """
        clean = self._clean_string
        raw = self._raw_string

        # count continuous sequence of chars from left and right
        nlen = len(clean)
        nlstripped = nlen - len(clean.lstrip(chars))
        nrstripped = nlen - len(clean.rstrip(chars))

        # within the stripped regions, only retain parts of the raw
        # string *not* matching the clean string (these are ansi/mxp tags)
        lstripped = ""
        ic, ir1 = 0, 0
        while nlstripped:
            if ic >= nlstripped:
                break
            elif raw[ir1] != clean[ic]:
                lstripped += raw[ir1]
            else:
                ic += 1
            ir1 += 1
        rstripped = ""
        ic, ir2 = nlen - 1, len(raw) - 1
        while nrstripped:
            if nlen - ic > nrstripped:
                break
            elif raw[ir2] != clean[ic]:
                rstripped += raw[ir2]
            else:
                ic -= 1
            ir2 -= 1
        rstripped = rstripped[::-1]
        return EvString(lstripped + raw[ir1 : ir2 + 1] + rstripped)

    def lstrip(self, chars=None):
        """
        Strip from the left, taking ANSI markers into account.

        Args:
            chars (str, optional): A string containing individual characters
                to strip off of the left end of the string. By default, any
                blank spaces are trimmed.
        Returns:
            result (EvString): A new EvString with the left end trimmed of
                the relevant characters.

        """
        clean = self._clean_string
        raw = self._raw_string

        # count continuous sequence of chars from left and right
        nlen = len(clean)
        nlstripped = nlen - len(clean.lstrip(chars))
        # within the stripped regions, only retain parts of the raw
        # string *not* matching the clean string (these are ansi/mxp tags)
        lstripped = ""
        ic, ir1 = 0, 0
        while nlstripped:
            if ic >= nlstripped:
                break
            elif raw[ir1] != clean[ic]:
                lstripped += raw[ir1]
            else:
                ic += 1
            ir1 += 1
        return EvString(lstripped + raw[ir1:])

    def rstrip(self, chars=None):
        """
        Strip from the right, taking ANSI markers into account.

        Args:
            chars (str, optional): A string containing individual characters
                to strip off of the right end of the string. By default, any
                blank spaces are trimmed.
        Returns:
            result (EvString): A new EvString with the right end trimmed of
                the relevant characters.

        """
        clean = self._clean_string
        raw = self._raw_string
        nlen = len(clean)
        nrstripped = nlen - len(clean.rstrip(chars))
        rstripped = ""
        ic, ir2 = nlen - 1, len(raw) - 1
        while nrstripped:
            if nlen - ic > nrstripped:
                break
            elif raw[ir2] != clean[ic]:
                rstripped += raw[ir2]
            else:
                ic -= 1
            ir2 -= 1
        rstripped = rstripped[::-1]
        return EvString(raw[: ir2 + 1] + rstripped)

    def join(self, iterable):
        """
        Joins together strings in an iterable, using this string between each
        one.

        NOTE: This should always be used for joining strings when EvStrings
        are involved. Otherwise color information will be discarded by python,
        due to details in the C implementation of strings.

        Args:
            iterable (list of strings): A list of strings to join together

        Returns:
            EvString: A single string with all of the iterable's
                contents concatenated, with this string between each.

        Examples:
            ::

                >>> EvString(', ').join(['up', 'right', 'left', 'down'])
                EvString('up, right, left, down')

        """
        result = EvString("")
        last_item = None
        for item in iterable:
            if last_item is not None:
                result += self._raw_string
            if not isinstance(item, EvString):
                item = EvString(item)
            result += item
            last_item = item
        return result

    def _filler(self, char, amount):
        """
        Generate a line of characters in a more efficient way than just adding
        EvStrings.

        """
        if not isinstance(char, EvString):
            line = char * amount
            return EvString(
                char * amount,
                code_indexes=[],
                char_indexes=list(range(0, len(line))),
                clean_string=char,
            )
        try:
            start = char._code_indexes[0]
        except IndexError:
            start = None
        end = char._char_indexes[0]
        prefix = char._raw_string[start:end]
        postfix = char._raw_string[end + 1 :]
        line = char._clean_string * amount
        code_indexes = [i for i in range(0, len(prefix))]
        length = len(prefix) + len(line)
        code_indexes.extend([i for i in range(length, length + len(postfix))])
        char_indexes = self._shifter(list(range(0, len(line))), len(prefix))
        raw_string = prefix + line + postfix
        return EvString(
            raw_string, clean_string=line, char_indexes=char_indexes, code_indexes=code_indexes
        )

    # The following methods should not be called with the '_difference' argument explicitly. This is
    # data provided by the wrapper _spacing_preflight.
    @_spacing_preflight
    def center(self, width, fillchar, _difference):
        """
        Center some text with some spaces padding both sides.

        Args:
            width (int): The target width of the output string.
            fillchar (str): A single character string to pad the output string
                with.
        Returns:
            result (EvString): A string padded on both ends with fillchar.

        """
        remainder = _difference % 2
        _difference //= 2
        spacing = self._filler(fillchar, _difference)
        result = spacing + self + spacing + self._filler(fillchar, remainder)
        return result

    @_spacing_preflight
    def ljust(self, width, fillchar, _difference):
        """
        Left justify some text.

        Args:
            width (int): The target width of the output string.
            fillchar (str): A single character string to pad the output string
                with.
        Returns:
            result (EvString): A string padded on the right with fillchar.

        """
        return self + self._filler(fillchar, _difference)

    @_spacing_preflight
    def rjust(self, width, fillchar, _difference):
        """
        Right justify some text.

        Args:
            width (int): The target width of the output string.
            fillchar (str): A single character string to pad the output string
                with.
        Returns:
            result (EvString): A string padded on the left with fillchar.

        """
        return self._filler(fillchar, _difference) + self


class EvStringContainer:
    """
    Abstract base class for formatting classes which contain EvString units,
    or other EvStringContainers.
    """
    sep = "\n"

    @staticmethod
    def _to_evstring(obj, regexable=False):
        "convert anything to EvString"

        if isinstance(obj, EvString):
            return obj
        elif isinstance(obj, str):
            # this should work better now??
            return EvString(obj)
            # # since ansi will be parsed twice (here and in the normal ansi send), we have to
            # # escape ansi twice.
            # obj = ansi_raw(obj)

        if isinstance(obj, dict):
            return dict(
                (key, EvStringContainer._to_evstring(value, regexable=regexable)) for key, value in obj.items()
            )
        # regular _to_evstring (from EvTable)
        elif is_iter(obj):
            return [EvStringContainer._to_evstring(o) for o in obj]
        else:
            return EvString(obj, regexable=regexable)

    def collect_evstring(self):
        """
        Collects all of the data into a list of EvStrings.
        """
        pass

    def ansi(self, **kwargs):
        """
        Return the container's data formatted with ANSI code
        """
        data = EvString(self.sep).join(self.collect_evstring())
        return data.ansi(**kwargs)
    
    def html(self, **kwargs):
        """
        Return the container's data formatted for HTML
        """
        data = EvString(self.sep).join(self.collect_evstring())
        return data.html(**kwargs)
        