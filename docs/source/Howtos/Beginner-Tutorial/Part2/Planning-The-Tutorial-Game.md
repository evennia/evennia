# Planning our tutorial game

Using the general plan from last lesson we'll now establish what kind of game we want to create for this tutorial.  We'll call it ... _EvAdventure_.
Remembering that we need to keep the scope down, let's establish some parameters.

- We want EvAdventure be a small game we can play ourselves for fun, but which could in principle be expanded  to something more later.
- We want to have a clear game-loop, with clear goals.
- Let's go with a fantasy theme, it's well understood.
- We will use a small, existing tabletop RPG rule set ([Knave](https://www.drivethrurpg.com/product/250888/Knave), more info later)
- We want to be able to create and customize a character of our own.
- While not roleplay-focused, it should still be possible to socialize and to collaborate.
- We don't want to have to rely on a Game master to resolve things, but will rely on code for skill resolution and combat.
- We want monsters to fight and NPCs we can talk to. So some sort of AI.
- We want some sort of quest system and merchants to buy stuff from.


## Game concept 

With these points in mind, here's a quick blurb for our game:

_Recently, the nearby village discovered that the old abandoned well contained a dark secret. The bottom of the well led to a previously undiscovered dungeon of ever shifting passages. No one knew why it was there or what its purpose was, but local rumors abound. The first adventurer that went down didn't come back. The second ... brought back a handful of glittering riches._

_Now the rush is on - there's a dungeon to explore and coin to earn. Knaves, cutthroats, adventurers and maybe even a hero or two are coming from all over the realm to challenge whatever lurks at the bottom of that well._

_Local merchants and opportunists have seen a chance for profit. A camp of tents has sprung up around the old well, providing food and drink, equipment, entertainment and rumors for a price. It's a festival to enjoy before paying the entrance fee for dropping down the well to find your fate among the shadows below ..._

Our game will consist of two main game modes - above ground and below. The player starts above ground and is expected to do 'expeditions' into the dark. The design goal is for them to be forced back up again when their health, equipment and luck is about to run out.
- Above, in the "dungeon festival", the player can restock and heal up, buy things and do a small set of quests. It's the only place where the characters can sleep and fully heal. They also need to spend coin here to gain XP and levels. This is a place for players to socialize and RP. There is no combat above ground except for an optional spot for non-lethal PvP. 
- Below is the mysterious dungeon. This is a procedurally generated set of rooms. Players can collaborate if they go down the well together, they will not be able to run into each other otherwise (so this works as an instance). Each room generally presents some challenge (normally a battle). Pushing deeper is more dangerous but can grant greater rewards. While the rooms could in theory go on forever, there should be a boss encounter once a player reaches deep enough.

Here's an overview of the topside camp for inspiration (quickly thrown together in the free version of [Inkarnate](https://inkarnate.com/)). We'll explore how to break this up into "rooms" (locations) when we get to creating the game world later.

![Last Step Camp](../../../_static/images/starting_tutorial/Dungeon_Merchant_Camp.jpg)

For the rest of this lesson we'll answer and reason around the specific questions posed in the previous [Game Planning](./Game-Planning.md) lesson.

## Administration

### Should your game rules be enforced by coded systems by human game masters?

Generally, the more work you expect human staffers/GMs to do, the less your code needs to work. To support GMs you'd need to design commands to support GM-specific actions and the type of game-mastering you want them to do. You may need to expand communication channels so you can easily talk to groups people in private and split off gaming groups from each other. RPG rules could be as simple
as the GM sitting with the rule books and using a dice-roller for visibility.

GM:ing is work-intensive however, and even the most skilled and enthusiastic GM can't be awake all hours of the day to serve an international player base. The computer never needs sleep, so having the ability for players to "self-serve" their RP itch when no GMs are around is a good idea even for the most GM-heavy games.

On the other side of the spectrum are games with no GMs at all; all gameplay are driven either by the computer or by the interactions between players. Such games still need an active staff, but nowhere as much active involvement. Allowing for solo-play with the computer also allows players to have fun when the number of active
players is low.

**EvAdventure Answer:**

We want EvAdventure to work entirely without depending on human GMs. That said, there'd be nothing stopping a GM from stepping in and run an adventure for some players should they want to.

### What is the staff hierarchy in your game? Is vanilla Evennia roles enough or do you need something else?

The default hierarchy is

- `Player`  - regular players
- `Player Helper`  - can create/edit help entries
- `Builder` - can use build commands
- `Admin` - can kick and ban accounts
- `Developer` - full access, usually also trusted with server access

There is also the _superuser_, the "owner" of the game you create when you first set up your database. This user
goes outside the regular hierarchy and should usually only.

**EvAdventure Answer**

We are okay with keeping the default permission structure for our game.

### Should players be able to post out-of-characters on channels and via other means like bulletin-boards?

Evennia's _Channels_ are by default only available between _Accounts_. That is, for players to communicate with each
other. By default, the `public` channel is created for general discourse.
Channels are logged to a file and when you are coming back to the game you can view the history of a channel in case you missed something.

    > public Hello world!
    [Public] MyName: Hello world!

But Channels can also be set up to work between Characters instead of Accounts. This would mean the channels would have an in-game meaning:

- Members of a guild could be linked telepathically.
- Survivors of the apocalypse can communicate over walkie-talkies.
- Radio stations you can tune into or have to discover.

_Bulletin boards_ are a sort of in-game forum where posts are made publicly or privately. Contrary to a channel, the messages are usually stored and are grouped into topics with replies. Evennia has no default bulletin-board system.

**EvAdventure Answer**

In EvAdventure we will just use the default inter-account channels. We will also not be implementing any bulletin boards; instead the merchant NPCs will act as quest givers.

## Building

### How will the world be built?

There are two main ways to handle this:
- Traditionally, from in-game with build-commands:  This means builders creating content in their game   client. This has the advantage of not requiring Python skills nor server access. This can often be a quite  intuitive way to build since you are sort-of walking around in your creation as you build it. However, the  developer (you) must make sure to provide build-commands that are flexible enough for builders to be able to  create the content you want for your game.
- Externally (by batchcmds): Evennia's `batchcmd` takes a text file with Evennia Commands and executes them   in sequence. This allows the build process to be repeated and applied quickly to a new database during development.
  It also allows builders to use proper text-editing tools rather than writing things line-by-line in their clients. The drawback is that for their changes to go live they either need server access or they need to send their batchcode to the game administrator so they can apply the changes. Or use version control.
- Externally (with batchcode or custom code): This is the "professional game development" approach. This gives the   builders maximum power by creating the content in Python using Evennia primitives. The `batchcode` processor
  allows Evennia to apply and re-apply build-scripts that are raw Python modules. Again, this would require the   builder to have server access or to use version control to share their work with the rest of the development team.

**EvAdventure Answer**

For EvAdventure, we will build the above-ground part of the game world using batch-scripts. The world below-ground we will build procedurally, using raw code.

### Can only privileged Builders create things or should regular players also have limited build-capability?

In some game styles, players have the ability to create objects and even script them. While giving regular users the ability to create objects with in-built commands is easy and safe, actual code-creation (aka _softcode_ ) is not something Evennia supports natively. 

Regular, untrusted users should never be allowed to execute raw Python
code (such as what you can do with the `py` command). You can
[read more about Evennia's stance on softcode here](../../../Concepts/Soft-Code.md). If you want users to do limited scripting, it's suggested that this is accomplished by adding more powerful build-commands for them to use.

**EvAdventure Answer**

For our tutorial-game, we will only allow privileged builders and admins to modify the world. 

## Systems

### Do you base your game off an existing RPG system or make up your own?

There is a plethora of options out there, and what you choose depends on the game you want. It can be tempting to grab a short free-form ruleset, but remember that the computer does not have any intuitiion or common sense to interpret the rules like a human GM could. Conversely, if you pick a very 'crunchy' game system, with detailed simulation of the real world, remember that you'll need to actually _code_ all those exceptions and tables yourself. 

For speediest development, what you want is a game with a _consolidated_ resolution mechanic - one you can code once and then use in a lot of situations. But you still want enough rules to help telling the computer how various situations should be resolved (combat is the most common system that needs such structure). 

**EvAdventure Answer**

For this tutorial, we will make use of [Knave](https://www.drivethrurpg.com/product/250888/Knave), a very light [OSR](https://en.wikipedia.org/wiki/Old_School_Renaissance) ruleset by Ben Milton. It's only a few pages long but highly compatible with old-school D&D games. It's consolidates all rules around a few opposed d20 rolls and includes clear rules for combat, inventory, equipment and so on. Since _Knave_ is a tabletop RPG, we will have to do some minor changes here and there to fit it to the computer medium.

_Knave_ is available under a Creative Commons Attributions 4.0 License, meaning it can be used for derivative work (even commercially). The above link allows you to purchase the PDF and supporting the author. Alternatively you can find unofficial fan releases of the rules [on this page](https://dungeonsandpossums.com/2020/04/some-great-knave-rpg-resources/). 


### What are the game mechanics? How do you decide if an action succeeds or fails?

This follows from the RPG system decided upon in the previous question.

**EvAdventure Answer**

_Knave_ gives every character a set of six traditional stats: Strength, Intelligence, Dexterity, Constitution, Intelligence, Wisdom and Charisma. Each has a value from +1 to +10. To find its "Defense" value, you add 10. 

    You have Strength +1. Your Strength-Defense is 10 + 1 = 11

To make a check, say an arm-wrestling challenge you roll a twenty-sided die (d20) and add your stat. You have to roll higher than the opponents defense for that stat.

    I have Strength +1, my opponent has a Strength of +2. To beat them in arm wrestling I must roll d20 + 1 and hope to get higher than 12, which is their Strength defense (10 + 2). 

If you attack someone you do the same, except you roll against their `Armor` defense. If you rolled higher, you roll for how much damage you do (depends on your weapon).
You can have _advantage_ or _disadvantage_ on a roll. This means rolling 2d20 and picking highest or lowest value. 

In Knave, combat is turn-based. In our implementation we'll also play turn-based, but we'll resolve everything _simultaneously_. This changes _Knave_'s feel quite a bit, but is a case where the computer can do things not practical to do when playing around a table.

There are also a few tables we'll need to implement. For example, if you lose all health, there's a one-in-six chance you'll die outright. We'll keep this perma-death aspect, but make it very easy to start a new character and jump back in.

> In this tutorial we will not add opportunities to make use of all of the character stats, making some, like strength, intelligence and dexterity more useful than others. In a full game, one would want to expand so a user can utilize all of their character's strengths.

### Does the flow of time matter in your game - does night and day change? What about seasons?

Most commonly, game-time runs faster than real-world time. There are
a few advantages with this:

- Unlike in a single-player game, you can't fast-forward time in a multiplayer game if you are waiting for something, like NPC shops opening. 
- Healing and other things that we know takes time will go faster while still being reasonably 'realistic'.

The main drawback is for games with slower roleplay pace. While you are having a thoughtful roleplaying scene over dinner, the game world reports that two days have passed. Having a slower game time than real-time is a less common, but possible solution for such games.

It is however _not_ recommended to let game-time exactly equal the speed of real time. The reason for this is that people will join your game from all around the world, and they will often only be able to play at particular times of their day. With a game-time drifting relative real-time, everyone will eventually be able to experience both day and night in the game.

**EvAdventure Answer**

The passage of time will have no impact on our particular game example, so we'll go with Evennia's default, which is that the game-time runs two times faster than real time.

### Do you want changing, global weather or should weather just be set manually in roleplay?

A weather system is a good example of a game-global system that affects a subset of game entities (outdoor rooms). 

**EvAdventure Answer**

We'll not change the weather, but will add some random messages to echo through
the game world at random intervals just to show the principle.

### Do you want a coded world-economy or just a simple barter system? Or no formal economy at all?
This is a big question and depends on how deep and interconnected the virtual transactions are that are happening in the game. Shop prices could rice and drop due to supply and demand, supply chains could involve crafting and production. One also could consider adding money sinks and manipulate the in-game market to combat inflation. 

The [Barter](../../../Contribs/Contrib-Barter.md) contrib provides a full interface for trading with another player in a safe way.

**EvAdventure Answer**

We will not deal with any of this complexity. We will allow for players to buy from npc sellers and players will be able to trade using the normal `give` command.

### Do you have concepts like reputation and influence?

These are useful things for a more social-interaction heavy game. 

**EvAdventure Answer**

We will not include them for this tutorial. Adding the Barter contrib is simple though. 

### Will your characters be known by their name or only by their physical appearance?

This is a common thing in RP-heavy games. Others will only see you as "The tall woman" until you introduce yourself and they 'recognize' you with a name. Linked to this is the concept of more complex emoting and posing.

Implementing such a system is not trivial, but the [RPsystem](../../../Contribs/Contrib-RPSystem.md) Evennia contrib offers a ready system with everything needed for free emoting, recognizing people by their appearance and more.

**EvAdventure Answer**

We will not use any special RP systems for this tutorial. Adding the RPSystem contrib is a good extra expansion though!

## Rooms

### Is a simple room description enough or should the description be able to change?

Changing room descriptions for day and night, winder and summer is actually quite easy to do, but looks very impressive. We happen to know there is also a contrib that helps with this, so we'll show how to include that.

There is an [Extended Room](../../../Contribs/Contrib-Extended-Room.md) contrib that adds a Room type that is aware of the time-of-day as well as seasonal variations. 

**EvAdventure Answer**

We will stick to a normal room in this tutorial and let the world be in a perpetual daylight. Making Rooms into ExtendedRooms is not hard though. 

### Should the room have different statuses?

One could picture weather making outdoor rooms wet, cold or burnt. In rain, bow strings could get wet and fireballs fizz out. In a hot room, characters could require drinking more water, or even take damage if not finding shelter.

**EvAdventure Answer**

For the above-ground we need to be able to disable combat all rooms except for the PvP location. We also need to consider how to auto-generate the rooms under ground. So we probably will need some statuses to control that. 

Since each room under ground should present some sort of challenge, we may need a few different room types different from the above-ground Rooms.

### Can objects be hidden in the room? Can a person hide in the room?

This ties into if you have hide/stealth mechanics. Maybe you could evesdrop or attack out of hiding. 

**EvAdventure Answer**

We will not model hiding and stealth. This will be a game of honorable face-to-face conflict.

## Objects

### How numerous are your objects? Do you want large loot-lists or are objects just role playing props?

This also depends on the type of game. In a pure freeform RPG, most objects may be 'imaginary' and just appearing in fiction. If the game is more coded, you want objects with properties that the computer can measure, track and calculate. In many roleplaying-heavy games, you find a mixture of the two, with players imagining items for roleplaying scenes, but only using 'real' objects to resolve conflicts. 

**EvAdventure Answer**

We will want objects with properties, like weapons and potions and such. Monsters should drop loot even though our list of objects will not be huge in this example game.

### Is each coin a separate object or do you just store a bank account value?

The advantage of having multiple items is that it can be more immersive. The drawback is that it's also very fiddly to deal with individual coins, especially if you have to deal with different currencies.

**EvAdventure Answer**

_Knave_ uses the "copper" as the base coin and so will we. Knave considers the weight of coin and one inventory "slot" can hold 100 coins. So we'll implement a "coin item" to represent many coins.

### Do multiple similar objects form stack and how are those stacks handled in that case?

If you drop two identical apples on the ground, Evennia will default to show this in the room as "two apples", but this is just a visual effect - there are still two apple-objects in the room. One could picture instead merging the two into a single object "X nr of apples" when you drop the apples. 

**EvAdventure Answer**

We will keep Evennia's default.

### Does an object have weight or volume (so you cannot carry an infinite amount of them)?

Limiting carrying weight is one way to stop players from hoarding. It also makes it more important for players to pick only the equipment they need. Carrying limits can easily come across as annoying to players though, so one needs to be careful with it.

**EvAdventure Answer**

_Knave_ limits your inventory to `Constitution + 10` "slots", where most items take up one slot and some large things, like armor, uses two. Small items (like rings) can fit 2-10 per slot and you can fit 100 coins in a slot.  This is an important game mechanic to limit players from hoarding. Especially since you need coin to level up.

### Can objects be broken? Can they be repaired?

Item breakage is very useful for a game economy; breaking weapons adds tactical considerations (if it's not too common, then it becomes annoying) and repairing things gives work for crafting players.

**EvAdventure Answer**

In _Knave_, items will break if you make a critical failure on using them (rolls a native 1 on d20). This means they lose a level of `quality` and once at 0, it's unusable. We will not allow players to repair, but we could allow merchants to repair items for a fee.

### Can you fight with a chair or a flower or must you use a special 'weapon' kind of thing?

Traditionally, only 'weapons' could be used to fight with. In the past this was a useful
simplification, but with Python classes and inheritance, it's not actually more work to just let all items in game work as a weapon in a pinch.

**EvAdventure Answer**

 Since _Knave_ deals with weapon lists and positions where items can be wielded, we will have a separate "Weapon" class for everything you can use for fighting. So, you won't be able to fight with a chair (unless we make it a weapon-inherited chair).

### Will characters be able to craft new objects?

Crafting is a common feature in multiplayer games. In code it usually means using a skill-check to combine base ingredients from a fixed recipe in order to create a new item. The classic example is to combine _leather straps_, a _hilt_, a _pommel_ and a _blade_ to make a new _sword_.

A full-fledged crafting system could require multiple levels of crafting, including having to mine for ore or cut down trees for wood.

Evennia's [Crafting](../../../Contribs/Contrib-Crafting.md) contrib adds a full crafting system to any game. It's based on [Tags](../../../Components/Tags.md), meaning that pretty much any object can be made usable for crafting, even used in an unexpected way. 

**EvAdventure Answer**

In our case we will not add any crafting in order to limit the scope of our game. Maybe NPCs will be able to repair items - for a cost?

### Should mobs/NPCs have some sort of AI?

As a rule, you should not hope to fool anyone into thinking your AI is actually intelligent. The best you will be able to do is to give interesting results and unless you have a side-gig as an AI researcher, users will likely not notice any practical difference between a simple state-machine and you spending a lot of time learning
how to train a neural net.

**EvAdventure Answer**

For this tutorial, we will show how to add a simple state-machine AI for monsters. NPCs will only be shop-keepers and quest-gives so they won't need any real AI to speak of.

### Are NPCs and mobs different entities? How do they differ?

"Mobs" or "mobiles" are things that move around. This is traditionally monsters you can fight with, but could also be city guards or the baker going to chat with the neighbor. Back in the day, they were often fundamentally different these days it's often easier to just make NPCs and mobs essentially the same thing.

**EvAdventure Answer**

In EvAdventure, Monsters and NPCs do very different things, so they will be different classes, sharing some code where possible.

### _Should there be NPCs giving quests? If so, how do you track Quest status?

Quests are a staple of many classic RPGs. 

**EvAdventure Answer**

We will design a simple quest system with some simple conditions for success, like carrying the right item or items back to the quest giver.

## Characters

### Can players have more than one Character active at a time or are they allowed to multi-play?

Since Evennia differentiates between `Sessions` (the client-connection to the game), `Accounts` and `Character`s, it natively supports multi-play. This is controlled by the `MULTISESSION_MODE` setting, which has a value from `0` (default) to `3`.

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

**EvAdventure Answer**

Due to the nature of _Knave_, characters are squishy and probably short-lived. So it makes little sense to keep a stable of them. We'll use use mode 0 or 1. 

### How does the character-generation work?

There are a few common ways to do character generation:

- Rooms. This is the traditional way. Each room's description tells you what command to use to modify   your character. When you are done you move to the next room. Only use this if you have another reason for   using a room, like having a training dummy to test skills on, for example.
- A Menu. The Evennia _EvMenu_ system allows you to code very flexible in-game menus without needing to walk   between rooms. You can both have a step-by-step menu (a 'wizard') or allow the user to jump between the
  steps as they please. This tends to be a lot easier for newcomers to understand since it doesn't require
  using custom commands they will likely never use again after this.
- Questions. A fun way to build a character is to answer a series of questions. This is usually implemented  with a sequential menu.

**EvAdventure Answer**

 Knave randomizes almost aspects of the Character generation. We'll use a menu to let the player add their name and sex as well as do the minor re-assignment of stats allowed by the rules.

### How do you implement different "classes" or "races"?

The way classes and races work in most RPGs is that they act as static 'templates' that inform which bonuses and special abilities you have. Much of this only comes into play during character generation or when leveling up. 

Often all we need to store on the Character is _which_ class and _which_ race they have; the actual logic can sit in Python code and just be looked up when we need it.

**EvAdventure Answer**

There are no races and no classes in _Knave_. Every character is a human.

### If a Character can hide in a room, what skill will decide if they are detected?

Hiding means a few things.
- The Character should not appear in the room's description / character list
- Others hould not be able to interact with a hidden character. It'd be weird if you could do `attack <name>`
  or `look <name>` if the named character is in hiding.
- There must be a way for the person to come out of hiding, and probably for others to search or accidentally
  find the person (probably based on skill checks).
- The room will also need to be involved, maybe with some modifier as to how easy it is to hide in the room.

**EvAdventure Answer**

We will not be including a hide-mechanic in EvAdventure. 

### What does the skill tree look like? Can a Character gain experience to improve? By killing enemies? Solving quests? By roleplaying?

Gaining experience points (XP) and improving one's character is a staple of roleplaying games. There are many
ways to implement this:
- Gaining XP from kills is very common; it's easy to let a monster be 'worth' a certain number of XP and it's easy to tell when you should gain it.
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

**EvAdventure Answer**

 We will use an alternative rule in _Knave_, where Characters gain XP by spending coins they carry back from their adventures. The above-ground merchants will allow you to spend your coins and exchange them for XP 1:1. Each level costs 1000 coins. Every level you have `1d8  * new level` (minimum what you had before + 1) HP, and can raise 3 different ability scores by 1 (max +10). There are no skills in _Knave_, but the principle of increasing them would be the same.

### May player-characters attack each other (PvP)?

Deciding this affects the style of your entire game. PvP makes for exciting gameplay but it opens a whole new can of worms when it comes to "fairness". Players will usually accept dying to an overpowered NPC dragon. They will not be as accepting if they perceive another player as being overpowered. PvP means that you
have to be very careful to balance the game - all characters does not have to be exactly equal but they should all be viable to play a fun game with. 

PvP does not only mean combat though. Players can compete in all sorts of ways, including gaining influence in a political game or gaining market share when selling their crafted merchandise.

**EvAdventure Answer**

 We will allow PvP only in one place - a special Dueling location where players can play-fight each other for training and prestige, but not actually get killed. Otherwise no PvP will be allowed. Note that without a full Barter system in place (just regular `give`, it makes it theoretically easier for players to scam one another.

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

- It's impopular. Many players will just not play a game where they risk losing their beloved character  just like that.
- Many players say they like the _idea_ of permadeath except when it could happen to them.
- It can limit roleplaying freedom and make people refuse to take any risks.
- It may make players even more reluctant to play conflict-driving 'bad guys'.
- Game balance is much, much more important when results are "final". This escalates the severity of 'unfairness'
  a hundred-fold. Things like bugs or exploits can also lead to much more server effects.

For these reasons, it's very common to do hybrid systems. Some tried variations:

- NPCs cannot kill you, only other players can.
- Death is permanent, but it's difficult to actually die - you are much more likely to end up being severely hurt/incapacitated.
- You can pre-pay 'insurance' to magically/technologically avoid actually dying. Only if don't have insurance will
  you die permanently.
- Death just means harsh penalties, not actual death.
- When you die you can fight your way back to life from some sort of afterlife.
- You'll only die permanently if you as a player explicitly allows it.

**EvAdventure Answer**

In _Knave_, when you hit 0 HP, you roll on a death table, with a 1/6 chance of immediate death (otherwise you lose points in a random stat). We will offer an "Insurance" that allows you to resurrect if you carry enough coin on you when you die. If not, you are perma-dead and have to create a new character (which is easy and quick since it's mostly randomized). 

## Conclusions

Going through the questions has helped us get a little bit more of a feel for the game we want to do. There are many, many other things we could ask ourselves, but if we can cover these points we will be a good way towards a complete,
playable game!

In the last of these planning lessons we'll sketch out how these ideas will map to Evennia.