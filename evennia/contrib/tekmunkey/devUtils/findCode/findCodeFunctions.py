import os
import re

from tekmunkey.devUtils import stringExtends

#
# Catches class or function declarations only at the topmost, unindented level
#   \1 is any spacing or indentation at the front of the line
#   \2 is class or def (identifying class or function declaration)
#   \3 is class or function name
#   \4 is anything inside parentheses, including parentheses, if they exist
#   ie:  class MyClass(baseClass):
#   \1 = "  "
#   \2 = class
#   \3 = MyClass
#   \4 = (baseClass)
#
regExPattern_CodeDeclaration = "^(\s*)(class|def)+\s+([A-Z|a-z|0-9|_]+)?.*$"

#
# If you're developing/debugging on Windows but hosting your development environment on Linux, this value MUST be True.
# Otherwise the \ (Windows path separator) will be passed to Linux, which expects / for path seps, so nothing will work.
#
# You MUST remember to set this to False no matter what your hosting environment is for Production, and you can set this
# to False if you're developing/debugging and hosting on the same platform, regardless of what that platform is, too.
#
forceLinuxPathSeparators = True

def getPathSep( forceLinuxPathSep = False ):
    """
    Anyone developing/debugging on Windows but hosting on Linux must pass forceLinuxPathSep as True or else Windows
    path separators (the \ char) will be passed along into the Linux environment at debug time and nothing will work,
    since Linux expects the / char.

    Anyone developing/debugging on the same platform they're hosting on (doesn't matter if it's Linux or Windows) can
    call this without arguments or call with forcelinuxpathsep = False.

    :param forcePinuxPathSep: {bool} Indicates whether / should be returned regardless of runtime environment.
    :return: {str} A path separator.  Returns os.pathsep unless forceLinuxPathSep is True, then returns / always.

    This function will never raise exceptions or return an error and will always return some string value.
    """
    r = "/"
    if not forceLinuxPathSep:
        r = os.path.sep
    return r



def isValidCodeType( codetype = None, robustconsumer = False ):
    """
    Given a codetype representing a type of code declaration (class or object, function or def), validates whether that
    is a valid codetype as supported by scripts found alongside the isValidCodeType function.

    More importantly, this function translates different types of programming experience and concepts into python
    concepts.  For example programmers who want to search for 'def' may pass in either 'function' or 'def' and this
    function will translate both into the Python keyword 'def' for use in module searches, while programmers who want
    to search for 'class' may pass in either 'object' or 'class' and this function will translate both of those into
    the Python keyword 'class' for use in module searches.

    :param codetype: {str} A codetype to search for.  Accepts 'class' or 'object' for instantiable declaration types,
                     'def' or 'function' for callable declaration types.  May be None or may be abbreviated (cl or fu).
                     Optional:  Default is 'def'
    :param robustconsumer: {bool} Indicates whether the consuming caller is robust - whether it can cope with execution
                           errors or not.  If True, then any errors encountered will be converted into error-code return
                           values.  If False, then any errors encountered cause script termination by raised exception.
                           Optional:  Default is False.
    :return: {str} 'class' if the specified codetype matches a class alias, 'def' if the specified codetype matches a
                   def alias.

             * When robustconsumer is True:
             * A return value of -1 means a codetype was specified and is a valid string but it is invalid codetype -
               not found in validFindTypes
             * A return value of -2 means a codetype was specified but is not valid string.
    """

    #
    # Add new codetype aliases by adding new array entries to the array below.  Each element is an array.
    # element[0] = declarationType
    # element[1] = declarationAlias
    #  Where declarationType is what will actually be found in .py code files
    #  Where declarationAlias is input that will be accepted by this function in the codetype parameter
    #
    # Absolutely nothing else needs to be done to add new codetype aliases.  All the work is done in the function body.
    #
    validcodetypes = []
    validcodetypes.append(['class','class'])
    validcodetypes.append(['class','object'])
    validcodetypes.append(['def','def'])
    validcodetypes.append(['def','function'])

    r = False
    if (codetype is not None) and isinstance( codetype, (str, unicode) ) and ( len( codetype ) > 0 ):
        #
        # Set r to the regex matched valid codetype
        #
        match = None
        for vt in validcodetypes:
            match = re.match("^\s*" + codetype + ".*\s*$", vt[1], re.IGNORECASE)
            if match is not None:
                r = vt[0]
                break
        else:
            #
            # A codetype was specified and is a valid string but it is invalid codetype - not found in validcodetypes
            #
            if robustconsumer:
                r = -1
            else:
                raise ValueError("Parameter 'codetype' to isValidcodeType( codetype ) ( " + codetype + " ) is not a valid find codetype")
    elif ( codetype is not None ) and ( not isinstance( codetype, (str, unicode) ) ):
        #
        # A codetype was specified but is not valid string
        #
        if robustconsumer:
            r = -2
        else:
            raise ValueError( "Parameter 'codetype' to isValidcodeType( codetype ) must be a {str} value.  Value supplied is " + str( type( codetype ) ) )
    elif (codetype is None) or ( not isinstance( codetype, (str, unicode) ) ) or ( len( codetype ) == 0 ):
        #
        # r defaults to function where codetype is None or empty string
        #
        r = 'def'

    return r



