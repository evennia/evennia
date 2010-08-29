"""
Implementation of the @search command that resembles MUX2.
"""
from django.db.models import Q
#from src.objects.models import Object
from src.utils import OBJECT as Object 
from src import defines_global
from src.cmdtable import GLOBAL_CMD_TABLE

def _parse_restriction_split(source_object, restriction_split, search_low_dbnum,
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
            source_object.msg("Invalid value for low dbref limit.")
            return False
    if restriction_size >= 3:
        try:
            search_high_dbnum = int(restriction_split[2].strip())
        except ValueError:
            source_object.msg("Invalid value for high dbref limit.")
            return False
        
    return search_low_dbnum, search_high_dbnum

def display_results(source_object, search_query):
    """
    Display the results to the searcher.
    """
    # Lists to hold results by type. There may be a better way to do this
    thing_list = []
    room_list = []
    exit_list = []
    player_list = []
    # this bits gotta get totally redone 
    for obj in search_query:
        thing_list.append(obj)

    # Render each section for different object types
    if thing_list:
        source_object.msg("\n\rTHINGS:")
        for thing in thing_list:
            source_object.msg(thing.name)
            
    if exit_list:
        source_object.msg("\n\rEXITS:")
        for exit in exit_list:
            source_object.msg(exit.name)
            
    if room_list:
        source_object.msg("\n\rROOMS:")
        for room in room_list:
            source_object.msg(room.name)
            
    if player_list:
        source_object.msg("\n\rPLAYER:")
        for player in player_list:
            source_object.msg(player.name)
            
    # Show the total counts by type
    source_object.msg("\n\rFound:  Rooms...%d  Exits...%d  Things...%d  Players...%d" % (
                                len(room_list),
                                len(exit_list),
                                len(thing_list),
                                len(player_list)))
    
def build_query(source_object, search_query, search_player, search_type, 
                search_restriction, search_low_dbnum, search_high_dbnum):
    """
    Builds and returns a QuerySet object, or None if an error occurs.
    """
    # Look up an Object matching the player search query
    if search_player:
        # Replace the string variable with an Object reference
        search_player = source_object.search_for_object(search_player)
        # Use standard_objsearch to handle duplicate/nonexistant results
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
            source_object.msg("Invalid class. See 'help SEARCH CLASSES'.")
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
        zone_obj = source_object.search_for_object(search_restriction)
        # Use search_for_object to handle duplicate/nonexistant results.
        if not zone_obj:
            return None
        search_query = search_query.filter(zone=zone_obj)
    elif search_type == "power":
        # TODO: Need this once we have powers implemented.
        source_object.msg("To be implemented...")
        return None
    elif search_type == "flags":
        flag_list = search_restriction.split()
        #source_object.msg("restriction: %s" % flag_list)
        for flag in flag_list:
            search_query = search_query.filter(Q(flags__icontains=flag) | Q(nosave_flags__icontains=flag))
    
    if search_low_dbnum:
        search_query = search_query.filter(id__gte=search_low_dbnum)
        
    if search_high_dbnum:
        search_query = search_query.filter(id__lte=search_high_dbnum)
        
    return search_query

def cmd_search(command):
    """
    search

    Usage:
      search <name>

    Searches for owned objects as per MUX2.
    """
    source_object = command.source_object
    
    search_player = None
    search_type = None
    search_restriction = None
    search_low_dbnum = None
    search_high_dbnum = None

    if not command.command_argument:
        search_player = "#" + str(source_object.id)
    else:
        first_check_split = command.command_argument.split(' ', 1)
        if '=' in first_check_split[0]:
            # @search class=restriction...
            eq_split = command.command_argument.split('=', 1)
            search_type = eq_split[0]
            restriction_split = eq_split[1].split(',')
            search_restriction = restriction_split[0].strip()
            #source_object.msg("@search class=restriction")
            #source_object.msg("eq_split: %s" % eq_split)
            #source_object.msg("restriction_split: %s" % restriction_split)
            
            try:
                search_low_dbnum, search_high_dbnum = _parse_restriction_split(source_object,
                                                     restriction_split,
                                                     search_low_dbnum,
                                                     search_high_dbnum)
            except TypeError:
                return
            
        else:
            # @search player
            if len(first_check_split) == 1:
                #source_object.msg("@search player")
                #source_object.msg(first_check_split)
                search_player = first_check_split[0]
            else:
                #source_object.msg("@search player class=restriction")
                #source_object.msg(first_check_split)
                search_player = first_check_split[0]
                eq_split = first_check_split[1].split('=', 1)
                search_type = eq_split[0]
                #source_object.msg("eq_split: %s" % eq_split)
                restriction_split = eq_split[1].split(',')
                search_restriction = restriction_split[0]
                #source_object.msg("restriction_split: %s" % restriction_split)
                
                try:
                    search_low_dbnum, search_high_dbnum = _parse_restriction_split(source_object,
                                                         restriction_split,
                                                         search_low_dbnum,
                                                         search_high_dbnum)
                except TypeError:
                    return  
    
    search_query = Object.objects.all()
        
    #source_object.msg("search_player: %s" % search_player)
    #source_object.msg("search_type: %s" % search_type)
    #source_object.msg("search_restriction: %s" % search_restriction)
    #source_object.msg("search_lowdb: %s" % search_low_dbnum)
    #source_object.msg("search_highdb: %s" % search_high_dbnum)
    
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
    search_query = build_query(source_object, search_query, search_player, search_type, 
                               search_restriction, search_low_dbnum, 
                               search_high_dbnum)
    
    # Something bad happened in query construction, die here.
    if search_query is None:
        return
                
    display_results(source_object, search_query)
GLOBAL_CMD_TABLE.add_command("@search", cmd_search,
                             priv_tuple=("objects.info",),
                             help_category="Building")
