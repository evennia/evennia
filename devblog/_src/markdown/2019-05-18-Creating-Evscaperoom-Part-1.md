[![](https://2.bp.blogspot.com/-lfWBLhFKJjA/XOAWicyFg-I/AAAAAAAAKeM/sKHVm2iWCnAPjgvFRSuOiqe74HpDJDlEgCLcBGAs/s320/Screenshot%2Bfrom%2B2019-05-17%2B11-36-47.png)](https://2.bp.blogspot.com/-lfWBLhFKJjA/XOAWicyFg-I/AAAAAAAAKeM/sKHVm2iWCnAPjgvFRSuOiqe74HpDJDlEgCLcBGAs/s1600/Screenshot%2Bfrom%2B2019-05-17%2B11-36-47.png)

Over the last month (April-May 2019) I have taken part in the [Mud Coder's Guild Game Jam](https://itch.io/jam/enterthemud2) "Enter the (Multi-User) Dungeon". This year the theme for the jam was _One Room._  
  
The result was [Evscaperoom](http://experimental.evennia.com/), an text-based multi-player "escape-room" written in Python using the [Evennia](http://www.evennia.com/) MU* creation system. You can play it from that link in your browser or MU*-client of choice. If you are so inclined, you can also [vote for it here](https://itch.io/jam/enterthemud2/rate/422945) in the jam (well, no more).  
  
This little series of (likely two) dev-blog entries will try to recount the planning and technical aspects of the Evscaperoom. This is also for myself - I'd better write stuff down now while it's still fresh in my mind!  
  
Update: The Evscaperoom can these days be played by connecting to the Evennia game demo at [https://demo.evennia.com](https://demo.evennia.com).  

  
## Inception   
  
When I first heard about the upcoming game-jam's theme of _One Room_, an 'escape room' was the first thing that came to mind, not the least because I just recently got to solve my my own first real-world escape-room as a gift on my birthday.   
  
If you are not familiar with escape-rooms, the premise is simple - you are locked into a room and have to figure out a way to get out of it by solving practical puzzles and finding hidden clues in the room.   
  
While you could create such a thing in your own bedroom (and there are also some one-use board game variants), most escape-rooms are managed by companies selling this as an experience for small groups. You usually have one hour to escape and if you get stuck you can press a button (or similar) to get a hint.  
  
I thought making a computer escape-room. Not only can you do things in the computer that you cannot do in the real world, restricting the game to a single room limits so that it's conceivable to actually finish the damned thing in a month.   
  
A concern I had was that everyone else in the jam surely must have went for the same obvious idea. In the end that was not an issue at all though.  
  
  
## Basic premises  
   
I was pretty confident that I would _technically_ be able to create the game in time (not only is Python and Evennia perfect for this kind of fast experimentation and prototyping, I know the engine very well). But that's not enough; I had to first decide on how the thing should actually _play._ Here are the questions I had to consider:  
  
### Room State   
  
 An escape room can be seen as going through multiple _states_ as puzzles are solved. For example, you may open a cabinet and that may open up new puzzles to solve. This is fine in a single-player game, but how to handle it in a multi-player environment?  
  
My first thought was that each object may have multiple states and that players could co-exist in the same room, seeing _different_ states at the same time. I really started planning for this. It would certainly be possible to implement.  
  
But in the end I considered how a real-world escape-room works - people in the same room solves it together. For there to be any _meaning_ with multi-player, they must _share_ the room state.  
  
So what I went with was a solution where players can create their own room or join an existing one. Each such room is generated on the fly (and filled with objects etc) and will change as players solve it. Once complete and/or everyone leaves, the room is deleted along with all objects in it. Clean and tidy.  
  
So how to describe these states? I pictured that these would be described as normal Python modules with a start- and end function that initialized each state and cleaned it up when a new state was started. In the beginning I pictured these states as being pretty small (like one state to change one thing in the room). In the end though, the entire Evscaperoom fits in 12 state modules. I'll describe them in more detail in the second part of this post.   
  
### Accessibility and "pixel-hunting" in text
  
When I first started writing descriptions I didn't always note which objects where interactive. It's a very simple and tempting puzzle to add - mention an object as part of a larger description and let the player figure out that it's something they can interact with. This practice is sort-of equivalent to _pixel-hunting_ in graphical games - sweeping with the mouse across the screen until you find that little spot on the screen that you can do something with.  
  
Problem is, pixel-hunting's not really _fun_. You easily get stuck and when you eventually find out what was blocking you, you don't really feel clever but only frustrated. So I decided that I should _clearly mark every object that people could interact with_ and focus puzzles on better things.  
  
  
In fact, in the end I made it an option:  
  

[![Option menu ('quit' to return)   1: ( ) No item markings (hard mode)  2: ( ) Items marked as item (with color)  3: (*) Items are marked as [item] (screenreader friendly)  4: ( ) Screenreader mode](https://3.bp.blogspot.com/-HdLAfVl8P5A/XOAWjd_zoDI/AAAAAAAAKek/GBrnsZDvck0rkeBW2WVLZHXNG6ePqKEjgCEwYBhgL/s400/Screenshot%2Bfrom%2B2019-05-17%2B11-49-20.png "In-game option menu")](https://3.bp.blogspot.com/-HdLAfVl8P5A/XOAWjd_zoDI/AAAAAAAAKek/GBrnsZDvck0rkeBW2WVLZHXNG6ePqKEjgCEwYBhgL/s1600/Screenshot%2Bfrom%2B2019-05-17%2B11-49-20.png)

  
As part of this I had to remind myself _never to use colors only_ when marking important information: Visually impaired people with screen readers will simply miss that. Not to mention that some just disable colors in their clients.  
  
So while I personally think option 2 above is the most visually pleasing, Evscaperoom defaults to the third option. It should should start everyone off on equal footing. Evennia has a screen-reader mode out of the box, but I moved it into the menu here for easy access.  
  
### Inventory and collaboration
  
In a puzzle-game, you often find objects and combine them with other things. Again, this is simple to do in a single-player game: Players just pick things up and use them later.  
  
But in a multi-player game this offers a huge risk: players that pick up something important and then log off. The remaining players in that room would then be stuck in an unsolvable room - and it would be very hard for them to know this.  
  
In principle you could try to 'clean' player inventories when they leave, but not only does it add complexity, there is another issue with players picking things up: It means that _the person first to find/pick up the item is the only one that can use it and look at it_. Others won't have access until the first player gives it up. Trusting that to anonymous players online is not a good idea.  
  
So in the end I arrived at the following conclusions:  

-   As soon as an item/resource is discovered, _everyone_ in the room must be able to access it immediately.
-   There can be _no inventory_. Nothing can ever be picked up and tied to a specific player.
-   As soon as a discovery is made, this _must be echoed to the entire room_ (it must not be up to the finder to announce what they found to everyone else).  

As a side-effect of this I also set a limit to the kind of puzzles I would allow:  

-   _No puzzles must require more than one player to solve_. While one could indeed create some very cool puzzles where people collaborate, it's simply not feasible to do so with random strangers on the internet. At any moment the other guy may log off and leave you stuck. And that's if you even find someone logged in at the same time in the first place! The room should always be possible to solve solo, from beginning to end.

  
### Focusing on objects  
  
So without inventory system, how _do_ you interact with objects? A trademark of any puzzle is using one object with another and also to explore things closer to find clues. I turned to graphical adventure games for inspiration:  
[![Hovering with mouse over lens object offers action "look at lens"](https://1.bp.blogspot.com/-hTP1HlMck3c/XOA9-qVnrHI/AAAAAAAAKew/GOVcWIfwyZIr25CZj3VadztdjeVwmzl7gCLcBGAs/s400/1569-4-secret-of-monkey-island-the.jpg "Monkey Island GUI")](https://1.bp.blogspot.com/-hTP1HlMck3c/XOA9-qVnrHI/AAAAAAAAKew/GOVcWIfwyZIr25CZj3VadztdjeVwmzl7gCLcBGAs/s1600/1569-4-secret-of-monkey-island-the.jpg)

_Secret of Monkey Island ©1990 LucasArts. Image from old-games.com_

  
A common way to operate on an object in traditional adventure games is to hover the mouse over it and then select the action you want to apply to it. In later (3D) games you might even zoom in of the object and rotate it around with your mouse to see if there are some clues to be had.  
  
While Evennia and modern UI clients _may_ allow you to use the mouse to select objects, I wanted this to work the traditional MUD-way, by inserting commands. So I decided that you as a player would be in one of two states:  

-   The 'normal' state: When you use **look** you see the room description.
-   The 'focused' state: You focus on a specific object with the **examine <target>** command (aliases are **ex** or just **e**). Now object-specific actions become available to you. Use **examine** again to "un-focus". 

[![A small stone fireplace sits in the middle of the wall opposite the [door]. On the chimney hangs a small oil [painting] of a man. Hanging over the hearth is a black [cauldron]. The piles of [ashes] below are cold.  (It looks like fireplace may be suitable to [climb].)](https://2.bp.blogspot.com/-E-J-PZZ2KbY/XOAWidK1Y_I/AAAAAAAAKek/mcWbgVNkvVkBBZEUpOuaaWyBVkNoE7K9gCEwYBhgL/s400/Screenshot%2Bfrom%2B2019-05-17%2B11-41-50.png "Examining a fireplace")](https://2.bp.blogspot.com/-E-J-PZZ2KbY/XOAWidK1Y_I/AAAAAAAAKek/mcWbgVNkvVkBBZEUpOuaaWyBVkNoE7K9gCEwYBhgL/s1600/Screenshot%2Bfrom%2B2019-05-17%2B11-41-50.png)

  
In the example above, the fireplace points out other objects you could also focus on, whereas the last parenthesis includes one or more "actions" that you can perform on the fireplace only when you have it focused.   
  
This ends up pretty different from most traditional MUD-style inputs. When I first released this to the public, I found people logged off after their first examine. It turned out that they couldn't figure out how to leave the focus mode. So they just assumed the thing was buggy and quit instead. Of course it's mentioned if you care to write **help**, but this is clearly one step too many for such an important UI concept.   
  
So I ended up adding the header above that always reminds you. And since then I've not seen any confusion over how the focus mode works.  
  
For making it easy to focus on things, I also decided that each room would only ever have one object named a particular thing. So there is for example only one single object in the game named "key" that you can focus on.   
  
### Communication  
  
I wanted players to co-exist in the same room so that they could collaborate on solving it. This meant communication must be possible. I pictured people would want to point things out and talk to each other.  
  
In my first round of revisions I had a truckload of individual emotes; you could  
  
      **point at target**  
  
 for example. In the end I just limited it to   
  
 **say/shout/whisper <message>**  
  
and   
  
     **emote <whatever>**  
  
And seeing what people actually use, this is more than enough (**say** alone is probably 99% of what people need, really). I had a notion that the shout/whisper could be used in a puzzle later but in the end I decided that communication commands should be strictly between players and not have anything to do with the puzzles.  
  
I removed all other interaction: There is no fighting and without an inventory or requirement to collaborate on puzzles, there is no need for other interactions than to communicate.  
  
First version you didn't even see what the others did, but eventually I added so that you at least saw what other players were focusing on at the moment (and of course if some major thing was solved/found).  
  
In the end I don't even list characters as objects in the room (you have to use the **who** command to see who's in there with you).  
  

[![Listing of commands available in the Evscaperoom (output of the help-command in game)](https://1.bp.blogspot.com/-JVAZ65CrRZ0/XOAWibmcrhI/AAAAAAAAKeg/_YopP6nWqPUqK6B3JD_54RDqvE5a_fijQCEwYBhgL/s400/Screenshot%2Bfrom%2B2019-05-17%2B11-38-49.png "Help command output")](https://1.bp.blogspot.com/-JVAZ65CrRZ0/XOAWibmcrhI/AAAAAAAAKeg/_YopP6nWqPUqK6B3JD_54RDqvE5a_fijQCEwYBhgL/s1600/Screenshot%2Bfrom%2B2019-05-17%2B11-38-49.png)

The main **help** command output.

## Story  
  
It's very common for this type of game to have a dangerous or scary theme. Things like "get out before the bomb explodes", "save the space ship before the engines overheat", "flee the axe murderer before he comes back" etc). I'm no stranger to dark themes, but for this I wanted something friendlier and brighter, maybe with a some dark undercurrents here and there.  
  
My [Jester character](https://www.deviantart.com/griatch-art/art/Say-hi-to-Mrs-Buttons-153984575) is someone I've not only depicted in art, but she's also an old RP character and literary protagonist of mine. Who else would find it funny to lock someone into a room only to provide crazy puzzles and hints for them to get out again? So my flimsy 'premise' was this:   
  

_The village Jester wants to win the pie eating contest. You are one of her most dangerous opponents. She tricked you to her cabin and now you are locked in! If you don't get out in time, she'll get to eat all those pies on her own and surely win!_

  
That's it - this became the premise from which the entire game flowed. I quickly decided that it to be a very "small-scale" story: no life-or-death situation, no saving of the world. The drama takes place in a small village with an "adversary" that doesn't really want to hurt you, but only to eat more pies than you.  
  
From this, the way to offer hints came naturally - just eat a slice of "hintberry pie" the jester made (she even encourage you to eat it). It gives you a hint but is also very filling. So if you eat too much, how will you beat her in the contest later, even if you do get out?  
  
To further the rustic and friendly tone I made sure the story took place on a warm summer day. Many descriptions describe sunshine, chirping birds and the smell of pie. I aimed at letting the text point out quirky and slightly comedic tone of the puzzles the Jester left behind. The player also sometimes gets teased by the game when doing things that does not make sense.  
  
I won't go into the story further here - it's best if you experience it yourself. Let's just say that the village has some old secrets. And and the Jester has her own ways of doing things and of telling a story. The game has multiple endings and so far people have drawn very different conclusions in the end.  
  
## Scoring  
  
Most often in escape rooms, final score is determined by the time and the number of hints used. I do keep the latter - for every pie you eat, you get a penalty on your final score.  
  
As for time - this background story _would_ fit very well with a time limit (get out in X time, after which the pie-eating contest will start!). But from experience with other online text-based games I decided against this. Not only should a player be able to take a break, they may also want to wait for a friend to leave and come back etc.   
  
But more importantly, I want players to explore and read all my carefully crafted descriptions! So I'd much rather prefer they take their time and reward them for being thorough.   
  
So in the end I give specific scores for actions throughout the game instead. Most points are for doing things that drive the story forward, such as using something or solving a puzzle. But a significant portion of the score comes from turning every stone and trying everything out. The nice side-effect of this is that even if you know exactly how to solve everything and rush through the game you will still not end up with a perfect score.   
  
The final score, adjusted by hints is then used to determine if you make it in time to the contest and how you fare. This means that if you explore carefully you have a "buffer" of points so eating a few pies may still land you a good result in the end.  
   
  
## First sketch  
  
I really entered the game 'building' aspect with no real notion of how the Jester's cabin should look nor which puzzles should be in it. I tried to write things down beforehand but it didn't really work for me.   
  
So in the end I decided "let's just put a lot of interesting stuff in the room and then I'll figure out how they interact with each other". I'm sure this is different from game-maker to game-maker. But for me, this process worked perfectly.   
  
  

[![Scribbles on my notebook, sketching up the room's main items](https://1.bp.blogspot.com/-3mV7GIsQbDo/XOBI3SX6bmI/AAAAAAAAKe8/DSYB7q6otCwLkKb1JNTco6kTJ1UEbVp1ACKgBGAs/s640/20190515_230856.jpg "Scriblles on notebook")](https://1.bp.blogspot.com/-3mV7GIsQbDo/XOBI3SX6bmI/AAAAAAAAKe8/DSYB7q6otCwLkKb1JNTco6kTJ1UEbVp1ACKgBGAs/s1600/20190515_230856.jpg)

> My first, very rough, sketch of the Jester's cabin
  
The above, first sketch ended up being what I used, although many of the objects mentioned never ended up in the final game and some things switched places. I did some other sketches too, but they'd be spoilers so I won't show them here ...  
  
  
## The actual game logic  
  
The Evscaperoom principles outlined above deviate quite a bit from the traditional MU* style of game play.   
  
While Evennia provides everything for database management, in-game objects, commands, networking and other resources, the specifics of your game is something you need to make yourself - and you have the full power of Python to do it!  
  
So for the first three days of the jam I used Evennia to build the custom game logic needed to provide the evscaperoom style of game play. I also made the tools I needed to quickly create the game content (which then took me the rest of the jam to make).   
  
In part 2 of this blog post I will cover the technical details of the Evscaperoom I built. I'll also go through some issues I ran into and conclusions I drew. I'll link to that from here when it's available!