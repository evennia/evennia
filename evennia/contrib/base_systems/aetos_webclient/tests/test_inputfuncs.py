"""
Tests for the Aetos server-side handshake handler.

The handler receives untrusted browser input, so the malformed cases matter as
much as the happy path. A handshake that raises would surface to the player as a
dead client with no explanation.

"""

from django.test import TestCase, override_settings

from evennia.contrib.base_systems.aetos_webclient import inputfuncs, protocol


class FakeSession:
    """
    Minimal stand-in for an Evennia session.

    Only what the handler touches: an id, a puppet, and a msg() that records
    outgoing messages so tests can assert on them.

    """

    def __init__(self):
        self.sessid = 1
        self.puppet = None
        self.sent = []

    def msg(self, **kwargs):
        self.sent.append(kwargs)

    def last(self, name):
        """
        Return the kwargs payload of the last message of a given name.

        Args:
            name (str): Outputfunc name, e.g. "aetos_manifest".

        Returns:
            dict or None: The payload, or None if no such message was sent.

        """
        for message in reversed(self.sent):
            if name in message:
                return message[name][1]
        return None


class TestHandshakeSuccess(TestCase):
    """A well-formed handshake."""

    def setUp(self):
        self.session = FakeSession()

    def test_replies_with_a_manifest(self):
        inputfuncs.aetos_hello(self.session, **protocol.build_hello())
        self.assertIsNotNone(self.session.last("aetos_manifest"))

    def test_manifest_declares_the_protocol_version(self):
        inputfuncs.aetos_hello(self.session, **protocol.build_hello())
        self.assertEqual(self.session.last("aetos_manifest")["protocol"], 1)

    def test_records_capabilities_on_the_session(self):
        """
        Transient connection state, so later milestones can tailor what they
        send. It dies with the session -- Aetos stores no player profile.

        """
        inputfuncs.aetos_hello(self.session, **protocol.build_hello())
        self.assertIn(protocol.CAPABILITY_MAP, self.session.aetos_capabilities)
        self.assertEqual(self.session.aetos_protocol, 1)

    def test_tolerates_evennias_own_bookkeeping_kwargs(self):
        """
        Evennia adds `options` and `cmdid` to every inputfunc call. Treating
        those as client-supplied fields would reject every real handshake.

        """
        payload = protocol.build_hello()
        payload["options"] = {"foo": "bar"}
        payload["cmdid"] = 7
        inputfuncs.aetos_hello(self.session, **payload)
        self.assertIsNotNone(self.session.last("aetos_manifest"))

    def test_accepts_unknown_capabilities(self):
        """A newer client must not be locked out by an older server."""
        inputfuncs.aetos_hello(
            self.session, protocol=1, client="aetos", capabilities=["map", "telepathy"]
        )
        self.assertIsNotNone(self.session.last("aetos_manifest"))


class TestHandshakeFailure(TestCase):
    """Malformed handshakes, all reachable by anyone who can open a websocket."""

    def setUp(self):
        self.session = FakeSession()

    def test_malformed_handshake_gets_an_error_not_an_exception(self):
        """
        A raising handler would leave the player with a dead client and no
        explanation. The client is told instead.

        """
        inputfuncs.aetos_hello(self.session, protocol="not-a-number")
        error = self.session.last("aetos_error")
        self.assertIsNotNone(error)
        self.assertEqual(error["stage"], "hello")

    def test_malformed_handshake_sends_no_manifest(self):
        """A rejected client must not receive game data anyway."""
        inputfuncs.aetos_hello(self.session, protocol=0)
        self.assertIsNone(self.session.last("aetos_manifest"))

    def test_missing_protocol_is_rejected(self):
        inputfuncs.aetos_hello(self.session, client="aetos")
        self.assertIsNotNone(self.session.last("aetos_error"))

    @override_settings(AETOS_AUTOMATION={"nonsense_key": True})
    def test_server_misconfiguration_is_reported_not_raised(self):
        """
        A developer's bad settings must not take down a player's session. The
        error is logged for the developer and the client is told plainly.

        """
        inputfuncs.aetos_hello(self.session, **protocol.build_hello())
        error = self.session.last("aetos_error")
        self.assertIsNotNone(error)
        self.assertIn("misconfiguration", error["message"])
        self.assertIsNone(self.session.last("aetos_manifest"))

    #: One malformed value per Aetos setting a game can write.
    #:
    #: Kept as a table because the test above used `AETOS_AUTOMATION` alone --
    #: and `AETOS_AUTOMATION` happened to raise the one exception the handshake
    #: catches. `AETOS_UI` raises `AetosUIError`, a *sibling* of
    #: `AetosManifestError` rather than a subclass, so it went straight through
    #: `aetos_hello` as an unhandled exception. Every player connecting to a game
    #: with a mistyped `AETOS_UI` hit it, the startup check having only warned.
    #:
    #: Found by asking what a malformed setting does for *each* setting rather
    #: than for the one that was convenient to write a test with.
    MALFORMED = {
        "AETOS_UI": {"resources": "not a list"},
        "AETOS_FEATURES": {"resources": "yes"},
        "AETOS_AUTOMATION": {"macros": "sometimes"},
        "AETOS_PROVIDERS": {"resources": "world.nope.Missing"},
        "AETOS_BINDINGS": {"resources": {"h": {"value": "db.hp()"}}},
    }

    def test_no_malformed_setting_escapes_the_handshake(self):
        """
        Whatever a developer gets wrong, a player must get an answer.

        Either the manifest is built anyway -- providers and bindings degrade to
        their defaults on purpose -- or the client is told the server is
        misconfigured. What must never happen is an exception leaving
        `aetos_hello`, because that is a connection that neither completes nor
        explains itself.

        """
        for name, value in self.MALFORMED.items():
            with self.subTest(setting=name):
                session = FakeSession()
                with override_settings(**{name: value}):
                    try:
                        inputfuncs.aetos_hello(session, **protocol.build_hello())
                    except Exception as err:  # noqa: BLE001 - that is the finding
                        self.fail(
                            "a malformed %s escaped the handshake as %s: %s"
                            % (name, type(err).__name__, err)
                        )

                answered = session.last("aetos_manifest") or session.last("aetos_error")
                self.assertIsNotNone(
                    answered, "a malformed %s left the client with no reply at all" % name
                )
