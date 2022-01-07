# Color markups

Contribution, Griatch 2017

Additional color markup styles for Evennia (extending or replacing the default
`|r`, `|234` etc).


## Installation

Import the desired style variables from this module into
mygame/server/conf/settings.py and add them to the settings variables below.
Each are specified as a list, and multiple such lists can be added to each
variable to support multiple formats. Note that list order affects which regexes
are applied first. You must restart both Portal and Server for color tags to
update.

Assign to the following settings variables (see below for example):

    COLOR_ANSI_EXTRA_MAP - a mapping between regexes and ANSI colors
    COLOR_XTERM256_EXTRA_FG - regex for defining XTERM256 foreground colors
    COLOR_XTERM256_EXTRA_BG - regex for defining XTERM256 background colors
    COLOR_XTERM256_EXTRA_GFG - regex for defining XTERM256 grayscale foreground colors
    COLOR_XTERM256_EXTRA_GBG - regex for defining XTERM256 grayscale background colors
    COLOR_ANSI_BRIGHT_BG_EXTRA_MAP = ANSI does not support bright backgrounds; we fake
    this by mapping ANSI markup to matching bright XTERM256 backgrounds

    COLOR_NO_DEFAULT - Set True/False. If False (default), extend the default
    markup, otherwise replace it completely.

## Example

To add the {- "curly-bracket" style, add the following to your settings file,
then reboot both Server and Portal:

```python
from evennia.contrib.base_systems import color_markups
COLOR_ANSI_EXTRA_MAP = color_markups.CURLY_COLOR_ANSI_EXTRA_MAP
COLOR_XTERM256_EXTRA_FG = color_markups.CURLY_COLOR_XTERM256_EXTRA_FG
COLOR_XTERM256_EXTRA_BG = color_markups.CURLY_COLOR_XTERM256_EXTRA_BG
COLOR_XTERM256_EXTRA_GFG = color_markups.CURLY_COLOR_XTERM256_EXTRA_GFG
COLOR_XTERM256_EXTRA_GBG = color_markups.CURLY_COLOR_XTERM256_EXTRA_GBG
COLOR_ANSI_BRIGHT_BG_EXTRA_MAP = color_markups.CURLY_COLOR_ANSI_BRIGHT_BG_EXTRA_MAP
```

To add the `%c-` "mux/mush" style, add the following to your settings file, then
reboot both Server and Portal:

```python
from evennia.contrib.base_systems import color_markups
COLOR_ANSI_EXTRA_MAP = color_markups.MUX_COLOR_ANSI_EXTRA_MAP
COLOR_XTERM256_EXTRA_FG = color_markups.MUX_COLOR_XTERM256_EXTRA_FG
COLOR_XTERM256_EXTRA_BG = color_markups.MUX_COLOR_XTERM256_EXTRA_BG
COLOR_XTERM256_EXTRA_GFG = color_markups.MUX_COLOR_XTERM256_EXTRA_GFG
COLOR_XTERM256_EXTRA_GBG = color_markups.MUX_COLOR_XTERM256_EXTRA_GBG
COLOR_ANSI_BRIGHT_BGS_EXTRA_MAP = color_markups.CURLY_COLOR_ANSI_BRIGHT_BGS_EXTRA_MAP
```


----

<small>This document page is generated from `evennia/contrib/base_systems/color_markups/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
