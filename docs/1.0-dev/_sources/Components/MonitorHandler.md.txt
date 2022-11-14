# MonitorHandler


The *MonitorHandler* is a system for watching changes in properties or Attributes on objects. A
monitor can be thought of as a sort of trigger that responds to change.

The main use for the MonitorHandler is to report changes to the client; for example the client
Session may ask Evennia to monitor the value of the Characer's `health` attribute and report
whenever it changes. This way the client could for example update its health bar graphic as needed.

## Using the MonitorHandler

The MontorHandler is accessed from the singleton `evennia.MONITOR_HANDLER`. The code for the handler
is in `evennia.scripts.monitorhandler`.

Here's how to add a new monitor: 

```python
from evennia import MONITOR_HANDLER

MONITOR_HANDLER.add(obj, fieldname, callback,
                    idstring="", persistent=False, **kwargs)

```

 - `obj` ([Typeclassed](./Typeclasses.md) entity) - the object to monitor. Since this must be
typeclassed, it means you can't monitor changes on [Sessions](./Sessions.md) with the monitorhandler, for
example.
 - `fieldname` (str) - the name of a field or [Attribute](./Attributes.md) on `obj`. If you want to
monitor a database field you must specify its full name, including the starting `db_` (like
`db_key`, `db_location` etc). Any names not starting with `db_` are instead assumed to be the names
of Attributes. This difference matters, since the MonitorHandler will automatically know to watch
the `db_value` field of the Attribute.
 - `callback`(callable) - This will be called as `callback(fieldname=fieldname, obj=obj, **kwargs)`
when the field updates.
 - `idstring` (str) - this is used to separate multiple monitors on the same object and fieldname.
This is required in order to properly identify and remove the monitor later. It's also used for
saving it.
 - `persistent` (bool) - if True, the monitor will survive a server reboot.

Example: 

```python
from evennia import MONITOR_HANDLER as monitorhandler

def _monitor_callback(fieldname="", obj=None, **kwargs):    
    # reporting callback that works both
    # for db-fields and Attributes
    if fieldname.startswith("db_"):
        new_value = getattr(obj, fieldname)
    else: # an attribute    
        new_value = obj.attributes.get(fieldname)
    obj.msg(f"{obj.key}.{fieldname} changed to '{new_value}'.")

# (we could add _some_other_monitor_callback here too)

# monitor Attribute (assume we have obj from before)
monitorhandler.add(obj, "desc", _monitor_callback)  

# monitor same db-field with two different callbacks (must separate by id_string)
monitorhandler.add(obj, "db_key", _monitor_callback, id_string="foo")  
monitorhandler.add(obj, "db_key", _some_other_monitor_callback, id_string="bar")

```

A monitor is uniquely identified by the combination of the *object instance* it is monitoring, the
*name* of the field/attribute to monitor on that object and its `idstring` (`obj` + `fieldname` +
`idstring`). The `idstring` will be the empty string unless given explicitly.

So to "un-monitor" the above you need to supply enough information for the system to uniquely find
the monitor to remove:

```
monitorhandler.remove(obj, "desc")
monitorhandler.remove(obj, "db_key", idstring="foo")
monitorhandler.remove(obj, "db_key", idstring="bar")
```