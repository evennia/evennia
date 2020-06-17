# TextTags


This documentation details the various text tags supported by Evennia, namely *colours*, *command
links* and *inline functions*.

There is also an [Understanding Color Tags](Howto/Understanding-Color-Tags) tutorial which expands on the
use of ANSI color tags and the pitfalls of mixing ANSI and Xterms256 color tags in the same context.

## Coloured text

*Note that the Documentation does not display colour the way it would look on the screen.*
 
Color can be a very useful tool for your game. It can be used to increase readability and make your
game more appealing visually.

Remember however that, with the exception of the webclient, you generally don't control the client
used to connect to the game.  There is, for example, one special tag meaning "yellow". But exactly
*which* hue of yellow is actually displayed on the user's screen depends on the settings of their
particular mud client. They could even swap the colours around or turn them off altogether if so
desired. Some clients don't even support color - text games are also played with special reading
equipment by people who are blind or have otherwise diminished eyesight.

So a good rule of thumb is to use colour to enhance your game but don't *rely* on it to display
critical information. If you are coding the game, you can add functionality to let users disable
colours as they please, as described [here](Howto/Manually-Configuring-Color).

To see which colours your client support, use the default `@color` command. This will list all
available colours for ANSI and Xterm256 along with the codes you use for them. You can find a list
of all the parsed `ANSI`-colour codes in `evennia/utils/ansi.py`.

### ANSI colours

