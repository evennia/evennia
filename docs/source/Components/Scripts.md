# Scripts

[Script API reference](api:evennia.scripts.scripts)

*Scripts* are the out-of-character siblings to the in-character
[Objects](./Objects). Scripts are so flexible that the name "Script" is a bit limiting
in itself - but we had to pick _something_ to name them. Other possible names
(depending on what you'd use them for) would be `OOBObjects`, `StorageContainers` or `TimerObjects`. 

If you ever consider creating an [Object](./Objects) with a `None`-location just to store some game data,
you should really be using a Script instead.

- Scripts are full [Typeclassed](./Typeclasses) entities - they have [Attributes](./Attributes) and
  can be modified in the same way. But they have _no in-game existence_, so no
  location or command-execution like [Objects](./Objects) and no connection to a particular 
  player/session like [Accounts](./Accounts). This means they are perfectly suitable for acting 
  as database-storage backends for game _systems_: Storing the current state of the economy, 
  who is involved in the current fight, tracking an ongoing barter and so on. They are great as 
  persistent system handlers.
- Scripts have an optional _timer component_. This means that you can set up the script 
  to tick the `at_repeat` hook on the Script at a certain interval. The timer can be controlled 
  independently of the rest of the script as needed. This component is optional
  and complementary to other timing functions in Evennia, like 
  [evennia.utils.delay](api:evennia.utils.utils#evennia.utils.utils.delay) and 
    [evennia.utils.repeat](api:evennia.utils.utils#evennia.utils.utils.repeat).
- Scripts can _attach_ to Objects and Accounts via e.g. `obj.scripts.add/remove`. In the 
  script you can then access the object/account as `self.obj` or `self.account`. This can be used to 
  dynamically extend other typeclasses but also to use the timer component to affect the parent object 
  in various ways. For historical reasons, a Script _not_ attached to an object is referred to as a 
  _Global_ Script.
  
```versionchanged:: 1.0
   In previus Evennia versions, stopping the Script's timer also meant deleting the Script object. 
   Starting with this version, the timer can be start/stopped separately and `.delete()` must be called 
   on the Script explicitly to delete it.

``` 
  
### In-game command examples

There are two main commands controlling scripts in the default cmdset:

The `addscript` command is used for attaching scripts to existing objects:

    > addscript obj = bodyfunctions.BodyFunctions
    
The `scripts` command is used to view all scripts and perform operations on them:

    > scripts
    > scripts/stop bodyfunctions.BodyFunctions
    > scripts/start #244
    > scripts/pause #11
    > scripts/delete #566

```versionchanged:: 1.0
   The `addscript` command used to be only `script` which was easy to confuse with `scripts`.
```

### Code examples

Here are some examples of working with Scripts in-code (more details to follow in later
sections).

Create a new script:
```python
new_script = evennia.create_script(key="myscript", typeclass=...)
```

Create script with timer component:

```python
# (note that this will call `timed_script.at_repeat` which is empty by default)
timed_script = evennia.create_script(key="Timed script", 
                                     interval=34,  # seconds <=0 means off
                                     start_delay=True,  # wait interval before first call
                                     autostart=True)  # start timer (else needing .start() )

# manipulate the script's timer
timed_script.stop()
timed_script.start()
timed_script.pause()                                      
timed_script.unpause()
```

Attach script to another object:

```python
myobj.scripts.add(new_script)
myobj.scripts.add(evennia.DefaultScript)
all_scripts_on_obj = myobj.scripts.all()
```

Search/find scripts in various ways:

```python
# regular search (this is always a list, also if there is only one match)
list_of_myscripts = evennia.search_script("myscript")

# search through Evennia's GLOBAL_SCRIPTS container (based on 
# script's key only)
from evennia import GLOBAL_SCRIPTS

myscript = GLOBAL_SCRIPTS.myscript
GLOBAL_SCRIPTS.get("Timed script").db.foo = "bar"
```

Delete the Script (this will also stop its timer):

```python
new_script.delete()
timed_script.delete()
```

## Defining new Scripts

A Script is defined as a class and is created in the same way as other
[typeclassed](./Typeclasses) entities. The parent class is `evennia.DefaultScript`.


### Simple storage script

In `mygame/typeclasses/scripts.py` is an empty `Script` class already set up. You 
can use this as a base for your own scripts.

```python
# in mygame/typeclasses/scripts.py

from evennia import DefaultScript

class Script(DefaultScript):
    # stuff common for all your scripts goes here

class MyScript(Script):
    def at_script_creation(selfself):
        """Called once, when script is first created"""
        self.key = "myscript"
        self.db.foo = "bar"

```

Once created, this simple Script could act as a global storage:

```python
evennia.create_script('typeclasses.scripts.MyScript')

# from somewhere else 

myscript = evennia.search_script("myscript")
bar = myscript.db.foo
myscript.db.something_else = 1000

```

Note that if you give keyword arguments to `create_script` you can override the values
you set in your `at_script_creation`:

```python

evennia.create_script('typeclasses.scripts.MyScript', key="another name",
                      attributes=[("foo", "bar-alternative")])
            

```

See the [create_script](api:evennia.utils.create#evennia.utils.create.create_script) and 
[search_script](api:evennia.utils.search#evennia.utils.search.search_script) API documentation for more options
on creating and finding Scripts.


### Timed Scripts

There are several properties one can set on the Script to control its timer component.

```python
# in mygame/typeclasses/scripts.py

class TimerScript(Script):

    def at_script_creation(self):
        self.key = "myscript"
        self.desc = "An example script"
        self.interval = 60  # 1 min repeat

    def at_repeat(self):
        # do stuff every minute 

```

This example will call `at_repeat` every minute. The `create_script` function has an `autostart=True` keyword
set by default - this means the script's timer component will be started automatically. Otherwise 
`.start()` must be called separately.

Supported properties are:

- `key` (str): The name of the script. This makes it easier to search for it later. If it's a script 
  attached to another object one can also get all scripts off that object and get the script that way.
- `desc` (str): Note - not `.db.desc`! This is a database field on the Script shown in script listings
  to help identifying what does what.
- `interval` (int): The amount of time (in seconds) between every 'tick' of the timer. Note that 
  it's generally bad practice to use sub-second timers for anything in a text-game - the player will
  not be able to appreciate the precision (and if you print it, it will just spam the screen). For
  calculations you can pretty much always do them on-demand, or at a much slower interval without the 
  player being the wiser.
- `start_delay` (bool): If timer should start right away or wait `interval` seconds first.
- `repeats` (int): If >0, the timer will only run this many times before stopping. Otherwise the 
  number of repeats are infinite. If set to 1, the Script mimics a `delay` action.
- `persistent` (bool): This defaults to `True` and means the timer will survive a server reload/reboot. 
  If not, a reload will have the timer come back in a stopped state. Setting this to `False` will _not_
  delete the Script object itself (use `.delete()` for this). 
  
The timer component is controlled with methods on the Script class: 

- `.at_repeat()` - this method is called every `interval` seconds while the timer is 
  active.
- `.is_valid()` - this method is called by the timer just before `at_repeat()`. If it returns `False`
  the timer is immediately stopped.
- `.start()` - start/update the timer. If keyword arguments are given, they can be used to 
  change `interval`, `start_delay` etc on the fly. This calls the `.at_start()` hook. 
  This is also called after a server reload assuming the timer was not previously stopped.
- `.update()` - legacy alias for `.start`.
- `.stop()`  - stops and resets the timer. This calls the `.at_stop()` hook.
- `.pause()` - pauses the timer where it is, storing its current position. This calls 
  the `.at_pause(manual_pause=True)` hook. This is also called on a server reload/reboot,
  at which time the `manual_pause` will be `False`.
- `.unpause()` - unpause a previously paused script. This will call the `at_start` hook.
- `.time_until_next_repeat()` - get the time until next time the timer fires.
- `.remaining_repeats()` - get the number of repeats remaining, or `None` if repeats are infinite.
- `.reset_callcount()` - this resets the repeat counter to start over from 0. Only useful if `repeats>0`.
- `.force_repeat()` - this prematurely forces `at_repeat` to be called right away. Doing so will reset the
  countdown so that next call will again happen after `interval` seconds.

#### Script timers vs delay/repeat

If the _only_ goal is to get a repeat/delay effect, the 
[evennia.utils.delay](api:evennia.utils.utils#evennia.utils.utils.delay) and 
[evennia.utils.repeat](api:evennia.utils.utils#evennia.utils.utils.repeat) functions
should generally be considered first. A Script is a lot 'heavier' to create/delete on the fly. 
In fact, for making a single delayed call (`script.repeats==1`), the `utils.delay` call is 
probably always the better choice.

For repeating tasks, the `utils.repeat` is optimized for quick repeating of a large number of objects. It
uses the TickerHandler under the hood. Its subscription-based model makes it very efficient to 
start/stop the repeating action for an object. The side effect is however that all objects set to tick 
at a given interval will _all do so at the same time_. This may or may not look strange in-game depending
on the situation. By contrast the Script uses its own ticker that will operate independently from the 
tickers of all other Scripts.

It's also worth noting that once the script object has _already been created_, 
starting/stopping/pausing/unpausing the timer has very little overhead. The pause/unpause and update 
methods of the script also offers a bit more fine-control than using `utils.delays/repeat`.

### Script attached to another object

Scripts can be attached to an [Account](./Accounts) or (more commonly) an [Object](./Objects).
If so, the 'parent object' will be available to the script as either `.obj` or `.account`.


```python
    # mygame/typeclasses/scripts.py  
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

If attached to a room, this Script will randomly report some weather 
to everyone in the room every 5 minutes.

```python
    myroom.scripts.add(scripts.Weather)
```

> Note that `typeclasses` in your game dir is added to the setting `TYPECLASS_PATHS`. 
> Therefore we don't need to give the full path (`typeclasses.scripts.Weather`
> but only `scripts.Weather` above.

You can also attach the script as part of creating it: 

```python
    create_script('typeclasses.weather.Weather', obj=myroom)
```

## Other Script methods 

A Script has all the properties of a typeclassed object, such as `db` and `ndb`(see
[Typeclasses](./Typeclasses)). Setting `key` is useful in order to manage scripts (delete them by name
etc). These are usually set up in the Script's typeclass, but can also be assigned on the fly as
keyword arguments to `evennia.create_script`.

- `at_script_creation()` - this is only called once - when the script is first created.
- `at_server_reload()` - this is called whenever the server is warm-rebooted (e.g. with the
`reload` command). It's a good place to save non-persistent data you might want to survive a
reload.
- `at_server_shutdown()` - this is called when a system reset or systems shutdown is invoked.
- `at_server_start()` - this is called when the server comes back (from reload/shutdown/reboot). It
  can be usuful for initializations and caching of non-persistent data when starting up a script's
  functionality.
- `at_repeat()`
- `at_start()`
- `at_pause()`
- `at_stop()`
- `delete()` - same as for other typeclassed entities, this will delete the Script. Of note is that
  it will also stop the timer (if it runs), leading to the `at_stop` hook being called.

In addition, Scripts support [Attributes](./Attributes), [Tags](./Tags) and [Locks](./Locks) etc like other
Typeclassed entities.

See also the methods involved in controlling a [Timed Script](#Timed_Scripts) above.

## The GLOBAL_SCRIPTS container

A Script not attached to another entity is commonly referred to as a _Global_ script since it't available
to access from anywhere. This means they need to be searched for in order to be used.

Evennia supplies a convenient "container" `evennia.GLOBAL_SCRIPTS` to help organize your global
scripts. All you need is the Script's `key`.


```python
from evennia import GLOBAL_SCRIPTS

# access as a property on the container, named the same as the key
my_script = GLOBAL_SCRIPTS.my_script
# needed if there are spaces in name or name determined on the fly
another_script = GLOBAL_SCRIPTS.get("another script")
# get all global scripts (this returns a Django Queryset)
all_scripts = GLOBAL_SCRIPTS.all()
# you can operate directly on the script
GLOBAL_SCRIPTS.weather.db.current_weather = "Cloudy"

```

```warning::
    Note that global scripts appear as properties on `GLOBAL_SCRIPTS` based on their `key`. 
    If you were to create two global scripts with the same `key` (even with different typeclasses),
    the `GLOBAL_SCRIPTS` container will only return one of them (which one depends on order in 
    the database). Best is to organize your scripts so that this does not happen. Otherwise, use
    `evennia.search_scripts` to get exactly the script you want.
```

There are two ways to make a script appear as a property on `GLOBAL_SCRIPTS`:

1. Manually create a new global script with a `key` using `create_script`.
2. Define the script's properties in the `GLOBAL_SCRIPTS` settings variable. This tells Evennia 
   that it should check if a script with that `key` exists and if not, create it for you.
   This is very useful for scripts that must always exist and/or should be auto-created with your server.

Here's how to tell Evennia to manage the script in settings:

```python
# in mygame/server/conf/settings.py

GLOBAL_SCRIPTS = {
    "my_script": {               
        "typeclass": "scripts.Weather",
        "repeats": -1,
        "interval": 50,
        "desc": "Weather script"
    },
    "storagescript": {}
}
```
Above we add two scripts with keys `myscript` and `storagescript`respectively. The following dict 
can be empty - the `settings.BASE_SCRIPT_TYPECLASS` will then be used. Under the hood, the provided 
dict (along with the `key`) will be passed into `create_script` automatically, so 
all the [same keyword arguments as for create_script](api:evennia.utils.create.create_script) are 
supported here.

```warning::
    Before setting up Evennia to manage your script like this, make sure that your Script typeclass 
    does not have any critical errors (test it separately). If there are, you'll see errors in your log 
    and your Script will temporarily fall back to being a `DefaultScript` type.
```

Moreover, a script defined this way is *guaranteed* to exist when you try to access it:

```python
from evennia import GLOBAL_SCRIPTS
# Delete the script
GLOBAL_SCRIPTS.storagescript.delete()
# running the `scripts` command now will show no storagescript
# but below it's automatically recreated again! 
storage = GLOBAL_SCRIPTS.storagescript
```

That is, if the script is deleted, next time you get it from `GLOBAL_SCRIPTS`, Evennia will use the
information in settings to recreate it for you on the fly. 


## Hints: Dealing with Script Errors

Errors inside a timed, executing script can sometimes be rather terse or point to
parts of the execution mechanism that is hard to interpret. One way to make it
easier to debug scripts is to import Evennia's native logger and wrap your
functions in a try/catch block. Evennia's logger can show you where the
traceback occurred in your script.

```python

from evennia.utils import logger

class Weather(Script): 

    # [...]

    def at_repeat(self):
        
        try:  
            # [...]
        except Exception:
            logger.log_trace()