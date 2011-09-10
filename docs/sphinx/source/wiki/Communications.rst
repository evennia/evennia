<wiki:toc max*depth*

"3" />
======

Communications

Apart from moving around in the game world and talking, players might
need other forms of communication. This is offered by Evennia's ``Comm``
system. Stock evennia implements a 'MUX-like

::

    system of channels, but there is nothing stopping you from changing things to better suit your taste. Comms rely on two main database objects -

Msg``and``Channel

::

    . == Msg ==The

Msg

::

    object is the basic unit of communication in Evennia. A message works a little like an e-mail; it  always has a sender (a [Players Player]) and one or more recipients. The recipients may be either other Players,  or a _Channel_ (see below). You can mix recipients to send the message to both Channels and Players if you like.Once created, a

Msg

::

    is normally not changed. It is peristently saved in the database. This allows for comprehensive  logging of communications, both in channels, but also for allowing senders/receivers to have 'mailboxes' with  the messages they want to keep. === Properties defined on

Msg

::

    === *

sender

::

    - this is a reference to a unique [Players Player] object sending the message.  *

receivers

::

    - a list of target [Players] to send to.  *

channels

::

    - a list of target Channels to send to.  *

message

::

    - the actual text being sent  *

datesent

::

    - when message was sent.  *

locks

::

    - a [Locks lock definition].  The following is currently unimplemented in Evennia (stay tuned):   * hide_from_sender - bool if message should be hidden from sender   * hide_from_receivers - list of receiver objects to hide message from  * hide_from_channels - list of channels objects to hide message fromYou create new messages in code using

src.utils.create.create*message.*

::

    ===!TempMsg===

src.objects.models``contains a class called``TempMsg``that mimics a``Msg``but does not get saved to the database and do not require a sender object of a certain type. It's not used by default, but you could use it in code to send one-off messages to systems expecting a``Msg

::

    .== Channels == Channels act as generic distributors of messages. Players _subscribe_ to channels and can then send and receive message from it. Channels have [Locks] to limit who may join them. There are three default channels created in stock Evennia -

MUDinfo``,``MUDconnections``and``Public

::

    . Two first ones are server-related messages meant for Admins, the last one is open to everyone to  chat on (all new players are automatically joined to it when logging in, useful for asking questions). You create new channels with

src.utils.create.createchannel()

::

    .In code, messages are sent to a channel using the

msg(message, fromobj

None)``method. The argument``message``can either be a previously constructed``Msg``object or a message string. If you send a text string, you should usually also define``fromobj``; a``Msg``object will then be created for you behind the scenes. If you don't supply``from\_obj``, just the string will be sent to the channel and nothing will be stored in the database (could be useful for certain spammy error messages). You can also use``channel.tempmsg()``to always send a non-persistent message, also if you send it a``Msg

::

    object.# assume we have a 'sender' object and a channel named 'mychan'# send and store in database  from src.utils import create mymsg = create.create_message(sender, "Hello!", channels=[mychan]) mychan.msg(mymsg)# send a one-time message mychan.msg("Hello!")# send a one-time message created from a Msg object mychan.tempmsg(mymsg)

As a more advanced note, sending text to channels is a "special
exception" as far as commands are concerned, and you may completely
customize how this works by defining a *system*command\_ with your own
code. See `Commands <Commands.html>`_ for more details.

Properties defined on ``Channel``
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
