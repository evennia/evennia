"""
This module handles all in-game locks.

A lock object contains a set of criteria (keys). When queried, the
lock tries the tested object/player against these criteria and returns
a True/False result. 
"""
import traceback
from src.objects.models import Object 
from src import logger 

class Key(object):
    """
    This implements a lock key.
    
    Normally the Key is of OR type; if an object matches any criterion in the key,
    the entire key is considered a match. With the 'exact' criterion, all criteria
    contained in the key (except the list of object dbrefs) must also exist in the
    object.
    With the NOT flag the key is inversed, that is, only objects which do not
    match the criterias (exact or not) will be considered to have access.

    Supplying no criteria will make the lock impassable (NOT flag results in an alvays open lock)
    """
    def __init__(self, criteria=[], extra=[], NOT=False, exact=False):
        """
        Defines the basic permission laws
        permlist (list of strings) - permission definitions
        grouplist (list of strings) - group names
        objlist (list of obj or dbrefs) - match individual objects to the lock
        NOT (bool) - invert the lock 
        exact (bool) - objects must match all criteria. Default is OR operation.
        """
        self.criteria = criteria
        self.extra = extra 
        
        #set the boolean operators 
        self.NOT = not NOT 
        self.exact = exact

        # if we have no criteria, this is an impassable lock (or always open if NOT given).
        self.impassable = not(criteria)

    def __str__(self):
        s = ""
        if not self.criteria:
            s += " <Impassable>"
        for crit in self.criteria:
            s += " <%s>" % crit
        return s.strip()
        
    def _result(self, result):
        if self.exact:
            result = result == len(self.criteria)            
        if result:
            return self.NOT
        else:
            return not self.NOT
        
    def check(self, object):
        """
        Compare the object to see if the key matches.
        """
        if self.NOT:            
            return not self.impassable
        return self.impassable

class ObjKey(Key):
    """
    This implements a Key matching against object id
    """
    def check(self, object):
           
        if self.impassable:
            return self.NOT
        if object.dbref() in self.criteria:
            return self.NOT
        else:
            return not self.NOT
    
class GroupKey(Key):
    """
    This key matches against group membership
    """
    def check(self, object):
        if self.impassable: return self.NOT
        user = object.get_user_account()
        if not user: return False
        return self._result(len([g for g in user.groups.all() if str(g) in self.criteria]))
        
class PermKey(Key):
    """
    This key matches against permissions
    """
    def check(self, object):
        if self.impassable: return self.NOT
        user = object.get_user_account()
        if not user: return False
        return self._result(len([p for p in self.criteria if object.has_perm(p)]))

class FlagKey(Key):
    """
    This key use a set of object flagss to define access.
    """
    def check(self, object):
        if self.impassable: return self.NOT
        return self._result(len([f for f in self.criteria if object.has_flag(f)]))
                
class AttrKey(Key):
    """
    This key use a list of arbitrary attributes to define access.

    The attribute names are in the usual criteria. If there is a matching
    list of values in the self.extra list we compare the values directly,
    otherwise we just check for the existence of the attribute. 
    """
    def check(self, object):
        if self.impassable: return self.NOT
        val_list = self.extra 
        attr_list = self.criteria 
        if len(val_list) == len(attr_list):
            return self._result(len([i for i in range(attr_list)
                                if object.get_attribute_value(attr_list[i])==val_list[i]]))
        else:
            return _result(len([a for a in attr_list if object.get_attribute_value(a)]))
        
class Locks(object):
    """
    The Locks object defines an overall grouping of Locks based after type. Each lock
    contains a set of keys to limit access to a certain action.
    The Lock object is stored in the attribute LOCKS on the object in question and the
    engine queries it during the relevant situations.

    Below is a list copied from MUX. Currently Evennia only use 3 lock types:
    Default, Use and Enter; it's not clear if any more are really needed.
    
    Name:          Affects:        Effect:  
    -----------------------------------------------------------------------
    DefaultLock:   Exits:          controls who may traverse the exit to
                                   its destination.
                   Rooms:          controls whether the player sees the SUCC
                                   or FAIL message for the room following the
                                   room description when looking at the room.
                   Players/Things: controls who may GET the object.
     EnterLock:    Players/Things: controls who may ENTER the object if the
                                   object is ENTER_OK. Also, the enter lock
                                   of an object being used as a Zone Master
                                   Object determines control of that zone.
     GetFromLock:  All but Exits:  controls who may gets things from a given
                                   location.
     GiveLock:     Players/Things: controls who may give the object.
     LeaveLock:    Players/Things: controls who may LEAVE the object.
     LinkLock:     All but Exits:  controls who may link to the location if the
                                   location is LINK_OK (for linking exits or
                                   setting drop-tos) or ABODE (for setting
                                   homes)
     MailLock:     Players:        controls who may @mail the player.
     OpenLock:     All but Exits:  controls who may open an exit.
     PageLock:     Players:        controls who may page the player.
     ParentLock:   All:            controls who may make @parent links to the
                                   object.
     ReceiveLock:  Players/Things: controls who may give things to the object.
     SpeechLock:   All but Exits:  controls who may speak in that location
                                   (only checked if AUDITORIUM flag is set
                                   on that location)
     TeloutLock:   All but Exits:  controls who may teleport out of the
                                   location.
     TportLock:    Rooms/Things:   controls who may teleport there if the
                                   location is JUMP_OK.
     UseLock:      All but Exits:  controls who may USE the object, GIVE the
                                   object money and have the PAY attributes
                                   run, have their messages heard and possibly
                                   acted on by LISTEN and AxHEAR, and invoke
                                   $-commands stored on the object.
     DropLock:     All but rooms:  controls who may drop that object.
     UserLock:     All:            Not used by MUX, is intended to be used
                                   in MUX programming where a user-defined
                                   lock is needed.
     VisibleLock:  All:            Controls object visibility when the object
                                   is not dark and the looker passes the lock.
                                   In DARK locations, the object must also be
                                   set LIGHT and the viewer must pass the
                                   VisibleLock.
    """

    def __init__(self):
        """

        The Lock logic is strictly OR. If you want to make access restricted,
        make it so in the respective Key. 
        """
        self.locks = {}

    def __str__(self):
        s = ""
        for lock in self.locks.keys():
            s += " %s" % lock
        return s.strip()

    def add_type(self, ltype, keys=[]):
        """
        type (string) : the type pf lock, like DefaultLock, UseLock etc. 
        keylist = list of Key objects defining who have access. 
        """
        if type(keys) != type(list()):
            keys = [keys]
        self.locks[ltype] = keys

    def del_type(self,ltype):
        """
        Clears a lock. 
        """
        if self.has_type(ltype):
            del self.locks[ltype]
    
    def has_type(self,ltype):
        return self.locks.has_key(ltype)

    def show(self):
        if not self.locks:
            return "No locks."            
        s = ""
        for lock, keys in self.locks.items():
            s += "\n %s\n  " % lock
            for key in keys:
                s += " %s" % key
        return s

    def check(self, ltype, object):
        """
        This is called by the engine. It checks if this lock is of the right type,
        and if so if there is access. If the type does not exist, there is no
        lock for it and thus we return True. 
        """
        if not self.has_type(ltype):
            return True
        result = False 
        for key in self.locks[ltype]:
            try:
                result = result or key.check(object)
            except KeyError:
                pass 
        if not result and object.is_superuser():
            object.emit_to("Lock '%s' - Superuser override." % ltype)
            return True        
        return result 
