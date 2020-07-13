# Game Planning


So you have Evennia up and running. You have a great game idea in mind. Now it's time to start
cracking!  But where to start? Here are some ideas for a workflow. Note that the suggestions on this
page are just that - suggestions. Also, they are primarily aimed at a lone hobby designer or a small
team developing a game in their free time. There is an article in the Imaginary Realities e-zine
which was written by the Evennia lead dev. It focuses more on you finding out your motivations for
making a game - you can 
[read the article here](http://journal.imaginary-realities.com/volume-07/issue-03/where-do-i-begin/index.html).


Below are some minimal steps for getting the first version of a new game world going with players.
It's worth to at least make the attempt to do these steps in order even if you are itching to jump
ahead in the development cycle. On the other hand, you should also make sure to keep your work fun
for you, or motivation will falter. Making a full game is a lot of work as it is, you'll need all
your motivation to make it a reality.

Remember that *99.99999% of all great game ideas never lead to a game*. Especially not to an online
game that people can actually play and enjoy. So our first all overshadowing goal is to beat those
odds and get *something* out the door! Even if it's a scaled-down version of your dream game,
lacking many "must-have" features! It's better to get it out there and expand on it later than to
code in isolation forever until you burn out, lose interest or your hard drive crashes.

Like is common with online games, getting a game out the door does not mean you are going to be
"finished" with the game - most MUDs add features gradually over the course of years - it's often
part of the fun!

## Planning (step 1)

This is what you do before having coded a single line or built a single room. Many prospective game
developers are very good at *parts* of this process, namely in defining what their world is "about":
The theme, the world concept, cool monsters and so on. It is by all means very important to define
what is the unique appeal of your game. But it's unfortunately not enough to make your game a
reality. To do that you must also have an idea of how to actually map those great ideas onto
Evennia.

A good start is to begin by planning out the basic primitives of the game and what they need to be
able to do. Below are a far-from-complete list of examples (and for your first version you should
definitely try for a much shorter list):

### Systems 

These are the behind-the-scenes features that exist in your game, often without being represented by
a specific in-game object.

- Should your game rules be enforced by coded systems or are you planning for human game masters to
run and arbitrate rules?
- What are the actual mechanical game rules? How do you decide if an action succeeds or fails? What
"rolls" does the game need to be able to do? Do you base your game off an existing system or make up
your own?
- Does the flow of time matter in your game - does night and day change? What about seasons? Maybe
your magic system is affected by the phase of the moon?
- Do you want changing, global weather? This might need to operate in tandem over a large number of
rooms.
- Do you want a game-wide economy or just a simple barter system? Or no formal economy at all?
- Should characters be able to send mail to each other in-game?
- Should players be able to post on Bulletin boards?
- What is the staff hierarchy in your game? What powers do you want your staff to have?
- What should a Builder be able to build and what commands do they need in order to do that?
- etc.

### Rooms 

Consider the most basic room in your game.

 - Is a simple description enough or should the description be able to change (such as with time, by
light conditions, weather or season)?
 - Should the room have different statuses? Can it have smells, sounds? Can it be affected by
dramatic weather, fire or magical effects? If so, how would this affect things in the room? Or are
these things something admins/game masters should handle manually?
 - Can objects be hidden in the room? Can a person hide in the room? How does the room display this?
 - etc.

### Objects

Consider the most basic (non-player-controlled) object in your game.

- How numerous are your objects? Do you want large loot-lists or are objects just role playing props
created on demand?
- Does the game use money? If so, is each coin a separate object or do you just store a bank account
value?
- What about multiple identical objects? Do they form stacks and how are those stacks handled in
that case?
- Does an object have weight or volume (so you cannot carry an infinite amount of them)?
- Can objects be broken? If so, does it have a health value? Is burning it causing the same damage
as smashing it? Can it be repaired?
- Is a weapon a specific type of object or are you supposed to be able to fight with a chair too?
Can you fight with a flower or piece of paper as well?
- NPCs/mobs are also objects. Should they just stand around or should they have some sort of AI?
- Are NPCs/mobs differet entities? How is an Orc different from a Kobold, in code - are they the
same object with different names or completely different types of objects, with custom code?
- Should there be NPCs giving quests? If so, how would you track quest status and what happens when
multiple players try to do the same quest? Do you use instances or some other mechanism?
- etc.

### Characters

These are the objects controlled directly by Players.

- Can players have more than one Character active at a time or are they allowed to multi-play?
- How does a Player create their Character? A Character-creation screen? Answering questions?
Filling in a form?
- Do you want to use classes (like "Thief", "Warrior" etc) or some other system, like Skill-based?
- How do you implement different "classes" or "races"? Are they separate types of objects or do you
simply load different stats on a basic object depending on what the Player wants?
- If a Character can hide in a room, what skill will decide if they are detected?
- What skill allows a Character to wield a weapon and hit? Do they need a special skill to wield a
chair rather than a sword?
- Does a Character need a Strength attribute to tell how much they can carry or which objects they
can smash?
- What does the skill tree look like? Can a Character gain experience to improve? By killing
enemies? Solving quests? By roleplaying?
- etc.

A MUD's a lot more involved than you would think and these things hang together in a complex web. It
can easily become overwhelming and it's tempting to want *all* functionality right out of the door.
Try to identify the basic things that "make" your game and focus *only* on them for your first
release. Make a list. Keep future expansions in mind but limit yourself.

## Coding (step 2)

This is the actual work of creating the "game" part of your game. Many "game-designer" types tend to
gloss over this bit and jump directly to **World Building**. Vice versa, many "game-coder" types
tend to jump directly to this part without doing the **Planning** first. Neither way is good and
*will* lead to you having to redo all your hard work at least once, probably more.

Evennia's [Evennia Component overview](../../../Components/Components-Overview) tries to help you with this bit of development. We
also have a slew of [Tutorials](../../Howto-Overview) with worked examples. Evennia tries hard to make this
part easier for you, but there is no way around the fact that if you want anything but a very basic
Talker-type game you *will* have to bite the bullet and code your game (or find a coder willing to
do it for you).

Even if you won't code anything yourself, as a designer you need to at least understand the basic
paradigms of Evennia, such as [Objects](../../../Components/Objects), 
[Commands](../../../Components/Commands) and [Scripts](../../../Components/Scripts) and
how they hang together. We recommend you go through the [Tutorial World](../Part1/Tutorial-World-Introduction) in detail (as well as glancing at its code) to get at least a feel for what is
involved behind the scenes. You could also look through the tutorial for 
[building a game from scratch](../Part3/Tutorial-for-basic-MUSH-like-game).

During Coding you look back at the things you wanted during the **Planning** phase and try to
implement them. Don't be shy to update your plans if you find things easier/harder than you thought.
The earlier you revise problems, the easier they will be to fix.

A good idea is to host your code online (publicly or privately) using version control. Not only will
this make it easy for multiple coders to collaborate (and have a bug-tracker etc), it also means
your work is backed up at all times. The [Version Control](../../../Coding/Version-Control) tutorial has
instructions for setting up a sane developer environment with proper version control.

### "Tech Demo" Building

This is an integral part of your Coding. It might seem obvious to experienced coders, but it cannot
be emphasized enough that you should *test things on a small scale* before putting your untested
code into a large game-world. The earlier you test, the easier and cheaper it will be to fix bugs
and even rework things that didn't work out the way you thought they would. You might even have to
go back to the **Planning** phase if your ideas can't handle their meet with reality.

This means building singular in-game examples. Make one room and one object of each important type
and test so they work correctly in isolation. Then add more if they are supposed to interact with
each other in some way. Build a small series of rooms to test how mobs move around ... and so on. In
short, a test-bed for your growing code. It should be done gradually until you have a fully
functioning (if not guaranteed bug-free) miniature tech demo that shows *all* the features you want
in the first release of your game. There does not need to be any game play or even a theme to your
tests, this is only for you and your co-coders to see. The more testing you do on this small scale,
the less headaches you will have in the next phase.

## World Building (step 3) 

Up until this point we've only had a few tech-demo objects in the database. This step is the act of
populating the database with a larger, thematic world. Too many would-be developers jump to this
stage too soon (skipping the **Coding** or even **Planning** stages).  What if the rooms you build
now doesn't include all the nice weather messages the code grows to support? Or the way you store
data changes under the hood? Your building work would at best require some rework and at worst you
would have to redo the whole thing. And whereas Evennia's typeclass system does allow you to edit
the properties of existing objects, some hooks are only called at object creation ...  Suffice to
say you are in for a *lot* of unnecessary work if you build stuff en masse without having the
underlying code systems in some reasonable shape first.

So before starting to build, the "game" bit (**Coding** + **Testing**) should be more or less
**complete**, *at least to the level of your initial release*.

Before starting to build, you should also plan ahead again. Make sure it is clear to yourself and
your eventual builders just which parts of the world you want for your initial release. Establish
for everyone which style, quality and level of detail you expect. Your goal should *not* be to
complete your entire world in one go. You want just enough to make the game's "feel" come across.
You want a minimal but functioning world where the intended game play can be tested and roughly
balanced. You can always add new areas later.

During building you get free and extensive testing of whatever custom build commands and systems you
have made at this point. Since Building often involves different people than those Coding, you also
get a chance to hear if some things are hard to understand or non-intuitive.  Make sure to respond
to this feedback.


## Alpha Release

As mentioned, don't hold onto your world more than necessary. *Get it out there* with a huge *Alpha*
flag and let people try it! Call upon your alpha-players to try everything - they *will* find ways
to break your game in ways that you never could have imagined. In Alpha you might be best off to
focus on inviting friends and maybe other MUD developers, people who you can pester to give proper
feedback and bug reports (there *will* be bugs, there is no way around it). Follow the quick
instructions for [Online Setup](../../../Setup/Online-Setup) to make your game visible online. If you hadn't
already, make sure to put up your game on the [Evennia game index](http://games.evennia.com/) so
people know it's in the works (actually, even pre-alpha games are allowed in the index so don't be
shy)!

## Beta Release/Perpetual Beta

Once things stabilize in Alpha you can move to *Beta* and let more people in. Many MUDs are in
[perpetual beta](http://en.wikipedia.org/wiki/Perpetual_beta), meaning they are never considered
"finished", but just repeat the cycle of Planning, Coding, Testing and Building over and over as new
features get implemented or Players come with suggestions. As the game designer it is now up to you
to gradually perfect your vision.

## Congratulate yourself! 

You are worthy of a celebration since at this point you have joined the small, exclusive crowd who
have made their dream game a reality!