class codeLineClass:
    """
    The codeLineClass represents a single line of Python code and provides functions for pulling metadata pertaining to
    that line of code.
    """

    lineNumber = None
    """
    lineNumber contains the line number, in the original file, that the code which a given codeLineClass instance 
    represents was found on.  
        
    This value is found on all individual instances as well but is set in here as a placemarker.
    """

    codeString = None
    """
    codeString contains the actual code, from the original file, which a given codeLineClass instance represents.  

    This value is found on all individual instances as well but is set in here as a placemarker.
    """

    def __init__( self, line, code ):
        """
        Initializes the codeLineClass instance.

        :param line: The line number in the file that the code appears on.
        :param code: The code itself.
        """

        self.lineNumber = line
        self.codeString = code

    def getIndent(self):
        """
        Gets the indentation, if any, preceding the code that this codeLineClass instance represents.  This returns the
        actual indentation, ie the space(s) or tabstop(s) themselve(s).  To get a count of the whitespace, use
        getIndent_Len()

        :return: {str} The indentation, if any, preceding the code that this codeLineClass instance represents.  This
                       returns the actual indentation, ie the space(s) or tabstop(s) themselve(s).  To get a count of
                       the whitespace, use getIndent_Len()
        """
        r = None
        if self.codeString is not None:
            match = re.match(regExPattern_CodeDeclaration, self.codeString, re.IGNORECASE)
            if match is not None:
                r = match.group(1)
        return r

    def getIndent_Len(self):
        """
        Gets the length of the indendation, if any, preceding the code that this codeLineClass instance represents.
        This returns a count of the number of space(s) or tabstop(s) found.  To get the actual whitespace, use
        getIndent()

        :return: {int}  The length of the indendation, if any, preceding the code that this codeLineClass instance
                        represents.  This returns a count of the number of space(s) or tabstop(s) found.  To get the
                        actual whitespace, use getIndent()
        """
        r = 0
        rval = None
        if self.codeString is not None:
            match = re.match( regExPattern_CodeDeclaration, self.codeString, re.IGNORECASE )
            if ( match is not None ) and ( match.group(1) is not None ):
                r = len( match.group(1) )
        return r

    def getCodeType(self):
        """
        Gets the type of code declaration that this codeLineClass instance rapresents.  This will always return 'class'
        or 'def'

        :return: {str} The type of code declaration that this codeLineClass instance rapresents.  This will always
                       return 'class' or 'def'
        """
        r = None
        if self.codeString is not None:
            match = re.match(regExPattern_CodeDeclaration, self.codeString, re.IGNORECASE)
            if match is not None:
                r = match.group(2)
        return r

    def getCodeName(self):
        """
        Gets the name of the code declaration that this codeLineClass instance represents.
        ie:  def myFunc():
        Returns myFunc

        :return: {str} The name of the code declaration that this codeLineClass instance represents.
                       ie:  def myFunc():
                       Returns myFunc
        """
        r = None
        if self.codeString is not None:
            match = re.match(regExPattern_CodeDeclaration, self.codeString, re.IGNORECASE)
            if match is not None:
                r = match.group(3)
        return r

    def getString(self):
        """
        Gets a formatted string that represents this codeLineClass instance in a meaningful way.
        ie:  Line 120      : def myFunc():

        :return: {str} Gets a formatted string that represents this codeLineClass instance in a meaningful way.
                       ie:  Line 120      : def myFunc():
        """
        r = '  Line ' + stringExtends.setStringLength( str( self.lineNumber ), 8 ) + " : " + self.codeString
        return r

