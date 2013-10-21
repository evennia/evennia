"""
Central caching module.

"""

from sys import getsizeof
import os, threading
from collections import defaultdict

from django.core.cache import get_cache
from src.server.models import ServerConfig
from src.utils.utils import uses_database, to_str, get_evennia_pids

_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__

_IS_SUBPROCESS = os.getpid() in get_evennia_pids()
_IS_MAIN_THREAD = threading.currentThread().getName() == "MainThread"

#
# Set up the cache stores
#

_ATTR_CACHE = {}
_PROP_CACHE = defaultdict(dict)

#------------------------------------------------------------
# Cache key hash generation
#------------------------------------------------------------

if uses_database("mysql") and ServerConfig.objects.get_mysql_db_version() < '5.6.4':
    # mysql <5.6.4 don't support millisecond precision
    _DATESTRING = "%Y:%m:%d-%H:%M:%S:000000"
else:
    _DATESTRING = "%Y:%m:%d-%H:%M:%S:%f"

def hashid(obj, suffix=""):
    """
    Returns a per-class unique hash that combines the object's
    class name with its idnum and creation time. This makes this id unique also
    between different typeclassed entities such as scripts and
    objects (which may still have the same id).
    """
    if not obj:
        return obj
    try:
        hid = _GA(obj, "_hashid")
    except AttributeError:
        try:
            date, idnum = _GA(obj, "db_date_created").strftime(_DATESTRING), _GA(obj, "id")
        except AttributeError:
            try:
                # maybe a typeclass, try to go to dbobj
                obj = _GA(obj, "dbobj")
                date, idnum = _GA(obj, "db_date_created").strftime(_DATESTRING), _GA(obj, "id")
            except AttributeError:
                # this happens if hashing something like ndb. We have to
                # rely on memory adressing in this case.
                date, idnum = "InMemory", id(obj)
        if not idnum or not date:
            # this will happen if setting properties on an object which is not yet saved
            return None
        hid = "%s-%s-#%s" % (_GA(obj, "__class__"), date, idnum)
        hid = hid.replace(" ", "") # we have to remove the class-name's space, for memcached's sake
        # we cache the object part of the hashid to avoid too many object lookups
        _SA(obj, "_hashid", hid)
    # build the complete hashid
    hid = "%s%s" % (hid, suffix)
    return to_str(hid)


#------------------------------------------------------------
# Cache callback handlers
#------------------------------------------------------------

#------------------------------------------------------------
# Field cache - makes sure to cache all database fields when
# they are saved, no matter from where.
#------------------------------------------------------------

# callback to field pre_save signal (connected in src.server.server)
def field_pre_save(sender, instance=None, update_fields=None, raw=False, **kwargs):
    """
    Called at the beginning of the field save operation. The save method
    must be called with the update_fields keyword in order to be most efficient.
    This method should NOT save; rather it is the save() that triggers this function.
    Its main purpose is to allow to plug-in a save handler and oob handlers.
    """
    if raw:
        return
    if update_fields:
        # this is a list of strings at this point. We want field objects
        update_fields = (_GA(_GA(instance, "_meta"), "get_field_by_name")(field)[0] for field in update_fields)
    else:
        # meta.fields are already field objects; get them all
        update_fields = _GA(_GA(instance, "_meta"), "fields")
    for field in update_fields:
        fieldname = field.name
        handlername = "_at_%s_presave" % fieldname
        handler = _GA(instance, handlername) if handlername in _GA(sender, '__dict__') else None
        if callable(handler):
            handler()

def field_post_save(sender, instance=None, update_fields=None, raw=False, **kwargs):
    """
    Called at the beginning of the field save operation. The save method
    must be called with the update_fields keyword in order to be most efficient.
    This method should NOT save; rather it is the save() that triggers this function.
    Its main purpose is to allow to plug-in a save handler and oob handlers.
    """
    if raw:
        return
    if update_fields:
        # this is a list of strings at this point. We want field objects
        update_fields = (_GA(_GA(instance, "_meta"), "get_field_by_name")(field)[0] for field in update_fields)
    else:
        # meta.fields are already field objects; get them all
        update_fields = _GA(_GA(instance, "_meta"), "fields")
    for field in update_fields:
        fieldname = field.name
        handlername = "_at_%s_postsave" % fieldname
        handler = _GA(instance, handlername) if handlername in _GA(sender, '__dict__') else None
        if callable(handler):
            handler()
        trackerhandler = _GA(instance, "_trackerhandler") if "_trackerhandler" in _GA(instance, '__dict__') else None
        if trackerhandler:
            trackerhandler.update(fieldname, _GA(instance, fieldname))

