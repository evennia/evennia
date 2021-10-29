# Developer Central


This page serves as a central nexus for information on using Evennia as well as developing the
library itself.

### General Evennia development information

- [Introduction to coding with Evennia](./Coding-Introduction.md)
- [Evennia Licensing FAQ](./Licensing.md)
- [Contributing to Evennia](./Contributing.md)
- [Code Style Guide](https://github.com/evennia/evennia/blob/master/CODING_STYLE.md) (Important!)
- [Policy for 'MUX-like' default commands](./Using-MUX-as-a-Standard.md)
- [Setting up a Git environment for coding](./Version-Control.md)
- [Getting started with Travis and Github for continuous integration testing](./Using-Travis.md)
- [Planning your own Evennia game](./Game-Planning.md)
- [First steps coding Evennia](./First-Steps-Coding.md)
- [Translating Evennia](./Internationalization.md#translating-evennia)
- [Evennia Quirks](./Quirks.md) to keep in mind.
- [Directions for configuring PyCharm with Evennia on Windows](./Setting-up-PyCharm.md)

### Evennia API

- [Directory Overview](./Directory-Overview.md)
- [evennia - the flat API](./Evennia-API.md)
  - [Running and Testing Python code](./Execute-Python-Code.md)

#### Core components and protocols

- [Server and Portal](./Portal-And-Server.md)
  - [Sessions](./Sessions.md)
  - [Configuration and module plugins](./Server-Conf.md)
- [The message path](./Messagepath.md)
  - [OOB](./OOB.md) - Out-of-band communication
  - [Inputfuncs](./Inputfuncs.md)
  - [Adding new protocols (client APIs) and services](./Custom-Protocols.md)
- [Adding new database models](./New-Models.md)
- [Unit Testing](./Unit-Testing.md)
- [Running profiling](./Profiling.md)
- [Debugging your code](./Debugging.md)

#### In-game Commands

- [Command System overview](./Command-System.md)
- [Commands](./Commands.md)
- [Command Sets](./Command-Sets.md)
- [Command Auto-help](./Help-System.md#command-auto-help-system)

#### Typeclasses and related concepts

- [General about Typeclasses](./Typeclasses.md)
- [Objects](./Objects.md)
  - [Characters](./Objects.md#characters)
  - [Rooms](./Objects.md#rooms)
  - [Exits](./Objects.md#exits)
- [Accounts](./Accounts.md)
- [Communications](./Communications.md)
  - [Channels](./Communications.md#channels)
- [Scripts](./Scripts.md)
  - [Global Scripts](./Scripts.md#global-scripts)
  - [TickerHandler](./TickerHandler.md)
  - [utils.delay](./Coding-Utils.md#utilsdelay)
  - [MonitorHandler](./MonitorHandler.md)
- [Attributes](./Attributes.md)
- [Nicks](./Nicks.md)
- [Tags](./Tags.md)
  - [Tags for Aliases and Permissions](./Tags.md#using-aliases-and-permissions)

#### Web

- [Web features overview](./Web-Features.md)
- [The Webclient](./Webclient.md)
- [Web tutorials](./Web-Tutorial.md)

#### Other systems

- [Locks](./Locks.md)
   - [Permissions](./Locks.md#permissions)
- [Help System](./Help-System.md)
- [Signals](./Signals.md)
- [General coding utilities](./Coding-Utils.md)
   - [Utils in evennia.utils.utils](evennia.utils.utils)
- [Game time](./Coding-Utils.md#game-time)
- [Game Menus](./EvMenu.md) (EvMenu)
- [Text paging/scrolling](./EvMore.md) (EvMore)
- [Text Line Editor](./EvEditor.md) (EvEditor)
- [Text Tables](github:evennia.utils.evtable) (EvTable)
- [Text Form generation](github:evennia.utils.evform) (EvForm)
- [Spawner and Prototypes](./Spawner-and-Prototypes.md)
- [Inlinefuncs](./TextTags.md#inline-functions)
- [Asynchronous execution](./Async-Process.md)

### Developer brainstorms and whitepages

- [API refactoring](./API-refactoring.md), discussing what parts of the Evennia API needs a
refactoring/cleanup/simplification
- [Docs refactoring](./Docs-refactoring.md), discussing how to reorganize and structure this wiki/docs
better going forward
- [Webclient brainstorm](./Webclient-brainstorm.md), some ideas for a future webclient gui
- [Roadmap](./Roadmap.md), a tentative list of future major features
- [Change log](https://github.com/evennia/evennia/blob/master/CHANGELOG.md) of big Evennia updates
over time


[group]: https://groups.google.com/forum/#!forum/evennia
[online-form]: https://docs.google.com/spreadsheet/viewform?hl=en_US&formkey=dGN0VlJXMWpCT3VHaHpscDE
zY1RoZGc6MQ#gid=0
[issues]: https://github.com/evennia/evennia/issues


```{toctree}
    :hidden:
   
    Coding-Introduction
    Licensing
    Contributing
    Using-MUX-as-a-Standard
    Version-Control
    Using-Travis
    Game-Planning
    First-Steps-Coding
    Internationalization
    Quirks
    Setting-up-PyCharm
    Directory-Overview
    Evennia-API
    Execute-Python-Code
    Portal-And-Server
    Sessions
    Server-Conf 
    Messagepath
    OOB
    Inputfuncs
    Custom-Protocols
    New-Models
    Unit-Testing
    Profiling
    Debugging
    Command-System
    Commands
    Command-Sets
    Help-System
    Typeclasses
    Objects
    Accounts 
    Communications
    Scripts
    TickerHandler
    Coding-Utils
    MonitorHandler
    Attributes
    Nicks
    Tags
    Web-Features
    Webclient
    Web-Tutorial
    Locks
    Signals
    Coding-Utils
    EvMenu
    EvMore
    EvEditor
    Spawner-and-Prototypes
    TextTags
    Async-Process
    API-refactoring
    Docs-refactoring
    Webclient-brainstorm 

```
