This fork of django-idmapper fixes some bugs that prevented the
idmapper from being used in many instances. In particular, the caching
manager is now inherited by SharedMemoryManager subclasses, and it is
used when Django uses an automatic manager (see
http://docs.djangoproject.com/en/dev/topics/db/managers/#controlling-automatic-manager-types).
This means access through foreign keys now uses identity mapping.

Tested with Django version 1.2 alpha 1 SVN-12375.

My modifications are usually accompanied by comments marked with "CL:".

Django Identity Mapper
======================

A pluggable Django application which allows you to explicitally mark
your models to use an identity mapping pattern. This will share
instances of the same model in memory throughout your interpreter.

Please note, that deserialization (such as from the cache) will *not* use the identity mapper.

Usage
----- To use the shared memory model you simply need to inherit from
it (instead of models.Model). This enable all queries (and relational
queries) to this model to use the shared memory instance cache,
effectively creating a single instance for each unique row (based on
primary key) in the queryset.

For example, if you want to simply mark all of your models as a
SharedMemoryModel, you might as well just import it as models.
::

	from idmapper import models

	class MyModel(models.SharedMemoryModel):
	    name = models.CharField(...)

Because the system is isolated, you may mix and match
SharedMemoryModels with regular Models. The module idmapper.models
imports everything from django.db.models and only adds
SharedMemoryModel, so you can simply replace your import of models
from django.db.
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
