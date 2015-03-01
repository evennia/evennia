"""
OOB configuration.

This module should be included in (or replace) the
default module set in settings.OOB_PLUGIN_MODULES

A function oob_error will be used as optional error management.
The available OOB commands can be extended by changing

    `settings.OOB_PLUGIN_MODULES`

CMD_MAP: This module must contain a global dictionary CMD_MAP. This is
a dictionary that maps the call-name available  to a function in this
module (this allows you to map multiple oob cmdnames to a single
actual Python function, for example).

oob functions have the following call signature:

    function(session, *args, **kwargs)

where session is the active session and *args, **kwargs are extra
arguments sent with the oob command.

A function mapped to the key "oob_error" will retrieve error strings
if it is defined. It will get the error message as its 1st argument.

    oob_error(session, error, *args, **kwargs)

This allows for customizing error handling.

Data is usually returned to the user via a return OOB call:

   session.msg(oob=(oobcmdname, (args,), {kwargs}))

Oobcmdnames are case-sensitive.  Note that args, kwargs must be
iterable. Non-iterables will be interpreted as a new command name (you
can send multiple oob commands with one msg() call))

"""

# import the contents of the default msdp module
from evennia.server.oob_cmds import *


# def oob_echo(session, *args, **kwargs):
#     """
#     Example echo function. Echoes args, kwargs sent to it.
#
#     Args:
#         session (Session): The Session to receive the echo.
#         args (list of str): Echo text.
#         kwargs (dict of str, optional): Keyed echo text
#
#     """
#     session.msg(oob=("echo", args, kwargs))
#
## oob command map
# CMD_MAP = {"ECHO": oob_echo}
