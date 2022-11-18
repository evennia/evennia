"""
Grapevine network connection

This is an implementation of the Grapevine Websocket protocol v 1.0.0 as
outlined here: https://grapevine.haus/docs

This will allow the linked game to transfer status as well as connects
the grapevine client to in-game channels.

"""

import json

from autobahn.twisted.websocket import (
    WebSocketClientFactory,
    WebSocketClientProtocol,
    connectWS,
)
from django.conf import settings
from twisted.internet import protocol

from evennia.server.session import Session
from evennia.utils import get_evennia_version
from evennia.utils.logger import log_err, log_info

# There is only one at this time
GRAPEVINE_URI = "wss://grapevine.haus/socket"

GRAPEVINE_CLIENT_ID = settings.GRAPEVINE_CLIENT_ID
GRAPEVINE_CLIENT_SECRET = settings.GRAPEVINE_CLIENT_SECRET
GRAPEVINE_CHANNELS = settings.GRAPEVINE_CHANNELS

# defined error codes
CLOSE_NORMAL = 1000
GRAPEVINE_AUTH_ERROR = 4000
GRAPEVINE_HEARTBEAT_FAILURE = 4001


class RestartingWebsocketServerFactory(WebSocketClientFactory, protocol.ReconnectingClientFactory):
    """
    A variant of the websocket-factory that auto-reconnects.

    """

    initialDelay = 1
    factor = 1.5
    maxDelay = 60

    def __init__(self, sessionhandler, *args, **kwargs):

        self.uid = kwargs.pop("uid")
        self.channel = kwargs.pop("grapevine_channel")
        self.sessionhandler = sessionhandler

        # self.noisy = False
        self.port = None
        self.bot = None

        WebSocketClientFactory.__init__(self, GRAPEVINE_URI, *args, **kwargs)

    def buildProtocol(self, addr):
        """
        Build new instance of protocol

        Args:
            addr (str): Not used, using factory/settings data

        """
        protocol = GrapevineClient()
        protocol.factory = self
        protocol.channel = self.channel
        protocol.sessionhandler = self.sessionhandler
        return protocol

    def startedConnecting(self, connector):
        """
        Tracks reconnections for debugging.

        Args:
            connector (Connector): Represents the connection.

        """
        log_info("(re)connecting to grapevine channel '%s'" % self.channel)

    def clientConnectionFailed(self, connector, reason):
        """
        Called when Client failed to connect.

        Args:
            connector (Connection): Represents the connection.
            reason (str): The reason for the failure.

        """
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionLost(self, connector, reason):
        """
        Called when Client loses connection.

        Args:
            connector (Connection): Represents the connection.
            reason (str): The reason for the failure.

        """
        if not (self.bot or (self.bot and self.bot.stopping)):
            self.retry(connector)

    def reconnect(self):
        """
        Force a reconnection of the bot protocol. This requires
        de-registering the session and then reattaching a new one,
        otherwise you end up with an ever growing number of bot
        sessions.

        """
        self.bot.stopping = True
        self.bot.transport.loseConnection()
        self.sessionhandler.server_disconnect(self.bot)
        self.start()

    def start(self):
        "Connect protocol to remote server"

        try:
            from twisted.internet import ssl
        except ImportError:
            log_err("To use Grapevine, The PyOpenSSL module must be installed.")
        else:
            context_factory = ssl.ClientContextFactory() if self.isSecure else None
            connectWS(self, context_factory)
            # service.name = "websocket/grapevine"
            # self.sessionhandler.portal.services.addService(service)


