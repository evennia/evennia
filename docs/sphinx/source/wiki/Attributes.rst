Attributes
==========

When performing actions in Evennia it is often important that you store
data for later. If you write a menu system, you have to keep track of
the current location in the menu tree so that the player can give
correct subsequent commands. If you are writing a combat system, you
might have a combattant's next roll get easier dependent on if their
opponent failed. Your characters will probably need to store
roleplaying-attributes like strength and agility. And so on.

`Typeclassed <Typeclasses.html>`_ game entities
(`Players <Players.html>`_, `Objects <Objects.html>`_ and
`Scripts <Scripts.html>`_) always have *Attributes* associated with
them. Attributes are used to store any type of data 'on' such entities.
This is different from storing data in properties already defined on
entities (such as ``key`` or ``location``) - these have very specific
names and require very specific types of data (for example you couldn't
assign a python *list* to the ``key`` property no matter how hard you
tried). ``Attributes`` come into play when you want to assign arbitrary
data to arbitrary names.

Saving and Retrieving data
--------------------------

To save persistent data on a Typeclassed object you normally use the
``db`` (DataBase) operator. Let's try to save some data to a *Rose* (an
`Object <Objects.html>`_):

::

    # saving 
    rose.db.has_thorns = True 
    # getting it back
    is_ouch = rose.db.has_thorns

This looks like any normal Python assignment, but that ``db`` makes sure
that an *Attribute* is created behind the scenes and is stored in the
database. Your rose will continue to have thorns throughout the life of
the server now, until you deliberately remove them.

To be sure to save **non-persistently**, i.e. to make sure NOT to create
a database entry, you use ``ndb`` (NonDataBase). It works in the same
way:

::

    # saving 
    rose.ndb.has_thorns = True 
    # getting it back
    is_ouch = rose.ndb.has_thorns

Strictly speaking, ``ndb`` has nothing to do with ``Attributes``,
despite how similar they look. No ``Attribute`` object is created behind
the scenes when using ``ndb``. In fact the database is not invoked at
all since we are not interested in persistence.

You can also ``del`` properties on ``db`` and ``ndb`` as normal. This
will for example delete an ``Attribute``:

::

    del rose.db.has_thorns

Both ``db`` and ``ndb`` defaults to offering an ``all()`` method on
themselves. This returns all associated attributes or non-persistent
properties.

::

     list_of_all_rose_attributes = rose.db.all()
     list_of_all_rose_ndb_attrs = rose.ndb.all()

If you use ``all`` as the name of an attribute, this will be used
instead. Later deleting your custom ``all`` will return the default
behaviour.

Properties of Attributes
------------------------

An Attribute object is stored in the database. It has the following
properties:

-  ``key`` - the name of the Attribute. When doing e.g.
   ``obj.db.attrname = value``, this property is set to ``attrname``.
-  ``value`` - this is the value of the Attribute. This value can be
   anything which can be pickled - objects, lists, numbers or what have
   you (see
   [Attributes#What\_types\_of\_data\_can\_I\_save\_in\_an\_Attribute
   this section] for more info). In the example
   ``obj.db.attrname = value``, the ``value`` is stored here.
-  ``category`` - this is an optional property that is set to None for
   most Attributes. Setting this allows to use Attributes for different
   functionality. This is usually not needed unless you want to use
   Attributes for very different functionality (`Nicks <Nicks.html>`_ is
   an example of using Attributes in this way). To modify this property
   you need to use the [Attributes#The\_Attribute\_Handler Attribute
   Handler].
