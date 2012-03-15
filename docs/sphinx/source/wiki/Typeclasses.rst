Typeclassed objects
===================

How do you represent different objects in a game? What makes a bear
different from a stone, or a character different from a house? How do
you store such differences in the database? One way would be to create
new database tables for each type. So a bear would have a database field
"claws" and the stone would have fields specifying its weight and colour
... and you'd soon go crazy with making custom database manipulations
for all infinite combinations.

Evennia instead uses very generic and simple database models and
"decorates" these with normal Python classes that specify their
functionality. Using Python classes means you get all the flexibility of
Python object management for free.

There are three main game 'entities' in Evennia that are what we call
*typeclassed*. They are `Players <Players.html>`_,
`Objects <Objects.html>`_ and `Scripts <Scripts.html>`_. This means that
they are *almost* normal Python classes - they behave and can be
inherited from etc just like normal Python classes except that for
storing data they hide underlying database models ...

... and that's basically all you *really* need to know about how
typeclasses work behind the scenes.

To work with them you should however know that Objects, Scripts and
Players all inherit a lot of helper methods from the typeclass system,
properties you can *always* expect a typeclassed entity to have. In
addition to these, each of the three sub types also offer a host of help
methods and properties you can use. The database handling is hidden, but
it means that typeclasses do some special things with their in-built
class methods that you shouldn't edit.

Properties available to all typeclassed entities (Players, Objects,
Scripts)
----------------------------------------------------------------------------

-  ``key`` - the main identifier for the entity, say 'Rose', 'myscript'
   or 'Paul'. ``name`` is an alias that can also be used.
-  ``date_created`` - time stamp when this object was created.
-  ``locks`` - the `lockhandler <Locks.html>`_ that manages access
   restrictsions. Use locks.add(), locks.get() etc.
-  ``dbref`` - the database id (database ref) of the object. This is a
   unique integer. You can usually also use ``id``.

There are three further properties that warrant special mention:

-  ``db`` (!DataBase) - this is the interface to the `Attribute
   system <Attributes.html>`_, allowing for *persistently* storing your
   own custom data on the entity (i.e. data that will survive a server
   restart).
-  ``ndb`` (!NotDataBase) - this is equivalent to the functionality of
   ``db`` but is used to store *non-peristent* data (i.e. data that will
   be lost on server restart).
-  ``dbobj`` - this is a reference to the *Database object* connected to
   this typeclass (reversely, ``dbobj.typeclass`` is a reference back to
   this very typeclass).

Each of the typeclassed entities then extend this list with their own
properties. Go to the pages for `Objects <Objects.html>`_,
`Scripts <Scripts.html>`_ and `Players <Players.html>`_ respectively for
more info.

Things to remember when using TypeClasses
-----------------------------------------

Typeclasses mostly behave like normal Python classes - you can
add/overload custom methods and inherit your own classes from them -
most things you'd expect to be able to do with a Python class. There are
a few things that you need to remember however:

-  Evennia will look for and call especially named *hook methods* on the
   typeclass in different situations. Just define a new method on the
   class named correctly and Evennia will call it appropriately. Hooks
   are your main way to interact with the server. Available hook methods
   are listed in the resepective base modules in ``game/gamesrc/``.
-  Don't use the normal ``__init__()`` to set up your typeclass. It is
   used by Evennia to set up the mechanics of the Typeclass system. Use
   the designated hook method instead, such as ``at_object_creation()``,
   ``at_player_creation()`` or ``at_script_creation()``.
-  Don't re-implement the python special class methods
   ``__setattr__()``, ``__getattribute__()`` and ``__delattr__()``.
   These are used extensively by the Typeclass system.
-  Some property names cannot be assigned to a Typeclassed entity due to
   being used for internal Typeclass operations. If you try, you will
   get an error. These property names are *id*, *dbobj*, *db*, *ndb*,
   *objects*, *typeclass*, *attr*, *save* and *delete*.
