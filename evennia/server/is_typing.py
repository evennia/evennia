"""
This module allows users based on a given condition (defaults to same location) to see
whether applicable users are typing or not. Currently, only the webclient is supported.
"""

from evennia import DefaultCharacter
from evennia.commands.default.general import CmdSay

# Notification timeout in milliseconds + <=100ms polling interval in the client.
_IS_TYPING_TIMEOUT = 1000 * 5


def is_typing_setup(session, *args, **kwargs):
    """
    This fetches any aliases for the "say" command and the
    specified notification timeout in milliseconds.

    Args:
        session: The player's current session.
    """

    options = session.protocol_flags
    is_typing = options.get("ISTYPING", True)

    if not is_typing:
        return

    session.msg(
        is_typing={
            "type": "setup",
            "payload": {"say_aliases": CmdSay.aliases, "talking_timeout": _IS_TYPING_TIMEOUT},
        }
    )


def is_typing_state(session, *args, **kwargs):
    """
    Broadcasts a typing state update from the session's puppet
    to all other characters meeting the configured conditions
    (defaults to same location).

    Args:
        session (Session): The player's current session.
        **kwargs:
            - state (bool): The typing state to broadcast.
    """
    options = session.protocol_flags
    is_typing = options.get("ISTYPING", True)

    if not is_typing:
        return

    state = kwargs.get("state")

    audience = DefaultCharacter.objects.filter_family(db_location=session.puppet.location).exclude(
        db_key=session.puppet.key
    )

    for puppet in audience:

        for puppet_session in puppet.sessions.all():
            puppet_session_options = puppet_session.protocol_flags
            puppet_session_is_typing = puppet_session_options.get("ISTYPING", True)

            if puppet_session_is_typing:
                puppet_session.msg(
                    is_typing={
                        "type": "typing",
                        "payload": {"name": session.puppet.name, "state": state},
                    }
                )
