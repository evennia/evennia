"""
Inputhandler functions

Inputcommands are always called from the client (they handle server
input, hence the name).

This module is loaded by being included in
`settings.INPUT_HANDLER_MODULES`.

All *global functions* included in this module are
considered input-handler functions and can be called
by the client to handle input.

An inputhandler function must have the following call signature:

    cmdname(session, *args, **kwargs)

Where session will be the active session and *args, **kwargs are extra
incoming arguments and keyword properties.

A special command is the "default" command, which is called when
no other cmdname matches:

    default(session, cmdname, *args, **kwargs)

"""

# import the contents of the default inputhandler_func module
#from evennia.server.inputhandler_funcs import *


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
#
# def default(session, cmdname, *args, **kwargs):
#     """
#     Handles commands without a matching inputhandler func.
#
#     Args:
#         session (Session): The active Session.
#         cmdname (str): The (unmatched) command name
#         args, kwargs (any): Arguments to function.
#
#     """
#     pass
