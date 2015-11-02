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

    # tick myobj every 15 seconds
    TICKER_HANDLER.add(myobj, 15)
```

The handler will by default try to call a hook `at_tick()`
on the subscribing object. The hook's name can be changed
if the `hook_key` keyword is given to the `add()` method (only
one such alternate name per interval though). The
handler will transparently set up and add new timers behind
the scenes to tick at given intervals, using a TickerPool.

To remove:

```python
    TICKER_HANDLER.remove(myobj, 15)
```

The interval must be given since a single object can be subscribed
to many different tickers at the same time.


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
from builtins import object
from future.utils import listvalues

from twisted.internet.defer import inlineCallbacks
from django.core.exceptions import ObjectDoesNotExist
from evennia.scripts.scripts import ExtendedLoopingCall
from evennia.server.models import ServerConfig
from evennia.utils.logger import log_trace, log_err
from evennia.utils.dbserialize import dbserialize, dbunserialize, pack_dbobj, unpack_dbobj

_GA = object.__getattribute__
_SA = object.__setattr__


_ERROR_ADD_INTERVAL = \
"""TickerHandler: Tried to add a ticker with invalid interval:
obj={obj}, interval={interval}, args={args}, kwargs={kwargs}
store_key={store_key}
Ticker was not added."""

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
        for store_key, (obj, args, kwargs) in self.subscriptions.items():
            hook_key = yield kwargs.pop("_hook_key", "at_tick")
            if not obj or not obj.pk:
                # object was deleted between calls
                self.remove(store_key)
                continue
            try:
                yield _GA(obj, hook_key)(*args, **kwargs)
            except ObjectDoesNotExist:
                log_trace()
                self.remove(store_key)
            except Exception:
                log_trace()
            finally:
                # make sure to re-store
                kwargs["_hook_key"] = hook_key

    def __init__(self, interval):
        """
        Set up the ticker

        Args:
            interval (int): The stepping interval.

        """
        self.interval = interval
        self.subscriptions = {}
        # set up a twisted asynchronous repeat call
        self.task = ExtendedLoopingCall(self._callback)

    def validate(self, start_delay=None):
        """
        Start/stop the task depending on how many subscribers we have
        using it.

        Args:
            start_delay (int): Time to way before starting.

        """
        subs = self.subscriptions
        if None in subs.values():
            # clean out objects that may have been deleted
            subs = dict((store_key, obj) for store_key, obj in subs if obj)
            self.subscriptions = subs
        if self.task.running:
            if not subs:
                self.task.stop()
        elif subs:
            self.task.start(self.interval, now=False, start_delay=start_delay)

    def add(self, store_key, obj, *args, **kwargs):
        """
        Sign up a subscriber to this ticker.
        Args:
            store_key (str): Unique storage hash for this ticker subscription.
            obj (Object): Object subscribing to this ticker.
            args (any, optional): Arguments to call the hook method with.

        Kwargs:
            _start_delay (int): If set, this will be
                used to delay the start of the trigger instead of
                `interval`.
            _hooK_key (str): This carries the name of the hook method
                to call. It is passed on as-is from this method.

        """
        start_delay = kwargs.pop("_start_delay", None)
        self.subscriptions[store_key] = (obj, args, kwargs)
        self.validate(start_delay=start_delay)

    def remove(self, store_key):
        """
        Unsubscribe object from this ticker

        Args:
            store_key (str): Unique store key.

        """
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

    def add(self, store_key, obj, interval, *args, **kwargs):
        """
        Add new ticker subscriber.

        Args:
            store_key (str): Unique storage hash.
            obj (Object): Object subscribing.
            interval (int): How often to call the ticker.
            args (any, optional): Arguments to send to the hook method.

        Kwargs:
            _start_delay (int): If set, this will be
                used to delay the start of the trigger instead of
                `interval`. It is passed on as-is from this method.
            _hooK_key (str): This carries the name of the hook method
                to call. It is passed on as-is from this method.

        """
        if not interval:
            log_err(_ERROR_ADD_INTERVAL.format(store_key=store_key, obj=obj,
                                       interval=interval, args=args, kwargs=kwargs))
            return

        if interval not in self.tickers:
            self.tickers[interval] = self.ticker_class(interval)
        self.tickers[interval].add(store_key, obj, *args, **kwargs)

    def remove(self, store_key, interval):
        """
        Remove subscription from pool.

        Args:
            store_key (str): Unique storage hash.
            interval (int): Ticker interval.

        Notes:
            A given subscription is uniquely identified both
            via its `store_key` and its `interval`.

        """
        if interval in self.tickers:
            self.tickers[interval].remove(store_key)

    def stop(self, interval=None):
        """
        Stop all scripts in pool. This is done at server reload since
        restoring the pool will automatically re-populate the pool.

        Args:
            interval (int, optional): Only stop tickers with this
                interval.

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

    def _store_key(self, obj, interval, idstring=""):
        """
        Tries to create a store_key for the object.  Returns a tuple
        (isdb, store_key) where isdb is a boolean True if obj was a
        database object, False otherwise.

        Args:
            obj (Object): Subscribing object.
            interval (int): Ticker interval
            idstring (str, optional): Additional separator between
                different subscription types.

        """
        if hasattr(obj, "db_key"):
            # create a store_key using the database representation
            objkey = pack_dbobj(obj)
            isdb = True
        else:
            # non-db object, look for a property "key" on it, otherwise
            # use its memory location.
            try:
                objkey = _GA(obj, "key")
            except AttributeError:
                objkey = id(obj)
            isdb = False
        # return sidb and store_key
        return isdb, (objkey, interval, idstring)

    def save(self):
        """
        Save ticker_storage as a serialized string into a temporary
        ServerConf field. Whereas saving is done on the fly, if called
        by server when it shuts down, the current timer of each ticker
        will be saved so it can start over from that point.

        """
        if self.ticker_storage:
            start_delays = dict((interval, ticker.task.next_call_time())
                                 for interval, ticker in self.ticker_pool.tickers.items())
            # update the timers for the tickers
            #for (obj, interval, idstring), (args, kwargs) in self.ticker_storage.items():
            for store_key, (args, kwargs) in self.ticker_storage.items():
                interval = store_key[1]
                # this is a mutable, so it's updated in-place in ticker_storage
                kwargs["_start_delay"] = start_delays.get(interval, None)
            ServerConfig.objects.conf(key=self.save_name,
                                    value=dbserialize(self.ticker_storage))
        else:
            # make sure we have nothing lingering in the database
            ServerConfig.objects.conf(key=self.save_name, delete=True)

    def restore(self):
        """
        Restore ticker_storage from database and re-initialize the
        handler from storage. This is triggered by the server at
        restart.

        """
        # load stored command instructions and use them to re-initialize handler
        ticker_storage = ServerConfig.objects.conf(key=self.save_name)
        if ticker_storage:
            self.ticker_storage = dbunserialize(ticker_storage)
            for store_key, (args, kwargs) in self.ticker_storage.items():
                obj, interval, idstring = store_key
                obj = unpack_dbobj(obj)
                _, store_key = self._store_key(obj, interval, idstring)
                self.ticker_pool.add(store_key, obj, interval, *args, **kwargs)

    def add(self, obj, interval, idstring="", hook_key="at_tick", *args, **kwargs):
        """
        Add object to tickerhandler

        Args:
            obj (Object): The object to subscribe to the ticker.
            interval (int): Interval in seconds between calling
                `hook_key` below.
            idstring (str, optional): Identifier for separating
                this ticker-subscription from others with the same
                interval. Allows for managing multiple calls with
                the same time interval
            hook_key (str, optional): The name of the hook method
                on `obj` to call every `interval` seconds. Defaults to
                `at_tick(*args, **kwargs`. All hook methods must
                always accept *args, **kwargs.
            args, kwargs (optional): These will be passed into the
                method given by `hook_key` every time it is called.

        Notes:
            The combination of `obj`, `interval` and `idstring`
            together uniquely defines the ticker subscription. They
            must all be supplied in order to unsubscribe from it
            later.

        """
        isdb, store_key = self._store_key(obj, interval, idstring)
        if isdb:
            self.ticker_storage[store_key] = (args, kwargs)
            self.save()
        kwargs["_hook_key"] = hook_key
        self.ticker_pool.add(store_key, obj, interval, *args, **kwargs)

    def remove(self, obj, interval=None, idstring=""):
        """
        Remove object from ticker or only remove it from tickers with
        a given interval.

        Args:
            obj (Object): The object subscribing to the ticker.
            interval (int, optional): Interval of ticker to remove. If
                `None`, all tickers on this object matching `idstring`
                will be removed, regardless of their `interval` setting.
            idstring (str, optional): Identifier id of ticker to remove.

        """
        if interval:
            isdb, store_key = self._store_key(obj, interval, idstring)
            if isdb:
                self.ticker_storage.pop(store_key, None)
                self.save()
            self.ticker_pool.remove(store_key, interval)
        else:
            # remove all objects with any intervals
            intervals = list(self.ticker_pool.tickers)
            should_save = False
            for interval in intervals:
                isdb, store_key = self._store_key(obj, interval, idstring)
                if isdb:
                    self.ticker_storage.pop(store_key, None)
                    should_save = True
                self.ticker_pool.remove(store_key, interval)
            if should_save:
                self.save()



    def clear(self, interval=None):
        """
        Stop/remove all tickers from handler.

        Args:
            interval (int): Only stop tickers with this interval.

        Notes:
            This is the only supported way to kill tickers related to
            non-db objects.

        """
        self.ticker_pool.stop(interval)
        if interval:
            self.ticker_storage = dict((store_key, store_key)
                                        for store_key in self.ticker_storage
                                        if store_key[1] != interval)
        else:
            self.ticker_storage = {}
        self.save()

    def all(self, interval=None):
        """
        Get all subscriptions.

        Args:
            interval (int): Limit match to tickers with this interval.

        Returns:
            tickers (list): If `interval` was given, this is a list of
                tickers using that interval.
            tickerpool_layout (dict): If `interval` was *not* given,
                this is a dict {interval1: [ticker1, ticker2, ...],  ...}

        """
        if interval is None:
            # return dict of all, ordered by interval
            return dict((interval, listvalues(ticker.subscriptions))
                         for interval, ticker in self.ticker_pool.tickers.items())
        else:
            # get individual interval
            ticker = self.ticker_pool.tickers.get(interval, None)
            if ticker:
                return listvalues(ticker.subscriptions)


# main tickerhandler
TICKER_HANDLER = TickerHandler()
