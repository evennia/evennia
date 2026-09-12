"""
Tests for A7 -- AAC architecture and the simplified workspace.

Addendum A.51, A.59–A.69. Gate: A.94.

**Aetos does not claim AAC support, and these tests do not assert that it has
any.** A.94 requires somebody familiar with picture-supported communication to
review the concept organisation, the symbol assumptions, the sentence strip, the
terminology and the cognitive load before that claim is made. That review has
not happened, and it is logged in `questions.md`.

What is tested is everything that can be tested without that judgement: that the
model separates the four things A.60 says it must, that no W3C identifier is
invented, that no symbol is ever guessed, that nothing is generatively inferred,
that the strip is fully keyboard operable, that the preview cannot be bypassed,
and that what is sent is an ordinary command.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"


def _read(relative):
    """
    Read a client module.

    Args:
        relative (str): Path under the js directory.

    Returns:
        str: Contents.

    """
    return (JS_DIR / relative).read_text(encoding="utf-8")


def _code_only(source):
    """
    Strip comments, leaving only what executes.

    Args:
        source (str): JavaScript source.

    Returns:
        str: Source without comments.

    """
    without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", without_block, flags=re.MULTILINE)


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


CONCEPTS = _read("aac/concepts.js")
SYMBOLS = _read("aac/symbols.js")
BOARD = _read("aac/board.js")
WORKSPACES = _read("workspaces.js")
SHELL = _read("aetos.js")


class TestTheConceptModel(TestCase):
    """
    A.60. Four things, separated because they vary independently: what is
    meant, what is written, what is drawn, and what is sent.

    """

    def test_a_concept_carries_all_four_fields(self):
        body = _function_body(CONCEPTS, "function concept(id, label", "var CONCEPTS = [")
        for field in (
            "id:",
            "label:",
            "text:",
            "category:",
            "waiAdaptConcept:",
            "commandTemplate:",
        ):
            self.assertIn(field, body)

    def test_the_key_cap_and_the_speech_are_separate(self):
        """
        A key is a heading and reads better capitalised; a sentence is speech.
        Joining the labels produced `say I Want Help`, which is what somebody's
        every message would have looked like in public chat -- and looking like
        that is not a neutral cost for a player already using a board to be
        heard.

        """
        body = _function_body(CONCEPTS, "function concept(id, label", "var CONCEPTS = [")
        self.assertIn("text: text || label.toLowerCase()", body)

        sentence = _function_body(CONCEPTS, "function toText(concepts)", "window.AetosConcepts")
        self.assertIn("entry.text", sentence)
        self.assertNotIn("entry.label", sentence)

    def test_a_word_that_must_not_be_lower_cased_is_declared(self):
        """
        An English rule about one pronoun is not something to encode as
        cleverness. "I" is given explicitly.

        """
        self.assertIn('concept("i", "I", "people", null, "I")', CONCEPTS)

    def test_every_category_a65_names_is_present(self):
        block = CONCEPTS[CONCEPTS.index("var CATEGORIES = [") :]
        block = block[: block.index("\n    ];")]
        ids = set(re.findall(r'id: "(\w+)"', block))
        for required in (
            "common",
            "movement",
            "people",
            "actions",
            "social",
            "questions",
            "feelings",
            "objects",
        ):
            self.assertIn(required, ids, "A.65 names the %r category" % required)

    def test_the_urgent_words_are_in_the_first_category(self):
        """
        A player who has to page through six categories to say "stop" has been
        failed by the layout regardless of how good the symbols are.

        """
        block = CONCEPTS[CONCEPTS.index("var CONCEPTS = [") :]
        common = block[: block.index("// Movement")]
        for word in ('concept("yes"', 'concept("no"', 'concept("stop"', 'concept("help"'):
            self.assertIn(word, common)

    def test_concepts_a65_names_are_present(self):
        ids = set(re.findall(r'concept\("([\w-]+)"', CONCEPTS))
        for required in (
            "i",
            "you",
            "want",
            "need",
            "help",
            "yes",
            "no",
            "stop",
            "look",
            "go",
            "north",
            "south",
            "east",
            "west",
            "talk",
            "friend",
            "trade",
            "take",
            "give",
            "eat",
            "drink",
        ):
            self.assertIn(required, ids, "A.65 names the %r concept" % required)

    def test_no_combat_vocabulary_is_bundled(self):
        """
        A.65: only concepts with known meanings and appropriate mappings. The
        command for attacking is entirely game-specific, and a board sending
        `attack` to a game with no such command would fail silently at the
        moment somebody most needed it to work.

        """
        ids = set(re.findall(r'concept\("([\w-]+)"', CONCEPTS))
        for absent in ("attack", "kill", "fight", "flee", "cast"):
            self.assertNotIn(absent, ids)


class TestNoInventedIdentifiers(TestCase):
    """
    A.60: **Aetos MUST NOT invent W3C concept IDs.**

    An identifier is a claim that this concept *is* that published concept.
    Aetos has no way to verify one, and a plausible-looking invented ID would be
    worse than none -- it would propagate into other tools as though it had been
    checked.

    """

    def test_every_bundled_concept_declares_a_null_identifier(self):
        body = _function_body(CONCEPTS, "function concept(id, label", "var CONCEPTS = [")
        self.assertIn("waiAdaptConcept: null", body)

    def test_no_concept_overrides_it_with_a_value(self):
        code = _code_only(CONCEPTS)
        self.assertEqual(code.count("waiAdaptConcept"), 1)

    def test_the_attribute_is_only_emitted_when_one_exists(self):
        """
        A.61. Emits nothing today, and is here so a pack or a game supplying
        verified ids gets the attribute for free -- and so nobody adds invented
        ids later to make the attribute appear.

        """
        body = _function_body(BOARD, "function conceptButton(concept)", "function renderStrip")
        self.assertIn("if (concept.waiAdaptConcept)", body)
        self.assertIn('button.setAttribute("adapt-symbol", concept.waiAdaptConcept)', body)


class TestNoGenerativeInference(TestCase):
    """
    A.69, a hard MUST NOT. Mappings are deterministic.

    A system that speaks *for* somebody has to be one they can predict
    completely -- otherwise it is putting words in their mouth, which is the
    specific harm AAC exists to prevent.

    """

    def test_text_is_the_labels_joined_and_nothing_else(self):
        """
        No grammar, no conjugation, no inserted articles, no reordering. "I want
        help" is what the player built. A system that produced "I would like
        some help, please" would, the first time it guessed wrong, have said
        something they did not mean, in public, under their name.

        """
        body = _function_body(CONCEPTS, "function toText(concepts)", "window.AetosConcepts")
        self.assertIn('.join(" ")', body)
        for cleverness in ("conjugate", "grammar", "pluralize", "article", "rewrite"):
            self.assertNotIn(cleverness, body.lower())

    def test_nothing_predicts_the_next_concept(self):
        code = _code_only(BOARD) + _code_only(CONCEPTS)
        for guessing in ("predict", "suggest", "autocomplete", "infer", "likely"):
            self.assertNotIn(guessing, code.lower(), "AAC must not %r" % guessing)

    def test_no_network_or_model_calls(self):
        for name, source in (
            ("concepts.js", CONCEPTS),
            ("board.js", BOARD),
            ("symbols.js", SYMBOLS),
        ):
            for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon"):
                self.assertNotIn(forbidden, source, "%s uses %r" % (name, forbidden))


class TestSymbols(TestCase):
    """A.62, A.63, A.64."""

    def test_no_artwork_is_bundled(self):
        """
        A.63. The symbol sets AAC users actually know are licensed, and "it is
        for accessibility" is not a licence. Shipping them unverified would
        expose every game installing this contrib to somebody else's copyright
        claim.

        """
        aac_dir = JS_DIR / "aac"
        images = [
            path.name
            for path in aac_dir.iterdir()
            if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
        ]
        self.assertEqual(images, [], "the contrib bundles symbol artwork")

    def test_a_pack_without_a_licence_is_refused(self):
        """
        Refused rather than defaulted. A pack with no stated licence is one
        nobody can safely pass on, and a default of "unknown" would let it
        spread anyway with the question quietly settled in the worst direction.

        """
        body = _function_body(SYMBOLS, "function registerPack(pack)", "function usePack")
        self.assertIn("if (!pack.license)", body)
        self.assertIn("will not install", body)

    def test_a_missing_symbol_returns_null_and_never_a_substitute(self):
        """
        A.62: never guess a replacement. A symbol *is* the word for somebody
        using one -- substituting a near-miss is substituting a different word,
        and the player has no way to know it happened.

        """
        body = _function_body(SYMBOLS, "function getSymbol(concept)", "function activePack")
        self.assertIn("return null;", body)
        code = _code_only(body)
        for guessing in ("similar", "fallbackSymbol", "placeholder", "nearest", "default.png"):
            self.assertNotIn(guessing, code)

    def test_a_symbol_always_has_an_accessible_name(self):
        body = _function_body(SYMBOLS, "function getSymbol(concept)", "function activePack")
        self.assertIn("found.alt || concept.label", body)

    def test_a_pack_cannot_change_what_a_concept_says(self):
        """
        A pack's wording is the image's alternative text, never the label. The
        label is what the player is choosing, and it must not change depending
        on which pack is installed.

        """
        code = _code_only(
            _function_body(SYMBOLS, "function registerPack(pack)", "function usePack")
        )
        # Comments stripped: the block necessarily *explains* that it does not
        # touch the label, so a bare search fails the file for documenting
        # itself. Ninth instance of that mistake here; the M17 rule holds --
        # anchor on an access, not a word.
        self.assertIn("alt:", code)
        self.assertNotIn("label", code)
        self.assertNotIn("entry.label", code)

    def test_symbol_sources_are_checked(self):
        """
        A pack is a file from somewhere, and `javascript:` in a `src` runs with
        the client's full privileges.

        """
        body = _function_body(SYMBOLS, "function isSafeSource(value)", "function createProvider")
        # The slash is escaped inside the regex literal, so the source reads
        # `data:image\/` rather than `data:image/`.
        self.assertIn(r"data:image\/", body)
        self.assertIn("base64", body)
        self.assertIn(r'indexOf("\\")', body)

    def test_symbol_and_text_by_default(self):
        """
        A.64. A symbol nobody recognises with no word under it is unusable,
        while the reverse is merely plain.

        """
        preferences = _read("accessibility/preferences.js")
        self.assertIn("showTextWithSymbols: true", preferences)

    def test_the_label_is_shown_when_there_is_no_symbol(self):
        body = _function_body(BOARD, "function conceptButton(concept)", "function renderStrip")
        self.assertIn("if (showText() || !symbol)", body)

    def test_the_symbol_is_not_announced_twice(self):
        """
        Otherwise a screen reader reads the word from the image and again from
        the text, which on a board of sixty keys is sixty duplications.

        """
        body = _function_body(BOARD, "function conceptButton(concept)", "function renderStrip")
        self.assertIn('image.alt = showText() ? "" : symbol.alt', body)


class TestTheSentenceStripIsKeyboardOperable(TestCase):
    """
    A.66. Drag-and-drop MAY exist visually but MUST NOT be required.

    """

    def test_every_required_operation_exists(self):
        for operation in (
            "function add(conceptId)",
            "function removeAt(index)",
            "function move(index, offset)",
            "function clear()",
            "function preview()",
            "function send(command)",
        ):
            self.assertIn(operation, BOARD, "A.66 requires %s" % operation)

    def test_drag_and_drop_is_not_implemented_at_all(self):
        """
        Permitted as an addition, forbidden as a requirement. The population
        most likely to use a communication board includes people for whom
        dragging is difficult or impossible, and building the pointer version
        first is how a keyboard path ends up as an afterthought nobody tests.

        """
        code = _code_only(BOARD)
        for pointer_only in ("draggable", "dragstart", "dragover", "ondrop", "mousedown"):
            self.assertNotIn(pointer_only, code, "board.js uses %r" % pointer_only)

    def test_every_strip_control_is_a_button(self):
        body = _function_body(BOARD, "function renderStrip()", "function renderGrid")
        self.assertIn('button.type = "button"', body)

    def test_strip_controls_name_the_word_they_act_on(self):
        """
        "Left" repeated five times down a strip is indistinguishable when tabbed
        through, and this is the surface where getting the wrong one means
        saying something you did not mean.

        """
        body = _function_body(BOARD, "function renderStrip()", "function renderGrid")
        self.assertIn('control.action + ": " + concept.label', body)

    def test_the_strip_comes_before_the_board_in_reading_order(self):
        """
        The sentence being built is the thing a player needs to check. Putting
        sixty keys before it means tabbing past all of them to reach what you
        just said.

        """
        body = _function_body(BOARD, "mount: function (context)", "destroy: function ()")
        self.assertLess(body.index("stripSection"), body.index("aetos-aac__grid"))

    def test_word_order_can_be_corrected(self):
        """
        "You give me" and "me give you" are different sentences.

        """
        body = _function_body(BOARD, "function move(index, offset)", "function clear()")
        self.assertIn("strip[index] = strip[target]", body)

    def test_the_strip_is_bounded(self):
        self.assertIn("MAX_STRIP", BOARD)
        self.assertIn("strip.length >= MAX_STRIP", BOARD)


class TestOutputSafety(TestCase):
    """
    A.67. The preview exists because a wrong concept-to-text mapping would
    otherwise speak for the player, in public, under their name, without them
    seeing what was said.

    """

    def test_sending_always_goes_through_the_preview(self):
        body = _function_body(BOARD, "function preview()", "function editText")
        self.assertIn("dialog.open({", body)
        self.assertIn("onSubmit: function () {", body)

    def test_the_preview_shows_the_exact_command(self):
        body = _function_body(BOARD, "function preview()", "function editText")
        self.assertIn("shown.textContent = command", body)
        self.assertIn("exactly as written", body)

    def test_all_three_choices_are_offered(self):
        body = _function_body(BOARD, "function preview()", "function editText")
        self.assertIn('submitLabel: "Send"', body)
        self.assertIn('label: "Edit text"', body)

    def test_editing_is_offered_because_the_player_is_the_authority(self):
        """
        A board is a keyboard, not a translator.

        """
        self.assertIn("function editText(command)", BOARD)
        body = _function_body(BOARD, "function editText(command)", "function send(command)")
        self.assertIn("Change anything you like", body)

    def test_nothing_is_sent_when_there_is_no_way_to_preview(self):
        """
        Send nothing rather than send unseen.

        """
        body = _function_body(BOARD, "function preview()", "function editText")
        self.assertIn("if (!dialog)", body)
        window = body[body.index("if (!dialog)") :]
        self.assertIn("return null;", window[: window.index("var body")])

    def test_a_failed_send_keeps_the_sentence(self):
        """
        A board that cleared itself on a failed send would have thrown away a
        sentence somebody spent a minute building.

        """
        body = _function_body(BOARD, "function send(command)", "/* --- Rendering")
        self.assertIn("if (sent) {", body)
        self.assertIn("still here", body)


class TestServerAuthority(TestCase):
    """
    A.68 and blueprint 2.4. AAC composition generates normal game input.

    """

    def test_the_board_sends_through_the_single_outbound_seam(self):
        body = _function_body(
            SHELL, "window.AetosBoard.createWidget({", "registry.register(aacBoard)"
        )
        self.assertIn("sendCommand: function (text) { return sendCommand(text); }", body)

    def test_the_board_never_reaches_the_transport(self):
        """
        A board that bypassed a mute would be a board that got somebody into
        trouble for a sentence the game had already refused.

        """
        for forbidden in ("Evennia.msg", "dispatcher", "emitter"):
            self.assertNotIn(forbidden, BOARD, "board.js uses %r" % forbidden)

    def test_the_command_is_ordinary(self):
        body = _function_body(BOARD, "function buildCommand()", "function preview()")
        self.assertIn('preferences.value("aac.sayCommand", "say")', body)

    def test_a_direction_is_sent_as_movement_not_as_speech(self):
        """
        "North" means go north, not say the word "north".

        """
        body = _function_body(BOARD, "function buildCommand()", "function preview()")
        self.assertIn("strip[0].commandTemplate", body)

    def test_the_server_is_never_told_the_player_uses_aac(self):
        """
        A.68. The server does not need an AAC subsystem and is not
        automatically informed.

        """
        for probe in ("aac", "AAC"):
            protocol = (Path(AETOS_STATIC_DIR).parent / "protocol.py").read_text(encoding="utf-8")
            self.assertNotIn(probe, protocol)


class TestTheSimplifiedWorkspace(TestCase):
    """
    A.51. **Not an inferior client** -- a simplified presentation of the same
    underlying capabilities.

    """

    def test_it_removes_nothing(self):
        """
        A "simple mode" that quietly removed functionality would be making a
        decision about what somebody is capable of, on the basis of them having
        asked for a calmer screen. Those are not the same request.

        """
        body = _function_body(
            WORKSPACES, "function applySimplifiedLayout()", "/* --- Keyboard bindings"
        )
        self.assertIn("still in the command palette", body)
        for disabling in ("setEnabled(false)", "disable", "remove from registry"):
            self.assertNotIn(disabling, body)

    def test_it_only_places_what_the_game_actually_has(self):
        """
        A layout that added a map panel to a game with no map would be six
        panels of which one is permanently empty -- worse than five, and
        precisely the confusion the layout removes.

        """
        body = _function_body(
            WORKSPACES, "function applySimplifiedLayout()", "/* --- Keyboard bindings"
        )
        self.assertIn("registry.available(manifest)", body)
        self.assertIn("offered.indexOf(id) !== -1", body)

    def test_the_panels_match_what_a51_names(self):
        block = WORKSPACES[WORKSPACES.index("var SIMPLIFIED_WIDGETS = [") :]
        block = block[: block.index("];")]
        ids = set(re.findall(r'"(\w+)"', block))
        self.assertEqual(ids, {"people", "map", "state", "aac"})

    def test_it_is_reachable_from_the_palette(self):
        self.assertIn('"layout.simplified"', SHELL)

    def test_it_is_distinct_from_focus_mode(self):
        """
        Focus Mode is a temporary quieting; this is a layout somebody might use
        permanently.

        """
        self.assertIn('"focus.toggle"', SHELL)
        self.assertIn('"layout.simplified"', SHELL)


class TestTheClaimIsNotMade(TestCase):
    """
    A.94: do not claim useful AAC support until an AAC practitioner has
    reviewed it. **Do not claim AAC expertise solely from standards
    compliance.**

    This test exists so that writing the claim requires deleting a test that
    says why not.

    """

    def test_the_source_says_what_has_not_happened(self):
        self.assertIn("NOT REVIEWED AAC SUPPORT", BOARD)
        self.assertIn("A.94", CONCEPTS)

    def test_the_open_review_is_recorded(self):
        questions = (
            Path(AETOS_STATIC_DIR).parent.parent.parent.parent.parent.parent / "questions.md"
        )
        if not questions.is_file():
            self.skipTest("questions.md lives in the published repo, not the contrib")
        self.assertIn("AAC", questions.read_text(encoding="utf-8"))

    def test_the_help_topic_does_not_claim_support(self):
        help_source = _read("help.js")
        for claim in ("full AAC support", "AAC support for", "we support AAC"):
            self.assertNotIn(claim, help_source)


class TestReachability(TestCase):
    """A.97."""

    def test_the_modules_are_loaded_in_dependency_order(self):
        template = (Path(AETOS_STATIC_DIR).parent / "templates" / "webclient.html").read_text(
            encoding="utf-8"
        )
        for module in ("aac/concepts.js", "aac/symbols.js", "aac/board.js"):
            self.assertIn(module, template)
        self.assertLess(template.index("aac/concepts.js"), template.index("aac/board.js"))
        self.assertLess(template.index("aac/symbols.js"), template.index("aac/board.js"))

    def test_the_board_declares_a_widget_contract(self):
        for field in (
            'landmarkLabel: "Picture communication"',
            "heading:",
            "keyboardOperable: true",
            "liveUpdates: false",
        ):
            self.assertIn(field, BOARD)

    def test_the_board_is_in_the_palette(self):
        for command in ('"aac.clear"', '"aac.send"'):
            self.assertIn(command, SHELL)

    def test_the_keys_meet_the_enhanced_target_size(self):
        """
        A.57 asks for 44x44 wherever practical, and this is the surface where
        it matters most: a mis-tap here does not mean a wasted click, it means
        saying the wrong word.

        """
        css = (Path(AETOS_STATIC_DIR) / "aetos" / "css" / "aetos.css").read_text(encoding="utf-8")
        block = css[css.index(".aetos-aac__key {") :]
        block = block[: block.index("}")]
        self.assertIn("min-width: 44px", block)
        self.assertIn("min-height: 44px", block)

    def test_the_word_grid_has_a_role_to_carry_its_label(self):
        """
        `aria-label` on a plain <div> is prohibited and, worse, silently
        ignored -- the grid was simply unlabelled and the only sign was axe
        reporting `aria-prohibited-attr` as *incomplete* rather than as a
        violation.

        A group is right for buttons in a container. The same role on a <ul>
        would orphan its list items, which this client has got wrong twice.

        """
        body = _function_body(BOARD, "mount: function (context)", "destroy: function ()")
        start = body.index('gridEl.className = "aetos-aac__grid"')
        window = body[start : body.index("renderStrip();", start)]
        self.assertIn('gridEl.setAttribute("role", "group")', window)
        self.assertLess(window.index('"role", "group"'), window.index('"aria-label", "Words"'))

    def test_the_strip_is_a_list_and_keeps_its_semantics(self):
        """
        A <ul> takes `aria-label` without a role, and must not be given one.

        """
        body = _function_body(BOARD, "mount: function (context)", "destroy: function ()")
        start = body.index('stripEl.className = "aetos-aac__strip"')
        window = body[start : body.index("actions", start)]
        self.assertIn('stripEl.setAttribute("aria-label", "Your sentence")', window)
        self.assertNotIn('stripEl.setAttribute("role"', window)

    def test_the_category_state_is_not_shown_by_colour_alone(self):
        body = _function_body(BOARD, "mount: function (context)", "destroy: function ()")
        self.assertIn('"aria-pressed"', body)


class TestSymbolPackMappings(TestCase):
    """
    A.63 draws the line precisely: "Concept identifiers and mappings may be
    bundled where legally permitted. Symbol imagery requires explicit licensing
    review."

    So Aetos ships mappings and a builder, and never artwork.

    """

    def _mappings_dir(self):
        """
        Locate the bundled mapping files.

        Returns:
            Path: The `aac_mappings` directory.

        """
        return Path(AETOS_STATIC_DIR).parent / "aac_mappings"

    def test_mappings_are_bundled(self):
        files = sorted(self._mappings_dir().glob("*.json"))
        self.assertTrue(files, "no concept mappings are bundled")

    def test_no_artwork_is_bundled_anywhere_in_the_contrib(self):
        """
        The check that matters. Not "we did not add images this time" but "the
        contrib contains none".

        """
        root = Path(AETOS_STATIC_DIR).parent
        images = [
            str(path.relative_to(root))
            for path in root.rglob("*")
            if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
        ]
        self.assertEqual(images, [], "the contrib bundles image files: %s" % images)

    def test_every_mapping_states_its_licence_and_attribution(self):
        """
        A mapping without them is one nobody can safely act on: the whole point
        is to tell an installer what terms they are accepting.

        """
        import json

        for path in self._mappings_dir().glob("*.json"):
            mapping = json.loads(path.read_text(encoding="utf-8"))
            for field in (
                "set",
                "name",
                "license",
                "attribution",
                "source",
                "path_template",
                "concepts",
            ):
                self.assertIn(field, mapping, "%s lacks %r" % (path.name, field))
            self.assertTrue(mapping["attribution"].strip())

    def test_mapped_concepts_all_exist(self):
        """
        A mapping naming a concept Aetos does not have is dead weight that
        looks like coverage.

        """
        import json

        known = set(re.findall(r'concept\("([\w-]+)"', CONCEPTS))
        for path in self._mappings_dir().glob("*.json"):
            mapping = json.loads(path.read_text(encoding="utf-8"))
            unknown = set(mapping["concepts"]) - known
            self.assertEqual(
                unknown, set(), "%s maps unknown concepts %s" % (path.name, sorted(unknown))
            )

    def test_the_mulberry_coverage_gap_is_documented_not_hidden(self):
        """
        Mulberry is a vocabulary set, not a core board: it has no `yes`, `no`,
        `stop`, `please`, `thank you`, `sorry` or `friend`.

        That gap is the reason it is not bundled, and it is recorded in the
        mapping itself so nobody later concludes the mapping is simply
        unfinished and "completes" it by guessing.

        """
        import json

        path = self._mappings_dir() / "mulberry.json"
        if not path.is_file():
            self.skipTest("no mulberry mapping")
        mapping = json.loads(path.read_text(encoding="utf-8"))
        comment = " ".join(mapping.get("_comment", []))
        self.assertIn("COVERAGE IS PARTIAL", comment)
        for absent in ("yes", "no", "stop", "please"):
            self.assertNotIn(
                absent,
                mapping["concepts"],
                "mulberry.json claims a %r symbol that does not exist" % absent,
            )


class TestPackImport(TestCase):
    """Installing a pack, and being told what it does and does not cover."""

    def test_a_pack_is_imported_from_a_local_file(self):
        """
        Aetos does not download symbol sets on a player's behalf: which set is
        appropriate depends on the game's licensing and on which symbols that
        person already knows, and neither is Aetos's decision.

        """
        self.assertIn("function importPack(text)", SYMBOLS)
        body = _function_body(SYMBOLS, "function importPack(text)", "function missingConcepts")
        self.assertIn("JSON.parse(text)", body)
        for forbidden in ("fetch(", "XMLHttpRequest", "import(", "src ="):
            self.assertNotIn(forbidden, body, "importPack uses %r" % forbidden)

    def test_an_import_reports_what_it_refused(self):
        """
        An import that silently drops half a pack is worse than one that fails,
        because the board then has holes the player discovers one word at a
        time.

        """
        body = _function_body(SYMBOLS, "function importPack(text)", "function missingConcepts")
        self.assertIn("refused:", body)
        self.assertIn("accepted:", body)

    def test_missing_concepts_are_surfaced_up_front(self):
        """
        A pack covering everything except `yes`, `no` and `stop` is a specific
        and predictable failure, and a player deserves to see it before they
        rely on the board mid-conversation.

        """
        self.assertIn("function missingConcepts()", SYMBOLS)
        body = _function_body(SYMBOLS, "function missingConcepts()", "function activePack")
        self.assertIn("!pack.symbols[concept.id]", body)

    def test_whether_a_pack_phones_home_is_reported(self):
        """
        A pack of remote URLs tells whoever hosts them, every time the board
        renders, that this browser is showing a communication board -- a
        disclosure about disability, made silently, to a third party the player
        never chose to tell.

        """
        self.assertIn("selfContained:", SYMBOLS)
        self.assertIn("packSelfContained:", SYMBOLS)
        body = _function_body(SYMBOLS, "selfContained: Object.keys(symbols)", "symbols: symbols")
        self.assertIn('indexOf("data:") === 0', body)

    def test_the_correction_is_kept_rather_than_quietly_replaced(self):
        """
        An earlier version of this module asserted that the major AAC symbol
        sets are all restrictively licensed. That was wrong -- Mulberry is
        CC BY-SA 4.0 and permits commercial use.

        The correction stays in the source because the wrong reason produced
        the right decision, and that is exactly how a bad assumption survives
        long enough to be repeated somewhere it matters.

        """
        self.assertIn("That was wrong", SYMBOLS)
        self.assertIn("CC BY-NC-SA", SYMBOLS)
        self.assertIn("CC BY-SA 4.0", SYMBOLS)
