[prev lesson](Game-Planningd) | [next lesson](Unimplemented)

# Planning our tutorial game

Using the general plan from last lesson we'll now establish what kind of game we want to create for this tutorial.
Remembering that we need to keep the scope down, let's establish some parameters. Note that for your own 
game you don't _need_ to agree/adopt any of these. Many game-types need more or much less than this. 
But this makes for good, instructive examples.

- We want a small game we can play ourselves for fun, but which could in principle be expanded 
  to something more later.
- Let's go with a fantasy theme, it's well understood.
- We'll use some existing, simple RPG system. 
- We want to be able to create and customize a character of our own. 
- We want the tools to roleplay with other players. 
- We don't want to have to rely on a Game master to resolve things, but will rely on code for skill resolution
  and combat.
- We want monsters to fight and NPCs we can talk to. So some sort of AI. 
- We want to be able to buy and sell stuff. 
- We want some sort of crafting system.
- We want some sort of quest system. 

Let's answer the questions from the previous lesson and discuss some of the possibilities. 

### Administration 

#### Should your game rules be enforced by coded systems by human game masters?



We want to have a game that doesn't require human game masters to run. Human GMs are great but only when they are available. 
  
- _What is the staff hierarchy in your game? Is vanilla Evennia roles enough or do you need something else?_ -
  The default hierarchy should be enough: `Player` - `Player Helper` - `Builder` - `Admin` - `Developer`.
- _Should characters be able to send mail (IC/OOC?) to each other in-game?_ - Why not! 
- _Should players be able to post out-of-characters on channels and via other means like bulletin-boards?_ - We will
  not be implementing a bulletin-board in this tutorial, but we'll allow use of the default channels coming 
  with Evennia.
  

### Building

- _How will the world be built? Traditionally (from in-game with build-commands) or externally (by batchcmds/code 
  or directly with custom code)?_ - We will show examples of a few differnt ways, but we'll build the brunt of 
  things using Evennia's Batchcode system.  
- _Can only privileged Builders create things or should regular players also have limited build-capability?_ - We 
  will only allow privileged builders to modify the world. The exception is crafting, where we will allow players to
  to use in-game commands to create specific, prescribed objects from recipes. 

### Systems

- _What are the game mechanics? How do you decide if an action succeeds or fails?_ - We will let the system decide this
 from case to case by passing questions to a rule module we'll create. 
- _Do you base your game off an existing RPG system or make up your own?_ - We will make use of 
 [Open Adventure](http://www.geekguild.com/openadventure/), an 'old school' RRG-system that is available for 
 free under the Creative Commons license. We'll only use a subset of the rules from the blue "basic" book. 
- _How does the character-generation work? Walk from room-to-room? A menu?_ - We'll be fancy and do this as a
 as a menu, it's all the rage. 
- _Does the flow of time matter in your game - does night and day change? What about seasons?_ - We'll find there
  is a contrib to add this, so we'll do so.
- _Do you want changing, global weather or should weather just be set manually in roleplay?_ - We'll not model
  weather in this tutorial. 
- _Do you want a coded world-economy or just a simple barter system? Or no formal economy at all?_ - We'll 
  allow for barter and buying/selling but we won't try to emulate a full economic system here. 
- _Do you have concepts like reputation and influence?_ - We will not have anything like that. 
- _Will your characters be known by their name or only by their physical appearance?_ - We can easily add this
  because we happen to know there is a contrib available for it, so we'll add it. 

### Rooms 

- _Is a simple room description enough or should the description be able to change (such as with time, by
light conditions, weather or season)?_ - We will make use of a contrib to allow us to change these things, so yes.
- _Should the room have different statuses? Can it have smells, sounds? Can it be affected by
dramatic weather, fire or magical effects? If so, how would this affect things in the room? Or are
these things something admins/game masters should handle manually?_ - We will not model any of this. 
- _Can objects be hidden in the room? Can a person hide in the room? How does the room display this?_ - We will
 not go into hiding and visibility in this tutorial. 

### Objects

- _How numerous are your objects? Do you want large loot-lists or are objects just role playing props
created on demand?_ - We will have a mix - some loot from monsters but also quest objects. 
- _If you use money, is each coin a separate object or do you just store a bank account value?_ - We'll use 
  coin as-objects. 
- _Do multiple similar objects form stacks and how are those stacks handled in that case?_ - We want objects 
  to to stack when they are put together. 
- _Does an object have weight or volume (so you cannot carry an infinite amount of them)?_ - Sure, why not.
- _Can objects be broken? Can they be repaired?_ - While interesting, we will not model breaking or repairs.
- _Is a weapon a specific type of object or can you fight with a chair or a flower too?_ - We can let all 
  objects have the ability to be used in an attack. 
- _NPCs/mobs are also objects. Should they just stand around or should they have some sort of AI?_ - We won't 
  be very sophisticated about it, but we want them to move around and have some rudimentary AI. 
- _Are NPCs and mobs different entities? How do they differ?_ - Monsters you fight and NPCs will be variations 
  of the same parent. 
- _Should there be NPCs giving quests? If so, how do you track Quest status?_ - We will design a simple quest system.

### Characters

- _Can players have more than one Character active at a time or are they allowed to multi-play?_ - We will
  allow 
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




[prev lesson](Game-Planningd) | [next lesson](Unimplemented)
