# Coding Utils


Evennia comes with many utilities to help with common coding tasks. Most are accessible directly
from the flat API, otherwise you can find them in the `evennia/utils/` folder.

> This is just a small selection of the tools in `evennia/utils`. It's worth to browse [the directory](evennia.utils) and in particular the content of [evennia/utils/utils.py](evennia.utils.utils) directly to find more useful stuff.

## Searching

A common thing to do is to search for objects. There it's easiest to use the `search` method defined
on all objects. This will search for objects in the same location and inside the self object:

```python
     obj = self.search(objname)
```

The most common time one needs to do this is inside a command body. `obj = self.caller.search(objname)` will search inside the caller's (typically, the character that typed the command) `.contents` (their "inventory") and `.location` (their "room").

Give the keyword `global_search=True` to extend search to encompass entire database. Aliases will also be matched by this search. You will find multiple examples of this functionality in the default command set.

If you need to search for objects in a code module you can use the functions in
`evennia.utils.search`. You can access these as shortcuts `evennia.search_*`.

```python
     from evennia import search_object
     obj = search_object(objname)
```

- [evennia.search_account](evennia.accounts.manager.AccountDBManager.search_account)
- [evennia.search_object](evennia.objects.manager.ObjectDBManager.search_object)
- [evennia.search(object)_by_tag](evennia.utils.search.search_tag)
- [evennia.search_script](evennia.scripts.manager.ScriptDBManager.search_script)
- [evennia.search_channel](evennia.comms.managers.ChannelDBManager.search_channel)
- [evennia.search_message](evennia.comms.managers.MsgManager.search_message)
- [evennia.search_help](evennia.help.manager.HelpEntryManager.search_help)

Note that these latter methods will always return a `list` of results, even if the list has one or zero entries.

## Create

Apart from the in-game build commands (`@create` etc), you can also build all of Evennia's game entities directly in code (for example when defining new create commands).

```python
   import evennia

   myobj = evennia.create_objects("game.gamesrc.objects.myobj.MyObj", key="MyObj")
```

- [evennia.create_account](evennia.utils.create.create_account)
- [evennia.create_object](evennia.utils.create.create_object)
- [evennia.create_script](evennia.utils.create.create_script)
- [evennia.create_channel](evennia.utils.create.create_channel)
- [evennia.create_help_entry](evennia.utils.create.create_help_entry)
- [evennia.create_message](evennia.utils.create.create_message)

Each of these create-functions have a host of arguments to further customize the created entity. See `evennia/utils/create.py` for more information.

## Logging

Normally you can use Python `print` statements to see output to the terminal/log. The `print`
statement should only be used for debugging though. For producion output, use the `logger` which will create proper logs either to terminal or to file.

```python
     from evennia import logger
     #
     logger.log_err("This is an Error!")
     logger.log_warn("This is a Warning!")
     logger.log_info("This is normal information")
     logger.log_dep("This feature is deprecated")
```

There is a special log-message type, `log_trace()` that is intended to be called from inside a traceback - this can be very useful for relaying the traceback message back to log without having it
kill the server.

```python
     try:
       # [some code that may fail...]
     except Exception:
       logger.log_trace("This text will show beneath the traceback itself.")
```

