# Persistent objects and typeclasses

Now that we have learned a little about how to find things in the Evennia library, let's use it. 

In the [Python classes and objects](./Python-classes-and-objects.md) lesson we created the dragons Fluffy, Cuddly 
and Smaug and made them fly and breathe fire. So far our dragons are short-lived - whenever we `restart`
the server or `quit()` out of python mode they are gone. 

This is what you should have in `mygame/typeclasses/monsters.py` so far: 


```python

class Monster:
    """
    This is a base class for Monsters.
    """
 
    def __init__(self, key):
        self.key = key 

    def move_around(self):
        print(f"{self.key} is moving!")


class Dragon(Monster):
    """
    This is a dragon-specific monster.
    """

    def move_around(self):
        super().move_around()
        print("The world trembles.")

    def firebreath(self):
        """ 
        Let our dragon breathe fire.
        """
        print(f"{self.key} breathes fire!")

```

## Our first persistent object

At this point we should know enough to understand what is happening in `mygame/typeclasses/objects.py`. Let's
open it:  

```python
"""
module docstring
"""
from evennia import DefaultObject

class Object(DefaultObject):
    """
    class docstring
    """
    pass
```

So we have a class `Object` that _inherits_ from `DefaultObject`, which we have imported from Evennia. 
The class itself doesn't do anything (it just `pass`es) but that doesn't mean it's useless. As we've seen,
it inherits all the functionality of its parent. It's in fact an _exact replica_ of `DefaultObject` right now. 
If we knew what kind of methods and resources were available on `DefaultObject` we could add our own and 
change the way it works!

> Hint: We will get back to this, but to learn what resources an Evennia parent like `DefaultObject` offers, 
> easiest is to peek at its [API documentation](evennia.objects.objects.DefaultObject). The docstring for
> the `Object` class can also help.

One thing that Evennia classes offers and which you don't get with vanilla Python classes is _persistence_. As 
you've found, Fluffy, Cuddly and Smaug are gone once we reload the server. Let's see if we can fix this. 

Go back to `mygame/typeclasses/monsters.py`. Change it as follows: 

```python

from typeclasses.objects import Object

class Monster(Object):
    """
    This is a base class for Monsters.
    """
    def move_around(self):
        print(f"{self.key} is moving!")


class Dragon(Monster):
    """
    This is a dragon-specific Monster.
    """

    def move_around(self):
        super().move_around()
        print("The world trembles.")

    def firebreath(self):
        """ 
        Let our dragon breathe fire.
        """
        print(f"{self.key} breathes fire!")

```

