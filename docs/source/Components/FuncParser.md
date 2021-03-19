# The Inline Function Parser

The [FuncParser](api:evennia.utils.funcparser.FuncParser) extracts and executes 'inline functions'
embedded in a string on the form `$funcname(args, kwargs)`. Under the hood, this will 
lead to a call to a Python function you control. The inline function call will be replaced by 
the return from the function.

```python 
from evennia.utils.funcparser import FuncParser

def _square(*args, **kwargs):
    """This will be callable as $square(number) in string"""
    return float(args[0]) ** 2

parser = FuncParser({"square": _square})

parser.parse("We have that 4 x 4 is $square(4).")
"We have that 4 x 4 is 16."

```

Normally the return is always converted to a string but you can also retrieve other data types
from the function calls:

```python
parser.parse_to_any("$square(4)")
16
```

To show a `$func()` verbatim in your code without parsing it, escape it as either `$$func()` or `\$func()`.

The point of inline-parsed functions is that they allow users to call dynamic code without giving 
regular users full access to Python. You can supply any python function to process the users' input. 

Here are some more examples: 

    "Let's meet at our guild hall. Here's how you get here: $route(Warrior's Guild)."

This can be parsed when sending messages, the users's current session passed into the callable. Assuming the 
game used a grid system and some path-finding mechanism, this would calculate the route to the guild 
individually for each recipient, such as:

    player1: "Let's meet at our guild hall. Here's how you get here: north,west,north,north.
    player2: "Let's meet at our guild hall. Here's how you get here: south,east.
    player3: "Let's meet at our guild hall. Here's how you get here: south,south,south,east.

It can be used (by user or developer) to implement _Actor stance emoting_ (2nd person) so people see
different variations depending on who they are (the [RPSystem contrib](../Contribs/Contrib-Overview) does 
this in a different way for _Director stance_):

    sendstr = "$me() $inflect(look) at the $obj(garden)."
    
    I see: "You look at the Splendid Green Garden."
    others see: "Anna looks at the Splendid Green Garden."

... embedded dice rolls ...

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

### Inlinefunc parsing

This is inactive by default. When active, Evennia will run the parser on _every outgoing string_
from a character, making the current [Session](./Sessions) available to every callable. This allows for a single string 
to appear differently to different users (see the example of `$route()` or `$me()`) above). 

To turn on this parsing, set `INLINEFUNC_ENABLED=True` in your settings file. You can add more callables in
`mygame/server/conf/inlinefuncs.py` and expand the list `INLINEFUNC_MODULES` with paths to modules containing
callables.
  
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
is mainly used for in-game protoype building. The prototype keys/values are parsed with the 
`FuncParser.parser_to_any` method so the user can set non-strings on prototype keys.

See the prototype documentation for which protfuncs are available.
    
## Using the FuncParser 
    
You can apply inline function parsing to any string. The 
[FuncParser](api:evennia.utils.funcparser.FuncParser) is found in `evennia.utils.funcparser.py`. 

```python
from evennia.utils import funcparser

parser = FuncParser(callables, **default_kwargs)
parsed_string = parser.parser(input_string, raise_errors=False, 
                              escape=False, strip=False, 
                              return_str=True, **reserved_kwargs)

# callables can also be passed as paths to modules
parser = FuncParser(["game.myfuncparser_callables", "game.more_funcparser_callables"])
```

- `callables` - This is either a `dict` mapping `{"funcname": callable, ...}`, a python path to 
a module or a list of such paths. If one or more paths, all top-level callables (whose name 
does not start with an underscore) in that module are used to build the mapping automatically.
- `raise_errors` - By default, any errors from a callable will be quietly ignored and the result 
  will be that the failing function call will show as if it was escaped. If `raise_errors` is set, 
  then parsing will stop and the error raised. It'd be up to you to handle this properly.
- `escape` - Returns a string where every `$func(...)` has been escaped as `\$func()`. This makes the 
  string safe from further parsing.
- `strip` - Remove all `$func(...)` calls from string (as if each returned `''`).
- `return_str` - When `True` (default), `parser` always returns a string. If `False`, it may return 
  the return value of a single function call in the string. This is the same as using the `.parse_to_any` 
  method.
- The `**default/reserved_keywords` are optional and allow you to pass custom data into _every_ function
  call. This is great for including things like the current session or config options. Defaults can be
  replaced if the user gives the same-named kwarg in the string's function call. Reserved kwargs 
  are always passed, ignoring defaults or what the user passed.

