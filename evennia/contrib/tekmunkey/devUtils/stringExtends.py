import math, re

#
# regexPattern_evenniaANSI seeks ANSI and XTERM color tags as used by evennia with a negative lookbehind assertion to ignore tags that are escaped by the use of double-piping
# ie:  this matches |r but not ||r
#
# At one point Evennia may have used { instead of | for ANSI/XTERM tag starters.  These regex strings do not support that.
#
regexPattern_evenniaANSI = r"(?<!\|)(\|r|\|R|\|\[r|\|\[R|\|g|\|G|\|\[g|\|\[G|\|y|\|Y|\|\[y|\|\[Y|\|b|\|B|\|\[b|\|\[B|\|m|\|M|\|\[m|\|\[M|\|c|\|C|\|\[c|\|\[C|\|w|\|W|\|\[w|\|\[W|\|x|\|X|\|\[x|\|\[X|\|\/|\|-|\|_|\|\*|\|u|\|n|\|h|\|000|\|100|\|200|\|300|\|400|\|500|\|\[000|\|\[100|\|\[200|\|\[300|\|\[400|\|\[500|\|001|\|101|\|201|\|301|\|401|\|501|\|\[001|\|\[101|\|\[201|\|\[301|\|\[401|\|\[501|\|002|\|102|\|202|\|302|\|402|\|502|\|\[002|\|\[102|\|\[202|\|\[302|\|\[402|\|\[502|\|003|\|103|\|203|\|303|\|403|\|503|\|\[003|\|\[103|\|\[203|\|\[303|\|\[403|\|\[503|\|004|\|104|\|204|\|304|\|404|\|504|\|\[004|\|\[104|\|\[204|\|\[304|\|\[404|\|\[504|\|005|\|105|\|205|\|305|\|405|\|505|\|\[005|\|\[105|\|\[205|\|\[305|\|\[405|\|\[505|\|010|\|110|\|210|\|310|\|410|\|510|\|\[010|\|\[110|\|\[210|\|\[310|\|\[410|\|\[510|\|011|\|111|\|211|\|311|\|411|\|511|\|\[011|\|\[111|\|\[211|\|\[311|\|\[411|\|\[511|\|012|\|112|\|212|\|312|\|412|\|512|\|\[012|\|\[112|\|\[212|\|\[312|\|\[412|\|\[512|\|013|\|113|\|213|\|313|\|413|\|513|\|\[013|\|\[113|\|\[213|\|\[313|\|\[413|\|\[513|\|014|\|114|\|214|\|314|\|414|\|514|\|\[014|\|\[114|\|\[214|\|\[314|\|\[414|\|\[514|\|015|\|115|\|215|\|315|\|415|\|515|\|\[015|\|\[115|\|\[215|\|\[315|\|\[415|\|\[515|\|020|\|120|\|220|\|320|\|420|\|520|\|\[020|\|\[120|\|\[220|\|\[320|\|\[420|\|\[520|\|021|\|121|\|221|\|321|\|421|\|521|\|\[021|\|\[121|\|\[221|\|\[321|\|\[421|\|\[521|\|022|\|122|\|222|\|322|\|422|\|522|\|\[022|\|\[122|\|\[222|\|\[322|\|\[422|\|\[522|\|023|\|123|\|223|\|323|\|423|\|523|\|\[023|\|\[123|\|\[223|\|\[323|\|\[423|\|\[523|\|024|\|124|\|224|\|324|\|424|\|524|\|\[024|\|\[124|\|\[224|\|\[324|\|\[424|\|\[524|\|025|\|125|\|225|\|325|\|425|\|525|\|\[025|\|\[125|\|\[225|\|\[325|\|\[425|\|\[525|\|030|\|130|\|230|\|330|\|430|\|530|\|\[030|\|\[130|\|\[230|\|\[330|\|\[430|\|\[530|\|031|\|131|\|231|\|331|\|431|\|531|\|\[031|\|\[131|\|\[231|\|\[331|\|\[431|\|\[531|\|032|\|132|\|232|\|332|\|432|\|532|\|\[032|\|\[132|\|\[232|\|\[332|\|\[432|\|\[532|\|033|\|133|\|233|\|333|\|433|\|533|\|\[033|\|\[133|\|\[233|\|\[333|\|\[433|\|\[533|\|034|\|134|\|234|\|334|\|434|\|534|\|\[034|\|\[134|\|\[234|\|\[334|\|\[434|\|\[534|\|035|\|135|\|235|\|335|\|435|\|535|\|\[035|\|\[135|\|\[235|\|\[335|\|\[435|\|\[535|\|040|\|140|\|240|\|340|\|440|\|540|\|\[040|\|\[140|\|\[240|\|\[340|\|\[440|\|\[540|\|041|\|141|\|241|\|341|\|441|\|541|\|\[041|\|\[141|\|\[241|\|\[341|\|\[441|\|\[541|\|042|\|142|\|242|\|342|\|442|\|542|\|\[042|\|\[142|\|\[242|\|\[342|\|\[442|\|\[542|\|043|\|143|\|243|\|343|\|443|\|543|\|\[043|\|\[143|\|\[243|\|\[343|\|\[443|\|\[543|\|044|\|144|\|244|\|344|\|444|\|544|\|\[044|\|\[144|\|\[244|\|\[344|\|\[444|\|\[544|\|045|\|145|\|245|\|345|\|445|\|545|\|\[045|\|\[145|\|\[245|\|\[345|\|\[445|\|\[545|\|050|\|150|\|250|\|350|\|450|\|550|\|\[050|\|\[150|\|\[250|\|\[350|\|\[450|\|\[550|\|051|\|151|\|251|\|351|\|451|\|551|\|\[051|\|\[151|\|\[251|\|\[351|\|\[451|\|\[551|\|052|\|152|\|252|\|352|\|452|\|552|\|\[052|\|\[152|\|\[252|\|\[352|\|\[452|\|\[552|\|053|\|153|\|253|\|353|\|453|\|553|\|\[053|\|\[153|\|\[253|\|\[353|\|\[453|\|\[553|\|054|\|154|\|254|\|354|\|454|\|554|\|\[054|\|\[154|\|\[254|\|\[354|\|\[454|\|\[554|\|055|\|155|\|255|\|355|\|455|\|555|\|\[055|\|\[155|\|\[255|\|\[355|\|\[455|\|\[555|\|=a|\|=b|\|=c|\|=d|\|=e|\|=f|\|\[=a|\|\[=b|\|\[=c|\|\[=d|\|\[=e|\|\[=f|\|=g|\|=h|\|=i|\|=j|\|=k|\|=l|\|\[=g|\|\[=h|\|\[=i|\|\[=j|\|\[=k|\|\[=l|\|=m|\|=n|\|=o|\|=p|\|=q|\|=r|\|\[=m|\|\[=n|\|\[=o|\|\[=p|\|\[=q|\|\[=r|\|=s|\|=t|\|=u|\|=v|\|=w|\|=x|\|\[=s|\|\[=t|\|\[=u|\|\[=v|\|\[=w|\|\[=x|\|=y|\|=z|\|\[=y|\|\[=z)"
#
# regexPattern_lonePipe seeks lone pipes with a negative lookahead assertion to ignore pipes that are used to define ANSI tags or as escape characters for other pipes.
#
# At one point Evennia may have used { instead of | for ANSI/XTERM tag starters.  These regex strings do not support that.
#
regexPattern_lonePipe = r"\|(?!\||r|R|\[r|\[R|g|G|\[g|\[G|y|Y|\[y|\[Y|b|B|\[b|\[B|m|M|\[m|\[M|c|C|\[c|\[C|w|W|\[w|\[W|x|X|\[x|\[X|\/|-|_|\*|u|n|h|000|100|200|300|400|500|\[000|\[100|\[200|\[300|\[400|\[500|001|101|201|301|401|501|\[001|\[101|\[201|\[301|\[401|\[501|002|102|202|302|402|502|\[002|\[102|\[202|\[302|\[402|\[502|003|103|203|303|403|503|\[003|\[103|\[203|\[303|\[403|\[503|004|104|204|304|404|504|\[004|\[104|\[204|\[304|\[404|\[504|005|105|205|305|405|505|\[005|\[105|\[205|\[305|\[405|\[505|010|110|210|310|410|510|\[010|\[110|\[210|\[310|\[410|\[510|011|111|211|311|411|511|\[011|\[111|\[211|\[311|\[411|\[511|012|112|212|312|412|512|\[012|\[112|\[212|\[312|\[412|\[512|013|113|213|313|413|513|\[013|\[113|\[213|\[313|\[413|\[513|014|114|214|314|414|514|\[014|\[114|\[214|\[314|\[414|\[514|015|115|215|315|415|515|\[015|\[115|\[215|\[315|\[415|\[515|020|120|220|320|420|520|\[020|\[120|\[220|\[320|\[420|\[520|021|121|221|321|421|521|\[021|\[121|\[221|\[321|\[421|\[521|022|122|222|322|422|522|\[022|\[122|\[222|\[322|\[422|\[522|023|123|223|323|423|523|\[023|\[123|\[223|\[323|\[423|\[523|024|124|224|324|424|524|\[024|\[124|\[224|\[324|\[424|\[524|025|125|225|325|425|525|\[025|\[125|\[225|\[325|\[425|\[525|030|130|230|330|430|530|\[030|\[130|\[230|\[330|\[430|\[530|031|131|231|331|431|531|\[031|\[131|\[231|\[331|\[431|\[531|032|132|232|332|432|532|\[032|\[132|\[232|\[332|\[432|\[532|033|133|233|333|433|533|\[033|\[133|\[233|\[333|\[433|\[533|034|134|234|334|434|534|\[034|\[134|\[234|\[334|\[434|\[534|035|135|235|335|435|535|\[035|\[135|\[235|\[335|\[435|\[535|040|140|240|340|440|540|\[040|\[140|\[240|\[340|\[440|\[540|041|141|241|341|441|541|\[041|\[141|\[241|\[341|\[441|\[541|042|142|242|342|442|542|\[042|\[142|\[242|\[342|\[442|\[542|043|143|243|343|443|543|\[043|\[143|\[243|\[343|\[443|\[543|044|144|244|344|444|544|\[044|\[144|\[244|\[344|\[444|\[544|045|145|245|345|445|545|\[045|\[145|\[245|\[345|\[445|\[545|050|150|250|350|450|550|\[050|\[150|\[250|\[350|\[450|\[550|051|151|251|351|451|551|\[051|\[151|\[251|\[351|\[451|\[551|052|152|252|352|452|552|\[052|\[152|\[252|\[352|\[452|\[552|053|153|253|353|453|553|\[053|\[153|\[253|\[353|\[453|\[553|054|154|254|354|454|554|\[054|\[154|\[254|\[354|\[454|\[554|055|155|255|355|455|555|\[055|\[155|\[255|\[355|\[455|\[555|=a|=b|=c|=d|=e|=f|\[=a|\[=b|\[=c|\[=d|\[=e|\[=f|=g|=h|=i|=j|=k|=l|\[=g|\[=h|\[=i|\[=j|\[=k|\[=l|=m|=n|=o|=p|=q|=r|\[=m|\[=n|\[=o|\[=p|\[=q|\[=r|=s|=t|=u|=v|=w|=x|\[=s|\[=t|\[=u|\[=v|\[=w|\[=x|=y|=z|\[=y|\[=z)"

