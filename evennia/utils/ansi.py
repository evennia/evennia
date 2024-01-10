"""
ANSI - Gives colour to text.

Use the codes defined in the *ANSIParser* class to apply colour to text. The
`parse_ansi` function in this module parses text for markup and `strip_markup`
removes it.

You should usually not need to call `parse_ansi` explicitly; it is run by
Evennia just before returning data to/from the user. Alternative markup is
possible by overriding the parser class (see also contrib/ for deprecated
markup schemes).


Supported standards:

- ANSI 8 bright and 8 dark fg (foreground) colors
- ANSI 8 dark bg (background) colors
- 'ANSI' 8 bright bg colors 'faked' with xterm256 (bright bg not included in ANSI standard)
- Xterm256 - 255 fg/bg colors + 26 greyscale fg/bg colors

## Markup

ANSI colors: `r` ed, `g` reen, `y` ellow, `b` lue, `m` agenta, `c` yan, `n` ormal (no color).
Capital letters indicate the 'dark' variant.

- `|r` fg bright red
- `|R` fg dark red
- `|[r` bg bright red
- `|[R` bg dark red
- `|[R|g` bg dark red, fg bright green

```python
"This is |rRed text|n and this is normal again."

```

Xterm256 colors are given as RGB (Red-Green-Blue), with values 0-5:

- `|500` fg bright red
- `|050` fg bright green
- `|005` fg bright blue
- `|110` fg dark brown
- `|425` fg pink
- `|[431` bg orange

Xterm256 greyscale:

- `|=a` fg black
- `|=g` fg dark grey
- `|=o` fg middle grey
- `|=v` fg bright grey
- `|=z` fg white
- `|[=r` bg middle grey

```python
"This is |500Red text|n and this is normal again."
"This is |[=jText on dark grey background"

```

----

"""
import re
from collections import OrderedDict

from django.conf import settings

from evennia.utils import logger, utils

MXP_ENABLED = settings.MXP_ENABLED
_MARKUP_CHAR = settings.MARKUP_CHAR

_EVSTRING = None

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

_COLOR_NO_DEFAULT = settings.COLOR_NO_DEFAULT

_RE_HEX = re.compile(fr'(?<!\{_MARKUP_CHAR})\{_MARKUP_CHAR}#([0-9a-f]{6})', re.I)
_RE_HEX_BG = re.compile(fr'(?<!\{_MARKUP_CHAR})\{_MARKUP_CHAR}\[#([0-9a-f]{6})', re.I)
_RE_XTERM = re.compile(fr'(?<!\{_MARKUP_CHAR})\{_MARKUP_CHAR}([0-5][0-5][0-5]|\=[a-z])')
_RE_XTERM_BG = re.compile(fr'(?<!\{_MARKUP_CHAR})\{_MARKUP_CHAR}\[([0-5][0-5][0-5]|\=[a-z])')

_PARSE_CACHE = OrderedDict()
_PARSE_CACHE_SIZE = 10000

