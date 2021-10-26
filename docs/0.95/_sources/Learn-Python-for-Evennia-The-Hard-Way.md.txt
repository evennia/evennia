# Learn Python for Evennia The Hard Way

# WORK IN PROGRESS - DO NOT USE

Evennia provides a great foundation to build your very own MU* whether you have programming
experience or none at all. Whilst Evennia has a number of in-game building commands and tutorials
available to get you started, when approaching game systems of any complexity it is advisable to
have the basics of Python under your belt before jumping into the code. There are many Python
tutorials freely available online however this page focuses on Learn Python the Hard Way (LPTHW) by
Zed Shaw. This tutorial takes you through the basics of Python and progresses you to creating your
very own online text based game. Whilst completing the course feel free to install Evennia and try
out some of our beginner tutorials. On completion you can return to this page, which will act as an
overview to the concepts separating your online text based game and the inner-workings of Evennia.
-The latter portion of the tutorial focuses working your engine into a webpage and is not strictly
required for development in Evennia.

## Exercise 23
You may have returned here when you were invited to read some code. If you haven’t already, you
should now have the knowledge necessary to install Evennia. Head over to the Getting Started page
for install instructions. You can also try some of our tutorials to get you started on working with
Evennia.

## Bridging the gap.
If you have successfully completed the Learn Python the Hard Way tutorial you should now have a
simple browser based Interactive Fiction engine which looks similar to this.
This engine is built using a single interactive object type, the Room class. The Room class holds a
description of itself that is presented to the user and a list of hardcoded commands which if
selected correctly will present you with the next rooms’ description and commands. Whilst your game
only has one interactive object, MU* have many more: Swords and shields, potions and scrolls or even
laser guns and robots. Even the player has an in-game representation in the form of your character.
Each of these examples are represented by their own object with their own description that can be
presented to the user.

A basic object in Evennia has a number of default functions but perhaps most important is the idea
of location. In your text engine you receive a description of a room but you are not really in the
room because you have no in-game representation. However, in Evennia when you enter a Dungeon you
ARE in the dungeon. That is to say your character.location = Dungeon whilst the Dungeon.contents now
has a spunky young adventurer added to it. In turn, your character.contents may have amongst it a
number of swords and potions to help you on your adventure and their location would be you.

In reality each of these “objects” are just an entry in your Evennia projects database which keeps
track of all these attributes, such as location and contents. Making changes to those attributes and
the rules in which they are changed is the most fundamental perspective of how your game works. We
define those rules in the objects Typeclass. The Typeclass is a Python class with a special
connection to the games database which changes values for us through various class methods. Let’s
look at your characters Typeclass rules for changing location.

             1. `self.at_before_move(destination)` (if this returns False, move is aborted)
             2. `self.announce_move_from(destination)`
             3. (move happens here)
             4. `self.announce_move_to(source_location)`
             5. `self.at_after_move(source_location)`

First we check if it’s okay to leave our current location, then we tell everyone there that we’re
leaving. We move locations and tell everyone at our new location that we’ve arrived before checking
we’re okay to be there. By default stages 1 and 5 are empty ready for us to add some rules. We’ll
leave an explanation as to how to make those changes for the tutorial section, but imagine if you
were an astronaut. A smart astronaut might stop at step 1 to remember to put his helmet on whilst a
slower astronaut might realise he’s forgotten in step 5 before shortly after ceasing to be an
astronaut.

With all these objects and all this moving around it raises another problem. In your text engine the
commands available to the player were hard-coded to the room. That means if we have commands we
always want available to the player we’ll need to have those commands hard-coded on every single
room. What about an armoury? When all the swords are gone the command to take a sword would still
remain causing confusion. Evennia solves this problem by giving each object the ability to hold
commands. Rooms can have commands attached to them specific to that location, like climbing a tree;
Players can have commands which are always available to them, like ‘look’, ‘get’ and ‘say’; and
objects can have commands attached to them which unlock when taking possession of it, like attack
commands when obtaining a weapon.
