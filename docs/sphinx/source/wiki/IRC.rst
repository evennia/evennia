IRC
===

`IRC (Internet Relay
Chat) <http://en.wikipedia.org/wiki/Internet_Relay_Chat>`_ is a long
standing chat protocol used by many open-source projects for
communicating in real time. By connecting one of Evennia's
`Channels <Communications.html>`_ to an IRC channel you can communicate
also with people not on an mud themselves. Note that you can use IRC
also if you are only running your Evennia MUD locally on your computer
(your game don't need to be open to the public)! All you need is an
internet connection. For IRC operation you also need
`twisted.words <http://twistedmatrix.com/trac/wiki/TwistedWords>`_. This
is available simply as a package *python-twisted-words* in many Linux
distros, or directly downloadable from the link.

Configuring IRC
---------------

To configure IRC, you'll need to activate it in your settings file. You
do this by copying the ``IRC_ENABLED`` flag from
``evennia/src/config_defaults.py`` into your
``evennia/game/settings.py`` and setting it to ``True``.

Start Evennia and log in as a privileged user. You should now have a new
command availabele: ``@irc2chan``. This command is called like this:

::

     @irc2chan[/switches] <evennia_channel> = <ircnetwork> <port> <#irchannel> <botname>

If you already know how IRC works, this should be pretty self-evident to
use. Read the help entry for more features.

Setting up IRC, step by step
----------------------------

You can connect IRC to any Evennia channel, but for testing, let's set
up a new channel ``irc``.

::

     @ccreate irc = This is connected to an irc channel!

You will automatically join the new channel.

Next we will create a connection to an external IRC network and channel.
There are many, many IRC nets.
`Here <http://www.irchelp.org/irchelp/networks/popular.html>`_ is a list
of some of the biggest ones, the one you choose is not really very
important unless you want to connect to a particular channel (also make
sure that the network allows for "bots" to connect).

For testing, we choose the *Freenode* network, ``irc.freenode.net``. We
will connect to a test channel, let's call it *#myevennia-test* (an IRC
channel always begins with ``#``). It's best if you pick an obscure
channel name that didn't exist previously - if it didn't exist it will
be created for you. *Don't* connect to ``#evennia``, that is Evennia's
official chat channel!

A *port* needed depends on the network. For Freenode this is ``6667``.

What will happen is that your Evennia server will connect to this IRC
channel as a normal user. This "user" (or "bot") needs a name, which you
must also supply. Let's call it "mud-bot".

To test that the bot connects correctly you also want to log onto this
channel with a separate, third-party IRC client. There are hundreds of
such clients available. If you use Firefox, the *Chatzilla* plugin is
good and easy. There are also web-based clients like *Mibbit* that you
can try. Once you have connected to a network, the command to join is
usually ``/join channelname`` (don't forget the #).

Next we connect Evennia with the IRC channel.

::

     @irc2chan irc = irc.freenode.net 6667 #myevennia-test mud-bot

Evennia will now create a new IRC bot ``mud-bot`` and connect it to the
IRC network and the channel #myevennia. If you are connected to the IRC
channel you will soon see the user *mud-bot* connect.

Write something in the Evennia channel *irc*.

::

     irc Hello, World!
    [irc] Anna: Hello, World!

If you are viewing your IRC channel with a separate IRC client you
should see your text appearing there, spoken by the bot:

::

    mud-bot> [irc] Anna: Hello, World!

Write ``Hello!`` in your IRC client window and it will appear in your
normal channel, marked with the name of the IRC channel you used
(#evennia here).

::

     
    [irc] Anna@#myevennia-test: Hello!

Your Evennia gamers can now chat with users on external IRC channels!

Talking between IRC and IMC
---------------------------

You can easily connect IRC and IMC by simply connecting them to the same
Evennia channel. IMC connections are described `here <IMC2.html>`_.