#
# bring in the regular regex options so consumers don't have to import regex just to use this file
#
re_IGNORECASE = 2
re_I = re_IGNORECASE
re_LOCALE = 4
re_L = re_LOCALE
re_MULTILINE = 8
re_M = re_MULTILINE
re_DOTALL= 16
re_S = re_DOTALL
re_UNICODE = 32
re_U = re_UNICODE
re_VERBOSE = 64
re_V = re_VERBOSE

strRegExFlags = \
    [
        [2, "IGNORECASE"],
        [2, "I"],
        [4, "LOCALE"],
        [4, "L"],
        [8, "MULTILINE"],
        [8, "M"],
        [16, "DOTALL"],
        [16, "S"],
        [32, "UNICODE"],
        [32, "U"],
        [64, "VERBOSE"],
        [64, "V"],
    ]

def getRegExFlagsFromStr( strflags = None ):
    """
    Given a string representation of regular expression flags, for example IGNORECASE, LOCALE, re.IGNORECASE,
    re_IGNORECASE, or any of these standard references to regular expression flags as defined by re. or defined in
    this codefile as re_, or a string of these options or'd together such as IGNORECASE|DOTALL, returns the appropriate
    value.

    :param strregexoptions: {str} A string representation of a regular expression option or options bitwise ORed
                                  together, such as IGNORECASE, IGNORECASE|DOTALL, etc.  You can specify re.IGNORECASE
                                  or re_IGNORECASE depending on which notation you're most accustomed to using in code.
    :return: {int} The appropriate regular expression flags value translated from the string value.
    """
    r = 0
    str_regex = None
    if isinstance( strflags, ( str, unicode ) ):
        str_regex = strflags.split( "|" )
        for re_flag in strRegExFlags:
            re_flag[1] = re_flag[1].lower()
            for usr_flag in str_regex:
                usr_flag = usr_flag.strip().lower()
                if usr_flag.startswith( 're.' ) or usr_flag.startswith( 're_' ):
                    usr_flag = usr_flag[3:]
                if usr_flag == re_flag[1]:
                    r |= re_flag[0]
    return r

