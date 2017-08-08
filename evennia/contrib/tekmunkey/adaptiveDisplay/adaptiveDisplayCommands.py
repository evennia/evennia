import random
from evennia import default_cmds
from tekmunkey.devUtils import stringExtends
from tekmunkey.adaptiveDisplay import adaptiveDisplayFunctions


class cmdTestAnsiSlice( default_cmds.MuxCommand ):
    """
    +testAnsiSlice

    Demonstrates the stringExtends.ansiSlice function based on your input.  Requires start index as its first parameter,
    end index as its second parameter, and text as its third parameter.  These parameters are not named.

    Note that Start index and End index refer to character indices in the string itself, ignoring the presence of any
    ANSI/XTERM tags.  ANSI/XTERM tags are metadata which describe the characters in the string, they are not part of
    the string itself.

    ie:
    +testAnsiSlice 3 10 ||h||rmy tes||yting string!||n
    +testAnsiSlice -15 -8 ||h||rmy t||ces||yti||gng string!||n
    ( yes, both of the above equate to the same indices - you can change them up yourself in further tests )
    """
    key = "+testAnsiSlice"

    def parse(self):
        if ( self.args is None ) or ( len( self.args.strip( r" " ) ) == 0 ):
            # op code indicating no arguments provided
            self.opCode = -255
        else:
            stripargs = self.args.strip( r" " )
            # specifying 2 for split count actually results in 3 array elements O.o
            args = stripargs.split( r" ", 2 )
            self.opCode = 0
            self.sliceStartIndex = stringExtends.getIntFromStr( args[0] )
            self.sliceStopIndex = stringExtends.getIntFromStr( args[1] )
            self.sliceAnsiString = args[2]

    def func(self):
        if self.opCode == 0:
            ansistring_test = stringExtends.ansiStringClass( self.sliceAnsiString )
            self.caller.msg( ansistring_test.ansiSlice( self.sliceStartIndex, self.sliceStopIndex ) )
        elif self.opCode == -255:
            self.caller.msg( r"You must supply a start index, an end index, and a string to test against." )


#
# Allows users to manually override NAWS.  Has no effect on their client's actual columns width - they still have to set that if they can.  This only determines how much text the MU spits out on one line.
#
class cmdSetScreenWidth( default_cmds.MuxCommand ):
    """
    +setScreenWidth <value>
        
    Sets your screen width as seen by the game, in terms of the width of
    borders and pre-wrapped text that will be sent to your client.  This game
    may make use of ASCII art and other fixed-width character-based images, so
    the minimum value (above 0) is 40 columns - you may not and must not
    attempt to set your screen width lower than that.

    You may set your screen width to 0, which will return you to the
    default that is assigned by NAWS.

    If you type +setScreenWidth with no argument at all, it will tell you what your screen width is currently set to.
    
    * This allows users to manually override NAWS.  This has no effect on
      a MU client's actual columns width - that still has to be set if it can
      be.  This only determines how much text the MU spits out on one line.
    """
    
    key = "+setScreenWidth"

    def parse( self ):
        self.trgVal = 78
        if ( self.args is None ) or ( self.args == '' ):
            # op code indicating user needs current value displayed
            self.trgVal = -100
        else:
            try:
                self.trgVal = int( self.args.strip( ' ' ) )
            except:
                # error code indicating string value supplied
                self.trgVal = -200
            if self.trgVal == 0:
                self.trgVal = adaptiveDisplayFunctions.getClientScreenWidth( self.player )

    def func(self):
        out_str = ''
        if self.trgVal == -100:
            out_str = "Your screen width is currently set to:  " + str( adaptiveDisplayFunctions.getUserScreenWidth( self.player ) )
        elif self.trgVal == -200:
            out_str = "Value supplied to +setScreenWidth must be a number"
        elif not self.trgVal >= 40:
            out_str = "Value supplied to +setScreenWidth must be 40 or greater"
        else:
            self.player.db.screenWidth = self.trgVal
            out_str = "Your screen width has been set to " + str( self.trgVal )
        self.player.msg( out_str )





