# Default Exit Errors


Evennia allows for exits to have any name. The command "kitchen" is a valid exit name as well as
"jump out the window" or "north". An exit actually consists of two parts: an [Exit Object](../Component/Objects)
and an [Exit Command](../Component/Commands) stored on said exit object. The command has the same key and aliases
as the object, which is why you can see the exit in the room and just write its name to traverse it.

If you try to enter the name of a non-existing exit, it is thus the same as trying a non-exising
command; Evennia doesn't care about the difference:

     > jump out the window
     Command 'jump out the window' is not available. Type "help" for help.

Many games don't need this type of freedom however. They define only the cardinal directions as
valid exit names (Evennia's `@tunnel` command also offers this functionality). In this case, the
error starts to look less logical:

     > west
     Command 'west' is not available. Maybe you meant "@set" or "@reset"?

Since we for our particular game *know* that west is an exit direction, it would be better if the
error message just told us that we couldn't go there.

## Adding default error commands

To solve this you need to be aware of how to [write and add new commands](Starting/Part1/Adding-Commands).
What you need to do is to create new commands for all directions you want to support in your game.
In this example all we'll do is echo an error message, but you could certainly consider more
advanced uses. You add these commands to the default command set. Here is an example of such a set
of commands:

```python
# for example in a file mygame/commands/movecommands.py

from evennia import default_cmds

class CmdExitError(default_cmds.MuxCommand):
    "Parent class for all exit-errors."        
    locks = "cmd:all()"
    arg_regex = r"\s|$"
    auto_help = False
    def func(self):
        "returns the error"
        self.caller.msg("You cannot move %s." % self.key)   

class CmdExitErrorNorth(CmdExitError):
    key = "north"
    aliases = ["n"]

class CmdExitErrorEast(CmdExitError):
    key = "east"
    aliases = ["e"]

class CmdExitErrorSouth(CmdExitError):
    key = "south"
    aliases = ["s"]

class CmdExitErrorWest(CmdExitError):
    key = "west"
    aliases = ["w"]
```

Make sure to add the directional commands (not their parent) to the `CharacterCmdSet` class in
`mygame/commands/default_cmdsets.py`:

```python
# in mygame/commands/default_cmdsets.py

from commands import movecommands

# [...]
class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # [...]
    def at_cmdset_creation(self):
        # [...]
        self.add(movecommands.CmdExitErrorNorth())
        self.add(movecommands.CmdExitErrorEast()) 
        self.add(movecommands.CmdExitErrorSouth())
        self.add(movecommands.CmdExitErrorWest())
```

After a `@reload` these commands (assuming you don't get any errors - check your log) will be
loaded. What happens henceforth is that if you are in a room with an Exitobject (let's say it's
"north"), the proper Exit-command will overload your error command (also named "north"). But if you
enter an direction without having a matching exit for it, you will fallback to your default error
commands:

     > east
     You cannot move east.

Further expansions by the exit system (including manipulating the way the Exit command itself is
created) can be done by modifying the [Exit typeclass](../Component/Typeclasses) directly.

## Additional Comments

So why didn't we create a single error command above? Something like this: 

```python
     class CmdExitError(default_cmds.MuxCommand):
        "Handles all exit-errors."
        key = "error_cmd"
        aliases = ["north", "n", 
                   "east", "e",
                   "south", "s",
                   "west", "w"]
         #[...]
```
The anwer is that this would *not* work and understanding why is important in order to not be
confused when working with commands and command sets.

The reason it doesn't work is because Evennia's [command system](../Component/Commands) compares commands *both*
by `key` and by `aliases`.  If *either* of those match, the two commands are considered *identical*
as far as cmdset merging system is concerned.

So the above example would work fine as long as there were no Exits at all in the room. But what
happens when we enter a room with an exit "north"? The Exit's cmdset is merged onto the default one,
and since there is an alias match, the system determines our `CmdExitError` to be identical. It is
thus overloaded by the Exit command (which also correctly defaults to a higher priority). The result
is that you can go through the north exit normally but none of the error messages for the other
directions are available since the single error command was completely overloaded by the single
matching "north" exit-command.