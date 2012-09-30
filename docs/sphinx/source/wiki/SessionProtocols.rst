Portal Sessions and Protocols
=============================

*Note: This is considered an advanced topic and is mostly of interest to
users planning to implement their own custom client protocol.*

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
   call ``self.init_session()`` with three arguments: an *identifier*
   for the protocol type (e.g. the string 'telnet' or 'ssh'), the *IP
   address* of the client connecting, and a reference to the
   *sessionhandler*. The sessionhandler is by convention made available
   by storing it on the protocol's *Factory* in
   ``src/server/portal.py``, see that file for examples. Doing it this
   way avoids many possible recursive import issues.
-  ``connectionLost`` - called when connection is dropped for whatever
   reason. This must call ``self.sessionhandler.disconnect(self)`` so
   the handler can make sure the disconnect is reported to the rest of
   the system.
-  ``getData`` - data arriving from the player to Evennia. This should
   apply whatever custom formatting this protocol needs, then relay the
   data to ``self.sessionhandler.data_in(self, msg, data)``.
-  ``sendLine`` - data from Server to Player. This is called by hook
   ``data_out()`` below.

See an example of this in
`server/telnet.py <http://code.google.com/p/evennia/source/browse/trunk/src/server/telnet.py>`_.

These might not be as clear-cut in all protocols, but the principle is
there. These four basic components - however they are accessed - links
to the *Portal Session*, which is the actual common interface between
the different low-level protocols and Evennia.

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
   This method should handle any protocol-specific processing before
   relaying data on to a send-method like ``self.sendLine()`` mentioned
   above. ``string`` is normally a raw text string with formatting.
   ``data`` can be a collection of any extra information the server want
   to give to the protocol- it's completely up to the Protocol to handle
   this. To take an example, telnet assumes ``data`` to be either
   ``None`` or a dictionary with flags for how the text should be
   parsed. From inside Evennia, ``data_out`` is often called with the
   alias ``msg`` instead.

Out-of-band communication
-------------------------

Out-of-band communication (OOB) is data being sent to and fro the
player's client and the server on the protocol level, often due to the
request of the player's client software rather than any sort of active
input by the player. There are two main types:

-  Data requested by the client to which the server responds
   immediately. This could for example be data that should go into a
   window that the client just opened up.
-  Data the server sends to the client to keep it up-to-date. A common
   example of this is something like a graphical health bar - *whenever*
   the character's health status changes the server sends this data to
   the client so it can update the bar graphic. This sending could also
   be done on a timer, for example updating a weather map regularly.

To communicate to the client, there are a range of protocols available
for MUDs, supported by different clients, such as MSDP and GMCP. They
basically implements custom telnet negotiation sequences and goes into a
custom Evennia Portal protocol so Evennia can understand it.

It then needs to translate each protocol-specific function into an
Evennia function name - specifically a name of a module-level function
you define in the module given by ``settings.OOB_FUNC_MODULE``. These
function will get the session/character as first argument but is
otherwise completely free of form. The portal packs all function names
and eventual arguments they need in a dictionary and sends them off to
the Server by use of the ``sessionhandler.oob_data_in()`` method. On the
Server side, the dictionary is parsed, and the correct functions in
``settings.OOB_FUNC_MODULE`` are called with the given arguments. The
results from this function are again packed in a dictionary (keyed by
function name) and sent back to the portal. It will appear in the Portal
session's ``oob_data_out(data)`` method.

So to summarize: To implement a Portal protocol with OOB communication
support, you need to first let your normal ``getData`` method somehow
parse out the special protocol format format coming in from the client
(MSDP, GMCP etc). It needs to translate what the client wants into
function names matching that in the ``OOB_FUNC_MODULE`` - these
functions need to be created to match too of course. The function name
and arguments are packed in a dictionary and sent off to the server via
``sessionhandler.oob_data_in()``. Finally, the portal session must
implement ``oob_data_out(data)`` to handle the data coming back from
Server. It will be a dictionary of return values keyed by the function
names.

Example of out-of-band calling sequence
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's say we want our client to be able to request the character's
current health, stamina and maybe some skill values. In our Portal
protocol we somehow parse the incoming data stream and figure out what
the request for health looks like. We map this to the Evennia
``get_health`` function.

We point ``settings.OOB_FUNC_MODULE`` to someplace in ``game/`` and
create a module there with the following functions:

::

    # the caller is automatically added as first argument
    def get_health(character):
        "Get health, stored as simple attribute"    
        return character.db.health 
    def get_stamina(character):
        "Get stamina level, stored as simple attribute"
        return character.db.stamina
    def get_skill(character, skillname, master=False):
        """we assume skills are stored as a dictionary 
           stored in an attribute. Master skills are 
           stored separately (for whatever reason)"""
        if master:
            return character.db.skills_master.get(skillname, "NoSkill")
        return character.db.skills.get(skillname, "NoSkill")

