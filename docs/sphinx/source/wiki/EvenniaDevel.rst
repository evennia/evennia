*Note: The devel branch merged with trunk as of r970 (aug2010). So if
you are new to Evennia, this page is of no real interest to you.*

Introduction
============

The Evennia that has been growing in trunk for the last few years is a
wonderful piece of software, with which you can do very nice coding
work. It has however grown 'organically', adding features here and there
by different coders at different times, and some features (such as my
State system) were bolted onto an underlying structure for which it was
never originally intended. Meanwhile Evennia is still in an alpha stage
and not yet largely used. If one needs to do a cleanup/refactoring and
homogenization of the code, now is the time time to do it. So I set out
to do just that.

The "devel-branch" of Evennia is a clean rework of Evennia based on
trunk. I should point out that the main goal has been to make system
names consistent, to add all features in a fully integrated way, and to
give all subsystems a more common API for the admin to work against.
This means that in the choice between a cleaner implementation and
backwards-compatability with trunk, the latter has had to stand back.
However, you'll hopefully find that converting old codes shouldn't be
too hard. Another goal is to further push Evennia as a full-fledged
barebones system for *any* type of mud, not just MUX. So you'll find far
more are now user-configurability now than ever before (MUX remains the
default though).

Devel is now almost ready for merging with the main trunk, but it needs
some more eyes to look at it first. If you are brave and want to help
report bugs, you can get it from the *griatch* branch with

``svn checkout http://evennia.googlecode.com/svn/branches/griatch evennia-devel``

Concepts changed from trunk to devel
====================================

Script parent -> Typeclasses
----------------------------

The biggest change is probably that script parents have been replaced by
*typeclasses*. Both handle the abstraction of in-game objects without
having to create a separate database model for each (i.e. it allows
objects to be anything from players to apples, rooms and swords all with
the same django database model). A script parent in trunk was a class
stored in a separate module together with a 'factory' function that the
engine called. The admin had to always remember if they were calling a
function on the database model or if it in fact sat on the script parent
(the call was made through something called the "scriptlink").

By contrast, a typeclass is a normal python class that inherits from the
*TypeClass* parent. There are no other required functions to define.
This class uses *\_getattribute\_* and *\_setattr\_* transparently
behind the scenes to store data onto the persistent django object. Also
the django model is aware of the typeclass in the reverse direction. The
admin don't really have to worry about this connection, they can usually
consider the two objects (typeclass and django model) to be one.

So if you have your 'apple' typeclass, accessing, say the 'location',
which is stored as a persistent field on the django model, you can now
just do ``loc = apple.location`` without caring where it is stored.

The main drawback with any typeclass/parent system is that it adds an
overhead to all calls, and this overhead might be slightly larger with
typeclasses than with trunk's script parents although I've not done any
testing. You also need to use Evennia's supplied ``create`` methods to
create the objects rather than to create objects with plain Django by
instantiating the model class; this so that the rather complex
relationships can be instantiated safely behind the scenes.

Command functions + !StateCommands-> Command classes + !CmdSets
---------------------------------------------------------------

In trunk, there was one default group of commands in a list
GLOBAL\_CMD\_TABLE. Every player in game used this. There was a second
dictionary GLOBAL\_STATE\_TABLE that held commands valid only for
certain *states* the player might end up in - like entering a dark room,
a text editor, or whatever. The problem with this state system, was that
it was limited in its use - every player could ever only be in one state
at a time for example, never two at the same time. The way the system
was set up also explicitly made states something unique to players - an
object could not offer different commands dependent on its state, for
example.

In devel, *every* command definition is grouped in what's called a
*CmdSet* (this is, like most things in Devel, defined as a class). A
command can exist in any number of cmdsets at the same time. Also the
'default' group of commands belong to a cmdset. These command sets are
no longer stored globally, but instead locally on each object capable of
launching commands. You can add and new cmdsets to an object in a
stack-like way. The cmdsets support set operations (Union, Difference
etc) and will merge together into one cmdset with a unique set of
commands. Removing a cmdset will re-calculate those available commands.
This allows you to do things like the following (impossible in trunk): A
player is walking down a corridor. The 'default' cmdset is in play. Now
he meets an enemy. The 'combat' cmdset is merged onto (and maybe
replacing part of) the default cmdset, giving him new combat-related
commands only available during combat. The enemy hits him over the head,
dazing him. The "Dazed" cmdset is now added on top of the previous ones
- maybe he now can't use certain commands, or might even get a garbled
message if trying to use 'look'. After a few moments the dazed state is
over, and the 'Dazed' cmdset is removed, returning us to the combat mode
we were in before. And so on.