```python

def _test(*args, **kwargs):
    # do stuff
    return something

parser = funcparser.FuncParser({"test": _test}, mydefault=2)
result = parser.parse("$test(foo, bar=4)", myreserved=[1, 2, 3])

```

Here the callable will be called as `_test('foo', bar='4', mydefault=2, myreserved=[1, 2, 3])`. 
Note that everything given in the `$test(...)` call will enter the callable as strings. The 
kwargs passed outside will be passed as whatever type they were given as. The `mydef` kwarg
could be overwritten by `$test(mydefault=...)` but `myreserved` will always be sent as-is, ignoring
any same-named kwarg given to `$test`.

## Defining custom callables

All callables made available to the parser must have the following signature:

```python
def funcname(*args, **kwargs):
    # ...
    return something
```

As said, the input from the top-level string call will always be a string. However, if you 
nest functions the input may be the return from _another_ callable. This may not be a string.
Since you should expect users to mix and match function calls, you must make sure your callables 
gracefully can handle any input type.

On error, return an empty/default value or raise `evennia.utils.funcparser.ParsingError` to completely 
stop the parsing at any nesting depth (the `raise_errors` boolean will determine what happens).

Any type can be returned from the callable, but if its embedded in a longer string (or parsed without 
`return_str=True`), the final outcome will always be a string.

First, here are two useful tools for converting strings to other Python types in a safe way:

- [ast.literal_eval](https://docs.python.org/3.8/library/ast.html#ast.literal_eval) is an in-built Python
  function. It
  _only_ supports strings, bytes, numbers, tuples, lists, dicts, sets, booleans and `None`. That's
  it - no arithmetic or modifications of data is allowed. This is good for converting individual values and
  lists/dicts from the input line to real Python objects.
- [simpleeval](https://pypi.org/project/simpleeval/) is imported by Evennia. This allows for safe evaluation
  of simple (and thus safe) expressions. One can operate on numbers and strings with +-/* as well 
  as do simple comparisons like `4 > 3` and more. It does _not_ accept more complex containers like 
  lists/dicts etc, so the two are complementary to each other.

First we try `literal_eval`. This also illustrates how input types work.

```python
from ast import literal_eval

def _literal(*args, **kwargs):
    if args:
        try:
            return literal_eval(args[0])
        except ValueError:
            pass
    return ''
   
def _add(*args, **kwargs):
  if len(args) > 1:
      return args[0] + args[1]
  return ''

parser = FuncParser({"literal": _literal, "add": _add})
```

We first try to add two numbers together straight up

```python
parser.parse("$add(5, 10)")
"510"
```
The result is that we concatenated the strings "5" + "10" which is not what we wanted. This 
because the arguments from the top level string always enter the callable as strings. We next
try to convert each input value:

```python
parser.parse("$add($lit(5), $lit(10))")
"15"
parser.parse_to_any("$add($lit(5), $lit(10))")
15
parser.parse_to_any("$add($lit(5), $lit(10)) and extra text")
"15 and extra text"
```
Now we correctly convert the strings to numbers and add them together. The result is still a string unless
we use `parse_to_any` (or `.parse(..., return_str=False)`). If we include the call as part of a bigger string,
the outcome is always be a string. 

In this case, `simple_eval` makes things easier:

```python
from simpleeval import simple_eval

def _eval((*args, **kwargs):
    if args:
        try:
            return simple_eval(args[0])
        except Exception as err:
            return f"<Error: {err}>"
            
parser = FuncParser({"eval": _eval})
parser.parse_to_any("5 + 10")
10

```

This is a lot more natural in this case, but `literal_eval` can convert things like lists/dicts that the
`simple_eval` cannot. Here we also tried out a different way to handle errors - by letting an error replace
the `$func`-call directly in the string. This is not always suitable.

```warning::
   It may be tempting to run Python's in-built `eval()` or `exec()` commands on the input in order to convert 
   it from a string to regular Python objects. NEVER DO THIS. The parser is intended for untrusted users (if
   you were trusted you'd have access to Python already). Letting untrusted users pass strings to eval/exec 
   is a MAJOR security risk. It allows the caller to effectively run arbitrary Python code on your server. 
   This is the way to maliciously deleted hard drives. Just don't do it and sleep better at night.
```

## Example:

An 

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