def getIntFromStr( strint = 0 ):
    """
    Given a string representation of an integer value, for example '0' or '1', converts it to an int value.

    :param strint: {str} The string representation of an int value.
    :return: {int} The translated integer
    """
    r = 0
    if isinstance( strint, ( str, unicode ) ) or isinstance( strint, float ):
        r = int( strint )
    elif isinstance( strint, int ):
        r = strint
    return r

def getBoolFromStr( strbool = False ):
    """
    Given a string representation of a boolean value, for example 'true' or 'false', converts it to a bool value.  The
    string representation of the boolean is not case sensitive (ie it could be True or TRUE or FaLSe)

    :param strBool: {str} The string representation of a boolean value.
    :return: {bool} The translated boolean.
    """
    r = False
    if isinstance( strbool, ( str, unicode ) ):
        strbool = strbool.strip( ' ' ).lower()
        r = (strbool == 'true')
    return r

def setStringLength( text = '', textlength = 1, padcharacter = ' ', padside = 'r' ):
    """
    Pads or slices the specified text to the specified textlength, if necessary.  If the specified text is already the
    specified length, no change is made.

    :param text: {str} The text to set to length.
    :param textlength: {int} The length to set the text to.
    :param padcharacter: {str} A value that will be used to pad the string if it must be padded.  Default is space.
    :param padside: {str} A value indicating whether the string will be padded on the left 'l' or the right 'r'.
                          Default is right 'r'.
    :return: {str} The original text padded to the specified minimum length.

    This function will never raise exceptions or return an error and will always return some string value.
    """
    r = ''
    if isinstance( text, ( str, unicode ) ):
        r = text

    return_length = 1
    if isinstance( textlength, int ):
        return_length = textlength

    return_pad_string = ' '
    if isinstance( padcharacter, (str, unicode) ):
        return_pad_string = padcharacter

    return_pad_side = 'r'
    if isinstance( padside, (str, unicode) ) and (re.match( "^\s*(r|l)\s*$", padside, re.IGNORECASE ) is not None):
        return_pad_side = re.match("^\s*(r|l)\s*$", padside, re.IGNORECASE ).group( 1 ).strip( ).lower( )

    if len( r ) > return_length:
        # length of text is gtn desired length, so text must be truncated
        r = r[0:return_length]
        pass
    elif ( len( r ) < return_length ):
        # length of text is ltn desired length, so text must be padded
        # number of padding characters needed = ( total line width - length of string )
        padcnt = ( return_length - len( r ) )
        # padpend contains the padding that will eventually be appended or prepended to r
        padpend = ''
        if len( return_pad_string ) > 0:
            # number of times to repeat padcharacter = ( number of padding characters needed / length of padding string )
            padpend = ( return_pad_string * int( math.floor( padcnt / len( return_pad_string ) ) ) )
            if ( len( r ) + len( padpend ) ) < return_length:
                padpend += return_pad_string[0:return_length - ( len( r ) + len( padpend ) )]
            if return_pad_side == 'r':
                r = r + padpend
            elif return_pad_side == 'l':
                r = padpend + r

    return r

