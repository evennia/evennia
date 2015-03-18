# Evennia MUD/MU\* Creation System ![evennia logo][logo]
[![Build Status][travisimg]][travislink]

*Evennia* is a modern library for creating [online multiplayer text
games][wikimudpage] (MUD, MUSH, MUX, MOO etc) in pure Python. It allows game
creators to design and flesh out their games with great freedom.
Evennia is made available under the very friendly [BSD license][license].

http://www.evennia.com is the main hub tracking all things Evennia.


## Features and Philosophy

Evennia aims to supply a bare-bones MU\* codebase that allows vast
flexibility for game designers while taking care of all the gritty
networking and database-handling behind the scenes. Evennia offers an
easy API for handling persistent objects, time-dependent scripting and
all the other low-level features needed to create an online text-based
game. The idea is to allow the mud-coder to concentrate solely on
designing the parts and systems of the mud that makes it uniquely fit
their ideas.

Coding in Evennia is primarily done by normal Python modules, making
the codebase extremely flexible. The code is heavily documented and
you use Python classes to represent your objects, scripts and players.
The database layer is abstracted away.

![screenshot][screenshot]

Evennia offers extensive connectivity options. A single server
instance may offer connections over Telnet, SSH, SSL and HTTP. The
latter is possible since Evennia is also its own web server: A default
website as well as a browser-based comet-style mud client comes as
part of the package.

Due to our Django and Twisted foundations, web integration is
easy since the same code that powers the game may also be used to run
its web presence.

Whereas Evennia is intended to be customized to almost any level you
like, we do offer some defaults you can build from. The code base
comes with basic classes for objects, exits, rooms and characters.
There is also a default command set for handling administration,
building, chat channels, poses and so on. This is enough to run a
'Talker' or some other social-style game out of the box. Stock Evennia
is however deliberately void of any game-world-specific systems. So
you won't find any AI codes, mobs, skill systems, races or combat
stats in the default distribution (we might expand our contributions
folder with optional plugins in the future though).

## Current Status

The codebase is currently in **Beta**. While development continues,
Evennia is already stable enough to be suitable for prototyping and
development of your own games. 

## Where to go from here

If this piqued your interest, there is a [lengthier introduction][introduction] to read.

To learn how to get your hands on the code base, the [Getting started][gettingstarted] page 
is the way to go. Otherwise you could browse
the [Documentation][wiki] or why not come join the [Evennia Community forum][group] 
or join us in our [development chat][chat]. Welcome!


[homepage]: http://www.evennia.com
[gettingstarted]: http://github.com/evennia/evennia/wiki/Getting-Started
[wiki]: https://github.com/evennia/evennia/wiki
[screenshot]: https://raw.githubusercontent.com/wiki/evennia/evennia/images/evennia_screenshot3.png
[logo]: https://github.com/evennia/evennia/blob/master/evennia/web/static/evennia_general/images/evennia_logo.png
[travisimg]: https://travis-ci.org/evennia/evennia.svg?branch=master
[travislink]: https://travis-ci.org/evennia/evennia
[introduction]: https://github.com/evennia/evennia/wiki/Evennia-Introduction
[license]: https://github.com/evennia/evennia/wiki/Licensing
[group]: https://groups.google.com/forum/#!forum/evennia
[chat]: http://webchat.freenode.net/?channels=evennia&uio=MT1mYWxzZSY5PXRydWUmMTE9MTk1JjEyPXRydWUbb
[wikimudpage]: http://en.wikipedia.org/wiki/MUD
