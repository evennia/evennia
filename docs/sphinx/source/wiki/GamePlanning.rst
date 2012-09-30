Game development tips and tricks
================================

So you have Evennia up and running. You have a great game idea in mind.
Now it's time to start cracking! But where to start? Here are some ideas
for a workflow. Note that the suggestions on this page are just that -
suggestions. Also, they are primarily aimed at a lone hobby designer or
a small team developing a game in their free time.

Phases of Evennia game development
==================================

Below are some minimal steps for getting the first version of a new game
world going with players. It's worth to at least make the attempt to do
these steps in order even if you are itching to jump ahead in the
development cycle. On the other hand, you should also make sure to keep
your work fun for you, or motivation will falter. Making a full game is
a lot of work as it is, you'll need all your motivation to make it a
reality.

Remember that *99.99999% of all great game ideas never lead to an online
game*. So your first all overshadowing goal is to beat those odds and
get *something* out the door! *Even* if it's a scaled-down version of
your dream game, lacking many "must-have" features! It's better to get
it out there and expand on it later than to code in isolation forever
until you burn out, lose interest or your hard drive crashes.

Like is common with online games, getting a game out the door does not
mean you are going to be "finished" with the game - most MUDs add
features gradually over the course of years - it's often part of the
fun!

1: Planning
-----------

This is what you do before having coded a single line or built a single
room. Many prospective game developers are very good at *parts* of this
process, namely in defining what their world is "about": The theme, the
world concept, cool monsters and so on. This is by all means important -
yes critical to the appeal of your game. But it's unfortunately not
enough to make your game a reality. To do that you must have an idea of
how to actually map those great ideas onto Evennia.

A good start is to begin by planning out the basic primitives of the
game and what they need to be able to do.

-  **Rooms** - consider the most basic room in your game. How "big" is
   it in a game sense? What should Players be able to do inside it? Is a
   simple description enough? Can it be dark (description
   changed/hidden)? Should it have smells, sounds? Weather? Different
   terrain? How are those to be conveyed? Are there special "magic"
   rooms that do things to people entering? Can a person hide in the
   room? Should all rooms have the ability to be this complex or should
   there be different types of rooms? Evennia allows you to change the
   very concept of rooms should you be very ambitious, but is that a
   road you really want to go down for your project?
-  **Objects** - consider the most basic (non-player-controlled) object
   in your game. What should a Player be able to do with it? Smash it?
   If so, will it need some measure of its health? Does it have weight
   or volume (so you cannot carry an infinite amount of them)? How do
   you handle multiple identical objects? Try to give rough
   classifications. Is a weapon a different type of object or are you
   supposed to be able to fight with a chair as well? What about
   NPCs/mobs, should they have some sort of AI?
-  **Systems** - These are the behind-the-scenes features that exist in
   your game, often without being represented by a specific in-game
   object. For a role playing game, you need to define chances of
   success ("rolls") for example. Will weather messages be random in
   every room or should it follow some sort of realistic pattern over
   all rooms? Do you have a game-wide economy - if so, how is that
   supposed to work? If magic is dependent on the position of the
   planets, the planets must change with time. What about spreading
   rumors? Mail boxes? Bulletin boards?
-  **Characters** - to do all those things with the rooms, objects and
   systems in the game, what will the Characters need to have? What
   skill will decide if they can "hide" in a room? Wield a chair as a
   weapon? How to tell how much they can carry or which objects they can
   smash? Can they gain experience and how? How about skills, classes,
   attributes?

A MUD's a lot more involved than you would think and these things hang
together in a complex web. It can easily become overwhelming and it's
tempting to want *all* functionality right out of the door. Try to
identify the basic things that "make" your game and focus on them for
the first release. Make a list. Keep future expansions in mind but limit
yourself.

2: Coding
---------

