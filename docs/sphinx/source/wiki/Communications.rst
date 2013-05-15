Communications
==============

Apart from moving around in the game world and talking, players might
need other forms of communication. This is offered by Evennia's ``Comm``
system. Stock evennia implements a 'MUX-like' system of channels, but
there is nothing stopping you from changing things to better suit your
taste.

Comms rely on two main database objects - ``Msg`` and ``Channel``.

Msg
---

The ``Msg`` object is the basic unit of communication in Evennia. A
message works a little like an e-mail; it always has a sender (a
`Player <Players.html>`_) and one or more recipients. The recipients may
be either other Players, or a *Channel* (see below). You can mix
recipients to send the message to both Channels and Players if you like.

Once created, a ``Msg`` is normally not changed. It is peristently saved
in the database. This allows for comprehensive logging of
communications, both in channels, but also for allowing
senders/receivers to have 'mailboxes' with the messages they want to
keep.

Properties defined on \`Msg\`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  ``senders`` - this is a reference to one or many
   `Player <Players.html>`_ or `Objects <Objects.html>`_ (normally
   *Characters*) sending the message. This could also be an *External
   Connection* such as a message coming in over IRC/IMC2 (see below).
   There is usually only one sender, but the types can also be mixed in
   any combination.
-  ``receivers`` - a list of target `Players <Players.html>`_,
   `Objects <Objects.html>`_ (usually *Characters*) or *Channels* to
   send the message to. The types of receivers can be mixed in any
   combination.
-  ``header`` - this has a max-length of 128 characters. This could be
   used to store mime-type information for this type of message (such as
   if it's a mail or a page), but depending on your game it could also
   instead be used for the subject line or other types of header info
   you want to track. Being an indexed field it can be used for quick
   look-ups in the database.
-  ``message`` - the actual text being sent.
-  ``date_sent`` - when message was sent (auto-created).
-  ``locks`` - a `lock definition <Locks.html>`_.
-  ``hide_from`` - this can optionally hold a list of objects, players
   or channels to hide this ``Msg`` from. This relationship is stored in
   the database primarily for optimization reasons, allowing for quickly
   post-filter out messages not intended for a given target. There is no
   in-game methods for setting this, it's intended to be done in code.

You create new messages in code using ``ev.create_message`` (or
``src.utils.create.create_message.``)

!TempMsg
--------

``src.comms.models`` contains a class called ``TempMsg`` which mimics
the API of ``Msg`` but is not connected to the database. It's not used
by default but you could use it in code to send non-persistent messages
to systems expecting a ``Msg`` (like *Channels*, see the example in the
next section).

Channels
--------

Channels act as generic distributors of messages. Think of them as
"switch boards" redistributing ``Msg`` objects. Internally they hold a
list of "listening" objects and any ``Msg`` sent to the channel will be
distributed out to all channel listeners. Channels have
`Locks <Locks.html>`_ to limit who may listen and/or send messages
through them.

There are three default channels created in stock Evennia - ``MUDinfo``,
``MUDconnections`` and ``Public``. Two first ones are server-related
messages meant for Admins, the last one is open to everyone to chat on
(all new players are automatically joined to it when logging in, useful
for asking questions). The default channels created are defined by
``settings.CHANNEL_PUBLIC``, ``settings.CHANNEL_MUDINFO`` and
``settings.CHANNEL_CONNECTINFO``.

You create new channels with ``ev.create_channel`` (or
``src.utils.create.create_channel``).

In code, messages are sent to a channel using the ``msg`` or ``tempmsg``
methods of channels:

::

     channel.msg(msgobj, header=None, senders=None, persistent=True)

The argument ``msgobj`` can be a previously constructed ``Msg`` or
``TempMsg`` - in that case all the following keywords are ignored. If
``msgobj`` is a string, the other keywords are used for creating a new
``Msg`` or ``TempMsg`` on the fly, depending on if ``persistent`` is set
or not.

::

    # assume we have a 'sender' object and a channel named 'mychan'

    # send and store Msg in database 
    from src.utils import create
    mymsg = create.create_message(sender, "Hello!", channels=[mychan])
    # use the Msg object directly, no other keywords are needed
    mychan.msg(mymsg)

    # create a Msg automatically behind the scenes
    mychan.msg("Hello!", senders=[sender])

    # send a non-persistent TempMsg (note that the senders 
    # keyword can also be used without a list if there is
    # only one sender)
    mychan.msg("Hello!", senders=sender, persistent=False)

    # this is a shortcut that always sends a non-persistent TempMsg
    # also if a full Msg was supplied to it (it also creates TempMsgs
    # on the fly if given a string).
    mychan.tempmsg(mymsg)

On a more advanced note, when a player enters something like
``ooc Hello!`` (where ``ooc`` is the name/alias of a channel), this is
treated as a `System Command <Commands.html>`_ by Evennia. You may
completely customize how this works by defining a system command with
your own code. See `Commands <Commands.html>`_ for more details.

Properties defined on \`Channel\`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` - main name for channel
-  ``aliases`` - alternative native names for channels
-  ``desc`` - optional description of channel (seen in listings)
-  ``keep_log`` (bool) - if the channel should store messages (default)
-  ``locks`` - A `lock definition <Locks.html>`_. Channels normally use
   the access\_types ``send, admin`` and ``listen``.

External Connections
====================

Channels may also communicate through what is called an *External
Connection*. Whereas normal users send messages through in-game Evennia
commands, an external connection instead takes data from a remote
location. `IMC2 <IMC2.html>`_ and `IRC <IRC.html>`_ connections make use
of this.
