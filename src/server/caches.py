"""
Central caching module.

"""

from sys import getsizeof
from collections import defaultdict
from django.conf import settings

_ENABLE_LOCAL_CACHES = settings.GAME_CACHE_TYPE

_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__

# OOB hooks (OOB not yet functional, don't use yet)
_OOB_FIELD_UPDATE_HOOKS = defaultdict(dict)
_OOB_PROP_UPDATE_HOOKS = defaultdict(dict)
_OOB_ATTR_UPDATE_HOOKS = defaultdict(dict)
_OOB_NDB_UPDATE_HOOKS = defaultdict(dict)
_OOB_CUSTOM_UPDATE_HOOKS = defaultdict(dict)

_OOB_HANDLER = None # set by oob handler when it initializes

def hashid(obj):
    """
    Returns a per-class unique that combines the object's
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
            date, idnum = _GA(obj, "db_date_created"), _GA(obj, "id")
            if not idnum or not date:
                # this will happen if setting properties on an object
                # which is not yet saved
                return None
        except AttributeError:
            # this happens if hashing something like ndb. We have to
            # rely on memory adressing in this case.
            date, idnum = "Nondb", id(obj)
        # build the hashid
        hid = "%s-%s-#%s" % (_GA(obj, "__class__"), date, idnum)
        _SA(obj, "_hashid", hid)
    return hid

# oob helper functions
def register_oob_update_hook(obj,name, entity="field"):
    """
    Register hook function to be called when field/property/db/ndb is updated.
    Given function will be called with function(obj, entityname, newvalue, *args, **kwargs)
     entity - one of "field", "property", "db", "ndb" or "custom"
    """
    hid = hashid(obj)
    if hid:
        if entity == "field":
            global _OOB_FIELD_UPDATE_HOOKS
            _OOB_FIELD_UPDATE_HOOKS[hid][name] = True
            return
        elif entity == "property":
            global _OOB_PROP_UPDATE_HOOKS
            _OOB_PROP_UPDATE_HOOKS[hid][name] = True
        elif entity == "db":
            global _OOB_ATTR_UPDATE_HOOKS
            _OOB_ATTR_UPDATE_HOOKS[hid][name] = True
        elif entity == "ndb":
            global _OOB_NDB_UPDATE_HOOKS
            _OOB_NDB_UPDATE_HOOKS[hid][name] = True
        elif entity == "custom":
            global _OOB_CUSTOM_UPDATE_HOOKS
            _OOB_CUSTOM_UPDATE_HOOKS[hid][name] = True
        else:
            return None

def unregister_oob_update_hook(obj, name, entity="property"):
    """
    Un-register a report hook
    """
    hid = hashid(obj)
    if hid:
        global _OOB_FIELD_UPDATE_HOOKS,_OOB_PROP_UPDATE_HOOKS, _OOB_ATTR_UPDATE_HOOKS
        global _OOB_CUSTOM_UPDATE_HOOKS, _OOB_NDB_UPDATE_HOOKS
        if entity == "field" and name in _OOB_FIELD_UPDATE_HOOKS:
            del _OOB_FIELD_UPDATE_HOOKS[hid][name]
        elif entity == "property" and name in _OOB_PROP_UPDATE_HOOKS:
            del _OOB_PROP_UPDATE_HOOKS[hid][name]
        elif entity == "db" and name in _OOB_ATTR_UPDATE_HOOKS:
            del _OOB_ATTR_UPDATE_HOOKS[hid][name]
        elif entity == "ndb" and name in _OOB_NDB_UPDATE_HOOKS:
            del _OOB_NDB_UPDATE_HOOKS[hid][name]
        elif entity == "custom" and name in _OOB_CUSTOM_UPDATE_HOOKS:
            del _OOB_CUSTOM_UPDATE_HOOKS[hid][name]
        else:
            return None

def call_ndb_hooks(obj, attrname, value):
    """
    No caching is done of ndb here, but
    we use this as a way to call OOB hooks.
    """
    hid = hashid(obj)
    if hid:
        oob_hook = _OOB_NDB_UPDATE_HOOKS[hid].get(attrname)
        if oob_hook:
            oob_hook[0](obj.typeclass, attrname, value, *oob_hook[1], **oob_hook[2])

def call_custom_hooks(obj, attrname, value):
    """
    Custom handler for developers adding their own oob hooks, e.g. to
    custom typeclass properties.
    """
    hid = hashid(obj)
    if hid:
        oob_hook = _OOB_CUSTOM_UPDATE_HOOKS[hid].get(attrname)
        if oob_hook:
            oob_hook[0](obj.typeclass, attrname, value, *oob_hook[1], **oob_hook[2])


if _ENABLE_LOCAL_CACHES:

    # Cache stores
    _ATTR_CACHE = defaultdict(dict)
    _FIELD_CACHE = defaultdict(dict)
    _PROP_CACHE = defaultdict(dict)


    def get_cache_sizes():
        """
        Get cache sizes, expressed in number of objects and memory size in MB
        """
        global _ATTR_CACHE, _FIELD_CACHE, _PROP_CACHE

        attr_n = sum(len(dic) for dic in _ATTR_CACHE.values())
        attr_mb = sum(sum(getsizeof(obj) for obj in dic.values()) for dic in _ATTR_CACHE.values()) / 1024.0

        field_n = sum(len(dic) for dic in _FIELD_CACHE.values())
        field_mb = sum(sum([getsizeof(obj) for obj in dic.values()]) for dic in _FIELD_CACHE.values()) / 1024.0

        prop_n = sum(len(dic) for dic in _PROP_CACHE.values())
        prop_mb = sum(sum([getsizeof(obj) for obj in dic.values()]) for dic in _PROP_CACHE.values()) / 1024.0

        return (attr_n, attr_mb), (field_n, field_mb), (prop_n, prop_mb)

    # on-object database field cache
    def get_field_cache(obj, name):
        "On-model Cache handler."
        global _FIELD_CACHE
        hid = hashid(obj)
        if hid:
            try:
                return _FIELD_CACHE[hid][name]
            except KeyError:
                val = _GA(obj, "db_%s" % name)
                _FIELD_CACHE[hid][name] = val
                return val
        return _GA(obj, "db_%s" % name)

    def set_field_cache(obj, name, val):
        "On-model Cache setter. Also updates database."
        _SA(obj, "db_%s" % name, val)
        _GA(obj, "save")()
        hid = hashid(obj)
        if hid:
            global _FIELD_CACHE
            _FIELD_CACHE[hid][name] = val
            # oob hook functionality
            if _OOB_FIELD_UPDATE_HOOKS[hid].get(name):
                _OOB_HANDLER.update(hid, name, val)

    def del_field_cache(obj, name):
        "On-model cache deleter"
        hid = hashid(obj)
        _SA(obj, "db_%s" % name, None)
        _GA(obj, "save")()
        if hid:
            try:
                del _FIELD_CACHE[hid][name]
            except KeyError:
                pass
            if _OOB_FIELD_UPDATE_HOOKS[hid].get(name):
                _OOB_HANDLER.update(hid, name, None)

    def flush_field_cache(obj=None):
        "On-model cache resetter"
        hid = hashid(obj)
        global _FIELD_CACHE
        if hid:
            del _FIELD_CACHE[hashid(obj)]
        else:
            # clean cache completely
            _FIELD_CACHE = defaultdict(dict)

    # on-object property cache (unrelated to database)
    # Note that the get/set_prop_cache handler do not actually
    # get/set the property "on" the object but only reads the
    # value to/from the cache. This is intended to be used
    # with a get/setter property on the object.

    def get_prop_cache(obj, name, default=None):
        "On-model Cache handler."
        global _PROP_CACHE
        hid = hashid(obj)
        if hid:
            try:
                val = _PROP_CACHE[hid][name]
            except KeyError:
                return default
            _PROP_CACHE[hid][name] = val
            return val
        return default

    def set_prop_cache(obj, name, val):
        "On-model Cache setter. Also updates database."
        hid = hashid(obj)
        if hid:
            global _PROP_CACHE
            _PROP_CACHE[hid][name] = val
            # oob hook functionality
            oob_hook = _OOB_PROP_UPDATE_HOOKS[hid].get(name)
            if oob_hook:
                oob_hook[0](obj.typeclass, name, val, *oob_hook[1], **oob_hook[2])


    def del_prop_cache(obj, name):
        "On-model cache deleter"
        try:
            del _PROP_CACHE[hashid(obj)][name]
        except KeyError:
            pass
    def flush_prop_cache(obj=None):
        "On-model cache resetter"
        hid = hashid(obj)
        global _PROP_CACHE
        if hid:
            del _PROP_CACHE[hashid(obj)]
        else:
            # clean cache completely
            _PROP_CACHE = defaultdict(dict)

    # attribute cache

    def get_attr_cache(obj, attrname):
        """
        Attribute cache store
        """
        return _ATTR_CACHE[hashid(obj)].get(attrname, None)

    def set_attr_cache(obj, attrname, attrobj):
        """
        Cache an attribute object
        """
        hid = hashid(obj)
        if hid:
            global _ATTR_CACHE
            _ATTR_CACHE[hid][attrname] = attrobj
            # oob hook functionality
            oob_hook = _OOB_ATTR_UPDATE_HOOKS[hid].get(attrname)
            if oob_hook:
                oob_hook[0](obj.typeclass, attrname, attrobj.value, *oob_hook[1], **oob_hook[2])

    def del_attr_cache(obj, attrname):
        """
        Remove attribute from cache
        """
        global _ATTR_CACHE
        try:
            del _ATTR_CACHE[hashid(obj)][attrname]
        except KeyError:
            pass

    def flush_attr_cache(obj=None):
        """
        Flush the attribute cache for this object.
        """
        global _ATTR_CACHE
        if obj:
            del _ATTR_CACHE[hashid(obj)]
        else:
            # clean cache completely
            _ATTR_CACHE = defaultdict(dict)


else:
    # local caches disabled. Use simple pass-through replacements

    def get_cache_sizes():
        return (0, 0), (0, 0), (0, 0)
    def get_field_cache(obj, name):
        return _GA(obj, "db_%s" % name)
    def set_field_cache(obj, name, val):
        _SA(obj, "db_%s" % name, val)
        _GA(obj, "save")()
        hid = hashid(obj)
        if _OOB_FIELD_UPDATE_HOOKS[hid].get(name):
            _OOB_HANDLER.update(hid, name, val)
    def del_field_cache(obj, name):
        _SA(obj, "db_%s" % name, None)
        _GA(obj, "save")()
        hid = hashid(obj)
        if _OOB_FIELD_UPDATE_HOOKS[hid].get(name):
            _OOB_HANDLER.update(hid, name, None)
    def flush_field_cache(obj=None):
        pass
    # these should get oob handlers when oob is implemented.
    def get_prop_cache(obj, name, default=None):
        return None
    def set_prop_cache(obj, name, val):
        pass
    def del_prop_cache(obj, name):
        pass
    def flush_prop_cache(obj=None):
        pass
    def get_attr_cache(obj, attrname):
        return None
    def set_attr_cache(obj, attrname, attrobj):
        pass
    def del_attr_cache(obj, attrname):
        pass
    def flush_attr_cache(obj=None):
        pass

