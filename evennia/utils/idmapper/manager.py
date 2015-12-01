"""
IDmapper extension to the default manager.
"""
from django.db.models.manager import Manager

class SharedMemoryManager(Manager):
    # CL: this ensures our manager is used when accessing instances via
    # ForeignKey etc. (see docs)
    use_for_related_fields = True

    # TODO: improve on this implementation
    # We need a way to handle reverse lookups so that this model can
    # still use the singleton cache, but the active model isn't required
    # to be a SharedMemoryModel.
    def get(self, *args, **kwargs):
        """
        Data entity lookup.
        """
        items = list(kwargs)
        inst = None
        if len(items) == 1:
            # CL: support __exact
            key = items[0]
            if key.endswith('__exact'):
                key = key[:-len('__exact')]
            if key in ('pk', self.model._meta.pk.attname):
                inst = self.model.get_cached_instance(kwargs[items[0]])
        if inst is None:
            inst = super(SharedMemoryManager, self).get(*args, **kwargs)
        return inst
