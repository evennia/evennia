import math

from tekmunkey.adaptiveDisplay import default_display_vars
from tekmunkey.devUtils import stringExtends

ansiTags = \
    [
        r"|r",
        r"|R",
        r"|[r",
        r"|[R",
        r"|g",
        r"|G",
        r"|[g",
        r"|[G",
        r"|y",
        r"|Y",
        r"|[y",
        r"|[Y",
        r"|b",
        r"|B",
        r"|[b",
        r"|[B",
        r"|m",
        r"|M",
        r"|[m",
        r"|[M",
        r"|c",
        r"|C",
        r"|[c",
        r"|[C",
        r"|w",
        r"|W",
        r"|[w",
        r"|[W",
        r"|x",
        r"|X",
        r"|[x",
        r"|[X",
        r"|X",
        r"|*",
        r"|u",
        r"|h",
    ]

def getClientScreenWidth( player ):
    """
    Returns the screen width reported by NAWS to the ServerSession by a player's client, or returns the minimum width
    value of 40, or returns the default value of 78 if the ServerSession or Client returns 0 or 1 (which would mean
    NAWS was unsupported or badly supported in the client).

    If for any reason the player object has multiple sessions attached to it, this function will return the value
    reported by the last session in their sessions collection, or it will return the default or minimum if that last
    reported value requires it.

    If for any reason the player object has no sessions attached to it, this function will always return the default
    value 78.

    :param player: {player} An instance of the player typeclass.
    :return: {int} The player's screen width, as determined by NAWS or defaults.
    """
    r = 78  # default screen width for any output
    if (player.sessions is not None) and (player.sessions.count() > 0):
        for s in player.sessions.all():
            r = 78
            s_width = s.get_client_size()[0]
            # if NAWS reported screen width is not none and is either > 78 or is at least > 40 (the mininum allowed)
            if (s_width is not None) and ((int(int(s_width)) > r) or (int(s_width) > 40)):
                r = int(s_width)
            elif (s_width is not None) and (int(s_width) > 1):
                #
                # We are told by Evennia devs that sometimes clients will return 0 so then Evennia's
                # session.get_client_size()[0] will be 1 to avoid DBZ issues... in those cases we do want to
                # default to 78.
                # In cases where clients return values > 0 or 1 but < 40 we want to default to 40 instead
                #
                r = 40
    return r

def getUserScreenWidth( player ):
    """
    Returns either the user's specified screen width as set into a persistent db attribute by the +setscreenwidth
    command or else the value of getClientScreenWidth, if there is no persistent db value to retrieve.

    :param player: {player} An instance of the player typeclass.
    :return: {int} The player's screen width, as determined by their specified/databased value or by NAWS or defaults.
    """
    r = player.db.screenWidth
    if r is None:
        r = getClientScreenWidth(player)
    return r

def wrapTextAt( text, linewidth=78 ):
    """
    Wraps the specified text at the specified line linewidth, or 78 columns by default.

    :param text: {str} The string to wrap.
    :param linewidth: {int} The output display width, in characters or columns.
    :return: {str} The specified text wrapped at the specified line width.
    """
    ansistring = ansistring = stringExtends.ansiStringClass( "" )
    if ( text is not None ) and isinstance( text, ( str,unicode ) ):
        ansistring.Text = text

    line_width = 78
    if (linewidth is not None) and isinstance( linewidth, (int, float) ):
        line_width = linewidth

    r = ""
    for line in ansistring.ansiTextWrap( line_width ):
        r += line + "\n"

    r = r[:-1]
    return r

