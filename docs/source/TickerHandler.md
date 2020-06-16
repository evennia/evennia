# TickerHandler


One way to implement a dynamic MUD is by using "tickers", also known as "heartbeats". A ticker is a
timer that fires ("ticks") at a given interval. The tick triggers updates in various game systems.

## About Tickers

Tickers are very common or even unavoidable in other mud code bases.  Certain code bases are even
hard-coded to rely on the concept of the global 'tick'. Evennia has no such notion - the decision to
use tickers is very much up to the need of your game and which requirements you have. The "ticker
recipe" is just one way of cranking the wheels.

The most fine-grained way to manage the flow of time is of course to use [Scripts](Scripts). Many
types of operations (weather being the classic example) are however done on multiple objects in the
same way at regular intervals, and for this, storing separate Scripts on each object is inefficient.
The way to do this is to use a ticker with a "subscription model" - let objects sign up to be
triggered at the same interval, unsubscribing when the updating is no longer desired.

Evennia offers an optimized implementation of the subscription model - the *TickerHandler*. This is
a singleton global handler reachable from `evennia.TICKER_HANDLER`. You can assign any *callable* (a
function or, more commonly, a method on a database object) to this handler. The TickerHandler will
then call this callable at an interval you specify, and with the arguments you supply when adding
it. This continues until the callable un-subscribes from the ticker. The handler survives a reboot
and is highly optimized in resource usage.

Here is an example of importing `TICKER_HANDLER` and using it: 

```python
    # we assume that obj has a hook "at_tick" defined on itself
    from evennia import TICKER_HANDLER as tickerhandler    

    tickerhandler.add(20, obj.at_tick)
``` 

That's it - from now on, `obj.at_tick()` will be called every 20 seconds. 

You can also import function and tick that: 

```python
    from evennia import TICKER_HANDLER as tickerhandler
    from mymodule import myfunc

    tickerhandler.add(30, myfunc)
```

Removing (stopping) the ticker works as expected: 

```python
    tickerhandler.remove(20, obj.at_tick)
    tickerhandler.remove(30, myfunc) 
```

Note that you have to also supply `interval` to identify which subscription to remove. This is
because the TickerHandler maintains a pool of tickers and a given callable can subscribe to be
ticked at any number of different intervals.

The full definition of the `tickerhandler.add` method is

```python
    tickerhandler.add(interval, callback, 
                      idstring="", persistent=True, *args, **kwargs)
```

Here `*args` and `**kwargs` will be passed to `callback` every `interval` seconds. If `persistent`
is `False`, this subscription will not survive a server reload.

Tickers are identified and stored by making a key of the callable itself, the ticker-interval, the
`persistent` flag and the `idstring` (the latter being an empty string when not given explicitly).

Since the arguments are not included in the ticker's identification, the `idstring` must be used to
have a specific callback triggered multiple times on the same interval but with different arguments:

```python
    tickerhandler.add(10, obj.update, "ticker1", True, 1, 2, 3)
    tickerhandler.add(10, obj.update, "ticker2", True, 4, 5)
```

> Note that, when we want to send arguments to our callback within a ticker handler, we need to
specify `idstring` and `persistent` before, unless we call our arguments as keywords, which would
often be more readable:

```python
    tickerhandler.add(10, obj.update, caller=self, value=118)
```

If you add a ticker with exactly the same combination of callback, interval and idstring, it will
overload the existing ticker. This identification is also crucial for later removing (stopping) the
subscription:

```python
    tickerhandler.remove(10, obj.update, idstring="ticker1")
    tickerhandler.remove(10, obj.update, idstring="ticker2")
```

The `callable` can be on any form as long as it accepts the arguments you give to send to it in
`TickerHandler.add`.

> Note that everything you supply to the TickerHandler will need to be pickled at some point to be
saved into the database. Most of the time the handler will correctly store things like database
objects, but the same restrictions as for [Attributes](Attributes) apply to what the TickerHandler
may store.

When testing, you can stop all tickers in the entire game with `tickerhandler.clear()`. You can also
view the currently subscribed objects with `tickerhandler.all()`.

See the [Weather Tutorial](Weather-Tutorial) for an example of using the TickerHandler.

### When *not* to use TickerHandler

Using the TickerHandler may sound very useful but it is important to consider when not to use it.
Even if you are used to habitually relying on tickers for everything in other code bases, stop and
think about what you really need it for. This is the main point:
 
> You should *never*  use  a ticker to catch *changes*. 

Think about it - you might have to run the ticker every second to react to the change fast enough.
Most likely nothing will have changed at a given moment. So you are doing pointless calls (since
skipping the call gives the same result as doing it). Making sure nothing's changed might even be
computationally expensive depending on the complexity of your system. Not to mention that you might
need to run the check *on every object in the database*. Every second. Just to maintain status quo
...

Rather than checking over and over on the off-chance that something changed, consider a more
proactive approach. Could you implement your rarely changing system to *itself* report when its
status changes?  It's almost always much cheaper/efficient if you can do things "on demand". Evennia
itself uses hook methods for this very reason.

So, if you consider a ticker that will fire very often but which you expect to have no effect 99% of
the time, consider handling things things some other way. A self-reporting on-demand solution is
usually cheaper also for fast-updating properties. Also remember that some things may not need to be
updated until someone actually is examining or using them - any interim changes happening up to that
moment are pointless waste of computing time.

The main reason for needing a ticker is when you want things to happen to multiple objects at the
same time without input from something else.