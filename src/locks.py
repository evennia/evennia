"""
This module handles all in-game locks.

A lock object contains a set of criteria (keys). When queried, the
lock tries the tested object/player against these criteria and returns
a True/False result. 
"""

from src.objects.models import Object 

class Key(object):
    """
    This implements a lock key.
    
    Normally the Key is of OR type; if an object matches any criterion in the key,
    the entire key is considered a match. With the 'exact' criterion, all criteria
    contained in the key (except the list of object dbrefs) must also exist in the
    object.
    With the invert_result flag the key is inversed, that is, only objects which do not
    match the criteria (exact or not) will be considered to have access.

    Supplying no criteria will make the lock impassable (invert_result flag results in an alvays open lock)
    """
    def __init__(self, criteria=[], extra=None, invert_result=False, exact=False):
        """
        Defines the basic permission laws
        permlist (list of strings) - permission definitions
        grouplist (list of strings) - group names
        objlist (list of obj or dbrefs) - match individual objects to the lock
        invert_result (bool) - invert the lock 
        exact (bool) - objects must match all criteria. Default is OR operation.
        """
        self.criteria = criteria
        self.extra = extra 
        
        #set the boolean operators 
        self.invert_result = not invert_result 
        self.exact = exact

        # if we have no criteria, this is an impassable lock
        # (or always open if invert_result given).
        self.impassable = not(criteria)

    def __str__(self):
        string = " "
        if not self.criteria:
            string += " <Impassable>"
        for crit in self.criteria:
            string += " %s," % crit
        return string[:-1].strip()
        
    def _result(self, result):
        "Return result depending on exact criterion."
        if self.exact:
            result = result == len(self.criteria)            
        if result:
            return self.invert_result
        else:
            return not self.invert_result
        
    def check(self, obj):
        """
        Compare the object to see if the key matches.
        """
        if self.invert_result:            
            return not self.impassable
        return self.impassable

class ObjKey(Key):
    """
    This implements a Key matching against object id
    """
    def check(self, obj):
        "Checks object against the key."           
        if self.impassable:
            return self.invert_result
        if obj.dbref() in self.criteria:
            return self.invert_result
        else:
            return not self.invert_result
    
class GroupKey(Key):
    """
    This key matches against group membership
    """
    def check(self, obj):
        "Checks object against the key."
        if self.impassable:
            return self.invert_result
        user = obj.get_user_account()
        if not user:
            return False
        return self._result(len([g for g in user.groups.all()
                                 if str(g) in self.criteria]))
        
class PermKey(Key):
    """
    This key matches against permissions
    """
    def check(self, obj):
        "Checks object against the key."
        if self.impassable:
            return self.invert_result
        user = obj.get_user_account()
        if not user:
            return False
        return self._result(len([p for p in self.criteria
                                 if obj.has_perm(p)]))

class FlagKey(Key):
    """
    This key use a set of object flags to define access.
    Only if the trying object has the correct flags will
    it pass the lock. 
    self.criterion holds the flag names
    """
    def __str__(self):
        string = " "
        if not self.criteria:
            string += " <Impassable>"
        for crit in self.criteria:
            string += " obj.%s," % str(crit).upper()
        return string[:-1].strip()
    
    def check(self, obj):
        "Checks object against the key."
        if self.impassable:
            return self.invert_result
        return self._result(len([f for f in self.criteria
                                 if obj.has_flag(f)]))
                
class AttrKey(Key):
    """
    This key use a list of arbitrary attributes to define access.

    self.criteria contains a list of tuples [(attrname, value),...].
    The attribute with the given name must match the given value in
    order to pass the lock. 
    """
    def __str__(self):
        string = " "
        if not self.criteria:
            string += " <Impassable>"
        for crit in self.criteria:
            string += " obj.%s=%s," % (crit[0],crit[1])
        return string[:-1].strip()

    def check(self, obj):
        "Checks object against the key."

        if self.impassable:
            return self.invert_result

        return self._result(len([tup for tup in self.criteria
                                 if len(tup)>1 and
                                 obj.get_attribute_value(tup[0]) == tup[1]]))

class FuncKey(Key):
    """
    This Key stores a set of function names and return values. The matching
    of those return values depend on the function (defined on the locked object) to
    return a matching value to the one stored in the key    

    The relevant data is stored in the key in this format:
    self.criteria = list of (funcname, return_value) tuples, where funcname
                    is a function to be called on the locked object.
                    This function func(obj) takes the calling object
                    as argument and only
                    if its return value matches the one set in the tuple
                    will the lock be passed. Note that the return value
                    can, in the case of locks set with @lock, only be
                    a string, so in the comparison we do a string
                    conversion of the return values. 
    self.index contains the locked object's dbref. 
    """
    def __str__(self):
        string = ""
        if not self.criteria:
            string += " <Impassable>"
        for crit in self.criteria:
            string += " lockobj.%s(obj) => %s" % (crit[0],crit[1])
        return string.strip()

    def check(self, obj):
        "Checks object against the stored locks."
        if self.impassable:
            return self.invert_result

        # we need the locked object since the lock-function is defined on it. 
        lock_obj = Object.objects.dbref_search(self.extra)
        if not lock_obj:
            return self.invert_result

        # build tuples of functions and their return values
        ftuple_list = [(getattr(lock_obj.scriptlink, tup[0], None),
                        tup[1]) for tup in self.criteria
                       if len(tup) > 1]
        
        # loop through the comparisons. Convert to strings before
        # doing the comparison. 
        return self._result(len([ftup for ftup in ftuple_list
                                if callable(ftup[0]) and
                                str(ftup[0](obj)) == str(ftup[1])]))
                
class Locks(object):
    """
    The Locks object defines an overall grouping of Locks based after type.
    The Locks object is stored in the reserved attribute LOCKS on the locked object.
    Each Locks instance stores a set of keys for each Lock type, normally
    created using the @lock command in-game. The engine queries Locks.check()
    with an object as argument in order to determine if the object has access. 

    Below is a list of Lock-types copied from MUX. Currently Evennia only use
    3 lock types: Default, Use and Enter; it's not clear if any more are really
    needed.
    
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
        string = ""
        for lock in self.locks.keys():
            string += " %s" % lock
        return string.strip()

    def add_type(self, ltype, keys=[]):
        """
        type (string) : the type pf lock, like DefaultLock, UseLock etc. 
        keylist = list of Key objects defining who have access. 
        """
        if type(keys) != type(list()):
            keys = [keys]
        self.locks[ltype] = keys

    def del_type(self, ltype):
        """
        Clears a lock. 
        """
        if self.has_type(ltype):
            del self.locks[ltype]
    
    def has_type(self, ltype):
        "Checks if LockType ltype exists in the lock."
        return self.locks.has_key(ltype)

    def show(self):
        """
        Displays a fancier view of the stored locks and their keys. 
        """
        if not self.locks:
            return "No locks."            
        string = " "
        for lock, keys in self.locks.items():
            string += "\n %s\n  " % lock
            for key in keys:
                string += " %s," % key
            string = string[:-1]
        return string

    def check(self, ltype, obj):
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
                result = result or key.check(obj)
            except KeyError:
                pass 
        if not result and obj.is_superuser():
            obj.emit_to("Lock '%s' - Superuser override." % ltype)
            return True        
        return result 
