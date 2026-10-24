/*
 * Aetos triggers.
 *
 * Two kinds, as blueprint section 30 describes:
 *
 *   TEXT       -- when game output contains or matches something
 *   STRUCTURED -- when a value in the store crosses a condition
 *
 * Structured triggers are preferred wherever a game exposes data. Scraping
 * output is fragile: it breaks when a game rewords a message, and it cannot
 * distinguish "You begin bleeding" from someone saying that phrase in chat.
 * A structured trigger on `resources.health < 0.2` has neither problem.
 *
 * SAFETY IS THE WHOLE DESIGN.
 *
 * A trigger sends commands in response to game output. Commands produce output.
 * That is a feedback loop with a player's account on one end, and section 62
 * lists trigger loops and automation runaway in the threat model. So:
 *
 *   - every trigger has a COOLDOWN, so one cannot fire on its own echo
 *   - a GLOBAL RATE LIMIT caps total firings per window across all triggers
 *   - triggers do not fire while the queue is already running their commands
 *   - a trigger that trips the rate limit is DISABLED and the player is told,
 *     rather than being throttled silently forever
 *
 * Regex patterns are compiled once and rejected if invalid, so a mistyped
 * pattern reports an error at save time rather than throwing on every line of
 * game output.
 */

(function (window) {
    "use strict";

    //: Minimum gap between firings of the same trigger.
    var DEFAULT_COOLDOWN = 1000;

    //: Global limiter: at most this many firings within the window, across all
    //: triggers. Generous for real play, decisive against a loop.
    var RATE_LIMIT = 12;
    var RATE_WINDOW = 5000;

    var MAX_PATTERN_LENGTH = 400;
    var MAX_COMMANDS = 5;

    var COMPARATORS = {
        lt: function (a, b) { return a < b; },
        lte: function (a, b) { return a <= b; },
        gt: function (a, b) { return a > b; },
        gte: function (a, b) { return a >= b; },
        eq: function (a, b) { return a === b; },
        ne: function (a, b) { return a !== b; }
    };

    function createTriggers(services) {
        var groups = services.groups || null;

        /*
         * Effective enabled-state.  C.15.
         *
         * Delegates to the automation groups module when one is present, and
         * falls back to the rule's own flag when it is not -- so a client
         * without the groups module behaves exactly as it did before them.
         */
        function allowed(rule) {
            if (groups && typeof groups.allows === "function") {
                return groups.allows(rule);
            }
            return !rule || rule.enabled !== false;
        }

        var storage = services.storage;
        var queue = services.queue;
        var store = services.store;
        var announce = services.announce || function () {};
        var isAllowed = services.isAllowed || function () { return true; };
        var now = services.now || function () { return Date.now(); };

        var lastFired = {};
        var recentFirings = [];

        function normalize(trigger) {
            var commands = (trigger.commands || [])
                .map(function (entry) { return String(entry || "").trim(); })
                .filter(Boolean)
                .slice(0, MAX_COMMANDS);
            return {
                id: trigger.id || String(trigger.label || "trigger").toLowerCase(),
                label: String(trigger.label || "Trigger").slice(0, 80),
                kind: trigger.kind === "structured" ? "structured" : "text",
                // Text trigger fields.
                pattern: String(trigger.pattern || "").slice(0, MAX_PATTERN_LENGTH),
                mode: trigger.mode === "regex" ? "regex" : "contains",
                // Structured trigger fields.
                subject: trigger.subject || null,
                comparator: COMPARATORS[trigger.comparator] ? trigger.comparator : "lt",
                value: trigger.value,
                commands: commands,
                cooldown: typeof trigger.cooldown === "number"
                    ? trigger.cooldown : DEFAULT_COOLDOWN,
                enabled: trigger.enabled !== false,
                // Which automation group this belongs to, if any (C.15).
                group: String(trigger.group || "")
            };
        }

        function save(trigger) {
            if (!storage) {
                return window.Promise.resolve(null);
            }
            var record = normalize(trigger);
            if (!record.commands.length) {
                return window.Promise.reject(
                    new Error("A trigger needs at least one command."));
            }
            if (record.kind === "text") {
                if (!record.pattern) {
                    return window.Promise.reject(new Error("A text trigger needs a pattern."));
                }
                if (record.mode === "regex") {
                    // Validate now. A bad pattern must fail once here rather
                    // than throwing on every line of game output forever.
                    try {
                        new RegExp(record.pattern);
                    } catch (err) {
                        return window.Promise.reject(
                            new Error("That is not a valid regular expression: " + err.message));
                    }
                }
            } else if (!record.subject) {
                return window.Promise.reject(
                    new Error("A structured trigger needs a subject."));
            }
            return storage.put("triggers", record.id, record).then(function () {
                return record;
            });
        }

        function remove(id) {
            return storage ? storage.remove("triggers", id) : window.Promise.resolve(false);
        }

        function all() {
            if (!storage) {
                return window.Promise.resolve([]);
            }
            return storage.all("triggers").then(function (rows) {
                return rows.map(function (row) { return row.value; });
            });
        }

        /*
         * Global rate limit.
         *
         * Returns false once too many firings have happened in the window. This
         * is the backstop against a loop that the per-trigger cooldown cannot
         * catch -- two triggers firing each other, for example.
         */
        function withinRateLimit() {
            var cutoff = now() - RATE_WINDOW;
            recentFirings = recentFirings.filter(function (stamp) { return stamp > cutoff; });
            return recentFirings.length < RATE_LIMIT;
        }

        function readPath(path) {
            var parts = String(path || "").split(".");
            var section = store ? store.get(parts[0]) : null;
            if (!section) {
                return undefined;
            }
            // Resources live in a list, so "resources.health" means "the
            // resource whose id is health" rather than a literal property.
            if (parts[0] === "resources" && parts[1]) {
                var found = (section.items || []).filter(function (entry) {
                    return entry.id === parts[1];
                })[0];
                if (!found) {
                    return undefined;
                }
                // A fraction is what a player means by "below 20%", and it works
                // regardless of the resource's scale.
                if (typeof found.maximum === "number" && found.maximum > 0) {
                    var minimum = typeof found.minimum === "number" ? found.minimum : 0;
                    return (found.value - minimum) / (found.maximum - minimum);
                }
                return found.value;
            }
            var cursor = section;
            for (var i = 1; i < parts.length; i++) {
                if (cursor === null || cursor === undefined) {
                    return undefined;
                }
                cursor = cursor[parts[i]];
            }
            return cursor;
        }

        function matchesText(trigger, line) {
            if (trigger.mode === "regex") {
                try {
                    return new RegExp(trigger.pattern).test(line);
                } catch (err) {
                    return false;
                }
            }
            return line.toLowerCase().indexOf(trigger.pattern.toLowerCase()) !== -1;
        }

        function matchesStructured(trigger) {
            var actual = readPath(trigger.subject);
            if (actual === undefined) {
                return false;
            }
            var compare = COMPARATORS[trigger.comparator];
            return compare ? compare(actual, trigger.value) : false;
        }

        /*
         * Fire a trigger, subject to every limit.
         *
         * Order matters: the cheap per-trigger cooldown is checked before the
         * global limiter, so ordinary repeated matches do not consume the global
         * budget that exists to catch runaway loops.
         */
        function fire(trigger) {
            var stamp = now();
            /*
             * "Never fired" is not the same as "fired at time zero".
             *
             * Using `lastFired[id] || 0` conflates them, which means a trigger's
             * very first match is judged against a cooldown it has not had a
             * chance to serve -- so it never fires at all. Real clocks hide this
             * because Date.now() is large; a monotonic or injected clock starting
             * near zero exposes it immediately.
             */
            var hasFiredBefore = Object.prototype.hasOwnProperty.call(lastFired, trigger.id);
            if (hasFiredBefore && stamp - lastFired[trigger.id] < trigger.cooldown) {
                return false;
            }
            if (!withinRateLimit()) {
                // Disable rather than throttle. A trigger hitting the global
                // limit is looping, and silently throttling it forever leaves a
                // player wondering why their client feels broken.
                trigger.enabled = false;
                if (storage) {
                    storage.put("triggers", trigger.id, trigger);
                }
                announce(
                    "Trigger " + trigger.label +
                    " fired too often and has been disabled. Check it for a loop.");
                return false;
            }

            lastFired[trigger.id] = stamp;
            recentFirings.push(stamp);
            queue.run(trigger.commands, {
                label: trigger.label,
                announceStart: false,
                announceCompletion: false
            });
            return true;
        }

        /*
         * Evaluate text triggers against a line of game output.
         *
         * Called with the plain text form, never the HTML: matching against
         * markup would make a pattern depend on colour codes the player never
         * sees.
         */
        function onText(line, triggerList) {
            if (!isAllowed() || !line) {
                return [];
            }
            var fired = [];
            (triggerList || []).forEach(function (trigger) {
                // effective = rule.enabled AND group.enabled (C.15).
                // Consulted rather than reimplemented: five copies of a
                // two-term expression is five chances for one to drift.
                if (!allowed(trigger) || trigger.kind !== "text") {
                    return;
                }
                if (matchesText(trigger, line) && fire(trigger)) {
                    fired.push(trigger.id);
                }
            });
            return fired;
        }

        /*
         * Evaluate structured triggers against current state.
         *
         * Edge-triggered: fires when the condition becomes true, not while it
         * stays true. A health trigger must not fire every sync for as long as
         * the player is hurt.
         */
        var previouslyTrue = {};

        function onState(triggerList) {
            if (!isAllowed()) {
                return [];
            }
            var fired = [];
            (triggerList || []).forEach(function (trigger) {
                if (!allowed(trigger) || trigger.kind !== "structured") {
                    return;
                }
                var isTrue = matchesStructured(trigger);
                var was = previouslyTrue[trigger.id] === true;
                previouslyTrue[trigger.id] = isTrue;
                if (isTrue && !was && fire(trigger)) {
                    fired.push(trigger.id);
                }
            });
            return fired;
        }

        function resetLimits() {
            lastFired = {};
            recentFirings = [];
            previouslyTrue = {};
        }

        return {
            RATE_LIMIT: RATE_LIMIT,
            RATE_WINDOW: RATE_WINDOW,
            DEFAULT_COOLDOWN: DEFAULT_COOLDOWN,
            MAX_COMMANDS: MAX_COMMANDS,
            normalize: normalize,
            save: save,
            remove: remove,
            all: all,
            onText: onText,
            onState: onState,
            readPath: readPath,
            matchesText: matchesText,
            matchesStructured: matchesStructured,
            resetLimits: resetLimits,
            withinRateLimit: withinRateLimit
        };
    }

    window.AetosTriggers = {
        create: createTriggers,
        RATE_LIMIT: RATE_LIMIT,
        RATE_WINDOW: RATE_WINDOW,
        DEFAULT_COOLDOWN: DEFAULT_COOLDOWN
    };

})(window);
