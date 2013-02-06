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

class ANSIParser(object):
    """
    A class that parses ansi markup
    to ANSI command sequences

    We also allow to escape colour codes
    by prepending with a \ for mux-style and xterm256,
    an extra { for Merc-style codes
    """

    def __init__(self):
        "Sets the mappings"

        # MUX-style mappings %cr %cn etc

        self.mux_ansi_map = [
            # commented out by default; they (especially blink) are potentially annoying
            (r'%r',  ANSI_RETURN),
            (r'%t',  ANSI_TAB),
            (r'%b',  ANSI_SPACE),
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
            (r'%cX', ANSI_BACK_BLACK),
            (r'%ch', ANSI_HILITE),
            (r'%cn', ANSI_NORMAL),
            ]

        # Expanded mapping {r {n etc

        hilite = ANSI_HILITE
        normal = ANSI_NORMAL
        self.ext_ansi_map = [
            (r'{r', hilite + ANSI_RED),
            (r'{R', normal + ANSI_RED),
            (r'{g', hilite + ANSI_GREEN),
            (r'{G', normal + ANSI_GREEN),
            (r'{y', hilite + ANSI_YELLOW),
            (r'{Y', normal + ANSI_YELLOW),
            (r'{b', hilite + ANSI_BLUE),
            (r'{B', normal + ANSI_BLUE),
            (r'{m', hilite + ANSI_MAGENTA),
            (r'{M', normal + ANSI_MAGENTA),
            (r'{c', hilite + ANSI_CYAN),
            (r'{C', normal + ANSI_CYAN),
            (r'{w', hilite + ANSI_WHITE), # pure white
            (r'{W', normal + ANSI_WHITE), #light grey
            (r'{x', hilite + ANSI_BLACK), #dark grey
            (r'{X', normal + ANSI_BLACK), #pure black
            (r'{n', normal)               #reset
            ]

        # xterm256 {123, %c134,

        self.xterm256_map = [
            (r'%c([0-5]{3})', self.parse_rgb),  # %c123 - foreground colour
            (r'%c(b[0-5]{3})', self.parse_rgb), # %cb123 - background colour
            (r'{([0-5]{3})', self.parse_rgb),   # {123 - foreground colour
            (r'{(b[0-5]{3})', self.parse_rgb)   # {b123 - background colour
            ]

        # obs - order matters here, we want to do the xterms first since
        # they collide with some of the other mappings otherwise.
        self.ansi_map = self.xterm256_map + self.mux_ansi_map + self.ext_ansi_map

        # prepare regex matching
        self.ansi_sub = [(re.compile(sub[0], re.DOTALL), sub[1])
                         for sub in self.ansi_map]

        # prepare matching ansi codes overall
        self.ansi_regex = re.compile("\033\[[0-9;]+m")

        # escapes - these double-chars will be replaced with a single instance of each
        self.ansi_escapes = re.compile(r"(%s)" % "|".join(ANSI_ESCAPES), re.DOTALL)

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

        background = rgbtag[0] == 'b'
        if background:
            red, green, blue = int(rgbtag[1]), int(rgbtag[2]), int(rgbtag[3])
        else:
            red, green, blue = int(rgbtag[0]), int(rgbtag[1]), int(rgbtag[2])

        if self.do_xterm256:
            colval = 16 + (red * 36) + (green * 6) + blue
            #print "RGB colours:", red, green, blue
            return "\033[%s8;5;%s%s%sm" % (3 + int(background), colval/100, (colval%100)/10, colval%10)
        else:
            #print "ANSI convert:", red, green, blue
            # xterm256 not supported, convert the rgb value to ansi instead
            if red == green and red == blue and red < 2:
                if background: return ANSI_BACK_BLACK
                elif red >= 1: return ANSI_HILITE + ANSI_BLACK
                else: return ANSI_NORMAL + ANSI_BLACK
            elif red == green and red == blue:
                if background: return ANSI_BACK_WHITE
                elif red >= 4: return ANSI_HILITE + ANSI_WHITE
                else: return ANSI_NORMAL + ANSI_WHITE
            elif red > green and red > blue:
                if background: return ANSI_BACK_RED
                elif red >= 3: return ANSI_HILITE + ANSI_RED
                else: return ANSI_NORMAL + ANSI_RED
            elif red == green and red > blue:
                if background: return ANSI_BACK_YELLOW
                elif red >= 3: return ANSI_HILITE + ANSI_YELLOW
                else: return ANSI_NORMAL + ANSI_YELLOW
            elif red == blue and red > green:
                if background: return ANSI_BACK_MAGENTA
                elif red >= 3: return ANSI_HILITE + ANSI_MAGENTA
                else: return ANSI_NORMAL + ANSI_MAGENTA
            elif green > blue:
                if background: return ANSI_BACK_GREEN
                elif green >= 3: return ANSI_HILITE + ANSI_GREEN
                else: return ANSI_NORMAL + ANSI_GREEN
            elif green == blue:
                if background: return ANSI_BACK_CYAN
                elif green >= 3: return ANSI_HILITE + ANSI_CYAN
                else: return ANSI_NORMAL + ANSI_CYAN
            else:    # mostly blue
                if background: return ANSI_BACK_BLUE
                elif blue >= 3: return ANSI_HILITE + ANSI_BLUE
                else: return ANSI_NORMAL + ANSI_BLUE

    def parse_ansi(self, string, strip_ansi=False, xterm256=False):
        """
        Parses a string, subbing color codes according to
        the stored mapping.

        strip_ansi flag instead removes all ansi markup.

        """
        if not string:
            return ''
        self.do_xterm256 = xterm256
        string = utils.to_str(string)

        # go through all available mappings and translate them
        parts = self.ansi_escapes.split(string) + [" "]
        string = ""
        for part, sep in zip(parts[::2], parts[1::2]):
            for sub in self.ansi_sub:
                part = sub[0].sub(sub[1], part)
            string += "%s%s" % (part, sep[0].strip())
        if strip_ansi:
            # remove all ansi codes (including those manually inserted in string)
            string = self.ansi_regex.sub("", string)
        return string


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
    return string.replace('{','{{').replace('%','%%')
