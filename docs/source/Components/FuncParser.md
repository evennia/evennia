# The Inline Function Parser

The [FuncParser](evennia.utils.funcparser.FuncParser) extracts and executes
'inline functions'
embedded in a string on the form `$funcname(args, kwargs)`. Under the hood, this will
lead to a call to a Python function you control. The inline function call will be replaced by
the return from the function.

```python
from evennia.utils.funcparser import FuncParser

def _power_callable(*args, **kwargs):
    """This will be callable as $pow(number, power=<num>) in string"""
    pow = int(kwargs.get('power', 2))
    return float(args[0]) ** pow

# create a parser and tell it that '$pow' means using _power_callable
parser = FuncParser({"pow": _power_callable})

```
Next, just pass a string into the parser, containing `$func(...)` markers:

```python
parser.parse("We have that 4 x 4 x 4 is $pow(4, power=3).")
"We have that 4 x 4 x 4 is 64."
```

Normally the return is always converted to a string but you can also get the actual data type from the call:

```python
parser.parse_to_any("$pow(4)")
16
```

To show a `$func()` verbatim in your code without parsing it, escape it as either `$$func()` or `\$func()`:


```python
parser.parse("This is an escaped $$pow(4) and so is this \$pow(3)")
"This is an escaped $pow(4) and so is this $pow(3)"
```

## Uses in default Evennia

The FuncParser can be applied to any string. Out of the box it's applied in a few situations:

- _Outgoing messages_. All messages sent from the server is processed through FuncParser and every
  callable is provided the [Session](./Sessions.md) of the object receiving the message. This potentially
  allows a message to be modified on the fly to look different for different recipients.
- _Prototype values_. A [Prototype](./Prototypes.md) dict's values are run through the parser such that every
  callable gets a reference to the rest of the prototype. In the Prototype ORM, this would allow builders
  to safely call functions to set non-string values to prototype values, get random values, reference
  other fields of the prototype, and more.
- _Actor-stance in messages to others_. In the
  [Object.msg_contents](evennia.objects.objects.DefaultObject.msg_contents) method,
  the outgoing string is parsed for special `$You()` and `$conj()` callables to decide if a given recipient
  should see "You" or the character's name.

```{important}
   The inline-function parser is not intended as a 'softcode' programming language. It does not
   have things like loops and conditionals, for example. While you could in principle extend it to
   do very advanced things and allow builders a lot of power, all-out coding is something
   Evennia expects you to do in a proper text editor, outside of the game, not from inside it.
```

## Using the FuncParser

You can apply inline function parsing to any string. The
[FuncParser](evennia.utils.funcparser.FuncParser) is imported as `evennia.utils.funcparser`.

```python
from evennia.utils import funcparser

parser = FuncParser(callables, **default_kwargs)
parsed_string = parser.parse(input_string, raise_errors=False,
                              escape=False, strip=False,
                              return_str=True, **reserved_kwargs)

# callables can also be passed as paths to modules
parser = FuncParser(["game.myfuncparser_callables", "game.more_funcparser_callables"])
```

Here, `callables` points to a collection of normal Python functions (see next section) for you to make
available to the parser as you parse strings with it. It can either be
- A `dict` of `{"functionname": callable, ...}`. This allows you do pick and choose exactly which callables
  to include and how they should be named. Do you want a callable to be available under more than one name?
  Just add it multiple times to the dict, with a different key.
- A `module` or (more commonly) a `python-path` to a module. This module can define a dict
  `FUNCPARSER_CALLABLES = {"funcname": callable, ...}` - this will be imported and used like the `dict` above.
  If no such variable is defined, _every_ top-level function in the module (whose name doesn't start with
  an underscore `_`) will be considered a suitable callable. The name of the function will be the `$funcname`
  by which it can be called.
- A `list` of modules/paths. This allows you to pull in modules from many sources for your parsing.
- The `**default` kwargs are optional kwargs that will be passed to _all_
  callables every time this parser is used - unless the user overrides it explicitly in
  their call. This is great for providing sensible standards that the user can
  tweak as needed.

`FuncParser.parse` takes further arguments, and can vary for every string parsed.

- `raise_errors` - By default, any errors from a callable will be quietly ignored and the result
  will be that the failing function call will show verbatim. If `raise_errors` is set,
  then parsing will stop and whatever exception happened will be raised. It'd be up to you to handle
  this properly.
- `escape` - Returns a string where every `$func(...)` has been escaped as `\$func()`.
- `strip` - Remove all `$func(...)` calls from string (as if each returned `''`).
- `return_str` - When `True` (default), `parser` always returns a string. If `False`, it may return
  the return value of a single function call in the string. This is the same as using the `.parse_to_any`
  method.
