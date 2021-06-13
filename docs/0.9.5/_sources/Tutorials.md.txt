# Tutorials


Before continuing to read these tutorials (and especially before you start to code or build your
game in earnest) it's strongly recommended that you read the
[Evennia coding introduction](./Coding-Introduction) as well as the [Planning your own game](./Game-Planning) pages first.

Please note that it's not within the scope of our tutorials to teach you basic Python. If you are
new to the language, expect to have to look up concepts you are unfamiliar with. Usually a quick
internet search will give you all info you need. Furthermore, our tutorials tend to focus on
implementation and concepts. As such they give only brief explanations to use Evennia features while
providing ample links to the relevant detailed documentation.

The main information resource for builders is the [Builder Documentation](./Builder-Docs). Coders
should refer to the [Developer Central](./Developer-Central) for further information.

### Building

_Help with populating your game world._

- [Tutorial: Building Quick-start](./Building-Quickstart) - helps you build your first rocks and
crates using Evennia's defaults.
- [Tutorial: Understanding Color Tags](./Understanding-Color-Tags)- explains how you color your game's
text.
- [Introduction: The Tutorial World](./Tutorial-World-Introduction) - this introduces the full (if
small) solo-adventure game that comes with the Evennia distribution. It is useful both as an example
of building and of coding.
- [Tutorial: Building a Giant Mech](./Building-a-mech-tutorial) - this starts as a building tutorial
and transitions into writing code.

### General Development tutorials

_General code practices for newbie game developers._

