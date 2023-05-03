# Twitch Combat 

In this lesson we will build upon the basic combat framework we devised [in the previous lesson](./Beginner-Tutorial-Combat-Base.md).  

```shell
> attack troll 
  You attack the Troll! 

The Troll roars!

You attack the Troll with Sword: Roll vs armor(11):
 rolled 3 on d20 + strength(+1) vs 11 -> Fail
 
Troll attacks you with Terrible claws: Roll vs armor(12): 
 rolled 13 on d20 + strength(+3) vs 12 -> Success
 Troll hits you for 5 damage! 
 
You attack the Troll with Sword: Roll vs armor(11):
 rolled 14 on d20 + strength(+1) vs 11 -> Success
 You hit the Troll for 2 damage!
 
> look 
  A dark cave 
  
  Water is dripping from the ceiling. 
  
  Exits: south and west 
  Enemies: The Troll 
  --------- Combat Status ----------
  You (Wounded)  vs  Troll (Scraped)

> use potion 
  You prepare to use a healing potion! 
  
Troll attacks you with Terrible claws: Roll vs armor(12): 
 rolled 2 on d20 + strength(+3) vs 12 -> Fail
 
You use a healing potion. 
 You heal 4 damage. 
 
Troll attacks you with Terrible claws: Roll vs armor(12): 
 rolled 8 on d20 + strength(+3) vs 12 -> Fail
 
You attack the troll with Sword: Roll vs armor(11):
 rolled 20 on d20 + strength(+1) vs 11 -> Success (critical success)
 You critically hit the Troll for 8 damage! 
 The Troll falls to the ground, dead. 
 
The battle is over. You are still standing. 
```
> Documentation doesn't show colors.

With "Twitch" combat, we refer to a type of combat system that runs without any clear divisions of 'turns' (the opposite of [Turn-based combat](./Beginner-Tutorial-Combat-Turnbased.md)). It is inspired by the way combat worked in the old  [DikuMUD](https://en.wikipedia.org/wiki/DikuMUD) codebase, but is more flexible. 

```{sidebar} Differences to DIKU combat
In DIKU, all actions in combat happen on a _global_ 'tick' of, say 3 seconds. In our system, each combatant have their own 'tick' which is completely independent of each other. Now, in Evadventure, each combatant will tick at the same rate and thus mimic DIKU ... but they don't _have_ to. 
```

Basically, a user enters an action and after a certain time that action will execute (normally an attack). If they don't do anything, the attack will repeat over and over (with a random result) until the enemy or you is defeated. 

You can change up your strategy by performing other actions (like drinking a potion or cast a spell). You can also simply move to another room to 'flee' the combat (but the enemy may of course follow you)

