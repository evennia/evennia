Adding Colour to your game
==========================

*Note that the Docs does not display colour the way it would look on the
screen.*

Evennia supports the ``ANSI`` standard for displaying text. This means
that you can put markers in your text and if the user's
client/console/display supports those markers, they will see the text in
the specified colour. Remember that whereas there is, for example, one
special marker meaning "yellow", which colour (hue) of yellow is
*actually* displayed on the user's screen depends on the settings of
their particular mud client/viewer. They could even swap around the
colours displayed if they wanted to. or turn them off altogether. Some
clients don't support colour from the onset - text games are also played
with special reading equipment by people who are blind or have otherwise
diminished eyesight. So a good rule of thumb is to use colour to enhance
your game, but don't *rely* on it to display critical information. If
you are coding the game, you can add functionality to let users disable
colours as they please, as described `here <RemovingColour.html>`_.

Adding colour to in-game text is easy. You just put in special markers
in your text that tell Evennia when a certain colour begins and when it
ends. There are two markup styles. The traditional(?) one use ``%c#`` to
mark colour:

::

     This is a %crRed text%cn This is normal text again.
     %cRThis text has red background%cn this is normal text.

``%c#`` - markup works like a switch that is on until you actively turn
it off with ``%cn`` (this returns the text to your default setting).
Capital letters mean background colour, lower-case means letter-colour.
So ``%cR`` means a red area behind your normal-colour text. If you
combine red background with red foreground text - ``%cR%cr``, you get a
solid red block with no characters visible! Similarly, ``%cR%cx`` gives
red background with black text. ``%ch`` 'hilights' your current text, so
grey becomes white, dark yellow becomes bright yellow etc.

The drawback of the ``%cs`` style has to do with how Python formats
strings - the ``%`` is used in Python to create special text formatting,
and combining that with colour codes easily leads to messy and
unreadable code. It is thus often easier to use ``{#`` style codes:

::

     This is a {rBright red text{n This is normal text again

The ``{x`` format don't include background colour, it only colours the
foreground text. The basic rule is that lower-case letter means bright
(hilighted) colour, whereas the upper-case one is for darker colour. So
``{g`` means bright green and ``{G`` means dark green. ``{n`` returns to
normal text colour. The equivalent in ``%c``-style markup is ``%cg%ch``
for bright green and ``%cg`` for dark green.

You can find a list of all the parsed ``ANSI``-colour codes in
``src/utils/ansi.py``.
