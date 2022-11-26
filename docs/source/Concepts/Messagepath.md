# The Message path

```shell
> look

A Meadow 

This is a beautiful meadow. It is full of flowers.

You see: a flower
Exits: north, east
```

When you send a command like `look` into Evennia - what actually happens? How does that `look` string end up being handled by the `CmdLook` class? What happens when we use e.g. `caller.msg()` to send the message back 

Understanding this flow of data - the _message path_ is important in order to understand how Evennia works.

## Ingoing message path 

```
            Internet│
            ┌─────┐ │                                   ┌────────┐
┌──────┐    │Text │ │  ┌────────────┐    ┌─────────┐    │Command │
│Client├────┤JSON ├─┼──►commandtuple├────►Inputfunc├────►DB query│
└──────┘    │etc  │ │  └────────────┘    └─────────┘    │etc     │
            └─────┘ │                                   └────────┘
                    │Evennia
```

### Incoming command tuples 

Ingoing data from the client (coming in as raw strings or serialized JSON) is converted by Evennia to a `commandtuple`. Thesa are the same regardless of what client or connection was used. A `commandtuple` is a simple tuple with three elements: 

```python
(commandname, (args), {kwargs})
```

For the `look`-command (and anything else written by the player), the `text` `commandtuple` is generated: 

```python
("text", ("look",), {})
```

### Inputfuncs 

On the Evennia server side, a list of [inputfucs](Inputuncs) are registered. You can add your own by extending `settings.INPUT_FUNC_MODULES`.

