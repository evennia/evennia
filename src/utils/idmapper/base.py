"""
Django ID mapper

Modified for Evennia by making sure that no model references
leave caching unexpectedly (no use if WeakRefs).

Also adds cache_size() for monitoring the size of the cache.
"""

import os, threading
#from twisted.internet import reactor
#from twisted.internet.threads import blockingCallFromThread
from twisted.internet.reactor import callFromThread
from django.core.exceptions import ObjectDoesNotExist, FieldError
from django.db.models.base import Model, ModelBase
from django.db.models.signals import post_save, pre_delete, post_syncdb
from src.utils.utils import dbref, get_evennia_pids, to_str

from manager import SharedMemoryManager

_FIELD_CACHE_GET = None
_FIELD_CACHE_SET = None
_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__


# determine if our current pid is different from the server PID (i.e.
# if we are in a subprocess or not)
from src import PROC_MODIFIED_OBJS

# get info about the current process and thread
_SELF_PID = os.getpid()
_SERVER_PID, _PORTAL_PID = get_evennia_pids()
_IS_SUBPROCESS = (_SERVER_PID and _PORTAL_PID) and not _SELF_PID in (_SERVER_PID, _PORTAL_PID)
_IS_MAIN_THREAD = threading.currentThread().getName() == "MainThread"

