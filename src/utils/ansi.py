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
import re
from src.utils import utils

# ANSI definitions

ANSI_BEEP = "\07"
ANSI_ESCAPE = "\033"
ANSI_NORMAL = "\033[0m"

ANSI_UNDERLINE = "\033[4m"
ANSI_HILITE = "\033[1m"
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
ANSI_ESCAPES = ("{{", "%%", "\\\\")


def sub_meth(obj, function):
    """
    RegexObject.sub() allows for the 'repl' argument to be a function.
    However, it doesn't call bound methods correctly. This forces 'self'
    to be passed.
    """
    if isinstance(function, basestring):
        return function
    def wrapped(*args, **kwargs):
        return function(obj, *args, **kwargs)
    return wrapped


class ANSIParser(object):
    """
    A class that parses ansi markup
    to ANSI command sequences

    We also allow to escape colour codes
    by prepending with a \ for mux-style and xterm256,
    an extra { for Merc-style codes
    """

    def parse_rgb(self, rgbmatch):
        """
        This is a replacer method called by re.sub with the matched
        tag. It must return the correct ansi sequence.

        It checks self.do_xterm256 to determine if conversion
        to standard ansi should be done or not.
        """
        if not rgbmatch:
            return ""
        rgbtag = rgbmatch.groups()[0]

        background = rgbtag[0] == '['
        if background:
            red, green, blue = int(rgbtag[1]), int(rgbtag[2]), int(rgbtag[3])
        else:
            red, green, blue = int(rgbtag[0]), int(rgbtag[1]), int(rgbtag[2])

        if self.do_xterm256:
            colval = 16 + (red * 36) + (green * 6) + blue
            #print "RGB colours:", red, green, blue
            return "\033[%s8;5;%s%s%sm" % (3 + int(background), colval/100, (colval % 100)/10, colval%10)
        else:
            #print "ANSI convert:", red, green, blue
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

    def parse_ansi(self, string, strip_ansi=False, xterm256=False):
        """
        Parses a string, subbing color codes according to
        the stored mapping.

        strip_ansi flag instead removes all ansi markup.

        """
        if hasattr(string, 'raw_string'):
            if strip_ansi:
                return string.clean_string
            else:
                return string.raw_string
        if not string:
            return ''
        self.do_xterm256 = xterm256
        string = utils.to_str(string)

        # go through all available mappings and translate them
        parts = self.ansi_escapes.split(string) + [" "]
        string = ""
        for part, sep in zip(parts[::2], parts[1::2]):
            for sub in self.ansi_sub:
                part = sub[0].sub(sub_meth(self, sub[1]), part)
            string += "%s%s" % (part, sep[0].strip())
        if strip_ansi:
            # remove all ansi codes (including those manually
            # inserted in string)
            string = self.ansi_regex.sub("", string)
        return string

    # MUX-style mappings %cr %cn etc

    mux_ansi_map = [
        # commented out by default; they (especially blink) are
        # potentially annoying
        (r'%cn', ANSI_NORMAL),
        (r'%ch', ANSI_HILITE),
        (r'%r', ANSI_RETURN),
        (r'%t', ANSI_TAB),
        (r'%b', ANSI_SPACE),
        #(r'%cf', ANSI_BLINK),
        #(r'%ci', ANSI_INVERSE),
        (r'%cr', ANSI_RED),
        (r'%cR', ANSI_BACK_RED),
        (r'%cg', ANSI_GREEN),
        (r'%cG', ANSI_BACK_GREEN),
        (r'%cy', ANSI_YELLOW),
        (r'%cY', ANSI_BACK_YELLOW),
        (r'%cb', ANSI_BLUE),
        (r'%cB', ANSI_BACK_BLUE),
        (r'%cm', ANSI_MAGENTA),
        (r'%cM', ANSI_BACK_MAGENTA),
        (r'%cc', ANSI_CYAN),
        (r'%cC', ANSI_BACK_CYAN),
        (r'%cw', ANSI_WHITE),
        (r'%cW', ANSI_BACK_WHITE),
        (r'%cx', ANSI_BLACK),
        (r'%cX', ANSI_BACK_BLACK)
        ]

    # Expanded mapping {r {n etc

    hilite = ANSI_HILITE
    normal = ANSI_NORMAL

    ext_ansi_map = [
        (r'{n', normal),                # reset
        (r'{/', ANSI_RETURN),          # line break
        (r'{-', ANSI_TAB),             # tab
        (r'{_', ANSI_SPACE),           # space
        (r'{\*', ANSI_INVERSE),        # invert
        (r'{\^', ANSI_BLINK),          # blinking text (very annoying and not supported by all clients)

        (r'{r', hilite + ANSI_RED),
        (r'{g', hilite + ANSI_GREEN),
        (r'{y', hilite + ANSI_YELLOW),
        (r'{b', hilite + ANSI_BLUE),
        (r'{m', hilite + ANSI_MAGENTA),
        (r'{c', hilite + ANSI_CYAN),
        (r'{w', hilite + ANSI_WHITE),  # pure white
        (r'{x', hilite + ANSI_BLACK),  # dark grey

        (r'{R', normal + ANSI_RED),
        (r'{G', normal + ANSI_GREEN),
        (r'{Y', normal + ANSI_YELLOW),
        (r'{B', normal + ANSI_BLUE),
        (r'{M', normal + ANSI_MAGENTA),
        (r'{C', normal + ANSI_CYAN),
        (r'{W', normal + ANSI_WHITE),  # light grey
        (r'{X', normal + ANSI_BLACK),  # pure black

        (r'{\[r', ANSI_BACK_RED),
        (r'{\[g', ANSI_BACK_GREEN),
        (r'{\[y', ANSI_BACK_YELLOW),
        (r'{\[b', ANSI_BACK_BLUE),
        (r'{\[m', ANSI_BACK_MAGENTA),
        (r'{\[c', ANSI_BACK_CYAN),
        (r'{\[w', ANSI_BACK_WHITE),    # light grey background
        (r'{\[x', ANSI_BACK_BLACK)     # pure black background
        ]

    # xterm256 {123, %c134,

    xterm256_map = [
        (r'%([0-5]{3})', parse_rgb),  # %123 - foreground colour
        (r'%(\[[0-5]{3})', parse_rgb),  # %-123 - background colour
        (r'{([0-5]{3})', parse_rgb),   # {123 - foreground colour
        (r'{(\[[0-5]{3})', parse_rgb)   # {-123 - background colour
        ]

    # obs - order matters here, we want to do the xterms first since
    # they collide with some of the other mappings otherwise.
    ansi_map = xterm256_map + mux_ansi_map + ext_ansi_map

    # prepare regex matching
    ansi_sub = [(re.compile(sub[0], re.DOTALL), sub[1])
                     for sub in ansi_map]

    # prepare matching ansi codes overall
    ansi_regex = re.compile("\033\[[0-9;]+m")

    # escapes - these double-chars will be replaced with a single
    # instance of each
    ansi_escapes = re.compile(r"(%s)" % "|".join(ANSI_ESCAPES), re.DOTALL)

