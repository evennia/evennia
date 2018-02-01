# Evennia MUD/MU\* Creation System ![evennia logo][logo]
[![Build Status][travisimg]][travislink] [![Coverage Status][coverimg]][coverlink]

*Evennia* is a modern library for creating [online multiplayer text
games][wikimudpage] (MUD, MUSH, MUX, MUCK, MOO etc) in pure Python. It
allows game creators to design and flesh out their ideas with great
freedom. Evennia is made available under the very friendly [BSD
license][license].

http://www.evennia.com is the main hub tracking all things Evennia.


## Features and Philosophy

The Evennia library aims for you to have a fully functioning, if
empty, online game up and running in minutes. Rather than imposing a
particular style, genre or game mechanic we offer a framework on which
you build the game of your dreams. The idea is to allow you to
concentrate on designing the bits that make your game unique.

Coding in Evennia is done using normal Python modules imported into
the server at runtime. All library code is heavily documented and
Evennia comes with extensive manuals and tutorials. You use Python
classes to represent your objects, scripts, players, in-game channels
and so on. The database layer is abstracted away. This makes it
possible to create the game using modern code practices using the full
flexibility and power of Python.

![screenshot][screenshot]

Evennia offers extensive connectivity options, including traditional
telnet connections. Evennia is also its own web server: A default
website as well as a browser-based mud client (html5 websockets, with
fallback to AJAX) runs by default. Due to our Django and Twisted
foundations, web integration is easy since the same code powering the
game is also used to run its web presence.

Whereas Evennia is intentionally empty of game content from the onset,
we *do* offer some defaults you can build from. The code base comes
with basic classes for objects, exits, rooms and characters. There are
systems for handling puppeting, scripting, timers, dynamic games
states etc. A default command set (completely replaceable with your
own syntax and functionality) handles administration, building, chat
channels, poses and so on. The default setup is enough to run a
'Talker' or some other social-style game out of the box. We also have
a contributions folder with optional plugins and examples of more
game-specific systems.

## Current Status

The codebase is currently in **Beta**. While development continues,
Evennia is already stable enough to be suitable for prototyping and
development of your own games.

## Where to go from here

If this piqued your interest, there is a [lengthier
introduction][introduction] to read.

To learn how to get your hands on the code base, the [Getting
started][gettingstarted] page is the way to go. Otherwise you could
browse the [Documentation][wiki] or why not come join the [Evennia
Community forum][group] or join us in our [development chat][chat].
Welcome!


[homepage]: http://www.evennia.com
[gettingstarted]: http://github.com/evennia/evennia/wiki/Getting-Started
[wiki]: https://github.com/evennia/evennia/wiki
[screenshot]: https://user-images.githubusercontent.com/294267/30773728-ea45afb6-a076-11e7-8820-49be2168a6b8.png
[logo]: https://github.com/evennia/evennia/blob/master/evennia/web/website/static/website/images/evennia_logo.png
[travisimg]: https://travis-ci.org/evennia/evennia.svg?branch=master
[travislink]: https://travis-ci.org/evennia/evennia
[coverimg]: https://coveralls.io/repos/github/evennia/evennia/badge.svg?branch=master
[coverlink]: https://coveralls.io/github/evennia/evennia?branch=master
[introduction]: https://github.com/evennia/evennia/wiki/Evennia-Introduction
[license]: https://github.com/evennia/evennia/wiki/Licensing
[group]: https://groups.google.com/forum/#!forum/evennia
[chat]: http://webchat.freenode.net/?channels=evennia&uio=MT1mYWxzZSY5PXRydWUmMTE9MTk1JjEyPXRydWUbb
[wikimudpage]: http://en.wikipedia.org/wiki/MUD
