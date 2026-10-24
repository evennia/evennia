"""
Aetos server-side input handlers.

Evennia treats every public function in a module listed in
`INPUT_FUNC_MODULES` as an inputfunc, dispatched by name. Aetos adds exactly one:
the `aetos_hello` handshake. Everything else Aetos sends is server-to-client.

This module is deliberately small. It never executes a command and never grants a
capability -- it answers a handshake with a description of what the game exposes.
Commands continue to arrive through Evennia's ordinary `text` inputfunc, so
Aetos adds no path that could bypass the command parser, locks or permissions.

"""

from evennia.contrib.base_systems.aetos_webclient import (
    manifest,
    protocol,
    providers,
    state,
)
from evennia.utils import logger


def _send_error(session, message):
    """
    Tell a client its handshake was rejected.

    Args:
        session (Session): The session to reply to.
        message (str): Human-readable reason.

    """
    session.msg(aetos_error=((), {"stage": "hello", "message": message}))


def aetos_hello(session, *args, **kwargs):
    """
    Handle an `aetos_hello` handshake from a client.

    Replies with the manifest describing what this game exposes. A malformed
    handshake is answered with an error rather than an exception: the payload is
    untrusted browser input, and anyone able to open a websocket can send it.

    Args:
        session (Session): The session that sent the handshake.
        *args: Unused; Aetos carries its data in kwargs.
        **kwargs: The handshake payload, plus Evennia's protocol options.

    """
    # Evennia adds its own bookkeeping keys to every inputfunc call. Strip them
    # so that a client is not blamed for fields it never sent.
    payload = {key: value for key, value in kwargs.items() if key not in ("options", "cmdid")}

    try:
        hello = protocol.parse_hello(payload)
    except protocol.AetosProtocolError as err:
        # Not logged at error level: a malformed hello is a client problem, and
        # an attacker could otherwise fill the server log at will.
        logger.log_info("Aetos: rejected handshake from session %s: %s" % (session.sessid, err))
        _send_error(session, str(err))
        return

    # Once per session, not once per handshake.
    #
    # A client may send `aetos_hello` as often as it likes -- Evennia's Portal
    # throttles it to MAX_COMMAND_RATE like any other input, but that is still
    # 80 a second, each writing up to 4KB of attacker-chosen capability names
    # into the game's log. The rejection path above already declined to log at
    # error level for exactly this reason; the acceptance path had the same
    # problem and not the same care.
    #
    # Comparing against the last set logged, rather than a "have logged" flag,
    # so a client that genuinely changes its capabilities is still reported.
    unknown = hello.unknown_capabilities
    if unknown and unknown != getattr(session, "aetos_logged_unknown", None):
        logger.log_info(
            "Aetos: session %s advertised unknown capabilities %s (ignored)"
            % (session.sessid, sorted(unknown))
        )
        session.aetos_logged_unknown = unknown

    # Record the handshake on the session so later milestones can tailor what
    # they send. This is transient connection state, not a stored player
    # profile -- it dies with the session.
    session.aetos_protocol = hello.protocol
    session.aetos_capabilities = hello.capabilities

    try:
        payload = manifest.build_manifest(character=getattr(session, "puppet", None))
    except manifest.AetosManifestError as err:
        # The game's own settings are wrong. That is a developer error worth an
        # error-level log, and the client is told rather than left waiting.
        logger.log_err("Aetos: invalid configuration, cannot build manifest: %s" % err)
        _send_error(session, "server misconfiguration: %s" % err)
        return

    session.msg(aetos_manifest=((), payload))


def aetos_request_sync(session, *args, **kwargs):
    """
    Handle a client request for a full state sync.

    Aetos must work on a game with zero custom code, and a pristine Evennia game
    has no hooks that call into Aetos. So the client asks: after connecting, and
    after each command it sends. A game wanting real push can call
    `state.push_sync()` from its own typeclass hooks instead, but must never have
    to.

    Args:
        session (Session): The requesting session.
        *args: Unused.
        **kwargs: Unused beyond Evennia's protocol options.

    """
    try:
        state.push_sync(session)
    except providers.AetosProviderError as err:
        # Bad provider configuration is a developer error. Report it once per
        # request rather than letting it surface as an empty, silent client.
        logger.log_err("Aetos: invalid provider configuration: %s" % err)
        session.msg(
            aetos_error=((), {"stage": "sync", "message": "server misconfiguration: %s" % err})
        )
