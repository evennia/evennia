Django Identity Mapper
======================

A pluggable Django application which allows you to explicitally mark your models to use an identity mapping pattern. This will share instances of the same model in memory throughout your interpreter.

Please note, that deserialization (such as from the cache) will *not* use the identity mapper.

Usage
-----
To use the shared memory model you simply need to inherit from it (instead of models.Model). This enable all queries (and relational queries) to this model to use the shared memory instance cache, effectively creating a single instance for each unique row (based on primary key) in the queryset.

For example, if you want to simply mark all of your models as a SharedMemoryModel, you might as well just import it as models.
::

	from idmapper import models

	class MyModel(models.SharedMemoryModel):
	    name = models.CharField(...)

Because the system is isolated, you may mix and match SharedMemoryModel's with regular Model's.
::

	from idmapper import models

	class MyModel(models.SharedMemoryModel):
	    name = models.CharField(...)
	    fkey = models.ForeignKey('Other')

	class Other(models.Model):
	    name = models.CharField(...)

References
----------

Original code and concept: http://code.djangoproject.com/ticket/17