This is the actual work of creating the "game" part of your game. Many
"game-designer" types tend to gloss over this bit and jump directly to
**Building**. Vice-versa, many "game-coder" types tend to jump directly
to this part without doing the **Planning** first. Neither is good and
*will* lead to you having to redo all your hard work at least once,
probably more.

Evennia's `Developer Central <DeveloperCentral.html>`_ is focused on how
to perform this bit of the development. Evennia tries hard to make this
part easier for you, but there is no way around the fact that if you
want anything but a very basic Talker-type game you *will* have to bite
the bullet and code your game (or find a coder willing to do it for
you). Even if you won't code anything yourself, as a designer you need
to at least understand the basic paradigms of Evennia, such as objects,
commands and scripts and how they hang together. We recommend you go
through the `Tutorial World <TutorialWorldIntroduction.html>`_ in detail
(as well as skimming its code) to get at least a feel for what is
involved behind the scenes.

During Coding you look back at the things you wanted during the
**Planning** phase and try to implement them. Don't be shy to update
your plans if you find things easier/harder than you thought. The
earlier you revise problems, the easier they will be to fix.
`Here <VersionControl.html>`_ are some hints for setting up a sane
coding environment.

"Tech Demo" Building
~~~~~~~~~~~~~~~~~~~~

This is an integral part of your Coding. It might seem obvious to
experienced coders, but it cannot be emphasized enough that you should
*test* things on a *small* scale before putting your untested code into
a large game-world. The earlier you test, the easier and cheaper it will
be to fix bugs and even rework things that didn't work out the way you
thought they would. You might even have to go back to the **Planning**
phase if your ideas can't handle their meet with reality.

This means building singular in-game examples. Make one room and one
object of each important type and test they work as they should in
isolation, then add more if they are supposed to interact with each
other in some way. Build a small series of rooms to test how mobs move
around ... and so on. In short, a test-bed for your growing code. It
should be done gradually until you have a fully functioning (if not
guaranteed bug-free) miniature tech demo that shows *all* the features
you want in the first release of your game. There does not need to be
any game play or even a theme to your tests, but the more testing you do
on this small scale, the less headaches you will have in the next phase.

3: World Building
-----------------

Up until this point we've only had a few tech-demo objects in the
database. This step is the act of populating the database with a larger,
thematic world. Too many would-be developers jump to this stage too soon
and then have to go back and rework things on already existing objects.
Evennia's typeclass system does allow you to edit the properties of
existing objects, but some hooks are only called at object creation, and
you are in for a *lot* of unnecessary work if you build stuff en masse
without having the underlying code systems in some reasonable shape
first.

So, at this point the "game" bit (Coding + Testing) should be more or
less complete, *at least to the level of your initial release*. Building
often involves non-coders, so you also get to test whatever custom build
systems you have made at this point. You don't have to complete your
entire world in one go - just enough to make the game's "feel" come
across - an actual world where the intended game play can be tested and
roughly balanced. You can always add new areas later, so limit yourself.

Alpha Release
-------------

As mentioned, don't hold onto your world more than necessary. *Get it
out there* with a huge *Alpha* flag and let people try it! Call upon
your alpha-players to try everything - they *will* find ways to break
your game in ways that you never could have imagined. In Alpha you might
be best off to focus on inviting friends and maybe other MUD developers,
people who you can pester to give proper feedback and bug reports (there
*will* be bugs, there is no way around it). Follow the quick
instructions `here <OnlineSetup.html>`_ to make your game visible
online.

Beta Release/Perpetual Beta
---------------------------

Once things stabilize in Alpha you can move to *Beta* and let more
people in. Many MUDs are in `perpetual
beta <http://en.wikipedia.org/wiki/Perpetual_beta>`_, meaning they are
never considered "finished", but just repeat the cycle of Planning,
Coding, Testing and Building over and over as new features get
implemented or Players come with suggestions. As the game designer it's
up to you to perfect your vision.

Congratulations, at this point you have joined the small, exclusive
crowd who have made their dream game a reality!
