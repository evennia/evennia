    "*A MUD (originally Multi-User Dungeon, with later variants
    Multi-User Dimension and Multi-User Domain), pronounced 'mud', is a
    multiplayer real-time virtual world described primarily in text.
    MUDs combine elements of role-playing games, hack and slash, player
    versus player, interactive fiction, and online chat. Players can
    read or view descriptions of rooms, objects, other players,
    non-player characters, and actions performed in the virtual world.
    Players typically interact with each other and the world by typing
    commands that resemble a natural language.*\ " -
    `Wikipedia <http://en.wikipedia.org/wiki/MUD>`_

Evennia introduction
====================

If you are reading this, it's quite likely you are dreaming of creating
and running a text-based massively-multiplayer game
(`MUD/MUX/MUSH <http://tinyurl.com/c5sc4bm>`_ etc) of your very own. You
might just be starting to think about it, or you might have lugged
around that *perfect* game in your mind for years ... you know *just*
how good it would be, if you could only make it come to reality. We know
how you feel. That is, after all, why Evennia came to be.

Evennia is in principle a MUD-building system: a bare-bones Python
codebase and server intended to be highly extendable for any style of
game. "Bare-bones" in this context means that we try to impose as few
game-specific things on you as possible. So whereas we for convenience
offer basic building blocks like objects, characters, rooms, default
commands for building and administration etc, we don't prescribe any
combat rules, mob AI, races, skills, character classes or other things
that will be different from game to game anyway. It is possible that we
will offer some such systems as contributions in the future, but these
will in that case all be optional.

What we *do* however, is to provide a solid foundation for all the
boring database, networking, and behind-the-scenes administration stuff
that all online games need whether they like it or not. Evennia is
*fully persistent*, that means things you drop on the ground somewhere
will still be there a dozen server reboots later. Through Django we
support a large variety of different database systems (a database is
created for you automatically if you use the defaults).

Using the full power of Python throughout the server offers some
distinct advantages. All your coding, from object definitions and custom
commands to AI scripts and economic systems is done in normal Python
modules rather than some ad-hoc scripting language. The fact that you
script the game in the same high-level language that you code it in
allows for very powerful and custom game implementations indeed.

The server ships with a default set of player commands that are similar
to the MUX command set. We *do not* aim specifically to be a MUX server,
but we had to pick some default to go with (see `this <SoftCode.html>`_
for more about our original motivations). It's easy to remove or add
commands, or to have the command syntax mimic other systems, like Diku,
LP, MOO and so on. Or why not create a new and better command system of
your own design.

Can I test it somewhere?
------------------------

There are Evennia-based muds under development but they are still not
publicly available. If you do try to install Evennia (it's not hard), it
comes with its own tutorial though - this shows off some of the
possibilities *and* gives you a small single-player quest to play. The
tutorial takes only one single in-game command to install as explained
`here <TutorialWorldIntroduction.html>`_.

If you didn't see it before, here is also a
`screenshot <Screenshot.html>`_ of Evennia running.

Brief summary of features
=========================

Technical
---------

-  Game development is done by the server importing your normal Python
   modules. Specific server features are implemented by overloading
   hooks that the engine calls appropriately.
-  All game entities are simply Python classes that handles database
   negotiations behind the scenes without you needing to worry.
-  Command sets are stored on individual objects (including characters)
   to offer unique functionality and object-specific commands. Sets can
   be updated and modified on the fly to expand/limit player input
   options during play.
-  Scripts are used to offer asynchronous/timed execution abilities.
   Scripts can also be persistent. There are easy mechanisms to thread
   particularly long-running processes.
-  In-game communication channels are modular and can be modified to any
   functionality, including mailing systems and full logging of all
   messages.
-  Server can be fully rebooted/reloaded without users disconnecting.
-  A session (player) can freely connect/disconnect from game-objects,
   offering an easy way to implement multi-character systems and
   puppeting.
-  All source code is extensively documented.
-  Unit-testing suite, including tests of default commands and plugins

Default content
---------------

-  Basic classes for Objects, Characers, Rooms and Exits
-  Basic login system, using the Player's login name as their in-game
   Character's name for simplicity
-  "MUX-like" command set with administration, building, puppeting,
   channels and social commands
-  In-game Tutorial
-  Contributions folder with working, but optional, code such as
   alternative login, menus, character generation and more

Standards/Protocols supported
-----------------------------

-  Telnet with mud-specific extensions (MCCP, MSSP, TTYPE)
-  SSH
-  SSL
-  TCP/Comet, JavaScript browser webclient included
-  HTTP - Website served by in-built webserver and connected to same
   database as game.
-  IRC/IMC2 - external IRC and/or IMC2 channels can be connected to
   in-game chat channels
-  RSS feeds can be echoed to in-game channels
-  ANSI, xterm256 colours
-  Several different databases supported (SQLite3, MySQL, ...)

For more extensive feature information, see
`here <http://code.google.com/p/evennia/wiki/DeveloperCentral>`_.

What you need to know to work with Evennia
==========================================

Assuming you have Evennia working (see the `quick start
instructions <GettingStarted.html>`_) and have gotten as far as to start
the server and connect to it with the client of your choice, here's what
you need to know depending on your skills and needs.

I don't know (or don't want to do) any programming - I just want to run a game!
-------------------------------------------------------------------------------