ANSI_PARSER = ANSIParser()


#
# Access function
#

def parse_ansi(string, strip_ansi=False, parser=ANSI_PARSER, xterm256=False):
    """
    Parses a string, subbing color codes as needed.

    """
    return parser.parse_ansi(string, strip_ansi=strip_ansi, xterm256=xterm256)


def raw(string):
    """
    Escapes a string into a form which won't be colorized by the ansi parser.
    """
    return string.replace('{', '{{').replace('%', '%%')


def group(lst, n):
    for i in range(0, len(lst), n):
        val = lst[i:i+n]
        if len(val) == n:
            yield tuple(val)


def _spacing_preflight(func):
    def wrapped(self, width, fillchar=None):
        if fillchar is None:
            fillchar = " "
        if (len(fillchar) != 1) or (not isinstance(fillchar, str)):
            raise TypeError("must be char, not %s" % type(fillchar))
        if not isinstance(width, int):
            raise TypeError("integer argument expected, got %s" % type(width))
        difference = width - len(self)
        if difference <= 0:
            return self
        return func(self, width, fillchar, difference)
    return wrapped


class ANSIString(unicode):
    """
    String-like object that is aware of ANSI codes.

    This isn't especially efficient, as it doesn't really have an
    understanding of what the codes mean in order to eliminate
    redundant characters, but a proper parser would have to be written for
    that.

    Take note of the instructions at the bottom of the module, which modify
    this class.
    """

    def __new__(cls, *args, **kwargs):
        """
        When creating a new ANSIString, you may use a custom parser that has
        the same attributes as the standard one, and you may declare the
        string to be handled as already decoded. It is important not to double
        decode strings, as escapes can only be respected once.
        """
        string = args[0]
        if not isinstance(string, basestring):
            string = str(string)
        args = args[1:]
        parser = kwargs.get('parser', ANSI_PARSER)
        decoded = kwargs.get('decoded', False) or hasattr(string, 'raw_string')
        if not decoded:
            string = parser.parse_ansi(string)
        return super(ANSIString, cls).__new__(ANSIString, string, *args)

    def __repr__(self):
        return "ANSIString(%s, decoded=True)" % repr(self.raw_string)

    def __init__(self, *args, **kwargs):
        self.parser = kwargs.pop('parser', ANSI_PARSER)
        super(ANSIString, self).__init__(*args, **kwargs)
        self.raw_string = unicode(self)
        self.clean_string = unicode(self.parser.parse_ansi(
            self.raw_string, strip_ansi=True))
        self._code_indexes, self._char_indexes = self._get_indexes()

    def __len__(self):
        return len(self.clean_string)

    def __add__(self, other):
        if not isinstance(other, basestring):
            return NotImplemented
        return ANSIString(self.raw_string + getattr(
            other, 'raw_string', other), decoded=True)

    def __radd__(self, other):
        if not isinstance(other, basestring):
            return NotImplemented
        return ANSIString(getattr(
            other, 'raw_string', other) + self.raw_string, decoded=True)

    def __getslice__(self, i, j):
        return self.__getitem__(slice(i, j))

    def _slice(self, item):
        slice_indexes = self._char_indexes[item]
        if not slice_indexes:
            return ANSIString('')
        try:
            string = self[item.start].raw_string
        except IndexError:
            return ANSIString('')
        last_mark = slice_indexes[0]
        for i in slice_indexes[1:]:
            for index in range(last_mark, i):
                if index in self._code_indexes:
                    string += self.raw_string[index]
            last_mark = i
            try:
                string += self.raw_string[i]
            except IndexError:
                pass
        return ANSIString(string, decoded=True)

    def __getitem__(self, item):
        if isinstance(item, slice):
            return self._slice(item)
        try:
            item = self._char_indexes[item]
        except IndexError:
            raise IndexError("ANSIString index out of range.")
        clean = self.raw_string[item]

        result = ''
        for index in range(0, item + 1):
            if index in self._code_indexes:
                result += self.raw_string[index]
        return ANSIString(result + clean, decoded=True)

    def rsplit(self, sep=None, maxsplit=None):
        return self.split(sep, maxsplit, reverse=True)

    def split(self, sep=None, maxsplit=None, reverse=False):
        if hasattr(sep, 'clean_string'):
            sep = sep.clean_string
        args = [sep]
        if maxsplit is not None:
            args.append(maxsplit)
        if reverse:
            parent_result = self.clean_string.rsplit(*args)
        else:
            parent_result = self.clean_string.split(*args)
        current_index = 0
        result = []
        for section in parent_result:
            result.append(self[current_index:current_index + len(section)])
            current_index += (len(section)) + len(sep)
        return result

    def partition(self, sep, reverse=False):
        if hasattr(sep, 'clean_string'):
            sep = sep.clean_string
        if reverse:
            parent_result = self.clean_string.rpartition(sep)
        else:
            parent_result = self.clean_string.partition(sep)
        current_index = 0
        result = tuple()
        for section in parent_result:
            result += (self[current_index:current_index + len(section)],)
            current_index += len(section)
        return result

    def _get_indexes(self):
        matches = [
            (match.start(), match.end())
            for match in self.parser.ansi_regex.finditer(self.raw_string)]
        code_indexes = []
        # These are all the indexes which hold code characters.
        for start, end in matches:
            code_indexes.extend(range(start, end))

        if not code_indexes:
            # Plain string, no ANSI codes.
            return code_indexes, range(0, len(self.raw_string))
        flat_ranges = []
        # We need to get the ones between them, but the code might start at
        # the beginning, and there might be codes at the end.
        for tup in matches:
            flat_ranges.extend(tup)
        # Is the beginning of the string a code character?
        if flat_ranges[0] == 0:
            flat_ranges.pop(0)
        else:
            flat_ranges.insert(0, 0)
        # How about the end?
        end_index = (len(self.raw_string) - 1)
        if flat_ranges[-1] == end_index:
            flat_ranges.pop()
        else:
            flat_ranges.append(end_index)
        char_indexes = []
        for start, end in list(group(flat_ranges, 2)):
            char_indexes.extend(range(start, end))
        # The end character will be left off if it's a normal character. Fix
        # that here.
        if end_index in flat_ranges:
            char_indexes.append(end_index)
        return code_indexes, char_indexes

    @_spacing_preflight
    def center(self, width, fillchar, difference):
        remainder = difference % 2
        difference /= 2
        spacing = difference * fillchar
        result = spacing + self + spacing + (remainder * fillchar)
        return result

    @_spacing_preflight
    def ljust(self, width, fillchar, difference):
        return self + (difference * fillchar)

    @_spacing_preflight
    def rjust(self, width, fillchar, difference):
        return (difference * fillchar) + self