-  ``strvalue`` - this is a separate value field that only accepts
   strings. This severaly limits the data possible to store, but allows
   for easier database lookups. This property is usually not used except
   when re-using Attributes for some other purpose
   (`Nicks <Nicks.html>`_ use it). It is only accessible via the
   [Attributes#The\_Attribute\_Handler Attribute Handler].

Non-database attributes have no equivalence to category nor strvalue.

The Attribute Handler
---------------------

The Attribute handler is what is used under the hood to manage the
Attributes on an object. It is accessible as ``obj.attributes``. For
most operations, the ``db`` or ``ndb`` wrappers are enough. But
sometimes you won't know the attribute name beforehand or you need to
manipulate your Attributes in more detail. The Attribute handler has the
following methods (the argument lists are mostly shortened; you can see
the full call signatures in ``src.typeclasses.models``):

-  ``attributes.has(...)`` - this checks if the object has an Attribute
   with this key. This is equivalent to doing ``obj.db.key``.
-  ``get(...)`` - this retrieves the given Attribute. Normally the
   ``value`` property of the Attribute is returned, but the method takes
   keywords for returning the Attribute object itself. By supplying an
   ``accessing_object`` oto the call one can also make sure to check
   permissions before modifying anything.
-  ``add(...)`` - this adds a new Attribute to the object. An optional
   `lockstring <Locks.html>`_ can be supplied here to restrict future
   access and also the call itself may be checked against locks.
-  ``remove(...)`` - Remove the given Attribute. This can optionally be
   made to check for permission before performing the deletion.
-  ``clear(...)`` - removes all Attributes from object.
-  ``all(...)`` - returns all Attributes (of the given category)
   attached to this object.

See [Attributes#Locking\_and\_checking\_Attributes this section] for
more about locking down Attribute access and editing.

There is an equivalent ``nattribute`` handler for managing non-database
Attributes. This has the same methods but is much simpler since it does
not concern itself with category nor strvalue. It also offers no concept
of access control.

Persistent vs non-persistent
----------------------------

So *persistent* data means that your data will survive a server reboot,
whereas with *non-persistent* data it will not ...

... So why would you ever want to use non-persistent data? The answer
is, you don't have to. Most of the time you really want to save as much
as you possibly can. Non-persistent data is potentially useful in a few
situations though.

-  You are worried about database performance. Since Evennia caches
   Attributes very aggressively, this is not an issue unless you are
   reading *and* writing to your Attribute very often (like many times
   per second). Reading from an already cached Attribute is as fast as
   reading any Python property. But even then this is not likely
   something to worry about: Apart from Evennia's own caching, modern
   database systems themselves also cache data very efficiently for
   speed. Our default database even runs completely in RAM if possible,
   alleviating much of the need to write to disk during heavy loads.
-  A more valid reason for using non-persistent data is if you *want* to
   loose your state when logging off. Maybe you are storing throw-away
   data that are re-initialized at server startup. Maybe you are
   implementing some caching of your own. Or maybe you are testing a
   buggy `Script <Scripts.html>`_ that does potentially harmful stuff to
   your character object. With non-persistent storage you can be sure
   that whatever is messed up, it's nothing a server reboot can't clear
   up.
-  You want to implement a fully or partly *non-persistent world*. Who
   are we to argue with your grand vision!

What types of data can I save in an Attribute?
----------------------------------------------

Evennia uses the ``pickle`` module to serialize Attribute data into the
database. So if you store a single object (that is, not an iterable list
of objects), you can practically store any Python object that can be
`pickled <http://docs.python.org/library/pickle.html>`_.

If you store many objects however, you can only store them using normal
Python structures (i.e. in either a *tuple*, *list*, *dictionary* or
*set*). All other iterables (such as custom containers) are converted to
*lists* by the Attribute (see next section for the reason for this).
Since you can nest dictionaries, sets, lists and tuples together in any
combination, this is usually not much of a limitation.

There is one notable type of object that cannot be pickled - and that is
a Django database object. These will instead be stored as a wrapper
object containing the ID and its database model. It will be read back to
a new instantiated `typeclass <Typeclasses.html>`_ when the Attribute is
accessed. Since erroneously trying to save database objects in an
Attribute will lead to errors, Evennia will try to detect database
objects by analyzing the data being stored. This means that Evennia must
recursively traverse all iterables to make sure all database objects in
them are stored safely. So for efficiency, it can be a good idea to
avoid deeply nested lists with objects if you can.

*Note that you could fool the safety check if you for example created
custom, non-iterable classes and stored database objects in them. So to
make this clear - saving such an object is **not supported** and will
probably make your game unstable. Store your database objects using
lists, tuples, dictionaries, sets or a combination of the four and you
should be fine.*

Examples of valid attribute data:

::

     # a single value
     obj.db.test1 = 23
     obj.db.test1 = False 
     # a database object (will be stored as dbref)
     obj.db.test2 = myobj
     # a list of objects
     obj.db.test3 = [obj1, 45, obj2, 67]
     # a dictionary
     obj.db.test4 = {'str':34, 'dex':56, 'agi':22, 'int':77}
     # a mixed dictionary/list
     obj.db.test5 = {'members': [obj1,obj2,obj3], 'enemies':[obj4,obj5]}
     # a tuple with a list in it
     obj.db.test6 = (1,3,4,8, ["test", "test2"], 9)
     # a set will still be stored and returned as a list [1,2,3,4,5]!
     obj.db.test7 = set([1,2,3,4,5])
     # in-situ manipulation
     obj.db.test8 = [1,2,{"test":1}]
     obj.db.test8[0] = 4
     obj.db.test8[2]["test"] = 5
     # test8 is now [4,2,{"test":5}]

Example of non-supported save:

::

    # this will fool the dbobj-check since myobj (a database object) is "hidden"
    # inside a custom object. This is unsupported and will lead to unexpected
    # results! 
    class BadStorage(object):
        pass
    bad = BadStorage()
    bad.dbobj = myobj
    obj.db.test8 = bad # this will likely lead to a traceback

Retrieving Mutable objects
--------------------------

A side effect of the way Evennia stores Attributes is that Python Lists,
Dictionaries and Sets are handled by custom objects called PackedLists,
PackedDicts and PackedSets. These behave just like normal lists and
dicts except they have the special property that they save to the
database whenever new data gets assigned to them. This allows you to do
things like ``self.db.mylist[4]`` = val without having to extract the
mylist Attribute into a temporary variable first.

There is however an important thing to remember. If you retrieve this
data into another variable, e.g. ``mylist2 = obj.db.mylist``, your new
variable (``mylist2``) will *still* be a PackedList! This means it will
continue to save itself to the database whenever it is updated! This is
important to keep in mind so you are not confused by the results.

::

     obj.db.mylist = [1,2,3,4]
     mylist = obj.db.mylist
     mylist[3] = 5 # this will also update database
     print mylist # this is now [1,2,3,5]
     print mylist.db.mylist # this is also [1,2,3,5]

To "disconnect" your extracted mutable variable from the database you
simply need to convert the PackedList or PackedDict to a normal Python
list or dictionary. This is done with the builtin ``list()`` and
``dict()`` functions. In the case of "nested" lists and dicts, you only
have to convert the "outermost" list/dict in order to cut the entire
structure's connection to the database.

::

     obj.db.mylist = [1,2,3,4]
     mylist = list(obj.db.mylist) # convert to normal list
     mylist[3] = 5
     print mylist # this is now [1,2,3,5]
     print obj.db.mylist # this remains [1,2,3,4]

Remember, this is only valid for mutable iterables - lists and dicts and
combinations of the two.
`Immutable <http://en.wikipedia.org/wiki/Immutable>`_ objects (strings,
numbers, tuples etc) are already disconnected from the database from the
onset. So making the outermost iterable into a tuple is also a way to
stop any changes to the structure from updating the database.

::

     obj.db.mytup = (1,2,[3,4])
     obj.db.mytup[0] = 5 # this fails since tuples are immutable
     obj.db.mytup[2][1] = 5 # this works but will NOT update database since outermost iterable is a tuple
     print obj.db.mytup[2][1] # this still returns 4, not 5
     mytup1 = obj.db.mytup
     # mytup1 is already disconnected from database since outermost 
     # iterable is a tuple, so we can edit the internal list as we want 
     # without affecting the database. 

Locking and checking Attributes
-------------------------------

Attributes are normally not locked down by default, but you can easily
change that for individual Attributes (like those that may be
game-sensitive in games with user-level building).

First you need to set a *lock string* on your Attribute. Lock strings
are specified `here <Locks.html>`_. The relevant lock types are

-  *attrread* - limits who may read the value of the Attribute
-  *attredit* - limits who may set/change this Attribute

You cannot use the ``db`` handler to modify Attribute object (such as
setting a lock on them) - The ``db`` handler will return the Attribute's
*value*, not the Attribute object itself. Instead you use
``get_attribute_obj`` (see next section) which allows you to set the
lock something like this:

::

     obj.attributes.get("myattr", return_obj=True).locks.add("attread:all();attredit:perm(Wizards)")

A lock is no good if nothing checks it -- and by default Evennia does
not check locks on Attributes. You have to add a check to your
commands/code wherever it fits (such as before setting an Attribute).

::

    # in some command code where we want to limit
    # setting of a given attribute name on an object
    attr = obj.attributes.get(attrname, return_obj=True, accessing_obj=caller, default=None, default_access=False)
    if not attr: 
        caller.msg("You cannot edit that Attribute!")
        return
    # edit the Attribute here

The same keywords are available to use with ``obj.attributes.set()`` and
``obj.attributes.remove()``, those will check for the *attredit* lock
type.
