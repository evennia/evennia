Tutorial World Introduction
===========================

The *Tutorial World* is, quite simply, a small example of Evennia usage
for you to learn from. It's also a functioning (if small) game - a small
single-player quest area with some 20 rooms that you can explore on your
quest to find a mythical weapon.

The source code is fully documented and you can find the whole thing in
``contrib/tutorial_world``.

Some features exemplified by the tutorial world:

-  Tutorial command, giving "behind-the-scenes" help for every room and
   some of the special objects
-  Hidden exits
-  Objects with multiple custom interactions
-  Large-area rooms
-  Outdoor weather rooms
-  Dark room, needing light source
-  Puzzle object
-  Multi-room puzzle
-  Aggressive mobile with roam, pursue and battle state-engine AI
-  Weapons, also used by mobs
-  Simple combat system with attack/defend commands
-  Object spawn
-  Teleporter trap rooms

Install
-------

The tutorial world consists of a a few modules in
``contrib/tutorial_world/`` containing custom
`Typeclasses <Typeclasses.html>`_ for `rooms and
objects <Objects.html>`_, associated `commands <Commands.html>`_ and a
few custom `scripts <Scripts.html>`_ to make things tick.

These reusable bits and pieces are then put together into a functioning
game area ("world" is maybe too big a word for such a small zone) using
a `batch script <BatchProcessors.html>`_ called ``build.ev``. To
install, log into the server as the superuser (user #1) and run:

::

    @batchcommand contrib.tutorial_world.build

The world will be built (there will be a lot of text output) and you
will end up back in Limbo with a new exit called ``tutorial``. You can
also use the ``/interactive`` switch of ``@batchcommand`` to be able to
slowly go through each step of building the world in detail.

To play the tutorial "correctly", you should *not* do so as superuser.
The reason for this is that many game systems ignore the presence of a
superuser and will thus not work as normal. Create a new, non-superuser
character instead (as superuser you can of course examine things "under
the hood" later if you want).

Notes
-----

When reading and learning from the code, keep in mind that *Tutorial
World* was created with a very specific goal: to install easily and to
not permanently modify the rest of the server. It therefore goes to some
length to use only temporary solutions and to clean up after itself.
None of the basic typeclasses are modified more than temporarily. This
means the tutorial sometimes needs to solve things in a more complex
fashion than really needed.

When coding your own game you'd of course not have such considerations -
you'd just customize the base typeclasses to always work just the way
you want and be done with it.
