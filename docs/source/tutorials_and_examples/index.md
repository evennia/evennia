# Tutorials


Before continuing to read these tutorials (and especially before you start to code or build your game in earnest) it's strongly recommended that you read the [Evennia coding introduction](Coding-Introduction) as well as the [Planning your own game](Game-Planning) pages first. 

Please note that it's not within the scope of our tutorials to teach you basic Python. If you are new to the language, expect to have to look up concepts you are unfamiliar with. Usually a quick internet search will give you all info you need. Furthermore, our tutorials tend to focus on implementation and concepts. As such they give only brief explanations to use Evennia features while providing ample links to the relevant detailed documentation.

The main information resource for builders is the [Builder Documentation](building/Builder-Docs). Coders should refer to the [Developer Central](Developer-Central) for further information.

### Building

_Help with populating your game world._

- [Tutorial: Building Quick-start](building/building-overview) - helps you build your first rocks and crates using Evennia's defaults.
- [Tutorial: Understanding Color Tags](ui/Understanding-Color-Tags)- explains how you color your game's text.
- [Introduction: The Tutorial World](contribs/Tutorial-World-Introduction) - this introduces the full (if small) solo-adventure game that comes with the Evennia distribution. It is useful both as an example of building and of coding. 
- [Tutorial: Building a Giant Mech](objects/Building-a-mech-tutorial) - this starts as a building tutorial and transitions into writing code. 

### General Development tutorials

_General code practices for newbie game developers._

