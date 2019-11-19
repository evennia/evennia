"""
Django ID mapper

Modified for Evennia by making sure that no model references
leave caching unexpectedly (no use of WeakRefs).

Also adds `cache_size()` for monitoring the size of the cache.
"""

import os
import threading
import gc
import time
from weakref import WeakValueDictionary
from twisted.internet.reactor import callFromThread
from django.core.exceptions import ObjectDoesNotExist, FieldError
from django.db.models.signals import post_save
from django.db.models.base import Model, ModelBase
from django.db.models.signals import pre_delete, post_migrate
from django.db.utils import DatabaseError
from evennia.utils import logger
from evennia.utils.utils import dbref, get_evennia_pids, to_str

from .manager import SharedMemoryManager

AUTO_FLUSH_MIN_INTERVAL = 60.0 * 5  # at least 5 mins between cache flushes

_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__
_MONITOR_HANDLER = None

# References to db-updated objects are stored here so the
# main process can be informed to re-cache itself.
PROC_MODIFIED_COUNT = 0
PROC_MODIFIED_OBJS = WeakValueDictionary()

# get info about the current process and thread; determine if our
# current pid is different from the server PID (i.e.  # if we are in a
# subprocess or not)
_SELF_PID = os.getpid()
_SERVER_PID, _PORTAL_PID = get_evennia_pids()
_IS_SUBPROCESS = (_SERVER_PID and _PORTAL_PID) and _SELF_PID not in (_SERVER_PID, _PORTAL_PID)
_IS_MAIN_THREAD = threading.currentThread().getName() == "MainThread"


