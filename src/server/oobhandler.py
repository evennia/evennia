"""
OOBHandler - Out Of Band Handler

The OOBHandler is called directly by out-of-band protocols. It supplies three
pieces of functionality:

    function execution - the oob protocol can execute a function directly on
                         the server. Only functions specified in settings.OOB_PLUGIN_MODULE.OOB_FUNCS
                         are valid for this use.
    repeat func execution - the oob protocol can request a given function be executed repeatedly
                            at a regular interval.
    tracking - the oob protocol can request Evennia to track changes to fields/properties on
               objects, as well as changes in Attributes. This is done by dynamically adding
               tracker-objects on entities. The behaviour of those objects can be customized
               via settings.OOB_PLUGIN_MODULE.OOB_TRACKERS.

oob functions have the following call signature:
    function(caller, *args, **kwargs)

oob trackers should inherit from the OOBTracker class in this
    module and implement a minimum of the same functionality.

"""

from django.conf import settings
from src.server.models import ServerConfig
from src.server.sessionhandler import SESSIONS
from src.scripts.scripts import Script
from src.create import create_script
from src.utils.dbserialize import dbserialize, dbunserialize, pack_dbobj
from src.utils import logger
from src.utils.utils import variable_from_module, to_str

_SA = object.__setattr__
_GA = object.__getattribute__
_DA = object.__delattribute__

# trackers track property changes and keep returning until they are removed
_OOB_TRACKERS = variable_from_module(settings.OBB_PLUGIN_MODULE, "OBB_TRACKERS", default={})
# functions return immediately
_OOB_FUNCS = variable_from_module(settings.OBB_PLUGIN_MODULE, "OBB_FUNCS", default={})

class OOBTrackerBase(object):
    """
    Base class for OOB Tracker objects. This can be overloaded in settings.to implement
    callback functionality. Stored as a property given by the key in _OOB_TRACKERS or
    by the value of a class variable property_name.
    """
    def __init__(self, obj, *args, **kwargs):
        self.obj = obj
    def update(self, *args, **kwargs):
        "Called by tracked objects"
        pass
    def at_remove(self, *args, **kwargs):
        "Called when OOB is removed, in case cleanup is needed"
        pass

# Default tracker OOB class

class OOBTracker(OOBTrackerBase):
    """
    A OOB object that passively responds whenever
    a named database field, property or attribute
    changes. This is directly supported by Evennia's
    caching mechanism, which looks for hooks stored with
    names on the form
      _at_db_<name>_change - track database field changes
      _at_prop_<name>_change - track other property changes
      _at_attr_<name>_change - track Attribute changes
    and will call the update() method

    OOBHandler launches this tracking with e.g.
     OOBHANDLER.track(obj, "_at_db_key_change", "db_key", "field", sessid)
    """
    def __init__(self, obj, name, sessid, *args, **kwargs):
        """
        obj - the object to store this hook on
        name - name of entity to track, such as "db_key"
        track_type - one of "field", "prop" or "attr" for Database fields,
                     non-database Property or Attribute
        sessid - sessid of session to report to
        """
        self.obj = obj
        self.name = name
        self.sessid = sessid

    def update(self, new_value, *args, **kwargs):
        "Called by cache when updating the tracked entitiy"
        SESSIONS.session_from_sessid(self.sessid).msg(oob={"cmdkey":"trackreturn",
                                                           "name":self.name,
                                                           "value":new_value})


class _RepeaterPool(object):
    """
    This maintains a pool of _RepeaterScript scripts, ordered one per interval. It
    will automatically cull itself once a given interval's script has no more
    subscriptions.
    """

    class _RepeaterScript(Script):
        """
        Repeating script for triggering OOB functions. Maintained in the pool.
        """
        def at_script_creation(self):
            "Called when script is initialized"
            self.key = "oob_func"
            self.desc = "OOB functionality script"
            self.persistent = False #oob scripts should always be non-persistent
            self.ndb.subscriptions = {}

        def at_repeat(self):
            """
            Calls subscriptions every self.interval seconds
            """
            for (func_key, caller, interval, args, kwargs) in self.ndb.subscriptions.values():
                try:
                    _OOB_FUNCS[func_key](caller, *args, **kwargs)
                except Exception:
                    logger.log_trace()

        def subscribe(self, store_key, caller, func_key, interval, *args, **kwargs):
            """
            Sign up a subscriber to this oobfunction. Subscriber is
            a database object with a dbref.
            """
            self.ndb.subscriptions[store_key] = (func_key, caller, interval, args, kwargs)

        def unsubscribe(self, store_key):
            """
            Unsubscribe from oobfunction. Returns True if removal was
            successful, False otherwise
            """
            self.ndb.subscriptions.pop(store_key, None)

    def __init__(self):
        self.scripts = {}

    def add(self, store_key, caller, func_key, interval, *args, **kwargs):
        """
        Add a new tracking
        """
        if interval not in self.scripts:
            # if no existing interval exists, create new script to fill the gap
            new_tracker = create_script(self._RepeaterScript, key="oob_repeater_%is" % interval, interval=interval)
            self.scripts[interval] = new_tracker
        self.scripts[interval].subscribe(store_key, caller, func_key, interval, *args, **kwargs)

    def remove(self, store_key, interval):
        """
        Remove tracking
        """
        if interval in self.scripts:
            self.scripts[interval].unsubscribe(store_key)
            if len(self.scripts[interval].ndb.subscriptions) == 0:
                # no more subscriptions for this interval. Clean out the script.
                self.scripts[interval].stop()


# Default OOB funcs

def OOB_get_attr_val(caller, attrname):
    "Get the given attrback from caller"
    caller.msg(oob={"cmdkey":"get_attr", "value":to_str(caller.attributes.get(attrname))})


