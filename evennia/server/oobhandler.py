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
from collections import defaultdict
from django.conf import settings
from evennia.server.models import ServerConfig
from evennia.server.sessionhandler import SESSIONS
from evennia.scripts.tickerhandler import TickerHandler
from evennia.utils.dbserialize import dbserialize, dbunserialize, pack_dbobj, unpack_dbobj
from evennia.utils import logger
from evennia.utils.utils import all_from_module, make_iter

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

class OOBFieldMonitor(object):
    """
    This object should be stored on the
    tracked object as "_oob_at_<fieldname>_update".
    the update() method will be called by the
    save mechanism, which in turn will call the
    user-customizable func()
    """
    def __init__(self):
        """
        This initializes the monitor with the object it sits on.
        """
        self.subscribers = defaultdict(list)

    def __call__(self, new_value, obj):
        """
        Called by the save() mechanism when the given
        field has updated.
        """
        for sessid, (oobfuncname, args, kwargs) in self.subscribers.items():
            OOB_HANDLER.execute_cmd(sessid, oobfuncname, new_value, obj=obj, *args, **kwargs)

    def add(self, sessid, oobfuncname, *args, **kwargs):
        """
        Add a specific tracking callback to monitor

        Args:
            sessid (int): Session id
            oobfuncname (str): oob command to call when field updates
            args,kwargs: arguments to pass to oob commjand

        Notes:
            Each sessid may have a list of (oobfuncname, args, kwargs)
            tuples, all of which will be executed when the
            field updates.
        """
        self.subscribers[sessid].append((oobfuncname, args, kwargs))

    def remove(self, sessid, oobfuncname=None):
        """
        Remove a subscribing session from the monitor

        Args:
            sessid(int): Session id
        Keyword Args:
            oobfuncname (str, optional): Only delete this cmdname.
                If not given, delete all.

        """
        if oobfuncname:
            self.subscribers[sessid] = [item for item in self.subscribers[sessid]
                                        if item[0] != oobfuncname]
        else:
            self.subscribers.pop(sessid, None)


class OOBAtRepeat(object):
    """
    This object should be stored on a target object, named
    as the hook to call repeatedly, e.g.

    _oob_listen_every_20s_for_sessid_1 = AtRepat()
    """

    def __call__(self, sessid, oobfuncname, *args, **kwargs):
        "Called at regular intervals. Calls the oob function"
        OOB_HANDLER.execute_cmd(sessid, oobfuncname, *args, **kwargs)


# Main OOB Handler

