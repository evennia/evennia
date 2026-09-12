/*
 * Aetos focus manager.  Addendum A.19, A.20.
 *
 * A11Y-FOCUS-001: server events never move focus.
 *
 * This is the requirement most easily broken by accident and hardest to notice
 * once broken. Focus moving unexpectedly is a mild annoyance with a mouse, a
 * real problem with a keyboard, and genuinely disabling with braille -- where
 * the display follows focus, so an unrequested move throws away the reader's
 * place in a passage they were part-way through, with no way to get back to it.
 *
 * A game where a poison tick stole focus every three seconds would be
 * unplayable in a way that is invisible to a sighted mouse user testing it.
 *
 * So the rule here is inverted from the usual: focus moves only in response to
 * something the *player* did. Everything arriving from the server is rendered
 * where it belongs and left alone.
 *
 * This module offers three things:
 *
 *   - a save/restore stack, so a dialog can return focus where it found it
 *   - a focus trap, so a modal actually is one
 *   - a development-time guard that reports focus moving with no user gesture
 *     to explain it, which is how a violation gets found before a player does
 */

(function (window, document) {
    "use strict";

    var FOCUSABLE = [
        "button:not([disabled])",
        "input:not([disabled])",
        "textarea:not([disabled])",
        "select:not([disabled])",
        "a[href]",
        "[tabindex]:not([tabindex='-1'])"
    ].join(",");

    /*
     * How long after a real user gesture a focus change is still attributable
     * to it. Generous, because a click may legitimately open a dialog that
     * loads data before focusing something.
     */
    var GESTURE_WINDOW_MS = 1000;

    function createFocusManager(services) {
        var settings = services || {};
        var root = settings.root || document;
        var onViolation = settings.onViolation || null;

        var stack = [];
        var trap = null;
        var lastGestureAt = 0;
        var guarding = false;

        function now() {
            return (settings.now || Date.now)();
        }

        function isVisible(element) {
            return element && (element.offsetParent !== null ||
                element === document.activeElement);
        }

        function focusableWithin(container) {
            if (!container) {
                return [];
            }
            return Array.prototype.slice.call(container.querySelectorAll(FOCUSABLE))
                .filter(isVisible);
        }

        /* --- Save and restore ------------------------------------------- */

        /*
         * Remember where focus is, before deliberately moving it.
         *
         * Returns a restore function rather than requiring a matching pop, so a
         * caller cannot unbalance the stack by taking an early return path.
         */
        function capture() {
            var previous = document.activeElement;
            stack.push(previous);
            var restored = false;

            return function restore() {
                if (restored) {
                    return false;
                }
                restored = true;
                var index = stack.indexOf(previous);
                if (index !== -1) {
                    stack.splice(index, 1);
                }
                // The opener may have been removed while the dialog was open --
                // a note deleted from its own editor, for instance. Focusing a
                // detached node silently sends focus to <body>, which loses the
                // player's place, so fall back to something real.
                if (previous && document.contains(previous) && isVisible(previous)) {
                    userFocus(previous);
                    return true;
                }
                var fallback = settings.fallback && settings.fallback();
                if (fallback && document.contains(fallback)) {
                    userFocus(fallback);
                    return true;
                }
                return false;
            };
        }

        /*
         * Move focus as the result of a user action.
         *
         * Everything that legitimately moves focus goes through here, so the
         * guard below can tell an intended move from a stray one.
         */
        function userFocus(element) {
            if (!element || typeof element.focus !== "function") {
                return false;
            }
            lastGestureAt = now();
            element.focus();
            return document.activeElement === element;
        }

        /* --- Trapping ---------------------------------------------------- */

        /*
         * Confine Tab within a container.
         *
         * A trap that does not trap is worse than none: a screen-reader user
         * tabs past the end of the dialog into the page behind it, where they
         * can operate controls they cannot see and which the dialog is
         * conceptually blocking, with no indication they have left.
         */
        function trapWithin(container) {
            release();

            function handler(event) {
                if (event.key !== "Tab") {
                    return;
                }
                var focusables = focusableWithin(container);
                if (!focusables.length) {
                    // Nothing to cycle between, so keep focus where it is
                    // rather than letting Tab escape to the page behind.
                    event.preventDefault();
                    return;
                }
                var first = focusables[0];
                var last = focusables[focusables.length - 1];
                var active = document.activeElement;

                if (!container.contains(active)) {
                    event.preventDefault();
                    userFocus(event.shiftKey ? last : first);
                    return;
                }
                if (event.shiftKey && active === first) {
                    event.preventDefault();
                    userFocus(last);
                } else if (!event.shiftKey && active === last) {
                    event.preventDefault();
                    userFocus(first);
                }
            }

            document.addEventListener("keydown", handler, true);
            trap = { container: container, handler: handler };
            return release;
        }

        function release() {
            if (!trap) {
                return false;
            }
            document.removeEventListener("keydown", trap.handler, true);
            trap = null;
            return true;
        }

        /* --- The guard ---------------------------------------------------
         *
         * Reports focus landing somewhere with no recent user gesture to
         * explain it. It does not *prevent* the move -- silently refusing a
         * focus call would produce a subtler bug than the one it fixed. It
         * reports, so the violation is found in QA rather than by a player.
         */

        function gestureSeen() {
            lastGestureAt = now();
        }

        function onFocusIn(event) {
            if (now() - lastGestureAt <= GESTURE_WINDOW_MS) {
                return;
            }
            // Focus arriving at <body> is the browser tidying up after a
            // removed element, not the client stealing anything.
            if (!event.target || event.target === document.body) {
                return;
            }
            if (onViolation) {
                onViolation({
                    element: event.target,
                    id: event.target.id || null,
                    reason: "focus moved with no user gesture within " +
                        GESTURE_WINDOW_MS + "ms"
                });
            }
        }

        function startGuard() {
            if (guarding) {
                return false;
            }
            guarding = true;
            ["keydown", "mousedown", "touchstart", "pointerdown"].forEach(function (name) {
                root.addEventListener(name, gestureSeen, true);
            });
            document.addEventListener("focusin", onFocusIn, true);
            return true;
        }

        function stopGuard() {
            if (!guarding) {
                return false;
            }
            guarding = false;
            ["keydown", "mousedown", "touchstart", "pointerdown"].forEach(function (name) {
                root.removeEventListener(name, gestureSeen, true);
            });
            document.removeEventListener("focusin", onFocusIn, true);
            return true;
        }

        return {
            capture: capture,
            userFocus: userFocus,
            focusableWithin: focusableWithin,
            trapWithin: trapWithin,
            release: release,
            startGuard: startGuard,
            stopGuard: stopGuard,
            gestureSeen: gestureSeen,
            depth: function () { return stack.length; },
            isTrapped: function () { return !!trap; }
        };
    }

    window.AetosFocusManager = {
        create: createFocusManager,
        FOCUSABLE: FOCUSABLE,
        GESTURE_WINDOW_MS: GESTURE_WINDOW_MS
    };

})(window, document);
