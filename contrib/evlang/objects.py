"""

Evlang usage examples
 scriptable Evennia base typeclass and @code command

Evennia contribution - Griatch 2012

The ScriptableObject typeclass initiates the Evlang handler on
itself as well as sets up a range of commands to
allow for scripting its functionality. It sets up an access
control system using the 'code' locktype to limit access to
these codes.

The @code command allows to add scripted evlang code to
a ScriptableObject. It will handle access checks.


There are also a few examples of usage - a simple Room
object that has scriptable behaviour when it is being entered
as well as a more generic template for a Craftable object along
with a base crafting command to create it and set it up with
access restrictions making it only scriptable by the original
creator.

"""

from contrib.evlang import evlang
from src.locks.lockhandler import LockHandler
from ev import Object


#------------------------------------------------------------
# Typeclass bases
#------------------------------------------------------------

class ScriptableObject(Object):
    """
    Base class for an object possible to script. By default it defines
    no scriptable types.
    """

    def init_evlang(self):
        """
        Initialize an Evlang handler with access control. Requires
        the evlang_locks attribute to be set to a dictionary with
        {name:lockstring, ...}.
        """
        evl = evlang.Evlang(self)
        evl.lock_storage = ""
        evl.lockhandler = LockHandler(evl)
        for lockstring in self.db.evlang_locks.values():
            evl.lockhandler.add(lockstring)
        return evl

    def at_object_creation(self):
        """
        We add the Evlang handler and sets up
        the needed properties.
        """
        # this defines the available types along with the lockstring
        # restricting access to them. Anything not defined in this
        # dictionary is forbidden to script at all. Just because
        # a script type is -available- does not mean there is any
        # code yet in that slot!
        self.db.evlang_locks = {}
        # This stores actual code snippets. Only code with codetypes
        # matching the keys in db.evlang_locks will work.
        self.db.evlang_scripts = {}
        # store Evlang handler non-persistently
        self.ndb.evlang = self.init_evlang()

    def at_init(self):
        "We must also re-add the handler at server reboots"
        self.ndb.evlang = self.init_evlang()

# Example object types

from ev import Room
class ScriptableRoom(Room, ScriptableObject):
    """
    A room that is scriptable as well as allows users
    to script what happens when users enter it.

    Allowed scripts:
       "enter"  (allowed to be modified by all builders)

    """
    def at_object_creation(self):
        "initialize the scriptable object"
        self.db.evlang_locks = {"enter": "code:perm(Builders)"}
        self.db.evlang_scripts = {}
        self.ndb.evlang = self.init_evlang()

    def at_object_receive(self, obj, source_location):
        "fires a script of type 'enter' (no error if it's not defined)"
        self.ndb.evlang.run_by_name("enter", obj)