#
# Spits out display function tests.  Signal test pattern anyone?  Anyone?  Beuller?  Anyone?
#
class cmdTestDisplay(default_cmds.MuxCommand):
    """
    +testDisplay <name>

    Runs several display function tests down your screen, testing Top and Bottom borders and headers, centering, wrapping, and boxing.
    """
    key = "+testDisplay"

    def parse(self):
        # argstype = str( type( self.args ) )
        # self.caller.msg( "type( self.args ):  " + argstype )
        self.trgPlayer = None
        if (self.args is None) or (self.args == ''):
            self.trgPlayer = self.player
        else:
            # self.trgPlayer = self.caller.search( self.args )
            # self.caller.msg("self.caller.search( self.args ):  " + self.args)
            srchrslt = self.caller.search(self.args.strip(' '), quiet=True, global_search=True)
            if (srchrslt is None) or (len(srchrslt) < 1):
                #
                # Just let this fall through
                #
                pass
            else:
                #
                # We found 1 or more matches - return the first in the list and let the sucker at the keyboard refine their search if they want somebody else
                #
                self.trgPlayer = srchrslt[0].player

    def func(self):
        if self.trgPlayer is not None:
            self.caller.msg( adaptiveDisplayFunctions.topBorderFor( self.trgPlayer ) )
            self.caller.msg( adaptiveDisplayFunctions.bottomBorderFor( self.trgPlayer ) )
            self.caller.msg( adaptiveDisplayFunctions.topHeaderFor( self.trgPlayer, "Top Header" ) )
            self.caller.msg( adaptiveDisplayFunctions.bottomHeaderFor( self.trgPlayer, "Bottom Footer" ) )
            self.caller.msg(adaptiveDisplayFunctions.centerTextFor(self.trgPlayer, "Center"))
            self.caller.msg(adaptiveDisplayFunctions.centerTextFor(self.trgPlayer, "Center", "-"))
            self.caller.msg(adaptiveDisplayFunctions.centerTextFor(self.trgPlayer, "Center", "=,"))
            self.caller.msg(adaptiveDisplayFunctions.centerTextFor(self.trgPlayer, "Center", "-=-"))
            testStr = "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium totam rem aperiam eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo. Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt neque porro quisquam est qui dolorem ipsum quia dolor sit amet consectetur adipisci[ng] velit sed quia non numquam [do] eius modi tempora inci[di]dunt ut labore et dolore magnam aliquam quaerat voluptatem. Ut enim ad minima veniam quis nostrum exercitationem ullam corporis suscipit laboriosam nisi ut aliquid ex ea commodi consequatur? Quis autem vel eum iure reprehenderit qui in ea voluptate velit esse quam nihil molestiae consequatur vel illum qui dolorem eum fugiat quo voluptas nulla pariatur?|/|/At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi sint obcaecati cupiditate non provident similique sunt in culpa qui officia deserunt mollitia animi id est laborum et dolorum fuga. Et harum quidem rerum facilis est et expedita distinctio. Nam libero tempore cum soluta nobis est eligendi optio cumque nihil impedit quo minus id quod maxime placeat facere possimus omnis voluptas assumenda est omnis dolor repellendus. Temporibus autem quibusdam et aut officiis debitis aut rerum necessitatibus saepe eveniet ut et voluptates repudiandae sint et molestiae non recusandae. Itaque earum rerum hic tenetur a sapiente delectus ut aut reiciendis voluptatibus maiores alias consequatur aut perferendis doloribus asperiores repellat."
            self.caller.msg(adaptiveDisplayFunctions.wrapTextFor(self.trgPlayer, testStr))
            headerString = "[ Box Display Header ]"
            self.caller.msg(adaptiveDisplayFunctions.centerTextFor(self.trgPlayer, headerString, "-"))
            self.caller.msg(adaptiveDisplayFunctions.boxTextFor(self.trgPlayer, testStr))
            footerString = adaptiveDisplayFunctions.centerTextFor(self.trgPlayer, None, "=")
            self.caller.msg(footerString)

            rand1 = random.randrange(0,5)
            rand2 = random.randrange(5,10)
            rand3 = random.randrange(10,15)
            ansiTestStr = random.choice( adaptiveDisplayFunctions.ansiTags ) + headerString[:rand1] +  random.choice( adaptiveDisplayFunctions.ansiTags ) + headerString[rand1:rand2] + random.choice( adaptiveDisplayFunctions.ansiTags ) + headerString[rand2:rand3] +  random.choice( adaptiveDisplayFunctions.ansiTags ) + headerString[rand3:] + "|n"
            self.caller.msg(adaptiveDisplayFunctions.centerTextFor(self.trgPlayer, ansiTestStr, "-"))
            rand1 = random.randrange(0, 800)
            rand2 = random.randrange(800, 1200)
            rand3 = random.randrange(1200, 1800)
            ansiTestStr = random.choice( adaptiveDisplayFunctions.ansiTags ) + testStr[:rand1] +  random.choice( adaptiveDisplayFunctions.ansiTags ) + testStr[rand1:rand2] + random.choice( adaptiveDisplayFunctions.ansiTags ) + testStr[rand2:rand3] +  random.choice( adaptiveDisplayFunctions.ansiTags ) + testStr[rand3:] + "|n"
            self.caller.msg(adaptiveDisplayFunctions.boxTextFor(self.trgPlayer, ansiTestStr))
            rand1 = random.randrange(0, 5)
            rand2 = random.randrange(5, 10)
            rand3 = random.randrange(10, 15)
            ansiTestStr = random.choice( adaptiveDisplayFunctions.ansiTags ) + footerString[:rand1] +  random.choice( adaptiveDisplayFunctions.ansiTags ) + footerString[rand1:rand2] + random.choice( adaptiveDisplayFunctions.ansiTags ) + footerString[rand2:rand3] +  random.choice( adaptiveDisplayFunctions.ansiTags ) + footerString[rand3:] + "|n"
            self.caller.msg(ansiTestStr)
        else:
            self.caller.msg("Could not locate player:  " + self.args)