-  Even if they are not explicitly protected, you should not redefine
   the "type" of the default typeclass properties listed above and on
   each typeclassed entity (such as trying to store an integer in the
   ``key`` property). These properties are often called by the engine
   expecting a certain type of return, and some are even tied directly
   to the database and will thus return errors if given a value of the
   wrong type.
-  *Advanced note*: If you are doing advanced coding you might (very
   rarely) find that overloading ``__init__``, ``_setattr__`` etc allows
   for some functionality not possible with hooks alone. You *can* do it
   if you know what you are doing, but you *must* then remember to use
   Python's built-in function ``super()`` to call the parent method too,
   or you *will* crash the server! You have been warned.

How typeclasses actually work
=============================

\_You don't need to read this section to use typeclassed entities, but
it might be useful if you want to do advanced things or are interested
in knowing how Evennia actually does things behind the scenes.\_

All typeclassed entities actually consist of two (three) parts:

#. The *Typeclass* (a normal Python class with customized get/set
   behaviour)
#. The *Database model* (Django model)
#. (`Attributes <Attributes.html>`_)

The *Typeclass* is an almost normal Python class, and holds all the
flexibility of such a class. This is what makes the class special, some
of which was already mentioned above:

-  It inherits from ``src.typeclasses.typeclass.TypeClass``.
-  ``__init__()`` is reserved for various custom startup procedures.
-  It always initiates a property ``dbobj`` that points to a *Database
   model*.
-  It redefines python's normal ``__getattribute__()``,
   ``__setattr__()`` and ``__delattr__`` on itself to relay all data on
   itself to/from ``dbobj`` (i.e. to/from the database model).

The related *Database model* in turn communicates data in and out of the
the database. The Database model holds the following (typeclass-related)
features:

-  It inherits from ``src.typeclasses.models.TypedObject`` (this
   actually implements a
   `idmapper <http://github.com/dcramer/django-idmapper>`_-type model.
   If that doesn't mean anything to you, never mind).
-  It has a field ``typelclass_path`` that gives the python path to the
   *Typeclass* associated with this particular model instance.
-  It has a property *typeclass* that dynamically imports and loads the
   *Typeclass* from ``typeclass_path``, and assigns itself to the
   Typeclass' ``dbobj`` property.
-  It redefines ``__getattribute__()`` to search its typeclass too,
   while avoiding loops. This means you can search either object and
   find also data stored on the other.

The *Attributes* are not really part of the typeclass scheme, but are
very important for saving data without having to change the database
object itself. They are covered in a separate entry
`here <Attributes.html>`_.

Why split it like this?
-----------------------

The *Database model* (Django model) allows for saving data to the
database and is a great place for storing persistent data an object
might need during and between sessions. But it is not suitable for
representing all the various objects a game needs. You *don't* want to
have to redefine a new database representation just because a
``CarObject`` needs to look and behave differently than a
``ChairObject``. So instead we keep the database model pretty "generic",
and only put database Fields on it that we know that *all* objects would
need (or that require fast and regular database searches). Examples of
such fields are "key" and "location".

Enter the *Typeclass*. For lack of a better word, a typeclass
"decorates" a Django database model. Through the re-definition of the
class' get/set methods, the typeclass constantly communicates behind the
scenes with the Django model. The beauty of it is that this is all
hidden from you, the coder. As long as you don't overwrite the few magic
methods listed above you can deal with the typeclass almost as you would
any normal Python class. You can extend it, inherit from it, and so on,
mostly without caring that it is infact hiding a full persistent
database representation. So you can now create a typeclass-class
*Flowers* and then inherit a bunch of other typeclass-classes from that
one, like *Rose*, *Tulip*, *Sunflower*. As your classes are instantiated
they will each secretly carry a reference to a database model to which
all data *actually* goes. We, however, can treat the two as if they
where one.

Below is a schematic of the database/typeclass structure.

.. figure:: http://d.imagehost.org/0784/typeclasses1.png
   :align: center
   :alt: 
Let's see how object creation looks like in an example.

#. We have defined a Typeclass called *Rose* in
   ``game.gamesrc.objects.flower.Rose``. It inherits from
   ``game.gamesrc.objects.baseobjects.Object``, which is a grandchild of
   ``src.typeclasses.typeclass.TypeClass``. So the rose a typeclassed
   object, just as it should be.
#. Using a command we create a new *Rose* instance *!RedRose* (e.g. with
   ``@create redrose:flowers.Rose``).
