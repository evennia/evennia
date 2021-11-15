[![](https://3.bp.blogspot.com/-uODV_t0eTv8/UC0czBg9ctI/AAAAAAAABTk/NvEUkwrrZPY/s1600/200px-Venn0001.svg.png)](https://3.bp.blogspot.com/-uODV_t0eTv8/UC0czBg9ctI/AAAAAAAABTk/NvEUkwrrZPY/s1600/200px-Venn0001.svg.png)_Commands_ are the bread and butter of any game. Commands are the instructions coming in from the player telling the game (or their avatar in the game) to do stuff. This post will outline the reasoning leading up to Evennia's somewhat (I think) non-standard way of handling commands.  
  
In the case of MUDs and other text games commands usually come in the form of entered text. But clicking on a graphical button or using a joystick is also at some level issuing a command - one way or another the Player instructs the game in a way it understands. In this post I will stick to text commands though. So _open door with red key_ is a potential command.  
  
Evennia, being a MUD design system, needs to offer a stable and extensive way to handle new and old commands.  More than that, we need to allow developers pretty big freedom with developing their own command syntax if they so please (our default is not for everyone). A small hard-coded command set is not an option.  
  

### Identifying the command

  

First step is _identifying_ the command coming in. When looking at _open door with red key_ it's probably _open_ that is the unique command. The other words are "options" to the command, stuff the _open_ command supposedly knows what to do with. If you _know_ already at this stage exactly how the command syntax looks, you could hard-code the parsing already here. In Evennia's case that's not possible though - we aim to let people define their command syntax as freely as possible. Our identifier actually requires no more than that the uniquely identifying command word (or words) appear _first_ on the input line. It is hard to picture a command syntax where this isn't true ... but if so people may freely plug in their own identifyer routine.  
  
So the identifyer digs out the _open_ command and sends it its options ... but what kind of code object is _open_?  

###  The way to define the command

  
A common variant I've seen in various Python codebases is to implement commands as _functions_. A function maps intuitively to a command - it can take arguments and it does stuff in return. It is probably more than enough for some types of games.  
  
Evennia chooses to let the command be defined as a _class_ instead. There are a few reasons. Most predominantly, classes can inherit and require less boiler plate (there are a few more reasons that has to do with storing the results of a command between calls, but that's not as commonly useful). Each Evennia command class has two primary methods:  

-   _parse()_ - this is responsible for parsing and splitting up the _options_ part of the command into easy-to use chunks. In the case of _open door with red key,_ it could be as simple as splitting the options into a list of strings. But this may potentially be more complex. A mux-like command, for exampe, takes _/switches_ to control its functionality. They also have a recurring syntax using the '=' character to set properties. These components could maybe be parsed into a list _switches_ and two parameters _lhs_ and _rhs_ holding the left- and right hand side of the equation sign. 
-   _func()_ - this takes the chunks of pre-parsed input and actually does stuff with it. 

One of of the good things with executing class instances is that neither of these methods need to have any arguments or returns. They just store the data on their object (_self.switches_) and the next method can just access them as it pleases. Same is true when the command system instantiates the command. It will set a few useful properties on the command for the programmer to make use of in their code (_self.caller_ always references the one executing the command, for example). This shortcut may sound like a minor thing, but for developers using Evennia to create countless custom commands for their game, it's really very nice to not have to have all the input/output boilerplate to remember. 

  
  
... And of course, class objects support inheritance. In Evennia's default command set the _parse()_ function is  only implemented once, all handling all possible permutations of the syntax. Other commands just inherit from it and only needs to implement _func()._ Some advanced build commands just use a parent with an overloaded and slightly expanded _parse()_.  
  

###  Commands in States

  
So we have individual commands. Just as important is how we now group and access them. The most common way to do this (also used in an older version of Evennia) is to use a simple _global list_. Whenever a player enters a command, the _identifier_ looks the command up in the list. Every player has access to this list (admin commands check permissions before running). It seems this is what is used in a large amount of code bases and thus obviously works well for many types of games. Where it starts to crack is when it comes to _game states._  

-   A first example is an in-game menu. Selecting a menu item means an instruction from the player - i.e. a command. A menu could have numbered options but it might also have named options that vary from menu node to menu node. Each of these are a command name that must be identified by the parser. Should you make _all_ those possible commands globally available to your players at all times? Or do you hide them somehow until the player actually is in a menu? Or do you bypass the command system entirely and write new code only for handling menus...?
-   Second example: Picture this scenario: You are walking down a dark hallway, torch in hand. Suddenly your light goes out and you are thrown into darkness. You cannot see anything now, not even to look in your own backpack. How would you handle this in code? Trivially you can put _if_ statements in your _look_ and _inventory_ commands. They check for the "dark" flag. Fair enough. Next you knock your head and goes 'dizzy'. Suddenly your "navigation" skill is gone and your movement commands may randomly be turned around. Dizziness combined with darkness means your inventory command now returns a strange confused mess. Next you get into a fight ... the number of if statements starts piling up.  
-   Last example: In the hypothetical FishingMUD,. you have lots of detailed skills for fishing. But different types of fishing rods makes different types of throws (commands) available. Also, they all work differently if you are on a shore as compared to being on a boat. Again, lots of if statements. It's all possible to do, but the problem is maintenance; your command body keep growing to handle edge cases. Especially in a MUD, where new features tend to be added gradually over the course of years, this gives lots of possibilities for regressions.

All of these are examples of situation-dependent (or object-dependent) commands. Let's jointly call them _state-dependent commands._ You could picture handling the in-game menu by somehow dynamically changing the global list of commands available. But then the _global_ bit becomes problematic - not all players are in the same menu at the same time. So you'll then have to start to track _who_ has which list of commands available to them. And what happens when a state ends? How do you get back to the previous state - a state which may itself be different from the "default" state (like clearing your dizzy state while still being in darkness)? This means you have to track the previous few states and ...  
  
A few iterations of such thinking lead to what Evennia now uses: a _non-global_ _command set_ system. A command set (cmdset) is a structure that looks pretty much like a mathematical _set._ It can contain any number of (unique) command objects, and a particular command can occur in any number of command sets.  

-   A cmdset stored on an object makes all commands in that cmdset available to the object. So all player characters in the game has a "default cmdset" stored on them with all the common commands like _look, get_ and so on.
-   Optionally, an object can make its cmdset available to other objects in the same location instead. This allows for commands only applicable with a given object or location, such as _wind up grandfather clock._ Or the various commands of different types of fishing rods. 
-   Cmdsets can be non-destructively combined and merged like mathematical sets, using operations like "Union", "Intersect" and a few other cmdset-special operations. Each cmdset can have priorities and exceptions to the various operations applied to them. Removing a set from the mix will dynamically rebuild the remaining sets into a new mixed set.

The last point is the most interesting aspect of cmdsets. The ability to merge cmdsets allows you to develop your game states in isolation. You then just merge them in dynamically whenever the game state changes. So to implement the dark example above, you would define two types of "look" (the dark version probably being a child of the normal version). Normally you use your "default cmdset" containing the normal _look_. But once you end up in a dark room the system (or more likely the room) "merges" the _dark_ cmdset with the default one on the player, replacing same-named commands with new ones. The _dark_ cmdset contains the commands that are different (or new) to the dark condition - such as the _look_ command and the changed _inventory_ command.  Becoming dazed just means yet another merger - merging the _dazed_ set on top of the other two. Since all merges are non-destructive, you can later remove either of the sets to rebuild a new "combined" set only involving the remaining ones in any combination. 

  
Similarly, the menu becomes very simple to create in isolation (in Evennia it's actually an optional contrib). All it needs to do is define the required menu-commands in its own cmdset. Whenever someone triggers the menu, that cmdset is loaded onto the player. All relevant commands are then made available. Once the menu is exited, the menu-cmdset is simply removed and the player automatically returns to whichever state he or she was in before.  
  

### Final words

  
The combination of _commands-as-classes_ and _command sets_ has proved to very flexible. It's not as easy to conceptualize as is the simple functions in a list, but so far it seems people are not having too much trouble. I also think it makes it pretty easy to both create and, importantly, expand a game with interesting new forms of gameplay _without_ drastically rewriting old systems.