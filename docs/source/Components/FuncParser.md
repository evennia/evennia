# The Inline Function Parser

The [FuncParser](api:evennia.utils.funcparser.FuncParser) extracts and executes 'inline functions'
embedded in a string on the form `$funcname(args, kwargs)`. Under the hood, this will 
lead to a call to a same-named Python function you control. The inline function call will be 
replaced by the return from the function.

A common use is to grant common players the ability to create dynamic content without access to 
Python. But inline functions are also potentially useful for developers. 

Here are some examples:

    "Let's meet at our guild hall. Here's how you get here: $route(Warrior's Guild)."
    
In this example, the `$route()` call would be evaluated as an inline function call. Assuming the game
used a grid system and some path-finding mechanism, this would calculate the route to the guild
individually for each recipient, such as: 

    "Let's meet at our guild hall. Here's how you get here: north,west,north,north.
    "Let's meet at our guild hall. Here's how you get here: south,east.
    "Let's meet at our guild hall. Here's how you get here: south,south,south,east.
    
It can be used (by user or developer) to implement _Actor stance emoting_ (2nd person) so people see 
different variations depending on who they are (the [RPSystem contrib](../Contribs/Contrib-Overview) does this in 
a different way for _Director stance_):

    sendstr = "$me() $inflect(look) at the $obj(garden)."
    
    I see: "You look at the Splendid green Garden."
    others see: "Anna looks at the Splendid green Garden."
    
One could do simple mathematical operations ...
   
    "There are $eval(4**2) possibilities ..."
    "There are 16 possibilities ..."    
    
... Or why not embedded dice rolls ...

    "I make a sweeping attack and roll $roll(2d6)!"
    "I make a sweeping attack and roll 8 (3+5 on 2d6)!"
    
Function calls can also be nested. Here's an example of inline formatting

    "This is a $fmt('-' * 20, $clr(r, red text)!, '-' * 20")
    "This is a --------------------red text!--------------------" 
    
```important::
    The inline-function parser is not intended as a 'softcode' programming language. It does not
    have things like loops and conditionals, for example. While you could in principle extend it to 
    do very advanced things and allow builders a lot of power, all-out coding is something 
    Evennia expects you to do in a proper text editor, outside of the game, not from inside it.
```


## Standard uses of parser
Out of the box, Evennia applies the parser in two situations: 

### Inlinefuncs 

The original use for inline function parsing. When enabled (disabled by default), Evennia will 
apply the parser to every client-bound outgoing message. This is per-Session and 
`session=<current_session>` is always passed into each callable. This allows for things like 
the per-receiver `$route` in the example above.

- To enable inlinefunc parsing, set `INLINEFUNC_ENABLED=True` in your settings file 
  (`mygame/server/conf/settings.py`) and reload.
- To add more functions, you can just add them to the pre-made module in 
  `mygame/server/conf/inlinefuncs.py`. Evennia will look here and use all top-level functions you add
  (unless their name starts with an underscore).
- If you want to get inlinefuncs from other places, `INLINEFUNC_MODULES` is a list of the paths
  Evennia will use to find new modules with callables. See defaults in `evennia/settings_default.py`.
  
These are some example callables distributed with Evennia for inlinefunc-use.

- `$random([minval, maxval])` - produce a random number. `$random()` will give a random 
  number between 0 and 1. Giving a min/maxval will give a random value between these numbers.
  If only one number is given, a random value from 0...number will be given.
  The result will be an int or a float depending on if you give decimals or not.
- `$pad(text[, width, align, fillchar])` - this will pad content. `$pad("Hello", 30, c, -)`
  will lead to a text centered in a 30-wide block surrounded by `-` characters.
- `$crop(text, width=78, suffix='[...]')` - this will crop a text longer than the width,
  ending it with a `[...]`-suffix that also fits within the width.
- `$space(num)` - this will insert `num` spaces.
- `$clr(startcolor, text[, endcolor])` - color text. The color is given with one or two characters
  without the preceeding `|`. If no endcolor is given, the string will go back to neutral. 
  so `$clr(r, Hello)` is equivalent to `|rHello|n`. 


### Protfuncs

Evennia applies the parser on the keys and values of [Prototypes definitions](./Prototypes). This 
is meant for a user of the OLC to create prototypes with dynamic content (such as random stats). 

