On MUX and Softcode: A brief overview
=====================================

Evennia was originally created in order to provide a MUX/MUSH-style
development environment without the kludgery of softcode. Although it
has since grown to be adaptable to any style of MU\ ``*`` it still ships
with 'MUX-like' default commands.

This document will provide a quick overview of what softcode is, why it
drove us to write Evennia, and why we instead use Python.

Softcode is a very simple programming language that was created for
in-game development on TinyMUD derivatives such as MUX, PennMUSH,
TinyMUSH, and RhostMUSH. The idea is that by providing a stripped down,
minimalistic language for in-game use, you can allow quick and easy
building and game development to happen without having to learn C/C++.
There is an added benefit of not having to have to hand out shell access
to all developers, and permissions can be used to alleviate many
security problems.

Writing and installing softcode is done through a MUD client. As is
such, it is not a formatted language. Each softcode function is a single
line of varying size. Some functions can be a half of a page long due to
this, which is obviously not very readable. The lack of formatting is
one of the big reasons Evennia exists today. Bigger projects tend to
choke under their own weight after time unless your entire staff has a
good understanding of functional programming practices.

Examples of Softcode
--------------------

Here is a simple 'Hello World!' command:

::

    @set me=HELLO_WORLD.C:$hello:@pemit %#=Hello World!

Pasting this into a MUX/MUSH and typing 'hello' will theoretically yield
'Hello World!', assuming certain flags are not set on your player
object.

Setting attributes is done via ``@set``. Softcode also allows the use of
the ampersand (``&``) symbol. This shorter version looks like this:

::

    &HELLO_WORLD.C me=$hello:@pemit %#=Hello World!

Perhaps I want to break the Hello World into an attribute which is
retrieved when emitting:

::

    &HELLO_VALUE.D me=Hello World
    &HELLO_WORLD.C me=$hello:@pemit %#=[v(HELLO_VALUE.D)]

The v() function returns the HELLO\_VALUE.D attribute on the object that
the command resides (``me``, which is yourself in this case). This
should yield the same output as the first example.

If you are still curious about how Softcode works, take a look at some
external resources:

-  `http://www.tinymux.com/wiki/index.php/Softcode <http://www.tinymux.com/wiki/index.php/Softcode>`_
-  `http://www.duh.com/discordia/mushman/man2x1 <http://www.duh.com/discordia/mushman/man2x1>`_

Problems with Softcode
----------------------

Softcode is excellent at what it was intended for: simple things. It is
an incredible tool if used for its intended purposes - an interactive
object, a room with ambiance, simple global commands, simple economies
and coded systems. However, once you start to try to write something
like a complex combat system or a higher end economy, you're likely to
find yourself buried under a mountain of functions that span various
objects and are of various length.

Not to mention, softcode is not an inherently fast language. It is not
compiled, it is parsed with each calling of a function. While MUX and
MUSH parsers have jumped light years ahead of where they were even seven
or eight years ago, they can still stutter under the weight of the more
complex systems if not designed properly.

Changing Times
--------------

Now that starting text-based games is easy and an option for even the
most technically inarticulate, new projects are a dime a dozen. People
are starting new MUDs every day with varying levels of commitment and
ability. Because of this shift from fewer, larger, well-staffed games to
a bunch of small, one or two developer games, some of the benefit of
softcode fades.

Softcode is great in that it allows a mid to large sized staff all work
on the same game without stepping on one another's toes. As mentioned
before, shell access is not necessary to develop a MUX or a MUSH.
However, now that we are seeing a lot more small, one or two-man shops,
the issue of shell access and stepping on each other's toes is a lot
less.

Our Solution
============

For the hobbyist who would like the option to use a full-featured
language, we created Evennia. We are no longer bound to single lines of
softcode. Game developers now have access to the entire library of
Python modules out there in the wild. Our complex systems may be
organized neatly into modules, sub-modules, or even broken out into
entire Python packages.

So what is *not* included in Evennia proper is a MUX/MOO-like online
player building system. Advanced coding and building in Evennia is
primarily intended to be done outside the game, in full-fledged Python
modules. We feel that with a small development team you are better off
using a professional source-control system (svn, git, bazaar, mercurial
etc) anyway.

Your Solution
=============

Adding very advanced and flexible building commands to your game will
probably often be enough to satisfy most creative builders. However, if
you really, *really* want to offer online coding there is of course
nothing stopping you from adding that to Evennia, no matter our
recommendations. You could even re-implement MUX' softcode in Python
should you be very ambitious.

There is an experimental restricted python environment named *Evlang* to
be found in our *contrib* folder. Being in this folder means it's not a
part of the core server and is completely optional to use. Evlang could
serve as a starting point if you want to go down the route of simple
online player coding.
