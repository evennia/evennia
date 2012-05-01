Objects
=======

All in-game objects in Evennia, be it characters, chairs, monsters,
rooms or hand grenades are represented by an Evennia *Object*. Objects
form the core of Evennia and is probably what you'll spend most time
working with. Objects are `TypeClassed <Typeclasses.html>`_ entities.

How to create your own object types
-----------------------------------

An Evennia Object is, per definition, a Python class that includes
``src.objects.objects.Object`` among its parents (if you are aware of
how typeclasses work, this is a typeclass linked to the ``ObjectDB``
database model). In your code you can however conveniently refer to
``ev.Object`` instead.

Here's how to define a new Object typeclass in code:

::

    from ev import Objectclass Rose(Object):     """     This creates a simple rose object             """         def at_object_creation(self):         "this is called only once, when object is first created"         # add a persistent attribute 'desc' to object.         self.db.desc = "This is a pretty rose with thorns."

Save your class to a module under ``game/gamesrc/objects``, say
``flowers.py``. Now you just need to point to the class *Rose* with the
``@create`` command to make a new rose:

::

    > @create/drop MyRose:flowers.Rose

To create a new object in code, use the method ``ev.create_object`` (a
shortcut to src.utils.create.create\_object()

::

    ):from ev import create_object new_rose = create_object("game.gamesrc.objects.flowers.Rose", key="MyRose")

