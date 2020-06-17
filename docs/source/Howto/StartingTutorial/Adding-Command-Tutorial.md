# Adding Command Tutorial

This is a quick first-time tutorial expanding on the [Commands](Commands) documentation. 

Let's assume you have just downloaded Evennia, installed it and created your game folder (let's call
it just `mygame` here). Now you want to try to add a new command. This is the fastest way to do it.

## Step 1: Creating a custom command

1. Open `mygame/commands/command.py` in a text editor. This is just one place commands could be
placed but you get it setup from the onset as an easy place to start. It also already contains some
example code.
1. Create a new class in `command.py` inheriting from `default_cmds.MuxCommand`. Let's call it
   `CmdEcho` in this example.
1. Set the class variable `key` to a good command name, like  `echo`.
1. Give your class a useful _docstring_. A docstring is the string at the very top of a class or
function/method. The docstring at the top of the command class is read by Evennia to become the help
entry for the Command (see
   [Command Auto-help](Help-System#command-auto-help-system)).
1. Define a class method `func(self)` that echoes your input back to you. 

Below is an example how this all could look for the echo command:

```python
        # file mygame/commands/command.py
        #[...]
        from evennia import default_cmds
        class CmdEcho(default_cmds.MuxCommand):
            """
            Simple command example
    
            Usage: 
              echo [text]
    
            This command simply echoes text back to the caller.
            """
    
            key = "echo"
    
            def func(self):
                "This actually does things" 
                if not self.args:
                    self.caller.msg("You didn't enter anything!")           
                else:
                    self.caller.msg("You gave the string: '%s'" % self.args)
```

## Step 2: Adding the Command to a default Cmdset

The command is not available to use until it is part of a [Command Set](Command-Sets). In this
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

See [Commands](Commands) for many more details and possibilities when defining Commands and using
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
custom [Typeclasses](Typeclasses)' `at_object_creation` method: 

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

See `evennia/settings_default.py` for the other settings. 