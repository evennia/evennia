# Profiling

*This is considered an advanced topic mainly of interest to server developers.*

## Introduction

Sometimes it can be useful to try to determine just how efficient a particular piece of code is, or
to figure out if one could speed up things more than they are. There are many ways to test the
performance of Python and the running server.

Before digging into this section, remember Donald Knuth's [words of wisdom](https://en.wikipedia.org/wiki/Program_optimization#When_to_optimize):

> *[...]about 97% of the time: Premature optimization is the root of all evil*.

That is, don't start to try to optimize your code until you have actually identified a need to do
so. This means your code must actually be working before you start to consider optimization.
Optimization will also often make your code more complex and harder to read. Consider readability
and maintainability and you may find that a small gain in speed is just not worth it.

## Simple timer tests

Python's `timeit` module is very good for testing small things. For example, in order to test if it is faster to use a `for` loop or a list comprehension you could use the following code:

```python
    import timeit
    # Time to do 1000000 for loops
    timeit.timeit("for i in range(100):\n    a.append(i)", setup="a = []")
   <<< 10.70982813835144
    # Time to do 1000000 list comprehensions
    timeit.timeit("a = [i for i in range(100)]")
   <<<  5.358283996582031
```

The `setup` keyword is used to set up things that should not be included in the time measurement, like `a = []` in the first call.

By default the `timeit` function will re-run the given test 1000000 times and returns the *total time* to do so (so *not* the average per test). A hint is to not use this default for testing something that includes database writes - for that you may want to use a lower number of repeats (say 100 or 1000) using the `number=100` keyword.

## Using cProfile

Python comes with its own profiler, named cProfile (this is for cPython, no tests have been done with `pypy` at this point). Due to the way Evennia's processes are handled, there is no point in using the normal way to start the profiler (`python -m cProfile evennia.py`). Instead you start the profiler through the launcher:

    evennia --profiler start

This will start Evennia with the Server component running (in daemon mode) under cProfile. You could instead try `--profile` with the `portal` argument to profile the Portal (you would then need to [start the Server separately](Start-Stop-Reload)).

Please note that while the profiler is running, your process will use a lot more memory than usual. Memory usage is even likely to climb over time. So don't leave it running perpetually but monitor it carefully (for example using the `top` command on Linux or the Task Manager's memory display on Windows).

Once you have run the server for a while, you need to stop it so the profiler can give its report. Do *not* kill the program from your task manager or by sending it a kill signal - this will most likely also mess with the profiler. Instead either use `evennia.py stop` or (which may be even better), use `@shutdown` from inside the game.

Once the server has fully shut down (this may be a lot slower than usual) you will find that profiler has created a new file `mygame/server/logs/server.prof`.

## Analyzing the profile

The `server.prof` file is a binary file. There are many ways to analyze and display its contents, all of which has only been tested in Linux (If you are a Windows/Mac user, let us know what works).

We recommend the
[Runsnake](http://www.vrplumber.com/programming/runsnakerun/) visualizer to see the processor usage of different processes in a graphical form. For more detailed listing of usage time, you can use [KCachegrind](http://kcachegrind.sourceforge.net/html/Home.html). To make KCachegrind work with Python profiles you also need the wrapper script [pyprof2calltree](https://pypi.python.org/pypi/pyprof2calltree/). You can get pyprof2calltree via `pip` whereas KCacheGrind is something you need to get via your package manager or their homepage.

How to analyze and interpret profiling data is not a trivial issue and depends on what you are profiling for. Evennia being an asynchronous server can also confuse profiling. Ask on the mailing list if you need help and be ready to be able to supply your `server.prof` file for comparison, along with the exact conditions under which it was obtained.

## The Dummyrunner

It is difficult to test "actual" game performance without having players in your game. For this reason Evennia comes with the *Dummyrunner* system. The Dummyrunner is a stress-testing system: a separate program that logs into your game with simulated players (aka "bots" or "dummies"). Once connected these dummies will semi-randomly perform various tasks from a list of possible actions. Use `Ctrl-C` to stop the Dummyrunner.

> Warning: You should not run the Dummyrunner on a production database. It will spawn many objects and also needs to run with general permissions.

To launch the Dummyrunner, first start your server normally (with or without profiling, as above). Then start a new terminal/console window and active your virtualenv there too. In the new terminal, try to connect 10 dummy players:

    evennia --dummyrunner 10

The first time you do this you will most likely get a warning from Dummyrunner. It will tell you to copy an import string to the end of your settings file. Quit the Dummyrunner (`Ctrl-C`) and follow the instructions. Restart Evennia and try `evennia --dummyrunner 10` again. Make sure to remove that extra settings line when running a public server.

The actions perform by the dummies is controlled by a settings file. The default Dummyrunner settings file is `evennia/server/server/profiling/dummyrunner_settings.py` but you shouldn't modify this directly. Rather create/copy the default file to `mygame/server/conf/` and modify it there. To make sure to use your file over the default, add the following line to your settings file:

```python
DUMMYRUNNER_SETTINGS_MODULE = "server/conf/dummyrunner_settings.py"
```

> Hint: Don't start with too many dummies. The Dummyrunner defaults to taxing the server much more intensely than an equal number of human players. A good dummy number to start with is 10-100.

Once you have the dummyrunner running, stop it with `Ctrl-C`.

Generally, the dummyrunner system makes for a decent test of general performance; but it is of
course hard to actually mimic human user behavior. For this, actual real-game testing is required.
