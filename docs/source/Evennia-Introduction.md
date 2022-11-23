# Evennia Introduction

> *A MUD (originally Multi-User Dungeon, with later variants Multi-User Dimension and Multi-User
Domain) is a multiplayer real-time virtual world described primarily in text. MUDs combine elements
of role-playing games, hack and slash, player versus player, interactive fiction and online chat.
Players can read or view descriptions of rooms, objects, other players, non-player characters, and
actions performed in the virtual world. Players typically interact with each other and the world by
typing commands that resemble a natural language.* - [Wikipedia](https://en.wikipedia.org/wiki/MUD)

If you are reading this, it's quite likely you are dreaming of creating and running a text-based
massively-multiplayer game ([MUD/MUX/MUSH](https://tinyurl.com/c5sc4bm) etc) of your very own. You
might just be starting to think about it, or you might have lugged around that *perfect* game in
your mind for years ... you know *just* how good it would be, if you could only make it come to
reality. We know how you feel. That is, after all, why Evennia came to be.

Evennia is a MU\*-building system: a bare-bones Python codebase and server intended to
be highly extendable for any style of game. "Bare-bones" in this context means that we try to impose as few game-specific things on you as possible. For convenience offer basic building
blocks like objects, characters, rooms, default commands for building and administration etc, we
don't prescribe any combat rules, mob AI, races, skills, character classes or other things that will
be different from game to game anyway. 

What we *do* however, is to provide a solid foundation for all the boring database, networking, and
behind-the-scenes administration stuff that all online games need whether they like it or not.
Evennia is *fully persistent*, that means things you drop on the ground somewhere will still be
there a dozen server reboots later. Through Django we support a large variety of different database
systems (a database is created for you automatically if you use the defaults).

We also include a growing list of *optional* [contribs](Contribs/Contribs-Overview.md) you can use for your game  would you want something to build from. 

Using the full power of Python throughout the server offers some distinct advantages. All your coding, from object definitions and custom commands to AI scripts and economic systems is  done in normal Python modules rather than some ad-hoc scripting language. The fact that you script the game in the same high-level language that you code it in allows for very powerful and custom game implementations indeed.

Out of the box, Evennia gives you a 'talker'-type of game; you can walk around, chat, build rooms and objects, do basic roleplaying and administration. The server ships with a default set of player commands that are  similar to the MUX command set. We *do not* aim specifically to be a MUX server, but we had to pick some  default to go with (see [this](Concepts/Soft-Code.md) for more about our original motivations). It's easy to  remove or add commands, or to have the command syntax mimic other systems, like Diku, LP, MOO and so on. Or why not create a new and better command system of your own design.

## Can I test it somewhere?

Evennia's demo server can be found at [https://demo.evennia.com](https://demo.evennia.com). If you prefer to
connect to the demo via your telnet client you can do so at `demo.evennia.com`, port `4000`.

Once you installed Evennia yourself it comes with its own tutorial - this shows off some of the
possibilities _and_ gives you a small single-player quest to play. The tutorial takes only one
single in-game command to install as explained [here](Howtos/Beginner-Tutorial/Part1/Beginner-Tutorial-Tutorial-World.md).

## What you need to know to work with Evennia

Assuming you have Evennia working (see the [quick start instructions](Setup/Installation.md)) and have
gotten as far as to start the server and connect to it with the client of your choice, here's what
you need to know depending on your skills and needs.

### I don't know (or don't want to do) any programming - I just want to run a game!

Evennia comes with a default set of commands for the Python newbies and for those who need to get a game running *now*. Stock Evennia is enough for running a simple 'Talker'-type game - you can build and describe rooms and basic objects, have chat channels, do emotes and other things suitable for a social or free-form MU\*. Combat, mobs and other game elements are not included, so you'll have a very basic game indeed if you are not willing to do at least *some* coding.

### I know basic Python, or I am willing to learn

Evennia's source code is [extensively documented](https://www.evennia.com/docs/latest). But while Python is considered a very easy programming language to get into, you do have a learning curve to climb if you are new to programming. Evennia's [Starting-tutorial](Howtos/Beginner-Tutorial/Part1/Beginner-Tutorial-Part1-Overview.md) has a [basic introduction to Python](Howtos/Beginner-Tutorial/Part1/Beginner-Tutorial-Python-basic-introduction.md) but you should probably also sit down  with a full Python beginner's tutorial at some point (there are plenty of them on the web if you look around). See also our [link page](./Links.md) for some reading suggestions.

To code your dream game in Evennia you don't need to be a Python guru, but you do need to be able to read example code containing at least these basic Python features:

- Importing and using python [modules](https://docs.python.org/3.7/tutorial/modules.html)
- Using [variables](https://www.tutorialspoint.com/python/python_variable_types.htm), [conditional statements](https://docs.python.org/tutorial/controlflow.html#if-statements),
[loops](https://docs.python.org/tutorial/controlflow.html#for-statements) and [functions](https://docs.python.org/tutorial/controlflow.html#defining-functions)
- Using [lists, dictionaries and list comprehensions](https://docs.python.org/tutorial/datastructures.html)
- Doing [string handling and formatting](https://docs.python.org/tutorial/introduction.html#strings)
- Have a basic understanding of [object-oriented programming](https://www.tutorialspoint.com/python/python_classes_objects.htm), using
[Classes](https://docs.python.org/tutorial/classes.html), their methods and properties

Obviously, the more things you feel comfortable with, the easier time you'll have to find your way.
With just basic knowledge you should be able to define your own [Commands](Components/Commands.md), create custom
[Objects](Components/Objects.md) as well as make your world come alive with basic [Scripts](Components/Scripts.md). You can
definitely build a whole advanced and customized game from extending Evennia's examples only.

### I know my Python stuff and I am willing to use it!

Even if you started out as a Python beginner, you will likely get to this point after working on your game for a while.  With more general knowledge in Python the full power of Evennia opens up for you. Apart from modifying commands, objects and scripts, you can develop everything from advanced mob AI and economic systems, through sophisticated combat and social mini games, to redefining how commands, players, rooms or channels themselves work. Since you code your game by importing normal Python modules, there are few limits to what you can accomplish.

If you *also* happen to know some web programming (HTML, CSS, Javascript) there is also a web
presence (a website and a mud web client) to play around with ...

## Where to from here?

It's recommended you jump into the [Beginner Tutorial](Howtos/Beginner-Tutorial/Beginner-Tutorial-Overview.md). You can either follow it or jump around to lessons that seem interesting.  You can also read the lead developer's [dev blog](https://www.evennia.com/devblog/index.html) for many tidbits and snippets about Evennia's development and structure.

Sometimes it's easier to ask for help. Get engaged in the Evennia community by joining our [Discord](https://discord.gg/AJJpcRUhtF) for direct support. Make an introductory post to our [Discussion forum](https://github.com/evennia/evennia/discussions)  and say hi!.