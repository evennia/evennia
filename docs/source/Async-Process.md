# Async Process


*This is considered an advanced topic.*

## Synchronous versus Asynchronous

Most program code operates *synchronously*. This means that each statement in your code gets
processed and finishes before the next can begin. This makes for easy-to-understand code. It is also
a *requirement* in many cases - a subsequent piece of code often depend on something calculated or
defined in a previous statement.

Consider this piece of code in a traditional Python program:

```python
    print("before call ...")
    long_running_function()
    print("after call ...")

```

When run, this will print `"before call ..."`, after which the `long_running_function` gets to work
for however long time. Only once that is done, the system prints `"after call ..."`. Easy and
logical to follow. Most of Evennia work in this way and often it's important that commands get
executed in the same strict order they were coded.

Evennia, via Twisted, is a single-process multi-user server. In simple terms this means that it
swiftly switches between dealing with player input so quickly that each player feels like they do
things at the same time.  This is a clever illusion however: If one user, say, runs a command
containing that `long_running_function`, *all* other players are effectively forced to wait until it
finishes.

Now, it should be said that on a modern computer system this is rarely an issue. Very few commands
run so long that other users notice it.  And as mentioned, most of the time you *want* to enforce
all commands to occur in strict sequence.

When delays do become noticeable and you don't care in which order the command actually completes,
you can run it *asynchronously*. This makes use of the `run_async()` function in
`src/utils/utils.py`:

```python
    run_async(function, *args, **kwargs)
```

Where `function` will be called asynchronously with `*args` and `**kwargs`. Example:

```python
    from evennia import utils
    print("before call ...")
    utils.run_async(long_running_function)
    print("after call ...")
```

Now, when running this you will find that the program will not wait around for
`long_running_function` to finish. In fact you will see `"before call ..."` and `"after call ..."`
printed out right away. The long-running function will run in the background and you (and other
users) can go on as normal.

## Customizing asynchronous operation

A complication with using asynchronous calls is what to do with the result from that call. What if
`long_running_function` returns a value that you need? It makes no real sense to put any lines of
code after the call to try to deal with the result from `long_running_function` above - as we saw
the `"after call ..."` got printed long before `long_running_function` was finished, making that
line quite pointless for processing any data from the function. Instead one has to use *callbacks*.

`utils.run_async` takes reserved kwargs that won't be passed into the long-running function:

- `at_return(r)` (the *callback*) is called when the asynchronous function (`long_running_function`
  above) finishes successfully. The argument `r` will then be the return value of that function (or
  `None`).

    ```python
        def at_return(r):
            print(r)
    ```

- `at_return_kwargs` - an optional dictionary that will be fed as keyword arguments to the
`at_return` callback.
- `at_err(e)` (the *errback*) is called if the asynchronous function fails and raises an exception.
  This exception is passed to the errback wrapped in a *Failure* object `e`. If you do not supply an
  errback of your own, Evennia will automatically add one that silently writes errors to the evennia
  log. An example of an errback is found below:

```python
        def at_err(e):
            print("There was an error:", str(e))
```

- `at_err_kwargs` - an optional dictionary that will be fed as keyword arguments to the `at_err`
  errback.

An example of making an asynchronous call from inside a [Command](./Commands) definition:

```python
    from evennia import utils, Command

    class CmdAsync(Command):

       key = "asynccommand"

       def func(self):

           def long_running_function():
               #[... lots of time-consuming code  ...]
               return final_value

           def at_return_function(r):
               self.caller.msg(f"The final value is {r}")

           def at_err_function(e):
               self.caller.msg(f"There was an error: {e}")

           # do the async call, setting all callbacks
           utils.run_async(long_running_function, at_return=at_return_function,
at_err=at_err_function)
```

That's it - from here on we can forget about `long_running_function` and go on with what else need
to be done. *Whenever* it finishes, the `at_return_function` function will be called and the final
value will
pop up for us to see. If not we will see an error message.

## delay

The `delay` function is a much simpler sibling to `run_async`. It is in fact just a way to delay the
execution of a command until a future time. This is equivalent to something like `time.sleep()`
except delay is asynchronous while `sleep` would lock the entire server for the duration of the
sleep.

```python
     from evennia.utils import delay

     # [...]
     # e.g. inside a Command, where `self.caller` is available
     def callback(obj):
        obj.msg("Returning!")
     delay(10, callback, self.caller)
```

This will delay the execution of the callback for 10 seconds. This function is explored much more in
the [Command Duration Tutorial](./Command-Duration).

You can also try the following snippet just see how it works:

    @py from evennia.utils import delay; delay(10, lambda who: who.msg("Test!"), self)

Wait 10 seconds and 'Test!' should be echoed back to you.


## The @interactive decorator

As of Evennia 0.9, the `@interactive` [decorator](https://realpython.com/primer-on-python-decorators/)
is available. This makes any function or method possible to 'pause' and/or await player input
in an interactive way.

```python
    from evennia.utils import interactive

    @interactive
    def myfunc(caller):

      while True:
          caller.msg("Getting ready to wait ...")
          yield(5)
          caller.msg("Now 5 seconds have passed.")

          response = yield("Do you want to wait another 5 secs?")

          if response.lower() not in ("yes", "y"):
              break
```

The `@interactive` decorator gives the function the ability to pause. The use
of `yield(seconds)` will do just that - it will asynchronously pause for the
number of seconds given before continuing. This is technically equivalent to
using `call_async` with a callback that continues after 5 secs. But the code
with `@interactive` is a little easier to follow.

Within the `@interactive` function, the `response = yield("question")` question
allows you to ask the user for input. You can then process the input, just like
you would if you used the Python `input` function. There is one caveat to this
functionality though - _it will only work if the function/method has an
argument named exactly `caller`_.  This is because internally Evennia will look
for the `caller` argument and treat that as the source of input.

All of this makes the `@interactive` decorator very useful. But it comes with a
few caveats. Notably, decorating a function/method with `@interactive` turns it
into a Python [generator](https://wiki.python.org/moin/Generators). The most
common issue is that you cannot use `return <value>` from a generator (just an
empty `return` works). To return a value from a function/method you have decorated
with `@interactive`, you must instead use a special Twisted function
`twisted.internet.defer.returnValue`. Evennia also makes this function
conveniently available from `evennia.utils`:

```python
    from evennia.utils import interactive, returnValue

    @interactive
    def myfunc():

        # ...
        result = 10

        # this must be used instead of `return result`
        returnValue(result)

```



## Assorted notes

Overall, be careful with choosing when to use asynchronous calls. It is mainly useful for large
administration operations that have no direct influence on the game world (imports and backup
operations come to mind). Since there is no telling exactly when an asynchronous call actually ends,
using them for in-game commands is to potentially invite confusion and inconsistencies (and very
hard-to-reproduce bugs).

The very first synchronous example above is not *really* correct in the case of Twisted, which is
inherently an asynchronous server.  Notably you might find that you will *not* see the first `before
call ...` text being printed out right away. Instead all texts could end up being delayed until
after the long-running process finishes. So all commands will retain their relative order as
expected, but they may appear with delays or in groups.

## Further reading

Technically, `run_async` is just a very thin and simplified wrapper around a
[Twisted Deferred](http://twistedmatrix.com/documents/9.0.0/core/howto/defer.html) object; the
wrapper sets
up a default errback also if none is supplied. If you know what you are doing there is nothing
stopping you from bypassing the utility function, building a more sophisticated callback chain after
your own liking.