Evennia comes with a default set of commands for the Python newbies and
for those who need to get a game running *now*. Stock Evennia is enough
for running a simple 'Talker'-type game - you can build and describe
rooms and basic objects, have chat channels, do emotes and other things
suitable for a social or free-form MU\ ``*``. Combat, mobs and other
game elements are not included, so you'll have a very basic game indeed
if you are not willing to do at least *some* coding.

I know basic Python, or am willing to learn
-------------------------------------------

Evennia's source code is extensively documented and `viewable
online <http://code.google.com/p/evennia/source/browse/>`_. We also have
a comprehensive `online
manual <http://code.google.com/p/evennia/wiki/Index>`_ with lots of
examples. But while Python is a relatively easy programming language, it
still represents a learning curve if you are new to programming. You
should probably sit down with a Python beginner's
`tutorial <http://docs.python.org/tutorial/>`_ (there are plenty of them
on the web if you look around) so you at least know what you are seeing.
To efficiently code your dream game in Evennia you don't need to be a
Python guru, but you do need to be able to read example code containing
at least these basic Python features:

-  Importing python modules
-  Using variables, `conditional
   statements <http://docs.python.org/tutorial/controlflow.html#if-statements>`_,
   `loops <http://docs.python.org/tutorial/controlflow.html#for-statements>`_
   and
   `functions <http://docs.python.org/tutorial/controlflow.html#defining-functions>`_
-  Using `lists, dictionaries and list
   comprehensions <http://docs.python.org/tutorial/datastructures.html>`_
-  Doing `string handling and
   formatting <http://docs.python.org/tutorial/introduction.html#strings>`_
-  Using `Classes <http://docs.python.org/tutorial/classes.html>`_,
   their methods and properties

Obviously, the more things you feel comfortable with, the easier time
you'll have to find your way. With just basic knowledge you should be
able to define your own `Commands <Commands.html>`_, create custom
`Objects <Objects.html>`_ as well as make your world come alive with
basic `Scripts <Scripts.html>`_. You can definitely build a whole
advanced and customized game from extending Evennia's examples only.

I know my Python stuff and am willing to use it!
------------------------------------------------

Even if you started out as a Python beginner, you will likely get to
this point after working on your game for a while. With more general
knowledge in Python the full power of Evennia opens up for you. Apart
from modifying commands, objects and scripts, you can develop everything
from advanced mob AI and economic systems, through sophisticated combat
and social minigames, to redefining how commands, players, rooms or
channels themselves work. Since you code your game by importing normal
Python modules, there are few limits to what you can accomplish.

If you *also* happen to know some web programming (HTML, CSS,
Javascript) there is also a web presence (a website and an mud web
client) to play around with ...

From here you can continue to the `Index <Index.html>`_ to find more
info about Evennia.
