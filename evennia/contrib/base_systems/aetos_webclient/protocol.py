"""
The Aetos protocol.

Aetos rides on Evennia's existing structured webclient messages. Every Aetos
message is an ordinary Evennia outputfunc/inputfunc whose name is prefixed with
`aetos_`, so nothing in Evennia's transport needs to change and a non-Aetos client
simply ignores messages it does not recognise.

Message flow::

    client                          server
      |  aetos_hello  ------------->  |   client announces protocol + capabilities
      |  <-------------  aetos_manifest|  server describes what it exposes
      |  <-------------  aetos_sync    |  full authoritative state
      |  <-------------  aetos_*       |  deltas thereafter

Two rules govern everything here:

* **The server is authoritative.** Nothing in this module executes a command or
  grants a capability. Aetos messages describe state; commands still travel the
  ordinary Evennia command path and are still subject to locks and permissions.

* **Unknown is not fatal.** A client speaking a newer protocol, or a game exposing
  a capability this version has never heard of, must degrade rather than break.
  Validation here rejects malformed structure, not unfamiliar content.

"""

from evennia.contrib.base_systems.aetos_webclient import constants

# --- Message names -------------------------------------------------------

#: Client -> server. Sent once on connect and again after every reconnect.
MSG_HELLO = "aetos_hello"

#: Server -> client. Describes what this game exposes.
MSG_MANIFEST = "aetos_manifest"

#: Server -> client. Complete authoritative state; replaces transient client state.
MSG_SYNC = "aetos_sync"

#: Server -> client delta messages.
MSG_STATE = "aetos_state"
MSG_RESOURCES = "aetos_resources"
MSG_ROOM = "aetos_room"
MSG_ENTITIES = "aetos_entities"
MSG_MAP = "aetos_map"
MSG_ACTIONS = "aetos_actions"
MSG_EFFECTS = "aetos_effects"

#: A categorised game event.  Addendum A.76, A.11.
#:
#: Optional, and the reason it exists is worth stating: Aetos must never infer
#: what a line of game text *means*. It cannot tell a tell from a shout by
#: looking, and a client that guessed would be wrong on every game that words
#: things differently -- which is all of them.
#:
#: So a game that wants its output categorised says so. A game that does not is
#: not punished: everything arrives as "other", review by time and search still
#: work, and only review-by-channel is unavailable.
MSG_EVENT = "aetos_event"
MSG_TARGET = "aetos_target"
MSG_MEDIA = "aetos_media"
MSG_MODE = "aetos_mode"

#: Every delta message name, in the order they appear in a full sync.
DELTA_MESSAGES = (
    MSG_STATE,
    MSG_RESOURCES,
    MSG_ROOM,
    MSG_ENTITIES,
    MSG_MAP,
    MSG_ACTIONS,
    MSG_EFFECTS,
    MSG_TARGET,
    MSG_MEDIA,
    MSG_MODE,
)

#: Capabilities a client may advertise in its hello. A client is not required to
#: support all of them, and a server must not assume any particular one.
CAPABILITY_MANIFEST = "manifest"
CAPABILITY_RESOURCES = "resources"
CAPABILITY_MAP = "map"
CAPABILITY_ACTIONS = "actions"
CAPABILITY_MEDIA = "media"
CAPABILITY_ENTITIES = "entities"
CAPABILITY_EFFECTS = "effects"
CAPABILITY_TARGET = "target"
CAPABILITY_MODE = "mode"
CAPABILITY_VOICE = "voice"

KNOWN_CAPABILITIES = frozenset(
    (
        CAPABILITY_MANIFEST,
        CAPABILITY_RESOURCES,
        CAPABILITY_MAP,
        CAPABILITY_ACTIONS,
        CAPABILITY_MEDIA,
        CAPABILITY_ENTITIES,
        CAPABILITY_EFFECTS,
        CAPABILITY_TARGET,
        CAPABILITY_MODE,
        CAPABILITY_VOICE,
    )
)

#: Upper bound on how many capabilities a client may advertise. A hello is
#: attacker-controlled input; an unbounded list is a cheap memory amplifier.
MAX_CAPABILITIES = 64

#: Upper bound on the length of a single capability string.
MAX_CAPABILITY_LENGTH = 64


class AetosProtocolError(ValueError):
    """Raised when an Aetos message is structurally invalid."""


