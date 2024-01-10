
# ------------------------------------------------------------
#
# EvString - markup-aware string class
#
# ------------------------------------------------------------


import functools
from collections import namedtuple
from itertools import pairwise
from textwrap import TextWrapper
from django.conf import settings
from evennia.server.portal.mxp import mxp_parse
from evennia.utils import logger
# from evennia.utils.ansi import ANSI_PARSER
# from evennia.utils.html import HTML_PARSER
from evennia.utils.utils import class_from_module, display_len, is_iter, to_str

import re

MXP_ENABLED = settings.MXP_ENABLED
_ANSI_RENDERER = class_from_module(settings.ANSI_RENDERER)
_HTML_RENDERER = class_from_module(settings.HTML_RENDERER)

_MARKUP_CHAR = settings.MARKUP_CHAR
# TODO: make this settings-definable?
_STYLE_KEYS = {
    'u': 'underline',
    '*': 'invert',
    '^': 'blink',
#    'i': 'italics,
}

_RE_HEX = re.compile(fr'(?<!\{_MARKUP_CHAR})\{_MARKUP_CHAR}#([0-9a-f]{6})', re.I)
_RE_HEX_BG = re.compile(fr'(?<!\{_MARKUP_CHAR})\{_MARKUP_CHAR}\[#([0-9a-f]{6})', re.I)
_RE_XTERM = re.compile(fr'(?<!\{_MARKUP_CHAR})\{_MARKUP_CHAR}([0-5][0-5][0-5]|\=[a-z])')
_RE_XTERM_BG = re.compile(fr'(?<!\{_MARKUP_CHAR})\{_MARKUP_CHAR}\[([0-5][0-5][0-5]|\=[a-z])')
_GREYS = "abcdefghijklmnopqrstuvwxyz"
_RE_WHITESPACE = re.compile(fr'(?<!\{_MARKUP_CHAR})\{_MARKUP_CHAR}\[?([\/\-\_\>])')
# ALL evennia markup, except for links and escapes
_RE_STYLES = re.compile(fr'\{_MARKUP_CHAR}(\[?[rRgGbBcCyYwWxXmMhHu\*n\/\-\_\>\^\{_MARKUP_CHAR}]|#[0-9a-fA-F]{6}|[0-5]{3}|\=[a-z])')
_RE_MXP = re.compile(fr"(?<!\{_MARKUP_CHAR})\{_MARKUP_CHAR}l([uc])(.*?)\{_MARKUP_CHAR}lt(.*?)\{_MARKUP_CHAR}le", re.DOTALL)
_RE_LINE = re.compile(r'^(-+|_+)$', re.MULTILINE)

LinkData = namedtuple('LinkData', 'text link key')

def strip_markup(text):
    """
    Removes all Evennia markup codes from the text.
    """
    # handle EvStrings too
    if not hasattr(text, 'clean'):
        text = EvString(text)
    return text.clean()

def strip_mxp(text):
    """
    Removes all MXP codes from a string
    """
    if hasattr(text, 'strip_mxp'):
        return text.strip_mxp()
    return _RE_MXP.sub(r'\g<3>', text)

