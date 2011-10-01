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

The **default** way of storing data on Typeclassed objects is simply to
assign data to it. Let's try to save some data to a *Rose* (an
`Object <Objects.html>`_):

::

    # saving
    rose.has_thorns = True# getting it back
    is_ouch = rose.has_thorns

Whether this data is saved *persistently* to the database or not (i.e.
if it survives a server reboot) depends on the setting of the variable
``FULL_PERSISTENCE`` in the settings (it's described in more detail
later on this page).

To be **sure** to save your data persistently, regardless of the setting
of ``FULL_PERSISTENCE``, use the ``db`` (!DataBase) interface.

::

    # saving 
    rose.db.has_thorns = True # getting it back
    is_ouch = rose.db.has_thorns

This creates a new ``Attribute`` object and links it uniquely to
``rose``. Using ``db`` ``will`` always save data to the database.

To be sure to save **non-persistently**, you use ``ndb`` (!NonDataBase).
It works in the same way:

::

    # saving 
    rose.ndb.has_thorns = True # getting it back
    is_ouch = rose.ndb.has_thorns

(Using ``ndb`` like this will **NEVER** use the database.)

Strictly speaking, ``ndb`` has nothing to do with ``Attributes``,
despite how similar they look. No ``Attribute`` object is created behind
the scenes when using ``ndb``. In fact the database is not invoked at
all since we are not interested in persistence.

You can also ``del`` properties on ``db`` and ``ndb`` as normal. This
will for example delete an ``Attribute``:

::

    del rose.db.has_thorns

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
   the most extreme of situations. The default database even runs in RAM
   if possible, alleviating the need to write to disk.
-  You *want* to loose your state when logging off. Maybe you are
   testing a buggy `Script <Scripts.html>`_ that does potentially
   harmful stuff to your character object. With non-persistent storage
   you can be sure that whatever the script messes up, it's nothing a
   server reboot can't clear up.
-  You want to implement a fully or partly *non-persistent world*.
   Whereas this sounds to us like something of an under-use of the
   codebase's potential, who are we to argue with your grand vision!

FULL\_PERSISTENCE
-----------------

As mentioned above, Evennia allows you to change the default operation
when storing attributes by using ``FULL_PERSISTENCE`` in
``settings.py``.

With ``FULL_PERSISTENCE`` on, you can completely ignore ``db`` and
assign properties to your object as you would any python object. This is
the 'default' method shown at the top). Behind the scenes an
``Attribute`` will be created and your data will be saved to the
database. Only thing you have to do explicitly is if you *don't* want
persistence, where you have to use ``ndb``.

With ``FULL_PERSISTENCE`` off, the inverse is true. You then have to
specify ``db`` if you want to save, whereas normal assignment means
non-persistence.

Regardless of the setting you can always use ``db`` and ``ndb``
explicitly to get the result you want. This means writing a little bit
more, but has the advantage of clarity and portability: If you plan to
distribute your code to others, it's recommended you use explicit
assignment. This avoids weird errors when your users don't happen to use
the save persistence setting as you. The Evennia server distribution
always use explicit assignment everywhere.

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

    # a single value
    obj.db.test1 = 23
    obj.db.test1 = False 
    # a database object (will be stored as dbref)
    obj.db.test2 = myobj
    # a list of objects
    obj.db.test3 = [obj1, 45, obj2, 67]
    # a dictionary
    obj.db.test4 = 'str':34, 'dex':56, 'agi':22, 'int':77
    # a mixed dictionary/list
    obj.db.test5 = 'members': [obj1,obj2,obj3], 'enemies':[obj4,obj5]
    # a tuple with a list in it
    obj.db.test6 = (1,3,4,8, ["test", "test2"], 9)
    # a set will still be stored and returned as a list [1,2,3,4,5]!
    obj.db.test7 = set([1,2,3,4,5])

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

Storing nested data directly on the variable
--------------------------------------------

Evennia needs to do a lot of work behind the scenes in order to save and
retrieve data from the database. Most of the time, things work just like
normal Python, but there is one further exception except the one about
storing database objects above. It is related to updating already
existing attributes in-place. Normally this works just as it should. For
example, you can do

::

    # saving data
    obj.db.mydict["key"] = "test1"
    obj.db.mylist[34] = "test2"
    obj.db.mylist.append("test3")
    # retrieving data
    obj.db.mydict["key"] # returns "test1"
    obj.db.mylist[34] # returns "test2
    obj.db.mylist[-1] # returns "test3"

and it will work fine, thanks to a lot of magic happening behind the
scenes. What will *not* work however is editing *nested*
lists/dictionaries in-place. This is due to the way Python referencing
works. Consider the following:

::

    obj.db.mydict = 1:2:3

This is a perfectly valid nested dictionary and Evennia will store it
just fine.

::

    obj.db.mydict[1][2] # correctly returns 3

However:

::

    obj.db.mydict[1][2] = "test" # fails!

will not work - trying to edit the nested structure will fail silently
and nothing will have changed. No, this is not consistent with normal
Python operation, it's where the database magic fails. All is not lost
however. In order to change a nested structure, you simply need to use a
temporary variable:

::

    # retrieve old db data into temporary variable
    mydict = obj.db.mydict
    # update temporary variable
    mydict[1][2] = "test"
    # save back to database
    obj.db.mydict = mydict
    # test
    obj.db.mydict[1][2] # now correctly returns "test"

mydict was updated and recreated in the database.

Notes
-----

There are several other ways to assign Attributes to be found on the
typeclassed objects, all being more 'low-level' underpinnings to
``db``/``ndb``. Read their descriptions in the respective modules.
