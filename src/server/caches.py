"""
Central caching module.

"""

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

_FIELD_CACHE = {}
_ATTR_CACHE = {}
_PROP_CACHE = defaultdict(dict)

# OOB trackers
_TRACKED_FIELDS = {}
_TRACKED_ATTRS = {}
_TRACKED_CACHE = {}


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
    #print "field_pre_save:", instance, update_fields# if hasattr(instance, "db_key") else instance, update_fields
    if update_fields:
        # this is a list of strings at this point. We want field objects
        update_fields = (_GA(_GA(instance, "_meta"), "get_field_by_name")(field)[0] for field in update_fields)
    else:
        # meta.fields are already field objects; get them all
        update_fields = _GA(_GA(instance, "_meta"), "fields")
    for field in update_fields:
        fieldname = field.name
        new_value = field.value_from_object(instance)
        # try to see if there is a handler on object that should be triggered when saving.
        handlername = "_at_%s_save" % fieldname
        handler = _GA(instance, handlername) if handlername in _GA(instance, '__dict__') else None
        if callable(handler):
            #hid = hashid(instance, "-%s" % fieldname)
            try:
                old_value = _GA(instance, _GA(field, "get_cache_name")())#_FIELD_CACHE.get(hid) if hid else None
            except AttributeError:
                old_value=None
            # the handler may modify the stored value in various ways
            # don't catch exceptions, the handler must work!
            new_value = handler(new_value, old_value=old_value)
            # we re-assign this to the field, save() will pick it up from there
            _SA(instance, fieldname, new_value)
        trackerhandler = _GA(instance, "_trackerhandler") if "_trackerhandler" in _GA(instance, '__dict__') else None
        if trackerhandler:
            trackerhandler.update(fieldname, new_value)
        #if hid:
        #    # update cache
        #    _FIELD_CACHE[hid] = new_value

def get_cache_sizes():
    return (0, 0), (0, 0), (0, 0)
def get_field_cache(obj, name):
    return _GA(obj, "db_%s" % name)
def set_field_cache(obj, name, val):
    _SA(obj, "db_%s" % name, val)
    _GA(obj, "save")()
    #hid = hashid(obj)
    #if _OOB_FIELD_UPDATE_HOOKS[hid].get(name):
    #    _OOB_HANDLER.update(hid, name, val)
def del_field_cache(obj, name):
    _SA(obj, "db_%s" % name, None)
    _GA(obj, "save")()
    #hid = hashid(obj)
    #if _OOB_FIELD_UPDATE_HOOKS[hid].get(name):
    #    _OOB_HANDLER.update(hid, name, None)


#------------------------------------------------------------
# Attr cache - caching the attribute objects related to a given object to
# avoid lookups more than necessary (this makes Attributes en par in speed
# to any property).
#------------------------------------------------------------

# connected to m2m_changed signal in respective model class
def post_attr_update(sender, **kwargs):
    "Called when the many2many relation changes some way"
    obj = kwargs['instance']
    model = kwargs['model']
    action = kwargs['action']
    #print "update_attr_cache:", obj, model, action
    if kwargs['reverse']:
        # the reverse relation changed (the Attribute itself was acted on)
        pass
    else:
        # forward relation changed (the Object holding the Attribute m2m field)
        if not kwargs["pk_set"]:
            return
        if action == "post_add":
            # cache all added objects
            for attr_id in kwargs["pk_set"]:
                attr_obj = model.objects.get(pk=attr_id)
                set_attr_cache(obj, _GA(attr_obj, "db_key"), attr_obj)
        elif action == "post_remove":
            # obj.db_attributes.remove(attr) was called
            for attr_id in kwargs["pk_set"]:
                attr_obj = model.objects.get(pk=attr_id)
                del_attr_cache(obj, _GA(attr_obj, "db_key"))
                attr_obj.delete()
        elif action == "post_clear":
            # obj.db_attributes.clear() was called
            clear_obj_attr_cache(obj)

# access methods

def get_attr_cache(obj, attrname):
    "Called by getting attribute"
    hid = hashid(obj, "-%s" % attrname)
    return hid and _ATTR_CACHE.get(hid, None) or None

def set_attr_cache(obj, attrname, attrobj):
    "Set the attr cache manually; this can be used to update"
    global _ATTR_CACHE
    hid = hashid(obj, "-%s" % attrname)
    _ATTR_CACHE[hid] = attrobj

def del_attr_cache(obj, attrname):
    "Del attribute cache"
    global _ATTR_CACHE
    hid = hashid(obj, "-%s" % attrname)
    if hid in _ATTR_CACHE:
        del _ATTR_CACHE[hid]

def flush_attr_cache():
    "Clear attribute cache"
    global _ATTR_CACHE
    _ATTR_CACHE = {}

def clear_obj_attr_cache(obj):
    global _ATTR_CACHE
    hid = hashid(obj)
    _ATTR_CACHE = {key:value for key, value in _ATTR_CACHE if not key.startswith(hid)}

#------------------------------------------------------------
# Property cache - this is a generic cache for properties stored on models.
#------------------------------------------------------------

# access methods

def get_prop_cache(obj, propname):
    "retrieve data from cache"
    hid = hashid(obj, "-%s" % propname)
    if hid:
        #print "get_prop_cache", hid, propname, _PROP_CACHE.get(hid, None)
        return _PROP_CACHE[hid].get(propname, None)

