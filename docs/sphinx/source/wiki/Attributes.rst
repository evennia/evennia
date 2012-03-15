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
``db`` operator. Let's try to save some data to a *Rose* (an
`Object <Objects.html>`_):

::

    # saving  rose.db.has_thorns = True # getting it back is_ouch = rose.db.has_thorns

This looks like any normal Python assignment, but that ``db`` makes sure
that an *Attribute* is created behind the scenes and is stored in the
database. Your rose will continue to have thorns throughout the life of
the server now, until you deliberately remove them.

To be sure to save **non-persistently**, i.e. to make sure NOT create a
database entry, you use ``ndb`` (!NonDataBase). It works in the same
way:

::

    # saving  rose.ndb.has_thorns = True # getting it back is_ouch = rose.ndb.has_thorns

Strictly speaking, ``ndb`` has nothing to do with ``Attributes``,
despite how similar they look. No ``Attribute`` object is created behind
the scenes when using ``ndb``. In fact the database is not invoked at
all since we are not interested in persistence.

You can also ``del`` properties on ``db`` and ``ndb`` as normal. This
will for example delete an ``Attribute``:

::

    del rose.db.has_thorns

Fast assignment
---------------

For quick testing you can most often skip the ``db`` operator and assign
Attributes like you would any normal Python property:

::

    # saving rose.has_thorns = True# getting it back is_ouch = rose.has_thorns

This looks like any normal Python assignment, but calls ``db`` behind
the scenes for you.

Note however that this form stands the chance of overloading already
existing properties on typeclasses and their database objects.
``rose.msg()`` is for example an already defined method for sending
messages. Doing ``rose.msg = "Ouch"`` will overload the method with a
string and will create all sorts of trouble down the road (the engine
uses ``msg()`` a lot to send text to you). Using
``rose.db.msg = "Ouch"`` will always do what you expect and is usually
the safer bet. And it also makes it visually clear at all times when you
are saving to the database and not.

Another drawback of this shorter form is that it will handle a non-found
Attribute as it would any non-found property on the object. The ``db``
operator will instead return ``None`` if no matching Attribute is found.
So if an object has no attribute (or property) named ``test``, doing
``obj.test`` will raise an ``AttributeException`` error, whereas
``obj.db.test`` will return ``None``.

Persistent vs non-persistent
----------------------------

So *persistent* data means that your data will survive a server reboot,
whereas with *non-persistent* data it will not ...

... So why would you ever want to use non-persistent data? The answer
is, you don't have to. Most of the time you really want to save as much
as you possibly can. Non-persistent data is potentially useful in a few
situations though.

-  You are worried about database performance. Maybe you are
   reading/storing data many times a second (for whatever reason) or you
   have many players doing things at the same time. Hitting the database
   over and over might not be ideal in that case. Non-persistent data
   simply writes to memory, it doesn't hit the database at all. It
   should be said that with the speed and quality of hardware these
   days, this point is less likely to be of any big concern except for
   the most extreme of situations. Modern database systems cache data
   very efficiently for speed. Our default database even runs completely
   in RAM if possible, alleviating much of the need to write to disk
   during heavy loads.
-  You *want* to loose your state when logging off. Maybe you are
   testing a buggy `Script <Scripts.html>`_ that does potentially
   harmful stuff to your character object. With non-persistent storage
   you can be sure that whatever the script messes up, it's nothing a
   server reboot can't clear up.
-  You want to implement a fully or partly *non-persistent world*. Who
   are we to argue with your grand vision!

What types of data can I save?
------------------------------

If you store a single object (that is, not a iterable list of objects),
you can practically store any Python object that can be
`pickled <http://docs.python.org/library/pickle.html>`_. Evennia uses
the ``pickle`` module to serialize data into the database.

There is one notable type of object that cannot be pickled - and that is
a Django database object. These will instead be stored as a wrapper
object containing the ID and its database model. It will be read back to
a new instantiated `typeclass <Typeclasses.html>`_ when the Attribute is
accessed. Since erroneously trying to save database objects in an
Attribute will lead to errors, Evennia will try to detect database
objects by analyzing the data being stored. This means that Evennia must
recursively traverse all iterables to make sure all database objects in
them are stored safely. So for efficiency, it can be a good idea is to
avoid deeply nested lists with objects if you can.

To store several objects, you may only use python *lists*,
*dictionaries* or *tuples* to store them. If you try to save any other
form of iterable (like a ``set`` or a home-made class), the Attribute
will convert, store and retrieve it as a list instead. Since you can
nest dictionaries, lists and tuples together in any combination, this is
usually not a limitation you need to worry about.

*Note that you could fool the safety check if you for example created
custom, non-iterable classes and stored database objects in them. So to
make this clear - saving such an object is **not supported** and will
probably make your game unstable. Store your database objects using
lists, dictionaries or a combination of the two and you should be fine.*

Examples of valid attribute data:

::

    # a single value obj.db.test1 = 23 obj.db.test1 = False  # a database object (will be stored as dbref) obj.db.test2 = myobj # a list of objects obj.db.test3 = [obj1, 45, obj2, 67] # a dictionary obj.db.test4 = 'str':34, 'dex':56, 'agi':22, 'int':77 # a mixed dictionary/list obj.db.test5 = 'members': [obj1,obj2,obj3], 'enemies':[obj4,obj5] # a tuple with a list in it obj.db.test6 = (1,3,4,8, ["test", "test2"], 9) # a set will still be stored and returned as a list [1,2,3,4,5]! obj.db.test7 = set([1,2,3,4,5])

Example of non-supported save:

::

    # this will fool the dbobj-check since myobj (a database object) is "hidden" # inside a custom object. This is unsupported and will lead to unexpected # results!  class BadStorage(object):     pass bad = BadStorage() bad.dbobj = myobj obj.db.test8 = bad # this will likely lead to a traceback

Retrieving Mutable objects
--------------------------

A side effect of the way Evennia stores Attributes is that Python Lists
and Dictionaries (only )are handled by custom objects called PackedLists
and !PackedDicts. These have the special property that they save to the
database whenever new data gets assigned to them. This allows you to do
things like self.db.mylist`4 <4.html>`_

val without having to extract the mylist Attribute into a temporary
variable first.

There is however an important thing to remember. If you retrieve this
data into another variable, e.g. ``mylist2 = obj.db.mylist``, your new
variable will *still* be a PackedList, and if you assign things to it,
it will save to the database! To "disconnect" it from the database
system, you need to convert it to a normal list with mylist2

list(mylist2).

Notes
-----

There are several other ways to assign Attributes to be found on the
typeclassed objects, all being more 'low-level' underpinnings to
``db``/``ndb``. Read their descriptions in the respective modules.
