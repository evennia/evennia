# The Tutorial World

The *Tutorial World* is a small and functioning MUD-style game world shipped with Evennia.
It's a small showcase of what is possible. It can also be useful for those who have an easier
time learning by deconstructing existing code.

Stand in the Limbo room and install it with

    batchcommand tutorial_world.build

What this does is to run the build script
[evennia/contrib/tutorial_world/build.ev](github:evennia/contrib/tutorial_world/build.ev).
This is pretty much just a list of build-commands executed in sequence by the `batchcommand` command.
Wait for the building to complete and don't run it twice.

> After having run the batchcommand, the `intro` command also becomes available in Limbo. Try it out to 
> for in-game help and to get an example of [EvMenu](../../../Components/EvMenu.md), Evennia's in-built 
> menu generation system!

The game consists of a single-player quest and has some 20 rooms that you can explore as you seek
to discover the whereabouts of a mythical weapon. 

A new exit should have appeared named _Tutorial_. Enter by writing `tutorial`.

You will automatically `quell` when you enter (and `unquell` when you leave), so you can play the way it was intended.
Both if you are triumphant or if you use the `give up` command you will eventually end up back in Limbo.

```{important}
Only LOSERS and QUITTERS use the `give up` command.
```

## Gameplay

![the castle off the moor](https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/22916c25-6299-453d-a221-446ec839f567/da2pmzu-46d63c6d-9cdc-41dd-87d6-1106db5a5e1a.jpg/v1/fill/w_600,h_849,q_75,strp/the_castle_off_the_moor_by_griatch_art_da2pmzu-fullview.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOiIsImlzcyI6InVybjphcHA6Iiwib2JqIjpbW3siaGVpZ2h0IjoiPD04NDkiLCJwYXRoIjoiXC9mXC8yMjkxNmMyNS02Mjk5LTQ1M2QtYTIyMS00NDZlYzgzOWY1NjdcL2RhMnBtenUtNDZkNjNjNmQtOWNkYy00MWRkLTg3ZDYtMTEwNmRiNWE1ZTFhLmpwZyIsIndpZHRoIjoiPD02MDAifV1dLCJhdWQiOlsidXJuOnNlcnZpY2U6aW1hZ2Uub3BlcmF0aW9ucyJdfQ.omuS3D1RmFiZCy9OSXiIita-HxVGrBok3_7asq0rflw)
(image by Griatch)

*To get into the mood of this miniature quest, imagine you are an adventurer out to find fame and
fortune. You have heard rumours of an old castle ruin by the coast. In its depth a warrior  princess
was buried together with her powerful magical weapon - a valuable prize, if it's true. Of course
this is a chance to adventure that you cannot turn down!*

*You reach the ocean in the midst of a raging thunderstorm. With wind and rain screaming in your
face you stand where the moor meets the sea along a high, rocky coast ...*

---

### Gameplay hints

- Use the command `tutorial` to get code insight behind the scenes of every room.
- Look at everything. While a demo, the Tutorial World is not necessarily trivial to solve - it depends 
on your experience with text-based adventure games. Just remember that everything can be solved or bypassed.
- Some objects are interactive in more than one way. Use the normal `help` command to get a feel for
which commands are available at any given time.
- In order to fight, you need to first find some type of weapon.
    - *slash* is a normal attack
    - *stab* launches an attack that makes more damage but has a lower chance to hit.
    - *defend* will lower the chance to taking damage on your enemy's next attack.
- Some things _cannot_ be hurt by mundane weapons. In that case it's OK to run away. Expect
  to be chased though.
- Being defeated is a part of the experience. You can't actually die, but getting knocked out
  means being left in the dark ...

## Once you are done (or had enough)

Afterwards you'll either have conquered the old ruin and returned in glory and triumph ... or
you returned limping and whimpering from the challenge by using the `give up` command.
Either way you should now be back in Limbo, able to reflect on the experience.

Some features exemplified by the tutorial world:

- Rooms with custom ability to show details (like looking at the wall in the dark room)
- Hidden or impassable exits until you fulfilled some criterion
- Objects with multiple custom interactions (like swords, the well, the obelisk ...)
- Large-area rooms (that bridge is actually only one room!)
- Outdoor weather rooms with weather (the rain pummeling you)
- Dark room, needing light source to reveal itself (the burning splinter even burns out after a while)
- Puzzle object (the wines in the dark cell; hope you didn't get stuck!)
- Multi-room puzzle (the obelisk and the crypt)
- Aggressive mobile with roam, pursue and battle state-engine AI (quite deadly until you find the right weapon)
- Weapons, also used by mobs (most are admittedly not that useful against the big baddie)
- Simple combat system with attack/defend commands (teleporting on-defeat)
- Object spawning (the weapons in the barrel and the final weapoon is actually randomized)
- Teleporter trap rooms (if you fail the obelisk puzzle)

```{sidebar} Extra Credit

If you have previous programming experience (or after you have gone
through this Starter tutorial) it may be instructive to dig a little deeper into the Tutorial-world
code to learn how it achieves what it does. The code is heavily documented.
You can find all the code in [evennia/contrib/tutorials/tutorial_world](../../../api/evennia.contrib.tutorials.tutorial_world.md).
The build-script is [here](github:evennia/contrib/tutorials/tutorial_world/build.ev).


When reading the  code, remember that the Tutorial World was designed to install easily and to not permanently modify 
the rest of the game. It therefore makes sure to only use temporary solutions and to clean up after itself. This is 
not something you will often need to worry about when making your own game.
```

Quite a lot of stuff crammed in such a small area!

## Uninstall the tutorial world

Once are done playing with the tutorial world, let's uninstall it.
Uninstalling the tutorial world basically means deleting all the rooms and objects it consists of.
Make sure you are back in Limbo, then

     find tut#01
     find tut#16

This should locate the first and last rooms created by `build.ev` - *Intro* and *Outro*. If you
installed normally, everything created between these two numbers should be part of the tutorial.
Note their #dbref numbers, for example 5 and 80. Next we just delete all objects in that range:

     del 5-80

You will see some errors since some objects are auto-deleted and so cannot be found when the delete
mechanism gets to them. That's fine.  You should have removed the tutorial completely once the
command finishes.

Even if the game-style of the Tutorial-world was not similar to the one you are interested in, it
should  hopefully have given you a little taste of some of the possibilities of Evennia. Now we'll
move on with how to access this power through code.


