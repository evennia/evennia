"""
The cache module implements a volatile and
semi-volatile storage
object mechanism for Evennia.

Volatile Cache:

Data stored using the Cache is stored in
memory (so requires no database access). The
drawback is that it will be lost upon a
reboot. It is however @reload-safe unless
explicitly flushed with @reload/cache (the cache
is not flushed with @reload/all)

Access I/O of the cache is normally done through
the object model, using e.g.

source_object.cache.variable = data 
and
data = source_object.cache.variable

Semi-persistent Cache:

This form of cache works like the volatile cache but the
data will survive a reboot since the state is backed up
to the database at regular intervals (it is thus a save-point
scheme). How often the backup is done can be set in preferences.

Access I/O:

source_object.pcache = data
and
data = source_object.pcache 

Whereas you can also access the cache(s) using
set_cache/get_cache and set_pcache/get_pcache
directly, you must continue to use these methods
on a particular piece of data once you start using them
(i.e. you won't be able to use dot-notation to retrieve
a piece of data saved explicitly using set_cache())

"""
from src.cache.models import PersistentCache
from src import logger

class Cache(object):
    """
    Each Cache object is intended to store the volatile properties
    of one in-game database object or one user-defined application.

    By default, the object allows to safely reference variables on
    itself also if it does not exist (so test = cache.var will
    set test to None if cache has no attribute var instead of raising
    a traceback). This allows for stable and transparent operation
    during most circumstances.
    
    Due to how the objects are stored in database (using pickle), the
    object has a __safedot switch to deactivate the safe mode
    of variables mentioned above; this is necessary in order to have
    pickle work correctly (it does not like redefining __getattr__)
    and should not be used for anything else.

    Observe that this object in itself is not persistent, the only
    thing determining if it is persistent is which of the global
    variables (CACHE or PCACHE) it is saved in (and that there
    exists an event to save the cache at regular intervals, use
    @ps to check that this is the case).

    """            

    __safedot = True

    def __getattr__(self, key):
        """
        This implements a safe dot notation (i.e. it will not
        raise an exception if a variable does not exist)
        """
        if self.__safedot:
            return self.__dict__.get(key, None)
        else:
            super(Cache, self).__getattr__(key)

    def show(self):
        """
        Return nice display of data.
        """
        return ", ".join(key for key in sorted(self.__dict__.keys())
                         if key != '_Cache__safedot')
    
    def store(self, key, value):
        """
        Store data directly, without going through the dot notation.
        """
        if key != '__safedot':
            self.__dict__[key] = value

    def retrieve(self, key):
        """
        Retrieve data directly, without going through dot notation.
        Note that this intentionally raises a KeyError if key is not
        found. This is mainly used by get_cache to determine if a
        new cache object should be created. 
        """
        return self.__dict__[key]
         
    def pickle_yes(self):
        """
        Since pickle cannot handle a custom getattr, we
        need to deactivate it before pickling. 
        """
        self.__safedot = False
        for data in (data for data in self.__dict__.values()
                     if type(data)==type(self)):
            data.pickle_yes()

    def pickle_no(self):
        """
        Convert back from pickle mode to normal safe dot notation.              
        """
        self.__safedot = True
        for data in (data for data in self.__dict__.values()
                     if type(data)==type(self)):
            data.pickle_no()            
            
    def has_key(self, key):
        """
        Decide if cache has a particular piece of data.
        """
        return key in self.__dict__

    def to_dict(self):
        """
        Return all data stored in cache in
        the form of a dictionary.
        """
        return self.__dict__

    def del_key(self, key):
        """
        Clear cache data.
        """
        if key in self.__dict__:
            del self.__dict__[key]
        
# Cache access functions - these only deal with the default global
# cache and pcache. 

# Volatile cache

def set_cache(cache_key, value):
    """
    Set a value in the volatile cache (oftenmost this is done
    through properties instead).
    """
    CACHE.store(cache_key, value)
    
def get_cache(cache_key):
    """
    Retrieve a cache object from the storage. This is primarily
    used by the objects.models.Object.cache property. 
        
    cache_key - identifies the cache storage area (e.g. an object dbref)
    reference - this bool describes if the function is called as part of
                a obj.cache.cache_key.data contstruct.
    """
    try:
        return CACHE.retrieve(cache_key)
    except:
        CACHE.store(cache_key, Cache())
        return CACHE.retrieve(cache_key)
    
def flush_cache(cache_key=None):
    """
    Clears a particular cache_key from memory.  If
    no key is given, entire cache is flushed. 
    """
    global CACHE
    if cache_key == None:
        CACHE = Cache()
    else:
        CACHE.del_key(cache_key)

# Persistent cache

def set_pcache(cache_key, value):
    """
    Set a value in the volatile cache (oftenmost this is done
    through properties instead).
    """
    PCACHE.store(cache_key, value)

def get_pcache(pcache_key):
    """
    Retrieve a pcache object from the storage. This is primarily
    used by the objects.models.Object.cache property. 
        
    cache_key - identifies the cache storage area (e.g. an object dbref)
    """
    try:
        return PCACHE.retrieve(pcache_key)
    except KeyError:
        PCACHE.store(pcache_key, Cache())
        return PCACHE.retrieve(pcache_key)
     
def flush_pcache(pcache_key=None):
    """
    Clears a particular cache_key from memory.  If
    no key is given, entire cache is flushed. 
    """
    global PCACHE
    if pcache_key == None:
        PCACHE = Cache()
    elif pcache_key in PCACHE.__dict__:
        PCACHE.del_key(pcache_key)        

def show():
    """
    Show objects stored in caches
    """
    return CACHE.show(), PCACHE.show()

# Admin-level commands for initializing and saving/loading pcaches. 

def init_pcache(cache_name=None):
    """
    Creates the global pcache object in database.
    (this is normally only called by initial_setup.py)
    """
    from src.cache.managers.cache import GLOBAL_PCACHE_NAME        

    pcache = PersistentCache()
    if cache_name:
        pcache.cache_name = cache_name
    else:
        pcache.cache_name = GLOBAL_PCACHE_NAME    
    #initial save of the the empty pcache object to database
    pcache.save()
    #create empty storage object  in cache
    pcache.save_cache(Cache())
    
def save_pcache(cache_name=""):
    """
    Force-save persistent cache right away. 
    """
    try:
        if cache_name:            
            pcache = PersistentCache.objects.get(cache_name=cache_name) 
        else:                
            pcache = PersistentCache.objects.get_default_pcache()           
    except:
        logger.log_errmsg("Save error: %s Pcache not initialized." % cache_name)
        return        
    pcache.save_cache(PCACHE)
    
def load_pcache(cache_name=""):
    """
    Load pcache from database storage. This is also called during
    startup and fills the pcache with persistent cache data. 
    """
    global PCACHE
    try:
        if cache_name:
            pcache = PersistentCache.objects.get(cache_name=cache_name) 
            return pcache
        else:
            pcache = PersistentCache.objects.get_default_pcache()           
    except:
        logger.log_errmsg("Could not load %s: Pcache not found." % cache_name)
        return
    if pcache :
        print " Loading persistent cache from disk."
        unpacked = pcache.load_cache()
        if unpacked:
            PCACHE = unpacked
    
# Volatile Cache. This is a non-persistent cache. It will be lost upon
# a reboot. This can be referenced directly, but most
# transparently it's accessed through the object model.
CACHE = Cache()

# Persistent Cache. The system will make sure to save the contents of this
# cache at regular intervals, recovering it after a server
# reboot. It is accessed directly or through the object model. 
PCACHE = Cache()
