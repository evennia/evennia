"""
OOBHandler - Out Of Band Handler

The OOBHandler is called directly by out-of-band protocols. It supplies three
pieces of functionality:

    function execution - the oob protocol can execute a function directly on
                         the server. The available functions must be defined
                         as global functions via settings.OOB_PLUGIN_MODULES.
    repeat func execution - the oob protocol can request a given function be
                            executed repeatedly at a regular interval. This
                            uses an internal script pool.
    tracking - the oob protocol can request Evennia to track changes to
               fields on objects, as well as changes in Attributes. This is
               done by dynamically adding tracker-objects on entities. The
               behaviour of those objects can be customized via
               settings.OOB_PLUGIN_MODULES.

What goes into the OOB_PLUGIN_MODULES is a list of modules with input
for the OOB system.

oob functions have the following call signature:
    function(caller, *args, **kwargs)

oob trackers should inherit from the OOBTracker class in this
    module and implement a minimum of the same functionality.

a global function oob_error will be used as optional error management.

"""

from inspect import isfunction
from django.conf import settings
from src.server.models import ServerConfig
from src.server.sessionhandler import SESSIONS
from src.scripts.scripts import Script
from src.utils.create import create_script
from src.utils.dbserialize import dbserialize, dbunserialize, pack_dbobj, unpack_dbobj
from src.utils import logger
from src.utils.utils import all_from_module, make_iter

_SA = object.__setattr__
_GA = object.__getattribute__
_DA = object.__delattr__

# load from plugin module
_OOB_FUNCS = {}
for mod in make_iter(settings.OOB_PLUGIN_MODULES):
    _OOB_FUNCS.update(dict((key.lower(), func) for key, func in all_from_module(mod) if isfunction(func)))
_OOB_ERROR = _OOB_FUNCS.get("oob_error", None)


class TrackerHandler(object):
    """
    This object is dynamically assigned to objects whenever one of its fields
    are to be tracked. It holds an internal dictionary mapping to the fields
    on that object. Each field can be tracked by any number of trackers (each
    tied to a different callback).
    """
    def __init__(self, obj):
        """
        This is initiated and stored on the object as a
        property _trackerhandler.
        """
        try:
            obj = obj.dbobj
        except AttributeError:
            pass
        self.obj = obj
        self.ntrackers = 0
        # initiate store only with valid on-object fieldnames
        self.tracktargets = dict((key, {})
                for key in _GA(_GA(self.obj, "_meta"), "get_all_field_names")())

    def add(self, fieldname, tracker):
        """
        Add tracker to the handler. Raises KeyError if fieldname
        does not exist.
        """
        trackerkey = tracker.__class__.__name__
        self.tracktargets[fieldname][trackerkey] = tracker
        self.ntrackers += 1

    def remove(self, fieldname, trackerclass, *args, **kwargs):
        """
        Remove tracker from handler. Raises KeyError if tracker
        is not found.
        """
        trackerkey = trackerclass.__name__
        tracker = self.tracktargets[fieldname][trackerkey]
        try:
            tracker.at_delete(*args, **kwargs)
        except Exception:
            logger.log_trace()
        del tracker
        self.ntrackers -= 1
        if self.ntrackers <= 0:
            # if there are no more trackers, clean this handler
            del self

    def update(self, fieldname, new_value):
        """
        Called by the field when it updates to a new value
        """
        for tracker in self.tracktargets[fieldname].values():
            try:
                tracker.update(new_value)
            except Exception:
                logger.log_trace()


class TrackerBase(object):
    """
    Base class for OOB Tracker objects.
    """
    def __init__(self, *args, **kwargs):
        pass

    def update(self, *args, **kwargs):
        "Called by tracked objects"
        pass

    def at_remove(self, *args, **kwargs):
        "Called when tracker is removed"
        pass


class _RepeaterScript(Script):
    """
    Repeating and subscription-enabled script for triggering OOB
    functions. Maintained in a _RepeaterPool.
    """
    def at_script_creation(self):
        "Called when script is initialized"
        self.key = "oob_func"
        self.desc = "OOB functionality script"
        self.persistent = False  # oob scripts should always be non-persistent
        self.ndb.subscriptions = {}

    def at_repeat(self):
        """
        Calls subscriptions every self.interval seconds
        """
        for (func_key, sessid, interval, args, kwargs) in self.ndb.subscriptions.values():
            session = SESSIONS.session_from_sessid(sessid)
            OOB_HANDLER.execute_cmd(session, func_key, *args, **kwargs)

    def subscribe(self, store_key, sessid, func_key, interval, *args, **kwargs):
        """
        Sign up a subscriber to this oobfunction. Subscriber is
        a database object with a dbref.
        """
        self.ndb.subscriptions[store_key] = (func_key, sessid, interval, args, kwargs)

    def unsubscribe(self, store_key):
        """
        Unsubscribe from oobfunction. Returns True if removal was
        successful, False otherwise
        """
        self.ndb.subscriptions.pop(store_key, None)


