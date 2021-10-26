# Objects


All in-game objects in Evennia, be it characters, chairs, monsters, rooms or hand grenades are
represented by an Evennia *Object*. Objects form the core of Evennia and is probably what you'll
spend most time working with. Objects are [Typeclassed](./Typeclasses.md) entities.

## How to create your own object types

An Evennia Object is, per definition, a Python class that includes `evennia.DefaultObject` among its
parents. In `mygame/typeclasses/objects.py` there is already a class `Object` that inherits from
`DefaultObject` and that you can inherit from. You can put your new typeclass directly in that
module or you could organize your code in some other way. Here we assume we make a new module
`mygame/typeclasses/flowers.py`:

```python
    # mygame/typeclasses/flowers.py

    from typeclasses.objects import Object

    class Rose(Object):
        """
        This creates a simple rose object        
        """    
        def at_object_creation(self):
            "this is called only once, when object is first created"
            # add a persistent attribute 'desc' 
            # to object (silly example).
            self.db.desc = "This is a pretty rose with thorns."     
```
   
You could save this in the `mygame/typeclasses/objects.py` (then you'd not need to import `Object`)
or you can put it in a new module. Let's say we do the latter, making a module
`typeclasses/flowers.py`.  Now you just need to point to the class *Rose* with the `@create` command
to make a new rose:

     @create/drop MyRose:flowers.Rose

What the `@create` command actually *does* is to use `evennia.create_object`. You can do the same
thing yourself in code:

```python
    from evennia import create_object
    new_rose = create_object("typeclasses.flowers.Rose", key="MyRose")
```

(The `@create` command will auto-append the most likely path to your typeclass, if you enter the
call manually you have to give the full path to the class. The `create.create_object` function is
powerful and should be used for all coded object creating (so this is what you use when defining
your own building commands). Check out the `ev.create_*` functions for how to build other entities
like [Scripts](./Scripts.md)).

This particular Rose class doesn't really do much, all it does it make sure the attribute
`desc`(which is what the `look` command looks for) is pre-set, which is pretty pointless since you
will usually want to change this at build time (using the `@desc` command or using the
[Spawner](./Prototypes.md)). The `Object` typeclass offers many more hooks that is available
to use though - see next section.

## Properties and functions on Objects

Beyond the properties assigned to all [typeclassed](./Typeclasses.md) objects (see that page for a list
of those), the Object also has the following custom properties:

- `aliases` - a handler that allows you to add and remove aliases from this object. Use
`aliases.add()` to add a new alias and `aliases.remove()` to remove one.
- `location` - a reference to the object currently containing this object.
- `home` is a backup location. The main motivation is to have a safe place to move the object to if
its `location` is destroyed. All objects should usually have a home location for safety.
- `destination` - this holds a reference to another object this object links to in some way. Its
main use is for [Exits](./Objects.md#exits), it's otherwise usually unset.
- `nicks` - as opposed to aliases, a [Nick](./Nicks.md) holds a convenient nickname replacement for a
real name, word or sequence, only valid for this object. This mainly makes sense if the Object is
used as a game character - it can then store briefer shorts, example so as to quickly reference game
commands or other characters. Use nicks.add(alias, realname) to add a new one.
- `account` - this holds a reference to a connected [Account](./Accounts.md) controlling this object (if
any). Note that this is set also if the controlling account is *not* currently online - to test if
an account is online, use the `has_account` property instead.
- `sessions` - if `account` field is set *and the account is online*, this is a list of all active
sessions (server connections) to contact them through (it may be more than one if multiple
connections are allowed in settings).
- `has_account` - a shorthand for checking if an *online* account is currently connected to this
object.
- `contents` - this returns a list referencing all objects 'inside' this object (i,e. which has this
object set as their `location`).
- `exits` - this returns all objects inside this object that are *Exits*, that is, has the
`destination` property set.

The last two properties are special:

- `cmdset` - this is a handler that stores all [command sets](./Command-Sets.md) defined on the
object (if any).
- `scripts` - this is a handler that manages [Scripts](./Scripts.md) attached to the object (if any).

The Object also has a host of useful utility functions. See the function headers in
`src/objects/objects.py` for their arguments and more details.

- `msg()` - this function is used to send messages from the server to an account connected to this
object.
- `msg_contents()` - calls `msg` on all objects inside this object.
- `search()` - this is a convenient shorthand to search for a specific object, at a given location
or globally. It's mainly useful when defining commands (in which case the object executing the
command is named `caller` and one can do `caller.search()` to find objects in the room to operate
on).
- `execute_cmd()` - Lets the object execute the given string as if it was given on the command line.
- `move_to` - perform a full move of this object to a new location.  This is the main move method
and will call all relevant hooks, do all checks etc.
- `clear_exits()` - will delete all [Exits](./Objects.md#exits) to *and* from this object.
- `clear_contents()` - this will not delete anything, but rather move all contents (except Exits) to
their designated `Home` locations.
- `delete()` - deletes this object, first calling `clear_exits()` and
    `clear_contents()`.

The Object Typeclass defines many more *hook methods* beyond `at_object_creation`. Evennia calls
these hooks at various points.  When implementing your custom objects, you will inherit from the
base parent and overload these hooks with your own custom code. See `evennia.objects.objects` for an
updated list of all the available hooks or the [API for DefaultObject here](evennia.objects.objects.DefaultObject).

## Subclasses of `Object`

There are three special subclasses of *Object* in default Evennia - *Characters*, *Rooms* and
*Exits*. The reason they are separated is because these particular object types are fundamental,
something you will always need and in some cases requires some extra attention in order to be
recognized by the game engine (there is nothing stopping you from redefining them though). In
practice they are all pretty similar to the base Object.

### Characters

Characters are objects controlled by [Accounts](./Accounts.md). When a new Account
logs in to Evennia for the first time, a new `Character` object is created and
the Account object is assigned to the `account` attribute. A `Character` object
must have a [Default Commandset](./Command-Sets.md) set on itself at
creation, or the account will not be able to issue any commands! If you just
inherit your own class from `evennia.DefaultCharacter` and make sure to use
`super()` to call the parent methods you should be fine. In
`mygame/typeclasses/characters.py` is an empty `Character` class ready for you
to modify.

### Rooms

*Rooms* are the root containers of all other objects. The only thing really separating a room from
any other object is that they have no `location` of their own and that default commands like `@dig`
creates objects of this class - so if you want to expand your rooms with more functionality, just
inherit from `ev.DefaultRoom`. In `mygame/typeclasses/rooms.py` is an empty `Room` class ready for
you to modify.

### Exits

*Exits* are objects connecting other objects (usually *Rooms*) together. An object named *North* or
*in* might be an exit, as well as *door*, *portal* or *jump out the window*. An exit has two things
that separate them from other objects. Firstly, their *destination* property is set and points to a
valid object. This fact makes it easy and fast to locate exits in the database. Secondly, exits
define a special [Transit Command](./Commands.md) on themselves when they are created. This command is
named the same as the exit object and will, when called, handle the practicalities of moving the
character to the Exits's *destination* - this allows you to just enter the name of the exit on its
own to move around, just as you would expect.

The exit functionality is all defined on the Exit typeclass, so you could in principle completely
change how exits work in your game (it's not recommended though, unless you really know what you are
doing). Exits are [locked](./Locks.md) using an access_type called *traverse* and also make use of a few
hook methods for giving feedback if the traversal fails.  See `evennia.DefaultExit` for more info.
In `mygame/typeclasses/exits.py` there is an empty `Exit` class for you to modify.

The process of traversing an exit is as follows:

1. The traversing `obj` sends a command that matches the Exit-command name on the Exit object. The
[cmdhandler](./Commands.md) detects this and triggers the command defined on the Exit. Traversal always
involves the "source" (the current location) and the `destination` (this is stored on the Exit
object).
1. The Exit command checks the `traverse` lock on the Exit object
1. The Exit command triggers `at_traverse(obj, destination)` on the Exit object.
1. In `at_traverse`, `object.move_to(destination)` is triggered. This triggers the following hooks,
in order:
    1. `obj.at_before_move(destination)` - if this returns False, move is aborted.
    1. `origin.at_before_leave(obj, destination)`
    1. `obj.announce_move_from(destination)`
    1. Move is performed by changing `obj.location` from source location to `destination`.
    1. `obj.announce_move_to(source)`
    1. `destination.at_object_receive(obj, source)`
    1. `obj.at_after_move(source)`
1. On the Exit object, `at_after_traverse(obj, source)` is triggered.

If the move fails for whatever reason, the Exit will look for an Attribute `err_traverse` on itself
and display this as an error message. If this is not found, the Exit will instead call
`at_failed_traverse(obj)` on itself. 