#------------------------------------------------------------
# Attr cache - caching the attribute objects related to a given object to
# avoid lookups more than necessary (this makes Attributes en par in speed
# to any property).
#------------------------------------------------------------

## connected to m2m_changed signal in respective model class
#def post_attr_update(sender, **kwargs):
#    "Called when the many2many relation changes (NOT when updating the value of an Attribute!)"
#    obj = kwargs['instance']
#    model = kwargs['model']
#    action = kwargs['action']
#    if kwargs['reverse']:
#        # the reverse relation changed (the Attribute itself was acted on)
#        pass
#    else:
#        # forward relation changed (the Object holding the Attribute m2m field)
#        if not kwargs["pk_set"]:
#            return
#        if action == "post_add":
#            # cache all added objects
#            for attr_id in kwargs["pk_set"]:
#                attr_obj = model.objects.get(pk=attr_id)
#                set_attr_cache(obj, _GA(attr_obj, "db_key"), attr_obj)
#        elif action == "post_remove":
#            # obj.db_attributes.remove(attr) was called
#            for attr_id in kwargs["pk_set"]:
#                attr_obj = model.objects.get(pk=attr_id)
#                del_attr_cache(obj, _GA(attr_obj, "db_key"))
#                attr_obj.delete()
#        elif action == "post_clear":
#            # obj.db_attributes.clear() was called
#            clear_obj_attr_cache(obj)
#
#
## attr cache - this is only left as deprecated cache
#
#def get_attr_cache(obj, attrname):
#    "Called by getting attribute"
#    hid = hashid(obj, "-%s" % attrname)
#    return _ATTR_CACHE.get(hid, None)
#
#def set_attr_cache(obj, attrname, attrobj):
#    "Set the attr cache manually; this can be used to update"
#    global _ATTR_CACHE
#    hid = hashid(obj, "-%s" % attrname)
#    _ATTR_CACHE[hid] = attrobj
#
#def del_attr_cache(obj, attrname):
#    "Del attribute cache"
#    global _ATTR_CACHE
#    hid = hashid(obj, "-%s" % attrname)
#    if hid in _ATTR_CACHE:
#        del _ATTR_CACHE[hid]
#
#def flush_attr_cache():
#    "Clear attribute cache"
#    global _ATTR_CACHE
#    _ATTR_CACHE = {}
#
#def clear_obj_attr_cache(obj):
#    global _ATTR_CACHE
#    hid = hashid(obj)
#    _ATTR_CACHE = {key:value for key, value in _ATTR_CACHE if not key.startswith(hid)}

#------------------------------------------------------------
# Property cache - this is a generic cache for properties stored on models.
#------------------------------------------------------------

# access methods

def get_prop_cache(obj, propname):
    "retrieve data from cache"
    hid = hashid(obj, "-%s" % propname)
    return _PROP_CACHE[hid].get(propname, None) if hid else None

def set_prop_cache(obj, propname, propvalue):
    "Set property cache"
    hid = hashid(obj, "-%s" % propname)
    if hid:
        _PROP_CACHE[hid][propname] = propvalue

def del_prop_cache(obj, propname):
    "Delete element from property cache"
    hid = hashid(obj, "-%s" % propname)
    if hid:
        if propname in _PROP_CACHE[hid]:
            del _PROP_CACHE[hid][propname]

def flush_prop_cache():
    "Clear property cache"
    global _PROP_CACHE
    _PROP_CACHE = defaultdict(dict)
    #_PROP_CACHE.clear()

def get_cache_sizes():
    """
    Get cache sizes, expressed in number of objects and memory size in MB
    """
    global _ATTR_CACHE, _PROP_CACHE
    attr_n = len(_ATTR_CACHE)
    attr_mb = sum(getsizeof(obj) for obj in _ATTR_CACHE) / 1024.0
    field_n = 0 #sum(len(dic) for dic in _FIELD_CACHE.values())
    field_mb = 0 # sum(sum([getsizeof(obj) for obj in dic.values()]) for dic in _FIELD_CACHE.values()) / 1024.0
    prop_n = sum(len(dic) for dic in _PROP_CACHE.values())
    prop_mb = sum(sum([getsizeof(obj) for obj in dic.values()]) for dic in _PROP_CACHE.values()) / 1024.0
    return (attr_n, attr_mb), (field_n, field_mb), (prop_n, prop_mb)


