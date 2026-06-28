"""
This module allows users based on a given condition (defaults to same location) to see
whether applicable users are typing or not. Currently, only the webclient is supported.

Relevant Settings:
    WEBCLIENT_TYPING_TIMEOUT - the timeout in seconds between polling intervals.
    WEBCLIENT_TYPING_AUDIENCE_GETTER - the path to the method that returns the sessions
                                       that should receive typing updates. Must return
                                       a list of session objects.

Upon the webclient loading the is_typing plugin, it will request setup from the server
(is_typing_setup) which will return the timeout and what words to watch for. Anytime
the client uses a relevant word, it will notify the server of the relevant session and
its state (typing or not typing). The server then fetches that session's relevant (if
any) other sessions based on the criteria of the audience_getter and passes on the state
update to the fetched audience.
"""

from django.conf import settings
from evennia.utils.utils import class_from_module


def is_typing_get_audience_common_location(session, *args, **kwargs):
    """
    This should return a list of puppets to relay our client live reporting messages.
    The example returns other puppets in the same room as the reporting session with
    the typing puppet filtered out.

    Args:
        session: The player's current session.
    """

    if session.puppet is None:
       return []

    audience_including_typer = session.puppet.location.contents_get(content_type="character")

    audience = [puppet for puppet in audience_including_typer if puppet.id != session.puppet.id]

    return audience


# A utility to fetch the method used to get the relevant audience for client live
# reporting commands. The retrieved method should return a list of session objects.
# Sessions without a puppet will be ignored.
audience_getter = class_from_module(
    settings.WEBCLIENT_TYPING_AUDIENCE_GETTER
    or "evennia.server.is_typing.is_typing_get_audience_common_location"
)


def is_typing_setup(session, *args, **kwargs):
    """
    This fetches any commands/aliases/nicks that we want to monitor and the
    specified notification timeout in milliseconds.

    Args:
        session: The player's current session.
    """

    options = session.protocol_flags
    is_typing = options.get("ISTYPING", True)

    if not is_typing or session.puppet is None:
        return

    live_report_commands = [
        cmd for cmd in session.puppet.cmdset.current if cmd.client_live_report_typing
    ]

    # Commands and aliases
    live_report_keywords = [kw for kw in live_report_commands for kw in (kw.key, *kw.aliases)]

    live_report_keywords += [
        nick.value[2]  # this is the 'nick'
        for nick in session.puppet.nicks.all()
        if nick.value[3].split(" ")[0] in live_report_commands  # spaced keywords
        or nick.value[3][0] in live_report_commands  # handle things like ', ", :
    ]

    session.msg(
        is_typing={
            "type": "setup",
            "payload": {
                "live_report_keywords": live_report_keywords,
                "typing_timeout": settings.WEBCLIENT_TYPING_TIMEOUT * 1000,
            },
        }
    )


def is_typing_state(user_session, *args, **kwargs):
    """
    Broadcasts a typing state update from the session's puppet
    to all other characters meeting the configured conditions
    (defaults to same location).

    Args:
        session (Session): The player's current session.
        **kwargs:
            - state (bool): The typing state to broadcast.
    """
    global audience_getter

    options = user_session.protocol_flags
    is_typing = options.get("ISTYPING", True)

    if not is_typing or user_session.puppet is None:
        return

    state = kwargs.get("state")

    audience = audience_getter(session=user_session, args=args, kwargs=kwargs)

    # Filter out clients not interested in updates
    relevant_sessions = [
        puppet_session
        for puppet in audience
        for puppet_session in puppet.sessions.all()
        if puppet_session.protocol_flags.get("ISTYPING", True)
    ] # Potential timeout adjustment based on audience size

    # Update relevant clients
    for puppet_session in relevant_sessions:
        puppet_session.msg(
            is_typing={
                "type": "typing",
                "payload": {"name": user_session.puppet.name, "state": state},
            }
        )
