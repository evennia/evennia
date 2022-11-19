# Evennia MUD/MU\* Creation System ![][logo]
[![Build Status][unittestciimg]][unittestcilink] [![Coverage Status][coverimg]][coverlink]


*Evennia* is a modern library for creating [online multiplayer text
games][wikimudpage] (MUD, MUSH, MUX, MUCK, MOO etc) in pure Python. It
allows game creators to design and flesh out their ideas with great
freedom.

Evennia does not impose a particular style, genre or game mechanic. Instead it
solves the boring networking and provides a framework for you to build the game
you want. Coding in Evennia is done using normal Python modules imported into
the server at runtime. All library code is heavily documented. Evennia has
extensive manuals and tutorials as well as a very active support community!

## Installation

    pip install evennia
    evennia --init mygame
    cd mygame
    evennia migrate
    evennia start / stop / reload

Next, browse to http://localhost:4001 or telnet to localhost port 4000 to see your working (if empty) game!

- https://www.evennia.com is the main hub tracking all things Evennia.
- [Here is a shortcut to the documentation and tutorials](https://www.evennia.com/docs/latest/)

![screenshot][screenshot]

## Current Status

The codebase is currently in **Beta**. While development continues,
Evennia is already stable enough to be suitable for prototyping and
development of your own games.

## Where to go from here

If this piqued your interest, there is a [lengthier
introduction][introduction] to read.

To learn how to get your hands on the code base, the [Getting
started][gettingstarted] page is the way to go. Otherwise you could
browse the [Documentation][docs] or why not come join the [Evennia
Community forum][group] or join us in our [development chat][chat].
Welcome!


[homepage]: https://www.evennia.com
[gettingstarted]: https://www.evennia.com/docs/latest/Getting-Started.html
[docs]: https://www.evennia.com/docs/latest
[screenshot]: https://user-images.githubusercontent.com/294267/30773728-ea45afb6-a076-11e7-8820-49be2168a6b8.png
[logo]: https://github.com/evennia/evennia/blob/master/evennia/web/website/static/website/images/evennia_logo.png
[unittestciimg]: https://github.com/evennia/evennia/workflows/test-suite/badge.svg
[unittestcilink]: https://github.com/evennia/evennia/actions?query=workflow%3Atest-suite
[coverimg]: https://coveralls.io/repos/github/evennia/evennia/badge.svg?branch=master
[coverlink]: https://coveralls.io/github/evennia/evennia?branch=master
[introduction]: https://www.evennia.com/docs/latest/Evennia-Introduction.html
[license]: https://www.evennia.com/docs/latest/Licensing.html
[group]: https://github.com/evennia/evennia/discussions
[chat]: https://discord.gg/AJJpcRUhtF
[wikimudpage]: http://en.wikipedia.org/wiki/MUD
