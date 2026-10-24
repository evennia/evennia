/*
 * Aetos state store.
 *
 * The single source of truth the browser renders from. Widgets subscribe to a
 * section and are told when it changes; they never parse websocket messages and
 * never reach for each other's data (blueprint sections 7 and 12).
 *
 * Two properties matter more than the API surface:
 *
 *   - Notifications are BATCHED. A combat round can deliver resources, effects,
 *     entities and target in the same tick. Notifying synchronously per message
 *     would lay out the page several times per frame; instead subscribers are
 *     called once per animation frame with whatever changed.
 *
 *   - A full sync REPLACES authoritative state rather than merging into it.
 *     Merging would let a stale entity from before a reconnect survive forever,
 *     which is exactly the class of bug that makes reconnect handling untrustworthy.
 */

(function (window) {
    "use strict";

    // The canonical sections. Fixed at protocol v1 so a widget can subscribe to
    // a section that is merely empty rather than absent.
    /*
     * The sections the store knows about.
     *
     * This list is the store's whole contract with the protocol, and anything
     * absent from it is silently discarded by applySync -- which is exactly what
     * happened to `inventory` and `equipment` when M16 added them server-side
     * and here but not to this array. The payload arrived, the widgets
     * subscribed, and nothing ever appeared, with no error anywhere.
     *
     * A section added to `build_sync` MUST be added here in the same change.
     * Guarded by a test that compares the two lists.
     */
    var SECTIONS = [
        "connection",
        "manifest",
        "character",
        "room",
        "entities",
        "resources",
        "inventory",
        "equipment",
        "target",
        "effects",
        "map",
        "actions",
        "mode",
        "media"
    ];

    function emptyState() {
        var state = {};
        SECTIONS.forEach(function (section) {
            state[section] = {};
        });
        return state;
    }

    function createStore(options) {
        var opts = options || {};
        var state = emptyState();
        var subscribers = {};
        var pending = {};
        var frameHandle = null;

        /*
         * Whether a flush is already queued.
         *
         * Separate from `frameHandle`, and that separation is the bug fix.
         *
         * The guard used to be `if (frameHandle !== null) return;`, which
         * conflates "a flush is pending" with "the scheduler returned a
         * cancellable handle". `requestAnimationFrame` returns a number so it
         * worked in a browser -- but an injected scheduler that runs
         * synchronously returns `undefined`, and `undefined !== null` is true,
         * so every flush after the first was silently skipped.
         *
         * That made the documented test seam deliver exactly one update and
         * then go quiet, which is a bad failure for a seam whose whole purpose
         * is making update behaviour testable. Found at M22 while testing
         * widget failure isolation, where it looked at first like the widget
         * had stopped receiving events.
         */
        var flushQueued = false;

        /*
         * Scheduler for batched notifications.
         *
         * requestAnimationFrame alone is WRONG here. Browsers do not run rAF in
         * a hidden or backgrounded tab, so a player who switches away would keep
         * receiving state that never reaches a widget -- and would come back to
         * a client showing the world as it was when they left. Blueprint section
         * 60 lists browser sleep and tab resume as cases that must work.
         *
         * So rAF and a timeout are armed together and whichever fires first
         * wins. Visible tabs still coalesce updates to paint; hidden tabs still
         * get their updates.
         */
        var schedule = opts.schedule || function (fn) {
            var done = false;
            var run = function () {
                if (done) {
                    return;
                }
                done = true;
                fn();
            };
            if (typeof window.requestAnimationFrame === "function") {
                window.requestAnimationFrame(run);
            }
            // Also covers environments with no rAF at all.
            return window.setTimeout(run, 50);
        };

        function isKnownSection(section) {
            return SECTIONS.indexOf(section) !== -1;
        }

        function get(section) {
            return state[section];
        }

        function snapshot() {
            // A shallow copy per section: enough to stop a widget mutating the
            // store by accident, without the cost of deep-cloning every frame.
            var copy = {};
            SECTIONS.forEach(function (name) {
                copy[name] = state[name];
            });
            return copy;
        }

        function subscribe(section, listener) {
            if (typeof listener !== "function") {
                return function () {};
            }
            if (!isKnownSection(section)) {
                window.console.error("Aetos store: unknown section " + section);
                return function () {};
            }
            if (!subscribers[section]) {
                subscribers[section] = [];
            }
            subscribers[section].push(listener);
            return function unsubscribe() {
                subscribers[section] = subscribers[section].filter(function (entry) {
                    return entry !== listener;
                });
            };
        }

        function markChanged(section) {
            pending[section] = true;
            if (flushQueued) {
                return;
            }
            flushQueued = true;
            frameHandle = schedule(flush);
        }

        function flush() {
            frameHandle = null;
            flushQueued = false;
            var changed = Object.keys(pending);
            pending = {};
            changed.forEach(function (section) {
                var listeners = subscribers[section];
                if (!listeners || !listeners.length) {
                    return;
                }
                listeners.slice().forEach(function (listener) {
                    // One broken widget must not stop the others updating.
                    try {
                        listener(state[section], section);
                    } catch (err) {
                        window.console.error(
                            "Aetos store: subscriber for " + section + " threw", err);
                    }
                });
            });
        }

        // Replace a section outright. Used for deltas that carry a complete new
        // value for their section.
        function set(section, value) {
            if (!isKnownSection(section)) {
                window.console.error("Aetos store: unknown section " + section);
                return;
            }
            state[section] = value;
            markChanged(section);
        }

        // Merge keys into a section, for partial updates.
        function merge(section, values) {
            if (!isKnownSection(section)) {
                window.console.error("Aetos store: unknown section " + section);
                return;
            }
            var current = state[section] || {};
            var next = {};
            Object.keys(current).forEach(function (key) {
                next[key] = current[key];
            });
            Object.keys(values || {}).forEach(function (key) {
                next[key] = values[key];
            });
            state[section] = next;
            markChanged(section);
        }

        /*
         * Apply a full authoritative sync.
         *
         * Authoritative sections are REPLACED, not merged: anything the server
         * did not mention is cleared. After a reconnect the server's view is the
         * truth, and a merge would strand entities, effects or a target that no
         * longer exist.
         *
         * Two sections are exempt, because a sync is not their source:
         *
         *   - `connection` is client-observed transport state, which the server
         *     never reports.
         *   - `manifest` arrives in its own `aetos_manifest` message, once per
         *     handshake. Clearing it here would wipe the game's declared
         *     capabilities on the very first sync, silently disabling every
         *     capability-gated widget for the rest of the session.
         */
        function applySync(payload) {
            var data = payload || {};
            SECTIONS.forEach(function (section) {
                if (section === "connection" || section === "manifest") {
                    return;
                }
                state[section] = Object.prototype.hasOwnProperty.call(data, section)
                    ? data[section]
                    : {};
                markChanged(section);
            });
        }

        function reset() {
            var connection = state.connection;
            state = emptyState();
            state.connection = connection;
            SECTIONS.forEach(markChanged);
        }

        // Exposed so tests can assert synchronously without waiting a frame.
        function flushNow() {
            flushQueued = false;
            if (frameHandle !== null && frameHandle !== undefined &&
                    typeof window.cancelAnimationFrame === "function") {
                window.cancelAnimationFrame(frameHandle);
            }
            frameHandle = null;
            flush();
        }

        return {
            sections: SECTIONS.slice(),
            get: get,
            snapshot: snapshot,
            subscribe: subscribe,
            set: set,
            merge: merge,
            applySync: applySync,
            reset: reset,
            flushNow: flushNow
        };
    }

    window.AetosStore = { create: createStore, SECTIONS: SECTIONS.slice() };

})(window);