class codeBlockClass(codeLineClass):
    """
    The codeBlockClass represents a block of code, which is a line of code that begins a collection of codelines which
    may contain additional code blocks as well as additional code lines.
    """

    codeBlocks = None
    """
    codeBlocks is an array of codeBlockClass instances representing code blocks that are contained by or subordinate to 
    this one (ie class or function declarations at deeper indentation levels in the codefile where they were found).  
    
    This value is found on all individual instances as well but is set in here as a placemarker.
    """

    def __init__( self, line, code ):
        """
        Initializes the codeBlockClass instance.

        :param line: The line number in the file that the code block is declared on.
        :param code: The code block declaration itself.
        """

        self.lineNumber = line
        self.codeString = code
        self.codeBlocks = []

    def getStrings(self):
        """
        Gets a formatted string that represents this codeLineClass instance in a meaningful way, by calling its base
        codeLineClass.getString() first and then calling codeBlockClass.getStrings() on each member found in its
        codeBlocks[] array.
        ie:  Line 120      : class myClass():
             Line 125      :     class mySubClass():
             Line 126      :         def __init__( self ):

        :return: {str} A formatted string that represents this codeLineClass instance in a meaningful way, by calling
        its base codeLineClass.getString() first and then calling codeBlockClass.getStrings() on each child found in
        its codeBlocks[] array.
        ie:  Line 120      : class myClass():
             Line 125      :     class mySubClass():
             Line 126      :         def __init__( self ):
        """
        r = self.getString()
        for cb in self.codeBlocks:
            r += cb.getStrings()
        return r

    def clearEmptyBlocks( self ):
        """
        Iterates through each member of this codeBlockClass instance's codeBlocks[] array, calling its
        codeBlockClass.clearEmptyBlocks() function, then removing any members whose codeType is 'class' and whose
        codeBlocks[] array contain no members themselves.  This iteratively removes empty blocks through the child
        chain, ultimately leaving this block empty itself if none of its children contain function definitions.

        This function is most useful when searching for a specific function name, since the codeFileClass will populate
        codeBlockClass instances regardless and we don't want to output a long list of irrelevant class definitions.

        :return: No return value.
        """
        #
        # Python appears to translate 'forward by reference' into 'forward by index' by some means in the engine
        # So can't use 'for cb in self.codeBlocks' and remove( cb ) at the end
        #
        if len(self.codeBlocks) > 0:
            for i in range(len(self.codeBlocks) - 1, -1, -1):
                cb = self.codeBlocks[i]
                if (cb.getCodeType() is not None) and (cb.getCodeType() == 'class'):
                    cb.clearEmptyBlocks()
                    if len(cb.codeBlocks) == 0:
                        del self.codeBlocks[i]

    def countCodeBlocks( self ):
        """
        Gets a count of the codeblocks contained in this codeBlockClass instance, including their children, and their
        children, and their...

        :return: {int} The total number of codeblocks subordinate to this codeBlockClass instance, including itself.
        """
        r = 0
        for cb in self.codeBlocks:
            r += cb.countCodeBlocks()
        r += 1
        return r

    def getClassOwningIndent( self, indent = 0 ):
        """
        Given an indentation level, rewinds through the members of its codeBlocks[] array (including itself) and
        returns the first one (or the last one, if you prefer, since it starts at the end and works toward the
        beginning) whose indentation level is LESS THAN the indent specified, or returns itself, or returns None if the
        indent specified is less than the indent level of itself and all of its child blocks.

        The return value will therefore be the codeBlockClass instance that owns the specified indentation level, not
        the codeBlockClass instance at the specified indentation level, or None.

        :param indent: {int} The number of whitespace characters representing the indent level to search for.
        :return: {codeBlockClass} The first codeBlockClass instance in the backward chain that matches the specified
                                  indent level.

                                  The return value will therefore be the codeBlockClass instance that owns the
                                  specified indentation level, not the codeBlockClass instance at the specified
                                  indentation level.
        """

        r = None
        if indent < self.getIndent_Len():
            #
            # If indent specified is less than this codeBlockClass instance's own indent level then it will surely be
            # less than any of its children - absolutely no need to iterate through them all!
            #
            pass
        elif indent > 0:
            #
            # We have to work backward, never ever forward, with self as the last possible option (since it's the first)
            #
            if len( self.codeBlocks ) > 0:
                for i in range( len( self.codeBlocks ) - 1, -1, -1 ):
                    testclass = self.codeBlocks[i].getClassOwningIndent(indent)
                    if ( testclass is not None ) and ( testclass.getCodeType() == "class" ) and ( testclass.getIndent_Len() < indent ):
                        #
                        # since testclass is less indented than current test case, it must be the owner
                        #
                        r = testclass
                    else:
                        #
                        # If testclass is >= indentation of the current test case, it must not be the owner
                        # leave this in for future development
                        #
                        pass
                    if r is not None:
                        break
            #
            # If we reached the end of all the contained classes and found no owner, then perhaps self is the owner...
            #
            if self.getIndent_Len() < indent:
                r = self
        else:
            #
            # defaulted to none - leave this in for future development
            #
            pass
        return r

    def getNamedBlock( self, namematch = None, blocktype = None, skipvaluechecking = False ):
        """
        Gets the named, and optionally typed, block from the members of its codeBlocks[] array (including itself), or
        returns None if no match is found.

        :param namematch: {str} or {stringExtends.stringMatchClass}
                          A string instance representing the exact, case-sensitive name of
                          the block to search for or else a stringMatchClass instance
                          representing the matching algorithm used to match the name of the
                          block to search for.
        :param blocktype: {str}
                          The type of the block to search for.  This may be any type recognized by the
                          isValidCodeCodeType() function, including abbreviations.  If omitted or None, default
                          is 'def' or 'function'
        :param skipvaluechecking: {bool}
                                  A shortcut we can use to enhance performance if we already know parameter
                                  values are good.  FOR USE ONLY AFTER AT LEAST THE FIRST PASS OF VALIDATION!
        :return: {codeBlockClass} The codeBlockClass instance whose getCodeType() and getCodeName() values match the
                                  specified blockname and blocktype values, or None if no match was found.
        """

        r_namematch = None
        r_blocktype = "def"
        r = None
        if not skipvaluechecking:
            if namematch is None:
                raise ValueError( 'namematch parameter to codeBlockClass.getNamedBlock must not be None.' )
            else:
                if isinstance( namematch, ( str, unicode ) ):
                    #
                    # namematch is a string, so make a stringExtends.stringMatchClass out of it
                    #
                    r_namematch = stringExtends.stringMatchClass( matchvalue =namematch, useregex =False, regexflags =None )
                elif (isinstance( namematch, stringExtends.stringMatchClass )):
                    #
                    # namematch is already a stringMatchClass
                    #
                    r_namematch = namematch

            if isinstance( blocktype, ( str, unicode ) ):
                #
                # blocktype is declared and is a valid string - test if it's a valid blocktype.
                # if consumers don't want to get exceptions, they can call isValidCodeType themselves before passing
                # the blocktype value
                #
                r_blocktype = isValidCodeType( codetype = blocktype, robustconsumer = False)
        else:
            r_namematch = namematch
            r_blocktype = blocktype

        #
        # Now perform the meat and potatoes
        #
        if r_namematch.isRawMatch( self.getCodeName( ) ):
            r = self
        if r is None:
            for cb in self.codeBlocks:
                # we can skip value checking
                r = cb.getNamedBlock( namematch = r_namematch, blocktype = r_blocktype, skipvaluechecking = True )
                if r is not None:
                    break
        return r

