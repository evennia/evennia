"""
Monitors - catch changes to model fields and Attributes.

The MONITOR_HANDLER singleton from this module offers the following
functionality:

- Field-monitor - track a object's specific database field and perform
    an action whenever that field *changes* for whatever reason.
- Attribute-monitor tracks an object's specific Attribute and perform
    an action whenever that Attribute *changes* for whatever reason.

"""
from builtins import object

from collections import defaultdict
from evennia.server.models import ServerConfig
from evennia.utils.dbserialize import dbserialize, dbunserialize
from evennia.utils import logger

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
        self.monitors = defaultdict(lambda:defaultdict(dict))

    def at_update(self, obj, fieldname):
        """
        Called by the field as it saves.
        """
        to_delete = []
        if obj in self.monitors and fieldname in self.monitors[obj]:
            for (callback, kwargs) in self.monitors[obj][fieldname].iteritems():
                kwargs.update({"obj": obj, "fieldname": fieldname})
                try:
                    callback( **kwargs)
                except Exception:
                    to_delete.append((obj, fieldname, callback))
                    logger.log_trace("Monitor callback was removed.")
            # we need to do the cleanup after loop has finished
            for (obj, fieldname, callback) in to_delete:
                del self.monitors[obj][fieldname][callback]

    def add(self, obj, fieldname, callback, **kwargs):
        """
        Add monitoring to a given field or Attribute. A field must
        be specified with the full db_* name or it will be assumed
        to be an Attribute (so `db_key`, not just `key`).

        Args:
            obj (Typeclassed Entity): The entity on which to monitor a
                field or Attribute.
            fieldname (str): Name of field (db_*) or Attribute to monitor.
            callback (callable): A callable on the form `callable(obj,
                fieldname, **kwargs), where kwargs holds keys fieldname
                and obj.
            uid (hashable): A unique id to identify this particular monitor.
                It is used together with obj to
            persistent (bool): If this monitor should survive a server
                reboot or not (it will always survive a reload).

        """
        if not fieldname.startswith("db_") or not hasattr(obj, fieldname):
            # an Attribute - we track it's db_value field
            obj = obj.attributes.get(fieldname, return_obj=True)
            if not obj:
                return
            fieldname = "db_value"

        # we try to serialize this data to test it's valid. Otherwise we won't accept it.
        try:
            dbserialize((obj, fieldname, callback, kwargs))
        except Exception:
            err = "Invalid monitor definition (skipped since it could not be serialized):\n" \
                  " (%s, %s, %s, %s)" % (obj, fieldname, callback, kwargs)
            logger.log_trace(err)
        else:
            self.monitors[obj][fieldname][callback] = kwargs


    def remove(self, obj, fieldname, callback):
        """
        Remove a monitor.
        """
        callback_dict = self.monitors[obj][fieldname]
        if callback in callback_dict:
            del callback_dict[callback]

    def save(self):
        """
        Store our monitors to the database. This is called
        by the server process.

        Since dbserialize can't handle defaultdicts, we convert to an
        intermediary save format ((obj,fieldname, callback, kwargs), ...)

        """
        savedata = []
        for obj in self.monitors:
            for fieldname in self.monitors[obj]:
                for callback in self.monitors[obj][fieldname]:
                    savedata.append((obj, fieldname, callback, self.monitors[obj][fieldname][callback]))
        savedata = dbserialize(savedata)
        ServerConfig.objects.conf(key=self.savekey,
                                  value=savedata)

    def restore(self):
        """
        Restore our monitors after a reload. This is called
        by the server process.
        """
        savedata = ServerConfig.objects.conf(key=self.savekey)
        if savedata:
            for (obj, fieldname, callback, kwargs) in dbunserialize(savedata):
                self.monitors[obj][fieldname][callback] = kwargs
            ServerConfig.objects.conf(key=self.savekey, delete=True)

# access object
MONITOR_HANDLER = MonitorHandler()
