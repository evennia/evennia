This article describes the MU* development system [Evennia](http://www.evennia.com/) using pictures!   
  

_This article was originally written for [Optional Realities](http://www.optionalrealities.com/)._ 

_Since it is no longer available to read on OR, I'm reposting it in full here._
  
#### Figure 1: The parts of the Evennia library

  

[![](https://2.bp.blogspot.com/-0-oir21e76k/W3kaUuGrg3I/AAAAAAAAJLU/qlQWmXlAiGUz_eKG_oYYVRf0yP6KVDdmQCEwYBhgL/s640/Evennia_illustrated_fig1.png)](https://2.bp.blogspot.com/-0-oir21e76k/W3kaUuGrg3I/AAAAAAAAJLU/qlQWmXlAiGUz_eKG_oYYVRf0yP6KVDdmQCEwYBhgL/s1600/Evennia_illustrated_fig1.png)

  

Evennia is a game development library. What you see in Figure 1 is the part you download from us. This will not run on its own, we will soon initialize the missing “jigsaw puzzle” piece on the left. But first let’s look at what we’ve got.

  

Looking at Figure 1 you will notice that Evennia internally has two components, the Portal and the Server. These will run as separate processes.

  

The Portal tracks all connections to the outside world and understands Telnet protocols, websockets, SSH and so on. It knows nothing about the database or the game state. Data sent between the Portal and the Server is protocol-agnostic, meaning the Server sends/receives the same data regardless of how the user is connected. Hiding behind the Portal also means that the Server can be completely rebooted without anyone getting disconnected.

  

The Server is the main “mud driver” and handles everything related to the game world and its database. It's asynchronous and uses [Twisted](http://twistedmatrix.com/trac/). In the same process of the Server is also the Evennia web server component that serves the game’s website. That the Server and webserver are accessing the database in the same process allows for a consistent game state without any concerns for caching or race condition issues.

  

Now, let’s get a game going. We’ll call it mygame. Original, isn’t it?

  

#### Figure 2: The full setup for mygame

[![](https://4.bp.blogspot.com/-TuLk-PIVyK8/W3kaUi-e-MI/AAAAAAAAJLc/DA9oMA6m5ooObZlf0Ao6ywW1jHqsPQZAQCEwYBhgL/s640/Evennia_illustrated_fig2.png)](https://4.bp.blogspot.com/-TuLk-PIVyK8/W3kaUi-e-MI/AAAAAAAAJLc/DA9oMA6m5ooObZlf0Ao6ywW1jHqsPQZAQCEwYBhgL/s1600/Evennia_illustrated_fig2.png)

  

After [installing evennia](https://github.com/evennia/evennia/wiki/Getting-Started) you will have the evennia command available. Using this you create a game directory - the darker grey piece in Figure 2 that was missing previously. This is where you will create your dream game!

  

During initialization, Evennia will create Python module templates in mygame/ and link up all configurations to make mygame a fully functioning, if empty, game, ready to start extending. Two more commands will create your database and then start the server. From this point on, mygame is up and running and you can connect to your new game with telnet on localhost:4000 or by pointing your browser to http://localhost:4001.

  

Now, our new mygame world needs Characters, locations, items and more! These we commonly refer to as game entities. Let’s see how Evennia handles those.

  

#### Figure 3: The Database Abstraction of Evennia entities

[![](https://3.bp.blogspot.com/-81zsySVi_EE/W3kaVRn4IWI/AAAAAAAAJLc/yA-j1Nwy4H8F28BF403EDdCquYZ9sN4ZgCEwYBhgL/s400/Evennia_illustrated_fig3.png)](https://3.bp.blogspot.com/-81zsySVi_EE/W3kaVRn4IWI/AAAAAAAAJLc/yA-j1Nwy4H8F28BF403EDdCquYZ9sN4ZgCEwYBhgL/s1600/Evennia_illustrated_fig3.png)

Evennia is fully persistent and abstracts its database in Python using [Django](https://www.djangoproject.com/). The database tables are few and generic, each represented by a single Python class. As seen in Figure 3, the example ObjectDB Python class represents one database table. The properties on the class are the columns (fields) of the table. Each row is an instance of the class (one entity in the game).

  

Among the example columns shown is the key (name) of the ObjectDB entity as well as a [Foreign key](https://en.wikipedia.org/wiki/Foreign_key)-relationship for its current “location”. From the above we can see that Trigger is in the Dungeon, carrying his trusty crossbow Old Betsy!

  

The db_typeclass_path is an important field. This is a python-style path and tells Evennia which subclass of ObjectDB is actually representing this entity.

  

#### Figure 4: Inheriting classes to customize entities  

[![](https://2.bp.blogspot.com/--4_MqVdHj8Q/W3kaVpdAZKI/AAAAAAAAJLk/jvTsuBBUlkEbBCaV9vyIU0IWiuF6PLsSwCEwYBhgL/s400/Evennia_illustrated_fig4.png)](https://2.bp.blogspot.com/--4_MqVdHj8Q/W3kaVpdAZKI/AAAAAAAAJLk/jvTsuBBUlkEbBCaV9vyIU0IWiuF6PLsSwCEwYBhgL/s1600/Evennia_illustrated_fig4.png)

  

In Figure 4 we see the (somewhat simplified) Python class inheritance tree that you as an Evennia developer will see, along with the three instanced entities.  
  

ObjectDB represents stuff you will actually see in-game and its child classes implement all the handlers, helper code and the hook methods that Evennia makes use of. In your mygame/ folder you just import these and overload the things you want to modify. In this way, the Crossbow is modified to do the stuff only crossbows can do and CastleRoom adds whatever it is that is special about rooms in the castle.

  

When creating a new entity in-game, a new row will automatically be created in the database table and then “Trigger” will appear in-game! If we, in code, search the database for Trigger, we will get an instance of the Character class back - a Python object we can work with normally.

  

Looking at this you may think that you will be making a lot of classes for every different object in the game. Your exact layout is up to you but Evennia also offers other ways to customize each individual object, as exemplified by Figure 5.

  

#### Figure 5: Adding persistent Attributes to a game entity.

[![](https://3.bp.blogspot.com/-6ulv5T_gUCI/W3kaViWBBfI/AAAAAAAAJLU/0NqeAsz3YVsQKwpODzsmjzR-7tICw1pTQCEwYBhgL/s400/Evennia_illustrated_fig5.png)](https://3.bp.blogspot.com/-6ulv5T_gUCI/W3kaViWBBfI/AAAAAAAAJLU/0NqeAsz3YVsQKwpODzsmjzR-7tICw1pTQCEwYBhgL/s1600/Evennia_illustrated_fig5.png)

  

The Attribute is another class directly tied to the database behind the scenes. Each Attribute basically has a key, a value and a ForeignKey relation to another ObjectDB. An Attribute serializes Python constructs into the database, meaning you can store basically any valid Python, like the dictionary of skills seen in Figure 5. The “strength” and “skills” Attributes will henceforth be reachable directly from the Trigger object. This (and a few other resources) allow you to create individualized entities while only needing to create classes for those that really behave fundamentally different.  
  
  

#### Figure 6: Sessions, Players and Objects

[![](https://4.bp.blogspot.com/-u-npXjlq6VI/W3kaVwAoiUI/AAAAAAAAJLY/T9bhrzhJJuQwTR8nKHH9GUxQ74hyldKOgCEwYBhgL/s400/Evennia_illustrated_fig6.png)](https://4.bp.blogspot.com/-u-npXjlq6VI/W3kaVwAoiUI/AAAAAAAAJLY/T9bhrzhJJuQwTR8nKHH9GUxQ74hyldKOgCEwYBhgL/s1600/Evennia_illustrated_fig6.png)

  

  

Trigger is most likely played by a human. This human connects to the game via one or more Sessions, one for each client they connect with. Their account on mygame is represented by a PlayerDB entity. The PlayerDB holds the password and other account info but has no existence in the game world. Through the PlayerDB entity, Sessions can control (“puppet”) one or more ObjectDB entities in-game.

  

In Figure 6, a user is connected to the game with three Sessions simultaneously. They are logged in to their Player account Richard. Through these Sessions they are simultaneously puppeting the in-game entities Trigger and Sir Hiss. Evennia can be configured to allow or disallow a range of different gaming styles like this.

  

Now, for users to be able to control their game entities and actually play the game, they need to be able to send Commands.

  

#### Figure 7: Commands are Python classes too

[![](https://3.bp.blogspot.com/-_RM9-Pb2uKg/W3kaWIs4ndI/AAAAAAAAJLc/n45Hcvk1PiYhNdBbAAr_JjkebRVReffTgCEwYBhgL/s400/Evennia_illustrated_fig7.png)](https://3.bp.blogspot.com/-_RM9-Pb2uKg/W3kaWIs4ndI/AAAAAAAAJLc/n45Hcvk1PiYhNdBbAAr_JjkebRVReffTgCEwYBhgL/s1600/Evennia_illustrated_fig7.png)

  
Commands represent anything a user can input actively to the game, such as the look command, get, quit, emote and so on.

  

Each Command handles both argument parsing and execution. Since each Command is described with a normal Python class, it means that you can implement parsing once and then just have the rest of your commands inherit the effect. In Figure 7, the DIKUCommand parent class implements parsing of all the syntax common for all DIKU-style commands so CmdLook and others won’t have to.

  

#### Figure 8: Commands are grouped together in sets and always associated with game entities.

  

[![](https://2.bp.blogspot.com/-pgpYPsd4CLM/W3kaWG2ffuI/AAAAAAAAJLg/LKl4m4-1xkYxVA7JXXuVP28Q9ZqhNZXTACEwYBhgL/s400/Evennia_illustrated_fig8.png)](https://2.bp.blogspot.com/-pgpYPsd4CLM/W3kaWG2ffuI/AAAAAAAAJLg/LKl4m4-1xkYxVA7JXXuVP28Q9ZqhNZXTACEwYBhgL/s1600/Evennia_illustrated_fig8.png)

  
Commands in Evennia are always joined together in Command Sets. These are containers that can hold many Command instances. A given Command class can contribute Command instances to any number of Command Sets. These sets are always associated with game entities. In Figure 8, Trigger has received a Command Set with a bunch of useful commands that he (and by extension his controlling Player) can now use.

  

#### Figure 9: Command Sets can affect those around them

  

[![](https://3.bp.blogspot.com/-acmVo7kUZCk/W3kaWZWlT0I/AAAAAAAAJLk/nnFrNaq_TNoO08MDleadwhHfVQLdO74eACEwYBhgL/s400/Evennia_illustrated_fig9.png)](https://3.bp.blogspot.com/-acmVo7kUZCk/W3kaWZWlT0I/AAAAAAAAJLk/nnFrNaq_TNoO08MDleadwhHfVQLdO74eACEwYBhgL/s1600/Evennia_illustrated_fig9.png)

  

Trigger’s Command Set is only available to himself. In Figure 8 we put a Command Set with three commands on the Dungeon room. The room itself has no use for commands but we configure this set to affect those inside it instead. Note that we let these be different versions of these commands (hence the different color)! We’ll explain why below.  
  

#### Figure 10: The name Command “Set” is not just a name

  

[![](https://4.bp.blogspot.com/--lixKOYjEe4/W3kaUl9SFXI/AAAAAAAAJLQ/tCGd-dFhZ8gfLH1HAsQbZdaIS_OQuvU3wCEwYBhgL/s400/Evennia_illustrated_fig10.png)](https://4.bp.blogspot.com/--lixKOYjEe4/W3kaUl9SFXI/AAAAAAAAJLQ/tCGd-dFhZ8gfLH1HAsQbZdaIS_OQuvU3wCEwYBhgL/s1600/Evennia_illustrated_fig10.png)

  

Command Sets can be dynamically (and temporarily) merged together in a similar fashion as [Set Theory](https://en.wikipedia.org/wiki/Set_theory), except the merge priority can be customized. In Figure 10 we see a Union-type merger where the Commands from Dungeon of the same name temporarily override the commands from Trigger. While in the Dungeon, Trigger will be using this version of those commands. When Trigger leaves, his own Command Set will be restored unharmed.  
  

Why would we want to do this? Consider for example that the dungeon is in darkness. We can then let the Dungeon’s version of the look command only show the contents of the room if Trigger is carrying a light source. You might also not be able to easily get things in the room without light - you might even be fumbling randomly in your inventory!

  

Any number of Command Sets can be merged on the fly. This allows you to implement multiple overlapping states (like combat in a darkened room while intoxicated) without needing huge if statements for every possible combination. The merger is non-destructive, so you can remove cmdsets to get back previous states as needed.

  

… And that’s how many illustrations I have the stamina to draw at this time. Hopefully this quick illustrated dive into Evennia helps to clarify some of the basic features of the system!