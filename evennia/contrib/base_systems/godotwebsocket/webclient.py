import json

from autobahn.twisted import WebSocketServerFactory
from twisted.application import internet

from evennia import settings
from evennia.contrib.base_systems.godotwebsocket.text2bbcode import parse_to_bbcode
from evennia.server.portal import webclient
from evennia.server.portal.portalsessionhandler import PORTAL_SESSIONS
from evennia.settings_default import LOCKDOWN_MODE


class GodotWebSocketClient(webclient.WebSocketClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.protocol_key = "godotclient/websocket"

    def send_text(self, *args, **kwargs):
        """
        Send text data. This will pre-process the text for
        color-replacement, conversion to html etc.

        Args:
            text (str): Text to send.

        Keyword Args:
            options (dict): Options-dict with the following keys understood:
                - raw (bool): No parsing at all (leave ansi-to-html markers unparsed).
                - nocolor (bool): Clean out all color.
                - screenreader (bool): Use Screenreader mode.
                - send_prompt (bool): Send a prompt with parsed html

        """
        if args:
            args = list(args)
            text = args[0]
            if text is None:
                return
        else:
            return

        flags = self.protocol_flags

        options = kwargs.pop("options", {})
        raw = options.get("raw", flags.get("RAW", False))
        client_raw = options.get("client_raw", False)
        nocolor = options.get("nocolor", flags.get("NOCOLOR", False))
        screenreader = options.get("screenreader", flags.get("SCREENREADER", False))
        prompt = options.get("send_prompt", False)

        if screenreader:
            # screenreader mode cleans up output
            text = webclient.parse_ansi(text, strip_ansi=True, xterm256=False, mxp=False)
            text = webclient._RE_SCREENREADER_REGEX.sub("", text)
        cmd = "prompt" if prompt else "text"
        if raw:
            if client_raw:
                args[0] = text
            else:
                args[0] = webclient.html.escape(text)  # escape html!
        else:
            args[0] = parse_to_bbcode(text, strip_ansi=nocolor)

        # send to client on required form [cmdname, args, kwargs]
        self.sendLine(json.dumps([cmd, args, kwargs]))


def start_plugin_services(portal):
    class GodotWebsocket(WebSocketServerFactory):
        "Only here for better naming in logs"
        pass

    factory = GodotWebsocket()
    factory.noisy = False
    factory.protocol = GodotWebSocketClient
    factory.sessionhandler = PORTAL_SESSIONS

    interface = "127.0.0.1" if LOCKDOWN_MODE else settings.GODOT_CLIENT_WEBSOCKET_CLIENT_INTERFACE

    port = settings.GODOT_CLIENT_WEBSOCKET_PORT
    websocket_service = internet.TCPServer(port, factory, interface=interface)
    websocket_service.setName("GodotWebSocket%s:%s" % (interface, port))
    portal.services.addService(websocket_service)