Done, the functions will return what we want assuming Characters do
store this information in our game. Let's finish up the first part of
the portal protocol:

::

    # this method could be named differently depending on the 
    # protocol you are using (this is telnet)
    def lineReceived(self, string):
       # (does stuff to analyze the incoming string)
       # ...
       outdict = {}
       if GET_HEALTH:
           # call get_health(char)
           outdict["get_health"] = ([], {})
       elif GET_STAMINA:
           # call get_mana(char)
           outdict["get_stamina"] = ([], {})
       elif GET_MASTER_SKILL_SMITH:
           # call get_skill(char, "smithing", master=True)
           outdict["get_skill"] = (["smithing"], {'master':True})

       [...]

       self.sessionhandler.oob_data_out(outdict)   

The Server will properly accept this and call the relevant functions to
get their return values for the health, stamina and skill. The return
values will be packed in a dictionary keyed by function name before
being passed back to the Portal. We need to define
``oob_data_out(data)`` in our portal protocol to catch this:

::

    def oob_data_out(self, data):
        # the indata is a dictionary {funcname:retval}

        outstring = ""
        for funcname, retval in data.items():
            if funcname == 'get_health':
                # convert to the right format for sending back to client, store
                # in outstring ...
         [...]
        # send off using the protocols send method (this is telnet)
        sendLine(outstring)

As seen, ``oob_data`` takes the values and formats into a form the
protocol understands before sending it off.

Implementing auto-sending
~~~~~~~~~~~~~~~~~~~~~~~~~

To have the Server update the client regularly, simply create a global
`Script <Scripts.html>`_ that upon each repeat creates the request
dictionary (basically faking a request from the portal) and sends it
directly to
``src.server.sessionhandler.oob_data_in(session.sessid, datadict)``.
Loop over all relevant sessions. The Server will treat this like a
Portal call and data will be sent back to be handled by the portal as
normal.

Adding custom Protocols
=======================

Evennia has a plugin-system that allows you to add new custom Protocols
without editing any files in ``src/``. To do this you need to add the
protocol as a new "service" to the application.

Take a look at for example ``src/server/portal.py``, notably the
sections towards the end of that file. These are where the various
in-built services like telnet, ssh, webclient etc are added to the
Portal (there is an equivalent but shorter list in
``src/server.server.py``.

To add a new service of your own (for example your own custom client
protocol) to e.g. the Portal, create a new module in
``game/gamesrc/conf/``. Let's call it ``myproc_plugin.py``. We need to
tell the Server or Portal that they need to import this module. In
``game/settings.py``, add one of the following:

::

    # add to the Server
    SERVER_SERVICES_PLUGIN_MODULES.append('game.gamesrc.conf.myproc_plugin')
    # or, if you want to add to the Portal
    PORTAL_SERVICES_PLUGIN_MODULES.append('game.gamesrc.conf.myproc_plugin')

This module can contain whatever you need to define your protocol, but
it *must* contain a function ``start_plugin_services(app)``. This is
called by the Portal as part of its upstart. The function
``start_plugin_services`` must contain all startup code the server need.
The ``app`` argument is a reference to the Portal application itself so
the custom service can be added to it. The function should not return
anything.

This is how it can look:

::

    # game/gamesrc/conf/myproc_plugin.py

    # here the new Portal Twisted protocol is defined
    class MyOwnFactory( ... ):
       [...]

    # some configs
    MYPROC_ENABLED = True # convenient off-flag to avoid having to edit settings all the time
    MY_PORT = 6666

    def start_plugin_services(portal):
        "This is called by the Portal during startup"
         if not MYPROC_ENABLED:
             return 
         # output to list this with the other services at startup
         print "  myproc: %s" % MY_PORT

         # some setup (simple example)
         factory = MyOwnFactory()
         my_service = internet.TCPServer(MY_PORT, factory)
         # all Evennia services must be uniquely named
         my_service.setName("MyService")
         # add to the main portal application
         portal.services.addService(my_service)

One the module is defined and targeted in settings, just reload the
server and your new protocol/services should start with the others.

Assorted notes
==============

To take two examples, Evennia supports the *telnet* protocol as well as
*webclient*, a custom ajax protocol. You'll find that whereas telnet is
a textbook example of a Twisted protocol as seen above, the ajax client
protocol looks quite different due to how it interacts with the
webserver through long-polling (comet) style requests. All the necessary
parts mentioned above are still there, but implemented in very different
ways.
