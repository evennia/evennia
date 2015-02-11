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
from evennia.server.models import ServerConfig
from evennia.server.sessionhandler import SESSIONS
from evennia.scripts.tickerhandler import Ticker, TickerPool, TickerHandler
from evennia.utils.dbserialize import dbserialize, dbunserialize, pack_dbobj, unpack_dbobj
from evennia.utils import logger
from evennia.utils.utils import all_from_module, make_iter, to_str

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

class FieldTracker(object):
    """
    This object should be stored on the
    tracked object as "_oob_at_<fieldname>_update".
    the update() method will be called by the
    save mechanism, which in turn will call the
    user-customizable func()
    """
    def __init__(self, obj):
        """
        This initializes the tracker with the object it sits on.
        """
        self.obj = obj
        self.subscribers = {}

    def add(self, session):
        """
        Add a subscribing session to the tracker
        """
        self.subscribers[session.sessid] = session

    def remove(self, session):
        """
        Remove a subsribing session from the tracker
        """
        self.subscribers.pop(session.sessid)

    def trigger_update(self, fieldname, new_value):
        """
        Called by the save() mechanism when the given
        field has updated.
        """
        for session in self.subscribers.values():
            try:
                self.at_field_update(session, fieldname, new_value)
            except Exception:
                pass

    def at_field_update(self, session, fieldname, new_value):
        """
        This needs to be overloaded for each tracking
        command.

        Args:
            session (Session): the session subscribing
                to this update.
            fieldname (str): the name of the updated field.
            value (any): the new value now in this field.
        """
        pass


class ReportFieldTracker(FieldTracker):
    """
    Tracker that passively sends data to a stored sessid whenever
    a named database field changes. The TrackerHandler calls this with
    the correct arguments.
    """
    def at_field_update(self, session, fieldname, new_value):
        """
        Called when field updates.
        """
        # we must never relay objects across to the Portal, only
        # text.
        try:
            # it may be an object
            new_value = new_value.key
        except AttributeError:
            # ... or not
            new_value = to_str(new_value, force_string=True)
        # return as an OOB call of type "report"
        session.msg(oob=("report", {fieldname:new_value}))


class ReportAttributeTracker(FieldTracker):
    """
    Tracker that passively sends data to a stored sessid whenever
    the Attribute updates. Since the Attribute's field is always
    db_value, we return the attribute's name instead.
    """
    def at_field_update(self, session, fieldname, new_value):
        """
        Called when field updates.
        """
        # we must never relay objects across to the Portal, only
        # text.
        try:
            # it may be an object
            new_value = new_value.key
        except AttributeError:
            # ... or not
            new_value = to_str(new_value, force_string=True)
        session.msg(oob=("report", {obj.db_key: new_value})



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

class OOBHandler(TickerHandler):

    class AtTick(object):
        """
        A wrapper object with a hook to call at regular intervals
        """
        global SESSIONS, _OOB_FUNCS

        def at_tick(self, oobhandler, cmdname, sessid, *args, **kwargs):
            "Called at regular intervals. Calls the oob function"
            session = SESSIONS.session_from_sessid(sessid):
            cmd = _OOB_FUNCS.get(cmdname, None)
            try:
                cmd(oobhandler, session, *args, **kwargs)
            except Exception:
                logger.log_trace()

    def __init__(self, *args, **kwargs):
        self.save_name = "oob_ticker_storage"
        super(OOBHandler, self).__init__(*args, **kwargs)

    def set_repeat(self, obj, sessid, oobfunc, interval=20, *args, **kwargs):
        """
        Set an oob function to be repeatedly called.

        Args:
            obj (Object) - the object registering the repeat
            sessid (int) - session id of the session registering
            oobfunc (str) - oob function name to call every interval seconds
            interval (int) - interval to call oobfunc, in seconds
            *args, **kwargs - are used as arguments to the oobfunc
        """


    def _track(self, obj, sessid, propname, trackerclass, *args, **kwargs):
        """
        Create an OOB obj of class _oob_MAPPING[tracker_key] on obj. args,
        kwargs will be used to initialize the OOB hook  before adding
        it to obj.
        If propname is not given, but the OOB has a class property
        named as propname, this will be used as the property name when assigning
        the OOB to obj, otherwise tracker_key is used as the property name.
        """
        if not hasattr(obj, "_trackerhandler"):
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
        attrobj = obj.attributes.get(attr_name, return_obj=True)
        #print "track_attribute attrobj:", attrobj, id(attrobj)
        if attrobj:
            self._track(attrobj, sessid, "db_value", trackerclass, attr_name)

    def untrack_attribute(self, obj, sessid, attr_name, trackerclass=ReportAttributeTracker):
        """
        Shortcut for deactivating tracking for a given attribute.
        """
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
