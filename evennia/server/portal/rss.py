"""
RSS parser for Evennia

This connects an RSS feed to an in-game Evennia channel, sending messages
to the channel whenever the feed updates.

"""

from twisted.internet import task, threads
from django.conf import settings
from evennia.server.session import Session
from evennia.utils import logger

RSS_ENABLED = settings.RSS_ENABLED
#RETAG = re.compile(r'<[^>]*?>')

if RSS_ENABLED:
    try:
        import feedparser
    except ImportError:
        raise ImportError("RSS requires python-feedparser to be installed. Install or set RSS_ENABLED=False.")

class RSSReader(Session):
    """
    A simple RSS reader using universal feedparser
    """
    def __init__(self, factory, url, rate):
        self.url = url
        self.rate = rate
        self.factory = factory
        self.old_entries = {}

    def get_new(self):
        """Returns list of new items."""
        feed = feedparser.parse(self.url)
        new_entries = []
        for entry in feed['entries']:
            idval = entry['id'] + entry.get("updated", "")
            if idval not in self.old_entries:
                self.old_entries[idval] = entry
                new_entries.append(entry)
        return new_entries

    def disconnect(self, reason=None):
        "Disconnect from feed"
        if self.factory.task and self.factory.task.running:
            self.factory.task.stop()
        self.sessionhandler.disconnect(self)

    def _callback(self, new_entries, init):
        "Called when RSS returns (threaded)"
        if not init:
            # for initialization we just ignore old entries
            for entry in reversed(new_entries):
                self.data_in("bot_data_in " + entry)

    def data_in(self, text=None, **kwargs):
        "Data RSS -> Server"
        self.sessionhandler.data_in(self, text=text, **kwargs)

    def _errback(self, fail):
        "Report error"
        logger.log_errmsg("RSS feed error: %s" % fail.value)

    def update(self, init=False):
        "Request feed"
        return threads.deferToThread(self.get_new).addCallback(self._callback, init).addErrback(self._errback)

class RSSBotFactory(object):
    """
    Initializes new bots
    """

    def __init__(self, sessionhandler, uid=None, url=None, rate=None):
        "Initialize"
        self.sessionhandler = sessionhandler
        self.url = url
        self.rate = rate
        self.uid = uid
        self.bot = RSSReader(self, url, rate)
        self.task = None

    def start(self):
        """
        Called by portalsessionhandler
        """
        def errback(fail):
            logger.log_errmsg(fail.value)

        # set up session and connect it to sessionhandler
        self.bot.init_session("rssbot", self.url, self.sessionhandler)
        self.bot.uid = self.uid
        self.bot.logged_in = True
        self.sessionhandler.connect(self.bot)

        # start repeater task
        self.bot.update(init=True)
        self.task = task.LoopingCall(self.bot.update)
        if self.rate:
            self.task.start(self.rate, now=False).addErrback(errback)