To use Evennia, you will need basic understanding of Python [modules](http://docs.python.org/3.7/tutorial/modules.html), [variables](http://www.tutorialspoint.com/python/python_variable_types.htm), [conditional statements](http://docs.python.org/tutorial/controlflow.html#if-statements), [loops](http://docs.python.org/tutorial/controlflow.html#for-statements), [functions](http://docs.python.org/tutorial/controlflow.html#defining-functions), [lists, dictionaries, list comprehensions](http://docs.python.org/tutorial/datastructures.html) and [string formatting](http://docs.python.org/tutorial/introduction.html#strings). You should also have a basic understanding of [object-oriented programming](http://www.tutorialspoint.com/python/python_classes_objects.htm) and what Python [Classes](http://docs.python.org/tutorial/classes.html) are.

- [Python tutorials for beginners](https://wiki.python.org/moin/BeginnersGuide/NonProgrammers) - external link with tutorials for those not familiar with coding in general or Python in particular.
- [Tutorial: Version Control](python/Version-Control) - use GIT to organize your code both for your own game project and for contributing to Evennia.  
- MIT offers free courses in many subjects.  Their [Introduction to Computer Science and Programming](https://ocw.mit.edu/courses/electrical-engineering-and-computer-science/6-00sc-introduction-to-computer-science-and-programming-spring-2011/) uses Python as its language of choice.  Longer path, but more in-depth.  Definitely worth a look.

### Coding - First Step tutorials

_Starting tutorials for you who are new to developing with Evennia._

- [Python basic introduction](python/Python-basic-introduction) (part 1) - Python intro using Evennia.
- [Python basic introduction](python/Python-basic-tutorial-part-two) (part 2) - More on objects, classes and finding where things are. 
- [Tutorial: First Steps Coding](python/First%20Steps%20Coding) - learn each basic feature on their own through step-by-step instruction. 
- [Tutorial: A small first game](systems/Tutorial-for-basic-MUSH-like-game) - learn basic features as part of building a small but working game from scratch.
- [Tutorial: Adding new commands](../../evennia_core/system/commands/Commands/Adding-Command-Tutorial) - focuses specifically on how to add new commands.
- [Tutorial: Parsing command argument](../../evennia_core/system/commands/Commands/parsing-command-arguments).
- [Tutorial: Adding new objects](objectsAdding-Object-Typeclass-Tutorial) - focuses specifically on how to add new objects.
- [Tutorial: Searching objects in the database](objects/Tutorial-Searching-For-Objects) - how to find existing objects so you can operate on them.


### Custom objects and typeclasses

_Examples of designing new objects for your game world_

- [Tutorial: Rooms with Weather](rooms/Weather-Tutorial)
- [Tutorial: Aggressive NPC's](npcs/Tutorial-Aggressive-NPCs)
- [Tutorial: Listening NPC's](npcs/Tutorial-NPCs-listening)
- [Tutorial: Creating a vehicle](objects/Tutorial-Vehicles)
- [Tutorial: Making an NPC shop](npcs/NPC-shop-Tutorial)
- [Tutorial: Implementing a Static In Game Map](rooms/Static-In-Game-Map)
- [Tutorial: Implementing a Dynamic In Game Map](rooms/Dynamic-In-Game-Map)
- [Tutorial: Writing your own unit tests](python/Unit-Testing#testing-for-game-development-mini-tutorial)

### Game mechanics tutorials

_Creating the underlying game mechanics of game play._

- [Hints: Implementing a game rule system](systems/Implementing-a-game-rule-system)
- [Tutorial: Implementing a Combat system](systems/Turn-based-Combat-System)
- [Tutorial: Evennia for running tabletop rpgs](systems/Evennia-for-roleplaying-sessions)

### Miscellaneous system tutorials

_Design various game systems and achieve particular effects._

- [FAQ](Coding-FAQ): A place for users to enter their own hints on achieving various goals in Evennia.
- [Tutorial: Adding a Command prompt](../../evennia_core/system/commands/Commands/Command-Prompt)
- [Tutorial: Creating a Zoning system](rooms/Zones)
- [Tutorial: Letting players manually configure color settings](ui/Manually-Configuring-Color)
- [Hints: Asking the user a question and dealing with the result](EvMenu#ask-for-simple-input)
- [Hints: Designing commands that take time to finish](../../evennia_core/system/commands/Commands/Command-Duration)
- [Hints: Adding cooldowns to commands](../../evennia_core/system/commands/Commands/Command-Cooldown)
- [Tutorial: Mass and weight for objects](objects/Mass-and-weight-for-objects)
- [Hints: Show a different message when trying a non-existent exit](exits/Default-Exit-Errors)
- [Tutorial: Make automatic tweets of game statistics](communications/Tutorial-Tweeting-Game-Stats)
- [Tutorial: Handling virtual time in your game](systems/Gametime-Tutorial)
- [Tutorial: Setting up a coordinate system for rooms](rooms/Coordinates)
- [Tutorial: customize the way channels and channel commands work in your game](channels/Customize-channels)
- [Tutorial: Adding unit tests to your game project](python/Unit-Testing#testing-for-game-development-mini-tutorial)

### Contrib

_This section contains tutorials linked with contribs.  These contribs can be used in your game, but you'll need to install them explicitly.  They add common features that can earn you time in implementation._

- [list of contribs](https://github.com/evennia/evennia/blob/master/evennia/contrib/README.md)

- [In-game Python: dialogues with characters](npcs/Dialogues-in-events).
- [In-game Python: a voice-operated elevator](events/A-voice-operated-elevator-using-events).

### Web tutorials

_Expanding Evennia's web presence._

- [Tutorial: Add a new web page](web/Add-a-simple-new-web-page) - simple example to see how Django pages hang together.
- [Tutorial: Website customization](web/Web-Tutorial) - learn how to start customizing your game's web presence.
- [Tutorial: Bootstrap & Evennia](web/Bootstrap-&-Evennia) - Learn more about Bootstrap, the current CSS framework Evennia is using 
- [Tutorial: Build a web page displaying a game character](web/Web-Character-View-Tutorial) - make a way to view your character on the web page.
- [Tutorial: access your help system from your website](builder/Help-System-Tutorial)
- [Tutorial: add a wiki on your website](web/Add-a-wiki-on-your-website)
- [Tutorial: Web Character Generation](web/Web-Character-Generation/) - make a web-based character application form.
- [Tutorial: Bootstrap Components and Utilities](web/Bootstrap-Components-and-Utilities) - Describes some common Bootstrap Components and Utilities that might help in designing for Evennia

### Evennia for [Engine]-Users

_Hints for new users more familiar with other game engines._

- [Evennia for Diku Users](Evennia-for-Diku-Users) - read up on the differences between Diku style muds and Evennia.
- [Evennia for MUSH Users](Evennia-for-MUSH-Users) - an introduction to Evennia for those accustomed to MUSH-style servers.