class RenderToANSI(object):
    """
    A class that converts Evennia markup to ANSI command sequences

    """

    ansi_map = [
        # alternative |-format
        (r"n", ANSI_NORMAL),  # reset
        (r"/", ANSI_RETURN),  # line break
        (r"-", ANSI_TAB),  # tab
        (r">", ANSI_SPACE * 4),  # indent (4 spaces)
        (r"_", ANSI_SPACE),  # space
        (r"*", ANSI_INVERSE),  # invert
        (r"^", ANSI_BLINK),  # blinking text (very annoying and not supported by all clients)
        (r"u", ANSI_UNDERLINE),  # underline
        (r"r", ANSI_HILITE + ANSI_RED),
        (r"g", ANSI_HILITE + ANSI_GREEN),
        (r"y", ANSI_HILITE + ANSI_YELLOW),
        (r"b", ANSI_HILITE + ANSI_BLUE),
        (r"m", ANSI_HILITE + ANSI_MAGENTA),
        (r"c", ANSI_HILITE + ANSI_CYAN),
        (r"w", ANSI_HILITE + ANSI_WHITE),  # pure white
        (r"x", ANSI_HILITE + ANSI_BLACK),  # dark grey
        (r"R", ANSI_UNHILITE + ANSI_RED),
        (r"G", ANSI_UNHILITE + ANSI_GREEN),
        (r"Y", ANSI_UNHILITE + ANSI_YELLOW),
        (r"B", ANSI_UNHILITE + ANSI_BLUE),
        (r"M", ANSI_UNHILITE + ANSI_MAGENTA),
        (r"C", ANSI_UNHILITE + ANSI_CYAN),
        (r"W", ANSI_UNHILITE + ANSI_WHITE),  # light grey
        (r"X", ANSI_UNHILITE + ANSI_BLACK),  # pure black
        # hilight-able colors
        (r"h", ANSI_HILITE),
        (r"H", ANSI_UNHILITE),
        (r"!R", ANSI_RED),
        (r"!G", ANSI_GREEN),
        (r"!Y", ANSI_YELLOW),
        (r"!B", ANSI_BLUE),
        (r"!M", ANSI_MAGENTA),
        (r"!C", ANSI_CYAN),
        (r"!W", ANSI_WHITE),  # light grey
        (r"!X", ANSI_BLACK),  # pure black
        # normal ANSI backgrounds
        (r"[R", ANSI_BACK_RED),
        (r"[G", ANSI_BACK_GREEN),
        (r"[Y", ANSI_BACK_YELLOW),
        (r"[B", ANSI_BACK_BLUE),
        (r"[M", ANSI_BACK_MAGENTA),
        (r"[C", ANSI_BACK_CYAN),
        (r"[W", ANSI_BACK_WHITE),  # light grey background
        (r"[X", ANSI_BACK_BLACK),  # pure black background
    ]

    ansi_xterm256_bright_bg_map = [
        # "bright" ANSI backgrounds using xterm256 since ANSI
        # standard does not support it (will
        # fallback to dark ANSI background colors if xterm256
        # is not supported by client)
        # |-style variations
        (r"[r", r"|[500"),
        (r"[g", r"|[050"),
        (r"[y", r"|[550"),
        (r"[b", r"|[005"),
        (r"[m", r"|[505"),
        (r"[c", r"|[055"),
        (r"[w", r"|[555"),  # white background
        (r"[x", r"|[222"),  # dark grey background
    ]

    # xterm256. These are replaced directly by
    # the sub_xterm256 method

    # with adding the markup character to the settings, this should be deprecated?
    if settings.COLOR_NO_DEFAULT:
        ansi_map = settings.COLOR_ANSI_EXTRA_MAP
        xterm256_fg = settings.COLOR_XTERM256_EXTRA_FG
        xterm256_bg = settings.COLOR_XTERM256_EXTRA_BG
        xterm256_gfg = settings.COLOR_XTERM256_EXTRA_GFG
        xterm256_gbg = settings.COLOR_XTERM256_EXTRA_GBG
        ansi_xterm256_bright_bg_map = settings.COLOR_ANSI_XTERM256_BRIGHT_BG_EXTRA_MAP
    else:
        xterm256_fg = [fr"\{_MARKUP_CHAR}([0-5])([0-5])([0-5])"]  # |123 - foreground colour
        xterm256_bg = [fr"\{_MARKUP_CHAR}\[([0-5])([0-5])([0-5])"]  # |[123 - background colour
        xterm256_gfg = [fr"\{_MARKUP_CHAR}=([a-z])"]  # |=a - greyscale foreground
        xterm256_gbg = [fr"\{_MARKUP_CHAR}\[=([a-z])"]  # |[=a - greyscale background
        ansi_map += settings.COLOR_ANSI_EXTRA_MAP
        xterm256_fg += settings.COLOR_XTERM256_EXTRA_FG
        xterm256_bg += settings.COLOR_XTERM256_EXTRA_BG
        xterm256_gfg += settings.COLOR_XTERM256_EXTRA_GFG
        xterm256_gbg += settings.COLOR_XTERM256_EXTRA_GBG
        ansi_xterm256_bright_bg_map += settings.COLOR_ANSI_XTERM256_BRIGHT_BG_EXTRA_MAP

    # prepare regex matching
    re_xterm256_fg = re.compile(r"|".join(xterm256_fg), re.DOTALL)
    re_xterm256_bg = re.compile(r"|".join(xterm256_bg), re.DOTALL)
    re_xterm256_gfg = re.compile(r"|".join(xterm256_gfg), re.DOTALL)
    re_xterm256_gbg = re.compile(r"|".join(xterm256_gbg), re.DOTALL)

    # used by regex replacer to correctly map ansi sequences
    ansi_map_dict = dict(ansi_map)
    ansi_xterm256_bright_bg_map_dict = dict(ansi_xterm256_bright_bg_map)

    # for matching ansi codes overall
    ansi_regex = re.compile(r"\033\[[0-9;]+m")

    hex_fg = _RE_HEX
    hex_bg = _RE_HEX_BG

    def convert_xterm256(self, rgbmatch, use_xterm256=False, color_type="fg"):
        """
        This is a replacer method called by `re.sub` with the matched
        tag. It must return the correct ansi sequence.

        Args:
            rgbmatch (re.matchobject): The match.
            use_xterm256 (bool, optional): Don't convert 256-colors to 16.
            color_type (str): One of 'fg', 'bg', 'gfg', 'gbg'.

        Returns:
            processed (str): The processed match string.

        """
        if not rgbmatch:
            return ""

        # get tag, stripping the initial marker
        # rgbtag = rgbmatch.group()[1:]

        background = color_type in ("bg", "gbg")
        grayscale = color_type in ("gfg", "gbg")

        if not grayscale:
            # 6x6x6 color-cube (xterm indexes 16-231)
            try:
                red, green, blue = [int(val) for val in rgbmatch.groups() if val is not None]
            except (IndexError, ValueError):
                logger.log_trace()
                return rgbmatch.group(0)
        else:
            # grayscale values (xterm indexes 0, 232-255, 15) for full spectrum
            try:
                letter = [val for val in rgbmatch.groups() if val is not None][0]
            except IndexError:
                logger.log_trace()
                return rgbmatch.group(0)

            if letter == "a":
                colval = 16  # pure black @ index 16 (first color cube entry)
            elif letter == "z":
                colval = 231  # pure white @ index 231 (last color cube entry)
            else:
                # letter in range [b..y] (exactly 24 values!)
                colval = 134 + ord(letter)

            # ansi fallback logic expects r,g,b values in [0..5] range
            gray = round((ord(letter) - 97) / 5.0)
            red, green, blue = gray, gray, gray

        if use_xterm256:

            if not grayscale:
                colval = 16 + (red * 36) + (green * 6) + blue

            return "\033[{}8;5;{}m".format(3 + int(background), colval)
            # replaced since some clients (like Potato) does not accept codes with leading zeroes,
            # see issue #1024.
            # return "\033[%s8;5;%s%s%sm" % (3 + int(background), colval // 100, (colval % 100) // 10, colval%10)  # noqa

        else:
            # xterm256 not supported, convert the rgb value to ansi instead
            rgb = (red, green, blue)
  
            def _convert_for_ansi(val):
                return int((val+1)//2)

            # greys
            if (max(rgb) - min(rgb)) <= 1:
                match rgb:
                    case (0,0,0):
                        return ANSI_BACK_BLACK if background else ANSI_NORMAL + ANSI_BLACK
                    case ((1|2), (1|2), (1|2)):
                        return ANSI_BACK_BLACK if background else ANSI_HILITE + ANSI_BLACK
                    case ((2|3), (2|3), (2|3)):
                        return ANSI_BACK_WHITE if background else ANSI_NORMAL + ANSI_WHITE
                    case ((3|4), (3|4), (3|4)):
                        return ANSI_BACK_WHITE if background else ANSI_NORMAL + ANSI_WHITE
                    case ((4|5), (4|5), (4|5)):
                        return ANSI_BACK_WHITE if background else ANSI_HILITE + ANSI_WHITE

            match tuple(_convert_for_ansi(c) for c in rgb):
                # red
                case ((2|3), (0|1), (0|1)):
                    return ANSI_BACK_RED if background else ANSI_HILITE + ANSI_RED
                case ((1|2), 0, 0):
                    return ANSI_BACK_RED if background else ANSI_NORMAL + ANSI_RED
                # green
                case ((0|1), (2|3), (0|1)):
                    return ANSI_BACK_GREEN if background else ANSI_HILITE + ANSI_GREEN
                case ((0 | 1), 1, 0) if green > red:
                    return ANSI_BACK_GREEN if background else ANSI_NORMAL + ANSI_GREEN
                # blue
                case ((0|1), (0|1), (2|3)):
                    return ANSI_BACK_BLUE if background else ANSI_HILITE + ANSI_BLUE
                case (0, 0, 1):
                    return ANSI_BACK_BLUE if background else ANSI_NORMAL + ANSI_BLUE
                # cyan
                case ((0|1|2), (2|3), (2|3)) if red == min(rgb):
                    return ANSI_BACK_CYAN if background else ANSI_HILITE + ANSI_CYAN
                case (0, (1|2), (1|2)):
                    return ANSI_BACK_CYAN if background else ANSI_NORMAL + ANSI_CYAN
                # yellow
                case ((2|3), (2|3), (0|1|2)) if blue == min(rgb):
                    return ANSI_BACK_YELLOW if background else ANSI_HILITE + ANSI_YELLOW
                case ((2|1), (2|1), (0|1)):
                    return ANSI_BACK_YELLOW if background else ANSI_NORMAL + ANSI_YELLOW
                # magenta
                case ((2|3), (0|1|2), (2|3)) if green == min(rgb):
                    return ANSI_BACK_MAGENTA if background else ANSI_HILITE + ANSI_MAGENTA
                case ((1|2), 0, (1|2)):
                    return ANSI_BACK_MAGENTA if background else ANSI_NORMAL + ANSI_MAGENTA
                

    def hex_to_xterm(self, string, bg=False):
        """
        Converts a hexadecimal rgb string to an xterm256 rgb string

        Args:
          string (str): the text to parse for tags

        Returns:
          str: the text with converted tags
        """
        def split_hex(text):
          return ( int(text[i:i+2],16) for i in range(0,6,2) )
          
        def grey_int(num):
          return round( max((num-8),0)/10 )

        def hue_int(num):
          return round(max((num-45),0)/40)
        
        r, g, b = split_hex(string)

        if r == g and g == b:
            # greyscale
            i = grey_int(r)
            string = _MARKUP_CHAR + '=' + _GREYS[i]
        else:
            string = f"{_MARKUP_CHAR}{'[' if bg else ''}{hue_int(r)}{hue_int(g)}{hue_int(b)}"
        
        return string

    def strip_raw_codes(self, string):
        """
        Strips raw ANSI codes from a string.

        Args:
            string (str): The string to strip.

        Returns:
            string (str): The processed string.

        """
        return self.ansi_regex.sub("", string)

    def strip_unsafe_tokens(self, string):
        """
        Strip explicitly ansi line breaks and tabs.

        """
        return self.unsafe_tokens.sub("", string)

    def convert_markup(self, chunks, strip_markup=False, xterm256=False, rgb=False, mxp=False):
        """
        Replaces any evennia markup elements with ANSI codes

        Args:
            chunks (iter): The chunked string/code data to process
            strip_markup (bool, optional): Strip all ANSI sequences.
            rgb (bool, optional): Support full RGB color or not.
            xterm256 (bool, optional): Support xterm256 or not.
            mxp (bool, optional): Support MXP markup or not.

        Returns:
            string (str): The parsed string.

        """
        global _EVSTRING
        if not _EVSTRING:
            from evennia.utils.evstring import EvString as _EVSTRING

        # check cached parsings
        global _PARSE_CACHE
        cachekey = "%s-%s-%s-%s" % (''.join(chunks), strip_markup, xterm256, mxp)
        if cachekey in _PARSE_CACHE:
            return _PARSE_CACHE[cachekey]

        from evennia.utils.evstring import EvCode, EvLink

        output = []
        for chunk in chunks:
            if isinstance(chunk, EvCode):
                code_str = str(chunk)
                # check for hex first
                # TODO: if rgb = True, convert; for now, always fall back to xterm
                if match := self.hex_fg.search(code_str):
                    code_str = hex_to_xterm(match.group(0))
                elif match := self.hex_bg.search(code_str):
                    code_str = hex_to_xterm(match.group(0), bg=True)
                # next, check for bright bg matches (slicing off the markup tag)
                if match := self.ansi_xterm256_bright_bg_map_dict.get(code_str[1:]):
                    code_str = match
                # convert to correct form actual coded string
                if match := self.re_xterm256_fg.search(code_str):
                    code_str = self.convert_xterm256(match, use_xterm256=xterm256, color_type='fg')
                elif match := self.re_xterm256_gfg.search(code_str):
                    code_str = self.convert_xterm256(match, use_xterm256=xterm256, color_type='gfg')
                elif match := self.re_xterm256_bg.search(code_str):
                    code_str = self.convert_xterm256(match, use_xterm256=xterm256, color_type='bg')
                elif match := self.re_xterm256_gbg.search(code_str):
                    code_str = self.convert_xterm256(match, use_xterm256=xterm256, color_type='gbg')
                else:
                    # slice off the markup character for this
                    code_str = self.ansi_map_dict.get(code_str[1:], '')
                # by this point it's either converted or unconvertible, so use it
                output.append(code_str)
            
            elif isinstance(chunk, EvLink):
                link = chunk.data()
                text = _EVSTRING(link.text, ansi=self).to_ansi()
                if mxp:
                    output.append(self.convert_mxp(text, link_type=link.key, link_value=link.link))
                else:
                    output.append(text)
            
            else:
                # it's a normal string
                text = chunk
                if strip_markup:
                    # remove all ansi codes (including those manually inserted in string)
                    text = self.ansi_regex.sub("", text)
                output.append(text)

        parsed_string = ''.join(output)
        # cache and crop old cache
        _PARSE_CACHE[cachekey] = parsed_string
        if len(_PARSE_CACHE) > _PARSE_CACHE_SIZE:
            _PARSE_CACHE.popitem(last=False)

        return parsed_string

    def parse(self, string, strip_markup=False, **kwargs):
        """
        Parses a string to ANSI format, subbing color codes as needed.

        Args:
            string (str): The string to parse.

        Returns:
            string (str): The parsed string.

        """
        global _EVSTRING
        if not _EVSTRING:
            from evennia.utils.evstring import EvString as _EVSTRING
        # ensure we use this renderer for conversion
        string = _EVSTRING(string, ansi=self)
        if strip_markup:
            return self.convert_markup( (string.clean(),), **kwargs )
        return self.convert_markup(string._code_chunks)

ANSI_PARSER = RenderToANSI()


#
# Access function
#


def to_ansi(string, parser=ANSI_PARSER, **kwargs):
    """
    Access function for parsing a string and substituting Evennia markup with ANSI.
    
    Args:
        string (str): The string to be processed
        parser (ansi.AnsiParser, optional): A parser instance to use.

    Returns:
        string (str): The parsed string.

    """
    string = string or ""
    return parser.parse(string, **kwargs)

def strip_unsafe_tokens(string):
    ANSI_PARSER.strip_unsafe_tokens(string)
