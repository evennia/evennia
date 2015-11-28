"""
ANSI - Gives colour to text.

Use the codes defined in ANSIPARSER in your text
to apply colour to text according to the ANSI standard.

Examples:
 This is %crRed text%cn and this is normal again.
 This is {rRed text{n and this is normal again.

Mostly you should not need to call parse_ansi() explicitly;
it is run by Evennia just before returning data to/from the
user.

"""
from builtins import object, range

import re
from evennia.utils import utils
from evennia.utils.utils import to_str, to_unicode
from future.utils import with_metaclass

# ANSI definitions

ANSI_BEEP = "\07"
ANSI_ESCAPE = "\033"
ANSI_NORMAL = "\033[0m"

ANSI_UNDERLINE = "\033[4m"
ANSI_HILITE = "\033[1m"
ANSI_UNHILITE = "\033[22m"
ANSI_BLINK = "\033[5m"
ANSI_INVERSE = "\033[7m"
ANSI_INV_HILITE = "\033[1;7m"
ANSI_INV_BLINK = "\033[7;5m"
ANSI_BLINK_HILITE = "\033[1;5m"
ANSI_INV_BLINK_HILITE = "\033[1;5;7m"

# Foreground colors
ANSI_BLACK = "\033[30m"
ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_BLUE = "\033[34m"
ANSI_MAGENTA = "\033[35m"
ANSI_CYAN = "\033[36m"
ANSI_WHITE = "\033[37m"

# Background colors
ANSI_BACK_BLACK = "\033[40m"
ANSI_BACK_RED = "\033[41m"
ANSI_BACK_GREEN = "\033[42m"
ANSI_BACK_YELLOW = "\033[43m"
ANSI_BACK_BLUE = "\033[44m"
ANSI_BACK_MAGENTA = "\033[45m"
ANSI_BACK_CYAN = "\033[46m"
ANSI_BACK_WHITE = "\033[47m"

# Formatting Characters
ANSI_RETURN = "\r\n"
ANSI_TAB = "\t"
ANSI_SPACE = " "

# Escapes
ANSI_ESCAPES = ("{{", "\\\\", "\|\|")

from collections import OrderedDict
_PARSE_CACHE = OrderedDict()
_PARSE_CACHE_SIZE = 10000


