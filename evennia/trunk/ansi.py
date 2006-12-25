import re
"""
ANSI related stuff.
"""
ansi = {}
ansi["beep"]   = "\07"
ansi["escape"] = "\033"
ansi["normal"] = "\033[0m"

ansi["underline"]        = "\033[4m"
ansi["hilite"]           = "\033[1m"
ansi["blink"]            = "\033[5m"
ansi["inverse"]          = "\033[7m"
ansi["inv_hilite"]       = "\033[1;7m"
ansi["inv_blink"]        = "\033[7;5m"
ansi["blink_hilite"]     = "\033[1;5m"
ansi["inv_blink_hilite"] = "\033[1;5;7m"

# Foreground colors
ansi["black"]   = "\033[30m"
ansi["red"]     = "\033[31m"
ansi["green"]   = "\033[32m"
ansi["yellow"]  = "\033[33m"
ansi["blue"]    = "\033[34m"
ansi["magenta"] = "\033[35m"
ansi["cyan"]    = "\033[36m"
ansi["white"]   = "\033[37m"

# Background colors
ansi["back_black"]   = "\033[40m"
ansi["back_red"]     = "\033[41m"
ansi["back_green"]   = "\033[42m"
ansi["back_yellow"]  = "\033[43m"
ansi["back_blue"]    = "\033[44m"
ansi["back_magenta"] = "\033[45m"
ansi["back_cyan"]    = "\033[46m"
ansi["back_white"]   = "\033[47m"

# Formatting Characters
ansi["return"] = "\n\r"
ansi["tab"]    = "\t"
ansi["space"]  = " "

def parse_ansi(string, strip_ansi=False, strip_formatting=False):
   """
   Parses a string, subbing color codes as needed.
   """
   if strip_formatting:
      char_return = ""
      char_tab = ""
      char_space = ""
   else:
      char_return = ansi["return"]
      char_tab = ansi["tab"]
      char_space = ansi["space"]
      
   ansi_subs = [
      (r'%r',  char_return),
      (r'%t',  char_tab),
      (r'%b',  char_space),
      (r'%cf', ansi["blink"]),
      (r'%ci', ansi["inverse"]),
      (r'%ch', ansi["hilite"]),
      (r'%cn', ansi["normal"]),
      (r'%cx', ansi["black"]),
      (r'%cX', ansi["back_black"]),
      (r'%cr', ansi["red"]),
      (r'%cR', ansi["back_red"]),
      (r'%cg', ansi["green"]),
      (r'%cG', ansi["back_green"]),
      (r'%cy', ansi["yellow"]),
      (r'%cY', ansi["back_yellow"]),
      (r'%cb', ansi["blue"]),
      (r'%cB', ansi["back_blue"]),
      (r'%cm', ansi["magenta"]),
      (r'%cM', ansi["back_magenta"]),
      (r'%cc', ansi["cyan"]),
      (r'%cC', ansi["back_cyan"]),
      (r'%cw', ansi["white"]),
      (r'%cW', ansi["back_white"]),
   ]
   
   for sub in ansi_subs:
      p = re.compile(sub[0], re.DOTALL)
      if strip_ansi:
         string = p.sub("", string)
      else:
         string = p.sub(sub[1], string)

   if strip_ansi:
      return '%s' % (string)
   else:
      return '%s%s' % (string, ansi["normal"])

