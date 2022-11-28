"""
TickerHandler

This implements an efficient Ticker which uses a subscription
model to 'tick' subscribed objects at regular intervals.

The ticker mechanism is used by importing and accessing
the instantiated TICKER_HANDLER instance in this module. This
instance is run by the server; it will save its status across
server reloads and be started automaticall on boot.

Example:

```python
    from evennia.scripts.tickerhandler import TICKER_HANDLER

    # call tick myobj.at_tick(*args, **kwargs) every 15 seconds
    TICKER_HANDLER.add(15, myobj.at_tick, *args, **kwargs)
```

You supply the interval to tick and a callable to call regularly with
any extra args/kwargs. The callable should either be a stand-alone
function in a module *or* the method on a *typeclassed* entity (that
is, on an object that can be safely and stably returned from the
database).  Functions that are dynamically created or sits on
in-memory objects cannot be used by the tickerhandler (there is no way
to reference them safely across reboots and saves).

The handler will transparently set
up and add new timers behind the scenes to tick at given intervals,
using a TickerPool - all callables with the same interval will share
the interval ticker.

To remove:

```python
    TICKER_HANDLER.remove(15, myobj.at_tick)
```

Both interval and callable must be given since a single object can be subscribed
to many different tickers at the same time. You can also supply `idstring`
as an identifying string if you ever want to tick the callable at the same interval
but with different arguments (args/kwargs are not used for identifying the ticker). There
is also `persistent=False` if you don't want to make a ticker that don't survive a reload.
If either or both `idstring` or `persistent` has been changed from their defaults, they
must be supplied to the `TICKER_HANDLER.remove` call to properly identify the ticker
to remove.

The TickerHandler's functionality can be overloaded by modifying the
Ticker class and then changing TickerPool and TickerHandler to use the
custom classes

```python
class MyTicker(Ticker):
    # [doing custom stuff]

class MyTickerPool(TickerPool):
    ticker_class = MyTicker
class MyTickerHandler(TickerHandler):
    ticker_pool_class = MyTickerPool
```

If one wants to duplicate TICKER_HANDLER's auto-saving feature in
a  custom handler one can make a custom `AT_STARTSTOP_MODULE` entry to
call the handler's `save()` and `restore()` methods when the server reboots.

"""
import inspect

from django.core.exceptions import ObjectDoesNotExist
from twisted.internet.defer import inlineCallbacks

from evennia.scripts.scripts import ExtendedLoopingCall
from evennia.server.models import ServerConfig
from evennia.utils import inherits_from, variable_from_module
from evennia.utils.dbserialize import dbserialize, dbunserialize, pack_dbobj
from evennia.utils.logger import log_err, log_trace

_GA = object.__getattribute__
_SA = object.__setattr__


_ERROR_ADD_TICKER = """TickerHandler: Tried to add an invalid ticker:
{store_key}
Ticker was not added."""

_ERROR_ADD_TICKER_SUB_SECOND = """You are trying to add a ticker running faster
than once per second. This is not supported and also probably not useful:
Spamming messages to the user faster than once per second serves no purpose in
a text-game, and if you want to update some property, consider doing so
on-demand rather than using a ticker.
"""


