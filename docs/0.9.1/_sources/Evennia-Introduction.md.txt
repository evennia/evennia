# Evennia Introduction

> *A MUD (originally Multi-User Dungeon, with later variants Multi-User Dimension and Multi-User Domain) is a multiplayer real-time virtual world described primarily in text. MUDs combine elements of role-playing games, hack and slash, player versus player, interactive fiction and online chat. Players can read or view descriptions of rooms, objects, other players, non-player characters, and actions performed in the virtual world. Players typically interact with each other and the world by typing commands that resemble a natural language.* - [Wikipedia](http://en.wikipedia.org/wiki/MUD)

If you are reading this, it's quite likely you are dreaming of creating and running a text-based massively-multiplayer game ([MUD/MUX/MUSH](http://tinyurl.com/c5sc4bm) etc) of your very own. You might just be starting to think about it, or you might have lugged around that *perfect* game in your mind for years ... you know *just* how good it would be, if you could only make it come to reality. We know how you feel. That is, after all, why Evennia came to be. 

Evennia is in principle a MUD-building system: a bare-bones Python codebase and server intended to be highly extendable for any style of game. "Bare-bones" in this context means that we try to impose as few game-specific things on you as possible. So whereas we for convenience offer basic building blocks like objects, characters, rooms, default commands for building and administration etc, we don't prescribe any combat rules, mob AI, races, skills, character classes or other things that will be different from game to game anyway. It is possible that we will offer some such systems as contributions in the future, but these will in that case all be optional. 

What we *do* however, is to provide a solid foundation for all the boring database, networking, and behind-the-scenes administration stuff that all online games need whether they like it or not. Evennia is *fully persistent*, that means things you drop on the ground somewhere will still be there a dozen server reboots later. Through Django we support a large variety of different database systems (a database is created for you automatically if you use the defaults). 

Using the full power of Python throughout the server offers some distinct advantages. All your coding, from object definitions and custom commands to AI scripts and economic systems is  done in normal Python modules rather than some ad-hoc scripting language. The fact that you script the game in the same high-level language that you code it in allows for very powerful and custom game implementations indeed. 

The server ships with a default set of player commands that are similar to the MUX command set. We *do not* aim specifically to be a MUX server, but we had to pick some default to go with (see [this](./Soft-Code) for more about our original motivations).  It's easy to remove or add commands, or to have the command syntax mimic other systems, like Diku, LP, MOO and so on. Or why not create a new and better command system of your own design. 

## Can I test it somewhere?

Evennia's demo server can be found at [demo.evennia.com](http://demo.evennia.com). If you prefer to connect to the demo via your own telnet client you can do so at `silvren.com`, port `4280`. Here is a [screenshot](./Screenshot).

Once you installed Evennia yourself it comes with its own tutorial - this shows off some of the possibilities _and_ gives you a small single-player quest to play. The tutorial takes only one single in-game command to install as explained [here](./Tutorial-World-Introduction).

## Brief summary of features

### Technical

- Game development is done by the server importing your normal Python modules. Specific server features are implemented by overloading hooks that the engine calls appropriately.
- All game entities are simply Python classes that handle database negotiations behind the scenes without you needing to worry.
- Command sets are stored on individual objects (including characters) to offer unique functionality and object-specific commands. Sets can be updated and modified on the fly to expand/limit player input options during play.
- Scripts are used to offer asynchronous/timed execution abilities. Scripts can also be persistent. There are easy mechanisms to thread particularly long-running processes and built-in ways to start "tickers" for games that wants them.
- In-game communication channels are modular and can be modified to any functionality, including mailing systems and full logging of all messages.
- Server can be fully rebooted/reloaded without users disconnecting.
- An Account can freely connect/disconnect from game-objects, offering an easy way to implement multi-character systems and puppeting.
- Each Account can optionally control multiple Characters/Objects at the same time using the same login information.
- Spawning of individual objects via a prototypes-like system.
- Tagging can be used to implement zones and object groupings.
- All source code is extensively documented.
- Unit-testing suite, including tests of default commands and plugins.

### Default content

- Basic classes for Objects, Characters, Rooms and Exits
- Basic login system, using the Account's login name as their in-game Character's name for simplicity
- "MUX-like" command set with administration, building, puppeting, channels and social commands
- In-game Tutorial
- Contributions folder with working, but optional, code such as alternative login, menus, character generation and more

### Standards/Protocols supported

- TCP/websocket HTML5 browser web client, with ajax/comet fallback for older browsers
- Telnet and Telnet + SSL with mud-specific extensions ([MCCP](http://tintin.sourceforge.net/mccp/), [MSSP](http://tintin.sourceforge.net/mssp/), [TTYPE](http://tintin.sourceforge.net/mtts/), [MSDP](http://tintin.sourceforge.net/msdp/), [GMCP](https://www.ironrealms.com/rapture/manual/files/FeatGMCP-txt.html), [MXP](https://www.zuggsoft.com/zmud/mxp.htm) links)
- ANSI and xterm256 colours
- SSH
- HTTP - Website served by in-built webserver and connected to same database as game.
- IRC - external IRC channels can be connected to in-game chat channels
- RSS feeds can be echoed to in-game channels (things like Twitter can easily be added)
- Several different databases supported (SQLite3, MySQL, PostgreSQL, ...)

For more extensive feature information, see the [Developer Central](./Developer-Central).

## What you need to know to work with Evennia

Assuming you have Evennia working (see the [quick start instructions](./Getting-Started)) and have gotten as far as to start the server and connect to it with the client of your choice, here's what you need to know depending on your skills and needs. 

### I don't know (or don't want to do) any programming - I just want to run a game!

Evennia comes with a default set of commands for the Python newbies and for those who need to get a game running *now*. Stock Evennia is enough for running a simple 'Talker'-type game - you can build and describe rooms and basic objects, have chat channels, do emotes and other things suitable for a social or free-form MU\*. Combat, mobs and other game elements are not included, so you'll have a very basic game indeed if you are not willing to do at least *some* coding. 

### I know basic Python, or I am willing to learn

Evennia's source code is extensively documented and is [viewable online](https://github.com/evennia/evennia). We also have a comprehensive [online manual](https://github.com/evennia/evennia/wiki) with lots of examples. But while Python is considered a very easy programming language to get into, you do have a learning curve to climb if you are new to programming. You should probably sit down
with a Python beginner's [tutorial](http://docs.python.org/tutorial/) (there are plenty of them on the web if you look around) so you at least know what you are seeing. See also our [link page](./Links#wiki-litterature) for some reading suggestions. To efficiently code your dream game in Evennia you don't need to be a Python guru, but you do need to be able to read example code containing at least these basic Python features:

- Importing and using python [modules](http://docs.python.org/3.7/tutorial/modules.html)
- Using [variables](http://www.tutorialspoint.com/python/python_variable_types.htm), [conditional statements](http://docs.python.org/tutorial/controlflow.html#if-statements), [loops](http://docs.python.org/tutorial/controlflow.html#for-statements) and [functions](http://docs.python.org/tutorial/controlflow.html#defining-functions)
- Using [lists, dictionaries and list comprehensions](http://docs.python.org/tutorial/datastructures.html)
- Doing [string handling and formatting](http://docs.python.org/tutorial/introduction.html#strings)
- Have a basic understanding of [object-oriented programming](http://www.tutorialspoint.com/python/python_classes_objects.htm), using [Classes](http://docs.python.org/tutorial/classes.html), their methods and properties

Obviously, the more things you feel comfortable with, the easier time you'll have to find your way.  With just basic knowledge you should be able to define your own [Commands](./Commands), create custom [Objects](./Objects) as well as make your world come alive with basic [Scripts](./Scripts). You can definitely build a whole advanced and customized game from extending Evennia's examples only.  

### I know my Python stuff and I am willing to use it!

Even if you started out as a Python beginner, you will likely get to this point after working on your game for a while.  With more general knowledge in Python the full power of Evennia opens up for you. Apart from modifying commands, objects and scripts, you can develop everything from advanced mob AI and economic systems, through sophisticated combat and social mini games, to redefining how commands, players, rooms or channels themselves work. Since you code your game by importing normal Python modules, there are few limits to what you can accomplish.

If you *also* happen to know some web programming (HTML, CSS, Javascript) there is also a web presence (a website and a mud web client) to play around with ...

### Where to from here?

From here you can continue browsing the [online documentation]([online documentation](index)) to find more info about Evennia. Or you can jump into the [Tutorials](./Tutorials) and get your hands dirty with code right away. You can also read the developer's [dev blog](https://evennia.blogspot.com/) for many tidbits and snippets about Evennia's development and structure.

Some more hints: 

1. Get engaged in the community. Make an introductory post to our [mailing list/forum](https://groups.google.com/forum/#!forum/evennia) and get to know people. It's also highly recommended you hop onto our [Developer chat](http://webchat.freenode.net/?channels=evennia&uio=MT1mYWxzZSY5PXRydWUmMTE9MTk1JjEyPXRydWUbb) on IRC. This allows you to chat directly with other developers new and old as well as with the devs of Evennia itself. This chat is logged (you can find links on http://www.evennia.com) and can also be searched from the same place for discussion topics you are interested in. 
2. Read the [Game Planning](./Game-Planning) wiki page. It gives some ideas for your work flow and the state of mind you should aim for - including cutting down the scope of your game for its first release.
3. Do the [Tutorial for basic MUSH-like game](./Tutorial-for-basic-MUSH-like-game) carefully from beginning to end and try to understand what does what. Even if you are not interested in a MUSH for your own game, you will end up with a small (very small) game that you can build or learn from.
