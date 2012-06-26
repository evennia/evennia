\`ev\` - Evennia's flat API
===========================

Evennia consists of many components, some of which interact in rather
complex ways. One such example is the Typeclass system which is
implemented across four different folders in ``src/``. This is for
efficiency reasons and to avoid code duplication, but it means that it
can be a bit of a hurdle to understand just what connects to what and
which properties are actually available/inherited on a particular game
entity you want to use.

Evennia's ``ev`` API (Application Programming Interface) tries to help
with this. ``ev.py`` sits in evennia's root directory which means you
can import it from your code simply with ``import ev``. The ``ev``
module basically implements shortcuts to the innards of ``src/``. The
goal is to give a very "flat" structure (as opposed to a deeply nested
one). Not only is this a Python recommendation, it also makes it much
easier to see what you have.

Exploring \`ev\`
----------------

To check out evennia interactively, it's recommended you use a more
advanced Python interpreter, like `ipython <http://ipython.org/>`_. With
ipython you can easily read module headers and help texts as well as
list possible completions.

Start a python interactive shell, then get ``ev``:

::

     import ev

In ipython we can now do for example ``ev?`` to read the API's help
text. Using eg. ``ev.Object?`` will read the documentation for the
``Object`` typeclass. Use ``??`` to see source code. Tab on ``ev.`` to
see what ``ev`` contains.

Some highlights
---------------

-  ``Object, Player, Script, Room, Character, Exit`` - direct links to
   the most common base classes in Evennia.
-  ``search_*`` - shortcuts to the search functions in
   ``src.utils.search``, such as ``search_object()`` or
   ``search_script()``
-  ``create_*`` - are convenient links to all object-creation functions.
   Note that all Typeclassed objects *must* be created with methods such
   as these (or their parents in ``src.utils.create``) to make
   Typeclasses work.
-  ``managers`` - this is a container object that groups shortcuts to
   initiated versions of Evennia's django *managers*. So
   ``managers.objects`` is in fact equivalent to ``ObjectDB.objects``
   and you can do ``managers.objects.all()`` to get a list of all
   database objects. The managers allows to explore the database in
   various ways. To use, do ``from ev import manager`` and access the
   desired manager on the imported ``managers`` object.
-  default\_cmds - this is a container on ``ev`` that groups all default
   commands and command sets under itself. Do
   ``from ev import default_cmds`` and you can then access any default
   command from the imported ``default_cmds`` object.
-  ``utils, logger, gametime, ansi`` are various utilities. Especially
   utils contains many useful functions described
   `here <CodingUtils.html>`_.
-  ``syscmdkeys`` is a container that holds all the system-command keys
   needed to define system commands. Similar to the ``managers``
   container, you import this and can then access the keys on the
   imported ``syscmdkeys`` object.

To remember when importing from \`ev\`
--------------------------------------

Properties on ``ev`` are *not* modules in their own right. They are just
shortcut properties stored in the ``ev.py`` module. That means that you
cannot use dot-notation to ``import`` nested module-names over ``ev``.
The rule of thumb is that you cannot use ``import`` for more than one
level down. Hence you can do

::

     import ev
     print ev.default_cmds.CmdLook

or import one level down

::

     from ev import default_cmds
     print default_cmds.CmdLook

but you *cannot* import two levels down

::

     from ev.default_cmds import CmdLook # error!

This will give you an ``ImportError`` telling you that the module
``default_cmds`` cannot be found. This is not so strange -
``default_cmds`` is just a variable name in the ``ev.py`` module, it
does not exist outside of it.

As long as you keep this in mind, you should be fine. If you really want
full control over which level of package you import you can always
bypass ``ev`` and import directly from ``src/``. If so, look at
``ev.py`` to see where it imports from.