class Ticker(object):
    """
    Represents a repeatedly running task that calls
    hooks repeatedly. Overload `_callback` to change the
    way it operates.
    """

    @inlineCallbacks
    def _callback(self):
        """
        This will be called repeatedly every `self.interval` seconds.
        `self.subscriptions` contain tuples of (obj, args, kwargs) for
        each subscribing object.

        If overloading, this callback is expected to handle all
        subscriptions when it is triggered. It should not return
        anything and should not traceback on poorly designed hooks.
        The callback should ideally work under @inlineCallbacks so it
        can yield appropriately.

        The _hook_key, which is passed down through the handler via
        kwargs is used here to identify which hook method to call.

        """
        self._to_add = []
        self._to_remove = []
        self._is_ticking = True
        for store_key, (args, kwargs) in self.subscriptions.items():
            callback = yield kwargs.pop("_callback", "at_tick")
            obj = yield kwargs.pop("_obj", None)
            try:
                if callable(callback):
                    # call directly
                    yield callback(*args, **kwargs)
                    continue
                # try object method
                if not obj or not obj.pk:
                    # object was deleted between calls
                    self._to_remove.append(store_key)
                    continue
                else:
                    yield _GA(obj, callback)(*args, **kwargs)
            except ObjectDoesNotExist:
                log_trace("Removing ticker.")
                self._to_remove.append(store_key)
            except Exception:
                log_trace()
            finally:
                # make sure to re-store
                kwargs["_callback"] = callback
                kwargs["_obj"] = obj
        # cleanup - we do this here to avoid changing the subscription dict while it loops
        self._is_ticking = False
        for store_key in self._to_remove:
            self.remove(store_key)
        for store_key, (args, kwargs) in self._to_add:
            self.add(store_key, *args, **kwargs)
        self._to_remove = []
        self._to_add = []

    def __init__(self, interval):
        """
        Set up the ticker

        Args:
            interval (int): The stepping interval.

        """
        self.interval = interval
        self.subscriptions = {}
        self._is_ticking = False
        self._to_remove = []
        self._to_add = []
        # set up a twisted asynchronous repeat call
        self.task = ExtendedLoopingCall(self._callback)

    def validate(self, start_delay=None):
        """
        Start/stop the task depending on how many subscribers we have
        using it.

        Args:
            start_delay (int, optional): Time to way before starting.

        """
        subs = self.subscriptions
        if self.task.running:
            if not subs:
                self.task.stop()
        elif subs:
            self.task.start(self.interval, now=False, start_delay=start_delay)

    def add(self, store_key, *args, **kwargs):
        """
        Sign up a subscriber to this ticker.
        Args:
            store_key (str): Unique storage hash for this ticker subscription.
            args (any, optional): Arguments to call the hook method with.

        Keyword Args:
            _start_delay (int): If set, this will be
                used to delay the start of the trigger instead of
                `interval`.

        """
        if self._is_ticking:
            # protects the subscription dict from
            # updating while it is looping
            self._to_add.append((store_key, (args, kwargs)))
        else:
            start_delay = kwargs.pop("_start_delay", None)
            self.subscriptions[store_key] = (args, kwargs)
            self.validate(start_delay=start_delay)

    def remove(self, store_key):
        """
        Unsubscribe object from this ticker

        Args:
            store_key (str): Unique store key.

        """
        if self._is_ticking:
            # this protects the subscription dict from
            # updating while it is looping
            self._to_remove.append(store_key)
        else:
            self.subscriptions.pop(store_key, False)
            self.validate()

    def stop(self):
        """
        Kill the Task, regardless of subscriptions.

        """
        self.subscriptions = {}
        self.validate()


class TickerPool(object):
    """
    This maintains a pool of
    `evennia.scripts.scripts.ExtendedLoopingCall` tasks for calling
    subscribed objects at given times.

    """

    ticker_class = Ticker

    def __init__(self):
        """
        Initialize the pool.

        """
        self.tickers = {}

    def add(self, store_key, *args, **kwargs):
        """
        Add new ticker subscriber.

        Args:
            store_key (str): Unique storage hash.
            args (any, optional): Arguments to send to the hook method.

        """
        _, _, _, interval, _, _ = store_key
        if not interval:
            log_err(_ERROR_ADD_TICKER.format(store_key=store_key))
            return

        if interval not in self.tickers:
            self.tickers[interval] = self.ticker_class(interval)
        self.tickers[interval].add(store_key, *args, **kwargs)

    def remove(self, store_key):
        """
        Remove subscription from pool.

        Args:
            store_key (str): Unique storage hash to remove

        """
        _, _, _, interval, _, _ = store_key
        if interval in self.tickers:
            self.tickers[interval].remove(store_key)
            if not self.tickers[interval]:
                del self.tickers[interval]

    def stop(self, interval=None):
        """
        Stop all scripts in pool. This is done at server reload since
        restoring the pool will automatically re-populate the pool.

        Args:
            interval (int, optional): Only stop tickers with this interval.

        """
        if interval and interval in self.tickers:
            self.tickers[interval].stop()
        else:
            for ticker in self.tickers.values():
                ticker.stop()