class ANSIParser(object):
    """
    A class that parses ANSI markup
    to ANSI command sequences

    We also allow to escape colour codes
    by prepending with a \ for xterm256,
    an extra { for Merc-style codes
    """

    def sub_ansi(self, ansimatch):
        """
        Replacer used by `re.sub` to replace ANSI
        markers with correct ANSI sequences

        Args:
            ansimatch (re.matchobject): The match.

        Returns:
            processed (str): The processed match string.

        """
        return self.ansi_map.get(ansimatch.group(), "")

    def sub_brightbg(self, ansimatch):
        """
        Replacer used by `re.sub` to replace ANSI
        bright background markers with Xterm256 replacement

        Args:
            ansimatch (re.matchobject): The match.

        Returns:
            processed (str): The processed match string.

        """
        return self.ansi_bright_bgs.get(ansimatch.group(), "")

    def sub_xterm256(self, rgbmatch, convert=False):
        """
        This is a replacer method called by `re.sub` with the matched
        tag. It must return the correct ansi sequence.

        It checks `self.do_xterm256` to determine if conversion
        to standard ANSI should be done or not.

        Args:
            rgbmatch (re.matchobject): The match.
            convert (bool, optional): Convert 256-colors to 16.

        Returns:
            processed (str): The processed match string.

        """
        if not rgbmatch:
            return ""

        # get tag, stripping the initial marker
        rgbtag = rgbmatch.group()[1:]

        background = rgbtag[0] == '['
        if background:
            red, green, blue = int(rgbtag[1]), int(rgbtag[2]), int(rgbtag[3])
        else:
            red, green, blue = int(rgbtag[0]), int(rgbtag[1]), int(rgbtag[2])

        if convert:
            colval = 16 + (red * 36) + (green * 6) + blue
            return "\033[%s8;5;%s%s%sm" % (3 + int(background), colval // 100, (colval % 100) // 10, colval%10)
        else:
            # xterm256 not supported, convert the rgb value to ansi instead
            if red == green and red == blue and red < 2:
                if background:
                    return ANSI_BACK_BLACK
                elif red >= 1:
                    return ANSI_HILITE + ANSI_BLACK
                else:
                    return ANSI_NORMAL + ANSI_BLACK
            elif red == green and red == blue:
                if background:
                    return ANSI_BACK_WHITE
                elif red >= 4:
                    return ANSI_HILITE + ANSI_WHITE
                else:
                    return ANSI_NORMAL + ANSI_WHITE
            elif red > green and red > blue:
                if background:
                    return ANSI_BACK_RED
                elif red >= 3:
                    return ANSI_HILITE + ANSI_RED
                else:
                    return ANSI_NORMAL + ANSI_RED
            elif red == green and red > blue:
                if background:
                    return ANSI_BACK_YELLOW
                elif red >= 3:
                    return ANSI_HILITE + ANSI_YELLOW
                else:
                    return ANSI_NORMAL + ANSI_YELLOW
            elif red == blue and red > green:
                if background:
                    return ANSI_BACK_MAGENTA
                elif red >= 3:
                    return ANSI_HILITE + ANSI_MAGENTA
                else:
                    return ANSI_NORMAL + ANSI_MAGENTA
            elif green > blue:
                if background:
                    return ANSI_BACK_GREEN
                elif green >= 3:
                    return ANSI_HILITE + ANSI_GREEN
                else:
                    return ANSI_NORMAL + ANSI_GREEN
            elif green == blue:
                if background:
                    return ANSI_BACK_CYAN
                elif green >= 3:
                    return ANSI_HILITE + ANSI_CYAN
                else:
                    return ANSI_NORMAL + ANSI_CYAN
            else:    # mostly blue
                if background:
                    return ANSI_BACK_BLUE
                elif blue >= 3:
                    return ANSI_HILITE + ANSI_BLUE
                else:
                    return ANSI_NORMAL + ANSI_BLUE

    def strip_raw_codes(self, string):
        """
        Strips raw ANSI codes from a string.

        Args:
            string (str): The string to strip.

        Returns:
            string (str): The processed string.

        """
        return self.ansi_regex.sub("", string)

    def strip_mxp(self, string):
        """
        Strips all MXP codes from a string.

        Args:
            string (str): The string to strip.

        Returns:
            string (str): The processed string.

        """
        return self.mxp_sub.sub(r'\2', string)

    def parse_ansi(self, string, strip_ansi=False, xterm256=False, mxp=False):
        """
        Parses a string, subbing color codes according to the stored
        mapping.

        Args:
            string (str): The string to parse.
            strip_ansi (boolean, optional): Strip all found ansi markup.
            xterm256 (boolean, optional): If actually using xterm256 or if
                these values should be converted to 16-color ANSI.
            mxp (boolean, optional): Parse MXP commands in string.

        Returns:
            string (str): The parsed string.

        """
        if hasattr(string, '_raw_string'):
            if strip_ansi:
                return string.clean()
            else:
                return string.raw()

        if not string:
            return ''

        # check cached parsings
        global _PARSE_CACHE
        cachekey = "%s-%s-%s-%s" % (string, strip_ansi, xterm256, mxp)
        if cachekey in _PARSE_CACHE:
            return _PARSE_CACHE[cachekey]

        # pre-convert bright colors to xterm256 color tags
        string = self.brightbg_sub.sub(self.sub_brightbg, string)

        def do_xterm256(part):
            return self.sub_xterm256(part, xterm256)

        in_string = utils.to_str(string)

        # do string replacement
        parsed_string =  ""
        parts = self.ansi_escapes.split(in_string) + [" "]
        for part, sep in zip(parts[::2], parts[1::2]):
            pstring = self.xterm256_sub.sub(do_xterm256, part)
            pstring = self.ansi_sub.sub(self.sub_ansi, pstring)
            parsed_string += "%s%s" % (pstring, sep[0].strip())

        if not mxp:
            parsed_string = self.strip_mxp(parsed_string)

        if strip_ansi:
            # remove all ansi codes (including those manually
            # inserted in string)
            return self.strip_raw_codes(parsed_string)

        # cache and crop old cache
        _PARSE_CACHE[cachekey] = parsed_string
        if len(_PARSE_CACHE) > _PARSE_CACHE_SIZE:
           _PARSE_CACHE.popitem(last=False)

        return parsed_string

    # Mapping using {r {n etc

    hilite = ANSI_HILITE
    unhilite = ANSI_UNHILITE

    ext_ansi_map = [
        (r'{n', ANSI_NORMAL),          # reset
        (r'{/', ANSI_RETURN),          # line break
        (r'{-', ANSI_TAB),             # tab
        (r'{_', ANSI_SPACE),           # space
        (r'{*', ANSI_INVERSE),        # invert
        (r'{^', ANSI_BLINK),          # blinking text (very annoying and not supported by all clients)
        (r'{u', ANSI_UNDERLINE),       # underline

        (r'{r', hilite + ANSI_RED),
        (r'{g', hilite + ANSI_GREEN),
        (r'{y', hilite + ANSI_YELLOW),
        (r'{b', hilite + ANSI_BLUE),
        (r'{m', hilite + ANSI_MAGENTA),
        (r'{c', hilite + ANSI_CYAN),
        (r'{w', hilite + ANSI_WHITE),  # pure white
        (r'{x', hilite + ANSI_BLACK),  # dark grey

        (r'{R', unhilite + ANSI_RED),
        (r'{G', unhilite + ANSI_GREEN),
        (r'{Y', unhilite + ANSI_YELLOW),
        (r'{B', unhilite + ANSI_BLUE),
        (r'{M', unhilite + ANSI_MAGENTA),
        (r'{C', unhilite + ANSI_CYAN),
        (r'{W', unhilite + ANSI_WHITE),  # light grey
        (r'{X', unhilite + ANSI_BLACK),  # pure black

        # hilight-able colors
        (r'{h', hilite),
        (r'{H', unhilite),

        (r'{!R', ANSI_RED),
        (r'{!G', ANSI_GREEN),
        (r'{!Y', ANSI_YELLOW),
        (r'{!B', ANSI_BLUE),
        (r'{!M', ANSI_MAGENTA),
        (r'{!C', ANSI_CYAN),
        (r'{!W', ANSI_WHITE),  # light grey
        (r'{!X', ANSI_BLACK),  # pure black

        # normal ANSI backgrounds
        (r'{[R', ANSI_BACK_RED),
        (r'{[G', ANSI_BACK_GREEN),
        (r'{[Y', ANSI_BACK_YELLOW),
        (r'{[B', ANSI_BACK_BLUE),
        (r'{[M', ANSI_BACK_MAGENTA),
        (r'{[C', ANSI_BACK_CYAN),
        (r'{[W', ANSI_BACK_WHITE),    # light grey background
        (r'{[X', ANSI_BACK_BLACK),     # pure black background

        ## alternative |-format

        (r'|n', ANSI_NORMAL),          # reset
        (r'|/', ANSI_RETURN),          # line break
        (r'|-', ANSI_TAB),             # tab
        (r'|_', ANSI_SPACE),           # space
        (r'|*', ANSI_INVERSE),        # invert
        (r'|^', ANSI_BLINK),          # blinking text (very annoying and not supported by all clients)
        (r'|u', ANSI_UNDERLINE),       # underline

        (r'|r', hilite + ANSI_RED),
        (r'|g', hilite + ANSI_GREEN),
        (r'|y', hilite + ANSI_YELLOW),
        (r'|b', hilite + ANSI_BLUE),
        (r'|m', hilite + ANSI_MAGENTA),
        (r'|c', hilite + ANSI_CYAN),
        (r'|w', hilite + ANSI_WHITE),  # pure white
        (r'|x', hilite + ANSI_BLACK),  # dark grey

        (r'|R', unhilite + ANSI_RED),
        (r'|G', unhilite + ANSI_GREEN),
        (r'|Y', unhilite + ANSI_YELLOW),
        (r'|B', unhilite + ANSI_BLUE),
        (r'|M', unhilite + ANSI_MAGENTA),
        (r'|C', unhilite + ANSI_CYAN),
        (r'|W', unhilite + ANSI_WHITE),  # light grey
        (r'|X', unhilite + ANSI_BLACK),  # pure black

        # hilight-able colors
        (r'|h', hilite),
        (r'|H', unhilite),

        (r'|!R', ANSI_RED),
        (r'|!G', ANSI_GREEN),
        (r'|!Y', ANSI_YELLOW),
        (r'|!B', ANSI_BLUE),
        (r'|!M', ANSI_MAGENTA),
        (r'|!C', ANSI_CYAN),
        (r'|!W', ANSI_WHITE),  # light grey
        (r'|!X', ANSI_BLACK),  # pure black

        # normal ANSI backgrounds
        (r'|[R', ANSI_BACK_RED),
        (r'|[G', ANSI_BACK_GREEN),
        (r'|[Y', ANSI_BACK_YELLOW),
        (r'|[B', ANSI_BACK_BLUE),
        (r'|[M', ANSI_BACK_MAGENTA),
        (r'|[C', ANSI_BACK_CYAN),
        (r'|[W', ANSI_BACK_WHITE),    # light grey background
        (r'|[X', ANSI_BACK_BLACK)     # pure black background
        ]

    ansi_bright_bgs = [
        # "bright" ANSI backgrounds using xterm256 since ANSI
        # standard does not support it (will
        # fallback to dark ANSI background colors if xterm256
        # is not supported by client)
        (r'{[r', r'{[500'),
        (r'{[g', r'{[050'),
        (r'{[y', r'{[550'),
        (r'{[b', r'{[005'),
        (r'{[m', r'{[505'),
        (r'{[c', r'{[055'),
        (r'{[w', r'{[555'),     # white background
        (r'{[x', r'{[222'),     # dark grey background

        ## |-style variations

        (r'|[r', r'|[500'),
        (r'|[g', r'|[050'),
        (r'|[y', r'|[550'),
        (r'|[b', r'|[005'),
        (r'|[m', r'|[505'),
        (r'|[c', r'|[055'),
        (r'|[w', r'|[555'),     # white background
        (r'|[x', r'|[222')]     # dark grey background

    # xterm256 {123, %c134. These are replaced directly by
    # the sub_xterm256 method

    xterm256_map = [
        (r'\{[0-5]{3}', ""),   # {123 - foreground colour
        (r'\{\[[0-5]{3}', ""),   # {[123 - background colour
        ## -style
        (r'\|[0-5]{3}', ""),  # |123 - foreground colour
        (r'\|\[[0-5]{3}', ""),  # |[123 - background colour

        (r'\{[0-5]{3}', ""),   # {123 - foreground colour
        (r'\{\[[0-5]{3}', ""),   # {[123 - background colour
        ## |-style
        (r'\|[0-5]{3}', ""),  # |123 - foreground colour
        (r'\|\[[0-5]{3}', ""),  # |[123 - background colour
        ]

    mxp_re = r'\{lc(.*?)\{lt(.*?)\{le|' \
           + r'\|lc(.*?)\|lt(.*?)\|le'

    # prepare regex matching
    brightbg_sub = re.compile(r"|".join([re.escape(tup[0]) for tup in ansi_bright_bgs]), re.DOTALL)
    xterm256_sub = re.compile(r"|".join([tup[0] for tup in xterm256_map]), re.DOTALL)
    ansi_sub = re.compile(r"|".join([re.escape(tup[0]) for tup in ext_ansi_map]), re.DOTALL)
    mxp_sub = re.compile(mxp_re, re.DOTALL)

    # used by regex replacer to correctly map ansi sequences
    ansi_map = dict(ext_ansi_map)
    ansi_bright_bgs = dict(ansi_bright_bgs)

    # prepare matching ansi codes overall
    ansi_re = r"\033\[[0-9;]+m"
    ansi_regex = re.compile(ansi_re)

    # escapes - these double-chars will be replaced with a single
    # instance of each
    ansi_escapes = re.compile(r"(%s)" % "|".join(ANSI_ESCAPES), re.DOTALL)

ANSI_PARSER = ANSIParser()


#
# Access function
#

def parse_ansi(string, strip_ansi=False, parser=ANSI_PARSER, xterm256=False, mxp=False):
    """
    Parses a string, subbing color codes as needed.

    Args:
        string (str): The string to parse.
        strip_ansi (bool, optional): Strip all ANSI sequences.
        parser (ansi.AnsiParser, optional): A parser instance to use.
        xterm256 (bool, optional): Support xterm256 or not.
        mxp (bool, optional): Support MXP markup or not.

    Returns:
        string (str): The parsed string.

    """
    return parser.parse_ansi(string, strip_ansi=strip_ansi, xterm256=xterm256, mxp=mxp)


def strip_ansi(string, parser=ANSI_PARSER):
    """
    Strip all ansi from the string. This handles the Evennia-specific
    markup.

    Args:
        parser (ansi.AnsiParser, optional): The parser to use.

    Returns:
        string (str): The stripped string.

    """
    return parser.parse_ansi(string, strip_ansi=True)

def strip_raw_ansi(string, parser=ANSI_PARSER):
    """
    Remove raw ansi codes from string. This assumes pure
    ANSI-bytecodes in the string.

    Args:
        string (str): The string to parse.
        parser (bool, optional): The parser to use.

    Returns:
        string (str): the stripped string.
    """
    return parser.strip_raw_codes(string)


def raw(string):
    """
    Escapes a string into a form which won't be colorized by the ansi
    parser.

    Returns:
        string (str): The raw, escaped string.

    """
    return string.replace('{', '{{')


def group(lst, n):
    for i in range(0, len(lst), n):
        val = lst[i:i+n]
        if len(val) == n:
            yield tuple(val)


def _spacing_preflight(func):
    """
    This wrapper function is used to do some preflight checks on
    functions used for padding ANSIStrings.

    """
    def wrapped(self, width, fillchar=None):
        if fillchar is None:
            fillchar = " "
        if (len(fillchar) != 1) or (not isinstance(fillchar, basestring)):
            raise TypeError("must be char, not %s" % type(fillchar))
        if not isinstance(width, int):
            raise TypeError("integer argument expected, got %s" % type(width))
        difference = width - len(self)
        if difference <= 0:
            return self
        return func(self, width, fillchar, difference)
    return wrapped


def _query_super(func_name):
    """
    Have the string class handle this with the cleaned string instead
    of ANSIString.

    """
    def wrapped(self, *args, **kwargs):
        return getattr(self.clean(), func_name)(*args, **kwargs)
    return wrapped


def _on_raw(func_name):
    """
    Like query_super, but makes the operation run on the raw string.

    """
    def wrapped(self, *args, **kwargs):
        args = list(args)
        try:
            string = args.pop(0)
            if hasattr(string, '_raw_string'):
                args.insert(0, string.raw())
            else:
                args.insert(0, string)
        except IndexError:
            pass
        result = getattr(self._raw_string, func_name)(*args, **kwargs)
        if isinstance(result, basestring):
            return ANSIString(result, decoded=True)
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
        char_counter = 0
        for index in range(0, len(self._raw_string)):
            if index in self._code_indexes:
                to_string.append(self._raw_string[index])
            elif index in self._char_indexes:
                to_string.append(replacement_string[char_counter])
                char_counter += 1
        return ANSIString(
            ''.join(to_string), decoded=True,
            code_indexes=self._code_indexes, char_indexes=self._char_indexes,
            clean_string=replacement_string)
    return wrapped


class ANSIMeta(type):
    """
    Many functions on ANSIString are just light wrappers around the unicode
    base class. We apply them here, as part of the classes construction.

    """
    def __init__(cls, *args, **kwargs):
        for func_name in [
                'count', 'startswith', 'endswith', 'find', 'index', 'isalnum',
                'isalpha', 'isdigit', 'islower', 'isspace', 'istitle', 'isupper',
                'rfind', 'rindex', '__len__']:
            setattr(cls, func_name, _query_super(func_name))
        for func_name in [
                '__mod__', 'expandtabs', 'decode', 'replace', 'format',
                'encode']:
            setattr(cls, func_name, _on_raw(func_name))
        for func_name in [
                'capitalize', 'translate', 'lower', 'upper', 'swapcase']:
            setattr(cls, func_name, _transform(func_name))
        super(ANSIMeta, cls).__init__(*args, **kwargs)


class ANSIString(with_metaclass(ANSIMeta, unicode)):
    """
    String-like object that is aware of ANSI codes.

    This isn't especially efficient, as it doesn't really have an
    understanding of what the codes mean in order to eliminate
    redundant characters. This could be made as an enhancement to ANSI_PARSER.

    If one is going to use ANSIString, one should generally avoid converting
    away from it until one is about to send information on the wire. This is
    because escape sequences in the string may otherwise already be decoded,
    and taken literally the second time around.

    Please refer to the Metaclass, ANSIMeta, which is used to apply wrappers
    for several of the methods that need not be defined directly here.

    """

    def __new__(cls, *args, **kwargs):
        """
        When creating a new ANSIString, you may use a custom parser that has
        the same attributes as the standard one, and you may declare the
        string to be handled as already decoded. It is important not to double
        decode strings, as escapes can only be respected once.

        Internally, ANSIString can also passes itself precached code/character
        indexes and clean strings to avoid doing extra work when combining
        ANSIStrings.

        """
        string = args[0]
        if not isinstance(string, basestring):
            string = to_str(string, force_string=True)
        parser = kwargs.get('parser', ANSI_PARSER)
        decoded = kwargs.get('decoded', False) or hasattr(string, '_raw_string')
        code_indexes = kwargs.pop('code_indexes', None)
        char_indexes = kwargs.pop('char_indexes', None)
        clean_string = kwargs.pop('clean_string', None)
        # All True, or All False, not just one.
        checks = [x is None for x in [code_indexes, char_indexes, clean_string]]
        if not len(set(checks)) == 1:
            raise ValueError("You must specify code_indexes, char_indexes, "
                             "and clean_string together, or not at all.")
        if not all(checks):
            decoded = True
        if not decoded:
            # Completely new ANSI String
            clean_string = to_unicode(parser.parse_ansi(string, strip_ansi=True, mxp=True))
            string = parser.parse_ansi(string, xterm256=True, mxp=True)
        elif clean_string is not None:
            # We have an explicit clean string.
            pass
        elif hasattr(string, '_clean_string'):
            # It's already an ANSIString
            clean_string = string._clean_string
            code_indexes = string._code_indexes
            char_indexes = string._char_indexes
            string = string._raw_string
        else:
            # It's a string that has been pre-ansi decoded.
            clean_string = parser.strip_raw_codes(string)

        if not isinstance(string, unicode):
            string = string.decode('utf-8')

        ansi_string = super(ANSIString, cls).__new__(ANSIString, to_str(clean_string), "utf-8")
        ansi_string._raw_string = string
        ansi_string._clean_string = clean_string
        ansi_string._code_indexes = code_indexes
        ansi_string._char_indexes = char_indexes
        return ansi_string

    def __str__(self):
        return self._raw_string.encode('utf-8')

    def __unicode__(self):
        """
        Unfortunately, this is not called during print() statements
        due to a bug in the Python interpreter. You can always do
        unicode() or str() around the resulting ANSIString and print
        that.

        """
        return self._raw_string

    def __repr__(self):
        """
        Let's make the repr the command that would actually be used to
        construct this object, for convenience and reference.

        """
        return "ANSIString(%s, decoded=True)" % repr(self._raw_string)

    def __init__(self, *_, **kwargs):
        """
        When the ANSIString is first initialized, a few internal variables
        have to be set.

        The first is the parser. It is possible to replace Evennia's standard
        ANSI parser with one of your own syntax if you wish, so long as it
        implements the same interface.

        The second is the _raw_string. It should be noted that the ANSIStrings
        are unicode based. This seemed more reasonable than basing it off of
        the string class, because if someone were to use a unicode character,
        the benefits of knowing the indexes of the ANSI characters would be
        negated by the fact that a character within the string might require
        more than one byte to be represented. The raw string is, then, a
        unicode object rather than a true encoded string. If you need the
        encoded string for sending over the wire, try using the .encode()
        method.

        The third thing to set is the _clean_string. This is a unicode object
        that is devoid of all ANSI Escapes.

        Finally, _code_indexes and _char_indexes are defined. These are lookup
        tables for which characters in the raw string are related to ANSI
        escapes, and which are for the readable text.

        """
        self.parser = kwargs.pop('parser', ANSI_PARSER)
        super(ANSIString, self).__init__()
        if self._code_indexes is None:
            self._code_indexes, self._char_indexes = self._get_indexes()

    @staticmethod
    def _shifter(iterable, offset):
        """
        Takes a list of integers, and produces a new one incrementing all
        by a number.

        """
        return [i + offset for i in iterable]

    @classmethod
    def _adder(cls, first, second):
        """
        Joins two ANSIStrings, preserving calculated info.

        """

        raw_string = first._raw_string + second._raw_string
        clean_string = first._clean_string + second._clean_string
        code_indexes = first._code_indexes[:]
        char_indexes = first._char_indexes[:]
        code_indexes.extend(
            cls._shifter(second._code_indexes, len(first._raw_string)))
        char_indexes.extend(
            cls._shifter(second._char_indexes, len(first._raw_string)))
        return ANSIString(raw_string, code_indexes=code_indexes,
                          char_indexes=char_indexes,
                          clean_string=clean_string)

    def __add__(self, other):
        """
        We have to be careful when adding two strings not to reprocess things
        that don't need to be reprocessed, lest we end up with escapes being
        interpreted literally.

        """
        if not isinstance(other, basestring):
            return NotImplemented
        if not isinstance(other, ANSIString):
            other = ANSIString(other)
        return self._adder(self, other)

    def __radd__(self, other):
        """
        Likewise, if we're on the other end.

        """
        if not isinstance(other, basestring):
            return NotImplemented
        if not isinstance(other, ANSIString):
            other = ANSIString(other)
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
        slice_indexes = self._char_indexes[slc]
        # If it's the end of the string, we need to append final color codes.
        if not slice_indexes:
            return ANSIString('')
        try:
            string = self[slc.start]._raw_string
        except IndexError:
            return ANSIString('')
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
                pass
        if i is not None:
            append_tail = self._get_interleving(self._char_indexes.index(i) + 1)
        else:
            append_tail = ''
        return ANSIString(string + append_tail, decoded=True)

    def __getitem__(self, item):
        """
        Gateway for slices and getting specific indexes in the ANSIString. If
        this is a regexable ANSIString, it will get the data from the raw
        string instead, bypassing ANSIString's intelligent escape skipping,
        for reasons explained in the __new__ method's docstring.

        """
        if isinstance(item, slice):
            # Slices must be handled specially.
            return self._slice(item)
        try:
            self._char_indexes[item]
        except IndexError:
            raise IndexError("ANSIString Index out of range")
        # Get character codes after the index as well.
        if self._char_indexes[-1] == self._char_indexes[item]:
            append_tail = self._get_interleving(item + 1)
        else:
            append_tail = ''
        item = self._char_indexes[item]

        clean = self._raw_string[item]
        result = ''
        # Get the character they're after, and replay all escape sequences
        # previous to it.
        for index in range(0, item + 1):
            if index in self._code_indexes:
                result += self._raw_string[index]
        return ANSIString(result + clean + append_tail, decoded=True)

    def clean(self):
        """
        Return a unicode object without the ANSI escapes.

        """
        return self._clean_string

    def raw(self):
        """
        Return a unicode object with the ANSI escapes.

        """
        return self._raw_string

    def partition(self, sep, reverse=False):
        """
        Similar to split, but always creates a tuple with three items:

        1. The part before the separator
        2. The separator itself.
        3. The part after.

        We use the same techniques we used in split() to make sure each are
        colored.

        """
        if hasattr(sep, '_clean_string'):
            sep = sep.clean()
        if reverse:
            parent_result = self._clean_string.rpartition(sep)
        else:
            parent_result = self._clean_string.partition(sep)
        current_index = 0
        result = tuple()
        for section in parent_result:
            result += (self[current_index:current_index + len(section)],)
            current_index += len(section)
        return result

    def _get_indexes(self):
        """
        Two tables need to be made, one which contains the indexes of all
        readable characters, and one which contains the indexes of all ANSI
        escapes. It's important to remember that ANSI escapes require more
        that one character at a time, though no readable character needs more
        than one character, since the unicode base class abstracts that away
        from us. However, several readable characters can be placed in a row.

        We must use regexes here to figure out where all the escape sequences
        are hiding in the string. Then we use the ranges of their starts and
        ends to create a final, comprehensive list of all indexes which are
        dedicated to code, and all dedicated to text.

        It's possible that only one of these tables is actually needed, the
        other assumed to be what isn't in the first.

        """

        code_indexes = []
        for match in self.parser.ansi_regex.finditer(self._raw_string):
            code_indexes.extend(range(match.start(), match.end()))
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
            return ''
        s = ''
        while True:
            index += 1
            if index in self._char_indexes:
                break
            elif index in self._code_indexes:
                s += self._raw_string[index]
            else:
                break
        return s

    def split(self, by, maxsplit=-1):
        """
        Stolen from PyPy's pure Python string implementation, tweaked for
        ANSIString.

        PyPy is distributed under the MIT licence.
        http://opensource.org/licenses/MIT

        """
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
            maxsplit -= 1   # NB. if it's already < 0, it stays < 0

        res.append(self[start:len(self)])
        return res

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
        for i in range(1, other + 1):
            code_indexes.extend(
                self._shifter(self._code_indexes, i * len(self._raw_string)))
            char_indexes.extend(
                self._shifter(self._char_indexes, i * len(self._raw_string)))
        return ANSIString(
            raw_string, code_indexes=code_indexes, char_indexes=char_indexes,
            clean_string=clean_string)

    def __rmul__(self, other):
        return self.__mul__(other)

    def rsplit(self, by, maxsplit=-1):
        """
        Stolen from PyPy's pure Python string implementation, tweaked for
        ANSIString.

        PyPy is distributed under the MIT licence.
        http://opensource.org/licenses/MIT

        """
        res = []
        end = len(self)
        bylen = len(by)
        if bylen == 0:
            raise ValueError("empty separator")

        while maxsplit != 0:
            next = self._clean_string.rfind(by, 0, end)
            if next < 0:
                break
            # Get character codes after the index as well.
            res.append(self[next+bylen:end])
            end = next
            maxsplit -= 1   # NB. if it's already < 0, it stays < 0

        res.append(self[:end])
        res.reverse()
        return res

    def join(self, iterable):
        """
        Joins together strings in an iterable.

        """
        result = ANSIString('')
        last_item = None
        for item in iterable:
            if last_item is not None:
                result += self._raw_string
            if not isinstance(item, ANSIString):
                item = ANSIString(item)
            result += item
            last_item = item
        return result

    def _filler(self, char, amount):
        """
        Generate a line of characters in a more efficient way than just adding
        ANSIStrings.

        """
        if not isinstance(char, ANSIString):
            line = char * amount
            return ANSIString(
                char * amount, code_indexes=[], char_indexes=list(range(0, len(line))),
                clean_string=char)
        try:
            start = char._code_indexes[0]
        except IndexError:
            start = None
        end = char._char_indexes[0]
        prefix = char._raw_string[start:end]
        postfix = char._raw_string[end + 1:]
        line = char._clean_string * amount
        code_indexes = [i for i in range(0, len(prefix))]
        length = len(prefix) + len(line)
        code_indexes.extend([i for i in range(length, length + len(postfix))])
        char_indexes = self._shifter(range(0, len(line)), len(prefix))
        raw_string = prefix + line + postfix
        return ANSIString(
            raw_string, clean_string=line, char_indexes=char_indexes,
            code_indexes=code_indexes)

    @_spacing_preflight
    def center(self, width, fillchar, difference):
        """
        Center some text with some spaces padding both sides.

        """
        remainder = difference % 2
        difference /= 2
        spacing = self._filler(fillchar, difference)
        result = spacing + self + spacing + self._filler(fillchar, remainder)
        return result

    @_spacing_preflight
    def ljust(self, width, fillchar, difference):
        """
        Left justify some text.

        """
        return self + self._filler(fillchar, difference)

    @_spacing_preflight
    def rjust(self, width, fillchar, difference):
        """
        Right justify some text.

        """
        return self._filler(fillchar, difference) + self
