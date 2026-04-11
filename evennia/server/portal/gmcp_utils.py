"""
Shared GMCP (Generic MUD Communication Protocol) utilities.

This module provides encoding and decoding functions for GMCP messages,
shared between telnet OOB and WebSocket wire format implementations.

GMCP messages follow the format: "Package.Subpackage json_payload"

The mapping dictionaries translate between Evennia's internal command
names and standard GMCP package names.
"""

import json

from evennia.utils.utils import is_iter

# Mapping from Evennia internal names to standard GMCP package names.
EVENNIA_TO_GMCP = {
    "client_options": "Core.Supports.Get",
    "get_inputfuncs": "Core.Commands.Get",
    "get_value": "Char.Value.Get",
    "repeat": "Char.Repeat.Update",
    "monitor": "Char.Monitor.Update",
}

# Reverse mapping from GMCP package names to Evennia internal names.
GMCP_TO_EVENNIA = {v: k for k, v in EVENNIA_TO_GMCP.items()}


def encode_gmcp(cmdname, *args, **kwargs):
    """
    Encode an Evennia command into a GMCP message string.

    Args:
        cmdname (str): Evennia OOB command name.
        *args: Command arguments.
        **kwargs: Command keyword arguments.

    Returns:
        str: A GMCP-formatted string like "Package.Name json_data"

    Notes:
        GMCP messages are formatted as:
            [cmdname, [], {}]          -> Cmd.Name
            [cmdname, [arg], {}]       -> Cmd.Name arg
            [cmdname, [args], {}]      -> Cmd.Name [args]
            [cmdname, [], {kwargs}]    -> Cmd.Name {kwargs}
            [cmdname, [arg], {kwargs}] -> Cmd.Name [arg, {kwargs}]
            [cmdname, [args], {kwargs}] -> Cmd.Name [[args], {kwargs}]

        Note: When there is exactly one positional argument, it is
        collapsed (encoded directly rather than wrapped in a list).
        This applies both with and without keyword arguments. This
        is inherited behavior from the original telnet_oob.py.

        If cmdname has a direct mapping in EVENNIA_TO_GMCP, that
        mapped name is used. Otherwise, underscores are converted to
        dots with initial capitalization. Names without underscores
        are placed in the Core package.

    """
    if cmdname in EVENNIA_TO_GMCP:
        gmcp_cmdname = EVENNIA_TO_GMCP[cmdname]
    elif "_" in cmdname:
        gmcp_cmdname = ".".join(
            word.capitalize() if not word.isupper() else word
            for word in cmdname.split("_")
        )
    else:
        gmcp_cmdname = "Core.%s" % (
            cmdname if cmdname.istitle() else cmdname.capitalize()
        )

    if not (args or kwargs):
        return gmcp_cmdname
    elif args:
        if len(args) == 1:
            args = args[0]
        if kwargs:
            return "%s %s" % (gmcp_cmdname, json.dumps([args, kwargs]))
        else:
            return "%s %s" % (gmcp_cmdname, json.dumps(args))
    else:
        return "%s %s" % (gmcp_cmdname, json.dumps(kwargs))


def decode_gmcp(data):
    """
    Decode a GMCP message string into Evennia command format.

    Args:
        data (str or bytes): GMCP data in the form "Module.Submodule.Cmdname structure".
            Bytes input is decoded as UTF-8.

    Returns:
        dict: A dict suitable for data_in(), e.g. ``{"cmdname": [[args], {kwargs}]}``.
            Returns empty dict if data is empty or cannot be parsed.

    Notes:
        Incoming GMCP is parsed as::

            Core.Name                         -> {"name": [[], {}]}
            Core.Name "string"                -> {"name": [["string"], {}]}
            Core.Name [arg, arg, ...]         -> {"name": [[args], {}]}
            Core.Name {key:val, ...}          -> {"name": [[], {kwargs}]}
            Core.Name [[args], {kwargs}]      -> {"name": [[args], {kwargs}]}

        Non-JSON payloads (plain strings that aren't valid JSON) are
        wrapped as a single-element list: ``{"name": [["the string"], {}]}``.
        This differs from the previous ``telnet_oob.py`` implementation
        which would split plain strings into individual characters due to
        ``list("string")`` being iterable.

    """
    if isinstance(data, bytes):
        data = data.decode("utf-8", errors="replace")

    if not data:
        return {}

    has_payload = True
    try:
        cmdname, structure = data.split(None, 1)
    except ValueError:
        cmdname, structure = data, ""
        has_payload = False

    # Check if this is a known GMCP package name
    if cmdname in GMCP_TO_EVENNIA:
        evennia_cmdname = GMCP_TO_EVENNIA[cmdname]
    else:
        # Convert Package.Name to package_name
        evennia_cmdname = cmdname.replace(".", "_")
        if evennia_cmdname.lower().startswith("core_"):
            evennia_cmdname = evennia_cmdname[5:]
        evennia_cmdname = evennia_cmdname.lower()

    try:
        structure = json.loads(structure)
    except (json.JSONDecodeError, ValueError):
        # structure is not JSON — treat as plain string
        pass

    args, kwargs = [], {}
    if is_iter(structure):
        if isinstance(structure, dict):
            kwargs = {key: value for key, value in structure.items() if key}
        else:
            args = list(structure)
    elif has_payload:
        args = [structure]

    return {evennia_cmdname: [args, kwargs]}
