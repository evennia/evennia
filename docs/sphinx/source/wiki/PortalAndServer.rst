Portal and Server layout
========================

Evennia consists of two processes, known as *Portal* and *Server*. They
can be controlled from inside the game or from the command line as
described `here <StartStopReload.html>`_.

If you are new to the concept, the main purpose of separating the two is
to have players connect to the Portal but keep the MUD running on the
Server. This way one can restart/reload the game (the Server part)
without Players getting disconnected.

|image0|

The Server and Portal are glued together via an AMP (Asynchronous
Messaging Protocol) connection. This allows the two programs to
communicate seamlessly.

Portal and Server Sessions
--------------------------

*note: This is not really necessary to understand if you are new to
Evennia.*

New Player connections are listened for and handled by the Portal using
the `protocols <SessionProtocols.html>`_ it understands (such as telnet,
ssh, webclient etc). When a new connection is established, a *Portal
Session* is created on the Portal side. This session object looks
different depending on which protocol is used to connect, but all still
have a minimum set of attributes that are generic to all sessions.

These common properties are piped from the Portal, through AMP, to the
*Server*, which is now informed a new connection has been established.
On the Server side, a *Server Session* object is created to represent
this. There is only one type of Server Session. It looks the same
regardless of how the Player connects.

From now on, there is a one-to-one match between the Server Session on
one side of the AMP connection and the Portal Session on the other. Data
arriving to the Portal Session is sent on to its mirror Server session
and vice versa.

During certain situations, the portal- and server-side sessions are
"synced" with each other:

-  The Player closes their client, killing the Portal Session. The
   Portal syncs with the Server to make sure the corresponding Server
   Session is also deleted.
-  The Player quits from inside the game, killing the Server Session.
   The Server then syncs with the Portal to make sure to close the
   Portal connection cleanly.
-  The Server is rebooted/reset/shutdown - The Server Sessions are
   copied over ("saved") to the Portal side. When the Server comes back
   up, this data is returned by the Portal so the two are again in sync.
   This way a Player's login status and other connection-critical things
   can survive a server reboot (assuming the Portal is not stopped at
   the same time, obviously).

Sessionhandlers
---------------

Both the Portal and Server each have a *sessionhandler* to manage the
connections. These handlers contain all methods for relaying data across
the AMP bridge. All types of Sessions hold a reference to their
respective Sessionhandler (the property is called ``sessionhandler``) so
they can relay data. See `protocols <SessionProtocols.html>`_ for more
info on building new protocols.

.. |image0| image:: https://2498159658166209538-a-1802744773732722657-s-sites.googlegroups.com/site/evenniaserver/file-cabinet/evennia_server_portal.png