def strUnprefix( text = '', prefix = '' ):
    """
    Removes the specified prefix from the specified string, if it exists.

    :param text: {str} The text to remove a prefix from
    :param prefix: {str} The prefix to remove
    :return: {str} The original text with the prefix removed, if it was found.

    This function will never raise exceptions or return an error and will always return some string value.
    """
    r = ''
    rpre = ''
    if isinstance( text, ( str, unicode ) ):
        r = text
    if isinstance( prefix, ( str, unicode ) ):
        rpre = prefix
    if r.startswith(rpre):
        r = r[len(rpre):]
    return r

class stringMatchClass:
    """
    A class representing a string matchable against variable string data
    """

    #
    # bring in the standard regex options so consumers don't have to import regex just to use this class
    #
    re_IGNORECASE = 2
    re_I = re_IGNORECASE
    re_LOCALE = 4
    re_L = re_LOCALE
    re_MULTILINE = 8
    re_M = re_MULTILINE
    re_DOTALL = 16
    re_S = re_DOTALL
    re_UNICODE = 32
    re_U = re_UNICODE
    re_VERBOSE = 64
    re_V = re_VERBOSE

    #
    # The string to match variable data against
    #
    stringMatch = None
    #
    # A value indicating whether the stringMatch value should be treated as a regularExpression
    #
    isRegEx = None
    #
    # A value to be used as RegEx Flags if isRegEx is true.  Ignored if isRegEx is False
    #
    reFlags = None

    def __init__( self, matchvalue = None, useregex = False, regexflags = None ):
        """
        Initializes the stringMatchClass.

        :param matchvalue: The string to match variable data against
        :param useregex: A boolean  value indicating whether the stringMatch value should be treated as a
                         regularExpression
        :param regexflags: An integer value to be used as RegEx flags if useRegEx is true.  Ignored if useRegEx is
                           False.  This value can be built by ORing together values such as re.I, re.M, re.S, etc (the
                           stringMatchClass also has re_I, re_M, and etc set as static constants on itself for your
                           convenience).
        """
        if isinstance( matchvalue, (str, unicode) ):
            self.stringMatch = matchvalue
        else:
            self.stringMatch = ''
        self.isRegEx = useregex
        if useregex and isinstance( regexflags, int ):
            self.reFlags = regexflags
        else:
            self.reFlags = 0

    def isMatch( self, text = None ):
        """
        Tests the supplied variable string text against the stringMatchClass instance's stringMatch value and
        returns True if they match according to the instance's specified options.  Otherwise False.

        :param text: A variable string to test for a match against the stringMatchClass instance.
        :return: True if a match is made.  Otherwise False.

        Calling this function may throw errors if the value of of the stringMatchClass instance's stringMatch is not
        a valid regex pattern or if the reFlags are not valid regex flags.
        """
        r = False
        if self.isRegEx:
            r = re.match( self.stringMatch, text, self.reFlags )
        else:
            r = (text == self.stringMatch)

        return r

