import pprint

"""
This module allows users based on a given condition (defaults to same location) to see
whether applicable users are typing or not. Currently, only the webclient is supported.
"""

# Notification timeout in milliseconds + <=100ms polling interval in the client.
_IS_TYPING_TIMEOUT = 1000 * 5


def is_typing_get_audience(session, *args, **kwargs):
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

    if not is_typing:
        return

    live_report_commands = [
        cmd for cmd in session.puppet.cmdset.current if hasattr(cmd, "client_live_report_typing")
    ]

    live_report_keywords = []  # full list
    for cmd in live_report_commands:
        live_report_keywords.append(cmd.key)  # actual commands
        live_report_keywords += cmd.aliases  # aliases

    live_report_keywords += [
        nick.value[2]  # this is the 'nick'
        for nick in session.puppet.nicks.all()
        if nick.value[1].split(" ")[0] in live_report_commands  # spaced keywords
        or nick[1][0] in live_report_commands  # handle things like ', ", :
    ]

    session.msg(
        is_typing={
            "type": "setup",
            "payload": {
                "live_report_keywords": live_report_keywords,
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

    audience = is_typing_get_audience(session=session, args=args, kwargs=kwargs)

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
