# Scripts


*Scripts* are the out-of-character siblings to the in-character
[Objects](Component/Objects). Scripts are so flexible that the "Script" is a bit limiting
- we had to pick something to name them after all. Other possible names
(depending on what you'd use them for) would be `OOBObjects`,
`StorageContainers` or `TimerObjects`. 

Scripts can be used for many different things in Evennia:

- They can attach to Objects to influence them in various ways - or exist
  independently of any one in-game entity (so-called *Global Scripts*).
- They can work as timers and tickers - anything that may change with Time. But
  they can also have no time dependence at all. Note though that if all you want
  is just to have an object method called repeatedly, you should consider using
  the [TickerHandler](Component/TickerHandler) which is more limited but is specialized on
  just this task. 
- They can describe State changes. A Script is an excellent platform for
hosting a persistent, but unique system handler. For example, a Script could be
used as the base to track the state of a turn-based combat system. Since
Scripts can also operate on a timer they can also update themselves regularly
to perform various actions. 
- They can act as data stores for storing game data persistently in the database 
(thanks to its ability to have [Attributes](Component/Attributes)). 
- They can be used as OOC stores for sharing data between groups of objects, for 
example for tracking the turns in a turn-based combat system or barter exchange.

Scripts are [Typeclassed](Component/Typeclasses) entities and are manipulated in a similar 
way to how it works for other such Evennia entities: 

```python
# create a new script 
new_script = evennia.create_script(key="myscript", typeclass=...)  

# search (this is always a list, also if there is only one match)
list_of_myscript = evennia.search_script("myscript")

```

## Defining new Scripts

A Script is defined as a class and is created in the same way as other
[typeclassed](Component/Typeclasses) entities. The class has several properties 
to control the timer-component of the scripts. These are all _optional_ -
leaving them out will just create a Script with no timer components (useful to act as
a database store or to hold a persistent game system, for example).

This you can do for example in the module
`evennia/typeclasses/scripts.py`. Below is an example Script
   Typeclass.

```python
from evennia import DefaultScript

class MyScript(DefaultScript):

    def at_script_creation(self):
        self.key = "myscript"
        self.interval = 60  # 1 min repeat

    def at_repeat(self):
        # do stuff every minute 
```

In `mygame/typeclasses/scripts.py` is the `Script` class which inherits from `DefaultScript`
already. This is provided as your own base class to do with what you like: You can tweak `Script` if
you want to change the default behavior and it is usually convenient to inherit from this instead.
Here's an example:

```python
    # for example in mygame/typeclasses/scripts.py  
    # Script class is defined at the top of this module

    import random

    class Weather(Script): 
        """
        A timer script that displays weather info. Meant to 
        be attached to a room. 
          
        """
        def at_script_creation(self):
            self.key = "weather_script"
            self.desc = "Gives random weather messages."
            self.interval = 60 * 5  # every 5 minutes
            self.persistent = True  # will survive reload

        def at_repeat(self):
            "called every self.interval seconds."        
            rand = random.random()
            if rand < 0.5:
                weather = "A faint breeze is felt."
            elif rand < 0.7:
                weather = "Clouds sweep across the sky." 
            else:
                weather = "There is a light drizzle of rain."
            # send this message to everyone inside the object this
            # script is attached to (likely a room)
            self.obj.msg_contents(weather)
```

If we put this script on a room, it will randomly report some weather 
to everyone in the room every 5 minutes.

To activate it, just add it to the script handler (`scripts`) on an
[Room](Component/Objects). That object becomes `self.obj` in the example above.  Here we
put it on a room called `myroom`:

```
    myroom.scripts.add(scripts.Weather)
```

> Note that `typeclasses` in your game dir is added to the setting `TYPECLASS_PATHS`. 
> Therefore we don't need to give the full path (`typeclasses.scripts.Weather`
> but only `scripts.Weather` above.

You can also create scripts using the `evennia.create_script` function:

```python
    from evennia import create_script
    create_script('typeclasses.weather.Weather', obj=myroom)
```

Note that if you were to give a keyword argument to `create_script`, that would
override the default value in your Typeclass. So for example, here is an instance
of the weather script that runs every 10 minutes instead (and also not survive
a server reload):

```python
    create_script('typeclasses.weather.Weather', obj=myroom, 
                   persistent=False, interval=10*60)
```

From in-game you can use the `@script` command to launch the Script on things: 

```
     @script here = typeclasses.scripts.Weather 
```

You can conveniently view and kill running Scripts by using the `@scripts`
command in-game.

## Properties and functions defined on Scripts

A Script has all the properties of a typeclassed object, such as `db` and `ndb`(see
[Typeclasses](Component/Typeclasses)). Setting `key` is useful in order to manage scripts (delete them by name
etc). These are usually set up in the Script's typeclass, but can also be assigned on the fly as
keyword arguments to `evennia.create_script`.

- `desc` - an optional description of the script's function. Seen in script listings.
- `interval` - how often the script should run. If `interval == 0` (default), this script has no
timing component, will not repeat and will exist forever. This is useful for Scripts used for
storage or acting as bases for various non-time dependent game systems.
- `start_delay` - (bool), if we should wait `interval` seconds before firing for the first time or
not.
- `repeats` - How many times we should repeat, assuming `interval > 0`. If repeats is set to `<= 0`,
the script will repeat indefinitely. Note that *each* firing of the script (including the first one)
counts towards this value. So a `Script` with `start_delay=False` and `repeats=1` will start,
immediately fire and shut down right away.
- `persistent`- if this script should survive a server *reset* or server *shutdown*. (You don't need
to set this for it to survive a normal reload - the script will be paused and seamlessly restart
after the reload is complete).

There is one special property:

- `obj` - the [Object](Component/Objects) this script is attached to (if any).  You should not need to set
this manually. If you add the script to the Object with `myobj.scripts.add(myscriptpath)` or give
`myobj` as an argument to the `utils.create.create_script` function, the `obj` property will be set
to `myobj` for you.

It's also imperative to know the hook functions. Normally, overriding
these are all the customization you'll need to do in Scripts. You can
find longer descriptions of these in `src/scripts/scripts.py`.

- `at_script_creation()` - this is usually where the script class sets things like `interval` and
`repeats`; things that control how the script runs. It is only called once - when the script is
first created.
- `is_valid()` - determines if the script should still be running or not. This is called when
running `obj.scripts.validate()`, which you can run manually, but which is also called by Evennia
during certain situations such as reloads. This is also useful for using scripts as state managers.
If the method returns `False`, the script is stopped and cleanly removed.
- `at_start()` - this is called when the script starts or is unpaused. For persistent scripts this
is at least once ever server startup. Note that this will *always* be called right away, also if
`start_delay` is `True`.
- `at_repeat()` - this is called every `interval` seconds, or not at all. It is called right away at
startup, unless `start_delay` is `True`, in which case the system will wait `interval` seconds
before calling.
- `at_stop()` - this is called when the script stops for whatever reason. It's a good place to do
custom cleanup.
- `at_server_reload()` - this is called whenever the server is warm-rebooted (e.g. with the
`@reload` command). It's a good place to save non-persistent data you might want to survive a
reload.
- `at_server_shutdown()` - this is called when a system reset or systems shutdown is invoked.

Running methods (usually called automatically by the engine, but possible to also invoke manually)

- `start()` - this will start the script. This is called automatically whenever you add a new script
to a handler. `at_start()` will be called.
- `stop()` - this will stop the script and delete it. Removing a script from a handler will stop it
automatically. `at_stop()` will be called.
- `pause()` - this pauses a running script, rendering it inactive, but not deleting it. All
properties are saved and timers can be resumed. This is called automatically when the server reloads
and will *not* lead to the *at_stop()* hook being called. This is a suspension of the script, not a
change of state.
- `unpause()` - resumes a previously paused script. The `at_start()` hook *will* be called to allow
it to reclaim its internal state. Timers etc are restored to what they were before pause. The server
automatically unpauses all paused scripts after a server reload.
- `force_repeat()` - this will forcibly step the script, regardless of when it would otherwise have
fired. The timer will reset and the `at_repeat()` hook is called as normal. This also counts towards
the total number of repeats, if limited.
- `time_until_next_repeat()` - for timed scripts, this returns the time in seconds until it next
fires. Returns `None` if `interval==0`.
- `remaining_repeats()` - if the Script should run a limited amount of times, this tells us how many
are currently left.
- `reset_callcount(value=0)` - this allows you to reset the number of times the Script has fired. It
only makes sense if `repeats > 0`.
- `restart(interval=None, repeats=None, start_delay=None)` - this method allows you to restart the
Script in-place with different run settings. If you do, the `at_stop` hook will be called and the
Script brought to a halt, then the `at_start` hook will be called as the Script starts up with your
(possibly changed) settings. Any keyword left at `None` means to not change the original setting.


## Global Scripts

A script does not have to be connected to an in-game object. If not it is
called a *Global script*. You can create global scripts by simply not supplying an object to store
it on:

```python
     # adding a global script
     from evennia import create_script
     create_script("typeclasses.globals.MyGlobalEconomy", 
                    key="economy", persistent=True, obj=None)
```
Henceforth you can then get it back by searching for its key or other identifier with 
`evennia.search_script`. In-game, the `scripts` command will show all scripts. 

Evennia supplies a convenient "container" called `GLOBAL_SCRIPTS` that can offer an easy 
way to access global scripts. If you know the name (key) of the script you can get it like so: 

```python
from evennia import GLOBAL_SCRIPTS

my_script = GLOBAL_SCRIPTS.my_script
# needed if there are spaces in name or name determined on the fly
another_script = GLOBAL_SCRIPTS.get("another script")
# get all global scripts (this returns a Queryset)
all_scripts = GLOBAL_SCRIPTS.all()
# you can operate directly on the script
GLOBAL_SCRIPTS.weather.db.current_weather = "Cloudy"

```

> Note that global scripts appear as properties on `GLOBAL_SCRIPTS` based on their `key`. 
If you were to create two global scripts with the same `key` (even with different typeclasses),
the `GLOBAL_SCRIPTS` container will only return one of them (which one depends on order in 
the database). Best is to organize your scripts so that this does not happen. Otherwise, use
`evennia.search_script` to get exactly the script you want.

There are two ways to make a script appear as a property on `GLOBAL_SCRIPTS`. The first is 
to manually create a new global script with `create_script` as mentioned above. Often you want this
to happen automatically when the server starts though. For this you can use the setting
`GLOBAL_SCRIPTS`:

```python
GLOBAL_SCRIPTS = {
    "my_script": {               
        "typeclass": "scripts.Weather",
        "repeats": -1,
        "interval": 50,
        "desc": "Weather script"
        "persistent": True
    },
    "storagescript": {
        "typeclass": "scripts.Storage",
        "persistent": True
    }
}
```
Here the key (`myscript` and `storagescript` above) is required, all other fields are optional. If
`typeclass` is not given, a script of type `settings.BASE_SCRIPT_TYPECLASS` is assumed. The keys
related to timing and intervals are only needed if the script is timed.

Evennia will use the information in `settings.GLOBAL_SCRIPTS` to automatically create and start
these
scripts when the server starts (unless they already exist, based on their `key`). You need to reload
the server before the setting is read and new scripts become available. You can then find the `key`
you gave as properties on `evennia.GLOBAL_SCRIPTS`
(such as `evennia.GLOBAL_SCRIPTS.storagescript`). 
 
> Note: Make sure that your Script typeclass does not have any critical errors. If so, you'll see
errors in your log and your Script will temporarily fall back to being a `DefaultScript` type.

Moreover, a script defined this way is *guaranteed* to exist when you try to access it:
```python
from evennia import GLOBAL_SCRIPTS
# first stop the script 
GLOBAL_SCRIPTS.storagescript.stop()
# running the `scripts` command now will show no storagescript
# but below now it's recreated again! 
storage = GLOBAL_SCRIPTS.storagescript
```
That is, if the script is deleted, next time you get it from `GLOBAL_SCRIPTS`, it will use the
information
in settings to recreate it for you.

> Note that if your goal with the Script is to store persistent data, you should set it as
`persistent=True`, either in `settings.GLOBAL_SCRIPTS` or in the Scripts typeclass. Otherwise any
data you wanted to store on it will be gone (since a new script of the same name is restarted
instead).

## Dealing with Errors

Errors inside an timed, executing script can sometimes be rather terse or point to
parts of the execution mechanism that is hard to interpret. One way to make it
easier to debug scripts is to import Evennia's native logger and wrap your
functions in a try/catch block. Evennia's logger can show you where the
traceback occurred in your script.

```python

from evennia.utils import logger

class Weather(DefaultScript): 

    # [...]

    def at_repeat(self):
        
        try:  
            # [...] code as above
        except Exception:
            # logs the error 
            logger.log_trace()
    
```

## Example of a timed script

In-game you can try out scripts using the `@script` command. In the
`evennia/contrib/tutorial_examples/bodyfunctions.py` is a little example script
that makes you do little 'sounds' at random intervals. Try the following to apply an
example time-based script to your character.

    > @script self = bodyfunctions.BodyFunctions

> Note: Since `evennia/contrib/tutorial_examples` is in the default setting
> `TYPECLASS_PATHS`, we only need to specify the final part of the path,
> that is, `bodyfunctions.BodyFunctions`.

If you want to inflict your flatulence script on another person, place or
thing, try something like the following:

    > @py self.location.search('matt').scripts.add('bodyfunctions.BodyFunctions')

Here's how you stop it on yourself. 

    > @script/stop self = bodyfunctions.BodyFunctions 

This will kill the script again. You can use the `@scripts` command to list all
active scripts in the game, if any (there are none by default). 


For another example of a Script in use, check out the [Turn Based Combat System
tutorial](https://github.com/evennia/evennia/wiki/Turn%20based%20Combat%20System).