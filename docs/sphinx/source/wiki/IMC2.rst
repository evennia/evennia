IMC2
====

`IMC2 <http://en.wikipedia.org/wiki/InterMUD>`_, *InterMud
Communications, protocol version 2*, is a protocol that allows
individual mud games (Evennia-powered or not) to connect to a remote
server for the purpose of IRC-like communication with other games. By
connecting your MUD to IMC, you and your admins/players will be able to
communicate with players on other muds connected to the network! Note
that you can use IMC2 also if your Evennia install is only running
locally on your computer -all you need is an internet connection.

Evennia's IMC implementation is special in that it integrates Evennia's
normal channel system with IMC. The basic principle is that you
"connect" an IMC channel to an existing Evennia channel. Users on the
IMC network will then see what is said on the channel and vice versa.

Joining the IMC network
-----------------------

To configure IMC, you first need to activate it by setting
``IMC2_ENABLED=True`` in your settings file. This will make several new
IMC-related commands available to a privileged user. Since the IMC
network will need to know your mud's name, make sure you have also set
``settings.SERVERNAME`` to the mud name you want.

Next you need to register your mud at a IMC2 network. We suggest the
`MudBytes IMC2 network <http://www.mudbytes.net/intermud>`_. You can
join for free
`here <http://www.mudbytes.net/imc2-intermud-join-network>`_. On that
page, follow the following steps:

#. From the drop-down list, select "Other unsupported IMC2 version",
   then click Submit
#. You will get to a form. In "Short Mud name" you need to enter the
   name of your mud as defined by ``settings.SERVERNAME``.
#. Give client- and server passwords to anything you want, but remember
   them.
#. Give an admin e-mail. This shouldn't be too critical.
#. Choose a server. It shouldn't really matter which you choose, as long
   as you remember what you picked (Evennia's development channel
   ``ievennia`` is found on ``Server01``). Click "Join".

You have now created an account on the Mudbytes IMC network and are
ready to go on.

Now fill in the rest of the IMC2 information in your settings file -
give the network name and port, as well as the client- and server
passwords you used when registering on mudbytes.

For testing, you can connect your mud client to the IMC mini-mud called
*Talon* on ``talon.mudbytes.net:2000``. This works pretty much like an
IRC client.

Creating an Evennia channel
---------------------------

Evennia maps in-game channels to remote IMC channels. This means that
you get all of the features of the local comm system for remote IMC
channels as well (channel history, permissions-based channel entry,
etc.)

Let's create a dedicated Evennia channel to host imc communications (you
could also use an existing channel like ``ooc`` if you wanted):

::

     @ccreate imc2 = This is connected to an IMC2 channel!

You should join the channel automatically.

Setting up a Channel \`<->\` IMC2 binding
-----------------------------------------

Evennia developers have an open-access IMC channel called ``ievennia``
on ``Server01`` of the Mudbytes network. For Evennia development we
recommend you connect to this for sharing evennia anecdotes!

Activating IMC2 have made new commands available, the one you need is
``@imc2chan``. You use this to create a permanent link between an IMC
channel and an existing Evennia channel of your choice. You can use the
``imcchanlist`` to see which IMC channels are available on the network.

    Let's connect our new ``imc2`` channel to the ``ievennia`` channel
    on Server01.

::

     @imc2chan imc2 = ievennia

To test, use the IMC mud *Talon*, make sure you "listen" to
``ievennia``, then write something to the channel. You should see the
text appear in Evennia's ``imc2`` channel and vice versa.

Administration and notes
------------------------

You can view all your IMC-to-Evennia mappings using ``@imc2chan/list``.
To permanently remove a connection, use ``@imc2chan`` with the
``/delete`` switch like this:

::

     @imc2chan/delete imc2 = ievennia

A single Evennia channel may *listen* to any number of remote IMC
channels. Just use ``@imc2chan`` to add more connections. Your channel
can however only ever *send* to one IMC2 channel and that is the first
one you link to it (``ievennia`` in this example).

The ``@imclist`` command will list all other MUDs connected to the
network (not including yourself).

Talk between IRC and IMC
------------------------

This is easy - just bind IMC to the same evennia channel that IRC binds
to. The process of binding IRC channels is described in more detail
`here <IRC.html>`_.
