# OOB

OOB, or Out-Of-Band, means sending data between Evennia and the user's client without the user
prompting it or necessarily being aware that it's being passed. Common uses would be to update
client health-bars, handle client button-presses or to display certain tagged text in a different
window pane.

## Briefly on input/outputcommands

Inside Evennia, all server-client communication happens in the same way (so plain text is also an
'OOB message' as far as Evennia is concerned). The message follows the [Message Path](Concept/Messagepath).
You should read up on that if you are unfamiliar with it. As the message travels along the path it
has a standardized internal form: a tuple with a string, a tuple and a dict:

    ("cmdname", (args), {kwargs})

This is often referred to as an *inputcommand* or *outputcommand*, depending on the direction it's
traveling. The end point for an inputcommand, (the 'Evennia-end' of the message path) is a matching
[Inputfunc](Component/Inputfuncs). This function is called as `cmdname(session, *args, **kwargs)` where
`session` is the Session-source of the command. Inputfuncs can easily be added by the developer to
support/map client commands to actions inside Evennia (see the [inputfunc](Component/Inputfuncs) page for more
details).

When a message is outgoing (at the 'Client-end' of the message path) the outputcommand is handled by
a matching *Outputfunc*. This is responsible for converting the internal Evennia representation to a
form suitable to send over the wire to the Client. Outputfuncs are hard-coded. Which is chosen and
how it processes the outgoing data depends on the nature of the client it's connected to. The only
time one would want to add new outputfuncs is as part of developing support for a new Evennia
[Protocol](Concept/Custom-Protocols).

## Sending and receiving an OOB message

Sending is simple. You just use the normal `msg` method of the object whose session you want to send
to. For example in a Command:

```python
    caller.msg(cmdname=((args, ...), {key:value, ...}))
```

A special case is the `text` input/outputfunc. It's so common that it's the default of the `msg`
method. So these are equivalent:

```python
    caller.msg("Hello")
    caller.msg(text="Hello")
```

You don't have to specify the full output/input definition. So for example, if your particular
command only needs kwargs, you can skip the `(args)` part. Like in the `text` case you can skip
writing the tuple if there is only one arg ... and so on - the input is pretty flexible. If there
are no args at all you need to give the empty tuple `msg(cmdname=(,)` (giving `None` would mean a
single argument `None`).

Which commands you can send depends on the client. If the client does not support an explicit OOB
protocol (like many old/legacy MUD clients) Evennia can only send `text` to them and will quietly
drop any other types of outputfuncs.

> Remember that a given message may go to multiple clients with different capabilities. So unless
you turn off telnet completely and only rely on the webclient, you should never rely on non-`text`
OOB messages always reaching all targets.

[Inputfuncs](Component/Inputfuncs) lists the default inputfuncs available to handle incoming OOB messages. To
accept more you need to add more inputfuncs (see that page for more info).

## Supported OOB protocols

Evennia supports clients using one of the following protocols: 

### Telnet

By default telnet (and telnet+SSL) supports only the plain `text` outputcommand. Evennia however
detects if the Client supports one of two MUD-specific OOB *extensions* to the standard telnet
protocol - GMCP or MSDP. Evennia supports both simultaneously and will switch to the protocol the
client uses. If the client supports both, GMCP will be used.

> Note that for Telnet, `text` has a special status as the "in-band" operation. So the `text`
outputcommand sends the `text` argument directly over the wire, without going through the OOB
translations described below.

#### Telnet + GMCP

