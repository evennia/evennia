"""
Tickerhandler

This implements an efficient Ticker which uses a subscription
model to 'tick' subscribed objects at regular intervals. All
that is required is that the subscribing objects has a
method "at_tick".
"""
from twisted.internet.task import LoopingCall
from src.server.models import ServerConfig
from src.utils.logger import log_trace
from src.utils.dbserialize import dbserialize, dbunserialize, pack_dbobj, unpack_dbobj

_GA = object.__getattribute__
_SA = object.__setattr__


class Ticker(object):
    """
    Represents a repeatedly running task that calls
    hooks repeatedly.
    """
    def __init__(self, interval):
        """
        Set up the ticker
        """
        def callback(self):
            "This should be fed _Task as argument"
            for key, (obj, args, kwargs) in self.subscriptions.items():
                hook_key = kwargs.get("hook_key", "at_tick")
                try:
                    _GA(obj, hook_key)(*args, **kwargs)
                except Exception:
                    log_trace()

        self.interval = interval
        self.subscriptions = {}
        self.task = LoopingCall(callback, self)


    def validate(self):
        """
        Start/stop the task depending on how many
        subscribers we have using it.
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
            self.task.start(self.interval, now=False)

    def add(self, store_key, obj, *args, **kwargs):
        """
        Sign up a subscriber to this ticker
        """
        self.subscriptions[store_key] = (obj, args, kwargs)
        self.validate()

    def remove(self, store_key):
        """
        Unsubscribe object from this ticker
        """
        self.subscriptions.pop(store_key, False)
        self.validate()

    def stop(self):
        """
        Kill the Task, regardless of subscriptions
        """
        self.subscriptions = {}
        self.validate()

class TickerPool(object):
    """
    This maintains a pool of Twisted LoopingCall tasks
    for calling subscribed objects at given times.
    """
    def __init__(self):
        "Initialize the pool"
        self.tickers = {}

    def add(self, store_key, obj, interval, *args, **kwargs):
        """
        Add new ticker subscriber
        """
        if interval not in self.tickers:
            self.tickers[interval] = Ticker(interval)
        self.tickers[interval].add(store_key, obj, *args, **kwargs)

    def remove(self, store_key, interval):
        """
        Remove subscription from pool
        """
        if interval in self.tickers:
            self.tickers[interval].remove(store_key)

    def stop(self, interval=None):
        """
        Stop all scripts in pool. This is done at server reload since
        restoring the pool will automatically re-populate the pool.
        If interval is given, only stop tickers with that interval.
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
    def __init__(self, save_name="ticker_storage"):
        """
        Initialize handler
        """
        self.ticker_storage = {}
        self.save_name = save_name
        self.ticker_pool = TickerPool()

    def _store_key(self, obj, interval):
        """
        Tries to create a store_key for the object.
        Returns a tuple (isdb, store_key) where isdb
        is a boolean True if obj was a database object,
        False otherwise.
        """
        try:
            obj = obj.typeclass
        except AttributeError:
            pass
        dbobj = None
        try:
            dbobj = obj.dbobj
        except AttributeError:
            pass
        isdb = True
        if dbobj:
            # create a store_key using the database representation
            objkey = pack_dbobj(dbobj)
        else:
            # non-db object, look for a property "key" on it, otherwise
            # use its memory location.
            try:
                objkey = _GA(obj, "key")
            except AttributeError:
                objkey = id(obj)
            isdb = False
        # return sidb and store_key
        return isdb, (objkey, interval)

    def save(self):
        """
        Save ticker_storage as a serialized string into a temporary
        ServerConf field. This is called by server when it shuts down
        """
        #print "save:", self.ticker_storage
        if self.ticker_storage:
            ServerConfig.objects.conf(key=self.save_name,
                                    value=dbserialize(self.ticker_storage))
        else:
            ServerConfig.objects.conf(key=self.save_name, delete=True)

    def restore(self):
        """
        Restore ticker_storage from database and re-initialize the handler from storage. This is triggered by the server at restart.
        """
        # load stored command instructions and use them to re-initialize handler
        ticker_storage = ServerConfig.objects.conf(key=self.save_name)
        if ticker_storage:
            self.ticker_storage = dbunserialize(ticker_storage)
            print "restore:", self.ticker_storage
            for (obj, interval), (args, kwargs) in self.ticker_storage.items():
                obj = unpack_dbobj(obj)
                _, store_key = self._store_key(obj, interval)
                self.ticker_pool.add(store_key, obj, interval, *args, **kwargs)

    def add(self, obj, interval, *args, **kwargs):
        """
        Add object to tickerhandler. The object must have an at_tick
        method. This will be called every interval seconds until the
        object is unsubscribed from the ticker.
        """
        isdb, store_key = self._store_key(obj, interval)
        if isdb:
            self.ticker_storage[store_key] = (args, kwargs)
            self.save()
        self.ticker_pool.add(store_key, obj, interval, *args, **kwargs)

    def remove(self, obj, interval):
        """
        Remove object from ticker with given interval.
        """
        isdb, store_key = self._store_key(obj, interval)
        if isdb:
            self.ticker_storage.pop(store_key, None)
            self.save()
        self.ticker_pool.remove(store_key, interval)

    def clear(self, interval=None):
        """
        Stop/remove all tickers from handler, or the ones
        with a given interval. This is the only supported
        way to kill tickers for non-db objects. If interval
        is given, only stop tickers with this interval.
        """
        self.ticker_pool.stop(interval)
        if interval:
            self.ticker_storage = dict((store_key, store_key) for store_key in self.ticker_storage if store_key[1] != interval)
        else:
            self.ticker_storage = {}
        self.save()

    def all(self, interval=None):
        """
        Get the subsciptions for a given interval. If interval
        is not given, return a dictionary with lists for every
        interval in the tickerhandler.
        """
        if interval is None:
            # return dict of all, ordered by interval
            return dict((interval, ticker.subscriptions.values())
                         for interval, ticker in self.ticker_pool.tickers.items())
        else:
            # get individual interval
            ticker = self.ticker_pool.tickers.get(interval, None)
            if ticker:
                return ticker.subscriptions.values()

# main tickerhandler
TICKER_HANDLER = TickerHandler()