# Main OOB Handler

class OOBHandler(object):
    """
    The OOBHandler maintains all dynamic on-object oob hooks. It will store the
    creation instructions and and re-apply them at a server reload (but not after
    a server shutdown)
    """
    def __init__(self):
        """
        Initialize handler
        """
        self.oob_tracker_storage = {}
        self.oob_repeat_storage = {}
        self.oob_tracker_pool = _RepeaterPool()

    def save(self):
        """
        Save the command_storage as a serialized string into a temporary
        ServerConf field
        """
        if self.oob_tracker_storage:
            ServerConfig.objects.conf(key="oob_tracker_storage", value=dbserialize(self.oob_tracker_storage))
        if  self.oob_repeat_storage:
            ServerConfig.objects.conf(key="oob_repeat_storage", value=dbserialize(self.oob_repeat_storage))

    def restore(self):
        """
        Restore the command_storage from database and re-initialize the handler from storage.. This is
        only triggered after a server reload, not after a shutdown-restart
        """
        # load stored command instructions and use them to re-initialize handler
        tracker_storage = ServerConfig.objects.conf(key="oob_tracker_storage")
        if tracker_storage:
            self.oob_tracker_storage = dbunserialize(tracker_storage)
            for tracker_key, (obj, prop_name, args, kwargs) in self.oob_tracker_storage.items():
                self.track(obj, tracker_key, *args, **kwargs)

        repeat_storage = ServerConfig.objects.conf(key="oob_repeat_storage")
        if repeat_storage:
            self.oob_repeat_storage = dbunserialize(repeat_storage)
            for func_key, (caller, func_key, interval, args, kwargs) in self.oob_repeat_storage.items():
                self.repeat(caller, func_key, interval, *args, **kwargs)


    def track(self, obj, tracker_key, property_name=None, *args, **kwargs):
        """
        Create an OOB obj of class _oob_MAPPING[tracker_key] on obj. args,
        kwargs will be used to initialize the OOB hook  before adding
        it to obj.
        If property_key is not given, but the OOB has a class property property_name, this
        will be used as the property name when assigning the OOB to
        obj, otherwise tracker_key is ysed as the property name.
        """
        oobclass = _OOB_TRACKERS[tracker_key] # raise traceback if not found
        prop_name = property_name or (hasattr(oobclass,"property_name") and oobclass.property_name) or tracker_key
        # initialize
        oob = oobclass(obj, *args, **kwargs)
        _SA(obj, prop_name, oob)
        # store calling arguments as a pickle for retrieval later
        storekey = (pack_dbobj(obj), prop_name)
        stored = (obj, prop_name, args, kwargs)
        self.oob_tracker_storage[storekey] = stored

    def untrack(self, obj, tracker_key, *args, **kwargs):
        """
        Remove the OOB from obj. If oob implements an
        at_delete hook, this will be called with args, kwargs
        """
        oobclass = _OOB_TRACKERS[tracker_key] # raise traceback if not found
        prop_name = oobclass.property_name if hasattr(oobclass, "property_name") else tracker_key
        try:
            # call at_delete hook
            _GA(obj, prop_name).at_delete(*args, **kwargs)
        except AttributeError:
            pass
        _DA(obj, prop_name)
        # remove the pickle from storage
        store_key = (pack_dbobj(obj), prop_name)
        self.oob_tracker_storage.pop(store_key, None)

    def track_field(self, obj, sessid, field_name, tracker_key="oobtracker"):
        """
        Shortcut wrapper method for specifically tracking a database field.
        Uses OOBTracker by default (change tracker_key to redirect)
        Will create a tracker with a property name that the field cache
        expects.
        """
        # all database field names starts with db_*
        field_name = field_name if field_name.startswith("db_") else "db_%s" % field_name
        oob_tracker_name = "_track_%s_change" % field_name # field cache looks for name on this form
        self.track(obj, tracker_key, field_name, sessid, property_name=oob_tracker_name)

    def track_attribute(self, obj, sessid, attr_name, tracker_key="oobtracker"):
        """
        Shortcut wrapper method for specifically tracking the changes of an
        Attribute on an object. Will create a tracker on the Attribute Object and
        name in a way the Attribute expects.
        """
        # get the attribute object if we can
        attrobj = _GA(obj, "attributes").get(attr_name, return_obj=True)
        if attrobj:
            oob_tracker_name = "_track_db_value_change"
            self.track(attrobj, tracker_key, attr_name, sessid, property_name=oob_tracker_name)


    def run(self, func_key, *args, **kwargs):
        """
        Retrieve oobfunc from OOB_FUNCS and execute it immediately
        using *args and **kwargs
        """
        oobfunc = _OOB_FUNCS[func_key] # raise traceback if not found
        try:
            oobfunc(*args, **kwargs)
        except Exception:
            logger.log_trace()

    def repeat(self, caller, func_key, interval=20, *args, **kwargs):
        """
        Start a repeating action. Every interval seconds,
        the oobfunc corresponding to func_key is called with
        args and kwargs.
        """
        if not func_key in _OOB_FUNCS:
            raise KeyError("%s is not a valid OOB function name.")
        store_key = (pack_dbobj(caller), func_key, interval)
        # prepare to store
        self.oob_repeat_storage[store_key] = (caller, func_key, interval, args, kwargs)
        self.oob_tracker_pool.add(store_key, caller, func_key, interval, *args, **kwargs)

    def unrepeat(self, caller, func_key, interval=20):
        """
        Stop a repeating action
        """
        store_key = (pack_dbobj(caller), func_key, interval)
        self.oob_tracker_pool.remove(store_key, interval)
        self.oob_repeat_storage.pop(store_key, None)



# access object
OOB_HANDLER = OOBHandler()
