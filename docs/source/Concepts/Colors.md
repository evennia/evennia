# Colors

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
colours as they please, as described [here](../Howtos/Manually-Configuring-Color.md).

Evennia supports two color standards: 

- `ANSI` - 16 foreground colors + 8  background colors. Widely supported. 
- `Xterm256` - 128 RGB colors, 32 greyscales. Not always supported in old clients.

To see which colours your client support, use the default `color` command. This will list all
available colours for ANSI and Xterm256 along with the codes you use for them. The 
central ansi/xterm256 parser is located in  [evennia/utils/ansi.py](evennia.utils.ansi).

## ANSI colours

Evennia supports the `ANSI` standard for text. This is by far the most supported MUD-color standard, available in all but the most ancient mud clients. 

To colour your text you put special tags in it. Evennia will parse these and convert them to the
correct markup for the client used. If the user's client/console/display supports ANSI colour, they
will see the text in the specified colour, otherwise the tags will be stripped (uncolored text).

For the webclient, Evennia will translate the codes to CSS tags.

| Tag | Effect | 
| ----  | ----- | 
| \|n | end all color formatting, including background colors. |
|\|r | bright red foreground color |
|\|g | bright green foreground color |
|\|y | bright yellow foreground color |
|\|b | bright blue foreground color |
|\|m | bright magentaforeground color |
|\|c | bright cyan foreground color |
|\|w | bright white foreground color |
|\|x | bright black (dark grey) foreground color |
|\|R | normal red foreground color |
|\|G | normal green foreground color |
|\|Y | normal yellow foreground color |
|\|B | normal blue foreground color |
|\|M | normal magentaforeground color |
|\|C | normal cyan foreground color |
|\|W | normal white (light grey) foreground color |
|\|X | normal black foreground color |
| \|\[# | background colours, e.g. \|\[c for bright cyan background and \|\[C a normal cyan background. |
| \|!# | foreground color that inherits brightness from previous tags. Always uppcase, like \|!R |
| \|h | make any following foreground ANSI colors bright (no effect on Xterm colors). Use with \|!#. Technically, \|h\|G == \|g. |
| \|H  | negates the effects of \|h, return foreground to normal (no effect on Xterm colors) | 
| \|/ | line break. Use instead of Python \\n when adding strings from in-game. |
| \|- | tab character when adding strings in-game. Can vay per client, so usually better with spaces. |
| \|_ | a space. Only needed to avoid auto-cropping at the end of a in-game input | 
| \|* | invert the current text/background colours, like a marker. See note below. |  

Here is an example of the tags in action:

     |rThis text is bright red.|n This is normal text.
     |RThis is a dark red text.|n This is normal text.
     |[rThis text has red background.|n This is normal text.
     |b|[yThis is bright blue text on yellow background.|n This is normal text.

Note: The ANSI standard does not actually support bright backgrounds like `|[r` - the standard
only supports "normal" intensity backgrounds.  To get around this Evennia implements these as [Xterm256 colours](#xterm256-colours) behind the scenes. If the client does not support
Xterm256 the ANSI colors will be used instead and there will be no visible difference between using upper- and lower-case background tags.

If you want to display an ANSI marker as output text (without having any effect), you need to escape it by preceding its `|` with another `|`:

```
say The ||r ANSI marker changes text color to bright red.
```

This will output the raw `|r` without any color change. This can also be necessary if you are doing
ansi art that uses `|` with a letter directly following it.

Use the command

    color ansi

to get a list of all supported ANSI colours and the tags used to produce them.

A few additional ANSI codes are supported:


### Caveats of `|*`

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

The _Xterm256_ standard is a colour scheme that supports 256 colours for text and/or background. It can be combined freely with ANSI colors (above), but some ANSI tags don't affect Xterm256 tags. 

While this offers many more possibilities than traditional ANSI colours, be wary that too many text
colors will be confusing to the eye. Also, not all clients support Xterm256 - these will instead see
the closest equivalent ANSI color. You can mix Xterm256 tags with ANSI tags as you please.

| Tag | Effect | 
| ---- | ---- | 
| \|### | foreground RGB (red/green/blue), each from 0 to 5. | 
| \|\[### | background RGB | 
| \|=# | a-z foreground greyscale, where `a` is black and `z` is white. | 
| \|\[=#| a-z background greyscale

Some examples: 

| Tag | Effect | 
| ---- | ---- | 
| \|500 | bright red | 
| \|050 | bright green | 
| \|005 | bright blue | 
| \|520 | red + a little green = orange | 
|\|555 |  pure white foreground | 
|\|230 | olive green foreground | 
|\|\[300 | text with a dark red background | 
|\|005\|\[054 | dark blue text on a bright cyan background |
|\|=a | greyscale foreground, equal to black |
| \|=m | greyscale foreground, midway between white and black.
| \|=z | greyscale foreground, equal to white | 
| \|\[=m | greyscale background | 

Xterm256 don't use bright/normal intensity like ANSI does; intensity is just varied by increasing/decreasing  all RGB values by the same amount.

If you have a client that supports Xterm256, you can use

    color xterm256

to get a table of all the 256 colours and the codes that produce them. If the table looks broken up
into a few blocks of colors, it means Xterm256 is not supported and ANSI are used as a replacement. You can use the `options` command to see if xterm256 is active for you. This depends on if your client told Evennia what it supports - if not, and you know what your client supports, you may have to activate some features manually.

## More reading

There is an [Understanding Color Tags](../Howtos/Understanding-Color-Tags.md) tutorial which expands on the use of ANSI color tags and the pitfalls of mixing ANSI and Xterms256 color tags in the same context.