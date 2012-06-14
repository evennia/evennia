"""
RSS parser for Evennia

This connects an RSS feed to an in-game Evennia channel, sending messages
to the channel whenever the feed updates.

"""

import re
from twisted.internet import task
from django.conf import settings
from src.comms.models import ExternalChannelConnection, Channel
from src.utils import logger, utils
from src.scripts.models import ScriptDB

RSS_ENABLED = settings.RSS_ENABLED
RSS_UPDATE_INTERVAL = settings.RSS_UPDATE_INTERVAL
INFOCHANNEL = Channel.objects.channel_search(settings.CHANNEL_MUDINFO[0])
RETAG = re.compile(r'<[^>]*?>')

# holds rss readers they can be shut down at will.
RSS_READERS = {}

def msg_info(message):
    """
    Send info to default info channel
    """
    message = '[%s][RSS]: %s' % (INFOCHANNEL[0].key, message)
    try:
        INFOCHANNEL[0].msg(message)
    except AttributeError:
        logger.log_infomsg("MUDinfo (rss): %s" % message)

if RSS_ENABLED:
    try:
        import feedparser
    except ImportError:
        raise ImportError("RSS requires python-feedparser to be installed. Install or set RSS_ENABLED=False.")

class RSSReader(object):
    """
    Reader script used to connect to each individual RSS feed
    """
    def __init__(self, key, url, interval):
        """
        The reader needs an rss url and It also needs an interval
        for how often it is to check for new updates (defaults
        to 10 minutes)
        """
        self.key = key
        self.url = url
        self.interval = interval
        self.entries = {} # stored feeds
        self.task = None
        # first we do is to load the feed so we don't resend
        # old entries whenever the reader starts.
        self.update_feed()
        # start runner
        self.start()

    def update_feed(self):
        "Read the url for new updated data and determine what's new."
        feed = feedparser.parse(self.url)
        new = []
        for entry in (e for e in feed['entries'] if e['id'] not in self.entries):
            txt = "[RSS] %s: %s" % (RETAG.sub("", entry['title']), entry['link'].replace('\n','').encode('utf-8'))
            self.entries[entry['id']] = txt
            new.append(txt)
        return new

    def update(self):
        """
        Called every self.interval seconds - tries to get new feed entries,
        and if so, uses the appropriate ExternalChannelConnection to send the
        data to subscribing channels.
        """
        new = self.update_feed()
        if not new:
            return
        conns = ExternalChannelConnection.objects.filter(db_external_key=self.key)
        for conn in (conn for conn in conns if conn.channel):
            for txt in new:
                conn.to_channel("%s:%s" % (conn.channel.key, txt))

    def start(self):
        """
        Starting the update task and store a reference in the
        global variable so it can be found and shut down later.
        """
        global RSS_READERS
        self.task = task.LoopingCall(self.update)
        self.task.start(self.interval, now=False)
        RSS_READERS[self.key] = self

def build_connection_key(channel, url):
    "This is used to id the connection"
    if hasattr(channel, 'key'):
        channel = channel.key
    return "rss_%s>%s" % (url, channel)

def create_connection(channel, url, interval):
    """
    This will create a new RSS->channel connection
    """
    if not type(channel) == Channel:
        new_channel = Channel.objects.filter(db_key=channel)
        if not new_channel:
            logger.log_errmsg("Cannot attach RSS->Evennia: Evennia Channel '%s' not found." % channel)
            return False
        channel = new_channel[0]
    key = build_connection_key(channel, url)
    old_conns = ExternalChannelConnection.objects.filter(db_external_key=key)
    if old_conns:
        return False
    config = "%s|%i" % (url, interval)
    # There is no sendback from evennia to the rss, so we need not define any sendback code.
    conn = ExternalChannelConnection(db_channel=channel, db_external_key=key, db_external_config=config)
    conn.save()

    connect_to_rss(conn)
    return True

def delete_connection(channel, url):
    """
    Delete rss connection between channel and url
    """
    key = build_connection_key(channel, url)
    try:
        conn = ExternalChannelConnection.objects.get(db_external_key=key)
    except Exception:
        return False
    conn.delete()
    reader = RSS_READERS.get(key, None)
    if reader and reader.task:
        reader.task.stop()
    return True

def connect_to_rss(connection):
    """
    Create the parser instance and connect to RSS feed and channel
    """
    global RSS_READERS
    key = utils.to_str(connection.external_key)
    url, interval = [utils.to_str(conf) for conf in connection.external_config.split('|')]
    # Create reader (this starts the running task and stores a reference in RSS_TASKS)
    RSSReader(key, url, int(interval))

def connect_all():
    """
    Activate all rss feed parsers
    """
    if not RSS_ENABLED:
        return
    for connection in ExternalChannelConnection.objects.filter(db_external_key__startswith="rss_"):
        print "connecting RSS: %s" % connection
        connect_to_rss(connection)
