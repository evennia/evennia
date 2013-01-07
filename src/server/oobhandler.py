"""
-- OBS - OOB is not yet functional in Evennia. Don't use this module --

OOB - Out-of-band central handler

This module presents a central API for requesting data from objects in
Evennia via OOB negotiation. It is meant specifically to be imported
and used by the module defined in settings.OOB_FUNC_MODULE.

Import src.server.oobhandler and use the methods in OOBHANDLER.

The actual client protocol (MSDP, GMCP, whatever) does not matter at
this level, serialization is assumed to happen at the protocol level
only.

This module offers the following basic functionality:

track_passive - retrieve field, property, db/ndb attribute from an object, then continue reporting
         changes henceforth. This is done efficiently and on-demand using hooks. This should be
         used preferentially since it's very resource efficient.
track_active - this is an active reporting mechanism making use of a Script. This should normally
         only be used if:
         1) you want changes to be reported SLOWER than the actual rate of update (such
            as only wanting to show an average of change over time)
         2) the data you are reporting is NOT stored as a field/property/db/ndb on an object (such
            as some sort of server statistic calculated on the fly).

Trivial operations such as get/setting individual properties one time is best done directly from
the OOB_MODULE functions.

Examples of call from OOB_FUNC_MODULE:

from src.server.oobhandler import OOBHANDLER

def track_desc(session, *args, **kwargs):
    "Sets up a passive watch for the desc attribute on session object"
    if session.player and session.player.character:
        char = session.player.character
        OOBHANDLER.track_passive(session, char, "desc", entity="db")
        # to start off we return the value once
        return char.db.desc

"""

from collections import defaultdict
from src.scripts.objects import ScriptDB
from src.scripts.script import Script
from src.server import caches
from src.server.caches import hashid
from src.utils import logger, create

class _OOBTracker(Script):
    """
    Active tracker script, handles subscriptions
    """
    def at_script_creation(self):
        "Called at script creation"
        self.key = "oob_tracking_30" # default to 30 second interval
        self.desc = "Active tracking of oob data"
        self.interval = 30
        self.persistent = False
        self.start_delay = True
        # holds dictionary of  key:(function, (args,), {kwargs}) to call
        self.db.subs = {}

    def track(self, key, func, *args, **kwargs):
        """
        Add sub to track. func(*args, **kwargs) will be called at self.interval.
        key is a unique identifier for removing the tracking later.
        """
        self.subs[key] = (func, args, kwargs)

    def untrack(self, key):
        """
        Clear a tracking. Return True if untracked successfully, None if
        no previous track was found.
        """
        if key in self.subs:
            del self.subs[key]
            if not self.subs:
                # we have no more subs. Stop this script.
                self.stop()
            return True

    def at_repeat(self):
        """
        Loops through all subs, calling their given function
        """
        for func, args, kwargs in self.subs:
            try:
                func(*args, **kwargs)
            except Exception:
                logger.log_trace()

class _OOBStore(Script):
    """
    Store OOB data between restarts
    """
    def at_script_creation(self):
        "Called at script creation"
        self.key = "oob_save_store"
        self.desc = "Stores OOB data"
        self.persistent = True
    def save_oob_data(self, data):
        self.db.store = data
    def get_oob_data(self):
        return self.db.store

