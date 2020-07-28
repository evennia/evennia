[prev lesson](../Starting-Part2) | [next lesson](Planning-The-Tutorial-Game)

# On Planning a Game

This lesson will be less hands-on and more introspective. We'll go through some general things to think
about when planning your game. In the following lessons we'll apply this to plan out the tutorial-game we will
be making. 

Note that the suggestions on this page are just that - suggestions. Also, they are primarily aimed at a lone 
hobby designer or a small team developing a game in their free time. 

```important:: 

  Your first all overshadowing goal is to beat the odds and get **something** out the door! 
  Even if it's a scaled-down version of your dream game, lacking many "must-have" features! 

```

Remember: *99.99999% of all great game ideas never lead to a game*. Especially not to an online
game that people can actually play and enjoy. It's better to get your game out there and expand on it 
later than to code in isolation until you burn out, lose interest or your hard drive crashes.

- Keep the scope of your initial release down. Way down. 
- Start small, with an eye towards expansions later, after first release.
- If the suggestions here seems boring or a chore to you, do it your way instead. Everyone's different. 
- Keep having _fun_. You must keep your motivation up, whichever way works for _you_. 


## The steps 

Here are the rough steps towards your goal.

1. Planning 
2. Coding + Gradually building a tech-demo
3. Building the actual game world
4. Release
5. Celebrate

## Planning 

You need to have at least a rough idea about what you want to create. Some like a lot of planning, others 
do it more seat-of-the-pants style. Regardless, while _some_ planning is always good to do, it's common 
to have your plans change on you as you create your code prototypes. So don't get _too_ bogged down in 
the details out of the gate.

Many prospective game developers are very good at *parts* of this process, namely in defining what their 
world is "about": The theme, the world concept, cool monsters and so on. Such things are very important. But 
unfortunately, they are not enough to make your game. You need to figure out how to accomplish your ideas in 
Evennia.

Below are some questions to get you going. Depending on your game, there are many more possible questions you 
could ask yourself. 

### Administration 

- Should your game rules be enforced by coded systems by human game masters?
- What is the staff hierarchy in your game? Is vanilla Evennia roles enough or do you need something else?
- Should characters be able to send mail (IC/OOC?) to each other in-game?
- Should players be able to post out-of-characters on channels and via other means like bulletin-boards?

### Building

- How will the world be built? Traditionally (from in-game with build-commands) or externally (by batchcmds/code 
  or directly with custom code)? 
- Can only privileged Builders create things or should regular players also have limited build-capability?

### Systems

- What are the game mechanics? How do you decide if an action succeeds or fails? 
- Do you base your game off an existing RPG system or make up your own?
- How does the character-generation work? Walk from room-to-room? A menu? 
- Does the flow of time matter in your game - does night and day change? What about seasons?
- Do you want changing, global weather or should weather just be set manually in roleplay? 
- Do you want a coded world-economy or just a simple barter system? Or no formal economy at all?
- Do you have concepts like reputation and influence? 
- Will your characters be known by their name or only by their physical appearance? 

### Rooms 

- Is a simple room description enough or should the description be able to change (such as with time, by
light conditions, weather or season)?
- Should the room have different statuses? Can it have smells, sounds? Can it be affected by
dramatic weather, fire or magical effects? If so, how would this affect things in the room? Or are
these things something admins/game masters should handle manually?
- Can objects be hidden in the room? Can a person hide in the room? How does the room display this?

### Objects

- How numerous are your objects? Do you want large loot-lists or are objects just role playing props
created on demand?
- If you use money, is each coin a separate object or do you just store a bank account value?
- Do multiple similar objects form stacks and how are those stacks handled in that case?
- Does an object have weight or volume (so you cannot carry an infinite amount of them)?
- Can objects be broken? Can they be repaired?
- Is a weapon a specific type of object or can you fight with a chair or a flower too?
- NPCs/mobs are also objects. Should they just stand around or should they have some sort of AI?
- Are NPCs and mobs different entities? How do they differ? 
- Should there be NPCs giving quests? If so, how do you track Quest status? 

### Characters

- Can players have more than one Character active at a time or are they allowed to multi-play?
- How will Character creation work? Walking room-to-room? A menu? Answering questions? Filling in a form?
- How do you implement different "classes" or "races"? Are they separate types of objects or do you
simply load different stats on a basic object depending on what the Player wants?
- If a Character can hide in a room, what skill will decide if they are detected?
- What skill allows a Character to wield a weapon and hit? Do they need a special skill to wield a
chair rather than a sword?
- Does a Character need a Strength attribute to tell how much they can carry or which objects they
can smash?
- What does the skill tree look like? Can a Character gain experience to improve? By killing
enemies? Solving quests? By roleplaying?
- May player-characters attack each other (PvP)?
- What are the penalties of defeat? Permanent death? Quick respawn? Time in prison? 

