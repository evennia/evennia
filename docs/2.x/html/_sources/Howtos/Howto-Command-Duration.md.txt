# Commands that take time to finish

    > craft fine sword 
    You start crafting a fine sword. 
    > north 
    You are too focused on your crafting, and can't move!
    You create the blade of the sword. 
    You create the pommel of the sword. 
    You finish crafting a Fine Sword.

In some types of games a command should not start and finish immediately.

Loading a crossbow might take a bit of time to do - time you don't have when
the enemy comes rushing at you. Crafting that armour will not be immediate
either. For some types of games the very act of moving or changing pose all
comes with a certain time associated with it. 

There are two main suitable ways to introduce a 'delay' in a [Command](../Components/Commands.md)'s execution:

- Using `yield` in the Command's `func` method. 
- Using the  `evennia.utils.delay` utility function.

We'll simplify both below.

## Pause commands with `yield`

The `yield` keyword is a reserved word in Python. It's used to create [generators](https://realpython.com/introduction-to-python-generators/), which are interesting in their own right. For the purpose of this howto though, we just need to know that Evennia will use it to 'pause' the execution of the command for a certain time.

```{sidebar} This only works in Command.func!

This `yield` functionality will *only* work in the `func` method of
Commands. It works because Evennia has especially catered for it as a convenient shortcut. Trying to  use it elsewhere will not work. If you want the same functionality  elsewhere you should look up the [interactive decorator](../Concepts/Async-Process.md#the-interactive-decorator).
```

```{code-block} python
:linenos:
:emphasize-lines: 15

class CmdTest(Command):

    """
    A test command just to test waiting.

    Usage:
        test

    """

    key = "test"

    def func(self):
        self.msg("Before ten seconds...")
        yield 10
        self.msg("Afterwards.")
```

- **Line 15** : This is the important line.  The `yield 10` tells Evennia to "pause" the command
and to wait for 10 seconds to execute the rest.  If you add this command and
run it, you'll see the first message, then, after a pause of ten seconds, the
next message.  You can use `yield` several times in your command.

This syntax will not "freeze" all commands.  While the command is "pausing", you can execute other commands (or even call the same command again).  And other players aren't frozen either.

> Using `yield` is non-persistent. If you `reload` the game while a command is "paused", that pause state is lost and it will _not_ resume after the server has  reloaded. 

## Pause commands with `utils.delay`

The `yield` syntax is easy to read, easy to understand, easy to use.  But it's non-persistent and not that flexible if you want more advanced options. 

The `evennia.utils.delay` represents is a more powerful way to introduce delays. Unlike `yield`, it  
can be made persistent and also works outside of `Command.func`.  It's however a little more cumbersome to write since unlike `yield` it will not actually stop at the line it's called. 

```{code-block} python
:linenos:
:emphasize-lines: 14,30

from evennia import default_cmds, utils
    
class CmdEcho(default_cmds.MuxCommand):
    """
    Wait for an echo
    
    Usage: 
      echo <string>
    
    Calls and waits for an echo.
    """
    key = "echo"
    
    def echo(self):
        "Called after 10 seconds."
        shout = self.args
        self.caller.msg(
            "You hear an echo: "
            f"{shout.upper()} ... "
            f"{shout.capitalize()} ... "
            f"{shout.lower()}"
        )
    
    def func(self):
        """
         This is called at the initial shout.            
        """
        self.caller.msg(f"You shout '{self.args}' and wait for an echo ...")
        # this waits non-blocking for 10 seconds, then calls self.echo
        utils.delay(10, self.echo) # call echo after 10 seconds
    
```

Import this new echo command into the default command set and reload the server. You will find that it will take 10 seconds before you see your shout coming back. 

- **Line 14**: We add a new method `echo`. This is a _callback_ - a method/function we will call after a certain time. 
- **Line 30**: Here we use `utils.delay` to tell Evennia "Please wait for 10 seconds, then call "`self.echo`". Note how we pass `self.echo` and _not_ `self.echo()`!  If we did the latter, `echo` would fire _immediately_. Instead we let Evennia do this call for us ten seconds later.

You will also find that this is a *non-blocking* effect; you can issue other commands in the interim and the game will go on as usual. The echo will come back to you in its own time.