class OOBHandler(TickerHandler):
    """
    The OOBHandler manages all server-side OOB functionality
    """

    def __init__(self, *args, **kwargs):
        self.save_name = "oob_ticker_storage"
        self.oob_save_name = "oob_monitor_storage"
        self.oob_monitor_storage = {}
        super(OOBHandler, self).__init__(*args, **kwargs)

    def _get_repeat_hook_name(self, oobfuncname, interval, sessid):
        "Return the unique repeat call hook name for this object"
        return "_oob_%s_every_%ss_for_sessid_%s" % (oobfuncname, interval, sessid)

    def _get_fieldmonitor_name(self, fieldname):
        "Return the fieldmonitor name"
        return "_oob_at_%s_postsave" % fieldname

    def _add_monitor(self, obj, sessid, fieldname, oobfuncname, *args, **kwargs):
        """
        Create a fieldmonitor and store it on the object. This tracker
        will be updated whenever the given field changes.
        """
        fieldmonitorname = self._get_fieldtracker_name(fieldname)
        if not hasattr(obj, fieldmonitorname):
            # assign a new fieldmonitor to the object
            _SA(obj, fieldmonitorname, OOBFieldMonitor())
        # register the session with the monitor
        _GA(obj, fieldmonitorname).add(sessid, oobfuncname, *args, **kwargs)

        # store calling arguments as a pickle for retrieval at reload
        storekey = (pack_dbobj(obj), sessid, fieldname, oobfuncname)
        stored = (args, kwargs)
        self.oob_monitor_storage[storekey] = stored

    def _remove_monitor(self, obj, sessid, fieldname, oobfuncname=None):
        """
        Remove the OOB from obj. If oob implements an
        at_delete hook, this will be called with args, kwargs
        """
        fieldmonitorname = self._get_fieldtracker_name(fieldname)
        try:
            _GA(obj, fieldmonitorname).remove(sessid, oobfuncname=oobfuncname)
            if not _GA(obj, fieldmonitorname).subscribers:
                _DA(obj, fieldmonitorname)
        except AttributeError:
            pass
        # remove the pickle from storage
        store_key = (pack_dbobj(obj), sessid, fieldname, oobfuncname)
        self.oob_monitor_storage.pop(store_key, None)

    def save(self):
        """
        Handles saving of the OOBHandler data when the server reloads.
        Called from the Server process.
        """
        # save ourselves as a tickerhandler
        super(OOBHandler, self).save()
        # handle the extra oob monitor store
        if self.ticker_storage:
            ServerConfig.objects.conf(key=self.oob_save_name,
                                      value=dbserialize(self.oob_monitor_storage))
        else:
            # make sure we have nothing lingering in the database
            ServerConfig.objects.conf(key=self.oob_save_name, delete=True)

    def restore(self):
        """
        Called when the handler recovers after a Server reload. Called
        by the Server process as part of the reload upstart. Here we
        overload the tickerhandler's restore method completely to make
        sure we correctly re-apply and re-initialize the correct
        monitor and repeat objects on all saved objects.
        """
        # load the oob monitors and initialize them
        oob_storage = ServerConfig.objects.conf(key=self.oob_save_name)
        if oob_storage:
            self.oob_storage = dbunserialize(oob_storage)
            for store_key, (args, kwargs) in self.oob_storage.items():
                # re-create the monitors
                obj, sessid, fieldname, oobfuncname = store_key
                obj = unpack_dbobj(obj)
                self._add_monitor(obj, sessid, fieldname, oobfuncname, *args, **kwargs)
        # handle the tickers (same as in TickerHandler except we  call
        # the add_repeat method which makes sure to add the hooks before
        # starting the tickerpool)
        ticker_storage = ServerConfig.objects.conf(key=self.save_name)
        if ticker_storage:
            self.ticker_storage = dbunserialize(ticker_storage)
            for store_key, (args, kwargs) in self.ticker_storage.items():
                obj, interval, idstring = store_key
                obj = unpack_dbobj(obj)
                # we saved these in add_repeat before, can now retrieve them
                sessid = kwargs["sessid"]
                oobfuncname = kwargs["oobfuncname"]
                self.add_repeat(obj, sessid, oobfuncname, interval, *args, **kwargs)

    def add_repeat(self, obj, sessid, oobfuncname, interval=20, *args, **kwargs):
        """
        Set an oob function to be repeatedly called.

        Args:
            obj (Object) - the object on which to register the repeat
            sessid (int) - session id of the session registering
            oobfuncname (str) - oob function name to call every interval seconds
            interval (int) - interval to call oobfunc, in seconds
            *args, **kwargs - are used as arguments to the oobfunc
        """
        hook = OOBAtRepeat()
        hookname = self._get_repeat_hook_name(oobfuncname, interval, sessid)
        _SA(obj, hookname, hook)
        kwargs.update({"sessid":sessid, "oobfuncname":oobfuncname})
        # we store these in kwargs so that tickerhandler saves them with the rest
        kwargs["sessid"] = sessid
        kwargs["oobfuncbame"] = oobfuncname
        self.add(obj, interval, idstring=oobfuncname, hook_key=hookname, *args, **kwargs)

    def remove_repeat(self, obj, sessid, oobfuncname, interval=20):
        """
        Remove the repeatedly calling oob function

        Args:
            obj (Object): The object on which the repeater sits
            sessid (int): Session id of the Session that registered the repeat
            oob

        """
        self.remove(obj, interval, idstring=oobfuncname)
        hookname = self._get_repeat_hook_name(oobfuncname, interval, sessid)
        try:
            _DA(obj, hookname)
        except AttributeError:
            pass

    def add_field_monitor(self, obj, sessid, field_name, oobfuncname, *args, **kwargs):
        """
        Add a monitor tracking a database field

        Args:
            obj (Object): The object who'se field is to be monitored
            sessid (int): Session if of the session monitoring
            field_name (str): Name of database field to monitor. The db_* can optionally
                be skipped (it will be automatically appended if missing)
            oobfuncname (str): OOB function to call when field changes

        Notes:
            The optional args, and kwargs will be passed on to the
            oobfunction.
        """
        # all database field names starts with db_*
        field_name = field_name if field_name.startswith("db_") else "db_%s" % field_name
        self._add_monitor(obj, sessid, field_name, field_name, oobfuncname=None)

    def remove_field_monitor(self, obj, sessid, field_name, oobfuncname=None):
        """
        Un-tracks a database field

        Args:
            obj (Object): Entity with the monitored field
            sessid (int): Session id of session that monitors
            field_name (str): database field monitored (the db_* can optionally be
                skipped (it will be auto-appended if missing)
            oobfuncname (str, optional): OOB command to call on that field

        """
        field_name = field_name if field_name.startswith("db_") else "db_%s" % field_name
        self._remove_monitor(obj, sessid, field_name, oobfuncname=oobfuncname)

    def add_attribute_track(self, obj, sessid, attr_name, oobfuncname):
        """
        Monitor the changes of an Attribute on an object. Will trigger when
        the Attribute's `db_value` field updates.

        Args:
            obj (Object): Object with the Attribute to monitor.
            sessid (int): Session id of monitoring Session.
            attr_name (str): Name (key) of Attribute to monitor.
            oobfuncname (str): OOB function to call when Attribute updates.

        """
        # get the attribute object if we can
        attrobj = obj.attributes.get(attr_name, return_obj=True)
        if attrobj:
            self._add_monitor(attrobj, sessid, "db_value", oobfuncname)

    def remove_attribute_monitor(self, obj, sessid, attr_name, oobfuncname):
        """
        Deactivate tracking for a given object's Attribute

        Args:
            obj (Object): Object monitored.
            sessid (int): Session id of monitoring Session.
            attr_name (str): Name of Attribute monitored.
            oobfuncname (str): OOB function name called when Attribute updates.

        """
        attrobj = obj.attributes.get(attr_name, return_obj=True)
        if attrobj:
            self._remove_monitor(attrobj, sessid, "db_value", attr_name, oobfuncname)

    def get_all_monitors(self, sessid):
        """
        Get the names of all variables this session is tracking.

        Args:
            sessid (id): Session id of monitoring Session

        """
        return [stored for key, stored in self.oob_monitor_storage.items() if key[1] == sessid]


    # access method - called from session.msg()

    def execute_cmd(self, session, oobfuncname, *args, **kwargs):
        """
        Execute an oob command

        Args:
            session (Session or int):  Session or Session.sessid calling
                the oob command
            oobfuncname (str): The name of the oob command (case sensitive)

        Notes:
            If the oobfuncname is a valid oob function, the `*args` and
            `**kwargs` are passed into the oob command.

        """
        if isinstance(session, int):
            # a sessid. Convert to a session
            session = SESSIONS.session_from_sessid(self.sessid)
        if not session:
            errmsg = "OOB Error: execute_cmd(%s,%s,%s,%s) - no valid session" % \
                                                    (session, oobfuncname, args, kwargs)
            raise RuntimeError(errmsg)

        # don't catch this, wrong oobfuncname should be reported
        oobfunc = _OOB_FUNCS[oobfuncname]

        # we found an oob command. Execute it.
        try:
            #print "OOB execute_cmd:", session, func_key, args, kwargs, _OOB_FUNCS.keys()
            oobfunc(self, session, *args, **kwargs)
        except Exception, err:
            errmsg = "OOB Error: Exception in '%s'(%s, %s):\n%s" % (oobfuncname, args, kwargs, err)
            if _OOB_ERROR:
                _OOB_ERROR(self, session, errmsg, *args, **kwargs)
            logger.log_trace(errmsg)
            raise Exception(errmsg)


# access object
OOB_HANDLER = OOBHandler()
