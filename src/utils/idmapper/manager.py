from django.db.models.manager import Manager

class SharedMemoryManager(Manager):
    # TODO: improve on this implementation
    # We need a way to handle reverse lookups so that this model can
    # still use the singleton cache, but the active model isn't required
    # to be a SharedMemoryModel.
    def get(self, **kwargs):
        items = kwargs.keys()
        inst = None
        if len(items) == 1 and items[0] in ('pk', self.model._meta.pk.attname):
            inst = self.model.get_cached_instance(kwargs[items[0]])
        if inst is None:
            inst = super(SharedMemoryManager, self).get(**kwargs)
        return inst