# Commands


Commands are intimately linked to [Command Sets](./Command-Sets.md) and you need to read that page too to
be familiar with how the command system works. The two pages were split for easy reading.

The basic way for users to communicate with the game is through *Commands*. These can be commands directly related to the game world such as *look*, *get*, *drop* and so on, or administrative commands such as *examine* or *dig*.

The [default commands](./Default-Commands.md) coming with Evennia are 'MUX-like' in that they use @ for admin commands, support things like switches, syntax with the '=' symbol etc, but there is nothing that prevents you from implementing a completely different command scheme for your game. You can find the default commands in `evennia/commands/default`. You should not edit these directly - they will be updated by the Evennia team as new features are added. Rather you should look to them for inspiration and inherit your own designs from them.

There are two components to having a command running - the *Command* class and the [Command Set](./Command-Sets.md) (command sets were split into a separate wiki page for ease of reading).

1. A *Command* is a python class containing all the functioning code for what a command does - for example, a *get* command would contain code for picking up objects.
1. A *Command Set* (often referred to as a CmdSet or cmdset) is like a container for one or more Commands. A given Command can go into any number of different command sets. Only by putting the command set on a character object you will make all the commands therein available to use by that character. You can also store command sets on normal objects if you want users to be able to use the object in various ways. Consider a "Tree" object with a cmdset defining the commands *climb* and *chop down*. Or a "Clock" with a cmdset containing the single command *check time*.

This page goes into full detail about how to use Commands. To fully use them you must also read the page detailing [Command Sets](./Command-Sets.md).  There is also a step-by-step [Adding Command Tutorial](../Howtos/Beginner-Tutorial/Part1/Beginner-Tutorial-Adding-Commands.md) that will get you started quickly without the extra explanations.

## Defining Commands

All commands are implemented as normal Python classes inheriting from the base class `Command`
(`evennia.Command`). You will find that this base class is very "bare". The default commands of
Evennia actually inherit from a child of `Command` called `MuxCommand` - this is the class that
knows all the mux-like syntax like `/switches`, splitting by "=" etc.  Below we'll avoid mux-
specifics and use the base `Command` class directly.

```python
    # basic Command definition
    from evennia import Command

    class MyCmd(Command):
       """
       This is the help-text for the command
       """
       key = "mycommand"
       def parse(self):
           # parsing the command line here
       def func(self):
           # executing the command here
```

Here is a minimalistic command with no custom parsing:

```python
    from evennia import Command

    class CmdEcho(Command):
        key = "echo"

        def func(self):
            # echo the caller's input back to the caller
            self.caller.msg(f"Echo: {self.args}")

```

You define a new command by assigning a few class-global properties on your inherited class and
overloading one or two hook functions. The full gritty mechanic behind how commands work are found
towards the end of this page; for now you only need to know that the command handler creates an
instance of this class and uses that instance whenever you use this command - it also dynamically
assigns the new command instance a few useful properties that you can assume to always be available.

### Who is calling the command?

In Evennia there are three types of objects that may call the command.  It is important to be aware
of this since this will also assign appropriate `caller`, `session`, `sessid` and `account`
properties on the command body at runtime. Most often the calling type is `Session`.

* A [Session](./Sessions.md). This is by far the most common case when a user is entering a command in
their client.
    * `caller` - this is set to the puppeted [Object](./Objects.md) if such an object exists. If no
puppet is found, `caller` is set equal to `account`. Only if an Account is not found either (such as
before being logged in) will this be set to the Session object itself.
    * `session` - a reference to the [Session](./Sessions.md) object itself.
    * `sessid` - `sessid.id`, a unique integer identifier of the session.
    * `account` - the [Account](./Accounts.md) object connected to this Session. None if not logged in.
* An [Account](./Accounts.md). This only happens if `account.execute_cmd()` was used. No Session
information can be obtained in this case.
    * `caller` - this is set to the puppeted Object if such an object can be determined (without
Session info this can only be determined in `MULTISESSION_MODE=0` or `1`). If no puppet is found,
this is equal to `account`.
    * `session` - `None*`
    * `sessid` - `None*`
    * `account` - Set to the Account object.