def boxTextAt( text = "", lboxchar = " ", rboxchar = " ", paddingchar = " ", linewidth = 78 ):
    """
    Wraps the specified text and presents it inside a boxed display at the specified linewidth, or 78 columns by default.
    If lboxchar, rboxchar, and paddingchar are not specified, default characters are pulled from
    default_display_vars.py

    :param text: {str} The string to box.
    :param lboxchar: {str} The left-side boxing character.  If omitted, defaults to default_display_vars.borderChar_Left
    :param rboxchar: {str} The right-side boxing character.    If omitted, defaults to default_display_vars.borderChar_Right
    :param paddingchar: {str} The this_pad_string character that extends from the end of each wrapped line to the right-side
                              boxing character.  If omitted, defaults to default_display_vars.boxText_padding
    :param linewidth: {int} The output display width, in characters or columns.
    :return: {str} The specified text wrapped to fit inside the specified boxing characters.  The entire boxed line fits
                   inside the specified linewidth.
    """

    ansistring_text = stringExtends.ansiStringClass( "" )
    if isinstance( text, ( str, unicode ) ):
        ansistring_text.Text = text

    ansistring_lboxchar = stringExtends.ansiStringClass( default_display_vars.borderChar_Left )
    if isinstance( lboxchar, ( str, unicode ) ):
        ansistring_lboxchar.Text = lboxchar

    ansistring_rboxchar = stringExtends.ansiStringClass( default_display_vars.borderChar_Right )
    if isinstance( rboxchar, (str, unicode) ) :
        ansistring_rboxchar.Text = rboxchar

    ansistring_paddingchar = stringExtends.ansiStringClass( default_display_vars.boxText_padding )
    if isinstance( paddingchar, (str, unicode) ) :
        ansistring_paddingchar.Text = paddingchar

    line_width = 78
    if isinstance( linewidth, ( int, float ) ):
        line_width = linewidth

    r = stringExtends.ansiStringClass( '' )
    for line in ansistring_text.ansiTextWrap( line_width - ( ansistring_lboxchar.rawTextLen() + ansistring_rboxchar.rawTextLen() ) ):
        ansistring_line = stringExtends.ansiStringClass( line )

        pad_len = line_width - ( ansistring_lboxchar.rawTextLen() + ansistring_rboxchar.rawTextLen() + ansistring_line.rawTextLen() )

        this_pad_string = ( ansistring_paddingchar.ansiTextFormat() * int( math.floor( pad_len / ansistring_paddingchar.rawTextLen() ) ) )

        r.Text += ansistring_lboxchar.ansiTextFormat() + ansistring_line.ansiTextFormat() + this_pad_string
        if ( r.rawTextLen() + ansistring_rboxchar.ansiTextLen() ) < line_width:
            r.Text += ansistring_paddingchar.ansiSlice( 0, ( line_width - r.rawTextLen() ) - ansistring_rboxchar.ansiTextLen() )
        r.Text += ansistring_rboxchar.ansiTextFormat() + "\n"

    r.Text = r.Text[:-1]
    return r.Text

def centerTextAt( text = "", fillchar= " ", linewidth = 78 ):
    """
    Centers the specified text in the specified linewidth, or 78 columns by default.  If fillchar is not specified, it
    defaults to a space.

    :param text: {str} The text to center.  This may be None or an empty string to produce a horizontal header line.
    :param fillchar: {str} The character or characters to fill the line on each side of the text with.
    :param linewidth: {int} The output display width, in characters or columns.
    :return: {str} The specified text centered in the specified linewidth, filled on each side with the specified
                   fillchar string.
    """
    r_linewidth = 78
    if isinstance( linewidth, (int, float) ):
        r_linewidth = linewidth
    center_line = int( math.floor( r_linewidth / 2 ) )

    ansistring_printheader = stringExtends.ansiStringClass( "" )
    if isinstance( text, ( str, unicode ) ):
        ansistring_printheader = stringExtends.ansiStringClass( text )
    center_header = int( math.floor( ansistring_printheader.rawTextLen() / 2 ) )

    ansistring_fillchar = ansistring_fillchar = stringExtends.ansiStringClass( " " )
    if isinstance( fillchar, ( str, unicode ) ):
        ansistring_fillchar = stringExtends.ansiStringClass( fillchar )
    fillchar_repeat_count = int( math.floor( ( ( ( center_line - center_header ) - 1) / ansistring_fillchar.rawTextLen() ) ) )

    r = stringExtends.ansiStringClass( "" )
    r.Text += (ansistring_fillchar.ansiTextFormat() * fillchar_repeat_count)
    if r.rawTextLen() < ( center_line - center_header ):
        r.Text += ansistring_fillchar.ansiSlice( 0, ( ( center_line - center_header ) - r.rawTextLen() ) )
    r.Text += ansistring_printheader.ansiTextFormat()

    fillchar_repeat_count = int( math.floor( ( r_linewidth - r.rawTextLen() ) / ansistring_fillchar.rawTextLen() ) )

    r.Text += ( ansistring_fillchar.ansiTextFormat() * fillchar_repeat_count )
    if r.rawTextLen() < r_linewidth:
        r.Text += ansistring_fillchar.ansiSlice( 0, ( r_linewidth - r.rawTextLen() ) )

    return r.Text

