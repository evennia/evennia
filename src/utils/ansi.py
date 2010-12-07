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

class ANSITable(object):
    """
    A table defining the 
    standard ANSI command sequences.

    """
    ansi = {}
    ansi["beep"] = "\07"
    ansi["escape"] = "\033"
    ansi["normal"] = "\033[0m"
    
    ansi["underline"] = "\033[4m"
    ansi["hilite"] = "\033[1m"
    ansi["blink"] = "\033[5m"
    ansi["inverse"] = "\033[7m"
    ansi["inv_hilite"] = "\033[1;7m"
    ansi["inv_blink"] = "\033[7;5m"
    ansi["blink_hilite"] = "\033[1;5m"
    ansi["inv_blink_hilite"] = "\033[1;5;7m"
    
    # Foreground colors
    ansi["black"] = "\033[30m"
    ansi["red"] = "\033[31m"
    ansi["green"] = "\033[32m"
    ansi["yellow"] = "\033[33m"
    ansi["blue"] = "\033[34m"
    ansi["magenta"] = "\033[35m"
    ansi["cyan"] = "\033[36m"
    ansi["white"] = "\033[37m"
    
    # Background colors
    ansi["back_black"] = "\033[40m"
    ansi["back_red"] = "\033[41m"
    ansi["back_green"] = "\033[42m"
    ansi["back_yellow"] = "\033[43m"
    ansi["back_blue"] = "\033[44m"
    ansi["back_magenta"] = "\033[45m"
    ansi["back_cyan"] = "\033[46m"
    ansi["back_white"] = "\033[47m"
    
    # Formatting Characters
    ansi["return"] = "\r\n"
    ansi["tab"] = "\t"
    ansi["space"] = " "
    

class ANSIParser(object):
    """
    A class that parses ansi markup 
    to ANSI command sequences
    """

    def __init__(self):
        "Sets the mappings"

        # MUX-style mappings %cr %cn etc

        self.mux_ansi_map = [
            (r'%r',  ANSITable.ansi["return"]),
            (r'%t',  ANSITable.ansi["tab"]),
            (r'%b',  ANSITable.ansi["space"]),
            (r'%cf', ANSITable.ansi["blink"]),
            (r'%ci', ANSITable.ansi["inverse"]),
            (r'%ch', ANSITable.ansi["hilite"]),
            (r'%cn', ANSITable.ansi["normal"]),
            (r'%cx', ANSITable.ansi["black"]),
            (r'%cX', ANSITable.ansi["back_black"]),
            (r'%cr', ANSITable.ansi["red"]),
            (r'%cR', ANSITable.ansi["back_red"]),
            (r'%cg', ANSITable.ansi["green"]),
            (r'%cG', ANSITable.ansi["back_green"]),
            (r'%cy', ANSITable.ansi["yellow"]),
            (r'%cY', ANSITable.ansi["back_yellow"]),
            (r'%cb', ANSITable.ansi["blue"]),
            (r'%cB', ANSITable.ansi["back_blue"]),
            (r'%cm', ANSITable.ansi["magenta"]),
            (r'%cM', ANSITable.ansi["back_magenta"]),
            (r'%cc', ANSITable.ansi["cyan"]),
            (r'%cC', ANSITable.ansi["back_cyan"]),
            (r'%cw', ANSITable.ansi["white"]),
            (r'%cW', ANSITable.ansi["back_white"]),
            ]

        # Expanded mapping {r {n etc

        hilite = ANSITable.ansi['hilite']
        normal = ANSITable.ansi['normal']
        self.ext_ansi_map = [
            (r'{r', hilite + ANSITable.ansi['red']),    
            (r'{R', normal + ANSITable.ansi['red']),    
            (r'{g', hilite + ANSITable.ansi['green']),
            (r'{G', normal + ANSITable.ansi['green']),
            (r'{y', hilite + ANSITable.ansi['yellow']),
            (r'{Y', normal + ANSITable.ansi['yellow']),
            (r'{b', hilite + ANSITable.ansi['blue']),
            (r'{B', normal + ANSITable.ansi['blue']),
            (r'{m', hilite + ANSITable.ansi['magenta']),
            (r'{M', normal + ANSITable.ansi['magenta']),
            (r'{c', hilite + ANSITable.ansi['cyan']),
            (r'{C', normal + ANSITable.ansi['cyan']),
            (r'{w', hilite + ANSITable.ansi['white']), #white
            (r'{W', normal + ANSITable.ansi['white']), #light grey
            (r'{x', hilite + ANSITable.ansi['black']), #dark grey
            (r'{X', normal + ANSITable.ansi['black']), #pure black
            (r'{n', normal)                            #reset
            ] 
        
        self.ansi_map = self.mux_ansi_map + self.ext_ansi_map

        # prepare regex matching
        self.ansi_sub = [(re.compile(sub[0], re.DOTALL), sub[1])
                         for sub in self.ansi_map]
        # prepare matching ansi codes overall
        self.ansi_regex = re.compile("\033\[[0-9;]+m")

    def parse_ansi(self, string, strip_ansi=False):
        """
        Parses a string, subbing color codes according to
        the stored mapping. 

        strip_ansi flag instead removes all ansi markup.

        """
        if not string:
            return ''
        string = str(string)
        for sub in self.ansi_sub:
            # go through all available mappings and translate them
            string = sub[0].sub(sub[1], string)
        if strip_ansi:
            # remove all ANSI escape codes
            string = self.ansi_regex.sub("", string)
        return string 


            
ANSI_PARSER = ANSIParser()

#
# Access function
#

def parse_ansi(string, strip_ansi=False, parser=ANSI_PARSER):
    """
    Parses a string, subbing color codes as needed.

    """
    return parser.parse_ansi(string, strip_ansi=strip_ansi)


