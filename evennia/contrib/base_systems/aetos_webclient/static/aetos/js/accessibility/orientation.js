/*
 * Aetos orientation.  Addendum A.36, A.37, A.38, A.39, A.40.
 *
 * "Where am I, how did I get here, and what was I doing?"
 *
 * WHO THIS IS FOR. Anyone who was interrupted. A player who took a phone call,
 * whose screen reader was talking over the game, who lost their place on a
 * braille display, who has an attention or memory condition, or who simply
 * looked away for two minutes. The game does not pause for any of them, and
 * scrollback answers "what happened" rather than "where am I".
 *
 * THE HARD RULE: NO INTENTION INFERENCE (A11Y-COG-002).
 *
 * Aetos never says "you were trying to...", "you wanted to..." or "your
 * objective is...". It reports **facts**: where you are, how you got here, who
 * is present, what you did most recently, what you asked to be reminded about.
 *
 * The reason is not modesty. A client that guessed at intent would be
 * confidently wrong at exactly the moment somebody was relying on it to
 * reorient -- and a wrong answer delivered with certainty is worse than no
 * answer, because it costs the player the time to discover it was wrong plus
 * the trust they had in the feature. Someone using this because their memory is
 * unreliable is the last person who should be handed a plausible fabrication.
 *
 * Recent *commands* are facts. What they were for is not.
 */

