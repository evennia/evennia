Creating your own object classes
================================

Evennia comes with a few very basic classes of in-game entities:

::

    Object
       |
       Character
       Room
       Exit

So the more specific object-types are just children of the basic
``Object`` class (technically these are all
`Typeclasses <Typeclassed.html>`_ entities, but for this tutorial, just
treat them as normal Python classes).

For your own game you will most likely want to expand on these very
simple beginnings. It's normal to want your Characters to have various
attributes. Maybe Rooms should hold extra information or even *all*
Objects in your game should have properties not included in basic
Evennia.

First a brief overview of how Evennia handles its object classes. The
default classes are defined under ``src/objects/objects.py``. You can
look at them there or you can bring up a Python prompt and interactively
examine ``ev.Object``, ``ev.Room`` etc.

You will create your own object classes in ``game/gamesrc/objects``. You
should normally inherit from the default classes (normal Python class
inheritance) and go from there. Once you have a working new class you
can immediately start to create objects in-game inheriting from that
class.

If you want to change the *default* object classes, there is one more
step. Evennia's default commands and internal creation mechanisms look
at a range of variables in your ``settings.py`` file to determine which
are the "default" classes. These defaults are used by the vanilla
creation commands if you don't specify the typeclass specifically. They
are also used as a fallback by Evennia if there are errors in other
typeclasses, so make sure that your new default class is bug-free.

The following sections spells this out more explicitly.

Create a new Typeclass
----------------------

This is the simplest case. Say you want to create a new "Heavy" object
that characters should not have the ability to pick up.

#. Go to ``game/gamesrc/objects/``. It should already contain a
   directory ``examples/``.
#. Create a new module here, named ``heavy.py``. Alternatively you can
   copy ``examples/object.py`` up one level and rename that file to
   ``heavy.py`` instead - you will then have a template to start from.
#. Code away in the ``heavy.py`` module, implementing the chair
   functionality. See `Objects <Objects.html>`_ for more details and the
   example class below. Let's call the typeclass simply ``Heavy``.
#. Once you are done, log into the game with a build-capable account and
   do ``@create/drop rock:heavy.Heavy`` to drop a new heavy "rock"
   object in your location. Note that you have to log in as a
   non-superuser (i.e. not as User #1) when trying to get the rock in
   order to see its heavy effects.

That's it. Below is a ``Heavy`` Typeclass that you could try. Note that
the `lock <Locks.html>`_ and `Attribute <Attribute.html>`_ here set in
the typeclass could just as well have been set using commands in-game,
so this is a *very* simple example.

::

    # file game/gamesrc/objects/heavy.py
    from ev import Object

    class Heavy(Object):
       "Heavy object"
       at_object_creation(self):
           "Called whenever a new object is created"
           # lock the object down by default
           self.locks.add("get:false()")
           # the default "get" command looks for this Attribute in order
           # return a customized error message (we just happen to know
           # this, you'd have to look at the code of the 'get' command to
           # find out).
           self.db.get_err_msg = "This is too heavy for you to pick up."

Change Default Rooms, Exits, Character Typeclass
------------------------------------------------

This is only slightly more complex than creating any other Typeclass. In
fact it only includes one extra step - telling Evennia to use the new
default.

Let's say we want to change Rooms to use our new typeclass ``MyRoom``.

#. Create a new module in ``game/gamesrc/objects/myroom.py`` and code
   your ``MyRoom`` typeclass as described in the previous section. Make
   sure to test it by digging a few rooms of this class (e.g.
   ``@dig Hall:myroom.MyRoom``).
#. Once you are sure the new class works as it should, edit
   ``game/settings.py`` and add
   ``BASE_ROOM_TYPECLASS="game.gamesrc.objects.myroom.MyRoom"``.
#. Reload Evennia.

For example the ``@dig`` and ``@tunnel`` commands will henceforth use
this new default when digging new rooms whenever you don't give a
typeclass explicitly. For the other sub-types, change
``BASE_CHARACTER_TYPECLASS`` (used by character creation commands) and
``BASE_EXIT_TYPECLASS`` (used by ``@dig``/``@tunnel`` etc) respectively.

Change the default Object Typeclass
-----------------------------------

Changing the root ``Object`` class works identically to changing the
``Character``, ``Room`` or ``Exit`` typeclass. After having created your
new typeclass, set ``settings.BASE_EXIT_TYPECLASS`` to point to your new
class. Let's say you call your new default ``Object`` class
``MyObject``.

There however one important further thing to remember: ``Characters``,
``Rooms`` and ``Exits`` will still inherit from the *old* ``Object`` at
this point (not ``MyObject``). This is by design - depending on your
type of game, you may not need some or all of these subclasses to
inherit any of the new stuff you put in ``MyObject``.

If you do want that however, you need to also overload these subclasses.
For each of the ``Character``, ``Room`` and ``Exit`` you want to
customize, do the following:

#. Create a new module in ``game/gamesrc/``, e.g. ``mycharacter.py``
   etc. A good flexible solution for overloading only parts of the
   default is to make inheriting classes *multi-inherited* (see below).
   As a place-holder you can make the class empty for now (just put
   ``pass`` in it).
#. In your ``settings.py`` file, add and define
   ``BASE_CHARACTER_TYPECLASS``, ``BASE_ROOM_TYPECLASS`` and
   ``BASE_EXIT_TYPECLASS`` to point to your new typeclasses.
#. Reload Evennia.

This will give you maximum flexibility with creating and expanding your
own types of rooms, characters and exit objects (or not). Below is an
example of a new ``myroom.py``:

::

    # file gamesrc/objects/myroom.py
    from ev import Object
    from gamesrc.objects.myobject import MyObject
    # we use multi-inheritance, this will primarily use MyObject,
    # falling back to the default Object for things MyObject do
    # not overload
    class MyRoom(MyObject, Object):
        "My own expandable room class"
        pass

Notes
=====

All above examples puts each class in its own module. This makes it easy
to find, but it is really up to you how you organize things. There is
nothing stopping you from putting all base classes into one module, for
example.

Also remember that Python may dynamically rename module classes as they
are imported. So if you feel it annoying to have to refer to your new
default as ``MyObject`` all the time, you can also import them to
another name like in the below example:

::

    from ev import Object as BaseObject
    from gamesrc.objects.myobject import MyObject as Object
    class MyRoom(Object, BaseObject):
         [...]

This doesn't actually change the meaning of the code, but might make the
relationships clearer inside a module.
