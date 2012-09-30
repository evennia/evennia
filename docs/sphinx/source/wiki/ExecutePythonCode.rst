The \`@py\` command
===================

The ``@py`` command supplied with the default command set of Evennia
allows you to execute Python commands directly from inside the game. An
alias to ``@py`` is simply "``!``\ ". *Access to the ``@py`` command
should be severely restricted*. This is no joke - being able to execute
arbitrary Python code on the server is not something you should entrust
to just anybody.

::

    @py 1+2 
    <<< 3

Available variables
-------------------

A few local variables are made available when running ``@py``. These
offer entry into the running system.

-  **self** / **me** - the calling object (i.e. you)
-  **here** - the current caller's location
-  **obj** - a dummy `Object <Objects.html>`_ instance
-  **ev** - Evennia's flat API - through this you can access all of
   Evennia.

Returning output
----------------

This is an example where we import and test one of Evennia's utilities
found in ``src/utils/utils.py``, but also accessible through
``ev.utils``:

::

    @py from ev import utils; utils.time_format(33333)
    <<< Done.

Note that we didn't get any return value, all we where told is that the
code finished executing without error. This is often the case in more
complex pieces of code which has no single obvious return value. To see
the output from the ``time_format()`` function we need to tell the
system to echo it to us explicitly with ``self.msg()``.

::

    @py from ev import utils; self.msg(utils.time_format(33333))
    09:15
    <<< Done.

If you were to use Python's standard ``print``, you will see the result
in your current ``stdout`` (your terminal by default), *if* you are
running Evennia in *interactive mode* (with the ``-i`` flag).

Finding objects
---------------

A common use for ``@py`` is to explore objects in the database, for
debugging and performing specific operations that are not covered by a
particular command.

Locating an object is best done using ``self.search()``:

::

    @py self.search("red_ball")
    <<< Ball 

    @py self.search("red_ball").db.color = "red"
    <<< Done. 

    @py self.search("red_ball").db.color
    <<< red

``self.search()`` is by far the most used case, but you can also search
other database tables for other Evennia entities like scripts or
configuration entities. To do this you can use the generic search
entries found in ``ev.search_*``.

::

    @py ev.search_script("sys_game_time")
    <<< [<src.utils.gametime.GameTime object at 0x852be2c>]

(Note that since this becomes a simple statement, we don't have to wrap
it in ``self.msg()`` to get the output). You can also use the database
model managers directly (accessible through the ``objects`` properties
of database models or as ``ev.managers.*``). This is a bit more flexible
since it gives you access to the full range of database search methods
defined in each manager.

::

    @py ev.managers.scripts.script_search("sys_game_time")
    <<< [<src.utils.gametime.GameTime object at 0x852be2c>]

The managers are useful for all sorts of database studies.

::

    @py ev.managers.configvalues.all()
    <<< [<ConfigValue: default_home]>, <ConfigValue:site_name>, ...]

In doing so however, keep in mind the difference between `Typeclasses
and Database Objects <Typeclasses.html>`_: Using the search commands in
the managers will return *TypeClasses*. Using Django's default search
methods (``get``, ``filter`` etc) will return *Database objects*. This
distinction can often be disregarded, but as a convention you should try
to stick with the manager search functions and work with TypeClasses in
most situations.

::

    # this uses Evennia's manager method get_id(). 
    # It returns a Character typeclass instance
    @py ev.managers.objects.get_id(1).__class__
    <<< Character

    # this uses the standard Django get() query. 
    # It returns a django database model instance.
    @py ev.managers.objects.get(id=1).__class__
    <<< <class 'src.objects.models.ObjectDB'>

Running a Python Parser outside the game
========================================

``@py`` has the advantage of operating inside a running server, where
you can test things in real time. Much of this *can* be done from the
outside too though.

Go to the ``game`` directory and get into a new terminal.

::

    python manage.py shell

Your default Python intrepeter will start up, configured to be able to
work with and import all modules of your Evennia installation. From here
you can explore the database and test-run individual modules as desired.
Most of the time you can get by with just the ``ev`` module though. A
fully featured Python interpreter like
`iPython <http://ipython.scipy.org/moin/>`_ allow you to work over
several lines, but also has lots of other editing features, usch as
tab-completion and ``__doc__``-string reading.

::

    $ python manage.py shell

    IPython 0.10 -- An enhanced Interactive Python
    ...

    In [1]: import ev
    In [2]: ev.managers.objects.all()
    Out[3]: [<ObjectDB: Harry>, <ObjectDB: Limbo>, ...]