Command definitions used to be functions, but are now classes. Instead
of relying on input arguments, all relevant variables are stored
directly on the command object at run-time. Also parsing and function
execution have been split into two methods that are very suitable for
subclassing (an example is all the commands in the default set which
inherits from the MuxCommand class - that's the one knowing about MUX's
special syntax with /switches, '=' and so on, Evennia's core don't deal
with this at all!).

Example of new command definition:

::

    class CmdTest(Command):
        def func(self):
             self.caller.msg("This is the test!")        

Events + States -> Scripts
--------------------------

The Event system of Evennia used to be a non-persistent affair; python
objects that needed to be explicitly called from code when starting.
States allowed for mapping different groups of commands to a certain
situations (see CmdSets above for how commands are now always grouped).

*Scripts* (warning: Not to be confused with the old *script parents*!)
are persistent database objects now and are only deleted on a server
restart if explicitly marked as non-persistent.

A script can have a time-component, like Events used to have, but it can
also work like an 'Action' or a 'State' since a script constantly checks
if it is still 'valid' and if not will delete itself. A script handles
everything that changes with time in Evennia. For example, all players
have a script attached to them that assigns them the default cmdset when
logging in.

Oh, and Scripts have typeclasses too, just like Objects, and carries all
the same flexibility of the Typeclass system.

User + player -> User + Player + character
------------------------------------------

In trunk there is no clear separation between the User (which is the
django model representing the player connecting to the mud) and the
player object. They are both forced to the same dbref and are
essentially the same for most purposes. This has its advantages, but the
problem is configurability for different game types - the in-game player
object becomes the place to store also OOC info, and allowing a player
to have many characters is a hassle (although doable, I have coded such
a system for trunk privately). Devel-branch instead separate a "player
character" into three tiers:

-  The User (Django object)
-  The PlayerDB (User profile + Player typeclass)
-  The ObjectDB (+ Character typeclass)

User is not something we can get out of without changing Django; this is
a permission/password sensitive object through which all Django users
connect. It is not configurable to any great extent except through it's
*profile*, a django feature that allows you to have a separate model
that configures the User. We call this profile 'PlayerDB', and for
almost all situations we deal with this rather than User. PlayerDB can
hold attributes and is typeclassed just like Objects and Scripts
(normally with a typeclass named simply *Player*) allowing very big
configurability options (although you can probably get away with just
the default setup and use attributes for all but the most exotic
designs). The Player is an OOC entity, it is what chats on channels but
is not visible in a room. The last stage is the in-game ObjectDB model,
typeclassed with a class called 'Character' by default. This is the
in-game object that the player controls.

The neat thing with this separation is that the Player object can easily
switch its Character object if desired - the two are just linking to
each other through attributes. This makes implementing multi-character
game types much easier and less contrived than in the old system.

Help database -> command help + help database
---------------------------------------------

Trunk stores all help entries in the database, including those created
dynamically from the command's doc strings. This forced a system where
the auto-help creation could be turned off so as to not overwrite later
changes made by hand. There was also a mini-language that allowed for
creating multiple help entries from the ``__doc__`` string.

Devel-branch is simpler in this regard. All commands are *always* using
``__doc__`` on the fly at run time without hitting the database (this
makes use of cmdsets to only show help for commands actually available
to you). The help database is stand-alone and you can add entries to it
as you like, the help command will look through both sources of help
entries to match your query.

django-perms + locks -> permission/locks
----------------------------------------

Trunk relies on Django's user-permissions. These are powerful but have
the disadvantage of being 'app-centric' in a way that makes sense for a
web app, not so much for a mud. The devel-branch thus implements a
completely stand-alone permission system that incoorperate both
permissions and locks into one go - the system uses a mini-language that
has a permission string work as a keystring in one situation and as a
complex lock (calling python lock functions you can define yourself) in
another.

The permission system is working on a fundamental level, but the default
setup probably needs some refinements still.

Mux-like comms -> Generic comms
-------------------------------

The trunk comm system is decidedly MUX-like. This is fine, but the
problem is that much of that mux-likeness is hard-coded in the engine.

Devel just defines three objects, Channel and Msg and an object to track
connections between players and channels (this is needed to easily
delete/break connections). How they interact with each other is up to
the commands that use them, making the system completely configurable by
the admin.

All ooc messages - to channels or to players or both at the same time,
are sent through use of the Msg object. This means a full log of all
communications become possible to keep. Other uses could be an e-mail
like in/out box for every player. The default setup is still mux-like
though.

Hard-coded parsing -> user customized parsing
---------------------------------------------

Essentially all parts of parsing a command from the command line can be
customized. The main parser can be replaced, as well as error messages
for multiple-search matches. There is also a considerable difference in
handling exits and channels - they are handled as commands with their
separate cmdsets and searched with the same mechanisms as any command
(almost any, anyway).

Aliases -> Nicks
----------------

