/*
 * Aetos touch gestures.  Milestone M20.  Addendum A.57.
 *
 * EVERY GESTURE HERE IS A SHORTCUT FOR SOMETHING THAT IS ALSO A BUTTON.
 *
 * A.57 forbids requiring dragging, double clicking, precision pointer
 * placement, multi-point gestures or hover-only activation. Aetos reads that
 * as a design rule rather than a checklist: a gesture may make something
 * faster, and may never be the only way to do it.
 *
 * The reason is not only motor disability, though that is reason enough. A
 * gesture is invisible. It cannot be discovered, cannot be listed, cannot be
 * rebound, and cannot be announced -- so a feature reachable only by swipe does
 * not exist for anyone using a screen reader, anyone using a switch device,
 * anyone on a desktop, or anyone who simply never guessed it was there.
 *
 * Each gesture below therefore names the palette command it duplicates, the
 * same rule the keyboard shortcut manager enforces (A.23). If the command is
 * absent the gesture is not registered, because a shortcut for something that
 * does not exist is worse than no shortcut.
 *
 * SINGLE POINTER ONLY.
 *
 * No pinch, no two-finger anything. Multi-point gestures are explicitly named
 * in A.57, and they exclude anyone operating a touchscreen with one hand, a
 * stylus, a head pointer or a single switch.
 *
 * NO DRAGGING.
 *
 * A swipe is not a drag: it starts, moves and ends without anything following
 * the finger, and it is cancelled by lifting early. Nothing in Aetos requires
 * holding a target while moving -- the layout editor moves panels with arrow
 * keys precisely so that it never needs to (M7).
 *
 * GENEROUS THRESHOLDS.
 *
 * A swipe must travel far enough to be deliberate, and stay straight enough not
 * to be a scroll. Both bars are set for somebody with a tremor rather than for
 * somebody with a steady hand: a gesture that only works when performed neatly
 * is a gesture that fails for the people who most needed it to be easy.
 */