class SharedMemoryModelBase(ModelBase):
    # CL: upstream had a __new__ method that skipped ModelBase's __new__ if
    # SharedMemoryModelBase was not in the model class's ancestors. It's not
    # clear what was the intended purpose, but skipping ModelBase.__new__
    # broke things; in particular, default manager inheritance.

    def __call__(cls, *args, **kwargs):
        """
        this method will either create an instance (by calling the default implementation)
        or try to retrieve one from the class-wide cache by inferring the pk value from
        `args` and `kwargs`. If instance caching is enabled for this class, the cache is
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
            cls.cache_instance(cached_instance, new=True)
        return cached_instance

    def _prepare(cls):
        """
        Prepare the cache, making sure that proxies of the same db base
        share the same cache.

        """
        # the dbmodel is either the proxy base or ourselves
        dbmodel = cls._meta.concrete_model if cls._meta.proxy else cls
        cls.__dbclass__ = dbmodel
        if not hasattr(dbmodel, "__instance_cache__"):
            # we store __instance_cache__ only on the dbmodel base
            dbmodel.__instance_cache__ = {}
        super()._prepare()

    def __new__(cls, name, bases, attrs):
        """
        Field shortcut creation:

        Takes field names `db_*` and creates property wrappers named
        without the `db_` prefix. So db_key -> key

        This wrapper happens on the class level, so there is no
        overhead when creating objects.  If a class already has a
        wrapper of the given name, the automatic creation is skipped.

        Notes:
            Remember to document this auto-wrapping in the class
            header, this could seem very much like magic to the user
            otherwise.
        """

        attrs["typename"] = cls.__name__
        attrs["path"] = "%s.%s" % (attrs["__module__"], name)
        attrs["_is_deleted"] = False

        # set up the typeclass handling only if a variable _is_typeclass is set on the class
        def create_wrapper(cls, fieldname, wrappername, editable=True, foreignkey=False):
            "Helper method to create property wrappers with unique names (must be in separate call)"

            def _get(cls, fname):
                "Wrapper for getting database field"
                if _GA(cls, "_is_deleted"):
                    raise ObjectDoesNotExist(
                        "Cannot access %s: Hosting object was already deleted." % fname
                    )
                return _GA(cls, fieldname)

            def _get_foreign(cls, fname):
                "Wrapper for returning foreignkey fields"
                if _GA(cls, "_is_deleted"):
                    raise ObjectDoesNotExist(
                        "Cannot access %s: Hosting object was already deleted." % fname
                    )
                return _GA(cls, fieldname)

            def _set_nonedit(cls, fname, value):
                "Wrapper for blocking editing of field"
                raise FieldError("Field %s cannot be edited." % fname)

            def _set(cls, fname, value):
                "Wrapper for setting database field"
                if _GA(cls, "_is_deleted"):
                    raise ObjectDoesNotExist(
                        "Cannot set %s to %s: Hosting object was already deleted!" % (fname, value)
                    )
                _SA(cls, fname, value)
                # only use explicit update_fields in save if we actually have a
                # primary key assigned already (won't be set when first creating object)
                update_fields = (
                    [fname] if _GA(cls, "_get_pk_val")(_GA(cls, "_meta")) is not None else None
                )
                _GA(cls, "save")(update_fields=update_fields)

            def _set_foreign(cls, fname, value):
                "Setter only used on foreign key relations, allows setting with #dbref"
                if _GA(cls, "_is_deleted"):
                    raise ObjectDoesNotExist(
                        "Cannot set %s to %s: Hosting object was already deleted!" % (fname, value)
                    )
                if isinstance(value, (str, int)):
                    value = to_str(value)
                    if value.isdigit() or value.startswith("#"):
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
                update_fields = (
                    [fname] if _GA(cls, "_get_pk_val")(_GA(cls, "_meta")) is not None else None
                )
                _GA(cls, "save")(update_fields=update_fields)

            def _del_nonedit(cls, fname):
                "wrapper for not allowing deletion"
                raise FieldError("Field %s cannot be edited." % fname)

            def _del(cls, fname):
                "Wrapper for clearing database field - sets it to None"
                _SA(cls, fname, None)
                update_fields = (
                    [fname] if _GA(cls, "_get_pk_val")(_GA(cls, "_meta")) is not None else None
                )
                _GA(cls, "save")(update_fields=update_fields)

            # wrapper factories
            if not editable:

                def fget(cls):
                    return _get(cls, fieldname)

                def fset(cls, val):
                    return _set_nonedit(cls, fieldname, val)

            elif foreignkey:

                def fget(cls):
                    return _get_foreign(cls, fieldname)

                def fset(cls, val):
                    return _set_foreign(cls, fieldname, val)

            else:

                def fget(cls):
                    return _get(cls, fieldname)

                def fset(cls, val):
                    return _set(cls, fieldname, val)

            def fdel(cls):
                return _del(cls, fieldname) if editable else _del_nonedit(cls, fieldname)

            # set docstrings for auto-doc
            fget.__doc__ = "A wrapper for getting database field `%s`." % fieldname
            fset.__doc__ = "A wrapper for setting (and saving) database field `%s`." % fieldname
            fdel.__doc__ = "A wrapper for deleting database field `%s`." % fieldname
            # assigning
            attrs[wrappername] = property(fget, fset, fdel)
            # type(cls).__setattr__(cls, wrappername, property(fget, fset, fdel))#, doc))

        # exclude some models that should not auto-create wrapper fields
        if cls.__name__ in ("ServerConfig", "TypeNick"):
            return
        # dynamically create the wrapper properties for all fields not already handled
        # (manytomanyfields are always handlers)
        for fieldname, field in (
            (fname, field)
            for fname, field in list(attrs.items())
            if fname.startswith("db_") and type(field).__name__ != "ManyToManyField"
        ):
            foreignkey = type(field).__name__ == "ForeignKey"
            wrappername = "dbid" if fieldname == "id" else fieldname.replace("db_", "", 1)
            if wrappername not in attrs:
                # makes sure not to overload manually created wrappers on the model
                create_wrapper(
                    cls, fieldname, wrappername, editable=field.editable, foreignkey=foreignkey
                )

        return super().__new__(cls, name, bases, attrs)


class SharedMemoryModel(Model, metaclass=SharedMemoryModelBase):
    """
    Base class for idmapped objects. Inherit from `this`.
    """

    objects = SharedMemoryManager()

    class Meta(object):
        abstract = True

    @classmethod
    def _get_cache_key(cls, args, kwargs):
        """
        This method is used by the caching subsystem to infer the PK
        value from the constructor arguments.  It is used to decide if
        an instance has to be built or is already in the cache.

        """
        result = None
        # Quick hack for my composites work for now.
        if hasattr(cls._meta, "pks"):
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

    @classmethod
    def get_cached_instance(cls, id):
        """
        Method to retrieve a cached instance by pk value. Returns None
        when not found (which will always be the case when caching is
        disabled for this class). Please note that the lookup will be
        done even when instance caching is disabled.

        """
        return cls.__dbclass__.__instance_cache__.get(id)

    @classmethod
    def cache_instance(cls, instance, new=False):
        """
        Method to store an instance in the cache.

        Args:
            instance (Class instance): the instance to cache.
            new (bool, optional): this is the first time this instance is
                cached (i.e. this is not an update operation like after a
                db save).

        """
        pk = instance._get_pk_val()
        if pk is not None:
            cls.__dbclass__.__instance_cache__[pk] = instance
            if new:
                try:
                    # trigger the at_init hook only
                    # at first initialization
                    instance.at_init()
                except AttributeError:
                    # The at_init hook is not assigned to all entities
                    pass

    @classmethod
    def get_all_cached_instances(cls):
        """
        Return the objects so far cached by idmapper for this class.

        """
        return list(cls.__dbclass__.__instance_cache__.values())

    @classmethod
    def _flush_cached_by_key(cls, key, force=True):
        """
        Remove the cached reference.

        """
        try:
            if force or cls.at_idmapper_flush():
                del cls.__dbclass__.__instance_cache__[key]
            else:
                cls._dbclass__.__instance_cache__[key].refresh_from_db()
        except KeyError:
            # No need to remove if cache doesn't contain it already
            pass

    @classmethod
    def flush_cached_instance(cls, instance, force=True):
        """
        Method to flush an instance from the cache. The instance will
        always be flushed from the cache, since this is most likely
        called from delete(), and we want to make sure we don't cache
        dead objects.

        """
        cls._flush_cached_by_key(instance._get_pk_val(), force=force)

    # flush_cached_instance = classmethod(flush_cached_instance)

    @classmethod
    def flush_instance_cache(cls, force=False):
        """
        This will clean safe objects from the cache. Use `force`
        keyword to remove all objects, safe or not.

        """
        if force:
            cls.__dbclass__.__instance_cache__ = {}
        else:
            cls.__dbclass__.__instance_cache__ = dict(
                (key, obj)
                for key, obj in cls.__dbclass__.__instance_cache__.items()
                if not obj.at_idmapper_flush()
            )

    # flush_instance_cache = classmethod(flush_instance_cache)

    # per-instance methods

    def __eq__(self, other):
        return super().__eq__(other)

    def __hash__(self):
        # this is required to maintain hashing
        return super().__hash__()

    def at_idmapper_flush(self):
        """
        This is called when the idmapper cache is flushed and
        allows customized actions when this happens.

        Returns:
            do_flush (bool): If True, flush this object as normal. If
                False, don't flush and expect this object to handle
                the flushing on its own.
        """
        return True

    def flush_from_cache(self, force=False):
        """
        Flush this instance from the instance cache. Use
        `force` to override the result of at_idmapper_flush() for the object.

        """
        pk = self._get_pk_val()
        if pk:
            if force or self.at_idmapper_flush():
                self.__class__.__dbclass__.__instance_cache__.pop(pk, None)

    def delete(self, *args, **kwargs):
        """
        Delete the object, clearing cache.

        """
        self.flush_from_cache()
        self._is_deleted = True
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        """
        Central database save operation.

        Notes:
            Arguments as per Django documentation.
            Calls `self.at_<fieldname>_postsave(new)`
            (this is a wrapper set by oobhandler:
            self._oob_at_<fieldname>_postsave())

        """
        global _MONITOR_HANDLER
        if not _MONITOR_HANDLER:
            from evennia.scripts.monitorhandler import MONITOR_HANDLER as _MONITOR_HANDLER

        if _IS_SUBPROCESS:
            # we keep a store of objects modified in subprocesses so
            # we know to update their caches in the central process
            global PROC_MODIFIED_COUNT, PROC_MODIFIED_OBJS
            PROC_MODIFIED_COUNT += 1
            PROC_MODIFIED_OBJS[PROC_MODIFIED_COUNT] = self

        if _IS_MAIN_THREAD:
            # in main thread - normal operation
            try:
                super().save(*args, **kwargs)
            except DatabaseError:
                # we handle the 'update_fields did not update any rows' error that
                # may happen due to timing issues with attributes
                ufields_removed = kwargs.pop("update_fields", None)
                if ufields_removed:
                    super().save(*args, **kwargs)
                else:
                    raise
        else:
            # in another thread; make sure to save in reactor thread
            def _save_callback(cls, *args, **kwargs):
                super().save(*args, **kwargs)

            callFromThread(_save_callback, self, *args, **kwargs)

        if not self.pk:
            # this can happen if some of the startup methods immediately
            # delete the object (an example are Scripts that start and die immediately)
            return

        # update field-update hooks and eventual OOB watchers
        new = False
        if "update_fields" in kwargs and kwargs["update_fields"]:
            # get field objects from their names
            update_fields = (
                self._meta.get_field(fieldname) for fieldname in kwargs.get("update_fields")
            )
        else:
            # meta.fields are already field objects; get them all
            new = True
            update_fields = self._meta.fields
        for field in update_fields:
            fieldname = field.name
            # trigger eventual monitors
            _MONITOR_HANDLER.at_update(self, fieldname)
            # if a hook is defined it must be named exactly on this form
            hookname = "at_%s_postsave" % fieldname
            if hasattr(self, hookname) and callable(_GA(self, hookname)):
                _GA(self, hookname)(new)

        #            # if a trackerhandler is set on this object, update it with the
        #            # fieldname and the new value
        #            fieldtracker = "_oob_at_%s_postsave" % fieldname
        #            if hasattr(self, fieldtracker):
        #                _GA(self, fieldtracker)(fieldname)
        pass


class WeakSharedMemoryModelBase(SharedMemoryModelBase):
    """
    Uses a WeakValue dictionary for caching instead of a regular one.

    """

    def _prepare(cls):
        super()._prepare()
        cls.__dbclass__.__instance_cache__ = WeakValueDictionary()


class WeakSharedMemoryModel(SharedMemoryModel, metaclass=WeakSharedMemoryModelBase):
    """
    Uses a WeakValue dictionary for caching instead of a regular one

    """

    class Meta(object):
        abstract = True


def flush_cache(**kwargs):
    """
    Flush idmapper cache. When doing so the cache will fire the
    at_idmapper_flush hook to allow the object to optionally handle
    its own flushing.

    Uses a signal so we make sure to catch cascades.

    """

    def class_hierarchy(clslist):
        """Recursively yield a class hierarchy"""
        for cls in clslist:
            subclass_list = cls.__subclasses__()
            if subclass_list:
                for subcls in class_hierarchy(subclass_list):
                    yield subcls
            else:
                yield cls

    for cls in class_hierarchy([SharedMemoryModel]):
        cls.flush_instance_cache()
    # run the python garbage collector
    return gc.collect()


# request_finished.connect(flush_cache)
post_migrate.connect(flush_cache)


def flush_cached_instance(sender, instance, **kwargs):
    """
    Flush the idmapper cache only for a given instance.

    """
    # XXX: Is this the best way to make sure we can flush?
    if not hasattr(instance, "flush_cached_instance"):
        return
    sender.flush_cached_instance(instance, force=True)


pre_delete.connect(flush_cached_instance)


def update_cached_instance(sender, instance, **kwargs):
    """
    Re-cache the given instance in the idmapper cache.

    """
    if not hasattr(instance, "cache_instance"):
        return
    sender.cache_instance(instance)


post_save.connect(update_cached_instance)


LAST_FLUSH = None


def conditional_flush(max_rmem, force=False):
    """
    Flush the cache if the estimated memory usage exceeds `max_rmem`.

    The flusher has a timeout to avoid flushing over and over
    in particular situations (this means that for some setups
    the memory usage will exceed the requirement and a server with
    more memory is probably required for the given game).

    Args:
        max_rmem (int): memory-usage estimation-treshold after which
            cache is flushed.
        force (bool, optional): forces a flush, regardless of timeout.
            Defaults to `False`.

    """
    global LAST_FLUSH

    def mem2cachesize(desired_rmem):
        """
        Estimate the size of the idmapper cache based on the memory
        desired. This is used to optionally cap the cache size.

        desired_rmem - memory in MB (minimum 50MB)

        The formula is empirically estimated from usage tests (Linux)
        and is
            Ncache = RMEM - 35.0 / 0.0157
        where RMEM is given in MB and Ncache is the size of the cache
        for this memory usage. VMEM tends to be about 100MB higher
        than RMEM for large memory usage.
        """
        vmem = max(desired_rmem, 50.0)
        Ncache = int(abs(float(vmem) - 35.0) / 0.0157)
        return Ncache

    if not max_rmem:
        # auto-flush is disabled
        return

    now = time.time()
    if not LAST_FLUSH:
        # server is just starting
        LAST_FLUSH = now
        return

    if ((now - LAST_FLUSH) < AUTO_FLUSH_MIN_INTERVAL) and not force:
        # too soon after last flush.
        logger.log_warn(
            "Warning: Idmapper flush called more than "
            "once in %s min interval. Check memory usage." % (AUTO_FLUSH_MIN_INTERVAL / 60.0)
        )
        return

    if os.name == "nt":
        # we can't look for mem info in Windows at the moment
        return

    # check actual memory usage
    Ncache_max = mem2cachesize(max_rmem)
    Ncache, _ = cache_size()
    actual_rmem = (
        float(os.popen("ps -p %d -o %s | tail -1" % (os.getpid(), "rss")).read()) / 1000.0
    )  # resident memory

    if Ncache >= Ncache_max and actual_rmem > max_rmem * 0.9:
        # flush cache when number of objects in cache is big enough and our
        # actual memory use is within 10% of our set max
        flush_cache()
        LAST_FLUSH = now


def cache_size(mb=True):
    """
    Calculate statistics about the cache.

    Note: we cannot get reliable memory statistics from the cache -
    whereas we could do `getsizof` each object in cache, the result is
    highly imprecise and for a large number of objects the result is
    many times larger than the actual memory usage of the entire server;
    Python is clearly reusing memory behind the scenes that we cannot
    catch in an easy way here.  Ideas are appreciated. /Griatch

    Returns:
      total_num, {objclass:total_num, ...}

    """
    numtotal = [0]  # use mutable to keep reference through recursion
    classdict = {}

    def get_recurse(submodels):
        for submodel in submodels:
            subclasses = submodel.__subclasses__()
            if not subclasses:
                num = len(submodel.get_all_cached_instances())
                numtotal[0] += num
                classdict[submodel.__dbclass__.__name__] = num
            else:
                get_recurse(subclasses)

    get_recurse(SharedMemoryModel.__subclasses__())
    return numtotal[0], classdict