Evennia supports the `ANSI` standard for text. This is by far the most supported MUD-color standard,
available in all but the most ancient mud clients. The ANSI colours are **r**ed, **g**reen,
**y**ellow, **b**lue, **m**agenta, **c**yan, **w**hite and black. They are abbreviated by their
first letter except for black which is abbreviated with the letter **x**. In ANSI there are "bright"
and "normal" (darker) versions of each color, adding up to a total of 16 colours to use for
foreground text. There are also 8 "background" colours. These have no bright alternative in ANSI
(but Evennia uses the [Xterm256](Concept/TextTags#xterm256-colours) extension behind the scenes to offer
them anyway).

To colour your text you put special tags in it. Evennia will parse these and convert them to the
correct markup for the client used. If the user's client/console/display supports ANSI colour, they
will see the text in the specified colour, otherwise the tags will be stripped (uncolored text).
This works also for non-terminal clients, such as the webclient. For the webclient, Evennia will
translate the codes to HTML RGB colors.

Here is an example of the tags in action: 

     |rThis text is bright red.|n This is normal text.
     |RThis is a dark red text.|n This is normal text.
     |[rThis text has red background.|n This is normal text.
     |b|[yThis is bright blue text on yellow background.|n This is normal text.

- `|n` - this tag will turn off all color formatting, including background colors.
- `|#`- markup marks the start of foreground color. The case defines if the text is "bright" or
"normal". So `|g` is a bright green and `|G` is "normal" (darker) green.
- `|[#` is used to add a background colour to the text. The case again specifies if it is "bright"
or "normal", so `|[c` starts a bright cyan background and `|[C` a darker cyan background.
- `|!#` is used to add foreground color without any enforced brightness/normal information. 
    These are normal-intensity and are thus always given as uppercase, such as 
    `|!R` for red. The difference between e.g. `|!R` and `|R` is that 
    `|!R` will "inherit" the brightness setting from previously set color tags, whereas `|R` will
always reset to the normal-intensity red. The `|#` format contains an implicit `|h`/`|H` tag in it:
disabling highlighting when switching to a normal color, and enabling it for bright ones. So `|btest
|!Rtest2` will result in a bright red `test2` since the brightness setting from `|b` "bleeds over".
You could use this to for example quickly switch the intensity of a multitude of color tags.  There
is  no background-color equivalent to `|!` style tags.
- `|h` is used to make any following foreground ANSI colors bright (it has no effect on Xterm
colors). This is only relevant  to use with `|!` type tags and will be valid until the next `|n`,
`|H` or normal (upper-case) `|#` tag. This tag will never affect background colors, those have to be
set bright/normal explicitly.  Technically, `|h|!G` is identical to `|g`.
- `|H` negates the effects `|h` and returns all ANSI foreground colors (`|!` and `|` types) to
'normal' intensity. It has no effect on background and Xterm colors.

> Note: The ANSI standard does not actually support bright backgrounds like `|[r` - the standard
only supports "normal" intensity backgrounds.  To get around this Evennia instead implements these
as [Xterm256 colours](Concept/TextTags#xterm256-colours) behind the scenes. If the client does not support
Xterm256 the ANSI colors will be used instead and there will be no visible difference between using
upper- and lower-case background tags.

If you want to display an ANSI marker as output text (without having any effect), you need to escape
it by preceding its `|` with another `|`:

```
say The ||r ANSI marker changes text color to bright red.
```

This will output the raw `|r` without any color change. This can also be necessary if you are doing
ansi art that uses `|` with a letter directly following it.

Use the command

    @color ansi 

to get a list of all supported ANSI colours and the tags used to produce them.

A few additional ANSI codes are supported: 

- `|/` A line break. You cannot put the normal Python `\n` line breaks in text entered inside the
game (Evennia will filter this for security reasons). This is what you use instead: use the `|/`
marker to format text with line breaks from the game command line.
- `` This will translate into a `TAB` character. This will not always show (or show differently) to
the client since it depends on their local settings. It's often better to use multiple spaces.
- `|_` This is a space. You can usually use the normal space character, but if the space is *at the
end of the line*, Evennia will likely crop it. This tag will not be cropped but always result in a
space.
- `|*` This will invert the current text/background colours. Can be useful to mark things (but see
below).

##### Caveats of `|*`

The `|*` tag (inverse video) is an old ANSI standard and should usually not be used for more than to
mark short snippets of text. If combined with other tags it comes with a series of potentially
confusing behaviors:

* The `|*` tag will only work once in a row:, ie: after using it once it won't have an effect again
until you declare another tag. This is an example:

    ```
    Normal text, |*reversed text|*, still reversed text.
    ```

  that is, it will not reverse to normal at the second `|*`. You need to reset it manually: 

    ```
    Normal text, |*reversed text|n, normal again.
    ```  

*  The `|*` tag does not take "bright" colors into account:

    ```
    |RNormal red, |hnow brightened. |*BG is normal red.
    ```

  So `|*` only considers the 'true' foreground color, ignoring any highlighting. Think of the bright
state (`|h`) as something like like `<strong>` in HTML: it modifies the _appearance_ of a normal
foreground color to match its bright counterpart, without changing its normal color.
* Finally, after a `|*`, if the previous background was set to a dark color (via `|[`), `|!#`) will
actually change the background color instead of the foreground:

    ```
    |*reversed text |!R now BG is red.
    ```
For a detailed explanation of these caveats, see the [Understanding Color Tags](Understanding-Color-
Tags) tutorial. But most of the time you might be better off to simply avoid `|*` and mark your text
manually instead.

### Xterm256 Colours

The _Xterm256_ standard is a colour scheme that supports 256 colours for text and/or background.
While this offers many more possibilities than traditional ANSI colours, be wary that too many text
colors will be confusing to the eye. Also, not all clients support Xterm256 - these will instead see
the closest equivalent ANSI color. You can mix Xterm256 tags with ANSI tags as you please.

    |555 This is pure white text.|n This is normal text.
    |230 This is olive green text.
    |[300 This text has a dark red background.
    |005|[054 This is dark blue text on a bright cyan background.
    |=a This is a greyscale value, equal to black.
    |=m This is a greyscale value, midway between white and black.
    |=z This is a greyscale value, equal to white.
    |[=m This is a background greyscale value.

- `|###` - markup consists of three digits, each an integer from 0 to 5. The three digits describe
the amount of **r**ed, **g**reen and **b**lue (RGB) components used in the colour. So `|500` means
maximum red and none of the other colours - the result is a bright red. `|520` is red with a touch
of green - the result is orange. As opposed to ANSI colors, Xterm256 syntax does not worry about
bright/normal intensity, a brighter (lighter) color is just achieved by upping all RGB values with
the same amount.
- `|[###` - this works the same way but produces a coloured background.
- `|=#` - markup produces the xterm256 gray scale tones, where `#` is a letter from `a` (black) to
`z` (white). This offers many more nuances of gray than the normal `|###` markup (which only has
four gray tones between solid black and white (`|000`, `|111`, `|222`, `|333` and `|444`)).
- `|[=#` - this works in the same way but produces background gray scale tones.

If you have a client that supports Xterm256, you can use
    
    @color xterm256

to get a table of all the 256 colours and the codes that produce them. If the table looks broken up
into a few blocks of colors, it means Xterm256 is not supported and ANSI are used as a replacement.
You can use the `@options` command to see if xterm256 is active for you. This depends on if your
client told Evennia what it supports - if not, and you know what your client supports, you may have
to activate some features manually.

## Clickable links

Evennia supports clickable links for clients that supports it. This marks certain text so it can be
clicked by a mouse and trigger a given Evennia command. To support clickable links, Evennia requires
the webclient or an third-party telnet client with [MXP](http://www.zuggsoft.com/zmud/mxp.htm)
support (*Note: Evennia only supports clickable links, no other MXP features*).

 - `|lc` to start the link, by defining the command to execute.
 - `|lt` to continue with the text to show to the user (the link text).
 - `|le` to end the link text and the link definition.

All elements must appear in exactly this order to make a valid link. For example, 

```
"If you go |lcnorth|ltto the north|le you will find a cottage."
```

This will display as "If you go __to the north__ you will find a cottage." where clicking the link
will execute the command `north`. If the client does not support clickable links, only the link text
will be shown.

## Inline functions

> Note: Inlinefuncs are **not** activated by default. To use them you need to add
`INLINEFUNC_ENABLED=True` to your settings file.

Evennia has its own inline text formatting language, known as *inlinefuncs*. It allows the builder
to include special function calls in code. They are executed dynamically by each session that
receives them.

To add an inlinefunc, you embed it in a text string like this: 

```
"A normal string with $funcname(arg, arg, ...) embedded inside it."
```

When this string is sent to a session (with the `msg()` method), these embedded inlinefuncs will be
parsed. Their return value (which always is a string) replace their call location in the finalized
string. The interesting thing with this is that the function called will have access to which
session is seeing the string, meaning the string can end up looking different depending on who is
looking. It could of course also vary depending on other factors like game time.

Any number of comma-separated arguments can be given (or none). No keywords are supported. You can
also nest inlinefuncs by letting an argument itself also be another `$funcname(arg, arg, ...)` call
(down to any depth of nesting). Function call resolution happens as in all programming languages
inside-out, with the nested calls replacing the argument with their return strings before calling he
parent.

```
   > say  "This is $pad(a center-padded text, 30,c,-) of width 30."
   You say, "This is ---- a center-padded text----- of width 30."
```

A special case happens if wanting to use an inlinefunc argument that itself includes a comma - this
would be parsed as an argument separator. To escape commas you can either escape each comma manually
with a backslash `\,`, or you can embed the entire string in python triple-quotes `"""` or `'''` -
this will escape the entire argument, including commas and any nested inlinefunc calls within.

Only certain functions are available to use as inlinefuncs and the game developer may add their own
functions as needed.

### New inlinefuncs 

To add new inlinefuncs, edit the file `mygame/server/conf/inlinefuncs.py`.

*All globally defined functions in this module* are considered inline functions by the system. The
only exception is functions whose name starts with an underscore `_`.  An inlinefunc must be of the
following form:

```python
def funcname(*args, **kwargs):
    # ...
    return modified_text
```

where `*args` denotes all the arguments this function will accept as an `$inlinefunc`. The inline
function is expected to clean arguments and check that they are valid. If needed arguments are not
given, default values should be used. The function should always return a string (even if it's
empty). An inlinefunc should never cause a traceback regardless of the input (but it could log
errors if desired).

Note that whereas the function should accept `**kwargs`, keyword inputs are *not* usable in the call
to the inlinefunction. The `kwargs` part is instead intended for Evennia to be able to supply extra
information. Currently Evennia sends a single keyword to every inline function and that is
`session`, which holds the [serversession](Component/Sessions) this text is targeted at. Through the session
object, a lot of dynamic possibilities are opened up for your inline functions.

The `settings.INLINEFUNC_MODULES` configuration option is a list that decides which modules should
be parsed for inline function definitions. This will include `mygame/server/conf/inlinefuncs.py` but
more could be added. The list is read from left to right so if you want to overload default
functions you just have to put your custom module-paths later in the list and name your functions
the same as default ones.

Here is an example, the `crop` default inlinefunction:

```python
from evennia.utils import utils

def crop(*args, **kwargs):
    """
    Inlinefunc. Crops ingoing text to given widths.
    Args:
        text (str, optional): Text to crop.
        width (str, optional): Will be converted to an integer. Width of
            crop in characters.
        suffix (str, optional): End string to mark the fact that a part
            of the string was cropped. Defaults to `[...]`.
    Kwargs:
        session (Session): Session performing the crop.
    Example:
        `$crop(text, 50, [...])`

    """
    text, width, suffix = "", 78, "[...]"
    nargs = len(args)
    if nargs > 0:
        text = args[0]
    if nargs > 1:
        width = int(args[1]) if args[1].strip().isdigit() else 78
    if nargs > 2:
        suffix = args[2]
    return utils.crop(text, width=width, suffix=suffix)
```
Another example, making use of the Session:

```python
def charactername(*args, **kwargs):
    """
    Inserts the character name of whomever sees the string
    (so everyone will see their own name). Uses the account
    name for OOC communications. 

    Example:
        say "This means YOU, $charactername()!"   

    """
    session = kwargs["session"]
    if session.puppet:
        return kwargs["session"].puppet.key
    else:
        return session.account.key
```

Evennia itself offers the following default inline functions (mostly as examples):

* `crop(text, width, suffix)` - See above. 
* `pad(text, width, align, fillchar)` - this pads the text to `width` (default 78), alignment ("c",
"l" or "r", defaulting to "c") and fill-in character (defaults to space). Example: `$pad(40,l,-)`
* `clr(startclr, text, endclr)` - A programmatic way to enter colored text for those who don't want
to use the normal `|c` type color markers for some reason. The `color` argument is the same as the
color markers except without the actual pre-marker, so `|r` would be just `r`. If `endclr` is not
given, it defaults to resetting the color (`n`). Example: `$clr(b, A blue text)`
* `space(number)` - Inserts the given number of spaces. If no argument is given, use 4 spaces. 