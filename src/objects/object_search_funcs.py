"""
Default functions for formatting and processing object searches.

This is in its own module due to them being possible to
replace from the settings file by use of setting the variables

ALTERNATE_OBJECT_SEARCH_ERROR_HANDLER
ALTERNATE_OBJECT_SEARCH_MULTIMATCH_PARSER 

Both the replacing functions must have the same name and same input/output
as the ones in this module. 
"""

def handle_search_errors(emit_to_obj, ostring, results, global_search=False):
    """
    Takes a search result (a list) and
    formats eventual errors.

    emit_to_obj - object to receive feedback. 
    ostring - original search string 
    results - list of object matches, if any 
    global_search - if this was a global_search or not
            (if it is, there might be an idea of supplying
            dbrefs instead of only numbers)
    """
    if not results: 
        emit_to_obj.msg("Could not find '%s'." % ostring)
        return None 
    if len(results) > 1:
        # we have more than one match. We will display a
        # list of the form 1-objname, 2-objname etc.        

        # check if the emit_to_object may se dbrefs
        show_dbref = global_search and \
            emit_to_obj.check_permstring('Builders')

        string = "More than one match for '%s'" % ostring
        string += " (please narrow target):" 
        for num, result in enumerate(results):
            invtext = ""            
            dbreftext = ""
            if result.location == emit_to_obj:
                invtext = " (carried)"                    
            if show_dbref:
                dbreftext = "(#%i)" % result.id 
            string += "\n %i-%s%s%s" % (num+1, result.name, 
                                        dbreftext, invtext)        
        emit_to_obj.msg(string.strip())            
        return None 
    else:
        return results[0]

def object_multimatch_parser(ostring):
    """
    Parse number-identifiers.
    
    Sometimes it can happen that there are several objects in the room
    all with exactly the same key/identifier. Showing dbrefs to
    separate them is not suitable for all types of games since it's
    unique to that object (and e.g. in rp-games the object might not
    want to be identified like that). Instead Evennia allows for
    dbref-free matching by letting the user number which of the
    objects in a multi-match they want.

    Ex for use in game session:

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

    The actual feedback upon multiple matches has to be
    handled by the searching command. The syntax shown above is the
    default.

    For replacing, the method must be named the same and
    take the searchstring as argument and
    return a tuple (int, string) where int is the identifier
    matching which of the results (in order) should be used to
    pick out the right match from the multimatch). Note
    that the engine assumes this number to start with 1 (i.e. not
    zero as in normal Python).
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
