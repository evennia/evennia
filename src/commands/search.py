"""
Implementation of the @search command that resembles MUX2.
"""
from django.db.models import Q
from src.objects.models import Object
from src import defines_global

def _parse_restriction_split(session, restriction_split, search_low_dbnum,
                                                         search_high_dbnum):
    """
    Parses a split restriction string and sets some needed variables.
    
    Returns a tuple in the form of: (low dbnum, high dbnum)
    """
    restriction_size = len(restriction_split)
    if restriction_size >= 2:
        try:
            search_low_dbnum = int(restriction_split[1].strip())
        except ValueError:
            session.msg("Invalid value for low dbref limit.")
            return False
    if restriction_size >= 3:
        try:
            search_high_dbnum = int(restriction_split[2].strip())
        except ValueError:
            session.msg("Invalid value for high dbref limit.")
            return False
        
    return search_low_dbnum, search_high_dbnum

def display_results(session, search_query):
    """
    Display the results to the searcher.
    """
    # Lists to hold results by type. There may be a better way to do this
    thing_list = []
    room_list = []
    exit_list = []
    player_list = []
    
    for obj in search_query:
        if obj.is_thing():
            thing_list.append(obj)
        elif obj.is_room():
            room_list.append(obj)
        elif obj.is_exit():
            exit_list.append(obj)
        elif obj.is_player():
            player_list.append(obj)

    # Render each section for different object types
    if thing_list:
        session.msg("\n\rTHINGS:")
        for thing in thing_list:
            session.msg(thing.get_name(show_dbref=True, show_flags=True))
            
    if exit_list:
        session.msg("\n\rEXITS:")
        for exit in exit_list:
            session.msg(exit.get_name(show_dbref=True, show_flags=True))
            
    if room_list:
        session.msg("\n\rROOMS:")
        for room in room_list:
            session.msg(room.get_name(show_dbref=True, show_flags=True))
            
    if player_list:
        session.msg("\n\rPLAYER:")
        for player in player_list:
            session.msg(player.get_name(show_dbref=True, show_flags=True))
            
    # Show the total counts by type
    session.msg("\n\rFound:  Rooms...%d  Exits...%d  Things...%d  Players...%d" % (
                                len(room_list),
                                len(exit_list),
                                len(thing_list),
                                len(player_list)))
    
def build_query(session, search_query, search_player, search_type, 
                search_restriction, search_low_dbnum, search_high_dbnum):
    """
    Builds and returns a QuerySet object, or None if an error occurs.
    """
    # Look up an Object matching the player search query
    if search_player:
        # Replace the string variable with an Object reference
        search_player = Object.objects.standard_plr_objsearch(session, 
                                                              search_player)
        # Use standard_plr_objsearch to handle duplicate/nonexistant results
        if not search_player:
            return None
        
        # Searching by player, chain filter
        search_query = search_query.filter(owner=search_player)
    
    # Check to ensure valid search types
    if search_type == "type":
        if search_restriction == "room":
            search_query = search_query.filter(type=defines_global.OTYPE_ROOM)
        elif search_restriction == "thing":
            search_query = search_query.filter(type=defines_global.OTYPE_THING)
        elif search_restriction == "exit":
            search_query = search_query.filter(type=defines_global.OTYPE_EXIT)
        elif search_restriction == "player":
            search_query = search_query.filter(type=defines_global.OTYPE_PLAYER)
        else:
            session.msg("Invalid class. See 'help SEARCH CLASSES'.")
            return None
    elif search_type == "parent":
        search_query = search_query.filter(script_parent__iexact=search_restriction)
    elif search_type == "object" or search_type == "thing":
        search_query = search_query.filter(name__icontains=search_restriction,
                                           type=defines_global.OTYPE_THING)
    elif search_type == "rooms":
        search_query = search_query.filter(name__icontains=search_restriction,
                                           type=defines_global.OTYPE_ROOM)
    elif search_type == "exits":
        search_query = search_query.filter(name__icontains=search_restriction,
                                           type=defines_global.OTYPE_EXIT)
    elif search_type == "players":
        search_query = search_query.filter(name__icontains=search_restriction,
                                           type=defines_global.OTYPE_PLAYER)
    elif search_type == "zone":
        zone_obj = Object.objects.standard_plr_objsearch(session, 
                                                    search_restriction)
        # Use standard_plr_objsearch to handle duplicate/nonexistant results.
        if not zone_obj:
            return None
        search_query = search_query.filter(zone=zone_obj)
    elif search_type == "power":
        # TODO: Need this once we have powers implemented.
        session.msg("To be implemented...")
        return None
    elif search_type == "flags":
        flag_list = search_restriction.split()
        #session.msg("restriction: %s" % flag_list)
        for flag in flag_list:
            search_query = search_query.filter(Q(flags__icontains=flag) | Q(nosave_flags__icontains=flag))
    
    if search_low_dbnum:
        search_query = search_query.filter(id__gte=search_low_dbnum)
        
    if search_high_dbnum:
        search_query = search_query.filter(id__lte=search_high_dbnum)
        
    return search_query