See the prototype documentation for which protfuncs are available.

    
## Using the FuncParser 
    
You can apply inline function parsing to any string. The 
[FuncParser](api:evennia.utils.funcparser.FuncParser) is found in `evennia.utils.funcparser.py`. 
Here's how it's used:

```python
from evennia.utils import funcparser

parser = FuncParser(callables, **default_kwargs)
parsed_string = parser.parser(input_string, raise_errors=False, **reserved_kwargs)

```

The `callables` is either a `dict` mapping `{"funcname": callable, ...}`, a python path to 
a module or a list of such paths. If one or more paths, all top-level callables (whose name 
does not start with an underscore) in that module are used to build the mapping automatically.

By default, any errors from a callable will be quietly ignored and the result will be that 
the un-parsed form of the callable shows in the string instead. If `raise_errors` is set, 
then an error will stop parsing and a `evennia.utils.funcparser.ParsingError` will be raised
with a string of info about the problem. It'd be up to you to handle this properly.

The default/reserved keywords are optional and allow you to pass custom data into _every_ function
call. This is great for including things like the current session or config options. See the next
section for details. 


```python
parser = funcparser.FuncParser(callables, test='bar')
result = parser.parse("$header(foo)")
```

Here the callable (`_header` from the first example) will be called as `_header('foo', test='bar')`. All
callables called through this parser will get this extra keyword passed to them. These does _not_ have 
to be strings.

Default keywords will be overridden if changed in the function call: 

```python
result = parser.parse("$header(foo, test=moo)")
```

Now the callable will be called as `_header('foo', test='moo'`) instead. Note that the values passed
in from the string will always enter the callable as strings.

If you want to _guarantee_ a certain keyword is always passed, you should pass it when you call `.parse`:

``` python
result = parser.parser("$header(foo, test=moo)", test='override')
```

The kwarg passed with `.parse` overrides the others, so now `_header('foo', test='override')` will
be called. Like for default kwargs, these keywords do _not_ have to be strings. This is very useful 
when you must pass something for the functionality to work. You may for example want to pass the 
current user's Session as `session=session` so you can customize the response per-user.


## Callables

All callables made available to the parser must have the following signature:

```python
def funcname(*args, **kwargs):
    # ...
    return string
```

It's up to you as the dev to correctly parse all possible input. Remember that this may be called 
by untrusted users. If the return is not a string, it will be converted to one, so make sure this
is possible. 

> Note, returning nothing is the same as returning `None` in Python, and this will convert to a 
> string `"None"`. You usually want to return the empty string `''` instead.

While the default/reserved kwargs can be any data type, the data from the parsed function call 
itself will always be of type `str`. If you want more complex operations you need to convert 
from the string to the data type you want.

Evennia comes with the [simpleeval](https://pypi.org/project/simpleeval/) package, which
can be used for safe evaluation of simple (and thus safe) expressions.

```warning::
   Inline-func parsing can be made to operate on any string, including strings from regular users. It may 
   be tempting to run the Python full `eval()` or `exec()` commands on the input in order to convert it 
   from a string to regular Python objects. NEVER DO THIS. This would be a major security problem since it 
   would allow the user to effectively run arbitrary Python code on your server. There are plenty of 
   examples to find online showing how a malicious user could mess up your system this way. If you ever 
   decide to use eval/exec you should be 100% sure that it operates on strings that untrusted users 
   can't modify.
```

## Example of usage

Here's a simple example 

```python
from evennia.utils import funcparser
from evennia.utils import gametime

def _header(*args, **kwargs):
    if args:
        return "\n-------- {args[0]} --------"
    return ''

def _uptime(*args, **kwargs):
    return gametime.uptime()

callables = {
    "header": _header,
    "uptime": _uptime
}

parser = funcparser.FuncParser(callables)

string = "This is the current uptime:$header($uptime() seconds)"
result = parser.parse(string)

```

Above we define two callables `_header` and `_uptime` and map them to names `"header"` and `"uptime"`,
which is what we then can call as `$header` and `$uptime` in the string. 

We nest the functions so the parsed result of the above would be something like this: 

```
This is the current uptime:
------- 343 seconds ------- 
```

