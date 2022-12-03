"""
Godot Websocket - ChrisLR 2022

This provides parsing the ansi text to bbcode used by Godot for their RichTextLabel
and also provides the proper portal service to dedicate a port for Godot's Websockets.

This allows you to connect both the regular webclient and a godot specific webclient.
You can simply connect the resulting text to Godot's RichTextLabel and have the proper display.
You could also pass extra data to this client for advanced functionality.

See the docs for more information.
"""
from evennia.contrib.base_systems.godotwebsocket.text2bbcode import (
    BBCODE_PARSER,
    parse_to_bbcode,
)
from evennia.contrib.base_systems.godotwebsocket.webclient import GodotWebSocketClient
