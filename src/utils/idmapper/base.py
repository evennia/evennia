from weakref import WeakValueDictionary

from django.db.models.base import Model, ModelBase

from manager import SharedMemoryManager

class SharedMemoryModelBase(ModelBase):
    def __new__(cls, name, bases, attrs):
        super_new = super(ModelBase, cls).__new__
        parents = [b for b in bases if isinstance(b, SharedMemoryModelBase)]
        if not parents:
            # If this isn't a subclass of Model, don't do anything special.
            return super_new(cls, name, bases, attrs)

        return super(SharedMemoryModelBase, cls).__new__(cls, name, bases, attrs)

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
        cls.__instance_cache__ = WeakValueDictionary()
        super(SharedMemoryModelBase, cls)._prepare()
        
        

class SharedMemoryModel(Model):
    # XXX: this is creating a model and it shouldn't be.. how do we properly
    # subclass now?
    __metaclass__ = SharedMemoryModelBase

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

    def _flush_cached_by_key(cls, key):
        del cls.__instance_cache__[key]
    _flush_cached_by_key = classmethod(_flush_cached_by_key)
        
    def flush_cached_instance(cls, instance):
        """
        Method to flush an instance from the cache. The instance will always be flushed from the cache, 
        since this is most likely called from delete(), and we want to make sure we don't cache dead objects.
        """
        cls._flush_cached_by_key(instance._get_pk_val())
    flush_cached_instance = classmethod(flush_cached_instance)
    
    def save(self, *args, **kwargs):
        super(SharedMemoryModel, self).save(*args, **kwargs)
        self.__class__.cache_instance(self)

    # TODO: This needs moved to the prepare stage (I believe?)
    objects = SharedMemoryManager()

from django.db.models.signals import pre_delete

# Use a signal so we make sure to catch cascades.
def flush_singleton_cache(sender, instance, **kwargs):
    # XXX: Is this the best way to make sure we can flush?
    if isinstance(instance, SharedMemoryModel):
        instance.__class__.flush_cached_instance(instance)
pre_delete.connect(flush_singleton_cache)

# XXX: It's to be determined if we should use this or not.
# def update_singleton_cache(sender, instance, **kwargs):
#     if isinstance(instance.__class__, SharedMemoryModel):
#          instance.__class__.cache_instance(instance)
# post_save.connect(flush_singleton_cache)