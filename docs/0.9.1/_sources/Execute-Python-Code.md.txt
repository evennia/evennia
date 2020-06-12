# Execute Python Code


The `@py` command supplied with the default command set of Evennia allows you to execute Python commands directly from inside the game.  An alias to `@py` is simply "`!`". *Access to the `@py` command should be severely restricted*. This is no joke - being able to execute arbitrary Python code on the server is not something you should entrust to just anybody.

    @py 1+2 
    <<< 3

## Available variables 

A few local variables are made available when running `@py`. These offer entry into the running system.

- **self** / **me** - the calling object (i.e. you)
- **here** - the current caller's location
- **obj** - a dummy [Object](Objects) instance
- **evennia** - Evennia's [flat API](Evennia-API) - through this you can access all of Evennia.

For accessing other objects in the same room you need to use `self.search(name)`. For objects in other locations, use one of the `evennia.search_*` methods. See [below](Execute-Python-Code#finding-objects).

## Returning output

This is an example where we import and test one of Evennia's utilities found in `src/utils/utils.py`, but also accessible through `ev.utils`:

    @py from ev import utils; utils.time_format(33333)
    <<< Done.

Note that we didn't get any return value, all we where told is that the code finished executing without error. This is often the case in more complex pieces of code which has no single obvious return value.  To see the output from the `time_format()` function we need to tell the system to echo it to us explicitly with `self.msg()`.

    @py from ev import utils; self.msg(str(utils.time_format(33333)))
    09:15
    <<< Done.

> Warning: When using the `msg` function wrap our argument in `str()` to convert it into a string above. This is not strictly necessary for most types of data (Evennia will usually convert to a string behind the scenes for you). But for *lists* and *tuples* you will be confused by the output if you don't wrap them in `str()`: only the first item of the iterable will be returned. This is because doing `msg(text)` is actually just a convenience shortcut; the full argument that `msg` accepts is something called an *outputfunc* on the form `(cmdname, (args), {kwargs})` (see [the message path](Messagepath) for more info). Sending a list/tuple confuses Evennia to think you are sending such a structure. Converting it to a string however makes it clear it should just be displayed as-is. 

If you were to use Python's standard `print`, you will see the result in your current `stdout` (your terminal by default, otherwise your log file).

## Finding objects

A common use for `@py` is to explore objects in the database, for debugging and performing specific operations that are not covered by a particular command. 

Locating an object is best done using `self.search()`:

    @py self.search("red_ball")
    <<< Ball 
    
    @py self.search("red_ball").db.color = "red"
    <<< Done. 
    
    @py self.search("red_ball").db.color
    <<< red

`self.search()` is by far the most used case, but you can also search other database tables for other Evennia entities like scripts or configuration entities. To do this you can use the generic search entries found in `ev.search_*`.

    @py evennia.search_script("sys_game_time")
    <<< [<src.utils.gametime.GameTime object at 0x852be2c>]

(Note that since this becomes a simple statement, we don't have to wrap it in `self.msg()` to get the output). You can also use the database model managers directly (accessible through the `objects` properties of database models or as `evennia.managers.*`). This is a bit more flexible since it gives you access to the full range of database search methods defined in each manager.

    @py evennia.managers.scripts.script_search("sys_game_time")
    <<< [<src.utils.gametime.GameTime object at 0x852be2c>]

The managers are useful for all sorts of database studies.

    @py ev.managers.configvalues.all()
    <<< [<ConfigValue: default_home]>, <ConfigValue:site_name>, ...]

## Testing code outside the game

`@py` has the advantage of operating inside a running server (sharing the same process), where you can test things in real time. Much of this *can* be done from the outside too though. 

In a terminal, cd to the top of your game directory (this bit is important since we need access to your config file) and run

    evennia shell

Your default Python interpreter will start up, configured to be able to work with and import all modules of your Evennia installation. From here you can explore the database and test-run individual modules as desired.

It's recommended that you get a more fully featured Python interpreter like [iPython](http://ipython.scipy.org/moin/). If you use a virtual environment, you can just get it with `pip install ipython`. IPython allows you to better work over several lines, and also has a lot of other editing features, such as tab-completion and `__doc__`-string reading.

    $ evennia shell
    
    IPython 0.10 -- An enhanced Interactive Python
    ...
    
    In [1]: import evennia
    In [2]: evennia.managers.objects.all()
    Out[3]: [<ObjectDB: Harry>, <ObjectDB: Limbo>, ...]

See the page about the [Evennia-API](Evennia-API) for more things to explore. 
