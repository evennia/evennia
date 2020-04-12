```python
class Documentation:
    RATING = "Excellent"
```

# Directory Overview

This is an overview of the directories relevant to Evennia coding. 

## The Game directory

The game directory is created with `evennia --init <name>`. In the Evennia documentation we always assume it's called `mygame`. Apart from the `server/` subfolder within, you could reorganize this folder if you preferred a different code structure for your game.

- `mygame/`
  - `commands/` - Overload default Commands or add your own here.
  - `server/`  - The structure of this folder should not change since Evennia expects it.  
    - `conf/` - All server configuration files sits here. The most important file is `settings.py`. 
    - `logs/` - Portal log files are stored here (Server is logging to the terminal by default)
  - `typeclasses/` - this folder contains empty templates for overloading default game entities of Evennia. Evennia will automatically use the changes in those templates for the game entities it creates. 
  - `web/` - This holds the Web features of your game. 
  - `world/` - this is a "miscellaneous" folder holding everything related to the world you are building, such as build scripts and rules modules that don't fit with one of the other folders.  

## Evennia library layout:

If you cloned the GIT repo following the instructions, you will have a folder named `evennia`. The top level of it contains Python package specific stuff such as a readme file, `setup.py` etc. It also has two subfolders`bin/` and `evennia/` (again).  

The `bin/` directory holds OS-specific binaries that will be used when installing Evennia with `pip` as per the [installation instructions](../../evennia_core/setup/installation). The library itself is in the `evennia` subfolder. From your code you will access this subfolder simply by `import evennia`. 

- evennia
   - `__init__.py` - The "[flat API](../../evennia_core/evennia-flat-api)" of Evennia resides here. 
   - `settings_default.py` - Root settings of Evennia. Copy settings from here to `mygame/server/settings.py` file.
   - `commands/` - The command parser and handler.
     - `default/` - The default commands and cmdsets. 
   - `comms/` - Systems for communicating in-game. 
   - `contrib/` - Optional plugins too game-specific for core Evennia.
   - `game_template/` - Copied to become the "game directory" when using `--init`. 
   - `help/` - Handles the storage and  creation of help entries.
   - `locale/` - Language files (i18n).
   - `locks/` - Lock system for restricting access to in-game entities.
   - `objects/` - In-game entities (all types of items and Characters).
   - `prototypes/` - Object Prototype/spawning system and OLC menu
   - `accounts/` - Out-of-game Session-controlled entities (accounts, bots etc)
   - `scripts/` - Out-of-game entities equivalence to Objects, also with timer support. 
   - `server/` - Core server code and Session handling. 
     - `portal/` - Portal proxy and connection protocols.
   - `typeclasses/` - Abstract classes for the typeclass storage and database system.
   - `utils/` - Various miscellaneous useful coding resources.
   - `web/` - Web resources and webserver. Partly copied into game directory on initialization.
