The Batch-Code processor
========================

For an introduction and motivation to using batch processors, see
`here <BatchProcessors.html>`_. This page describes the Batch-*code*
processor. The Batch-*command* one is covered
`here <BatchCommandProcessor.html>`_.

Basic Usage
-----------

The batch-command processor is a superuser-only function, invoked by

::

     > @batchcode path.to.batchcodefile

Where ``path.to.batchcodefile`` is the path to a *batch-code file* with
the "``.py``\ " file ending. This path is given like a python path
relative to a folder you define to hold your batch files, set by
``BATCH_IMPORT_PATH`` in your settings. Default folder is
``game/gamesrc/world``. So if you want to run the example batch file in
``game/gamesrc/world/examples/batch_code.py``, you could simply use

::

     > @batchcommand examples.batch_code

This will try to run through the entire batch file in one go. For more
gradual, *interactive* control you can use the ``/interactive`` switch.
The switch ``/debug`` will put the processor in *debug* mode. Read below
for more info.

The batch file
--------------

A batch-code file is mostly a normal Python source file. The only thing
separating a batch file from any standard Python module is that the code
is wrapped into *blocks* using a special syntax. These blocks allow the
batch processor more control over execution, especially when using the
processor's *interactive* mode. In interactive mode these blocs allow
the batchcode runner to pause and only execute certain blocks at a time.
There is however nothing stopping you from coding everything in one
single block if you don't want to split things up into chunks like this.

Here are the rules of syntax of the batch-command ``*.py`` file.

-  ``#HEADER`` as the first on a line marks the start of a *header*
   block. This is intended to hold imports and variables that might be
   of use for other blocks. All python code defined in a header block
   will always be inserted at the top of all ``#CODE`` blocks in the
   file. You may have more than one ``#HEADER`` block, but that is
   equivalent to having one big one. Comments in ``#HEADER`` blocks are
   stripped out before merging.
-  ``#CODE`` as the first on a line marks the start of a *code* block.
   Code blocks contain functional python code. ``#HEADER`` blocks are
   added to the top of code blocks at runtime.
-  ``#CODE (info) obj1, obj2, ...`` is an optional form of the code
   block header. The ``(info)`` field gives extra info about what's
   going on in the block and is displayed by the batch processor. The
   ``obj1, obj2, ...`` parts are optional object labels used by the
   processor's *debug* mode in order to auto-delete objects after a test
   run.
-  ``#INSERT path.filename`` as the first on a line loads the contents
   of another batch-code file into this one. Its ``#CODE`` blocks will
   be executed as if they were defined in this file, but they will not
   share ``#HEADER``\ s with the current file, but only use its own, if
   any.
-  A new ``#HEADER``, ``#CODE`` or ``#INSERT`` (or the end of the file)
   ends a previous block. Text before the first block are ignored.
-  A ``#`` that is not starting a ``#HEADER``, ``#CODE`` or ``#INSERT``
   instruction is considered a comment.
-  Inside a block, normal Python syntax rules apply. For the sake of
   indentation, each block acts as a separate python module.
-  The variable ``caller`` is always made available to the script,
   pointing to the object executing the batchcommand.

Below is a version of the example file found in
``game/gamesrc/commands/examples/batch_code.py``.

::

    #
    # This is an example batch-code build file for Evennia. 
    #

    #HEADER

    # This will be included in all other #CODE blocks

    from src.utils import create, search
    from game.gamesrc.objects.examples import red_button
    from game.gamesrc.objects import baseobjects

    limbo = search.objects(caller, 'Limbo', global_search=True)[0]


    #CODE (create red button)

    red_button = create.create_object(red_button.RedButton, key="Red button", 
                                      location=limbo, aliases=["button"])

    # caller points to the one running the script
    caller.msg("A red button was created.")

    # importing more code from another batch-code file
    #INSERT examples.batch_code_insert

    #CODE (create table and chair) table, chair

    table = create.create_object(baseobjects.Object, key="Blue Table", location=limbo)
    chair = create.create_object(baseobjects.Object, key="Blue Chair", location=limbo)

    string = "A %s and %s were created. If debug was active, they were deleted again." 
    caller.msg(string % (table, chair))

This uses Evennia's Python API to create three objects in sequence.

Debug mode
----------

Try to run the example script with

::

     > @batchcode/debug examples.batch_code

