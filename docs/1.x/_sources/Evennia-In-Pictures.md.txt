# Evennia in pictures 

```{sidebar}
This is _not_ an exhaustive overview. Think of it as a snapshot of some interesting things to start looking into.
```

This article tries to give a high-level overview of the Evennia server and some of its moving parts. It should hopefully give a better understanding of how everything hangs together. 

<div style="clear: right;"></div>

## The two main Evennia pieces
![evennia portal and server][image1]

What you see in this figure is the part of Evennia that you download from us. It will _not_ start a game on its own. We'll soon create the missing 'jigsaw puzzle piece'. But first, let's see what we have.

First, you'll notice that Evennia has two main components - the [Portal and Server](Components/Portal-And-Server.md). These are separate processes. 

The Portal tracks all connections to the outside world and understands Telnet protocols, websockets, SSH and so on. It knows nothing about the database or the game state. Data sent between the Portal and the Server is protocol-agnostic, meaning the Server sends/receives the same data regardless of how the user is connected. Hiding behind the Portal also means that the Server can be completely rebooted without anyone getting disconnected.

The Server is the main “mud driver” and handles everything related to the game world and its database. It's asynchronous and uses [Twisted](http://twistedmatrix.com/trac/). 

In the same process of the Server is also the Evennia [Web Server](Components/Webserver.md) . This serves the game’s website. 
<div style="clear: right;"></div>

### Initializing the game folder

![creating the game folder][image2]