The `log_file` logger,  finally, is a very useful logger for outputting arbitrary log messages. This is a heavily optimized asynchronous log mechanism using [threads](https://en.wikipedia.org/wiki/Thread_%28computing%29) to avoid overhead. You should be able to use it for very heavy custom logging without fearing disk-write delays.

```python
 logger.log_file(message, filename="mylog.log")
```

If not an absolute path is given, the log file will appear in the `mygame/server/logs/` directory. If the file already exists, it will be appended to. Timestamps on the same format as the normal Evennia logs will be automatically added to each entry.  If a filename is not specified, output will be written to a file `game/logs/game.log`.

See also the [Debugging](../Coding/Debugging.md) documentation for help with finding elusive bugs.

## Time Utilities

### Game time

Evennia tracks the current server time. You can access this time via the `evennia.gametime` shortcut:

```python
from evennia import gametime

# all the functions below return times in seconds).

# total running time of the server
runtime = gametime.runtime()
# time since latest hard reboot (not including reloads)
uptime = gametime.uptime()
# server epoch (its start time)
server_epoch = gametime.server_epoch()

# in-game epoch (this can be set by `settings.TIME_GAME_EPOCH`.
# If not, the server epoch is used.
game_epoch = gametime.game_epoch()
# in-game time passed since time started running
gametime = gametime.gametime()
# in-game time plus game epoch (i.e. the current in-game
# time stamp)
gametime = gametime.gametime(absolute=True)
# reset the game time (back to game epoch)
gametime.reset_gametime()

```

The setting `TIME_FACTOR` determines how fast/slow in-game time runs compared to the real world. The setting `TIME_GAME_EPOCH` sets the starting game epoch (in seconds). The functions from the `gametime` module all return their times in seconds. You can convert this to whatever units of time you desire for your game. You can use the `@time` command to view the server time info. 
You can also *schedule* things to happen at specific in-game times using the [gametime.schedule](evennia.utils.gametime.schedule) function:

```python
import evennia

def church_clock:
    limbo = evennia.search_object(key="Limbo")
    limbo.msg_contents("The church clock chimes two.")

gametime.schedule(church_clock, hour=2)
```

### utils.time_format()

This function takes a number of seconds as input (e.g. from the `gametime` module above) and converts it to a nice text output in days, hours etc. It's useful when you want to show how old something is. It converts to four different styles of output using the *style* keyword: 

- style 0 - `5d:45m:12s` (standard colon output)
- style 1 - `5d` (shows only the longest time unit)
- style 2 - `5 days, 45 minutes` (full format, ignores seconds)
- style 3 - `5 days, 45 minutes, 12 seconds` (full format, with seconds)

### utils.delay()

This allows for making a delayed call. 

```python
from evennia import utils

def _callback(obj, text):
    obj.msg(text)

# wait 10 seconds before sending "Echo!" to obj (which we assume is defined)
utils.delay(10, _callback, obj, "Echo!", persistent=False)

# code here will run immediately, not waiting for the delay to fire!

```

See [The Asynchronous process](../Concepts/Async-Process.md#delay) for more information.

## Finding Classes

### utils.inherits_from()

This useful function takes two arguments - an object to check and a parent. It returns `True` if object inherits from parent *at any distance* (as opposed to Python's in-built `is_instance()` that
will only catch immediate dependence). This function also accepts as input any combination of
classes, instances or python-paths-to-classes.

Note that Python code should usually work with [duck typing](https://en.wikipedia.org/wiki/Duck_typing). But in Evennia's case it can sometimes be useful to check if an object inherits from a given [Typeclass](./Typeclasses.md) as a way of identification. Say for example that we have a typeclass *Animal*. This has a subclass *Felines* which in turn has a subclass *HouseCat*. Maybe there are a bunch of other animal types too, like horses and dogs. Using `inherits_from` will allow you to check for all animals in one go:

```python
     from evennia import utils
     if (utils.inherits_from(obj, "typeclasses.objects.animals.Animal"):
        obj.msg("The bouncer stops you in the door. He says: 'No talking animals allowed.'")
```

## Text utilities

In a text game, you are naturally doing a lot of work shuffling text back and forth. Here is a *non-
complete* selection of text utilities found in `evennia/utils/utils.py` (shortcut `evennia.utils`).
If nothing else it can be good to look here before starting to develop a solution of your own.

### utils.fill()

This flood-fills a text to a given width (shuffles the words to make each line evenly wide). It also indents as needed.

```python
     outtxt = fill(intxt, width=78, indent=4)
```

### utils.crop()

This function will crop a very long line, adding a suffix to show the line actually continues. This
can be useful in listings when showing multiple lines would mess up things.

```python
     intxt = "This is a long text that we want to crop."
     outtxt = crop(intxt, width=19, suffix="[...]")
     # outtxt is now "This is a long text[...]"
```

### utils.dedent()

This solves what may at first glance appear to be a trivial problem with text - removing indentations. It is used to shift entire paragraphs to the left, without disturbing any further formatting they may have. A common case for this is when using Python triple-quoted strings in code - they will retain whichever indentation they have in the code, and to make easily-readable source code one usually don't want to shift the string to the left edge.

```python
    #python code is entered at a given indentation
          intxt = """
          This is an example text that will end
          up with a lot of whitespace on the left.
                    It also has indentations of
                    its own."""
          outtxt = dedent(intxt)
          # outtxt will now retain all internal indentation
          # but be shifted all the way to the left.
```

Normally you do the dedent in the display code (this is for example how the help system homogenizes
help entries).

### to_str() and to_bytes()

Evennia supplies two utility functions for converting text to the correct encodings. `to_str()` and `to_bytes()`. Unless you are adding a custom protocol and need to send byte-data over the wire, `to_str` is the only one you'll need. 

The difference from Python's in-built `str()` and `bytes()` operators are that the Evennia ones makes use of the `ENCODINGS` setting and will try very hard to never raise a traceback but instead echo errors through logging. See [here](../Concepts/Text-Encodings.md) for more info.