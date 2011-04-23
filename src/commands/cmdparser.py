"""
The default command parser. Use your own by assigning
settings.ALTERNATE_PARSER to a Python path to a module containing the
replacing cmdparser function. The replacement parser must
return a CommandCandidates object.
"""
import re
from django.conf import settings

# This defines how many space-separated words may at most be in a command.
COMMAND_MAXLEN = settings.COMMAND_MAXLEN

# These chars (and space) end a command name and may
# thus never be part of a command name. Exception is
# if the char is the very first character - the char
# is then treated as the name of the command. 
SPECIAL_CHARS = ["/", "\\", "'", '"', ":", ";", "\-", '#', '=', '!']

# Pre-compiling the regular expression is more effective
REGEX = re.compile(r"""["%s"]""" % ("".join(SPECIAL_CHARS)))


class CommandCandidate(object):
    """
    This is a convenient container for one possible
    combination of command names that may appear if we allow
    many-word commands.     
    """
    def __init__(self, cmdname, args=0, priority=0, obj_key=None):
        "initiate"
        self.cmdname = cmdname
        self.args = args
        self.priority = priority
        self.obj_key = obj_key
    def __str__(self):
        string = "cmdcandidate <name:'%s',args:'%s', "
        string += "prio:%s, obj_key:'%s'>" 
        return string % (self.cmdname, self.args, self.priority, self.obj_key)
        
#
# The command parser 
#
def cmdparser(raw_string):
    """
    This function parses the raw string into three parts: command
    name(s), keywords(if any) and arguments(if any). It returns a
    CommandCandidates object.  It should be general enough for most
    game implementations, but you can also overwrite it should you
    wish to implement some completely different way of handling and
    ranking commands. Arguments and keywords are parsed/dealt with by
    each individual command's parse() command.

    The cmdparser understand the following command combinations (where
    [] marks optional parts and <char> is one of the SPECIAL_CHARs
    defined globally.):

    [<char>]cmdname[ cmdname2 cmdname3 ...][<char>] [the rest]

    A command may contain spaces, but never any of of the <char>s. A
    command can maximum have CMD_MAXLEN words, or the number of words
    up to the first <char>, whichever is smallest. An exception is if
    <char> is the very first character in the string - the <char> is
    then assumed to be the actual command name (a common use for this
    is for e.g ':' to be a shortcut for 'emote').
    All words not part of the command name is considered a part of the
    command's argument. Note that <char>s ending a command are never
    removed but are included as the first character in the
    argument. This makes it easier for individual commands to identify
    things like switches. Example: '@create/drop ball' finds the
    command name to trivially be '@create' since '/' ends it. As the
    command's arguments are sent '/drop ball'. In this MUX-inspired
    example, '/' denotes a keyword (or switch) and it is now easy for
    the receiving command to parse /drop as a keyword just by looking
    at the first character.
    
    Allowing multiple command names means we have to take care of all
    possible meanings and the result will be a CommandCandidates
    object with up to COMMAND_MAXLEN names stored in it. So if
    COMMAND_MAXLEN was, say, 4, we would have to search all commands
    matching one of 'hit', 'hit orc', 'hit orc with' and 'hit orc with
    sword' - each which are potentially valid commands. Assuming a
    longer written name means being more specific, a longer command
    name takes precedence over a short one.

    There are two optional forms:
    <objname>-[<char>]cmdname[ cmdname2 cmdname3 ...][<char>] [the rest]
    <num>-[<char>]cmdname[ cmdname2 cmdname3 ...][<char>] [the rest]

    This allows for the user to manually choose between unresolvable
    command matches. The main use for this is probably for Exit-commands.
    The <objname>- identifier is used to differentiate between same-named
    commands on different objects. E.g. if a 'watch' and a 'door' both
    have a command 'open' defined on them, the user could differentiate 
    between them with 
      > watch-open
    Alternatively, if they know (and the Multiple-match error reports
    it correctly), the number among the multiples may be picked with 
    the <num>- identifier: 
      > 2-open 

    """    

    def produce_candidates(nr_candidates, wordlist):    
        "Helper function"
        candidates = []
        cmdwords_list = []
        for n_words in range(nr_candidates):                        
            cmdwords_list.append(wordlist.pop(0))
            cmdwords = " ".join([word.strip().lower()
                                 for word in cmdwords_list])            
            args = ""
            for word in wordlist:
                if not args or (word and (REGEX.search(word[0]))):
                    #print "nospace: %s '%s'" % (args, word)
                    args += word                    
                else:
                    #print "space: %s '%s'" % (args, word)
                    args += " %s" % word            
            #print "'%s' | '%s'" % (cmdwords, args)
            candidates.append(CommandCandidate(cmdwords, args, priority=n_words))
        return candidates

    raw_string = raw_string.strip()    
    candidates = []
    
    regex_result = REGEX.search(raw_string)

    if not regex_result == None:
        # there are characters from SPECIAL_CHARS in the string.
        # since they cannot be part of a longer command, these
        # will cut short the command, no matter how long we 
        # allow commands to be.

        end_index = regex_result.start()
        end_char = raw_string[end_index]

        if end_index == 0:
            # There is one exception: if the input *begins* with
            # a special char, we let that be the command name.
            cmdwords = end_char
            if len(raw_string) > 1:
                args = raw_string[1:]
            else:
                args = ""
            candidates.append(CommandCandidate(cmdwords, args))
            return candidates 
        else:
            # the special char occurred somewhere inside the string
            if end_char == "-" and len(raw_string) > end_index+1:
                # the command is on the forms "<num>-command" 
                # or "<word>-command"
                obj_key = raw_string[:end_index]
                alt_string = raw_string[end_index+1:]
                for candidate in cmdparser(alt_string):
                    candidate.obj_key = obj_key
                    candidate.priority =- 1 
                    candidates.append(candidate)
                                     
            # We have dealt with the special possibilities. We now continue
            # in case they where just accidental.
            # We only run the command finder up until the end char
            nr_candidates = len(raw_string[:end_index].split(None))
            if nr_candidates <= COMMAND_MAXLEN:
                wordlist = raw_string[:end_index].split(" ")                
                wordlist.extend(raw_string[end_index:].split(" "))
                #print "%i, wordlist: %s" % (nr_candidates, wordlist) 
                candidates.extend(produce_candidates(nr_candidates, wordlist))
                return candidates

    # if there were no special characters, or that character
    # was not found within the allowed number of words, we run normally
    nr_candidates = min(COMMAND_MAXLEN,
                        len(raw_string.split(None)))                
    wordlist = raw_string.split(" ")           
    candidates.extend(produce_candidates(nr_candidates, wordlist))
    return candidates


