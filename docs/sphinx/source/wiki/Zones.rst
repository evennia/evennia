Zones
=====

Problem
-------

Say you create a room named *Meadow* in your nice big forest MUD. That's
all nice and dandy, but what if you, in the other end of that forest
want another *Meadow*? As a game creator, this can cause all sorts of
confusion. For example, teleporting to *Meadow* will now give you a
warning that there are two *Meadow* s and you have to select which one.
It's no problem to do that, you just choose for example to go to
``2-meadow``, but unless you examine them you couldn't be sure which of
the two sat in the magical part of the forest and which didn't.

Another issue is if you want to group rooms in geographic regions for
example. Let's say the "normal" part of the forest should have separate
weather patterns from the magical part. Or maybe a magical disturbance
echoes through all magical-forest rooms. It would then be convenient to
be able to simply find all rooms that are "magical" so you could send
messages to them.

Zones in Evennia
----------------

*Zones* try to separate rooms by global location. In our example we
would separate the forest into two parts - the magical and the
non-magical part. Each have a *Meadow* and rooms belonging to each part
should be easy to retrieve.

Many MUD codebases hardcode zones as part of the engine and database.
Evennia does no such distinction due to the fact that rooms themselves
are meant to be customized to any level anyway. Below is just *one*
example of how one could add zone-like functionality to a game.

All objects have a *key* property, stored in the database. This is the
primary name of the object. But it can also have any number of *Aliases*
connected to itself. This allows Players to refer to the object using
both key and alias - a "big red door" can also be referred to as the
alias "door". Aliases are actually separate database entities and are as
such very fast to search for in the database, about as fast as searching
for the object's primary key in fact.

This makes Aliases prime candiates for implementing zones. All you need
to do is to come up with a consistent aliasing scheme. Here's one
suggestion:

::

     #zonename|key

So say we (arbitrarily) divide our forest example into the zones
``magicforest`` and ``normalforest``. These are the added aliases we use
for the respective *Meadow* 's:

::

     #magicforest|meadow
     #normalforest|meadow

The primary key of each will still be *Meadow*, and players will still
see that name. We can also add any number of other Aliases to each
meadow if we want. But we will also henceforth always be able to
uniquely identify the right meadow by prepending its primary key name
with ``#zonename|``.

Enforcing zones
---------------

Maybe you feel that this usage of aliases for zones is somehow loose and
ad-hoc. It is, and there is no guarantee that a builder would follow the
naming convention - unless you force them. And you can do that easily by
changing for example the ``@dig`` `Command <Commands.html>`_ to require
the zone to be given:

::

     @dig zone|roomname:typeclass = north;n, south;s

Just have the ``@dig`` command auto-add an alias of the correct format
and hey-presto! A functioning zone system! An even more convenient way
to enforce zones would be for the new room to inherit the zone from the
room we are building from.

Overload the default ``search`` method on a typeclass for further
functionality:

::

    def search(self, ostring, zone=None, *args, **kwargs):
        if zone:
            ostring = "#%s|%s" % (ostring, zone)
        return self.dbobj.search(ostring, *args, **kwargs)

You will then be able to do, from commands:

::

     meadow_obj = self.caller.search("meadow", zone="magicforest")

and be sure you are getting the magical meadow, not the normal one.

You could also easily build search queries searching only for rooms with
aliases starting with ``#magicforest|``. This would allow for easy
grouping and retrieving of all rooms in a zone for whatever need to
have.

Evennia's open solution to zones means that you have much more power
than in most MUD systems. There is for example no reason why you have to
group and organize only rooms with this scheme.

Using typeclasses and inheritance for zoning
--------------------------------------------

The above alias scheme is basically a way to easily find and group
objects together at run-time - a way to label, if you will. It doesn't
instill any sort of functional difference between a magical forest room
and a normal one. For this you will need to use Typeclasses. If you know
that a certain typeclass of room will always be in a certain zone you
could even hard-code the zone in the typeclass rather than enforce the
``@dig`` command to do it:

::

     class MagicalForestRoom(Room)
         def at_object_creation(self):
             ...
             self.aliases = "#magicforest|%s" % self.key  
             ...
     class NormalForestRoom(Room)
         def at_object_creation(self):
             ...
             self.aliases = "#normalforest|%s" % self.key
             ...

Of course, an alternative way to implement zones themselves is to have
all rooms/objects in a zone inherit from a given typeclass parent - and
then limit your searches to objects inheriting from that given parent.
The effect would be the same and you wouldn't need to implement any
ad-hoc aliasing scheme; but you'd need to expand the search
functionality to properly search the inheritance tree.
