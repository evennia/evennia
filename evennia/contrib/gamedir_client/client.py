import urllib

from django.conf import settings
from twisted.internet import defer
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.web.client import Agent, _HTTP11ClientFactory, HTTPConnectionPool
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from zope.interface import implements

from evennia.players.models import PlayerDB
from evennia.server.sessionhandler import SESSIONS
from evennia.utils import get_evennia_version, logger


class EvenniaGameDirClient(object):
    """
    This client class is used for gathering and sending game details to the
    Evennia Game Directory. Since EGD is in the early goings, this isn't
    incredibly configurable as far as what is being sent.
    """
    def __init__(self, on_bad_request=None):
        """
        :param on_bad_request: Optional callable to trigger when a bad request
            was sent. This is almost always going to be due to bad config.
        """
        self.report_host = 'http://evennia-game-directory.appspot.com'
        self.report_path = '/api/v1/game/check_in'
        self.report_url = self.report_host + self.report_path

        self._on_bad_request = on_bad_request
        # Oh, the humanity. Silence the factory start/stop messages.
        self._conn_pool = HTTPConnectionPool(reactor)
        self._conn_pool._factory = QuietHTTP11ClientFactory

    @inlineCallbacks
    def send_game_details(self):
        """
        This is where the magic happens. Send details about the game to the
        Evennia Game Directory.
        """
        status_code, response_body = yield self._form_and_send_request()
        if status_code == 200:
            logger.log_infomsg(
                "Successfully sent game details to Evennia Game Directory.")
            return
        # At this point, either EGD is having issues or the payload we sent
        # is improperly formed (probably due to mis-configuration).
        logger.log_errmsg(
            'Failed to send game details to Evennia Game Directory. HTTP '
            'status code was %s. Message was: %s' % (status_code, response_body)
        )
        if status_code == 400 and self._on_bad_request:
            # Improperly formed request. Defer to the callback as far as what
            # to do. Probably not a great idea to continue attempting to send
            # to EGD, though.
            self._on_bad_request()

    def _form_and_send_request(self):
        agent = Agent(reactor, pool=self._conn_pool)
        headers = {
            'User-Agent': ['Evennia Game Directory Client'],
            'Content-Type': ['application/x-www-form-urlencoded'],
        }
        gd_config = settings.GAMEDIR_CLIENT
        values = {
            'game_name': settings.SERVERNAME,
            'game_status': gd_config['game_status'],
            'game_website': gd_config.get('game_website'),
            'listing_contact': gd_config['listing_contact'],
            'evennia_version': get_evennia_version(),
            'telnet_hostname': gd_config['telnet_hostname'],
            'telnet_port': gd_config['telnet_port'],
            'connected_player_count': SESSIONS.player_count(),
            'total_player_count': PlayerDB.objects.num_total_players() or 0,
        }
        data = urllib.urlencode(values)

        d = agent.request(
            'POST', self.report_url,
            headers=Headers(headers),
            bodyProducer=StringProducer(data))

        d.addCallback(self.handle_egd_response)
        return d

    def handle_egd_response(self, response):
        if 200 <= response.code < 300:
            d = defer.succeed((response.code, 'OK'))
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
        self.buf = ''
        self.d = d

    def dataReceived(self, data):
        self.buf += data

    def connectionLost(self, reason=protocol.connectionDone):
        self.d.callback((self.status_code, self.buf))


class StringProducer(object):
    """
    Used for feeding a request body to the tx HTTP client.
    """
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
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
