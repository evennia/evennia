"""
The cache module implements a volatile storage
object mechanism for Evennia.

Data stored using this module is stored in
memory (so requires no database access). The
drawback is that it will be lost upon a
reboot. It is however @reload-safe unless
explicitly flushed with @reload/cache (the cache
is not flushed with @reload/all)

Access I/O of the cache is normally done through
the object model, using e.g.

source_object.cache.variable = data 
or
data = source_object.cache.variable
"""

# global storage. This can be references directly, but most
# transparently it's accessed through the object model.

CACHE = {}

class Cache(dict):
    """
    This storage object is stored to act as a save target for
    volatile variables through use of object properties. It
    can also be used as a dict if desired. It lists the contents
    of itself and makes sure to return None of the sought attribute
    is not set on itself (so test = cache.var will set test to None
    if cache has no attribute var instead of raising a traceback).

    Each Cache object is intended to store the volatile properties
    of one in-game database object or one user-defined application.
    """
    def __str__(self):
        """
        Printing the cache object shows all properties
        stored on it. 
        """
        return ", ".join(sorted(self.__dict__.keys()))

    def __getattr__(self, name):
        """
        Make sure to return None if the attribute is not set.
        (instead of the usual traceback)
        """
        return self.__dict__.get(name, None)

         
def get(cache_key):
    """
    Retrieve a cache object from the storage. This is primarily
    used by the objects.models.Object.cache property. 
        
    cache_key - identifies the cache storage area (e.g. an object dbref)
    """
    if cache_key not in CACHE: 
        CACHE[cache_key] = Cache()
    return CACHE[cache_key]

def flush(cache_key=None):
    """
    Clears a particular cache_key from memory.  If
    no key is given, entire cache is flushed. 
    """
    global CACHE
    if cache_key == None:
        CACHE = {}
    elif cache_key in CACHE:
        del CACHE[cache_key]
        
def show():
    """
    Show objects stored in cache
    """
    return CACHE.keys()
    
