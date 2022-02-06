# Planning our tutorial game

Using the general plan from last lesson we'll now establish what kind of game we want to create for this tutorial.
Remembering that we need to keep the scope down, let's establish some parameters.
Note that for your own
game you don't _need_ to agree/adopt any of these. Many game-types need more or much less than this.
But this makes for good, instructive examples.

- To have something to refer to rather than just saying "our tutorial game" over and over, we'll
  name it ... _EvAdventure_.
- We want EvAdventure be a small game we can play ourselves for fun, but which could in principle be expanded
  to something more later.
- Let's go with a fantasy theme, it's well understood.
- We'll use some existing, simple RPG system.
- We want to be able to create and customize a character of our own.
- We want the tools to roleplay with other players.
- We don't want to have to rely on a Game master to resolve things, but will rely on code for skill resolution
  and combat.
- We want monsters to fight and NPCs we can talk to. So some sort of AI.
- We want to be able to buy and sell stuff, both with NPCs and other players.
- We want some sort of crafting system.
- We want some sort of quest system.

Let's answer the questions from the previous lesson and discuss some of the possibilities.

## Administration

### Should your game rules be enforced by coded systems by human game masters?

Generally, the more work you expect human staffers/GMs to do, the less your code needs to work. To
support GMs you'd need to design commands to support GM-specific actions and the type of game-mastering
you want them to do. You may need to expand communication channels so you can easily
talk to groups people in private and split off gaming groups from each other. RPG rules could be as simple
as the GM sitting with the rule books and using a dice-roller for visibility.

GM:ing is work-intensive however, and even the most skilled and enthusiastic GM can't be awake all hours
of the day to serve an international player base. The computer never needs sleep, so having the ability for
players to "self-serve" their RP itch when no GMs are around is a good idea even for the most GM-heavy games.

On the other side of the spectrum are games with no GMs at all; all gameplay are driven either by the computer
or by the interactions between players. Such games still need an active staff, but nowhere as much active
involvement. Allowing for solo-play with the computer also allows players to have fun when the number of active
players is low.

We want EvAdventure to work entirely without depending on human GMs. That said, there'd be nothing
stopping a GM from stepping in and run an adventure for some players should they want to.

### What is the staff hierarchy in your game? Is vanilla Evennia roles enough or do you need something else?

The default hierarchy is

- `Player`  - regular players
- `Player Helper`  - can create/edit help entries
- `Builder` - can use build commands
- `Admin` - can kick and ban accounts
- `Developer` - full access, usually also trusted with server access

There is also the _superuser_, the "owner" of the game you create when you first set up your database. This user
goes outside the regular hierarchy and should usually only.

We are okay with keeping this structure for our game.

### Should players be able to post out-of-characters on channels and via other means like bulletin-boards?

Evennia's _Channels_ are by default only available between _Accounts_. That is, for players to communicate with each
other. By default, the `public` channel is created for general discourse.
Channels are logged to a file and when you are coming back to the game you can view the history of a channel
in case you missed something.

    > public Hello world!
    [Public] MyName: Hello world!

But Channels can also be set up to work between Characters instead of Accounts. This would mean the channels
would have an in-game meaning:

- Members of a guild could be linked telepathically.
- Survivors of the apocalypse can communicate over walkie-talkies.
- Radio stations you can tune into or have to discover.

_Bulletin boards_ are a sort of in-game forum where posts are made publicly or privately. Contrary to a channel,
the messages are usually stored and are grouped into topics with replies. Evennia has no default bulletin-board
system.

In EvAdventure we will just use the default inter-account channels. We will also not be implementing any
bulletin boards.

## Building

### How will the world be built?

There are two main ways to handle this:
- Traditionally, from in-game with build-commands:  This means builders creating content in their game
  client. This has the advantage of not requiring Python skills nor server access. This can often be a quite
  intuitive way to build since you are sort-of walking around in your creation as you build it. However, the
  developer (you) must make sure to provide build-commands that are flexible enough for builders to be able to
  create the content you want for your game.
