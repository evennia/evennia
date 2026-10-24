"""
Tests for the raw-markup defect Gary reported while running a macro.

**The symptom.** Lines of game output appeared in the client as literal markup::

    <span class="color-002"><a id="mxplink" href="#" onclick="Evennia.msg(...)
    ">setres</a>

**The cause.** The canonical event carried one text field, `originalText`, which
is what the server sent -- markup included, because Evennia renders ANSI colour
to HTML server-side. The console's sanitiser handles that correctly. Four other
places did not:

- **Display rules** matched, substituted and computed highlight offsets against
  the markup. The console then renders `displayText` with `textContent`, on the
  documented assumption that it is plain -- so the moment any rule touched a
  coloured line, the player was shown the tags.
- **The history panel** assigned `originalText` to `textContent`
  unconditionally, so *every* coloured line showed as markup there.
- **History search** matched the markup: "span" matched every coloured line,
  while a word split by a colour change matched none.
- **Review Mode's announcement** included the markup, so a screen reader read
  "span class equals color hyphen zero zero two" before each line.

Triggers were the one place that got it right, and their comment says why:
"matching against HTML would make a player's pattern depend on colour codes they
never see". The rest of the client had the same requirement and each place
either solved it separately or not at all.

**The fix.** Derive the plain rendering once, in `normalize`, and carry it on the
canonical event as `plainText`. `originalText` is unchanged and is still what the
console sanitises. Everything that *matches or displays text as text* now reads
the same string by construction, rather than by several implementations
happening to agree.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"
SHELL = (JS_DIR / "aetos.js").read_text(encoding="utf-8")
LOG = (JS_DIR / "events" / "canonical_log.js").read_text(encoding="utf-8")
PIPELINE = (JS_DIR / "events" / "pipeline.js").read_text(encoding="utf-8")
RULES = (JS_DIR / "presentation" / "rules.js").read_text(encoding="utf-8")
HISTORY = (JS_DIR / "history.js").read_text(encoding="utf-8")
REVIEW = (JS_DIR / "events" / "review.js").read_text(encoding="utf-8")


def _slice(source, start, end):
    """
    The source between two landmarks.

    Character-count windows were used here first, and three of them broke the
    moment the code inside them gained an explanatory comment -- the assertion
    was still true and the window no longer reached it. A landmark cannot drift
    that way.

    Args:
        source (str): Source to slice.
        start (str): Landmark to start at.
        end (str): Landmark to stop before.

    Returns:
        str: The slice between them.

    """
    begin = source.index(start)
    return source[begin : source.index(end, begin)]


class TestTheEventCarriesBothForms(TestCase):
    """
    One record, two renderings of it -- not two records.

    """

    def test_the_log_keeps_the_markup_untouched(self):
        """
        `originalText` is the permanent record and this defect did not change
        it. The console still sanitises that, which is what preserves colour.

        """
        self.assertIn('originalText: entry.originalText || ""', LOG)

    def test_the_log_also_keeps_a_plain_rendering(self):
        self.assertIn("plainText: entry.plainText === undefined", LOG)

    def test_an_event_with_no_plain_form_falls_back_to_the_markup(self):
        """
        For a line with no markup the two strings are identical, so the
        fallback is correct rather than merely safe.

        """
        window = LOG[LOG.index("plainText: entry.plainText === undefined") :][:200]
        self.assertIn('entry.originalText || ""', window)

    def test_a_reader_actually_receives_it(self):
        """
        The gap that made the original fix not work.

        `append` stored `plainText` and `copy` -- the function every reader goes
        through, because the log hands out copies rather than its own records --
        had an explicit field list that did not include it. So every consumer
        got an event without one and fell back to the markup, and the history
        panel went on showing `<span class="color-012">` for a whole milestone
        after this was called fixed.

        The M29 tests checked the write path and the helper functions. Nothing
        checked what a reader ends up holding, which is the only thing that
        matters. Found by looking at a screenshot.

        """
        block = LOG[LOG.index("function copy(event)") :]
        block = block[: block.index("\n        }")]
        self.assertIn("plainText: event.plainText", block)

    def test_every_field_append_stores_survives_the_copy(self):
        """
        Generalised, because the specific bug will not recur and the shape will.
        Any field the record carries and the copy drops is invisible to every
        reader.

        """
        stored = set(
            re.findall(r"^\s{16}(\w+):", LOG[LOG.index("function append(entry)") :][:1800], re.M)
        )
        copied = set(
            re.findall(r"^\s{16}(\w+):", LOG[LOG.index("function copy(event)") :][:900], re.M)
        )
        self.assertTrue(stored, "could not read the stored fields")
        missing = stored - copied
        self.assertEqual(missing, set(), "copy() drops fields append() stores: %s" % missing)

    def test_the_pipeline_carries_it_on_both_paths(self):
        """
        Including the path taken when no canonical log is configured, which is
        the one that gets forgotten.

        """
        self.assertIn("normalized.plainText = normalized.originalText", PIPELINE)
        self.assertIn("plainText: normalized.plainText", PIPELINE)


class TestItIsDerivedOnceAndOnlyWhenNeeded(TestCase):
    """
    The alternative -- each consumer stripping markup for itself -- is what
    produced the defect.

    """

    def test_the_shell_derives_it_at_normalize(self):
        body = _slice(SHELL, "normalize: function (validated)", "applyState:")
        self.assertIn("sanitizeHtml(text)", body)
        self.assertIn("holder.textContent", body)
        self.assertIn("plainText: plain", body)

    def test_a_line_with_no_markup_is_not_parsed(self):
        """
        M25 took a DOM round trip off the per-line path. Doing one here for
        every line would put it straight back, and the great majority of lines
        contain no markup at all.

        """
        body = _slice(SHELL, "normalize: function (validated)", "applyState:")
        self.assertIn('text.indexOf("<") !== -1', body)

    def test_triggers_use_the_shared_derivation(self):
        """
        They were already right, and separately. Now they read the same field
        as everything else, so the two cannot drift apart again.

        """
        self.assertIn("triggers.onText(event.plainText", SHELL)
        self.assertNotIn("plain.appendChild(sanitizeHtml(event.originalText))", SHELL)


class TestEveryPlaceThatShowsTextAsTextUsesIt(TestCase):
    """
    The four places that did not.

    """

    def test_display_rules_match_what_the_player_can_see(self):
        body = _slice(RULES, "function present(event, activeGroups)", "rules.forEach")
        self.assertIn("event.plainText === undefined", body)
        self.assertNotIn(
            'var text = String(event.originalText || "")',
            body,
            "display rules still match the markup",
        )

    def test_the_history_panel_renders_words_rather_than_tags(self):
        self.assertIn("body.textContent = displayable(event);", HISTORY)
        self.assertNotIn("body.textContent = event.originalText", HISTORY)

    def test_history_search_matches_words_rather_than_tags(self):
        self.assertIn("displayable(event).toLowerCase()", HISTORY)
        self.assertNotIn("event.originalText.toLowerCase()", HISTORY)

    def test_review_mode_announces_words_rather_than_tags(self):
        """
        The accessibility half of the defect. A screen reader in Review Mode was
        reading the tag names aloud before every coloured line.

        """
        self.assertIn("readable(event)", REVIEW)
        self.assertNotIn("event.originalText.toLowerCase()", REVIEW)

    def test_each_helper_falls_back_rather_than_failing(self):
        """
        An event from a capture recorded before this existed has no `plainText`.
        Replaying one must not produce empty rows.

        """
        for name, source in (("history.js", HISTORY), ("review.js", REVIEW)):
            self.assertIn(
                "event.plainText === undefined",
                source,
                "%s does not handle an event without plainText" % name,
            )


class TestTheConsoleStillShowsColour(TestCase):
    """
    The fix must not become "strip the markup everywhere", which would throw
    away the colour the game sent.

    """

    def test_the_console_is_still_handed_the_markup(self):
        self.assertIn("consoleWidget.append(event.originalText, null, presentation)", SHELL)

    def test_and_still_sanitises_it_rather_than_printing_it(self):
        body = _slice(
            SHELL, "function append(content, className, presentation)", "pending.push(line);"
        )
        self.assertIn("line.appendChild(sanitizeHtml(content))", body)

    def test_the_substituted_and_highlighted_branches_are_plain_by_design(self):
        """
        Both assign or measure `displayText`, which is now genuinely plain. The
        comment in the console said the offsets were "computed against plain
        text"; until this fix that was a description of the intent rather than
        of the code.

        """
        body = _slice(
            SHELL, "function append(content, className, presentation)", "pending.push(line);"
        )
        self.assertIn("line.textContent = display.displayText", body)
        self.assertIn("renderHighlighted(", body)


class TestTheConsoleStillDrawsColour(TestCase):
    """
    The worst defect this work produced, and it was mine.

    The console chose between "draw the sanitised markup" and "draw the
    substituted plain text" by comparing `displayText` with the original. That
    comparison was only ever meaningful while the two started out as the same
    string. Once `displayText` became the *plain* rendering, they differed on
    every line carrying any markup at all -- so the console treated every
    coloured line as substituted and drew it as text.

    **The client lost ANSI colour entirely, on every line, for a whole
    milestone.** No test noticed, because every one of them asserts on text and
    the text was right. Gary found it in a screenshot, where the giveaway was
    not the missing colour but the words: "need" and "help" welded together
    where a `<br>` used to be.

    """

    def test_a_substitution_is_stated_rather_than_inferred(self):
        self.assertIn("substituted: false", RULES)
        self.assertIn("result.substituted = replaced !== result.displayText;", RULES)

    def test_the_console_asks_whether_a_rule_rewrote_the_line(self):
        body = _slice(
            SHELL, "function append(content, className, presentation)", "pending.push(line);"
        )
        self.assertIn("display.substituted && display.displayText !== undefined", body)

    def test_it_no_longer_compares_the_two_texts(self):
        """
        The comparison is the defect. Keeping it anywhere in this branch would
        let it come back the next time somebody edits around it.

        """
        body = _slice(
            SHELL, "function append(content, className, presentation)", "pending.push(line);"
        )
        self.assertNotIn("display.displayText !== content", body)

    def test_an_untouched_line_still_goes_through_the_sanitiser(self):
        """
        Which is what preserves the colour: the markup is rebuilt from the
        allowlist rather than printed.

        """
        body = _slice(
            SHELL, "function append(content, className, presentation)", "pending.push(line);"
        )
        self.assertIn("line.appendChild(sanitizeHtml(content))", body)


class TestThePlainRenderingKeepsLineBreaks(TestCase):
    """
    `<br>` contributes no text, so `textContent` alone welds the words on either
    side of it together. A room description became one run-on paragraph, and
    "if you need<br>help" read as "needhelp".

    """

    def test_breaks_become_newlines_before_the_text_is_taken(self):
        body = _slice(SHELL, "normalize: function (validated)", "applyState:")
        self.assertIn('querySelectorAll("br")', body)
        self.assertIn('createTextNode("\\n")', body)

    def test_the_replacement_happens_before_textcontent_is_read(self):
        """
        Order is the whole fix: reading first and replacing after would change
        nothing.

        """
        body = _slice(SHELL, "normalize: function (validated)", "applyState:")
        self.assertLess(
            body.index('querySelectorAll("br")'), body.index("plain = holder.textContent")
        )

    def test_a_newline_rather_than_a_space(self):
        """
        The break carried structure. The history panel and a braille display
        both want the line to end there, not to run on with a space in it.

        """
        body = _slice(SHELL, "normalize: function (validated)", "applyState:")
        self.assertNotIn('createTextNode(" ")', body)
