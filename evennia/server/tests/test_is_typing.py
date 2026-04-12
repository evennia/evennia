"""
Tests for the is_typing module.

Covers:
- is_typing_get_audience: audience filtering by location
- is_typing_setup: setup message with commands, aliases, and nicks
- is_typing_state: state broadcast with per-session ISTYPING flag
"""

from unittest.mock import MagicMock, patch

from evennia.commands.command import Command
from evennia.server.is_typing import is_typing_get_audience, is_typing_setup, is_typing_state
from evennia.utils.test_resources import BaseEvenniaTest


# ---------------------------------------------------------------------------
# Minimal test commands with client_live_report_typing
# ---------------------------------------------------------------------------


class _SayCmd(Command):
    """Test stand-in for CmdSay."""

    key = "say"
    aliases = ['"', "'"]
    locks = "cmd:all()"
    client_live_report_typing = True

    def func(self):
        pass


class _PoseCmd(Command):
    """Test stand-in for CmdPose."""

    key = "pose"
    aliases = [":", "emote"]
    locks = "cmd:all()"
    client_live_report_typing = True

    def func(self):
        pass


class _NormalCmd(Command):
    """A command without live_report_typing -- should be excluded."""

    key = "look"
    aliases = ["l"]
    locks = "cmd:all()"

    def func(self):
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_puppet_session(istyping=True):
    """Return a mock session suitable for use as a puppet's session."""
    sess = MagicMock()
    sess.protocol_flags = {"ISTYPING": istyping}
    return sess


# ---------------------------------------------------------------------------
# is_typing_get_audience
# ---------------------------------------------------------------------------


class TestIsTypingGetAudience(BaseEvenniaTest):
    """Tests for is_typing_get_audience."""

    def setUp(self):
        super().setUp()
        self.session.puppet = self.char1

    def test_excludes_typer_from_audience(self):
        """Other characters in the same room are returned; the typer is not."""
        audience = is_typing_get_audience(self.session)
        self.assertIn(self.char2, audience)
        self.assertNotIn(self.char1, audience)

    def test_excludes_non_character_objects(self):
        """Non-character objects in the room are not included."""
        audience = is_typing_get_audience(self.session)
        self.assertNotIn(self.obj1, audience)
        self.assertNotIn(self.obj2, audience)

    def test_empty_when_typer_is_alone(self):
        """Audience is empty when no other characters share the location."""
        self.char2.location = self.room2
        audience = is_typing_get_audience(self.session)
        self.assertEqual(audience, [])

    def test_returns_multiple_others(self):
        """All other characters in the same room are included."""
        from evennia.utils import create

        char3 = create.create_object(
            self.character_typeclass, key="Char3", location=self.room1, home=self.room1
        )
        try:
            audience = is_typing_get_audience(self.session)
            self.assertIn(self.char2, audience)
            self.assertIn(char3, audience)
            self.assertEqual(len(audience), 2)
        finally:
            char3.delete()


# ---------------------------------------------------------------------------
# is_typing_setup
# ---------------------------------------------------------------------------


class TestIsTypingSetup(BaseEvenniaTest):
    """Tests for is_typing_setup."""

    def setUp(self):
        super().setUp()
        self.session.puppet = self.char1
        self.session.msg = MagicMock()
        # Provide a controlled cmdset with known commands.
        self.say_cmd = _SayCmd()
        self.pose_cmd = _PoseCmd()
        self.normal_cmd = _NormalCmd()
        self.char1.cmdset.current = [self.say_cmd, self.pose_cmd, self.normal_cmd]

    def _get_setup_payload(self):
        """Return the payload dict from the first is_typing msg call."""
        self.session.msg.assert_called_once()
        kwargs = self.session.msg.call_args.kwargs
        self.assertIn("is_typing", kwargs)
        return kwargs["is_typing"]

    def test_sends_setup_message(self):
        """A setup message is sent to the session when ISTYPING is enabled."""
        is_typing_setup(self.session)
        payload = self._get_setup_payload()
        self.assertEqual(payload["type"], "setup")
        self.assertIn("live_report_keywords", payload["payload"])
        self.assertIn("typing_timeout", payload["payload"])

    def test_istyping_false_sends_nothing(self):
        """No message is sent when ISTYPING is explicitly disabled."""
        self.session.protocol_flags["ISTYPING"] = False
        is_typing_setup(self.session)
        self.session.msg.assert_not_called()

    def test_istyping_defaults_to_enabled(self):
        """ISTYPING defaults to True when absent from protocol_flags."""
        self.session.protocol_flags.pop("ISTYPING", None)
        is_typing_setup(self.session)
        self.session.msg.assert_called_once()

    def test_includes_command_key(self):
        """The key of a live-reporting command is in the keywords."""
        is_typing_setup(self.session)
        keywords = self._get_setup_payload()["payload"]["live_report_keywords"]
        self.assertIn("say", keywords)
        self.assertIn("pose", keywords)

    def test_includes_command_aliases(self):
        """Aliases of live-reporting commands are in the keywords."""
        is_typing_setup(self.session)
        keywords = self._get_setup_payload()["payload"]["live_report_keywords"]
        # CmdSay aliases
        self.assertIn('"', keywords)
        self.assertIn("'", keywords)
        # CmdPose aliases
        self.assertIn(":", keywords)
        self.assertIn("emote", keywords)

    def test_excludes_non_live_command(self):
        """Commands without client_live_report_typing are not in the keywords."""
        is_typing_setup(self.session)
        keywords = self._get_setup_payload()["payload"]["live_report_keywords"]
        self.assertNotIn("look", keywords)
        self.assertNotIn("l", keywords)

    def test_includes_nick_with_spaced_live_command(self):
        """A nick whose replacement starts with a live command is included."""
        # "s $1" -> "say $1": first word of replacement is "say" -> match
        self.char1.nicks.add("s $1", "say $1")
        is_typing_setup(self.session)
        keywords = self._get_setup_payload()["payload"]["live_report_keywords"]
        self.assertIn("s $1", keywords)

    def test_excludes_nick_not_mapped_to_live_command(self):
        """A nick that maps to a non-live command is not included."""
        # "go $1" -> "look $1": "look" is not a live command
        self.char1.nicks.add("go $1", "look $1")
        is_typing_setup(self.session)
        keywords = self._get_setup_payload()["payload"]["live_report_keywords"]
        self.assertNotIn("go $1", keywords)

    def test_includes_nick_with_single_char_command_alias(self):
        """A nick whose replacement starts with a single-char command alias is included."""
        # "greet" -> "'hello friend": first char of replacement is "'", an alias for say
        self.char1.nicks.add("greet", "'hello friend")
        is_typing_setup(self.session)
        keywords = self._get_setup_payload()["payload"]["live_report_keywords"]
        self.assertIn("greet", keywords)

    def test_typing_timeout_value(self):
        """The timeout sent matches the module constant."""
        from evennia.server.is_typing import _IS_TYPING_TIMEOUT

        is_typing_setup(self.session)
        timeout = self._get_setup_payload()["payload"]["typing_timeout"]
        self.assertEqual(timeout, _IS_TYPING_TIMEOUT)