Don't forget to save. We removed `Monster.__init__` and made `Monster` inherit from Evennia's `Object` (which in turn 
inherits from Evennia's `DefaultObject`, as we saw). By extension, this means that `Dragon` also inherits 
from `DefaultObject`, just from further away!

### Making a new object by calling the class

First reload the server as usual. We will need to create the dragon a little differently this time: 

```{sidebar} Keyword arguments

    Keyword arguments (like `db_key="Smaug"`) is a way to 
    name the input arguments to a function or method. They make 
    things easier to read but also allows for conveniently setting 
    defaults for values not given explicitly.

```
    > py
    > from typeclasses.monsters import Dragon
    > smaug = Dragon(db_key="Smaug", db_location=here)
    > smaug.save()
    > smaug.move_around()
    Smaug is moving!
    The world trembles.

Smaug works the same as before, but we created him differently: first we used 
`Dragon(db_key="Smaug", db_location=here)` to create the object, and then we used `smaug.save()` afterwards. 

    > quit()
    Python Console is closing.
    > look 
    
You should now see that Smaug _is in the room with you_. Woah! 

    > reload 
    > look 
    
_He's still there_... What we just did was to create a new entry in the database for Smaug. We gave the object 
its name (key) and set its location to our current location (remember that `here` is just something available 
in the `py` command, you can't use it elsewhere). 

To make use of Smaug in code we must first find him in the database. For an object in the current 
location we can easily do this in `py` by using `me.search()`: 

    > py smaug = me.search("Smaug") ; smaug.firebreath()
    Smaug breathes fire!  

### Creating using create_object

Creating Smaug like we did above is nice because it's similar to how we created non-database
bound Python instances before. But you need to use `db_key` instead of `key` and you also have to 
remember to call `.save()` afterwards. Evennia has a helper function that is more common to use, 
called `create_object`:

    > py fluffy = evennia.create_object('typeclases.monster.Monster', key="Fluffy", location=here)
    > look 
    
Boom, Fluffy should now be in the room with you, a little less scary than Smaug. You specify the 
python-path to the code you want and then set the key and location. Evennia sets things up and saves for you. 

If you want to find Fluffy from anywhere, you can use Evennia's `search_object` helper: 

    > fluffy = evennia.search_object("Fluffy")[0] ; fluffy.move_around()
    Fluffy is moving! 

> The `[0]` is because `search_object` always returns a _list_ of zero, one or more found objects. The `[0]`
means that we want the first element of this list (counting in Python always starts from 0). If there were 
multiple Fluffies we could get the second one with `[1]`.

### Creating using create-command

Finally, you can also create a new Dragon using the familiar builder-commands we explored a few lessons ago:

    > create/drop Cuddly:typeclasses.monsters.Monster

Cuddly is now in the room. After learning about how objects are created you'll realize that all this command really
does is to parse your input, figure out that `/drop` means to "give the object the same location as the caller",
and then do a call akin to

    evennia.create_object("typeclasses.monsters.Monster", key="Cuddly", location=here)

That's pretty much all there is to the mighty `create` command! The rest is just parsing for the command
to understand just what the user wants to create. 

## Typeclasses

The `Object` (and `DefafultObject` class we inherited from above is what we refer to as a _Typeclass_. This
is an Evennia thing. The instance of a typeclass saves itself to the database when it is created, and after
that you can just search for it to get it back. We use the term _typeclass_ or _typeclassed_ to differentiate 
these types of classes and objects from the normal Python classes, whose instances go away on a reload. 

The number of typeclasses in Evennia are so few they can be learned by heart:

- `evennia.DefaultObject`: This is the parent of all in-game entities - everything with a location. Evennia makes
   a few very useful child classes of this class:
   - `evennia.DefaultCharacter`: The default entity represening a player avatar in-game.
   - `evennia.DefaultRoom`: A location in the game world.
   - `evennia.DefaultExit`: A link between locations.
- `evennia.DefaultAccount`: The OOC representation of a player, holds password and account info.
- `evennia.DefaultChannel`: In-game channels. These could be used for all sorts of in-game communication.
- `evennia.DefaultScript`: Out-of-game objects, with no presence in the game world. Anything you want to create that
    needs to be persistent can be stored with these entities, such as combat state, economic systems or what have you.
    
If you take a look in `mygame/typeclasses/` you'll find modules for each of these. Each contains an empty child 
class ready that already inherits from the right parent, ready for you to modify or build from:

- `mygame/typeclasses/objects.py` has `class Object(DefaultObject)`, a class directly inheriting the basic in-game entity, this
    works as a base for any object. 
- `mygame/typeclasses/characters.py` has `class Character(DefaultCharacter)`
- `mygame/typeclasses/rooms.py` has `class Room(DefaultRoom)`
- `mygame/typeclasses/exits.py` has `class Exit(DefaultExit)`
- `mygame/typeclasses/accounts.py` has `class Account(DefaultAccount)`
- `mygame/typeclasses/channels.py` has `class Channel(DefaultChannel)`
- `mygame/typeclasses/scripts.py` has `class Script(DefaultScript)`

> Notice that the classes in `mygame/typeclasses/` are _not inheriting from each other_. For example, 
> `Character` is inheriting from `evennia.DefaultCharacter` and not from `typeclasses.objects.Object`. 
> So if you change `Object` you will not cause any change in the `Character` class. If you want that you
> can easily just change the child classes to inherit in that way instead; Evennia doesn't care.

As seen with our `Dragon` example, you don't _have_ to modify these modules directly. You can just make your 
own modules and import the base class. 

### Examining and defaults

When you do 

    > create/drop giantess:typeclasses.monsters.Monster
    You create a new Monster: giantess.
    
or 

    > py evennia.create_object("typeclasses.monsters.Monster", key="Giantess", location=here)
    
You are specifying exactly which typeclass you want to use to build the Giantess. Let's examine the result:

    > examine giantess
    ------------------------------------------------------------------------------- 
    Name/key: Giantess (#14)
    Typeclass: Monster (typeclasses.monsters.Monster)
    Location: Limbo (#2)
    Home: Limbo (#2)
    Permissions: <None>
    Locks: call:true(); control:id(1) or perm(Admin); delete:id(1) or perm(Admin);
       drop:holds(); edit:perm(Admin); examine:perm(Builder); get:all();
       puppet:pperm(Developer); tell:perm(Admin); view:all()
    Persistent attributes:
     desc = You see nothing special. 
    ------------------------------------------------------------------------------- 

We used the `examine` command briefly in the [lesson about building in-game](./Building-Quickstart.md). Now these lines
may be more useful to us:
- **Name/key** - The name of this thing. The value `(#14)` is probably different for you. This is the 
    unique 'primary key' or _dbref_ for this entity in the database.
- **Typeclass**: This show the typeclass we specified, and the path to it. 
- **Location**: We are in Limbo. If you moved elsewhere you'll see that instead. Also the `#dbref` is shown.
- **Permissions**: _Permissions_ are like the inverse to _Locks_ - they are like keys to unlock access to other things.
  The giantess have no such keys (maybe fortunately).
- **Locks**: Locks are the inverse of _Permissions_ - specify what criterion _other_ objects must fulfill in order to 
  access the `giantess` object. This uses a very flexible mini-language. For examine, the line `examine:perm(Builders)`
  is read as "Only those with permission _Builder_ or higher can _examine_ this object". Since we are the superuser
  we pass (even bypass) such locks with ease.
- **Persistent attributes**: This allows for storing arbitrary, persistent data on the typeclassed entity. We'll get 
to those in the next section.
  
Note how the **Typeclass** line describes exactly where to find the code of this object? This is very useful for 
understanding how any object in Evennia works. 

What happens if we _don't_ specify the typeclass though? 

    > create/drop box 
    You create a new Object: box.
    
or

    > py create.create_object(None, key="box", location=here)
    
Now check it out: 
    
    > examine box  
    
You will find that the **Typeclass** line now reads

    Typeclass: Object (typeclasses.objects.Object) 
    
So when you didn't specify a typeclass, Evennia used a default, more specifically the (so far) empty `Object` class in 
`mygame/typeclasses/objects.py`. This is usually what you want, especially since you can tweak that class as much 
as you like. 

But the reason Evennia knows to fall back to this class is not hard-coded - it's a setting. The default is 
in [evennia/settings_default.py](https://github.com/evennia/evennia/blob/master/evennia/settings_default.py#L465), 
with the name `BASE_OBJECT_TYPECLASS`, which is set to `typeclasses.objects.Object`. 

```{sidebar} Changing things

    While it's tempting to change folders around to your liking, this can
    make it harder to follow tutorials and may confuse if 
    you are asking others for help. So don't overdo it unless you really 
    know what you are doing.
```

So if you wanted the creation commands and methods to default to some other class you could 
add your own `BASE_OBJECT_TYPECLASS` line to `mygame/server/conf/settings.py`. The same is true for all the other
typeclasseses, like characters, rooms and accounts. This way you can change the 
layout of your game dir considerably if you wanted. You just need to tell Evennia where everything is.
    
## Modifying ourselves 

Let's try to modify ourselves a little. Open up `mygame/typeclasses/characters.py`.

```python
"""
(module docstring)
"""
from evennia import DefaultCharacter

class Character(DefaultCharacter):
    """
    (class docstring)
    """
    pass
```

This looks quite familiar now - an empty class inheriting from the Evennia base typeclass. As you would expect,
this is also the default typeclass used for creating Characters if you don't specify it. You can verify it: 

    > examine me
    ------------------------------------------------------------------------------
    Name/key: YourName (#1)
    Session id(s): #1
    Account: YourName
    Account Perms: <Superuser> (quelled)
    Typeclass: Character (typeclasses.characters.Character)
    Location: Limbo (#2)
    Home: Limbo (#2)
    Permissions: developer, player
    Locks:      boot:false(); call:false(); control:perm(Developer); delete:false();
          drop:holds(); edit:false(); examine:perm(Developer); get:false();
          msg:all(); puppet:false(); tell:perm(Admin); view:all()
    Stored Cmdset(s):
     commands.default_cmdsets.CharacterCmdSet [DefaultCharacter] (Union, prio 0)
    Merged Cmdset(s):
       ...
    Commands available to YourName (result of Merged CmdSets):
       ...
    Persistent attributes:
     desc = This is User #1.
     prelogout_location = Limbo
    Non-Persistent attributes:
     last_cmd = None
    ------------------------------------------------------------------------------
    
You got a lot longer output this time. You have a lot more going on than a simple Object. Here are some new fields of note: 
- **Session id(s)**: This identifies the _Session_ (that is, the individual connection to a player's game client).
- **Account** shows, well the `Account` object associated with this Character and Session.
- **Stored/Merged Cmdsets** and **Commands available** is related to which _Commands_ are stored on you. We will
    get to them in the [next lesson](./Adding-Commands.md). For now it's enough to know these consitute all the 
    commands available to you at a given moment. 
- **Non-Persistent attributes** are Attributes that are only stored temporarily and will go away on next reload.

Look at the **Typeclass** field and you'll find that it points to `typeclasses.character.Character` as expected. 
So if we modify this class we'll also modify ourselves.

### A method on ourselves

Let's try something simple first. Back in `mygame/typeclasses/characters.py`:

```python

class Character(DefaultCharacter):
    """
    (class docstring)
    """

    str = 10
    dex = 12
    int = 15

    def get_stats(self):
        """
        Get the main stats of this character
        """
        return self.str, self.dex, self.int

```

    > reload 
    > py self.get_stats()
    (10, 12, 15)
    
```{sidebar} Tuples and lists

    - A `list` is written `[a, b, c, d, ...]`. It can be modified after creation.
    - A `tuple` is written `(a, b, c, ...)`. It cannot be modified once created.
```
We made a new method, gave it a docstring and had it `return` the RP-esque values we set. It comes back as a
_tuple_ `(10, 12, 15)`. To get a specific value you could specify the _index_ of the value you want,
starting from zero:

    > py stats = self.get_stats() ; print(f"Strength is {stats[0]}.")
    Strength is 10.

### Attributes 

So what happens when we increase our strength? This would be one way: 

    > py self.str = self.str + 1
    > py self.str
    11
    
Here we set the strength equal to its previous value + 1. A shorter way to write this is to use Python's `+=`
operator: 

    > py self.str += 1
    > py self.str 
    12     
    > py self.get_stats()
    (12, 12, 15)
    
This looks correct! Try to change the values for dex and int too; it works fine. However: 

    > reload 
    > py self.get_stats()
    (10, 12, 15)
    
After a reload all our changes were forgotten. When we change properties like this, it only changes in memory,
not in the database (nor do we modify the python module's code). So when we reloaded, the 'fresh' `Character` 
class was loaded, and it still has the original stats we wrote to it. 
 
In principle we could change the python code. But we don't want to do that manually every time. And more importantly
since we have the stats hardcoded in the class, _every_ character instance in the game will have exactly the 
same `str`, `dex` and `int` now! This is clearly not what we want. 

Evennia offers a special, persistent type of property for this, called an `Attribute`. Rework your 
`mygame/typeclasses/characters.py` like this: 
    
```python

class Character(DefaultCharacter):
    """
    (class docstring)
    """

    def get_stats(self):
        """
        Get the main stats of this character
        """
        return self.db.str, self.db.dex, self.db.int
```

```{sidebar} Spaces in Attribute name?

    What if you want spaces in your Attribute name? Or you want to assign the 
    name of the Attribute on-the fly? Then you can use `.attributes.add(name, value)` instead,
    for example `self.attributes.add("str", 10)`. 

```

We removed the hard-coded stats and added added `.db` for every stat. The `.db` handler makes the stat
into an an Evennia `Attribute`.

    > reload 
    > py self.get_stats()
    (None, None, None) 
    
Since we removed the hard-coded values, Evennia don't know what they should be (yet). So all we get back 
is `None`, which is a Python reserved word to represent nothing, a no-value. This is different from a normal python 
property:

    > py self.str
    AttributeError: 'Character' object has no attribute 'str'
    > py self.db.str
    (nothing will be displayed, because it's None)

Trying to get an unknown normal Python property will give an error. Getting an unknown Evennia `Attribute` will 
never give an error, but only result in `None` being returned. This is often very practical. 

    > py self.db.str, self.db.dex, self.db.int = 10, 12, 15
    > py self.get_stats()
    (10, 12, 15)
    > reload 
    > py self.get_stats()
    (10, 12, 15)
    
Now we set the Attributes to the right values. We can see that things work the same as before, also after a 
server reload. Let's modify the strength: 
    
    > py self.db.str += 2 
    > py self.get_stats()
    (12, 12, 15)
    > reload 
    > py self.get_stats()
    (12, 12, 15)
    
 Our change now survives a reload since Evennia automatically saves the Attribute to the database for us.  

### Setting things on new Characters 

Things a looking better, but one thing remains strange - the stats start out with a value `None` and we 
have to manually set them to something reasonable. In a later lesson we will investigate character-creation 
in more detail. For now, let's give every new character some random stats to start with. 

We want those stats to be set only once, when the object is first created. For the Character, this method 
is called `at_object_creation`.

```{sidebar} __init__ vs at_object_creation

    For the `Monster` class we used `__init__` to set up the class. We can't use this
    for a typeclass because it will be called more than once, at the very least after
    every reload and maybe more depending on caching. Even if you are familiar with Python,
    avoid touching `__init__` for typeclasses, the results will not be what you expect.

```

```python
# up by the other imports
import random 

class Character(DefaultCharacter):
    """
    (class docstring)
    """

    def at_object_creation(self):       
        self.db.str = random.randint(3, 18)
        self.db.dex = random.randint(3, 18)
        self.db.int = random.randint(3, 18)
    
    def get_stats(self):
        """
        Get the main stats of this character
        """
        return self.db.str, self.db.dex, self.db.int
```

We imported a new module, `random`. This is part of Python's standard library. We used `random.randint` to 
set a random value from 3 to 18 to each stat. Simple, but for some classical RPGs this is all you need! 

    > reload 
    > py self.get_stats()
    (12, 12, 15)
    
Hm, this is the same values we set before. They are not random. The reason for this is of course that, as said,
`at_object_creation` only runs _once_, the very first time a character is created. Our character object was already 
created long before, so it will not be called again. 
    
It's simple enough to run it manually though: 

    > self.at_object_creation()
    > py self.get_stats()
    (5, 4, 8)
    
Lady luck didn't smile on us for this example; maybe you'll fare better. Evennia has a helper command
`update` that re-runs the creation hook and also cleans up any other Attributes not re-created by `at_object_creation`:

    > update self
    > py self.get_stats()
    (8, 16, 14)
   
### Updating all Characters in a loop
    
Needless to say, for your game you are wise to have a feel for what you want to go into the `at_object_creation` hook
before you create a lot of objects (characters in this case). But should it come to that you don't want to have to 
go around and re-run the method on everyone manually. For the Python beginner, doing this will also give a chance to 
try out Python _loops_. We try them out in multi-line Python mode: 

    > py
    > for a in [1, 2, "foo"]:     >     print(a)
    1
    2
    foo
    
A python _for-loop_ allows us to loop over something. Above, we made a _list_ of two numbers and a string. In
every iteration of the loop, the variable `a` becomes one element in turn, and we print that.
    
For our list, we want to loop over all Characters, and want to call `.at_object_creation` on each. This is how 
this is done (still in python multi-line mode): 

    > from typeclasses.characters import Character
    > for char in Character.objects.all()
    >     char.at_object_creation()
    
```{sidebar} Database queries

    `Character.objects.all()` is an example of a database query expressed in Python. This will be converted 
    into a database query under the hood. This syntax is part of 
    `Django's query language <https://docs.djangoproject.com/en/3.0/topics/db/queries/>`_. You don't need to
    know Django to use Evennia, but if you ever need more specific database queries, this is always available
    when you need it.

``` 
We import the `Character` class and then we use `.objects.all()` to get all `Character` instances. Simplified,
`.objects` is a resource from which one can _query_ for all `Characters`. Using `.all()` gets us a listing 
of all of them that we then immediately loop over. Boom, we just updated all Characters, including ourselves: 

    > quit()
    Closing the Python console.
    > self.get_stats()
    (3, 18, 10)

## Extra Credits

This principle is the same for other typeclasses. So using the tools explored in this lesson, try to expand 
the default room with an `is_dark` flag. It can be either `True` or `False`. 
Have all new rooms start with `is_dark = False` and make it so that once you change it, it survives a reload. 
Oh, and if you created any other rooms before, make sure they get the new flag too! 

## Conclusions

In this lesson we created database-persistent dragons by having their classes inherit from one `Object`, one 
of Evennia's _typeclasses_. We explored where Evennia looks for typeclasses if we don't specify the path 
explicitly. We then modified ourselves - via the `Character` class - to give us some simple RPG stats. This 
led to the need to use Evennia's _Attributes_, settable via `.db` and to use a for-loop to update ourselves.

Typeclasses are a fundamental part of Evennia and we will see a lot of more uses of them in the course of 
this tutorial. But that's enough of them for now. It's time to take some action. Let's learn about _Commands_. 


