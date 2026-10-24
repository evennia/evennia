"""
Guards on the promise that a player's personal data never reaches the server.

Blueprint section 2.3 forbids storing a player's notes, relationships, tags,
macros, layouts and the rest on the game server. Section 24 adds that a
relationship tag does not affect server-side social systems.

The behaviour is verified in a browser by `browser-qa/qa-local-data.js`, which
watches the command dispatcher while local data is created. What Python pins down
here is the *structural* half: the server-side code contains nothing capable of
receiving or storing this data in the first place.

That distinction matters. A behavioural test proves nothing was sent on the paths
it exercised; these tests prove there is nowhere for it to go.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import (
    AETOS_STATIC_DIR,
    inputfuncs,
    protocol,
)

CONTRIB_DIR = Path(AETOS_STATIC_DIR).parent
JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"

#: Categories of personal data the blueprint forbids storing server-side.
PERSONAL_DATA = (
    "notes",
    "relationships",
    "tags",
    "macros",
    "aliases",
    "triggers",
    "layouts",
    "workspaces",
    "themes",
    "keybindings",
    "map_notes",
    "map_pois",
)


def _strip_comments(source):
    """
    Remove JS comments.

    Assertions here are about executable code; the comments deliberately discuss
    the very things being forbidden.

    Args:
        source (str): JavaScript source.

    Returns:
        str: Source with comments removed.

    """
    without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", without_block, flags=re.MULTILINE)


class TestServerCannotReceivePersonalData(TestCase):
    """The server has no handler that accepts any of it."""

    def test_the_only_inputfuncs_are_the_protocol_ones(self):
        """
        Evennia treats every public function in the module as an inputfunc. A new
        one accepting notes or relationships would be a silent privacy hole, so
        the set is pinned.

        """
        public = [
            name
            for name in dir(inputfuncs)
            if not name.startswith("_") and callable(getattr(inputfuncs, name))
        ]
        aetos_handlers = [name for name in public if name.startswith("aetos_")]
        self.assertEqual(sorted(aetos_handlers), ["aetos_hello", "aetos_request_sync"])

    def test_no_protocol_message_carries_personal_data(self):
        """
        The wire format has no message for any of it. There is nothing to send
        even if a client tried.

        """
        names = [protocol.MSG_HELLO, protocol.MSG_MANIFEST, protocol.MSG_SYNC]
        names.extend(protocol.DELTA_MESSAGES)
        joined = " ".join(names)
        for category in ("note", "relationship", "macro", "alias", "trigger"):
            self.assertNotIn(category, joined, "protocol mentions %r" % category)


class TestServerStoresNothing(TestCase):
    """No model, no migration, no persistence."""

    def test_no_database_models(self):
        self.assertFalse((CONTRIB_DIR / "models.py").exists())
        self.assertFalse((CONTRIB_DIR / "migrations").exists())

    def test_no_python_module_writes_personal_data_to_attributes(self):
        """
        Writing to `.db.` or `.attributes.add` would persist data on the game's
        own objects, which is exactly what section 2.3 forbids.

        """
        offenders = []
        for path in CONTRIB_DIR.rglob("*.py"):
            if "tests" in path.parts:
                continue
            source = path.read_text(encoding="utf-8")
            for category in PERSONAL_DATA:
                if ".db.%s" % category in source:
                    offenders.append("%s writes .db.%s" % (path.name, category))
                if 'attributes.add("%s' % category in source:
                    offenders.append("%s writes attribute %s" % (path.name, category))
        self.assertEqual(offenders, [])

    def test_session_state_is_transient_only(self):
        """
        The handshake records the client's protocol and capabilities on the
        session, and since M26 also the set of unknown capabilities it has
        already logged, so a client cannot fill the game's log by repeating its
        handshake. All three are connection state that dies with the session,
        not a stored profile -- and they must stay that way.

        The assertion is an exact list rather than a search for anything
        suspicious, so adding a fourth is a deliberate act with a reason
        attached rather than something that slides in.

        """
        source = (CONTRIB_DIR / "inputfuncs.py").read_text(encoding="utf-8")
        stored = re.findall(r"session\.(\w+)\s*=", source)
        self.assertEqual(
            sorted(stored),
            ["aetos_capabilities", "aetos_logged_unknown", "aetos_protocol"],
        )


class TestLocalDataStaysClientSide(TestCase):
    """
    The client modules that own personal data cannot send it.

    A local menu action carries a `run` function rather than a `command`, so
    there is nothing for the command dispatcher to transmit. This is the
    structural guarantee behind the behavioural one.

    """

    def test_relationships_module_never_touches_the_transport(self):
        code = _strip_comments((JS_DIR / "relationships.js").read_text(encoding="utf-8"))
        for forbidden in ("Evennia.msg", "evennia.msg", "dispatcher", "WebSocket", "fetch("):
            self.assertNotIn(forbidden, code, "relationships.js references %r" % forbidden)

    def test_notes_module_never_touches_the_transport(self):
        code = _strip_comments((JS_DIR / "notes.js").read_text(encoding="utf-8"))
        for forbidden in ("Evennia.msg", "evennia.msg", "dispatcher", "WebSocket", "fetch("):
            self.assertNotIn(forbidden, code, "notes.js references %r" % forbidden)

    def test_local_data_is_stored_in_local_namespaces(self):
        relationships = (JS_DIR / "relationships.js").read_text(encoding="utf-8")
        notes = (JS_DIR / "notes.js").read_text(encoding="utf-8")
        self.assertIn('"relationships"', relationships)
        self.assertIn('"notes"', notes)

    def test_menu_distinguishes_local_from_server_actions(self):
        """
        A player marking someone an Enemy must not wonder whether the game was
        told. The menu separates the two groups and labels the local ones.

        """
        menu = (JS_DIR / "menu.js").read_text(encoding="utf-8")
        self.assertIn('role", "separator"', menu)
        self.assertIn("private to this browser", menu)

    def test_local_actions_run_rather_than_send(self):
        """
        The structural guarantee: a local action executes a function and never
        reaches the command path.

        """
        menu = _strip_comments((JS_DIR / "menu.js").read_text(encoding="utf-8"))
        self.assertIn('typeof action.run === "function"', menu)