[GMCP](http://www.gammon.com.au/gmcp), the *Generic Mud Communication Protocol* sends data on the
form `cmdname + JSONdata`. Here the cmdname is expected to be on the form "Package.Subpackage".
There could also be additional Sub-sub packages etc. The names of these 'packages' and 'subpackages'
are not that well standardized beyond what individual MUDs or companies have chosen to go with over
the years. You can decide on your own package names, but here are what others are using:

- [Aardwolf GMCP](http://www.aardwolf.com/wiki/index.php/Clients/GMCP)
- [Discworld GMCP](http://discworld.starturtle.net/lpc/playing/documentation.c?path=/concepts/gmcp)
- [Avatar GMCP](http://www.outland.org/infusions/wiclear/index.php?title=MUD%20Protocols&lang=en)
- [IRE games GMCP](http://nexus.ironrealms.com/GMCP)

Evennia will translate underscores to `.` and capitalize to fit the specification. So the
outputcommand `foo_bar` will become a GMCP command-name `Foo.Bar`. A GMCP command "Foo.Bar" will be
come `foo_bar`. To send a GMCP command that turns into an Evennia inputcommand without an
underscore, use the `Core` package. So `Core.Cmdname` becomes just `cmdname` in Evennia and vice
versa.

On the wire, a GMCP instruction for `("cmdname", ("arg",), {})` will look like this: 

    IAC SB GMCP "cmdname" "arg" IAC SE

where all the capitalized words are telnet character constants specified in
`evennia/server/portal/telnet_oob.py`. These are parsed/added by the protocol and we don't include
these in the listings below.

Input/Outputfunc | GMCP-Command
------------------
`[cmd_name, [], {}]`  |  Cmd.Name
`[cmd_name, [arg], {}]` |      Cmd.Name arg
`[cmd_na_me, [args],{}]`  |     Cmd.Na.Me [args]
`[cmd_name, [], {kwargs}]` |    Cmd.Name {kwargs}
`[cmdname, [args, {kwargs}]` | Core.Cmdname [[args],{kwargs}]

Since Evennia already supplies default inputfuncs that don't match the names expected by the most
common GMCP implementations we have a few hard-coded mappings for those:

GMCP command name | Input/Outputfunc name
-----------------
"Core.Hello" | "client_options" 
"Core.Supports.Get" | "client_options" 
"Core.Commands.Get" | "get_inputfuncs" 
"Char.Value.Get" | "get_value"
"Char.Repeat.Update" | "repeat"
"Char.Monitor.Update" | "monitor"

#### Telnet + MSDP 

[MSDP](http://tintin.sourceforge.net/msdp/), the *Mud Server Data Protocol*, is a competing standard
to GMCP. The MSDP protocol page specifies a range of "recommended" available MSDP command names.
Evennia does *not* support those - since MSDP doesn't specify a special format for its command names
(like GMCP does) the client can and should just call the internal Evennia inputfunc by its actual
name.

MSDP uses Telnet character constants to package various structured data over the wire. MSDP supports
strings, arrays (lists) and tables (dicts). These are used to define the cmdname, args and kwargs
needed. When sending MSDP for `("cmdname", ("arg",), {})` the resulting MSDP instruction will look
like this:

    IAC SB MSDP VAR cmdname VAL arg IAC SE

The various available MSDP constants like `VAR` (variable), `VAL` (value), `ARRAYOPEN`/`ARRAYCLOSE`
and `TABLEOPEN`/`TABLECLOSE` are specified in `evennia/server/portal/telnet_oob`.

Outputfunc/Inputfunc | MSDP instruction
-------------------------
`[cmdname, [], {}]` | VAR cmdname VAL
`[cmdname, [arg], {}]` | VAR cmdname VAL arg
`[cmdname, [args],{}]`  | VAR cmdname VAL ARRAYOPEN VAL arg VAL arg ... ARRAYCLOSE
`[cmdname, [], {kwargs}]`  | VAR cmdname VAL TABLEOPEN VAR key VAL val ... TABLECLOSE
`[cmdname, [args], {kwargs}]` | VAR cmdname VAL ARRAYOPEN VAL arg VAL arg ... ARRAYCLOSE VAR cmdname
VAL TABLEOPEN VAR key VAL val ... TABLECLOSE

Observe that `VAR ... VAL` always identifies cmdnames, so if there are multiple arrays/dicts tagged
with the same cmdname they will be appended to the args, kwargs of that inputfunc. Vice-versa, a
different `VAR ... VAL` (outside a table) will come out as a second, different command input.

### SSH

SSH only supports the `text` input/outputcommand. 

### Web client

Our web client uses pure JSON structures for all its communication, including `text`. This maps
directly to the Evennia internal output/inputcommand, including eventual empty args/kwargs. So the
same example `("cmdname", ("arg",), {})` will be sent/received as a valid JSON structure

    ["cmdname, ["arg"], {}]

Since JSON is native to Javascript, this becomes very easy for the webclient to handle.