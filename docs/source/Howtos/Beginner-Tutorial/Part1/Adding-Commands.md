# Adding custom commands

In this lesson we'll learn how to create our own Evennia _Commands_. If you are new to Python you'll
also learn some more basics about how to manipulate strings and get information out of Evennia.

A Command is something that handles the input from a user and causes a result to happen.
An example is `look`, which examines your current location and tells how it looks like and
what is in it.

```{sidebar} Commands are not typeclassed

If you just came from the previous lesson, you might want to know that Commands and
CommandSets are not `typeclassed`. That is, instances of them are not saved to the
database. They are "just" normal Python classes.
```

In Evennia, a Command is a Python _class_. If you are unsure about what a class is, review the
previous lessons! A Command inherits from `evennia.Command` or from one of the alternative command-
classes, such as `MuxCommand` which is what most default commands use.

All Commands are in turn grouped in another class called a _Command Set_. Think of a Command Set
as a bag holding many different commands. One CmdSet could for example hold all commands for
combat, another for building etc. By default, Evennia groups all character-commands into one
big cmdset.

Command-Sets are then associated with objects, for example with your Character. Doing so makes the
commands in that cmdset available to the object. So, to summarize:

- Commands are classes
- A group of Commands is stored in a CmdSet
- CmdSets are stored on objects - this defines which commands are available to that object.

## Creating a custom command

Open `mygame/commands/command.py`:

```python
"""
(module docstring)
"""

from evennia import Command as BaseCommand
# from evennia import default_cmds

class Command(BaseCommand):
    """
    (class docstring)
    """
    pass

# (lots of commented-out stuff)
# ...
```

Ignoring the docstrings (which you can read if you want), this is the only really active code in the module.

We can see that we import `Command` from `evennia` and use the `from ... import ... as ...` form to rename it
to `BaseCommand`. This is so we can let our child class also be named `Command` for reference.  The class
itself doesn't do anything, it just has `pass`. So in the same way as `Object` in the previous lesson, this
class is identical to its parent.

> The commented out `default_cmds` gives us access to Evennia's default commands for easy overriding. We'll try
> that a little later.

We could modify this module directly, but to train imports we'll work in a separate module. Open a new file
`mygame/commands/mycommands.py` and add the following code:

```python

from commands.command import Command

class CmdEcho(Command):
    key = "echo"

```

This is the simplest form of command you can imagine. It just gives itself a name, "echo". This is
what you will use to call this command later.

Next we need to put this in a CmdSet. It will be a one-command CmdSet for now! Change your file as such:


```python

from commands.command import Command
from evennia import CmdSet

class CmdEcho(Command):
    key = "echo"


class MyCmdSet(CmdSet):

    def at_cmdset_creation(self):
        self.add(CmdEcho)

```

Our `EchoCmdSet` class must have an `at_cmdset_creation` method, named exactly
like this - this is what Evennia will be looking for when setting up the cmdset later, so
if you didn't set it up, it will use the parent's version, which is empty. Inside we add the
command class to the cmdset by `self.add()`. If you wanted to add more commands to this CmdSet you
could just add more lines of `self.add` after this.

Finally, let's add this command to ourselves so we can try it out. In-game you can experiment with `py` again:

    > py self.cmdset.add("commands.mycommands.MyCmdSet")

Now try

    > echo
    Command echo has no defined `func()` - showing on-command variables:
    ...
    ...

