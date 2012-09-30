Tutorial World Introduction
===========================

The *Tutorial World* is, quite simply, a small example of Evennia usage
for you to learn from. It's also a functioning (if small) game - a
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

The world will be built (this might take a while, so don't rerun the
command even if it seems the system has frozen). After finishing you
will end up back in Limbo with a new exit called ``tutorial``.

An alternative is

::

    @batchcommand/interactive contrib.tutorial_world.build

with the /interactive switch you are able to step through the building
process at your own pace to see what happens in detail.

To play the tutorial "correctly", you should *not* do so as superuser.
The reason for this is that many game systems ignore the presence of a
superuser and will thus not work as normal. Log out, then reconnect.
From the login screen, create a new, non-superuser character for playing
instead. As superuser you can of course examine things "under the hood"
later if you want.

Gameplay
--------

*To get into the mood of this miniature quest, imagine you are an
adventurer out to find fame and fortune. You have heard rumours of an
old castle ruin by the coast. In its depth a warrior princess was buried
together with her powerful magical weapon - a valuable prize, if it's
true. Of course this is a chance to adventure that you cannot turn
down!*

*You reach the ocean in the midst of a raging thunderstorm. With wind
and rain screaming in your face you stand where the moor meets the sea
along a high, rocky coast ...*

-  Look at everything.
-  Some objects are interactive in more than one way. Use the normal
   ``help`` command to get a feel for which commands are available at
   any given time. (use the command ``tutorial`` to get insight behind
   the scenes of the tutorial).
-  In order to fight, you need to first find some type of weapon.

   -  *slash* is a normal attack
   -  *stab* launches an attack that makes more damage but has a lower
      chance to hit.
   -  *defend* will lower the chance to taking damage on your enemy's
      next attack.

-  You *can* run from a fight that feels too deadly. Expect to be chased
   though.
-  Being defeated is a part of the experience ...

Uninstall
---------

Uninstalling the tutorial world basically means deleting all the rooms
and objects it consists of. First, move out of the tutorial area.

::

     @find tut#01
     @find tut#17

This should locate the first and last rooms created by ``build.ev`` -
*Intro* and *Outro*. If you installed normally, everything created
between these two numbers should be part of the tutorial. Note their
dbref numbers, for example 5 and 80. Next we just delete all objects in
that range:

::

     @del 5-80

You will see some errors since some objects are auto-deleted and so
cannot be found when the delete mechanism gets to them. That's fine. You
should have removed the tutorial completely once the command finishes.

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
