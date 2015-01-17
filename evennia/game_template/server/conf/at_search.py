"""
Search and multimatch handling

This module allows for overloading two functions used by Evennia's
search functionality:

    at_search_result:
        This is called whenever a result is returned from an object
        search (a common operation in commands).  It should (together
        with at_multimatch_input below) define some way to present and
        differentiate between multiple matches (by default these are
        presented as 1-ball, 2-ball etc)
    at_multimatch_input:
        This is called with a search term and should be able to
        identify if the user wants to separate a multimatch-result
        (such as that from a previous search). By default, this
        function understands input on the form 1-ball, 2-ball etc as
        indicating that the 1st or 2nd match for "ball" should be
        used.

This module is not called by default. To overload the defaults, add
one or both of the following lines to your settings.py file:

    SEARCH_AT_RESULT = "server.conf.at_search.at_search_result"
    SEARCH_AT_MULTIMATCH_INPUT = "server.conf.at_search.at_multimatch_input"

"""

def at_search_result(msg_obj, ostring, results, global_search=False,
                     nofound_string=None, multimatch_string=None, quiet=False):
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
    nofound_string - optional custom string for not-found error message.
    multimatch_string - optional custom string for multimatch error header
    quiet - work normally, but don't echo to caller, just return the
            results.

    Multiple matches are returned to the searching object
    as a list of results ["1-object", "2-object","3-object",...]
    A single match is returned on its own.
    """
    pass


def at_multimatch_input(ostring):
    """
    This parser will be called by the engine when a user supplies
    a search term. The search term must be analyzed to determine
    if the user wants to differentiate between multiple matches
    (usually found during a previous search).

    This method should separate out any identifiers from the search
    string used to differentiate between same-named objects. The
    result should be a tuple (index, search_string) where the index
    gives which match among multiple matches should be used (1 being
    the lowest number, rather than 0 as in Python).

    The default parser will intercept input on the following form:

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
    pass
