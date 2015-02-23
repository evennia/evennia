
# IDMAPPER

https://github.com/dcramer/django-idmapper

IDmapper (actually Django-idmapper) implements a custom Django model
that is cached between database writes/read (SharedMemoryModel). It
not only lowers memory consumption but most importantly allows for
semi-persistance of properties on database model instances (something
not guaranteed for normal Django models).

Evennia makes extensive modifications to the original IDmapper
routines:

- We change the caching from a WeakValueDictionary to a normal
  dictionary. This is done because we use the models as semi-
  persistent storage while the server was running. In some situations
  the models would run out of scope and the WeakValueDictionary
  then allowed them to be garbage collected. With this change they
  are guaranteed to remain (which is good for persistence but 
  potentially bad for memory consumption).
- We change the save and init code to allow for typeclass hook loading
  and subprocessor checks.
- We add caching/reset hooks called from the server side. 
- We add dynamic field wrappers for all fields named db_*


