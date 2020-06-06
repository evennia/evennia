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

> Technically these are all [Typeclassed](Typeclasses), which can be ignored for now. In
> `mygame/typeclasses` are also base typeclasses for out-of-character things, notably
> [Channels](Communications), [Accounts](Accounts) and [Scripts](Scripts). We don't cover those in
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

Note that the [Locks](Locks) and [Attribute](Attributes) which are set in the typeclass could just
as well have been set using commands in-game, so this is a *very* simple example.

## Storing data on initialization

The `at_object_creation` is only called once, when the object is first created. This makes it ideal
for database-bound things like [Attributes](Attributes). But sometimes you want to create temporary
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

> Note: As mentioned in the [Typeclasses](Typeclasses) documentation, `at_init` replaces the use of
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
