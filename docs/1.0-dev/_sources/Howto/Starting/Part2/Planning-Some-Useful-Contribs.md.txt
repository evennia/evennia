# Planning the use of some useful contribs

Evennia is deliberately bare-bones out of the box. The idea is that you should be as unrestricted as possible
in designing your game. This is why you can easily replace the few defaults we have and why we don't try to 
prescribe any major game systems on you. 

That said, Evennia _does_ offer some more game-opinionated _optional_ stuff. These are referred to as _Contribs_
and is an ever-growing treasure trove of code snippets, concepts and even full systems you can pick and choose 
from to use, tweak or take inspiration from when you make your game.

The [Contrib overview](../../../Contribs/Contrib-Overview) page gives the full list of the current roster of contributions. On
this page we will review a few contribs we will make use of for our game. We will do the actual installation
of them when we start coding in the next part of this tutorial series. While we will introduce them here, you
are wise to read their doc-strings yourself for the details.

This is the things we know we need:

- A barter system
- Character generation
- Some concept of wearing armor 
- The ability to roll dice
- Rooms with awareness of day, night and season
- Roleplaying with short-descs, poses and emotes
- Quests 
- Combat (with players and against monsters)

## Barter contrib 

[source](api:evennia.contrib.barter)

Reviewing this contrib suggests that it allows for safe trading between two parties. The basic principle
is that the parties puts up the stuff they want to sell and the system will guarantee that these systems are
exactly what is being offered. Both sides can modify their offers (bartering) until both mark themselves happy
with the deal. Only then the deal is sealed and the objects are exchanged automatically. Interestingly, this 
works just fine for money too - just put coin objects on one side of the transaction. 

    Sue > trade Tom: Hi, I have a necklace to sell; wanna trade for a healing potion?
    Tom > trade Sue: Hm, I could use a necklace ...
       <both accepted trade. Start trade> 
    Sue > offer necklace: This necklace is really worth it. 
    Tom > evaluate necklace:
       <Tom sees necklace stats>
    Tom > offer ration: I don't have a healing potion, but I'll trade you an iron ration!
    Sue > Hey, this is a nice necklace, I need more than a ration for it...
    Tom > offer ration, 10gold: Ok, a ration and 10 gold as well.
    Sue > accept: Ok, that sounds fair! 
    Tom > accept: Good! Nice doing business with you.
       <goods change hands automatically. Trade ends>    

Arguably, in a small game you are just fine to just talk to people and use `give` to do the exchange. The 
barter system guarantees trading safety if you don't trust your counterpart to try to give you the wrong thing or
to run away with your money. 

We will use the barter contrib as an optional feature for player-player bartering. More importantly we can 
add it for NPC shopkeepers and expand it with a little AI, which allows them to potentially trade in other 
things than boring gold coin.

## Character generation contrib

[source](api:evennia.contrib.chargen)

This contrib is an example module for creating characters. Since we will be using `MULTISESSION_MODE=3` we will
get a selection screen like this automatically. We also plan to use a proper menu to build our character, so 
we will _not_ be using this contrib.

## Clothing contrib

[source](api:evennia.contrib.clothing)

This contrib provides a full system primarily aimed at wearing clothes, but it could also work for armor. You wear
an object in a particular location and this will then be reflected in your character's description. You can 
also add roleplaying flavor: 

    > wear helmet slightly askew on her head
    look self
    Username is wearing a helmet slightly askew on her head.
 
By default there are no 'body locations' in this contrib, we will need to expand on it a little to make it useful
for things like armor. It's a good contrib to build from though, so that's what we'll do. 

## Dice contrib 

[source](api:evennia.contrib.dice)

The dice contrib presents a general dice roller to use in game.

    > roll 2d6
    Roll(s): 2 and 5. Total result is 7.
    > roll 1d100 + 2
    Roll(s): 43. Total result is 47
    > roll 1d20 > 12
    Roll(s): 7. Total result is 7. This is a failure (by 5)
    > roll/hidden 1d20 > 12
    Roll(s): 18. Total result is 17. This is a success (by 6). (not echoed)
    
The contrib also has a python function for producing these results in-code. However, while
we will emulate rolls for our rule system, we'll do this as simply as possible with Python's `random` 
module. 

So while this contrib is fun to have around for GMs or for players who want to get a random result 
or play a game, we will not need it for the core of our game.

## Extended room contrib 

[source](api:evennia.contrib.extended_room)

This is a custom Room typeclass that changes its description based on time of day and season.

For example, at night, in wintertime you could show the room as being dark and frost-covered while in daylight
at summer it could describe a flowering meadow. The description can also contain special markers, so 
`<morning> ... </morning>` would include text only visible at morning. 

The extended room also supports _details_, which are things to "look at" in the room without there having
to be a separate database object created for it. For example, a player in a church may do `look window` and
get a description of the windows without there needing to be an actual `window` object in the room.

Adding all those extra descriptions can be a lot of work, so they are optional; if not given the room works
like a normal room. 

The contrib is simple to add and provides a lot of optional flexibility, so we'll add it to our 
game, why not! 

## RP-System contrib

[source](api:evennia.contrib.rpsystem)

