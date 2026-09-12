/*
 * Aetos announcement manager.  Addendum A.13, A.14, A.15.
 *
 * A11Y-ANN-001: every automatic announcement passes through here. Widgets do
 * not own live regions.
 *
 * WHY THAT RULE EXISTS. A live region is a shared, serialised channel: the
 * player has one pair of ears and one braille display. Thirty widgets each with
 * their own `aria-live` do not produce thirty conversations, they produce one
 * conversation with thirty interruptions, and whichever widget updated last
 * wins. Centralising it means the client can decide what matters instead of
 * that being settled by render order.
 *
 * TWO REGIONS, USED VERY DIFFERENTLY (A.15).
 *
 *   polite  -- waits for a gap in speech. Almost everything.
 *   urgent  -- interrupts. Connection loss and session failure, essentially.
 *
 * Gameplay never reaches the urgent region. A channel that interrupts you
 * constantly stops being an interruption and becomes noise, at which point the
 * one message that genuinely needed to interrupt is the one that gets ignored.
 *
 * FLOOD CONTROL (A.16). A browser cannot know when a screen reader has finished
 * speaking -- there is no event for it, on any platform. So Aetos does not try
 * to synchronise against speech. It counts, and when announceable events arrive
 * faster than anyone could listen to them it stops reading each one and starts
 * reporting the shape of the burst instead:
 *
 *     Goblin attacks. Bob attacks. You dodge. Jane attacks. Goblin parries...
 *          ↓
 *     "Heavy activity. 12 further combat events."
 *
 * Every individual line is still in the transcript. What is dropped is the
 * *reading aloud* of each one, which was never going to be heard anyway: speech
 * is serial, and a queue growing faster than it drains does not inform anybody,
 * it just means the player hears a minute-old message and cannot interrupt it.
 *
 * Tells and critical messages bypass aggregation. Someone speaking to you
 * directly is the thing you most need to hear during a fight, and it is exactly
 * what a naive rate limiter would bury.
 */

