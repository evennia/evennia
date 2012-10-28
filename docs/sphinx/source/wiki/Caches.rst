Caches
======

*Note: This is an advanced topic. You might want to skip it on a first
read-through.*

Evennia is a fully persistent system, which means that it will store
things in the database whenever its state changes. Since accessing the
database i comparably expensive, Evennia uses an extensive *caching*
scheme. Caching normally means that once data is read from the database,
it is stored in memory for quick retrieval henceforth. Only when data
changes will the database be accessed again (and the cache updated).

With a few exceptions, caching are primarily motivated by speed and to
minimize bottlenecks found by profiling the server. Some systems must
access certain pieces of data often, and going through the django API
over and over builds up. Depending on operation, individual speedups of
hundreds of times can be achieved by clever caching.

The price for extended caching is memory consumption and added
complexity. This page tries to explain the various cache strategies in
place. Most users should not have to worry about them, but if you ever
try to "bang the metal" with Evennia, you should know what you are
seeing.

The default ``@server`` command will give a brief listing of the memory
usage of most relevant caches.

Idmapper
--------

Evennia's django object model is extended by *idmapper* functionality.
The idmapper is an external third-party system that sits in
``src/utils/idmapper``. The idmapper is an on-demand memory mapper for
all database models in the game. This means that a given database object
is represented by the same memory area whenever it is accessed. This may
sound trivial but it is not - in plain Django there is no such
guarantee. Doing something like ``objdb.test = "Test"`` (were objdb is a
django model instance) would be unsafe and most likely the ``test``
variable would be lost next time the model is retrieved from the
database. As Evennia ties `Typeclasses <Typeclasses.html>`_ to django
models, this would be a catastophy.

Idmapper is originally a memory saver for django websites. In the case
of a website, object access is brief and fleeting - not so for us. So we
have extended idmapper to never loose its reference to a stored object
(not doing this was the cause of a very long-standing, very hard-to-find
bug).

Idmapper is an on-demand cache, meaning that it will only cache objects
that are actually accessed. Whereas it is possible to clean the idmapper
cache via on-model methods, this does not necessarily mean its memory
will be freed - this depends on any lingering references in the system
(this is how Python's reference counting works). If you ever need to
clean the idmapper cache, the safest way is therefore a soft-reload of
the server (via e.g. the ``@reload`` command).

Most developers will not need to care with the idmapper cache - it just
makes models work intuitively. It is visible mostly in that all database
models in Evennia inherits from
``src.utils.idmapper.models.SharedMemoryModel``.

On-object variable cache
------------------------

All database fields on all objects in Evennia are cached by use of
`Python
properties <http://docs.python.org/library/functions.html#property>`_.
So when you do ``name = obj.key``, you are actually *not* directly
accessing a database field "key" on the object. What you are doing is
actually to access a handler. This handler looks for hidden variable
named ``_cached_db_key``. If that can be found, it is what is returned.
If not, the actual database field, named ``db_key`` are accessed. The
result is returned and cached for next time.

The naming scheme is consistent, so a given property ``obj.foo`` is a
handler with a cache named ``obj._cached_db_foo`` and a database field
``obj.db_key.`` The handler methods for the property are always named
``obj.foo_get()``, ``obj.foo_set()`` and ``obj.foo_del()`` (all are not
always needed).

Apart from caching, property handlers also serves another function -
they hide away Django administration. So doing ``obj.key = "Peter"``
will not only assign (and cache) the string "Peter" in the database
field ``obj.db_key``, it will also call ``obj.save()`` for you in order
to update the database.

Hiding away the model fields presents one complication for developers,
and that is searching using normal django methods. Basically, if you
search using e.g. the standard django ``filter`` method, you must search
for ``db_key``, not ``key``. Only the former is known by django, the
latter will give an invalid-field error. If you use Evennia's own search
methods you don't need to worry about this, they look for the right
things behind the scenes for you.

Mutable variable caches
~~~~~~~~~~~~~~~~~~~~~~~

Some object properties may appear mutable - that is, they return lists.
One such example is the ``permissions`` property. This is however not
actually a list - it's just a handler that *returns* and *accepts*
lists. ``db_permissions`` is actually stored as a comma-separated
string. The uptake of this is that you cannot do list operations on the
handler. So ``obj.permissions.append('Immortals')`` will not work.
Rather, you will have to do such operations on what is returned. Like
this:

::

    perms = obj.permissions # this returns a list!
    perms.append("Immortals")
    obj.permissions = perms  # overwrites with new list

Content cache
~~~~~~~~~~~~~

A special case of on-object caching is the *content* cache. Finding the
"contents" of a particular location turns out to be a very common and
pretty expensive operation. Whenever a person moves, says something or
does other things, "everyone else" in a given location must be informed.
This means a database search for which objects share the location.

``obj.contents`` is a convenient container that at every moment contains
a cached list of all objects "inside" that particular object. It is
updated by the ``location`` property. So ``obj1.location = obj2`` will
update ``obj2.contents`` on the fly to contain ``obj1``. It will also
remove ``obj1`` from the ``contents`` list of its previous location.
Testing shows that when moving from one room to another, finding and
messaging everyone in the room took up as much as *25%* of the total
computer time needed for the operation. After caching ``contents``,
messaging now takes up *0.25%* instead ...

The contents cache should be used at all times. The main thing to
remember is that if you were to somehow bypass the ``location`` handler
(such as by setting the ``db_location`` field manually), you will bring
the cache and database out of sync until you reload the server.

Typeclass cache
~~~~~~~~~~~~~~~

All typeclasses are cached on the database model. This allows for quick
access to the typeclass through ``dbobj.typeclass``. Behind the scenes
this operation will import the typeclass definition from a path stored
in ``db_typeclass_path`` (available via the property handler
``typeclass_path``). All checks and eventual debug messages will be
handled, and the result cached.

The only exception to the caching is if the typeclass module had some
sort of syntax error or other show-stopping bug. The default typeclass
(as defined in ``settings``) will then be loaded instead. The error will
be reported and *no* caching will take place. This is in order to keep
reloading the typeclass also next try, until it is fixed.

On-object Attribute cache
-------------------------

`Attribute <Attributes.html>`_ lookups are cached by use of hidden
dictionaries on all `Typeclassed <Typeclasses.html>`_ objects - this
removes the necessity for subsequent database look-ups in order to
retrieve attributes. Both ``db`` and ``ndn`` work the same way in this
regard.

Attribute value cache
---------------------

Each Attribute object also caches the values stored in it. Whenever
retrieving an attribute value, it is also cached for future accesses. In
effect this means that (after the first time) accessing an attribute is
equivalent to accessing any normal property.