(You have to give the full path to the class in this case -
``create.create_object`` is a powerful function that should be used for
all coded creating, for example if you create your own command that
creates some objects as it runs. Check out the ``ev.create_*``
functions.

This particular Rose class doesn't really do much, all it does it make
sure the attribute ``desc``\ (which is what the ``look`` command looks
for) is pre-set, which is pretty pointless since you will usually want
to change this at build time (using the ``@describe`` command). The
``Object`` typeclass offers many more hooks that is available to use
though - see next section.

If you define a new Object class (inheriting from the base one), and
wants the default create command (``@create``) to default to that
instead, set ``BASE_OBJECT_TYPECLASS`` in ``settings.py`` to point to
your new class.

Properties and functions on Objects
-----------------------------------

Beyond those properties assigned to all
`typeclassed <Typeclasses.html>`_ objects, the Object also has the
following custom properties:

-  ``aliases`` - a list of alternative names for the object. Aliases are
   stored in the database and can be searched for very fast. The
   ``aliases`` property receives and returns lists - so assign to it
   like normal, e.g. ``obj.aliases=['flower', 'red blossom']``
-  ``location`` - a reference to the object currently containing this
   object.
-  ``home`` is a backup location. The main motivation is to have a safe
   place to move the object to if its ``location`` is destroyed. All
   objects should usually have a home location for safety.
-  ``destination`` - this holds a reference to another object this
   object links to in some way. Its main use is for
   `Exits <Objects#Exits.html>`_, it's otherwise usually unset.
-  ``nicks`` - as opposed to aliases, a `Nick <Nicks.html>`_ holds a
   convenient nickname replacement for a real name, word or sequence,
   only valid for this object. This mainly makes sense if the Object is
   used as a game character - it can then store briefer shorts, example
   so as to quickly reference game commands or other characters. Nicks
   are stored in the database and are a bit more complex than aliases
   since they have a *type* that defines where Evennia tries to do the
   substituion. In code, use nicks.get(alias, type) to get a nick, or
   nicks.add(alias, realname) to add a new one.
-  ``player`` - this holds a reference to a connected
   `Player <Players.html>`_ controlling this object (if any). Note that
   this is set also if the controlling player is *not* currently online
   - to test if a player is online, use the ``has_player`` property
   instead.
-  ``sessions`` - if ``player`` field is set *and the player is online*,
   this is a list of all active sessions (server connections) to contact
   them through (it may be more than one if multiple connections are
   allowed in settings).
-  ``permissions`` - a list of `permission strings <Locks.html>`_ for
   defining access rights for this Object.
-  ``has_player`` - a shorthand for checking if an *online* player is
   currently connected to this object.
-  ``contents`` - this returns a list referencing all objects 'inside'
   this object (i,e. which has this object set as their ``location``).
-  ``exits`` - this returns all objects inside this object that are
   *Exits*, that is, has the ``destination`` property set.

The last two properties are special:

-  ``cmdset`` - this is a handler that stores all `command
   sets <Commands#Command_Sets.html>`_ defined on the object (if any).
-  ``scripts`` - this is a handler that manages
   `scripts <Scripts.html>`_ attached to the object (if any).

The Object also has a host of useful utility functions. See the function
headers in ``src/objects/objects.py`` for their arguments and more
details.

-  ``msg()`` - this function is used to send messages from the server to
   a player connected to this object.
-  ``msg_contents()`` - calls ``msg`` on all objects inside this object.
-  ``search()`` - this is a convenient shorthand to search for a
   specific object, at a given location or globally. It's mainly useful
   when defining commands (in which case the object executing the
   command is named ``caller`` and one can do ``caller.search()`` to
   find objects in the room to operate on).
-  ``execute_cmd()`` - Lets the object execute the given string as if it
   was given on the command line.
-  ``move_to`` - perform a full move of this object to a new location.
   This is the main move method and will call all relevant hooks, do all
   checks etc.
-  ``clear_exits()`` - will delete all `Exits <Objects#Exits.html>`_ to
   *and* from this object.
-  ``clear_contents()`` - this will not delete anything, but rather move
   all contents (except Exits) to their designated ``Home`` locations.
-  ``delete()`` - deletes this object, first calling ``clear_exits()``
   and ``clear_contents()``.

The Object Typeclass defines many more *hook methods* beyond
``at_object_creation``. Evennia calls these hooks at various points.
When implementing your custom objects, you will inherit from the base
parent and overload these hooks with your own custom code. See
``src.objects.objects`` for an updated list of all the available hooks.

Subclasses of *Object*
----------------------

There are three special subclasses of *Object* in default Evennia -
*Characters*, *Rooms* and *Exits*. The reason they are separated is
because these particular object types are fundamental, something you
will always need and in some cases requires some extra attention in
order to be recognized by the game engine (there is nothing stopping you
from redefining them though). In practice they are all pretty similar to
the base Object.

Characters
~~~~~~~~~~

Characters are objects controlled by `Players <Players.html>`_. When a
new Player logs in to Evennia for the first time, a new ``Character``
object is created and the Player object is assigned to the ``player``
attribute. A ``Character`` object must have a `Default
Commandset <Commands#Command_Sets.html>`_ set on itself at creation, or
the player will not be able to issue any commands! If you just inherit
your own class from ``ev.Character`` and make sure the parent methods
are not stopped from running you should not have to worry about this.
You can change the default typeclass assigned to new Players in your
settings with ``BASE_CHARACTER_TYPECLASS``.

Rooms
~~~~~

*Rooms* are the root containers of all other objects. The only thing
really separating a room from any other object is that they have no
``location`` of their own and that default commands like ``@dig``
creates objects of this class - so if you want to expand your rooms with
more functionality, just inherit from ``ev.Room``. Change the default
used by ``@dig`` with ``BASE_ROOM_TYPECLASS``.

Exits
~~~~~

*Exits* are objects connecting other objects (usually *Rooms*) together.
An object named *North* or *in* might be an exit, as well as *door*,
*portal* or *jump out the window*. An exit has two things that separate
them from other objects. Firstly, their *destination* property is set
and points to a valid object. This fact makes it easy and fast to locate
exits in the database. Secondly, exits define a special `Transit
Command <Commands.html>`_ on themselves when they are created. This
command is named the same as the exit object and will, when called,
handle the practicalities of moving the character to the Exits's
*destination* - this allows you to just enter the name of the exit on
its own to move around, just as you would expect.

The exit functionality is all defined on the Exit typeclass, so you
could in principle completely change how exits work in your game (it's
not recommended though, unless you really know what you are doing).
Exits are `locked <Locks.html>`_ using an access\ *type
called*\ traverse\_ and also make use of a few hook methods for giving
feedback if the traversal fails. See ``ev.Exit`` for more info, that is
also what you should inherit from to make custom exit types. Change the
default class used by e.g. ``@dig`` and ``@open`` by editing
``BASE_EXIT_TYPECLASS`` in your settings.

Further notes
-------------

For a more advanced example of a customized object class, see
``game/gamesrc/objects/examples/red_button.py``.
