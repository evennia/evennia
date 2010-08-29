"""
This module provides a set of permission lock functions for use
with Evennia's permissions system.

To call these locks, make sure this module is included in the
settings tuple PERMISSION_FUNC_MODULES then define a permission
string of the form 'myfunction(myargs)' and store it in the
'permissions' field or variable on your object/command/channel/whatever.
As part of the permission check, such permission strings will be
evaluated to call myfunction(checking_obj, checked_obj, *yourargs) in
this module. A boolean value is expected back. 

Note that checking_obj and checked_obj can be any object type
with a permissions variable/field, so be careful to not expect
a certain object type. 


MUX locks

Below is a list nicked from the MUX docs on the locks available
in MUX. These are not all necessarily relevant to an Evennia game
but to show they are all possible with Evennia, each entry is a
suggestion on how one could implement similar functionality in Evennia. 

Name:          Affects:        Effect:                                   
-------------------------------------------------------------------------
DefaultLock:   Exits:          controls who may traverse the exit to
                               its destination.
                               Evennia: specialized permission key
                               'traverse' checked in move method
               Rooms:          controls whether the player sees the SUCC
                               or FAIL message for the room following the
                               room description when looking at the room.
                               Evennia: This is better done by implementing
                               a clever room class ...
               Players/Things: controls who may GET the object.
                               Evennia: specialized permission key 'get'
                               defined on object, checked by get command
 EnterLock:    Players/Things: controls who may ENTER the object
                               Evennia: specialized permission key 'enter'
                               defined on object, checked by move command 
 GetFromLock:  All but Exits:  controls who may gets things from a given
                               location.
                               Evennia: Probably done best with a lock function
                               that searches the database for permitted users
 GiveLock:     Players/Things: controls who may give the object.
                               Evennia: specialized permission key 'give'
                               checked by the give command 
 LeaveLock:    Players/Things: controls who may LEAVE the object.
                               Evennia: specialized permission key 'leave'
                               checked by move command 
 LinkLock:     All but Exits:  controls who may link to the location if the
                               location is LINK_OK (for linking exits or
                               setting drop-tos) or ABODE (for setting
                               homes)
                               Evennia: specialized permission key 'link'
                               set on obj and checked by link command 
 MailLock:     Players:        controls who may @mail the player.
                               Evennia: Lock function that pulls the
                               config from the player to see if the
                               calling player is on the blacklist/whitelist
 OpenLock:     All but Exits:  controls who may open an exit.
                               Evennia: specialized permission key 'open'
                               set on exit, checked by open command 
 PageLock:     Players:        controls who may page the player.
                               Evennia: see Maillock 
 ParentLock:   All:            controls who may make @parent links to the
                               object.
                               Evennia: This is handled with typeclasses
                               and typeclass switching instead. 
 ReceiveLock:  Players/Things: controls who may give things to the object.
                               Evennia: See GiveLock
 SpeechLock:   All but Exits:  controls who may speak in that location
                               Evennia: Lock function checking if there
                               is some special restrictions on the room
                               (game dependent)
 TeloutLock:   All but Exits:  controls who may teleport out of the
                               location.
                               Evennia: See LeaveLock
 TportLock:    Rooms/Things:   controls who may teleport there
                               Evennia: See EnterLock 
 UseLock:      All but Exits:  controls who may USE the object, GIVE the
                               object money and have the PAY attributes
                               run, have their messages heard and possibly
                               acted on by LISTEN and AxHEAR, and invoke
                               $-commands stored on the object.
                               Evennia: Implemented per game 
 DropLock:     All but rooms:  controls who may drop that object.
                               Evennia: specialized permission key 'drop'
                               set on room, checked by drop command.
 VisibleLock:  All:            Controls object visibility when the object
                               is not dark and the looker passes the lock.
                               In DARK locations, the object must also be
                               set LIGHT and the viewer must pass the
                               VisibleLock.
                               Evennia: Better done with Scripts implementing
                               a dark state/cmdset. For a single object,
                               use a specialized permission key 'visible'
                               set on object and checked by look command. 

"""

from src.permissions.permissions import get_types, has_perm, has_perm_string
from src.utils import search


def noperm(checking_obj, checked_obj, *args):
    """
    Usage:
       noperm(mypermstring)
       noperm(perm1, perm2, perm3, ...)

    A negative permission; this will return False only if 
    the checking object *has any* of the given permission(s), True
    otherwise. The searched permission cannot itself be a 
    function-permission (i.e. you cannot wrap functions in
    functions). 
    """    
    if not args:
        # this is an always-false permission
        return False
    return not has_perm_string(checking_obj, args)

def is_superuser(checking_obj, checked_obj, *args):
    """
    Usage:
      is_superuser()

    Determines if the checking object is superuser.
    """
    if hasattr(checking_obj, 'is_superuser'):
        return checking_obj.is_superuser
    return False 

def has_id(checking_obj, checked_obj, *args):
    """
    Usage:
      has_id(3)
    
    This lock type checks if the checking object
    has a particular dbref. Note that this only
    works for checking objects that are stored
    in the database (e.g. not for commands)
    """
    if not args:
        return False
    try:
        dbref = int(args[0].strip())
    except ValueError:
        return False
    if hasattr(checking_obj, 'id'):
        return dbref == checking_obj.id
    return False 

def has_attr(checking_obj, checked_obj, *args):
    """
    Usage:
      has_attr(attrname)
      has_attr(attrname, value)

    Searches attributes *and* properties stored on the checking
    object. The first form works like a flag - if the attribute/property
    exists on the object, it returns True. The second form also requires
    that the value of the attribute/property matches. Note that all
    retrieved values will be converted to strings before doing the comparison.     
    """
    # deal with arguments 
    if not args:
        return False
    attrname = args[0].strip()
    value = None 
    if len(args) > 1:
        value = args[1].strip()
    # first, look for normal properties on the object trying to gain access
    if hasattr(checking_obj, attrname):
        if value:
            return str(getattr(checking_obj, attrname)) == value
        return True 
    # check attributes, if they exist
    #print "lockfunc default: %s (%s)" % (checking_obj, attrname)
    if hasattr(checking_obj, 'has_attribute') \
           and checking_obj.has_attribute(attrname):
        if value:
            return hasattr(checking_obj, 'attr') \
                   and checking_obj.attr(attrname) == value
        return True 
    return False 