class _RepeaterPool(object):
    """
    This maintains a pool of _RepeaterScript scripts, ordered one per
    interval. It will automatically cull itself once a given interval's
    script has no more subscriptions.

    This is used and accessed from oobhandler.repeat/unrepeat
    """

    def __init__(self):
        self.scripts = {}

    def add(self, store_key, sessid, func_key, interval, *args, **kwargs):
        """
        Add a new tracking
        """
        if interval not in self.scripts:
            # if no existing interval exists, create new script to fill the gap
            new_tracker = create_script(_RepeaterScript,
                           key="oob_repeater_%is" % interval, interval=interval)
            self.scripts[interval] = new_tracker
        self.scripts[interval].subscribe(store_key, sessid, func_key,
                                                      interval, *args, **kwargs)

    def remove(self, store_key, interval):
        """
        Remove tracking
        """
        if interval in self.scripts:
            self.scripts[interval].unsubscribe(store_key)
            if len(self.scripts[interval].ndb.subscriptions) == 0:
                # no more subscriptions for this interval. Clean out the script.
                self.scripts[interval].stop()

    def stop(self):
        """
        Stop all scripts in pool. This is done at server reload since
        restoring the pool will automatically re-populate the pool.
        """
        for script in self.scripts.values():
            script.stop()


# Main OOB Handler