```python
inputfunc_commandname(session, *args, **kwargs)
```
Here the `session` represents the unique client connection this is coming from (that is, it's identifying just _who_ is sending this input). 

One such inputfunc is named `text`. For sending a `look`, it will be called as 
```{sidebar}
If you know how `*args` and `**kwargs` work in Python, you'll see that this is the same as a call `text(session, "look")`
```

```python
text(session, *("look",), **{})  
```

What an `inputfunc` does with this depends. For an [Out-of-band](./OOB.md) instruction, it could fetch the health of a player or tick down some counter. 

```{sidebar} No text parsing happens before this
If you send `look here`, the call would be `text(session, *("look here", **{})`. All parsing of the text input happens in the command-parser, after this step.
```
For the `text` `inputfunc` the Evennia [CommandHandler](../Components/Commands.md) is invoked and the argument is parsed further in order to figure which command was intended. 

In the example of `look`, the `CmdLook` command-class will be invoked. This will retrieve the description of the current location.

## Outgoing message path

```
            Internet│
            ┌─────┐ │
┌──────┐    │Text │ │  ┌──────────┐    ┌────────────┐   ┌─────┐
│Client◄────┤JSON ├─┼──┤outputfunc◄────┤commandtuple◄───┤msg()│
└──────┘    │etc  │ │  └──────────┘    └────────────┘   └─────┘
            └─────┘ │
                    │Evennia
```

### `msg`  to outgoing commandtuple

When the `inputfunc` has finished whatever it is supposed to, the server may or may not decide to return a result (Some types of `inputcommands` may not expect or require a response at all). The server also often sends outgoing messages without any prior matching ingoing data.

Whenever data needs to be sent "out" of Evennia,  we must generalize it into a (now outgoing) `commandtuple` `(commandname, (args), {kwargs})`. This we do with the  `msg()` method. For convenience, this methods is available on every major entity, such as `Object.msg()` and `Account.msg()`. They all link back to `Session.msg()`.

```python
msg(text=None, from_obj=None, session=None, options=None, **kwargs)
```

`text` is so common that it is given as the default: 

```python
msg("A meadow\n\nThis is a beautiful meadow...")
```

This is converted to a `commandtuple`  looking like this:
```python
("text", ("A meadow\n\nThis is a beutiful meadow...",) {})
```

The `msg()` method allows you to define the `commandtuple` directly, for whatever outgoing instruction you want to find: 

```python
msg(current_status=(("healthy", "charged"), {"hp": 12, "mp": 20}))
```

This will be converted to a `commandtuple` looking like this: 

```python
("current_status", ("healthy", "charged"), {"hp": 12, "mp": 20})
```

### outputfuncs 

```{sidebar}
`outputfuncs` are tightly coupled to the protocol and you usually don't need to touch them, unless you are adding a new protocol entirely.
```
Since `msg()` is aware of which [Session](../Components/Sessions.md) to send to, the outgoing `commandtuple` is always end up pointed at the right client. 

Each supported Evennia Protocol (Telnet, SSH, Webclient etc) has their own `outputfunc`, which converts the generic `commandtuple` into a form that particular protocol understands, such as telnet instructions or JSON. 

For telnet (no SSL), the `look` will return over the wire as plain text:

    A meadow\n\nThis is a beautiful meadow...

When sending to the webclient, the `commandtuple` is converted as serialized JSON, like this:

    '["look", ["A meadow\\n\\nThis is a beautiful meadow..."], {}]'

This is then sent to the client over the wire. It's then up to the client to interpret and handle the data properly.


## Components along the path

### Ingoing 

```
                ┌──────┐                ┌─────────────────────────┐
                │Client│                │                         │
                └──┬───┘                │  ┌────────────────────┐ │
                   │             ┌──────┼─►│ServerSessionHandler│ │
┌──────────────────┼──────┐      │      │  └───┬────────────────┘ │
│ Portal           │      │      │      │      │                  │
│        ┌─────────▼───┐  │    ┌─┴─┐    │  ┌───▼─────────┐        │
│        │PortalSession│  │    │AMP│    │  │ServerSession│        │
│        └─────────┬───┘  │    └─┬─┘    │  └───┬─────────┘        │
│                  │      │      │      │      │                  │
│ ┌────────────────▼───┐  │      │      │  ┌───▼─────┐            │
│ │PortalSessionHandler├──┼──────┘      │  │Inputfunc│            │
│ └────────────────────┘  │             │  └─────────┘            │
│                         │             │                  Server │
└─────────────────────────┘             └─────────────────────────┘
```

1. Client - sends handshake or commands over the wire. This is received by the Evennia [Portal](../Components/Portal-And-Server.md).
2. `PortalSession` represents one client connection. It understands the communiation protocol used. It converts the protocol-specific input to a generic  `commandtuple` structure `(cmdname, (args), {kwargs})`. 
3. `PortalSessionHandler` handles all connections. It pickles the `commandtuple` together with the session-id. 
4.  Pickled data is sent  across the `AMP` (Asynchronous Message Protocol) connection to the [Server](Server-And-Portal) part of Evennia.
5. `ServerSessionHandler` unpickles the `commandtuple` and matches the session-id to a matching `SessionSession`.
6. `ServerSession` represents the session-connection on the Server side. It looks through its registry of [Inputfuncs](../Components/Inputfuncs.md) to find a match. 
7. The appropriate `Inputfunc` is called with the args/kwargs included in the `commandtuple`. Depending on `Inputfunc`, this could have different effects. For the `text` inputfunc, it fires the [CommandHandler](../Components/Commands.md).

### Outgoing 

```
                ┌──────┐                ┌─────────────────────────┐
                │Client│                │                         │
                └──▲───┘                │  ┌────────────────────┐ │
                   │             ┌──────┼──┤ServerSessionHandler│ │
┌──────────────────┼──────┐      │      │  └───▲────────────────┘ │
│ Portal           │      │      │      │      │                  │
│        ┌─────────┴───┐  │    ┌─┴─┐    │  ┌───┴─────────┐        │
│        │PortalSession│  │    │AMP│    │  │ServerSession│        │
│        └─────────▲───┘  │    └─┬─┘    │  └───▲─────────┘        │
│                  │      │      │      │      │                  │
│ ┌────────────────┴───┐  │      │      │  ┌───┴──────┐           │
│ │PortalSessionHandler◄──┼──────┘      │  │msg() call│           │
│ └────────────────────┘  │             │  └──────────┘           │
│                         │             │                  Server │
└─────────────────────────┘             └─────────────────────────┘
```

1. The `msg()` method is called
2. `ServerSession` and in particular `ServerSession.msg()`  is the central point through which all `msg()` calls are routed in order to send data to that [Session](../Components/Sessions.md). 
3. `ServerSessionHandler` converts the `msg` input to a proper `commandtuple` structure `(cmdname, (args), {kwargs})`.   It pickles the `commandtuple` together with the session-id.
4.  Pickled data is sent across across the `AMP` (Asynchronous Message Protocol) connection to the [Portal](Server-And-Portal) part of Evennia.
5. `PortalSessionHandler` unpickles the `commandtuple` and matches its session id to a matching `PortalSession`.
6. The `PortalSession` is now responsible for converting the generic `commandtuple` to the communication protocol used by that particular connection.
7. The Client receives the data and can act on it. 