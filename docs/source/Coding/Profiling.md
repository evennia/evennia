# Profiling

*This is considered an advanced topic mainly of interest to server developers.*

## Introduction

Sometimes it can be useful to try to determine just how efficient a particular
piece of code is, or to figure out if one could speed up things more than they
are. There are many ways to test the performance of Python and the running
server.

Before digging into this section, remember Donald Knuth's
[words of wisdom](https://en.wikipedia.org/wiki/Program_optimization#When_to_optimize):

> *[...]about 97% of the time: Premature optimization is the root of all evil*.

That is, don't start to try to optimize your code until you have actually
identified a need to do so. This means your code must actually be working before
you start to consider optimization.  Optimization will also often make your code
more complex and harder to read. Consider readability and maintainability and
you may find that a small gain in speed is just not worth it.

## Simple timer tests

Python's `timeit` module is very good for testing small things. For example, in
order to test if it is faster to use a `for` loop or a list comprehension you
could use the following code:

```python
    import timeit
    # Time to do 1000000 for loops
    timeit.timeit("for i in range(100):\n    a.append(i)", setup="a = []")
   <<< 10.70982813835144
    # Time to do 1000000 list comprehensions
    timeit.timeit("a = [i for i in range(100)]")
   <<<  5.358283996582031
```

The `setup` keyword is used to set up things that should not be included in the
time measurement, like `a = []` in the first call.

By default the `timeit` function will re-run the given test 1000000 times and
returns the *total time* to do so (so *not* the average per test). A hint is to
not use this default for testing something that includes database writes - for
that you may want to use a lower number of repeats (say 100 or 1000) using the
`number=100` keyword.

## Using cProfile

Python comes with its own profiler, named cProfile (this is for cPython, no
tests have been done with `pypy` at this point). Due to the way Evennia's
processes are handled, there is no point in using the normal way to start the
profiler (`python -m cProfile evennia.py`). Instead you start the profiler
through the launcher:

    evennia --profiler start

This will start Evennia with the Server component running (in daemon mode) under
cProfile. You could instead try `--profile` with the `portal` argument to
profile the Portal (you would then need to
[start the Server separately](../Setup/Start-Stop-Reload.md)).

Please note that while the profiler is running, your process will use a lot more
memory than usual.  Memory usage is even likely to climb over time. So don't
leave it running perpetually but monitor it carefully (for example using the
`top` command on Linux or the Task Manager's memory display on Windows).

Once you have run the server for a while, you need to stop it so the profiler
can give its report.  Do *not* kill the program from your task manager or by
sending it a kill signal - this will most likely also mess with the profiler.
Instead either use `evennia.py stop` or (which may be even better), use
`@shutdown` from inside the game.

Once the server has fully shut down (this may be a lot slower than usual) you
will find that profiler has created a new file `mygame/server/logs/server.prof`.

### Analyzing the profile

The `server.prof` file is a binary file. There are many ways to analyze and
display its contents, all of which has only been tested in Linux (If you are a
Windows/Mac user, let us know what works).

You can look at the contents of the profile file with Python's in-built `pstats`
module in the evennia shell (it's recommended you install `ipython` with `pip
install ipython` in your virtualenv first, for prettier output):

    evennia shell

Then in the shell

```python
import pstats
from pstats import SortKey

p = pstats.Stats('server/log/server.prof')
p.strip_dirs().sort_stats(-1).print_stats()

```

See the
[Python profiling documentation](https://docs.python.org/3/library/profile.html#instant-user-s-manual)
for more information.

You can also visualize the data in various ways.
- [Runsnake](https://pypi.org/project/RunSnakeRun/) visualizes the profile to
  give a good overview. Install with `pip install runsnakerun`. Note that this
  may require a C compiler and be quite slow to install.
- For more detailed listing of usage time, you can use
  [KCachegrind](http://kcachegrind.sourceforge.net/html/Home.html). To make
  KCachegrind work with Python profiles you also need the wrapper script
  [pyprof2calltree](https://pypi.python.org/pypi/pyprof2calltree/). You can get
  `pyprof2calltree` via `pip` whereas KCacheGrind is something you need to get
  via your package manager or their homepage.

How to analyze and interpret profiling data is not a trivial issue and depends
on what you are profiling for. Evennia being an asynchronous server can also
confuse profiling. Ask on the mailing list if you need help and be ready to be
able to supply your `server.prof` file for comparison, along with the exact
conditions under which it was obtained.

## The Dummyrunner

It is difficult to test "actual" game performance without having players in your
game. For this reason Evennia comes with the *Dummyrunner* system. The
Dummyrunner is a stress-testing system: a separate program that logs into your
game with simulated players (aka "bots" or "dummies"). Once connected, these
dummies will semi-randomly perform various tasks from a list of possible
actions.  Use `Ctrl-C` to stop the Dummyrunner.

```{warning}

    You should not run the Dummyrunner on a production database. It
    will spawn many objects and also needs to run with general permissions.

This is the recommended process for using the dummy runner:
```

1. Stop your server completely with `evennia stop`.
1. At _the end_ of your `mygame/server/conf.settings.py` file, add the line

        from evennia.server.profiling.settings_mixin import *

   This will override your settings and disable Evennia's rate limiters and
   DoS-protections, which would otherwise block mass-connecting clients from
   one IP. Notably, it will also change to a different (faster) password hasher.
1. (recommended): Build a new database. If you use default Sqlite3 and want to
   keep your existing database, just rename `mygame/server/evennia.db3` to
   `mygame/server/evennia.db3_backup` and run `evennia migrate` and `evennia
   start` to create a new superuser as usual.
1. (recommended) Log into the game as your superuser. This is just so you
   can manually check response. If you kept an old database, you will _not_
   be able to connect with an _existing_ user since the password hasher changed!
1. Start the dummyrunner with 10 dummy users from the terminal with

        evennia --dummyrunner 10

   Use `Ctrl-C` (or `Cmd-C`) to stop it.

If you want to see what the dummies are actually doing you can run with a single
dummy:

    evennia --dummyrunner 1

The inputs/outputs from the dummy will then be printed. By default the runner
uses the 'looker' profile, which just logs in and sends the 'look' command
over and over. To change the settings, copy the file
`evennia/server/profiling/dummyrunner_settings.py` to your `mygame/server/conf/`
directory, then add this line to your settings file to use it in the new
location:

    DUMMYRUNNER_SETTINGS_MODULE = "server/conf/dummyrunner_settings.py"

The dummyrunner settings file is a python code module in its own right - it
defines the actions available to the dummies. These are just tuples of command
strings (like "look here") for the dummy to send to the server along with a
probability of them happening. The dummyrunner looks for a global variable
`ACTIONS`, a list of tuples, where the first two elements define the
commands for logging in/out of the server.

Below is a simplified minimal setup (the default settings file adds a lot more
functionality and info):

```python
# minimal dummyrunner setup file

# Time between each dummyrunner "tick", in seconds. Each dummy will be called
# with this frequency.
TIMESTEP = 1

# Chance of a dummy actually performing an action on a given tick. This
# spreads out usage randomly, like it would be in reality.
CHANCE_OF_ACTION = 0.5

# Chance of a currently unlogged-in dummy performing its login action every
# tick. This emulates not all accounts logging in at exactly the same time.
CHANCE_OF_LOGIN = 0.01

# Which telnet port to connect to. If set to None, uses the first default
# telnet port of the running server.
TELNET_PORT = None

# actions

def c_login(client):
    name = f"Character-{client.gid}"
    pwd = f"23fwsf23sdfw23wef23"
    return (
        f"create {name} {pwd}"
        f"connect {name} {pwd}"
    )

def c_logout(client):
    return ("quit", )

def c_look(client):
    return ("look here", "look me")

# this is read by dummyrunner.
ACTIONS = (
    c_login,
    c_logout,
    (1.0, c_look)   # (probability, command-generator)
)

```

At the bottom of the default file are a few default profiles you can test out
by just setting the `PROFILE` variable to one of the options.

### Dummyrunner hints

- Don't start with too many dummies. The Dummyrunner taxes the server much more
  than 'real' users tend to do. Start with 10-100 to begin with.
- Stress-testing can be fun, but also consider what a 'realistic' number of
  users would be for your game.
- Note in the dummyrunner output how many commands/s are being sent to the
  server by all dummies. This is usually a lot higher than what you'd
  realistically expect to see from the same number of users.
- The default settings sets up a 'lag' measure to measaure the round-about
  message time. It updates with an average every 30 seconds. It can be worth to
  have this running for a small number of dummies in one terminal before adding
  more by starting another dummyrunner in another terminal - the first one will
  act as a measure of how lag changes with different loads. Also verify the
  lag-times by entering commands manually in-game.
- Check the CPU usage of your server using `top/htop` (linux). In-game, use the
  `server` command.
- You can run the server with `--profiler start` to test it with dummies. Note
  that the profiler will itself affect server performance, especially memory
  consumption.
- Generally, the dummyrunner system makes for a decent test of general
  performance; but it is of course hard to actually mimic human user behavior.
  For this, actual real-game testing is required.

