# Creating things

We have already created some things - dragons for example. There are many different things to create in Evennia though. In the [Typeclasses tutorial](./Beginner-Tutorial-Learning-Typeclasses.md),  we noted that there are 7 default Typeclasses coming with Evennia out of the box: 

| Evennia base typeclass | mygame.typeclasses child | description |  
| --------------- |  --------------| ------------- | 
| `evennia.DefaultObject` | `typeclasses.objects.Object` | Everything with a location |
| `evennia.DefaultCharacter` (child of `DefaultObject`) | `typeclasses.characters.Character` | Player avatars |
| `evennia.DefaultRoom` (child of `DefaultObject`) | `typeclasses.rooms.Room` | In-game locations | 
| `evennia.DefaultExit` (chld of `DefaultObject`) | `typeclasses.exits.Exit` | Links between rooms | 
| `evennia.DefaultAccount` | `typeclasses.accounts.Account` | A player account | 
| `evennia.DefaultChannel` | `typeclasses.channels.Channel` | In-game comms | 
|  `evennia.DefaultScript` | `typeclasses.scripts.Script` | Entities with no location | 

Given you have an imported Typeclass, there are four ways to create an instance of it:

- Firstly, you can call the class directly, and then `.save()` it:

        obj = SomeTypeClass(db_key=...)
        obj.save()

   This has the drawback of being two operations; you must also import the class and have to pass 
   the actual database field names, such as `db_key`  instead of `key` as keyword arguments. This is closest to how a 'normal' Python class works, but is not recommended. 
- Secondly you can use the Evennia creation helpers:

        obj = evennia.create_object(SomeTypeClass, key=...)

   This is the recommended way if you are trying to create things in Python. The first argument can either be  the class _or_ the python-path to the typeclass, like `"path.to.SomeTypeClass"`. It can also be `None` in which  case the Evennia default will be used. While all the creation methods
   are available on `evennia`, they are actually implemented in [evennia/utils/create.py](../../../api/evennia.utils.create.md). Each of  the different base classes have their own creation function, like `create_account` and `create_script` etc.
- Thirdly, you can use the `.create` method on the Typeclass itself: 

    ```python
    obj, err = SomeTypeClass.create(key=...)
    ```
	Since `.create` is a method on the typeclass, this form is useful if you want to customize how the creation process works for your custom typeclasses. Note that it returns _two_ values - the `obj` is  either the new object or `None`, in which case `err` should be a list of error-strings detailing what went wrong.
- Finally, you can create objects using an in-game command, such as

        create obj:path.to.SomeTypeClass

  As a developer you are usually best off using the other methods, but a command is usually the only way  to let regular players or builders without Python-access help build the game world. 

## Creating Objects

An [Object](../../../Components/Objects.md) is one of the most common creation-types. These are entities that inherits from `DefaultObject` at any distance. They have an existence in the game world and includes rooms, characters, exits, weapons, flower pots and castles.

    > py
    > import evennia 
    > rose = evennia.create_object(key="rose")

Since we didn't specify the `typeclass` as the first argument, the default given by `settings.BASE_OBJECT_TYPECLASS`  (`typeclasses.objects.Object` out of the box) will be used. 

The `create_object` has [a lot of options](evennia.utils.create.create_object). A more detailed example in code: 

```python 
from evennia import create_object, search_object

meadow = search_object("Meadow")[0]

lasgun = create_object("typeclasses.objects.guns.LasGun", 
					   key="lasgun", 
					   location=meadow,
					   attributes=[("desc", "A fearsome Lasgun.")])

```

Here we set the location of a weapon as well as gave it an [Attribute](../../../Components/Attributes.md) `desc`, which is what the `look` command will use when looking this and other things.

## Creating Rooms, Characters and Exits

`Characters`, `Rooms` and `Exits` are all subclasses of `DefaultObject`. So there is for example no separate `create_character`, you just create characters with `create_object` pointing to the `Character` typeclass. 

