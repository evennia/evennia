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
