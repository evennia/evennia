Building Quick-start
====================

The default `command <Commands.html>`_ definitions coming with Evennia
follows a style `similar <UsingMUXAsAStandard.html>`_ to that of MUX, so
the commands should be familiar if you used any such code bases before.
If you haven't, you might be confused by the use of ``@`` all over. This
is just a naming convention - commands related to out-of-character or
admin-related actions tend to start with ``@``, the symbol has no
meaning of its own.

The default commands have the following style (where ``[...]`` marks
optional parts):

::

     command[/switch/switch...] [arguments ...]

A *switch* is a special, optional flag to the command to make it behave
differently. It is always put directly after the command name, and
begins with a forward slash (``/``). The *arguments* are one or more
inputs to the commands. It's common to use an equal sign (``=``) when
assigning something to an object.

Below are some examples of commands. Use ``help <command>`` for learning
more about each command and their detailed options.

Making a Builder
----------------

If you just installed Evennia, your very first player account is called
user #1, also known as the *superuser* or *god user*. This user is very
powerful, so powerful that it will override many game restrictions such
as locks. This can be useful, but it also hides some functionality that
you might want to test. Let's create a more "normal" Builder player
account instead.

Get to Evennia's login screen (log off with ``@quit`` if you are already
connected) and choose ``create`` from the login screen. Create a new
account (don't log in yet). You can use any e-mail address, it doesn't
have to be an existing one. Let's say we call the new account "Anna".
Next log in *on your superuser account* and give the recently created
player build rights:

::

     @perm Anna = Builders

You could give the permission "Immortals" instead, if you want to assign
full admin privileges. Log out of your superuser account (``@quit``) and
finally log back in again as your new builder account.

Creating an object
------------------

Basic objects can be anything -- swords, flowers and non-player
characters. They are created using the ``@create`` command:

::

    > @create box

This created a new 'box' (of the default object type) in your inventory.
Use the command ``inventory`` (or ``i``) to see it. Now, 'box' is a
rather short name, let's is give a few aliases.

::

    > @name box = very large box;box;very;bo;crate

We now actually renamed the box to *very large box* (and this is what we
will see when looking at the room), but we will also recognize it by any
of the other names we give - like *crate* or simply *box* as before. We
could have given these aliases directly after the name in the
``@create`` command, this is true for all creation commands - you can
always tag on a list of ;-separated aliases to the name of your new
object. If you had wanted to not change the name itself, but to only add
aliases, you could have used the ``@alias`` command.

We are currently carrying the box, which you can see if you give the
command ``inventory`` (or ``i``). Let's drop it.

::

    > drop box

Hey presto - there it is on the ground, in all its normality (you can
also create & drop in one go using the ``/drop`` switch, like this:
``@create/drop box``).

::

    > examine box

This will show some technical details about the box object (you can
normally just write ``ex`` as a short for ``examine``).

Try to ``look`` at the box to see the (default) description.

::

    > look box

Let's add some flavor.

::

    > @describe box = This is a large and very heavy box.

If you try the ``get`` command we will pick up the box. So far so good,
but if we really want this to be a large and heavy box, people should
*not* be able to run off with it that easily. To prevent this we need to
lock it down. This is done by assigning a *Lock* to it. Make sure the
box was dropped in the room, then try this:

::

    > @lock box = get:false()

Locks are a rather `big topic <Locks.html>`_, but for now that will do
what we want. This will lock the box so noone can lift it. The exception
is superusers, they override all locks and will pick it up anyway. Make
sure you are using your builder account and not the superuser account
and try to get the box now:

::

    > get box
    You can't get that. 

Think the default error message looks dull? The ``get`` command looks
for an `Attribute <Attributes.html>`_ named ``get_err_msg`` for
returning a nicer error message (we just happen to know this, you would
need to peek into the code for the ``get`` command to find out). You set
attributes using the ``@set`` command:

::

    > @set box/get_err_msg = The box is way too heavy for you to lift. 

Try to get it now and you should see a nicer error message echoed back
to you.

Get a personality
-----------------

`Scripts <Scripts.html>`_ are powerful things that allows time-dependent
effects on objects. To try out a first script, let's put one on
ourselves. There is an example script in
``game/gamesrc/scripts/examples/bodyfunctions.py`` that is called
``BodyFunctions``. To add this to us we will use the ``@script``
command:

::

    > @script self = examples.bodyfunctions.BodyFunctions

(note that you don't have to give the full path as long as you are
pointing to a place inside the ``gamesrc/scripts`` directory). Wait a
while and you will notice yourself starting making random observations.

::

    > @script self 

This will show details about scripts on yourself (also ``examine``
works). You will see how long it is until it "fires" next. Don't be
alarmed if nothing happens when the countdown reaches zero - this
particular script has a randomizer to determine if it will say something
or not. So you will not see output every time it fires.

When you are tired of your character's "insights", kill the script with

::

    > @script/stop self = examples.bodyfunctions.BodyFunctions

Pushing your buttons
--------------------

If we get back to the box we made, there is only so much fun you can do
with it at this point. It's just a dumb generic object. If you renamed
it ``carpet`` and changed its description noone would be the wiser.
However, with the combined use of custom
`Typeclasses <Typeclasses.html>`_, `Scripts <Scripts.html>`_ and
object-based `Commands <Commands.html>`_, you could expand it and other
items to be as unique, complex and interactive as you want.

Let's take an example. So far we have only created objects that use the
default object typeclass named simply ``Object``. Let's create an object
that is a little more interesting. Under ``game/gamesrc/objects/`` there
is a directory ``examples`` with a module ``red_button.py``. It contains
the enigmatic RedButton typeclass.

Let's make us one of *those*!

::

    > @create/drop button:examples.red_button.RedButton

We import the RedButton python class the same way you would import it in
Python except Evennia defaults to looking in ``game/gamesrc/objects/``
so you don't have to write the full path every time. There you go - one
red button.

The RedButton is an example object intended to show off many of
Evennia's features. You will find that the `Scripts <Scripts.html>`_ and
`Commands <Commands.html>`_ controlling it are scattered in
``examples``-folders all across ``game/gamesrc/``.

If you wait for a while (make sure you dropped it!) the button will
blink invitingly. Why don't you try to push it ...? Surely a big red
button is meant to be pushed. You know you want to.

Creating a room called 'house'
------------------------------

The main command for shaping the game world is ``@dig``. For example, if
you are standing in Limbo you can dig a route to your new house location
like this:

::

    > @dig house = large red door;door;in, to the outside;out

This will create a new room named 'house'. It will also directly create
an exit from your current location named 'large red door' and a
corresponding exit named 'to the outside' in the house room leading back
to Limbo. We also define a few aliases to those exits, so people don't
have to write the full thing all the time.

If you wanted to use normal compass directions (north, west, southwest
etc), you could do that with ``@dig`` too. But Evennia also has a
limited version of ``@dig`` that helps for compass directions (and also
up/down and in/out). It's called ``@tunnel``:

::

    > @tunnel sw = cliff

This will create a new room "cliff" with an exit "southwest" leading
there and a path "northeast" leading back from the cliff to your current
location.

You can create exits from anywhere at any time using the ``@open``
command:

::

    > @open north;n = house

This opens an exit ``north`` to the previously created room ``house``.

If you have many rooms named ``house`` you will get a list of matches
and have to select which one you want to link to. You can also give its
database ref number, which is unique to every object. This can be found
with the ``examine`` command or by looking at the latest constructions
with ``@objects``.

Follow the north exit to your 'house' or ``@teleport`` to it:

::

    > north

or:

::

    > @teleport house

To manually open an exit back to Limbo (if you didn't do so with the
``@dig`` command):

::

    > @open door = limbo

(or give limbo's dbref which is #2)

Finding and manipulating existing objects
-----------------------------------------

To re-point an exit at another room or object, you can use

::

    > @link <room name> = <new_target name>

To find something, use

::

    > @find <name>

This will return a list of dbrefs that have a similar name.

To teleport something somewhere, one uses

::

    > @teleport <object> = <destination>

To destroy something existing, use

::

    > @destroy <object>

You can destroy many objects in one go by giving a comma-separated list
of objects to the command.

Adding a help entry
-------------------

An important part of building is keeping the help files updated. You can
add, delete and append to existing help entries using the ``@sethelp``
command.

::

    > @sethelp/add MyTopic = This help topic is about ... 

Adding a World
--------------

Evennia comes with a tutorial world for you to build. To build this you
need to log back in as *superuser*. Place yourself in Limbo and do:

::

     @batchcommand contrib.tutorial_world.build

This will take a while, but you will see a lot of messages as the world
is built for you. You will end up with a new exit from Limbo named
*tutorial*. See more info about the tutorial world
`here <TutorialWorldIntroduction.html>`_. Read
``contrib/tutorial/world/build.ev`` to see exactly how it's built, step
by step.
