# Objects

**Message-path:**
```
┌──────┐ │   ┌───────┐    ┌───────┐   ┌──────┐
│Client├─┼──►│Session├───►│Account├──►│Object│
└──────┘ │   └───────┘    └───────┘   └──────┘
                                         ^
```

All in-game objects in Evennia, be it characters, chairs, monsters, rooms or hand grenades are jointly referred to as an Evennia *Object*. An Object is generally something you can look and interact with in the game world. When a message travels from the client, the Object-level is the last stop. 

Objects form the core of Evennia and is probably what you'll spend most time working with. Objects are [Typeclassed](./Typeclasses.md) entities.

An Evennia Object is, by definition, a Python class that includes  [evennia.objects.objects.DefaultObject](evennia.objects.objects.DefaultObject) among its parents. Evennia defines several subclasses of `DefaultObject`:

- `Object` - the base in-game entity. Found in `mygame/typeclasses/objects.py`. Inherits directly from `DefaultObject`.
- [Characters](./Characters.md) -  the normal in-game Character, controlled by a player. Found in  `mygame/typeclasses/characters.py`. Inherits from `DefaultCharacter`, which is turn a child of `DefaultObject`.
- [Rooms](./Rooms.md) - a location in the game world. Found in `mygame/typeclasses/rooms.py`. Inherits from `DefaultRoom`, which is in turn a child of `DefaultObject`).
- [Exits](./Exits.md) - represents a one-way connection to another location. Found in `mygame/typeclasses/exits.py` (inherits from `DefaultExit`, which is in turn a child of `DefaultObject`).

## Object

**Inheritance Tree:**
```
┌─────────────┐
│DefaultObject│
└──────▲──────┘
       │       ┌────────────┐
       │ ┌─────►ObjectParent│
       │ │     └────────────┘
     ┌─┴─┴──┐
     │Object│
     └──────┘
```

> For an explanation of `ObjectParent`, see next section.

The `Object` class is meant to be used as the basis for creating things that are neither characters, rooms or exits - anything from weapons and armour, equipment and houses can be represented by extending the Object class. Depending on your game, this also goes for NPCs and monsters (in some games you may want to treat NPCs as just an un-puppeted [Character](./Characters.md) instead). 

You should not use Objects for game _systems_. Don't use an 'invisible' Object for tracking weather, combat, economy or guild memberships - that's what [Scripts](./Scripts.md) are for. 

##  ObjectParent - Adding common functionality

`Object`,  as well as `Character`, `Room` and `Exit` classes all additionally inherit from `mygame.typeclasses.objects.ObjectParent`.

`ObjectParent` is an empty 'mixin' class. You can add stuff to this class that you want _all_ in-game entities to have.

Here is an example: 

```python
# in mygame/typeclasses/objects.py
# ... 

from evennia.objects.objects import DefaultObject 

class ObjectParent:
    def at_pre_get(self, getter, **kwargs):
       # make all entities by default un-pickable
      return False
```

Now all of `Object`, `Exit`. `Room` and `Character` default to not being able to be picked up using the `get` command.

## Working with children of DefaultObject

This functionality is shared by all sub-classes of `DefaultObject`. You can easily add your own in-game behavior by either modifying one of the typeclasses in  your game dir or by inheriting further from them.  

You can put your new typeclass directly in the relevant module, or you could organize your code in some other way. Here we assume we make a new module `mygame/typeclasses/flowers.py`: 

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
   
Now you just need to point to the class *Rose* with the `create` command to make a new rose:

     create/drop MyRose:flowers.Rose

What the `create` command actually *does* is to use the [evennia.create_object](evennia.utils.create.create_object)  function. You can do the same thing yourself in code:

```python
    from evennia import create_object
    new_rose = create_object("typeclasses.flowers.Rose", key="MyRose")
```

