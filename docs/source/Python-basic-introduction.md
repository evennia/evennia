# Python basic introduction

This is the first part of our beginner's guide to the basics of using Python with Evennia. It's
aimed at you with limited or no programming/Python experience. But also if you are an experienced
programmer new to Evennia or Python you might still pick up a thing or two. It is by necessity brief
and low on detail. There are countless Python guides and tutorials, books and videos out there for
learning more in-depth - use them!

**Contents:**
- [Evennia Hello world](./Python-basic-introduction#evennia-hello-world)
- [Importing modules](./Python-basic-introduction#importing-modules)
- [Parsing Python errors](./Python-basic-introduction#parsing-python-errors)
- [Our first function](./Python-basic-introduction#our-first-function)
- [Looking at the log](./Python-basic-introduction#looking-at-the-log)
- (continued in [part 2](./Python-basic-tutorial-part-two))

This quickstart assumes you have [gotten Evennia started](./Getting-Started). You should make sure
that you are able to see the output from the server in the console from which you started it. Log
into the game either with a mud client on `localhost:4000` or by pointing a web browser to
`localhost:4001/webclient`. Log in as your superuser (the user you created during install).

Below, lines starting with a single `>` means command input.

### Evennia Hello world

The `py` (or `!` which is an alias) command allows you as a superuser to run raw Python from in-
game. From the game's input line, enter the following:

    > py print("Hello World!")

You will see

    > print("Hello world!")
    Hello World

To understand what is going on: some extra info: The `print(...)` *function* is the basic, in-built
way to output text in Python. The quotes `"..."` means you are inputing a *string* (i.e. text). You
could also have used single-quotes `'...'`, Python accepts both.

The first return line (with `>>>`) is just `py` echoing what you input (we won't include that in the
examples henceforth).

> Note: You may sometimes see people/docs refer to `@py` or other commands starting with `@`.
Evennia ignores `@` by default, so `@py` is the exact same thing as `py`.

The `print` command is a standard Python structure. We can use that here in the `py` command, and
it's great for debugging and quick testing. But if you need to send a text to an actual player,
`print` won't do, because it doesn't know _who_ to send to. Try this:

    > py me.msg("Hello world!")
    Hello world!

This looks the same as the `print` result, but we are now actually messaging a specific *object*,
`me`. The `me` is something uniquely available in the `py` command (we could also use `self`, it's
an alias). It represents "us", the ones calling the `py` command. The `me` is an example of an
*Object instance*. Objects are fundamental in Python and Evennia. The `me` object not only
represents the character we play in the game, it also contains a lot of useful resources for doing
things with that Object. One such resource is `msg`. `msg` works like `print` except it sends the
text to the object it is attached to. So if we, for example, had an object `you`, doing
`you.msg(...)` would send a message to the object `you`.

You access an Object's resources by using the full-stop character `.`. So `self.msg` accesses the
`msg` resource and then we call it like we did print, with our "Hello World!" greeting in
parentheses.

> Important: something like `print(...)` we refer to as a *function*, while `msg(...)` which sits on
an object is called a *method*.

For now, `print` and `me.msg` behaves the same, just remember that you're going to mostly be using
the latter in the future. Try printing other things. Also try to include `|r` at the start of your
string to make the output red in-game. Use `color` to learn more color tags.

### Importing modules

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

Don't forget to save the file. A file with the ending `.py` is referred to as a Python *module*. To
use this in-game we have to *import* it. Try this:

```python
> @py import world.test
Hello World
```
If you make some error (we'll cover how to handle errors below) you may need to run the `@reload`
command for your changes to take effect.

So importing `world.test` actually means importing `world/test.py`. Think of the period `.` as
replacing `/` (or `\` for Windows) in your path. The `.py` ending of `test.py` is also never
included in this "Python-path", but _only_ files with that ending can be imported this way. Where is
`mygame` in that Python-path? The answer is that Evennia has already told Python that your `mygame`
folder is a good place to look for imports. So we don't include `mygame` in the path - Evennia
handles this for us.

When you import the module, the top "level" of it will execute. In this case, it will immediately
print "Hello World".

> If you look in the folder you'll also often find new files ending with `.pyc`. These are compiled
Python binaries that Python auto-creates when running code. Just ignore them, you should never edit
those anyway.

Now try to run this a second time:

```python
> py import world.test
```
You will *not* see any output  this second time or any subsequent times! This is not a bug. Rather
it is because Python is being clever - it stores all imported modules and to be efficient it will
avoid importing them more than once. So your `print` will only run the first time, when the module
is first imported. To see it again you need to `@reload` first, so Python forgets about the module
and has to import it again.

We'll get back to importing code in the second part of this tutorial. For now, let's press on.

### Parsing Python errors

Next, erase the single `print` statement you had in `test.py` and replace it with this instead:

```python
me.msg("Hello World!")
```

As you recall we used this from `py` earlier - it echoed "Hello World!" in-game.
Save your file and `reload` your server - this makes sure Evennia sees the new version of your code.
Try to import it from `py` in the same way as earlier:

```python
> py import world.test
```

No go - this time you get an error!

```python
File "./world/test.py", line 1, in <module>
    me.msg("Hello world!")
NameError: name 'me' is not defined
```

This is called a *traceback*. Python's errors are very friendly and will most of the time tell you
exactly what and where things are wrong. It's important that you learn to parse tracebacks so you
can fix your code. Let's look at this one. A traceback is to be read from the _bottom up_. The last
line is the error Python balked at, while the two lines above it details exactly where that error
was encountered.

1. An error of type `NameError` is the problem ...
2. ... more specifically it is due to the variable `me` not being defined.
3. This happened on the line `me.msg("Hello world!")` ...
4.  ... which is on line `1` of the file `./world/test.py`.

In our case the traceback is short. There may be many more lines above it, tracking just how
different modules called each other until it got to the faulty line. That can sometimes be useful
information, but reading from the bottom is always a good start.

The `NameError` we see here is due to a module being its own isolated thing. It knows nothing about
the environment into which it is imported. It knew what `print` is because that is a special
[reserved Python keyword](https://docs.python.org/2.5/ref/keywords.html). But `me` is *not* such a
reserved word. As far as the module is concerned `me` is just there out of nowhere. Hence the
`NameError`.

### Our first function

Let's see if we can resolve that `NameError` from the previous section. We know that `me` is defined
at the time we use the `@py` command because if we do `py me.msg("Hello World!")` directly in-game
it works fine. What if we could *send* that `me` to the `test.py` module so it knows what it is? One
way to do this is with a *function*.

Change your `mygame/world/test.py` file to look like this:

```python
def hello_world(who):
    who.msg("Hello World!")
```

Now that we are moving onto multi-line Python code, there are some important things to remember:

- Capitalization matters in Python. It must be `def` and not `DEF`, `who` is not the same as `Who`
etc.
- Indentation matters in Python. The second line must be indented or it's not valid code. You should
also use a consistent indentation length. We *strongly* recommend that you set up your editor to
always indent *4 spaces* (**not** a single tab-character) when you press the TAB key - it will make
your life a lot easier.
- `def` is short for "define" and defines a *function* (or a *method*, if sitting on an object).
This is a [reserved Python keyword](https://docs.python.org/2.5/ref/keywords.html); try not to use
these words anywhere else.
- A function name can not have spaces but otherwise we could have called it almost anything. We call
it `hello_world`. Evennia follows [Python's standard naming
style](https://github.com/evennia/evennia/blob/master/CODING_STYLE.md#a-quick-list-of-code-style-
points) with lowercase letters and underscores. Use this style for now.
- `who` is what we call the *argument* to our function. Arguments are variables we pass to the
function. We could have named it anything and we could also have multiple arguments separated by
commas. What `who` is depends on what we pass to this function when we *call* it later (hint: we'll
pass `me` to it).
- The colon (`:`) at the end of the first line indicates that the header of the function is
complete.
- The indentation marks the beginning of the actual operating code of the function (the function's
*body*). If we wanted more lines to belong to this function those lines would all have to have to
start at this indentation level.
- In the function body we take the `who` argument and treat it as we would have treated `me` earlier
- we expect it to have a `.msg` method we can use to send "Hello World" to.

First, `reload` your game to make it aware of the updated Python module. Now we have defined our
first function, let's use it.

    > reload
    > py import world.test

Nothing happened! That is because the function in our module won't do anything just by importing it.
It will only act when we *call* it. We will need to enter the module we just imported and do so.

    > py import world.test ; world.test.hello_world(me)
    Hello world!

There is our "Hello World"! The `;` is the way to put multiple Python-statements on one line.

> Some MUD clients use `;` for their own purposes to separate client-inputs. If so you'll get a
`NameError` stating that `world` is not defined. Check so you understand why this is! Change the use
of `;` in your client or use the Evennia web client if this is a problem.

In the second statement we access the module path we imported (`world.test`) and reach for the
`hello_world` function within. We *call* the function with `me`, which becomes the `who` variable we
use inside the `hello_function`.

> As an exercise, try to pass something else into `hello_world`. Try for example to pass _who_ as
the number `5` or the simple string `"foo"`. You'll get errors that they don't have the attribute
`msg`. As we've seen, `me` *does* make `msg` available which is why it works (you'll learn more
about Objects like `me` in the next part of this tutorial). If you are familiar with other
programming languages you may be tempted to start *validating* `who` to make sure it works as
expected. This is usually not recommended in Python which suggests it's better to
[handle](https://docs.python.org/2/tutorial/errors.html) the error if it happens rather than to make
a lot of code to prevent it from happening. See also [duck
typing](https://en.wikipedia.org/wiki/Duck_typing).

# Looking at the log

As you start to explore Evennia, it's important that you know where to look when things go wrong.
While using the friendly `py` command you'll see errors directly in-game. But if something goes
wrong in your code while the game runs, you must know where to find the _log_.

Open a terminal (or go back to the terminal you started Evennia in), make sure your `virtualenv` is
active and that you are standing in your game directory (the one created with `evennia --init`
during installation). Enter

```
evennia --log
```
(or `evennia -l`)

This will show the log. New entries will show up in real time. Whenever you want to leave the log,
enter  `Ctrl-C` or `Cmd-C` depending on your system. As a game dev it is important to look at the
log output when working in Evennia - many errors will only appear with full details here. You may
sometimes have to scroll up in the history if you miss it.

This tutorial is continued in [Part 2](./Python-basic-tutorial-part-two), where we'll start learning
about objects and to explore the Evennia library.
