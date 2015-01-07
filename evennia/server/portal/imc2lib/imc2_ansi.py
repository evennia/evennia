"""
ANSI parser - this adds colour to text according to
special markup strings.

This is a IMC2 complacent version.
"""

import re
from evennia.utils import ansi


class IMCANSIParser(ansi.ANSIParser):
    """
    This parser is per the IMC2 specification.
    """
    def __init__(self):
        normal = ansi.ANSI_NORMAL
        hilite = ansi.ANSI_HILITE
        self.ansi_map = [
            (r'~Z', normal),  # Random
            (r'~x', normal + ansi.ANSI_BLACK),    # Black
            (r'~D', hilite + ansi.ANSI_BLACK),    # Dark Grey
            (r'~z', hilite + ansi.ANSI_BLACK),
            (r'~w', normal + ansi.ANSI_WHITE),    # Grey
            (r'~W', hilite + ansi.ANSI_WHITE),    # White
            (r'~g', normal + ansi.ANSI_GREEN),    # Dark Green
            (r'~G', hilite + ansi.ANSI_GREEN),    # Green
            (r'~p', normal + ansi.ANSI_MAGENTA),  # Dark magenta
            (r'~m', normal + ansi.ANSI_MAGENTA),
            (r'~M', hilite + ansi.ANSI_MAGENTA),  # Magenta
            (r'~P', hilite + ansi.ANSI_MAGENTA),
            (r'~c', normal + ansi.ANSI_CYAN),     # Cyan
            (r'~y', normal + ansi.ANSI_YELLOW),   # Dark Yellow (brown)
            (r'~Y', hilite + ansi.ANSI_YELLOW),   # Yellow
            (r'~b', normal + ansi.ANSI_BLUE),     # Dark Blue
            (r'~B', hilite + ansi.ANSI_BLUE),     # Blue
            (r'~C', hilite + ansi.ANSI_BLUE),
            (r'~r', normal + ansi.ANSI_RED),      # Dark Red
            (r'~R', hilite + ansi.ANSI_RED),      # Red

            ## Formatting
            (r'~L', hilite),                     # Bold/hilite
            (r'~!', normal),                     # reset
            (r'\\r', normal),
            (r'\\n', ansi.ANSI_RETURN),
        ]
        # prepare regex matching
        self.ansi_sub = [(re.compile(sub[0], re.DOTALL), sub[1])
                         for sub in self.ansi_map]
        # prepare matching ansi codes overall
        self.ansi_regex = re.compile("\033\[[0-9;]+m")

ANSI_PARSER = IMCANSIParser()


def parse_ansi(string, strip_ansi=False, parser=ANSI_PARSER):
    """
    Shortcut to use the IMC2 ANSI parser.
    """
    return parser.parse_ansi(string, strip_ansi=strip_ansi)