# ---------------------------------------------------------------------------
# is_typing_state
# ---------------------------------------------------------------------------


class TestIsTypingState(BaseEvenniaTest):
    """Tests for is_typing_state."""

    def setUp(self):
        super().setUp()
        self.session.puppet = self.char1
        self.char2_session = _make_mock_puppet_session(istyping=True)
        # Patch char2.sessions.all — the handler can't be replaced wholesale.
        self._sessions_patcher = patch.object(
            self.char2.sessions, "all", return_value=[self.char2_session]
        )
        self._sessions_patcher.start()

    def tearDown(self):
        self._sessions_patcher.stop()
        super().tearDown()

    def test_broadcasts_typing_true_to_audience(self):
        """A state=True update is sent to other characters' sessions."""
        is_typing_state(self.session, state=True)
        self.char2_session.msg.assert_called_once()
        payload = self.char2_session.msg.call_args.kwargs["is_typing"]
        self.assertEqual(payload["type"], "typing")
        self.assertEqual(payload["payload"]["state"], True)
        self.assertEqual(payload["payload"]["name"], self.char1.name)

    def test_broadcasts_typing_false_to_audience(self):
        """A state=False update (typing stopped) is also broadcast."""
        is_typing_state(self.session, state=False)
        self.char2_session.msg.assert_called_once()
        payload = self.char2_session.msg.call_args.kwargs["is_typing"]
        self.assertEqual(payload["payload"]["state"], False)

    def test_sender_istyping_false_sends_nothing(self):
        """If the sender has ISTYPING disabled, no messages are dispatched."""
        self.session.protocol_flags["ISTYPING"] = False
        is_typing_state(self.session, state=True)
        self.char2_session.msg.assert_not_called()

    def test_receiver_istyping_false_skips_that_session(self):
        """A receiver with ISTYPING disabled does not get the message."""
        self.char2_session.protocol_flags["ISTYPING"] = False
        is_typing_state(self.session, state=True)
        self.char2_session.msg.assert_not_called()

    def test_receiver_without_istyping_flag_defaults_to_enabled(self):
        """A receiver session with no ISTYPING key defaults to receiving messages."""
        self.char2_session.protocol_flags = {}
        is_typing_state(self.session, state=True)
        self.char2_session.msg.assert_called_once()

    def test_only_sessions_with_istyping_receive_message(self):
        """When char2 has two sessions, only the ISTYPING=True one gets the message."""
        silent_session = _make_mock_puppet_session(istyping=False)
        self.char2.sessions.all.return_value = [self.char2_session, silent_session]
        is_typing_state(self.session, state=True)
        self.char2_session.msg.assert_called_once()
        silent_session.msg.assert_not_called()

    def test_no_audience_means_no_messages(self):
        """No messages are sent when there are no other characters in the room."""
        self.char2.location = self.room2
        is_typing_state(self.session, state=True)
        self.char2_session.msg.assert_not_called()

    def test_typing_message_includes_typer_name(self):
        """The broadcast message identifies the typer by name."""
        is_typing_state(self.session, state=True)
        payload = self.char2_session.msg.call_args.kwargs["is_typing"]["payload"]
        self.assertEqual(payload["name"], self.char1.name)