* An [Object](./Objects.md). This only happens if `object.execute_cmd()` was used (for example by an
NPC).
    * `caller` - This is set to the calling Object in question.
    * `session` - `None*`
    * `sessid` - `None*`
    * `account` - `None`

> `*)`: There is a way to make the Session available also inside tests run directly on Accounts and Objects, and that is to pass it to `execute_cmd` like so: `account.execute_cmd("...", session=<Session>)`. Doing so *will* make the `.session` and `.sessid` properties available in the command.

### Properties assigned to the command instance at run-time

Let's say account *Bob* with a character *BigGuy* enters the command *look at sword*. After the system having successfully identified this as the "look" command and determined that BigGuy really has access to a command named `look`, it chugs the `look` command class out of storage and either loads an existing Command instance from cache or creates one. After some more checks it then assigns it the following properties:

- `caller` - The character BigGuy, in this example. This is a reference to the object executing the command. The value of this depends on what type of object is calling the command; see the previous section.
- `session` - the [Session](./Sessions.md) Bob uses to connect to the game and control BigGuy (see also previous section).
- `sessid` - the unique id of `self.session`, for quick lookup.
- `account` - the [Account](./Accounts.md) Bob (see previous section).
- `cmdstring` - the matched key for the command. This would be *look* in our example.
- `args` - this is the rest of the string, except the command name. So if the string entered was *look at sword*, `args` would be " *at sword*". Note the space kept - Evennia would correctly interpret `lookat sword` too. This is useful for things like `/switches` that should not use space. In the `MuxCommand` class used for default commands, this space is stripped. Also see the `arg_regex` property if you want to enforce a space to make `lookat sword` give a command-not-found error.
- `obj` - the game [Object](./Objects.md) on which this command is defined.  This need not be the caller, but since `look` is a common (default) command, this is probably defined directly on *BigGuy* - so `obj` will point to BigGuy.  Otherwise `obj` could be an Account or any interactive object with commands defined on it, like in the example of the "check time" command defined on a "Clock" object. - `cmdset` - this is a reference to the merged CmdSet (see below) from which this command was
matched. This variable is rarely used, it's main use is for the [auto-help system](./Help-System.md#command-auto-help-system) (*Advanced note: the merged cmdset need NOT be the same as `BigGuy.cmdset`.  The merged set can be a combination of the cmdsets from other objects in the room, for example*).
- `raw_string` - this is the raw input coming from the user, without stripping any surrounding
whitespace. The only thing that is stripped is the ending newline marker.

#### Other useful utility methods:

- `.get_help(caller, cmdset)` - Get the help entry for this command. By default the arguments are not used, but they could be used to implement alternate help-display systems.
- `.client_width()` - Shortcut for getting the client's screen-width. Note that not all clients will
  truthfully report this value - that case the `settings.DEFAULT_SCREEN_WIDTH` will be returned. - `.styled_table(*args, **kwargs)` - This returns an [EvTable](module- evennia.utils.evtable) styled based on the session calling this command. The args/kwargs are the same as for EvTable, except styling defaults are set.
- `.styled_header`, `_footer`, `separator` - These will produce styled decorations for display to the user. They are useful for creating listings and forms with colors adjustable per-user.

### Defining your own command classes

Beyond the properties Evennia always assigns to the command at run-time (listed above), your job is to define the following class properties: 