def _query_super(func_name):
    """
    Have the string class handle this with the cleaned string instead of
    ANSIString.
    """
    def query_func(self, *args, **kwargs):
        return getattr(self.clean_string, func_name)(*args, **kwargs)
    return query_func


def _on_raw(func_name):
    """
    Like query_super, but makes the operation run on the raw string.
    """
    def wrapped(self, *args, **kwargs):
        args = list(args)
        try:
            string = args.pop(0)
            if hasattr(string, 'raw_string'):
                args.insert(0, string.raw_string)
            else:
                args.insert(0, string)
        except IndexError:
            pass
        result = _query_super(func_name)(self, *args, **kwargs)
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
        for index in range(0, len(self.raw_string)):
            if index in self._code_indexes:
                to_string.append(self.raw_string[index])
            elif index in self._char_indexes:
                to_string.append(replacement_string[index])
        return ANSIString(''.join(to_string), decoded=True)
    return wrapped


for func_name in [
        'count', 'startswith', 'endswith', 'find', 'index', 'isalnum',
        'isalpha', 'isdigit', 'islower', 'isspace', 'istitle', 'isupper',
        'rfind', 'rindex']:
    setattr(ANSIString, func_name, _query_super(func_name))
for func_name in [
        '__mul__', '__mod__', 'expandtabs', '__rmul__', 'join',
        'decode', 'replace', 'format']:
    setattr(ANSIString, func_name, _on_raw(func_name))
for func_name in [
        'capitalize', 'translate', 'lower', 'upper', 'swapcase']:
    setattr(ANSIString, func_name, _transform(func_name))
