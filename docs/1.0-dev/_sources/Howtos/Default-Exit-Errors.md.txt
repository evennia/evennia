# Default Exit Errors

Evennia allows for exits to have any name. The command "kitchen" is a valid exit name as well as "jump out the window"
or "north". An exit actually consists of two parts: an [Exit Object](../Components/Objects.md) and
an [Exit Command](../Components/Commands.md) stored on said exit object. The command has the same key and aliases as the
exit-object, which is why you can see the exit in the room and just write its name to traverse it.

So if you try to enter the name of a non-existing exit, Evennia treats is the same way as if you were trying to 
use a non-existing command:

     > jump out the window
     Command 'jump out the window' is not available. Type "help" for help.

Many games don't need this type of freedom however. They define only the cardinal directions as valid exit names (
Evennia's `tunnel` command also offers this functionality). In this case, the error starts to look less logical:

     > west
     Command 'west' is not available. Maybe you meant "set" or "reset"?

Since we for our particular game *know* that west is an exit direction, it would be better if the error message just
told us that we couldn't go there.
    
     > west 
     You cannot move west.


## Adding default error commands

The way to do this is to give Evennia an _alternative_ Command to use when no Exit-Command is found
in the room. See [Adding Commands](Beginner-Tutorial/Part1/Beginner-Tutorial-Adding-Commands.md) for more info about the 
process of adding new Commands to Evennia.

In this example all we'll do is echo an error message.

```python
# for example in a file mygame/commands/movecommands.py

from evennia import default_cmds, CmdSet

class CmdExitError(default_cmds.MuxCommand):
    """Parent class for all exit-errors."""
    locks = "cmd:all()"
    arg_regex = r"\s|$"
    auto_help = False
    def func(self):
        """Returns error based on key"""
        self.caller.msg(f"You cannot move {self.key}.")

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

# you could add each command on its own to the default cmdset,
# but putting them all in a cmdset here allows you to
# just add this and makes it easier to expand with more 
# exit-errors in the future

class MovementFailCmdSet(CmdSet):
    def at_cmdset_creation(self): 
        self.add(CmdExitErrorNorth())
        self.add(CmdExitErrorEast())
        self.add(CmdExitErrorWest())
        self.add(CmdExitErrorSouth()) 
```

We pack our commands in a new little cmdset; if we add this to our 
`CharacterCmdSet`, we can just add more errors to `MovementFailCmdSet` 
later without having to change code in two places.

```python
# in mygame/commands/default_cmdsets.py

from commands import movecommands

# [...]
class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # [...]
    def at_cmdset_creation(self):
        # [...]
        # this adds all the commands at once
        self.add(movecommands.MovementFailCmdSet)
```

`reload` the server. What happens henceforth is that if you are in a room with an Exitobject (let's say it's "north"),
the proper Exit-command will _overload_ your error command (also named "north"). But if you enter a direction without
having a matching exit for it, you will fall back to your default error commands:

     > east
     You cannot move east.

Further expansions by the exit system (including manipulating the way the Exit command itself is created) can be done by
modifying the [Exit typeclass](../Components/Typeclasses.md) directly.

## Why not a single command?

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

The reason is that this would *not* work. Understanding why is important.

Evennia's [command system](../Components/Commands.md) compares commands by key and/or aliases. If _any_ key or alias
match, the two commands are considered _identical_. When the cmdsets merge, priority will then decide which of these
'identical' commandss replace which.

So the above example would work fine as long as there were _no Exits at all_ in the room. But when we enter
a room with an exit "north", its Exit-command (which has a higher priority) will override the single `CmdExitError`
with its alias 'north'. So the `CmdExitError` will be gone and while "north" will work, we'll again get the normal 
"Command not recognized" error for the other directions.