"""
Monitors - catch changes to model fields and Attributes.

The MONITOR_HANDLER singleton from this module offers the following
functionality:

- Field-monitor - track a object's specific database field and perform
    an action whenever that field *changes* for whatever reason.
- Attribute-monitor tracks an object's specific Attribute and perform
    an action whenever that Attribute *changes* for whatever reason.

"""
import inspect

from collections import defaultdict
from evennia.server.models import ServerConfig
from evennia.utils.dbserialize import dbserialize, dbunserialize
from evennia.utils import logger
from evennia.utils import variable_from_module

_SA = object.__setattr__
_GA = object.__getattribute__
_DA = object.__delattr__


class MonitorHandler(object):
    """
    This is a resource singleton that allows for registering
    callbacks for when a field or Attribute is updated (saved).
    """

    def __init__(self):
        """
        Initialize the handler.
        """
        self.savekey = "_monitorhandler_save"
        self.monitors = defaultdict(lambda: defaultdict(dict))

    def save(self):
        """
        Store our monitors to the database. This is called
        by the server process.

        Since dbserialize can't handle defaultdicts, we convert to an
        intermediary save format ((obj,fieldname, idstring, callback, kwargs), ...)

        """
        savedata = []
        if self.monitors:
            for obj in self.monitors:
                for fieldname in self.monitors[obj]:
                    for idstring, (callback, persistent, kwargs) in self.monitors[obj][
                        fieldname
                    ].items():
                        path = "%s.%s" % (callback.__module__, callback.__name__)
                        savedata.append((obj, fieldname, idstring, path, persistent, kwargs))
            savedata = dbserialize(savedata)
            ServerConfig.objects.conf(key=self.savekey, value=savedata)

    def restore(self, server_reload=True):
        """
        Restore our monitors after a reload. This is called
        by the server process.

        Args:
            server_reload (bool, optional): If this is False, it means
                the server went through a cold reboot and all
                non-persistent tickers must be killed.

        """
        self.monitors = defaultdict(lambda: defaultdict(dict))
        restored_monitors = ServerConfig.objects.conf(key=self.savekey)
        if restored_monitors:
            restored_monitors = dbunserialize(restored_monitors)
            for (obj, fieldname, idstring, path, persistent, kwargs) in restored_monitors:
                try:
                    if not server_reload and not persistent:
                        # this monitor will not be restarted
                        continue
                    if "session" in kwargs and not kwargs["session"]:
                        # the session was removed because it no longer
                        # exists. Don't restart the monitor.
                        continue
                    modname, varname = path.rsplit(".", 1)
                    callback = variable_from_module(modname, varname)

                    if obj and hasattr(obj, fieldname):
                        self.monitors[obj][fieldname][idstring] = (callback, persistent, kwargs)
                except Exception:
                    continue
        # make sure to clean data from database
        ServerConfig.objects.conf(key=self.savekey, delete=True)

    def at_update(self, obj, fieldname):
        """
        Called by the field as it saves.

        """
        to_delete = []
        if obj in self.monitors and fieldname in self.monitors[obj]:
            for idstring, (callback, persistent, kwargs) in self.monitors[obj][fieldname].items():
                try:
                    callback(obj=obj, fieldname=fieldname, **kwargs)
                except Exception:
                    to_delete.append((obj, fieldname, idstring))
                    logger.log_trace("Monitor callback was removed.")
        # we cleanup non-found monitors (has to be done after loop)
        for (obj, fieldname, idstring) in to_delete:
            del self.monitors[obj][fieldname][idstring]

    def add(self, obj, fieldname, callback, idstring="", persistent=False, **kwargs):
        """
        Add monitoring to a given field or Attribute. A field must
        be specified with the full db_* name or it will be assumed
        to be an Attribute (so `db_key`, not just `key`).

        Args:
            obj (Typeclassed Entity): The entity on which to monitor a
                field or Attribute.
            fieldname (str): Name of field (db_*) or Attribute to monitor.
            callback (callable): A callable on the form `callable(**kwargs),
                where kwargs holds keys fieldname and obj.
            idstring (str, optional): An id to separate this monitor from other monitors
                of the same field and object.
            persistent (bool, optional): If False, the monitor will survive
                a server reload but not a cold restart. This is default.

        Kwargs:
            session (Session): If this keyword is given, the monitorhandler will
                correctly analyze it and remove the monitor if after a reload/reboot
                the session is no longer valid.
            any (any): Any other kwargs are passed on to the callback. Remember that
                all kwargs must be possible to pickle!

        """
        if not fieldname.startswith("db_") or not hasattr(obj, fieldname):
            # an Attribute - we track its db_value field
            obj = obj.attributes.get(fieldname, return_obj=True)
            if not obj:
                return
            fieldname = "db_value"

        # we try to serialize this data to test it's valid. Otherwise we won't accept it.
        try:
            if not inspect.isfunction(callback):
                raise TypeError("callback is not a function.")
            dbserialize((obj, fieldname, callback, idstring, persistent, kwargs))
        except Exception:
            err = "Invalid monitor definition: \n" " (%s, %s, %s, %s, %s, %s)" % (
                obj,
                fieldname,
                callback,
                idstring,
                persistent,
                kwargs,
            )
            logger.log_trace(err)
        else:
            self.monitors[obj][fieldname][idstring] = (callback, persistent, kwargs)

    def remove(self, obj, fieldname, idstring=""):
        """
        Remove a monitor.
        """
        if not fieldname.startswith("db_") or not hasattr(obj, fieldname):
            obj = obj.attributes.get(fieldname, return_obj=True)
            if not obj:
                return
            fieldname = "db_value"

        idstring_dict = self.monitors[obj][fieldname]
        if idstring in idstring_dict:
            del self.monitors[obj][fieldname][idstring]

    def clear(self):
        """
        Delete all monitors.
        """
        self.monitors = defaultdict(lambda: defaultdict(dict))

    def all(self, obj=None):
        """
        List all monitors or all monitors of a given object.

        Args:
            obj (Object): The object on which to list all monitors.

        Returns:
            monitors (list): The handled monitors.

        """
        output = []
        objs = [obj] if obj else self.monitors

        for obj in objs:
            for fieldname in self.monitors[obj]:
                for idstring, (callback, persistent, kwargs) in self.monitors[obj][
                    fieldname
                ].items():
                    output.append((obj, fieldname, idstring, persistent, kwargs))
        return output


# access object
MONITOR_HANDLER = MonitorHandler()