class TickerHandler(object):
    """
    The Tickerhandler maintains a pool of tasks for subscribing
    objects to various tick rates.  The pool maintains creation
    instructions and and re-applies them at a server restart.

    """

    ticker_pool_class = TickerPool

    def __init__(self, save_name="ticker_storage"):
        """
        Initialize handler

        save_name (str, optional): The name of the ServerConfig
            instance to store the handler state persistently.

        """
        self.ticker_storage = {}
        self.save_name = save_name
        self.ticker_pool = self.ticker_pool_class()

    def _get_callback(self, callback):
        """
        Analyze callback and determine its consituents

        Args:
            callback (function or method): This is either a stand-alone
                function or class method on a typeclassed entitye (that is,
                an entity that can be saved to the database).
        Returns:
            ret (tuple): This is a tuple of the form `(obj, path, callfunc)`,
                where `obj` is the database object the callback is defined on
                if it's a method (otherwise `None`) and vice-versa, `path` is
                the python-path to the stand-alone function (`None` if a method).
                The `callfunc` is either the name of the method to call or the
                callable function object itself.
        Raises:
            TypeError: If the callback is of an unsupported type.

        """
        outobj, outpath, outcallfunc = None, None, None
        if callable(callback):
            if inspect.ismethod(callback):
                outobj = callback.__self__
                outcallfunc = callback.__func__.__name__
            elif inspect.isfunction(callback):
                outpath = "%s.%s" % (callback.__module__, callback.__name__)
                outcallfunc = callback
            else:
                raise TypeError(f"{callback} is not a method or function.")
        else:
            raise TypeError(f"{callback} is not a callable function or method.")

        if outobj and not inherits_from(outobj, "evennia.typeclasses.models.TypedObject"):
            raise TypeError(
                f"{callback} is a method on a normal object - it must "
                "be either a method on a typeclass, or a stand-alone function."
            )

        return outobj, outpath, outcallfunc

    def _store_key(self, obj, path, interval, callfunc, idstring="", persistent=True):
        """
        Tries to create a store_key for the object.

        Args:
            obj (Object, tuple or None): Subscribing object if any. If a tuple, this is
                a packed_obj tuple from dbserialize.
            path (str or None): Python-path to callable, if any.
            interval (int): Ticker interval. Floats will be converted to
                nearest lower integer value.
            callfunc (callable or str): This is either the callable function or
                the name of the method to call. Note that the callable is never
                stored in the key; that is uniquely identified with the python-path.
            idstring (str, optional): Additional separator between
                different subscription types.
            persistent (bool, optional): If this ticker should survive a system
                shutdown or not.

        Returns:
            store_key (tuple): A tuple `(packed_obj, methodname, outpath, interval,
                idstring, persistent)` that uniquely identifies the
                ticker. Here, `packed_obj` is the unique string representation of the
                object or `None`. The `methodname` is the string name of the method on
                `packed_obj` to call, or `None` if `packed_obj` is unset. `path` is
                the Python-path to a non-method callable, or `None`. Finally, `interval`
                `idstring` and `persistent` are integers, strings and bools respectively.

        """
        if interval < 1:
            raise RuntimeError(_ERROR_ADD_TICKER_SUB_SECOND)

        interval = int(interval)
        persistent = bool(persistent)
        packed_obj = pack_dbobj(obj)
        methodname = callfunc if callfunc and isinstance(callfunc, str) else None
        outpath = path if path and isinstance(path, str) else None
        return (packed_obj, methodname, outpath, interval, idstring, persistent)

    def save(self):
        """
        Save ticker_storage as a serialized string into a temporary
        ServerConf field. Whereas saving is done on the fly, if called
        by server when it shuts down, the current timer of each ticker
        will be saved so it can start over from that point.

        """
        if self.ticker_storage:
            # get the current times so the tickers can be restarted with a delay later
            start_delays = dict(
                (interval, ticker.task.next_call_time())
                for interval, ticker in self.ticker_pool.tickers.items()
            )

            # remove any subscriptions that lost its object in the interim
            to_save = {
                store_key: (args, kwargs)
                for store_key, (args, kwargs) in self.ticker_storage.items()
                if (
                    (
                        store_key[1]
                        and ("_obj" in kwargs and kwargs["_obj"].pk)
                        and hasattr(kwargs["_obj"], store_key[1])
                    )
                    or store_key[2]  # a valid method with existing obj
                )
            }  # a path given

            # update the timers for the tickers
            for store_key, (args, kwargs) in to_save.items():
                interval = store_key[1]
                # this is a mutable, so it's updated in-place in ticker_storage
                kwargs["_start_delay"] = start_delays.get(interval, None)
            ServerConfig.objects.conf(key=self.save_name, value=dbserialize(to_save))
        else:
            # make sure we have nothing lingering in the database
            ServerConfig.objects.conf(key=self.save_name, delete=True)

    def restore(self, server_reload=True):
        """
        Restore ticker_storage from database and re-initialize the
        handler from storage. This is triggered by the server at
        restart.

        Args:
            server_reload (bool, optional): If this is False, it means
                the server went through a cold reboot and all
                non-persistent tickers must be killed.

        """
        # load stored command instructions and use them to re-initialize handler
        restored_tickers = ServerConfig.objects.conf(key=self.save_name)
        if restored_tickers:
            # the dbunserialize will convert all serialized dbobjs to real objects

            restored_tickers = dbunserialize(restored_tickers)
            self.ticker_storage = {}
            for store_key, (args, kwargs) in restored_tickers.items():
                try:
                    # at this point obj is the actual object (or None) due to how
                    # the dbunserialize works
                    obj, callfunc, path, interval, idstring, persistent = store_key
                    if not persistent and not server_reload:
                        # this ticker will not be restarted
                        continue
                    if isinstance(callfunc, str) and not obj:
                        # methods must have an existing object
                        continue
                    # we must rebuild the store_key here since obj must not be
                    # stored as the object itself for the store_key to be hashable.
                    store_key = self._store_key(obj, path, interval, callfunc, idstring, persistent)

                    if obj and callfunc:
                        kwargs["_callback"] = callfunc
                        kwargs["_obj"] = obj
                    elif path:
                        modname, varname = path.rsplit(".", 1)
                        callback = variable_from_module(modname, varname)
                        kwargs["_callback"] = callback
                        kwargs["_obj"] = None
                    else:
                        # Neither object nor path - discard this ticker
                        log_err("Tickerhandler: Removing malformed ticker: %s" % str(store_key))
                        continue
                except Exception:
                    # this suggests a malformed save or missing objects
                    log_trace("Tickerhandler: Removing malformed ticker: %s" % str(store_key))
                    continue
                # if we get here we should create a new ticker
                self.ticker_storage[store_key] = (args, kwargs)
                self.ticker_pool.add(store_key, *args, **kwargs)

    def add(self, interval=60, callback=None, idstring="", persistent=True, *args, **kwargs):
        """
        Add subscription to tickerhandler

        Args:

            *args: Will be passed into the callback every time it's called. This must be
                data possible to pickle.

        Keyword Args:
            interval (int): Interval in seconds between calling
                `callable(*args, **kwargs)`
            callable (callable function or method): This
                should either be a stand-alone function or a method on a
                typeclassed entity (that is, one that can be saved to the
                database).
            idstring (str): Identifier for separating
                this ticker-subscription from others with the same
                interval. Allows for managing multiple calls with
                the same time interval and callback.
            persistent (bool): A ticker will always survive
                a server reload. If this is unset, the ticker will be
                deleted by a server shutdown.
            **kwargs Will be passed into the callback every time it is called.
                This must be data possible to pickle.

        Returns:
            store_key (tuple): The immutable store-key for this ticker. This can
                be stored and passed into `.remove(store_key=store_key)` later to
                easily stop this ticker later.

        Notes:
            The callback will be identified by type and stored either as
            as combination of serialized database object + methodname or
            as a python-path to the module + funcname. These strings will
            be combined iwth `interval` and `idstring` to define a
            unique storage key for saving. These must thus all be supplied
            when wanting to modify/remove the ticker later.

        """
        obj, path, callfunc = self._get_callback(callback)
        store_key = self._store_key(obj, path, interval, callfunc, idstring, persistent)
        kwargs["_obj"] = obj
        kwargs["_callback"] = callfunc  # either method-name or callable
        self.ticker_storage[store_key] = (args, kwargs)
        self.ticker_pool.add(store_key, *args, **kwargs)
        self.save()
        return store_key

    def remove(self, interval=60, callback=None, idstring="", persistent=True, store_key=None):
        """
        Remove ticker subscription from handler.

        Keyword Args:
            interval (int): Interval of ticker to remove.
            callback (callable function or method): Either a function or
                the method of a typeclassed object.
            idstring (str): Identifier id of ticker to remove.
            persistent (bool): Whether this ticker is persistent or not.
            store_key (str): If given, all other kwargs are ignored and only
                this is used to identify the ticker.

        Raises:
            KeyError: If no matching ticker was found to remove.

        Notes:
            The store-key is normally built from the interval/callback/idstring/persistent values;
            but if the `store_key` is explicitly given, this is used instead.

        """
        if isinstance(callback, int):
            raise RuntimeError(
                "TICKER_HANDLER.remove has changed: "
                "the interval is now the first argument, callback the second."
            )
        if not store_key:
            obj, path, callfunc = self._get_callback(callback)
            store_key = self._store_key(obj, path, interval, callfunc, idstring, persistent)
        to_remove = self.ticker_storage.pop(store_key, None)
        if to_remove:
            self.ticker_pool.remove(store_key)
            self.save()
        else:
            raise KeyError(f"No Ticker was found matching the store-key {store_key}.")

    def clear(self, interval=None):
        """
        Stop/remove tickers from handler.

        Args:
            interval (int, optional): Only stop tickers with this interval.

        Notes:
            This is the only supported way to kill tickers related to
            non-db objects.

        """
        self.ticker_pool.stop(interval)
        if interval:
            self.ticker_storage = dict(
                (store_key, store_value)
                for store_key, store_value in self.ticker_storage.items()
                if store_key[3] != interval
            )
        else:
            self.ticker_storage = {}
        self.save()

    def all(self, interval=None):
        """
        Get all ticker subscriptions.

        Args:
            interval (int, optional): Limit match to tickers with this interval.

        Returns:
            list or dict: If `interval` was given, this is a list of tickers using that interval.
            If `interval` was *not* given, this is a dict
            `{interval1: [ticker1, ticker2, ...],  ...}`

        """
        if interval is None:
            # return dict of all, ordered by interval
            return dict(
                (interval, ticker.subscriptions)
                for interval, ticker in self.ticker_pool.tickers.items()
            )
        else:
            # get individual interval
            ticker = self.ticker_pool.tickers.get(interval, None)
            if ticker:
                return {interval: ticker.subscriptions}
            return None

    def all_display(self):
        """
        Get all tickers on an easily displayable form.

        Returns:
            tickers (dict): A list of all storekeys

        """
        store_keys = []
        for ticker in self.ticker_pool.tickers.values():
            for (
                (objtup, callfunc, path, interval, idstring, persistent),
                (args, kwargs),
            ) in ticker.subscriptions.items():
                store_keys.append(
                    (kwargs.get("_obj", None), callfunc, path, interval, idstring, persistent)
                )
        return store_keys


# main tickerhandler
TICKER_HANDLER = TickerHandler()
