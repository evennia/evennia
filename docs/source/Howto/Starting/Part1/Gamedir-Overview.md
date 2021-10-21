# Overview of your new Game Dir

Next we will take a little detour to look at the _Tutorial World_. This is a little solo adventure
that comes with Evennia, a showcase for some of the things that are possible. 

Now we have 'run the game' a bit and started with our forays into Python from inside Evennia.
It is time to start to look at how things look 'outside of the game'. Let's do a tour of your game-dir 
Like everywhere in the docs we'll assume it's called `mygame`. 

> When looking through files, ignore files ending with `.pyc` and the
`__pycache__` folder if it exists. This is internal Python compilation files that you should never 
> need to touch. Files `__init__.py` is also often empty and can be ignored (they have to do with
> Python package management).

You may have noticed when we were building things in-game that we would often refer to code through 
"python paths", such as 

```{sidebar} Python-paths

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

The `commands/` folder holds Python modules related to creating and extending the [Commands](../../../Components/Commands.md)
of Evennia. These manifest in game like the server understanding input like `look` or `dig`. 

```{sidebar} Classes

    A `class` is  template for creating object-instances of a particular type
    in Python. We will explain classes in more detail in the next 
    `python overview <Python-basic-tutorial-part-two>`_.

```
- [command.py](github:evennia/game_template/commands/command.py) (Python-path: `commands.command`) - this contain the
  base _classes_ for designing new input commands, or override the defaults.
- [default_cmdsets.py](github:evennia/game_template/commands/default_cmdsets.py) (Python path: `commands.default_commands`) -
  a cmdset (Command-Set) groups Commands together. Command-sets can be added and removed from objects on the fly,
  meaning a user could have a different set of commands (or versions of commands) available depending on their circumstance 
  in the game. In order to add a new command to the game, it's common to import the new command-class 
  from `command.py` and add it to one of the default cmdsets in this module. 
  
## server/

This folder contains resource necessary for running Evennia. Contrary to the other folders, the structure 
of this should be kept the way it is. 

- `evennia.db3` - you will only have this file if you are using the default SQLite3 database. This file
  contains the entire database. Just copy it to make a backup. For development you could also just
  make a copy once you have set up everything you need and just copy that back to 'reset' the state.
  If you delete this file you can easily recreate it by running `evennia migrate`. 

### server/logs/

This holds the server logs. When you do `evennia --log`, the evennia program is in fact tailing and concatenating
the `server.log` and `portal.log` files in this directory. The logs are rotated every week. Depending on your settings,
other logs, like the webserver HTTP request log can also be found here. 

### server/conf/

This contains all configuration files of the Evennia server. These are regular Python modules which 
means that they must be extended with valid Python. You can also add logic to them if you wanted to.

Common for the settings is that you generally will never them directly via their python-path; instead Evennia
knows where they are and will read them to configure itself at startup. 

- `settings.py` - this is by far the most important file. It's nearly empty by default, rather you
  are expected to copy&paste the changes you need from [evennia/default_settings.py](github:evennia/default_settings.py).
  The default settings file is extensively documented. Importing/accessing the values in the settings
  file is done in a special way, like this: 
            
        from django.conf import settings 

    To get to the setting `TELNET_PORT` in the settings file you'd then do 
    
        telnet_port = settings.TELNET_PORT
        
    You cannot assign to the settings file dynamically; you must change the `settings.py` file directly to 
    change a setting.
- `secret_settings.py` - If you are making your code effort public, you may not want to share all settings online. 
    There may be server-specific secrets or just fine-tuning for your game systems that you prefer be kept secret
    from the players. Put such settings in here, it will override values in `settings.py` and not be included in 
    version control. 
- `at_initial_setup.py` - When Evennia starts up for the very first time, it does some basic tasks, like creating the 
    superuser and Limbo room. Adding to this file allows to add more actions for it to for first-startup.
- `at_search.py` - When searching for objects and either finding no match or more than one match, it will
    respond by giving a warning or offering the user to differentiate between the multiple matches. Modifying
    the code here will change this behavior to your liking.
- `at_server_startstop.py` - This allows to inject code to execute every time the server starts, stops or reloads
    in different ways. 
- `connection_screens.py` - This allows for changing the connection screen you see when you first connect to your 
    game. 
- `inlinefuncs.py` - _Inlinefuncs_ are optional and limited 'functions' that can be embedded in any strings being 
    sent to a player. They are written as `$funcname(args)` and are used to customize the output 
    depending on the user receiving it. For example sending people the text `"Let's meet at $realtime(13:00, GMT)!` 
    would show every player seeing that string the time given in their own time zone. The functions added to this
    module will become new inlinefuncs in the game.
- `inputfucs.py` - When a command like `look` is received by the server, it is handled by an _inputfunc_
    that redirects it to the cmdhandler system. But there could be other inputs coming from the clients, like 
    button-presses or the request to update a health-bar. While most common cases are already covered, this is 
    where one adds new functions to process new types of input.
