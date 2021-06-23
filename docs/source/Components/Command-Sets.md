# Command Sets


Command Sets are intimately linked with [Commands](./Commands) and you should be familiar with
Commands before reading this page. The two pages were split for ease of reading.

A *Command Set* (often referred to as a CmdSet or cmdset) is the basic unit for storing one or more
*Commands*. A given Command can go into any number of different command sets. Storing Command
classes in a command set is the way to make commands available to use in your game.

When storing a CmdSet on an object, you will make the commands in that command set available to the
object. An example is the default command set stored on new Characters. This command set contains
all the useful commands, from `look` and `inventory` to `@dig` and `@reload`
([permissions](./Locks#Permissions) then limit which players may use them, but that's a separate
topic).

When an account enters a command, cmdsets from the Account, Character, its location, and elsewhere
are pulled together into a *merge stack*. This stack is merged together in a specific order to
create a single "merged" cmdset, representing the pool of commands available at that very moment.

An example would be a `Window` object that has a cmdset with two commands in it: `look through
window` and `open window`. The command set would be visible to players in the room with the window,
allowing them to use those commands only there. You could imagine all sorts of clever uses of this,
like a `Television` object which had multiple commands for looking at it, switching channels and so
on. The tutorial world included with Evennia showcases a dark room that replaces certain critical
commands with its own versions because the Character cannot see.

If you want a quick start into defining your first commands and using them with command sets, you
can head over to the [Adding Command Tutorial](../Howto/Starting/Part1/Adding-Commands) which steps through things
without the explanations.

## Defining Command Sets

A CmdSet is, as most things in Evennia, defined as a Python class inheriting from the correct parent
(`evennia.CmdSet`, which is a shortcut to `evennia.commands.cmdset.CmdSet`). The CmdSet class only
needs to define one method, called `at_cmdset_creation()`. All other class parameters are optional,
but are used for more advanced set manipulation and coding (see the [merge rules](Command-
Sets#merge-rules) section).

```python
# file mygame/commands/mycmdset.py

from evennia import CmdSet

# this is a theoretical custom module with commands we 
# created previously: mygame/commands/mycommands.py
from commands import mycommands

class MyCmdSet(CmdSet):    
    def at_cmdset_creation(self):
        """
        The only thing this method should need
        to do is to add commands to the set.
        """ 
        self.add(mycommands.MyCommand1())
        self.add(mycommands.MyCommand2())
        self.add(mycommands.MyCommand3())
```

The CmdSet's `add()` method can also take another CmdSet as input. In this case all the commands
from that CmdSet will be appended to this one as if you added them line by line:

```python
    def at_cmdset_creation(): 
        ...
        self.add(AdditionalCmdSet) # adds all command from this set
        ...
```

If you added your command to an existing cmdset (like to the default cmdset), that set is already
loaded into memory. You need to make the server aware of the code changes:

```
@reload 
```

You should now be able to use the command. 

If you created a new, fresh cmdset, this must be added to an object in order to make the commands
within available. A simple way to temporarily test a cmdset on yourself is use the `@py` command to
execute a python snippet:

```python
@py self.cmdset.add('commands.mycmdset.MyCmdSet')
```

This will stay with you until you `@reset` or `@shutdown` the server, or you run

```python
@py self.cmdset.delete('commands.mycmdset.MyCmdSet')
```

In the example above, a specific Cmdset class is removed. Calling `delete` without arguments will
remove the latest added cmdset.

> Note: Command sets added using `cmdset.add` are, by default, *not* persistent in the database. 

If you want the cmdset to survive a reload, you can do: 

```
@py self.cmdset.add(commands.mycmdset.MyCmdSet, permanent=True)
```

Or you could add the cmdset as the *default* cmdset: 

```
@py self.cmdset.add_default(commands.mycmdset.MyCmdSet)
```

An object can only have one "default" cmdset (but can also have none). This is meant as a safe fall-
back even if all other cmdsets fail or are removed. It is always persistent and will not be affected
by `cmdset.delete()`. To remove a default cmdset you must explicitly call `cmdset.remove_default()`.

Command sets are often added to an object in its `at_object_creation` method. For more examples of
adding commands, read the [Step by step tutorial](../Howto/Starting/Part1/Adding-Commands). Generally you can
customize which command sets are added to your objects by using `self.cmdset.add()` or
`self.cmdset.add_default()`.

> Important: Commands are identified uniquely by key *or* alias (see [Commands](./Commands)). If any
overlap exists, two commands are considered identical. Adding a Command to a command set that
already has an identical command will *replace* the previous command. This is very important. You
must take this behavior into account when attempting to overload any default Evennia commands with
your own. Otherwise, you may accidentally "hide" your own command in your command set when adding a
new one that has a matching alias.

### Properties on Command Sets

There are several extra flags that you can set on CmdSets in order to modify how they work. All are
optional and will be set to defaults otherwise.  Since many of these relate to *merging* cmdsets,
you might want to read the [Adding and Merging Command Sets](./Command-Sets#adding-and-merging-
command-sets) section for some of these to make sense.

- `key` (string) - an identifier for the cmdset. This is optional, but should be unique. It is used
for display in lists, but also to identify special merging behaviours using the `key_mergetype`
dictionary below.
- `mergetype` (string) - allows for one of the following string values: "*Union*", "*Intersect*",
"*Replace*", or "*Remove*".
- `priority` (int) - This defines the merge order of the merge stack - cmdsets will merge in rising
order of priority with the highest priority set merging last. During a merger, the commands from the
set with the higher priority will have precedence (just what happens depends on the [merge
type](Command-Sets#adding-and-merging-command-sets)). If priority is identical, the order in the
merge stack determines preference. The priority value must be greater or equal to `-100`. Most in-
game sets should usually have priorities between `0` and `100`. Evennia default sets have priorities
as follows (these can be changed if you want a different distribution):
    - EmptySet: `-101` (should be lower than all other sets)
    - SessionCmdSet: `-20`
    - AccountCmdSet: `-10`
    - CharacterCmdSet: `0`
    - ExitCmdSet: ` 101` (generally should always be available)
    - ChannelCmdSet: `101` (should usually always be available) - since exits never accept
arguments, there is no collision between exits named the same as a channel even though the commands
"collide".
- `key_mergetype` (dict) - a dict of `key:mergetype` pairs. This allows this cmdset to merge
differently with certain named cmdsets. If the cmdset to merge with has a `key` matching an entry in
`key_mergetype`, it will not be merged according to the setting in `mergetype` but according to the
mode in this dict. Please note that this is more complex than it may seem due to the [merge
order](Command-Sets#adding-and-merging-command-sets) of command sets.  Please review that section
before using `key_mergetype`.
- `duplicates` (bool/None default `None`) - this determines what happens when merging same-priority
cmdsets containing same-key commands together. The`dupicate` option will *only* apply when merging
the cmdset with this option onto one other cmdset with the same priority. The resulting cmdset will
*not* retain this `duplicate` setting.
    - `None` (default): No duplicates are allowed and the cmdset being merged "onto" the old one
will take precedence. The result will be unique commands. *However*, the system will assume this
value to be `True` for cmdsets on Objects, to avoid dangerous clashes. This is usually the safe bet.
    - `False`: Like `None` except the system will not auto-assume any value for cmdsets defined on
Objects.
    - `True`: Same-named, same-prio commands will merge into the same cmdset.  This will lead to a
multimatch error (the user will get a list of possibilities in order to specify which command they
meant). This is is useful e.g. for on-object cmdsets (example: There is a `red button` and a `green
button` in the room. Both have a `press button` command, in cmdsets with the same priority. This
flag makes sure that just writing `press button` will force the Player to define just which object's
command was intended).
- `no_objs` this is a flag for the cmdhandler that builds the set of commands available at every
moment. It tells the handler not to include cmdsets from objects around the account (nor from rooms
or inventory) when building the merged set. Exit commands will still be included. This option can
have three values:
    - `None` (default): Passthrough of any value set explicitly earlier in the merge stack. If never
set explicitly, this acts as `False`.
    - `True`/`False`: Explicitly turn on/off. If two sets with explicit `no_objs` are merged,
priority determines what is used.
- `no_exits` - this is a flag for the cmdhandler that builds the set of commands available at every
moment. It tells the handler not to include cmdsets from exits. This flag can have three values:
    - `None` (default):  Passthrough of any value set explicitly earlier in the merge stack. If
never set explicitly, this acts as `False`.
    - `True`/`False`: Explicitly turn on/off. If two sets with explicit `no_exits` are merged,
priority determines what is used.
- `no_channels` (bool) - this is a flag for the cmdhandler that builds the set of commands available
at every moment. It tells the handler not to include cmdsets from available in-game channels. This
flag can have three values:
    - `None` (default):  Passthrough of any value set explicitly earlier in the merge stack. If
never set explicitly, this acts as `False`.
    - `True`/`False`: Explicitly turn on/off. If two sets with explicit `no_channels` are merged,
priority determines what is used.

## Command Sets Searched

When a user issues a command, it is matched against the [merged](./Command-Sets#adding-and-merging-
command-sets) command sets available to the player at the moment. Which those are may change at any
time (such as when the player walks into the room with the `Window` object described earlier).

The currently valid command sets are collected from the following sources:

- The cmdsets stored on the currently active [Session](./Sessions). Default is the empty
`SessionCmdSet` with merge priority `-20`.
- The cmdsets defined on the [Account](./Accounts). Default is the AccountCmdSet with merge priority
`-10`.
- All cmdsets on the Character/Object (assuming the Account is currently puppeting such a
Character/Object). Merge priority `0`.
- The cmdsets of all objects carried by the puppeted Character (checks the `call` lock). Will not be
included if `no_objs` option is active in the merge stack.
- The cmdsets of the Character's current location (checks the `call` lock). Will not be included if
`no_objs` option is active in the merge stack.
- The cmdsets of objects in the current location (checks the `call` lock). Will not be included if
`no_objs` option is active in the merge stack.
- The cmdsets of Exits in the location. Merge priority `+101`. Will not be included if `no_exits`
*or* `no_objs` option is active in the merge stack.
- The [channel](./Communications) cmdset containing commands for posting to all channels the account
or character is currently connected to. Merge priority `+101`. Will not be included if `no_channels`
option is active in the merge stack.

Note that an object does not *have* to share its commands with its surroundings. A Character's
cmdsets should not be shared for example, or all other Characters would get multi-match errors just
by being in the same room. The ability of an object to share its cmdsets is managed by its `call`
[lock](./Locks). For example, [Character objects](./Objects) defaults to `call:false()` so that any
cmdsets on them can only be accessed by themselves, not by other objects around them. Another
example might be to lock an object with `call:inside()` to only make their commands available to
objects inside them, or `cmd:holds()` to make their commands available only if they are held.

## Adding and Merging Command Sets

*Note: This is an advanced topic. It's very useful to know about, but you might want to skip it if
this is your first time learning about commands.*

CmdSets have the special ability that they can be *merged* together into new sets. Which of the
ingoing commands end up in the merged set is defined by the *merge rule* and the relative
*priorities* of the two sets.  Removing the latest added set will restore things back to the way it
was before the addition.

CmdSets are non-destructively stored in a stack inside the cmdset handler on the object. This stack
is parsed to create the "combined" cmdset active at the moment. CmdSets from other sources are also
included in the merger such as those on objects in the same room (like buttons to press) or those
introduced by state changes (such as when entering a menu). The cmdsets are all ordered after
priority and then merged together in *reverse order*. That is, the higher priority will be merged
"onto" lower-prio ones. By defining a cmdset with a merge-priority between that of two other sets,
you will make sure it will be merged in between them.
The very first cmdset in this stack is called the *Default cmdset* and is protected from accidental
deletion. Running `obj.cmdset.delete()` will never delete the default set. Instead one should add
new cmdsets on top of the default to "hide" it, as described below.  Use the special
`obj.cmdset.delete_default()` only if you really know what you are doing.

CmdSet merging is an advanced feature useful for implementing powerful game effects. Imagine for
example a player entering a dark room. You don't want the player to be able to find everything in
the room at a glance - maybe you even want them to have a hard time to find stuff in their backpack!
You can then define a different CmdSet with commands that override the normal ones. While they are
in the dark room, maybe the `look` and `inv` commands now just tell the player they cannot see
anything! Another example would be to offer special combat commands only when the player is in
combat. Or when being on a boat. Or when having taken the super power-up. All this can be done on
the fly by merging command sets.

### Merge Rules

Basic rule is that command sets are merged in *reverse priority order*. That is, lower-prio sets are
merged first and higher prio sets are merged "on top" of them. Think of it like a layered cake with
the highest priority on top.

To further understand how sets merge, we need to define some examples. Let's call the first command
set **A** and the second **B**. We assume **B** is the command set already active on our object and
we will merge **A** onto **B**. In code terms this would be done by `object.cdmset.add(A)`.
Remember, B is already active on `object` from before.

We let the **A** set have higher priority than **B**. A priority is simply an integer number. As
seen in the list above, Evennia's default cmdsets have priorities in the range `-101` to `120`. You
are usually safe to use a priority of `0` or `1` for most game effects.

In our examples, both sets contain a number of commands which we'll identify by numbers, like `A1,
A2` for set **A** and `B1, B2, B3, B4` for **B**. So for that example both sets contain commands
with the same keys (or aliases) "1" and "2" (this could for example be "look" and "get" in the real
game), whereas commands 3 and 4 are unique to **B**. To describe a merge between these sets, we
would write `A1,A2 + B1,B2,B3,B4 = ?` where `?` is a list of commands that depend on which merge
type **A** has, and which relative priorities the two sets have. By convention, we read this
statement as "New command set **A** is merged onto the old command set **B** to form **?**".

Below are the available merge types and how they work. Names are partly borrowed from [Set
theory](https://en.wikipedia.org/wiki/Set_theory).

- **Union** (default) - The two cmdsets are merged so that as many commands as possible from each
cmdset ends up in the merged cmdset. Same-key commands are merged by priority.

         # Union
         A1,A2 + B1,B2,B3,B4 = A1,A2,B3,B4 

- **Intersect** - Only commands found in *both* cmdsets (i.e. which have the same keys) end up in
the merged cmdset, with the higher-priority cmdset replacing the lower one's commands.

         # Intersect 
         A1,A3,A5 + B1,B2,B4,B5 = A1,A5

- **Replace** -   The commands of the higher-prio cmdset completely replaces the lower-priority
cmdset's commands, regardless of if same-key commands exist or not.

         # Replace
         A1,A3 + B1,B2,B4,B5 = A1,A3

- **Remove** - The high-priority command sets removes same-key commands from the lower-priority
cmdset. They are not replaced with anything, so this is a sort of filter that prunes the low-prio
set using the high-prio one as a template.

         # Remove
         A1,A3 + B1,B2,B3,B4,B5 = B2,B4,B5

Besides `priority` and `mergetype`, a command-set also takes a few other variables to control how
they merge:

- `duplicates` (bool) - determines what happens when two sets of equal priority merge. Default is
that the new set in the merger  (i.e.  **A** above) automatically takes precedence. But if
*duplicates* is true, the result will be a merger with more than one of each name match.  This will
usually lead to the player receiving a multiple-match error higher up the road, but can be good for
things like cmdsets on non-player objects in a room, to allow the system to warn that more than one
'ball' in the room has the same 'kick' command defined on it and offer a chance to  select which
ball to kick ...  Allowing duplicates only makes sense for *Union* and *Intersect*, the setting is
ignored for the other mergetypes.
- `key_mergetypes` (dict) - allows the cmdset to define a unique mergetype for particular cmdsets,
identified by their cmdset `key`.  Format is `{CmdSetkey:mergetype}`. Example:
`{'Myevilcmdset','Replace'}` which would make sure for this set to always use 'Replace' on the
cmdset with the key `Myevilcmdset` only, no matter what the main `mergetype` is set to.

> Warning: The `key_mergetypes` dictionary *can only work on the cmdset we merge onto*. When using
`key_mergetypes` it is thus important to consider the merge priorities - you must make sure that you
pick a priority *between* the cmdset you want to detect and the next higher one, if any. That is, if
we define a cmdset with a high priority and set it to affect a cmdset that is far down in the merge
stack, we would not "see" that set when it's time for us to merge. Example: Merge stack is
`A(prio=-10), B(prio=-5), C(prio=0), D(prio=5)`. We now merge a cmdset `E(prio=10)` onto this stack,
with a `key_mergetype={"B":"Replace"}`. But priorities dictate that we won't be merged onto B, we
will be merged onto E (which is a merger of the lower-prio sets at this point). Since we are merging
onto E and not B, our `key_mergetype` directive won't trigger. To make sure it works we must make
sure we merge onto B.  Setting E's priority to, say, -4 will make sure to merge it onto B and affect
it appropriately.

More advanced cmdset example: 

```python
from commands import mycommands

class MyCmdSet(CmdSet):
    
    key = "MyCmdSet"
    priority = 4
    mergetype = "Replace"
    key_mergetypes = {'MyOtherCmdSet':'Union'}  
    
    def at_cmdset_creation(self):
        """
        The only thing this method should need
        to do is to add commands to the set.
        """     
        self.add(mycommands.MyCommand1())
        self.add(mycommands.MyCommand2())
        self.add(mycommands.MyCommand3())
```

### Assorted Notes

It is very important to remember that two commands are compared *both* by their `key` properties
*and* by their `aliases` properties. If either keys or one of their aliases match, the two commands
are considered the *same*. So consider these two Commands:

 - A Command with key "kick" and alias "fight"
 - A Command with key "punch" also with an alias "fight"

During the cmdset merging (which happens all the time since also things like channel commands and
exits are merged in), these two commands will be considered *identical* since they share alias. It
means only one of them will remain after the merger. Each will also be compared with all other
commands having any combination of the keys and/or aliases "kick", "punch" or "fight".

... So avoid duplicate aliases, it will only cause confusion. 
