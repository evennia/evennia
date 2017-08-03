import getpass
import os

import evennia
from evennia import default_cmds

from tekmunkey.devUtils import stringExtends
from tekmunkey.devUtils.findCode import findCodeFunctions


class cmdFindCode( default_cmds.MuxCommand ):
    """
    +findcode dir=directoryFilter class=classFilter def=functionFilter
        Catalogs all files, classes, and functions in the specified library if they match the specified class and def
        filters.

    +findcode dir=all or evennia or myGame
        Catalogs all code files, classes, and functions in the specified directory.  If 'all' then both the Evennia
        library and the game library are included.  If 'evennia' then only the evennia library is searched.  If
        'mygame' then only the game library is searched.

        Any abbreviation may be used, such as 'a' for all, 'e' for evennia, or 'm' for mygame.

        If the dir option is omitted, then both directories are included (evennia and the game library).

    +findcode class=matchValue:className,useRegEx:False,regExFlags:None
        Catalogs all classes and their contained functions in the Evennia library and in the game library matching the
        specified class filter settings.

        If the class option is omitted, then all classes are included (none are filtered).

    +findcode def=matchValue:defName,useRegEx:False,regExFlags:None
        Catalogs all functions whether they are contained in classes or not, in the Evennia library and in the game
        library, matching the specified function filter settings.

        If the def option is omitted, then all functions are included (none are filtered).

    * A class or def filter is a stringExtends.stringMatchClass definition.
    * matchValue is the only required value.  This is of the form matchvalue:value
    * useRegEx is only required if you want the value of matchValue to be treated as a regular expression match.  This
      is a non-case-sensitive string representation of a boolean value.  If omitted, the default is false.
    * regExFlags is only required if you wish to use regular expression flags with regular expressions.  Even if set,
      this value is ignored unless useRegEx is True.  You may specify regExFlags as their name only (such as
      IGNORECASE or I, DOTALL or S) or you may specify them as you are accustomed to such as re.IGNORECASE, re.I, or
      re_IGNORECASE, RE_I, etc.  Flags may be ORed together as per normal in string format, such as re.I||re.S||re.M and
      etc.  All of the regex flags recognized by Python's re engine in Python 2.7 are supported.
    * When writing a class or def filter, filter parameter names are separated from filter parameter values by a :
      character, while individual filter parameters are separated by the , character.  So
      matchValue:value,useRegEx:value,regExFlags:value
    * Avoid spaces except between individual arguments to this command.  Spaces separate command parameters.
    """

    key = "+findCode"
    locks = "cmd:perm(Builders)"

    def parse( self ):
        self.evBaseDir = os.path.dirname( evennia.__file__  )
        self.evGameDir = evennia.settings.GAME_DIR

        self.classNameFilter = None
        self.defNameFilter = None
        self.trgDirs = None # [ self.evBaseDir, self.evGameDir ]
        self.orig_args = self.args.strip( ' ' )
        args = self.orig_args.split( ' ' )
        for a in args:
            a = a.split( '=' )
            if ( len( a ) > 1 ):
                arg_nam = a[0].strip( ' ' ).lower()

                #
                # calling isValidCodeType with robustconsumer = True makes it return an integer instead of raising an
                # exception on failure
                #
                iscodetype = findCodeFunctions.isValidCodeType( codetype = arg_nam, robustconsumer = True )
                if ( not( isinstance( iscodetype, int ) ) ):
                    #
                    # if iscodetype is not an integer then the arg_nam is a code type (meaning a class or def filter)
                    #
                    arg_nam = iscodetype

                arg_val = a[1].strip( ' ' )

                if ( arg_nam == 'dir' ):
                    #
                    # user could put in dir=a/al/all or dir=e/ev/eve/evennia or dir=m/my/mygam/mygame etc
                    #
                    argmatch = stringExtends.stringMatchClass( matchvalue = "^" + arg_val + ".*$", useregex = True, regexflags = stringExtends.re_IGNORECASE )
                    if argmatch.isRawMatch( "all" ):
                        self.trgDirs = [ self.evBaseDir, self.evGameDir ]
                        pass
                    elif argmatch.isRawMatch( "evennia" ):
                        self.trgDirs = [ self.evBaseDir ]
                        pass
                    elif argmatch.isRawMatch( "mygame" ):
                        self.trgDirs = [ self.evGameDir ]
                        pass
                elif ( arg_nam == 'class' ):
                    self.classNameFilter = stringExtends.stringMatchClass( )
                    #
                    # class name filter parameters must be input using comma delimited values
                    #
                    arg_val = arg_val.split( "," )
                    for av in arg_val:
                        av = av.split(":")
                        if av[0].lower() == "matchvalue":
                            self.classNameFilter.stringMatch = av[1 ]
                        elif av[0].lower() == "useregex":
                            self.classNameFilter.isRegEx = stringExtends.getBoolFromStr( av[1 ] )
                        elif av[0].lower() == "regexflags":
                            self.classNameFilter.reFlags = stringExtends.getRegExFlagsFromStr( av[1 ] )
                elif ( arg_nam == 'def' ):
                    self.defNameFilter = stringExtends.stringMatchClass( )
                    #
                    # def name filter parameters must be input using comma delimited values
                    #
                    arg_val = arg_val.split( "," )
                    for av in arg_val:
                        av = av.split( ":" )
                        if av[0].lower() == "matchvalue":
                            self.defNameFilter.stringMatch = av[1 ]
                        elif av[0].lower() == "useregex":
                            self.defNameFilter.isRegEx = stringExtends.getBoolFromStr( av[1 ] )
                        elif av[0].lower() == "regexflags":
                            self.defNameFilter.reFlags = stringExtends.getRegExFlagsFromStr( av[1 ] )

        #
        # if all args processed and trgDirs is still empty, default to ALL
        #
        if self.trgDirs is None:
            self.trgDirs = [ self.evBaseDir, self.evGameDir ]
        self.caller.msg("\nCataloging by:  " + self.orig_args)

    def func( self ):
        catalog_found = 0
        while len( self.trgDirs ) > 0:
            thisdir = self.trgDirs.pop()
            for fsobj in os.listdir(thisdir):
                b_anyfile = ( ( fsobj != '__init__.py' ) and ( os.path.splitext( fsobj )[1] == '.py' ) )

                os_path_sep = findCodeFunctions.getPathSep( False )
                if not thisdir.endswith( os_path_sep ):
                    thisdir += os_path_sep
                fspath = thisdir + fsobj


                if os.path.isdir( fspath ):
                    self.trgDirs.append(fspath)
                elif os.path.isfile( fspath ) and ( b_anyfile ):
                    filereport = findCodeFunctions.codeFileClass( name=fspath )
                    filereport.classNameFilter = self.classNameFilter
                    filereport.defNameFilter = self.defNameFilter
                    filereport.catalogFile()
                    filereport.clearEmptyBlocks()

                    if len( filereport.codeBlocks ) > 0:
                        catalog_found += filereport.countCodeBlocks()
                        #
                        # add/edit/remove string items to custom_unprefix for any path prefixes you want removed from
                        # paths that are output by filereport.getString, such as /home or /home/myusername, etc.
                        #
                        custom_unprefix = \
                        [
                            "/home",
                            "/" + getpass.getuser(),
                        ]
                        self.caller.msg( filereport.getString( custom_unprefix ) + '\n' )
        self.caller.msg( "Catalogued " + str( catalog_found ) + " codeblocks matching: " + self.orig_args + "\n")