class GrapevineClient(WebSocketClientProtocol, Session):
    """
    Implements the grapevine client
    """

    def __init__(self):
        WebSocketClientProtocol.__init__(self)
        Session.__init__(self)
        self.restart_downtime = None

    def at_login(self):
        pass

    def onOpen(self):
        """
        Called when connection is established.

        """
        self.restart_downtime = None
        self.restart_task = None

        self.stopping = False
        self.factory.bot = self

        self.init_session("grapevine", GRAPEVINE_URI, self.factory.sessionhandler)
        self.uid = int(self.factory.uid)
        self.logged_in = True
        self.sessionhandler.connect(self)

        self.send_authenticate()

    def onMessage(self, payload, isBinary):
        """
        Callback fired when a complete WebSocket message was received.

        Args:
            payload (bytes): The WebSocket message received.
            isBinary (bool): Flag indicating whether payload is binary or
                             UTF-8 encoded text.

        """
        if not isBinary:
            data = json.loads(str(payload, "utf-8"))
            self.data_in(data=data)
            self.retry_task = None

    def onClose(self, wasClean, code=None, reason=None):
        """
        This is executed when the connection is lost for whatever
        reason. it can also be called directly, from the disconnect
        method.

        Args:
            wasClean (bool): ``True`` if the WebSocket was closed cleanly.
            code (int or None): Close status as sent by the WebSocket peer.
            reason (str or None): Close reason as sent by the WebSocket peer.

        """
        self.disconnect(reason)

        if code == GRAPEVINE_HEARTBEAT_FAILURE:
            log_err("Grapevine connection lost (Heartbeat error)")
        elif code == GRAPEVINE_AUTH_ERROR:
            log_err("Grapevine connection lost (Auth error)")
        elif self.restart_downtime:
            # server previously warned us about downtime and told us to be
            # ready to reconnect.
            log_info("Grapevine connection lost (Server restart).")

    def _send_json(self, data):
        """
        Send (json-) data to client.

        Args:
            data (str): Text to send.

        """
        return self.sendMessage(json.dumps(data).encode("utf-8"))

    def disconnect(self, reason=None):
        """
        Generic hook for the engine to call in order to
        disconnect this protocol.

        Args:
            reason (str or None): Motivation for the disconnection.

        """
        self.sessionhandler.disconnect(self)
        # autobahn-python: 1000 for a normal close, 3000-4999 for app. specific,
        # in case anyone wants to expose this functionality later.
        #
        # sendClose() under autobahn/websocket/interfaces.py
        self.sendClose(CLOSE_NORMAL, reason)

    # send_* method are automatically callable through .msg(heartbeat={}) etc

    def send_authenticate(self, *args, **kwargs):
        """
        Send grapevine authentication. This should be send immediately upon connection.

        """
        data = {
            "event": "authenticate",
            "payload": {
                "client_id": GRAPEVINE_CLIENT_ID,
                "client_secret": GRAPEVINE_CLIENT_SECRET,
                "supports": ["channels"],
                "channels": GRAPEVINE_CHANNELS,
                "version": "1.0.0",
                "user_agent": get_evennia_version("pretty"),
            },
        }
        # override on-the-fly
        data.update(kwargs)

        self._send_json(data)

    def send_heartbeat(self, *args, **kwargs):
        """
        Send heartbeat to remote grapevine server.

        """
        # pass along all connected players
        data = {"event": "heartbeat", "payload": {}}
        sessions = self.sessionhandler.get_sessions(include_unloggedin=False)
        data["payload"]["players"] = [
            sess.account.key for sess in sessions if hasattr(sess, "account")
        ]

        self._send_json(data)

    def send_subscribe(self, channelname, *args, **kwargs):
        """
        Subscribe to new grapevine channel

        Use with session.msg(subscribe="channelname")
        """
        data = {"event": "channels/subscribe", "payload": {"channel": channelname}}
        self._send_json(data)

    def send_unsubscribe(self, channelname, *args, **kwargs):
        """
        Un-subscribe to a grapevine channel

        Use with session.msg(unsubscribe="channelname")
        """
        data = {"event": "channels/unsubscribe", "payload": {"channel": channelname}}
        self._send_json(data)

    def send_channel(self, text, channel, sender, *args, **kwargs):
        """
        Send text type Evennia -> grapevine

        This is the channels/send message type

        Use with session.msg(channel=(message, channel, sender))

        """

        data = {
            "event": "channels/send",
            "payload": {"message": text, "channel": channel, "name": sender},
        }
        self._send_json(data)

    def send_default(self, *args, **kwargs):
        """
        Ignore other outputfuncs

        """
        pass

    def data_in(self, data, **kwargs):
        """
        Send data grapevine -> Evennia

        Keyword Args:
            data (dict): Converted json data.

        """
        event = data["event"]
        if event == "authenticate":
            # server replies to our auth handshake
            if data["status"] != "success":
                log_err("Grapevine authentication failed.")
                self.disconnect()
            else:
                log_info("Connected and authenticated to Grapevine network.")
        elif event == "heartbeat":
            # server sends heartbeat - we have to send one back
            self.send_heartbeat()
        elif event == "restart":
            # set the expected downtime
            self.restart_downtime = data["payload"]["downtime"]
        elif event == "channels/subscribe":
            # subscription verification
            if data.get("status", "success") == "failure":
                err = data.get("error", "N/A")
                self.sessionhandler.data_in(
                    bot_data_in=((f"Grapevine error: {err}"), {"event": event})
                )
        elif event == "channels/unsubscribe":
            # unsubscribe-verification
            pass
        elif event == "channels/broadcast":
            # incoming broadcast from network
            payload = data["payload"]

            # print("channels/broadcast:", payload["channel"], self.channel)
            if str(payload["channel"]) != self.channel:
                # only echo from channels this particular bot actually listens to
                return
            else:
                # correct channel
                self.sessionhandler.data_in(
                    self,
                    bot_data_in=(
                        str(payload["message"]),
                        {
                            "event": event,
                            "grapevine_channel": str(payload["channel"]),
                            "sender": str(payload["name"]),
                            "game": str(payload["game"]),
                        },
                    ),
                )
        elif event == "channels/send":
            pass
        else:
            self.sessionhandler.data_in(self, bot_data_in=("", kwargs))
