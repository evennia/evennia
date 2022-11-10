"""
The client for sending data to the Evennia Game Index

"""
import platform
import urllib.error
import urllib.parse
import urllib.request

import django
from django.conf import settings
from twisted.internet import defer, protocol, reactor
from twisted.internet.defer import inlineCallbacks
from twisted.web.client import Agent, HTTPConnectionPool, _HTTP11ClientFactory
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from zope.interface import implementer

from evennia.accounts.models import AccountDB
from evennia.server.sessionhandler import SESSIONS
from evennia.utils import get_evennia_version, logger

_EGI_HOST = "http://evennia-game-index.appspot.com"
_EGI_REPORT_PATH = "/api/v1/game/check_in"


class EvenniaGameIndexClient(object):
    """
    This client class is used for gathering and sending game details to the
    Evennia Game Index. Since EGI is in the early goings, this isn't
    incredibly configurable as far as to what is being sent.
    """

    def __init__(self, on_bad_request=None):
        """
        :param on_bad_request: Optional callable to trigger when a bad request
            was sent. This is almost always going to be due to bad config.
        """
        self.report_host = _EGI_HOST
        self.report_path = _EGI_REPORT_PATH
        self.report_url = self.report_host + self.report_path
        self.logged_first_connect = False

        self._on_bad_request = on_bad_request
        # Oh, the humanity. Silence the factory start/stop messages.
        self._conn_pool = HTTPConnectionPool(reactor)
        self._conn_pool._factory = QuietHTTP11ClientFactory

    @inlineCallbacks
    def send_game_details(self):
        """
        This is where the magic happens. Send details about the game to the
        Evennia Game Index.
        """
        status_code, response_body = yield self._form_and_send_request()
        if status_code == 200:
            if not self.logged_first_connect:
                logger.log_infomsg("Successfully sent game details to Evennia Game Index.")
                self.logged_first_connect = True
            return
        # At this point, either EGD is having issues or the payload we sent
        # is improperly formed (probably due to mis-configuration).
        logger.log_errmsg(
            "Failed to send game details to Evennia Game Index. HTTP "
            "status code was %s. Message was: %s" % (status_code, response_body)
        )

        if status_code == 400 and self._on_bad_request:
            # Improperly formed request. Defer to the callback as far as what
            # to do. Probably not a great idea to continue attempting to send
            # to EGD, though.
            self._on_bad_request()

    def _form_and_send_request(self):
        """
        Build the request to send to the index.

        """
        agent = Agent(reactor, pool=self._conn_pool)
        headers = {
            b"User-Agent": [b"Evennia Game Index Client"],
            b"Content-Type": [b"application/x-www-form-urlencoded"],
        }
        egi_config = settings.GAME_INDEX_LISTING
        # We are using `or` statements below with dict.get() to avoid sending
        # stringified 'None' values to the server.
        try:
            values = {
                # Game listing stuff
                "game_name": egi_config.get("game_name", settings.SERVERNAME),
                "game_status": egi_config["game_status"],
                "game_website": egi_config.get("game_website", ""),
                "short_description": egi_config["short_description"],
                "long_description": egi_config.get("long_description", ""),
                "listing_contact": egi_config["listing_contact"],
                # How to play
                "telnet_hostname": egi_config.get("telnet_hostname", ""),
                "telnet_port": egi_config.get("telnet_port", ""),
                "web_client_url": egi_config.get("web_client_url", ""),
                # Game stats
                "connected_account_count": SESSIONS.account_count(),
                "total_account_count": AccountDB.objects.num_total_accounts() or 0,
                # System info
                "evennia_version": get_evennia_version(),
                "python_version": platform.python_version(),
                "django_version": django.get_version(),
                "server_platform": platform.platform(),
            }
        except KeyError as err:
            raise KeyError(f"Error loading GAME_INDEX_LISTING: {err}")

        data = urllib.parse.urlencode(values)

        d = agent.request(
            b"POST",
            bytes(self.report_url, "utf-8"),
            headers=Headers(headers),
            bodyProducer=StringProducer(data),
        )

        d.addCallback(self.handle_egd_response)
        return d

    def handle_egd_response(self, response):
        if 200 <= response.code < 300:
            d = defer.succeed((response.code, "OK"))
        else:
            # Go through the horrifying process of getting the response body
            # out of Twisted's plumbing.
            d = defer.Deferred()
            response.deliverBody(SimpleResponseReceiver(response.code, d))
        return d


class SimpleResponseReceiver(protocol.Protocol):
    """
    Used for pulling the response body out of an HTTP response.
    """

    def __init__(self, status_code, d):
        self.status_code = status_code
        self.buf = ""
        self.d = d

    def dataReceived(self, data):
        self.buf += data

    def connectionLost(self, reason=protocol.connectionDone):
        self.d.callback((self.status_code, self.buf))


@implementer(IBodyProducer)
class StringProducer(object):
    """
    Used for feeding a request body to the tx HTTP client.
    """

    def __init__(self, body):
        self.body = bytes(body, "utf-8")
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return defer.succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass


class QuietHTTP11ClientFactory(_HTTP11ClientFactory):
    """
    Silences the obnoxious factory start/stop messages in the default client.
    """

    noisy = False
