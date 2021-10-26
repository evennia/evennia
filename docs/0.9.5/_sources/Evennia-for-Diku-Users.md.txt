# Evennia for Diku Users


Evennia represents a learning curve for those who used to code on
[Diku](https://en.wikipedia.org/wiki/DikuMUD) type MUDs. While coding in Python is easy if you
already know C, the main effort is to get rid of old C programming habits. Trying to code Python the
way you code C will not only look ugly, it will lead to less optimal and harder to maintain code.
Reading Evennia example code is a good way to get a feel for how different problems are approached
in Python.

Overall, Python offers an extensive library of resources, safe memory management and excellent
handling of errors. While Python code does not run as fast as raw C code does, the difference is not
all that important for a text-based game. The main advantage of Python is an extremely fast
development cycle with and easy ways to create game systems that would take many times more code and
be much harder to make stable and maintainable in C.

### Core Differences

- As mentioned, the main difference between Evennia and a Diku-derived codebase is that Evennia is
written purely in Python. Since Python is an interpreted language there is no compile stage. It is
modified and extended by the server loading Python modules at run-time. It also runs on all computer
platforms Python runs on (which is basically everywhere).
- Vanilla Diku type engines save their data in custom *flat file* type storage solutions. By
contrast, Evennia stores all game data in one of several supported SQL databases. Whereas flat files
have the advantage of being easier to implement, they (normally) lack many expected safety features
and ways to effectively extract subsets of the stored data. For example, if the server loses power
while writing to a flatfile it may become corrupt and the data lost. A proper database solution is
not susceptible to this - at no point is the data in a state where it cannot be recovered. Databases
are also highly optimized for querying large data sets efficiently.

### Some Familiar Things

Diku expresses the character object referenced normally by:

`struct char ch*` then all character-related fields can be accessed by `ch->`. In Evennia, one must
pay attention to what object you are using, and when you are accessing another through back-
handling, that you are accessing the right object. In Diku C, accessing character object is normally
done by:

```c
/* creating pointer of both character and room struct */

void(struct char ch*, struct room room*){
    int dam;
    if (ROOM_FLAGGED(room, ROOM_LAVA)){
        dam = 100
        ch->damage_taken = dam
    };
};
```

As an example for creating Commands in Evennia via the `from evennia import Command` the character
object that calls the command is denoted by a class property as `self.caller`. In this example
`self.caller` is essentially the 'object' that has called the Command, but most of the time it is an
Account object. For a more familiar Diku feel, create a variable that becomes the account object as:

```python
#mygame/commands/command.py

from evennia import Command

class CmdMyCmd(Command):
    """
    This is a Command Evennia Object
    """
    
    [...]

    def func(self):
        ch = self.caller
        # then you can access the account object directly by using the familiar ch.
        ch.msg("...")
        account_name = ch.name
        race = ch.db.race

```

As mentioned above, care must be taken what specific object you are working with. If focused on a
room object and you need to access the account object:

```python
#mygame/typeclasses/room.py

from evennia import DefaultRoom

class MyRoom(DefaultRoom):
    [...]

    def is_account_object(self, object):
        # a test to see if object is an account
        [...]

    def myMethod(self):
        #self.caller would not make any sense, since self refers to the
        # object of 'DefaultRoom', you must find the character obj first:
        for ch in self.contents:
            if self.is_account_object(ch):
                # now you can access the account object with ch:
                account_name = ch.name
                race = ch.db.race
```


## Emulating Evennia to Look and Feel Like A Diku/ROM

To emulate a Diku Mud on Evennia some work has to be done before hand. If there is anything that all
coders and builders remember from Diku/Rom days is the presence of VNUMs. Essentially all data was
saved in flat files and indexed by VNUMs for easy access. Evennia has the ability to emulate VNUMS
to the extent of categorising rooms/mobs/objs/trigger/zones[...] into vnum ranges.

Evennia has objects that are called Scripts. As defined, they are the 'out of game' instances that
exist within the mud, but never directly interacted with. Scripts can be used for timers, mob AI,
and even a stand alone databases.

Because of their wonderful structure all mob, room, zone, triggers, etc.. data can be saved in
independently created global scripts.

Here is a sample mob file from a Diku Derived flat file.

```text
#0
mob0~
mob0~
mob0
~
   Mob0
~
10 0 0 0 0 0 0 0 0 E
1 20 9 0d0+10 1d2+0
10 100
8 8 0
E
#1
Puff dragon fractal~
Puff~
Puff the Fractal Dragon is here, contemplating a higher reality.
~
   Is that some type of differential curve involving some strange, and unknown
calculus that she seems to be made out of?
~
516106 0 0 0 2128 0 0 0 1000 E
34 9 -10 6d6+340 5d5+5
340 115600
8 8 2
BareHandAttack: 12
E
T 95
```
Each line represents something that the MUD reads in and does something with it. This isn't easy to
read, but let's see if we can emulate this as a dictionary to be stored on a database script created
in Evennia.

First, let's create a global script that does absolutely nothing and isn't attached to anything. You
can either create this directly in-game with the @py command or create it in another file to do some
checks and balances if for whatever reason the script needs to be created again. Progmatically it
can be done like so:

```python
from evennia import create_script

mob_db = create_script("typeclasses.scripts.DefaultScript", key="mobdb",
                       persistent=True, obj=None)
mob_db.db.vnums = {}
```
Just by creating a simple script object and assigning it a 'vnums' attribute as a type dictionary.
Next we have to create the mob layout..

```python
# vnum : mob_data

mob_vnum_1 = {
            'key' : 'puff',
            'sdesc' : 'puff the fractal dragon',
            'ldesc' : 'Puff the Fractal Dragon is here, ' \
                      'contemplating a higher reality.',
            'ddesc' : ' Is that some type of differential curve ' \
                      'involving some strange, and unknown calculus ' \
                      'that she seems to be made out of?',
            [...]
        }

# Then saving it to the data, assuming you have the script obj stored in a variable.
mob_db.db.vnums[1] = mob_vnum_1
```

This is a very 'caveman' example, but it gets the idea across. You can use the keys in the
`mob_db.vnums` to act as the mob vnum while the rest contains the data..

Much simpler to read and edit. If you plan on taking this route, you must keep in mind that by
default evennia 'looks' at different properties when using the `look` command for instance. If you
create an instance of this mob and make its `self.key = 1`, by default evennia will say

`Here is : 1`

You must restructure all default commands so that the mud looks at different properties defined on
your mob.




