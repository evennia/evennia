# Tutorial World Introduction


The *Tutorial World* is a small and functioning MUD-style game world.  It is intended to be
deconstructed and used as a way to learn Evennia.  The game consists of a single-player quest and
has some 20 rooms that you can explore as you seek to discover the whereabouts of a mythical weapon.

The source code is fully documented. You can find the whole thing in
`evennia/contrib/tutorial_world/`.

Some features exemplified by the tutorial world: 

- Tutorial command, giving "behind-the-scenes" help for every room and some of the special objects
- Rooms with custom `return_appearance` to show details. 
- Hidden exits
- Objects with multiple custom interactions
- Large-area rooms
- Outdoor weather rooms
- Dark room, needing light source
- Puzzle object
- Multi-room puzzle
- Aggressive mobile with roam, pursue and battle state-engine AI
- Weapons, also used by mobs
- Simple combat system with attack/defend commands
- Object spawning
- Teleporter trap rooms


## Install

The tutorial world consists of a few modules in `evennia/contrib/tutorial_world/` containing custom
[Typeclasses](Typeclasses) for [rooms and objects](Objects) and associated [Commands](Commands).

These reusable bits and pieces are then put together into a functioning game area ("world" is maybe
too big a word for such a small zone) using a [batch script](Batch-Processors) called `build.ev`. To
install, log into the server as the superuser (user #1) and run:

    @batchcommand tutorial_world.build

The world will be built (this might take a while, so don't rerun the command even if it seems the
system has frozen). After finishing you will end up back in Limbo with a new exit called `tutorial`.

An alternative is 

    @batchcommand/interactive tutorial_world.build

with the /interactive switch you are able to step through the building process at your own pace to
see what happens in detail.

To play the tutorial "correctly", you should *not* do so as superuser.  The reason for this is that
many game systems ignore the presence of a superuser and will thus not work as normal. Use the
`@quell` command to limit your powers or log out and reconnect as a different user. As superuser you
can of course examine things "under the hood" later if you want.

## Gameplay

![the castle off the moor](https://images-wixmp-
ed30a86b8c4ca887773594c2.wixmp.com/f/22916c25-6299-453d-a221-446ec839f567/da2pmzu-46d63c6d-9cdc-41dd-87d6-1106db5a5e1a.jpg/v1/fill/w_600,h_849,q_75,strp/the_castle_off_the_moor_by_griatch_art_da2pmzu-
fullview.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOiIsImlzcyI6InVybjphcHA6Iiwib2JqIjpbW3siaGVpZ2h0IjoiPD04NDkiLCJwYXRoIjoiXC9mXC8yMjkxNmMyNS02Mjk5LTQ1M2QtYTIyMS00NDZlYzgzOWY1NjdcL2RhMnBtenUtNDZkNjNjNmQtOWNkYy00MWRkLTg3ZDYtMTEwNmRiNWE1ZTFhLmpwZyIsIndpZHRoIjoiPD02MDAifV1dLCJhdWQiOlsidXJuOnNlcnZpY2U6aW1hZ2Uub3BlcmF0aW9ucyJdfQ.omuS3D1RmFiZCy9OSXiIita-
HxVGrBok3_7asq0rflw)


*To get into the mood of this miniature quest, imagine you are an adventurer out to find fame and
fortune. You have heard rumours of an old castle ruin by the coast. In its depth a warrior  princess
was buried together with her powerful magical weapon - a valuable prize, if it's true. Of course
this is a chance to adventure that you cannot turn down!*

*You reach the ocean in the midst of a raging thunderstorm. With wind and rain screaming in your
face you stand where the moor meets the sea along a high, rocky coast ...*

- Look at everything.
- Some objects are interactive in more than one way. Use the normal `help` command to get a feel for
which commands are available at any given time. (use the command `tutorial` to get insight behind
the scenes of the tutorial).

- In order to fight, you need to first find some type of weapon.
- *slash* is a normal attack
- *stab* launches an attack that makes more damage but has a lower chance to hit.
- *defend* will lower the chance to taking damage on your enemy's next attack.
- You *can* run from a fight that feels too deadly. Expect to be chased though.
- Being defeated is a part of the experience ...
 
## Uninstall

Uninstalling the tutorial world basically means deleting all the rooms and objects it consists of.
First, move out of the tutorial area.

     @find tut#01
     @find tut#16

This should locate the first and last rooms created by `build.ev` - *Intro* and *Outro*. If you
installed normally, everything created between these two numbers should be part of the tutorial.
Note their dbref numbers, for example 5 and 80. Next we just delete all objects in that range:

     @del 5-80

You will see some errors since some objects are auto-deleted and so cannot be found when the delete
mechanism gets to them. That's fine.  You should have removed the tutorial completely once the
command finishes.

## Notes

When reading and learning from the code, keep in mind that *Tutorial World* was created with a very
specific goal: to install easily and to not permanently modify the rest of the server. It therefore
goes to some length to use only temporary solutions and to clean up after
itself. 