After [installing evennia](Setup/Installation.md) you will have the `evennia` command available. Using this you create a game directory (let's call it `mygame`). This is the darker grey piece in this figure. It was missing previously. This is where you will create your dream game!

During initialization, Evennia will create Python module templates in `mygame/` and link up all configurations to make mygame a fully functioning, if empty, game, ready to start extending.

As part of the intialization, you'll create the database and then start the server. From this point on, your new game is up and running and you can connect to your new game with telnet on localhost:4000 or by pointing your browser to http://localhost:4001.

Now, our new mygame world needs Characters, locations, items and more! 

## The database 

![image3][image3]

Evennia is fully persistent and abstracts its database in Python using [Django](https://www.djangoproject.com/). The database tables are few and generic, each represented by a single Python class. As seen in this figure, the example `ObjectDB` Python class represents one database table. The properties on the class are the columns (fields) of the table. Each row is an instance of the class (one entity in the game).

Among the example columns shown is the key (name) of the `ObjectDB` entity as well as a [Foreign key](https://en.wikipedia.org/wiki/Foreign_key)-relationship for its current “location”. 

From the figure we can see that _Trigger_ is in the _Dungeon_, carrying his trusty crossbow _Old Betsy_!

The `db_typeclass_path` is an important field. This is a python-style path and tells Evennia which subclass of `ObjectDB` is actually representing this entity. This is the core of Evennia's [Typeclass system](Components/Typeclasses.md), which allows you to work with database entities using normal Python.

### From database to Python

![image4][image4]

Here we see the (somewhat simplified) Python class inheritance tree that you as an Evennia developer will see, along with the three instanced entities.

[Objects](Components/Objects.md) represent stuff you will actually see in-game and its child classes implement all the handlers, helper code and the hook methods that Evennia makes use of. In your `mygame/` folder you just import these and overload the things you want to modify. In this way, the `Crossbow` is modified to do the stuff only crossbows can do and `CastleRoom` adds whatever it is that is special about rooms in the castle.

When creating a new entity in-game, a new row will automatically be created in the database table and then `Trigger` will appear in-game! If we, in code, search the database for Trigger, we will get an instance of the [Character](Components/Objects.md#characters) class back - a Python object we can work with normally.

Looking at this you may think that you will be making a lot of classes for every different object in the game. Your exact layout is up to you but Evennia also offers other ways to customize each individual object. Read on. 

### Attributes

![image5][image5]

The [Attribute](Components/Attributes.md) is another class directly tied to the database behind the scenes. Each `Attribute` basically has a key, a value and a ForeignKey relation to another `ObjectDB`. 

An `Attribute` serializes Python constructs into the database, meaning you can store basically any valid Python, like the dictionary of skills in this image. The “strength” and “skills” Attributes will henceforth be reachable directly from the _Trigger_ object. This (and a few other resources) allow you to create individualized entities while only needing to create classes for those that really behave fundamentally different.

<div style="clear: right;"></div>

## Controlling the action

![image6][image6]

_Trigger_ is most likely played by a human. This human connects to the game via one or more [Sessions](Components/Sessions.md), one for each client they connect with.

Their account on `mygame` is represented by a [Account](Components/Accounts.md) entity. The `AccountDB` holds the password and other account info but has no existence in the game world. Through the `Account` entity, `Sessions` can control (“puppet”) one or more `Object` entities in-game.

In this figure, a user is connected to the game with three `Session`s simultaneously. They are logged in to their player `Account` named _Richard_. Through these `Session`s they are simultaneously puppeting the in-game entities _Trigger_ and _Sir Hiss_. Evennia can be configured to allow or disallow a range of different [Connection Styles](Concepts/Connection-Styles.md) like this.

### Commands

![image7][image7]

For users to be able to control their game entities and actually play the game, they need to be able to send [Commands](Components/Commands.md). 

A `Command` can be made to represent anything a user can input actively to the game, such as the `look` command, `get`, `quit`, `emote` and so on.

Each `Command` handles both argument parsing and execution. Since each Command is described with a normal Python class, it means that you can implement parsing once and then just have the rest of your commands inherit the effect. In the above figure, the `DIKUCommand` parent class implements parsing of all the syntax common for all DIKU-style commands so `CmdLook` and others won’t have to.

### Command Sets 

![image8][image8]

All Evennia Commands are are always joined together in `CommandSet`s. These are containers that can hold many `Command` instances. A given `Command` class can contribute instances to any number of `CommandSet`s. These sets are always associated with game entities.

In this figure, _Trigger_ has received a `CommandSet` with a bunch of useful commands that he (and by extension his controlling `Account`/Player) can now use.

![image9][image9]

_Trigger_’s `CommandSet` is only available to himself. In this figure we put a `CommandSet` with three commands on the Dungeon room. The room itself has no use for commands but we configure this set to affect those _inside it_ instead. Note that we let these be _different versions_ of these commands (hence the different color)! We’ll explain why below.

<div style="clear: right;"></div>

### Merging Command Sets

![image10][image10]

Multiple `CommandSet`s can be dynamically (and temporarily) merged together in a similar fashion as [Set Theory](https://en.wikipedia.org/wiki/Set_theory), except the merge priority can be customized. In this figure we see a _Union_-type merger where the Commands from Dungeon of the same name temporarily override the commands from Trigger. While in the Dungeon, Trigger will be using this version of those commands. When Trigger leaves, his own `CommandSet` will be restored unharmed.

Why would we want to do this? Consider for example that the dungeon is in darkness. We can then let the Dungeon’s version of the `look` command show only the contents of the room if Trigger is carrying a light source. You might also not be able to easily get things in the room without light - you might even be fumbling randomly in your inventory!

Any number of Command Sets can be merged on the fly. This allows you to implement multiple overlapping states (like combat in a darkened room while intoxicated) without needing huge if statements for every possible combination. The merger is non-destructive, so you can remove cmdsets to get back previous states as needed.

## Now go and explore! 

This is by no means a full list of Evennia features. But it should give you a bunch of interesting concepts to read more about. 

You can find a lot more detail in the  [Core Components](Components/Components-Overview.md) and [Core Concepts](Concepts/Concepts-Overview.md) sections of this manual.  If you haven't read it already, you should also check out the [Evennia Introduction](./Evennia-Introduction.md). 

[image1]: https://2.bp.blogspot.com/-0-oir21e76k/W3kaUuGrg3I/AAAAAAAAJLU/qlQWmXlAiGUz_eKG_oYYVRf0yP6KVDdmQCEwYBhgL/s1600/Evennia_illustrated_fig1.png
[image2]: https://4.bp.blogspot.com/-TuLk-PIVyK8/W3kaUi-e-MI/AAAAAAAAJLc/DA9oMA6m5ooObZlf0Ao6ywW1jHqsPQZAQCEwYBhgL/s1600/Evennia_illustrated_fig2.png
[image3]: https://3.bp.blogspot.com/-81zsySVi_EE/W3kaVRn4IWI/AAAAAAAAJLc/yA-j1Nwy4H8F28BF403EDdCquYZ9sN4ZgCEwYBhgL/s1600/Evennia_illustrated_fig3.png
[image4]: https://2.bp.blogspot.com/--4_MqVdHj8Q/W3kaVpdAZKI/AAAAAAAAJLk/jvTsuBBUlkEbBCaV9vyIU0IWiuF6PLsSwCEwYBhgL/s1600/Evennia_illustrated_fig4.png
[image5]: https://3.bp.blogspot.com/-6ulv5T_gUCI/W3kaViWBBfI/AAAAAAAAJLU/0NqeAsz3YVsQKwpODzsmjzR-7tICw1pTQCEwYBhgL/s1600/Evennia_illustrated_fig5.png
[image6]: https://4.bp.blogspot.com/-u-npXjlq6VI/W3kaVwAoiUI/AAAAAAAAJLY/T9bhrzhJJuQwTR8nKHH9GUxQ74hyldKOgCEwYBhgL/s1600/Evennia_illustrated_fig6.png
[image7]: https://3.bp.blogspot.com/-_RM9-Pb2uKg/W3kaWIs4ndI/AAAAAAAAJLc/n45Hcvk1PiYhNdBbAAr_JjkebRVReffTgCEwYBhgL/s1600/Evennia_illustrated_fig7.png
[image8]: https://2.bp.blogspot.com/-pgpYPsd4CLM/W3kaWG2ffuI/AAAAAAAAJLg/LKl4m4-1xkYxVA7JXXuVP28Q9ZqhNZXTACEwYBhgL/s1600/Evennia_illustrated_fig8.png
[image9]: https://3.bp.blogspot.com/-acmVo7kUZCk/W3kaWZWlT0I/AAAAAAAAJLk/nnFrNaq_TNoO08MDleadwhHfVQLdO74eACEwYBhgL/s1600/Evennia_illustrated_fig9.png
[image10]: https://4.bp.blogspot.com/--lixKOYjEe4/W3kaUl9SFXI/AAAAAAAAJLQ/tCGd-dFhZ8gfLH1HAsQbZdaIS_OQuvU3wCEwYBhgL/s1600/Evennia_illustrated_fig10.png
