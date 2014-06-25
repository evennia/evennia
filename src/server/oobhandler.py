"""
OOBHandler - Out Of Band Handler

The OOBHandler.execute_cmd is called by the sessionhandler when it detects
an OOB instruction (exactly how this looked depends on the protocol; at this
point all oob calls should look the same)

The handler pieces of functionality:

    function execution - the oob protocol can execute a function directly on
                         the server. The available functions must be defined
                         as global functions in settings.OOB_PLUGIN_MODULES.
    repeat func execution - the oob protocol can request a given function be
                            executed repeatedly at a regular interval. This
                            uses an internal script pool.
    tracking - the oob protocol can request Evennia to track changes to
               fields on objects, as well as changes in Attributes. This is
               done by dynamically adding tracker-objects on entities. The
               behaviour of those objects can be customized by adding new
               tracker classes in settings.OOB_PLUGIN_MODULES.

What goes into the OOB_PLUGIN_MODULES is a (list of) modules that contains
the working server-side code available to the OOB system: oob functions and
tracker classes.

oob functions have the following call signature:
    function(caller, session, *args, **kwargs)

oob trackers should inherit from the OOBTracker class (in this
    module) and implement a minimum of the same functionality.

If a function named "oob_error" is given, this will be called with error
messages.

"""

from inspect import isfunction
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall
from django.conf import settings
from src.server.models import ServerConfig
from src.server.sessionhandler import SESSIONS
#from src.scripts.scripts import Script
#from src.utils.create import create_script
from src.scripts.tickerhandler import Ticker, TickerPool, TickerHandler
from src.utils.dbserialize import dbserialize, dbunserialize, pack_dbobj, unpack_dbobj
from src.utils import logger
from src.utils.utils import all_from_module, make_iter

_SA = object.__setattr__
_GA = object.__getattribute__
_DA = object.__delattr__

# load resources from plugin module
_OOB_FUNCS = {}
for mod in make_iter(settings.OOB_PLUGIN_MODULES):
    _OOB_FUNCS.update(dict((key.lower(), func) for key, func in all_from_module(mod).items() if isfunction(func)))
# get custom error method or use the default
_OOB_ERROR = _OOB_FUNCS.get("oob_error", None)

if not _OOB_ERROR:
    # create default oob error message function
    def oob_error(oobhandler, session, errmsg, *args, **kwargs):
        "Error wrapper"
        session.msg(oob=("send", {"ERROR": errmsg}))
    _OOB_ERROR = oob_error


#
# TrackerHandler is assigned to objects that should notify themselves to
# the OOB system when some property changes. This is never assigned manually
# but automatically through the OOBHandler.
#

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


# Tracker loaded by the TrackerHandler

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

# Ticker of auto-updating objects

class OOBTicker(Ticker):
    """
    Version of Ticker that calls OOB_FUNC rather than trying to call
    a hook method.
    """
    @inlineCallbacks
    def _callback(self, oobhandler, sessions):
        "See original for more info"
        for key, (_, args, kwargs) in self.subscriptions.items():
            session = sessions.session_from_sessid(kwargs.get("sessid"))
            try:
                oobhandler.execute_cmd(session, kwargs.get("func_key"), *args, **kwargs)
            except Exception:
                logger.log_trace()

    def __init__(self, interval):
        "Sets up the Ticker"
        self.interval = interval
        self.subscriptions = {}
        self.task = LoopingCall(self._callback, OOB_HANDLER, SESSIONS)

class OOBTickerPool(TickerPool):
    ticker_class = OOBTicker

class OOBTickerHandler(TickerHandler):
    ticker_pool_class = OOBTickerPool


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
        self.tickerhandler = OOBTickerHandler("oob_ticker_storage")

    def save(self):
        """
        Save the command_storage as a serialized string into a temporary
        ServerConf field
        """
        if self.oob_tracker_storage:
            #print "saved tracker_storage:", self.oob_tracker_storage
            ServerConfig.objects.conf(key="oob_tracker_storage",
                                    value=dbserialize(self.oob_tracker_storage))
        self.tickerhandler.save()

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
            # make sure to purge the storage
            ServerConfig.objects.conf(key="oob_tracker_storage", delete=True)
        self.tickerhandler.restore()

    def _track(self, obj, sessid, propname, trackerclass, *args, **kwargs):
        """
        Create an OOB obj of class _oob_MAPPING[tracker_key] on obj. args,
        kwargs will be used to initialize the OOB hook  before adding
        it to obj.
        If propname is not given, but the OOB has a class property
        named as propname, this will be used as the property name when assigning
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
        tracker = trackerclass(self, propname, sessid, *args, **kwargs)
        _GA(obj, "_trackerhandler").add(propname, tracker)
        # store calling arguments as a pickle for retrieval later
        obj_packed = pack_dbobj(obj)
        storekey = (obj_packed, sessid, propname)
        stored = (obj_packed, sessid, propname, trackerclass,  args, kwargs)
        self.oob_tracker_storage[storekey] = stored

    def _untrack(self, obj, sessid, propname, trackerclass, *args, **kwargs):
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
            _GA(obj, "_trackerhandler").remove(propname, trackerclass, *args, **kwargs)
        except AttributeError:
            pass
        # remove the pickle from storage
        store_key = (pack_dbobj(obj), sessid, propname)
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
        self._track(obj, sessid, field_name, trackerclass)

    def untrack_field(self, obj, sessid, field_name):
        """
        Shortcut for untracking a database field. Uses OOBTracker by defualt
        """
        field_name = field_name if field_name.startswith("db_") else "db_%s" % field_name
        self._untrack(obj, sessid, field_name)

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
            self._track(attrobj, sessid, "db_value", trackerclass, attr_name)

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
            self._untrack(attrobj, sessid, attr_name, trackerclass)

    def repeat(self, obj, sessid, func_key, interval=20, *args, **kwargs):
        """
        Start a repeating action. Every interval seconds,
        the oobfunc corresponding to func_key is called with
        args and kwargs.
        """
        if not func_key in _OOB_FUNCS:
            raise KeyError("%s is not a valid OOB function name.")
        self.tickerhandler.add(self, obj, interval, func_key=func_key, sessid=sessid, *args, **kwargs)

    def unrepeat(self, obj, sessid, func_key, interval=20):
        """
        Stop a repeating action
        """
        self.tickerhandler.remove(self, obj, interval)

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
            print "OOB execute_cmd:", session, func_key, args, kwargs, _OOB_FUNCS.keys()
            oobfunc = _OOB_FUNCS[func_key]  # raise traceback if not found
            oobfunc(self, session, *args, **kwargs)
        except KeyError,e:
            errmsg = "OOB Error: function '%s' not recognized: %s" % (func_key, e)
            if _OOB_ERROR:
                _OOB_ERROR(self, session, errmsg, *args, **kwargs)
            else:
                logger.log_trace(errmsg)
            raise KeyError(errmsg)
        except Exception, err:
            errmsg = "OOB Error: Exception in '%s'(%s, %s):\n%s" % (func_key, args, kwargs, err)
            if _OOB_ERROR:
                _OOB_ERROR(self, session, errmsg, *args, **kwargs)
            else:
                logger.log_trace(errmsg)
            raise Exception(errmsg)
# access object
OOB_HANDLER = OOBHandler()
