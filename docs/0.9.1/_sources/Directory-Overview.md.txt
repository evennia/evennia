# Directory Overview


This is an overview of the directories relevant to Evennia coding. 

## The Game directory

The game directory is created with `evennia --init <name>`. In the Evennia documentation we always assume it's called `mygame`. Apart from the `server/` subfolder within, you could reorganize this folder if you preferred a different code structure for your game.

 - `mygame/`
  - `commands/` - Overload default [Commands](./Commands) or add your own Commands/[Command sets](./Command-Sets) here.
  - `server`/  - The structure of this folder should not change since Evennia expects it.  
    - [`conf/`](https://github.com/evennia/evennia/tree/master/evennia/game_template/server) - All server configuration files sits here. The most important file is `settings.py`. 
    - `logs/` - Portal log files are stored here (Server is logging to the terminal by default)
  - `typeclasses/` - this folder contains empty templates for overloading default game entities of Evennia. Evennia will automatically use the changes in those templates for the game entities it creates. 
  - `web/` - This holds the [Web features](./Web-Features) of your game. 
  - `world/` - this is a "miscellaneous" folder holding everything related to the world you are building, such as build scripts and rules modules that don't fit with one of the other folders.  

## Evennia library layout:

If you cloned the GIT repo following the instructions, you will have a folder named `evennia`. The top level of it contains Python package specific stuff such as a readme file, `setup.py` etc. It also has two subfolders`bin/` and `evennia/` (again).  

The `bin/` directory holds OS-specific binaries that will be used when installing Evennia with `pip` as per the [Getting started](./Getting-Started) instructions. The library itself is in the `evennia` subfolder. From your code you will access this subfolder simply by `import evennia`. 

 - evennia
   - [`__init__.py`](./Evennia-API) - The "flat API" of Evennia resides here. 
   - [`commands/`](./Commands) - The command parser and handler.
     - `default/` - The [default commands](./Default-Command-Help) and cmdsets. 
   - [`comms/`](./Communications) - Systems for communicating in-game. 
   - `contrib/` - Optional plugins too game-specific for core Evennia.
   - `game_template/` - Copied to become the "game directory" when using `evennia --init`. 
   - [`help/`](./Help-System) - Handles the storage and  creation of help entries.
   - `locale/` - Language files ([i18n](./Internationalization)).
   - [`locks/`](./Locks) - Lock system for restricting access to in-game entities.
   - [`objects/`](./Objects) - In-game entities (all types of items and Characters).
   - [`prototypes/`](./Spawner-and-Prototypes) - Object Prototype/spawning system and OLC menu
   - [`accounts/`](./Accounts) - Out-of-game Session-controlled entities (accounts, bots etc)
   - [`scripts/`](./Scripts) - Out-of-game entities equivalence to Objects, also with timer support. 
   - [`server/`](./Portal-And-Server) - Core server code and Session handling. 
     - `portal/` - Portal proxy and connection protocols.
   - [`settings_default.py`](./Server-Conf#Settings-file) - Root settings of Evennia. Copy settings from here to `mygame/server/settings.py` file. 
   - [`typeclasses/`](./Typeclasses) - Abstract classes for the typeclass storage and database system.
   - [`utils/`](./Coding-Utils) - Various miscellaneous useful coding resources.
   - [`web/`](./Web-Features) - Web resources and webserver. Partly copied into game directory on initialization.

All directories contain files ending in `.py`. These are Python *modules* and are the basic units of Python code. The roots of directories also have (usually empty) files named `__init__.py`. These are required by Python so as to be able to find and import modules in other directories. When you have run Evennia at least once you will find that there will also be `.pyc` files appearing, these are pre-compiled binary versions of the `.py` files to speed up execution.

The root of the `evennia` folder has an `__init__.py` file containing the "[flat API](./Evennia-API)". This holds shortcuts to various subfolders in the evennia library. It is provided to make it easier to find things; it allows you to just import `evennia` and access things from that rather than having to import from their actual locations inside the source tree. 
