# Adding Command Tutorial

[prev lesson](Python-classes-and-objects) | [next lesson]()

A Command is something that handles the input from a user and causes a result to happen.
An example is `look`, which examines your current location and tells how it looks like and
what is in it. 

In Evennia, a Command is a Python _class_. If you are unsure about what a class is, review the 
previous lesson. A Command inherits from `evennia.Command` or from one of the alternative command-
classes, such as `MuxCommand` which is what most default commands use. 

All Commands are in turn grouped in another class called a _Command Set_. Think of a Command set
as a bag holding many different commands. One CmdSet could for example hold all commands for 
combat, another for building etc. 

Command-Sets are then associated with objects. Doing so makes the commands in that cmdset available 
to the object. So, to summarize: 

- Commands are classes
- A group of Commands is stored in a CmdSet
- Putting a CmdSet on an object makes all commands in it available to the object

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
[basic Python tutorial](Python-basic-introduction), you will recognize `.msg` - this will send a message
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
enough to make `echo` a _permanent_ change though: 

    > py self.cmdset.add("commands.mycommands.MyCmdSet", permanent=True)
    
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

```python
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
- **Line 4**: The normal `class` header. We inherit from `Command` which we imported at the top of this file.
- **Lines 5**-11: The docstring and help-entry for the command. You could expand on this as much as you wanted.
- **Line 12**: We want to write `hit` to use this command.
- **Line 15**: We strip the whitespace from the argument like before. Since we don't want to have to do 
    `self.args.strip()` over and over, we store the stripped version
    in a _local variable_ `args`. Note that we don't modify `self.args` by doing this, `self.args` will still
    have the whitespace and is not the same as `args` in this example.
```sidebar:: if-statements
    
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
- **Line 16** has our first _conditional_, an `if` statement. This is written on the form `if <condition>:` and only
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
- **Lines 17-18**: This code will only run if the `if` statement is truthy, in this case if `args` is the empty string.
- **Line 18**: `return` is a reserved Python word that exits `func` immediately. 
- **Line 19**: We use `self.caller.search` to look for the target in the current location.
- **Lines 20-21**: A feature of `.search` is that it will already inform `self.caller` if it couldn't find the target.
   In that case, `target` will be `None` and we should just directly `return`. 
- **Lines 22-23**: At this point we have a suitable target and can send our punching strings to each.

Finally we must also add this to a CmdSet. Let's add it to `MyCmdSet` which we made permanent earlier. 

```python
# ...

class MyCmdSet(CmdSet):

    def at_cmdset_creation(self):
        self.add(CmdEcho)
        self.add(CmdHit)

```

```sidebar:: Errors in your code

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

## More advanced parsing 

Let's expand our simple `hit` command to accept a little more complex input: 

    hit <target> [[with] <weapon>]
    
That is, we want to support all of these forms

    hit target     
    hit target weapon
    hit target with weapon

If you don't specify a weapon you'll use your fists. It's also nice to be able to skip "with" if 
you are in a hurry. Time to modify `mygame/commands/mycommands.py` again. Let us break out the parsing 
a little, in a new method `parse`:


```python
#...

class CmdHit(Command):
    """
    Hit a target.
    
    Usage:
      hit <target>

    """
    key = "hit"

    def parse(self):       
        self.args = self.args.strip()
        target, *weapon = self.args.split(" with ", 1)
        if not weapon:
            target, *weapon = target.split(" ", 1)          
        self.target = target.strip() 
        if weapon:
            self.weapon = weapon.strip()
        else:
            self.weapon = ""

    def func(self):
        if not self.args:
            self.caller.msg("Who do you want to hit?")
            return 
        # get the target for the hit
        target = self.caller.search(self.target)              
        if not target:
            return 
        # get and handle the weapon 
        weapon = None
        if self.weapon:
            weapon = self.caller.search(self.weapon)
        if weapon: 
            weaponstr = f"{weapon.key}"
        else:
            weaponstr = "bare fists"
               
        self.caller.msg(f"You hit {target.key} with {weaponstr}!") 
        target.msg(f"You got hit by {self.caller.key} with {weaponstr}!")
# ...