(function (window, document) {
    "use strict";

    /*
     * Priorities, most to least urgent (A.14).
     *
     * `silent` is a real level, not the absence of one: a caller that decides
     * something is not worth saying still records that decision here, rather
     * than each call site inventing its own way of skipping the announcer.
     */
    var PRIORITIES = ["critical", "important", "normal", "background", "silent"];

    //: Only these interrupt. Deliberately short.
    var URGENT_PRIORITIES = ["critical"];

    /*
     * Default priority per category (A.14).
     *
     * These are defaults, not gameplay truths -- a game where combat is rare
     * and lethal is not the game these were tuned for, and the player's own
     * preferences override them.
     */
    var CATEGORY_PRIORITY = {
        connection: "critical",
        session: "critical",
        tell: "important",
        room: "important",
        chat: "normal",
        combat: "normal",
        command: "normal",
        effect: "normal",
        target: "normal",
        resource: "background",
        inventory: "background",
        media: "background",
        system: "normal",
        ambient: "silent",
        other: "normal"
    };

    //: Preference key governing each category, where one exists. A category
    //: absent from here is not individually switchable.
    var CATEGORY_PREFERENCE = {
        room: "screenReader.announceRoom",
        tell: "screenReader.announceTells",
        chat: "screenReader.announceChat",
        combat: "screenReader.announceCombat"
    };

    /*
     * Flood-control constants.  A.16.
     *
     * All in one object so they can be tuned from user testing rather than
     * hunted for. These are starting values, not findings -- the addendum's
     * own numbers, and they should be revisited once somebody has used this in
     * a real fight.
     */
    var FLOOD = {
        // Events per second above which a burst is considered to be underway.
        threshold: 5,
        // How long the rate must stay above the threshold before aggregating.
        // Without this a single busy moment would trigger summarising.
        sustainMs: 2000,
        // How often a summary is emitted while the burst continues.
        summaryMs: 2000,
        // Rolling window used to measure the rate.
        windowMs: 1000
    };

    //: Categories that never aggregate. Someone speaking to you directly is
    //: precisely what a naive rate limiter would bury.
    var NEVER_AGGREGATE = ["tell", "connection", "session"];

    function createAnnouncer(services) {
        var politeRegion = services.politeRegion || null;
        var urgentRegion = services.urgentRegion || null;
        var preferences = services.preferences || null;
        var now = services.now || function () { return Date.now(); };

        // Rolling record of recent announceable events, for rate measurement.
        var recent = [];
        var burstStartedAt = null;
        var lastSummaryAt = 0;
        var suppressed = {};
        var suppressedTotal = 0;
        var aggregating = false;

        // Kept for the Review Mode work in M17: while review is active the
        // manager holds low-priority announcements and counts them, so leaving
        // review can summarise rather than replay.
        var reviewing = false;
        var deferred = [];

        //: Optional speech renderer. Null unless the client wired one up.
        var speak = services.speak || null;

        var lastPolite = null;
        var lastUrgent = null;
        var history = [];
        var MAX_HISTORY = 50;

        function preferenceValue(path, fallback) {
            if (!preferences || typeof preferences.value !== "function") {
                return fallback;
            }
            var value = preferences.value(path);
            return value === undefined ? fallback : value;
        }

        /*
         * Decide whether to speak, and how loudly.
         *
         * Returns the effective priority, or null to stay silent. Kept as one
         * pure function so the policy is inspectable and testable rather than
         * scattered through the emit path.
         */
        function resolve(category, requested) {
            var priority = requested || CATEGORY_PRIORITY[category] || "normal";
            if (PRIORITIES.indexOf(priority) === -1) {
                priority = "normal";
            }
            if (priority === "silent") {
                return null;
            }

            // Critical always speaks. A player who has muted everything still
            // needs to know the connection dropped, because every other thing
            // the client tells them is now potentially stale.
            if (priority === "critical") {
                return priority;
            }

            var mode = preferenceValue("screenReader.announcementMode", "selective");
            if (mode === "minimal" && priority !== "important") {
                return null;
            }
            if (mode === "selective") {
                var key = CATEGORY_PREFERENCE[category];
                if (key && preferenceValue(key, true) === false) {
                    return null;
                }
                if (category === "resource") {
                    var setting = preferenceValue("screenReader.announceResources", "thresholds");
                    if (setting === "never") {
                        return null;
                    }
                }
            }

            /*
             * Quiet Mode suppresses interruptions without touching the
             * transcript (A.48). Important and critical still get through --
             * quiet is not deaf.
             *
             * A14b: it *was* deaf, and the line above was the claim it broke.
             *
             * Quiet mode dropped `normal` as well as `background`, and `other`
             * -- the category every line of ordinary game text arrives under --
             * is `normal`. So turning on "fewer interruptions" silenced the
             * game itself.
             *
             * For a sighted player that was invisible: the console is right
             * there and nothing appears to be lost. For somebody listening it
             * was total silence, because the console is deliberately
             * `aria-live="off"` and announcements are the only channel they
             * have. The setting's own description -- "Nothing is lost, it is
             * still in the log" -- is only true if you can read the log, which
             * is exactly the assumption this client should not be making.
             *
             * So: `background` only. That is the incidental chatter people mean
             * by interruptions -- resource ticks, inventory changes, media
             * events -- and it leaves the game audible. Combat is already off
             * by default through `announceCombat`, which is the right control
             * for that and is one a player chose.
             */
            if (preferenceValue("cognitive.quietMode", false)) {
                if (priority === "background") {
                    return null;
                }
            }

            return priority;
        }

        /**
         * Put a message into a live region, and speak it if speech is on.
         *
         * A15. The speech hook is here, at the moment the announcer has already
         * decided a message should be heard, rather than as a second subscriber
         * somewhere else. Everything above this line -- category, priority,
         * per-category preferences, announcement mode, quiet mode, review mode,
         * burst aggregation -- is decision-making, and duplicating any of it for
         * a second output would guarantee the two eventually disagreed about
         * what a player asked for.
         *
         * Speech is therefore a *renderer* of the announcer's output, exactly as
         * the live region is. It knows nothing about categories.
         *
         * @param {HTMLElement} region The live region to write to.
         * @param {string} message What to say.
         * @param {string} lastRef The previous message written here.
         * @param {boolean} urgent Whether this interrupts.
         * @returns {string} The message, as the new `lastRef`.
         */
        function write(region, message, lastRef, urgent) {
            if (speak) {
                speak(message, { urgent: !!urgent });
            }
            if (!region) {
                return lastRef;
            }
            // Re-setting identical text does not reliably re-trigger an
            // announcement, so the region is cleared first when a message
            // repeats. Without this, "Health is low" said twice is said once.
            if (message === lastRef) {
                region.textContent = "";
            }
            region.textContent = message;
            return message;
        }

        /*
         * Announce something.
         *
         * `options.category` and `options.priority` are both optional; a bare
         * string still works, which is what the existing call sites pass.
         */
        function announce(message, options) {
            if (!message) {
                return null;
            }
            var settings = options || {};
            var category = settings.category || "other";
            var priority = resolve(category, settings.priority);

            if (priority === null) {
                return null;
            }

            if (reviewing && priority !== "critical" && priority !== "important") {
                // Held rather than dropped. The player is reading; interrupting
                // them is the thing Review Mode exists to prevent, but the
                // event still happened and they are entitled to know it did.
                deferred.push({ message: message, category: category, priority: priority });
                return null;
            }

            /*
             * Burst handling.
             *
             * Measured on announceable events only -- events the player has
             * already chosen not to hear do not count towards a flood, because
             * they were never going to be spoken.
             */
            var moment = now();

            // Prune BEFORE counting, and count what was already there rather
            // than including this event. An earlier version pushed first and
            // then tested for an empty window, which could never be true --
            // so a burst never formally ended and the next message minutes
            // later was still reported as "heavy activity".
            while (recent.length && recent[0] < moment - FLOOD.windowMs) {
                recent.shift();
            }
            var quiet = recent.length === 0;
            recent.push(moment);

            var flooding = recent.length >= FLOOD.threshold;
            if (flooding && burstStartedAt === null) {
                burstStartedAt = moment;
            }

            var settledSummary = null;
            if (quiet && burstStartedAt !== null) {
                // A full window with nothing in it ends the burst. Anything
                // held back is reported rather than forgotten -- but NOT
                // written straight to the region, because the message that
                // ended the burst is about to be written there too and a live
                // region only ever announces its latest text. Writing both
                // would silently lose the summary.
                //
                // So it is carried and prefixed onto that message instead.
                if (suppressedTotal) {
                    settledSummary = buildBurstSummary(true);
                }
                burstStartedAt = null;
                aggregating = false;
                suppressed = {};
                suppressedTotal = 0;
                lastSummaryAt = moment;
            }

            var sustained = burstStartedAt !== null &&
                (moment - burstStartedAt) >= FLOOD.sustainMs;

            if (sustained && NEVER_AGGREGATE.indexOf(category) === -1 &&
                    priority !== "critical" && priority !== "important") {
                if (!aggregating) {
                    // The clock for the first summary starts when aggregation
                    // starts, not at zero. Otherwise the very first suppressed
                    // event trips the interval immediately and announces
                    // "Heavy activity. 1 chat event.", which is both useless
                    // and faintly absurd.
                    aggregating = true;
                    lastSummaryAt = moment;
                }
                suppressed[category] = (suppressed[category] || 0) + 1;
                suppressedTotal += 1;
                record(message, category, priority);

                if (moment - lastSummaryAt >= FLOOD.summaryMs) {
                    flushBurstSummary(moment, false);
                }
                return priority;
            }

            record(message, category, priority);

            var spoken = settledSummary ? settledSummary + " " + message : message;

            if (URGENT_PRIORITIES.indexOf(priority) !== -1) {
                lastUrgent = write(urgentRegion, spoken, lastUrgent, true);
                if (settledSummary) {
                    // The tail of a burst is not urgent even when the message
                    // that ended it is, so it goes to the polite region too
                    // rather than riding an interruption.
                    lastPolite = write(politeRegion, settledSummary, lastPolite, false);
                }
            } else {
                lastPolite = write(politeRegion, spoken, lastPolite, false);
            }
            return priority;
        }

        /*
         * Say what was skipped, in one line.
         *
         * The count is the information. "Twelve further combat events" tells a
         * player that a fight is happening and that they are not missing a
         * conversation, which is all the announcement channel can usefully
         * convey at that rate.
         */
        function buildBurstSummary(ending) {
            if (!suppressedTotal) {
                return null;
            }
            var parts = Object.keys(suppressed).map(function (category) {
                var count = suppressed[category];
                return count + " " + category + (count === 1 ? " event" : " events");
            });
            return (ending ? "Activity settled. " : "Heavy activity. ") +
                parts.join(", ") + ".";
        }

        function flushBurstSummary(moment, ending) {
            var message = buildBurstSummary(ending);
            if (!message) {
                return null;
            }
            suppressed = {};
            suppressedTotal = 0;
            lastSummaryAt = moment;
            if (ending) {
                aggregating = false;
            }
            lastPolite = write(politeRegion, message, lastPolite, false);
            return message;
        }

        function record(message, category, priority) {
            history.push({ message: message, category: category, priority: priority });
            if (history.length > MAX_HISTORY) {
                history.shift();
            }
        }

        /* --- Review Mode hooks, completed in M17 ------------------------ */

        function beginReview() {
            reviewing = true;
            deferred = [];
        }

        /*
         * Leave Review Mode.
         *
         * Returns a summary rather than replaying the queue. Reading out
         * seventeen held announcements in a row is worse than the interruption
         * they were held to avoid (A.17), so the caller gets counts and can
         * offer to show the detail.
         */
        function endReview() {
            reviewing = false;
            var held = deferred;
            deferred = [];

            if (!held.length) {
                return { total: 0, byCategory: {}, events: [] };
            }
            var byCategory = {};
            held.forEach(function (entry) {
                byCategory[entry.category] = (byCategory[entry.category] || 0) + 1;
            });
            return { total: held.length, byCategory: byCategory, events: held };
        }

        function summarize(result) {
            if (!result || !result.total) {
                return "";
            }
            var parts = Object.keys(result.byCategory).map(function (category) {
                var count = result.byCategory[category];
                return count + " " + category + (count === 1 ? " event" : " events");
            });
            return result.total + " events occurred while reviewing. " + parts.join(", ") + ".";
        }

        return {
            announce: announce,
            resolve: resolve,
            //: Attach or replace the speech renderer. Passing null detaches it.
            setSpeaker: function (renderer) { speak = renderer || null; },
            flushBurstSummary: function () { return flushBurstSummary(now(), true); },
            isFlooding: function () {
                return burstStartedAt !== null &&
                    (now() - burstStartedAt) >= FLOOD.sustainMs;
            },
            suppressedCount: function () { return suppressedTotal; },
            beginReview: beginReview,
            endReview: endReview,
            summarize: summarize,
            isReviewing: function () { return reviewing; },
            deferredCount: function () { return deferred.length; },
            history: function () { return history.slice(); }
        };
    }

    window.AetosAnnouncementManager = {
        create: createAnnouncer,
        FLOOD: FLOOD,
        NEVER_AGGREGATE: NEVER_AGGREGATE.slice(),
        PRIORITIES: PRIORITIES.slice(),
        URGENT_PRIORITIES: URGENT_PRIORITIES.slice(),
        CATEGORY_PRIORITY: CATEGORY_PRIORITY,
        CATEGORY_PREFERENCE: CATEGORY_PREFERENCE
    };

})(window, document);
