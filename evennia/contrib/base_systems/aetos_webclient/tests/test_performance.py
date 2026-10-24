"""
Tests for M25 -- performance hardening.

Two defects on the hot path, both found by measuring rather than by reading, and
both with the same cause: work whose cost grew with the length of the session,
done once per line of game output.

- **The console forced a layout per line.** `append` read `scrollHeight`, added
  a node, then wrote `scrollTop` -- interleaved, that makes the browser lay out
  the entire scrollback for every line. Measured against a full 5000-line
  console it cost **68ms per line**, so a 200-line burst froze the client for
  thirteen seconds.
- **The history widget redrew from the whole canonical log per event**,
  filtering up to 5000 events and rebuilding a page of DOM each time.

There is a lesson in the first one worth keeping: `maxLines` exists *so that* a
long session stays responsive, and `scrollTop = scrollHeight` over a list held at
its cap is the most expensive possible version of that write. The bound kept
memory flat and made latency quadratic.

Measured in the lab, before and after::

    200 lines, empty log       520ms  ->     27 - 37ms
    1000 lines              10 005ms  ->        150ms
    200 lines after 1200     3 824ms  ->     43 - 46ms
    per line at the cap       68.2ms  ->  0.28 - 0.73ms

These tests pin the *structure* that produces those numbers, because a timing
assertion in CI measures the build machine's load rather than this code. The
numbers themselves are re-measurable with `browser-qa/qa-performance.js`, which
is where the ranges above come from and why they are ranges.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"
SHELL = (JS_DIR / "aetos.js").read_text(encoding="utf-8")
TEMPLATE_DIR = Path(AETOS_STATIC_DIR).parent / "templates"
CLIENT_TEMPLATE = (TEMPLATE_DIR / "webclient.html").read_text(encoding="utf-8")
BASE_TEMPLATE = (TEMPLATE_DIR / "aetos" / "base.html").read_text(encoding="utf-8")


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


def _presentation_observer():
    """
    The pipeline observer that drives the history widget.

    Returns:
        str: JavaScript source.

    """
    return _function_body(
        SHELL, 'pipeline.observe("presentation", function () {', "// Presentation second"
    )


class TestAppendTouchesNoGeometry(TestCase):
    """
    The whole fix, stated as one property: building a line must not measure
    the document.

    """

    def _append_body(self):
        """
        The body of `ConsoleWidget.append`.

        Returns:
            str: JavaScript source.

        """
        return _function_body(
            SHELL, "function append(content, className, presentation) {", "pending.push(line);"
        )

    def test_it_reads_no_layout_property(self):
        """
        Reading any of these after a DOM mutation is what forces the layout.
        Naming all four rather than only the one that was there stops the next
        version of this bug arriving through a different property.

        """
        body = self._append_body()
        for geometry in ("scrollHeight", "scrollTop", "clientHeight", "offsetHeight"):
            self.assertNotIn(geometry, body, "append reads %r" % geometry)

    def test_it_does_not_touch_the_document(self):
        body = self._append_body()
        self.assertNotIn("rootElement.appendChild", body)
        self.assertNotIn("trim()", body)

    def test_the_line_goes_to_the_pending_batch(self):
        self.assertIn("pending.push(line);", SHELL)


class TestTheFlushIsWhereTheWorkHappens(TestCase):
    """One layout per frame, however many lines arrived in it."""

    def _flush_body(self):
        """
        The body of `ConsoleWidget.flush`.

        Returns:
            str: JavaScript source.

        """
        return _function_body(SHELL, "function flush() {", "// Bounded scrollback")

    def test_it_measures_once_before_adding_anything(self):
        """
        Order is the point. Measured after the append it would answer "is the
        console taller now", which is not the question.

        """
        body = self._flush_body()
        self.assertLess(body.index("isScrolledToBottom()"), body.index("rootElement.appendChild"))

    def test_the_batch_is_added_as_one_fragment(self):
        body = self._flush_body()
        self.assertIn("createDocumentFragment()", body)
        self.assertIn("rootElement.appendChild(fragment)", body)

    def test_the_scroll_is_written_once_and_last(self):
        """
        After `trim`, because trimming shrinks `scrollHeight` and a scroll
        written before it would land short of the bottom.

        """
        body = self._flush_body()
        self.assertLess(body.index("trim();"), body.index("rootElement.scrollTop ="))

    def test_an_empty_flush_does_nothing(self):
        """
        Two schedulers race to call it -- see below -- so the second must be
        free rather than merely harmless.

        """
        body = self._flush_body()
        self.assertIn("if (!pending.length)", body)


class TestTheBatchCannotGrowWithoutBound(TestCase):
    """
    The failure mode a naive animation-frame batch introduces: an environment
    where frames never run, and lines accumulate in memory instead of on screen.

    """

    def test_a_large_burst_flushes_itself(self):
        self.assertIn("var MAX_PENDING = 500;", SHELL)
        self.assertIn("if (pending.length >= MAX_PENDING) {", SHELL)

    def test_a_timer_backs_up_the_animation_frame(self):
        """
        A backgrounded tab runs no animation frames. The lines would not be
        *lost* -- the canonical log has them -- but they would be missing from
        a console somebody may be reading in another window.

        `setTimeout` unconditionally rather than as an `else`, so it also covers
        a frame callback that is scheduled and then never runs.

        """
        body = _function_body(SHELL, "function schedule() {", "function flush() {")
        self.assertIn("window.requestAnimationFrame(flush)", body)
        self.assertIn("window.setTimeout(flush, 100)", body)
        self.assertNotIn("} else {", body)

    def test_the_scrollback_cap_is_unchanged(self):
        """
        M25 changed when the trimming happens, not how much is kept.

        """
        self.assertIn("(options && options.maxLines) || 5000", SHELL)

    def test_a_caller_can_force_the_console_current(self):
        """
        Anything that reads the console DOM must be able to ask for it to be up
        to date rather than guessing at a frame boundary.

        """
        self.assertIn("return { append: append, flush: flush };", SHELL)


class TestHistoryRedrawsOncePerFrame(TestCase):
    """
    A redraw filters the entire canonical log and rebuilds a page of DOM. Per
    event, that made the cost of one line proportional to the length of the
    session.

    """

    def test_the_observer_schedules_rather_than_redrawing(self):
        body = _presentation_observer()
        self.assertIn("historyRefreshQueued", body)
        self.assertNotIn("historyRefreshers.forEach", body)

    def test_it_has_the_same_backstop_as_the_console(self):
        body = _presentation_observer()
        self.assertIn("window.requestAnimationFrame(refreshHistory)", body)
        self.assertIn("window.setTimeout(refreshHistory, 100)", body)

    def test_nothing_is_scheduled_when_no_widget_wants_it(self):
        """
        The history widget is optional. Scheduling a frame callback for a
        listener list that is empty is work done for nobody.

        """
        self.assertIn("!historyRefreshers.length", _presentation_observer())


class TestScriptsDoNotBlockTheParser(TestCase):
    """
    55 scripts in `<head>`, every one of them parser-blocking: the body was not
    parsed, and nothing painted, until all of them had downloaded and run. On a
    connection with any latency that is the whole of the startup cost.

    `defer` rather than `async`: execution order is load-bearing here -- the
    accessibility subsystem must exist before anything that announces -- and
    `async` explicitly does not preserve it.

    """

    def _script_tags(self, template):
        """
        Every `<script>` tag carrying a `src`.

        Args:
            template (str): Template source.

        Returns:
            list: The matched tag strings.

        """
        return re.findall(r"<script\b[^>]*\bsrc=[^>]*>", template)

    def test_every_script_in_the_client_template_is_deferred(self):
        """
        A floor rather than an exact count.

        The count guards against a regex that silently matches nothing, which
        would let the loop below pass by having no work to do. It is not itself
        interesting, and pinning it exactly meant every new module broke this
        test for a reason unrelated to what it checks.

        """
        tags = self._script_tags(CLIENT_TEMPLATE)
        self.assertGreater(len(tags), 40, "found only %d script tags" % len(tags))
        for tag in tags:
            self.assertIn("defer", tag, "not deferred: %s" % tag)

    def test_every_script_in_the_base_template_is_deferred(self):
        """
        Including Evennia's own `evennia.js` and the jQuery shim it needs.
        Deferring some and not others would reorder them against each other,
        which is the one thing that must not happen.

        """
        tags = self._script_tags(BASE_TEMPLATE)
        self.assertEqual(len(tags), 3)
        for tag in tags:
            self.assertIn("defer", tag, "not deferred: %s" % tag)

    def test_the_transport_bootstrap_is_deferred_like_the_rest(self):
        """
        M26 replaced the page's one inline script with `transport_bootstrap.js`,
        which defines the globals `evennia.js` reads.

        It has to be deferred *and* first: deferred scripts run in document
        order, and that ordering is the only thing guaranteeing the globals
        exist before `evennia.js` initialises. An inline script would have run
        at parse time and needed no ordering care, which is what made this the
        one place the change could go wrong.

        """
        tags = self._script_tags(BASE_TEMPLATE)
        bootstrap = [tag for tag in tags if "transport_bootstrap.js" in tag]
        self.assertEqual(len(bootstrap), 1)
        self.assertIn("defer", bootstrap[0])
        self.assertLess(
            BASE_TEMPLATE.index("transport_bootstrap.js"),
            BASE_TEMPLATE.index("webclient/js/evennia.js"),
        )