class AetosHello:
    """
    A validated client handshake.

    Attributes:
        protocol (int): Protocol version the client speaks.
        client (str): Client identifier, e.g. "aetos".
        capabilities (frozenset): Capability names the client advertises.

    """

    def __init__(self, protocol, client, capabilities):
        """
        Initialise a validated hello.

        Args:
            protocol (int): Protocol version the client speaks.
            client (str): Client identifier.
            capabilities (iterable): Capability names.

        """
        self.protocol = protocol
        self.client = client
        self.capabilities = frozenset(capabilities)

    @property
    def is_compatible(self):
        """
        bool: Whether this server can serve the client's protocol version.

        A client speaking an older protocol is served; the server simply omits
        anything that version does not understand. A client speaking a *newer*
        protocol is also served, at this server's version -- it is the client's
        job to degrade. Refusing either would break upgrades in both directions.

        """
        return self.protocol >= 1

    @property
    def unknown_capabilities(self):
        """
        frozenset: Advertised capabilities this server does not recognise.

        Present for diagnostics only. Unknown capabilities are never an error --
        a newer client may advertise things this server has not heard of.

        """
        return self.capabilities - KNOWN_CAPABILITIES

    def supports(self, capability):
        """
        Check whether the client advertised a capability.

        Args:
            capability (str): Capability name to test.

        Returns:
            bool: True if the client advertised it.

        """
        return capability in self.capabilities

    def __repr__(self):
        """
        Describe the handshake for a log line.

        Counts the capabilities rather than listing them: the payload is
        untrusted browser input, and a repr that expanded it would put up to
        4KB of somebody else's choosing into whatever was printing it.

        Returns:
            str: A short description.

        """
        return "<AetosHello protocol=%r client=%r capabilities=%d>" % (
            self.protocol,
            self.client,
            len(self.capabilities),
        )


def parse_hello(payload):
    """
    Validate and parse an `aetos_hello` payload.

    The payload arrives from the browser and is therefore untrusted. This
    rejects malformed structure but deliberately accepts unfamiliar capability
    names, so that a newer client is not locked out by an older server.

    Args:
        payload (dict): The raw kwargs of the inputfunc.

    Returns:
        AetosHello: The validated handshake.

    Raises:
        AetosProtocolError: If the payload is structurally invalid.

    """
    if not isinstance(payload, dict):
        raise AetosProtocolError("hello payload must be a mapping, got %r" % type(payload).__name__)

    protocol = payload.get("protocol")
    # bool is a subclass of int; True would otherwise pass as protocol version 1.
    if isinstance(protocol, bool) or not isinstance(protocol, int):
        raise AetosProtocolError("hello 'protocol' must be an integer, got %r" % (protocol,))
    if protocol < 1:
        raise AetosProtocolError("hello 'protocol' must be >= 1, got %r" % (protocol,))

    client = payload.get("client", "")
    if not isinstance(client, str):
        raise AetosProtocolError("hello 'client' must be a string, got %r" % type(client).__name__)
    client = client[:MAX_CAPABILITY_LENGTH]

    raw_capabilities = payload.get("capabilities", [])
    if not isinstance(raw_capabilities, (list, tuple)):
        raise AetosProtocolError(
            "hello 'capabilities' must be a list, got %r" % type(raw_capabilities).__name__
        )
    if len(raw_capabilities) > MAX_CAPABILITIES:
        raise AetosProtocolError(
            "hello advertises %d capabilities, maximum is %d"
            % (len(raw_capabilities), MAX_CAPABILITIES)
        )

    capabilities = set()
    for entry in raw_capabilities:
        if not isinstance(entry, str):
            raise AetosProtocolError(
                "hello capability entries must be strings, got %r" % type(entry).__name__
            )
        if entry:
            capabilities.add(entry[:MAX_CAPABILITY_LENGTH])

    return AetosHello(protocol=protocol, client=client, capabilities=capabilities)


def build_hello(capabilities=None, client=constants.CLIENT_NAME):
    """
    Build an `aetos_hello` payload.

    Provided so that tests and any Python-side client speak the same shape the
    browser does, rather than duplicating the literal.

    Args:
        capabilities (iterable, optional): Capability names to advertise.
            Defaults to every capability this version knows.
        client (str, optional): Client identifier.

    Returns:
        dict: The hello payload.

    """
    if capabilities is None:
        capabilities = sorted(KNOWN_CAPABILITIES)
    return {
        "protocol": constants.PROTOCOL_VERSION,
        "client": client,
        "capabilities": sorted(capabilities),
    }