#_SERVER_PID = None
#_PORTAL_PID = None
#        #global _SERVER_PID, _PORTAL_PID, _IS_SUBPROCESS, _SELF_PID
#        if not _SERVER_PID and not _PORTAL_PID:
#            _IS_SUBPROCESS = (_SERVER_PID and _PORTAL_PID) and not _SELF_PID in (_SERVER_PID, _PORTAL_PID)

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

    def __new__(cls, classname, bases, classdict, *args, **kwargs):
        """
        Field shortcut creation:
        Takes field names db_* and creates property wrappers named without the db_ prefix. So db_key -> key
        This wrapper happens on the class level, so there is no overhead when creating objects. If a class
        already has a wrapper of the given name, the automatic creation is skipped. Note: Remember to
        document this auto-wrapping in the class header, this could seem very much like magic to the user otherwise.
        """
        def create_wrapper(cls, fieldname, wrappername, editable=True, foreignkey=False):
            "Helper method to create property wrappers with unique names (must be in separate call)"
            def _get(cls, fname):
                "Wrapper for getting database field"
                #print "_get:", fieldname, wrappername,_GA(cls,fieldname)
                return _GA(cls, fieldname)
            def _get_foreign(cls, fname):
                "Wrapper for returing foreignkey fields"
                value = _GA(cls, fieldname)
                #print "_get_foreign:value:", value
                try:
                    return _GA(value, "typeclass")
                except:
                    return value
            def _set_nonedit(cls, fname, value):
                "Wrapper for blocking editing of field"
                raise FieldError("Field %s cannot be edited." % fname)
            def _set(cls, fname, value):
                "Wrapper for setting database field"
                _SA(cls, fname, value)
                # only use explicit update_fields in save if we actually have a
                # primary key assigned already (won't be set when first creating object)
                update_fields = [fname] if _GA(cls, "_get_pk_val")(_GA(cls, "_meta")) is not None else None
                _GA(cls, "save")(update_fields=update_fields)
            def _set_foreign(cls, fname, value):
                "Setter only used on foreign key relations, allows setting with #dbref"
                try:
                    value = _GA(value, "dbobj")
                except AttributeError:
                    pass
                if isinstance(value, (basestring, int)):
                    value = to_str(value, force_string=True)
                    if (value.isdigit() or value.startswith("#")):
                        # we also allow setting using dbrefs, if so we try to load the matching object.
                        # (we assume the object is of the same type as the class holding the field, if
                        # not a custom handler must be used for that field)
                        dbid = dbref(value, reqhash=False)
                        if dbid:
                            model = _GA(cls, "_meta").get_field(fname).model
                            try:
                                value = model._default_manager.get(id=dbid)
                            except ObjectDoesNotExist:
                                # maybe it is just a name that happens to look like a dbid
                                pass
                _SA(cls, fname, value)
                # only use explicit update_fields in save if we actually have a
                # primary key assigned already (won't be set when first creating object)
                update_fields = [fname] if _GA(cls, "_get_pk_val")(_GA(cls, "_meta")) is not None else None
                _GA(cls, "save")(update_fields=update_fields)
            def _del_nonedit(cls, fname):
                "wrapper for not allowing deletion"
                raise FieldError("Field %s cannot be edited." % fname)
            def _del(cls, fname):
                "Wrapper for clearing database field - sets it to None"
                _SA(cls, fname, None)
                update_fields = [fname] if _GA(cls, "_get_pk_val")(_GA(cls, "_meta")) is not None else None
                _GA(cls, "save")(update_fields=update_fields)

            # wrapper factories
            fget = lambda cls: _get(cls, fieldname)
            if not editable:
                fset = lambda cls, val: _set_nonedit(cls, fieldname, val)
            elif foreignkey:
                fget = lambda cls: _get_foreign(cls, fieldname)
                fset = lambda cls, val: _set_foreign(cls, fieldname, val)
            else:
                fset = lambda cls, val: _set(cls, fieldname, val)
            fdel = lambda cls: _del(cls, fieldname) if editable else _del_nonedit(cls,fieldname)
            # assigning
            classdict[wrappername] = property(fget, fset, fdel)
            #type(cls).__setattr__(cls, wrappername, property(fget, fset, fdel))#, doc))

        # exclude some models that should not auto-create wrapper fields
        if cls.__name__ in ("ServerConfig", "TypeNick"):
            return
        # dynamically create the wrapper properties for all fields not already handled (manytomanyfields are always handlers)
        for fieldname, field in ((fname, field) for fname, field in classdict.items()
                                  if fname.startswith("db_") and type(field).__name__ != "ManyToManyField"):
            foreignkey = type(field).__name__ == "ForeignKey"
            #print fieldname, type(field).__name__, field
            wrappername = "dbid" if fieldname == "id" else fieldname.replace("db_", "", 1)
            if wrappername not in classdict:
                # makes sure not to overload manually created wrappers on the model
                #print "wrapping %s -> %s" % (fieldname, wrappername)
                create_wrapper(cls, fieldname, wrappername, editable=field.editable, foreignkey=foreignkey)
        return super(SharedMemoryModelBase, cls).__new__(cls, classname, bases, classdict, *args, **kwargs)

    #def __init__(cls, *args, **kwargs):
    #    """
    #    Field shortcut creation:
    #    Takes field names db_* and creates property wrappers named without the db_ prefix. So db_key -> key
    #    This wrapper happens on the class level, so there is no overhead when creating objects. If a class
    #    already has a wrapper of the given name, the automatic creation is skipped. Note: Remember to
    #    document this auto-wrapping in the class header, this could seem very much like magic to the user otherwise.
    #    """
    #    super(SharedMemoryModelBase, cls).__init__(*args, **kwargs)
    #    def create_wrapper(cls, fieldname, wrappername, editable=True):
    #        "Helper method to create property wrappers with unique names (must be in separate call)"
    #        def _get(cls, fname):
    #            "Wrapper for getting database field"
    #            value = _GA(cls, fieldname)
    #            if type(value) in (basestring, int, float, bool):
    #                return value
    #            elif hasattr(value, "typeclass"):
    #                return _GA(value, "typeclass")
    #            return value
    #        def _set_nonedit(cls, fname, value):
    #            "Wrapper for blocking editing of field"
    #            raise FieldError("Field %s cannot be edited." % fname)
    #        def _set(cls, fname, value):
    #            "Wrapper for setting database field"
    #            #print "_set:", fname
    #            if hasattr(value, "dbobj"):
    #                value = _GA(value, "dbobj")
    #            elif isinstance(value, basestring) and (value.isdigit() or value.startswith("#")):
    #                # we also allow setting using dbrefs, if so we try to load the matching object.
    #                # (we assume the object is of the same type as the class holding the field, if
    #                # not a custom handler must be used for that field)
    #                dbid = dbref(value, reqhash=False)
    #                if dbid:
    #                    try:
    #                        value = cls._default_manager.get(id=dbid)
    #                    except ObjectDoesNotExist:
    #                        # maybe it is just a name that happens to look like a dbid
    #                        from src.utils.logger import log_trace
    #                        log_trace()
    #            #print "_set wrapper:", fname, value, type(value), cls._get_pk_val(cls._meta)
    #            _SA(cls, fname, value)
    #            # only use explicit update_fields in save if we actually have a
    #            # primary key assigned already (won't be set when first creating object)
    #            update_fields = [fname] if _GA(cls, "_get_pk_val")(_GA(cls, "_meta")) is not None else None
    #            _GA(cls, "save")(update_fields=update_fields)
    #        def _del_nonedit(cls, fname):
    #            "wrapper for not allowing deletion"
    #            raise FieldError("Field %s cannot be edited." % fname)
    #        def _del(cls, fname):
    #            "Wrapper for clearing database field - sets it to None"
    #            _SA(cls, fname, None)
    #            update_fields = [fname] if _GA(cls, "_get_pk_val")(_GA(cls, "_meta")) is not None else None
    #            _GA(cls, "save")(update_fields=update_fields)

    #        # create class field wrappers
    #        fget = lambda cls: _get(cls, fieldname)
    #        fset = lambda cls, val: _set(cls, fieldname, val) if editable else _set_nonedit(cls, fieldname, val)
    #        fdel = lambda cls: _del(cls, fieldname) if editable else _del_nonedit(cls,fieldname)
    #        type(cls).__setattr__(cls, wrappername, property(fget, fset, fdel))#, doc))

    #    # exclude some models that should not auto-create wrapper fields
    #    if cls.__name__ in ("ServerConfig", "TypeNick"):
    #        return
    #    # dynamically create the wrapper properties for all fields not already handled
    #    for field in cls._meta.fields:
    #        fieldname = field.name
    #        if fieldname.startswith("db_"):
    #            wrappername = "dbid" if fieldname == "id" else fieldname.replace("db_", "")
    #            if not hasattr(cls, wrappername):
    #                # makes sure not to overload manually created wrappers on the model
    #                #print "wrapping %s -> %s" % (fieldname, wrappername)
    #                create_wrapper(cls, fieldname, wrappername, editable=field.editable)

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

    def _flush_cached_by_key(cls, key):
        try:
            del cls.__instance_cache__[key]
        except KeyError:
            pass
    _flush_cached_by_key = classmethod(_flush_cached_by_key)

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
        "save method tracking process/thread issues"

        if _IS_SUBPROCESS:
            # we keep a store of objects modified in subprocesses so
            # we know to update their caches in the central process
            PROC_MODIFIED_OBJS.append(cls)

        if _IS_MAIN_THREAD:
            # in main thread - normal operation
            super(SharedMemoryModel, cls).save(*args, **kwargs)
        else:
            # in another thread; make sure to save in reactor thread
            def _save_callback(cls, *args, **kwargs):
                super(SharedMemoryModel, cls).save(*args, **kwargs)
            #blockingCallFromThread(reactor, _save_callback, cls, *args, **kwargs)
            callFromThread(_save_callback, cls, *args, **kwargs)

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