class codeFileClass:
    """
    The codeFileClass represents a code file which contains a collection of code lines and/or code blocks in a
    filesystem.
    """

    fileName = None
    """
    fileName represents the Fully Qualified Path (FQP) or the Relative Path (RP) or simply the File Name (FN), 
    depending on how you, the consumer of the codeFileClass, choose to pass the value in at runtime.  Since this value 
    is used as a default filepath in File IO and also output in reports, it is highly recommended that you use some 
    manner of path, either FQP in the filesystem or RP to the calling script.
    
    This value is found on all individual instances as well but is set in here as a placemarker.
    """

    codeBlocks = None
    """
    codeBlocks is an array of codeBlockClass instances representing code blocks that are contained by or subordinate to 
    this codeFileClass instance (ie class or function declarations in the codefile).  

    This value is found on all individual instances as well but is set in here as a placemarker.
    """

    classNameFilter = None
    """
    classNameFilter is a stringExtends.stringMatchClass instance representing a filter that will be applied to classes located when 
    cataloguing operations are performed by this codeFileClass instance.
    
    Any time a class definition is found during a cataloguing operation, it will only be catalogued (added to the 
    codeFileClass instance's codeBlocks array) if the classNameFilter.isRawMatch( codeBlock.getCodeName() ) operation 
    returns True.
    
    * If a classNameFilter is in place, then only functions found in classes matching the classNameFilter will be 
      catalogued whether a defNameFilter is in place or not.
    
    * If both a classNameFilter and a defNameFilter are in place, then functions matching the defNameFilter may be 
      omitted if they do not appear in classes which no not pass the classNameFilter.
    
    This value is found on all individual instances as well but is set in here as a placemarker.
    """

    defNameFilter = None
    """
    defNameFilter is a stringExtends.stringMatchClass instance representing a filter that will be applied to functions located when 
    cataloguing operations are performed by this codeFileClass instance.
    
    Any time a function definition is found during a cataloguing operation, it will only be catalogued (added to the 
    codeFileClass instance's codeBlocks array) if the defNameFilter.isRawMatch( codeBlock.getCodeName() ) operation 
    returns True.

    * See starred notes under classNameFilter

    * If no classNameFilter is in place, then defNameFilter is applied both to functions at the top level in the code 
      file and to functions found in class definitions.

    This value is found on all individual instances as well but is set in here as a placemarker.
    """

    def __init__(self, name):
        """
        Initializes the codeFileClass instance.

        :param name: {string} The filename of the codefile under examination.  Since this value is used as a default
                              filepath in File IO and also output in reports, it is highly recommended that you use
                              some manner of path, either Fully Qualified Path (FQP) in the filesystem or the Relative
                              Path (RP) to the calling script.
        """
        self.fileName = name
        self.codeBlocks = []
        self.classNameFilter = None
        self.defNameFilter = None

    def getString(self, custom_unprefix = None ):
        """
        Gets a formatted string that represents this codeFileClass instance in a meaningful way, by prepending its
        fileName value before calling codeBlockClass.getStrings() on each member found in its codeBlocks[] array.
        ie:  myDirectory/someCodeFile.py
               Line 120      : class myClass():
               Line 125      :     class mySubClass():
               Line 126      :         def __init__( self ):

        :return: {str} A formatted string that represents this codeFileClass instance in a meaningful way, by
                       prepending its fileName value before calling codeBlockClass.getStrings() on each member found in
                       its codeBlocks[] array.
                       ie:  myDirectory/someCodeFile.py
                              Line 120      : class myClass():
                              Line 125      :     class mySubClass():
                              Line 126      :         def __init__( self ):
        """
        r = stringExtends.strUnprefix( self.fileName, "../" )
        if isinstance( custom_unprefix, ( str, unicode ) ):
            r = stringExtends.strUnprefix( r, custom_unprefix )
        elif isinstance( custom_unprefix, ( list, tuple ) ):
            for unpre in custom_unprefix:
                if isinstance( unpre, ( str, unicode ) ):
                    r = stringExtends.strUnprefix( r, unpre )
        r += "\n"
        for s in self.codeBlocks:
            r += s.getStrings()
        return r

    def clearCatalog(self):
        """
        Simply sets the codeFileClass instance's catalog to None and then redeclares it as an empty array.  Returns
        nothing.

        :return: Returns nothing.
        """
        self.codeBlocks = None
        self.codeBlocks = []

    def clearEmptyBlocks(self):
        """
        Iterates through each member of this codeFileClass instance's codeBlocks[] array, calling its
        codeBlockClass.clearEmptyBlocks() function, then removing any members whose codeType is 'class' and whose
        codeBlocks[] array contain no members themselves.  If the resulting codeBlock is itself empty at that point, it
        is then removed from the codeFileClass instance's codeBlocks[] array.

        This function is most useful when searching for a specific function name, since the codeFileClass will populate
        codeBlockClass instances regardless and we don't want to output a long list of irrelevant class definitions.

        :return: No return value.
        """

        #
        # Python appears to translate 'forward by reference' into 'forward by index' by some means in the engine
        # So can't use 'for cb in self.codeBlocks' and remove( cb ) at the end
        #
        if len(self.codeBlocks) > 0:
            for i in range(len(self.codeBlocks) - 1, -1, -1):
                cb = self.codeBlocks[i]
                if (cb.getCodeType() is not None) and (cb.getCodeType() == 'class'):
                    cb.clearEmptyBlocks()
                    if len(cb.codeBlocks) == 0:
                        del self.codeBlocks[i]

    def countCodeBlocks( self ):
        """
        Gets a count of the codeblocks contained in this codeFileClass instance, including their children, and their
        children, and their...

        :return: {int} The total number of codeblocks subordinate to this codeFileClass instance.
        """
        r = 0
        for cb in self.codeBlocks:
            r += cb.countCodeBlocks()
        return r

    def getClassOwningIndent( self, indent = 0 ):
        """
        Given an indentation level, rewinds through the members of its codeBlocks[] array and returns the first one (or
        the last one, if you prefer, since it starts at the end and works toward the beginning) whose indentation level
        is LESS THAN the indent specified, or returns itself, or returns None if the indent specified is less than the
        indent level of all of its child blocks.

        The return value will therefore be the codeBlockClass instance that owns the specified indentation level, not
        the codeBlockClass instance at the specified indentation level, or None.

        :param indent: {int} The number of whitespace characters representing the indent level to search for.
        :return: {codeBlockClass} The first codeBlockClass instance in the backward chain that matches the specified
                                  indent level.

                                  The return value will therefore be the codeBlockClass instance that owns the
                                  specified indentation level, not the codeBlockClass instance at the specified
                                  indentation level.
        """
        r = None
        if indent > 0:
            if ( len( self.codeBlocks ) > 0 ):
                for i in range(len( self.codeBlocks ) - 1, -1, -1):
                    r = self.codeBlocks[i].getClassOwningIndent(indent)
                    if r is not None:
                        break
                    else:
                        #
                        # we can keep iterating until we run out of classes to test or we hit a break
                        #
                        pass
        else:
            #
            # defaulted to None for use in iteration above - leave this in for future development
            #
            pass

        if r is None:
            #
            # if r is none after all of the above, then the owner must be self
            #
            r = self

        return r

    def getNamedBlock( self, namematch = None, blocktype = None, skipvaluechecking = False ):
        """
        Gets the named, and optionally typed, block from the members of its codeBlocks[] array, or returns None if no
        match is found.

        :param namematch: {str} or {stringExtends.stringMatchClass} A string instance representing the exact, case-sensitive name of
                                                      the block to search for or else a stringMatchClass instance
                                                      representing the matching algorithm used to match the name of the
                                                      block to search for.
        :param blocktype: {str} The type of the block to search for.  This may be any type recognized by the
                                isValidCodeCodeType() function, including abbreviations.  If omitted or None, default
                                is 'def' or 'function'
        :param skipvaluechecking: {bool} A shortcut we can use to enhance performance if we already know parameter
                                         values are good.  FOR USE ONLY AFTER AT LEAST THE FIRST PASS OF VALIDATION!
        :return: {codeBlockClass} The codeBlockClass instance whose getCodeType() and getCodeName() values match the
                                  specified blockname and blocktype values, or None if no match was found.
        """

        r_namematch = None
        r_blocktype = "def"
        r = None
        if not skipvaluechecking:
            if namematch is None:
                raise ValueError( 'namematch parameter to codeFileClass.getNamedBlock must not be None.' )
            else:
                if isinstance( namematch, ( str, unicode ) ):
                    #
                    # namematch is a string, so make a stringExtends.stringMatchClass out of it
                    #
                    r_namematch = stringExtends.stringMatchClass( matchvalue =namematch, useregex =False, regexflags =None )
                elif (isinstance( namematch, stringExtends.stringMatchClass )):
                    #
                    # namematch is already a stringExtends.stringMatchClass
                    #
                    r_namematch = namematch

            if ( blocktype is not None ) and ( isinstance( blocktype, ( str, unicode ) ) ):
                #
                # blocktype is declared and is a valid string - test if it's a valid blocktype.
                # if consumers don't want to get exceptions, they can call isValidCodeType themselves before passing
                # the blocktype value
                #
                r_blocktype = isValidCodeType( codetype = blocktype, robustconsumer = False)
        else:
            r_namematch = namematch
            r_blocktype = blocktype

        #
        # Now perform the meat and potatoes
        #
        for cb in self.codeBlocks:
            # we can skip value checking
            r = cb.getNamedBlock(namematch=r_namematch, blocktype=r_blocktype, skipvaluechecking=True)
            if r is not None:
                break
        return r

    def catalogBlockAtLine( self, filename = None, linenumber = 0, appendcatalog = True ):
        """
        Given a line number and a filename, if it locates any definition (class or function) at that line number,
        produces a catalog of that definition.  If a class is found, it catalogs subclasses and functions.  If a
        function is found, it catalogs only that function.

        If no filename is provided, filename defaults to self.fileName.

        If no linenumber is provided, linenumber defaults to 0.

        :param filename: {string} A Fully Qualified Path (FQP) or Relative Path (RP) to the file to be catalogued.
                                  If no filename is provided, filename defaults to self.fileName.
        :param linenumber: {int} A line number into the file where cataloguing should begin.
                                 If no linenumber is provided, linenumber defaults to 0.
        :param appendcatalog: {bool} If True, appends the new data to the existing catalog.  If False, clears the
                                     existing catalog before performing the new cataloguing operation.  Default is
                                     True.
        :return: Returns nothing.  Populates its own codeBlocks[] array instead.  Use instance.getString() to retrieve
                 the report.
        """

        if not appendcatalog:
            self.clearCatalog()

        if filename is None:
            filename = self.fileName
        else:
            self.fileName = filename
        with open( filename ) as file:
            line_num = 0
            org_indent_len = -1
            cur_indent_len = 0
            curClass = None
            for line in file:
                line_num += 1
                if line_num < linenumber:
                    #
                    # we haven't yet reached the starting line number
                    #
                    pass
                else:
                    #
                    # we are past the starting line number
                    #
                    match = re.match( regExPattern_CodeDeclaration, line, re.IGNORECASE )
                    if (match is not None):
                        cur_indent_len = len( match.group(1) )
                        #
                        # we have matched a class or def declaration
                        #
                        if org_indent_len < 0:
                            #
                            # original indent has never been established - set it now
                            #
                            org_indent_len = cur_indent_len
                        #
                        # We need a brand new if right here or we always miss the first item found
                        #
                        if cur_indent_len < org_indent_len:
                            #
                            # current indent is less than original indent - WE ARE DONE!
                            #
                            break
                        elif match.group(2) == "class" and ((self.classNameFilter is None) or (( self.classNameFilter is not None ) and self.classNameFilter.isRawMatch( match.group( 3 ) ))):
                            codeblock = codeBlockClass( line=line_num, code=line )
                            if ( cur_indent_len == 0 ) or ( curClass is None ):
                                #
                                # indent level is 0 or curClass is None so we can safely create and add a brand new class
                                # to the file toplevel
                                #
                                curClass = codeblock
                                self.codeBlocks.append( codeblock )
                            elif ( curClass is not None ) and ( cur_indent_len > curClass.getIndent_Len() ):
                                #
                                # curClass is not None and current indentation is deeper than curClass, so we can safely
                                # create a new class and add it to curClass
                                #
                                curClass.codeBlocks.append( codeblock )
                                codeblock.ownerClass = curClass.getCodeName()
                                curClass = codeblock
                            elif ( curClass is not None ) and ( cur_indent_len < curClass.getIndent_Len() ):
                                #
                                # curClass is not None but current indentation is shallower than curClass, so we must
                                # rewind into the codeBlocks until we find the one at the appropriate indentation level
                                #
                                curClass = codeblock
                                classatindent = self.getClassOwningIndent(cur_indent_len)
                                curClass.ownerClass = classatindent.getCodeName()
                                classatindent.append( codeblock )
                                # either
                        elif (match.group(2) == "def") and ( ( self.classNameFilter is None ) or ( ( self.classNameFilter is not None) and ( curClass is not None ) ) ) and ((self.defNameFilter is None) or (( self.defNameFilter is not None ) and self.defNameFilter.isRawMatch( match.group( 3 ) ))):
                            codeline = codeBlockClass(line=line_num, code=line)
                            if ( curClass is not None ) and ( cur_indent_len > curClass.getIndent_Len() ):
                                #
                                # curClass is not None as current indentation is gtn curClass indent - add this codeline to
                                # curClass
                                #
                                curClass.codeBlocks.append(codeline)
                                codeline.ownerClass = curClass.getCodeName()
                            elif ( curClass is not None ) and ( cur_indent_len > 0 ) and (
                                cur_indent_len < curClass.getIndent_Len()):
                                #
                                # curClass is not None and current indentation is gtn 0 but ltn curClass indent, so we must
                                # rewind into the codeBlocks until we find the one at the appropriate indentation level
                                #
                                classatindent = self.getClassOwningIndent( cur_indent_len )
                                curClass = classatindent
                                codeline.ownerClass = classatindent.getCodeName()
                                curClass.codeBlocks.append( codeline )
                            elif ( cur_indent_len == 0 ):
                                #
                                # current indentation length is 0 so curClass is exited no matter what!
                                #
                                curClass = None
                                self.codeBlocks.append( codeline )
                            elif ( curClass is None ):
                                #
                                # curClass is None so we can safely create a new codeLine and add it to the file toplevel
                                #
                                self.codeBlocks.append( codeline )
                            #
                            # If this was a function and we are == specified line number, we're done!
                            #
                            if line_num == linenumber:
                                break

    def catalogTopLevelBlockContainingLine( self, filename=None, linenumber=0, appendcatalog = False ):
        """
        Given a line number and a filename, locates the first toplevel (unindented) block above that line number and
        produces a catalog of that declaration.

        If no filename is provided, filename defaults to self.fileName.

        If no linenumber is provided, linenumber defaults to 0.

        :param filename: {string} A Fully Qualified Path (FQP) or Relative Path (RP) to the file to be catalogued.
                                  If no filename is provided, filename defaults to self.fileName.
        :param linenumber: {int} A line number into the file where cataloguing should begin.
                                 If no linenumber is provided, linenumber defaults to 0.
        :param appendcatalog: {bool} If True, appends the new data to the existing catalog.  If False, clears the
                                     existing catalog before performing the new cataloguing operation.  Default is
                                     True.
        :return: Returns nothing.  Populates its own codeBlocks[] array instead.  Use instance.getString() to retrieve
                 the report.
        """

        if filename is None:
            filename = self.fileName
        else:
            self.fileName = filename
        if linenumber > 0:
            last_top_level = -1
            line_num = 0
            with open(filename) as file:
                for line in file:
                    line_num += 1
                    match = re.match( regExPattern_CodeDeclaration, line, re.IGNORECASE )
                    if (match is not None) and ((match.group(1) is None) or (len(match.group(1)) == 0)):
                        last_top_level = line_num
                    if line_num == linenumber:
                        break
            self.catalogBlockAtLine( filename = filename, linenumber = last_top_level, appendcatalog = appendcatalog )
        else:
            #
            # if linenumber not > 0 then we're done XD
            #
            pass

    def catalogFile( self, filename = None, appendcatalog = False ):
        """
        Given a filename, catalogs every block declaration in that file matching the instance's classNameFilter and
        defNameFilter.

        If no filename is provided, filename defaults to self.fileName.

        :param filename: {string} A Fully Qualified Path (FQP) or Relative Path (RP) to the file to be catalogued.
                                  If no filename is provided, filename defaults to self.fileName.
        :param appendcatalog: {bool} If True, appends the new data to the existing catalog.  If False, clears the
                                     existing catalog before performing the new cataloguing operation.  Default is
                                     False.
        :return: Returns nothing.  Populates its own codeBlocks[] array instead.  Use instance.getString() to retrieve
                 the report.
        """

        if not appendcatalog:
            self.clearCatalog()

        if filename is None:
            filename = self.fileName
        else:
            self.fileName = filename
        with open(filename) as file:
            line_num = 0
            cur_indent_len = 0
            curClass = None
            for line in file:
                line_num += 1
                match = re.match( regExPattern_CodeDeclaration, line, re.IGNORECASE )
                if match is not None:
                    if match.group(1) is not None:
                        cur_indent_len = len(match.group(1))
                    else:
                        cur_indent_len = 0

                    codeblock = codeBlockClass(line=line_num, code=line)

                    if ( match.group(2) == "class" ) and (( self.classNameFilter is None ) or (( self.classNameFilter is not None ) and self.classNameFilter.isRawMatch( match.group( 3 ) ))):
                        if ( curClass is not None ):
                            if ( cur_indent_len > curClass.getIndent_Len() ):
                                #
                                # curClass is not None and current indentation is deeper than curClass, so we can safely
                                # create a new class and add it to curClass
                                #
                                curClass.codeBlocks.append( codeblock )
                                curClass = codeblock
                            elif (cur_indent_len > 0 ) and ( cur_indent_len < curClass.getIndent_Len() ):
                                #
                                # curClass is not None but current indentation is shallower than curClass, so we must
                                # rewind into the codeBlocks until we find the one at the appropriate indentation level
                                #
                                # There is no reason to think that the last-used curClass is necessarily the correct
                                # indentation level
                                #
                                curClass = codeblock
                                self.getClassOwningIndent( cur_indent_len ).codeBlocks.append( codeblock )
                            elif ( cur_indent_len == 0 ):
                                curClass = codeblock
                                self.codeBlocks.append( codeblock )
                        else:
                            #
                            # curClass is None so we can safely create and add a brand new class to the file toplevel
                            #
                            curClass = codeblock
                            self.codeBlocks.append( codeblock )
                    elif ( match.group(2) == "def" ) and ( ( self.classNameFilter is None ) or ( ( self.classNameFilter is not None) and ( curClass is not None ) ) ) and (( self.defNameFilter is None ) or (( self.defNameFilter is not None ) and self.defNameFilter.isRawMatch( match.group( 3 ) ))):
                        if (curClass is not None):
                            if (cur_indent_len > curClass.getIndent_Len()):
                                #
                                # curClass is not None as current indentation is gtn curClass indent - add this codeblock to
                                # curClass
                                #
                                curClass.codeBlocks.append(codeblock)
                            elif ( cur_indent_len > 0 ) and ( cur_indent_len < curClass.getIndent_Len()):
                                #
                                # curClass is not None and current indentation is gtn 0 but ltn curClass indent, so we must
                                # rewind into the codeBlocks until we find the one at the appropriate indentation level
                                #
                                curClass = self.getClassOwningIndent(cur_indent_len)
                                curClass.codeBlocks.append(codeblock)
                            elif (cur_indent_len == 0):
                                #
                                # current indentation length is 0 so curClass is exited no matter what!
                                #
                                curClass = None
                                self.codeBlocks.append( codeblock )
                        else:
                            #
                            # curClass is None so we can safely create a new codeLine and add it to the file toplevel
                            #
                            self.codeBlocks.append( codeblock )

