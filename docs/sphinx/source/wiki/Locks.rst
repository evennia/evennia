Locks
=====

For most games it is a good idea to restrict what people can do. In
Evennia such restrictions are applied and checked by something called
*locks*. All Evennia entities (`commands <Commands.html>`_,
`objects <Objects.html>`_, `scripts <Scripts.html>`_,
`players <Players.html>`_, `help system <HelpSystem.html>`_,
[Communications#Msg messages] and [Communications#Channels channels])
are accessed through locks.

A lock can be thought of as an "access rule" restricting a particular
use of an Evennia entity. Whenever another entity wants that kind of
access the lock will analyze that entity in different ways to determine
if access should be granted or not. Evennia implements a "lockdown"
philosophy - all entities are inaccessible unless you explicitly define
a lock that allows some or full access.

Let's take an example: An object has a lock on itself that restricts how
people may "delete" that object. Apart from knowing that it restricts
deletion, the lock also knows that only players with the specific ID of,
say, '34' are allowed to delete it. So whenever a player tries to run
@delete on the object, the @delete command makes sure to check if this
player is really allowed to do so. It calls the lock, which in turn
checks if the player's id is 34. Only then will it allow @delete to go
on with its job.

Setting and checking a lock
---------------------------

The in-game command for setting locks on objects is ``@lock``:

::

     > @lock obj = <lockstring>

The ``<lockstring>`` is a string on a certain form that defines the
behaviour of the lock. We will go into more detail on how
``<lockstring>`` should look in the next section.

Code-wise, Evennia handles locks through what is usually called
``locks`` on all relevant entities. This is a handler that allows you to
add, delete and check locks.

::

     myobj.locks.add(<lockstring>)

One can call ``locks.check()`` to perform a lock check, but to hide the
underlying implementation all objects also have a convenience function
called ``access``. This should preferably be used. In the example below,
``accessing_obj`` is the object requesting the 'delete' access whereas
``obj`` is the object that might get deleted. This is how it would (and
do) look from inside the ``@delete`` command:

::

     if not obj.access(accessing_obj, 'delete'):
         accessing_obj.msg("Sorry, you may not delete that.")
         return 

Defining locks
--------------

Defining a lock (i.e. an access restriction) in Evennia is done by
adding simple strings of lock definitions to the object's ``locks``
property using ``obj.locks.add()``.

Here are some examples of lock strings (not including the quotes):

::

     delete:id(34)   # only allow obj #34 to delete
     edit:all()      # let everyone edit 
     get: not attr(very_weak) or perm(Wizard) # only those who are not "very_weak" or are Wizards may pick this up

Formally, a lockstring has the following syntax:

::

     access_type:[not] func1([arg1,..])[[and|or][ not] func2([arg1,...])[...]]

where ``[..]`` marks optional parts. AND, OR and NOT are not case
sensitive and excess spaces are ignored. ``func1, func2`` etc are
special *lock functions* available to the lock system.

So, a lockstring consists of the type of restriction (the
``access_type``), a colon (``:``) and then a list of function calls that
determine what is needed to pass the lock. Each function returns either
``True`` or ``False``. AND, OR and NOT work as they do normally in
Python. If the total result is True, the lock is passed.

You can create several lock types one after the other by separating them
with a semicolon (``;``) in the lockstring. The string below is
identical to the first two rows of the previous example:

::

    delete:id(34);edit:all()

Valid access\_types
~~~~~~~~~~~~~~~~~~~

An ``access_type``, the first part of a lockstring, defines what kind of
capability a lock controls, such as "delete" or "edit". You may in
principle name your ``access_type`` anything as long as it is unique for
the particular object. Access\_types are not case-sensitive.

If you want to make sure the lock is used however, you should pick
``access_type`` names that you (or the default command set) actually
tries, as in the example of ``@delete`` above that uses the 'delete'
``access_type``.

Below are the access\_types checked by the default commandset.

-  `Commands <Commands.html>`_: ``cmd`` - this defines who may call this
   command at all.
-  `Objects <Objects.html>`_:

   -  ``control`` - who is the "owner" of the object. Can set locks,
      delete it etc. Defaults to the creator of the object.
   -  ``call`` - who may call object-commands on this object.
   -  ``examine`` - who may examine this object's properties.
   -  ``delete`` - who may delete the object.
   -  ``edit`` - who may edit properties and attributes of the object.
   -  ``get``- who may pick up the object and carry it around.
   -  ``puppet`` - who may "become" this object and control it as their
      "character".
   -  ``attrcreate`` - allows to create new objects on object (default
      True)

-  [Objects#Characters Characters]: ``<Same as Objects>``
-  [Objects#Exits Exits]: ``<Same as Objects>`` + ``traverse`` - who may
   pass the exit.
-  `Players <Players.html>`_:

   -  ``examine`` - who may examine the player's properties.
   -  ``delete`` - who may delete the player.
   -  ``edit`` - who may edit the player's attributes and properties.
   -  ``msg`` - who may send messages to the player.
   -  ``boot`` - who may boot the player.

-  `Attributes <Attributes.html>`_: (*only checked by
   ``obj.secure_attr``*)

   -  ``attrread`` - see/access attribute
   -  ``attredit`` - change/delete attribute

-  [Communications#Channels Channels]:

   -  ``control`` - who is administrating the channel. This means the
      ability to delete the channel, boot listeners etc.
   -  ``send`` - who may send to the channel.
   -  ``listen`` - who may subscribe and listen to the channel.

-  `HelpEntry <HelpSystem.html>`_:

   -  ``examine`` - who may view this help entry (usually everyone)
   -  ``edit`` - who may edit this help entry.

So to take an example, whenever an exit is to be traversed, a lock of
the type *traverse* will be checked. Defining a suitable lock type for
an exit object would thus involve a lockstring
``traverse: <lock functions>``.

Lock functions
~~~~~~~~~~~~~~

You are not allowed to use just any function in your lock definition;
you are infact only allowed to use those functions defined in one of the
modules given in ``settings.LOCK_FUNC_MODULES``. All functions in any of
those modules will automatically be considered a valid lock function.
The default ones are found in ``src/locks/lockfuncs.py`` or via
``ev.lockfuncs``.

A lock function must always accept at least two arguments - the
*accessing object* (this is the object wanting to get access) and the
*accessed object* (this is the object with the lock). Those two are fed
automatically as the first two arguments the function when the lock is
checked. Any arguments explicitly given in the lock definition will
appear as extra arguments.

::

    # A simple example lock function. Called with e.g. id(34)

    def id(accessing_obj, accessed_obj, *args, **kwargs):
        if args:
            wanted_id = args[0]
            return accessing_obj.id == wanted_id
        return False 

(Using the ``*`` and ``**`` syntax causes Python to magically put all
extra arguments into a list ``args`` and all keyword arguments into a
dictionary ``kwargs`` respectively. If you are unfamiliar with how
``*args`` and ``**kwargs`` work, see the Python manuals).

Some useful default lockfuncs (see ``src/locks/lockfuncs.py`` for more):

-  ``true()/all()`` - give access to everyone
-  ``false()/none()/superuser()`` - give access to noone. Superusers
   bypass the check entirely.
-  ``perm(perm)`` - this tries to match a given ``permission`` property.
   See [Locks#Permissions below].
-  ``perm_above(perm)`` - requres a "higher" permission level than the
   one given.
-  ``id(num)/dbref(num)`` - checks so the access\_object has a certain
   dbref/id.
-  ``attr(attrname)`` - checks if a certain
   `Attribute <Attributes.html>`_ exists on accessing\_object.
-  ``attr(attrname, value)`` - checks so an attribute exists on
   accessing\_object *and* has the given value.
-  ``attr_gt(attrname, value)`` - checks so accessing\_object has a
   value larger (``>``) than the given value.
-  ``attr_ge, attr_lt, attr_le, attr_ne`` - corresponding for ``>=``,
   ``<``, ``<=`` and ``!=``.
-  ``holds(objid)`` - checks so the accessing objects contains an object
   of given name or dbref.
-  ``pperm(perm)``, ``pid(num)/pdbref(num)`` - same as ``perm``,
   ``id/dbref`` but always looks for permissions and dbrefs of
   *Players*, not on Characters.

Default locks
-------------

Evennia sets up a few basic locks on all new objects and players (if we
didn't, noone would have any access to anything from the start). This is
all defined in the root `Typeclasses <Typeclass.html>`_ of the
respective entity, in the hook method ``basetype_setup()`` (which you
usually don't want to edit unless you want to change how basic stuff
like rooms and exits store their internal variables). This is called
once, before ``at_object_creation``, so just put them in the latter
method on your child object to change the default. Also creation
commands like ``@create`` changes the locks of objects you create - for
example it sets the ``control`` lock\_type so as to allow you, its
creator, to control and delete the object.

Permissions
===========

A *permission* is simply a list of text strings stored on the property
``permissions`` on ``Objects`` and ``Players``. Permissions can be used
as a convenient way to structure access levels and hierarchies. It is
set by the ``@perm`` command.

::

     @perm Tommy = Builders

All new players/character are given a default set of permissions defined
by ``settings.PERMISSION_PLAYER_DEFAULT``.

Selected permission strings can be organized in a *permission hierarchy*
by editing the tuple ``settings.PERMISSION_HIERARCHY``. Evennia's
default permission hierarchy is as follows:

::

     Immortals
     Wizards
     Builders
     PlayerHelpers
     Players # this is what all new Players start with by default

The main use of this is that if you use the lock function ``perm()``
mentioned above, a lock check for a particular permission in the
hierarchy will *also* grant access to those with *higher* hierarchy
acces. So if you have the permission "Wizards" you will also pass a lock
defined as ``perm(Builders)`` or any of those levels below "Wizards".
The lock function ``perm_above(Players)`` require you to have a
permission level higher than ``Players`` and so on. If the permission
looked for is not in the hierarchy, an exact match is required.

::

    obj1.permissions = ["Builders", "cool_guy"]
    obj2.locks.add("enter:perm_above(Players) and perm(cool_guy)")

    obj2.access(obj1, "enter") # this returns True!

Superusers
----------

There is normally only one *superuser* account and that is the one first
created when starting Evennia (User #1). This is sometimes known as the
"Owner" or "God" user. A superuser has more than full access - it
completely *bypasses* all locks so no checks are even run. This allows
for the superuser to always have access to everything in an emergency.
But it also hides any eventual errors you might have made in your lock
definitions. So when trying out game systems you should use a secondary
character rather than #1 so your locks get tested correctly.

More Lock definition examples
=============================

::

    examine: attr(eyesight, excellent) or perm(Builders)

You are only allowed to do *examine* on this object if you have
'excellent' eyesight or is a Builder.

::

    # lock for the tell command
    cmd: not perm(no_tell)

Locks can be used to implement highly specific bans. This will allow
everyone *not* having the "permission" ``no_tell`` to use the ``tell``
command. Just give a player the "permission" ``no_tell`` to disable
their use of this particular command henceforth.

::

    open: holds('the green key') or perm(Builder) 

This could be called by the ``open`` command on a "door" object. The
check is passed if you are a Builder or has the right key in your
inventory.

::

    # this limits what commands are visible to the user
    cmd: perm(Builders)

Evennia's command handler looks for a lock of type ``cmd`` to determine
if a user is allowed to even call upon a particular command or not. When
you define a command, this is the kind of lock you must set. See the
default command set for lots of examples.

::

    dbref = caller.id
    lockstring = "control:id(%s);examine:perm(Builders);delete:id(%s) or perm(Wizards);get:all()" % (dbref, dbref)
    new_obj.locks.add(lockstring)

This is how the ``@create`` command sets up new objects. In sequence,
this permission string sets the owner of this object be the creator (the
one running ``@create``). Builders may examine the object whereas only
Wizards and the creator may delete it. Everyone can pick it up.

A complete example of setting locks on an object
================================================

Assume we have two objects - one is ourselves (not superuser) and the
other is an `Object <Objects.html>`_ called ``box``.

::

     > @create/drop box
     > @desc box = "This is a very big and heavy box."

We want to limit which objects can pick up this heavy box. Let's say
that to do that we require the would-be lifter to to have an attribute
*strength* on themselves, with a value greater than 50. We assign it to
ourselves to begin with.

::

     > @set self/strength = 45

Ok, so for testing we made ourselves strong, but not strong enough. Now
we need to look at what happens when someone tries to pick up the the
box - they use the ``get`` command (in the default set). This is defined
in ``game/gamesrc/commands/default/general.py``. In its code we find
this snippet:

::

    if not obj.access(caller, 'get'):
        if obj.db.get_err_msg:
            caller.msg(obj.db.get_err_msg)
        else:
            caller.msg("You can't get that.")
        return

So the ``get`` command looks for a lock with the type *get* (not so
surprising). It also looks for an `Attribute <Attributes.html>`_ on the
checked object called *get\_err\_msg* in order to return a customized
error message. Sounds good! Let's start by setting that on the box:

::

     > @set box/get_err_msg = You are not strong enough to lift this box.

Next we need to craft a Lock of type *get* on our box. We want it to
only be passed if the accessing object has the attribute *strength* of
the right value. For this we would need to create a lock function that
checks if attributes have a value greater than a given value. Luckily
there is already such a one included in evennia (see
``src/permissions/lockfuncs.py``), called ``attr_gt``.

So the lock string will look like this: ``get:attr_gt(strength, 50)``.
We put this on the box now:

::

     @lock box = get:attr_gt(strength, 50)

Try to ``get`` the object and you should get the message that we are not
strong enough. Increase your strength above 50 however and you'll pick
it up no problem. Done! A very heavy box!

If you wanted to set this up in python code, it would look something
like this:

::

    from ev import create_object

    box = create_object(None, key="box")
    box.locks.add("get:attr_gt(strength, 50)")

    # or we can assign locks right away
    box = create_object(None, key="box", locks="get:attr_gt(strength, 50)")

    # set the attributes
    box.db.desc = "This is a very big and heavy box."
    box.db.get_err_msg = "You are not strong enough to lift this box."

    # one heavy box, ready to withstand all but the strongest...

On Django's permission system
=============================

Django also implements a comprehensive permission/security system of its
own. The reason we don't use that is because it is app-centric (app in
the Django sense). Its permission strings are of the form
``appname.permstring`` and it automatically adds three of them for each
database model in the app - for the app src/object this would be for
example 'object.create', 'object.admin' and 'object.edit'. This makes a
lot of sense for a web application, not so much for a MUD, especially
when we try to hide away as much of the underlying architecture as
possible.

The django permissions are not completely gone however. We use it for
logging in users (the ``User`` object tied to `Players <Players.html>`_
is a part of Djangos's auth system). It is also used exclusively for
managing Evennia's web-based admin site, which is a graphical front-end
for the database of Evennia. You edit and assign such permissions
directly from the web interface. It's stand-alone from the permissions
described above.
