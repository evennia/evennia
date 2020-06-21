# Starting to code Evennia

[prev lesson](Tutorial-World-Introduction) | [next lesson](Gamedir-Overview)

Time to dip our toe into some coding! Evennia is written and extended in [Python](http://python.org), which
is a mature and professional programming language that is very fast to work with.

That said, even though Python is widely considered easy to learn, we can only cover the most immediately
important aspects of Python in this series of starting tutorials. Hopefully we can get you started 
but then you'll need to continue learning from there. See our [link section](../../Links) for finding
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

    The lines with a `>` indicate input to enter in-game, while the lines below are the 
    expected return from that input.
```

You will see

    > print("Hello world!")
    Hello World!

To understand what is going on: some extra info: The `print(...)` *function* is the basic, in-built
way to output text in Python. We are sending "Hello World" as an _argument_ to this function. The quotes `"..."` 
mean that you are inputting a *string* (i.e. text). You could also have used single-quotes `'...'`, 
Python accepts both.

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

```sidebar:: Functions and Methods

    Function:
        Stand-alone in a python module, like `print()`
    Method:
        Something that sits "on" an object, like `.msg()`
```

For now, `print` and `me.msg` behaves the same, just remember that `print` is mainly used for 
debugging and `.msg()` will be more useful for you in the future. 

For fun, try printing other things. Also try this: 

    > py self.msg("|rThis is red text!")
    
Adding that `|r` at the start will turn our output red. Enter the command `color ansi` or `color xterm` 
to see which colors are available.

### Importing code from other modules

As we saw in the previous section, we could use `me.msg` to access the `msg` method on `me`. This
use of the full-stop character is used to access all sorts of resources, including that in other
Python modules. If you've been following along, this is what we've referred to as the "Python path".

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

> If you look in the folder you'll also often find new files ending with `.pyc`. These are compiled
Python binaries that Python auto-creates when running code. Just ignore them, you should never edit
those anyway.

Now try to run this a second time:

    > py import world.test

You will *not* see any output  this second time or any subsequent times! This is not a bug. Rather
it is because Python is being clever - it stores all imported modules and to be efficient it will
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

### Parsing Python errors

Running print only on import is not too helpful. We want to print whenever we like to!
Go back to your `test.py` file and erase the single `print` statement you had. Replace
it with this instead:

```python
me.msg("Hello World!")
```

As you recall we used this with `py` earlier - it echoed "Hello World!" in-game. 
Save your file and `reload` your server - this makes sure Evennia knows to re-import 
it (with our new, fresh code this time). 

To test it, import it using `py` as before

     > py import world.test

No go - this time you get an error!

```python
File "./world/test.py", line 1, in <module>
    me.msg("Hello world!")
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
- (line 1)  ... which is on line `1` of the file `./world/test.py`.

In our case the traceback is short. There may be many more lines above it, tracking just how
different modules called each other until the program got to the faulty line. That can 
sometimes be useful information, but reading from the bottom is always a good start.

The `NameError` we see here is due to a module being its own isolated thing. It knows nothing about
the environment into which it is imported. It knew what `print` is because that is a special
[reserved Python keyword](https://docs.python.org/2.5/ref/keywords.html). But `me` is *not* such a
reserved word (as mentioned, it's just something Evennia came up with for convenience in the `py` 
command). As far as the module is concerned `me` is an unfamiliar name, appearing out of nowhere. 
Hence the `NameError`.

### Our first own function

Let's see if we can resolve that `NameError` from the previous section. We know that `me` is defined
at the time we use the `py` command. We know this because if we do `py me.msg("Hello World!")` 
directly in-game it works fine. What if we could *send* that `me` to the `test.py` module so it 
knows what it is? One way to do this is with a *function*.

Change your `mygame/world/test.py` file to look like this:

```python
def hello_world(who):
    who.msg("Hello World!")
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
- `who` is what we call the *argument* to our function. Arguments are variables _passed_ to the
function. We could have named it anything and we could also have multiple arguments separated by
commas. What `who` is depends on what we pass to this function when we *call* it later (hint: we'll
pass `me` to it).
- The colon (`:`) at the end of line 1 indicates that the header of the function is complete.

Line 2: 

- The indentation marks the beginning of the actual operating code of the function (the function's
*body*). If we wanted more lines to belong to this function those lines would all have to
start at least at this indentation level.
- In the function body we take the `who` argument and treat it as we would have treated `me` 
  earlier- we expect it to have a `.msg` method we can use to send "Hello World" to.

Now let's try this out. First `reload` your game to have it pick up 
our updated Python module when we reload. 

    > reload
    > py import world.test

Nothing happened! That is because the function in our module won't do anything just by importing it.
It will only act when we *call* it. So we need to first import the module and then access the 
function within:

    > py import world.test ; world.test.hello_world(me)
    Hello world!

There is our "Hello World"! Using `;` is the way to put multiple Python-statements on one line.

```warning:: MUD clients and semi-colon

    A common issue is that some MUD clients use the semi-colon `;` to split client-inputs
    into separate sends. If so, you'll get a `NameError` above, stating that 
    `world` is not defined. Check so you understand why this is! Most clients allow you to 
    remap to use some other separator than `;`. You can use the Evennia web client if this 
    problem remains.
```

So what happened there? First we imported `world.test` as usual. But this time we continued and
accessed the `hello_world` function _inside_ the newly imported module. 

We *call* the function with `me`, which becomes the `who` variable we use inside 
the `hello_function` (they are be the same object). And since `me.msg` works, so does `who.msg` 
inside the function. 

> **Extra Credit:** As an exercise, try to pass something else into `hello_world`. Try for example 
>to pass the number `5` or the string `"foo"`. You'll get errors telling you that they don't have 
>the attribute `msg`. They don't care about `me` itself not being a string or a number. If you are 
>familiar with other programming languages (especially C/Java) you may be tempted to start *validating* 
>`who` to make sure it's of the right type before you send it. This is usually not recommended in Python. 
>Python philosophy is to [handle](https://docs.python.org/2/tutorial/errors.html) the error if it happens 
>rather than to add a lot of code to prevent it from happening. See [duck typing](https://en.wikipedia.org/wiki/Duck_typing) 
>and the concept of _Leap before you Look_.


This gives you some initial feeling for how to run Python and import Python modules. We also 
tried to put a module in `module/world/`. Now let's look at the rest of the stuff you've got 
inside that `mygame/` folder ...

[prev lesson](Tutorial-World-Introduction) | [next lesson](Gamedir-Overview)