You should be getting a long list of outputs. The reason for this is that your `echo` function is not really
"doing" anything yet and the default function is then to show all useful resources available to you when you
use your Command. Let's look at some of those listed:

    Command echo has no defined `func()` - showing on-command variables:
    obj (<class 'typeclasses.characters.Character'>): YourName
    lockhandler (<class 'evennia.locks.lockhandler.LockHandler'>): cmd:all()
    caller (<class 'typeclasses.characters.Character'>): YourName
    cmdname (<class 'str'>): echo
    raw_cmdname (<class 'str'>): echo
    cmdstring (<class 'str'>): echo
    args (<class 'str'>):
    cmdset (<class 'evennia.commands.cmdset.CmdSet'>): @mail, about, access, accounts, addcom, alias, allcom, ban, batchcode, batchcommands, boot, cboot, ccreate,
        cdesc, cdestroy, cemit, channels, charcreate, chardelete, checklockstring, clientwidth, clock, cmdbare, cmdsets, color, copy, cpattr, create, cwho, delcom,
        desc, destroy, dig, dolphin, drop, echo, emit, examine, find, force, get, give, grapevine2chan, help, home, ic, inventory, irc2chan, ircstatus, link, lock,
        look, menutest, mudinfo, mvattr, name, nick, objects, ooc, open, option, page, password, perm, pose, public, py, quell, quit, reload, reset, rss2chan, say,
        script, scripts, server, service, sessions, set, setdesc, sethelp, sethome, shutdown, spawn, style, tag, tel, test2010, test2028, testrename, testtable,
        tickers, time, tunnel, typeclass, unban, unlink, up, up, userpassword, wall, whisper, who, wipe
    session (<class 'evennia.server.serversession.ServerSession'>): Griatch(#1)@1:2:7:.:0:.:0:.:1
    account (<class 'typeclasses.accounts.Account'>): Griatch(account 1)
    raw_string (<class 'str'>): echo

    --------------------------------------------------
    echo - Command variables from evennia:
    --------------------------------------------------
    name of cmd (self.key): echo
    cmd aliases (self.aliases): []
    cmd locks (self.locks): cmd:all();
    help category (self.help_category): General
    object calling (self.caller): Griatch
    object storing cmdset (self.obj): Griatch
    command string given (self.cmdstring): echo
    current cmdset (self.cmdset): ChannelCmdSet

These are all properties you can access with `.` on the Command instance, such as `.key`, `.args` and so on.
Evennia makes these available to you and they will be different every time a command is run. The most
important ones we will make use of now are:

 - `caller` - this is 'you', the person calling the command.
 - `args` - this is all arguments to the command. Now it's empty, but if you tried `echo foo bar` you'd find
   that this would be `" foo bar"`.
 - `obj` - this is object on which this Command (and CmdSet) "sits". So you, in this case.

The reason our command doesn't do anything yet is because it's missing a `func` method. This is what Evennia
looks for to figure out what a Command actually does. Modify your `CmdEcho` class:

```python
# ...

class CmdEcho(Command):
    """
    A simple echo command

    Usage:
        echo <something>

    """
    key = "echo"

    def func(self):
        self.caller.msg(f"Echo: '{self.args}'")

# ...
```

First we added a docstring. This is always a good thing to do in general, but for a Command class, it will also
automatically become the in-game help entry! Next we add the `func` method. It has one active line where it
makes use of some of those variables we found the Command offers to us. If you did the
[basic Python tutorial](./Python-basic-introduction.md), you will recognize `.msg` - this will send a message
to the object it is attached to us - in this case `self.caller`, that is, us. We grab `self.args` and includes
that in the message.

Since we haven't changed `MyCmdSet`, that will work as before. Reload and re-add this command to ourselves to
try out the new version:

    > reload
    > py self.cmdset.add("commands.mycommands.MyCmdSet")
    > echo
    Echo: ''

Try to pass an argument:

    > echo Woo Tang!
    Echo: ' Woo Tang!'

Note that there is an extra space before `Woo!`. That is because self.args contains the _everything_ after
the command name, including spaces. Evennia will happily understand if you skip that space too:

    > echoWoo Tang!
    Echo: 'Woo Tang!'

There are ways to force Evennia to _require_ an initial space, but right now we want to just ignore it since
it looks a bit weird for our echo example. Tweak the code:

```python
# ...

class CmdEcho(Command):
    """
    A simple echo command

    Usage:
        echo <something>

    """
    key = "echo"

    def func(self):
        self.caller.msg(f"Echo: '{self.args.strip()}'")

# ...
```

The only difference is that we called `.strip()` on `self.args`. This is a helper method available on all
strings - it strips out all whitespace before and after the string. Now the Command-argument will no longer
have any space in front of it.

    > reload
    > py self.cmdset.add("commands.mycommands.MyCmdSet")
    > echo Woo Tang!
    Echo: 'Woo Tang!'

Don't forget to look at the help for the echo command:

    > help echo

You will get the docstring you put in your Command-class.

### Making our cmdset persistent

It's getting a little annoying to have to re-add our cmdset every time we reload, right? It's simple
enough to make `echo` a _persistent_ change though:

    > py self.cmdset.add("commands.mycommands.MyCmdSet", persistent=True)

Now you can `reload` as much as you want and your code changes will be available directly without
needing to re-add the MyCmdSet again. To remove the cmdset again, do

    > py self.cmdset.remove("commands.mycommands.MyCmdSet")

But for now, keep it around, we'll expand it with some more examples.

### Figuring out who to hit

Let's try something a little more exciting than just echo. Let's make a `hit` command, for punching
someone in the face! This is how we want it to work:

    > hit <target>
    You hit <target> with full force!

Not only that, we want the <target> to see

    You got hit by <hitter> with full force!

Here, `<hitter>` would be the one using the `hit` command and `<target>` is the one doing the punching.

Still in `mygame/commands/mycommands.py`, add a new class, between `CmdEcho` and `MyCmdSet`.

```{code-block} python
:linenos:

# ...

class CmdHit(Command):
    """
    Hit a target.

    Usage:
      hit <target>

    """
    key = "hit"

    def func(self):
        args = self.args.strip()
        if not args:
            self.caller.msg("Who do you want to hit?")
            return
        target = self.caller.search(args)
        if not target:
            return
        self.caller.msg(f"You hit {target.key} with full force!")
        target.msg(f"You got hit by {self.caller.key} with full force!")
# ...

```

A lot of things to dissect here:
- **Line 3**: The normal `class` header. We inherit from `Command` which we imported at the top of this file.
- **Lines 4-10**: The docstring and help-entry for the command. You could expand on this as much as you wanted.
- **Line 11**: We want to write `hit` to use this command.
- **Line 14**: We strip the whitespace from the argument like before. Since we don't want to have to do
    `self.args.strip()` over and over, we store the stripped version
    in a _local variable_ `args`. Note that we don't modify `self.args` by doing this, `self.args` will still
    have the whitespace and is not the same as `args` in this example.
```{sidebar} if-statements

The full form of the if statement is

if condition:
    ...
elif othercondition:
    ...
else:
    ...

There can be any number of `elifs` to mark when different branches of the code should run. If
the `else` condition is given, it will run if none of the other conditions was truthy. In Python
the `if..elif..else` structure also serves the same function as `case` in some other languages.

```
- **Line 15** has our first _conditional_, an `if` statement. This is written on the form `if <condition>:` and only
    if that condition is 'truthy' will the indented code block under the `if` statement run. To learn what is truthy in
    Python it's usually easier to learn what is "falsy":
    - `False` - this is a reserved boolean word in Python. The opposite is `True`.
    - `None` - another reserved word. This represents nothing, a null-result or value.
    - `0` or `0.0`
    - The empty string `""` or `''` or `""""""` or `''''''`
    - Empty _iterables_ we haven't seen yet, like empty lists `[]`, empty tuples `()` and empty dicts `{}`.
    - Everything else is "truthy".

   Line 16's condition is `not args`. The `not` _inverses_ the result, so if `args` is the empty string (falsy), the
   whole conditional becomes truthy. Let's continue in the code:
- **Lines 16-17**: This code will only run if the `if` statement is truthy, in this case if `args` is the empty string.
- **Line 17**: `return` is a reserved Python word that exits `func` immediately.
- **Line 18**: We use `self.caller.search` to look for the target in the current location.
- **Lines 19-20**: A feature of `.search` is that it will already inform `self.caller` if it couldn't find the target.
   In that case, `target` will be `None` and we should just directly `return`.
- **Lines 21-22**: At this point we have a suitable target and can send our punching strings to each.

Finally we must also add this to a CmdSet. Let's add it to `MyCmdSet` which we made persistent earlier.

```python
# ...

class MyCmdSet(CmdSet):

    def at_cmdset_creation(self):
        self.add(CmdEcho)
        self.add(CmdHit)

```

```{sidebar} Errors in your code

With longer code snippets to try, it gets more and more likely you'll
make an error and get a `traceback` when you reload. This will either appear
directly in-game or in your log (view it with `evennia -l` in a terminal).
Don't panic; tracebacks are your friends - they are to be read bottom-up and usually describe
exactly where your problem is. Refer to `The Python intro <Python-basic-introduction.html>`_ for
more hints. If you get stuck, reach out to the Evennia community for help.

```

Next we reload to let Evennia know of these code changes and try it out:

    > reload
    hit
    Who do you want to hit?
    hit me
    You hit YourName with full force!
    You got hit by YourName with full force!

Lacking a target, we hit ourselves. If you have one of the dragons still around from the previous lesson
you could try to hit it (if you dare):

    hit smaug
    You hit Smaug with full force!

You won't see the second string. Only Smaug sees that (and is not amused).


## Summary

In this lesson we learned how to create our own Command, add it to a CmdSet and then to ourselves.
We also upset a dragon.

In the next lesson we'll learn how to hit Smaug with different weapons. We'll also
get into how we replace and extend Evennia's default Commands.
