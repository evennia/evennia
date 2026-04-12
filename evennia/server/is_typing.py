"""
This module allows users based on a given condition (defaults to same location) to see
whether applicable users are typing or not. Currently, only the webclient is supported.
"""

# Notification timeout in milliseconds + <=100ms polling interval in the client.
_IS_TYPING_TIMEOUT = 1000 * 5


def get_is_typing_audience(session, *args, **kwargs):
    """
    This should return a list of puppets to relay our client live reporting messages.
    The example returns other puppets in the same room as the reporting session with
    the typing puppet filtered out.

    Args:
        session: The player's current session.
    """

    audience_including_typer = session.puppet.location.contents_get(content_type="character")

    audience = [puppet for puppet in audience_including_typer if puppet.id != session.puppet.id]

    return audience


def is_typing_setup(session, *args, **kwargs):
    """
    This fetches any aliases for the "say" command and the
    specified notification timeout in milliseconds.

    Args:
        session: The player's current session.
    """

    options = session.protocol_flags
    is_typing = options.get("ISTYPING", True)

    live_report_commands = [
        cmd for cmd in session.puppet.cmdset.current if hasattr(cmd, "client_live_report_typing")
    ]
    commands_and_aliases = []
    for cmd in live_report_commands:
        commands_and_aliases.append(cmd.key)
        commands_and_aliases += cmd.aliases

    if not is_typing:
        return

    session.msg(
        is_typing={
            "type": "setup",
            "payload": {
                "live_report_commands": commands_and_aliases,
                "typing_timeout": _IS_TYPING_TIMEOUT,
            },
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

    audience = get_is_typing_audience(session=session, args=args, kwargs=kwargs)

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