- Externally (by batchcmds): Evennia's `batchcmd` takes a text file with Evennia Commands and executes them
  in sequence. This allows the build process to be repeated and applied quickly to a new database during development.
  It also allows builders to use proper text-editing tools rather than writing things line-by-line in their clients.
  The drawback is that for their changes to go live they either need server access or they need to send their
  batchcode to the game administrator so they can apply the changes. Or use version control.
- Externally (with batchcode or custom code): This is the "professional game development" approach. This gives the
  builders maximum power by creating the content in Python using Evennia primitives. The `batchcode` processor
  allows Evennia to apply and re-apply build-scripts that are raw Python modules. Again, this would require the
  builder to have server access or to use version control to share their work with the rest of the development team.

In this tutorial, we will show examples of all these ways, but since we don't have a team of builders we'll
build the brunt of things using Evennia's Batchcode system.

### Can only privileged Builders create things or should regular players also have limited build-capability?

In some game styles, players have the ability to create objects and even script them. While giving regular users
the ability to create objects with in-built commands is easy and safe, actual code-creation (aka _softcode_ ) is
not something Evennia supports natively. Regular, untrusted users should never be allowed to execute raw Python
code (such as what you can do with the `py` command). You can
[read more about Evennia's stance on softcode here](../../../Concepts/Soft-Code.md). If you want users to do limited scripting,
it's suggested that this is accomplished by adding more powerful build-commands for them to use.

For our tutorial-game, we will only allow privileged builders to modify the world. The exception is crafting,
which we will limit to repairing broken items by combining them with other repair-related items.

## Systems

### Do you base your game off an existing RPG system or make up your own?

We will make use of [Open Adventure](http://www.geekguild.com/openadventure/), a simple 'old school' RPG-system
that is available for free under the Creative Commons license. We'll only use a subset of the rules from
the blue "basic" book. For the sake of keeping down the length of this tutorial we will limit what features
we will include:

- Only two 'archetypes' (classes) - Arcanist (wizard) and Warrior, these are examples of two different play
  styles.
- Two races only (dwarves and elves), to show off how to implement races and race bonuses.
- No extra features of the races/archetypes such as foci and special feats. While these are good for fleshing
  out a character, these will work the same as other bonuses and are thus not that instructive.
- We will add only a small number of items/weapons from the Open Adventure rulebook to show how it's done.

### What are the game mechanics? How do you decide if an action succeeds or fails?

Open Adventure's conflict resolution is based on adding a trait (such as Strength) with a random number in
order to beat a target. We will emulate this in code.

Having a "skill" means getting a bonus to that roll for a more narrow action.
Since the computer will need to know exactly what those skills are, we will add them more explicitly than
in the rules, but we will only add the minimum to show off the functionality we need.

### Does the flow of time matter in your game - does night and day change? What about seasons?

Most commonly, game-time runs faster than real-world time. There are
a few advantages with this:

- Unlike in a single-player game, you can't fast-forward time in a multiplayer game if you are waiting for
  something, like NPC shops opening.
- Healing and other things that we know takes time will go faster while still being reasonably 'realistic'.

The main drawback is for games with slower roleplay pace. While you are having a thoughtful roleplaying scene
over dinner, the game world reports that two days have passed. Having a slower game time than real-time is
a less common, but possible solution for such games.

It is however _not_ recommended to let game-time exactly equal the speed of real time. The reason for this
is that people will join your game from all around the world, and they will often only be able to play at
particular times of their day. With a game-time drifting relative real-time, everyone will eventually be
able to experience both day and night in the game.

For this tutorial-game we will go with Evennia's default, which is that the game-time runs two times faster
than real time.

### Do you want changing, global weather or should weather just be set manually in roleplay?

A weather system is a good example of a game-global system that affects a subset of game entities
(outdoor rooms). We will not be doing any advanced weather simulation, but we'll show how to do
random weather changes happening across the game world.

### Do you want a coded world-economy or just a simple barter system? Or no formal economy at all?

We will allow for money and barter/trade between NPCs/Players and Player/Player, but will not care about
inflation. A real economic simulation could do things like modify shop prices based on supply and demand.
We will not go down that rabbit hole.

### Do you have concepts like reputation and influence?

These are useful things for a more social-interaction heavy game. We will not include them for this
tutorial however.

### Will your characters be known by their name or only by their physical appearance?

This is a common thing in RP-heavy games. Others will only see you as "The tall woman" until you
introduce yourself and they 'recognize' you with a name. Linked to this is the concept of more complex
emoting and posing.

Adding such a system from scratch is complex and way beyond the scope of this tutorial. However,
there is an existing Evennia contrib that adds all of this functionality and more, so we will
include that and explain briefly how it works.

## Rooms

### Is a simple room description enough or should the description be able to change?

Changing room descriptions for day and night, winder and summer is actually quite easy to do, but looks
very impressive. We happen to know there is also a contrib that helps with this, so we'll show how to
include that.

### Should the room have different statuses?

We will have different weather in outdoor rooms, but this will not have any gameplay effect - bow strings
will not get wet and fireballs will not fizzle if it rains.

### Can objects be hidden in the room? Can a person hide in the room?

We will not model hiding and stealth. This will be a game of honorable face-to-face conflict.

## Objects

### How numerous are your objects? Do you want large loot-lists or are objects just role playing props?

Since we are not going for a pure freeform RPG here, we will want objects with properties, like weapons
and potions and such. Monsters should drop loot even though our list of objects will not be huge.

### Is each coin a separate object or do you just store a bank account value?

Since we will use bartering, placing coin objects on one side of the barter makes for a simple way to
handle payments. So we will use coins as-objects.

### Do multiple similar objects form stacks and how are those stacks handled in that case?

Since we'll use coins, it's practical to have them and other items stack together. While Evennia does not
do this natively, we will make use of a contrib for this.

### Does an object have weight or volume (so you cannot carry an infinite amount of them)?

Limiting carrying weight is one way to stop players from hoarding. It also makes it more important
for players to pick only the equipment they need. Carrying limits can easily come across as
annoying to players though, so one needs to be careful with it.

Open Adventure rules include weight limits, so we will include them.

### Can objects be broken? Can they be repaired?

Item breakage is very useful for a game economy; breaking weapons adds tactical considerations (if it's not
too common, then it becomes annoying) and repairing things gives work for crafting players.

We wanted a crafting system, so this is what we will limit it to - repairing items using some sort
of raw materials.

### Can you fight with a chair or a flower or must you use a special 'weapon' kind of thing?

Traditionally, only 'weapons' could be used to fight with. In the past this was a useful
simplification, but with Python classes and inheritance, it's not actually more work to just
let all items in game work as a weapon in a pinch.

So for our game we will let a character use any item they want as a weapon. The difference will
be that non-weapon items will do less damage and also break and become unusable much quicker.

### Will characters be able to craft new objects?

Crafting is a common feature in multiplayer games. In code it usually means using a skill-check
to combine base ingredients from a fixed recipe in order to create a new item. The classic
example is to combine _leather straps_, a _hilt_, a _pommel_ and a _blade_ to make a new _sword_.
A full-fledged crafting system could require multiple levels of crafting, including having to mine
for ore or cut down trees for wood.

In our case we will limit our crafting to repairing broken items. To show how it's done, we will require
extra items (a recipe) in order to facilitate the repairs.

### Should mobs/NPCs have some sort of AI?

A rule of adding Artificial Intelligence is that with today's technology you should not hope to fool
anyone with it anytime soon. Unless you have a side-gig as an AI researcher, users will likely
not notice any practical difference between a simple state-machine and you spending a lot of time learning
how to train a neural net.

For this tutorial, we will show how to add a simple state-machine for monsters. NPCs will only be
shop-keepers and quest-gives so they won't need any real AI to speak of.

### Are NPCs and mobs different entities? How do they differ?

"Mobs" or "mobiles" are things that move around. This is traditionally monsters you can fight with, but could
also be city guards or the baker going to chat with the neighbor. Back in the day, they were often fundamentally
different these days it's often easier to just make NPCs and mobs essentially the same thing.

In EvAdventure, both Monsters and NPCs will be the same type of thing; A monster could give you a quest
and an NPC might fight you as a mob as well as trade with you.

### _Should there be NPCs giving quests? If so, how do you track Quest status?

We will design a simple quest system to track the status of ongoing quests.

## Characters

### Can players have more than one Character active at a time or are they allowed to multi-play?

Since Evennia differentiates between `Sessions` (the client-connection to the game), `Accounts`
and `Character`s, it natively supports multi-play. This is controlled by the `MULTISESSION_MODE`
setting, which has a value from `0` (default) to `3`.

- `0`- One Character per Account and one Session per Account. This means that if you login to the same
  account from another client you'll be disconnected from the first. When creating a new account, a Character
  will be auto-created with the same name as your Account. This is default mode and mimics legacy code bases
  which had no separation between Account and Character.
- `1` - One Character per Account, multiple Sessions per Account. So you can connect simultaneously from
  multiple clients and see the same output in all of them.
- `2` - Multiple Characters per Account, one Session per Character. This will not auto-create a same-named
  Character for you, instead you get to create/choose between a number of Characters up to a max limit given by
  the `MAX_NR_CHARACTERS` setting (default 1). You can play them all simultaneously if you have multiple clients
  open, but only one client per Character.
- `3` - Multiple Characters per Account, Multiple Sessions per Character. This is like mode 2, except players
  can control each Character from multiple clients, seeing the same output from each Character.

We will go with a multi-role game, so we will use `MULTISESSION_MODE=3` for this tutorial.

### How does the character-generation work?

There are a few common ways to do character generation:

- Rooms. This is the traditional way. Each room's description tells you what command to use to modify
  your character. When you are done you move to the next room. Only use this if you have another reason for
  using a room, like having a training dummy to test skills on, for example.
- A Menu. The Evennia _EvMenu_ system allows you to code very flexible in-game menus without needing to walk
  between rooms. You can both have a step-by-step menu (a 'wizard') or allow the user to jump between the
  steps as they please. This tends to be a lot easier for newcomers to understand since it doesn't require
  using custom commands they will likely never use again after this.
- Questions. A fun way to build a character is to answer a series of questions. This is usually implemented
  with a sequential menu.

For the tutorial we will use a menu to let the user modify each section of their character sheet in any order
until they are happy.

### How do you implement different "classes" or "races"?

The way classes and races work in most RPGs (as well as in OpenAdventure) is that they act as static 'templates'
that inform which bonuses and special abilities you have. This means that all we need to store on the
Character is _which_ class and _which_ race they have; the actual logic can sit in Python code and just
be looked up when we need it.

### If a Character can hide in a room, what skill will decide if they are detected?

Hiding means a few things.
- The Character should not appear in the room's description / character list
- Others hould not be able to interact with a hidden character. It'd be weird if you could do `attack <name>`
  or `look <name>` if the named character is in hiding.
- There must be a way for the person to come out of hiding, and probably for others to search or accidentally
  find the person (probably based on skill checks).
- The room will also need to be involved, maybe with some modifier as to how easy it is to hide in the room.

We will _not_ be including a hide-mechanic in EvAdventure though.

### What does the skill tree look like? Can a Character gain experience to improve? By killing enemies? Solving quests? By roleplaying?

Gaining experience points (XP) and improving one's character is a staple of roleplaying games. There are many
ways to implement this:
- Gaining XP from kills is very common; it's easy to let a monster be 'worth' a certain number of XP and it's
  easy to tell when you should gain it.
- Gaining XP from quests is the same - each quest is 'worth' XP and you get them when completing the test.
- Gaining XP from roleplay is harder to define. Different games have tried a lot of different ways to do this:
  - XP from being online - just being online gains you XP. This inflates player numbers but many players may
     just be lurking and not be actually playing the game at any given time.
  - XP from roleplaying scenes - you gain XP according to some algorithm analyzing your emotes for 'quality',
    how often you post, how long your emotes are etc.
  - XP from actions - you gain XP when doing things, anything. Maybe your XP is even specific to each action, so
    you gain XP only for running when you run, XP for your axe skill when you fight with an axe etc.
  - XP from fails - you only gain XP when failing rolls.
  - XP from other players - other players can award you XP for good RP.

For EvAdventure we will use Open Adventure's rules for XP, which will be driven by kills and quest successes.

### May player-characters attack each other (PvP)?

Deciding this affects the style of your entire game. PvP makes for exciting gameplay but it opens a whole new
can of worms when it comes to "fairness". Players will usually accept dying to an overpowered NPC dragon. They
will not be as accepting if they perceive another player is perceived as being overpowered. PvP means that you
have to be very careful to balance the game - all characters does not have to be exactly equal but they should
all be viable to play a fun game with. PvP does not only mean combat though. Players can compete in all sorts of ways, including gaining influence in
a political game or gaining market share when selling their crafted merchandise.

For the EvAdventure we will support both Player-vs-environment combat and turn-based PvP. We will allow players
to barter with each other (so potentially scam others?) but that's the extent of it. We will focus on showing
off techniques and will not focus on making a balanced game.

### What are the penalties of defeat? Permanent death? Quick respawn? Time in prison?

This is another big decision that strongly affects the mood and style of your game.

Perma-death means that once your character dies, it's gone and you have to make a new one.

- It allows for true heroism. If you genuinely risk losing your character of two years to fight the dragon,
  your triumph is an actual feat.
- It limits the old-timer dominance problem. If long-time players dies occationally, it will open things
  up for newcomers.
- It lowers inflation, since the hoarded resources of a dead character can be removed.
- It gives capital punishment genuine discouraging power.
- It's realistic.

Perma-death comes with some severe disadvantages however.

- It's impopular. Many players will just not play a game where they risk losing their beloved character
  just like that.
- Many players say they like the _idea_ of permadeath except when it could happen to them.
- It can limit roleplaying freedom and make people refuse to take any risks.
- It may make players even more reluctant to play conflict-driving 'bad guys'.
- Game balance is much, much more important when results are "final". This escalates the severity of 'unfairness'
  a hundred-fold. Things like bugs or exploits can also lead to much more server effects.

For these reasons, it's very common to do hybrid systems. Some tried variations:

- NPCs cannot kill you, only other players can.
- Death is permanent, but it's difficult to actually die - you are much more likely to end up being severely
hurt/incapacitated.
- You can pre-pay 'insurance' to magically/technologically avoid actually dying. Only if don't have insurance will
  you die permanently.
- Death just means harsh penalties, not actual death.
- When you die you can fight your way back to life from some sort of afterlife.
- You'll only die permanently if you as a player explicitly allows it.

For our tutorial-game we will not be messing with perma-death; instead your defeat will mean you will re-spawn
back at your home location with a fraction of your health.

## Conclusions

Going through the questions has helped us get a little bit more of a feel for the game we want to do. There are
many other things we could ask ourselves, but if we can cover these points we will be a good way towards a complete,
playable game!

Before starting to code in earnest a good coder should always do an inventory of all the stuff they _don't_ need
to code themselves. So in the next lesson we will check out what help we have from Evennia's _contribs_.