A MUD's a lot more involved than you would think and these things hang together in a complex web. It
can easily become overwhelming and it's tempting to want *all* functionality right out of the door.
Try to identify the basic things that "make" your game and focus *only* on them for your first
release. Make a list. Keep future expansions in mind but limit yourself.

## Coding and Tech demo 

This is the actual work of creating the "game" part of your game. As you code and test systems you should 
build a little "tech demo" along the way. 

```sidebar:: Tech demo

    With "tech demo" we mean a small example of your code in-action: A room with a mob,
    a way to jump into and test character-creation etc. The tech demo need not be pretty, it's 
    there to test functionality. It's not the beginning of your game world (unless you find that
    to be more fun).

```

Try to avoid going wild with building a huge game world before you have a tech-demo showing off all parts 
you expect to have in the first version of your game. Otherwise you run the risk of having to redo it all
again. 

Evennia tries hard to make the coding easier for you, but there is no way around the fact that if you want 
anything but a basic chat room you *will* have to bite the bullet and code your game (or find a coder willing 
to do it for you).

> Even if you won't code anything yourself, as a designer you need to at least understand the basic
paradigms and components of Evennia. It's recommended you look over the rest of this Beginner Tutorial to learn
what tools you have available. 

During Coding you look back at the things you wanted during the **Planning** phase and try to
implement them. Don't be shy to update your plans if you find things easier/harder than you thought.
The earlier you revise problems, the easier they will be to fix.

A good idea is to host your code online using _version control_. Github.com offers free Private repos 
these days if you don't want the world to learn your secrets. Not only version control
make it easy for your team to collaborate, it also means
your work is backed up at all times. The page on [Version Control](../../../Coding/Version-Control) 
will help you to setting up a sane developer environment with proper version control.

## World Building

Up until this point we've only had a few tech-demo objects in the database. This step is the act of
populating the database with a larger, thematic world. Too many would-be developers jump to this
stage too soon (skipping the **Coding** or even **Planning** stages).  What if the rooms you build
now doesn't include all the nice weather messages the code grows to support? Or the way you store
data changes under the hood? Your building work would at best require some rework and at worst you
would have to redo the whole thing. You could be in for a *lot* of unnecessary work if you build stuff 
en masse without having the underlying code systems in some reasonable shape first.

So before starting to build, the "game" bit (**Coding** + **Testing**) should be more or less
**complete**, *at least to the level of your initial release*.

Make sure it is clear to yourself and your eventual builders just which parts of the world you want 
for your initial release. Establish for everyone which style, quality and level of detail you expect. 

Your goal should *not* be to complete your entire world in one go. You want just enough to make the 
game's "feel" come across. You want a minimal but functioning world where the intended game play can 
be tested and roughly balanced. You can always add new areas later.

During building you get free and extensive testing of whatever custom build commands and systems you
have made at this point. If Builders and coders are different people you also
get a chance to hear if some things are hard to understand or non-intuitive.  Make sure to respond
to this feedback.


## Alpha Release

As mentioned, don't hold onto your world more than necessary. *Get it out there* with a huge *Alpha*
flag and let people try it! 

Call upon your alpha-players to try everything - they *will* find ways to break your game in ways that 
you never could have imagined. In Alpha you might be best off to
focus on inviting friends and maybe other MUD developers, people who you can pester to give proper
feedback and bug reports (there *will* be bugs, there is no way around it). 

Follow the quick instructions for [Online Setup](../../../Setup/Online-Setup) to make your 
game visible online. 

If you hadn't already, make sure to put up your game on the 
[Evennia game index](http://games.evennia.com/) so people know it's in the works (actually, even 
pre-alpha games are allowed in the index so don't be shy)!

## Beta Release/Perpetual Beta

Once things stabilize in Alpha you can move to *Beta* and let more people in. Many MUDs are in
[perpetual beta](http://en.wikipedia.org/wiki/Perpetual_beta), meaning they are never considered
"finished", but just repeat the cycle of Planning, Coding, Testing and Building over and over as new
features get implemented or Players come with suggestions. As the game designer it is now up to you
to gradually perfect your vision.

## Congratulate yourself! 

You are worthy of a celebration since at this point you have joined the small, exclusive crowd who
have made their dream game a reality!

## Planning our tutorial game

In the next lesson we'll make use of these general points and try to plan out our tutorial game. 

[prev lesson](../Starting-Part2) | [next lesson](Planning-The-Tutorial-Game)