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
from django.conf import settings
from src.server.models import ServerConfig
from src.server.sessionhandler import SESSIONS
#from src.scripts.scripts import Script
#from src.utils.create import create_script
from src.scripts.tickerhandler import Ticker, TickerPool, TickerHandler
from src.utils.dbserialize import dbserialize, dbunserialize, pack_dbobj, unpack_dbobj
from src.utils import logger
from src.utils.utils import all_from_module, make_iter, to_str

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
        session.msg(oob=("err", ("ERROR ", errmsg)))
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
        Remove identified tracker from TrackerHandler.
        Raises KeyError if tracker is not found.
        """
        trackerkey = trackerclass.__name__
        tracker = self.tracktargets[fieldname][trackerkey]
        try:
            tracker.at_remove(*args, **kwargs)
        except Exception:
            logger.log_trace()
        del self.tracktargets[fieldname][trackerkey]
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


# On-object Trackers to load with TrackerHandler

class TrackerBase(object):
    """
    Base class for OOB Tracker objects. Inherit from this
    to define custom trackers.
    """
    def __init__(self, *args, **kwargs):
        pass

    def update(self, *args, **kwargs):
        "Called by tracked objects"
        pass

    def at_remove(self, *args, **kwargs):
        "Called when tracker is removed"
        pass


class ReportFieldTracker(TrackerBase):
    """
    Tracker that passively sends data to a stored sessid whenever
    a named database field changes. The TrackerHandler calls this with
    the correct arguments.
    """
    def __init__(self, oobhandler, fieldname, sessid, *args, **kwargs):
        """
        name - name of entity to track, such as "db_key"
        sessid - sessid of session to report to
        """
        self.oobhandler = oobhandler
        self.fieldname = fieldname
        self.sessid = sessid

    def update(self, new_value, *args, **kwargs):
        "Called by cache when updating the tracked entitiy"
        # use oobhandler to relay data
        try:
            # we must never relay objects across the amp, only text data.
            new_value = new_value.key
        except AttributeError:
            new_value = to_str(new_value, force_string=True)
        kwargs[self.fieldname] = new_value
        # this is a wrapper call for sending oob data back to session
        self.oobhandler.msg(self.sessid, "report", *args, **kwargs)


class ReportAttributeTracker(TrackerBase):
    """
    Tracker that passively sends data to a stored sessid whenever
    the Attribute updates. Since the field here is always "db_key",
    we instead store the name of the attribute to return.
    """
    def __init__(self, oobhandler, fieldname, sessid, attrname, *args, **kwargs):
        """
        attrname - name of attribute to track
        sessid - sessid of session to report to
        """
        self.oobhandler = oobhandler
        self.attrname = attrname
        self.sessid = sessid

    def update(self, new_value, *args, **kwargs):
        "Called by cache when attribute's db_value field updates"
        try:
            new_value = new_value.dbobj
        except AttributeError:
            new_value = to_str(new_value, force_string=True)
        kwargs[self.attrname] = new_value
        # this is a wrapper call for sending oob data back to session
        self.oobhandler.msg(self.sessid, "report", *args, **kwargs)



# Ticker of auto-updating objects

class OOBTicker(Ticker):
    """
    Version of Ticker that executes an executable rather than trying to call
    a hook method.
    """
    @inlineCallbacks
    def _callback(self):
        "See original for more info"
        for key, (_, args, kwargs) in self.subscriptions.items():
            # args = (sessid, callback_function)
            session = SESSIONS.session_from_sessid(args[0])
            try:
                # execute the oob callback
                yield args[1](OOB_HANDLER, session, *args[2:], **kwargs)
            except Exception:
                logger.log_trace()

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
            for (obj, sessid, fieldname, trackerclass, args, kwargs) in self.oob_tracker_storage.values():
                #print "restoring tracking:",obj, sessid, fieldname, trackerclass
                self._track(unpack_dbobj(obj), sessid, fieldname, trackerclass, *args, **kwargs)
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
        #print "_track:", obj, id(obj), obj.__dict__

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
            # call at_remove hook on the trackerclass
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
        return [stored for key, stored in self.oob_tracker_storage.items() if key[1] == sessid]

    def track_field(self, obj, sessid, field_name, trackerclass=ReportFieldTracker):
        """
        Shortcut wrapper method for specifically tracking a database field.
        Takes the tracker class as argument.
        """
        # all database field names starts with db_*
        field_name = field_name if field_name.startswith("db_") else "db_%s" % field_name
        self._track(obj, sessid, field_name, trackerclass, field_name)

    def untrack_field(self, obj, sessid, field_name, trackerclass=ReportFieldTracker):
        """
        Shortcut for untracking a database field. Uses OOBTracker by defualt
        """
        field_name = field_name if field_name.startswith("db_") else "db_%s" % field_name
        self._untrack(obj, sessid, field_name, trackerclass)

    def track_attribute(self, obj, sessid, attr_name, trackerclass=ReportAttributeTracker):
        """
        Shortcut wrapper method for specifically tracking the changes of an
        Attribute on an object. Will create a tracker on the Attribute
        Object and name in a way the Attribute expects.
        """
        # get the attribute object if we can
        try:
            attrobj = obj.dbobj
        except AttributeError:
            pass
        attrobj = obj.attributes.get(attr_name, return_obj=True)
        #print "track_attribute attrobj:", attrobj, id(attrobj)
        if attrobj:
            self._track(attrobj, sessid, "db_value", trackerclass, attr_name)

    def untrack_attribute(self, obj, sessid, attr_name, trackerclass=ReportAttributeTracker):
        """
        Shortcut for deactivating tracking for a given attribute.
        """
        try:
            obj = obj.dbobj
        except AttributeError:
            pass
        attrobj = obj.attributes.get(attr_name, return_obj=True)
        if attrobj:
            self._untrack(attrobj, sessid, "db_value", trackerclass, attr_name)

    def repeat(self, obj, sessid, interval=20, callback=None, *args, **kwargs):
        """
        Start a repeating action. Every interval seconds, trigger
        callback(*args, **kwargs). The callback is called with
        args and kwargs; note that *args and **kwargs may not contain
        anything un-picklable (use dbrefs if wanting to use objects).
        """
        self.tickerhandler.add(obj, interval, sessid, callback, *args, **kwargs)

    def unrepeat(self, obj, sessid, interval=20):
        """
        Stop a repeating action
        """
        self.tickerhandler.remove(obj, interval)


    # access method - called from session.msg()

    def execute_cmd(self, session, func_key, *args, **kwargs):
        """
        Retrieve oobfunc from OOB_FUNCS and execute it immediately
        using *args and **kwargs
        """
        oobfunc = _OOB_FUNCS.get(func_key, None)
        if not oobfunc:
            # function not found
            errmsg = "OOB Error: function '%s' not recognized." % func_key
            if _OOB_ERROR:
                _OOB_ERROR(self, session, errmsg, *args, **kwargs)
                logger.log_trace()
            else:
                logger.log_trace(errmsg)
            return

        # execute the found function
        try:
            #print "OOB execute_cmd:", session, func_key, args, kwargs, _OOB_FUNCS.keys()
            oobfunc(self, session, *args, **kwargs)
        except Exception, err:
            errmsg = "OOB Error: Exception in '%s'(%s, %s):\n%s" % (func_key, args, kwargs, err)
            if _OOB_ERROR:
                _OOB_ERROR(self, session, errmsg, *args, **kwargs)
            logger.log_trace(errmsg)
            raise Exception(errmsg)

    def msg(self, sessid, funcname, *args, **kwargs):
        "Shortcut to force-send an OOB message through the oobhandler to a session"
        session = self.sessionhandler.session_from_sessid(sessid)
        #print "oobhandler msg:", sessid, session, funcname, args, kwargs
        if session:
            session.msg(oob=(funcname, args, kwargs))


# access object
OOB_HANDLER = OOBHandler()
