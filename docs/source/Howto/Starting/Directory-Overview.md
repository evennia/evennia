# Overview of your new Game Dir

[prev lesson](Tutorial-World-Introduction) | [next lesson]()

Now we have 'run the game' a bit and looked at what can be done in-game. It is time to start to look
at how things look 'outside of the game'. Let's do a tour of the game-dir you just created. Like
everywhere in the docs we'll assume it's called `mygame`.

You may have noticed when we were building things in-game that we would often refer to code through 
"python paths", such as 

```sidebar:: Python-paths

    A 'python path' uses '.' instead of '/' or '`\\`' and
    skips the `.py` ending of files. It can also point to 
    the code contents of python files. Since Evennia is already 
    looking for code in your game dir, your python paths can start 
    from there. 

    So a path `/home/foo/devel/mygame/commands/command.py`
    would translate to a Python-path `commands.command`. 
```

    create/drop button:tutorial_examples.red_button.RedButton

This is a fundamental aspect of coding Evennia - _you create code and then you tell Evennia where that
code is and when it should be used_. Above we told it to create a red button by pulling from specific code 
in the `contribs/` folder but the same principle is true everywhere. So it's important to know where code is
and how you point to it correctly.

 - `mygame/`
    - `commands/` - This holds all your custom commands (user-input handlers). You both add your own
   and override Evennia's defaults from here. 
    - `server`/  - The structure of this folder should not change since Evennia expects it.  
        - `conf/` - All server configuration files sits here. The most important file is `settings.py`.
        - `logs/` - Server log files are stored here. When you use `evennia --log` you are actually 
        tailing the files in this directory.
    - `typeclasses/` - this holds empty templates describing all database-bound entities in the 
        game, like Characters, Scripts, Accounts etc. Adding code here allows to customize and extend
        the defaults.  
    - `web/` - This is where you override and extend the default templates, views and static files used 
  for Evennia's web-presence, like the website and the HTML5 webclient.
    - `world/` - this is a "miscellaneous" folder holding everything related to the world you are
    building, such as build scripts and rules modules that don't fit with one of the other folders.

> The `server/` subfolder should remain the way it is - Evennia expects this. But you could in 
> principle change the structure of the rest of your game dir as best fits your preference. 
> Maybe you don't need a world/ folder but prefer many folders with different aspects of your world?
> Or a new folder 'rules' for your RPG rules? This is fine. If you move things around you just need 
> to update Evennia's default settings to point to the right places in the new structure. 

## commands/

The `commands/` folder holds Python _modules_ related to creating and extending the [Commands](../../Component/Commands)
of Evennia. These manifest in game like the server understanding input like `look` or `dig`. 

```sidebar:: Python modules

A `module` is the common term for a file ending with the `.py` file ending. A module
is a text file containing Python source code.
```





## Evennia library layout:

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

[prev lesson](Tutorial-World-Introduction) | [next lesson]()