def ljustText( text = "", fillchar= " ", fieldwidth = 78 ):
    """
    Left justifies the specified text in the specified fieldwidth, or 78 columns by default.  If fillchar is not
    specified, it defaults to a space.  If fieldseparator is not specified, it defaults to no field separator string
    (fields are separated only by fillchar padding, or by nothing if the text reaches the extend of fieldwidth).

    :param text: {str} The text to left justify.
    :param fillchar: {str} The character or characters to fill up the field with, between the end of the text and the
                           field extent.
    :return: {str} The specified text left-justified in the specified fieldwidth, with the specified fieldseparator
                   string on the left hand side.
    """
    ansistring_text = stringExtends.ansiStringClass( "" )
    if isinstance( text, ( str, unicode ) ):
        ansistring_text.Text = text

    ansistring_fillchar = stringExtends.ansiStringClass( " " )
    if isinstance( fillchar, ( str, unicode ) ):
        ansistring_fillchar.Text = fillchar

    return_fieldwidth = 78
    if isinstance( fieldwidth, ( int, float ) ):
        return_fieldwidth = int( fieldwidth )

    r = stringExtends.ansiStringClass( "" )
    if ansistring_text.rawTextLen() < return_fieldwidth:
        # need to do a little math ro figure out padding length, and apply padding
        padding_length = int( math.floor( ( return_fieldwidth - ansistring_text.rawTextLen() ) / ansistring_fillchar.rawTextLen() ) )
        r.Text = ansistring_text.ansiTextFormat() + ( ansistring_fillchar.ansiTextFormat() * padding_length )
        if r.rawTextLen() < return_fieldwidth:
            r.Text += ansistring_fillchar.ansislice( 0, ( return_fieldwidth - r.rawTextLen() ) )
    else:
        # we have to slice into the original text since it's longer than the fieldwidth
        r.Text = ansistring_text.ansislice( 0, return_fieldwidth )

    return r.Text


def rjustText( text = "", fillchar= " ", fieldwidth = 78 ):
    """
    Right justifies the specified text in the specified fieldwidth, or 78 columns by default.  If fillchar is not
    specified, it defaults to a space.  If fieldseparator is not specified, it defaults to no field separator string
    (fields are separated only by fillchar padding, or by nothing if the text reaches the extend of fieldwidth).

    :param text: {str} The text to right justify.
    :param fillchar: {str} The character or characters to fill up the field with, between the end of the text and the
                           field extent.
    :return: {str} The specified text right-justified in the specified fieldwidth, with the specified fieldseparator
                   string on the right hand side.
    """
    ansistring_text = stringExtends.ansiStringClass( "" )
    if isinstance( text, ( str, unicode ) ):
        ansistring_text.Text = text

    ansistring_fillchar = stringExtends.ansiStringClass( " " )
    if isinstance( fillchar, ( str, unicode ) ):
        ansistring_fillchar.Text = fillchar

    return_fieldwidth = 78
    if isinstance( fieldwidth, ( int, float ) ):
        return_fieldwidth = int( fieldwidth )

    r = stringExtends.ansiStringClass( "" )
    if ansistring_text.rawTextLen() < return_fieldwidth:
        # need to do a little math ro figure out padding length, and apply padding
        padding_length = int( math.floor( ( return_fieldwidth - ansistring_text.rawTextLen() ) / ansistring_fillchar.rawTextLen() ) )
        r.Text = ( ansistring_fillchar.ansiTextFormat() * padding_length )
        if ( ansistring_text.rawTextLen() + r.rawTextLen() ) < return_fieldwidth:
            r.Text += ansistring_fillchar.ansislice( 0, ( return_fieldwidth - ( r.rawTextLen( ) + ansistring_text.rawTextLen( ) )  ) )
        r.Text += ansistring_text.ansiTextFormat()
    else:
        # we have to slice into the original text since it's longer than the fieldwidth
        r.Text = ansistring_text.ansislice( 0, return_fieldwidth )

    return r.Text

def wrapTextFor(player, text):
    """
    An alias or shortcut for wraptTextAt, substituting the player's screen width (as manually specified or given by
    NAWS) for linewidth

    :param player: {player} An instance of typeclass player.
    :param text: {str} The text to wrap.
    :return: {str} The specified text wrapped at the specified line width.
    """
    return wrapTextAt( text, getUserScreenWidth( player ) )

