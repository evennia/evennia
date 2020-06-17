# Command Duration


Before reading this tutorial, if you haven't done so already, you might want to
read [the documentation on commands](Component/Commands) to get a basic understanding of
how commands work in Evennia.

In some types of games a command should not start and finish immediately.
Loading a crossbow might take a bit of time to do - time you don't have when
the enemy comes rushing at you. Crafting that armour will not be immediate
either. For some types of games the very act of moving or changing pose all
comes with a certain time associated with it. 

## The simple way to pause commands with yield

Evennia allows a shortcut in syntax to create simple pauses in commands.  This
syntax uses the `yield` keyword.  The `yield` keyword is used in Python to
create generators, although you don't need to know what generators are to use
this syntax.  A short example will probably make it clear:

```python
class CmdTest(Command):

    """
    A test command just to test waiting.

    Usage:
        test

    """

    key = "test"
    locks = "cmd:all()"

    def func(self):
        self.msg("Before ten seconds...")
        yield 10
        self.msg("Afterwards.")
```
> Important: The `yield` functionality will *only* work in the `func` method of
> Commands. It only works because Evennia has especially
> catered for it in Commands. If you want the same functionality elsewhere you
> must use the [interactive decorator](Concept/Async-Process#The-@interactive-decorator).

The important line is the `yield 10`.  It tells Evennia to "pause" the command
and to wait for 10 seconds to execute the rest.  If you add this command and
run it, you'll see the first message, then, after a pause of ten seconds, the
next message.  You can use `yield` several times in your command.

This syntax will not "freeze" all commands.  While the command is "pausing",
     you can execute other commands (or even call the same command again).  And
     other players aren't frozen either.

> Note: this will not save anything in the database.  If you reload the game
> while a command is "paused", it will not resume after the server has
> reloaded.


## The more advanced way with utils.delay

The `yield` syntax is easy to read, easy to understand, easy to use.  But it's not that flexible if
you want more advanced options.  Learning to use alternatives might be much worth it in the end.

Below is a simple command example for adding a duration for a command to finish.

```python
from evennia import default_cmds, utils
    
class CmdEcho(default_cmds.MuxCommand):
    """
    wait for an echo
    
    Usage: 
      echo <string>
    
    Calls and waits for an echo
    """
    key = "echo"
    locks = "cmd:all()"
    
    def func(self):
        """
         This is called at the initial shout.            
        """
        self.caller.msg("You shout '%s' and wait for an echo ..." % self.args)
        # this waits non-blocking for 10 seconds, then calls self.echo
        utils.delay(10, self.echo) # call echo after 10 seconds
    
    def echo(self):
        "Called after 10 seconds."
        shout = self.args
        string = "You hear an echo: %s ... %s ... %s"
        string = string % (shout.upper(), shout.capitalize(), shout.lower())
        self.caller.msg(string)
```

Import this new echo command into the default command set and reload the server. You will find that
it will take 10 seconds before you see your shout coming back. You will also find that this is a
*non-blocking* effect; you can issue other commands in the interim and the game will go on as usual.
The echo will come back to you in its own time.

### About utils.delay()

`utils.delay(timedelay, callback, persistent=False, *args, **kwargs)` is a useful function.  It will
wait `timedelay` seconds, then call the `callback` function, optionally passing to it the arguments
provided to utils.delay by way of *args and/or **kwargs`.

> Note: The callback argument should be provided with a python path to the desired function, for
instance `my_object.my_function` instead of `my_object.my_function()`. Otherwise my_function would
get called and run immediately upon attempting to pass it to the delay function.
If you want to provide arguments for utils.delay to use, when calling your callback function, you
have to do it separatly, for instance using the utils.delay *args and/or **kwargs, as mentioned
above.

> If you are not familiar with the syntax `*args` and `**kwargs`, [see the Python documentation
here](https://docs.python.org/2/tutorial/controlflow.html#arbitrary-argument-lists).

Looking at it you might think that `utils.delay(10, callback)` in the code above is just an
alternative to some more familiar thing like `time.sleep(10)`. This is *not* the case. If you do
`time.sleep(10)` you will in fact freeze the *entire server* for ten seconds! The `utils.delay()`is
a thin wrapper around a Twisted
[Deferred](http://twistedmatrix.com/documents/11.0.0/core/howto/defer.html) that will delay
execution until 10 seconds have passed, but will do so asynchronously, without bothering anyone else
(not even you - you can continue to do stuff normally while it waits to continue).

The point to remember here is that the `delay()` call will not "pause" at that point when it is
called (the way `yield` does in the previous section). The lines after the `delay()` call will
actually execute *right away*. What you must do is to tell it which function to call *after the time
has passed* (its "callback"). This may sound strange at first, but it is normal practice in
asynchronous systems. You can also link such calls together as seen below:

```python
from evennia import default_cmds, utils
    
class CmdEcho(default_cmds.MuxCommand):
    """
    waits for an echo
    
    Usage: 
      echo <string>
    
    Calls and waits for an echo
    """
    key = "echo"
    locks = "cmd:all()"
    
    def func(self):
        "This sets off a chain of delayed calls"
        self.caller.msg("You shout '%s', waiting for an echo ..." % self.args)

        # wait 2 seconds before calling self.echo1
        utils.delay(2, self.echo1)
    
    # callback chain, started above
    def echo1(self):
        "First echo"
        self.caller.msg("... %s" % self.args.upper())
        # wait 2 seconds for the next one
        utils.delay(2, self.echo2)

    def echo2(self):
        "Second echo"
        self.caller.msg("... %s" % self.args.capitalize())
        # wait another 2 seconds
        utils.delay(2, callback=self.echo3)

    def echo3(self):
        "Last echo"
        self.caller.msg("... %s ..." % self.args.lower())
```

The above version will have the echoes arrive one after another, each separated by a two second
delay.

    > echo Hello!
    ... HELLO!
    ... Hello!
    ... hello! ...

## Blocking commands

As mentioned, a great thing about the delay introduced by `yield` or `utils.delay()` is that it does
not block. It just goes on in the background and you are free to play normally in the interim. In
some cases this is not what you want however. Some commands should simply "block" other commands
while they are running. If you are in the process of crafting a helmet you shouldn't be able to also
start crafting a shield at the same time, or if you just did a huge power-swing with your weapon you
should not be able to do it again immediately.

The simplest way of implementing blocking is to use the technique covered in the [Command
Cooldown](Command-Cooldown) tutorial. In that tutorial we implemented cooldowns by having the
Command store the current time. Next time the Command was called, we compared the current time to
the stored time to determine if enough time had passed for a renewed use. This is a *very*
efficient, reliable and passive solution. The drawback is that there is nothing to tell the Player
when enough time has passed unless they keep trying.

Here is an example where we will use `utils.delay` to tell the player when the cooldown has passed:

```python
from evennia import utils, default_cmds
    
class CmdBigSwing(default_cmds.MuxCommand):
    """
    swing your weapon in a big way

    Usage:
      swing <target>
    
    Makes a mighty swing. Doing so will make you vulnerable
    to counter-attacks before you can recover. 
    """
    key = "bigswing"
    locks = "cmd:all()"
    
    def func(self):
        "Makes the swing" 

        if self.caller.ndb.off_balance:
            # we are still off-balance.
            self.caller.msg("You are off balance and need time to recover!")
            return      
      
        # [attack/hit code goes here ...]
        self.caller.msg("You swing big! You are off balance now.")   

        # set the off-balance flag
        self.caller.ndb.off_balance = True
            
        # wait 8 seconds before we can recover. During this time 
        # we won't be able to swing again due to the check at the top.        
        utils.delay(8, self.recover)
    
    def recover(self):
        "This will be called after 8 secs"
        del self.caller.ndb.off_balance            
        self.caller.msg("You regain your balance.")
```    

Note how, after the cooldown, the user will get a message telling them they are now ready for
another swing.

By storing the `off_balance` flag on the character (rather than on, say, the Command instance
itself) it can be accessed by other Commands too. Other attacks may also not work when you are off
balance. You could also have an enemy Command check your `off_balance` status to gain bonuses, to
take another example.

## Abortable commands

One can imagine that you will want to abort a long-running command before it has a time to finish.
If you are in the middle of crafting your armor you will probably want to stop doing that when a
monster enters your smithy.

You can implement this in the same way as you do the "blocking" command above, just in reverse.
Below is an example of a crafting command that can be aborted by starting a fight:

```python
from evennia import utils, default_cmds
    
class CmdCraftArmour(default_cmds.MuxCommand):
    """
    Craft armour
    
    Usage:
       craft <name of armour>
    
    This will craft a suit of armour, assuming you
    have all the components and tools. Doing some
    other action (such as attacking someone) will 
    abort the crafting process. 
    """
    key = "craft"
    locks = "cmd:all()"
    
    def func(self):
        "starts crafting"

        if self.caller.ndb.is_crafting:
            self.caller.msg("You are already crafting!")
            return 
        if self._is_fighting():
            self.caller.msg("You can't start to craft "
                            "in the middle of a fight!")
            return
            
        # [Crafting code, checking of components, skills etc]          

        # Start crafting
        self.caller.ndb.is_crafting = True
        self.caller.msg("You start crafting ...")
        utils.delay(60, self.step1)
    
    def _is_fighting(self):
        "checks if we are in a fight."
        if self.caller.ndb.is_fighting:                
            del self.caller.ndb.is_crafting 
            return True
      
    def step1(self):
        "first step of armour construction"
        if self._is_fighting(): 
            return
        self.msg("You create the first part of the armour.")
        utils.delay(60, callback=self.step2)

    def step2(self):
        "second step of armour construction"
        if self._is_fighting(): 
            return
        self.msg("You create the second part of the armour.")            
        utils.delay(60, step3)

    def step3(self):
        "last step of armour construction"
        if self._is_fighting():
            return          
    
        # [code for creating the armour object etc]

        del self.caller.ndb.is_crafting
        self.msg("You finalize your armour.")
    
    
# example of a command that aborts crafting
    
class CmdAttack(default_cmds.MuxCommand):
    """
    attack someone
    
    Usage:
        attack <target>
    
    Try to cause harm to someone. This will abort
    eventual crafting you may be currently doing. 
    """
    key = "attack"
    aliases = ["hit", "stab"]
    locks = "cmd:all()"
    
    def func(self):
        "Implements the command"

        self.caller.ndb.is_fighting = True
    
        # [...]
```

The above code creates a delayed crafting command that will gradually create the armour. If the
`attack` command is issued during this process it will set a flag that causes the crafting to be
quietly canceled next time it tries to update.

## Persistent delays

In the latter examples above we used `.ndb` storage. This is fast and easy but it will reset all
cooldowns/blocks/crafting etc if you reload the server. If you don't want that you can replace
`.ndb` with `.db`. But even this won't help because the `yield` keyword is not persisent and nor is
the use of `delay` shown above. To resolve this you can use `delay` with the `persistent=True`
keyword. But wait! Making something persistent will add some extra complications, because now you
must make sure Evennia can properly store things to the database.

Here is the original echo-command reworked to function with persistence: 
```python
from evennia import default_cmds, utils
    
# this is now in the outermost scope and takes two args! 
def echo(caller, args):
    "Called after 10 seconds."
    shout = args
    string = "You hear an echo: %s ... %s ... %s"
    string = string % (shout.upper(), shout.capitalize(), shout.lower())
    caller.msg(string)

class CmdEcho(default_cmds.MuxCommand):
    """
    wait for an echo
    
    Usage: 
      echo <string>
    
    Calls and waits for an echo
    """
    key = "echo"
    locks = "cmd:all()"
    
    def func(self):
        """
         This is called at the initial shout.            
        """
        self.caller.msg("You shout '%s' and wait for an echo ..." % self.args)
        # this waits non-blocking for 10 seconds, then calls echo(self.caller, self.args)
        utils.delay(10, echo, self.caller, self.args, persistent=True) # changes! 
    
```

Above you notice two changes: 
- The callback (`echo`) was moved out of the class and became its own stand-alone function in the
outermost scope of the module. It also now takes `caller` and `args` as arguments (it doesn't have
access to them directly since this is now a stand-alone function).
- `utils.delay` specifies the `echo` function (not `self.echo` - it's no longer a method!) and sends
`self.caller` and `self.args` as arguments for it to use. We also set `persistent=True`.

The reason for this change is because Evennia needs to `pickle` the callback into storage and it
cannot do this correctly when the method sits on the command class. Now this behave the same as the
first version except if you reload (or even shut down) the server mid-delay it will still fire the
callback when the server comes back up (it will resume the countdown and ignore the downtime).