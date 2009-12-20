"""
This module offers a collection of useful general functions from the
game engine to make things easier to find.
Just import game.gamesrc.utils and refer to the globals defined herein.

Note that this is not intended as a comprehensive collection, merely
a convenient place to refer to for the methods we have found to be
often used. You will still have to refer to the modules
in evennia/src for more specialized operations. 

You will also want to be well familiar with all the facilities each
object offers. The object model is defined in src/objects/models.py.
"""
#------------------------------------------------------------
# imports
#------------------------------------------------------------

from django.conf import settings as in_settings
from src import logger
from src import scheduler as in_scheduler
from src.objects.models import Object
from src import defines_global
from src.cmdtable import GLOBAL_CMD_TABLE as in_GLOBAL_CMD_TABLE
from src.statetable import GLOBAL_STATE_TABLE as in_GLOBAL_STATE_TABLE
from src.events import IntervalEvent as in_IntervalEvent 

#------------------------------------------------------------
# Import targets
#------------------------------------------------------------

settings = in_settings
GLOBAL_CMD_TABLE = in_GLOBAL_CMD_TABLE
GLOBAL_STATE_TABLE = in_GLOBAL_STATE_TABLE

# Events 
scheduler = in_scheduler
IntervalEvent = in_IntervalEvent


#------------------------------------------------------------
# Log to file/stdio
#   log_xxxmsg(msg)
#------------------------------------------------------------

log_errmsg = logger.log_errmsg
log_warnmsg = logger.log_warnmsg
log_infomsg = logger.log_infomsg 


#------------------------------------------------------------ 
# Search methods
#------------------------------------------------------------

# NOTE: All objects also has search_for_object() defined
# directly on themselves, which is a convenient entryway into a
# local and global search with automatic feedback to the
# calling player.

# def get_object_from_dbref(dbref):
#    Returns an object when given a dbref.
get_object_from_dbref = Object.objects.get_object_from_dbref

# def dbref_search(dbref_string, limit_types=False):
#    Searches for a given dbref.
dbref_search = Object.objects.dbref_search

# def global_object_name_search(ostring, exact_match=True, limit_types=[]):
#    Searches through all objects for a name match.
global_object_name_search = Object.objects.global_object_name_search

# def global_object_script_parent_search(script_parent):
#    Searches through all objects returning those which has a certain script parent.
global_object_script_parent_search = Object.objects.global_object_script_parent_search

# def player_name_search(searcher, ostring):
#    Search players by name.
player_name_search = Object.objects.player_name_search

# def local_and_global_search(searcher, ostring, search_contents=True, 
#                             search_location=True, dbref_only=False, 
#                             limit_types=False, attribute_name=None):
#    Searches an object's location then globally for a dbref or name match.
local_and_global_search = Object.objects.local_and_global_search


#------------------------------------------------------------
# Creation commands
#------------------------------------------------------------

# def create_object(name, otype, location, owner, home=None, script_parent=None):
#    Create a new object
create_object = Object.objects.create_object

# def copy_object(original_object, new_name=None, new_location=None, reset=False):
#     Create and return a new object as a copy of the source object. All will
#     be identical to the original except for the dbref. Does not allow the
#     copying of Player objects.
copy_object = Object.objects.copy_object


#------------------------------------------------------------
# Validation
#------------------------------------------------------------

# NOTE: The easiest way to check if an object
# is of a particular type is to use each object's
# is_X() function, like is_superuser(), is_thing(),
# is_room(), is_player(), is_exit() and get_type().
        
OTYPE_NOTHING = defines_global.OTYPE_NOTHING 
OTYPE_PLAYER = defines_global.OTYPE_PLAYER
OTYPE_ROOM = defines_global.OTYPE_ROOM
OTYPE_THING = defines_global.OTYPE_THING
OTYPE_EXIT = defines_global.OTYPE_EXIT
OTYPE_GOING = defines_global.OTYPE_GOING
TYPE_GARBAGE = defines_global.OTYPE_GARBAGE 

NOPERMS_MSG = defines_global.NOPERMS_MSG
NOCONTROL_MSG = defines_global.NOCONTROL_MSG

# def is_dbref(self, dbstring, require_pound=True):
#    Is the input a well-formed dbref number?
is_dbref = Object.objects.is_dbref