def cmd_search(command):
    """
    Searches for owned objects as per MUX2.
    """
    session = command.session
    pobject = session.get_pobject()
    
    search_player = None
    search_type = None
    search_restriction = None
    search_low_dbnum = None
    search_high_dbnum = None

    if not command.command_argument:
        search_player = "#" + str(pobject.id)
    else:
        first_check_split = command.command_argument.split(' ', 1)
        if '=' in first_check_split[0]:
            # @search class=restriction...
            eq_split = command.command_argument.split('=', 1)
            search_type = eq_split[0]
            restriction_split = eq_split[1].split(',')
            search_restriction = restriction_split[0].strip()
            #session.msg("@search class=restriction")
            #session.msg("eq_split: %s" % eq_split)
            #session.msg("restriction_split: %s" % restriction_split)
            
            try:
                search_low_dbnum, search_high_dbnum = _parse_restriction_split(session,
                                                     restriction_split,
                                                     search_low_dbnum,
                                                     search_high_dbnum)
            except TypeError:
                return
            
        else:
            # @search player
            if len(first_check_split) == 1:
                #session.msg("@search player")
                #session.msg(first_check_split)
                search_player = first_check_split[0]
            else:
                #session.msg("@search player class=restriction")
                #session.msg(first_check_split)
                search_player = first_check_split[0]
                eq_split = first_check_split[1].split('=', 1)
                search_type = eq_split[0]
                #session.msg("eq_split: %s" % eq_split)
                restriction_split = eq_split[1].split(',')
                search_restriction = restriction_split[0]
                #session.msg("restriction_split: %s" % restriction_split)
                
                try:
                    search_low_dbnum, search_high_dbnum = _parse_restriction_split(session,
                                                         restriction_split,
                                                         search_low_dbnum,
                                                         search_high_dbnum)
                except TypeError:
                    return  
    
    search_query = Object.objects.all()
        
    #session.msg("search_player: %s" % search_player)
    #session.msg("search_type: %s" % search_type)
    #session.msg("search_restriction: %s" % search_restriction)
    #session.msg("search_lowdb: %s" % search_low_dbnum)
    #session.msg("search_highdb: %s" % search_high_dbnum)
    
    # Clean up these variables for comparisons.
    try:
        search_type = search_type.strip().lower()
    except AttributeError:
        pass
    try:
        search_restriction = search_restriction.strip().lower()
    except AttributeError:
        pass
    
    # Build the search query.
    search_query = build_query(session, search_query, search_player, search_type, 
                               search_restriction, search_low_dbnum, 
                               search_high_dbnum)
    
    # Something bad happened in query construction, die here.
    if search_query is None:
        return
                
    display_results(session, search_query)