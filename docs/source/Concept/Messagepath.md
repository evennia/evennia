# Messagepath


The main functionality of Evennia is to communicate with clients connected to it; a player enters
commands or their client queries for a gui update (ingoing data). The server responds or sends data
on its own as the game changes (outgoing data). It's important to understand how this flow of
information works in Evennia.

## The ingoing message path

We'll start by tracing data from the client to the server. Here it is in short:

    Client ->
     PortalSession ->
      PortalSessionhandler ->
       (AMP) ->
        ServerSessionHandler ->
          ServerSession ->
            Inputfunc

### Client (ingoing)

The client sends data to Evennia in two ways.

 - When first connecting, the client can send data to the server about its
 capabilities. This is things like "I support xterm256 but not unicode" and is
 mainly used when a Telnet client connects. This is called a "handshake" and
 will generally set some flags on the [Portal Session](Portal-And-Server) that
 are later synced to the Server Session. Since this is not something the player
 controls, we'll not explore this further here.
 - The client can send an *inputcommand* to the server. Traditionally this only
 happens when the player enters text on the command line. But with a custom
 client GUI, a command could also come from the pressing of a button. Finally
 the client may send commands based on a timer or some trigger.

Exactly how the inputcommand looks when it travels from the client to Evennia
depends on the [Protocol](Custom-Protocols) used:
 - Telnet: A string. If GMCP or MSDP OOB protocols are used, this string will
 be formatted in a special way, but it's still a raw string. If Telnet SSL is
 active, the string will be encrypted.
 - SSH: An encrypted string
 - Webclient: A JSON-serialized string.

### Portal Session (ingoing)

Each client is connected to the game via a *Portal Session*, one per connection. This Session is
different depending on the type of connection (telnet, webclient etc) and thus know how to handle
that particular data type. So regardless of how the data arrives, the Session will identify the type
of the instruction and any arguments it should have. For example, the telnet protocol will figure
that anything arriving normally over the wire should be passed on as a "text" type.

### PortalSessionHandler (ingoing)

The *PortalSessionhandler* manages all connected Sessions in the Portal. Its `data_in` method
(called by each Portal Session) will parse the command names and arguments from the protocols and
convert them to a standardized form we call the *inputcommand*:

```python
    (commandname, (args), {kwargs})
```

All inputcommands must have a name, but they may or may not have arguments and keyword arguments -
in fact no default inputcommands use kwargs at all. The most common inputcommand is "text", which
has the argument the player input on the command line:

```python
    ("text", ("look",), {})
```

This inputcommand-structure is pickled together with the unique session-id of the Session to which
it belongs. This is then sent over the AMP connection.

### ServerSessionHandler (ingoing)

On the Server side, the AMP unpickles the data and associates the session id with the server-side
[Session](Sessions). Data and Session are passed to the server-side `SessionHandler.data_in`. This
in turn calls `ServerSession.data_in()`

### ServerSession (ingoing)

The method `ServerSession.data_in` is meant to offer a single place to override if they want to
examine *all* data passing into the server from the client. It is meant to call the
`ssessionhandler.call_inputfuncs` with the (potentially processed) data (so this is technically a
sort of detour back to the sessionhandler).

In `call_inputfuncs`, the inputcommand's name is compared against the names of all the *inputfuncs*
registered with the server. The inputfuncs are named the same as the inputcommand they are supposed
to handle, so the (default) inputfunc for handling our "look" command is called "text". These are
just normal functions and one can plugin new ones by simply putting them in a module where Evennia
looks for such functions.

If a matching inputfunc is found, it will be called with the Session and the inputcommand's
arguments:

```python
    text(session, *("look",), **{})
```

 If no matching inputfunc is found, an inputfunc named "default" will be tried and if that is also
not found, an error will be raised.

### Inputfunc

The [Inputfunc](Inputfuncs) must be on the form `func(session, *args, **kwargs)`. An exception is
the `default` inputfunc which has form `default(session, cmdname, *args, **kwargs)`, where `cmdname`
is the un-matched inputcommand string.