- The `**reserved_keywords` are _always_ passed to every callable in the string.
  They override any `**defaults` given when instantiating the parser and cannot
  be overridden by the user - if they enter the same kwarg it will be ignored.
  This is great for providing the current session, settings etc.
- The `funcparser` and `raise_errors`
  are always added as reserved keywords - the first is a
  back-reference to the `FuncParser` instance and the second
  is the `raise_errors` boolean given to `FuncParser.parse`.

Here's an example of using the default/reserved keywords:

```python
def _test(*args, **kwargs):
    # do stuff
    return something

parser = funcparser.FuncParser({"test": _test}, mydefault=2)
result = parser.parse("$test(foo, bar=4)", myreserved=[1, 2, 3])
```
Here the callable will be called as

```python
_test('foo', bar='4', mydefault=2, myreserved=[1, 2, 3],
      funcparser=<FuncParser>, raise_errors=False)
```

The `mydefault=2` kwarg could be overwritten if we made the call as `$test(mydefault=...)`
but `myreserved=[1, 2, 3]` will _always_ be sent as-is and will override a call `$test(myreserved=...)`.
The `funcparser`/`raise_errors` kwargs are also always included as reserved kwargs.

## Defining custom callables

All callables made available to the parser must have the following signature:

```python
def funcname(*args, **kwargs):
    # ...
    return something
```

> The `*args` and `**kwargs` must always be included. If you are unsure how `*args` and `**kwargs` work in Python,
> [read about them here](https://www.digitalocean.com/community/tutorials/how-to-use-args-and-kwargs-in-python-3).

The input from the innermost `$funcname(...)` call in your callable will always be a `str`. Here's
an example of an `$toint` function; it converts numbers to integers.

    "There's a $toint(22.0)% chance of survival."

What will enter the `$toint` callable (as `args[0]`) is the _string_ `"22.0"`. The function is responsible
for converting this to a number so that we can convert it to an integer. We must also properly handle invalid
inputs (like non-numbers).

If you want to mark an error, raise `evennia.utils.funcparser.ParsingError`. This stops the entire parsing
of the string and may or may not raise the exception depending on what you set `raise_errors` to when you
created the parser.

However, if you _nest_ functions, the return of the innermost function may be something other than
a string. Let's introduce the `$eval` function, which evaluates simple expressions using
Python's `literal_eval` and/or `simple_eval`. It returns whatever data type it
evaluates to.

    "There's a $toint($eval(10 * 2.2))% chance of survival."

Since the `$eval` is the innermost call, it will get a string as input - the string `"10 * 2.2"`.
It evaluates this and returns the `float` `22.0`. This time the outermost `$toint` will be called with
this `float` instead of with a string.

> It's important to safely validate your inputs since users may end up nesting your callables in any order.
> See the next section for useful tools to help with this.

In these examples, the result will be embedded in the larger string, so the result of the entire parsing
will be a string:

```python
  parser.parse(above_string)
  "There's a 22% chance of survival."
```

However, if you use the `parse_to_any` (or `parse(..., return_str=False)`) and
_don't add any extra string around the outermost function call_,
you'll get the return type of the outermost callable back:

```python
parser.parse_to_any("$toint($eval(10 * 2.2)")
22
parser.parse_to_any("the number $toint($eval(10 * 2.2).")
"the number 22"
parser.parse_to_any("$toint($eval(10 * 2.2)%")
"22%"
```

### Escaping special character

When entering funcparser callables in strings, it looks like a regular
function call inside a string:

```python
"This is a $myfunc(arg1, arg2, kwarg=foo)."
```

Commas (`,`) and equal-signs (`=`) are considered to separate the arguments and
kwargs. In the same way, the right parenthesis (`)`) closes the argument list.
Sometimes you want to include commas in the argument without it breaking the
argument list.

```python
"The $format(forest's smallest meadow, with dandelions) is to the west."
```

You can escape in various ways.

- Prepending special characters like `,` and `=` with the escape character `\`

```python
"The $format(forest's smallest meadow\, with dandelions) is to the west."
```

- Wrapping your strings in double quotes. Unlike in raw Python, you
can't escape with single quotes `'` since these could also be apostrophes (like
`forest's` above). The result will be a verbatim string that contains
everything but the outermost double quotes.

```python
'The $format("forest's smallest meadow, with dandelions") is to the west.'
```
- If you want verbatim double-quotes to appear in your string, you can escape
  them with `\"` in turn.

```python
'The $format("forest's smallest meadow, with \"dandelions\"') is to the west.'
```

### Safe convertion of inputs

Since you don't know in which order users may use your callables, they should
always check the types of its inputs and convert to the type the callable needs.
Note also that when converting from strings, there are limits what inputs you
can support. This is because FunctionParser strings can be used by
non-developer players/builders and some things (such as complex
classes/callables etc) are just not safe/possible to convert from string
representation.