(function (window, document) {
    "use strict";

    //: Minimum travel for a swipe, in CSS pixels. Generous on purpose -- a
    //: short threshold turns an imprecise tap into an accidental action.
    var MIN_DISTANCE = 60;

    //: How much the perpendicular drift may be, as a fraction of the travel.
    //: A tremor is not a diagonal, and a scroll is not a swipe.
    var MAX_DRIFT_RATIO = 0.6;

    //: Longer than this and it is not a swipe. Somebody resting a finger on the
    //: screen while thinking has not asked for anything.
    var MAX_DURATION_MS = 800;

    function createGestures(services) {
        var settings = services || {};
        var announce = settings.announce || function () {};
        var preferences = settings.preferences || null;

        var bindings = [];
        var start = null;
        var listening = false;

        function enabled() {
            if (!preferences || typeof preferences.value !== "function") {
                return true;
            }
            return preferences.value("pointer.gestures", true) !== false;
        }

        /*
         * Register a gesture.
         *
         * `paletteCommand` is required and is checked, not merely recorded.
         * The shortcut manager throws for a missing one (A.23) and this follows
         * the same rule for the same reason: a gesture with no visible
         * equivalent is a feature that does not exist for most of the people
         * this client is built for.
         */
        function register(gesture) {
            if (!gesture || !gesture.direction || !gesture.paletteCommand) {
                throw new Error(
                    "A gesture needs a direction and the palette command it duplicates."
                );
            }
            if (typeof gesture.run !== "function") {
                throw new Error("A gesture needs something to run.");
            }
            bindings.push({
                direction: gesture.direction,
                paletteCommand: gesture.paletteCommand,
                label: gesture.label || gesture.paletteCommand,
                run: gesture.run,
                when: gesture.when || function () { return true; }
            });
            return gesture.direction;
        }

        /*
         * Whether a gesture should fire here.
         *
         * Never inside a text field, a scrollable region, or anything the
         * player might be selecting text in. A swipe that stole a scroll would
         * make the transcript unreadable on the device where it is already
         * hardest to read.
         */
        function shouldIgnore(target) {
            if (!target || !target.closest) {
                return false;
            }
            if (target.closest("input, textarea, select, [contenteditable]")) {
                return true;
            }
            // Scrollable surfaces own their own vertical movement.
            return !!target.closest(
                "#aetos-console, .aetos-media__captions, .aetos-history__rows, " +
                ".aetos-privacy__list, .aetos-aac__grid"
            );
        }

        function classify(from, to, elapsed) {
            var dx = to.x - from.x;
            var dy = to.y - from.y;
            var horizontal = Math.abs(dx);
            var vertical = Math.abs(dy);

            if (elapsed > MAX_DURATION_MS) {
                return null;
            }
            if (horizontal >= MIN_DISTANCE && vertical <= horizontal * MAX_DRIFT_RATIO) {
                return dx > 0 ? "right" : "left";
            }
            if (vertical >= MIN_DISTANCE && horizontal <= vertical * MAX_DRIFT_RATIO) {
                return dy > 0 ? "down" : "up";
            }
            return null;
        }

        function fire(direction) {
            var matches = bindings.filter(function (binding) {
                try {
                    return binding.direction === direction && binding.when() !== false;
                } catch (err) {
                    return false;
                }
            });
            if (!matches.length) {
                return false;
            }
            var binding = matches[0];
            /*
             * Announced, because a gesture is invisible and its result may be
             * too. Somebody who swiped by accident needs to know what just
             * happened in order to undo it.
             */
            announce(binding.label + ".", { category: "system" });
            binding.run();
            return true;
        }

        function onStart(event) {
            // One finger. `touches.length > 1` is a pinch or a two-finger
            // scroll, and neither is Aetos's to interpret (A.57).
            if (!enabled() || !event.touches || event.touches.length !== 1) {
                start = null;
                return;
            }
            if (shouldIgnore(event.target)) {
                start = null;
                return;
            }
            var touch = event.touches[0];
            start = { x: touch.clientX, y: touch.clientY, at: event.timeStamp };
        }

        function onEnd(event) {
            if (!start) {
                return;
            }
            var began = start;
            start = null;

            // A second finger arriving mid-gesture cancels it rather than
            // completing it with whichever finger happened to lift last.
            if (!event.changedTouches || event.changedTouches.length !== 1) {
                return;
            }
            var touch = event.changedTouches[0];
            var direction = classify(
                began,
                { x: touch.clientX, y: touch.clientY },
                event.timeStamp - began.at
            );
            if (direction) {
                fire(direction);
            }
        }

        function listen(root) {
            if (listening) {
                return false;
            }
            var target = root || document;
            // Passive: this never calls preventDefault, so it can never block a
            // scroll. A gesture handler that fights the browser's own scrolling
            // is one that makes a page feel broken.
            target.addEventListener("touchstart", onStart, { passive: true });
            target.addEventListener("touchend", onEnd, { passive: true });
            target.addEventListener("touchcancel", function () { start = null; },
                { passive: true });
            listening = true;
            return true;
        }

        /*
         * Every gesture, for the help screen.
         *
         * A gesture nobody can list is a gesture nobody can learn. This is what
         * makes them documentable rather than folklore.
         */
        function all() {
            return bindings.map(function (binding) {
                return {
                    direction: binding.direction,
                    label: binding.label,
                    paletteCommand: binding.paletteCommand
                };
            });
        }

        return {
            register: register,
            listen: listen,
            all: all,
            classify: classify,
            enabled: enabled,
            MIN_DISTANCE: MIN_DISTANCE
        };
    }

    window.AetosGestures = {
        create: createGestures,
        MIN_DISTANCE: MIN_DISTANCE,
        MAX_DRIFT_RATIO: MAX_DRIFT_RATIO,
        MAX_DURATION_MS: MAX_DURATION_MS
    };

})(window, document);