This is where the message's path diverges, since just what happens next depends on the type of
inputfunc was triggered. In the example of sending "look", the inputfunc is named "text". It will
pass the argument to the `cmdhandler` which will eventually lead to the `look` command being
executed.


## The outgoing message path

Next let's trace the passage from server to client.

    msg ->
     ServerSession ->
      ServerSessionHandler ->
       (AMP) ->
        PortalSessionHandler ->
         PortalSession ->
          Client

### msg

All outgoing messages start in the `msg` method. This is accessible from three places:

 - `Object.msg`
 - `Account.msg`
 - `Session.msg`

The call sign of the `msg` method looks like this:

```python
    msg(text=None, from_obj=None, session=None, options=None, **kwargs)
```

For our purposes, what is important to know is that with the exception of `from_obj`, `session` and
`options`, all keywords given to the `msg` method is the name of an *outputcommand* and its
arguments. So `text` is actually such a command, taking a string as its argument. The reason `text`
sits as the first keyword argument is that it's so commonly used (`caller.msg("Text")` for example).
Here are some examples

```python
    msg("Hello!")   # using the 'text' outputfunc
    msg(prompt="HP:%i, SP: %i, MP: %i" % (HP, SP, MP))
    msg(mycommand=((1,2,3,4), {"foo": "bar"})

```
Note the form of the `mycommand` outputfunction. This explicitly defines the arguments and keyword
arguments for the function. In the case of the `text` and `prompt` calls we just specify a string -
this works too: The system will convert this into a single argument for us later in the message
path.

> Note: The `msg` method sits on your Object- and Account typeclasses. It means you can easily
override `msg` and make custom- or per-object modifications to the flow of data as it passes
through.

### ServerSession (outgoing)

Nothing is processed on the Session, it just serves as a gathering points for all different `msg`.
It immediately passes the data on to ...

### ServerSessionHandler (outgoing)

In the *ServerSessionhandler*, the keywords from the `msg` method are collated into one or more
*outputcommands* on a standardized form (identical to inputcommands):

```
    (commandname, (args), {kwargs})
```

This will intelligently convert different input to the same form. So `msg("Hello")` will end up as
an outputcommand `("text", ("Hello",), {})`.

This is also the point where [Inlinefuncs](TextTags#inline-functions) are parsed, depending on the
session to receive the data. Said data is pickled together with the Session id then sent over the
AMP bridge.

### PortalSessionHandler (outgoing)

After the AMP connection has unpickled the data and paired the session id to the matching
PortalSession, the handler next determines if this Session has a suitable method for handling the
outputcommand.

The situation is analogous to how inputfuncs work, except that protocols are fixed things that don't
need a plugin infrastructure like the inputfuncs are handled. So instead of an "outputfunc", the
handler looks for methods on the PortalSession with names of the form `send_<commandname>`.

For example, the common sending of text expects a PortalSession method `send_text`. This will be
called as `send_text(*("Hello",), **{})`. If the "prompt" outputfunction was used, send_prompt is
called. In all other cases the `send_default(cmdname, *args, **kwargs)` will be called - this is the
case for all client-custom outputcommands, like when wanting to tell the client to update a graphic
or play a sound.

### PortalSession (outgoing)

At this point it is up to the session to convert the command into a form understood by this
particular protocol. For telnet, `send_text` will just send the argument as a string (since that is
what telnet clients expect when "text" is coming). If `send_default` was called (basically
everything that is not traditional text or a prompt), it will pack the data as an GMCP or MSDP
command packet if the telnet client supports either (otherwise it won't send at all). If sending to
the webclient, the data will get packed into a JSON structure at all times.

### Client (outgoing)

Once arrived at the client, the outputcommand is handled in the way supported by the client (or it
may be quietly ignored if not). "text" commands will be displayed in the main window while others
may trigger changes in the GUI or play a sound etc.