def set_prop_cache(obj, propname, propvalue):
    "Set property cache"
    hid = hashid(obj, "-%s" % propname)
    if obj and hasattr(obj, "oobhandler"):
        obj.oobhandler.update(propname, _GA(obj, propname), propvalue, type="property", action="set")
    if hid:
        #print "set_prop_cache", propname, propvalue
        _PROP_CACHE[hid][propname] = propvalue
        #_PROP_CACHE.set(hid, propvalue)

def del_prop_cache(obj, propname):
    "Delete element from property cache"
    hid = hashid(obj, "-%s" % propname)
    if obj and hasattr(obj, "oobhandler"):
        obj.oobhandler.update(propname, _GA(obj, propname), None, type="property", action="delete")
    if hid and propname in _PROP_CACHE[hid]:
        del _PROP_CACHE[hid][propname]
        #_PROP_CACHE.delete(hid)

def flush_prop_cache():
    "Clear property cache"
    global _PROP_CACHE
    _PROP_CACHE = defaultdict(dict)
    #_PROP_CACHE.clear()


#_ENABLE_LOCAL_CACHES = settings.GAME_CACHE_TYPE
## oob helper functions
# OOB hooks (OOB not yet functional, don't use yet)
#_OOB_FIELD_UPDATE_HOOKS = defaultdict(dict)
#_OOB_PROP_UPDATE_HOOKS = defaultdict(dict)
#_OOB_ATTR_UPDATE_HOOKS = defaultdict(dict)
#_OOB_NDB_UPDATE_HOOKS = defaultdict(dict)
#_OOB_CUSTOM_UPDATE_HOOKS = defaultdict(dict)
#
#_OOB_HANDLER = None # set by oob handler when it initializes
#def register_oob_update_hook(obj,name, entity="field"):
#    """
#    Register hook function to be called when field/property/db/ndb is updated.
#    Given function will be called with function(obj, entityname, newvalue, *args, **kwargs)
#     entity - one of "field", "property", "db", "ndb" or "custom"
#    """
#    hid = hashid(obj)
#    if hid:
#        if entity == "field":
#            global _OOB_FIELD_UPDATE_HOOKS
#            _OOB_FIELD_UPDATE_HOOKS[hid][name] = True
#            return
#        elif entity == "property":
#            global _OOB_PROP_UPDATE_HOOKS
#            _OOB_PROP_UPDATE_HOOKS[hid][name] = True
#        elif entity == "db":
#            global _OOB_ATTR_UPDATE_HOOKS
#            _OOB_ATTR_UPDATE_HOOKS[hid][name] = True
#        elif entity == "ndb":
#            global _OOB_NDB_UPDATE_HOOKS
#            _OOB_NDB_UPDATE_HOOKS[hid][name] = True
#        elif entity == "custom":
#            global _OOB_CUSTOM_UPDATE_HOOKS
#            _OOB_CUSTOM_UPDATE_HOOKS[hid][name] = True
#        else:
#            return None
#
#def unregister_oob_update_hook(obj, name, entity="property"):
#    """
#    Un-register a report hook
#    """
#    hid = hashid(obj)
#    if hid:
#        global _OOB_FIELD_UPDATE_HOOKS,_OOB_PROP_UPDATE_HOOKS, _OOB_ATTR_UPDATE_HOOKS
#        global _OOB_CUSTOM_UPDATE_HOOKS, _OOB_NDB_UPDATE_HOOKS
#        if entity == "field" and name in _OOB_FIELD_UPDATE_HOOKS:
#            del _OOB_FIELD_UPDATE_HOOKS[hid][name]
#        elif entity == "property" and name in _OOB_PROP_UPDATE_HOOKS:
#            del _OOB_PROP_UPDATE_HOOKS[hid][name]
#        elif entity == "db" and name in _OOB_ATTR_UPDATE_HOOKS:
#            del _OOB_ATTR_UPDATE_HOOKS[hid][name]
#        elif entity == "ndb" and name in _OOB_NDB_UPDATE_HOOKS:
#            del _OOB_NDB_UPDATE_HOOKS[hid][name]
#        elif entity == "custom" and name in _OOB_CUSTOM_UPDATE_HOOKS:
#            del _OOB_CUSTOM_UPDATE_HOOKS[hid][name]
#        else:
#            return None
#
#def call_ndb_hooks(obj, attrname, value):
#    """
#    No caching is done of ndb here, but
#    we use this as a way to call OOB hooks.
#    """
#    hid = hashid(obj)
#    if hid:
#        oob_hook = _OOB_NDB_UPDATE_HOOKS[hid].get(attrname)
#        if oob_hook:
#            oob_hook[0](obj.typeclass, attrname, value, *oob_hook[1], **oob_hook[2])
#
#def call_custom_hooks(obj, attrname, value):
#    """
#    Custom handler for developers adding their own oob hooks, e.g. to
#    custom typeclass properties.
#    """
#    hid = hashid(obj)
#    if hid:
#        oob_hook = _OOB_CUSTOM_UPDATE_HOOKS[hid].get(attrname)
#        if oob_hook:
#            oob_hook[0](obj.typeclass, attrname, value, *oob_hook[1], **oob_hook[2])
#