class OOBhandler(object):
    """
    Main Out-of-band handler
    """
    def __init__(self):
        "initialization"
        self.track_passive_subs = defaultdict(dict)
        scripts = ScriptDB.objects.filter(db_key__startswith="oob_tracking_")
        self.track_active_subs = dict((s.interval, s) for s in scripts)
        # set reference on caches module
        caches._OOB_HANDLER = self

    def track_passive(self, oobkey, tracker, tracked, entityname, callback=None, mode="db", *args, **kwargs):
        """
        Passively track changes to an object property,
        attribute or non-db-attribute. Uses cache hooks to
        do this on demand, without active tracking.

        tracker - object who is tracking
        tracked - object being tracked
        entityname - field/property/attribute/ndb nam to watch
        function - function object to call when entity update. When entitye <key>
        is updated, this function will be called with called
              with function(obj, entityname, new_value, *args, **kwargs)
        *args - additional, optional arguments to send to function
        mode (keyword) - the type of entity to track. One of
             "property", "db", "ndb" or "custom" ("property" includes both
             changes to database fields and cached on-model properties)
        **kwargs - additional, optionak keywords to send to function

        Only entities that are being -cached- can be tracked. For custom
        on-typeclass properties, a custom hook needs to be created, calling
        the update() function in this module whenever the tracked entity changes.
        """

        # always store database object (in case typeclass changes along the way)
        try: tracker = tracker.dbobj
        except AttributeError: pass
        try: tracked = tracked.dbobj
        except AttributeError: pass

        def default_callback(tracker, tracked, entityname, new_val, *args, **kwargs):
            "Callback used if no function is supplied"
            pass

        thid = hashid(tracked)
        if not thid:
            return
        oob_call = (function, oobkey, tracker, tracked, entityname, args, kwargs)
        if thid not in self.track_passive_subs:
            if mode in ("db", "ndb", "custom"):
                caches.register_oob_update_hook(tracked, entityname, mode=mode)
            elif mode == "property":
                # track property/field. We must first determine which cache to use.
                if hasattr(tracked, 'db_%s' % entityname.lstrip("db_")):
                    hid = caches.register_oob_update_hook(tracked, entityname, mode="field")
                else:
                    hid = caches.register_oob_update_hook(tracked, entityname, mode="property")
        if not self.track_pass_subs[hid][entityname]:
            self.track_pass_subs[hid][entityname] = {tracker:oob_call}
        else:
            self.track_passive_subs[hid][entityname][tracker] = oob_call

    def untrack_passive(self, tracker, tracked, entityname, mode="db"):
        """
        Remove passive tracking from an object's entity.
        mode - one of "property", "db", "ndb" or "custom"
        """
        try: tracked = tracked.dbobj
        except AttributeError: pass

        thid = hashid(tracked)
        if not thid:
            return
        if len(self.track_passive_subs[thid][entityname]) == 1:
            if mode in ("db", "ndb", "custom"):
                caches.unregister_oob_update_hook(tracked, entityname, mode=mode)
            elif mode == "property":
                if hasattr(, 'db_%s' % entityname.lstrip("db_")):
                    caches.unregister_oob_update_hook(tracked, entityname, mode="field")
                else:
                    caches.unregister_oob_update_hook(tracked, entityname, mode="property")

        try: del self.track_passive_subs[thid][entityname][tracker]
        except (KeyError, TypeError): pass

    def update(self, hid, entityname, new_val):
        """
        This is called by the caches when the  object when its
        property/field/etc is updated, to inform the oob handler and
        all subscribing to this particular entity has been updated
        with new_val.
        """
        # tell all tracking objects of the update
        for tracker, oob in self.track_passive_subs[hid][entityname].items():
            try:
                # function(oobkey, tracker, tracked, entityname, new_value, *args, **kwargs)
                oob[0](tracker, oob[1], oob[2], new_val, *oob[3], **oob[4])
            except Exception:
                logger.log_trace()

    # Track (active/proactive tracking)

    # creating and storing tracker scripts
    def track_active(self, oobkey, func, interval=30, *args, **kwargs):
        """
        Create a tracking, re-use script with same interval if available,
        otherwise create a new one.

        args:
         oobkey - interval-unique identifier needed for removing tracking later
         func - function to call at interval seconds
            (all other args become argjs into func)
        keywords:
         interval (default 30s) - how often to update tracker
            (all other kwargs become kwargs into func)
        """
        if interval in self.track_active_subs:
            # tracker with given interval found. Add to its subs
            self.track_active_subs[interval].track(oobkey, func, *args, **kwargs)
        else:
            # create new tracker with given interval
            new_tracker = create.create_script(_OOBTracker, oobkey="oob_tracking_%i" % interval, interval=interval)
            new_tracker.track(oobkey, func, *args, **kwargs)
            self.track_active_subs[interval] = new_tracker

    def untrack_active(self, oobkey, interval):
        """
        Remove tracking for a given interval and oobkey
        """
        tracker = self.track_active_subs.get(interval)
        if tracker:
            tracker.untrack(oobkey)

# handler object
OOBHANDLER = OOBhandler()
