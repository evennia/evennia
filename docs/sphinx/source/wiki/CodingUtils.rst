Utils
=====

Evennia comes with many utilities to help with common coding tasks. Some
of these are part of the command interface but most can be found in the
``src/utils/`` folder. They are used all over the server, but offer help
for many common tasks when coding your own game as well. This is not a
complete list, check the module for more goodies.

Search
------

A common thing to do is to search for objects. The most common time one
needs to do this is inside a command body. There it's easiest to use the
``search`` method defined on all objects. This will search for objects
in the same location and inside the caller:

::

     obj = self.caller.search(objname)

Give the keyword ``global_search=True`` to extend search to encompass
entire database. Also aliases with be matched by this search. You will
find multiple examples of this functionality in the default command set.

If you need to search for objects in a code module you can use the
functions in ``src.utils.search``. You can access these as shortcuts
``ev.search_*``.

::

     from ev import search_object
     obj = search_object(objname)

``utils.search`` contains properties to the relevant database search
method. They are really just shortcuts to the django-database search
methods, like ``ObjectDB.objects.search()``.

**Note:** If you are a Django wizz, you might be tempted to use Django's
database search functions directly (using ``filter``, ``get`` etc). Just
remember that such operations will give you a django model whereas
Evennia's manager methods will give you a typeclass. It's easy to
convert between them with ``dbobj.typeclass`` and Â´typeclass.dbobjÂ´,
but you should remember this distinction. If you stick with Evennia's
search methods you will always get typeclasses back.

Create
------

Apart from the in-game build commands (``@create`` etc), you can also
build all of Evennia's game entities directly in code (for example when
defining new create commands). This *must* be done using
``src.utils.create`` or their shortcuts ``ev.create_*``- these functions
are responsible for setting up all the background intricacies of the
typeclass system and other things. Creating database instances using raw
Django will *not* work. Examples:

::

     import ev
     # 
     myobj = ev.create_objects("game.gamesrc.objects.myobj.MyObj",  key="MyObj")
     myscr = ev.create_script("game.gamesrc.scripts.myscripts.MyScript", obj=myobj)
     help = ev.create_help_entry("Emoting", "Emoting means that ...")
     msg = ev.create_message(senderobj, [receiverobj], "Hello ...")
     chan = ev.create_channel("news")
     player = ev.create_player("Henry", "henry@test.com", "H@passwd")

Each of these create functions have a host of arguments to further
customize the created entity. See ``src/utils/create.py`` for more
information.

Logging
-------

Normally you can use Python ``print`` statements to see output to the
terminal (if you started Evennia in *interactive mode* with the -i
switch). This should only be used for debugging though, for real output,
use the logger - it will log to the terminal in interactive mode, to the
log file otherwise.

::

     from ev import logger
     #
     logger.log_errmsg("This is an Error!")
     logger.log_warnmsg("This is a Warning!")
     logger.log_infomsg("This is normal information")
     logger.log_depmsg("This feature is deprecated")

There is also a special log-message type that is intended to be called
from inside a traceback - this can be very useful for relaying the
traceback message back to log without having it kill the server.

::

     try: 
       # [some code that may fail...]
     except Exception:
       logger.log_trace("This text will be appended to the traceback info")

inherits\_from()
----------------

This useful function takes two arguments - an object to check and a
parent. It returns ``True`` if object inherits from parent *at any
distance* (as opposed to Python's ``is_instance()`` that will only catch
immediate dependence. This function also accepts any combination of
classes, instances or python paths to classes as inputs.

Note that Python code should usually work with `duck
typing <http://en.wikipedia.org/wiki/Duck_typing>`_. But in Evennia's
case it can sometimes be useful to check if an object inherits from a
given `Typeclass <Typelasses.html>`_ as a way of identification. Say for
example that we have a typeclass *Animal*. This has a subclass *Felines*
which in turns is a parent to *HouseCat*. Maybe there are a bunch of
other animal types too, like horses and dogs. Using ``inherits_from``
will allow you to check for all animals in one go:

::

     from ev import utils
     if (utils.inherits_from(obj, "game.gamesrc.objects.animals.Animal"):
        obj.msg("The bouncer stops you in the door. He says: 'No talking animals allowed.'")

Some text utilities
-------------------

In a text game, you are naturally doing a lot of work shuffling text
back and forth. Here is a *non-complete* selection of text utilities
found in ``src/utils/utils.py`` (shortcut ``ev.utils``). If nothing else
it can be good to look here before starting to develop a solution of
your own.

fill()
~~~~~~

This flood-fills a text to a given width (shuffles the words to make
each line evenly wide). It also indents as needed.

::

     outtxt = fill(intxt, width=78, indent=4)

crop()
~~~~~~

This function will crop a very long line, adding a suffix to show the
line actually continues. This can be useful in listings when showing
multiple lines would mess up things.

::

     intxt = "This is a long text that we want to crop."
     outtxt = crop(intxt, width=19, suffix="[...]")
     # outtxt is now "This is a long text[...]"

dedent()
~~~~~~~~

This solves what may at first glance appear to be a trivial problem with
text - removing indentations. It is used to shift entire paragraphs to
the left, without disturbing any further formatting they may have. A
common case for this is when using Python triple-quoted strings in code
- they will retain whichever indentation they have in the code, and to
make easily-readable source code one usually don't want to shift the
string to the left edge.

::

          #python code is at this indentation 
          intxt = """
          This is an example text that will end
          up with a lot of whitespace on the left.
                    It also has indentations of 
                    its own."""                   
          outtxt = dedent(intxt)
          # outtxt will now retain all internal indentation
          # but be shifted all the way to the left. 

Normally you do the dedent in the display code (this is the way the help
system homogenizes help entries).

time\_format()
~~~~~~~~~~~~~~

This function takes a number of seconds as input and converts it to a
nice text output in days, hours etc. It's useful when you want to show
how old something is. It converts to four different styles of output
using the *style* keyword:

-  style 0 - ``5d:45m:12s`` (standard colon output)
-  style 1 - ``5d`` (shows only the longest time unit)
-  style 2 - ``5 days, 45 minutes`` (full format, ignores seconds)
-  style 3 - ``5 days, 45 minutes, 12 seconds`` (full format, with
   seconds)

text conversion()
~~~~~~~~~~~~~~~~~

Evennia supplies two utility functions for converting text to the
correct encodings. ``to_str()`` and ``to_unicode()``. The difference
from Python's in-built ``str()`` and ``unicode()`` operators are that
the Evennia ones makes use of the ``ENCODINGS`` setting and will try
very hard to never raise a traceback but instead echo errors through
logging. See `TextEncodings <TextEncodings.html>`_ for more info.

format\_table()
~~~~~~~~~~~~~~~

This function creates nicely formatted tables - columns of text all
lined up. It will automatically widen each column so all entries fit.

To use it, you need to create a list of lists - each sublist contains
the content of one column. The result will be a list of ready-formatted
strings to print.

::

    # title line 
    cols = [["num"],["x"],["y"]]
    # creating a dummy table with integers
    for i in range(3):
        cols[0].append(i)
        cols[1].append(i+1)
        cols[2].append(i+2)
    # format the table (returns list with rows)
    ftable = format_table(cols, extra_space=3)
    # print the rows, making header bright white
    for irow, row in enumerate(ftable):
        if irow == 0: # header
            print "{w%s{x" % row
        else:
            print row
    # Output (no colors shown):
    #
    # num   x   y
    #   1   2   3
    #   2   3   4
    #   3   4   5 
    #

Note that you cannot add colour codes to the input to ``format_table`` -
these would mess up the width of each column. Instead you can add this
to the output when printing.