This contrib adds a full roleplaying subsystem to your game. It gives every character a "short-description"
(sdesc) that is what people will see when first meeting them. Let's say Tom has an sdesc "A tall man" and
Sue has the sdesc "A muscular, blonde woman"

    Tom > look 
    Tom: <room desc> ... You see: A muscular, blonde woman
    Tom > emote /me smiles to /muscular.
    Tom: Tom smiles to A muscular, blonde woman.
    Sue: A tall man smiles to Sue. 
    Tom > emote Leaning forward, /me says, "Well hello, what's yer name?"
    Tom: Leaning forward, Tom says, "Well hello..."
    Sue: Leaning forward, A tall man says, "Well hello, what's yer name?"
    Sue > emote /me grins. "I'm Angelica", she says. 
    Sue: Sue grins. "I'm Angelica", she says.
    Tom: A muscular, blonde woman grins. "I'm Angelica", she says.
    Tom > recog muscular Angelica
    Tom > emote /me nods to /angelica: "I have a message for you ..."
    Tom: Tom nods to Angelica: "I have a message for you ..."
    Sue: A tall man nods to Sue: "I have a message for you ..."

Above, Sue introduces herself as "Angelica" and Tom uses this info to `recoc` her as "Angelica" hereafter. He
could have `recoc`-ed her with whatever name he liked - it's only for his own benefit. There is no separate 
`say`, the spoken words are embedded in the emotes in quotes `"..."`. 

The RPSystem module also includes options for `poses`, which help to establish your position in the room
when others look at you. 

    Tom > pose stands by the bar, looking bored.
    Sue > look
    Sue: <room desc> ... A tall man stands by the bar, looking bored.
     
You can also wear a mask to hide your identity; your sdesc will then be changed to the sdesc of the mask, 
like `a person with a mask`. 

The RPSystem gives a lot of roleplaying power out of the box, so we will add it. There is also a separate 
[rplanguage](api:evennia.contrib.rplanguage) module that integrates with the spoken words in your emotes and garbles them if you don't understand
the language spoken. In order to restrict the scope we will not include languages for the tutorial game.


## Talking NPC contrib

[source](api:evennia.contrib.talking_npc)

This exemplifies an NPC with a menu-driven dialogue tree. We will not use this contrib explicitly, but it's 
good as inspiration for how we'll do quest-givers later. 

## Traits contrib

[source](api:evennia.contrib.traits)

An issue with dealing with roleplaying attributes like strength, dexterity, or skills like hunting, sword etc
is how to keep track of the values in the moment. Your strength may temporarily be buffed by a strength-potion. 
Your swordmanship may be worse because you are encumbered. And when you drink your health potion you must make
sure that those +20 health does not bring your health higher than its maximum. All this adds complexity.

The _Traits_ contrib consists of several types of objects to help track and manage values like this. When 
installed, the traits are accessed on a new handler `.traits`, for example 

    > py self.traits.hp.value
    100
    > py self.traits.hp -= 20    # getting hurt
    > py self.traits.hp.value
    80
    > py self.traits.hp.reset()  # drink a potion
    > py self.traits.hp.value
    100
    
A Trait is persistent (it uses an Attribute under the hood) and tracks changes, min/max and other things 
automatically. They can also be added together in various mathematical operations. 

The contrib introduces three main Trait-classes

- _Static_ traits for single values like str, dex, things that at most gets a modifier.
- _Counters_ is a value that never moves outside a given range, even with modifiers. For example a skill
  that can at most get a maximum amount of buff. Counters can also easily be _timed_ so that they decrease
  or increase with a certain rate per second. This could be good for a time-limited curse for example.
- _Gauge_ is like a fuel-gauge; it starts at a max value and then empties gradually. This is perfect for 
things like health, stamina and the like. Gauges can also change with a rate, which works well for the
effects of slow poisons and healing both.

```
> py self.traits.hp.value
100
> py self.traits.hp.rate = -1         # poisoned! 
> py self.traits.hp.ratetarget = 50   # stop at 50 hp
# Wait 30s
> py self.traits.hp.value
70
# Wait another 30s
> py self.traits.hp.value
50                                    # stopped at 50
> py self.traits.hp.rate = 0          # no more poison
> py self.traits.hp.rate = 5          # healing magic!
# wait 5s 
> pyself.traits.hp.value
75
```
  
Traits will be very practical to use for our character sheets. 

## Turnbattle contrib

[source](api:evennia.contrib.turnbattle)

This contrib consists of several implementations of a turn-based combat system, divivided into complexity:

- basic - initiative and turn order, attacks against defense values, damage.
- equip - considers weapons and armor, wielding and weapon accuracy.
- items - adds usable items with conditions and status effects
- magic - adds spellcasting system using MP. 
- range - adds abstract positioning and 1D movement to differentiate between melee and ranged attacks.

The turnbattle system is comprehensive, but it's meant as a base to start from rather than offer 
a complete system. It's also not built with _Traits_ in mind, so we will need to adjust it for that.

## Conclusions

With some contribs selected, we have pieces to build from and don't have to write everything from scratch.
We will need Quests and will likely need to do a bunch of work on Combat to adapt the combat contrib 
to our needs.

We will now move into actually starting to implement our tutorial game 
in the next part of this tutorial series. When doing this for yourself, remember to refer 
back to your planning and adjust it as you learn what works and what does not. 