#------------------------------------------------------------
# Search parsers and support methods 
#------------------------------------------------------------
#
# Default functions for formatting and processing searches.
#
# This is in its own module due to them being possible to
# replace from the settings file by setting the variables
#
# SEARCH_AT_RESULTERROR_HANDLER
# SEARCH_MULTIMATCH_PARSER 
#
# The the replacing modules must have the same inputs and outputs as
# those in this module.
#

def at_search_result(msg_obj, ostring, results, global_search=False):
    """
    Called by search methods after a result of any type has been found.
    
    Takes a search result (a list) and
    formats eventual errors.

    msg_obj - object to receive feedback. 
    ostring - original search string 
    results - list of found matches (0, 1 or more)
    global_search - if this was a global_search or not
            (if it is, there might be an idea of supplying
            dbrefs instead of only numbers)

    Multiple matches are returned to the searching object
    as 
     1-object
     2-object 
     3-object 
       etc

    """
    string = ""
    if not results: 
        # no results. 
        string = "Could not find '%s'." % ostring
        results = None         

    elif len(results) > 1:
        # we have more than one match. We will display a
        # list of the form 1-objname, 2-objname etc.        

        # check if the msg_object may se dbrefs
        show_dbref = global_search

        string += "More than one match for '%s'" % ostring
        string += " (please narrow target):" 
        for num, result in enumerate(results):
            invtext = ""            
            dbreftext = ""
            if hasattr(result, "location") and result.location == msg_obj:
                invtext = " (carried)"                    
            if show_dbref:
                dbreftext = "(#%i)" % result.id 
            string += "\n %i-%s%s%s" % (num+1, result.name, 
                                        dbreftext, invtext)        
        results = None 
    else:
        # we have exactly one match.
        results = results[0]

    if string: 
        msg_obj.msg(string.strip())
    return results 

def at_multimatch_input(ostring):
    """
    Parse number-identifiers.

    This parser will be called by the engine when a user supplies
    a search term. The search term must be analyzed to determine
    if the user wants to differentiate between multiple matches
    (usually found during a previous search).

    This method should separate out any identifiers from the search
    string used to differentiate between same-named objects. The
    result should be a tuple (index, search_string) where the index
    gives which match among multiple matches should be used (1 being
    the lowest number, rather than 0 as in Python).

    This parser version will identify search strings on the following
    forms 

      2-object 

    This will be parsed to (2, "object") and, if applicable, will tell
    the engine to pick the second from a list of same-named matches of
    objects called "object".

    Ex for use in a game session:

     > look
    You see: ball, ball, ball and ball. 
     > get ball
    There where multiple matches for ball:
        1-ball
        2-ball
        3-ball
        4-ball
     > get 3-ball
     You get the ball. 

    """

    if not isinstance(ostring, basestring):
        return (None, ostring)
    if not '-' in ostring:
        return (None, ostring)
    try: 
        index  = ostring.find('-')
        number = int(ostring[:index])-1
        return (number, ostring[index+1:])
    except ValueError:
        #not a number; this is not an identifier.
        return (None, ostring)
    except IndexError:
        return (None, ostring)
