"""
RSS parser for Evennia

This connects an RSS feed to an in-game Evennia channel, sending messages
to the channel whenever the feed updates.

"""

import re
from twisted.internet import task, threads
from django.conf import settings
from src.comms.models import ExternalChannelConnection, ChannelDB
from src.server.session import Session
from src.utils import logger, utils

RSS_ENABLED = settings.RSS_ENABLED
RSS_UPDATE_INTERVAL = settings.RSS_UPDATE_INTERVAL
INFOCHANNEL = ChannelDB.objects.channel_search(settings.CHANNEL_MUDINFO[0])
RETAG = re.compile(r'<[^>]*?>')

# holds rss readers they can be shut down at will.
RSS_READERS = {}

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
        print "RSS feed error: %s" % fail.value

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
            print fail.value

        # set up session and connect it to sessionhandler
        self.bot.init_session("rssbot", self.url, self.sessionhandler)
        self.bot.uid = self.uid
        self.bot.logged_in = True
        self.sessionhandler.connect(self.bot)
        # start repeater task
        #self.bot.update(init=True)
        self.bot.update(init=True)
        self.task = task.LoopingCall(self.bot.update)
        if self.rate:
            self.task.start(self.rate, now=False).addErrback(errback)

#class RSSReader(object):
#    """
#    Reader script used to connect to each individual RSS feed
#    """
#    def __init__(self, key, url, interval):
#        """
#        The reader needs an rss url and It also needs an interval
#        for how often it is to check for new updates (defaults
#        to 10 minutes)
#        """
#        self.key = key
#        self.url = url
#        self.interval = interval
#        self.entries = {}  # stored feeds
#        self.task = None
#        # first we do is to load the feed so we don't resend
#        # old entries whenever the reader starts.
#        self.update_feed()
#        # start runner
#        self.start()
#
#    def update_feed(self):
#        "Read the url for new updated data and determine what's new."
#        feed = feedparser.parse(self.url)
#        new = []
#        for entry in (e for e in feed['entries'] if e['id'] not in self.entries):
#            txt = "[RSS] %s: %s" % (RETAG.sub("", entry['title']),
#                                    entry['link'].replace('\n','').encode('utf-8'))
#            self.entries[entry['id']] = txt
#            new.append(txt)
#        return new
#
#    def update(self):
#        """
#        Called every self.interval seconds - tries to get new feed entries,
#        and if so, uses the appropriate ExternalChannelConnection to send the
#        data to subscribing channels.
#        """
#        new = self.update_feed()
#        if not new:
#            return
#        conns = ExternalChannelConnection.objects.filter(db_external_key=self.key)
#        for conn in (conn for conn in conns if conn.channel):
#            for txt in new:
#                conn.to_channel("%s:%s" % (conn.channel.key, txt))
#
#    def start(self):
#        """
#        Starting the update task and store a reference in the
#        global variable so it can be found and shut down later.
#        """
#        global RSS_READERS
#        self.task = task.LoopingCall(self.update)
#        self.task.start(self.interval, now=False)
#        RSS_READERS[self.key] = self
#
#
#def build_connection_key(channel, url):
#    "This is used to id the connection"
#    if hasattr(channel, 'key'):
#        channel = channel.key
#    return "rss_%s>%s" % (url, channel)
#
#
#def create_connection(channel, url, interval):
#    """
#    This will create a new RSS->channel connection
#    """
#    if not type(channel) == ChannelDB:
#        new_channel = ChannelDB.objects.filter(db_key=channel)
#        if not new_channel:
#            logger.log_errmsg("Cannot attach RSS->Evennia: Evennia Channel '%s' not found." % channel)
#            return False
#        channel = new_channel[0]
#    key = build_connection_key(channel, url)
#    old_conns = ExternalChannelConnection.objects.filter(db_external_key=key)
#    if old_conns:
#        return False
#    config = "%s|%i" % (url, interval)
#    # There is no sendback from evennia to the rss, so we need not define
#    # any sendback code.
#    conn = ExternalChannelConnection(db_channel=channel,
#                                     db_external_key=key,
#                                     db_external_config=config)
#    conn.save()
#
#    connect_to_rss(conn)
#    return True
#
#
#def delete_connection(channel, url):
#    """
#    Delete rss connection between channel and url
#    """
#    key = build_connection_key(channel, url)
#    try:
#        conn = ExternalChannelConnection.objects.get(db_external_key=key)
#    except Exception:
#        return False
#    conn.delete()
#    reader = RSS_READERS.get(key, None)
#    if reader and reader.task:
#        reader.task.stop()
#    return True
#
#
#def connect_to_rss(connection):
#    """
#    Create the parser instance and connect to RSS feed and channel
#    """
#    global RSS_READERS
#    key = utils.to_str(connection.external_key)
#    url, interval = [utils.to_str(conf) for conf in connection.external_config.split('|')]
#    # Create reader (this starts the running task and stores a reference in RSS_TASKS)
#    RSSReader(key, url, int(interval))
#
#
#def connect_all():
#    """
#    Activate all rss feed parsers
#    """
#    if not RSS_ENABLED:
#        return
#    for connection in ExternalChannelConnection.objects.filter(db_external_key__startswith="rss_"):
#        print "connecting RSS: %s" % connection
#        connect_to_rss(connection)
