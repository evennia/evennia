# Objects


All in-game objects in Evennia, be it characters, chairs, monsters, rooms or hand grenades are represented by an Evennia *Object*. Objects form the core of Evennia and is probably what you'll spend most time working with. Objects are [Typeclassed](../typeclasses/Typeclasses) entities.

## How to create your own object types

An Evennia Object is, per definition, a Python class that includes `evennia.DefaultObject` among its parents. In `mygame/typeclasses/objects.py` there is already a class `Object` that inherits from `DefaultObject` and that you can inherit from. You can put your new typeclass directly in that module or you could organize your code in some other way. Here we assume we make a new module `mygame/typeclasses/flowers.py`:

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
   
You could save this in the `mygame/typeclasses/objects.py` (then you'd not need to import `Object`) or you can put it in a new module. Let's say we do the latter, making a module `typeclasses/flowers.py`.  Now you just need to point to the class *Rose* with the `@create` command to make a new rose:

     @create/drop MyRose:flowers.Rose

What the `@create` command actually *does* is to use `evennia.create_object`. You can do the same thing yourself in code:

```python
    from evennia import create_object
    new_rose = create_object("typeclasses.flowers.Rose", key="MyRose")
```

(The `@create` command will auto-append the most likely path to your typeclass, if you enter the call manually you have to give the full path to the class. The `create.create_object` function is powerful and should be used for all coded object creating (so this is what you use when defining your own building commands). Check out the `ev.create_*` functions for how to build other entities like [Scripts](../scripts/Scripts)). 

This particular Rose class doesn't really do much, all it does it make sure the attribute `desc`(which is what the `look` command looks for) is pre-set, which is pretty pointless since you will usually want to change this at build time (using the `@desc` command or using the [Spawner](../spawner/spawner)). The `Object` typeclass offers many more hooks that is available to use though - see next section. 

## Properties and functions on Objects

Beyond the properties assigned to all [typeclassed](../typeclasses/Typeclasses) objects (see that page for a list of those), the Object also has the following custom properties: 

- `aliases` - a handler that allows you to add and remove aliases from this object. Use `aliases.add()` to add a new alias and `aliases.remove()` to remove one. 
- `location` - a reference to the object currently containing this object.
- `home` is a backup location. The main motivation is to have a safe place to move the object to if its `location` is destroyed. All objects should usually have a home location for safety.
- `destination` - this holds a reference to another object this object links to in some way. Its main use is for [Exits](Exit), it's otherwise usually unset.
- `nicks` - as opposed to aliases, a [Nick](../nicks/Nicks) holds a convenient nickname replacement for a real name, word or sequence, only valid for this object. This mainly makes sense if the Object is used as a game character - it can then store briefer shorts, example so as to quickly reference game commands or other characters. Use nicks.add(alias, realname) to add a new one.
- `account` - this holds a reference to a connected [Account](../accounts/Accounts) controlling this object (if any). Note that this is set also if the controlling account is *not* currently online - to test if an account is online, use the `has_account` property instead.
- `sessions` - if `account` field is set *and the account is online*, this is a list of all active sessions (server connections) to contact them through (it may be more than one if multiple connections are allowed in settings).
- `has_account` - a shorthand for checking if an *online* account is currently connected to this object.
- `contents` - this returns a list referencing all objects 'inside' this object (i,e. which has this object set as their `location`).
- `exits` - this returns all objects inside this object that are *Exits*, that is, has the `destination` property set.

The last two properties are special:

- `cmdset` - this is a handler that stores all [command sets](../commands/Commands#Command_Sets) defined on the object (if any).
- `scripts` - this is a handler that manages Scripts attached to the object (if any).

The Object also has a host of useful utility functions. See the function headers in `src/objects/objects.py` for their arguments and more details. 

- `msg()` - this function is used to send messages from the server to an account connected to this object.
- `msg_contents()` - calls `msg` on all objects inside this object.
- `search()` - this is a convenient shorthand to search for a specific object, at a given location or globally. It's mainly useful when defining commands (in which case the object executing the command is named `caller` and one can do `caller.search()` to find objects in the room to operate on).
- `execute_cmd()` - Lets the object execute the given string as if it was given on the command line.
- `move_to` - perform a full move of this object to a new location.  This is the main move method and will call all relevant hooks, do all checks etc.
- `clear_exits()` - will delete all [Exits](Exit) to *and* from this object.
- `clear_contents()` - this will not delete anything, but rather move all contents (except Exits) to their designated `Home` locations.
- `delete()` - deletes this object, first calling `clear_exits()` and
    `clear_contents()`.

The Object Typeclass defines many more *hook methods* beyond `at_object_creation`. Evennia calls these hooks at various points.  When implementing your custom objects, you will inherit from the base parent and overload these hooks with your own custom code. See `evennia.objects.objects` for an updated list of all the available hooks or the [API for DefaultObject here]().

## Subclasses of `Object`

There are three special subclasses of *Object* in default Evennia - [*Characters*](Character), [*Rooms*](Room) and [*Exits*](Exit). 

The reason they are separated is because these particular object types are fundamental, something you will always need and in some cases requires some extra attention in order to be recognized by the game engine (there is nothing stopping you from redefining them though). In practice they are all pretty similar to the base Object.  



