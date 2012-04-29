from django.db.models.manager import Manager
try:
    from django.db import router
except:
    pass


class SharedMemoryManager(Manager):
    # CL: this ensures our manager is used when accessing instances via
    # ForeignKey etc. (see docs)
    use_for_related_fields = True

    # CL: in the dev version of django, ReverseSingleRelatedObjectDescriptor
    # will call us as:
    #     rel_obj = rel_mgr.using(db).get(**params)
    # We need to handle using, or the get method will be called on a vanilla
    # queryset, and we won't get a change to use the cache.
    def using(self, alias):
        if alias == router.db_for_read(self.model):
            return self
        else:
            return super(SharedMemoryManager, self).using(alias)

    # TODO: improve on this implementation
    # We need a way to handle reverse lookups so that this model can
    # still use the singleton cache, but the active model isn't required
    # to be a SharedMemoryModel.
    def get(self, **kwargs):
        items = kwargs.keys()
        inst = None
        if len(items) == 1:
            # CL: support __exact
            key = items[0]
            if key.endswith('__exact'):
                key = key[:-len('__exact')]
            if key in ('pk', self.model._meta.pk.attname):
                inst = self.model.get_cached_instance(kwargs[items[0]])
        if inst is None:
            inst = super(SharedMemoryManager, self).get(**kwargs)
        return inst