- `key` (string) - the identifier for the command, like `look`.  This should (ideally) be unique. A key can consist of more than one word, like "press button" or "pull left lever". Note that *both* `key` and `aliases` below determine the identity of a command. So two commands are considered if either matches. This is important for merging cmdsets described below.
- `aliases` (optional list) - a list of alternate names for the command (`["glance", "see", "l"]`). Same name rules as for `key` applies.
- `locks` (string) - a [lock definition](./Locks.md), usually on the form `cmd:<lockfuncs>`. Locks is a rather big topic, so until you learn more about locks, stick to giving the lockstring `"cmd:all()"` to make the command available to everyone (if you don't provide a lock string, this will be assigned for you).
- `help_category` (optional string) - setting this helps to structure the auto-help into categories. If none is set, this will be set to *General*.
- `save_for_next` (optional boolean). This defaults to `False`. If `True`, a copy of this command object (along with any changes you have done to it) will be stored by the system and can be accessed by the next command by retrieving `self.caller.ndb.last_cmd`. The next run command will either clear or replace the storage.
- `arg_regex` (optional raw string): Used to force the parser to limit itself and tell it when the command-name ends and arguments begin (such as requiring this to be a space or a /switch). This is done with a regular expression. [See the arg_regex section](./Commands.md#arg_regex) for the details.
- `auto_help` (optional boolean). Defaults to `True`. This allows for turning off the [auto-help system](./Help-System.md#command-auto-help-system) on a per-command basis. This could be useful if you either want to write your help entries manually or hide the existence of a command from `help`'s generated list.
- `is_exit` (bool) - this marks the command as being used for an in-game exit. This is, by default, set by all Exit objects and you should not need to set it manually unless you make your own Exit system. It is used for optimization and allows the cmdhandler to easily disregard this command when the cmdset has its `no_exits` flag set.
- `is_channel` (bool)- this marks the command as being used for an in-game channel. This is, by default, set by all Channel objects and you should not need to set it manually unless you make your own Channel system.  is used for optimization and allows the cmdhandler to easily disregard this command when its cmdset has its `no_channels` flag set.
- `msg_all_sessions` (bool): This affects the behavior of the `Command.msg` method. If unset (default), calling `self.msg(text)` from the Command will always only send text to the Session that actually triggered this Command. If set however, `self.msg(text)` will send to all Sessions relevant to the object this Command sits on. Just which Sessions receives the text depends on the object and the server's `MULTISESSION_MODE`.

You should also implement at least two methods, `parse()` and `func()` (You could also implement
`perm()`, but that's not needed unless you want to fundamentally change how access checks work).

- `at_pre_cmd()` is called very first on the command. If this function returns anything that evaluates to `True` the command execution is aborted at this point.
- `parse()` is intended to parse the arguments (`self.args`) of the function. You can do this in any way you like, then store the result(s) in variable(s) on the command object itself (i.e. on `self`). To take an example, the default mux-like system uses this method to detect "command switches" and store them as a list in `self.switches`. Since the parsing is usually quite similar inside a command scheme you should make  `parse()` as generic as possible and then inherit from it rather than re- implementing it over and over. In this way, the default `MuxCommand` class implements a `parse()` for all child commands to use.
- `func()` is called right after `parse()` and should make use of the pre-parsed input to actually do whatever the command is supposed to do. This is the main body of the command. The return value from this method will be returned from the execution as a Twisted Deferred.
- `at_post_cmd()` is called after `func()` to handle eventual cleanup.

Finally, you should always make an informative [doc string](https://www.python.org/dev/peps/pep-0257/#what-is-a-docstring) (`__doc__`) at the top of your class. This string is dynamically read by the [Help System](./Help-System.md) to create the help entry for this command. You should decide on a way to format your help and stick to that.

Below is how you define a simple alternative "`smile`" command:

```python
from evennia import Command

class CmdSmile(Command):
    """
    A smile command

    Usage:
      smile [at] [<someone>]
      grin [at] [<someone>]

    Smiles to someone in your vicinity or to the room
    in general.

    (This initial string (the __doc__ string)
    is also used to auto-generate the help
    for this command)
    """

    key = "smile"
    aliases = ["smile at", "grin", "grin at"]
    locks = "cmd:all()"
    help_category = "General"

    def parse(self):
        "Very trivial parser"
        self.target = self.args.strip()

    def func(self):
        "This actually does things"
        caller = self.caller

        if not self.target or self.target == "here":
            string = f"{caller.key} smiles"
        else:
            target = caller.search(self.target)
            if not target:
                return
            string = f"{caller.key} smiles at {target.key}"

        caller.location.msg_contents(string)

```

The power of having commands as classes and to separate `parse()` and `func()` lies in the ability to inherit functionality without having to parse every command individually. For example, as mentioned the default commands all inherit from `MuxCommand`. `MuxCommand` implements its own version of `parse()` that understands all the specifics of MUX-like commands. Almost none of the default commands thus need to implement `parse()` at all, but can assume the incoming string is already split up and parsed in suitable ways by its parent. 

Before you can actually use the command in your game, you must now store it within a *command set*. See the [Command Sets](./Command-Sets.md) page.

### Command prefixes 

Historically, many MU* servers used to use prefix, such as `@` or `&` to signify that  a command is used for administration or requires staff privileges. The problem with this is that  newcomers to MU often find such extra symbols confusing. Evennia allows commands that can be  accessed both with- or without such a prefix.

    CMD_IGNORE_PREFIXES = "@&/+`

This is a setting consisting of a string of characters. Each is a prefix that will be considered a skippable prefix - _if the command is still unique in its cmdset when skipping the prefix_.

So if you wanted to write `@look` instead of `look` you can do so - the `@` will be ignored. But If  we added an actual `@look` command (with a `key` or alias `@look`) then we would need to use the  `@` to separate between the two. 

This is also used in the default commands. For example, `@open` is a building  command that allows you to create new exits to link two rooms together. Its `key` is set to `@open`,  including the `@` (no alias is set). By default you can use both `@open` and `open` for  this command. But "open" is a pretty common word and let's say a developer adds a new `open` command for opening a door. Now `@open` and `open` are two different commands and the `@` must be used to separate them.

> The `help` command will prefer to show all command names without prefix if
> possible. Only if there is a collision, will the prefix be shown in the help system.

### arg_regex

The command parser is very general and does not require a space to end your command name. This means that the alias `:` to `emote` can be used like `:smiles` without modification. It also means `getstone` will get you the stone (unless there is a command specifically named `getstone`, then that will be used). If you want to tell the parser to require a certain separator between the command name and its arguments (so that `get stone` works but `getstone` gives you a 'command not found' error) you can do so with the `arg_regex` property.

The `arg_regex` is a [raw regular expression string](https://docs.python.org/library/re.html). The regex will be compiled by the system at runtime. This allows you to customize how the part *immediately following* the command name (or alias) must look in order for the parser to match for this command. Some examples:

- `commandname argument` (`arg_regex = r"\s.+"`): This forces the parser to require the command name to be followed by one or more spaces. Whatever is entered after the space will be treated as an argument. However, if you'd forget the space (like a command having no arguments), this would *not* match `commandname`.
- `commandname` or `commandname argument` (`arg_regex = r"\s.+|$"`): This makes both `look` and `look me` work but `lookme` will not.
- `commandname/switches arguments` (`arg_regex = r"(?:^(?:\s+|\/).*$)|^$"`. If you are using Evennia's `MuxCommand` Command parent, you may wish to use this since it will allow `/switche`s to work as well as having or not having a space.

The `arg_regex` allows you to customize the behavior of your commands. You can put it in the parent class of your command to customize all children of your Commands. However, you can also change the base default behavior for all Commands by modifying `settings.COMMAND_DEFAULT_ARG_REGEX`. 

## Exiting a command

Normally you just use `return` in one of your Command class' hook methods to exit that method. That will however still fire the other hook methods of the Command in sequence. That's usually what you want but sometimes it may be useful to just abort the command, for example if you find some unacceptable input in your parse method. To exit the command this way you can raise `evennia.InterruptCommand`:

```python
from evennia import InterruptCommand

class MyCommand(Command):

   # ...

   def parse(self):
       # ...
       # if this fires, `func()` and `at_post_cmd` will not
       # be called at all
       raise InterruptCommand()

```

## Pauses in commands

Sometimes you want to pause the execution of your command for a little while before continuing - maybe you want to simulate a heavy swing taking some time to finish, maybe you want the echo of your voice to return to you with an ever-longer delay. Since Evennia is running asynchronously, you cannot use `time.sleep()` in your commands (or anywhere, really).  If you do, the *entire game* will
be frozen for everyone! So don't do that. Fortunately, Evennia offers a really quick syntax for
making pauses in commands.

In your `func()` method, you can use the `yield` keyword.  This is a Python keyword that will freeze
the current execution of your command and wait for more before processing.

> Note that you *cannot* just drop `yield` into any code and expect it to pause. Evennia will only pause for you if you `yield` inside the Command's `func()` method. Don't expect it to work anywhere else.

Here's an example of a command using a small pause of five seconds between messages:

```python
from evennia import Command

class CmdWait(Command):
    """
    A dummy command to show how to wait

    Usage:
      wait

    """

    key = "wait"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        """Command execution."""
        self.msg("Beginner-Tutorial to wait ...")
        yield 5
        self.msg("... This shows after 5 seconds. Waiting ...")
        yield 2
        self.msg("... And now another 2 seconds have passed.")
```

The important line is the `yield 5` and `yield 2` lines. It will tell Evennia to pause execution here and not continue until the number of seconds given has passed.

There are two things to remember when using `yield` in your Command's `func` method:

1. The paused state produced by the `yield` is not saved anywhere. So if the server reloads in the middle of your command pausing, it will *not* resume when the server comes back up - the remainder of the command will never fire. So be careful that you are not freezing the character or account in a way that will not be cleared on reload.
2. If you use `yield` you may not also use `return <values>` in your `func` method. You'll get an error explaining this. This is due to how Python generators work. You can however use a "naked" `return` just fine. Usually there is no need for `func` to return a value, but if you ever do need to mix `yield` with a final return value in the same `func`, look at [twisted.internet.defer.returnValue](https://twistedmatrix.com/documents/current/api/twisted.internet.defer.html#returnValue).

## Asking for user input

The `yield` keyword can also be used to ask for user input.  Again you can't use Python's `input` in your command, for it would freeze Evennia for everyone while waiting for that user to input their text. Inside a Command's `func` method, the following syntax can also be used:

```python
answer = yield("Your question")
```

Here's a very simple example:

```python
class CmdConfirm(Command):

    """
    A dummy command to show confirmation.

    Usage:
        confirm

    """

    key = "confirm"

    def func(self):
        answer = yield("Are you sure you want to go on?")
        if answer.strip().lower() in ("yes", "y"):
            self.msg("Yes!")
        else:
            self.msg("No!")
```

This time, when the user enters the 'confirm' command, she will be asked if she wants to go on. Entering 'yes' or "y" (regardless of case) will give the first reply, otherwise the second reply will show. 

> Note again that the `yield` keyword does not store state.  If the game reloads while waiting for the user to answer, the user will have to start over. It is not a good idea to use `yield` for important or complex choices, a persistent [EvMenu](./EvMenu.md) might be more appropriate in this case. 

## System commands

*Note: This is an advanced topic. Skip it if this is your first time learning about commands.*

There are several command-situations that are exceptional in the eyes of the server. What happens if the account enters an empty string? What if the 'command' given is infact the name of a channel the user wants to send a message to? Or if there are multiple command possibilities? 

Such 'special cases' are handled by what's called  *system commands*.  A system command is defined in the same way as other commands, except that their name (key) must be set to one reserved by the engine (the names are defined at the top of `evennia/commands/cmdhandler.py`). You can find (unused) implementations of the system commands in `evennia/commands/default/system_commands.py`. Since these are not (by default) included in any `CmdSet` they are not actually used, they are just there for show. When the special situation occurs, Evennia will look through all valid `CmdSet`s for your custom system command. Only after that will it resort to its own, hard-coded implementation.

Here are the exceptional situations that triggers system commands. You can find the command keys they use as properties on `evennia.syscmdkeys`:

- No input (`syscmdkeys.CMD_NOINPUT`) - the account just pressed return without any input. Default is to do nothing, but it can be useful to do something here for certain implementations such as line editors that interpret non-commands as text input (an empty line in the editing buffer).
- Command not found (`syscmdkeys.CMD_NOMATCH`) - No matching command was found. Default is to display the "Huh?" error message.
- Several matching commands where found (`syscmdkeys.CMD_MULTIMATCH`) - Default is to show a list of matches.
- User is not allowed to execute the command (`syscmdkeys.CMD_NOPERM`) - Default is to display the "Huh?" error message.
- Channel (`syscmdkeys.CMD_CHANNEL`) - This is a [Channel](./Channels.md) name of a channel you are subscribing to - Default is to relay the command's argument to that channel. Such commands are created by the Comm system on the fly depending on your subscriptions.
- New session connection (`syscmdkeys.CMD_LOGINSTART`). This command name should be put in the `settings.CMDSET_UNLOGGEDIN`. Whenever a new connection is established, this command is always called on the server (default is to show the login screen).

Below is an example of redefining what happens when the account doesn't provide any input (e.g. just presses return). Of course the new system command must be added to a cmdset as well before it will work.

```python
    from evennia import syscmdkeys, Command

    class MyNoInputCommand(Command):
        "Usage: Just press return, I dare you"
        key = syscmdkeys.CMD_NOINPUT
        def func(self):
            self.caller.msg("Don't just press return like that, talk to me!")
```

## Dynamic Commands

*Note: This is an advanced topic.*

Normally Commands are created as fixed classes and used without modification. There are however situations when the exact key, alias or other properties is not possible (or impractical) to pre- code. 

To create a command with a dynamic call signature, first define the command body normally in a class (set your `key`, `aliases` to default values), then use the following call (assuming the command class you created is named `MyCommand`):

```python
     cmd = MyCommand(key="newname",
                     aliases=["test", "test2"],
                     locks="cmd:all()",
                     ...)
```

*All* keyword arguments you give to the Command constructor will be stored as a property on the command object. This will overload existing properties defined on the parent class.

Normally you would define your class and only overload things like `key` and `aliases` at run-time. But you could in principle also send method objects (like `func`) as keyword arguments in order to make your command completely customized at run-time. 

### Dynamic commands - Exits

Exits are examples of the use of a [Dynamic Command](./Commands.md#dynamic-commands).

The functionality of [Exit](./Objects.md) objects in Evennia is not hard-coded in the engine. Instead Exits are normal [typeclassed](./Typeclasses.md) objects that auto-create a [CmdSet](./Command-Sets.md) on themselves when they load. This cmdset has a single dynamically created Command with the same properties (key, aliases and locks) as the Exit object itself. When entering the name of the exit, this dynamic exit-command is triggered and (after access checks) moves the Character to the exit's destination.

Whereas you could customize the Exit object and its command to achieve completely different behaviour, you will usually be fine just using the appropriate `traverse_*` hooks on the Exit object. But if you are interested in really changing how things work under the hood, check out `evennia/objects/objects.py` for how the `Exit` typeclass is set up. 

## Command instances are re-used

*Note: This is an advanced topic that can be skipped when first learning about Commands.*

A Command class sitting on an object is instantiated once and then re-used. So if you run a command from object1 over and over you are in fact running the same command instance over and over (if you run the same command but sitting on object2 however, it will be a different instance). This is usually not something you'll notice, since every time the Command-instance is used, all the relevant properties on it will be overwritten. But armed with this knowledge you can implement some of the more exotic command mechanism out there, like the command having a 'memory' of what you last entered so that you can back-reference the previous arguments etc.

> Note: On a server reload, all Commands are rebuilt and memory is flushed.

To show this in practice, consider this command:

```python
class CmdTestID(Command):
    key = "testid"

    def func(self):

        if not hasattr(self, "xval"):
            self.xval = 0
        self.xval += 1

        self.caller.msg(f"Command memory ID: {id(self)} (xval={self.xval})")

```

Adding this to the default character cmdset gives a result like this in-game:

```
> testid
Command memory ID: 140313967648552 (xval=1)
> testid
Command memory ID: 140313967648552 (xval=2)
> testid
Command memory ID: 140313967648552 (xval=3)
```

Note how the in-memory address of the `testid` command never changes, but `xval` keeps ticking up. 

## Create a command on the fly

*This is also an advanced topic.*

Commands can also be created and added to a cmdset on the fly. Creating a class instance with a keyword argument, will assign that keyword argument as a property on this paricular command:

```
class MyCmdSet(CmdSet):

    def at_cmdset_creation(self):

        self.add(MyCommand(myvar=1, foo="test")

```

This will start the `MyCommand` with `myvar` and `foo` set as properties (accessable as `self.myvar` and `self.foo`). How they are used is up to the Command. Remember however the discussion from the previous section - since the Command instance is re-used, those properties will *remain* on the command as long as this cmdset and the object it sits is in memory (i.e. until the next reload). Unless `myvar` and `foo` are somehow reset when the command runs, they can be modified and that change will be remembered for subsequent uses of the command. 

## How commands actually work

*Note: This is an advanced topic mainly of interest to server developers.*

Any time the user sends text to Evennia, the server tries to figure out if the text entered
corresponds to a known command. This is how the command handler sequence looks for a logged-in user:

1. A user enters a string of text and presses enter.
2. The user's Session determines the text is not some protocol-specific control sequence or OOB command, but sends it on to the command handler.
3. Evennia's *command handler*  analyzes the Session and grabs eventual references to Account and eventual puppeted Characters (these will be stored on the command object later). The *caller* property is set appropriately.
4. If input is an empty string, resend command as `CMD_NOINPUT`. If no such command is found in cmdset, ignore.
5. If command.key matches `settings.IDLE_COMMAND`, update timers but don't do anything more.
6. The command handler gathers the CmdSets available to *caller* at this time:
    - The caller's own currently active CmdSet.
    - CmdSets defined on the current account, if caller is a puppeted object.
    - CmdSets defined on the Session itself.
    - The active CmdSets of eventual objects in the same location (if any). This includes commands on [Exits](./Objects.md#exits).
    - Sets of dynamically created *System commands* representing available [Communications](./Channels.md)
7. All CmdSets *of the same priority* are merged together in groups.  Grouping avoids order- dependent issues of merging multiple same-prio sets onto lower ones.
8. All the grouped CmdSets are *merged* in reverse priority into one combined CmdSet according to each set's merge rules.
9. Evennia's *command parser* takes the merged cmdset and matches each of its commands (using its key and aliases) against the beginning of the string entered by *caller*. This produces a set of candidates.
10. The *cmd parser* next rates the matches by how many characters they have and how many percent matches the respective known command. Only if candidates cannot be separated will it return multiple matches.
    - If multiple matches were returned, resend as `CMD_MULTIMATCH`. If no such command is found in cmdset, return hard-coded list of matches.
    - If no match was found, resend as `CMD_NOMATCH`. If no such command is found in cmdset, give hard-coded error message.
11. If a single command was found by the parser, the correct command object is plucked out of storage. This usually doesn't mean a re-initialization.
12. It is checked that the caller actually has access to the command by validating the *lockstring* of the command. If not, it is not considered as a suitable match and `CMD_NOMATCH` is triggered.
13. If the new command is tagged as a channel-command, resend as `CMD_CHANNEL`. If no such command is found in cmdset, use hard-coded implementation.
14. Assign several useful variables to the command instance (see previous sections).
15. Call `at_pre_command()` on the command instance.
16. Call `parse()` on the command instance. This is fed the remainder of the string, after the name of the command. It's intended to pre-parse the string into a form useful for the `func()` method.
17. Call `func()` on the command instance. This is the functional body of the command, actually doing useful things.
18. Call `at_post_command()` on the command instance.

## Assorted notes

The return value of `Command.func()` is a Twisted [deferred](https://twistedmatrix.com/documents/current/core/howto/defer.html).
Evennia does not use this return value at all by default. If you do, you must
thus do so asynchronously, using callbacks.

```python
     # in command class func()
     def callback(ret, caller):
        caller.msg(f"Returned is {ret}")
     deferred = self.execute_command("longrunning")
     deferred.addCallback(callback, self.caller)
```

This is probably not relevant to any but the most advanced/exotic designs (one might use it to create a "nested" command structure for example).

The `save_for_next` class variable can be used to implement state-persistent commands. For example it can make a command operate on "it", where it is determined by what the previous command operated on.