def centerTextFor( player, text="", fillchar= " " ):
    """
    An alias or shortcut for centerTextAt, substituting the player's screen width (as manually specified or given by
    NAWS) for linewidth.

    :param player: {player} An instance of typeclass player.
    :param text: {str} The text to center.  This may be None or an empty string to produce a horizontal header line.
    :param fillchar: {str} The character or characters to fill the line on each side of the text with.
    :return: {str} The specified text centered in the specified player's screen width, filled on each side with the
                   specified fillchar string.
    """
    return centerTextAt( text, fillchar, getUserScreenWidth( player ) )

def topBorderFor( player ):
    """
    An alias or shortcut for centerTextAt, substituting the player's screen width (as manually specified or given by
    NAWS) for linewidth and substituting devault_display_vars.borderChar_Top as the fillchar automatically.

    This passes an empty text string to produce a clean Top Border line.

    :param player: {player} An instance of typeclass player.
    :return: {str} The devault_display_vars.borderChar_Top string.
    """
    return centerTextAt( "", default_display_vars.borderChar_Top, getUserScreenWidth( player ) )

def bottomBorderFor( player ):
    """
    An alias or shortcut for centerTextAt, substituting the player's screen width (as manually specified or given by
    NAWS) for linewidth and substituting devault_display_vars.borderChar_Bottom as the fillchar automatically.

    This passes an empty text string to produce a clean Bottom Border line.

    :param player: {player} An instance of typeclass player.
    :return: {str} The devault_display_vars.borderChar_Bottom string.
    """
    return centerTextFor( player, "", default_display_vars.borderChar_Bottom )

def topHeaderFor( player, headertext = "" ):
    """
    An alias or shortcut for centerTextAt, substituting the player's screen width (as manually specified or given by
    NAWS) for linewidth and substituting devault_display_vars.borderChar_Top as the fillchar automatically.

    If headertext is a string instance of length > 0, then the header text is additionally wrappered in
    default_display_vars.headerBoxChar_Left and default_display_vars.headerBoxChar_Right

    :param player: {player} An instance of typeclass player.
    :param headertext: {str} The text to create a header from.
    :return: {str} The specified text top-headerized.
    """
    pass_header = ''
    if isinstance( headertext, ( str, unicode ) ):
        ansistring_headertext = stringExtends.ansiStringClass( headertext )
        if ansistring_headertext.rawTextLen() > 0:
            pass_header = default_display_vars.headerBoxChar_Left + headertext + default_display_vars.headerBoxChar_Right

    return centerTextFor(player, pass_header, default_display_vars.borderChar_Top)

def bottomHeaderFor( player, headertext = "" ):
    """
    An alias or shortcut for centerTextAt, substituting the player's screen width (as manually specified or given by
    NAWS) for linewidth and substituting devault_display_vars.borderChar_Bottom as the fillchar automatically.

    If headertext is a string instance of length > 0, then the header text is additionally wrappered in
    default_display_vars.headerBoxChar_Left and default_display_vars.headerBoxChar_Right

    :param player: {player} An instance of typeclass player.
    :param headertext: {str} The text to create a header from.
    :return: {str} The specified text bottom-headerized.
    """
    pass_header = ''
    if isinstance( headertext, ( str, unicode ) ):
        ansistring_headertext = stringExtends.ansiStringClass( headertext )
        if ansistring_headertext.rawTextLen() > 0:
            pass_header = default_display_vars.headerBoxChar_Left + headertext + default_display_vars.headerBoxChar_Right

    return centerTextFor( player, pass_header, default_display_vars.borderChar_Bottom )

def boxTextFor(player, text = ""):
    """
    An alias or shortcut for boxTextAt, substituting the player's screen width (as manually specified or given by
    NAWS) for linewidth and passing default_display_vars.headerBoxChar_Left and default_display_vars.headerBoxChar_Right
    as the boxing characters automatically.

    :param player: {player} An instance of typeclass player.
    :param headertext: {str} The text to wrap and box.
    :return: {str} The specified text wrapped and boxed at the player's screen width.
    """
    pass_text = ""
    if isinstance( text, ( str, unicode ) ):
        pass_text = text
    return boxTextAt( pass_text, default_display_vars.borderChar_Left, default_display_vars.borderChar_Right, default_display_vars.boxText_padding, getUserScreenWidth( player ) )


