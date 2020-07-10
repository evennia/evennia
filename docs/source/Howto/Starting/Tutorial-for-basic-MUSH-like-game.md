# Tutorial for basic MUSH like game


This tutorial lets you code a small but complete and functioning MUSH-like game in Evennia. A
[MUSH](http://en.wikipedia.org/wiki/MUSH) is, for our purposes, a class of roleplay-centric games
focused on free form storytelling. Even if you are not interested in MUSH:es, this is still a good
first game-type to try since it's not so code heavy. You will be able to use the same principles for
building other types of games.

The tutorial starts from scratch. If you did the [First Steps Coding](./Starting-Part1) tutorial
already you should have some ideas about how to do some of the steps already.

The following are the (very simplistic and cut-down) features we will implement (this was taken from
a feature request from a MUSH user new to Evennia). A Character in this system should:

- Have a “Power” score from 1 to 10 that measures how strong they are (stand-in for the stat
system).
- Have a command (e.g. `+setpower 4`) that sets their power (stand-in for character generation
code).
- Have a command (e.g. `+attack`) that lets them roll their power and produce a "Combat Score"
between `1` and `10*Power`, displaying the result and editing their object to record this number
(stand-in for `+actions` in the command code).
- Have a command that displays everyone in the room and what their most recent "Combat Score" roll
was (stand-in for the combat code).
- Have a command (e.g. `+createNPC Jenkins`) that creates an NPC with full abilities.
- Have a command to control NPCs, such as `+npc/cmd (name)=(command)` (stand-in for the NPC
controlling code).

In this tutorial we will assume you are starting from an empty database without any previous
modifications.

## Server Settings

To emulate a MUSH, the default `MULTISESSION_MODE=0` is enough (one unique session per
account/character). This is the default so you don't need to change anything. You will still be able
to puppet/unpuppet objects you have permission to, but there is no character selection out of the
box in this mode.

We will assume our game folder is called `mygame` henceforth.  You should be fine with the default
SQLite3 database.

## Creating the Character

First thing is to choose how our Character class works. We don't need to define a special NPC object
-- an NPC is after all just a Character without an Account currently controlling them.

Make your changes in the `mygame/typeclasses/characters.py` file:

```python
# mygame/typeclasses/characters.py

from evennia import DefaultCharacter

class Character(DefaultCharacter):
    """
     [...]
    """
    def at_object_creation(self):
        "This is called when object is first created, only."   
        self.db.power = 1         
        self.db.combat_score = 1
```

We defined two new [Attributes](../../Component/Attributes) `power` and `combat_score` and set them to default
values. Make sure to `@reload` the server if you had it already running (you need to reload every
time you update your python code, don't worry, no accounts will be disconnected by the reload).

Note that only *new* characters will see your new Attributes (since the `at_object_creation` hook is
called when the object is first created, existing Characters won't have it).  To update yourself,
run

     @typeclass/force self

This resets your own typeclass (the `/force` switch is a safety measure to not do this
accidentally), this means that `at_object_creation` is re-run.

     examine self

Under the "Persistent attributes" heading you should now find the new Attributes `power` and `score`
set on yourself by `at_object_creation`. If you don't, first make sure you `@reload`ed into the new
code, next look at your server log (in the terminal/console) to see if there were any syntax errors
in your code that may have stopped your new code from loading correctly.

## Character Generation

We assume in this example that Accounts first connect into a "character generation area". Evennia
also supports full OOC menu-driven character generation, but for this example, a simple start room
is enough. When in this room (or rooms) we allow character generation commands. In fact, character
generation commands will *only* be available in such rooms.

Note that this again is made so as to be easy to expand to a full-fledged game. With our simple
example, we could simply set an `is_in_chargen` flag on the account and have the `+setpower` command
check it. Using this method however will make it easy to add more functionality later.

What we need are the following:

- One character generation [Command](../../Component/Commands) to set the "Power" on the `Character`.  
- A chargen [CmdSet](../../Component/Command-Sets) to hold this command. Lets call it `ChargenCmdset`.  
- A custom `ChargenRoom` type that makes this set of commands available to players in such rooms.  
- One such room to test things in.  

### The +setpower command

For this tutorial we will add all our new commands to `mygame/commands/command.py` but you could
split your commands into multiple module if you prefered.

For this tutorial character generation will only consist of one [Command](../../Component/Commands) to set the
Character s "power" stat. It will be called on the following MUSH-like form:

     +setpower 4

Open `command.py` file. It contains documented empty templates for the base command and the
"MuxCommand" type used by default in Evennia. We will use the plain `Command` type here, the
`MuxCommand` class offers some extra features like stripping whitespace that may be useful - if so,
just import from that instead.

Add the following to the end of the `command.py` file: 

```python
# end of command.py
from evennia import Command # just for clarity; already imported above

class CmdSetPower(Command):
    """
    set the power of a character

    Usage: 
      +setpower <1-10>

    This sets the power of the current character. This can only be 
    used during character generation.    
    """
    
    key = "+setpower"
    help_category = "mush"

    def func(self):
        "This performs the actual command"
        errmsg = "You must supply a number between 1 and 10."
        if not self.args:
            self.caller.msg(errmsg)      
            return
        try:
            power = int(self.args)  
        except ValueError:
            self.caller.msg(errmsg)
            return
        if not (1 <= power <= 10):
            self.caller.msg(errmsg)
            return
        # at this point the argument is tested as valid. Let's set it.
        self.caller.db.power = power
        self.caller.msg("Your Power was set to %i." % power)
```
This is a pretty straightforward command. We do some error checking, then set the power on ourself.
We use a `help_category` of "mush" for all our commands, just so they are easy to find and separate
in the help list.

Save the file. We will now add it to a new [CmdSet](../../Component/Command-Sets) so it can be accessed (in a full
chargen system you would of course have more than one command here).

Open `mygame/commands/default_cmdsets.py` and import your `command.py` module at the top. We also
import the default `CmdSet` class for the next step:

```python
from evennia import CmdSet
from commands import command
```

Next scroll down and define a new command set (based on the base `CmdSet` class we just imported at
the end of this file, to hold only our chargen-specific command(s):

```python
# end of default_cmdsets.py

class ChargenCmdset(CmdSet):
    """
    This cmdset it used in character generation areas.
    """
    key = "Chargen"
    def at_cmdset_creation(self):
        "This is called at initialization"
        self.add(command.CmdSetPower()) 
```

In the future you can add any number of commands to this cmdset, to expand your character generation
system as you desire. Now we need to actually put that cmdset on something so it's made available to
users.  We could put it directly on the Character, but that would make it available all the time.
It's cleaner to put it on a room, so it's only available when players are in that room.

### Chargen areas

We will create a simple Room typeclass to act as a template for all our Chargen areas. Edit
`mygame/typeclasses/rooms.py` next:

```python 
from commands.default_cmdsets import ChargenCmdset

# ... 
# down at the end of rooms.py

class ChargenRoom(Room):
    """
    This room class is used by character-generation rooms. It makes
    the ChargenCmdset available.
    """
    def at_object_creation(self):
        "this is called only at first creation"
        self.cmdset.add(ChargenCmdset, permanent=True)
```
Note how new rooms created with this typeclass will always start with `ChargenCmdset` on themselves.
Don't forget the `permanent=True` keyword or you will lose the cmdset after a server reload. For
more information about [Command Sets](../../Component/Command-Sets) and [Commands](../../Component/Commands), see the respective
links.

### Testing chargen

First, make sure you have `@reload`ed the server (or use `evennia reload` from the terminal) to have
your new python code added to the game. Check your terminal and fix any errors you see - the error
traceback lists exactly where the error is found - look line numbers in files you have changed.

We can't test things unless we have some chargen areas to test. Log into the game (you should at
this point be using the new, custom Character class). Let's dig a chargen area to test.

     @dig chargen:rooms.ChargenRoom = chargen,finish

If you read the help for `@dig` you will find that this will create a new room named `chargen`. The
part after the `:` is the python-path to the Typeclass you want to use. Since Evennia will
automatically try the `typeclasses` folder of our game directory, we just specify
`rooms.ChargenRoom`, meaning it will look inside the module `rooms.py` for a class named
`ChargenRoom` (which is what we created above). The names given after `=` are the names of exits to
and from the room from your current location. You could also append aliases to each one name, such
as `chargen;character generation`.

So in summary, this will create a new room of type ChargenRoom and open an exit `chargen` to it and
an exit back here named `finish`. If you see errors at this stage, you must fix them in your code.
`@reload`
between fixes. Don't continue until the creation seems to have worked okay. 

     chargen

This should bring you to the chargen room. Being in there you should now have the `+setpower`
command available, so test it out. When you leave (via the `finish` exit), the command will go away
and trying `+setpower` should now give you a command-not-found error. Use `ex me` (as a privileged
user) to check so the `Power` [Attribute](../../Component/Attributes) has been set correctly.

If things are not working, make sure your typeclasses and commands are free of bugs and that you
have entered the paths to the various command sets and commands correctly. Check the logs or command
line for tracebacks and errors.

## Combat System

We will add our combat command to the default command set, meaning it will be available to everyone
at all times. The combat system consists of a `+attack` command to get how successful our attack is.
We also change the default `look` command to display the current combat score.


### Attacking with the +attack command

Attacking in this simple system means rolling a random "combat score" influenced by the `power` stat
set during Character generation:

    > +attack
    You +attack with a combat score of 12!

Go back to `mygame/commands/command.py` and add the command to the end like this: 

```python    
import random

# ... 

class CmdAttack(Command):
    """
    issues an attack 

    Usage: 
        +attack 

    This will calculate a new combat score based on your Power.
    Your combat score is visible to everyone in the same location.
    """
    key = "+attack"
    help_category = "mush"

    def func(self):
        "Calculate the random score between 1-10*Power"
        caller = self.caller
        power = caller.db.power
        if not power:
            # this can happen if caller is not of 
            # our custom Character typeclass 
            power = 1
        combat_score = random.randint(1, 10 * power)
        caller.db.combat_score = combat_score

        # announce
        message = "%s +attack%s with a combat score of %s!"
        caller.msg(message % ("You", "", combat_score))
        caller.location.msg_contents(message % 
                                     (caller.key, "s", combat_score),
                                     exclude=caller)
```            

What we do here is simply to generate a "combat score" using Python's inbuilt `random.randint()`
function. We then store that and echo the result to everyone involved.

To make the `+attack` command available to you in game, go back to
`mygame/commands/default_cmdsets.py` and scroll down to the `CharacterCmdSet` class. At the correct
place add this line:

```python
self.add(command.CmdAttack())
```

`@reload` Evennia and the `+attack` command should be available to you. Run it and use e.g. `@ex` to
make sure the `combat_score` attribute is saved correctly.

### Have "look" show combat scores

Players should be able to view all current combat scores in the room.  We could do this by simply
adding a second command named something like `+combatscores`, but we will instead let the default
`look` command do the heavy lifting for us and display our scores as part of its normal output, like
this:

    >  look Tom
    Tom (combat score: 3)
    This is a great warrior.

We don't actually have to modify the `look` command itself however. To understand why, take a look
at how the default `look` is actually defined. It sits in `evennia/commands/default/general.py` (or
browse it online
[here](https://github.com/evennia/evennia/blob/master/evennia/commands/default/general.py#L44)).
You will find that the actual return text is done by the `look` command calling a *hook method*
named `return_appearance` on the object looked at. All the `look` does is to echo whatever this hook
returns.  So what we need to do is to edit our custom Character typeclass and overload its
`return_appearance` to return what we want (this is where the advantage of having a custom typeclass
comes into play for real).

Go back to your custom Character typeclass in `mygame/typeclasses/characters.py`. The default
implementation of `return appearance` is found in  `evennia.DefaultCharacter` (or online
[here](https://github.com/evennia/evennia/blob/master/evennia/objects/objects.py#L1438)).  If you
want to make bigger changes you could copy & paste the whole default thing into our overloading
method. In our case the change is small though:

```python
class Character(DefaultCharacter):
    """
     [...]
    """
    def at_object_creation(self):
        "This is called when object is first created, only."   
        self.db.power = 1         
        self.db.combat_score = 1

    def return_appearance(self, looker):
        """
        The return from this method is what
        looker sees when looking at this object.
        """
        text = super().return_appearance(looker)
        cscore = " (combat score: %s)" % self.db.combat_score
        if "\n" in text:
            # text is multi-line, add score after first line
            first_line, rest = text.split("\n", 1)
            text = first_line + cscore + "\n" + rest
        else:
            # text is only one line; add score to end
            text += cscore
        return text
```

What we do is to simply let the default `return_appearance` do its thing (`super` will call the
parent's version of the same method). We then split out the first line of this text, append our
`combat_score` and put it back together again.

`@reload` the server and you should be able to look at other Characters and see their current combat
scores.

> Note: A potentially more useful way to do this would be to overload the entire `return_appearance`
of the `Room`s of your mush and change how they list their contents; in that way one could see all
combat scores of all present Characters at the same time as looking at the room. We leave this as an
exercise.

## NPC system

Here we will re-use the Character class by introducing a command that can create NPC objects. We
should also be able to set its Power and order it around.

There are a few ways to define the NPC class. We could in theory create a custom typeclass for it
and put a custom NPC-specific cmdset on all NPCs. This cmdset could hold all manipulation commands.
Since we expect NPC manipulation to be a common occurrence among the user base however, we will
instead put all relevant NPC commands in the default command set and limit eventual access with
[Permissions and Locks](../../Component/Locks#Permissions).

### Creating an NPC with +createNPC

We need a command for creating the NPC, this is a very straightforward command: 

    > +createnpc Anna
    You created the NPC 'Anna'.  

At the end of `command.py`, create our new command:

```python
from evennia import create_object
    
class CmdCreateNPC(Command):
    """
    create a new npc

    Usage:
        +createNPC <name>

    Creates a new, named NPC. The NPC will start with a Power of 1.
    """ 
    key = "+createnpc"
    aliases = ["+createNPC"]
    locks = "call:not perm(nonpcs)"
    help_category = "mush" 
    
    def func(self):
        "creates the object and names it"
        caller = self.caller
        if not self.args:
            caller.msg("Usage: +createNPC <name>")
            return
        if not caller.location:
            # may not create npc when OOC
            caller.msg("You must have a location to create an npc.")
            return
        # make name always start with capital letter
        name = self.args.strip().capitalize()
        # create npc in caller's location
        npc = create_object("characters.Character", 
                      key=name, 
                      location=caller.location,
                      locks="edit:id(%i) and perm(Builders);call:false()" % caller.id)
        # announce 
        message = "%s created the NPC '%s'."
        caller.msg(message % ("You", name)) 
        caller.location.msg_contents(message % (caller.key, name), 
                                                exclude=caller)        
```
Here we define a `+createnpc` (`+createNPC` works too) that is callable by everyone *not* having the
`nonpcs` "[permission](../../Component/Locks#Permissions)" (in Evennia, a "permission" can just as well be used to
block access, it depends on the lock we define). We create the NPC object in the caller's current
location, using our custom `Character` typeclass to do so.

We set an extra lock condition on the NPC, which we will use to check who may edit the NPC later --
we allow the creator to do so, and anyone with the Builders permission (or higher). See
[Locks](../../Component/Locks) for more information about the lock system.

Note that we just give the object default permissions (by not specifying the `permissions` keyword
to the `create_object()` call).  In some games one might want to give the NPC the same permissions
as the Character creating them, this might be a security risk though.

Add this command to your default cmdset the same way you did the `+attack` command earlier.
`@reload` and it will be available to test.

### Editing the NPC with +editNPC

Since we re-used our custom character typeclass, our new NPC already has a *Power* value - it
defaults to 1. How do we change this?

There are a few ways we can do this. The easiest is to remember that the `power` attribute is just a
simple [Attribute](../../Component/Attributes) stored on the NPC object. So as a Builder or Admin we could set this
right away with the default `@set` command:

     @set mynpc/power = 6

The `@set` command is too generally powerful though, and thus only available to staff. We will add a
custom command that only changes the things we want players to be allowed to change. We could in
principle re-work our old `+setpower` command, but let's try something more useful. Let's make a
`+editNPC` command.

    > +editNPC Anna/power = 10
    Set Anna's property 'power' to 10. 

This is a slightly more complex command. It goes at the end of your `command.py` file as before. 

```python
class CmdEditNPC(Command):
    """
    edit an existing NPC

    Usage: 
      +editnpc <name>[/<attribute> [= value]]
     
    Examples:
      +editnpc mynpc/power = 5
      +editnpc mynpc/power    - displays power value
      +editnpc mynpc          - shows all editable 
                                attributes and values

    This command edits an existing NPC. You must have 
    permission to edit the NPC to use this.
    """
    key = "+editnpc"
    aliases = ["+editNPC"]
    locks = "cmd:not perm(nonpcs)"
    help_category = "mush" 

    def parse(self):
        "We need to do some parsing here"
        args = self.args
        propname, propval = None, None
        if "=" in args: 
            args, propval = [part.strip() for part in args.rsplit("=", 1)] 
        if "/" in args:
            args, propname = [part.strip() for part in args.rsplit("/", 1)]
        # store, so we can access it below in func()
        self.name = args
        self.propname = propname
        # a propval without a propname is meaningless
        self.propval = propval if propname else None

    def func(self):
        "do the editing"

        allowed_propnames = ("power", "attribute1", "attribute2")
 
        caller = self.caller
        if not self.args or not self.name:
            caller.msg("Usage: +editnpc name[/propname][=propval]") 
            return
        npc = caller.search(self.name)
        if not npc:
            return
        if not npc.access(caller, "edit"):
            caller.msg("You cannot change this NPC.")
            return 
        if not self.propname:
            # this means we just list the values
            output = "Properties of %s:" % npc.key
            for propname in allowed_propnames: 
                propvalue = npc.attributes.get(propname, default="N/A")
                output += "\n %s = %s" % (propname, propvalue)
            caller.msg(output)
        elif self.propname not in allowed_propnames: 
            caller.msg("You may only change %s." % 
                              ", ".join(allowed_propnames))
        elif self.propval:
            # assigning a new propvalue
            # in this example, the properties are all integers...
            intpropval = int(self.propval)  
            npc.attributes.add(self.propname, intpropval) 
            caller.msg("Set %s's property '%s' to %s" %
                         (npc.key, self.propname, self.propval))
        else:
            # propname set, but not propval - show current value
            caller.msg("%s has property %s = %s" % 
                         (npc.key, self.propname, 
                          npc.attributes.get(self.propname, default="N/A")))
```

This command example shows off the use of more advanced parsing but otherwise it's mostly error
checking. It searches for the given npc in the same room, and checks so the caller actually has
permission to "edit" it before continuing. An account without the proper permission won't even be
able to view the properties on the given NPC. It's up to each game if this is the way it should be.

Add this to the default command set like before and you should be able to try it out. 

_Note: If you wanted a player to use this command to change an on-object property like the NPC's
name (the `key` property), you'd need to modify the command since "key" is not an Attribute (it is
not retrievable via `npc.attributes.get` but directly via `npc.key`). We leave this as an optional
exercise._

### Making the NPC do stuff - the +npc command

Finally, we will make a command to order our NPC around. For now, we will limit this command to only
be usable by those having the "edit" permission on the NPC. This can be changed if it's possible for
anyone to use the NPC.

The NPC, since it inherited our Character typeclass has access to most commands a player does. What
it doesn't have access to are Session and Player-based cmdsets (which means, among other things that
they cannot chat on channels, but they could do that if you just added those commands). This makes
the `+npc` command simple:

    +npc Anna = say Hello!
    Anna says, 'Hello!'

Again, add to the end of your `command.py` module:

```python
class CmdNPC(Command):
    """
    controls an NPC

    Usage: 
        +npc <name> = <command>

    This causes the npc to perform a command as itself. It will do so
    with its own permissions and accesses. 
    """
    key = "+npc"
    locks = "call:not perm(nonpcs)"
    help_category = "mush"

    def parse(self):
        "Simple split of the = sign"
        name, cmdname = None, None
        if "=" in self.args:
            name, cmdname = [part.strip() 
                             for part in self.args.rsplit("=", 1)]
        self.name, self.cmdname = name, cmdname

    def func(self):
        "Run the command"
        caller = self.caller
        if not self.cmdname:
            caller.msg("Usage: +npc <name> = <command>")
            return
        npc = caller.search(self.name)   
        if not npc:
            return
        if not npc.access(caller, "edit"):
            caller.msg("You may not order this NPC to do anything.")
            return
        # send the command order
        npc.execute_cmd(self.cmdname)
        caller.msg("You told %s to do '%s'." % (npc.key, self.cmdname))
```

Note that if you give an erroneous command, you will not see any error message, since that error
will be returned to the npc object, not to you. If you want players to see this, you can give the
caller's session ID to the `execute_cmd` call, like this:

```python
npc.execute_cmd(self.cmdname, sessid=self.caller.sessid)
```

Another thing to remember is however that this is a very simplistic way to control NPCs. Evennia
supports full puppeting very easily. An Account (assuming the "puppet" permission was set correctly)
could simply do `@ic mynpc` and be able to play the game "as" that NPC. This is in fact just what
happens when an Account takes control of their normal Character as well.

## Concluding remarks

This ends the tutorial. It looks like a lot of text but the amount of code you have to write is
actually relatively short. At this point you should have a basic skeleton of a game and a feel for
what is involved in coding your game.

From here on you could build a few more ChargenRooms and link that to a bigger grid. The `+setpower`
command can either be built upon or accompanied by many more to get a more elaborate character
generation.

The simple "Power" game mechanic should be easily expandable to something more full-fledged and
useful, same is true for the combat score principle. The `+attack` could be made to target a
specific player (or npc) and automatically compare their relevant attributes to determine a result.

To continue from here, you can take a look at the [Tutorial World](Part1/Tutorial-World-Introduction). For
more specific ideas, see the [other tutorials and hints](../Howto-Overview) as well
as the [Evennia Component overview](../../Component/Component-Overview).