- `lockfuncs.py` - _Locks_ restrict access to things in-game. Lock funcs are used in a mini-language 
    to defined more complex locks. For example you could have a lockfunc that checks if the user is carrying
    a given item, is bleeding or has a certain skill value. New functions added in this modules will 
    become available for use in lock definitions.
- `mssp.py` - Mud Server Status Protocol is a way for online MUD archives/listings (which you usually have 
    to sign up for) to track which MUDs are currently online, how many players they have etc. While Evennia handles 
    the dynamic information automatically, this is were you set up the meta-info about your game, such as its 
    theme, if player-killing is allowed and so on. This is a more generic form of the Evennia Game directory.
- `portal_services_plugins.py` - If you want to add new external connection protocols to Evennia, this is the place 
    to add them.
- `server_services_plugins.py` - This allows to override internal server connection protocols.
- `web_plugins.py` - This allows to add plugins to the Evennia webserver as it starts.

### typeclasses/

The [Typeclasses](../../../Components/Typeclasses.md) of Evennia are Evennia-specific Python classes whose instances save themselves
to the database. This allows a Character to remain in the same place and your updated strength stat to still
be the same after a server reboot. 

- [accounts.py](github:evennia/game_template/typeclasses/accounts.py) (Python-path: `typeclasses.accounts`) - An 
    [Account](../../../Components/Accounts.md) represents the player connecting to the game. It holds information like email,
    password and other out-of-character details.
- [channels.py](github:evennia/game_template/typeclasses/channels.py) (Python-path: `typeclasses.channels`) - 
    [Channels](../../../Components/Channels.md) are used to manage in-game communication between players. 
- [objects.py](github:evennia/game_template/typeclasses/objects.py) (Python-path: `typeclasses.objects`) - 
   [Objects](../../../Components/Objects.md) represent all things having a location within the game world.
- [characters.py](github:evennia/game_template/typeclasses/characters.py) (Python-path: `typeclasses.characters`) - 
    The [Character](../../../Components/Objects.md#characters) is a subclass of Objects, controlled by Accounts - they are the player's
    avatars in the game world.
- [rooms.py](github:evennia/game_template/typeclasses/rooms.py) (Python-path: `typeclasses.rooms`) - A 
    [Room](../../../Components/Objects.md#rooms) is also a subclass of Object; describing discrete locations. While the traditional
    term is 'room', such a location can be anything and on any scale that fits your game, from a forest glade, 
    an entire planet or an actual dungeon room.
- [exits.py](github:evennia/game_template/typeclasses/exits.py) (Python-path: `typeclasses.exits`) - 
    [Exits](../../../Components/Objects.md#exits) is another subclass of Object. Exits link one Room to another. 
- [scripts.py](github:evennia/game_template/typeclasses/scripts.py) (Python-path: `typeclasses.scripts`) - 
    [Scripts](../../../Components/Scripts.md) are 'out-of-character' objects. They have no location in-game and can serve as basis for 
    anything that needs database persistence, such as combat, weather, or economic systems. They also
    have the ability to execute code repeatedly, on a timer. 
    
### web/

This folder contains folders for overriding the default web-presence of Evennia with your own designs.
Most of these folders are empty except for a README file or a subset of other empty folders. 

- `media/` - this empty folder is where you can place your own images or other media files you want the
    web server to serve. If you are releasing your game with a lot of media (especially if you want videos) you 
    should consider re-pointing Evennia to use some external service to serve your media instead. 
- `static_overrides/` - 'static' files include fonts, CSS and JS. Within this folder you'll find sub-folders for 
    overriding the static files for the `admin` (this is the Django web-admin), the `webclient` (this is thet
    HTML5 webclient) and the `website`. Adding files to this folder will replace same-named files in the 
    default web presence. 
- `template_overrides/` - these are HTML files, for the `webclient` and the `website`. HTML files are written
    using [Jinja](https://jinja.palletsprojects.com/en/2.11.x/) templating, which means that one can override 
    only particular parts of a default template without touching others. 
- `static/` - this is a work-directory for the web system and should _not_ be manually modified. Basically,
    Evennia will copy static data from `static_overrides` here when the server starts. 
- `urls.py` - this module links up the Python code to the URLs you go to in the browser.

### world/ 

This folder only contains some example files. It's meant to hold 'the rest' of your game implementation. Many 
people change and re-structure this in various ways to better fit their ideas. 

- [batch_cmds.ev](github:evennia/game_template/world/batch_cmds.ev) - This is an `.ev` file, which is essentially
    just a list of Evennia commands to execute in sequence. This one is empty and ready to expand on. The 
    [Tutorial World](./Tutorial-World-Introduction.md) was built with such a batch-file.
- [prototypes.py](github:evennia/game_template/world/prototypes.py) - A [prototype](../../../Components/Prototypes.md) is a way
    to easily vary objects without changing their base typeclass. For example, one could use prototypes to 
    tell that Two goblins, while both of the class 'Goblin' (so they follow the same code logic), should have different 
    equipment, stats and looks.
    