class ansiTagClass:
    """
    A specialized class for handling ANSI/XTERM tags.  Stores the tag itself, its start offset and end offset in a
    string, and contains a helper function that determines if a given offset into the string hits within the bounds of
    the tag itself.
    """
    def __init__( self, ansitag, stringstartoffset, stringendoffset ):
        if isinstance( ansitag, ( str,unicode ) ):
            self.ansiTag = ansitag
        else:
            raise ValueError( "ansiTagClass.__init__ expects a unicode string parameter for ansitag" )
        if isinstance( stringstartoffset, int ):
            self.stringStartOffset = stringstartoffset
        else:
            raise ValueError( "ansiTagClass.__init__ expects an integer parameter for stringstartoffset" )
        if isinstance( stringendoffset, int ):
            self.stringEndOffset = stringendoffset
        else:
            raise ValueError( "ansiTagClass.__init__ expects an integer parameter for stringendoffset" )

    def isOffsetInTag( self, offset ):
        """
        Returns a value indicating whether the specified offset occurs within the bounds of this particular ANSI/XTERM
        tag's span of characters.

        :param offset: {int} The offset in the string to test against.
        :return: {bool}  True if the specified offset occurs within the bounds of this ANSI/XTERM tag.  Otherwise False.
        """
        r = False
        if isinstance( offset, ( int, float ) ):
            r = ( offset >= self.stringStartOffset ) and ( offset < self.stringEndOffset )
        return r