The call signature for `utils.delay` is: 

```python
utils.delay(timedelay, callback, persistent=False, *args, **kwargs) 
```

```{sidebar} *args and **kwargs 

These are used to indicate any number of arguments or keyword-arguments should be picked up here. In code they are treated as a `tuple` and a `dict` respectively. 

`*args` and `**kwargs` are used in many places in Evennia. [See an online tutorial here](https://realpython.com/python-kwargs-and-args).
```
If you set `persistent=True`, this delay will survive a `reload`. If you pass `*args` and/or `**kwargs`, they will be passed on into the `callback`. So this way you can pass more complex arguments to the delayed function. 

It's important to remember that the `delay()` call will not "pause" at that point when it is
called (the way `yield` does in the previous section). The lines after the `delay()` call will
actually execute *right away*. What you must do is to tell it which function to call *after the time
has passed* (its "callback"). This may sound strange at first, but it is normal practice in
asynchronous systems. You can also link such calls together:

```{code-block}
:linenos:
:emphasize-lines: 19,22,28,34

from evennia import default_cmds, utils
    
class CmdEcho(default_cmds.MuxCommand):
    """
    waits for an echo
    
    Usage: 
      echo <string>
    
    Calls and waits for an echo
    """
    key = "echo"
    
    def func(self):
        "This sets off a chain of delayed calls"
        self.caller.msg(f"You shout '{self.args}', waiting for an echo ...")

        # wait 2 seconds before calling self.echo1
        utils.delay(2, self.echo1)
    
    # callback chain, started above
    def echo1(self):
        "First echo"
        self.caller.msg(f"... {self.args.upper()}")
        # wait 2 seconds for the next one
        utils.delay(2, self.echo2)

    def echo2(self):
        "Second echo"
        self.caller.msg(f"... {self.args.capitalize()}")
        # wait another 2 seconds
        utils.delay(2, callback=self.echo3)

    def echo3(self):
        "Last echo"
        self.caller.msg(f"... {self.args.lower()} ...")
```

The above version will have the echoes arrive one after another, each separated by a two second
delay.

- **Line 19**: This sets off the chain, telling Evennia to wait 2 seconds before calling `self.echo1`.
- **Line 22**: This is called after 2 seconds. It tells Evennia to wait another 2 seconds before calling `self.echo2`.
- **Line 28**: This is called after yet another 2 seonds (4s total). It tells Evennia to wait another 2 seconds before calling, `self.echo3`.
- **Line34** Called after another 2 seconds (6s total). This ends  the delay-chain.

```
> echo Hello!
... HELLO!
... Hello!
... hello! ...
```

```{warning} What about time.sleep?

You may be aware of the `time.sleep` function coming with Python. Doing `time.sleep(10) pauses Python for 10 seconds. **Do not use this**, it will not work with Evennia. If you use it, you will block the _entire server_ (everyone!) for ten seconds! 

If you want specifics, `utils.delay` is a thin wrapper around a [Twisted Deferred](https://docs.twisted.org/en/twisted-22.1.0/core/howto/defer.html). This is an [asynchronous concept](../Concepts/Async-Process.md).
```

## Making a blocking command

Both `yield` or `utils.delay()` pauses the command but allows the user to use other commands while the first one waits to finish. 

In some cases you want to instead have that command 'block' other commands from running. An example is crafting a helmet: most likely you should not be able to start crafting a shield at the same time. Or even walk out of the smithy. 

The simplest way of implementing blocking is to use the technique covered in the [How to implement a Command Cooldown](./Howto-Command-Cooldown.md) tutorial. In that tutorial we cooldowns are implemented by comparing the current time with the last time the command was used. This is the best approach if you can get away with it. It could work well for our crafting example ... _if_ you don't want to automatically update the player on their progress. 

In short: 
    - If you are fine with the player making an active input to check their status, compare timestamps as done in the Command-cooldown tutorial. On-demand is by far the most efficent.
    - If you want Evennia to tell the user their status without them taking a further action, you need to use `yield` , `delay` (or some other active time-keeping method).

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
itself) it can be accessed by other Commands too. Other attacks may also not work when you are off balance. You could also have an enemy Command check your `off_balance` status to gain bonuses, to take another example.

## Make a Command possible to Abort

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