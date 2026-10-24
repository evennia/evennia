"""
Tests for M24 -- reconnect hardening.

Two defects, both of the same shape: the client presenting something as true
that it had no way to know was still true.

- A command typed during a disconnect was **reported as sent**. Evennia's
  transport does not buffer -- `websocket.send` on a closed socket throws or is
  dropped, and nothing is delivered on reconnect -- but `send()` called it
  unconditionally and returned `true` regardless.
- Every panel kept showing the last state it received, looking exactly as it
  did when that state was current.

The handshake already re-sent on reconnect (M4) and the command queue already
paused on disconnect (M12), so those are asserted here rather than added.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"
SHELL = (JS_DIR / "aetos.js").read_text(encoding="utf-8")
QUEUE = (JS_DIR / "queue.js").read_text(encoding="utf-8")
TEMPLATE = (Path(AETOS_STATIC_DIR).parent / "templates" / "webclient.html").read_text(
    encoding="utf-8"
)
CSS = (Path(AETOS_STATIC_DIR) / "aetos" / "css" / "aetos.css").read_text(encoding="utf-8")


def _function_body(source, signature, until):
    """
    Slice one function out of a module.

    Args:
        source (str): JavaScript source.
        signature (str): The line to start at.
        until (str): A later landmark that ends the window.

    Returns:
        str: The slice between them.

    """
    start = source.index(signature)
    return source[start : source.index(until, start)]


class TestACommandIsNeverReportedAsSentWhenItWasNot(TestCase):
    """
    The defect that mattered.

    Silently losing a command is bad; *claiming* to have sent it is worse,
    because it removes the player's chance to notice and retype.

    """

    def test_the_dispatcher_checks_the_connection(self):
        body = _function_body(SHELL, "function send(commandText)", "return { send: send };")
        self.assertIn('typeof settings.isConnected === "function"', body)
        self.assertIn("!settings.isConnected()", body)

    def test_it_returns_false_rather_than_true(self):
        body = _function_body(SHELL, "function send(commandText)", "return { send: send };")
        guard = body[body.index("settings.isConnected()") :]
        self.assertIn("return false;", guard[: guard.index("try {")])

    def test_a_socket_that_closes_mid_call_is_also_not_success(self):
        """
        The check and the call are not atomic. A throw between them is still
        not a delivered command.

        """
        body = _function_body(SHELL, "function send(commandText)", "return { send: send };")
        self.assertIn("try {", body)
        self.assertIn("catch (err)", body)

    def test_the_player_is_told(self):
        """
        A player who typed something and got no response assumes the game
        ignored them -- and on a slow dropout keeps typing, building up
        commands they believe are in flight.

        """
        body = _function_body(SHELL, "function sendCommand(text)", "requestSync();")
        self.assertIn("Not connected. That was not sent.", body)
        self.assertIn('priority: "important"', body)

    def test_nothing_queues_the_command_for_later(self):
        """
        Deliberate, not an omission.

        A player who typed "attack the dragon" during a thirty-second dropout
        may be somewhere else entirely when the socket returns, and replaying it
        would execute a decision they made about a situation that no longer
        exists. Saying it did not send leaves the choice with them.

        """
        body = _function_body(SHELL, "function send(commandText)", "return { send: send };")
        for buffering in ("pending.push", "backlog", "retry", "setTimeout"):
            self.assertNotIn(buffering, body, "the dispatcher buffers via %r" % buffering)

    def test_a_refused_command_is_not_recorded_as_sent(self):
        """
        Capture and the orientation trail both sit after the guard. A capture
        that recorded a refused command could not reproduce the session, and an
        orientation trail that did would tell a player they sent something they
        did not.

        """
        body = _function_body(SHELL, "function sendCommand(text)", "requestSync();")
        self.assertLess(body.index("return false;"), body.index("capture.recordOutbound"))
        self.assertLess(body.index("return false;"), body.index("orientation.observeCommand"))

    def test_an_unknown_state_does_not_block_the_first_command(self):
        """
        Refusing on "not yet known" would block the very first command of a
        session, before any connection event has arrived.

        """
        body = _function_body(SHELL, "isConnected: function ()", "});")
        self.assertIn('connection.state !== "closed"', body)
        self.assertIn("!connection ||", body)


class TestStaleStateIsMarkedAsStale(TestCase):
    """
    The moment a connection drops, every panel shows the world as it was --
    and looks exactly as it did when it was current.

    """

    def test_the_root_carries_a_stale_attribute(self):
        body = _function_body(
            SHELL, "function updateConnection(state)", 'emitter.on("connection_open"'
        )
        self.assertIn('"data-aetos-stale"', body)
        self.assertIn('state === "closed" ? "true" : "false"', body)

    def test_it_is_one_attribute_rather_than_sixteen_widgets(self):
        """
        The panels already render correctly; they are simply out of date.
        Restating that once in the frame is cheaper and more honest than making
        every widget invent its own way to say it.

        """
        self.assertEqual(SHELL.count('"data-aetos-stale"'), 1)

    def test_a_screen_reader_is_told_too(self):
        """
        `aria-describedby` rather than a live region: staleness is a *property*
        of what is on screen, not an event. The disconnection itself is
        announced once; this is what somebody hears when they navigate into a
        panel afterwards.

        """
        self.assertIn('aria-describedby="aetos-stale-notice"', TEMPLATE)
        self.assertIn('id="aetos-stale-notice"', TEMPLATE)

    def test_the_description_leaves_the_tree_when_connected(self):
        """
        `hidden`, not CSS. A description that is always present but sometimes
        false is worse than none.

        """
        self.assertIn("hidden", TEMPLATE[TEMPLATE.index('id="aetos-stale-notice"') :][:200])
        body = _function_body(
            SHELL, "function updateConnection(state)", 'emitter.on("connection_open"'
        )
        self.assertIn('notice.hidden = state !== "closed"', body)

    def test_the_visual_signal_is_not_the_only_signal(self):
        """
        "Slightly greyer" is not a message, and it is exactly the signal that
        disappears at high contrast, in bright sunlight, or for anyone whose
        perception of the difference is not the designer's.

        """
        self.assertIn("Not connected. Everything shown is the last state received.", TEMPLATE)

    def test_stale_panels_stay_readable(self):
        """
        Their content is the last thing the player was told and remains the
        best information they have. This says it is old, not worthless.

        """
        block = CSS[CSS.index('[data-aetos-stale="true"] .aetos-workspace {') :]
        block = block[: block.index("}")]
        opacity = re.search(r"opacity:\s*([\d.]+)", block)
        self.assertIsNotNone(opacity)
        self.assertGreater(float(opacity.group(1)), 0.6)


class TestWhatAlreadyWorked(TestCase):
    """
    Asserted rather than added. Both shipped earlier and both are load-bearing
    for a reconnect, so both are worth a test that would notice their removal.

    """

    def test_the_handshake_is_resent_on_every_open(self):
        """
        After a reconnect the server has no memory of this client's
        capabilities, and the reply is a fresh authoritative sync.

        """
        body = _function_body(
            SHELL, 'emitter.on("connection_open"', 'emitter.on("connection_close"'
        )
        self.assertIn("sendHello();", body)

    def test_the_hello_flag_is_cleared_on_close(self):
        """
        Otherwise the one-hello-per-connection guard would suppress the
        handshake on every reconnect after the first -- a client that came
        back connected but unknown to the server.

        """
        body = _function_body(SHELL, 'emitter.on("connection_close"', "/* --- Aetos protocol")
        self.assertIn("helloSent = false;", body)

    def test_a_running_queue_pauses_rather_than_failing(self):
        """
        A macro or route mid-flight when the connection drops must not fire its
        remaining commands into nothing.

        """
        self.assertIn("active.paused = true;", QUEUE)
        self.assertIn("Queued commands paused: disconnected.", QUEUE)

    def test_a_paused_queue_can_be_resumed(self):
        self.assertIn("active.paused = false;", QUEUE)

    def test_the_disconnection_itself_is_announced_as_critical(self):
        """
        The one category that interrupts. Everything the client is showing
        became potentially stale the moment it happened, so a player needs to
        know before they act on it.

        """
        body = _function_body(
            SHELL, "function updateConnection(state)", 'emitter.on("connection_open"'
        )
        self.assertIn('"Connection lost."', body)
        self.assertIn('priority: "critical"', body)

    def test_the_connection_state_reaches_the_capture(self):
        """
        A capture that did not record a dropout could not reproduce what the
        player actually experienced.

        """
        body = _function_body(
            SHELL, "function updateConnection(state)", 'emitter.on("connection_open"'
        )
        self.assertIn("capture.recordConnection(state)", body)