The batch script will run to the end and tell you it completed. You will
also get messages that the button and the two pieces of furniture where
created. Look around and you should see the button there. But you won't
see any chair nor a table! This is because we ran this with the
``/debug`` switch. The debug mode of the processor is intended to be
used when you test out a script. Maybe you are looking for bugs in your
code or try to see if things behave as they should. Running the script
over and over would then create an ever-growing stack of buttons, chairs
and tables, all with the same name. You would have to go back and
painstakingly delete them later. The debug mode simply tries to
automatically delete the objects that where created so as to not crowd
the room with unwanted objects.

The second ``#CODE`` block supplies the variable names ``table`` and
``chair``, which match the actual variables we later assign our new
ojects to. In debug mode the batch-code processor will look for these
references and simply run ``delete()`` on them. Since the
button-creating block does not define any such variables the processor
can't help us there - meaning the button stays also in debug mode.

Interactive mode
----------------

Interactive mode works very similar to the `batch-command processor
counterpart <BatchCommandProcessor.html>`_. It allows you more step-wise
control over how the batch file is executed. This is useful for
debugging or for picking and choosing only particular blocks to run. Use
``@batchcommand`` with the ``/interactive`` flag to enter interactive
mode.

::

     > @batchcode/interactive examples.batch_code

You should see the following:

::

    01/02: #CODE (create red button) [...]         (hh for help) 

This shows that you are on the first ``#CODE`` block, the first of only
two commands in this batch file. Observe that the block has *not*
actually been executed at this point!

To take a look at the full code snippet you are about to run, use ``ll``
(a batch-processor version of ``look``).

::

    from src.utils import create, search
    from game.gamesrc.objects.examples import red_button
    from game.gamesrc.objects import baseobjects

    limbo = search.objects(caller, 'Limbo', global_search=True)[0]

    red_button = create.create_object(red_button.RedButton, key="Red button", 
                                      location=limbo, aliases=["button"])

    # caller points to the one running the script
    caller.msg("A red button was created.")

Compare with the example code given earlier. Notice how the content of
``#HEADER`` has been pasted at the top of the ``#CODE`` block. Use
``pp`` to actually execute this block (this will create the button and
give you a message). Use ``nn`` (next) to go to the next command. Use
``hh`` for a list of commands.

If there are tracebacks, fix them in the batch file, then use ``rr`` to
reload the file. You will still be at the same code block and can rerun
it easily with ``pp`` as needed. This makes for a simple debug cycle. It
also allows you to rerun individual troublesome blocks - as mentioned,
in a large batch file this can be very useful (don't forget the
``/debug`` mode either).

Use ``nn`` and ``bb`` (next and back) to step through the file; e.g.
``nn 12`` will jump 12 steps forward (without processing any blocks in
between). All normal commands of Evennia should work too while working
in interactive mode.

Limitations and Caveats
-----------------------

The batch-code processor is by far the most flexible way to build a
world in Evennia. There are however some caveats you need to keep in
mind.

-  *Safety*. Or rather the lack of it. There is a reason only
   *superusers* are allowed to run the batch-code processor by default.
   The code-processor runs *without any Evennia security checks* and
   allows full access to Python. If an untrusted party could run the
   code-processor they could execute arbitrary python code on your
   machine, which is potentially a very dangerous thing. If you want to
   allow other users to access the batch-code processor you should make
   sure to run Evennia as a separate and very limited-access user on
   your machine (i.e. in a 'jail'). By comparison, the batch-command
   processor is much safer since the user running it is still 'inside'
   the game and can't really do anything outside what the game commands
   allow them to.
-  *You cannot communicate between code blocks*. Global variables won't
   work in code batch files, each block is executed as stand-alone
   environments. Similarly you cannot in one ``#CODE`` block assign to
   variables from the ``#HEADER`` block and expect to be able to read
   the changes from another ``#CODE`` block (whereas a python execution
   limitation, allowing this would also lead to very hard-to-debug code
   when using the interactive mode). The main issue with this is when
   building e.g. a room in one code block and later want to connect that
   room with a room you built in another block. To do this, you must
   perform a database search for the name of the room you created (since
   you cannot know in advance which dbref it got assigned). This sounds
   iffy, but there is an easy way to handler this - use object aliases.
   You can assign any number of aliases to any object. Make sure that
   one of those aliases is unique (like "room56") and you will
   henceforth be able to always find it later by searching for it from
   other code blocks regardless of if the main name is shared with
   hundreds of other rooms in your world (coincidentally, this is also
   one way of implementing "zones", should you want to group rooms
   together).