```

The `parse` method is called before `func` and has access to all the same on-command variables as in `func`. Using
`parse` not only makes things a little easier to read, it also means you can easily let other Commands _inherit_ 
your parsing - if you wanted some other Command to also understand input on the form `<arg> with <arg>` you'd inherit
from this class and just implement the `func` needed for that command without implementing `parse` anew.

```sidebar:: Tuples and Lists 

    - A `list` is written as `[a, b, c, d, ...]`. You can add and grow/shrink a list after it was first created. 
    - A `tuple` is written as `(a, b, c, d, ...)`. A tuple cannot be modified once it is created. 

```
- **Line 14** - We do the stripping of `self.args` once and for all here. We also store the stripped version back 
  into `self.args`, overwriting it. So there is no way to get back the non-stripped version from here on, which is fine
  for this command. 
- **Line 15** - This makes use of the `.split` method of strings. `.split` will, well, split the string by some criterion.
    `.split(" with ", 1)` means "split the string once, around the substring `" with "` if it exists". The result
    of this split is a _list_. Just how that list looks depends on the string we are trying to split:
    1. If we entered just `hit smaug`, we'd be splitting just `"smaug"` which would give the result `["smaug"]`.
    2. `hit smaug sword` gives `["smaug sword"]`
    3. `hit smaug with sword` gives `["smaug", "sword"]`
    
    So we get a list of 1 or 2 elements. We assign it to two variables like this, `target, *weapon = `. That 
    asterisk in `*weapon` is a nifty trick - it will automatically become a list of _0 or more_ values. It sorts of
    "soaks" up everything left over.
    1. `target` becomes `"smaug"` and `weapon` becomes `[]`
    2. `target` becomes `"smaug sword"` and `weapon` becomes `[]`
    3. `target` becomes `"smaug"` and `weapon` becomes `sword`
- **Lines 16-17** - In this `if` condition we check if `weapon` is falsy (that is, the empty list). This can happen
    under two conditions (from the example above): 
    1. `target` is simply `smaug`
    2. `target` is `smaug sword`
    
    To separate these cases we split `target` once again, this time by empty space `" "`. Again we store the 
    result back with `target, *weapon =`. The result will be one of the following:
    1. `target` remains `smaug` and `weapon` remains `[]`
    2. `target` becomes `smaug` and `weapon` becomes `sword`
- **Lines 18-22** - We now store `target` and `weapon` into `self.target` and `self.weapon`. We must do this in order
   for these local variables to made available in `func` later. Note how we need to check so `weapon` is not falsy
   before running `strip()` on it. This is because we know that if it's falsy, it's an empty list `[]` and lists 
   don't have the `.strip()` method on them (so if we tried to use it, we'd get an error).
   
Now onto the `func` method. The main difference is we now have `self.target` and `self.weapon` available for 
convenient use. 
- **Lines 29 and 35** - We make use of the previously parsed search terms for the target and weapon to find the 
    respective resource. 
- **Lines 34-39** - Since the weapon is optional, we need to supply a default (use our fists!) if it's not set. We 
    use this to create a `weaponstr` that is different depending on if we have a weapon or not.
- **Lines 41-42** - We merge the `weaponstr` with our attack text.

Let's try it out!

    > reload 
    > hit smaug with sword 
    Could not find 'sword'.
    You hit smaug with bare fists!
    
Oops, our `self.caller.search(self.weapon)` is telling us that it found no sword. Since we are not `return`ing
in this situation (like we do if failing to find `target`) we still continue fighting with our bare hands. 
This won't do. Let's make ourselves a sword. 

    > create sword 
    
Since we didn't specify `/drop`, the sword will end up in our inventory and can seen with the `i` or 
`inventory` command. The `.search` helper will still find it there. There is no need to reload to see this 
change (no code changed, only stuff in the database).

    > hit smaug with sword 
    You hit smaug with sword! 


## Adding the Command to a default Cmdset


For now, let's drop MyCmdSet:

    > py self.cmdset.remove("commands.mycommands.MyCmdSet")





The command is not available to use until it is part of a [Command Set](../../../Component/Command-Sets). In this
example we will go the easiest route and add it to the default Character commandset that already
exists. 

1. Edit `mygame/commands/default_cmdsets.py`
1. Import your new command with  `from commands.command import CmdEcho`.
1. Add a line `self.add(CmdEcho())` to `CharacterCmdSet`, in the `at_cmdset_creation` method (the
   template tells you where). 

This is approximately how it should look at this point:

```python
        # file mygame/commands/default_cmdsets.py
        #[...]
        from commands.command import CmdEcho
        #[...]
        class CharacterCmdSet(default_cmds.CharacterCmdSet):
        
            key = "DefaultCharacter"
    
            def at_cmdset_creation(self):
    
                # this first adds all default commands
                super(DefaultSet, self).at_cmdset_creation()
    
                # all commands added after this point will extend or 
                # overwrite the default commands.       
                self.add(CmdEcho())
