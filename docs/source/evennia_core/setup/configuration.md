```python
class Documentation:
    RATING = "Acceptable"
```

# Server Configuration

Evennia runs out of the box without any changes to its settings. But there are several important ways to customize the server and expand it with your own plugins. 

## Settings file

The "Settings" file referenced throughout the documentation is the file `mygame/server/conf/settings.py`. This is automatically created on the first run of `evennia --init` 

Your new `settings.py` is relatively bare out of the box. Evennia's core settings file is actually [evennia/settings_default.py](https://github.com/evennia/evennia/blob/master/evennia/settings_default.py) and is considerably more extensive (it is also heavily documented so you should refer to this file directly for the available settings). 

Since `mygame/server/conf/settings.py` is a normal Python module, it simply imports `evennia/settings_default.py` into itself at the top.

This means that if any setting you want to change were to depend on some *other* default setting, you might need to copy & paste both in order to change them and get the effect you want (for most commonly changed settings, this is not something you need to worry about).

You should never edit `evennia/settings_default.py`. Rather you should copy&paste the select variables you want to change into your `settings.py` and edit them there. This will overload the previously imported defaults.

> Warning: It may be tempting to copy everything from `settings_default.py` into your own settings file. There is a reason we don't do this out of the box though: it makes it directly clear what changes you did. Also, if you limit your copying to the things you really need you will directly be able to take advantage of upstream changes and additions to Evennia for anything you didn't customize. 

In code, the settings is accessed through 

```python
    from django.conf import settings
     # or (shorter):
    from evennia import settings
     # example:
    servername = settings.SERVER_NAME
```

Each setting appears as a property on the imported `settings` object.  You can also explore all possible options with `evennia.settings_full` (this also includes advanced Django defaults that are not touched in default Evennia). 

> It should be pointed out that when importing `settings` into your code like this, it will be *read only*. You *cannot* edit your settings from your code! The only way to change an Evennia setting is to edit `mygame/server/conf/settings.py` directly. You also generally need to restart the server (possibly also the Portal) before a changed setting becomes available. 

## Other settings

Apart from the main `settings.py` file, the `server/conf` directory contains additional configurable files: 

- `at_initial_setup.py` - this allows you to add a custom startup method to be called (only) the very first time Evennia starts (at the same time as user #1 and Limbo is created). It can be made to start your own global scripts or set up other system/world-related things your game needs to have running from the start.
- `at_search.py` - this allows for replacing the way Evennia handles [search](../../evennia_core/system/utils/search.md) results. It allows to change how errors are echoed and how multi-matches are resolved and reported (like how the default understands that "2-ball" should match the second "ball" object if there are two of them in the room).
- `at_server_startstop.py` - this module contains two functions that Evennia will call every time the Server starts and stops respectively - this includes stopping due to reloading and resetting as well as shutting down completely. It's a useful place to put custom startup code for handlers and other things that must run in your game but which has no database persistence.
- `cmdparser.py` -  a custom module can be used to totally replace Evennia's default command parser. All this does is to split the incoming string into "command name" and "the rest". It also handles things like error messages for no-matches and multiple-matches among other things that makes this more complex than it sounds. The default parser is *very* generic, so you are most often best served by modifying things further down the line (on the command parse level) than here.
- `connection_screens.py` - all global string variables in this module are interpreted by Evennia as a greeting screen to show when an Account first connects. If more than one string variable is present in the module a random one will be picked.
- `inlinefuncs.py` - this is where you can define custom [Inline functions](../../evennia_core/system/ui/TextTags.md).
- `inputfuncs.py` - this is where you define custom [Inputfuncs](../../evennia_core/system/portal/Inputfuncs.md) to handle data from the client.
- `lockfuncs.py` - this is one of many possible modules to hold your own "safe" *lock functions* to make available to Evennia's [Locks](../../evennia_core/system/locks/Locks.md).
- `mssp.py` - this holds meta information about your game. It is used by MUD search engines (which you often have to register with) in order to display what kind of game you are running along with
    statistics such as number of online accounts and online status.
- `portal_services_plugin.py` - this allows for adding your own custom services/protocols to the Portal. It must define one particular function that will be called by Evennia at startup. There can be any number of service plugin modules, all will be imported and used if defined. More info can be found [here](../../evennia_core/system/portal/Custom-Protocols.md).
- `server_services_plugin.py` - this is equivalent to the previous one, but used for adding new services to the Server instead. More info can be found [here](http://code.google.com/p/evennia/wiki/SessionProtocols#Adding_custom_Protocols).
- `web_plugins.py` - the equivalent to the plugin files above; allows changing the functionality of the website
- `secret_settings.py` - a settings file that supercedes the settings.py and can overwrite its values. Typically used for storing secrets (database connection information, containing passwords) and not added to a public repository
