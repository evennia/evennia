"""
Django ID mapper

Modified for Evennia by making sure that no model references
leave caching unexpectedly (no use if WeakRefs).

Also adds cache_size() for monitoring the size of the cache.
"""

import os
from django.db.models.base import Model, ModelBase
from django.db.models.signals import post_save, pre_delete, \
  post_syncdb

from manager import SharedMemoryManager

# determine if our current pid is different from the server PID (i.e.
# if we are in a subprocess or not)
from src import PROC_MODIFIED_OBJS
def _get_pids():
    """
    Get the PID (Process ID) by trying to access
    an PID file.
    """
    from django.conf import settings
    server_pidfile = os.path.join(settings.GAME_DIR, 'server.pid')
    portal_pidfile = os.path.join(settings.GAME_DIR, 'portal.pid')
    server_pid, portal_pid = None, None
    if os.path.exists(server_pidfile):
        f = open(server_pidfile, 'r')
        server_pid = f.read()
        f.close()
    if os.path.exists(portal_pidfile):
        f = open(portal_pidfile, 'r')
        portal_pid = f.read()
        f.close()
    if server_pid and portal_pid:
        return int(server_pid), int(portal_pid)
    return None, None
_SELF_PID = os.getpid()
_SERVER_PID = None
_PORTAL_PID = None
_IS_SUBPROCESS = False


class SharedMemoryModelBase(ModelBase):
    # CL: upstream had a __new__ method that skipped ModelBase's __new__ if
    # SharedMemoryModelBase was not in the model class's ancestors. It's not
    # clear what was the intended purpose, but skipping ModelBase.__new__
    # broke things; in particular, default manager inheritance.

    def __call__(cls, *args, **kwargs):
        """
        this method will either create an instance (by calling the default implementation)
        or try to retrieve one from the class-wide cache by infering the pk value from
        args and kwargs. If instance caching is enabled for this class, the cache is
        populated whenever possible (ie when it is possible to infer the pk value).
        """
        def new_instance():
            return super(SharedMemoryModelBase, cls).__call__(*args, **kwargs)

        instance_key = cls._get_cache_key(args, kwargs)
        # depending on the arguments, we might not be able to infer the PK, so in that case we create a new instance
        if instance_key is None:
            return new_instance()

        cached_instance = cls.get_cached_instance(instance_key)
        if cached_instance is None:
            cached_instance = new_instance()
            cls.cache_instance(cached_instance)

        return cached_instance

    def _prepare(cls):
        cls.__instance_cache__ = {}  #WeakValueDictionary()
        super(SharedMemoryModelBase, cls)._prepare()


