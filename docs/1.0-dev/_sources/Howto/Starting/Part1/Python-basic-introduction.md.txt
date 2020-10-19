# Starting to code Evennia

Time to dip our toe into some coding! Evennia is written and extended in [Python](http://python.org), which
is a mature and professional programming language that is very fast to work with.

That said, even though Python is widely considered easy to learn, we can only cover the most immediately
important aspects of Python in this series of starting tutorials. Hopefully we can get you started
but then you'll need to continue learning from there. See our [link section](../../../Links) for finding
more reference material and dedicated Python tutorials.

> While this will be quite basic if you are an experienced developer, you may want to at least
> stay around for the first few sections where we cover how to run Python from inside Evennia.

First, if you were quelling yourself to play the tutorial world, make sure to get your
superuser powers back:

       unquell


### Evennia Hello world

The `py` Command (or `!`, which is an alias) allows you as a superuser to execute raw Python from in-
game. This is useful for quick testing. From the game's input line, enter the following:

    > py print("Hello World!")


```sidebar:: Command input

    The line with `>` indicates input to enter in-game, while the lines below are the
    expected return from that input.
```

You will see

    > print("Hello world!")
    Hello World!

To understand what is going on: some extra info: The `print(...)` *function* is the basic, in-built
way to output text in Python. We are sending "Hello World" as an _argument_ to this function. The quotes `"..."`
mean that you are inputting a *string* (i.e. text). You could also have used single-quotes `'...'`,
Python accepts both. A third variant is triple-quotes (`"""..."""` or `'''...'''`, which work across multiple
lines and are common for larger text-blocks. The way we use the `py` command right now only supports
single-line input however.

### Making some text 'graphics'

When making a text-game you will, unsurprisingly, be working a lot with text. Even if you have the occational
button or even graphical element, the normal process is for the user to input commands as
text and get text back. As we saw above, a piece of text is called a _string_ in Python and is enclosed in
either single- or double-quotes.

Strings can be added together:

    > py print("This is a " + "breaking change.")
    This is a breaking change.

A string multiplied with a number will repeat that string as many times:

    > py print("|" + "-" * 40 + "|")
    |----------------------------------------|

 or

    > py print("A" + "a" * 5 + "rgh!")
    Aaaaaargh!

While combining different strings is useful, even more powerful is the ability to modify the contents
of the string in-place. There are several ways to do this in Python and we'll show two of them here. The first
is to use the `.format` _method_ of the string:

    > py print("This is a {} idea!".format("good"))
    This is a good idea!

```sidebar:: Functions and Methods

    Function:
        Something that performs and action when you `call` it with zero or more `arguments`. A function
        is stand-alone in a python module, like `print()`
    Method:
        A function that sits "on" an object, like `<string>.format()`.
```

A method can be thought of as a resource "on" another object. The method knows on which object it
sits and can thus affect it in various ways. You access it with the period `.`. In this case, the
string has a resource `format(...)` that modifies it. More specifically, it replaced the `{}` marker
inside the string with the value passed to the format. You can do so many times:

    > py print("This is a {} idea!".format("bad"))
    This is a bad idea!

or

    > py print("This is the {} and {} {} idea!".format("first", "second", "great"))
    This is the first and second great idea!

> Note the double-parenthesis at the end - the first closes the `format(...` method and the outermost
closes the `print(...`. Not closing them will give you a scary `SyntaxError`. We will talk a
little more about errors in the next section, for now just fix until it prints as expected.

Here we passed three comma-separated strings as _arguments_ to the string's `format` method. These
replaced the `{}` markers in the same order as they were given.

The input does not have to be strings either:

    > py print("STR: {}, DEX: {}, INT: {}".format(12, 14, 8))
    STR: 12, DEX: 14, INT: 8

To separate two Python instructions on the same line, you use the semi-colon, `;`. Try this:

    > py a = "awesome sauce" ; print("This is {}!".format(a))
    This is awesome sauce!

```warning:: MUD clients and semi-colon

    Some MUD clients use the semi-colon `;` to split client-inputs
    into separate sends. If so, the above will give an error. Most clients allow you to
    run in 'verbatim' mode or to remap to use some other separator than `;`. If you still have
    trouble, just use the Evennia web client for now. In real Python code you'll pretty much never use
    the semi-colon.
```

What happened here was that we _assigned_ the string `"awesome sauce"` to a _variable_ we chose
to name `a`. In the next statement, Python remembered what `a` was and we passed that into `format()`
to get the output. If you replaced the value of `a` with something else in between, _that_ would be printed
instead.

Here's the stat-example again, moving the stats to variables (here we just set them, but in a real
game they may be changed over time, or modified by circumstance):

    > py str, dex, int = 13, 14, 8 ; print("STR: {}, DEX: {}, INT: {}".format(stren, dex, int))
    STR: 13, DEX: 14, INT: 8

The point is that even if the values of the stats change, the print() statement would not change - it just keeps
pretty-printing whatever is given to it.

Using `.format()` is convenient (and there is a [lot more](https://www.w3schools.com/python/ref_string_format.asp)
you can do with it). But the _f-string_ can be even more convenient. An
f-string looks like a normal string ... except there is an `f` front of it, like this:

    f"this is now an f-string."

An f-string on its own is just like any other string. But let's redo the example we did before, using an f-string:

    > py a = "awesome sauce" ; print(f"This is {a}!")
    This is awesome sauce!

We could just insert that `a` variable directly into the f-string using `{a}`. Fewer parentheses to
remember and arguable easier to read as well.

    > py str, dex, int = 13, 14, 8 ; print(f"STR: {str}, DEX: {dex}, INT: {int}")
    STR: 13, DEX: 14, INT: 8

We will be exploring more complex string concepts when we get to creating Commands and need to
parse and understand player input.

Python itself knows nothing about colored text, this is an Evennia thing. Evennia supports the
standard color schemes of traditional MUDs.

    > py print("|rThis is red text!|n This is normal color.")

Adding that `|r` at the start will turn our output bright red. `|R` will make it dark red. `|n`
gives the normal text color. You can also use RGB (Red-Green-Blue) values from 0-5 (Xterm256 colors):

    > py print("|043This is a blue-green color.|[530|003 This is dark blue text on orange background.")

> If you don't see the expected color, your client or terminal may not support Xterm256 (or
  color at all). Use the Evennia webclient.

Use the commands `color ansi` or `color xterm` to see which colors are available. Experiment!

### Importing code from other modules

As we saw in the previous sections, we used `.format` to format strings and `me.msg` to access
the `msg` method on `me`. This use of the full-stop character is used to access all sorts of resources,
including that in other Python modules.

Keep your game running, then open a text editor of your choice. If your game folder is called
`mygame`, create a new text file `test.py` in the subfolder `mygame/world`. This is how the file
structure should look:

```
mygame/
    world/
        test.py
```

For now, only add one line to `test.py`:

```python
print("Hello World!")
```

```sidebar:: Python module

    This is a text file with the `.py` file ending. A module
    contains Python source code and from within Python one can
    access its contents by importing it via its python-path.

```

Don't forget to _save_ the file. We just created our first Python _module_!
To use this in-game we have to *import* it. Try this:

    > py import world.test
    Hello World

If you make some error (we'll cover how to handle errors below), fix the error in the module and
run the `reload` command in-game for your changes to take effect.

So importing `world.test` actually means importing `world/test.py`. Think of the period `.` as
replacing `/` (or `\` for Windows) in your path. The `.py` ending of `test.py` is also never
included in this "Python-path", but _only_ files with that ending can be imported this way.
Where is `mygame` in that Python-path? The answer is that Evennia has already told Python that
your `mygame` folder is a good place to look for imports. So we don't include `mygame` in the
path - Evennia handles this for us.

When you import the module, the top "level" of it will execute. In this case, it will immediately
print "Hello World".

Now try to run this a second time:

    > py import world.test

You will *not* see any output this second time or any subsequent times! This is not a bug. Rather
it is because of how Python importing works - it stores all imported modules and will
avoid importing them more than once. So your `print` will only run the first time, when the module
is first imported.

Try this:

    > reload

And then

    > py import world.test
    Hello World!

Now we see it again. The `reload` wiped the server's memory of what was imported, so it had to
import it anew. You'd have to do this every time you wanted the print to show though, which is
not very useful.

> We'll get back to more advanced ways to import code in later tutorial sections - this is an
> important topic. But for now, let's press on and resolve this particular problem.


### Our first own function

We want to be able to print our hello-world message at any time, not just once after a server
reload. Change your `mygame/world/test.py` file to look like this:

```python
def hello_world():
    print("Hello World!")
```

As we are moving to multi-line Python code, there are some important things to remember:

- Capitalization matters in Python. It must be `def` and not `DEF`, `who` is not the same as `Who`.
- Indentation matters in Python. The second line must be indented or it's not valid code. You should
also use a consistent indentation length. We *strongly* recommend that you, for your own sanity's sake,
set up your editor to always indent *4 spaces* (**not** a single tab-character) when you press the TAB key.

So about that function. Line 1:

- `def` is short for "define" and defines a *function* (or a *method*, if sitting on an object).
This is a [reserved Python keyword](https://docs.python.org/2.5/ref/keywords.html); try not to use
these words anywhere else.
- A function name can not have spaces but otherwise we could have called it almost anything. We call
it `hello_world`. Evennia follows [Python's standard naming style](https://github.com/evennia/evennia/blob/master/CODING_STYLE.md#a-quick-list-of-code-style-points)
with lowercase letters and underscores. We recommend you do the same.
- The colon (`:`) at the end of line 1 indicates that the header of the function is complete.

Line 2:

- The indentation marks the beginning of the actual operating code of the function (the function's
*body*). If we wanted more lines to belong to this function those lines would all have to
start at least at this indentation level.

Now let's try this out. First `reload` your game to have it pick up
our updated Python module, then import it.

    > reload
    > py import world.test

Nothing happened! That is because the function in our module won't do anything just by importing it (this
is what we wanted). It will only act when we *call* it. So we need to first import the module and then access the
function within:

    > py import world.test ; world.test.hello_world()
    Hello world!

There is our "Hello World"! As mentioned earlier, use use semi-colon to put multiple
Python-statements on one line. Note also the previous warning about mud-clients using the `;` to their
own ends.

So what happened there? First we imported `world.test` as usual. But this time we continued and
accessed the `hello_world` function _inside_ the newly imported module.

By adding `()` to the `hello_world` function we _call_ it, that is we run the body of the function and
print our text. We can now redo this as many times as we want without having to `reload` in between:


    > py import world.test ; world.test.hello_world()
    Hello world!
    > py import world.test ; world.test.hello_world()
    Hello world!

### Sending text to others

The `print` command is a standard Python structure. We can use that here in the `py` command since
we can se the output. It's great for debugging and quick testing. But if you need to send a text
to an actual player, `print` won't do, because it doesn't know _who_ to send to. Try this:

    > py me.msg("Hello world!")
    Hello world!

This looks the same as the `print` result, but we are now actually messaging a specific *object*,
`me`. The `me` is a shortcut to 'us', the one running the `py` command. It is not some special
Python thing, but something Evennia just makes available in the `py` command for convenience
(`self` is an alias).

The `me` is an example of an *Object instance*. Objects are fundamental in Python and Evennia.
The `me` object also contains a lot of useful resources for doing
things with that object. We access those resources with '`.`'.

One such resource is `msg`, which works like `print` except it sends the text to the object it
is attached to. So if we, for example, had an object `you`, doing `you.msg(...)` would send a message
to the object `you`.

For now, `print` and `me.msg` behaves the same, just remember that `print` is mainly used for
debugging and `.msg()` will be more useful for you in the future.


### Parsing Python errors

Let's try this new text-sending in the function we just created.  Go back to
your `test.py` file and Replace the function with this instead:

```python
def hello_world():
    me.msg("Hello World!")
```

Save your file and `reload` your server to tell Evennia to re-import new code,
then run it like before:

     > py import world.test ; world.test.hello_world()

No go - this time you get an error!

```python
File "./world/test.py", line 2, in hello_world
    me.msg("Hello World!")
NameError: name 'me' is not defined
```

```sidebar:: Errors in the logs

    In regular use, tracebacks will often appear in the log rather than
    in the game. Use `evennia --log` to view the log in the terminal. Make
    sure to scroll back if you expect an error and don't see it. Use
    `Ctrl-C` (or `Cmd-C` on Mac) to exit the log-view.

```

This is called a *traceback*. Python's errors are very friendly and will most of the time tell you
exactly what and where things go wrong. It's important that you learn to parse tracebacks so you
know how to fix your code.

A traceback is to be read from the _bottom up_:

- (line 3) An error of type `NameError` is the problem ...
- (line 3)  ... more specifically it is due to the variable `me` not being defined.
- (line 2) This happened on the line `me.msg("Hello world!")` ...
- (line 1)  ... which is on line `2` of the file `./world/test.py`.

In our case the traceback is short. There may be many more lines above it, tracking just how
different modules called each other until the program got to the faulty line. That can
sometimes be useful information, but reading from the bottom is always a good start.

The `NameError` we see here is due to a module being its own isolated thing. It knows nothing about
the environment into which it is imported. It knew what `print` is because that is a special
[reserved Python keyword](https://docs.python.org/2.5/ref/keywords.html). But `me` is *not* such a
reserved word (as mentioned, it's just something Evennia came up with for convenience in the `py`
command). As far as the module is concerned `me` is an unfamiliar name, appearing out of nowhere.
Hence the `NameError`.

### Passing arguments to functions

We know that `me` exists at the point when we run the `py` command, because we can do `py me.msg("Hello World!")`
with no problem. So let's _pass_ that me along to the function so it knows what it should be.
Go back to your `test.py` and change it to this:

```python
def hello_world(who):
    who.msg("Hello World!")
```
We now added an _argument_ to the function. We could have named it anything. Whatever `who` is,
we will call a method `.msg()` on it.

As usual, `reload` the server to make sure the new code is available.

    > py import world.test ; world.test.hello_world(me)
    Hello World!

Now it worked. We _passed_ `me` to our function. It will appear inside the function renamed as `who` and
now the function works and prints as expected. Note how the `hello_world` function doesn't care _what_ you
pass into it as long as it has a `.msg()` method on it. So you could reuse this function over and over for other
suitable targets.

> **Extra Credit:** As an exercise, try to pass something else into `hello_world`. Try for example
>to pass the number `5` or the string `"foo"`. You'll get errors telling you that they don't have
>the attribute `msg`. They don't care about `me` itself not being a string or a number. If you are
>familiar with other programming languages (especially C/Java) you may be tempted to start *validating*
>`who` to make sure it's of the right type before you send it. This is usually not recommended in Python.
>Python philosophy is to [handle](https://docs.python.org/2/tutorial/errors.html) the error if it happens
>rather than to add a lot of code to prevent it from happening. See [duck typing](https://en.wikipedia.org/wiki/Duck_typing)
>and the concept of _Leap before you Look_.


### Finding others to send to

Let's wrap up this first Python `py` crash-course by finding someone else to send to.

In Evennia's `contrib/` folder (`evennia/contrib/tutorial_examples/mirror.py`) is a handy little
object called the `TutorialMirror`. The mirror will echo whatever is being sent to it to
the room it is in.

On the game command-line, let's create a mirror:

    > create/drop mirror:contrib.tutorial_examples.mirror.TutorialMirror

```sidebar:: Creating objects

    The `create` command was first used to create boxes in the
    `Building Stuff <Building-Quickstart>`_ tutorial. Note how it
    uses a "python-path" to describe where to load the mirror's code from.
```

A mirror should appear in your location.

    > look mirror
    mirror shows your reflection:
    This is User #1

What you are seeing is actually your own avatar in the game, the same thing that is available as `me` in the `py`
command.

What we are aiming for now is the equivalent of `mirror.msg("Mirror Mirror on the wall")`. But the first thing that
comes to mind will not work:

    > py mirror.msg("Mirror, Mirror on the wall ...")
    NameError: name 'mirror' is not defined.

This is not surprising: Python knows nothing about "mirrors" or locations or anything. The `me` we've been using
is, as mentioned, just a convenient thing the Evennia devs makes available to the `py` command. They couldn't possibly
predict that you wanted to talk to mirrors.

Instead we will need to _search_ for that `mirror` object before we can send to it.
Make sure you are in the same location as the mirror and try:

    > py me.search("mirror")
    mirror

`me.search("name")` will, by default, search and _return_ an object with the given name found in _the same location_
as the `me` object is. If it can't find anything you'll see an error.

```sidebar:: Function returns

    Whereas a function like `print` only prints its arguments, it's very common
    for functions/methods to `return` a result of some kind. Think of the function
    as a machine - you put something in and out comes a result you can use. In the case
    of `me.search`, it will perform a database search and spit out the object it finds.
```

    > py me.search("dummy")
    Could not find 'dummy'.

Wanting to find things in the same location is very common, but as we continue we'll
find that Evennia provides ample tools for tagging, searching and finding things from all over your game.

Now that we know how to find the 'mirror' object, we just need to use that instead of `me`!

    > py mirror = self.search("mirror") ; mirror.msg("Mirror, Mirror on the wall ...")
    mirror echoes back to you:
    "Mirror, Mirror on the wall ..."

The mirror is useful for testing  because its `.msg` method just echoes whatever is sent to it back to the room. More common
would be to talk to a player character, in which case the text you sent would have appeared in their game client.


### Multi-line py

So far we have use `py` in single-line mode, using `;` to separate multiple inputs. This is very convenient
when you want to do some quick testing. But you can also start a full multi-line Python interactive interpreter
inside Evennia.

    > py
    Evennia Interactive Python mode
    Python 3.7.1 (default, Oct 22 2018, 11:21:55)
    [GCC 8.2.0] on Linux
    [py mode - quit() to exit]

(the details of the output will vary with your Python version and OS). You are now in python interpreter mode. It means
that _everything_ you insert from now on will become a line of Python (you can no longer look around or do other
commands).

    > print("Hello World")

    >>> print("Hello World")
    Hello World
    [py mode - quit() to exit]

Note that we didn't need to put `py` in front now. The system will also echo your input (that's the bit after
the `>>>`). For brevity in this tutorual we'll turn the echo off. First exit `py` and then start again with the
`/noecho` flag.

    > quit()
    Closing the Python console.
    > py/noecho
    Evennia Interactive Python mode (no echoing of prompts)
    Python 3.7.1 (default, Oct 22 2018, 11:21:55)
    [GCC 8.2.0] on Linux
    [py mode - quit() to exit]

```sidebar:: interactive py

    - Start with `py`.
    - Use `py/noecho` if you don't want your input to be echoed for every line.
    - All your inputs will now be interpreted as Python code.
    - Exit with `quit()`.
```

We can now enter multi-line Python code:

    > a = "Test"
    > print(f"This is a {a}."}
    This is a Test.

Let's try to define a function:

    > def hello_world(who, txt):
    ...
    >     who.msg(txt)
    ...
    >
    [py mode - quit() to exit]

Some important things above:

- Definining a function with `def` means we are starting a new code block. Python works so that you mark the content
  of the block with indention. So the next line must be manually indented (4 spaces is a good standard) in order
  for Python to know it's part of the function body.
- We expand the `hello_world` function with another argument `txt`. This allows us to send any text, not just
  "Hello World" over and over.
- To tell `py` that no more lines will be added to the function body, we end with an empty input. When
  the normal prompt on how to exit returns, we know we are done.

Now we have defined a new function. Let's try it out:

    > hello_world(me, "Hello world to me!")
    Hello world to me!

The `me` is still available to us, so we pass that as the `who` argument, along with a little longer
string. Let's combine this with searching for the mirror.

    > mirror = me.search("mirror")
    > hello_world(mirror, "Mirror, Mirror on the wall ...")
    mirror echoes back to you:
    "Mirror, Mirror on the wall ..."

Exit the `py` mode with

    > quit()
    Closing the Python console.

## Other ways to test Python code

The `py` command is very powerful for experimenting with Python in-game. It's great for quick testing.
But you are still limited to working over telnet or the webclient, interfaces that doesn't know anything
about Python per-se.

Outside the game, go to the terminal where you ran Evennia (or any terminal where the `evennia` command
is available).

- `cd` to your game dir.
- `evennia shell`

A Python shell opens. This works like `py` did inside the game, with the exception that you don't have
`me` available out of the box. If you want `me`, you need to first find yourself:

    > import evennia
    > me = evennia.search_object("YourChar")[0]

Here we make use of one of evennia's search functions, available by importing `evennia` directly.
We will cover more advanced searching later, but suffice to say, you put your own character name instead of
"YourChar" above.

> The `[0]` at the end is because `.search_object` returns a list of objects and we want to
get at the first of them (counting starts from 0).

Use `Ctrl-D` (`Cmd-D` on Mac) or `quit()` to exit the Python console.

### ipython

The default Python shell is quite limited and ugly. It's *highly* recommended to install `ipython` instead. This
is a much nicer, third-party Python interpreter with colors and many usability improvements.

    pip install ipython

If `ipython` is installed, `evennia shell` will use it automatically.

    evennia shell
    ...
    IPython 7.4.0 -- An enhanced Interactive Python. Type '?' for help
    In [1]: 
You now have Tab-completion:

    > import evennia
    > evennia.<TAB>

That is, enter `evennia.` and then press the TAB key - you will be given a list of all the resources
available on the `evennia` object. This is great for exploring what Evennia has to offer. For example,
use your arrow keys to scroll to `search_object()` to fill it in.

    > evennia.search_object?

Adding a `?` and pressing return will give you the full documentation for `.search_object`. Use `??` if you
want to see the entire source code.

As for the normal python interpreter, use `Ctrl-D`/`Cmd-D` or `quit()` to exit ipython.

```important:: Persistent code

    Common for both `py` and `python`/`ipython` is that the code you write is not persistent - it will
    be gone after you shut down the interpreter (but ipython will remember your input history). For making long-lasting
    Python code, we need to save it in a Python module, like we did for `world/test.py`.
```


## Conclusions

This covers quite a lot of basic Python usage. We printed and formatted strings, defined our own
first function, fixed an error and even searched and talked to a mirror! Being able to access
python inside and outside of the game is an important skill for testing and debugging, but in
practice you will be writing most your code in Python modules.

To that end we also created a first new Python module in the `mygame/` game dir, then imported and used it.
Now let's look at the rest of the stuff you've got going on inside that `mygame/` folder ...

