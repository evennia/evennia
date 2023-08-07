# Evennia MUD/MU\* Creation System ![][logo]
[![unittestciimg]][unittestcilink] [![Coverage Status][coverimg]][coverlink] [![Pypi Version][pypibadge]][pypilink]


[Evennia][homepage] is a modern library for creating [online multiplayer text
games][wikimudpage] (MUD, MUSH, MUX, MUCK, MOO etc) in pure Python. It
allows game creators to design and flesh out their ideas with great
freedom.

Evennia does not impose a particular style, genre or game mechanic. Instead it
solves the boring networking and basic stuff all online games need. It provides
a framework and tools for you to build the game you want. Coding in Evennia is
done using normal Python modules imported into the server at runtime.

Evennia has [extensive documentation][docs]. It also has a very active community
with [discussion forums][group] and a [discord server][chat] to help and support you!

## Installation

    pip install evennia
        (windows users once: py -m evennia)
    evennia --init mygame
    cd mygame
    evennia migrate
    evennia start / stop / reload

See [the full installation instructions][installation] for more help.

Next, browse to `http://localhost:4001` or use your third-party mud client to
connect to `localhost`, port `4000` to see your working (if empty) game!

![screenshot][screenshot]
_A game website is created automatically. Connect to your Evennia game from your
web browser as well as using traditional third-party clients_.

## Where to go next

If this piqued your interest, there is a [lengthier introduction][introduction] to read. You
can also read our [Evennia in pictures][evenniapictures] overview. After that,
why not check out the [Evennia Beginner tutorial][beginnertutorial].

Welcome!


[homepage]: https://www.evennia.com
[docs]: https://www.evennia.com/docs/latest
[screenshot]: https://user-images.githubusercontent.com/294267/205434941-14cc4f59-7109-49f7-9d71-0ad3371b007c.jpg
[logo]: https://github.com/evennia/evennia/blob/master/evennia/web/website/static/website/images/evennia_logo.png
[unittestciimg]: https://github.com/evennia/evennia/workflows/test-suite/badge.svg
[unittestcilink]: https://github.com/evennia/evennia/actions?query=workflow%3Atest-suite
[coverimg]: https://coveralls.io/repos/github/evennia/evennia/badge.svg?branch=main
[coverlink]: https://coveralls.io/github/evennia/evennia?branch=main
[pypibadge]: https://img.shields.io/pypi/v/evennia?color=blue
[pypilink]: https://pypi.org/project/evennia/
[introduction]: https://www.evennia.com/docs/latest/Evennia-Introduction.html
[license]: https://www.evennia.com/docs/latest/Licensing.html
[group]: https://github.com/evennia/evennia/discussions
[chat]: https://discord.gg/AJJpcRUhtF
[wikimudpage]: http://en.wikipedia.org/wiki/MUD
[evenniapictures]: https://www.evennia.com/docs/latest/Evennia-In-Pictures.html
[beginnertutorial]: https://www.evennia.com/docs/latest/Howtos/Beginner-Tutorial/Beginner-Tutorial-Overview.html
[installation]: https://www.evennia.com/docs/latest/Setup/Setup-Overview.html#installation-and-running
