"""
Central caching module.

"""

from sys import getsizeof
from collections import defaultdict
from weakref import WeakKeyDictionary

_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__

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

def hashid(obj):
    """
    Returns a per-class unique that combines the object's
    class name with its idnum and creation time. This makes this id unique also
    between different typeclassed entities such as scripts and
    objects (which may still have the same id).
    """
    try:
        hid = _GA(obj, "_hashid")
    except AttributeError:
        date, idnum = _GA(obj, "db_date_created"), _GA(obj, "id")
        if not idnum or not date:
            # this will happen if setting properties on an object
            # which is not yet saved
            return None
        # build the hashid
        hid = "%s-%s-#%s" % (_GA(obj, "__class__"), date, idnum)
        _SA(obj, "_hashid", hid)
    return hid

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

def del_field_cache(obj, name):
    "On-model cache deleter"
    hid = hashid(obj)
    if hid:
        try:
            del _FIELD_CACHE[hid][name]
        except KeyError:
            pass

def flush_field_cache(obj):
    "On-model cache resetter"
    hid = hashid(obj)
    if hid:
        global _FIELD_CACHE
        del _FIELD_CACHE[hashid(obj)]

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
            return _PROP_CACHE[hid][name]
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

def del_prop_cache(obj, name):
    "On-model cache deleter"
    try:
        del _PROP_CACHE[hashid(obj)][name]
    except KeyError:
        pass
def flush_field_cache(obj):
    "On-model cache resetter"
    hid = hashid(obj)
    if hid:
        global _PROP_CACHE
        del _PROP_CACHE[hashid(obj)]


# attribute cache

def get_attr_cache(obj, attrname):
    """
    Attribute cache store
    """
    return _ATTR_CACHE[hashid(obj)].get(attrname)

def set_attr_cache(obj, attrname, attrobj):
    """
    Cache an attribute object
    """
    global _ATTR_CACHE
    _ATTR_CACHE[hashid(obj)][attrname] = attrobj

def del_attr_cache(obj, attrname):
    """
    Remove attribute from cache
    """
    global _ATTR_CACHE
    try:
        del _ATTR_CACHE[hashid(obj)][attrname]
    except KeyError:
        pass

def flush_attr_cache(obj):
    """
    Flush the attribute cache for this object.
    """
    global _ATTR_CACHE
    del _ATTR_CACHE[hashid(obj)]