#
# findCode( codetype, name, listfuncs )
#   {str} codetype - Optional:  The codetype of code declaration to search for (class or function).  May be abbreviated.
#                Default is None.
#   {str} name - Optional:  The name of a code declaration to search for (default: None).   May be abbreviated.
#                Default is None.
#   {bool} listfuncs - Optional:  Whether to list functions defined in classes found.  Default depends on other
#                      parameters.
#   Returns {str} - a string listing path-to-filenames of all .py files in all subdirectories containing code
#                   definitions matching 'name' (or all definitions if 'name' is None or if 'name' is an empty string).
#
#   If 'codetype' is None and 'name' is None then 'listfuncs' is True and all code definitions are listed (same as if
#   'codetype' is Function and 'name' is None or an empty string).
#
#   If 'codetype' is Class and and 'listfuncs' is unspecified then its default is False.
#
#   If 'codetype' is Function and 'listfuncs' is unspecified then its default is True (obviously).
#
#
def findCode( topdir = None, subdirs = False, filename = None, matchinclassname = None, isclassmatchregex = False, matchindefname = None, isdefmatchregex = False, clearemptyblocks = False ):
    """
    Finds a specific code declaration given a specific toplevel directory, optionally iterating through subdirectories,
    optionally filtering by a specific filename, optionally filtering by a specific class name,

    :param topdir:
    :param subdirs:
    :param filename:
    :param matchinclassname:
    :param isclassmatchregex:
    :param matchindefname:
    :param isdefmatchregex:
    :param clearemptyblocks:
    :return:
    """
    r = ''

    find_in_dir = '..' + getPathSep( forceLinuxPathSeparators )
    if isinstance( topdir, (str, unicode) ):
        if not os.path.isdir( topdir ):
            raise ValueError( 'topdir parameter to findCode() must be a valid directory.' )
        else:
            find_in_dir = topdir

    find_in_subdirs = False
    if isinstance( subdirs, bool ):
        find_in_subdirs = subdirs

    find_in_filename = None
    if isinstance( filename, ( str, unicode )):
        find_in_filename = filename

    is_class_match_regex = False
    if isinstance( isclassmatchregex, bool ):
        is_class_match_regex = isclassmatchregex

    match_in_class_name = None
    if isinstance( matchinclassname, ( str,unicode ) ):
        match_in_class_name = stringExtends.stringMatchClass( matchinclassname, is_class_match_regex )

    is_def_match_regex = False
    if isinstance( isdefmatchregex, bool ):
        is_def_match_regex = isdefmatchregex

    match_in_def_name = None
    if isinstance(matchindefname, (str, unicode)):
        match_in_def_name = stringExtends.stringMatchClass( matchindefname, is_def_match_regex )

    clear_empty_blocks = False
    if isinstance( clearemptyblocks, bool ):
        clear_empty_blocks = clearemptyblocks

    dirs = []
    dirs.append( find_in_dir )
    while len( dirs ) > 0:
        thisdir = dirs.pop()
        for fsobj in os.listdir( thisdir ):
            b_anyfile = ( ( find_in_filename is None ) and ( fsobj != '__init__.py' ) and ( os.path.splitext( fsobj )[1] == '.py' ) )
            b_spcfile = ( ( find_in_filename is not None ) and ( fsobj == find_in_filename ) )

            if not thisdir.endswith( getPathSep( forceLinuxPathSeparators ) ):
                thisdir += getPathSep( forceLinuxPathSeparators )
            fspath = thisdir + fsobj

            if os.path.isdir( fspath ) and find_in_subdirs:
                dirs.append( fspath )
            elif os.path.isfile( fspath ) and ( b_anyfile or b_spcfile ):
                filereport = codeFileClass( name = fspath )

                if match_in_class_name is not None:
                    filereport.classNameFilter = match_in_class_name

                if match_in_def_name is not None:
                    filereport.defNameFilter = match_in_def_name

                filereport.catalogFile( filename = None )

                if clear_empty_blocks:
                    filereport.clearEmptyBlocks()

                if len( filereport.codeBlocks ) > 0:
                    r += filereport.getString() + '\n\n'

    return r

#dir_path = r"X:\MUSH\pyenv" # my particular virtual environment path for Python 2.7
#dir_path = r"X:\MUSH\evennia" # my particular virtual environment path for evennia package
#dir_path = r"X:\MUSH\evennia\evennia\objects"
#with open(r"X:\MUSH\findCode_outfile.txt", r"w+") as outfile:
#    rep = findCode( topdir = dir_path, subdirs = True, matchinclassname = r"MatchObject", matchindefname = None, clearemptyblocks = True )
#    rep = findCode( topdir = dir_path, subdirs = True, matchinclassname = None, matchindefname = r"search", clearemptyblocks = True )
#    rep = findCode( topdir = dir_path, subdirs=True, clearemptyblocks = False )
#    outfile.write(rep)

# the next line is only there to set a breakpoint in PyCharm
# breakpoint_here = None