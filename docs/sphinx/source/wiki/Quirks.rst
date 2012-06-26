Evennia Quirks
==============

This is a list of various problems or stumbling blocks that people often
ask about or report when using (or trying to use) Evennia. These are
common stumbling blocks, non-intuitive behaviour and common newbie
mistakes when working with Evennia. They are not bugs.

Actual Evennia bugs should be reported in
`Issues <https://code.google.com/p/evennia/issues/list>`_.

Editing code directly in \`src/\`
---------------------------------

Don't do this. Doing local changes to ``src`` will eventually conflict
with changes done by the Evennia developers. Rather you should import
``src``-modules into your own custom modules in ``game/gamesrc`` (or
copy&paste them over if you want to expand on the defaults). Next you
re-point the relevant links in your ``settings`` file to point to your
custom modules instead of the default ones.

If you want to expand the web interface, copy the entire ``src/web``
folder over to ``game/gamesrc`` and change the media links in your
``settings`` file.

If you find that ``src`` lacks some functionality you need, make an
`Issue <https://code.google.com/p/evennia/issues/list>`_ of the type
*Feature Request*. Or become a part of the Evennia development and
submit your own additions to the core.

Create typeclassed object by calling the typeclass
--------------------------------------------------

Alas, you cannot create a new Typeclass by just initializing the
classname. So ``obj = Object()`` won't do what you want. Whereas
Evennia's Typeclasses behave *pretty much* like normal Python classes,
this is one of the situations where they don't. You need to use
Evennia's create functions to add new objects. So use e.g.
``ev.create_object()``, ``ev.create_script()`` etc. (these are defined
in ``src/utils/create.py``). This will set up the Typeclass database
connection behind the scenes.

In the same vein, you cannot overload ``__init__()``, ``__setattr__`` or
``__getattribute__`` on Typeclasses. Use the hook methods
(``at_object_creation()`` etc) instead.

Web admin to create new Player
------------------------------

If you use the default login system and is trying to use the Web admin
to create a new Player account, you need to thread carefully. The
default login system *requires* the Player object to already have a
connected Character object - there is no character creation screen by
default. If using the normal mud login screen, a Character with the same
name is automatically created and connected to your Player. From the web
interface you must do this manually.

So, when creating the Player, make sure to also create the Character
*from the same form* as you create the Player from. This should set
everything up for you. Otherwise you need to manually set the "player"
property on the Character and the "character" property on the Player to
point to each other. You must also set the lockstring of the Character
to allow the Player to "puppet" this particular character.

The default login system is very simple and intended for you to easily
get into the game. The more advanced login system in ``contrib/`` along
with the example character-creation system does not require such an
initial coupling (i.e. you can create the coupling in-game). For your
initial experiments, it's easist to create your characters from the
normal MUD connection screen instead.

Mutable attributes and their connection to the database
-------------------------------------------------------

When storing a mutable object (usually a list or a dictionary) in an
Attribute

::

     object.db.mylist = [1,2,3]

you should know that the connection to the database is retained also if
you later extract that Attribute into another variable (what is stored
and retrieved is actually a ``PackedList`` or a ``PackedDict`` that
works just like their namesakes except they save themselves to the
database when changed). So if you do

::

     alist = object.db.mylist
     alist.append(4)

this updates the database behind the scenes, so both ``alist`` and
``object.db.mylist`` are now ``[1,2,3,4]``. If you don't want this,
convert the mutable object to its normal Python form.

::

     blist = list(object.db.mylist)
     blist.append(4)

The property ``blist`` is now ``[1,2,3,4]`` whereas ``object.db.mylist``
remains unchanged. You'd need to explicitly re-assign to the ``mylist``
Attribute in order to update the database. If you store nested mutables
you only need to convert the "outermost" one in order to "break" the
connection to the database like this.

General shakiness of the web admin
----------------------------------

Since focus has been on getting the underlying python core to work
efficiently, the web admin is not quite as stable nor easy to use as
we'd like at this point. Also, the web-based html code is, while
working, not very pretty or clean. These are areas where we'd much
appreciate getting more input and help.

Known upstream bugs
===================

These are known bugs in in the libraries Evennia uses, i.e. things out
of our control.

Error during manage.py syncdb
-----------------------------

This error can be seen using Django 1.4 without a *locale* set. It
causes a traceback during the ``manage.py syncdb`` phase, just when
trying to create the superuser.

::

    TypeError: decode() argument 1 must be string, not None

This opaque error means no locale could be found. Not properly handling
this is a bug in Django 1.4 reported
`here <https://code.djangoproject.com/ticket/16017>`_. You resolve it by
setting your locale (this is a good thing to have in any case). See the
comments to that bug report for how to do this.
