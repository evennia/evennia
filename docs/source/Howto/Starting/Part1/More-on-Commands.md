# More about Commands

[prev lesson](Adding-Commands) | [next lesson](Creating-Things)

In this lesson we learn some basics about parsing the input of Commands. We will 
also learn how to add, modify and extend Evennia's default commands. 

## More advanced parsing 

In the last lesson we made a `hit` Command and hit a dragon with it. You should have the code 
from that still around. 

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


## Adding a Command to an object 

The commands of a cmdset attached to an object with `obj.cmdset.add()` will by default be made available to that object
but _also to those in the same location as that object_. If you did the [Building introduction](Building-Quickstart)
you've seen an example of this with the "Red Button" object. The [Tutorial world](Tutorial-World-Introduction) 
also has many examples of objects with commands on them. 

To show how this could work, let's put our 'hit' Command on our simple `sword` object from the previous section.

    > self.search("sword").cmdset.add("commands.mycommands.MyCmdSet", permanent=True)

We find the sword (it's still in our inventory so `self.search` should be able to find it), then 
add `MyCmdSet` to it. This actually adds both `hit` and `echo` to the sword, which is fine. 

Let's try to swing it!

    > hit 
    More than one match for 'hit' (please narrow target):
    hit-1 (sword #11)
    hit-2

```sidebar:: Multi-matches
    
    Some game engines will just pick the first hit when finding more than one.
    Evennia will always give you a choice. The reason for this is that Evennia
    cannot know if `hit` and `hit` are different or the same - maybe it behaves
    differently depending on the object it sits on? Besides, imagine if you had 
    a red and a blue button both with the command `push` on it. Now you just write
    `push`. Wouldn't you prefer to be asked `which` button you really wanted to push?
```
Woah, that didn't go as planned. Evennia actually found _two_ `hit` commands to didn't know which one to use 
(_we_ know they are the same, but Evennia can't be sure of that). As we can see, `hit-1` is the one found on 
the sword. The other one is from adding `MyCmdSet` to ourself earlier. It's easy enough to tell Evennia which 
one you meant: 

    > hit-1 
    Who do you want to hit?
    > hit-2
    Who do you want to hit? 
    
In this case we don't need both command-sets, so let's just keep the one on the sword: 

    > self.cmdset.remove("commands.mycommands.MyCmdSet")
    > hit
    Who do you want to hit?

Now try this: 

    > tunnel n = kitchen
    > n 
    > drop sword 
    > s
    > hit
    Command 'hit' is not available. Maybe you meant ...
    > n
    > hit  
    Who do you want to hit? 
    
The `hit` command is now only available if you hold or are in the same room as the sword. 

### You need to hold the sword!

Let's get a little ahead of ourselves and make it so you have to _hold_ the sword for the `hit` command to 
be available. This involves a _Lock_. We've cover locks in more detail later, just know that they are useful
for limiting the kind of things you can do with an object, including limiting just when you can call commands on
it. 
```sidebar:: Locks

    Evennia Locks are defined as a mini-language defined in `lockstrings`. The lockstring
    is on a form `<situation>:<lockfuncs>`, where `situation` determines when this
    lock applies and the `lockfuncs` (there can be more than one) are run to determine
    if the lock-check passes or not depending on circumstance.
```

    > py self.search("sword").locks.add("call:holds()")
    
We added a new lock to the sword. The _lockstring_ `"call:holds()"` means that you can only _call_ commands on 
this object if you are _holding_ the object (that is, it's in your inventory). 

For locks to work, you cannot be _superuser_, since the superuser passes all locks. You need to `quell` yourself
first: 
```sidebar:: quell/unquell

    Quelling allows you as a developer to take on the role of players with less
    priveleges. This is useful for testing and debugging, in particular since a 
    superuser has a little `too` much power sometimes.
    Use `unquell` to get back to your normal self.
```

    > quell
    
If the sword lies on the ground, try

    > hit
    Command 'hit' is not available. ..
    > get sword 
    > hit 
    > Who do you want to hit?


Finally, we get rid of ours sword so we have a clean slate with no more `hit` commands floating around.
We can do that in two ways:

    delete sword 
    
or 

    py self.search("sword").delete() 


## Adding the Command to a default Cmdset


As we have seen we can use `obj.cmdset.add()` to add a new cmdset to objects, whether that object 
is ourself (`self`) or other objects like the `sword`. 

This is how all commands in Evennia work, including default commands like `look`, `dig`, `inventory` and so on. 
All these commands are in just loaded on the default objects that Evennia provides out of the box. 

- Characters (that is 'you' in the gameworld) has the `CharacterCmdSet`.
- Accounts (the thing that represents your out-of-character existence on the server) has the `AccountCmdSet`
- Sessions (representing one single client connection) has the `SessionCmdSet`
- Before you log in (at the connection screen) you'll have access to the `UnloggedinCmdSet`.

The thing must commonly modified is the `CharacterCmdSet`.

The default cmdset are defined in `mygame/commands/default_cmdsets.py`. Open that file now: 

```python
"""
(module docstring)
"""

from evennia import default_cmds

class CharacterCmdSet(default_cmds.CharacterCmdSet):

    key = "DefaultCharacter"

    def at_cmdset_creation(self):

        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones
        #

class AccountCmdSet(default_cmds.AccountCmdSet):

    key = "DefaultAccount"

    def at_cmdset_creation(self):

        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones
        #

class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):

        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones
        #

class SessionCmdSet(default_cmds.SessionCmdSet):

    key = "DefaultSession"

    def at_cmdset_creation(self):

        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones
        #
```

```sidebar:: super()
    
    The `super()` function refers to the parent of the current class and is commonly
    used to call same-named methods on the parent. 
```
`evennia.default_cmds` is a container that holds all of Evennia's default commands and cmdsets. In this module 
we can see that this was imported and then a new child class was made for each cmdset. Each class looks familiar
(except the `key`, that's mainly used to easily identify the cmdset in listings). In each `at_cmdset_creation` all
we do is call `super().at_cmdset_creation` which means that we call `at_cmdset_creation() on the _parent_ CmdSet.
This is what adds all the default commands to each CmdSet. 

To add even more Commands to a default cmdset, we can just add them below the `super()` line. Usefully, if we were to
add a Command with the same `.key` as a default command, it would completely replace that original. So if you were 
to add a command with a key `look`, the original `look` command would be replaced by your own version. 

For now, let's add our own `hit` and `echo` commands to the `CharacterCmdSet`:


```python
# ...

from commands import mycommands

class CharacterCmdSet(default_cmds.CharacterCmdSet):

    key = "DefaultCharacter"

    def at_cmdset_creation(self):

        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones
        #
        self.add(mycommands.CmdEcho)
        self.add(mycommands.CmdHit)

```

    > reload 
    > hit
    Who do you want to hit?     

Your new commands are now available for all player characters in the game. There is another way to add a bunch
of commands at once, and that is to add a _CmdSet_ to the other cmdset. All commands in that cmdset will then be added:

```python
from commands import mycommands

class CharacterCmdSet(default_cmds.CharacterCmdSet):

    key = "DefaultCharacter"

    def at_cmdset_creation(self):

        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones
        #
        self.add(mycommands.MyCmdSet)
```

Which way you use depends on how much control you want, but if you already have a CmdSet, 
this is practical. A Command can be a part of any number of different CmdSets.

### Removing Commands

To remove your custom commands again, you of course just delete the change you did to 
`mygame/commands/default_cmdsets.py`. But what if you want to remove a default command? 

We already know that we use `cmdset.remove()` to remove a cmdset. It turns out you can 
do the same in `at_cmdset_creation`. For example, let's remove the default `get` Command 
from Evennia. We happen to know this can be found as `default_cmds.CmdGet`.

    
```python
# ...
from commands import mycommands

class CharacterCmdSet(default_cmds.CharacterCmdSet):

    key = "DefaultCharacter"

    def at_cmdset_creation(self):

        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones
        #
        self.add(mycommands.MyCmdSet)
        self.remove(default_cmds.CmdGet)
# ...
```

    > reload 
    > get
    Command 'get' is not available ...

## Replace a default command

At this point you already have all the pieces for how to do this! We just need to add a new 
command with the same `key` in the `CharacterCmdSet` to replace the default one. 

Let's combine this with what we know about classes and 
how to _override_ a parent class. Open `mygame/commands/mycommands.py` and lets override
that `CmdGet` command.

```python
# up top, by the other imports
from evennia import default_cmds

# somewhere below 
class MyCmdGet(default_cmds.CmdGet):

    def func(self):
        super().func()
        self.caller.msg(str(self.caller.location.contents))

```

- **Line2**: We import `default_cmds` so we can get the parent class.
We made a new class and we make it _inherit_ `default_cmds.CmdGet`. We don't 
need to set `.key` or `.parse`, that's already handled by the parent. 
In `func` we call `super().func()` to let the parent do its normal thing, 
- **Line 7**: By adding our own `func` we replace the one in the parent.
- **Line 8**: For this simple change we still want the command to work the 
  same as before, so we use `super()` to call `func` on the parent.
- **Line 9**: `.location` is the place an object is at. `.contents` contains, well, the 
    contents of an object. If you tried `py self.contents` you'd get a list that equals 
    your inventory. For a room, the contents is everything in it. 
    So `self.caller.location.contents` gets the contents of our current location. This is
    a _list_. In order send this to us with `.msg` we turn the list into a string. Python
    has a special function `str()` to do this.
    
We now just have to add this so it replaces the default `get` command. Open 
`mygame/commands/default_cmdsets.py` again:

```python
# ...
from commands import mycommands

class CharacterCmdSet(default_cmds.CharacterCmdSet):

    key = "DefaultCharacter"

    def at_cmdset_creation(self):

        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones
        #
        self.add(mycommands.MyCmdSet)
        self.add(mycommands.MyCmdGet)
# ...
```
```sidebar:: Another way

    Instead of adding `MyCmdGet` explicitly in default_cmdset.py, 
    you could also add it to `mycommands.MyCmdSet` and let it be 
    added automatically for you.
```

    > reload 
    > get 
    Get What?
    [smaug, fluffy, YourName, ...] 

We just made a new `get`-command that tells us everything we could pick up (well, we can't pick up ourselves, so 
there's some room for improvement there). 

## Summary

In this lesson we got into some more advanced string formatting - many of those tricks will help you a lot in 
the future! We also made a functional sword. Finally we got into how to add to, extend and replace a default 
command on ourselves.

[prev lesson](Adding-Commands) | [next lesson](Creating-Things)