### Linking Exits and Rooms in code 

An `Exit` is a one-way link between rooms. For example, `east` could be an `Exit` between the `Forest` room and the `Meadow` room. 

    Meadow -> east -> Forest 

The `east` exit has a `key` of `east`, a `location` of `Meadow` and a `destination` of `Forest`. If you wanted to be able to go back from Forest to Meadow, you'd need to create a new `Exit`, say, `west`, where `location` is `Forest` and `destination` is `Meadow`.

    Meadow -> east -> Forest 
	Forest -> west -> Meadow

In-game you do this with `tunnel` and `dig` commands, bit if you want to ever set up these links in code, you can do it like this: 

```python
from evennia import create_object 
from mygame.typeclasses import rooms, exits 

# rooms
meadow = create_object(rooms.Room, key="Meadow")
forest = create_object(rooms.Room, key="Forest")

# exits 
create_object(exits.Exit, key="east", location=meadow, destination=forest)
create_object(exits.Exit, key="west", location=forest, destination=meadow)
```

## Creating Accounts

An [Account](../../../Components/Accounts.md) is an out-of-character (OOC) entity, with no existence in the game world. 
You can find the parent class for Accounts in `typeclasses/accounts.py`. 

Normally, you want to create the Account when a user authenticates. By default, this happens in the `create account` and `login` default commands in the `UnloggedInCmdSet`. This means that customizing this just means replacing those commands! 

So normally you'd modify those commands rather than make something from scratch. But here's the principle: 

```python 
from evennia import create_account 

new_account = create_account(
            accountname, email, password, 
            permissions=["Player"], 
            typeclass="typeclasses.accounts.MyAccount"
 )
```
The inputs are usually taken from the player via the command. The `email` must be given, but can be `None` if you are not using it. The `accountname` must be globally unique on the server. The `password` is stored encrypted in the database.  If `typeclass` is not given, the `settings.BASE_ACCOUNT_TYPECLASS` will be used (`typeclasses.accounts.Account`). 


## Creating Channels 

A [Channel](../../../Components/Channels.md) acts like a switchboard for sending in-game messages between users; like an IRC- or discord channel but inside the game. 

Users interact with channels via the `channel` command: 

	channel/all 
	channel/create channelname 
	channel/who channelname 
	channel/sub channel name 
    ...
	(see 'help channel')

If a channel named, say, `myguild` exists, a user can send a message to it just by writing the channel name: 

	> myguild Hello! I have some questions ... 

Creating channels follows a familiar syntax: 

```python 
from evennia import create_channel

new_channel = create_channel(channelname)
```

Channels can also be auto-created by the server by setting the `DEFAULT_CHANNELS` setting. See [Channels documentation](../../../Components/Channels.md) for details. 


## Creating Scripts 

A [Script](../../../Components/Scripts.md) is an entity that has no in-game location. It can be used to store arbitrary data and is often used for game systems that need persistent storage but which you can't 'look' at in-game. Examples are economic systems, weather and combat handlers. 

Scripts are multi-use and depending on what they do, a given script can either be 'global' or be attached "to" another object (like a Room or Character). 

```python 
from evennia import create_script, search_object 
# global script 
new_script = create_script("typeclasses.scripts.MyScript", key="myscript")

# on-object script 
meadow = search_object("Meadow")[0]
new_script = create_script("typeclasses.scripts.MyScripts", 
						   key"myscript2", obj=meadow)

```

A convenient way to create global scripts is define them in the `GLOBAL_SCRIPTS` setting; Evennia will then make sure to initialize them. Scripts also have an optional 'timer' component. See the dedicated [Script](../../../Components/Scripts.md) documentation for more info.

## Conclusion 

Any game will need peristent storage of data. This was a quick run-down of how to create each default type of typeclassed entity.  If you make your own typeclasses (as children of the default ones), you create them in the same way. 

Next we'll learn how to find them again by _searching_ for them in the database.