class OOBHandler(object):
    """
    The OOBHandler maintains all dynamic on-object oob hooks. It will store the
    creation instructions and and re-apply them at a server reload (but
    not after a server shutdown)
    """
    def __init__(self):
        """
        Initialize handler
        """
        self.sessionhandler = SESSIONS
        self.oob_tracker_storage = {}
        self.oob_repeat_storage = {}
        self.oob_tracker_pool = _RepeaterPool()

    def save(self):
        """
        Save the command_storage as a serialized string into a temporary
        ServerConf field
        """
        if self.oob_tracker_storage:
            #print "saved tracker_storage:", self.oob_tracker_storage
            ServerConfig.objects.conf(key="oob_tracker_storage",
                                    value=dbserialize(self.oob_tracker_storage))
        if  self.oob_repeat_storage:
            #print "saved repeat_storage:", self.oob_repeat_storage
            ServerConfig.objects.conf(key="oob_repeat_storage",
                                     value=dbserialize(self.oob_repeat_storage))
        self.oob_tracker_pool.stop()

    def restore(self):
        """
        Restore the command_storage from database and re-initialize the handler from storage.. This is
        only triggered after a server reload, not after a shutdown-restart
        """
        # load stored command instructions and use them to re-initialize handler
        tracker_storage = ServerConfig.objects.conf(key="oob_tracker_storage")
        if tracker_storage:
            self.oob_tracker_storage = dbunserialize(tracker_storage)
            #print "recovered from tracker_storage:", self.oob_tracker_storage
            for (obj, sessid, fieldname, trackerclass, args, kwargs) in self.oob_tracker_storage.values():
                self.track(unpack_dbobj(obj), sessid, fieldname, trackerclass, *args, **kwargs)
            # make sure to purce the storage
            ServerConfig.objects.conf(key="oob_tracker_storage", delete=True)

        repeat_storage = ServerConfig.objects.conf(key="oob_repeat_storage")
        if repeat_storage:
            self.oob_repeat_storage = dbunserialize(repeat_storage)
            #print "recovered from repeat_storage:", self.oob_repeat_storage
            for (obj, sessid, func_key, interval, args, kwargs) in self.oob_repeat_storage.values():
                self.repeat(unpack_dbobj(obj), sessid, func_key, interval, *args, **kwargs)
            # make sure to purge the storage
            ServerConfig.objects.conf(key="oob_repeat_storage", delete=True)

    def track(self, obj, sessid, fieldname, trackerclass, *args, **kwargs):
        """
        Create an OOB obj of class _oob_MAPPING[tracker_key] on obj. args,
        kwargs will be used to initialize the OOB hook  before adding
        it to obj.
        If property_key is not given, but the OOB has a class property
        property_name, this will be used as the property name when assigning
        the OOB to obj, otherwise tracker_key is used as the property name.
        """
        try:
            obj = obj.dbobj
        except AttributeError:
            pass

        if not "_trackerhandler" in _GA(obj, "__dict__"):
            # assign trackerhandler to object
            _SA(obj, "_trackerhandler", TrackerHandler(obj))
        # initialize object
        tracker = trackerclass(self, fieldname, sessid, *args, **kwargs)
        _GA(obj, "_trackerhandler").add(fieldname, tracker)
        # store calling arguments as a pickle for retrieval later
        obj_packed = pack_dbobj(obj)
        storekey = (obj_packed, sessid, fieldname)
        stored = (obj_packed, sessid, fieldname, trackerclass,  args, kwargs)
        self.oob_tracker_storage[storekey] = stored

    def untrack(self, obj, sessid, fieldname, trackerclass, *args, **kwargs):
        """
        Remove the OOB from obj. If oob implements an
        at_delete hook, this will be called with args, kwargs
        """
        try:
            obj = obj.dbobj
        except AttributeError:
            pass

        try:
            # call at_delete hook
            _GA(obj, "_trackerhandler").remove(fieldname, trackerclass, *args, **kwargs)
        except AttributeError:
            pass
        # remove the pickle from storage
        store_key = (pack_dbobj(obj), sessid, fieldname)
        self.oob_tracker_storage.pop(store_key, None)

    def get_all_tracked(self, session):
        """
        Get the names of all variables this session is tracking.
        """
        sessid = session.sessid
        return [key[2].lstrip("db_") for key in self.oob_tracker_storage.keys() if key[1] == sessid]

    def track_field(self, obj, sessid, field_name, trackerclass):
        """
        Shortcut wrapper method for specifically tracking a database field.
        Takes the tracker class as argument.
        """
        # all database field names starts with db_*
        field_name = field_name if field_name.startswith("db_") else "db_%s" % field_name
        self.track(obj, sessid, field_name, trackerclass)

    def untrack_field(self, obj, sessid, field_name):
        """
        Shortcut for untracking a database field. Uses OOBTracker by defualt
        """
        field_name = field_name if field_name.startswith("db_") else "db_%s" % field_name
        self.untrack(obj, sessid, field_name)

    def track_attribute(self, obj, sessid, attr_name, trackerclass):
        """
        Shortcut wrapper method for specifically tracking the changes of an
        Attribute on an object. Will create a tracker on the Attribute
        Object and name in a way the Attribute expects.
        """
        # get the attribute object if we can
        try:
            obj = obj.dbobj
        except AttributeError:
            pass
        attrobj = _GA(obj, "attributes").get(attr_name, return_obj=True)
        if attrobj:
            self.track(attrobj, sessid, "db_value", trackerclass, attr_name)

    def untrack_attribute(self, obj, sessid, attr_name, trackerclass):
        """
        Shortcut for deactivating tracking for a given attribute.
        """
        try:
            obj = obj.dbobj
        except AttributeError:
            pass
        attrobj = _GA(obj, "attributes").get(attr_name, return_obj=True)
        if attrobj:
            self.untrack(attrobj, sessid, attr_name, trackerclass)

    def repeat(self, obj, sessid, func_key, interval=20, *args, **kwargs):
        """
        Start a repeating action. Every interval seconds,
        the oobfunc corresponding to func_key is called with
        args and kwargs.
        """
        if not func_key in _OOB_FUNCS:
            raise KeyError("%s is not a valid OOB function name.")
        try:
            obj = obj.dbobj
        except AttributeError:
            pass
        store_obj = pack_dbobj(obj)
        store_key = (store_obj, sessid, func_key, interval)
        # prepare to store
        self.oob_repeat_storage[store_key] = (store_obj, sessid, func_key, interval, args, kwargs)
        self.oob_tracker_pool.add(store_key, sessid, func_key, interval, *args, **kwargs)

    def unrepeat(self, obj, sessid, func_key, interval=20):
        """
        Stop a repeating action
        """
        try:
            obj = obj.dbobj
        except AttributeError:
            pass
        store_key = (pack_dbobj(obj), sessid, func_key, interval)
        self.oob_tracker_pool.remove(store_key, interval)
        self.oob_repeat_storage.pop(store_key, None)

    def msg(self, sessid, funcname, *args, **kwargs):
        "Shortcut to relay oob data back to portal. Used by oob functions."
        session = self.sessionhandler.session_from_sessid(sessid)
        #print "oobhandler msg:", sessid, session, funcname, args, kwargs
        if session:
            session.msg(oob=(funcname, args, kwargs))

    # access method - called from session.msg()

    def execute_cmd(self, session, func_key, *args, **kwargs):
        """
        Retrieve oobfunc from OOB_FUNCS and execute it immediately
        using *args and **kwargs
        """
        try:
            #print "OOB execute_cmd:", session, func_key, args, kwargs, _OOB_FUNCS.keys()
            oobfunc = _OOB_FUNCS[func_key]  # raise traceback if not found
            oobfunc(self, session, *args, **kwargs)
        except KeyError,e:
            errmsg = "OOB Error: function '%s' not recognized: %s" % (func_key, e)
            if _OOB_ERROR:
                _OOB_ERROR(self, session, errmsg, *args, **kwargs)
            else:
                logger.log_trace(errmsg)
            raise
        except Exception, err:
            errmsg = "OOB Error: Exception in '%s'(%s, %s):\n%s" % (func_key, args, kwargs, err)
            if _OOB_ERROR:
                _OOB_ERROR(self, session, errmsg, *args, **kwargs)
            else:
                logger.log_trace(errmsg)
            raise
# access object
OOB_HANDLER = OOBHandler()
