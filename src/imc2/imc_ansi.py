"""
ANSI parser - this adds colour to text according to
special markup strings. 
"""

from src.utils import ansi
from ansi import BaseParser, ANSITable

class IMCANSIParser(BaseParser):
    """
    This parser is per the IMC2 specification.
    """
    def __init__(self):
        self.ansi_subs = [
            # Random
            (r'~Z', ANSITable.ansi["normal"]),
            # Dark Grey
            (r'~D', ANSITable.ansi["hilite"] + ANSITable.ansi["black"]),
            (r'~z', ANSITable.ansi["hilite"] + ANSITable.ansi["black"]),
            # Grey/reset
            (r'~w', ANSITable.ansi["normal"]),
            (r'~d', ANSITable.ansi["normal"]),
            (r'~!', ANSITable.ansi["normal"]),
            # Bold/hilite
            (r'~L', ANSITable.ansi["hilite"]),
            # White
            (r'~W', ANSITable.ansi["normal"] + ANSITable.ansi["hilite"]),
            # Dark Green
            (r'~g', ANSITable.ansi["normal"] + ANSITable.ansi["green"]),
            # Green
            (r'~G', ANSITable.ansi["hilite"] + ANSITable.ansi["green"]),
            # Dark magenta
            (r'~p', ANSITable.ansi["normal"] + ANSITable.ansi["magenta"]),
            (r'~m', ANSITable.ansi["normal"] + ANSITable.ansi["magenta"]),
            # Magenta
            (r'~M', ANSITable.ansi["hilite"] + ANSITable.ansi["magenta"]),
            (r'~P', ANSITable.ansi["hilite"] + ANSITable.ansi["magenta"]),
            # Black
            (r'~x', ANSITable.ansi["normal"] + ANSITable.ansi["black"]),
            # Cyan
            (r'~c', ANSITable.ansi["normal"] + ANSITable.ansi["cyan"]),
            # Dark Yellow (brown)
            (r'~Y', ANSITable.ansi["hilite"] + ANSITable.ansi["yellow"]),
            # Yellow
            (r'~y', ANSITable.ansi["normal"] + ANSITable.ansi["yellow"]),
            # Dark Blue
            (r'~B', ANSITable.ansi["normal"] + ANSITable.ansi["blue"]),
            # Blue
            (r'~C', ANSITable.ansi["hilite"] + ANSITable.ansi["blue"]),
            # Dark Red
            (r'~r', ANSITable.ansi["normal"] + ANSITable.ansi["red"]),
            # Red
            (r'~R', ANSITable.ansi["normal"] + ANSITable.ansi["red"]),
            # Dark Blue
            (r'~b', ANSITable.ansi["normal"] + ANSITable.ansi["blue"]),
            ## Formatting
            (r'\\r', ANSITable.ansi["normal"]),
            (r'\\n', ANSITable.ansi["return"]),
        ]
        
def parse_ansi(*args, **kwargs):
    """
    Shortcut to use the IMC2 ANSI parser.
    """
    return ansi.parse_ansi(parser=IMCANSIParser(), *args, **kwargs)
