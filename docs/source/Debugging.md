# Debugging


Sometimes, an error is not trivial to resolve. A few simple `print` statements is not enough to find
the cause of the issue. Running a *debugger* can then be very helpful and save a lot of time. Debugging
means running Evennia under control of a special *debugger* program. This allows you to stop the
action at a given point, view the current state and step forward through the program to see how its
logic works.

Evennia natively supports these debuggers:

- [Pdb](https://docs.python.org/2/library/pdb.html) is a part of the Python distribution and
  available out-of-the-box.
- [PuDB](https://pypi.org/project/pudb/) is a third-party debugger that has a slightly more
  'graphical', curses-based user interface than pdb. It is installed with `pip install pudb`.

## Debugging Evennia

To run Evennia with the debugger, follow these steps:

1. Find the point in the code where you want to have more insight. Add the following line at that
   point.
    ```python
    from evennia import set_trace;set_trace()
    ```
2. (Re-)start Evennia in interactive (foreground) mode with `evennia istart`. This is important -
   without this step the debugger will not start correctly - it will start in this interactive
   terminal.
3. Perform the steps that will trigger the line where you added the `set_trace()` call. The debugger
   will start in the terminal from which Evennia was interactively started.

The `evennia.set_trace` function takes the following arguments:


```python
    evennia.set_trace(debugger='auto', term_size=(140, 40))
```

Here, `debugger` is one of `pdb`, `pudb` or `auto`. If `auto`, use `pudb` if available, otherwise
use `pdb`. The `term_size` tuple sets the viewport size for `pudb` only (it's ignored by `pdb`).


## A simple example using pdb

The debugger is useful in different cases, but to begin with, let's see it working in a command.
Add the following test command (which has a range of deliberate errors) and also add it to your
default cmdset. Then restart Evennia in interactive mode with `evennia istart`.


```python
# In file commands/command.py


class CmdTest(Command):

    """
    A test command just to test pdb.

    Usage:
        test

    """

    key = "test"

    def func(self):
        from evennia import set_trace; set_trace()   # <--- start of debugger
        obj = self.search(self.args)
        self.msg("You've found {}.".format(obj.get_display_name()))

```

If you type `test` in your game, everything will freeze.  You won't get any feedback from the game,
and you won't be able to enter any command (nor anyone else).  It's because the debugger has started
in your console, and you will find it here. Below is an example with `pdb`.

```
...
> .../mygame/commands/command.py(79)func()
-> obj = self.search(self.args)
(Pdb)

```

`pdb` notes where it has stopped execution and, what line is about to be executed (in our case, `obj
= self.search(self.args)`), and ask what you would like to do.

### Listing surrounding lines of code

When you have the `pdb` prompt `(Pdb)`, you can type in different commands to explore the code.  The first one you should know is `list` (you can type `l` for short):

```
(Pdb) l
 43
 44         key = "test"
 45
 46         def func(self):
 47             from evennia import set_trace; set_trace()   # <--- start of debugger
 48  ->         obj = self.search(self.args)
 49             self.msg("You've found {}.".format(obj.get_display_name()))
 50
 51     # -------------------------------------------------------------
 52     #
 53     # The default commands inherit from
(Pdb)
```

Okay, this didn't do anything spectacular, but when you become more confident with `pdb` and find
yourself in lots of different files, you sometimes need to see what's around in code.  Notice that
there is a little arrow (`->`) before the line that is about to be executed.

This is important: **about to be**, not **has just been**.  You need to tell `pdb` to go on (we'll
soon see how).

### Examining variables

`pdb` allows you to examine variables (or really, to run any Python instruction).  It is very useful
to know the values of variables at a specific line.  To see a variable, just type its name (as if
you were in the Python interpreter:

```
(Pdb) self
<commands.command.CmdTest object at 0x045A0990>
(Pdb) self.args
u''
(Pdb) self.caller
<Character: XXX>
(Pdb)
```

If you try to see the variable `obj`, you'll get an error:

```
(Pdb) obj
*** NameError: name 'obj' is not defined
(Pdb)
```

That figures, since at this point, we haven't created the variable yet.

> Examining variable in this way is quite powerful.  You can even run Python code and keep on
> executing, which can help to check that your fix is actually working when you have identified an
> error.  If you have variable names that will conflict with `pdb` commands (like a `list`
> variable), you can prefix your variable with `!`, to tell `pdb` that what follows is Python code.

### Executing the current line

It's time we asked `pdb` to execute the current line. To do so, use the `next` command.  You can
shorten it by just typing `n`:

```
(Pdb) n
AttributeError: "'CmdTest' object has no attribute 'search'"
> .../mygame/commands/command.py(79)func()
-> obj = self.search(self.args)
(Pdb)
```

`Pdb` is complaining that you try to call the `search` method on a command... whereas there's no
`search` method on commands.  The character executing the command is in `self.caller`, so we might
change our line:

```python
obj = self.caller.search(self.args)
```

### Letting the program run

`pdb` is waiting to execute the same instruction... it provoked an error but it's ready to try
again, just in case.  We have fixed it in theory, but we need to reload, so we need to enter a
command.  To tell `pdb` to terminate and keep on running the program, use the `continue` (or `c`)
command:

```
(Pdb) c
...
```

You see an error being caught, that's the error we have fixed... or hope to have.  Let's reload the
game and try again. You need to run `evennia istart` again and then run `test` to get into the
command again.

```
> .../mygame/commands/command.py(79)func()
-> obj = self.caller.search(self.args)
(Pdb)

```

`pdb` is about to run the line again.

```
(Pdb) n
> .../mygame/commands/command.py(80)func()
-> self.msg("You've found {}.".format(obj.get_display_name()))
(Pdb)
```

This time the line ran without error.  Let's see what is in the `obj` variable:

```
(Pdb) obj
(Pdb) print obj
None
(Pdb)
```

We have entered the `test` command without parameter, so no object could be found in the search (`self.args` is an empty string).

Let's allow the command to continue and try to use an object name as parameter (although, we should
fix that bug too, it would be better):

```
(Pdb) c
...
```

Notice that you'll have an error in the game this time.  Let's try with a valid parameter.  I have
another character, `barkeep`, in this room:

```test barkeep```

And again, the command freezes, and we have the debugger opened in the console.

Let's execute this line right away:

```
> .../mygame/commands/command.py(79)func()
-> obj = self.caller.search(self.args)
(Pdb) n
> .../mygame/commands/command.py(80)func()
-> self.msg("You've found {}.".format(obj.get_display_name()))
(Pdb) obj
<Character: barkeep>
(Pdb)
```

At least this time we have found the object.  Let's process...

```
(Pdb) n
TypeError: 'get_display_name() takes exactly 2 arguments (1 given)'
> .../mygame/commands/command.py(80)func()
-> self.msg("You've found {}.".format(obj.get_display_name()))
(Pdb)
```

As an exercise, fix this error, reload and run the debugger again.  Nothing better than some
experimenting!

Your debugging will often follow the same strategy:

1. Receive an error you don't understand.
2. Put a breaking point **BEFORE** the error occurs.
3. Run the code again and see the debugger open.
4. Run the program line by line,examining variables, checking the logic of instructions.
5. Continue and try again, each step a bit further toward the truth and the working feature.

### Stepping through a function

`n` is useful, but it will avoid stepping inside of functions if it can.  But most of the time, when
we have an error we don't understand, it's because we use functions or methods in a way that wasn't
intended by the developer of the API.  Perhaps using wrong arguments, or calling the function in a
situation that would cause a bug.  When we have a line in the debugger that calls a function or
method, we can "step" to examine it further.  For instance, in the previous example, when `pdb` was
about to execute `obj = self.caller.search(self.args)`, we may want to see what happens inside of
the `search` method.

To do so, use the `step` (or `s`) command.  This command will show you the definition of the
function/method and you can then use `n` as before to see it line-by-line.  In our little example,
stepping through a function or method isn't that useful, but when you have an impressive set of
commands, functions and so on, it might really be handy to examine some feature and make sure they
operate as planned.

## Cheat-sheet of pdb/pudb commands

PuDB and Pdb share the same commands. The only real difference is how it's presented. The `look`
command is not needed much in `pudb` since it displays the code directly in its user interface.

| Pdb/PuDB command | To do what |
| ----------- | ---------- |
| list (or l) | List the lines around the point of execution (not needed for `pudb`, it will show this directly). |
| print (or p) | Display one or several variables. |
| `!` | Run Python code (using a `!` is often optional). |
| continue (or c) | Continue execution and terminate the debugger for this time. |
| next (or n) | Execute the current line and goes to the next one. |
| step (or s) | Step inside of a function or method to examine it. |
| `<RETURN>` | Repeat the last command (don't type `n` repeatedly, just type it once and then press `<RETURN>` to repeat it). |

If you want to learn more about debugging with Pdb, you will find an [interesting tutorial on that topic here](https://pymotw.com/3/pdb/).