class ansiStringClass:
    """
    A specialized class for handling strings with Evennia-style ANSI/XTERM color and formatting tags.
    """
    def __init__( self, text ):
        if isinstance( text, ( str, unicode ) ):
            self.Text = text
        else:
            raise ValueError( r"ansiStringClass.__init__ expects the text parameter to be a string value." )

    def ansiTextFormat(self):
        """
        To be called any time any operations are performed against the internal text.  Converts formatting tags (not
        ANSI/XTERM) to actual formatting.

        :return: {str} The internal text with formatting tags converted to actual formatting.
        """
        r = ""
        if isinstance( self.Text, ( str, unicode ) ):
            # replace |/ with \n
            # replace |- (tabstop) with 4 spaces
            # replace |_ with 1 space
            r = self.Text.replace( r"|/", "\n" ).replace( r"|-", r"    " ).replace( r"|_", r" " )
        return r

    def rawTextFormat(self):
        """
        To be called any time any operations are performed against the internal raw text.  Converts all formatting tags
        (not ANSI/XTERM) to actual formatting and strips ANSI/XTERM tags as well.

        :return: {str} The internal text with formatting tags converted to actual formatting.
        """
        r = ""
        if isinstance(self.Text, (str, unicode)):
            # replace |/ with \n
            # replace |- (tabstop) with 4 spaces
            # replace |_ with 1 space
            r = re.sub(regexPattern_evenniaANSI, "", self.ansiTextFormat())
        return r

    def rawTextLen( self ):
        """
        Gets the length of the internal text, excluding ANSI/XTERM tag characters.

        :return: {int} The length of the internal text, excluding ANSI/XTERM tag characters.
        """
        r = 0
        if isinstance( self.Text, ( str, unicode ) ):
            # strip other ANSI/XTERM tags from the user paragraph
            striptext = self.rawTextFormat()
            for character in striptext:
                r += 1
        return r

    def ansiTextLen( self ):
        """
        Gets the length of the internal text, including ANSI/XTERM tag characters.

        :return: {int} The length of the internal text, including ANSI/XTERM tag characters.
        """
        r = 0
        if isinstance( self.Text, ( str, unicode ) ):
            ansitext = self.ansiTextFormat()
            for character in ansitext:
                r += 1
        return r

    def catalogAnsiTags( self ):
        r = []
        ansitext = self.ansiTextFormat()
        rx = re.compile( pattern = regexPattern_evenniaANSI, flags = 0 )
        for match in rx.finditer( ansitext ):
            #
            # r_ansitags is an array
            # to that array we append an array containing the matchvalue (ie whatever ansi tag we found)
            # following that we append the match object.span value, which is another array
            # - at index 0 of the span value is the start in text index of the ansi tag, at index 1 is the end in text index of the ansi tag
            #
            r.append(ansiTagClass( ansitag = match.group( 0 ), stringstartoffset = match.span()[0], stringendoffset = match.span()[1] ) )
        return r

    def ansiStringIndex( self, rawstringindex ):
        """
        Look at the internal string as if it were a raw string, but the color codes were part of each character rather
        than individual characters themselves.  This function translates a raw string index, ie an index into the string
        without any ANSI/XTERM tags, into an index in the internal string with ANSI/XTERM tags in it, as if the
        ANSI/XTERM tags weren't there.

        :return:  {int} The string index representing a character position as if ANSI/XTERM tags didn't exist.
        """
        r_rawstringindex = 0
        if isinstance( rawstringindex, ( int, float ) ):
            r_rawstringindex = rawstringindex
        ansitext = self.ansiTextFormat()
        ansitext_len = self.ansiTextLen()
        # current_text_cursor is a cursor into the internal text as we step through it
        current_text_cursor = 0
        # counted_char_cursor is a cursor into the characters that we've actually counted, excluding ANSI/XTERM tags
        counted_char_cursor = 0
        ansi_catalog = self.catalogAnsiTags()
        while ( current_text_cursor < ansitext_len ):
            isansi = False
            character = ansitext[current_text_cursor]
            for ansi_tag in ansi_catalog:
                isansi = ansi_tag.isOffsetInTag( current_text_cursor )
                if isansi:
                    current_text_cursor = ansi_tag.stringEndOffset
                    ansi_catalog.remove( ansi_tag )
                    break
            if not isansi:
                counted_char_cursor += 1
                if ( counted_char_cursor <= rawstringindex ):
                    current_text_cursor += 1
                else:
                    break
        return current_text_cursor

    def rawSlice( self, begin, end ):
        """
        Performs a string slice operation on the internal string after stripping all ANSI/XTERM characters from it.

        Formatting characters such as |/, |-, and |_ are parsed into their actual entities such as \n for |/, 4 spaces
        for |- (tab), and single spaces for |_ so a slice operation that passes over a tab will want to consume 4
        characters.

        :param begin: {int} The index in the internal text to begin copying characters.
        :param end: {int} The index in the internal text to end copying characters.
        :return: {str} The portion of the string requested.
        """

        r_begin = 0
        if isinstance(begin, (int, float)):
            r_begin = begin
        else:
            raise ValueError( r"ansiStringClass.rawSlice expects begin parameter to be an integer value." )

        r_end = 0
        if isinstance(end, (int, float)):
            r_end = end
        else:
            raise ValueError( r"ansiStringClass.rawSlice expects end parameter to be an integer value." )

        striptext = self.rawTextFormat()
        striptext_length = self.rawTextLen()

        # normalize r_begin
        if r_begin < 0:
            # r_begin is < 0 so our start offset in the text is from the end of the internal text
            r_begin = striptext_length + r_begin

        # normalize r_end
        if r_end < 0:
            r_end = striptext_length + r_end
        elif r_end == 0:
            r_end = striptext_length

        r = striptext[r_begin:r_end]
        return r

    def ansiSlice( self, begin, end ):
        """
        Performs a string slice operation on the internal string, but instead of treating the string as a raw
        collection of characters it treats ANSI/XTERM characters as part and parcel of a character entity, so that
        a character with an ANSI/XTERM tag before it is treated as a single character although the ANSI/XTERM tag may
        in fact consume 2-3 (or more) characters in the string.

        Formatting characters such as |/, |-, and |_ are parsed into their actual entities such as \n for |/, 4 spaces
        for |- (tab), and single spaces for |_ so a slice operation that passes over a tab will want to consume 4
        characters.

        The consumer may want/need to add a |n to return to normal coloration after this slice, otherwise color tags
        from this text may affect text appended to it.

        :param begin: {int} The index in the internal text to begin copying characters.
        :param end: {int} The index in the internal text to end copying characters.
        :return: {str} The portion of the string requested.
        """

        r_begin = 0
        if isinstance(begin, (int, float)):
            r_begin = begin
        else:
            raise ValueError(r"ansiStringClass.rawSlice expects begin parameter to be an integer value.")

        r_end = 0
        if isinstance(end, (int, float)):
            r_end = end
        else:
            raise ValueError( r"ansiStringClass.rawSlice expects end parameter to be an integer value." )

        ansitext = self.ansiTextFormat()
        striptext_length = self.rawTextLen()

        # catalog the ansi tags in the internal text
        ansi_catalog = self.catalogAnsiTags()

        # normalize the begin and end values depending on ANSI/XTERM tag existence

        # normalize r_begin
        if r_begin < 0:
            # r_begin is < 0 so our start offset in the text is from the end of the internal text
            # r_begin represents the raw-string begin point requested by the caller
            r_begin = self.ansiStringIndex( striptext_length + r_begin )
        else:
            r_begin = self.ansiStringIndex( r_begin )

        # normalize r_end
        if r_end < 0:
            # r_end is < 0 so our end offset in the text is from the end of the internal text
            # r_end represents the raw-string end point requested by the caller
            r_end = self.ansiStringIndex( striptext_length + r_end )
        elif r_end == 0:
            r_end = self.ansiTextLen()
        else:
            r_end = self.ansiStringIndex( r_end )

        r = ""
        for ansi_tag in ansi_catalog:
            if ansi_tag.stringStartOffset < r_begin:
                r += ansi_tag.ansiTag
        r += ansitext[r_begin:r_end]
        # the consumer may want/need to add a |n to return to normal coloration after this slice
        return r

    def rawRegexSearch( self, regex_pattern = "", regex_flags = 0 ):
        """
        Performs a standard re.search against the internal raw text (with the ANSI/XTERM tags stripped and formatting
        tags converted to actual format characters) and returns the Match Object.  To work with the Match object
        returned, consumers should import re

        :param regex_pattern: {str} The regular expression pattern to use in the search operation.
        :param regex_flags: {int} The regular expression flags to use in the search.  These may be any combination of
                                  flag values ORed together from re.IGNORE and other standard flags.  Flags are also
                                  included such as stringExtends.re_IGNORE or stringExtends.re_I for convenience.
        :return: {MatchObject} A regular expression MatchObject instance.
        """
        striptext = self.rawTextFormat()
        r_pattern = ""
        if isinstance( regex_pattern, (str, unicode ) ):
            r_pattern = regex_pattern
        r_flags = 0
        if isinstance( regex_flags, ( int, float ) ):
            r_flags = int( regex_flags )
        r = re.search( r_pattern, striptext, r_flags )
        return r

    def ansiRegexSearch( self, regex_pattern = "", regex_flags = 0  ):
        """
        Performs a standard re.search against the internal ansi text (with the ANSI/XTERM tags ignored and formatting
        tags converted to actual format characters) and returns the Match Object.  To work with the Match object
        returned, consumers should import re

        :param regex_pattern: {str} The regular expression pattern to use in the search operation.
        :param regex_flags: {int} The regular expression flags to use in the search.  These may be any combination of
                                  flag values ORed together from re.IGNORE and other standard flags.  Flags are also
                                  included such as stringExtends.re_IGNORE or stringExtends.re_I for convenience.
        :return: {MatchObject} A regular expression MatchObject instance.
        """
        raw_match = self.rawRegexSearch( regex_pattern, regex_flags )

        return r

    def rawTextWrap( self, linelength ):
        """
        Gets the internal raw text (with non-ANSI/XTERM formatting tags converted to actual formatting, and all
        ANSI/XTERM tags removed) wrapped to the specified linelength, as an array of strings at the specified length.

        By default this will respect user-defined \n marks in the original text, and also automatically breaks at spaces
        or dashes.

        Long words will ONLY be broken up if the word itself is actually longer than the specified linelength, for
        example if the word is 12 characters and the line length is 10, the word will be broken.  Otherwise words
        will never be broken.

        :param linelength: {int} The length of an output line, in characters.
        :return: {array} The lines of the original text, broken into sections linelength characters long.
        """
        r = []
        r_linelength = 78
        if isinstance( linelength, ( int, float ) ):
            r_linelength = linelength

        striptext = self.rawTextFormat()
        striptext_length = self.rawTextLen()

        # last_line_ending tracks the index into striptext where we last wrapped the line
        # this is our slice-start-index
        last_line_ending = 0
        # current_text_cursor tracks the text cursor as we iterate through the characters in striptext
        # this our slice-end-index
        current_text_cursor = 0
        #current_line_length tracks the length of the current line as we iterate through the whole mess
        current_line_length = 0
        # last_break_poss tracks the last whitespace or - character located in the text, so if we don't find a break
        # character exactly at linelength we can break cleanly at that point without having to backsearch
        last_break_poss = -1

        if striptext_length > r_linelength:
            while current_text_cursor < striptext_length:
                character = striptext[ current_text_cursor ]
                if ( character == "\n" ):
                    # character is a newline so we're going to respect user-defined paragraphs
                    # we don't need to include the \n in the text itself
                    r.append(striptext[last_line_ending:current_text_cursor])
                    last_line_ending = current_text_cursor + 1
                    last_break_poss = last_line_ending
                    current_line_length = 0

                if ( ( character == " " ) or ( character == "-" ) ) and ( current_line_length == r_linelength ):
                    # we are at a line ending character and a perfect line length
                    if character == " ":
                        # if character is a space we want to omit it from the line
                        r.append( striptext[ last_line_ending:current_text_cursor ] )
                    else:
                        # if character is a dash we want to include it in the line
                        r.append( striptext[ last_line_ending:current_text_cursor + 1 ] )
                    last_line_ending = current_text_cursor + 1
                    last_break_poss = last_line_ending
                    current_line_length = 0
                elif ( current_line_length == r_linelength ):
                    # we are not at a line ending character but we've reached the line length
                    if character == " ":
                        # if character is a space we want to omit it from the line
                        r.append( striptext[ last_line_ending:last_break_poss ] )
                    else:
                        # if character is a dash we want to include it in the line
                        r.append( striptext[ last_line_ending:last_break_poss + 1 ] )
                    last_line_ending = last_break_poss + 1
                    last_break_poss = last_line_ending
                    current_text_cursor = last_line_ending
                    current_line_length = 0
                elif ( ( character == " " ) or ( character == "-" ) ):
                    # we found a possible line ending but are not yet at the line length
                    last_break_poss = current_text_cursor

                current_text_cursor += 1
                current_line_length += 1

            # append any remaining chars
            if ( current_text_cursor - last_line_ending ) > 0:
                # we iterated past the last line ending but didn't do any more appends, so there is string remaining
                r.append( striptext[ last_line_ending:current_text_cursor ] )
        else:
            r.append( striptext )

        return r

    def ansiTextWrap( self, linelength ):
        """
        Gets the internal raw text (with non-ANSI/XTERM formatting tags converted to actual formatting, and all
        ANSI/XTERM tags removed) wrapped to the specified linelength, as an array of strings at the specified length.

        By default this will respect user-defined \n marks in the original text, and also automatically breaks at spaces
        or dashes.

        Long words will ONLY be broken up if the word itself is actually longer than the specified linelength, for
        example if the word is 12 characters and the line length is 10, the word will be broken.  Otherwise words
        will never be broken.

        :param linelength: {int} The length of an output line, in characters.
        :return: {array} The lines of the original text, broken into sections linelength characters long.
        """
        r = []
        r_linelength = 78
        if isinstance( linelength, ( int, float ) ):
            r_linelength = linelength

        ansitext = self.ansiTextFormat()
        # we're working against striptext length, not ansitext length
        ansitext_length = self.ansiTextLen()

        # last_line_ending tracks the index into ansitext where we last wrapped the line
        # this is our slice-start-index
        last_line_ending = 0
        # current_text_cursor tracks the text cursor as we iterate through the characters in ansitext
        # this our slice-end-index
        current_text_cursor = 0
        #current_line_length tracks the length of the current line as we iterate through the whole mess
        current_line_length = 0
        # last_break_poss tracks the last whitespace or - character located in the text, so if we don't find a break
        # character exactly at linelength we can break cleanly at that point without having to backsearch
        last_break_poss = -1
        last_break_char = ""
        ansi_catalog = self.catalogAnsiTags()

        if ansitext_length > r_linelength:
            while current_text_cursor < ansitext_length:
                character = ansitext[ current_text_cursor ]
                if ( character == "\n" ):
                    # character is a newline so we're going to respect user-defined paragraphs
                    # we don't need to include the \n in the text itself
                    r.append( ansitext[ last_line_ending:current_text_cursor ] )
                    last_line_ending = current_text_cursor + 1
                    last_break_poss = last_line_ending
                    current_line_length = 0

                if ( ( character == " " ) or ( character == "-" ) ) and ( current_line_length == r_linelength ):
                    # we are at a line ending character and a perfect line length
                    if character == " ":
                        # if character is a space we want to omit it from the line
                        r.append( ansitext[ last_line_ending:current_text_cursor ] )
                    else:
                        # if character is a dash we want to include it in the line
                        r.append( ansitext[ last_line_ending:current_text_cursor + 1 ] )
                    last_line_ending = current_text_cursor + 1
                    last_break_poss = last_line_ending
                    last_break_char = character
                    current_line_length = 0
                elif ( current_line_length == r_linelength ):
                    # we are not at a line ending character but we've reached the line length
                    if last_break_char == " ":
                        # if character is a space we want to omit it from the line
                        r.append( ansitext[ last_line_ending:last_break_poss ] )
                    else:
                        # if character is a dash we want to include it in the line
                        r.append( ansitext[ last_line_ending:last_break_poss + 1 ] )
                    last_line_ending = last_break_poss + 1
                    last_break_poss = last_line_ending
                    current_text_cursor = last_line_ending
                    current_line_length = 0
                elif ( ( character == " " ) or ( character == "-" ) ):
                    # we found a possible line ending but are not yet at the line length
                    last_break_poss = current_text_cursor
                    last_break_char = character
                elif ( character == r"|" ):
                    for ansi_tag in ansi_catalog:
                        if ansi_tag.stringStartOffset == current_text_cursor:
                            # we found an ansi tag so we can skip over this item entirely
                            # we DO NOT increment line length
                            # we DO increment cursor position
                            # subtract 1 from the span's value because we add 1 below, this places the cursor at the
                            # end of the ANSI tag itself rather than at the beginning of the following character
                            current_text_cursor = ansi_tag.stringEndOffset - 1
                            # remove the ansi tag from the collection so we don't iterate it again
                            ansi_catalog.remove( ansi_tag )
                            break
                        elif ansi_tag.stringStartOffset > current_text_cursor:
                            # the next ansi tag's start offset is past our current cursor location, so we can quit
                            # looking
                            break
                current_text_cursor += 1
                current_line_length += 1

            # append any remaining chars
            if ( current_text_cursor - last_line_ending ) > 0:
                # we iterated past the last line ending but didn't do any more appends, so there is string remaining
                r.append( ansitext[ last_line_ending:current_text_cursor ] )
        else:
            r.append( ansitext )

        return r


# an in-game test string:
# for irc
# @py from tekmunkey.devUtils import stringExtends; ansistring = stringExtends.ansiStringClass("|h|rmy test|ying string|n");self.msg(ansistring.ansiSlice(3,10))
# for evennia
# @py from tekmunkey.devUtils import stringExtends; ansistring = stringExtends.ansiStringClass("||h||rmy test||ying string||n");self.msg(ansistring.ansiSlice(3,10))