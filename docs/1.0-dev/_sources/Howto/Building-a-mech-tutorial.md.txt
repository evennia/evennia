# Building a mech tutorial

> This page was adapted from the article "Building a Giant Mech in Evennia" by Griatch, published in
Imaginary Realities Volume 6, issue 1, 2014. The original article is no longer available online,
this is a version adopted to be compatible with the latest Evennia.

## Creating the Mech

Let us create a functioning giant mech using the Python MUD-creation system Evennia. Everyone likes
a giant mech, right? Start in-game as a character with build privileges (or the superuser).

    @create/drop Giant Mech ; mech

Boom. We created a Giant Mech Object and dropped it in the room. We also gave it an alias *mech*.
Let’s describe it.

    @desc mech = This is a huge mech. It has missiles and stuff.

Next we define who can “puppet” the mech object.

    @lock mech = puppet:all()

This makes it so that everyone can control the mech. More mechs to the people! (Note that whereas
Evennia’s default commands may look vaguely MUX-like, you can change the syntax to look like
whatever interface style you prefer.)

Before we continue, let’s make a brief detour. Evennia is very flexible about its objects and even
more flexible about using and adding commands to those objects. Here are some ground rules well
worth remembering for the remainder of this article:

- The [Account](../Components/Accounts) represents the real person logging in and has no game-world existence.
- Any [Object](../Components/Objects) can be puppeted by an Account (with proper permissions).
- [Characters](../Components/Objects#characters), [Rooms](../Components/Objects#rooms), and [Exits](../Components/Objects#exits) are just
children of normal Objects.
- Any Object can be inside another (except if it creates a loop).
- Any Object can store custom sets of commands on it. Those commands can:
    - be made available to the puppeteer (Account),
    - be made available to anyone in the same location as the Object, and
    - be made available to anyone “inside” the Object
    - Also Accounts can store commands on themselves. Account commands are always available unless
commands on a puppeted Object explicitly override them.

In Evennia, using the `@ic` command will allow you to puppet a given Object (assuming you have
puppet-access to do so). As mentioned above, the bog-standard Character class is in fact like any
Object: it is auto-puppeted when logging in and just has a command set on it containing the normal
in-game commands, like look, inventory, get and so on.

    @ic mech

You just jumped out of your Character and *are* now the mech! If people look at you in-game, they
will look at a mech. The problem at this point is that the mech Object has no commands of its own.
The usual things like look, inventory and get sat on the Character object, remember? So at the
moment the mech is not quite as cool as it could be.

    @ic <Your old Character>

You just jumped back to puppeting your normal, mundane Character again. All is well.

> (But, you ask, where did that `@ic` command come from, if the mech had no commands on it? The
answer is that it came from the Account's command set. This is important. Without the Account being
the one with the `@ic` command, we would not have been able to get back out of our mech again.)


### Arming the Mech

Let us make the mech a little more interesting. In our favorite text editor, we will create some new
mech-suitable commands. In Evennia, commands are defined as Python classes.

```python
# in a new file mygame/commands/mechcommands.py

from evennia import Command

class CmdShoot(Command):
    """
    Firing the mech’s gun

    Usage:
      shoot [target]

    This will fire your mech’s main gun. If no
    target is given, you will shoot in the air.
    """
    key = "shoot"
    aliases = ["fire", "fire!"]

    def func(self):
        "This actually does the shooting"

        caller = self.caller
        location = caller.location

        if not self.args:
            # no argument given to command - shoot in the air
            message = "BOOM! The mech fires its gun in the air!"
            location.msg_contents(message)
            return

        # we have an argument, search for target
        target = caller.search(self.args.strip())
        if target:
            message = "BOOM! The mech fires its gun at %s" % target.key
            location.msg_contents(message)

class CmdLaunch(Command):
    # make your own 'launch'-command here as an exercise!
    # (it's very similar to the 'shoot' command above).

```

This is saved as a normal Python module (let’s call it `mechcommands.py`), in a place Evennia looks
for such modules (`mygame/commands/`). This command will trigger when the player gives the command
“shoot”, “fire,” or even “fire!” with an exclamation mark. The mech can shoot in the air or at a
target if you give one. In a real game the gun would probably be given a chance to hit and give
damage to the target, but this is enough for now.

We also make a second command for launching missiles (`CmdLaunch`). To save
space we won’t describe it here; it looks the same except it returns a text
about the missiles being fired and has different `key` and `aliases`. We leave
that up to you to create as an exercise. You could have it print "WOOSH! The
mech launches missiles against <target>!", for example.

Now we shove our commands into a command set. A [Command Set](../Components/Command-Sets) (CmdSet) is a container
holding any number of commands. The command set is what we will store on the mech.

```python
# in the same file mygame/commands/mechcommands.py

from evennia import CmdSet
from evennia import default_cmds

class MechCmdSet(CmdSet):
    """
    This allows mechs to do do mech stuff.
    """
    key = "mechcmdset"

    def at_cmdset_creation(self):
        "Called once, when cmdset is first created"
        self.add(CmdShoot())
        self.add(CmdLaunch())
```

This simply groups all the commands we want. We add our new shoot/launch commands. Let’s head back
into the game. For testing we will manually attach our new CmdSet to the mech.

    @py self.search("mech").cmdset.add("commands.mechcommands.MechCmdSet")

This is a little Python snippet (run from the command line as an admin) that searches for the mech
in our current location and attaches our new MechCmdSet to it. What we add is actually the Python
path to our cmdset class. Evennia will import and initialize it behind the scenes.

    @ic mech

We are back as the mech! Let’s do some shooting!

    fire!
    BOOM! The mech fires its gun in the air!

There we go, one functioning mech. Try your own `launch` command and see that it works too. We can
not only walk around as the mech — since the CharacterCmdSet is included in our MechCmdSet, the mech
can also do everything a Character could do, like look around, pick up stuff, and have an inventory.
We could now shoot the gun at a target or try the missile launch command. Once you have your own
mech, what else do you need?

> Note: You'll find that the mech's commands are available to you by just standing in the same
location (not just by puppeting it). We'll solve this with a *lock* in the next section.

## Making a Mech production line

What we’ve done so far is just to make a normal Object, describe it and put some commands on it.
This is great for testing. The way we added it, the MechCmdSet will even go away if we reload the
server. Now we want to make the mech an actual object “type” so we can create mechs without those
extra steps. For this we need to create a new Typeclass.

A [Typeclass](../Components/Typeclasses) is a near-normal Python class that stores its existence to the database
behind the scenes. A Typeclass is created in a normal Python source file:

```python
# in the new file mygame/typeclasses/mech.py

from typeclasses.objects import Object
from commands.mechcommands import MechCmdSet
from evennia import default_cmds

class Mech(Object):
    """
    This typeclass describes an armed Mech.
    """
    def at_object_creation(self):
        "This is called only when object is first created"
        self.cmdset.add_default(default_cmds.CharacterCmdSet)
        self.cmdset.add(MechCmdSet, permanent=True)
        self.locks.add("puppet:all();call:false()")
        self.db.desc = "This is a huge mech. It has missiles and stuff."
```

For convenience we include the full contents of the default `CharacterCmdSet` in there. This will
make a Character’s normal commands available to the mech. We also add the mech-commands from before,
making sure they are stored persistently in the database. The locks specify that anyone can puppet
the meck and no-one can "call" the mech's Commands from 'outside' it - you have to puppet it to be
able to shoot.

That’s it. When Objects of this type are created, they will always start out with the mech’s command
set and the correct lock. We set a default description, but you would probably change this with
`@desc` to individualize your mechs as you build them.

Back in the game, just exit the old mech (`@ic` back to your old character) then do

    @create/drop The Bigger Mech ; bigmech : mech.Mech

We create a new, bigger mech with an alias bigmech. Note how we give the python-path to our
Typeclass at the end — this tells Evennia to create the new object based on that class (we don't
have to give the full path in our game dir `typeclasses.mech.Mech` because Evennia knows to look in
the `typeclasses` folder already). A shining new mech will appear in the room! Just use

    @ic bigmech

to take it on a test drive.

## Future Mechs

To expand on this you could add more commands to the mech and remove others. Maybe the mech
shouldn’t work just like a Character after all. Maybe it makes loud noises every time it passes from
room to room. Maybe it cannot pick up things without crushing them. Maybe it needs fuel, ammo and
repairs. Maybe you’ll lock it down so it can only be puppeted by emo teenagers.

Having you puppet the mech-object directly is also just one way to implement a giant mech in
Evennia.

For example, you could instead picture a mech as a “vehicle” that you “enter” as your normal
Character (since any Object can move inside another). In that case the “insides” of the mech Object
could be the “cockpit”. The cockpit would have the `MechCommandSet` stored on itself and all the
shooting goodness would be made available to you only when you enter it.

And of course you could put more guns on it. And make it fly.