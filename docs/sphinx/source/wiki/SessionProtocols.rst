Portal Sessions and Protocols
=============================

*Note: This is considered an advanced topic and not relevant to most
users.*

A *Portal Session* is the basic data object representing an external
connection to the Evennia `Portal <PortalAndServer.html>`_ -- usually a
human player running a mud client of some kind. The way they connect -
the language the player's client and Evennia use to talk to each other -
is called the connection *Protocol*. The most common such protocol for
MUD:s is the *Telnet* protocol. All Portal Sessions are stored and
managed by the Portal's *sessionhandler*.

It's technically sometimes hard to separate the concept of *Session*
from the concept of *Protocol* since both depend heavily on the other.

Protocols and Sessions both belong in ``src/server/``, so adding new
protocols is one of the rare situations where development needs to
happen in ``src/`` (in fact, if you do add a new useful protocol,
consider contacting Evennia devs so we can include it in the main
Evennia distribution!).

Protocols
---------

Writing a stable communication protocol from scratch is not something
we'll cover here, it's no trivial task. The good news is that Twisted
offers implementations of many common protocols, ready for adapting.

Writing a protocol implementation in Twisted usually involves creating a
class inheriting from a suitable Twisted parent, then overloading the
methods that particular protocol requires so that it talks to Evennia.
Whenever a new connection is made via this protocol, an instance of this
class will be called. As various states change, specific-named methods
on the class will be called (what they are named depends on the Twisted
implementation).

A straight-forward protocol (like Telnet) is assumed to at least have
the following components (although the actual method names might vary):

-  ``connectionMade`` - called when a new connection is made. This must
   call ``self.init_session()`` with three arguments: an identifier for
   the protocol type (e.g. the string 'telnet'), the IP address
   connecting, and a reference to the sessionhandler.
-  ``connectionLost`` - called when connection is dropped for whatever
   reason. This must call 'self.sessionhandler.disconnect(self)' so the
   handler can make sure the disconnect is reported to the rest of the
   system.
-  ``getData`` - data arriving from the player to Evennia. This should
   apply whatever custom formatting this protocol needs, then relay the
   data to ``self.sessionhandler.data_in(self, msg, data)``.
-  sendLine - data from server to Player. This is called by hook
   ``data_out()`` below.

See an example of this in
`server/telnet.py <http://code.google.com/p/evennia/source/browse/trunk/src/server/telnet.py>`_.

These might not be as clear-cut in all protocols, but the principle is
there. These four basic components - however they are accessed - links
to the *Session*, which is the actual common interface between the
different low-level protocols and Evennia.

Portal Sessions
---------------

A *Portal Session* is an Evennia-specific thing. It must be a class
inheriting from ``src.server.session.Session``. If you read the Telnet
example above, the Protocol and Session are infact sometimes
conveniently implemented in the same class through multiple inheritance.
At startup the Portal creates and adds the Portal Session to its
*sessionhandler*. While doing so, the session also gets assigned a
property ``sessionhandler`` that refers to that very handler. This is
important since the handler holds all methods relevant for sending and
receiving data to and from the Server.

Whereas we don't know the method names of a Twisted Protocol (this can
vary from protocol to protocol), the Session has a strict naming scheme
that may not change; it is the glue that connects the Protocol to
Evennia (along with some other convenient features).

The Session class must implement the following method hooks (which must
be named exactly like this):

-  ``disconnect()`` - called when manually disconnecting. Must call the
   protocol-specific disconnect method (e.g. ``connectionLost`` above)
-  ``data_out(string="", data=None)`` - data from Evennia to player.
   ``string`` is normally a raw text string with formatting. ``data``
   can be a collection of any extra information the server want to give
   to the protocol; it's completely up to the Protocol to handle this
   (e.g. telnet completely ignores the ``data`` variable). From inside
   Evennia, this if often called with the alias ``msg`` instead. This
   method should call the protocol-specific send method, such as
   ``self.sendLine()``, directly.

Assorted notes
--------------

To take two examples, Evennia supports the *telnet* protocol as well as
*webclient*, a custom ajax protocol. You'll find that whereas telnet is
a textbook example of a Twisted protocol as seen above, the ajax client
protocol looks quite different due to how it interacts with the
webserver through long-polling (comet) style requests.