def _query_super(func_name):
    """
    Have the string class handle this with the cleaned string instead
    of EvString.

    """

    def wrapped(self, *args, **kwargs):
        result = getattr(self.clean(), func_name)(*args, **kwargs)
        if isinstance(result, str):
            return EvString(result)
        return result

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
        index = 0
        for chunk in self._code_chunks:
            if isinstance(chunk, EvCode):
                to_string.append(chunk)
                continue
            new_chunk = replacement_string[index:index+len(chunk)]
            to_string.append(new_chunk)
            index += len(chunk)
        return EvString(
            "".join(to_string),
            clean=replacement_string,
            chunks=to_string,
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
            return EvString(result)
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
        for func_name in ["capitalize", "translate", "lower", "upper", "swapcase", "title"]:
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


def _to_evstring(obj):
    """
    convert to EvString.

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
        if self.break_on_hyphens is True:
            chunks = self.wordsep_re.split(text)
        else:
            chunks = self.wordsep_simple_re.split(text)
        newchunks = []
        for ch in chunks:
            if ch:
                newchunks += [c for c in EvString(ch)._code_chunks if c]
        return newchunks

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

    # def _handle_long_word(self, reversed_chunks, cur_line, cur_len, width):
    #     """_handle_long_word(chunks : [string],
    #                          cur_line : [string],
    #                          cur_len : int, width : int)

    #     Handle a chunk of text (most likely a word, not whitespace) that
    #     is too long to fit in any line.
    #     """
    #     # Figure out when indent is larger than the specified width, and make
    #     # sure at least one character is stripped off on every pass
    #     if width < 1:
    #         space_left = 1
    #     else:
    #         space_left = width - cur_len

    #     # If we're allowed to break long words, then do so: put as much
    #     # of the next chunk onto the current line as will fit.
    #     if self.break_long_words:
    #         end = space_left
    #         chunk = reversed_chunks[-1]
    #         if self.break_on_hyphens and display_len(chunk) > space_left:
    #             # break after last hyphen, but only if there are
    #             # non-hyphens before it
    #             hyphen = chunk.rfind('-', 0, space_left)
    #             if hyphen > 0 and any(c != '-' for c in chunk[:hyphen]):
    #                 end = hyphen + 1
    #         cur_line.append(chunk[:end])
    #         reversed_chunks[-1] = chunk[end:]

    #     # Otherwise, we have to preserve the long word intact.  Only add
    #     # it to the current line if there's nothing already there --
    #     # that minimizes how much we violate the width constraint.
    #     elif not cur_line:
    #         cur_line.append(reversed_chunks.pop())

    #     # If we're not allowed to break long words, and there's already
    #     # text on the current line, do nothing.  Next time through the
    #     # main loop of _wrap_chunks(), we'll wind up here again, but
    #     # cur_len will be zero, so the next line will be entirely
    #     # devoted to the long word that we can't handle right now.

class EvCode(str):
    """
    This class is used for wrapping and length calculations on EvStrings, to prevent style codes
    from being counted.
    """

    def __new__(cls, *args, **kwargs):
        """
        When creating a new EvCode string, you can provide a visible length, e.g. for space or tab
        tags. Otherwise, it will be assumed to have an effective length of 0.

        """
        text = args[0]
        if not isinstance(text, str):
            text = to_str(text)
        length = 0
        if len(args) > 1:
            length = int(args[1])

        # Since EvString consumes the style tag marker when splitting out codes, we add it back if necessary.
        if len(text) == 1 or not text.startswith(_MARKUP_CHAR):
            text = _MARKUP_CHAR + text
        
        code_string = super().__new__(EvCode, to_str(text))
        code_string._visible_length = length

        return code_string
    
    def __init__(self, *_, **kwargs):
        super().__init__()
        self._styles = self._classify_markup()
    
    def _classify_markup(self):
        def _classify_color(cstr):
            if cstr.startswith('#'):
                return ("hex", cstr)
            elif cstr.startswith('='):
                return ('xterm', cstr[1:])
            elif cstr[0].isdecimal():
                return ('xterm', cstr)
            else:
                return ('color', cstr)

        if markup := str(self):
            # categorize by styling group
            markup = markup[1:]
            # identify unstyled printable characters
            if self._visible_length:
                return ('str', markup)
            # reset to normal
            elif markup == 'n':
                return ('reset', markup)
            # check for unique-style markup, like underline
            elif markup in _STYLE_KEYS:
                return (_STYLE_KEYS[markup], markup)
            # identify background colors
            elif markup.startswith('['):
                cat, markup = _classify_color(markup[1:])
                return ( f'bg_{cat}', markup )
            # anything left should be a color
            else:
                cat, markup = _classify_color(markup)
                return ( f'fg_{cat}', markup )
    
    def styles(self):
        """
        Returns a dictionary with information about what kind of styling this markup should apply
        """
        k, v = self._styles
        return { k:v }

    def clean(self):
        """Returns a "clean" version of itself for markup-stripping"""
        if not self._visible_length:
            # style markup
            return ''
        elif self.endswith(_MARKUP_CHAR):
            # escaped markup character
            return _MARKUP_CHAR
        else:
            # everything else is whitespace
            # NOTE: should cleaned tabs print differently?
            return ' '

    def __len__(self):
        """Overrides the default length calculation to return the visible display length"""
        return self._visible_length

    def __repr__(self):
        if self._visible_length:
            return f"EvCode('{str(self)}', {self._visible_length})"
        else:
            return f"EvCode('{str(self)}')"

class EvLink(str):
    """
    A string-like object which represents a clickable MXP-style link. It does NOT do any splitting of the
    input string on its own, but rather, it takes the link and the text as two separate arguments.
    
    The type of link can be passed via the 'link_key' kwarg, but is assumed to be an MXP command by default.
    
    """
    def __new__(cls, *args, **kwargs):
        # if it's already an EvLink, we just use its data
        if hasattr(args[0], '_link_string'):
            link = args[0]._link_string
            text = args[0]._ev_string
            key = args[0]._link_key
            raw_string = args[0]._raw_string
        else:
            # the text can contain markup, so we make sure to convert it here
            text = EvString(args[0])
            link = kwargs.get('link_value', '')
            key = kwargs.get('link_key', 'c')
        
            # ignore keys that don't match
            if key not in ('c', 'u'):
                key = 'c'

            # recreate the original markup string, if not provided
            if not (raw_string := kwargs.get('raw')):
                raw_string =  f"|l{key}{link}|lt{text}|le"

        # we initialize on the raw display-string text to match EvString's implementation
        ev_link = super().__new__(EvLink, text.raw())
        ev_link._raw_string = raw_string
        ev_link._link_string = link
        ev_link._link_key = key
        ev_link._ev_string = text

        return ev_link

    def __repr__(self):
        """Returns the code that would actually recreate this object"""
        return f"EvLink('{self._ev_string.__repr__()}', link_value={self._link_string}, link_key={self._link_key}, raw='{self._raw_string}')"

    def __getitem__(self, item):
        """Returns a new EvLink with the visible text's character(s) corresponding to the index or slice"""
        text = self._ev_string[item]
        
        return EvLink(text, link_value=self._link_string, link_key=self._link_key)
    
    def partition(self, sep, reverse=False):
        """
        Splits the link text on the first instance of sep. Returns a tuple of length 3 containing a link
        with the first segment of text, the separator, and an EvString of the tail. If sep is not found,
        returns a tuple of self followed by two empty strings.
        """
        if sep not in self.clean():
            return (self, '', '')
        
        result = self._ev_string.partition(sep)
        return ( EvLink(result[0], link_value=self._link_string, link_key=self._link_key), result[1], result[2] )

    def rpartition(self, sep):
        """
        Splits the link text on the last instance of sep. Returns a tuple of length 3 containing a link
        with the first segment of text, the separator, and an EvString of the tail. If sep is not found,
        returns a tuple of two empty strings followed by self.
        """
        if sep not in self.clean():
            return ('', '', self)
        
        result = self.ev_string.partition(sep, reverse=True)
        return ( EvLink(result[0], link_value=self._link_string, link_key=self._link_key), result[1], result[2] )

    def data(self):
        """Returns the important elements of the link as a namedtuple"""
        return LinkData(self._ev_string, self._link_string, self._link_key)
    
    def raw(self):
        """Returns the original string with Evennia markup"""
        return self._raw_string
    
    def clean(self):
        """Returns just the text component of the link with no markup"""
        return self._ev_string.clean()


class EvString(str, metaclass=EvStringMeta):
    """
    Unicode-like object that is aware of Evennia format codes.

    This class can be used nearly identically to strings, in that it will
    report string length, handle slices, etc, much like a string object
    would. The methods should be used identically as string methods are.

    However, there are a few situations where the EvString will be converted
    back to a raw markup string. When using ''.join() or u''.join() on an
    EvString, or when using a regex method such as re.sub or re.search, Python
    forces the EvString back to a simple string - you will have to convert the
    results of those operations back to EvString.

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
        text = args[0]
        if not isinstance(text, str):
            text = to_str(text)
        
        ansi_render = kwargs.get("ansi", _ANSI_RENDERER)
        html_render = kwargs.get("html", _HTML_RENDERER)
        
        # check if the attributes are being passed in, for internal EvString operations 
        if kwargs.get('chunks'):
            raw_string = text
            code_chunks = tuple(kwargs['chunks'])
            clean_string = kwargs.get('clean')

        elif hasattr(text, "_clean_string"):
            # It's already an EvString
            clean_string = text._clean_string
            code_chunks = text._code_chunks
            raw_string = text._raw_string
        else:
            # we need to convert it
            raw_string = text
            clean_string = None
            code_chunks = None
            

        ev_string = super().__new__(EvString, to_str(raw_string))
        ev_string._raw_string = raw_string
        ev_string._clean_string = clean_string
        ev_string._code_chunks = code_chunks
        # TODO: support handling arbitrary parsers
        ev_string._ansi_render = ansi_render
        ev_string._html_render = html_render
        return ev_string

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
            ev_string (EvString): A new EvString with the formatting applied.

        """
        # This calls the compiled regex stored on EvString's class to analyze the format spec.
        # It returns a dictionary.
        format_data = self.re_format.match(format_spec).groupdict()
        align = format_data.get("align", "<")
        fill = format_data.get("fill", " ")

        width = format_data.get("width")
        if width is None:
            width = len(self)
        # make sure width is an integer
        else:
            width = int(width)

        if align == "<":
            ev_string = self.ljust(width, fill)
        elif align == ">":
            ev_string = self.rjust(width, fill)
        elif align == "^":
            ev_string = self.center(width, fill)
        elif align == "=":
            ev_string = EvString(self)
        else:
            ev_string = EvString(self)

        return ev_string

    def __repr__(self):
        """
        Let's make the repr the command that would actually be used to
        construct this object, for convenience and reference.
        
        NOTE: this does not curently do that; it needs to reference any custom parsers

        """
        return f"EvString('{self._raw_string}')"

    def __init__(self, *_, **kwargs):
        """
        When the EvString is first initialized, we make sure the raw string has been split
        into codes versus visible text.
        
        If this EvString was created from another EvString, the string has already been split,
        so we don't need to duplicate the effort.

        """
        super().__init__()
        if self._code_chunks is None:
            self._code_chunks = self._split_codes()
            self._renderable_chunks = self._collect_codes()

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
        raw_string = first.raw() + second.raw()
        clean_string = first.clean() + second.clean()
        # if either evstring is empty, just combine them
        if not len(first._code_chunks) or not len(second._code_chunks):
            code_chunks = first._code_chunks + second._code_chunks
        # if both EvStrings are joining on plain text strings, we combine the connecting chunks into one
        elif str == type(first._code_chunks[-1]) == type(second._code_chunks[0]):
            glue = first._code_chunks[-1] + second._code_chunks[0]
            code_chunks = first._code_chunks[:-1] + (glue,) + second._code_chunks[1:]
        # otherwise, we simply add the chunks
        else:
            code_chunks = first._code_chunks + second._code_chunks

        return EvString(
            raw_string,
            clean=clean_string,
            chunks=code_chunks,
        )

    def __add__(self, other):
        if not isinstance(other, str):
            return NotImplemented
        if not isinstance(other, EvString):
            other = EvString(other)
        return self._adder(self, other)

    def __radd__(self, other):
        if not isinstance(other, str):
            return NotImplemented
        if not isinstance(other, EvString):
            other = EvString(other)
        return self._adder(other, self)

    def _slice(self, slc):
        """
        This function takes a slice() object.

        In order to handle the "invisible" escape sequences, we increment through the chunks
        while checking their length against the target indices. Leading color markup of individual
        characters is included, while sliced MXP will wrap its output with the preserved link.
        """
        if not self._code_chunks:
            return EvString('')

        clean_str = self.clean()

        # we check the step first, because if it's negative, the default start/end are different
        step = slc.step or 1
        start = slc.start
        stop = slc.stop
        if step > 0:
            if start is None:
                start = 0
            if stop is None:
                stop = len(clean_str)
            chunk_iter = self._code_chunks
            slice_index = 0
            reverse = False
        else:
            if start is None:
                start = len(clean_str)
            if stop is None:
                stop = -1
            chunk_iter = reversed(self._code_chunks)
            slice_index = len(clean_str)-1
            reverse = True

        indices = list(range(start, stop, step))
        # we walk through our chunks to find the indices
        slice_chunks = []
        if not indices:
            # this can happen when getting an "empty" head or tail of a string
            # since we can have invisible codes, we must check for them on the appropriate end and return them
            if slc.start is None:
                # we have a head slice
                for item in chunk_iter:
                    if len(item):
                        break
                    slice_chunks.append(item)
            elif slc.stop is None:
                # we have a tail slice
                for item in reversed(chunk_iter):
                    if len(item):
                        break
                    slice_chunks.insert(0, item)

            return EvString(''.join(slice_chunks), chunks=slice_chunks)

        for i, item in enumerate(chunk_iter):
            if not len(item) and slice_index == indices[0]:
                # all zero-length items get prefixed to sliced items
                slice_chunks.append(item)
                continue

            if len(item) == 1 and slice_index == indices[0]:
                slice_chunks.append(item)
                indices.remove(slice_index)
            else:
                chunk_start = indices[0] - slice_index
                chunk_end = indices[-1] - slice_index
                if reverse:
                    chunk_start *= -1
                    chunk_end *= -1
                # we have to add 1 back on here for the slice stop, to make sure our final index is included
                chunk_slice = item[chunk_start:chunk_end+1:step]
                if len(chunk_slice):
                    # we make sure to include any color codes that prefixed this chunk
                    code_index = i-1
                    code_chunks = []
                    while not len(chunk_iter[code_index]) and code_index >= 0:
                        code_chunks.append(chunk_iter[code_index])
                        code_index -= 1

                    if code_chunks:
                        if not slice_chunks or slice_chunks[-1] != code_chunks[-1]:
                            slice_chunks += code_chunks

                    slice_chunks.append(chunk_slice)
                    # slice off however many indices we used; we know 1 index = 1 character length
                    indices = indices[len(chunk_slice):]
            
            if not indices:
                # we've completed the slicing
                break

            slice_index = slice_index - len(item) if reverse else slice_index + len(item)

        # make sure we add any trailing codes
        i += 1
        code_chunks = []
        while i < len(chunk_iter):
            # if it has a length, it's not a color code
            if len(chunk_iter[i]):
                # we only want to use invisible codes that are at the end of the whole EvString
                # if we break early here because of a visible item, we don't want to use them
                code_chunks = []
                break
            # otherwise, we add it to our tail chunks
            code_chunks.append(chunk_iter[i])
            i += 1
            
        slice_chunks += code_chunks

        return EvString(''.join(slice_chunks), chunks=slice_chunks)
                

    def __getitem__(self, item):
        """
        Gateway for slices and getting specific indexes in the EvString.
        
        When retrieving a single indexed character, it only considers the clean string.

        """
        if isinstance(item, slice):
            # Slices must be handled specially.
            return self._slice(item)
        try:
            return self._clean_string[item]
        except IndexError:
            raise IndexError("EvString Index out of range")


    def clean(self):
        """
        Return a string object *without* the Evennia markup.

        Returns:
            clean_string (str): A unicode object with no Evennia markup.

        """
        if self._clean_string is None:
            clean_string = ''
            for c in self._code_chunks:
                if hasattr(c, 'clean'):
                    clean_string += c.clean()
                else:
                    clean_string += c
            self._clean_string = clean_string

        return self._clean_string

    def raw(self):
        """
        Return a string object with the markup codes.

        Returns:
            raw (str): A unicode object *with* Evennia markup.

        """
        return self._raw_string

    def strip_mxp(self):
        """
        Returns an EvString with all link compontents removed from links
        """
        chunks = []
        for chunk in self._code_chunks:
            if hasattr(chunk, 'data'):
                # it's a link
                chunks += chunk.data().text._code_chunks
            else:
                chunks.append(chunk)
        
        return EvString(''.join(chunks), chunks=chunks)

    def to_ansi(self, xterm256=True, rgb=False, mxp=MXP_ENABLED):
        """
        Returns a string object with Evennia markup converted to ANSI
        """
        if self._ansi_render:
            return self._ansi_render.convert_markup(self._code_chunks, xterm256=xterm256, rgb=rgb, mxp=mxp)
        else:
            # should we raise an error?
            return self._clean_string

    def to_html(self, renderer=None):
        """
        Returns a string object with Evennia markup converted to HTML tags
        """
        if self._html_render:
            return self._html_render.convert_markup(self._renderable_chunks)
        elif renderer:
            try:
                return renderer.convert_markup(self._renderable_chunks)
            except:
                # it was an invalid renderer
                return self._clean_string
        else:
            # should we raise an error?
            return self._clean_string

    def partition(self, sep, reverse=False):
        """
        Splits once into three sections (with the separator being the middle section).
        
        Code segments of the EvString are not checked for the separator, as splitting
        in the middle of one of those elements would break it. Links will use the
        start of the text to a link and convert the tail to a normal EvString.

        Args:
            sep (str): The separator to split the string on.
            reverse (boolean): Whether to split the string on the last
                occurrence of the separator rather than the first.

        Returns:
            EvString: The part of the string before the separator
            EvString: The separator itself
            EvString: The part of the string after the separator.

        """
        result = tuple()
        if reverse:
            for i, chunk in reversed(enumerate(self._code_chunks)):
                # we do not split within codes
                if isinstance(chunk, EvCode):
                    continue
                result = chunk.rpartition(sep)
                if result[0]:
                    break
                else:
                    result = None
        else:
            # do the same thing, but forwards
            for i, chunk in enumerate(self._code_chunks):
                # we do not split within codes
                if isinstance(chunk, EvCode):
                    continue
                result = chunk.partition(sep)
                if result[-1]:
                    break
                else:
                    result = None
        
        # now we check our results
        if not result:
            return ('', '', self) if reverse else (self, '', '')
        
        else:
            # we broke the loop at i, so split the code chunks there
            first = self._code_chunks[:i] + (result[0],)
            last = (result[2],) + self._code_chunks[i+1:]
            # create new EvStrings from our partitioned results and return
            return ( EvString(''.join(first), chunks=first), sep, EvString(''.join(last), chunks=last), )
            
    def rpartition(self, sep):
        return self.partition(sep, reverse=True)

    def _split_codes(self):
        """
        Separates the raw string into chunks of content and Evennia codes.
        
        Evennia 
        """
        # first, we split out any MXP
        chunks = _RE_MXP.split(self._raw_string)
        if remainder := len(chunks) % 4:
            # take off the remainder items, to make sure we can iterate through the links
            i = len(chunks)-remainder
            tail = chunks[i:]
            chunks = chunks[:i]

        # now we can be sure there is a multiple of 4, if there are any
        if chunks:
            link_chunks = [chunks[i:i+4] for i in range(0, len(chunks), 4)]
            chunks = []
            for not_mxp, key, link, text in link_chunks:
                chunks.append(not_mxp)
                # since the display text for a link can contain codes, it needs to be an EvString itself
                # however, it can't contain another clickable length, so it is only ever nested 1 deep
                text = EvString(text)
                ev_link = EvLink(text, link_value=link, link_key=key)
                chunks.append(ev_link)
        # add the tail back in
        chunks.extend(tail)

        # next, iterate through again, but parse the plain str items for codes
        final_chunks = []
        for chunk in chunks:
            # we also want to remove empty items
            if not chunk:
                continue
            # if it's an EvLink, add it as-is and continue
            if isinstance(chunk, EvLink):
                final_chunks.append(chunk)
                continue
            # the style splitter will always have the pattern of text, then code
            for i, text in enumerate(_RE_STYLES.split(chunk)):
                # if it's empty, then it was a single pipe - add it back
                if i % 2:
                    # convert the code into an EvCode
                    # but first, check if it's a whitespace marker
                    if text in '_/|':
                        # these markup count as a length of 1
                        code = EvCode(text, 1)
                    elif text in '>-':
                        code = EvCode(text, settings.TAB_STOP)
                    elif not text:
                        code = EvCode(_MARKUP_CHAR, 1)
                    else:
                        code = EvCode(text)

                    final_chunks.append(code)
                else:
                    # text items are zero and even indices, e.g. mod 2 is falsey
                    # this escapes any single, unescaped markup characters left
                    split_chunk = [EvCode(i, 1) if i == _MARKUP_CHAR else i for i in re.split(f"(\{_MARKUP_CHAR})", text) if i]
                    final_chunks += split_chunk
                    # if text:
                    #     final_chunks.append(text)

        # since this may have added escaped markup characters, we re-generate the raw and clean strings
        self._raw_string = ''.join([str(c) for c in final_chunks])
        # clear these to be regenerated when next needed
        self._clean_string = None
        self._renderable_chunks = None
        return tuple(final_chunks)

    def _collect_codes(self):
        """
        Groups the internal code/string chunks into pairs of styling instructions and output text.
        """
        chunks = self._code_chunks

        output = []
        styling = {}
        str_output = ''
        for chunk in chunks:
            if isinstance(chunk, EvLink):
                output.append(({}, chunk))
            elif isinstance(chunk, EvCode):
                chunk_style = chunk.styles()
                if 'str' in chunk_style:
                    str_output += chunk_style['str']
                else:
                    styling = chunk_style if 'reset' in chunk_style else styling | chunk_style
            else:
                # normal text
                output.append( (tuple(styling.items()), str_output+chunk) )
                str_output = ''
                styling = {}

        return tuple(output)

    def split(self, sep=' ', maxsplit=-1):
        """
        Splits a string based on a separator.

        Args:
            sep (str): A string to search for which will be used to split
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
        if len(sep) == 0:
            raise ValueError("empty separator")

        res = []
        to_split = self
        while maxsplit != 0:
            if not to_split:
                break
            split = to_split.partition(sep)
            res.append(split[0]) 
            to_split = split[2]
            maxsplit -= 1  # NB. if it's already < 0, it stays < 0, thus ensuring all splits

        # make sure the final tail gets added
        if to_split:
            res.append(to_split)

        return res

    def rsplit(self, sep=' ', maxsplit=-1):
        """
        Like split, but starts from the end of the string rather than the
        beginning.

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
        if len(sep) == 0:
            raise ValueError("empty separator")

        res = []
        to_split = self
        while maxsplit != 0:
            if not to_split:
                break
            split = to_split.rpartition(sep)
            res.append(split[2]) 
            to_split = split[0]
            maxsplit -= 1  # NB. if it's already < 0, it stays < 0, thus ensuring all splits

        # make sure the final tail gets added, if there was one
        if to_split:
            res.append(to_split)
        # reverse it to make sure the split elements are in the same order as the base EvString
        res.reverse()
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
        if len(self._code_chunks) == 1:
            if not len(self._code_chunks[0]):
                return EvString(self._raw_string, chunks=self.code_chunks)
            else:
                return EvString(str(self._code_chunks[0]).strip())

        left_chunks = []
        stripped = None
        # iterate through from the start until we find a chunk that's not an EvCode
        for i, item in enumerate(self._code_chunks):
            if not len(item):
                left_chunks.append(item)
                continue
            stripped = item.lstrip(chars) if chars else item.lstrip()
            # check if anything is left after being stripped
            if stripped:
                break
            # if not, ignore this item and keep going

        if stripped is None:
            left_index = 0
            left_chunks = []
        else:
            left_chunks.append(stripped)
            left_index = i+1

        right_chunks = []
        stripped = None
        # iterate through from the end until we find a chunk that's not an EvCode
        reversed_chunks =  reversed(self._code_chunks)
        end = len(self._code_chunks) - left_index
        for i, item in enumerate(reversed_chunks):
            if i >= end:
                break
            if not len(item):
                right_chunks.append(item)
                continue
            stripped = item.rstrip(chars) if chars else item.rstrip()
            # check if anything is left after being stripped
            if stripped:
                break
            # if not, ignore this item and keep going

        if stripped is None:
            right_index = len(self._code_chunks)
            right_chunks = []
        else:
            right_chunks.append(stripped)
            right_chunks.reverse()
            right_index = len(self._code_chunks) - (i+1)

        new_chunks = (*left_chunks, *self._code_chunks[left_index:right_index], *right_chunks,)
        
        return EvString(''.join(new_chunks), chunks=new_chunks)
        

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
        if len(self._code_chunks) == 1:
            if not len(self._code_chunks[0]):
                return EvString(self._raw_string, chunks=self.code_chunks)
            else:
                return EvString(str(self._code_chunks[0]).lstrip())

        left_chunks = []
        stripped = None
        # iterate through until we find a chunk that's not an EvCode
        for i, item in enumerate(self._code_chunks):
            if not len(item):
                left_chunks.append(item)
                continue
            stripped = item.lstrip(chars) if chars else item.lstrip()
            # check if anything is left after being stripped
            if stripped:
                break
            # if not, ignore this item and keep going

        if stripped is None:
            return EvString(self)

        left_chunks.append(stripped)
        new_chunks = (*left_chunks, *self._code_chunks[i+1:],)
        
        return EvString(''.join(new_chunks), chunks=new_chunks)


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
        if len(self._code_chunks) == 1:
            if not len(self._code_chunks[0]):
                return EvString(self._raw_string, chunks=self.code_chunks)
            else:
                return EvString(str(self._code_chunks[0]).rstrip())

        right_chunks = []
        stripped = None
        # iterate through from the end until we find a chunk that's not an EvCode
        reversed_chunks =  reversed(self._code_chunks)
        for i, item in enumerate(reversed_chunks):
            if not len(item):
                right_chunks.append(item)
                continue
            stripped = item.rstrip(chars) if chars else item.rstrip()
            # check if anything is left after being stripped
            if stripped:
                break
            # if not, ignore this item and keep going
        
        if not stripped:
            return EvString(self)

        right_chunks.append(stripped)
        right_chunks.reverse()
        right_index = len(self._code_chunks) - i

        new_chunks = (*self._code_chunks[:right_index-1], *right_chunks,)
        
        return EvString(''.join(new_chunks), chunks=new_chunks)


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
                line,
                chunks=(line,),
                clean=line,
            )

        # at this point we assume it is an evstring
        chunks = char._code_chunks * amount
        clean = char._clean_string * amount
        raw = char._raw_string * amount
        return EvString(
            raw, clean=clean, chunks=chunks
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
    # TODO: actually make this an abstract
    sep = "\n"

    @staticmethod
    def _to_evstring(obj, **kwargs):
        "convert all string contents in anything to EvString"

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
                (key, EvStringContainer._to_evstring(value)) for key, value in obj.items()
            )
        # regular _to_evstring (from EvTable)
        elif is_iter(obj):
            return [EvStringContainer._to_evstring(o) for o in obj]
        else:
            return EvString(str(obj))

    def __str__(self):
        """
        Converts the container into a string.
        """
        return self.raw()

    def collect_evstring(self):
        """
        Collects all of the data into a list of EvStrings.
        """
        pass

    def clean(self):
        """
        Return the container's data with all markup stripped.
        """
        # support for using EvString separators
        sep = self.sep
        if hasattr(sep, 'clean'):
            sep = sep.clean()
        return str(sep).join([item.clean() for item in self.collect_evstring() if item])

    def raw(self):
        """
        Return the container's data with the original markup.
        """
        sep = self.sep
        if hasattr(sep, 'raw'):
            sep = sep.raw()
        return str(sep).join([item.raw() for item in self.collect_evstring() if item])

    def to_ansi(self, **kwargs):
        """
        Return the container's data formatted with ANSI code
        """
        sep = self.sep
        if not hasattr(sep, 'ansi'):
            sep = EvString(self.sep)
        return sep.to_ansi(**kwargs).join([item.to_ansi(**kwargs) for item in self.collect_evstring() if item])
    
    def to_html(self, **kwargs):
        """
        Return the container's data formatted for HTML
        """
        sep = self.sep
        if not hasattr(sep, 'html'):
            sep = EvString(self.sep)
        return sep.html(**kwargs).join([item.html(**kwargs) for item in self.collect_evstring() if item])



def escape_markup(text):
    """
    Escapes any Evennia markup in a string to prevent it from being converted to codes.

    Returns:
        string (str): The raw, escaped string.

    """
    if hasattr(text, 'raw'):
        text = text.raw()
    text = text or ""
    return text.replace(_MARKUP_CHAR, _MARKUP_CHAR*2)