#. A new database model is created and given the key *!RedRose*. Since
   this is an `Object <Objects.html>`_ typeclass (rather than a Script
   or Player), the database model used is
   ``src.objects.models.ObjectDB``, which inherits directly from
   ``src.typeclasses.models.TypedObject``).
#. This new Django-model instance receives the python-path to the *Rose*
   typeclass and stores it as a string on itself (in a database field
   ``typeclass_path``). When the server restarts in the future, the
   database model will restart from this point.
#. The database model next *imports* the Typeclass from its stored path
   and creates a new instance of it in memory. It stores a reference to
   this instance of *Rose* (*!RedRose*)in a property called
   ``typeclass``.
#. As *Rose* is instantiated, its ``__init__()`` method is called. What
   this does it to make sure to store the back-reference to the Django
   model on our new *Rose* instance. This back-reference is called
   ``dbobj``.
#. The creation method next runs the relevant startup hooks on the
   typeclass, such as ``at_object_creation()``.

Storing properties on the typeclass-instance will in fact transparently
save to the database object. So ``RedRose.thorns = True`` is the same as
``RedRose.dbobj.thorns = True`` (note also that depending on your
``FULL_PERSISTENCE`` setting, this may or may not save ``thorns`` as an
`Attribute <Attributes.html>`_ behind the scenes).

Doing ``ouch = RedRose.thorns`` is however not really as symmetric. The
system will in this case *first* check the Typeclass instance and only
if no property *thorns* was found will go on to examine the database
object. So ``ouch = RedRose.thorns`` is not necessarily the same as
``ouch = RedRose.dbobj.thorns`` in this case. The reason we don't assume
everything to be on the database object is that you are likely to
customize your *Rose* typeclass with custom parameters and methods that
are intended to *overload* the default methods on the database object.
These are thus searched and run first, and you can then safely use
``self.dbobj`` from the typeclass to call the original function if you
want. An example of Typeclass overloading is found
`here <CommandPrompt#Prompt%3Ci%3Eon%3C/i%3Ethe%3Ci%3Esame%3C/i%3Eline.html>`_.

Another example:

.. figure:: http://b.imagehost.org/0023/typeclasses2.png
   :align: center
   :alt: 
Caveats of the typeclass system
-------------------------------

While there are many advantages to the typeclass system over working
with Django models directly, there are also some caveats to remember.

Be careful when not using Evennia's search and create methods. Almost
all code in evennia (including default commands) assume that what is
returned from searches or creates are Typeclasses, not Django models
(i.e. the first of the two in the pair). This is what you get if you use
any of the model manager methods, and also the create/search functions
in ``src.utils.create`` and ``src.utils.search``. Old Django-gurus will
find it tempting to use Django's in-build database query methods, such
as ``ObjectDB.objects.filter()`` to get data. This works, but the result
will then of course *not* be a typeclass but a Django model object (a
query). You can easily convert between them with ``dbobj.typeclass`` and
``typeclass.dbobj``, but you should be aware of this distinction.

::

    obj = ObjectDB.objects.get_id(1) # custom evennia manager method. This returns the typeclass. obj = ObjectDB.objects.get(1) # standard Django. Returns a Django model object.

Even more important to know for Django affectionados: Evennia's custom
methods return *lists* where you with normal Django methods would expect
``Query`` objects (e.g. from the ``filter()`` method). As long as you
don't confuse what result type you are dealing with (for example you
cannot 'link' ``list``s together the way you can ``Querysets``), you
should be fine.

Read the ``manager.py`` files in each relevant folder under ``src/`` to
see which database access methods are available.
