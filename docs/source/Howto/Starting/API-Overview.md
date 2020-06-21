## Evennia API overview

If you cloned the GIT repo following the instructions, you will have a folder named `evennia`. The
top level of it contains Python package specific stuff such as a readme file, `setup.py` etc. It
also has two subfolders`bin/` and `evennia/` (again).

The `bin/` directory holds OS-specific binaries that will be used when installing Evennia with `pip`
as per the [Getting started](../Setup/Getting-Started) instructions. The library itself is in the `evennia`
subfolder. From your code you will access this subfolder simply by `import evennia`.

 - evennia
   - [`__init__.py`](Evennia-API) - The "flat API" of Evennia resides here. 
   - [`commands/`](Commands) - The command parser and handler.
     - `default/` - The [default commands](../../Component/Default-Command-Help) and cmdsets. 
   - [`comms/`](Communications) - Systems for communicating in-game. 
   - `contrib/` - Optional plugins too game-specific for core Evennia.
   - `game_template/` - Copied to become the "game directory" when using `evennia --init`. 
   - [`help/`](Help-System) - Handles the storage and  creation of help entries.
   - `locale/` - Language files ([i18n](../../Concept/Internationalization)).
   - [`locks/`](Locks) - Lock system for restricting access to in-game entities.
   - [`objects/`](Objects) - In-game entities (all types of items and Characters).
   - [`prototypes/`](Spawner-and-Prototypes) - Object Prototype/spawning system and OLC menu
   - [`accounts/`](Accounts) - Out-of-game Session-controlled entities (accounts, bots etc)
   - [`scripts/`](Scripts) - Out-of-game entities equivalence to Objects, also with timer support. 
   - [`server/`](Portal-And-Server) - Core server code and Session handling. 
     - `portal/` - Portal proxy and connection protocols.
   - [`settings_default.py`](Server-Conf#Settings-file) - Root settings of Evennia. Copy settings
from here to `mygame/server/settings.py` file.
   - [`typeclasses/`](Typeclasses) - Abstract classes for the typeclass storage and database system.
   - [`utils/`](Coding-Utils) - Various miscellaneous useful coding resources.
   - [`web/`](Web-Features) - Web resources and webserver. Partly copied into game directory on
initialization.

All directories contain files ending in `.py`. These are Python *modules* and are the basic units of
Python code. The roots of directories also have (usually empty) files named `__init__.py`. These are
required by Python so as to be able to find and import modules in other directories. When you have
run Evennia at least once you will find that there will also be `.pyc` files appearing, these are
pre-compiled binary versions of the `.py` files to speed up execution.

The root of the `evennia` folder has an `__init__.py` file containing the "[flat API](../../Evennia-API)".
This holds shortcuts to various subfolders in the evennia library. It is provided to make it easier
to find things; it allows you to just import `evennia` and access things from that rather than
having to import from their actual locations inside the source tree.