(function (window) {
    "use strict";

    //: How many rooms of history to keep. Enough to retrace a session's
    //: wandering; not so many that "how did I get here" becomes its own maze.
    var MAX_BREADCRUMBS = 50;

    //: Recent commands shown when reorienting. Four is roughly "what I was just
    //: doing"; twenty is a transcript, which the player already has.
    var RECENT_COMMANDS = 4;

    /*
     * Directions that reverse cleanly.
     *
     * Only the ones whose inverse is unambiguous. "in" reverses to "out" and
     * "enter" does not reverse to anything reliable -- a game may have entered
     * you into somewhere with three exits.
     */
    var INVERSE = {
        north: "south", south: "north",
        east: "west", west: "east",
        northeast: "southwest", southwest: "northeast",
        northwest: "southeast", southeast: "northwest",
        up: "down", down: "up",
        "in": "out", out: "in",
        n: "s", s: "n", e: "w", w: "e",
        ne: "sw", sw: "ne", nw: "se", se: "nw",
        u: "d", d: "u"
    };

    function createOrientation(services) {
        var settings = services || {};
        var store = settings.store || null;
        var announce = settings.announce || function () {};

        var breadcrumbs = [];
        var recentCommands = [];
        var lastRoomId = null;

        /*
         * Record a move.
         *
         * Driven by **authoritative room changes**, not by typed movement
         * commands (A11Y-COG-003). A player who types "north" into a wall has
         * not moved, and a breadcrumb trail built from intentions rather than
         * outcomes would be a trail to somewhere they have never been --
         * precisely useless to the person relying on it.
         */
        function observeRoom(room) {
            if (!room || !room.id || room.id === lastRoomId) {
                return null;
            }
            var entry = {
                id: room.id,
                name: room.name || room.id,
                // How they arrived, when the last command plausibly explains it.
                // Recorded as an observation, never asserted as intent.
                via: pendingDirection
            };
            pendingDirection = null;
            lastRoomId = room.id;

            breadcrumbs.push(entry);
            if (breadcrumbs.length > MAX_BREADCRUMBS) {
                breadcrumbs.shift();
            }
            return entry;
        }

        var pendingDirection = null;

        /*
         * Note a command the player sent.
         *
         * A movement-shaped command is remembered as the likely explanation for
         * the *next* room change. "Likely" is doing real work there: if the
         * command failed and the player moved for another reason, the label is
         * wrong -- so it is only ever shown as "from X by going north", a
         * description of the trail rather than a claim about causation.
         */
        function observeCommand(text) {
            var command = String(text || "").trim();
            if (!command) {
                return;
            }
            recentCommands.push(command);
            if (recentCommands.length > RECENT_COMMANDS) {
                recentCommands.shift();
            }
            var lowered = command.toLowerCase();
            if (Object.prototype.hasOwnProperty.call(INVERSE, lowered)) {
                pendingDirection = lowered;
            }
        }

        /* --- Reorient Me (A11Y-COG-001) ---------------------------------- */

        /*
         * A concise summary of what is true, as facts.
         *
         * Every line comes from the authoritative store or from something the
         * player themselves did. Nothing is inferred, and anything unknown is
         * omitted rather than guessed at.
         */
        function reorient() {
            var room = (store && store.get("room")) || {};
            var entities = ((store && store.get("entities")) || {}).items || [];
            var resources = ((store && store.get("resources")) || {}).items || [];
            var effects = ((store && store.get("effects")) || {}).items || [];
            var target = (store && store.get("target")) || {};

            var report = { sections: [] };

            function section(title, lines) {
                var kept = (lines || []).filter(Boolean);
                if (kept.length) {
                    report.sections.push({ title: title, lines: kept });
                }
            }

            section("Current location", [room.name || null]);

            var previous = breadcrumbs.length > 1
                ? breadcrumbs[breadcrumbs.length - 2]
                : null;
            var here = breadcrumbs[breadcrumbs.length - 1];
            section("You arrived", [
                previous
                    ? "From " + previous.name +
                      (here && here.via ? " by going " + here.via + "." : ".")
                    : null
            ]);

            var exits = (room.exits || []).map(function (exit) {
                return exit.direction || exit.name;
            });
            section("Exits", [exits.length ? exits.join(", ") + "." : "None visible."]);

            var people = entities
                .filter(function (entry) { return entry.kind === "character"; })
                .map(function (entry) { return entry.name; });
            section("People here", [people.length ? people.join(", ") + "." : null]);

            var status = resources.map(function (resource) {
                return resource.label + " " + resource.value +
                    (typeof resource.maximum === "number" ? "/" + resource.maximum : "") +
                    (resource.state_text ? " " + resource.state_text : "");
            });
            if (effects.length) {
                status.push(effects.map(function (effect) {
                    return effect.label;
                }).join(", ") + ".");
            }
            section("Character", status);

            section("Target", [target && target.name ? target.name + "." : null]);

            /*
             * Recent actions -- what you did, never what it was for.
             *
             * This is the line A11Y-COG-002 draws. "Looked at Captain Renn"
             * is a fact. "You were investigating Captain Renn" is a story, and
             * a client that told it would eventually tell the wrong one.
             */
            section("You recently sent", recentCommands.slice().reverse());

            var pinned = settings.pinnedReminders ? settings.pinnedReminders() : [];
            section("Pinned", pinned.map(function (item) { return item.text; }));

            var queue = settings.queueState ? settings.queueState() : null;
            section("In progress", [
                queue && queue.running
                    ? (queue.label || "Queued commands") + ", " +
                      queue.remaining + " of " + queue.total + " remaining."
                    : null
            ]);

            return report;
        }

        /*
         * Speak the summary.
         *
         * `important`, so it is heard even in Quiet Mode -- somebody who asked
         * where they are has asked a direct question, and quiet is about
         * unsolicited interruption rather than about refusing to answer.
         */
        function speakReorientation() {
            var report = reorient();
            /*
             * Semicolons between the lines of a section, full stops between
             * sections.
             *
             * Read aloud, a space-joined list is a single run-on phrase:
             * "You recently sent west look at renn east north" is not something
             * anybody can parse by ear. Punctuation is what makes a spoken list
             * a list -- every screen reader pauses on it.
             */
            var text = report.sections.map(function (section) {
                return section.title + ": " + section.lines.join("; ");
            }).join(". ");
            announce(text || "Nothing is known yet.", {
                category: "system",
                priority: "important"
            });
            return report;
        }

        /* --- How I Got Here (A11Y-COG-003) -------------------------------- */

        function trail() {
            return breadcrumbs.slice();
        }

        /*
         * The route back, as directions.
         *
         * Only reverses steps whose inverse is unambiguous. A trail containing
         * "enter the portal" stops there and says so, rather than inventing an
         * exit that may not exist -- the ambiguity rule (C.6) applied to
         * movement.
         */
        function backtrack() {
            var steps = [];
            for (var i = breadcrumbs.length - 1; i > 0; i--) {
                var via = breadcrumbs[i].via;
                if (!via || !Object.prototype.hasOwnProperty.call(INVERSE, via)) {
                    break;
                }
                steps.push(INVERSE[via]);
            }
            return steps;
        }

        /*
         * Walk back along the trail.  A.40.
         *
         * Ordinary movement commands through the ordinary queue, which stops on
         * failure. Aetos is not authoritative about movement and a locked door
         * ends the walk exactly where it should.
         */
        function walkBack() {
            var steps = backtrack();
            if (!steps.length) {
                announce(
                    breadcrumbs.length > 1
                        ? "The way back cannot be worked out from here."
                        : "No movement recorded yet.",
                    { category: "system", priority: "important" }
                );
                return null;
            }
            if (settings.queueRoute) {
                settings.queueRoute(steps);
            }
            announce(
                "Retracing " + steps.length +
                (steps.length === 1 ? " step." : " steps."),
                { category: "movement", priority: "important" }
            );
            return steps;
        }

        function clear() {
            breadcrumbs = [];
            recentCommands = [];
            lastRoomId = null;
            pendingDirection = null;
            return true;
        }

        return {
            observeRoom: observeRoom,
            observeCommand: observeCommand,
            reorient: reorient,
            speakReorientation: speakReorientation,
            trail: trail,
            backtrack: backtrack,
            walkBack: walkBack,
            clear: clear,
            recentCommands: function () { return recentCommands.slice(); }
        };
    }

    window.AetosOrientation = {
        create: createOrientation,
        INVERSE: INVERSE,
        MAX_BREADCRUMBS: MAX_BREADCRUMBS,
        RECENT_COMMANDS: RECENT_COMMANDS
    };

})(window);