(The `create` command will auto-append the most likely path to your typeclass, if you enter the call manually you have to give the full path to the class. The `create.create_object` function is powerful and should be used for all coded object creating (so this is what you use when defining your own building commands). 

This particular Rose class doesn't really do much, all it does it make sure the attribute `desc`(which is what the `look` command looks for) is pre-set, which is pretty pointless since you will usually want to change this at build time (using the `desc` command or using the [Spawner](./Prototypes.md)). 
 
### Properties and functions on Objects

Beyond the properties assigned to all [typeclassed](./Typeclasses.md) objects (see that page for a list
of those), the Object also has the following custom properties:

- `aliases` - a handler that allows you to add and remove aliases from this object. Use `aliases.add()` to add a new alias and `aliases.remove()` to remove one.
- `location` - a reference to the object currently containing this object.
- `home` is a backup location. The main motivation is to have a safe place to move the object to if its `location` is destroyed. All objects should usually have a home location for safety.
- `destination` - this holds a reference to another object this object links to in some way. Its main use is for [Exits](./Exits.md), it's otherwise usually unset.
- `nicks` - as opposed to aliases, a [Nick](./Nicks.md) holds a convenient nickname replacement for a real name, word or sequence, only valid for this object. This mainly makes sense if the Object is used as a game character - it can then store briefer shorts, example so as to quickly reference game commands or other characters. Use nicks.add(alias, realname) to add a new one.
- `account` - this holds a reference to a connected [Account](./Accounts.md) controlling this object (if any). Note that this is set also if the controlling account is *not* currently online - to test if an account is online, use the `has_account` property instead.
- `sessions` - if `account` field is set *and the account is online*, this is a list of all active sessions (server connections) to contact them through (it may be more than one if multiple connections are allowed in settings).
- `has_account` - a shorthand for checking if an *online* account is currently connected to this object.
- `contents` - this returns a list referencing all objects 'inside' this object (i,e. which has this object set as their `location`).
- `exits` - this returns all objects inside this object that are *Exits*, that is, has the `destination` property set.
- `appearance_template` - this helps formatting the look of the Object when someone looks at it (see next section).l
- `cmdset` - this is a handler that stores all [command sets](./Command-Sets.md) defined on the object (if any).
- `scripts` - this is a handler that manages [Scripts](./Scripts.md) attached to the object (if any).

The Object also has a host of useful utility functions. See the function headers in `src/objects/objects.py` for their arguments and more details.

- `msg()` - this function is used to send messages from the server to an account connected to this object.
- `msg_contents()` - calls `msg` on all objects inside this object.
- `search()` - this is a convenient shorthand to search for a specific object, at a given location or globally. It's mainly useful when defining commands (in which case the object executing the command is named `caller` and one can do `caller.search()` to find objects in the room to operate on).
- `execute_cmd()` - Lets the object execute the given string as if it was given on the command line.
- `move_to` - perform a full move of this object to a new location.  This is the main move method and will call all relevant hooks, do all checks etc.
- `clear_exits()` - will delete all [Exits](./Exits.md) to *and* from this object.
- `clear_contents()` - this will not delete anything, but rather move all contents (except Exits) to their designated `Home` locations.
- `delete()` - deletes this object, first calling `clear_exits()` and `clear_contents()`.
- `return_appearance`  is the main hook letting the object visually describe itself.

The Object Typeclass defines many more *hook methods* beyond `at_object_creation`. Evennia calls these hooks at various points.  When implementing your custom objects, you will inherit from the base parent and overload these hooks with your own custom code. See `evennia.objects.objects` for an updated list of all the available hooks or the [API for DefaultObject here](evennia.objects.objects.DefaultObject).


## Changing an Object's appearance

When you type `look <obj>`, this is the sequence of events that happen: 

1. The command checks if the `caller` of the command (the 'looker') passes the `view` [lock](./Locks.md) of the target `obj`. If not, they will not find anything to look at (this is how you make objects invisible). 
1. The `look` command calls `caller.at_look(obj)` - that is, the `at_look` hook on the 'looker' (the caller of the command) is called to perform the look on the target object. The command will echo whatever this hook returns.
2. `caller.at_look` calls and returns the outcome of `obj.return_apperance(looker, **kwargs)`. Here `looker` is the `caller` of the command. In other words, we ask the `obj` to descibe itself to `looker`. 
3. `obj.return_appearance` makes use of its `.appearance_template` property and calls a slew of helper-hooks to populate this template. This is how the template looks by default: 

            ```python
            appearance_template = """
            {header}
            |c{name}|n
            {desc}
            {exits}{characters}{things}
            {footer}
            """```

4. Each field of the template is populated by a matching helper method (and their default returns): 
    - `name` -> `obj.get_display_name(looker, **kwargs)`  - returns `obj.name`. 
    - `desc` -> `obj.get_display_desc(looker, **kwargs)` - returns `obj.db.desc`.
    - `header` -> `obj.get_display_header(looker, **kwargs)` - empty by default.
    - `footer` -> `obj.get_display_footer(looker, **kwargs)` - empty by default.
    - `exits` -> `obj.get_display_exits(looker, **kwargs)` - a list of `DefaultExit`-inheriting objects found inside this object (usually only present if `obj` is a `Room`).
    - `characters` -> `obj.get_display_characters(looker, **kwargs)` - a list of `DefaultCharacter`-inheriting entities inside this object.
    - `things` -> `obj.get_display_things(looker, **kwargs)` - a list of all other Objects inside `obj`. 
5. `obj.format_appearance(string, looker, **kwargs)` is the last step the populated template string goes through. This can be used for final adjustments, such as stripping whitespace. The return from this method is what the user will see. 

As each of these hooks (and the template itself) can be overridden in your child class, you can customize your look extensively. You can also have objects look different depending on who is looking at them. The extra `**kwargs` are not used by default, but are there to allow you to pass extra data into the system if you need it (like light conditions etc.)