In `evennia.utils.utils` is a helper called
[safe_convert_to_types](evennia.utils.utils.safe_convert_to_types). This function
automates the conversion of simple data types in a safe way:

```python
from evennia.utils.utils import safe_convert_to_types

def _process_callable(*args, **kwargs):
    """
    $process(expression, local, extra1=34, extra2=foo)

    """
    args, kwargs = safe_convert_to_type(
      (('py', str), {'extra1': int, 'extra2': str}),
      *args, **kwargs)

    # args/kwargs should be correct types now

```

In other words, in the callable `$process(expression, local, extra1=..,
extra2=...)`, the first argument will be handled by the 'py' converter
(described below), the second will passed through regular Python `str`,
kwargs will be handled by `int` and `str` respectively. You can supply
your own converter function as long as it takes one argument and returns
the converted result.

In other words,

```python
args, kwargs = safe_convert_to_type(
        (tuple_of_arg_converters, dict_of_kwarg_converters), *args, **kwargs)
```

The special converter `"py"` will try to convert a string argument to a Python structure with the help of the
following tools (which you may also find useful to experiment with on your own):

- [ast.literal_eval](https://docs.python.org/3.8/library/ast.html#ast.literal_eval) is an in-built Python
  function. It
  _only_ supports strings, bytes, numbers, tuples, lists, dicts, sets, booleans and `None`. That's
  it - no arithmetic or modifications of data is allowed. This is good for converting individual values and
  lists/dicts from the input line to real Python objects.
- [simpleeval](https://pypi.org/project/simpleeval/) is a third-party tool included with Evennia. This
  allows for evaluation of simple (and thus safe) expressions. One can operate on numbers and strings
  with `+-/*` as well as do simple comparisons like `4 > 3` and more. It does _not_ accept more complex
  containers like lists/dicts etc, so this and `literal_eval` are complementary to each other.

```{warning}
   It may be tempting to run use Python's in-built ``eval()`` or ``exec()`` functions as converters since
   these are able to convert any valid Python source code to Python. NEVER DO THIS unless you really, really
   know that ONLY developers will ever modify the string going into the callable. The parser is intended
   for untrusted users (if you were trusted you'd have access to Python already). Letting untrusted users
   pass strings to ``eval``/``exec`` is a MAJOR security risk. It allows the caller to run arbitrary
   Python code on your server. This is the path to maliciously deleted hard drives. Just don't do it and
   sleep better at night.
```

## Default callables

These are some example callables you can import and add your parser. They are divided into
global-level dicts in `evennia.utils.funcparser`. Just import the dict(s) and merge/add one or
more to them when you create your `FuncParser` instance to have those callables be available.

### `evennia.utils.funcparser.FUNCPARSER_CALLABLES`

These are the 'base' callables.

- `$eval(expression)` ([code](evennia.utils.funcparser.funcparser_callable_eval)) -
  this uses `literal_eval` and `simple_eval` (see previous section) attemt to convert a string expression
  to a python object. This handles e.g. lists of literals `[1, 2, 3]` and simple expressions like `"1 + 2"`.
- `$toint(number)` ([code](evennia.utils.funcparser.funcparser_callable_toint)) -
  always converts an output to an integer, if possible.
- `$add/sub/mult/div(obj1, obj2)` ([code](evennia.utils.funcparser.funcparser_callable_add)) -
  this adds/subtracts/multiplies and divides to elements together. While simple addition could be done with
  `$eval`, this could for example be used also to add two lists together, which is not possible with `eval`;
  for example `$add($eval([1,2,3]), $eval([4,5,6])) -> [1, 2, 3, 4, 5, 6]`.
- `$round(float, significant)` ([code](evennia.utils.funcparser.funcparser_callable_round)) -
  rounds an input float into the number of provided significant digits. For example `$round(3.54343, 3) -> 3.543`.
- `$random([start, [end]])` ([code](evennia.utils.funcparser.funcparser_callable_random)) -
  this works like the Python `random()` function, but will randomize to an integer value if both start/end are
  integers. Without argument, will return a float between 0 and 1.
- `$randint([start, [end]])` ([code](evennia.utils.funcparser.funcparser_callable_randint)) -
  works like the `randint()` python function and always returns an integer.
- `$choice(list)` ([code](evennia.utils.funcparser.funcparser_callable_choice)) -
  the input will automatically be parsed the same way as `$eval` and is expected to be an iterable. A random
  element of this list will be returned.
- `$pad(text[, width, align, fillchar])` ([code](evennia.utils.funcparser.funcparser_callable_pad)) -
  this will pad content. `$pad("Hello", 30, c, -)` will lead to a text centered in a 30-wide block surrounded by `-`
  characters.
- `$crop(text, width=78, suffix='[...]')` ([code](evennia.utils.funcparser.funcparser_callable_crop)) -
  this will crop a text longer than the width, by default ending it with a `[...]`-suffix that also fits within
  the width. If no width is given, the client width or `settings.DEFAULT_CLIENT_WIDTH` will be used.
- `$space(num)` ([code](evennia.utils.funcparser.funcparser_callable_space)) -
  this will insert `num` spaces.
- `$just(string, width=40, align=c, indent=2)` ([code](evennia.utils.funcparser.funcparser_callable_justify)) -
  justifies the text to a given width, aligning it left/right/center or 'f' for full (spread text across width).
- `$ljust` - shortcut to justify-left. Takes all other kwarg of `$just`.
- `$rjust` - shortcut to right justify.
- `$cjust` - shortcut to center justify.
- `$clr(startcolor, text[, endcolor])` ([code](evennia.utils.funcparser.funcparser_callable_clr)) -
   color text. The color is given with one or two characters without the preceeding `|`. If no endcolor is
   given, the string will go back to neutral, so `$clr(r, Hello)` is equivalent to `|rHello|n`.

### `evennia.utils.funcparser.SEARCHING_CALLABLES`

These are callables that requires access-checks in order to search for objects. So they require some
extra reserved kwargs to be passed when running the parser:

```python

parser.parse_to_any(string, caller=<object or account>, access="control", ...)

```
The `caller` is required, it's the the object to do the access-check for. The `access` kwarg is the
 [lock type](./Locks.md) to check, default being `"control"`.

- `$search(query,type=account|script,return_list=False)` ([code](evennia.utils.funcparser.funcparser_callable_search)) -
  this will look up and try to match an object by key or alias. Use the `type` kwarg to
  search for `account` or `script` instead. By default this will return nothing if there are more than one
  match; if `return_list` is `True` a list of 0, 1 or more matches will be returned instead.
- `$obj(query)`, `$dbref(query)` - legacy aliases for `$search`.
- `$objlist(query)` - legacy alias for `$search`, always returning a list.


### `evennia.utils.funcparser.ACTOR_STANCE_CALLABLES`

These are used to implement actor-stance emoting. They are used by the
[DefaultObject.msg_contents](evennia.objects.objects.DefaultObject.msg_contents) method
by default. You can read a lot more about this on the page
[Change messages per receiver](../Concepts/Change-Messages-Per-Receiver.md).

On the parser side, all these inline functions require extra kwargs be passed into the parser
(done by `msg_contents` by default):

```python
parser.parse(string, caller=<obj>, receiver=<obj>, mapping={'key': <obj>, ...})
```

Here the `caller` is the one sending the message and `receiver` the one to see it. The `mapping` contains
references to other objects accessible via these callables.

- `$you([key])` ([code](evennia.utils.funcparser.funcparser_callable_you)) -
  if no `key` is given, this represents the `caller`, otherwise an object from `mapping`
  will be used. As this message is sent to different recipients, the `receiver` will change and this will
  be replaced either with the string `you` (if you and the receiver is the same entity) or with the
  result of `you_obj.get_display_name(looker=receiver)`. This allows for a single string to echo differently
  depending on who sees it, and also to reference other people in the same way.
- `$You([key])` - same as `$you` but always capitalized.
- `$conj(verb)` ([code](evennia.utils.funcparser.funcparser_callable_conjugate)) - conjugates a verb
  between 2nd person presens to 3rd person presence depending on who
  sees the string. For example `"$You() $conj(smiles)".` will show as "You smile." and "Tom smiles." depending
  on who sees it. This makes use of the tools in [evennia.utils.verb_conjugation](evennia.utils.verb_conjugation)
  to do this, and only works for English verbs.
- `$pron(pronoun [,options])` ([code](evennia.utils.funcparser.funcparser_callable_pronoun)) - Dynamically
  map pronouns (like his, herself, you, its etc) between 1st/2nd person to 3rd person.

### Example

Here's an example of including the default callables together with two custom ones.

```python
from evennia.utils import funcparser
from evennia.utils import gametime

def _dashline(*args, **kwargs):
    if args:
        return f"\n-------- {args[0]} --------"
    return ''

def _uptime(*args, **kwargs):
    return gametime.uptime()

callables = {
    "dashline": _dashline,
    "uptime": _uptime,
    **funcparser.FUNCPARSER_CALLABLES,
    **funcparser.ACTOR_STANCE_CALLABLES,
    **funcparser.SEARCHING_CALLABLES
}

parser = funcparser.FuncParser(callables)

string = "This is the current uptime:$dashline($toint($uptime()) seconds)"
result = parser.parse(string)

```

Above we define two callables `_dashline` and `_uptime` and map them to names `"dashline"` and `"uptime"`,
which is what we then can call as `$header` and `$uptime` in the string. We also have access to
all the defaults (like `$toint()`).

The parsed result of the above would be something like this:

    This is the current uptime:
    ------- 343 seconds -------
