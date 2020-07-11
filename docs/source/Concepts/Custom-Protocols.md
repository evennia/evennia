# Custom Protocols


*Note: This is considered an advanced topic and is mostly of interest to users planning to implement
their own custom client protocol.*


A [PortalSession](../Components/Sessions#Portal-and-Server-Sessions) is the basic data object representing an
external
connection to the Evennia [Portal](../Components/Portal-And-Server) -- usually a human player running a mud client
of some kind.  The way they connect (the language the player's client and Evennia use to talk to
each other) is called the connection *Protocol*. The most common such protocol for MUD:s is the
*Telnet* protocol. All Portal Sessions are stored and managed by the Portal's *sessionhandler*.

It's technically sometimes hard to separate the concept of *PortalSession* from the concept of
*Protocol* since both depend heavily on the other (they are often created as the same class). When
data flows through this part of the system, this is how it goes

```
# In the Portal
You <-> 
  Protocol + PortalSession <-> 
    PortalSessionHandler <->
      (AMP) <-> 
        ServerSessionHandler <->
          ServerSession <->
            InputFunc  
```

(See the [Message Path](./Messagepath) for the bigger picture of how data flows through Evennia). The
parts that needs to be customized to make your own custom protocol is the `Protocol + PortalSession`
(which translates between data coming in/out over the wire to/from Evennia internal representation)
as well as the `InputFunc` (which handles incoming data).

## Adding custom Protocols

Evennia has a plugin-system that add the protocol as a new "service" to the application.

Take a look at `evennia/server/portal/portal.py`, notably the sections towards the end of that file.
These are where the various in-built services like telnet, ssh, webclient etc are added to the
Portal (there is an equivalent but shorter list in `evennia/server/server.py`).

To add a new service of your own (for example your own custom client protocol) to the Portal or
Server, look at  `mygame/server/conf/server_services_plugins` and `portal_services_plugins`. By
default Evennia will look into these modules to find plugins. If you wanted to have it look for more
modules, you could do the following:

```python
    # add to the Server
    SERVER_SERVICES_PLUGIN_MODULES.append('server.conf.my_server_plugins')
    # or, if you want to add to the Portal
    PORTAL_SERVICES_PLUGIN_MODULES.append('server.conf.my_portal_plugins')
```

When adding a new connection you'll most likely only need to add new things to the
`PORTAL_SERVICES_PLUGIN_MODULES`.

This module can contain whatever you need to define your protocol, but it *must* contain a function
`start_plugin_services(app)`. This is called by the Portal as part of its upstart. The function
`start_plugin_services` must contain all startup code the server need.  The `app` argument is a
reference to the Portal/Server application itself so the custom service can be added to it. The
function should not return anything.

This is how it looks:

```python
    # mygame/server/conf/portal_services_plugins.py

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
         print("  myproc: %s" % MY_PORT)

         # some setup (simple example)
         factory = MyOwnFactory()
         my_service = internet.TCPServer(MY_PORT, factory)
         # all Evennia services must be uniquely named
         my_service.setName("MyService")
         # add to the main portal application
         portal.services.addService(my_service)
```

Once the module is defined and targeted in settings, just reload the server and your new
protocol/services should start with the others.

## Writing your own Protocol

Writing a stable communication protocol from scratch is not something we'll cover here, it's no
trivial task. The good news is that Twisted offers implementations of many common protocols, ready
for adapting.

Writing a protocol implementation in Twisted usually involves creating a class inheriting from an
already existing Twisted protocol class and from `evennia.server.session.Session` (multiple
inheritance), then overloading the methods that particular protocol uses to link them to the
Evennia-specific inputs.

Here's a example to show the concept: 

```python
# In module that we'll later add to the system through PORTAL_SERVICE_PLUGIN_MODULES

# pseudo code 
from twisted.something import TwistedClient
# this class is used both for Portal- and Server Sessions
from evennia.server.session import Session 

from evennia.server.portal.portalsessionhandler import PORTAL_SESSIONS

class MyCustomClient(TwistedClient, Session): 

    def __init__(self, *args, **kwargs): 
        super().__init__(*args, **kwargs)
        self.sessionhandler = PORTAL_SESSIONS

    # these are methods we must know that TwistedClient uses for 
    # communication. Name and arguments could vary for different Twisted protocols
    def onOpen(self, *args, **kwargs):
        # let's say this is called when the client first connects

        # we need to init the session and connect to the sessionhandler. The .factory
        # is available through the Twisted parents

        client_address = self.getClientAddress()  # get client address somehow

        self.init_session("mycustom_protocol", client_address, self.factory.sessionhandler)
        self.sessionhandler.connect(self)

    def onClose(self, reason, *args, **kwargs):
        # called when the client connection is dropped
        # link to the Evennia equivalent
        self.disconnect(reason)

    def onMessage(self, indata, *args, **kwargs): 
        # called with incoming data
        # convert as needed here        
        self.data_in(data=indata) 

    def sendMessage(self, outdata, *args, **kwargs):
        # called to send data out
        # modify if needed        
        super().sendMessage(self, outdata, *args, **kwargs)

     # these are Evennia methods. They must all exist and look exactly like this
     # The above twisted-methods call them and vice-versa. This connects the protocol
     # the Evennia internals.  
     
     def disconnect(self, reason=None): 
         """
         Called when connection closes. 
         This can also be called directly by Evennia when manually closing the connection.
         Do any cleanups here.
         """
         self.sessionhandler.disconnect(self)

     def at_login(self): 
         """
         Called when this session authenticates by the server (if applicable)
         """    

     def data_in(self, **kwargs):
         """
         Data going into the server should go through this method. It 
         should pass data into `sessionhandler.data_in`. THis will be called
         by the sessionhandler with the data it gets from the approrpriate 
         send_* method found later in this protocol. 
         """
         self.sessionhandler.data_in(self, text=kwargs['data'])

     def data_out(self, **kwargs):
         """
         Data going out from the server should go through this method. It should
         hand off to the protocol's send method, whatever it's called.
         """
         # we assume we have a 'text' outputfunc
         self.onMessage(kwargs['text'])

     # 'outputfuncs' are defined as `send_<outputfunc_name>`. From in-code, they are called 
     # with `msg(outfunc_name=<data>)`. 

     def send_text(self, txt, *args, **kwargs): 
         """
         Send text, used with e.g. `session.msg(text="foo")`
         """
         # we make use of the 
         self.data_out(text=txt)

     def send_default(self, cmdname, *args, **kwargs): 
         """
         Handles all outputfuncs without an explicit `send_*` method to handle them.
         """
         self.data_out(**{cmdname: str(args)})

```
The principle here is that the Twisted-specific methods are overridden to redirect inputs/outputs to
the Evennia-specific methods.

### Sending data out

To send data out through this protocol, you'd need to get its Session and then you could e.g. 

```python
    session.msg(text="foo")
```

The message will pass through the system such that the sessionhandler will dig out the session and
check if it has a `send_text` method (it has). It will then pass the "foo" into that method, which
in our case means sending "foo" across the network.

### Receiving data 

Just because the protocol is there, does not mean Evennia knows what to do with it. An
[Inputfunc](../Components/Inputfuncs) must exist to receive it. In the case of the `text` input exemplified above,
Evennia alredy handles this input - it will parse it as a Command name followed by its inputs. So
handle that you need to simply add a cmdset with commands on your receiving Session (and/or the
Object/Character it is puppeting). If not you may need to add your own Inputfunc (see the
[Inputfunc](../Components/Inputfuncs) page for how to do this.

These might not be as clear-cut in all protocols, but the principle is there. These four basic
components - however they are accessed - links to the *Portal Session*, which is the actual common
interface between the different low-level protocols and Evennia.

## Assorted notes

To take two examples, Evennia supports the *telnet* protocol as well as *webclient*, via ajax or
websockets. You'll find that whereas telnet is a textbook example of a Twisted protocol as seen
above, the ajax protocol looks quite different due to how it interacts with the
webserver through long-polling (comet) style requests. All the necessary parts
mentioned above are still there, but by necessity implemented in very different
ways. 