class SharedMemoryModel(Model):
    # CL: setting abstract correctly to allow subclasses to inherit the default
    # manager.
    __metaclass__ = SharedMemoryModelBase

    objects = SharedMemoryManager()

    class Meta:
        abstract = True

    def _get_cache_key(cls, args, kwargs):
        """
        This method is used by the caching subsystem to infer the PK value from the constructor arguments.
        It is used to decide if an instance has to be built or is already in the cache.
        """
        result = None
        # Quick hack for my composites work for now.
        if hasattr(cls._meta, 'pks'):
            pk = cls._meta.pks[0]
        else:
            pk = cls._meta.pk
        # get the index of the pk in the class fields. this should be calculated *once*, but isn't atm
        pk_position = cls._meta.fields.index(pk)
        if len(args) > pk_position:
            # if it's in the args, we can get it easily by index
            result = args[pk_position]
        elif pk.attname in kwargs:
            # retrieve the pk value. Note that we use attname instead of name, to handle the case where the pk is a
            # a ForeignKey.
            result = kwargs[pk.attname]
        elif pk.name != pk.attname and pk.name in kwargs:
            # ok we couldn't find the value, but maybe it's a FK and we can find the corresponding object instead
            result = kwargs[pk.name]

        if result is not None and isinstance(result, Model):
            # if the pk value happens to be a model instance (which can happen wich a FK), we'd rather use its own pk as the key
            result = result._get_pk_val()
        return result
    _get_cache_key = classmethod(_get_cache_key)

    def get_cached_instance(cls, id):
        """
        Method to retrieve a cached instance by pk value. Returns None when not found
        (which will always be the case when caching is disabled for this class). Please
        note that the lookup will be done even when instance caching is disabled.
        """
        return cls.__instance_cache__.get(id)
    get_cached_instance = classmethod(get_cached_instance)

    def cache_instance(cls, instance):
        """
        Method to store an instance in the cache.
        """
        if instance._get_pk_val() is not None:
            cls.__instance_cache__[instance._get_pk_val()] = instance
    cache_instance = classmethod(cache_instance)

    def get_all_cached_instances(cls):
        "return the objects so far cached by idmapper for this class."
        return cls.__instance_cache__.values()
    get_all_cached_instances = classmethod(get_all_cached_instances)

    def _flush_cached_by_key(cls, key):
        try:
            del cls.__instance_cache__[key]
        except KeyError:
            pass
    _flush_cached_by_key = classmethod(_flush_cached_by_key)

    def flush_cached_instance(cls, instance):
        """
        Method to flush an instance from the cache. The instance will always be flushed from the cache,
        since this is most likely called from delete(), and we want to make sure we don't cache dead objects.
        """
        cls._flush_cached_by_key(instance._get_pk_val())
    flush_cached_instance = classmethod(flush_cached_instance)

    def flush_instance_cache(cls):
        cls.__instance_cache__ = {} #WeakValueDictionary()
    flush_instance_cache = classmethod(flush_instance_cache)

    def save(cls, *args, **kwargs):
        "overload spot for saving"
        global _SERVER_PID, _PORTAL_PID, _IS_SUBPROCESS, _SELF_PID
        if not _SERVER_PID and not _PORTAL_PID:
            _SERVER_PID, _PORTAL_PID = _get_pids()
            _IS_SUBPROCESS = (_SERVER_PID and _PORTAL_PID) and (_SERVER_PID != _SELF_PID) and (_PORTAL_PID != _SELF_PID)
        if _IS_SUBPROCESS:
            #print "storing in PROC_MODIFIED_OBJS:", cls.db_key, cls.id
            PROC_MODIFIED_OBJS.append(cls)
        super(SharedMemoryModel, cls).save(*args, **kwargs)

# Use a signal so we make sure to catch cascades.
def flush_cache(**kwargs):
    def class_hierarchy(root):
        """Recursively yield a class hierarchy."""
        yield root
        for subcls in root.__subclasses__():
            for cls in class_hierarchy(subcls):
                yield cls
    for model in class_hierarchy(SharedMemoryModel):
        model.flush_instance_cache()
#request_finished.connect(flush_cache)
post_syncdb.connect(flush_cache)


def flush_cached_instance(sender, instance, **kwargs):
    # XXX: Is this the best way to make sure we can flush?
    if not hasattr(instance, 'flush_cached_instance'):
        return
    sender.flush_cached_instance(instance)
pre_delete.connect(flush_cached_instance)

def update_cached_instance(sender, instance, **kwargs):
    if not hasattr(instance, 'cache_instance'):
        return
    sender.cache_instance(instance)
post_save.connect(update_cached_instance)

def cache_size(mb=True):
    """
    Returns a dictionary with estimates of the
    cache size of each subclass.

    mb - return the result in MB.
    """
    import sys
    sizedict = {"_total": [0, 0]}
    def getsize(model):
        instances = model.get_all_cached_instances()
        linst = len(instances)
        size = sum([sys.getsizeof(o) for o in instances])
        size = (mb and size/1024.0) or size
        return (linst, size)
    def get_recurse(submodels):
        for submodel in submodels:
            subclasses = submodel.__subclasses__()
            if not subclasses:
                tup = getsize(submodel)
                sizedict["_total"][0] += tup[0]
                sizedict["_total"][1] += tup[1]
                sizedict[submodel.__name__] = tup
            else:
                get_recurse(subclasses)
    get_recurse(SharedMemoryModel.__subclasses__())
    sizedict["_total"] = tuple(sizedict["_total"])
    return sizedict

