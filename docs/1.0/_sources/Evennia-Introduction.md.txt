# Evennia Introduction

> *A MUD (originally Multi-User Dungeon, with later variants Multi-User Dimension and Multi-User
Domain) is a multiplayer real-time virtual world described primarily in text. MUDs combine elements
of role-playing games, hack and slash, player versus player, interactive fiction and online chat.
Players can read or view descriptions of rooms, objects, other players, non-player characters, and
actions performed in the virtual world. Players typically interact with each other and the world by
typing commands that resemble a natural language.* - [Wikipedia](https://en.wikipedia.org/wiki/MUD)

If you are reading this, it's quite likely you are dreaming of creating and running a text-based massively-multiplayer game ([MUD/MUX/MUSH](https://tinyurl.com/c5sc4bm) etc) of your very own. You might just be starting to think about it, or you might have lugged around that *perfect* game in your mind for years ... you know *just* how good it would be, if you could only make it come to reality. 

We know how you feel. That is, after all, why Evennia came to be. 

## What is Evennia?

Evennia is a MU\*-building framework: a bare-bones Python codebase and server intended to be highly extendable for any style of game. 

### Bare-bones?

Evennia is "bare-bones" in the sense that we try to impose as few game-specific things on you as possible. We don't prescribe any combat rules, mob AI, races, skills, character classes or other things. 

We figure you will want to make that for yourself, just like you want it!

### Framework?

Evennia is bare-bones, but not _that_ barebones. We do offer basic building blocks like objects, characters and rooms, in-built channels and so on. We also provide of useful commands for building and administration etc. 

Out of the box you'll have a 'talker' type of game - an empty but fully functional social game where you can build rooms, walk around and chat/roleplay. Evennia handles all the boring database, networking, and behind-the-scenes administration stuff that all online games need whether they like it or not.  It's a blank slate for you to expand on.  

We also include a growing list of optional [contribs](Contribs/Contribs-Overview.md) you can use with your game. These are more game-specific and can help to inspire or have something to build from.

### Server?

Evennia is its own webserver. When you start Evennia, your server hosts a game website and a browser webclient. This allows your players to play both in their browsers as well as connect using traditional MUD clients. None of this is visible to the internet until you feel ready to share your game with the world.

### Python?

[Python](https://en.wikipedia.org/wiki/Python_(programming_language)) is not only one of the most popular programming languages languages in use today, it is also considered one of the easiest to learn. In the Evennia community, we have many people who learned Python or programming by making a game. Some even got a job from the skills they learned working with Evennia! 

All your coding, from object definitions and custom commands to AI scripts and economic systems is  done in normal Python modules rather than some ad-hoc scripting language.

## Can I test it somewhere?

Evennia's demo server can be found at [https://demo.evennia.com](https://demo.evennia.com) or on `demo.evennia.com`, port `4000` if you are using a traditional MUD client.

Once you installed Evennia, you can also create a tutorial mini-game with a single command. Read more about it [here](Howtos/Beginner-Tutorial/Part1/Beginner-Tutorial-Tutorial-World.md).

## What do I need to know to work with Evennia?

Once you [installed Evennia](Setup/Installation.md) and connected, you should decide on what you want to do.

### I don't know (or don't want to do) any programming - I just want to run a game!

Evennia comes with a default set of commands for the Python newbies and for those who need to get a game running *now*. 

Stock Evennia is enough for running a simple 'Talker'-type game - you can build and describe rooms and basic objects, have chat channels, do emotes and other things suitable for a social or free-form MU\*. 

Combat, mobs and other game elements are not included, so you'll have a very basic game indeed if you are not willing to do at least *some* coding.

### I know basic Python, or I am willing to learn

Start small. Evennia's [Beginner tutorial](Howtos/Beginner-Tutorial/Beginner-Tutorial-Overview.md)  is a good place to start. 

```{sidebar}
See also our [link page](./Links.md) for some reading suggestions.
```
While Python is considered a very easy programming language to get into, you do have a learning curve to climb if you are new to programming. The beginner-tutorial has a [basic introduction to Python](Howtos/Beginner-Tutorial/Part1/Beginner-Tutorial-Python-basic-introduction.md), but if you are completely new, you should probably also sit down  with a full Python beginner's tutorial at some point. There are plenty of them on the web if you look around. 

To code your dream game in Evennia you don't need to be a Python guru, but you do need to be able to read example code containing at least these basic Python features:

- Importing and using python [modules](https://docs.python.org/3.11/tutorial/modules.html)
- Using [variables](https://www.tutorialspoint.com/python/python_variable_types.htm), [conditional statements](https://docs.python.org/tutorial/controlflow.html#if-statements), [loops](https://docs.python.org/tutorial/controlflow.html#for-statements) and [functions](https://docs.python.org/tutorial/controlflow.html#defining-functions)
- Using [lists, dictionaries and list comprehensions](https://docs.python.org/tutorial/datastructures.html)
- Doing [string handling and formatting](https://docs.python.org/tutorial/introduction.html#strings)
- Have a basic understanding of [object-oriented programming](https://www.tutorialspoint.com/python/python_classes_objects.htm), using [Classes](https://docs.python.org/tutorial/classes.html), their methods and properties

Obviously, the more things you feel comfortable with, the easier time you'll have to find your way.

With just basic knowledge you can set out to build your game by expanding Evennia's examples.

### I know my Python stuff and I am willing to use it!

Even if you started out as a Python beginner, you will likely get to this point after working on your game for a while.  

With more general knowledge in Python the full power of Evennia opens up for you. Apart from modifying commands, objects and scripts, you can develop everything from advanced mob AI and economic systems, through sophisticated combat and social mini games, to redefining how commands, players, rooms or channels themselves work.   Since you code your game by importing normal Python modules, there are few limits to what you can accomplish.

If you *also* happen to know some web programming (HTML, CSS, Javascript) there is also a web
presence (a website and a mud web client) to play around with ...

## Where to from here?

To get a top-level overview of Evennia, you can check out [Evennia in pictures](./Evennia-In-Pictures.md).

After that it's a good idea to jump into the [Beginner Tutorial](Howtos/Beginner-Tutorial/Beginner-Tutorial-Overview.md). You can either follow it lesson for lesson or jump around to what seems interesting.  There are also more [Tutorials and Howto's](Howtos/Howtos-Overview.md#howtos) to look over.

You can also read the lead developer's [dev blog](https://www.evennia.com/devblog/index.html) for many tidbits and snippets about Evennia's development and structure.

Sometimes it's easier to ask for help. Get engaged in the Evennia community by joining our [Discord](https://discord.gg/AJJpcRUhtF) for direct support. Make an introductory post to our [Discussion forum](https://github.com/evennia/evennia/discussions)  and say hi! See [here](./Contributing.md) for more ways to get and give help to the project.

Welcome to Evennia!