```

Next, run the `@reload` command. You should now be able to use your new `echo` command from inside
the game. Use `help echo` to see the documentation for the command.

If you have trouble, make sure to check the log for error messages (probably due to syntax errors in
your command definition).

> Note: Typing `echotest` will also work. It will be handled as the command `echo` directly followed
by
its argument `test` (which will end up in `self.args). To change this behavior, you can add the
`arg_regex` property alongside `key`, `help_category` etc. [See the arg_regex
documentation](Commands#on-arg_regex) for more info.

If you want to overload existing default commands (such as `look` or `get`), just add your new
command with the same key as the old one - it will then replace it. Just remember that you must use
`@reload` to see any changes. 

See [Commands](../../../Component/Commands) for many more details and possibilities when defining Commands and using
Cmdsets in various ways.


## Adding the command to specific object types

Adding your Command to the `CharacterCmdSet` is just one easy exapmple. The cmdset system is very
generic. You can create your own cmdsets (let's say in a module `mycmdsets.py`) and add them to
objects as you please (how to control their merging is described in detail in the [Command Set
documentation](Command-Sets)).

```python
    # file mygame/commands/mycmdsets.py
    #[...]
    from commands.command import CmdEcho
    from evennia import CmdSet
    #[...]
    class MyCmdSet(CmdSet):
        
        key = "MyCmdSet"
    
        def at_cmdset_creation(self):     
            self.add(CmdEcho())
```
Now you just need to add this to an object. To test things (as superuser) you can do

     @py self.cmdset.add("mycmdsets.MyCmdSet")

This will add this cmdset (along with its echo command) to yourself so you can test it. Note that
you cannot add a single Command to an object on its own, it must be part of a CommandSet in order to
do so.

The Command you added is not there permanently at this point. If you do a `@reload` the merger will
be gone. You *could* add the `permanent=True` keyword to the `cmdset.add` call. This will however
only make the new merged cmdset permanent on that *single* object. Often you want *all* objects of
this particular class to have this cmdset.

To make sure all new created objects get your new merged set, put the `cmdset.add` call in your
custom [Typeclasses](../../../Component/Typeclasses)' `at_object_creation` method: 

```python
    # e.g. in mygame/typeclasses/objects.py

    from evennia import DefaultObject
    class MyObject(DefaultObject):
        
        def at_object_creation(self):
            "called when the object is first created"
            self.cmdset.add("mycmdset.MyCmdSet", permanent=True)
```           

All new objects of this typeclass will now start with this cmdset and it will survive a `@reload`. 

*Note:* An important caveat with this is that `at_object_creation` is only called *once*, when the
object is first created. This means that if you already have existing objects in your databases
using that typeclass, they will not have been initiated the same way. There are many ways to update
them; since it's a one-time update you can usually just simply loop through them. As superuser, try
the following: 

     @py from typeclasses.objects import MyObject; [o.cmdset.add("mycmdset.MyCmdSet") for o in
MyObject.objects.all()]

This goes through all objects in your database having the right typeclass, adding the new cmdset to
each. The good news is that you only have to do this if you want to post-add *cmdsets*. If you just
want to add a new *command*, you can simply add that command to the cmdset's `at_cmdset_creation`
and `@reload` to make the Command immediately available.

## Change where Evennia looks for command sets 

Evennia uses settings variables to know where to look for its default command sets. These are
normally not changed unless you want to re-organize your game folder in some way. For example, the
default character cmdset defaults to being defined as

    CMDSET_CHARACTER="commands.default_cmdset.CharacterCmdSet"


[prev lesson](Python-classes-and-objects) | [next lesson]()
