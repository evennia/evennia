# Persistent objects and typeclasses

[prev lesson](Python-classes-and-objects) | [next lesson](Adding-Commands)

In the last lesson we created the dragons Fluffy, Cuddly and Smaug and made the fly and breathe fire. We 
learned a bit about _classes_ in the process. But so far our dragons are short-lived - whenever we `restart`
the server or `quit()` out of python mode they are gone. 

This is what you should have in `mygame/typeclasses/mobile.py` so far: 


```python

class Mobile:
    """
    This is a base class for Mobiles.
    """
 
    def __init__(self, key):
        self.key = key 

    def move_around(self):
        print(f"{self.key} is moving!")


class Dragon(Mobile):
    """
    This is a dragon-specific mobile.
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

Now we should know enough to understand what is happening in `mygame/typeclasses/objects.py`.
Open it again: 

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
> easiest is to peek at its [API documentation](api:evennia.objects.objects#DefaultObject). The docstring for
> the `Object` class can also help.

One thing that Evennia offers and which you don't get with vanilla Python classes is _persistence_. As you've 
found, Fluffy, Cuddly and Smaug are gone once we reload the server. Let's see if we can fix this. 

Go back to `mygame/typeclasses/mobile.py`. Change it as follows: 

```python

from typeclasses.objects import Object

class Mobile(Object):
    """
    This is a base class for Mobiles.
    """
    def move_around(self):
        print(f"{self.key} is moving!")


class Dragon(Mobile):
    """
    This is a dragon-specific mobile.
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

Don't forget to save. We removed `Monster.__init__` and made `Mobile` inherit from Evennia's `Object` (which in turn 
inherits from Evennia's `DefaultObject`, as we saw). By extension, this means that `Dragon` also inherits 
from `DefaultObject`, just from further away!

### Creating by calling the class (less common way)

First reload the server as usual. We will need to create the dragon a little differently this time: 

```sidebar:: Keyword arguments

    Keyword arguments (like `db_key="Smaug"`) is a way to 
    name the input arguments to a function or method. They make 
    things easier to read but also allows for conveniently setting 
    defaults for values not given explicitly.

```
    > py
    > from typeclasses.mymobile import Dragon
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
    
_He's still there_... What we just did is to create a new entry in the database for Smaug. We gave the object 
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

    > py fluffy = evennia.create_object('typeclases.mymobile.Mobile', key="Fluffy", location=here)
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

    > create/drop Cuddly:typeclasses.mymobile.Mobile

Cuddly is now in the room. After learning about how objects are created you'll realize that all this command really
does is to parse your input, figure out that `/drop` means to "give the object the same location as the caller",
and then do a call akin to

    evennia.create_object("typeclasses.mymobile.Mobile", key="Cuddly", location=here)

That's pretty much all there is to the mighty `create` command. 

... And speaking of Commands, we should try to add one of our own next. 





# Adding Object Typeclass Tutorial

Evennia comes with a few very basic classes of in-game entities:

    DefaultObject
       |           
       DefaultCharacter
       DefaultRoom
       DefaultExit
       DefaultChannel

When you create a new Evennia game (with for example `evennia --init mygame`) Evennia will
automatically create empty child classes `Object`, `Character`, `Room` and `Exit` respectively. They
are found `mygame/typeclasses/objects.py`, `mygame/typeclasses/rooms.py` etc. 

> Technically these are all [Typeclassed](../../../Component/Typeclasses), which can be ignored for now. In
> `mygame/typeclasses` are also base typeclasses for out-of-character things, notably
> [Channels](../../../Component/Communications), [Accounts](../../../Component/Accounts) and [Scripts](../../../Component/Scripts). We don't cover those in
> this tutorial.

For your own game you will most likely want to expand on these very simple beginnings. It's normal
to want your Characters to have various attributes, for example. Maybe Rooms should hold extra
information or even *all* Objects in your game should have properties not included in basic Evennia.

## Change Default Rooms, Exits, Character Typeclass

This is the simplest case.

The default build commands of a new Evennia game is set up to use the `Room`, `Exit` and `Character`
classes found in the same-named modules under `mygame/typeclasses/`. By default these are empty and
just implements the default parents from the Evennia library (`DefaultRoom`etc). Just add the
changes you want to these classes and run `@reload` to add your new functionality. 

## Create a new type of object

Say you want to create a new "Heavy" object-type that characters should not have the ability to pick
up.

1. Edit `mygame/typeclasses/objects.py` (you could also create a new module there, named something
   like `heavy.py`, that's up to how you want to organize things).
1. Create a new class inheriting at any distance from `DefaultObject`. It could look something like
   this:
```python
    # end of file mygame/typeclasses/objects.py
    from evennia import DefaultObject
    
    class Heavy(DefaultObject):
       "Heavy object"
       def at_object_creation(self):
           "Called whenever a new object is created"
           # lock the object down by default
           self.locks.add("get:false()")
           # the default "get" command looks for this Attribute in order
           # to return a customized error message (we just happen to know
           # this, you'd have to look at the code of the 'get' command to
           # find out).
           self.db.get_err_msg = "This is too heavy to pick up."
```
1. Once you are done, log into the game with a build-capable account and do `@create/drop
   rock:objects.Heavy` to drop a new heavy "rock" object in your location. Next try to pick it up
(`@quell` yourself first if you are a superuser). If you get errors, look at your log files where
you will find the traceback. The most common error is that you have some sort of syntax error in
your class. 

Note that the [Locks](../../../Component/Locks) and [Attribute](../../../Component/Attributes) which are set in the typeclass could just
as well have been set using commands in-game, so this is a *very* simple example.

## Storing data on initialization

The `at_object_creation` is only called once, when the object is first created. This makes it ideal
for database-bound things like [Attributes](../../../Component/Attributes). But sometimes you want to create temporary
properties (things that are not to be stored in the database but still always exist every time the
object is created). Such properties can be initialized in the `at_init` method on the object.
`at_init` is called every time the object is loaded into memory. 

> Note: It's usually pointless and wasteful to assign database data in `at_init`, since this will
> hit the database with the same value over and over. Put those in `at_object_creation` instead. 

You are wise to use `ndb` (non-database Attributes) to store these non-persistent properties, since
ndb-properties are protected against being cached out in various ways and also allows you to list
them using various in-game tools:

```python
def at_init(self):
    self.ndb.counter = 0
    self.ndb.mylist = []
```

> Note: As mentioned in the [Typeclasses](../../../Component/Typeclasses) documentation, `at_init` replaces the use of
> the standard `__init__` method of typeclasses due to how the latter may be called in situations
> other than you'd expect. So use `at_init` where you would normally use `__init__`. 


## Updating existing objects

If you already have some `Heavy` objects created and you add a new `Attribute` in
`at_object_creation`, you will find that those existing objects will not have this Attribute. This
is not so strange, since `at_object_creation` is only called once, it will not be called again just
because you update it. You need to update existing objects manually. 

If the number of objects is limited, you can use `@typeclass/force/reload objectname` to force a
re-load of the `at_object_creation` method (only) on the object. This case is common enough that
there is an alias `@update objectname` you can use to get the same effect. If there are multiple
objects you can use `@py` to loop over the objects you need: 

```
@py from typeclasses.objects import Heavy; [obj.at_object_creation() for obj in Heavy.objects.all()]

``` 

[prev lesson](Python-classes-and-objects) | [next lesson](Adding-Commands)
