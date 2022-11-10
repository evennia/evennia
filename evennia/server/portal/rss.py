"""
RSS parser for Evennia

This connects an RSS feed to an in-game Evennia channel, sending messages
to the channel whenever the feed updates.

"""
from django.conf import settings
from twisted.internet import task, threads

from evennia.server.session import Session
from evennia.utils import logger

RSS_ENABLED = settings.RSS_ENABLED
# RETAG = re.compile(r'<[^>]*?>')

if RSS_ENABLED:
    try:
        import feedparser
    except ImportError:
        raise ImportError(
            "RSS requires python-feedparser to be installed. Install or set RSS_ENABLED=False."
        )


class RSSReader(Session):
    """
    A simple RSS reader using the feedparser module.

    """

    def __init__(self, factory, url, rate):
        """
        Initialize the reader.

        Args:
            factory (RSSFactory): The protocol factory.
            url (str): The RSS url.
            rate (int): The seconds between RSS lookups.

        """
        self.url = url
        self.rate = rate
        self.factory = factory
        self.old_entries = {}

    def get_new(self):
        """
        Returns list of new items.

        """
        feed = feedparser.parse(self.url)
        new_entries = []
        for entry in feed["entries"]:
            idval = entry["id"] + entry.get("updated", "")
            if idval not in self.old_entries:
                self.old_entries[idval] = entry
                new_entries.append(entry)
        return new_entries

    def disconnect(self, reason=None):
        """
        Disconnect from feed.

        Args:
            reason (str, optional): Motivation for the disconnect.

        """
        if self.factory.task and self.factory.task.running:
            self.factory.task.stop()
        self.sessionhandler.disconnect(self)

    def _callback(self, new_entries, init):
        """
        Called when RSS returns.

        Args:
            new_entries (list): List of new RSS entries since last.
            init (bool): If this is a startup operation (at which
                point all entries are considered new).

        """
        if not init:
            # for initialization we just ignore old entries
            for entry in reversed(new_entries):
                self.data_in(entry)

    def data_in(self, text=None, **kwargs):
        """
        Data RSS -> Evennia.

        Keyword Args:
            text (str): Incoming text
            kwargs (any): Options from protocol.

        """
        self.sessionhandler.data_in(self, bot_data_in=text, **kwargs)

    def _errback(self, fail):
        "Report error"
        logger.log_err("RSS feed error: %s" % fail.value)

    def update(self, init=False):
        """
        Request the latest version of feed.

        Args:
            init (bool, optional): If this is an initialization call
                or not (during init, all entries are conidered new).

        Notes:
            This call is done in a separate thread to avoid blocking
            on slow connections.

        """
        return (
            threads.deferToThread(self.get_new)
            .addCallback(self._callback, init)
            .addErrback(self._errback)
        )


class RSSBotFactory(object):
    """
    Initializes new bots.
    """

    def __init__(self, sessionhandler, uid=None, url=None, rate=None):
        """
        Initialize the bot.

        Args:
            sessionhandler (PortalSessionHandler): The main sessionhandler object.
            uid (int): User id for the bot.
            url (str): The RSS URL.
            rate (int): How often for the RSS to request the latest RSS entries.

        """
        self.sessionhandler = sessionhandler
        self.url = url
        self.rate = rate
        self.uid = uid
        self.bot = RSSReader(self, url, rate)
        self.task = None

    def start(self):
        """
        Called by portalsessionhandler. Starts the bot.

        """

        def errback(fail):
            logger.log_err(fail.value)

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
