Evennia coding introduction
===========================

Evennia allows for a lot of freedom when designing your game - but to
code efficiently you still need to adopt some best practices as well as
find a good place to start to learn.

Here are some pointers to get you going.

Code in \`game/gamesrc\`, not in \`src/\`
-----------------------------------------

You will create and code your game by adding Python modules in
``game/gamesrc/`` (see the `directory
overview <DirectoryOverview.html>`_). This is your home. You should
*never* need to modify anything under ``src/`` (anything you download
from us, really). Treat ``src/`` as a kind of library. You import useful
functionality from here. If you see code you like, copy&paste it out
into ``game/gamesrc`` and edit it there.

If you find that ``src/`` *doesn't* support some functionality you need,
make a `Feature
Request <https://code.google.com/p/evennia/issues/list>`_ about it. Same
goes for `bugs <https://code.google.com/p/evennia/issues/list>`_. If you
add features or fix bugs yourself, please consider
`contributing <Contributing.html>`_ your changes upstream!

Learn with \`ev\`
-----------------

Learn the `ev interface <evAPI.html>`_. This is a great way to explore
what Evennia has to offer. For example, start an interactive python
shell, import ``ev`` and just look around.

You can compliment your exploration by peeking at the sections of the
much more detailed `Developer Central <DeveloperCentral.html>`_. The
`Tutorials <Tutorials.html>`_ section also contains a growing collection
of system- or implementation-specific help.

Plan before you code
--------------------

Before you start coding away at your dream game, take a look at our
`game planning hints and tips <GamePlanning.html>`_ page. It might
hopefully help you avoid some common pitfalls and time sinks.

Docs are here to help you
-------------------------

Some people find reading documentation extremely dull and shun it out of
principle. That's your call, but reading docs really *does* help you,
promise! Evennia's documentation is pretty thorough and knowing what is
possible can often give you a lot of new cool game ideas. That said, if
you can't find the answer in the docs, don't be shy to ask questions!
The `discussion
group <https://sites.google.com/site/evenniaserver/discussions>`_ and
the `irc chat <http://webchat.freenode.net/?channels=evennia>`_ are
there for you.

The most important point
------------------------

And finally, of course, have fun!
