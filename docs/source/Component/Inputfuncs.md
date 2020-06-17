# Inputfuncs


An *inputfunc* is an Evennia function that handles a particular input (an [inputcommand](Concept/OOB)) from
the client. The inputfunc is the last destination for the inputcommand along the [ingoing message
path](Messagepath#the-ingoing-message-path). The inputcommand always has the form `(commandname,
(args), {kwargs})` and Evennia will use this to try to find and call an inputfunc on the form

```python
    def commandname(session, *args, **kwargs):
        # ...

```
Or, if no match was found, it will call an inputfunc named "default" on this form

```python
    def default(session, cmdname, *args, **kwargs):
        # cmdname is the name of the mismatched inputcommand

```

## Adding your own inputfuncs

This is simple. Add a function on the above form to `mygame/server/conf/inputfuncs.py`. Your
function must be in the global, outermost scope of that module and not start with an underscore
(`_`) to be recognized as an inputfunc.  Reload the server. That's it. To overload a default
inputfunc (see below), just add a function with the same name.

The modules Evennia looks into for inputfuncs are defined in the list `settings.INPUT_FUNC_MODULES`.
This list will be imported from left to right and later imported functions will replace earlier
ones.

## Default inputfuncs

Evennia defines a few default inputfuncs to handle the common cases. These are defined in
`evennia/server/inputfuncs.py`.

### text

 - Input: `("text", (textstring,), {})`
 - Output: Depends on Command triggered

This is the most common of inputcommands, and the only one supported by every traditional mud. The
argument is usually what the user sent from their command line. Since all text input from the user
like this is considered a [Command](Component/Commands), this inputfunc will do things like nick-replacement
and then pass on the input to the central Commandhandler.

### echo

 - Input: `("echo", (args), {})`
 - Output: `("text", ("Echo returns: %s" % args), {})`

This is a test input, which just echoes the argument back to the session as text. Can be used for
testing custom client input.

### default

The default function, as mentioned above, absorbs all non-recognized inputcommands. The default one
will just log an error.

### client_options

 - Input: `("client_options, (), {key:value, ...})`
 - Output:
  - normal: None
  - get: `("client_options", (), {key:value, ...})`

This is a direct command for setting protocol options. These are settable with the `@option`
command, but this offers a client-side way to set them. Not all connection protocols makes use of
all flags, but here are the possible keywords:

 - get (bool): If this is true, ignore all other kwargs and immediately return the current settings
as an outputcommand `("client_options", (), {key=value, ...})`-
 - client (str): A client identifier, like "mushclient".
 - version (str): A client version
 - ansi (bool): Supports ansi colors
 - xterm256 (bool): Supports xterm256 colors or not
 - mxp (bool): Supports MXP or not
 - utf-8 (bool): Supports UTF-8 or not
 - screenreader (bool): Screen-reader mode on/off
 - mccp (bool): MCCP compression on/off
 - screenheight (int): Screen height in lines
 - screenwidth (int): Screen width in characters
 - inputdebug (bool): Debug input functions
 - nomarkup (bool): Strip all text tags
 - raw (bool): Leave text tags unparsed 

> Note that there are two GMCP aliases to this inputfunc - `hello` and `supports_set`, which means
it will be accessed via the GMCP `Hello` and `Supports.Set` instructions assumed by some clients.

### get_client_options

 - Input: `("get_client_options, (), {key:value, ...})`
 - Output: `("client_options, (), {key:value, ...})`

This is a convenience wrapper that retrieves the current options by sending "get" to
`client_options` above.

### get_inputfuncs

- Input: `("get_inputfuncs", (), {})`
- Output: `("get_inputfuncs", (), {funcname:docstring, ...})`
 
Returns an outputcommand on the form `("get_inputfuncs", (), {funcname:docstring, ...})` - a list of
all the available inputfunctions along with their docstrings.

### login

> Note: this is currently experimental and not very well tested.

 - Input: `("login", (username, password), {})`
 - Output: Depends on login hooks

This performs the inputfunc version of a login operation on the current Session.

### get_value

Input: `("get_value", (name, ), {})`
Output: `("get_value", (value, ), {})`

Retrieves a value from the Character or Account currently controlled by this Session. Takes one
argument, This will only accept particular white-listed names, you'll need to overload the function
to expand. By default the following values can be retrieved:

 - "name" or "key": The key of the Account or puppeted Character.
 - "location": Name of the current location, or "None".
 - "servername": Name of the Evennia server connected to.

### repeat 

 - Input: `("repeat", (), {"callback":funcname, 
                       "interval": secs, "stop": False})` 
 - Output: Depends on the repeated function. Will return `("text", (repeatlist),{}` with a list of
accepted names if given an unfamiliar callback name.

This will tell evennia to repeatedly call a named function at a given interval. Behind the scenes
this will set up a [Ticker](Component/TickerHandler). Only previously acceptable functions are possible to
repeat-call in this way, you'll need to overload this inputfunc to add the ones you want to offer.
By default only two example functions are allowed, "test1" and "test2", which will just echo a text
back at the given interval. Stop the repeat by sending `"stop": True` (note that you must include
both the callback name and interval for Evennia to know what to stop).

### unrepeat

 - Input: `("unrepeat", (), ("callback":funcname, 
                             "interval": secs)`
 - Output: None

This is a convenience wrapper for sending "stop" to the `repeat` inputfunc. 

### monitor

 - Input: `("monitor", (), ("name":field_or_argname, stop=False)`
 - Output (on change): `("monitor", (), {"name":name, "value":value})`

This sets up on-object monitoring of Attributes or database fields. Whenever the field or Attribute
changes in any way, the outputcommand will be sent. This is using the
[MonitorHandler](Component/MonitorHandler) behind the scenes. Pass the "stop" key to stop monitoring. Note
that you must supply the name also when stopping to let the system know which monitor should be
cancelled.

Only fields/attributes in a whitelist are allowed to be used, you have to overload this function to
add more. By default the following fields/attributes can be monitored:

 - "name": The current character name 
 - "location": The current location
 - "desc": The description Argument

## unmonitor

 - Input: `("unmonitor", (), {"name":name})`
 - Output: None

A convenience wrapper that sends "stop" to the `monitor` function. 