To use Evennia, you will need basic understanding of Python
[modules](http://docs.python.org/3.7/tutorial/modules.html),
[variables](http://www.tutorialspoint.com/python/python_variable_types.htm), [conditional statements](http://docs.python.org/tutorial/controlflow.html#if-statements),
[loops](http://docs.python.org/tutorial/controlflow.html#for-statements),
[functions](http://docs.python.org/tutorial/controlflow.html#defining-functions), [lists, dictionaries, list comprehensions](http://docs.python.org/tutorial/datastructures.html) and [string formatting](http://docs.python.org/tutorial/introduction.html#strings). You should also have a basic
understanding of [object-oriented programming](http://www.tutorialspoint.com/python/python_classes_objects.htm) and what Python
[Classes](http://docs.python.org/tutorial/classes.html) are.

- [Python tutorials for beginners](https://wiki.python.org/moin/BeginnersGuide/NonProgrammers) -
external link with tutorials for those not familiar with coding in general or Python in particular.
- [Tutorial: Version Control](./Version-Control) - use GIT to organize your code both for your own
game project and for contributing to Evennia.
- MIT offers free courses in many subjects.  Their [Introduction to Computer Science and Programming](https://ocw.mit.edu/courses/electrical-engineering-and-computer-science/6-00sc-
introduction-to-computer-science-and-programming-spring-2011/) uses Python as its language of
choice.  Longer path, but more in-depth.  Definitely worth a look.

### Coding - First Step tutorials

_Starting tutorials for you who are new to developing with Evennia._

- [Python basic introduction](./Python-basic-introduction) (part 1) - Python intro using Evennia.
- [Python basic introduction](./Python-basic-tutorial-part-two) (part 2) - More on objects, classes
and finding where things are.
- [Tutorial: First Steps Coding](./First-Steps-Coding) - learn each basic feature on their own through
step-by-step instruction.
- [Tutorial: A small first game](./Tutorial-for-basic-MUSH-like-game) - learn basic features as part
of building a small but working game from scratch.
- [Tutorial: Adding new commands](./Adding-Command-Tutorial) - focuses specifically on how to add new
commands.
- [Tutorial: Parsing command argument](./Parsing-command-arguments,-theory-and-best-practices).
- [Tutorial: Adding new objects](./Adding-Object-Typeclass-Tutorial) - focuses specifically on how to
add new objects.
- [Tutorial: Searching objects in the database](./Tutorial-Searching-For-Objects) - how to find
existing objects so you can operate on them.


### Custom objects and typeclasses

_Examples of designing new objects for your game world_

- [Tutorial: Rooms with Weather](./Weather-Tutorial)
- [Tutorial: Aggressive NPC's](./Tutorial-Aggressive-NPCs)
- [Tutorial: Listening NPC's](./Tutorial-NPCs-listening)
- [Tutorial: Creating a vehicle](./Tutorial-Vehicles)
- [Tutorial: Making an NPC shop](./NPC-shop-Tutorial) (also advanced [EvMenu](./EvMenu) usage)
- [Tutorial: Implementing a Static In Game Map](./Static-In-Game-Map) (also [Batch Code](Batch-Code-
Processor) usage)
- [Tutorial: Implementing a Dynamic In Game Map](./Dynamic-In-Game-Map)
- [Tutorial: Writing your own unit tests](./Unit-Testing#testing-for-game-development-mini-tutorial)

### Game mechanics tutorials

_Creating the underlying game mechanics of game play._

- [Hints: Implementing a game rule system](./Implementing-a-game-rule-system)
- [Tutorial: Implementing a Combat system](./Turn-based-Combat-System)
- [Tutorial: Evennia for running tabletop rpgs](./Evennia-for-roleplaying-sessions)

### Miscellaneous system tutorials

_Design various game systems and achieve particular effects._

- [FAQ](./Coding-FAQ): A place for users to enter their own hints on achieving various goals in
Evennia.
- [Tutorial: Adding a Command prompt](./Command-Prompt)
- [Tutorial: Creating a Zoning system](./Zones)
- [Tutorial: Letting players manually configure color settings](./Manually-Configuring-Color)
- [Hints: Asking the user a question and dealing with the result](./EvMenu#ask-for-simple-input)
- [Hints: Designing commands that take time to finish](./Command-Duration)
- [Hints: Adding cooldowns to commands](./Command-Cooldown)
- [Tutorial: Mass and weight for objects](./Mass-and-weight-for-objects)
- [Hints: Show a different message when trying a non-existent exit](./Default-Exit-Errors)
- [Tutorial: Make automatic tweets of game statistics](./Tutorial-Tweeting-Game-Stats)
- [Tutorial: Handling virtual time in your game](./Gametime-Tutorial)
- [Tutorial: Setting up a coordinate system for rooms](./Coordinates)
- [Tutorial: customize the way channels and channel commands work in your game](./Customize-channels)
- [Tutorial: Adding unit tests to your game project](./Unit-Testing#testing-for-game-development-mini- tutorial)

### Contrib

_This section contains tutorials linked with contribs.  These contribs can be used in your game, but
you'll need to install them explicitly.  They add common features that can earn you time in
implementation._

- [list of contribs](https://github.com/evennia/evennia/blob/master/evennia/contrib/README.md)

- [In-game Python: dialogues with characters](./Dialogues-in-events).
- [In-game Python: a voice-operated elevator](./A-voice-operated-elevator-using-events).

### Web tutorials

_Expanding Evennia's web presence._

- [Tutorial: Add a new web page](./Add-a-simple-new-web-page) - simple example to see how Django pages
hang together.
- [Tutorial: Website customization](./Web-Tutorial) - learn how to start customizing your game's web
presence.
- [Tutorial: Bootstrap & Evennia](./Bootstrap-&-Evennia) - Learn more about Bootstrap, the current CSS
framework Evennia is using
- [Tutorial: Build a web page displaying a game character](./Web-Character-View-Tutorial) - make a way
to view your character on the web page.
- [Tutorial: access your help system from your website](./Help-System-Tutorial)
- [Tutorial: add a wiki on your website](./Add-a-wiki-on-your-website)
- [Tutorial: Web Character Generation](Web-Character-Generation/) - make a web-based character
application form.
- [Tutorial: Bootstrap Components and Utilities](./Bootstrap-Components-and-Utilities) - Describes
some common Bootstrap Components and Utilities that might help in designing for Evennia

### Evennia for [Engine]-Users

_Hints for new users more familiar with other game engines._

- [Evennia for Diku Users](./Evennia-for-Diku-Users) - read up on the differences between Diku style
muds and Evennia.
- [Evennia for MUSH Users](./Evennia-for-MUSH-Users) - an introduction to Evennia for those accustomed
to MUSH-style servers.


```toctree::
    :hidden:

    Game-Planning
    Building-Quickstart
    Understanding-Color-Tags
    Tutorial-World-Introduction
    Building-a-mech-tutorial
    Version-Control
    Python-basic-introduction
    Python-basic-tutorial-part-two
    First-Steps-Coding
    Tutorial-for-basic-MUSH-like-game
    Adding-Command-Tutorial
    Parsing-command-arguments,-theory-and-best-practices
    Adding-Object-Typeclass-Tutorial
    Tutorial-Searching-For-Objects
    Weather-Tutorial
    Tutorial-Aggressive-NPCs
    Tutorial-NPCs-listening
    Tutorial-Vehicles
    NPC-shop-Tutorial
    Static-In-Game-Map
    Dynamic-In-Game-Map
    Unit-Testing
    Implementing-a-game-rule-system
    Turn-based-Combat-System
    Evennia-for-roleplaying-sessions
    Coding-FAQ
    Command-Prompt
    Zones
    Manually-Configuring-Color
    EvMenu
    Command-Duration
    Command-Cooldown
    Mass-and-weight-for-objects
    Default-Exit-Errors
    Tutorial-Tweeting-Game-Stats
    Gametime-Tutorial
    Coordinates
    Customize-channels
    Dialogues-in-events
    A-voice-operated-elevator-using-events
    Add-a-simple-new-web-page
    Web-Tutorial
    Bootstrap-&-Evennia
    Web-Character-View-Tutorial
    Help-System-Tutorial
    Add-a-wiki-on-your-website
    Web-Character-Generation
    Bootstrap-Components-and-Utilities
    Evennia-for-Diku-Users
    Evennia-for-MUSH-Users

```
