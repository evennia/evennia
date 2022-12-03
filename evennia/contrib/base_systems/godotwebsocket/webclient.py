"""
Godot Websocket - ChrisLR 2022

This file contains the code necessary to dedicate a port to communicate with Godot via Websockets.
It uses the plugin system and should be plugged via settings as detailed in the readme.
"""
import json

from autobahn.twisted import WebSocketServerFactory
from twisted.application import internet

from evennia import settings
from evennia.contrib.base_systems.godotwebsocket.text2bbcode import parse_to_bbcode
from evennia.server.portal import webclient
from evennia.server.portal.portalsessionhandler import PORTAL_SESSIONS
from evennia.settings_default import LOCKDOWN_MODE


class GodotWebSocketClient(webclient.WebSocketClient):
    """
    Implements the server-side of the Websocket connection specific to Godot.
    It inherits from the basic Websocket implementation and changes only what is necessary.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.protocol_key = "godotclient/websocket"

    def send_text(self, *args, **kwargs):
        """
        Send text data. This will pre-process the text for
        color-replacement, conversion to bbcode etc.

        Args:
            text (str): Text to send.

        Keyword Args:
            options (dict): Options-dict with the following keys understood:
                - nocolor (bool): Clean out all color.
                - send_prompt (bool): Send a prompt with parsed bbcode

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
        nocolor = options.get("nocolor", flags.get("NOCOLOR", False))
        prompt = options.get("send_prompt", False)

        cmd = "prompt" if prompt else "text"
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