Aliases (that is, you choosing to for yourself rename something without
actually changing the object itself) used to be a separate database
table. It is now a dictionary 'nicks' on the Character object - that
replace input commands, object names and channel names on the fly. And
due to the separation between Player and Character, it means each
character can have its own aliases (making this a suitable start for a
recog system too, coincidentally).

Attributes -> properties
------------------------

To store data persistently in trunk requires you to call the methods
``get_attribute_value(attr)`` and ``set_attribute(attr, value)``. This
is available for in-game Objects only (which is really the only data
type that makes sense anyway in Trunk).

Devel allows attribute storage on both Objects, Scripts and Player
objects. The attribute system works the same but now offers the option
of using the ``db`` (for database) directly. So in devel you could now
just do:

::

    obj.db.attr = value 
    value = obj.db.attr

And for storing something non-persistently (stored only until the server
reboots) you can just do

::

    obj.attr = value
    value = obj.attr

The last example may sound trivial, but it's actually impossible to do
in trunk since django objects are not guaranteed to remain the same
between calls (only stuff stored to the database is guaranteed to
remain). Devel makes use of the third-party ``idmapper`` functionality
to offer this functionality. This used to be a very confusing thing to
new Evennia admins.

*All* database fields in Devel are now accessed through properties that
handle in/out data storage. There is no need to save() explicitly
anymore; indeed you should ideally not need to know the actual Field
names.

Always full persistence -> Semi/Full persistence
------------------------------------------------

In Evennia trunk, everything has to be saved back/from the database at
all times, also if you just need a temporary storage that you'll use
only once, one second from now. This enforced full persistency is a good
thing for most cases - especially for web-integration, where you want
the world to be consistent regardless of from where you are accessing
it. Devel offer the ability to yourself decide this; since
semi-persistent variables can be stored on objects (see previous
section). What actually happens is that such variables are stored on a
normal python object called ``ndb`` (non-database), which is
transparently accessed. This does not touch the database at all.

Evennia-devel offers a setting ``FULL_PERSISTENCE`` that switches how
the server operates. With this off, you have to explicitly assign
attributes to database storage with e.g. ``obj.db.attr = value``,
whereas normal assignment (``obj.attr = value``) will be stored
non-persistent. With ``FULL_PERSISTENT`` on however, the roles are
reversed. Doing ``obj.attr = value`` will now actually be saving to
database, and you have to explicitly do ``obj.ndb.attr = value`` if you
want non-persistence. In the end it's a matter of taste and of what kind
of game/features you are implementing. Default is to use full
persistence (but all of the engine explicitly put out ``db`` and ``ndb``
making it work the same with both).

Commonly used functions/concept that changed names
==================================================

There used to be that sending data to a player object used a method
``emit_to()``, whereas sending data to a session used a method
``msg()``. Both are now called ``msg()``. Since there are situations
where it might be unclear if you receive a session or a player object
(especially during login/logout), you can now use simply use ``msg()``
without having to check (however, you *can* still use ``emit_to`` for
legacy code, it's an alias to msg() now). Same is true with
emit\_to\_contents() -> msg\_to\_contents().

``source_object`` in default commands are now consistently named
*caller* instead.

``obj.get_attribute_value(attr)`` is now just
``obj.get_attribute(attr)`` (but see the section on Attributes above,
you should just use ``obj.db.attr`` to access your attribute).

How hard is it to convert from trunk to devel?
==============================================

It depends. Any game logic game modules you have written (AI codes,
whatever) should ideally not do much more than take input/output from
evennia. These can usually be used straight off.

Commands and Script parents take more work but translate over quite
cleanly since the idea is the same. For commands, you need to make the
function into a class and add the parse(self) and func(self) methods
(parse should be moved into a parent class so you don't have to use as
much double code), as well as learn what variable names is made
available (see the commands in ``gamesrc/commands/default`` for
guidance). You can make States into CmdSets very easy - just listing the
commands needed for the state in a new CmdSet.

Script parents are made into Typeclasses by deleting the factory
function and making them inherit from a TypeClassed object (such as
Object or Player) like the ones in ``gamesrc/typeclasses/basetypes.py``,
and then removing all code explicitly dealing with script parents.

Converting to the new Scripts (again, don't confuse with the old *script
parents*!) is probably the trickiest, since they are a more powerful
incarnation of what used to be two separate things; States and Events.
See the examples in the ``gamesrc/scripts/`` for some ideas.

Better docs on all of this will be forthcoming.

Things not working/not implemented in devel (Aug 2010)
======================================================

All features planned to go into Devel are finished. There are a few
features available in Trunk that is not going to work in Devel until
after it merges with Trunk:

-  IMC2/IRC support is not implemented.
-  Attribute-level permissions are not formalized in the default cmdset.
-  Some of the more esoteric commands are not converted.

Please play with it and report bugs to our bug tracker!
